from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from swallow.knowledge_retrieval.knowledge_plane import LIBRARIAN_AGENT_WRITE_AUTHORITY
from swallow.orchestration.models import AuditTriggerPolicy
from swallow.provider_router.router import normalize_route_policy_payload, normalize_route_registry_payload
from swallow.truth_governance.governance_models import ProposalTarget
from swallow.truth_governance.truth import DuplicateProposalError, PendingProposalRepo


@dataclass(frozen=True)
class _CanonicalProposal:
    base_dir: Path
    canonical_record: dict[str, object]
    write_authority: str
    mirror_files: bool
    persist_wiki: bool
    persist_wiki_first: bool
    refresh_derived: bool
    supersede_target_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class _RouteMetadataProposal:
    base_dir: Path
    route_registry: dict[str, dict[str, object]] | None = None
    route_policy: dict[str, object] | None = None
    route_weights: dict[str, float] | None = None
    route_capability_profiles: dict[str, dict[str, object]] | None = None
    review_path: Path | None = None


@dataclass(frozen=True)
class _PolicyProposal:
    base_dir: Path
    audit_trigger_policy: AuditTriggerPolicy


@dataclass(frozen=True)
class _MpsPolicyProposal:
    base_dir: Path
    kind: str
    value: int


_PENDING_PROPOSALS = PendingProposalRepo()


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
    supersede_target_ids: Iterable[str] | None = None,
) -> str:
    """Register a canonical proposal payload for the next apply call.

    Current canonical callers construct the canonical record in memory instead
    of persisting a proposal artifact. This compatibility adapter keeps the
    public `apply_proposal(proposal_id, operator_token, target)` signature
    stable while the repository still lacks a durable proposal artifact layer.
    """

    normalized_id = _normalize_proposal_id(proposal_id)
    return _PENDING_PROPOSALS.register(
        ProposalTarget.CANONICAL_KNOWLEDGE,
        normalized_id,
        _CanonicalProposal(
            base_dir=base_dir,
            canonical_record=dict(canonical_record),
            write_authority=write_authority,
            mirror_files=mirror_files,
            persist_wiki=persist_wiki,
            persist_wiki_first=persist_wiki_first,
            refresh_derived=refresh_derived,
            supersede_target_ids=_normalize_supersede_target_ids(supersede_target_ids),
        ),
    )


def register_route_metadata_proposal(
    *,
    base_dir: Path,
    proposal_id: str,
    route_registry: dict[str, dict[str, object]] | None = None,
    route_policy: dict[str, object] | None = None,
    route_weights: dict[str, float] | None = None,
    route_capability_profiles: dict[str, dict[str, object]] | None = None,
    review_path: Path | None = None,
) -> str:
    normalized_id = _normalize_proposal_id(proposal_id)
    if review_path is not None and (
        route_registry is not None
        or route_policy is not None
        or route_weights is not None
        or route_capability_profiles is not None
    ):
        raise ValueError("review_path proposals cannot also carry direct route metadata payloads.")
    if (
        review_path is None
        and route_registry is None
        and route_policy is None
        and route_weights is None
        and route_capability_profiles is None
    ):
        raise ValueError(
            "route metadata proposal requires route_registry, route_policy, route_weights, "
            "route_capability_profiles, or review_path."
        )

    copied_registry = normalize_route_registry_payload(route_registry) if route_registry is not None else None
    copied_policy = normalize_route_policy_payload(route_policy) if route_policy is not None else None
    copied_profiles = None
    if route_capability_profiles is not None:
        copied_profiles = {
            route_name: dict(profile)
            for route_name, profile in route_capability_profiles.items()
        }
    return _PENDING_PROPOSALS.register(
        ProposalTarget.ROUTE_METADATA,
        normalized_id,
        _RouteMetadataProposal(
            base_dir=base_dir,
            route_registry=copied_registry,
            route_policy=copied_policy,
            route_weights=dict(route_weights) if route_weights is not None else None,
            route_capability_profiles=copied_profiles,
            review_path=review_path,
        ),
    )


def register_policy_proposal(
    *,
    base_dir: Path,
    proposal_id: str,
    audit_trigger_policy: AuditTriggerPolicy,
) -> str:
    normalized_id = _normalize_proposal_id(proposal_id)
    if not isinstance(audit_trigger_policy, AuditTriggerPolicy):
        raise TypeError("audit_trigger_policy must be an AuditTriggerPolicy.")
    return _PENDING_PROPOSALS.register(
        ProposalTarget.POLICY,
        normalized_id,
        _PolicyProposal(
            base_dir=base_dir,
            audit_trigger_policy=AuditTriggerPolicy.from_dict(audit_trigger_policy.to_dict()),
        ),
    )


def register_mps_policy_proposal(
    *,
    base_dir: Path,
    proposal_id: str,
    kind: str,
    value: int,
) -> str:
    from swallow.application.services.mps_policy_store import normalize_mps_policy_kind, validate_mps_policy_value

    normalized_id = _normalize_proposal_id(proposal_id)
    normalized_kind = normalize_mps_policy_kind(kind)
    normalized_value = validate_mps_policy_value(normalized_kind, value)
    return _PENDING_PROPOSALS.register(
        ProposalTarget.POLICY,
        normalized_id,
        _MpsPolicyProposal(
            base_dir=base_dir,
            kind=normalized_kind,
            value=normalized_value,
        ),
    )


def load_mps_policy(base_dir: Path, kind: str) -> int | None:
    from swallow.application.services.mps_policy_store import read_mps_policy

    return read_mps_policy(base_dir, kind)


def load_proposal_artifact(proposal_id: str, target: ProposalTarget) -> object:
    return _PENDING_PROPOSALS.load(target, _normalize_proposal_id(proposal_id))


def validate_target(proposal: object, target: ProposalTarget) -> None:
    if target == ProposalTarget.CANONICAL_KNOWLEDGE and not isinstance(proposal, _CanonicalProposal):
        raise TypeError("canonical proposal payload is invalid.")
    if target == ProposalTarget.ROUTE_METADATA and not isinstance(proposal, _RouteMetadataProposal):
        raise TypeError("route metadata proposal payload is invalid.")
    if target == ProposalTarget.POLICY and not isinstance(proposal, (_PolicyProposal, _MpsPolicyProposal)):
        raise TypeError("policy proposal payload is invalid.")


def require_canonical_proposal(proposal: object) -> _CanonicalProposal:
    if not isinstance(proposal, _CanonicalProposal):
        raise TypeError("canonical proposal payload is invalid.")
    return proposal


def require_route_metadata_proposal(proposal: object) -> _RouteMetadataProposal:
    if not isinstance(proposal, _RouteMetadataProposal):
        raise TypeError("route metadata proposal payload is invalid.")
    return proposal


def is_mps_policy_proposal(proposal: object) -> bool:
    return isinstance(proposal, _MpsPolicyProposal)


def require_mps_policy_proposal(proposal: object) -> _MpsPolicyProposal:
    if not isinstance(proposal, _MpsPolicyProposal):
        raise TypeError("policy proposal payload is invalid.")
    return proposal


def require_policy_proposal(proposal: object) -> _PolicyProposal:
    if not isinstance(proposal, _PolicyProposal):
        raise TypeError("policy proposal payload is invalid.")
    return proposal


def _normalize_proposal_id(proposal_id: str) -> str:
    normalized_id = proposal_id.strip()
    if not normalized_id:
        raise ValueError("proposal_id must be a non-empty string.")
    return normalized_id


def _normalize_supersede_target_ids(target_ids: Iterable[str] | None) -> tuple[str, ...]:
    if target_ids is None:
        return ()
    values: Iterable[str]
    if isinstance(target_ids, str):
        values = (target_ids,)
    else:
        values = target_ids

    normalized_ids: list[str] = []
    seen: set[str] = set()
    for target_id in values:
        normalized_id = str(target_id).strip()
        if not normalized_id or normalized_id in seen:
            continue
        seen.add(normalized_id)
        normalized_ids.append(normalized_id)
    return tuple(normalized_ids)
