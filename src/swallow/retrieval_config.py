from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RelationExpansionConfig:
    depth_limit: int = 2
    min_confidence: float = 0.3
    decay_factor: float = 0.6


DEFAULT_RELATION_EXPANSION_CONFIG = RelationExpansionConfig()
