from __future__ import annotations

import json
import asyncio
from dataclasses import asdict, dataclass, field
from pathlib import Path
import re
from statistics import median_low
import time

from swallow.orchestration.models import (
    EVENT_EXECUTOR_COMPLETED,
    EVENT_EXECUTOR_FAILED,
    EVENT_TASK_EXECUTION_FALLBACK,
    ExecutorResult,
    META_OPTIMIZER_MEMORY_AUTHORITY,
    META_OPTIMIZER_SYSTEM_ROLE,
    OptimizationProposal,
    TaskCard,
    TaskState,
    utc_now,
)
from swallow.truth_governance.governance import OperatorToken, ProposalTarget, apply_proposal, register_route_metadata_proposal
from swallow.surface_tools.paths import (
    latest_optimization_proposal_bundle_path,
    optimization_proposal_bundle_path,
    optimization_proposal_review_path,
    optimization_proposals_path,
)
from swallow.provider_router.router import (
    load_route_capability_profiles,
    route_by_name,
)
from swallow.truth_governance.store import iter_recent_task_events


ROUTE_WEIGHT_PROPOSAL_PATTERN = re.compile(
    r"Route weight suggestion for `(?P<route_name>[^`]+)`: set quality weight to (?P<suggested_weight>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
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


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


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


def _normalize_task_family_name(value: object) -> str:
    return str(value or "").strip().lower()


def _suggest_task_family_score(stats: RouteTaskFamilyTelemetryStats) -> float:
    suggested = stats.success_rate() - (stats.degraded_rate() * 0.25)
    return round(min(max(suggested, 0.0), 1.0), 2)


def build_meta_optimizer_snapshot(base_dir: Path, last_n: int = 100) -> MetaOptimizerSnapshot:
    if last_n <= 0:
        raise ValueError("--last-n must be greater than 0")

    route_stats_by_name: dict[str, RouteTelemetryStats] = {}
    failure_fingerprints_by_key: dict[tuple[str, str], FailureFingerprint] = {}
    task_family_stats_by_name: dict[str, TaskFamilyTelemetryStats] = {}
    route_task_family_stats_by_key: dict[tuple[str, str], RouteTaskFamilyTelemetryStats] = {}
    scanned_task_ids: list[str] = []
    scanned_event_count = 0

    recent_task_events = iter_recent_task_events(base_dir, last_n)
    # Trend heuristics need oldest->newest ordering across the selected recent tasks.
    for task_id, events in reversed(recent_task_events):
        scanned_task_ids.append(task_id)
        scanned_event_count += len(events)

        for event in events:
            event_type = str(event.get("event_type", "")).strip()
            payload = event.get("payload", {})
            if not isinstance(payload, dict):
                payload = {}

            if event_type in {EVENT_EXECUTOR_COMPLETED, EVENT_EXECUTOR_FAILED}:
                route_name = str(payload.get("physical_route") or payload.get("route_name") or "unknown").strip()
                route_name = route_name or "unknown"
                route_stats = route_stats_by_name.setdefault(route_name, RouteTelemetryStats(route_name=route_name))
                task_family = _normalize_task_family_name(payload.get("task_family", ""))
                token_cost = _coerce_nonnegative_float(payload.get("token_cost", 0.0))
                family_stats = None
                route_task_family_stats = None
                if task_family:
                    family_stats = task_family_stats_by_name.setdefault(
                        task_family,
                        TaskFamilyTelemetryStats(task_family=task_family),
                    )
                    route_task_family_stats = route_task_family_stats_by_key.setdefault(
                        (route_name, task_family),
                        RouteTaskFamilyTelemetryStats(route_name=route_name, task_family=task_family),
                    )
                    family_stats.total_cost += token_cost
                    family_stats.cost_samples.append(token_cost)
                route_stats.total_latency_ms += _coerce_nonnegative_int(payload.get("latency_ms", 0))
                route_stats.total_cost += token_cost
                route_stats.cost_samples.append(token_cost)
                if task_family:
                    route_stats.task_families.add(task_family)
                if str(payload.get("review_feedback", "")).strip():
                    route_stats.debate_retry_count += 1
                    if family_stats is not None:
                        family_stats.debate_retry_count += 1
                    continue
                route_stats.event_count += 1
                if family_stats is not None:
                    family_stats.executor_event_count += 1
                if route_task_family_stats is not None:
                    route_task_family_stats.event_count += 1
                if bool(payload.get("degraded", False)):
                    route_stats.degraded_count += 1
                    if route_task_family_stats is not None:
                        route_task_family_stats.degraded_count += 1
                if event_type == EVENT_EXECUTOR_COMPLETED:
                    route_stats.success_count += 1
                    if route_task_family_stats is not None:
                        route_task_family_stats.success_count += 1
                else:
                    route_stats.failure_count += 1
                    if route_task_family_stats is not None:
                        route_task_family_stats.failure_count += 1
                    failure_kind = str(payload.get("failure_kind", "")).strip() or "unknown"
                    error_code = str(payload.get("error_code", "")).strip() or failure_kind
                    fingerprint = failure_fingerprints_by_key.setdefault(
                        (failure_kind, error_code),
                        FailureFingerprint(failure_kind=failure_kind, error_code=error_code),
                    )
                    fingerprint.count += 1
                    fingerprint.routes.add(route_name)
                continue

            if event_type == EVENT_TASK_EXECUTION_FALLBACK:
                previous_route_name = str(payload.get("previous_route_name", "")).strip()
                if not previous_route_name:
                    continue
                route_stats = route_stats_by_name.setdefault(
                    previous_route_name,
                    RouteTelemetryStats(route_name=previous_route_name),
                )
                route_stats.fallback_trigger_count += 1
                token_cost = _coerce_nonnegative_float(payload.get("token_cost", 0.0))
                route_stats.total_cost += token_cost
                route_stats.cost_samples.append(token_cost)

    route_stats = sorted(
        route_stats_by_name.values(),
        key=lambda item: (
            item.failure_rate(),
            item.fallback_rate(),
            item.degraded_count,
            item.route_name,
        ),
        reverse=True,
    )
    failure_fingerprints = sorted(
        failure_fingerprints_by_key.values(),
        key=lambda item: (item.count, item.failure_kind, item.error_code),
        reverse=True,
    )
    degraded_event_count = sum(item.degraded_count for item in route_stats)
    task_family_stats = sorted(task_family_stats_by_name.values(), key=lambda item: item.task_family)
    route_task_family_stats = sorted(
        route_task_family_stats_by_key.values(),
        key=lambda item: (item.route_name, item.task_family),
    )

    return MetaOptimizerSnapshot(
        generated_at=utc_now(),
        task_limit=last_n,
        scanned_task_ids=scanned_task_ids,
        scanned_event_count=scanned_event_count,
        route_stats=route_stats,
        failure_fingerprints=failure_fingerprints,
        degraded_event_count=degraded_event_count,
        task_family_stats=task_family_stats,
        route_task_family_stats=route_task_family_stats,
        proposals=build_optimization_proposals(
            base_dir,
            route_stats,
            failure_fingerprints,
            task_family_stats,
            route_task_family_stats,
        ),
    )


def build_optimization_proposals(
    base_dir: Path,
    route_stats: list[RouteTelemetryStats],
    failure_fingerprints: list[FailureFingerprint],
    task_family_stats: list[TaskFamilyTelemetryStats],
    route_task_family_stats: list[RouteTaskFamilyTelemetryStats],
) -> list[OptimizationProposal]:
    proposals: list[OptimizationProposal] = []
    for stats in route_stats:
        if stats.failure_rate() >= 0.25:
            description = (
                f"Review route `{stats.route_name}`: failure rate is {stats.failure_rate():.0%} "
                f"over {stats.event_count} executor events."
            )
            proposals.append(
                OptimizationProposal(
                    proposal_type="route",
                    severity="critical" if stats.failure_rate() >= 0.5 else "warn",
                    route_name=stats.route_name,
                    description=description,
                    suggested_action="Inspect recent executor failures and fallback coverage for this route.",
                )
            )
            suggested_weight = round(max(0.1, 1.0 - stats.failure_rate()), 2)
            proposals.append(
                OptimizationProposal(
                    proposal_type="route_weight",
                    severity="critical" if stats.failure_rate() >= 0.5 else "warn",
                    route_name=stats.route_name,
                    description=(
                        f"Route weight suggestion for `{stats.route_name}`: set quality weight to "
                        f"{suggested_weight:.2f} based on failure rate {stats.failure_rate():.0%}."
                    ),
                    suggested_action="Apply the lower quality weight if the route should be demoted without disabling it.",
                    suggested_weight=suggested_weight,
                )
            )
        if stats.fallback_rate() >= 0.15:
            description = (
                f"Review route `{stats.route_name}`: fallback rate is {stats.fallback_rate():.0%}, "
                "suggesting primary execution instability."
            )
            proposals.append(
                OptimizationProposal(
                    proposal_type="route",
                    severity="warn",
                    route_name=stats.route_name,
                    description=description,
                    suggested_action="Check whether the primary route should be stabilized before remaining first choice.",
                )
            )
        degraded_ratio = stats.degraded_count / stats.event_count if stats.event_count else 0.0
        if degraded_ratio >= 0.2:
            description = (
                f"Track degradation on `{stats.route_name}`: {stats.degraded_count}/{stats.event_count} "
                "executor events were degraded."
            )
            proposals.append(
                OptimizationProposal(
                    proposal_type="route",
                    severity="warn",
                    route_name=stats.route_name,
                    description=description,
                    suggested_action="Review degraded executions and confirm whether this route should stay operator-visible.",
                )
            )
        if stats.average_cost() >= 0.25:
            description = (
                f"Review route `{stats.route_name}`: average estimated cost is "
                f"${stats.average_cost():.2f}/task across {stats.event_count} executor events."
            )
            proposals.append(
                OptimizationProposal(
                    proposal_type="route",
                    severity="warn",
                    route_name=stats.route_name,
                    description=description,
                    suggested_action="Compare route cost against lower-cost alternatives for the same task family.",
                )
            )

    for fingerprint in failure_fingerprints:
        if fingerprint.count >= 2:
            description = (
                "Investigate repeated failure fingerprint "
                f"`{fingerprint.failure_kind}/{fingerprint.error_code}` across routes: "
                f"{', '.join(sorted(fingerprint.routes))}."
            )
            proposals.append(
                OptimizationProposal(
                    proposal_type="route",
                    severity="critical" if fingerprint.count >= 3 else "warn",
                    route_name=None,
                    description=description,
                    suggested_action="Inspect shared failure modes before changing route defaults.",
                )
            )

    routes_by_task_family: dict[str, list[RouteTelemetryStats]] = {}
    for stats in route_stats:
        for task_family in stats.task_families:
            routes_by_task_family.setdefault(task_family, []).append(stats)

    for task_family, family_routes in sorted(routes_by_task_family.items()):
        if len(family_routes) < 2:
            continue
        ranked_routes = sorted(family_routes, key=lambda item: (item.average_cost(), item.route_name))
        cheapest = ranked_routes[0]
        most_expensive = ranked_routes[-1]
        if most_expensive.average_cost() >= 0.10 and most_expensive.average_cost() >= cheapest.average_cost() * 2:
            description = (
                f"Compare cost for task_family `{task_family}`: route `{most_expensive.route_name}` "
                f"averages ${most_expensive.average_cost():.2f}/task versus "
                f"`{cheapest.route_name}` at ${cheapest.average_cost():.2f}/task."
            )
            proposals.append(
                OptimizationProposal(
                    proposal_type="route",
                    severity="info",
                    route_name=most_expensive.route_name,
                    description=description,
                    suggested_action="Review whether the more expensive route needs to remain preferred for this task family.",
                )
            )

    for stats in route_stats:
        if len(stats.cost_samples) < 4:
            continue
        midpoint = len(stats.cost_samples) // 2
        historical_average = sum(stats.cost_samples[:midpoint]) / max(midpoint, 1)
        recent_average = sum(stats.cost_samples[midpoint:]) / max(len(stats.cost_samples) - midpoint, 1)
        if recent_average >= 0.10 and recent_average >= historical_average * 1.5:
            description = (
                f"Watch cost trend on `{stats.route_name}`: recent estimated cost rose from "
                f"${historical_average:.2f} to ${recent_average:.2f} per executor event."
            )
            proposals.append(
                OptimizationProposal(
                    proposal_type="route",
                    severity="warn",
                    route_name=stats.route_name,
                    description=description,
                    suggested_action="Validate whether prompt or provider changes caused the recent cost increase.",
                )
            )

    for family_stats in task_family_stats:
        if family_stats.total_attempt_count() < 3:
            continue
        if family_stats.debate_retry_rate() >= 0.3:
            description = (
                f"Review workflow for task_family `{family_stats.task_family}`: debate retry rate is "
                f"{family_stats.debate_retry_rate():.0%} over {family_stats.total_attempt_count()} attempts."
            )
            proposals.append(
                OptimizationProposal(
                    proposal_type="workflow",
                    severity="warn",
                    route_name=None,
                    description=description,
                    suggested_action="Inspect review gate criteria or task-card planning for this task family.",
                )
            )

    family_average_costs = [stats.average_cost() for stats in task_family_stats if stats.total_attempt_count() > 0]
    median_cost = float(median_low(family_average_costs)) if family_average_costs else 0.0
    if median_cost > 0:
        for family_stats in task_family_stats:
            average_cost = family_stats.average_cost()
            if average_cost >= 0.10 and average_cost >= median_cost * 2:
                description = (
                    f"Review workflow cost for task_family `{family_stats.task_family}`: average estimated cost is "
                    f"${average_cost:.2f}/attempt versus median ${median_cost:.2f}."
                )
                proposals.append(
                    OptimizationProposal(
                        proposal_type="workflow",
                        severity="warn",
                        route_name=None,
                        description=description,
                        suggested_action="Inspect whether this task family is over-reviewing or using oversized routes.",
                    )
                )

    proposals.extend(_build_route_capability_proposals(base_dir, route_task_family_stats))
    if not proposals and route_stats:
        proposals.append(
            OptimizationProposal(
                proposal_type="workflow",
                severity="info",
                route_name=None,
                description=(
                    "No immediate route, fallback, degradation, or cost anomalies crossed the current heuristic thresholds."
                ),
                suggested_action="Keep collecting telemetry until a stronger signal appears.",
            )
        )
    return _ensure_proposal_metadata(proposals)


def _build_route_capability_proposals(
    base_dir: Path,
    route_task_family_stats: list[RouteTaskFamilyTelemetryStats],
) -> list[OptimizationProposal]:
    current_profiles = load_route_capability_profiles(base_dir)
    proposals: list[OptimizationProposal] = []
    for stats in route_task_family_stats:
        if stats.event_count < 2:
            continue
        if route_by_name(stats.route_name) is None:
            continue

        current_profile = current_profiles.get(stats.route_name, {})
        current_scores = current_profile.get("task_family_scores", {})
        current_score = None
        if isinstance(current_scores, dict):
            raw_score = current_scores.get(stats.task_family)
            if isinstance(raw_score, int | float):
                current_score = round(max(float(raw_score), 0.0), 2)
        unsupported_task_types = current_profile.get("unsupported_task_types", [])
        unsupported = False
        if isinstance(unsupported_task_types, list):
            unsupported = stats.task_family in {
                _normalize_task_family_name(item)
                for item in unsupported_task_types
            }

        if stats.success_count == 0 and stats.failure_count >= 2:
            if unsupported:
                continue
            proposals.append(
                OptimizationProposal(
                    proposal_type="route_capability",
                    severity="warn",
                    route_name=stats.route_name,
                    task_family=stats.task_family,
                    description=(
                        f"Capability boundary suggestion for `{stats.route_name}` on task_family "
                        f"`{stats.task_family}`: mark unsupported after {stats.failure_count} failures "
                        f"and 0 successful executor events."
                    ),
                    suggested_action=(
                        "Mark this task family unsupported so the strategy router can reject the route earlier."
                    ),
                    mark_task_family_unsupported=True,
                )
            )
            continue

        if stats.success_count <= 0:
            continue

        suggested_score = _suggest_task_family_score(stats)
        if (
            current_score is None
            and not unsupported
            and suggested_score >= 0.99
            and stats.failure_count == 0
            and stats.degraded_count == 0
        ):
            continue
        if not unsupported and current_score is not None and abs(current_score - suggested_score) < 0.15:
            continue
        proposals.append(
            OptimizationProposal(
                proposal_type="route_capability",
                severity="info" if suggested_score >= 0.75 else "warn",
                route_name=stats.route_name,
                task_family=stats.task_family,
                description=(
                    f"Capability score suggestion for `{stats.route_name}` on task_family "
                    f"`{stats.task_family}`: set score to {suggested_score:.2f} "
                    f"(success_rate={stats.success_rate():.0%}, degraded_rate={stats.degraded_rate():.0%}, "
                    f"events={stats.event_count})."
                ),
                suggested_action=(
                    "Persist the suggested capability score so task-family-aware routing can rank this route accurately."
                ),
                suggested_task_family_score=suggested_score,
            )
        )
    return proposals


def extract_route_weight_proposals_from_report(report_text: str) -> list[OptimizationProposal]:
    proposals: list[OptimizationProposal] = []
    for match in ROUTE_WEIGHT_PROPOSAL_PATTERN.finditer(report_text or ""):
        route_name = match.group("route_name").strip()
        suggested_weight = round(float(match.group("suggested_weight")), 2)
        proposals.append(
            OptimizationProposal(
                proposal_type="route_weight",
                severity="warn",
                route_name=route_name,
                description=match.group(0),
                suggested_action="Apply the suggested quality weight from the report.",
                suggested_weight=suggested_weight,
            )
        )
    return _ensure_proposal_metadata(proposals)


def build_meta_optimizer_report(snapshot: MetaOptimizerSnapshot) -> str:
    lines = [
        "# Meta-Optimizer Proposals",
        "",
        f"- generated_at: {snapshot.generated_at}",
        f"- scanned_task_count: {len(snapshot.scanned_task_ids)}",
        f"- scanned_event_count: {snapshot.scanned_event_count}",
        f"- task_limit: {snapshot.task_limit}",
    ]

    if not snapshot.scanned_task_ids or not snapshot.route_stats:
        lines.extend(
            [
                "",
                "## Status",
                "- no data",
            ]
        )
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            "",
            "## Route Health",
        ]
    )
    for stats in snapshot.route_stats:
        lines.append(
            f"- {stats.route_name}: success_rate={stats.success_rate():.0%} "
            f"failure_rate={stats.failure_rate():.0%} "
            f"fallback_rate={stats.fallback_rate():.0%} "
            f"debate_retry={stats.debate_retry_count} "
            f"avg_latency_ms={stats.average_latency_ms()} "
            f"avg_cost=${stats.average_cost():.6f} "
            f"degraded={stats.degraded_count}/{stats.event_count}"
        )

    lines.extend(
        [
            "",
            "## Failure Fingerprints",
        ]
    )
    if snapshot.failure_fingerprints:
        for fingerprint in snapshot.failure_fingerprints:
            lines.append(
                f"- failure_kind={fingerprint.failure_kind} "
                f"error_code={fingerprint.error_code} "
                f"count={fingerprint.count} "
                f"routes={', '.join(sorted(fingerprint.routes))}"
            )
    else:
        lines.append("- no failure fingerprints detected.")

    total_executor_events = sum(stats.event_count for stats in snapshot.route_stats)
    degraded_routes = [stats for stats in snapshot.route_stats if stats.degraded_count > 0]
    lines.extend(
        [
            "",
            "## Degradation Trends",
            f"- degraded_executor_events: {snapshot.degraded_event_count}/{total_executor_events}",
        ]
    )
    if degraded_routes:
        for stats in degraded_routes:
            lines.append(
                f"- {stats.route_name}: degraded_events={stats.degraded_count}/{stats.event_count}"
            )
    else:
        lines.append("- degraded_routes: none")

    lines.extend(
        [
            "",
            "## Cost Summary",
        ]
    )
    for stats in snapshot.route_stats:
        lines.append(
            f"- {stats.route_name}: total_cost=${stats.total_cost:.6f} "
            f"avg_cost=${stats.average_cost():.6f} "
            f"task_families={', '.join(sorted(stats.task_families)) or 'unknown'}"
        )

    lines.extend(
        [
            "",
            "## Route Task Family Signals",
        ]
    )
    if snapshot.route_task_family_stats:
        for stats in snapshot.route_task_family_stats:
            lines.append(
                f"- {stats.route_name}/{stats.task_family}: success_rate={stats.success_rate():.0%} "
                f"degraded_rate={stats.degraded_rate():.0%} "
                f"events={stats.event_count}"
            )
    else:
        lines.append("- no route task family signals detected.")

    lines.extend(
        [
            "",
            "## Proposals",
        ]
    )
    for proposal in snapshot.proposals:
        proposal_label = proposal.proposal_id or proposal.proposal_type
        lines.append(f"- [{proposal_label}] {proposal.description}")
    if not snapshot.proposals:
        lines.append("- No immediate optimization proposals were generated.")

    return "\n".join(lines) + "\n"


def save_optimization_proposal_bundle(
    base_dir: Path,
    snapshot: MetaOptimizerSnapshot,
    report_artifact: Path,
) -> tuple[OptimizationProposalBundle, Path]:
    bundle = OptimizationProposalBundle(
        bundle_id=f"bundle-{_timestamp_token(snapshot.generated_at)}",
        generated_at=snapshot.generated_at,
        task_limit=snapshot.task_limit,
        scanned_task_ids=list(snapshot.scanned_task_ids),
        scanned_event_count=snapshot.scanned_event_count,
        report_artifact=str(report_artifact),
        proposals=_ensure_proposal_metadata(list(snapshot.proposals)),
    )
    bundle_path = optimization_proposal_bundle_path(base_dir, bundle.bundle_id)
    payload = bundle.to_dict()
    _write_json(bundle_path, payload)
    _write_json(latest_optimization_proposal_bundle_path(base_dir), payload)
    return bundle, bundle_path


def load_optimization_proposal_bundle(bundle_path: Path) -> OptimizationProposalBundle:
    if not bundle_path.exists():
        raise FileNotFoundError(f"Proposal bundle not found: {bundle_path}")
    return OptimizationProposalBundle.from_dict(_load_json(bundle_path))


def review_optimization_proposals(
    base_dir: Path,
    bundle_path: Path,
    decision: str,
    proposal_ids: list[str] | None = None,
    note: str = "",
    reviewer: str = "swl_cli",
) -> tuple[OptimizationProposalReviewRecord, Path]:
    normalized_decision = decision.strip().lower()
    if normalized_decision not in VALID_PROPOSAL_REVIEW_DECISIONS:
        raise ValueError(f"Unsupported proposal decision: {decision}")

    bundle = load_optimization_proposal_bundle(bundle_path)
    selected_ids = {
        proposal_id.strip()
        for proposal_id in (proposal_ids or [])
        if proposal_id.strip()
    }
    known_ids = {proposal.proposal_id for proposal in bundle.proposals}
    unknown_ids = sorted(selected_ids - known_ids)
    if unknown_ids:
        raise ValueError(f"Unknown proposal ids: {', '.join(unknown_ids)}")

    review_entries: list[ProposalReviewEntry] = []
    for proposal in bundle.proposals:
        entry_decision = normalized_decision
        entry_note = note.strip()
        if selected_ids and proposal.proposal_id not in selected_ids:
            entry_decision = "deferred"
            entry_note = "not selected in this review"
        review_entries.append(
            ProposalReviewEntry(
                proposal_id=proposal.proposal_id,
                proposal_type=proposal.proposal_type,
                route_name=proposal.route_name,
                task_family=proposal.task_family,
                decision=entry_decision,
                description=proposal.description,
                suggested_action=proposal.suggested_action,
                note=entry_note,
                severity=proposal.severity,
                priority=proposal.priority or proposal.severity or "info",
                rationale=proposal.rationale or proposal.description,
                suggested_weight=proposal.suggested_weight,
                suggested_task_family_score=proposal.suggested_task_family_score,
                mark_task_family_unsupported=proposal.mark_task_family_unsupported,
            )
        )

    reviewed_at = utc_now()
    review_record = OptimizationProposalReviewRecord(
        review_id=f"review-{_timestamp_token(reviewed_at)}",
        reviewed_at=reviewed_at,
        decision=normalized_decision,
        source_bundle_path=str(bundle_path),
        source_bundle_id=bundle.bundle_id,
        reviewer=reviewer,
        note=note.strip(),
        entries=review_entries,
    )
    record_path = optimization_proposal_review_path(base_dir, review_record.review_id)
    _write_json(record_path, review_record.to_dict())
    return review_record, record_path


def load_optimization_proposal_review(review_path: Path) -> OptimizationProposalReviewRecord:
    if not review_path.exists():
        raise FileNotFoundError(f"Proposal review record not found: {review_path}")
    return OptimizationProposalReviewRecord.from_dict(_load_json(review_path))


def build_optimization_proposal_review_report(review_record: OptimizationProposalReviewRecord) -> str:
    lines = [
        "# Proposal Review Record",
        "",
        f"- review_id: {review_record.review_id}",
        f"- reviewed_at: {review_record.reviewed_at}",
        f"- reviewer: {review_record.reviewer}",
        f"- decision: {review_record.decision}",
        f"- source_bundle: {review_record.source_bundle_path}",
        f"- note: {review_record.note or 'none'}",
        "",
        "## Entries",
    ]
    if not review_record.entries:
        lines.append("- none")
        return "\n".join(lines) + "\n"

    for entry in review_record.entries:
        task_family_suffix = f" task_family={entry.task_family}" if entry.task_family else ""
        lines.append(
            f"- {entry.proposal_id}: decision={entry.decision} type={entry.proposal_type} "
            f"route={entry.route_name or 'global'}{task_family_suffix} "
            f"priority={entry.priority or entry.severity or 'info'}"
        )
    return "\n".join(lines) + "\n"


def apply_reviewed_optimization_proposals(
    base_dir: Path,
    review_path: Path,
) -> tuple[OptimizationProposalApplicationRecord, Path]:
    review_record = load_optimization_proposal_review(review_path)
    proposal_id = f"{review_record.review_id or review_path.stem}-apply-{time.time_ns():x}"
    register_route_metadata_proposal(
        base_dir=base_dir,
        proposal_id=proposal_id,
        review_path=review_path,
    )
    result = apply_proposal(proposal_id, OperatorToken(source="cli"), ProposalTarget.ROUTE_METADATA)
    if not isinstance(result.payload, tuple) or len(result.payload) != 2:
        raise RuntimeError("Route metadata apply result did not include an application record payload.")
    application_record, application_path = result.payload
    if not isinstance(application_record, OptimizationProposalApplicationRecord) or not isinstance(application_path, Path):
        raise RuntimeError("Route metadata apply result payload has an unexpected shape.")
    return application_record, application_path


def build_optimization_proposal_application_report(
    application_record: OptimizationProposalApplicationRecord,
) -> str:
    lines = [
        "# Proposal Application Record",
        "",
        f"- application_id: {application_record.application_id}",
        f"- applied_at: {application_record.applied_at}",
        f"- source_review: {application_record.source_review_path}",
        f"- applied_count: {application_record.applied_count}",
        f"- noop_count: {application_record.noop_count}",
        f"- skipped_count: {application_record.skipped_count}",
        f"- route_weights_path: {application_record.route_weights_path}",
        f"- route_capabilities_path: {application_record.route_capabilities_path}",
        "",
        "## Entries",
    ]
    if not application_record.entries:
        lines.append("- none")
        return "\n".join(lines) + "\n"

    for entry in application_record.entries:
        detail = entry.detail
        if entry.before_weight is not None and entry.after_weight is not None:
            detail = f"{detail} ({entry.before_weight:.6f} -> {entry.after_weight:.6f})"
        if entry.before_task_family_score is not None or entry.after_task_family_score is not None:
            before_score = "-" if entry.before_task_family_score is None else f"{entry.before_task_family_score:.6f}"
            after_score = "-" if entry.after_task_family_score is None else f"{entry.after_task_family_score:.6f}"
            detail = f"{detail} ({before_score} -> {after_score})"
        lines.append(
            f"- {entry.proposal_id}: status={entry.status} type={entry.proposal_type} "
            f"route={entry.route_name or 'global'}"
            f"{f' task_family={entry.task_family}' if entry.task_family else ''} detail={detail}"
        )
    return "\n".join(lines) + "\n"


class MetaOptimizerAgent:
    """Stateful specialist entity for read-only optimization telemetry analysis."""

    agent_name = META_OPTIMIZER_AGENT_NAME
    system_role = META_OPTIMIZER_SYSTEM_ROLE
    memory_authority = META_OPTIMIZER_MEMORY_AUTHORITY

    def _resolve_last_n(self, card: TaskCard) -> int:
        raw_last_n = card.input_context.get("last_n", 100)
        if isinstance(raw_last_n, bool):
            raise ValueError("MetaOptimizerAgent input_context.last_n must be a positive integer.")
        try:
            last_n = int(raw_last_n)
        except (TypeError, ValueError) as exc:
            raise ValueError("MetaOptimizerAgent input_context.last_n must be a positive integer.") from exc
        if last_n <= 0:
            raise ValueError("MetaOptimizerAgent input_context.last_n must be greater than 0.")
        return last_n

    def _build_prompt(self, state: TaskState, card: TaskCard, *, last_n: int) -> str:
        return "\n".join(
            [
                "# Meta-Optimizer Agent Task",
                "",
                f"- task_id: {state.task_id}",
                f"- agent_name: {self.agent_name}",
                f"- executor_role: {self.system_role}",
                f"- memory_authority: {self.memory_authority}",
                f"- task_limit: {last_n}",
                f"- route_name: {state.route_name or 'pending'}",
                f"- executor_name: {state.executor_name or self.agent_name}",
                f"- goal: {card.goal or state.goal}",
                "- workflow: scan recent task telemetry, summarize route and workflow signals, emit structured proposals, persist read-only proposal artifacts",
            ]
        )

    def execute(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[object],
    ) -> ExecutorResult:
        del retrieval_items

        last_n = self._resolve_last_n(card)
        prompt = self._build_prompt(state, card, last_n=last_n)
        started_at = time.perf_counter()
        snapshot, artifact_path, _report = run_meta_optimizer(base_dir, last_n=last_n)
        bundle_path = latest_optimization_proposal_bundle_path(base_dir)
        bundle = load_optimization_proposal_bundle(bundle_path)
        output_payload = {
            "kind": META_OPTIMIZER_SNAPSHOT_KIND,
            "agent_name": self.agent_name,
            "system_role": self.system_role,
            "memory_authority": self.memory_authority,
            "report_artifact": str(artifact_path),
            "bundle_path": str(bundle_path),
            "bundle_id": bundle.bundle_id,
            "snapshot": snapshot.to_dict(),
        }
        proposal_count = len(snapshot.proposals)
        scanned_task_count = len(snapshot.scanned_task_ids)
        latency_ms = int(round((time.perf_counter() - started_at) * 1000))
        return ExecutorResult(
            executor_name=META_OPTIMIZER_EXECUTOR_NAME,
            status="completed",
            message=(
                f"MetaOptimizerAgent generated {proposal_count} proposal(s) from "
                f"{scanned_task_count} scanned task(s)."
            ),
            output=json.dumps(output_payload, indent=2, sort_keys=True) + "\n",
            prompt=prompt,
            dialect="plain_text",
            latency_ms=max(latency_ms, 0),
            side_effects={
                "kind": META_OPTIMIZER_SNAPSHOT_KIND,
                "bundle_path": str(bundle_path),
                "report_artifact": str(artifact_path),
                "proposal_count": proposal_count,
                "scanned_task_count": scanned_task_count,
            },
        )

    async def execute_async(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[object],
    ) -> ExecutorResult:
        return await asyncio.to_thread(self.execute, base_dir, state, card, retrieval_items)


class MetaOptimizerExecutor(MetaOptimizerAgent):
    """Compatibility wrapper that preserves the historical executor name while delegating to MetaOptimizerAgent."""


def run_meta_optimizer(base_dir: Path, last_n: int = 100) -> tuple[MetaOptimizerSnapshot, Path, str]:
    snapshot = build_meta_optimizer_snapshot(base_dir, last_n=last_n)
    report = build_meta_optimizer_report(snapshot)
    artifact_path = optimization_proposals_path(base_dir)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(report, encoding="utf-8")
    save_optimization_proposal_bundle(base_dir, snapshot, artifact_path)
    return snapshot, artifact_path, report
