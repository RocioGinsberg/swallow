from __future__ import annotations

import re
from pathlib import Path
from statistics import median_low

from swallow.orchestration.models import OptimizationProposal
from swallow.provider_router.router import load_route_capability_profiles, route_by_name
from swallow.surface_tools.meta_optimizer_models import (
    FailureFingerprint,
    RouteTaskFamilyTelemetryStats,
    RouteTelemetryStats,
    TaskFamilyTelemetryStats,
    _ensure_proposal_metadata,
)

ROUTE_WEIGHT_PROPOSAL_PATTERN = re.compile(
    r"Route weight suggestion for `(?P<route_name>[^`]+)`: set quality weight to (?P<suggested_weight>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

def _normalize_task_family_name(value: object) -> str:
    return str(value or "").strip().lower()


def _suggest_task_family_score(stats: RouteTaskFamilyTelemetryStats) -> float:
    suggested = stats.success_rate() - (stats.degraded_rate() * 0.25)
    return round(min(max(suggested, 0.0), 1.0), 2)


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
