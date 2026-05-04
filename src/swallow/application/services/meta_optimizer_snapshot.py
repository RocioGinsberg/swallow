from __future__ import annotations

from pathlib import Path

from swallow.orchestration.models import (
    EVENT_EXECUTOR_COMPLETED,
    EVENT_EXECUTOR_FAILED,
    EVENT_TASK_EXECUTION_FALLBACK,
    utc_now,
)
from swallow.application.services.meta_optimizer_models import (
    FailureFingerprint,
    MetaOptimizerSnapshot,
    RouteTaskFamilyTelemetryStats,
    RouteTelemetryStats,
    TaskFamilyTelemetryStats,
    _coerce_nonnegative_float,
    _coerce_nonnegative_int,
)
from swallow.application.services.meta_optimizer_proposals import _normalize_task_family_name, build_optimization_proposals
from swallow.truth_governance.store import iter_recent_task_events

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
