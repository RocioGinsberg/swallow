from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal

from swallow.knowledge_retrieval.knowledge_plane import LIBRARIAN_AGENT_WRITE_AUTHORITY
from swallow.orchestration.models import AuditTriggerPolicy
from swallow.provider_router.router import (
    load_route_capability_profiles,
    load_route_weights,
    normalize_route_policy_payload,
    normalize_route_registry_payload,
    normalize_route_name,
    route_by_name,
)
from swallow.truth_governance.truth import DuplicateProposalError, KnowledgeRepo, PendingProposalRepo, PolicyRepo, RouteRepo

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


@dataclass(frozen=True)
class _CanonicalProposal:
    base_dir: Path
    canonical_record: dict[str, object]
    write_authority: str
    mirror_files: bool
    persist_wiki: bool
    persist_wiki_first: bool
    refresh_derived: bool


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
logger = logging.getLogger(__name__)


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
    normalized_id = proposal_id.strip()
    if not normalized_id:
        raise ValueError("proposal_id must be a non-empty string.")
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
    normalized_id = proposal_id.strip()
    if not normalized_id:
        raise ValueError("proposal_id must be a non-empty string.")
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
    from swallow.surface_tools.mps_policy_store import normalize_mps_policy_kind, validate_mps_policy_value

    normalized_id = proposal_id.strip()
    if not normalized_id:
        raise ValueError("proposal_id must be a non-empty string.")
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
    from swallow.surface_tools.mps_policy_store import read_mps_policy

    return read_mps_policy(base_dir, kind)


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
        result = _apply_route_metadata(proposal, operator_token, proposal_id=proposal_id)
    elif target == ProposalTarget.POLICY:
        result = _apply_policy(proposal, operator_token, proposal_id=proposal_id)
    else:  # pragma: no cover - enum exhaustiveness guard
        raise ValueError(f"Unsupported proposal target: {target}")

    _emit_event(operator_token, target, result)
    return result


def _load_proposal_artifact(proposal_id: str, target: ProposalTarget) -> object:
    normalized_id = proposal_id.strip()
    if not normalized_id:
        raise ValueError("proposal_id must be a non-empty string.")
    return _PENDING_PROPOSALS.load(target, normalized_id)


def _validate_target(proposal: object, target: ProposalTarget) -> None:
    if target == ProposalTarget.CANONICAL_KNOWLEDGE and not isinstance(proposal, _CanonicalProposal):
        raise TypeError("canonical proposal payload is invalid.")
    if target == ProposalTarget.ROUTE_METADATA and not isinstance(proposal, _RouteMetadataProposal):
        raise TypeError("route metadata proposal payload is invalid.")
    if target == ProposalTarget.POLICY and not isinstance(proposal, (_PolicyProposal, _MpsPolicyProposal)):
        raise TypeError("policy proposal payload is invalid.")


def _apply_canonical(proposal: object, _operator_token: OperatorToken, *, proposal_id: str) -> ApplyResult:
    if not isinstance(proposal, _CanonicalProposal):
        raise TypeError("canonical proposal payload is invalid.")

    applied_writes = KnowledgeRepo()._promote_canonical(
        base_dir=proposal.base_dir,
        canonical_record=proposal.canonical_record,
        write_authority=proposal.write_authority,
        mirror_files=proposal.mirror_files,
        persist_wiki=proposal.persist_wiki,
        persist_wiki_first=proposal.persist_wiki_first,
        refresh_derived=proposal.refresh_derived,
    )
    canonical_id = str(proposal.canonical_record.get("canonical_id", "")).strip()
    return ApplyResult(
        proposal_id=proposal_id,
        target=ProposalTarget.CANONICAL_KNOWLEDGE,
        success=True,
        detail=f"canonical_applied canonical_id={canonical_id or '-'}",
        applied_writes=applied_writes,
    )


def _apply_route_metadata(proposal: object, _operator_token: OperatorToken, *, proposal_id: str) -> ApplyResult:
    if not isinstance(proposal, _RouteMetadataProposal):
        raise TypeError("route metadata proposal payload is invalid.")
    if proposal.review_path is not None:
        return _apply_route_review_metadata(proposal, proposal_id=proposal_id)

    applied_writes = RouteRepo()._apply_metadata_change(
        base_dir=proposal.base_dir,
        route_registry=proposal.route_registry,
        route_policy=proposal.route_policy,
        route_weights=proposal.route_weights,
        route_capability_profiles=proposal.route_capability_profiles,
        proposal_id=proposal_id,
    )

    return ApplyResult(
        proposal_id=proposal_id,
        target=ProposalTarget.ROUTE_METADATA,
        success=True,
        detail="route_metadata_applied",
        applied_writes=applied_writes,
    )


def _apply_route_review_metadata(proposal: _RouteMetadataProposal, *, proposal_id: str) -> ApplyResult:
    from swallow.surface_tools.meta_optimizer import (
        OptimizationProposalApplicationRecord,
        ProposalApplicationEntry,
        _normalize_task_family_name,
        _timestamp_token,
        _write_json,
        load_optimization_proposal_review,
    )
    from swallow.orchestration.models import utc_now
    from swallow.surface_tools.paths import (
        optimization_proposal_application_path,
        route_capabilities_path,
        route_weights_path,
    )

    assert proposal.review_path is not None
    review_path = proposal.review_path
    review_record = load_optimization_proposal_review(review_path)
    approved_entries = [entry for entry in review_record.entries if entry.decision == "approved"]
    if not approved_entries:
        raise ValueError(f"No approved proposals found in {review_path}")

    updated_weights = load_route_weights(proposal.base_dir)
    existing_profiles = load_route_capability_profiles(proposal.base_dir)
    updated_profiles = {
        route_name: {
            "task_family_scores": dict(profile.get("task_family_scores", {}))
            if isinstance(profile.get("task_family_scores", {}), dict)
            else {},
            "unsupported_task_types": list(profile.get("unsupported_task_types", []))
            if isinstance(profile.get("unsupported_task_types", []), list)
            else [],
        }
        for route_name, profile in existing_profiles.items()
    }

    for entry in approved_entries:
        route_name = normalize_route_name(entry.route_name)
        if entry.proposal_type == "route_weight":
            if not route_name:
                raise ValueError(f"Approved route_weight proposal is missing route_name: {entry.proposal_id}")
            if route_by_name(route_name) is None:
                raise ValueError(f"Unknown route in approved proposal: {route_name}")
            if entry.suggested_weight is None:
                raise ValueError(f"Approved route_weight proposal is missing suggested_weight: {entry.proposal_id}")
            continue
        if entry.proposal_type == "route_capability":
            if not route_name:
                raise ValueError(f"Approved route_capability proposal is missing route_name: {entry.proposal_id}")
            if route_by_name(route_name) is None:
                raise ValueError(f"Unknown route in approved proposal: {route_name}")
            task_family = _normalize_task_family_name(entry.task_family)
            if not task_family:
                raise ValueError(f"Approved route_capability proposal is missing task_family: {entry.proposal_id}")
            if not entry.mark_task_family_unsupported and entry.suggested_task_family_score is None:
                raise ValueError(
                    f"Approved route_capability proposal is missing suggested_task_family_score: {entry.proposal_id}"
                )

    entries: list[ProposalApplicationEntry] = []
    rollback_weights: dict[str, float] = {}
    rollback_capability_profiles: dict[str, dict[str, object]] = {}
    applied_count = 0
    noop_count = 0
    skipped_count = 0
    for entry in approved_entries:
        if entry.proposal_type == "route_capability":
            route_name = normalize_route_name(entry.route_name)
            task_family = _normalize_task_family_name(entry.task_family)
            profile = updated_profiles.setdefault(
                route_name,
                {"task_family_scores": {}, "unsupported_task_types": []},
            )
            task_family_scores = dict(profile.get("task_family_scores", {}))
            unsupported_task_types = {
                _normalize_task_family_name(item)
                for item in profile.get("unsupported_task_types", [])
                if _normalize_task_family_name(item)
            }
            before_score_raw = task_family_scores.get(task_family)
            before_score = round(float(before_score_raw), 6) if isinstance(before_score_raw, int | float) else None
            before_unsupported = task_family in unsupported_task_types
            rollback_capability_profiles.setdefault(
                route_name,
                {
                    "task_family_scores": dict(task_family_scores),
                    "unsupported_task_types": sorted(unsupported_task_types),
                },
            )

            if entry.mark_task_family_unsupported:
                if before_unsupported:
                    noop_count += 1
                    entries.append(
                        ProposalApplicationEntry(
                            proposal_id=entry.proposal_id,
                            proposal_type=entry.proposal_type,
                            route_name=route_name,
                            task_family=task_family,
                            status="noop",
                            detail="Task family is already marked unsupported for this route.",
                            before_task_family_score=before_score,
                            after_task_family_score=before_score,
                            before_task_family_unsupported=before_unsupported,
                            after_task_family_unsupported=before_unsupported,
                        )
                    )
                    continue
                unsupported_task_types.add(task_family)
                task_family_scores.pop(task_family, None)
                applied_count += 1
                updated_profiles[route_name] = {
                    "task_family_scores": task_family_scores,
                    "unsupported_task_types": sorted(unsupported_task_types),
                }
                entries.append(
                    ProposalApplicationEntry(
                        proposal_id=entry.proposal_id,
                        proposal_type=entry.proposal_type,
                        route_name=route_name,
                        task_family=task_family,
                        status="applied",
                        detail="Marked the task family unsupported in the persisted route capability profile.",
                        before_task_family_score=before_score,
                        after_task_family_score=None,
                        before_task_family_unsupported=before_unsupported,
                        after_task_family_unsupported=True,
                    )
                )
                continue

            after_score = round(float(entry.suggested_task_family_score or 0.0), 6)
            if before_score is not None and abs(before_score - after_score) <= 1e-9 and not before_unsupported:
                noop_count += 1
                entries.append(
                    ProposalApplicationEntry(
                        proposal_id=entry.proposal_id,
                        proposal_type=entry.proposal_type,
                        route_name=route_name,
                        task_family=task_family,
                        status="noop",
                        detail="Suggested capability score already matches the current persisted value.",
                        before_task_family_score=before_score,
                        after_task_family_score=after_score,
                        before_task_family_unsupported=before_unsupported,
                        after_task_family_unsupported=before_unsupported,
                    )
                )
                continue

            task_family_scores[task_family] = after_score
            unsupported_task_types.discard(task_family)
            updated_profiles[route_name] = {
                "task_family_scores": task_family_scores,
                "unsupported_task_types": sorted(unsupported_task_types),
            }
            applied_count += 1
            entries.append(
                ProposalApplicationEntry(
                    proposal_id=entry.proposal_id,
                    proposal_type=entry.proposal_type,
                    route_name=route_name,
                    task_family=task_family,
                    status="applied",
                    detail="Persisted the approved route capability score.",
                    before_task_family_score=before_score,
                    after_task_family_score=after_score,
                    before_task_family_unsupported=before_unsupported,
                    after_task_family_unsupported=False,
                )
            )
            continue

        if entry.proposal_type != "route_weight":
            skipped_count += 1
            entries.append(
                ProposalApplicationEntry(
                    proposal_id=entry.proposal_id,
                    proposal_type=entry.proposal_type,
                    route_name=normalize_route_name(entry.route_name),
                    task_family=entry.task_family,
                    status="skipped",
                    detail="No automatic apply handler is registered for this proposal type.",
                )
            )
            continue

        route_name = normalize_route_name(entry.route_name)
        before_weight = float(updated_weights.get(route_name, 1.0))
        after_weight = round(float(entry.suggested_weight or 1.0), 6)
        rollback_weights[route_name] = before_weight
        if abs(before_weight - after_weight) <= 1e-9:
            noop_count += 1
            entries.append(
                ProposalApplicationEntry(
                    proposal_id=entry.proposal_id,
                    proposal_type=entry.proposal_type,
                    route_name=route_name,
                    task_family=entry.task_family,
                    status="noop",
                    detail="Suggested quality weight already matches the current persisted value.",
                    before_weight=before_weight,
                    after_weight=after_weight,
                )
            )
            continue

        updated_weights[route_name] = after_weight
        applied_count += 1
        entries.append(
            ProposalApplicationEntry(
                proposal_id=entry.proposal_id,
                proposal_type=entry.proposal_type,
                route_name=route_name,
                task_family=entry.task_family,
                status="applied",
                detail="Persisted the approved route quality weight.",
                before_weight=before_weight,
                after_weight=after_weight,
            )
        )

    persisted_weights = {
        route_name: weight
        for route_name, weight in updated_weights.items()
        if abs(weight - 1.0) > 1e-9
    }
    persisted_profiles = {
        route_name: profile
        for route_name, profile in updated_profiles.items()
        if profile.get("task_family_scores") or profile.get("unsupported_task_types")
    }
    RouteRepo()._apply_metadata_change(
        base_dir=proposal.base_dir,
        route_weights=persisted_weights,
        route_capability_profiles=persisted_profiles,
        proposal_id=proposal_id,
    )

    applied_at = utc_now()
    application_record = OptimizationProposalApplicationRecord(
        application_id=f"application-{_timestamp_token(applied_at)}",
        applied_at=applied_at,
        source_review_path=str(review_path),
        applied_count=applied_count,
        noop_count=noop_count,
        skipped_count=skipped_count,
        route_weights_path=str(route_weights_path(proposal.base_dir)),
        route_capabilities_path=str(route_capabilities_path(proposal.base_dir)),
        rollback_weights=rollback_weights,
        rollback_capability_profiles=rollback_capability_profiles,
        entries=entries,
    )
    application_path = optimization_proposal_application_path(proposal.base_dir, application_record.application_id)
    try:
        _write_json(application_path, application_record.to_dict())
    except OSError as exc:
        logger.warning(
            "review record artifact write failed; SQLite truth already committed",
            extra={
                "application_id": application_record.application_id,
                "path": str(application_path),
                "error": repr(exc),
            },
        )
    return ApplyResult(
        proposal_id=proposal_id,
        target=ProposalTarget.ROUTE_METADATA,
        success=True,
        detail=f"route_review_applied review_id={review_record.review_id}",
        applied_writes=("route_weights", "route_capability_profiles", "optimization_proposal_application"),
        payload=(application_record, application_path),
    )


def _apply_policy(proposal: object, _operator_token: OperatorToken, *, proposal_id: str) -> ApplyResult:
    if isinstance(proposal, _MpsPolicyProposal):
        applied_write, policy_path = PolicyRepo()._apply_policy_change(
            base_dir=proposal.base_dir,
            mps_kind=proposal.kind,
            mps_value=proposal.value,
            proposal_id=proposal_id,
        )
        return ApplyResult(
            proposal_id=proposal_id,
            target=ProposalTarget.POLICY,
            success=True,
            detail=f"mps_policy_applied kind={proposal.kind} path={policy_path}",
            applied_writes=(applied_write,),
            payload=policy_path,
        )

    if not isinstance(proposal, _PolicyProposal):
        raise TypeError("policy proposal payload is invalid.")

    applied_write, policy_path = PolicyRepo()._apply_policy_change(
        base_dir=proposal.base_dir,
        audit_trigger_policy=proposal.audit_trigger_policy,
        proposal_id=proposal_id,
    )
    return ApplyResult(
        proposal_id=proposal_id,
        target=ProposalTarget.POLICY,
        success=True,
        detail=f"policy_applied path={policy_path}",
        applied_writes=(applied_write,),
        payload=policy_path,
    )


def _emit_event(_operator_token: OperatorToken, _target: ProposalTarget, _result: ApplyResult) -> None:
    """Reserved for durable governance audit events once the event repository exists."""
