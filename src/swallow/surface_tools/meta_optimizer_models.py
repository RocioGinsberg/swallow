from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass, field

from swallow.orchestration.models import OptimizationProposal

META_OPTIMIZER_EXECUTOR_NAME = "meta-optimizer"
META_OPTIMIZER_AGENT_NAME = META_OPTIMIZER_EXECUTOR_NAME
META_OPTIMIZER_SNAPSHOT_KIND = "meta_optimizer_snapshot_v0"
PROPOSAL_BUNDLE_KIND = "meta_optimizer_proposal_bundle_v1"
PROPOSAL_REVIEW_KIND = "meta_optimizer_proposal_review_v1"
PROPOSAL_APPLICATION_KIND = "meta_optimizer_proposal_application_v1"
VALID_PROPOSAL_REVIEW_DECISIONS = {"approved", "rejected", "deferred"}

@dataclass(slots=True)
class RouteTelemetryStats:
    route_name: str
    success_count: int = 0
    failure_count: int = 0
    debate_retry_count: int = 0
    fallback_trigger_count: int = 0
    degraded_count: int = 0
    total_latency_ms: int = 0
    total_cost: float = 0.0
    event_count: int = 0
    task_families: set[str] = field(default_factory=set)
    cost_samples: list[float] = field(default_factory=list)

    def success_rate(self) -> float:
        return self.success_count / self.event_count if self.event_count else 0.0

    def failure_rate(self) -> float:
        return self.failure_count / self.event_count if self.event_count else 0.0

    def fallback_rate(self) -> float:
        return self.fallback_trigger_count / self.event_count if self.event_count else 0.0

    def cost_event_count(self) -> int:
        return self.event_count + self.debate_retry_count

    def average_latency_ms(self) -> int:
        return int(round(self.total_latency_ms / self.cost_event_count())) if self.cost_event_count() else 0

    def average_cost(self) -> float:
        return round(self.total_cost / self.cost_event_count(), 6) if self.cost_event_count() else 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "route_name": self.route_name,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "debate_retry_count": self.debate_retry_count,
            "fallback_trigger_count": self.fallback_trigger_count,
            "degraded_count": self.degraded_count,
            "total_latency_ms": self.total_latency_ms,
            "total_cost": self.total_cost,
            "event_count": self.event_count,
            "task_families": sorted(self.task_families),
        }


@dataclass(slots=True)
class FailureFingerprint:
    failure_kind: str
    error_code: str
    count: int = 0
    routes: set[str] = field(default_factory=set)

    def to_dict(self) -> dict[str, object]:
        return {
            "failure_kind": self.failure_kind,
            "error_code": self.error_code,
            "count": self.count,
            "routes": sorted(self.routes),
        }


@dataclass(slots=True)
class TaskFamilyTelemetryStats:
    task_family: str
    executor_event_count: int = 0
    debate_retry_count: int = 0
    total_cost: float = 0.0
    cost_samples: list[float] = field(default_factory=list)

    def total_attempt_count(self) -> int:
        return self.executor_event_count + self.debate_retry_count

    def debate_retry_rate(self) -> float:
        return self.debate_retry_count / self.total_attempt_count() if self.total_attempt_count() else 0.0

    def average_cost(self) -> float:
        return round(self.total_cost / self.total_attempt_count(), 6) if self.total_attempt_count() else 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "task_family": self.task_family,
            "executor_event_count": self.executor_event_count,
            "debate_retry_count": self.debate_retry_count,
            "total_cost": self.total_cost,
        }


@dataclass(slots=True)
class RouteTaskFamilyTelemetryStats:
    route_name: str
    task_family: str
    success_count: int = 0
    failure_count: int = 0
    degraded_count: int = 0
    event_count: int = 0

    def success_rate(self) -> float:
        return self.success_count / self.event_count if self.event_count else 0.0

    def degraded_rate(self) -> float:
        return self.degraded_count / self.event_count if self.event_count else 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "route_name": self.route_name,
            "task_family": self.task_family,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "degraded_count": self.degraded_count,
            "event_count": self.event_count,
        }


@dataclass(slots=True)
class MetaOptimizerSnapshot:
    generated_at: str
    task_limit: int
    scanned_task_ids: list[str]
    scanned_event_count: int
    route_stats: list[RouteTelemetryStats]
    failure_fingerprints: list[FailureFingerprint]
    degraded_event_count: int
    task_family_stats: list[TaskFamilyTelemetryStats]
    route_task_family_stats: list[RouteTaskFamilyTelemetryStats]
    proposals: list[OptimizationProposal]

    def to_dict(self) -> dict[str, object]:
        return {
            "generated_at": self.generated_at,
            "task_limit": self.task_limit,
            "scanned_task_ids": list(self.scanned_task_ids),
            "scanned_event_count": self.scanned_event_count,
            "route_stats": [item.to_dict() for item in self.route_stats],
            "failure_fingerprints": [item.to_dict() for item in self.failure_fingerprints],
            "degraded_event_count": self.degraded_event_count,
            "task_family_stats": [item.to_dict() for item in self.task_family_stats],
            "route_task_family_stats": [item.to_dict() for item in self.route_task_family_stats],
            "proposals": [proposal.to_dict() for proposal in self.proposals],
        }


@dataclass(slots=True)
class OptimizationProposalBundle:
    bundle_id: str
    generated_at: str
    task_limit: int
    scanned_task_ids: list[str]
    scanned_event_count: int
    report_artifact: str
    proposals: list[OptimizationProposal]
    kind: str = PROPOSAL_BUNDLE_KIND

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "bundle_id": self.bundle_id,
            "generated_at": self.generated_at,
            "task_limit": self.task_limit,
            "scanned_task_ids": list(self.scanned_task_ids),
            "scanned_event_count": self.scanned_event_count,
            "report_artifact": self.report_artifact,
            "proposals": [proposal.to_dict() for proposal in self.proposals],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "OptimizationProposalBundle":
        raw_proposals = data.get("proposals", [])
        proposals = [
            OptimizationProposal.from_dict(item)
            for item in raw_proposals
            if isinstance(item, dict)
        ]
        return cls(
            kind=str(data.get("kind", PROPOSAL_BUNDLE_KIND)).strip() or PROPOSAL_BUNDLE_KIND,
            bundle_id=str(data.get("bundle_id", "")).strip(),
            generated_at=str(data.get("generated_at", "")).strip(),
            task_limit=_coerce_nonnegative_int(data.get("task_limit", 0)),
            scanned_task_ids=[
                str(item).strip()
                for item in data.get("scanned_task_ids", [])
                if str(item).strip()
            ]
            if isinstance(data.get("scanned_task_ids", []), list)
            else [],
            scanned_event_count=_coerce_nonnegative_int(data.get("scanned_event_count", 0)),
            report_artifact=str(data.get("report_artifact", "")).strip(),
            proposals=_ensure_proposal_metadata(proposals),
        )


@dataclass(slots=True)
class ProposalReviewEntry:
    proposal_id: str
    proposal_type: str
    route_name: str | None
    task_family: str | None
    decision: str
    description: str
    suggested_action: str
    note: str = ""
    severity: str = ""
    priority: str = ""
    rationale: str = ""
    suggested_weight: float | None = None
    suggested_task_family_score: float | None = None
    mark_task_family_unsupported: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ProposalReviewEntry":
        raw_weight = data.get("suggested_weight")
        suggested_weight: float | None
        if raw_weight in {"", None}:
            suggested_weight = None
        else:
            try:
                suggested_weight = float(raw_weight)
            except (TypeError, ValueError):
                suggested_weight = None
        raw_task_family_score = data.get("suggested_task_family_score")
        suggested_task_family_score: float | None
        if raw_task_family_score in {"", None}:
            suggested_task_family_score = None
        else:
            try:
                suggested_task_family_score = max(float(raw_task_family_score), 0.0)
            except (TypeError, ValueError):
                suggested_task_family_score = None
        route_name = data.get("route_name")
        normalized_route_name = None if route_name in {"", None} else str(route_name)
        task_family = data.get("task_family")
        normalized_task_family = None if task_family in {"", None} else str(task_family).strip().lower()
        mark_task_family_unsupported = data.get("mark_task_family_unsupported", False)
        if not isinstance(mark_task_family_unsupported, bool):
            mark_task_family_unsupported = str(mark_task_family_unsupported).strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
        return cls(
            proposal_id=str(data.get("proposal_id", "")).strip(),
            proposal_type=str(data.get("proposal_type", "")).strip(),
            route_name=normalized_route_name,
            task_family=normalized_task_family,
            decision=str(data.get("decision", "deferred")).strip() or "deferred",
            description=str(data.get("description", "")).strip(),
            suggested_action=str(data.get("suggested_action", "")).strip(),
            note=str(data.get("note", "")).strip(),
            severity=str(data.get("severity", "")).strip(),
            priority=str(data.get("priority", "")).strip(),
            rationale=str(data.get("rationale", "")).strip(),
            suggested_weight=suggested_weight,
            suggested_task_family_score=suggested_task_family_score,
            mark_task_family_unsupported=mark_task_family_unsupported,
        )


@dataclass(slots=True)
class OptimizationProposalReviewRecord:
    review_id: str
    reviewed_at: str
    decision: str
    source_bundle_path: str
    source_bundle_id: str
    reviewer: str
    note: str
    entries: list[ProposalReviewEntry]
    kind: str = PROPOSAL_REVIEW_KIND

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "review_id": self.review_id,
            "reviewed_at": self.reviewed_at,
            "decision": self.decision,
            "source_bundle_path": self.source_bundle_path,
            "source_bundle_id": self.source_bundle_id,
            "reviewer": self.reviewer,
            "note": self.note,
            "entries": [entry.to_dict() for entry in self.entries],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "OptimizationProposalReviewRecord":
        raw_entries = data.get("entries", [])
        entries = [
            ProposalReviewEntry.from_dict(item)
            for item in raw_entries
            if isinstance(item, dict)
        ]
        return cls(
            kind=str(data.get("kind", PROPOSAL_REVIEW_KIND)).strip() or PROPOSAL_REVIEW_KIND,
            review_id=str(data.get("review_id", "")).strip(),
            reviewed_at=str(data.get("reviewed_at", "")).strip(),
            decision=str(data.get("decision", "deferred")).strip() or "deferred",
            source_bundle_path=str(data.get("source_bundle_path", "")).strip(),
            source_bundle_id=str(data.get("source_bundle_id", "")).strip(),
            reviewer=str(data.get("reviewer", "")).strip() or "swl_cli",
            note=str(data.get("note", "")).strip(),
            entries=entries,
        )


@dataclass(slots=True)
class ProposalApplicationEntry:
    proposal_id: str
    proposal_type: str
    route_name: str | None
    task_family: str | None
    status: str
    detail: str
    before_weight: float | None = None
    after_weight: float | None = None
    before_task_family_score: float | None = None
    after_task_family_score: float | None = None
    before_task_family_unsupported: bool | None = None
    after_task_family_unsupported: bool | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class OptimizationProposalApplicationRecord:
    application_id: str
    applied_at: str
    source_review_path: str
    applied_count: int
    noop_count: int
    skipped_count: int
    route_weights_path: str
    route_capabilities_path: str
    rollback_weights: dict[str, float]
    rollback_capability_profiles: dict[str, dict[str, object]]
    entries: list[ProposalApplicationEntry]
    kind: str = PROPOSAL_APPLICATION_KIND

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "application_id": self.application_id,
            "applied_at": self.applied_at,
            "source_review_path": self.source_review_path,
            "applied_count": self.applied_count,
            "noop_count": self.noop_count,
            "skipped_count": self.skipped_count,
            "route_weights_path": self.route_weights_path,
            "route_capabilities_path": self.route_capabilities_path,
            "rollback_weights": dict(sorted(self.rollback_weights.items())),
            "rollback_capability_profiles": {
                route_name: profile
                for route_name, profile in sorted(self.rollback_capability_profiles.items())
            },
            "entries": [entry.to_dict() for entry in self.entries],
        }


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return normalized or "unknown"


def _timestamp_token(value: str) -> str:
    return f"{_slugify(value.replace(':', '-'))}-{time.time_ns():x}"




def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return normalized or "unknown"


def _timestamp_token(value: str) -> str:
    return f"{_slugify(value.replace(':', '-'))}-{time.time_ns():x}"




def _ensure_proposal_metadata(proposals: list[OptimizationProposal]) -> list[OptimizationProposal]:
    for index, proposal in enumerate(proposals, start=1):
        route_part = _slugify(proposal.route_name or "global")
        if not proposal.proposal_id:
            proposal.proposal_id = f"proposal-{index:03d}-{_slugify(proposal.proposal_type)}-{route_part}"
        if not proposal.priority:
            proposal.priority = proposal.severity or "info"
        if not proposal.rationale:
            proposal.rationale = proposal.description
    return proposals

def _coerce_nonnegative_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return max(value, 0)
    if isinstance(value, float):
        return max(int(value), 0)
    if isinstance(value, str):
        try:
            return max(int(value.strip()), 0)
        except ValueError:
            return 0
    return 0


def _coerce_nonnegative_float(value: object) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, int | float):
        return max(float(value), 0.0)
    if isinstance(value, str):
        try:
            return max(float(value.strip()), 0.0)
        except ValueError:
            return 0.0
    return 0.0
