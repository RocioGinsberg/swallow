from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

import httpx

from .executor import (
    _http_request_headers,
    _normalize_http_response_content,
    clean_output,
    extract_api_usage,
    parse_timeout_seconds,
    resolve_new_api_api_key,
    resolve_new_api_chat_completions_url,
)
from .runtime_config import resolve_swl_chat_model


@dataclass(frozen=True, slots=True)
class AgentLLMResponse:
    content: str
    input_tokens: int
    output_tokens: int
    model: str


class AgentLLMUnavailable(RuntimeError):
    """Raised when specialist-agent direct LLM calls are unavailable."""


def resolve_agent_llm_model(explicit_model: str | None = None) -> str:
    return resolve_swl_chat_model(explicit_model=explicit_model)


def call_agent_llm(
    prompt: str,
    *,
    system: str = "",
    model: str | None = None,
    timeout_seconds: int | None = None,
) -> AgentLLMResponse:
    api_key = resolve_new_api_api_key()
    if not api_key:
        raise AgentLLMUnavailable("LLM enhancement unavailable: API key not configured.")

    resolved_timeout = timeout_seconds or parse_timeout_seconds(os.environ.get("AIWF_EXECUTOR_TIMEOUT_SECONDS", "30"))
    resolved_model = resolve_agent_llm_model(model)
    messages: list[dict[str, str]] = []
    if system.strip():
        messages.append({"role": "system", "content": system.strip()})
    messages.append({"role": "user", "content": prompt})

    try:
        response = httpx.post(
            resolve_new_api_chat_completions_url(),
            json={"model": resolved_model, "messages": messages},
            headers=_http_request_headers(),
            timeout=resolved_timeout,
        )
        response.raise_for_status()
        payload = response.json()
        choices = payload["choices"]
        message = choices[0]["message"]
        content = _normalize_http_response_content(message.get("content"))
    except httpx.HTTPError as exc:
        raise AgentLLMUnavailable(f"LLM enhancement unavailable: {exc}") from exc
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise AgentLLMUnavailable(f"LLM enhancement returned an unreadable payload: {exc}") from exc

    if not content:
        raise AgentLLMUnavailable("LLM enhancement returned an empty response.")

    input_tokens, output_tokens = extract_api_usage(payload)
    returned_model = clean_output(str(payload.get("model", "") or resolved_model)) or resolved_model
    return AgentLLMResponse(
        content=content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        model=returned_model,
    )


def extract_json_object(raw_content: str) -> dict[str, object]:
    content = str(raw_content or "").strip()
    if not content:
        raise ValueError("LLM content was empty.")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        return parsed

    for pattern in (r"\{.*\}", r"\[.*\]"):
        match = re.search(pattern, content, flags=re.DOTALL)
        if not match:
            continue
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("LLM content did not contain a valid JSON object.")
