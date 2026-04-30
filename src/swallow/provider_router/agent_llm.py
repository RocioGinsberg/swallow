from __future__ import annotations

import json
import re

from swallow.provider_router._http_helpers import AgentLLMResponse, AgentLLMUnavailable
from swallow.orchestration.runtime_config import resolve_swl_chat_model


def resolve_agent_llm_model(explicit_model: str | None = None) -> str:
    return resolve_swl_chat_model(explicit_model=explicit_model)


def call_agent_llm(
    prompt: str,
    *,
    system: str = "",
    model: str | None = None,
    timeout_seconds: int | None = None,
) -> AgentLLMResponse:
    from .router import invoke_completion

    return invoke_completion(prompt, system=system, model=model, timeout_seconds=timeout_seconds)


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
