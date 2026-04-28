from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal

from .canonical_registry import build_canonical_registry_index
from .canonical_reuse import build_canonical_reuse_summary
from .knowledge_store import LIBRARIAN_AGENT_WRITE_AUTHORITY, persist_wiki_entry_from_record
from .paths import canonical_registry_path
from .store import append_canonical_record, save_canonical_registry_index, save_canonical_reuse_policy

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


@dataclass(frozen=True)
class _CanonicalProposal:
    base_dir: Path
    canonical_record: dict[str, object]
    write_authority: str
    mirror_files: bool
    persist_wiki: bool
    persist_wiki_first: bool
    refresh_derived: bool


_PENDING_PROPOSALS: dict[tuple[ProposalTarget, str], object] = {}


def register_canonical_proposal(
    *,
    base_dir: Path,
    proposal_id: str,
    canonical_record: dict[str, object],
    write_authority: str = LIBRARIAN_AGENT_WRITE_AUTHORITY,
    mirror_files: bool = True,
    persist_wiki: bool = True,
    persist_wiki_first: bool = True,
    refresh_derived: bool = False,
) -> str:
    """Register a canonical proposal payload for the next apply call.

    Current canonical callers construct the canonical record in memory instead
    of persisting a proposal artifact. This compatibility adapter keeps the
    public `apply_proposal(proposal_id, operator_token, target)` signature
    stable while the repository still lacks a durable proposal artifact layer.
    """

    normalized_id = proposal_id.strip()
    if not normalized_id:
        raise ValueError("proposal_id must be a non-empty string.")
    _PENDING_PROPOSALS[(ProposalTarget.CANONICAL_KNOWLEDGE, normalized_id)] = _CanonicalProposal(
        base_dir=base_dir,
        canonical_record=dict(canonical_record),
        write_authority=write_authority,
        mirror_files=mirror_files,
        persist_wiki=persist_wiki,
        persist_wiki_first=persist_wiki_first,
        refresh_derived=refresh_derived,
    )
    return normalized_id


def apply_proposal(
    proposal_id: str,
    operator_token: OperatorToken,
    target: ProposalTarget,
) -> ApplyResult:
    """Canonical knowledge / route metadata / policy write boundary."""

    if not isinstance(operator_token, OperatorToken):
        raise TypeError("operator_token must be an OperatorToken.")
    if not isinstance(target, ProposalTarget):
        raise TypeError("target must be a ProposalTarget.")

    proposal = _load_proposal_artifact(proposal_id, target)
    _validate_target(proposal, target)

    if target == ProposalTarget.CANONICAL_KNOWLEDGE:
        result = _apply_canonical(proposal, operator_token, proposal_id=proposal_id)
    elif target == ProposalTarget.ROUTE_METADATA:
        raise NotImplementedError("Route metadata proposal application is implemented in Phase 61 S3.")
    elif target == ProposalTarget.POLICY:
        raise NotImplementedError("Policy proposal application is implemented in Phase 61 S4.")
    else:  # pragma: no cover - enum exhaustiveness guard
        raise ValueError(f"Unsupported proposal target: {target}")

    _emit_event(operator_token, target, result)
    return result


def _load_proposal_artifact(proposal_id: str, target: ProposalTarget) -> object:
    normalized_id = proposal_id.strip()
    if not normalized_id:
        raise ValueError("proposal_id must be a non-empty string.")
    key = (target, normalized_id)
    if key not in _PENDING_PROPOSALS:
        raise ValueError(f"Unknown proposal artifact: {normalized_id} ({target.value})")
    return _PENDING_PROPOSALS[key]


def _validate_target(proposal: object, target: ProposalTarget) -> None:
    if target == ProposalTarget.CANONICAL_KNOWLEDGE and not isinstance(proposal, _CanonicalProposal):
        raise TypeError("canonical proposal payload is invalid.")


def _apply_canonical(proposal: object, _operator_token: OperatorToken, *, proposal_id: str) -> ApplyResult:
    if not isinstance(proposal, _CanonicalProposal):
        raise TypeError("canonical proposal payload is invalid.")

    applied_writes: list[str] = []
    if proposal.persist_wiki and proposal.persist_wiki_first:
        persist_wiki_entry_from_record(
            proposal.base_dir,
            proposal.canonical_record,
            mirror_files=proposal.mirror_files,
            write_authority=proposal.write_authority,
        )
        applied_writes.append("wiki_entry")

    append_canonical_record(proposal.base_dir, proposal.canonical_record)
    applied_writes.append("canonical_registry")

    if proposal.persist_wiki and not proposal.persist_wiki_first:
        persist_wiki_entry_from_record(
            proposal.base_dir,
            proposal.canonical_record,
            mirror_files=proposal.mirror_files,
            write_authority=proposal.write_authority,
        )
        applied_writes.append("wiki_entry")

    if proposal.refresh_derived:
        _refresh_canonical_derivatives(proposal.base_dir)
        applied_writes.extend(["canonical_registry_index", "canonical_reuse_policy"])

    canonical_id = str(proposal.canonical_record.get("canonical_id", "")).strip()
    return ApplyResult(
        proposal_id=proposal_id,
        target=ProposalTarget.CANONICAL_KNOWLEDGE,
        success=True,
        detail=f"canonical_applied canonical_id={canonical_id or '-'}",
        applied_writes=tuple(applied_writes),
    )


def _refresh_canonical_derivatives(base_dir: Path) -> None:
    canonical_records = _load_json_lines(canonical_registry_path(base_dir))
    save_canonical_registry_index(base_dir, build_canonical_registry_index(canonical_records))
    save_canonical_reuse_policy(base_dir, build_canonical_reuse_summary(canonical_records))


def _load_json_lines(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    records: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            records.append(json.loads(stripped))
    return records


def _emit_event(_operator_token: OperatorToken, _target: ProposalTarget, _result: ApplyResult) -> None:
    """Reserved for durable governance audit events once the event repository exists."""

