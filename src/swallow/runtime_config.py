from __future__ import annotations

import os


DEFAULT_SWL_CHAT_MODEL = "gpt-4o-mini"


def resolve_swl_chat_model(*, explicit_model: str | None = None) -> str:
    configured = str(explicit_model or "").strip()
    if configured:
        return configured
    configured = os.environ.get("SWL_CHAT_MODEL", "").strip()
    if configured:
        return configured
    return DEFAULT_SWL_CHAT_MODEL
