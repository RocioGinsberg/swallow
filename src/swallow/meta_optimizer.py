from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
import re
from statistics import median_low

from .models import (
    EVENT_EXECUTOR_COMPLETED,
    EVENT_EXECUTOR_FAILED,
    EVENT_TASK_EXECUTION_FALLBACK,
    OptimizationProposal,
    utc_now,
)
from .paths import (
    latest_optimization_proposal_bundle_path,
    optimization_proposal_application_path,
    optimization_proposal_bundle_path,
    optimization_proposal_review_path,
    optimization_proposals_path,
    route_weights_path,
)
from .router import apply_route_weights, current_route_weights, route_by_name, save_route_weights
from .store import iter_recent_task_events


ROUTE_WEIGHT_PROPOSAL_PATTERN = re.compile(
    r"Route weight suggestion for `(?P<route_name>[^`]+)`: set quality weight to (?P<suggested_weight>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
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


@dataclass(slots=True)
class FailureFingerprint:
    failure_kind: str
    error_code: str
    count: int = 0
    routes: set[str] = field(default_factory=set)


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
    proposals: list[OptimizationProposal]


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
    decision: str
    description: str
    suggested_action: str
    note: str = ""
    severity: str = ""
    priority: str = ""
    rationale: str = ""
    suggested_weight: float | None = None

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
        route_name = data.get("route_name")
        normalized_route_name = None if route_name in {"", None} else str(route_name)
        return cls(
            proposal_id=str(data.get("proposal_id", "")).strip(),
            proposal_type=str(data.get("proposal_type", "")).strip(),
            route_name=normalized_route_name,
            decision=str(data.get("decision", "deferred")).strip() or "deferred",
            description=str(data.get("description", "")).strip(),
            suggested_action=str(data.get("suggested_action", "")).strip(),
            note=str(data.get("note", "")).strip(),
            severity=str(data.get("severity", "")).strip(),
            priority=str(data.get("priority", "")).strip(),
            rationale=str(data.get("rationale", "")).strip(),
            suggested_weight=suggested_weight,
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
    status: str
    detail: str
    before_weight: float | None = None
    after_weight: float | None = None

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
    rollback_weights: dict[str, float]
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
            "rollback_weights": dict(sorted(self.rollback_weights.items())),
            "entries": [entry.to_dict() for entry in self.entries],
        }


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return normalized or "unknown"


def _timestamp_token(value: str) -> str:
    return _slugify(value.replace(":", "-"))


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


def build_meta_optimizer_snapshot(base_dir: Path, last_n: int = 100) -> MetaOptimizerSnapshot:
    if last_n <= 0:
        raise ValueError("--last-n must be greater than 0")

    route_stats_by_name: dict[str, RouteTelemetryStats] = {}
    failure_fingerprints_by_key: dict[tuple[str, str], FailureFingerprint] = {}
    task_family_stats_by_name: dict[str, TaskFamilyTelemetryStats] = {}
    scanned_task_ids: list[str] = []
    scanned_event_count = 0

    for task_id, events in iter_recent_task_events(base_dir, last_n):
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
                task_family = str(payload.get("task_family", "")).strip()
                token_cost = _coerce_nonnegative_float(payload.get("token_cost", 0.0))
                family_stats = None
                if task_family:
                    family_stats = task_family_stats_by_name.setdefault(
                        task_family,
                        TaskFamilyTelemetryStats(task_family=task_family),
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
                if bool(payload.get("degraded", False)):
                    route_stats.degraded_count += 1
                if event_type == EVENT_EXECUTOR_COMPLETED:
                    route_stats.success_count += 1
                else:
                    route_stats.failure_count += 1
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

    return MetaOptimizerSnapshot(
        generated_at=utc_now(),
        task_limit=last_n,
        scanned_task_ids=scanned_task_ids,
        scanned_event_count=scanned_event_count,
        route_stats=route_stats,
        failure_fingerprints=failure_fingerprints,
        degraded_event_count=degraded_event_count,
        task_family_stats=task_family_stats,
        proposals=build_optimization_proposals(route_stats, failure_fingerprints, task_family_stats),
    )


def build_optimization_proposals(
    route_stats: list[RouteTelemetryStats],
    failure_fingerprints: list[FailureFingerprint],
    task_family_stats: list[TaskFamilyTelemetryStats],
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
        recent_average = sum(stats.cost_samples[:midpoint]) / max(midpoint, 1)
        historical_average = sum(stats.cost_samples[midpoint:]) / max(len(stats.cost_samples) - midpoint, 1)
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
                decision=entry_decision,
                description=proposal.description,
                suggested_action=proposal.suggested_action,
                note=entry_note,
                severity=proposal.severity,
                priority=proposal.priority or proposal.severity or "info",
                rationale=proposal.rationale or proposal.description,
                suggested_weight=proposal.suggested_weight,
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
        lines.append(
            f"- {entry.proposal_id}: decision={entry.decision} type={entry.proposal_type} "
            f"route={entry.route_name or 'global'} priority={entry.priority or entry.severity or 'info'}"
        )
    return "\n".join(lines) + "\n"


def apply_reviewed_optimization_proposals(
    base_dir: Path,
    review_path: Path,
) -> tuple[OptimizationProposalApplicationRecord, Path]:
    review_record = load_optimization_proposal_review(review_path)
    approved_entries = [entry for entry in review_record.entries if entry.decision == "approved"]
    if not approved_entries:
        raise ValueError(f"No approved proposals found in {review_path}")

    apply_route_weights(base_dir)
    updated_weights = current_route_weights()

    for entry in approved_entries:
        if entry.proposal_type != "route_weight":
            continue
        route_name = str(entry.route_name or "").strip()
        if not route_name:
            raise ValueError(f"Approved route_weight proposal is missing route_name: {entry.proposal_id}")
        if route_by_name(route_name) is None:
            raise ValueError(f"Unknown route in approved proposal: {route_name}")
        if entry.suggested_weight is None:
            raise ValueError(f"Approved route_weight proposal is missing suggested_weight: {entry.proposal_id}")

    entries: list[ProposalApplicationEntry] = []
    rollback_weights: dict[str, float] = {}
    applied_count = 0
    noop_count = 0
    skipped_count = 0
    for entry in approved_entries:
        if entry.proposal_type != "route_weight":
            skipped_count += 1
            entries.append(
                ProposalApplicationEntry(
                    proposal_id=entry.proposal_id,
                    proposal_type=entry.proposal_type,
                    route_name=entry.route_name,
                    status="skipped",
                    detail="No automatic apply handler is registered for this proposal type.",
                )
            )
            continue

        route_name = str(entry.route_name or "").strip()
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
    save_route_weights(base_dir, persisted_weights)
    apply_route_weights(base_dir)

    applied_at = utc_now()
    application_record = OptimizationProposalApplicationRecord(
        application_id=f"application-{_timestamp_token(applied_at)}",
        applied_at=applied_at,
        source_review_path=str(review_path),
        applied_count=applied_count,
        noop_count=noop_count,
        skipped_count=skipped_count,
        route_weights_path=str(route_weights_path(base_dir)),
        rollback_weights=rollback_weights,
        entries=entries,
    )
    application_path = optimization_proposal_application_path(base_dir, application_record.application_id)
    _write_json(application_path, application_record.to_dict())
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
        lines.append(
            f"- {entry.proposal_id}: status={entry.status} type={entry.proposal_type} "
            f"route={entry.route_name or 'global'} detail={detail}"
        )
    return "\n".join(lines) + "\n"


def run_meta_optimizer(base_dir: Path, last_n: int = 100) -> tuple[MetaOptimizerSnapshot, Path, str]:
    snapshot = build_meta_optimizer_snapshot(base_dir, last_n=last_n)
    report = build_meta_optimizer_report(snapshot)
    artifact_path = optimization_proposals_path(base_dir)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(report, encoding="utf-8")
    save_optimization_proposal_bundle(base_dir, snapshot, artifact_path)
    return snapshot, artifact_path, report
