from __future__ import annotations

import os


DEFAULT_SWL_API_BASE_URL = "http://localhost:3000"
DEFAULT_SWL_CHAT_MODEL = "gpt-4o-mini"
DEFAULT_SWL_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_SWL_EMBEDDING_DIMENSIONS = 1536


def resolve_swl_api_base_url() -> str:
    configured = os.environ.get("SWL_API_BASE_URL", "").strip()
    if configured:
        return configured.rstrip("/")
    return DEFAULT_SWL_API_BASE_URL


def resolve_swl_api_key() -> str:
    return os.environ.get("SWL_API_KEY", "").strip()


def resolve_swl_chat_model(*, explicit_model: str | None = None) -> str:
    configured = str(explicit_model or "").strip()
    if configured:
        return configured
    configured = os.environ.get("SWL_CHAT_MODEL", "").strip()
    if configured:
        return configured
    return DEFAULT_SWL_CHAT_MODEL


def resolve_swl_embedding_model(*, explicit_model: str | None = None) -> str:
    configured = str(explicit_model or "").strip()
    if configured:
        return configured
    configured = os.environ.get("SWL_EMBEDDING_MODEL", "").strip()
    if configured:
        return configured
    return DEFAULT_SWL_EMBEDDING_MODEL


def resolve_swl_embedding_dimensions(*, explicit_dimensions: int | None = None) -> int:
    if explicit_dimensions and explicit_dimensions > 0:
        return int(explicit_dimensions)
    configured = os.environ.get("SWL_EMBEDDING_DIMENSIONS", "").strip()
    if configured:
        try:
            parsed = int(configured)
        except ValueError:
            parsed = 0
        if parsed > 0:
            return parsed
    return DEFAULT_SWL_EMBEDDING_DIMENSIONS


def resolve_swl_embedding_api_base_url() -> str:
    configured = os.environ.get("SWL_EMBEDDING_API_BASE_URL", "").strip()
    if configured:
        return configured.rstrip("/")
    return resolve_swl_api_base_url()
