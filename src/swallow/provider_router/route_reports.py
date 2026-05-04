from __future__ import annotations

from pathlib import Path

from swallow.provider_router import route_policy as route_policy_module
from swallow.provider_router import route_registry as route_registry_module
from swallow.application.infrastructure.paths import route_capabilities_path, route_policy_path, route_registry_path, route_weights_path


def _active_registry(registry: route_registry_module.RouteRegistry | None = None) -> route_registry_module.RouteRegistry:
    return registry or route_registry_module.ROUTE_REGISTRY


def _current_route_weights(registry: route_registry_module.RouteRegistry) -> dict[str, float]:
    return {route.name: route.quality_weight for route in registry.values()}


def _current_route_capability_profiles(registry: route_registry_module.RouteRegistry) -> dict[str, dict[str, object]]:
    return {
        route.name: {
            "task_family_scores": route_registry_module.normalize_task_family_scores(route.task_family_scores),
            "unsupported_task_types": route_registry_module.normalize_unsupported_task_types(route.unsupported_task_types),
        }
        for route in registry.values()
    }


def build_route_registry_report(base_dir: Path, registry: route_registry_module.RouteRegistry | None = None) -> str:
    active_registry = _active_registry(registry)
    lines = [
        "# Route Registry",
        "",
        f"- path: {route_registry_path(base_dir)}",
        f"- default_path: {route_registry_module.DEFAULT_ROUTE_REGISTRY_PATH}",
        "",
        "## Routes",
    ]
    for route in sorted(active_registry.values(), key=lambda item: item.name):
        lines.extend(
            [
                f"- {route.name}",
                f"  executor_name: {route.executor_name}",
                f"  backend_kind: {route.backend_kind}",
                f"  model_hint: {route.model_hint}",
                f"  dialect_hint: {route.dialect_hint or '-'}",
                f"  fallback_route_name: {route.fallback_route_name or '-'}",
                f"  executor_family: {route.executor_family}",
                f"  execution_site: {route.execution_site}",
                f"  transport_kind: {route.transport_kind}",
                f"  taxonomy: {route.taxonomy.system_role} / {route.taxonomy.memory_authority}",
            ]
        )
    return "\n".join(lines) + "\n"


def build_route_policy_report(base_dir: Path) -> str:
    route_policy = route_policy_module.current_route_policy()
    lines = [
        "# Route Policy",
        "",
        f"- path: {route_policy_path(base_dir)}",
        f"- default_path: {route_policy_module.DEFAULT_ROUTE_POLICY_PATH}",
        f"- summary_fallback_route_name: {route_policy['summary_fallback_route_name']}",
        "",
        "## Route Modes",
    ]
    route_mode_routes = route_policy["route_mode_routes"]
    if isinstance(route_mode_routes, dict) and route_mode_routes:
        for mode, route_name in sorted(route_mode_routes.items()):
            lines.append(f"- {mode}: {route_name}")
    else:
        lines.append("- none")
    lines.extend(["", "## Complexity Bias"])
    complexity_bias_routes = route_policy["complexity_bias_routes"]
    if isinstance(complexity_bias_routes, dict) and complexity_bias_routes:
        for hint, route_name in sorted(complexity_bias_routes.items()):
            lines.append(f"- {hint}: {route_name}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Strategy Complexity Hints",
            ", ".join(route_policy["strategy_complexity_hints"]) or "none",
            "",
            "## Parallel Intent Hints",
            ", ".join(route_policy["parallel_intent_hints"]) or "none",
        ]
    )
    return "\n".join(lines) + "\n"


def build_route_weights_report(base_dir: Path, registry: route_registry_module.RouteRegistry | None = None) -> str:
    active_registry = _active_registry(registry)
    weights = _current_route_weights(active_registry)
    lines = [
        "# Route Quality Weights",
        "",
        f"- path: {route_weights_path(base_dir)}",
        "",
        "## Weights",
    ]
    for route_name, weight in sorted(weights.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {route_name}: {weight:.6f}")
    return "\n".join(lines) + "\n"


def build_route_capability_profiles_report(base_dir: Path, registry: route_registry_module.RouteRegistry | None = None) -> str:
    active_registry = _active_registry(registry)
    profiles = _current_route_capability_profiles(active_registry)
    lines = [
        "# Route Capability Profiles",
        "",
        f"- path: {route_capabilities_path(base_dir)}",
        "",
        "## Routes",
    ]
    for route_name in sorted(profiles):
        profile = profiles[route_name]
        score_text = ", ".join(
            f"{task_type}={score:.6f}"
            for task_type, score in sorted(profile["task_family_scores"].items())
        ) or "none"
        unsupported_text = ", ".join(profile["unsupported_task_types"]) or "none"
        lines.extend(
            [
                f"- {route_name}",
                f"  task_family_scores: {score_text}",
                f"  unsupported_task_types: {unsupported_text}",
            ]
        )
    return "\n".join(lines) + "\n"
