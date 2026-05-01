from __future__ import annotations

import os
from dataclasses import dataclass

KNOWLEDGE_PRIORITY_BONUS = 50
RETRIEVAL_SCORING_TEXT_LIMIT = 4000
RETRIEVAL_PREVIEW_LIMIT = 220


@dataclass(frozen=True, slots=True)
class RelationExpansionConfig:
    depth_limit: int = 2
    min_confidence: float = 0.3
    decay_factor: float = 0.6


@dataclass(frozen=True, slots=True)
class RetrievalRerankConfig:
    enabled: bool = True
    top_n: int = 10
    model: str = ""
    url: str = ""
    timeout_seconds: int = 20

    @property
    def configured(self) -> bool:
        return bool(self.model.strip() and self.url.strip())


DEFAULT_RELATION_EXPANSION_CONFIG = RelationExpansionConfig()
DEFAULT_RETRIEVAL_RERANK_CONFIG = RetrievalRerankConfig()


def resolve_retrieval_rerank_config() -> RetrievalRerankConfig:
    enabled_raw = os.environ.get("SWL_RETRIEVAL_RERANK_ENABLED", "").strip().lower()
    if enabled_raw in {"0", "false", "no", "off"}:
        enabled = False
    elif enabled_raw in {"1", "true", "yes", "on"}:
        enabled = True
    else:
        enabled = DEFAULT_RETRIEVAL_RERANK_CONFIG.enabled

    top_n_raw = os.environ.get("SWL_RETRIEVAL_RERANK_TOP_N", "").strip()
    try:
        top_n = int(top_n_raw) if top_n_raw else DEFAULT_RETRIEVAL_RERANK_CONFIG.top_n
    except ValueError:
        top_n = DEFAULT_RETRIEVAL_RERANK_CONFIG.top_n
    if top_n <= 0:
        top_n = DEFAULT_RETRIEVAL_RERANK_CONFIG.top_n

    model = os.environ.get("SWL_RETRIEVAL_RERANK_MODEL", "").strip()
    url = os.environ.get("SWL_RETRIEVAL_RERANK_URL", "").strip().rstrip("/")
    timeout_raw = os.environ.get("SWL_RETRIEVAL_RERANK_TIMEOUT_SECONDS", "").strip()
    try:
        timeout_seconds = int(timeout_raw) if timeout_raw else DEFAULT_RETRIEVAL_RERANK_CONFIG.timeout_seconds
    except ValueError:
        timeout_seconds = DEFAULT_RETRIEVAL_RERANK_CONFIG.timeout_seconds
    if timeout_seconds <= 0:
        timeout_seconds = DEFAULT_RETRIEVAL_RERANK_CONFIG.timeout_seconds

    return RetrievalRerankConfig(
        enabled=enabled,
        top_n=top_n,
        model=model,
        url=url,
        timeout_seconds=timeout_seconds,
    )
