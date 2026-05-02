from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


OperatorSource = Literal["cli", "system_auto", "librarian_side_effect"]
_VALID_OPERATOR_SOURCES = {"cli", "system_auto", "librarian_side_effect"}


class ProposalTarget(Enum):
    CANONICAL_KNOWLEDGE = "canonical_knowledge"
    ROUTE_METADATA = "route_metadata"
    POLICY = "policy"


@dataclass(frozen=True)
class OperatorToken:
    """Source marker for governance writes.

    This intentionally carries no actor identity in Phase 61. Adding source
    values changes the governance boundary and must go through a design phase.
    """

    source: OperatorSource
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.source not in _VALID_OPERATOR_SOURCES:
            expected = ", ".join(sorted(_VALID_OPERATOR_SOURCES))
            raise ValueError(f"Invalid operator token source: {self.source!r}. Expected one of: {expected}")


@dataclass(frozen=True)
class ApplyResult:
    proposal_id: str
    target: ProposalTarget
    success: bool
    detail: str
    applied_writes: tuple[str, ...] = ()
    payload: object | None = None
