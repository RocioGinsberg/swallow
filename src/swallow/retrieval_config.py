from __future__ import annotations

import os
from dataclasses import dataclass

KNOWLEDGE_PRIORITY_BONUS = 50


@dataclass(frozen=True, slots=True)
class RelationExpansionConfig:
    depth_limit: int = 2
    min_confidence: float = 0.3
    decay_factor: float = 0.6


@dataclass(frozen=True, slots=True)
class RetrievalRerankConfig:
    enabled: bool = True
    top_n: int = 10


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

    return RetrievalRerankConfig(enabled=enabled, top_n=top_n)
