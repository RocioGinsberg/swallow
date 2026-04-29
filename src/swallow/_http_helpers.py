from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_NEW_API_CHAT_COMPLETIONS_URL = "http://localhost:3000/v1/chat/completions"


@dataclass(frozen=True, slots=True)
class AgentLLMResponse:
    content: str
    input_tokens: int
    output_tokens: int
    model: str


class AgentLLMUnavailable(RuntimeError):
    """Raised when specialist-agent direct LLM calls are unavailable."""


def resolve_new_api_chat_completions_url() -> str:
    configured = os.environ.get("SWL_API_BASE_URL", "").strip().rstrip("/")
    if configured:
        return f"{configured}/v1/chat/completions"
    return DEFAULT_NEW_API_CHAT_COMPLETIONS_URL


def resolve_new_api_api_key() -> str:
    return os.environ.get("SWL_API_KEY", "").strip()


def http_request_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    api_key = resolve_new_api_api_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def normalize_http_response_content(content: object) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text_value = str(item.get("text", "")).strip()
                if text_value:
                    parts.append(text_value)
            else:
                text_value = str(item).strip()
                if text_value:
                    parts.append(text_value)
        return "\n".join(parts).strip()
    if content is None:
        return ""
    return str(content).strip()


def extract_api_usage(response_data: object) -> tuple[int, int]:
    if not isinstance(response_data, dict):
        return (0, 0)
    usage = response_data.get("usage", {})
    if not isinstance(usage, dict):
        return (0, 0)
    try:
        input_tokens = max(int(usage.get("prompt_tokens", 0) or 0), 0)
    except (TypeError, ValueError):
        input_tokens = 0
    try:
        output_tokens = max(int(usage.get("completion_tokens", 0) or 0), 0)
    except (TypeError, ValueError):
        output_tokens = 0
    return (input_tokens, output_tokens)


def parse_timeout_seconds(raw_value: str) -> int:
    try:
        parsed = int(raw_value)
    except ValueError:
        return 20
    return parsed if parsed > 0 else 20


def clean_output(raw: str | bytes | None) -> str:
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="ignore").strip()
    return raw.strip()
