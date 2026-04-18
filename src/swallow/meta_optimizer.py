from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .models import (
    EVENT_EXECUTOR_COMPLETED,
    EVENT_EXECUTOR_FAILED,
    EVENT_TASK_EXECUTION_FALLBACK,
    utc_now,
)
from .paths import optimization_proposals_path, tasks_root


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
class MetaOptimizerSnapshot:
    generated_at: str
    task_limit: int
    scanned_task_ids: list[str]
    scanned_event_count: int
    route_stats: list[RouteTelemetryStats]
    failure_fingerprints: list[FailureFingerprint]
    degraded_event_count: int
    proposals: list[str]


def _load_json_lines(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []

    records: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            records.append(payload)
    return records


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


def _recent_task_event_paths(base_dir: Path, last_n: int) -> list[tuple[str, Path]]:
    root = tasks_root(base_dir)
    if not root.exists():
        return []

    task_event_paths: list[tuple[str, Path]] = []
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        event_path = entry / "events.jsonl"
        if not event_path.exists():
            continue
        task_event_paths.append((entry.name, event_path))

    task_event_paths.sort(
        key=lambda item: (item[1].stat().st_mtime, item[0]),
        reverse=True,
    )
    return task_event_paths[:last_n]


def build_meta_optimizer_snapshot(base_dir: Path, last_n: int = 100) -> MetaOptimizerSnapshot:
    if last_n <= 0:
        raise ValueError("--last-n must be greater than 0")

    route_stats_by_name: dict[str, RouteTelemetryStats] = {}
    failure_fingerprints_by_key: dict[tuple[str, str], FailureFingerprint] = {}
    scanned_task_ids: list[str] = []
    scanned_event_count = 0

    for task_id, event_path in _recent_task_event_paths(base_dir, last_n):
        scanned_task_ids.append(task_id)
        events = _load_json_lines(event_path)
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
                route_stats.total_latency_ms += _coerce_nonnegative_int(payload.get("latency_ms", 0))
                route_stats.total_cost += token_cost
                route_stats.cost_samples.append(token_cost)
                if task_family:
                    route_stats.task_families.add(task_family)
                if str(payload.get("review_feedback", "")).strip():
                    route_stats.debate_retry_count += 1
                    continue
                route_stats.event_count += 1
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

    return MetaOptimizerSnapshot(
        generated_at=utc_now(),
        task_limit=last_n,
        scanned_task_ids=scanned_task_ids,
        scanned_event_count=scanned_event_count,
        route_stats=route_stats,
        failure_fingerprints=failure_fingerprints,
        degraded_event_count=degraded_event_count,
        proposals=build_optimization_proposals(route_stats, failure_fingerprints),
    )


def build_optimization_proposals(
    route_stats: list[RouteTelemetryStats],
    failure_fingerprints: list[FailureFingerprint],
) -> list[str]:
    proposals: list[str] = []
    for stats in route_stats:
        if stats.failure_rate() >= 0.25:
            proposals.append(
                f"Review route `{stats.route_name}`: failure rate is {stats.failure_rate():.0%} over {stats.event_count} executor events."
            )
        if stats.fallback_rate() >= 0.15:
            proposals.append(
                f"Review route `{stats.route_name}`: fallback rate is {stats.fallback_rate():.0%}, suggesting primary execution instability."
            )
        degraded_ratio = stats.degraded_count / stats.event_count if stats.event_count else 0.0
        if degraded_ratio >= 0.2:
            proposals.append(
                f"Track degradation on `{stats.route_name}`: {stats.degraded_count}/{stats.event_count} executor events were degraded."
            )
        if stats.average_cost() >= 0.25:
            proposals.append(
                f"Review route `{stats.route_name}`: average estimated cost is ${stats.average_cost():.2f}/task across {stats.event_count} executor events."
            )

    for fingerprint in failure_fingerprints:
        if fingerprint.count >= 2:
            proposals.append(
                "Investigate repeated failure fingerprint "
                f"`{fingerprint.failure_kind}/{fingerprint.error_code}` across routes: "
                f"{', '.join(sorted(fingerprint.routes))}."
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
            proposals.append(
                f"Compare cost for task_family `{task_family}`: route `{most_expensive.route_name}` averages ${most_expensive.average_cost():.2f}/task versus `{cheapest.route_name}` at ${cheapest.average_cost():.2f}/task."
            )

    for stats in route_stats:
        if len(stats.cost_samples) < 4:
            continue
        midpoint = len(stats.cost_samples) // 2
        recent_average = sum(stats.cost_samples[:midpoint]) / max(midpoint, 1)
        historical_average = sum(stats.cost_samples[midpoint:]) / max(len(stats.cost_samples) - midpoint, 1)
        if recent_average >= 0.10 and recent_average >= historical_average * 1.5:
            proposals.append(
                f"Watch cost trend on `{stats.route_name}`: recent estimated cost rose from ${historical_average:.2f} to ${recent_average:.2f} per executor event."
            )

    if not proposals and route_stats:
        proposals.append(
            "No immediate route, fallback, degradation, or cost anomalies crossed the current heuristic thresholds."
        )
    return proposals


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
    for proposal in snapshot.proposals or ["No immediate optimization proposals were generated."]:
        lines.append(f"- {proposal}")

    return "\n".join(lines) + "\n"


def run_meta_optimizer(base_dir: Path, last_n: int = 100) -> tuple[MetaOptimizerSnapshot, Path, str]:
    snapshot = build_meta_optimizer_snapshot(base_dir, last_n=last_n)
    report = build_meta_optimizer_report(snapshot)
    artifact_path = optimization_proposals_path(base_dir)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(report, encoding="utf-8")
    return snapshot, artifact_path, report
