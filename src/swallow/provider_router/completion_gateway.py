from __future__ import annotations

import json
import os

import httpx

from swallow.provider_router._http_helpers import (
    AgentLLMResponse,
    AgentLLMUnavailable,
    clean_output,
    extract_api_usage,
    http_request_headers,
    normalize_http_response_content,
    parse_timeout_seconds,
    resolve_new_api_api_key,
    resolve_new_api_chat_completions_url,
)
from swallow.orchestration.runtime_config import resolve_swl_chat_model


def invoke_completion(
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
    resolved_model = resolve_swl_chat_model(explicit_model=model)
    messages: list[dict[str, str]] = []
    if system.strip():
        messages.append({"role": "system", "content": system.strip()})
    messages.append({"role": "user", "content": prompt})

    try:
        response = httpx.post(
            resolve_new_api_chat_completions_url(),
            json={"model": resolved_model, "messages": messages},
            headers=http_request_headers(),
            timeout=resolved_timeout,
        )
        response.raise_for_status()
        payload = response.json()
        choices = payload["choices"]
        message = choices[0]["message"]
        content = normalize_http_response_content(message.get("content"))
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
