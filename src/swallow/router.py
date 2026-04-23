from __future__ import annotations

import json
import os
from collections.abc import Iterable
from pathlib import Path

from .executor import DEFAULT_EXECUTOR, normalize_executor_name
from .models import RouteCapabilities, RouteSelection, RouteSpec, TaskState, TaxonomyProfile
from .paths import route_weights_path


CAPABILITY_MATCH_FIELDS = (
    "execution_kind",
    "supports_tool_loop",
    "filesystem_access",
    "network_access",
    "deterministic",
    "resumable",
)

ROUTE_MODE_TO_ROUTE_NAME = {
    "live": "local-codex",
    "http": "local-http",
    "deterministic": "local-mock",
    "offline": "local-note",
    "summary": "local-summary",
}

SUMMARY_FALLBACK_ROUTE_NAME = "local-summary"

ROUTE_MODE_ALIASES = {
    "": "auto",
    "auto": "auto",
    "live": "live",
    "http": "http",
    "deterministic": "deterministic",
    "detached": "detached",
    "offline": "offline",
    "summary": "summary",
}


def _registered_executor_name(raw_name: str | None) -> str:
    raw = (raw_name or "").strip().lower()
    normalized = normalize_executor_name(raw_name)
    if raw and normalized == DEFAULT_EXECUTOR and raw != DEFAULT_EXECUTOR:
        return raw
    return normalized


def _normalize_quality_weight(value: object) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, int | float):
        return max(float(value), 0.0)
    if isinstance(value, str):
        try:
            return max(float(value.strip()), 0.0)
        except ValueError:
            return 1.0
    return 1.0


def _sort_routes_by_quality(routes: Iterable[RouteSpec]) -> list[RouteSpec]:
    route_list = list(routes)
    return sorted(route_list, key=lambda route: route.quality_weight, reverse=True)


class RouteRegistry:
    def __init__(self, routes: Iterable[RouteSpec] = ()) -> None:
        self._routes: dict[str, RouteSpec] = {}
        for route in routes:
            self.register(route)

    def register(self, route: RouteSpec) -> None:
        self._routes[route.name] = route

    def get(self, route_name: str) -> RouteSpec:
        return self._routes[route_name]

    def maybe_get(self, route_name: str) -> RouteSpec | None:
        return self._routes.get(route_name)

    def values(self) -> tuple[RouteSpec, ...]:
        return tuple(self._routes.values())

    def route_for_mode(self, route_mode: str) -> RouteSpec | None:
        route_name = ROUTE_MODE_TO_ROUTE_NAME.get(route_mode)
        return self.maybe_get(route_name) if route_name else None

    def route_for_executor(self, executor_name: str) -> RouteSpec:
        normalized_executor = normalize_executor_name(executor_name)
        for route in self.values():
            if _registered_executor_name(route.executor_name) == normalized_executor:
                return route
        return self.get("local-codex")

    def candidate_routes(
        self,
        *,
        route_name_hint: str = "",
        executor_name: str = "",
        model_hint: str = "",
        executor_family: str = "",
        execution_site: str = "",
        required_capabilities: dict[str, object] | None = None,
    ) -> tuple[list[RouteSpec], str]:
        if route_name_hint:
            hinted = self.maybe_get(route_name_hint)
            if hinted is not None:
                return [hinted], "exact_route_name"

        normalized_executor = normalize_executor_name(executor_name)
        exact_executor_matches = [
            route
            for route in self.values()
            if _registered_executor_name(route.executor_name) == normalized_executor
        ]
        if exact_executor_matches:
            model_matches = _filter_model_hint_matches(exact_executor_matches, model_hint)
            if model_matches:
                return _sort_routes_by_quality(model_matches), "exact_executor_model_hint"
            return _sort_routes_by_quality(exact_executor_matches), "exact_executor"

        family_site_matches = [
            route
            for route in self.values()
            if route.executor_family == executor_family and route.execution_site == execution_site
        ]
        if family_site_matches:
            capability_matches = _filter_capability_matches(family_site_matches, required_capabilities)
            if capability_matches:
                return _sort_routes_by_quality(capability_matches), "family_site"
            if not required_capabilities:
                return _sort_routes_by_quality(family_site_matches), "family_site"

        capability_matches = _filter_capability_matches(self.values(), required_capabilities)
        if capability_matches:
            return _sort_routes_by_quality(capability_matches), "capability"

        summary_route = self.maybe_get(SUMMARY_FALLBACK_ROUTE_NAME)
        if summary_route is not None:
            return [summary_route], "summary_fallback"
        return list(self.values()), "no_match"


def _filter_capability_matches(
    routes: Iterable[RouteSpec],
    required_capabilities: dict[str, object] | None,
) -> list[RouteSpec]:
    requirements = required_capabilities or {}
    if not requirements:
        return []

    matches: list[RouteSpec] = []
    for route in routes:
        if _route_matches_capabilities(route, requirements):
            matches.append(route)
    return matches


def _filter_model_hint_matches(routes: Iterable[RouteSpec], model_hint: str) -> list[RouteSpec]:
    requested_hint = (model_hint or "").strip().lower()
    if not requested_hint:
        return []

    matches: list[RouteSpec] = []
    for route in routes:
        route_hint = str(route.model_hint or "").strip().lower()
        if not route_hint:
            continue
        if route_hint == requested_hint or route_hint in requested_hint or requested_hint in route_hint:
            matches.append(route)
    return matches


def _route_matches_capabilities(route: RouteSpec, requirements: dict[str, object]) -> bool:
    has_requirement = False
    for field_name in CAPABILITY_MATCH_FIELDS:
        if field_name not in requirements:
            continue
        required = requirements[field_name]
        if required in {"", None}:
            continue
        has_requirement = True
        if getattr(route.capabilities, field_name) != required:
            return False
    return has_requirement


def _build_builtin_route_registry() -> RouteRegistry:
    return RouteRegistry(
        [
            RouteSpec(
                name="local-codex",
                executor_name="codex",
                backend_kind="local_cli",
                model_hint="codex",
                dialect_hint="codex_fim",
                fallback_route_name="local-summary",
                executor_family="cli",
                execution_site="local",
                remote_capable=False,
                transport_kind="local_process",
                capabilities=RouteCapabilities(
                    execution_kind="code_execution",
                    supports_tool_loop=True,
                    filesystem_access="workspace_write",
                    network_access="optional",
                    deterministic=False,
                    resumable=True,
                ),
                taxonomy=TaxonomyProfile(
                    system_role="general-executor",
                    memory_authority="task-state",
                ),
            ),
            RouteSpec(
                name="local-http",
                executor_name="http",
                backend_kind="http_api",
                model_hint="http-default",
                dialect_hint="plain_text",
                fallback_route_name="local-cline",
                executor_family="api",
                execution_site="local",
                remote_capable=False,
                transport_kind="http",
                capabilities=RouteCapabilities(
                    execution_kind="artifact_generation",
                    supports_tool_loop=False,
                    filesystem_access="workspace_read",
                    network_access="optional",
                    deterministic=False,
                    resumable=True,
                ),
                taxonomy=TaxonomyProfile(
                    system_role="general-executor",
                    memory_authority="task-state",
                ),
            ),
            RouteSpec(
                name="http-claude",
                executor_name="http",
                backend_kind="http_api",
                model_hint="claude-3-7-sonnet",
                dialect_hint="claude_xml",
                fallback_route_name="http-qwen",
                executor_family="api",
                execution_site="local",
                remote_capable=False,
                transport_kind="http",
                capabilities=RouteCapabilities(
                    execution_kind="artifact_generation",
                    supports_tool_loop=False,
                    filesystem_access="workspace_read",
                    network_access="optional",
                    deterministic=False,
                    resumable=True,
                ),
                taxonomy=TaxonomyProfile(
                    system_role="general-executor",
                    memory_authority="task-state",
                ),
            ),
            RouteSpec(
                name="http-qwen",
                executor_name="http",
                backend_kind="http_api",
                model_hint="qwen2.5-coder-32b-instruct",
                dialect_hint="plain_text",
                fallback_route_name="http-glm",
                executor_family="api",
                execution_site="local",
                remote_capable=False,
                transport_kind="http",
                capabilities=RouteCapabilities(
                    execution_kind="artifact_generation",
                    supports_tool_loop=False,
                    filesystem_access="workspace_read",
                    network_access="optional",
                    deterministic=False,
                    resumable=True,
                ),
                taxonomy=TaxonomyProfile(
                    system_role="general-executor",
                    memory_authority="task-state",
                ),
            ),
            RouteSpec(
                name="http-glm",
                executor_name="http",
                backend_kind="http_api",
                model_hint="glm-4.5-air",
                dialect_hint="plain_text",
                fallback_route_name="local-cline",
                executor_family="api",
                execution_site="local",
                remote_capable=False,
                transport_kind="http",
                capabilities=RouteCapabilities(
                    execution_kind="artifact_generation",
                    supports_tool_loop=False,
                    filesystem_access="workspace_read",
                    network_access="optional",
                    deterministic=False,
                    resumable=True,
                ),
                taxonomy=TaxonomyProfile(
                    system_role="general-executor",
                    memory_authority="task-state",
                ),
            ),
            RouteSpec(
                name="http-gemini",
                executor_name="http",
                backend_kind="http_api",
                model_hint="gemini-2.5-pro",
                dialect_hint="plain_text",
                fallback_route_name="http-qwen",
                executor_family="api",
                execution_site="local",
                remote_capable=False,
                transport_kind="http",
                capabilities=RouteCapabilities(
                    execution_kind="artifact_generation",
                    supports_tool_loop=False,
                    filesystem_access="workspace_read",
                    network_access="optional",
                    deterministic=False,
                    resumable=True,
                ),
                taxonomy=TaxonomyProfile(
                    system_role="general-executor",
                    memory_authority="task-state",
                ),
            ),
            RouteSpec(
                name="http-deepseek",
                executor_name="http",
                backend_kind="http_api",
                model_hint="deepseek-chat",
                dialect_hint="codex_fim",
                fallback_route_name="http-qwen",
                executor_family="api",
                execution_site="local",
                remote_capable=False,
                transport_kind="http",
                capabilities=RouteCapabilities(
                    execution_kind="code_execution",
                    supports_tool_loop=False,
                    filesystem_access="workspace_read",
                    network_access="optional",
                    deterministic=False,
                    resumable=True,
                ),
                taxonomy=TaxonomyProfile(
                    system_role="general-executor",
                    memory_authority="task-state",
                ),
            ),
            RouteSpec(
                name="local-cline",
                executor_name="cline",
                backend_kind="local_cli",
                model_hint="cline",
                dialect_hint="plain_text",
                fallback_route_name="local-summary",
                executor_family="cli",
                execution_site="local",
                remote_capable=False,
                transport_kind="local_process",
                capabilities=RouteCapabilities(
                    execution_kind="code_execution",
                    supports_tool_loop=True,
                    filesystem_access="workspace_write",
                    network_access="optional",
                    deterministic=False,
                    resumable=True,
                ),
                taxonomy=TaxonomyProfile(
                    system_role="general-executor",
                    memory_authority="task-state",
                ),
            ),
            RouteSpec(
                name="local-mock",
                executor_name="mock",
                backend_kind="deterministic_test",
                model_hint="mock",
                dialect_hint="plain_text",
                executor_family="cli",
                execution_site="local",
                remote_capable=False,
                transport_kind="local_process",
                capabilities=RouteCapabilities(
                    execution_kind="artifact_generation",
                    supports_tool_loop=False,
                    filesystem_access="workspace_read",
                    network_access="none",
                    deterministic=True,
                    resumable=True,
                ),
                taxonomy=TaxonomyProfile(
                    system_role="general-executor",
                    memory_authority="task-state",
                ),
            ),
            RouteSpec(
                name="local-note",
                executor_name="note-only",
                backend_kind="local_fallback",
                model_hint="codex",
                dialect_hint="plain_text",
                executor_family="cli",
                execution_site="local",
                remote_capable=False,
                transport_kind="local_process",
                capabilities=RouteCapabilities(
                    execution_kind="artifact_generation",
                    supports_tool_loop=False,
                    filesystem_access="workspace_read",
                    network_access="none",
                    deterministic=True,
                    resumable=True,
                ),
                taxonomy=TaxonomyProfile(
                    system_role="specialist",
                    memory_authority="task-memory",
                ),
            ),
            RouteSpec(
                name="local-summary",
                executor_name="local",
                backend_kind="local_summary",
                model_hint="local",
                dialect_hint="plain_text",
                executor_family="cli",
                execution_site="local",
                remote_capable=False,
                transport_kind="local_process",
                capabilities=RouteCapabilities(
                    execution_kind="artifact_generation",
                    supports_tool_loop=False,
                    filesystem_access="workspace_read",
                    network_access="none",
                    deterministic=True,
                    resumable=True,
                ),
                taxonomy=TaxonomyProfile(
                    system_role="general-executor",
                    memory_authority="task-state",
                ),
            ),
            RouteSpec(
                name="mock-remote",
                executor_name="mock-remote",
                backend_kind="mock_remote",
                model_hint="mock-remote",
                dialect_hint="plain_text",
                executor_family="cli",
                execution_site="remote",
                remote_capable=True,
                transport_kind="mock_remote_transport",
                capabilities=RouteCapabilities(
                    execution_kind="artifact_generation",
                    supports_tool_loop=False,
                    filesystem_access="workspace_read",
                    network_access="none",
                    deterministic=True,
                    resumable=True,
                ),
                taxonomy=TaxonomyProfile(
                    system_role="general-executor",
                    memory_authority="task-state",
                ),
            ),
        ]
    )


ROUTE_REGISTRY = _build_builtin_route_registry()


def build_detached_route(route: RouteSpec) -> RouteSpec:
    return RouteSpec(
        name=f"{route.name}-detached",
        executor_name=route.executor_name,
        backend_kind=f"{route.backend_kind}_detached",
        model_hint=route.model_hint,
        dialect_hint=route.dialect_hint,
        fallback_route_name=route.fallback_route_name,
        quality_weight=route.quality_weight,
        executor_family=route.executor_family,
        execution_site="local",
        remote_capable=False,
        transport_kind="local_detached_process",
        capabilities=route.capabilities,
        taxonomy=route.taxonomy,
    )


def normalize_route_mode(raw_mode: str | None) -> str:
    normalized = (raw_mode or "").strip().lower()
    return ROUTE_MODE_ALIASES.get(normalized, "auto")


def load_route_weights(base_dir: Path) -> dict[str, float]:
    path = route_weights_path(base_dir)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}

    weights: dict[str, float] = {}
    for route_name, raw_weight in payload.items():
        normalized_name = str(route_name).strip()
        if not normalized_name:
            continue
        weights[normalized_name] = _normalize_quality_weight(raw_weight)
    return weights


def save_route_weights(base_dir: Path, weights: dict[str, float]) -> Path:
    path = route_weights_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized_weights = {
        route_name: round(_normalize_quality_weight(weight), 6)
        for route_name, weight in sorted(weights.items())
    }
    path.write_text(json.dumps(normalized_weights, indent=2) + "\n", encoding="utf-8")
    return path


def apply_route_weights(base_dir: Path, registry: RouteRegistry | None = None) -> dict[str, float]:
    active_registry = registry or ROUTE_REGISTRY
    persisted_weights = load_route_weights(base_dir)
    for route in active_registry.values():
        route.quality_weight = persisted_weights.get(route.name, 1.0)
    return {route.name: route.quality_weight for route in active_registry.values()}


def current_route_weights(registry: RouteRegistry | None = None) -> dict[str, float]:
    active_registry = registry or ROUTE_REGISTRY
    return {route.name: route.quality_weight for route in active_registry.values()}


def build_route_weights_report(base_dir: Path, registry: RouteRegistry | None = None) -> str:
    active_registry = registry or ROUTE_REGISTRY
    weights = current_route_weights(active_registry)
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


def route_for_executor(executor_name: str) -> RouteSpec:
    return ROUTE_REGISTRY.route_for_executor(executor_name)


def route_for_mode(route_mode: str) -> RouteSpec | None:
    return ROUTE_REGISTRY.route_for_mode(route_mode)


def route_by_name(route_name: str) -> RouteSpec | None:
    route = ROUTE_REGISTRY.maybe_get(route_name)
    if route is not None:
        return route
    if route_name.endswith("-detached"):
        base_route = ROUTE_REGISTRY.maybe_get(route_name[: -len("-detached")])
        if base_route is not None:
            return build_detached_route(base_route)
    return None


def fallback_route_for(route_name: str) -> RouteSpec | None:
    route = route_by_name(route_name)
    if route is None or not route.fallback_route_name:
        return None
    return route_by_name(route.fallback_route_name)


def _reason_with_strategy_match(base_reason: str, match_kind: str) -> str:
    if match_kind in {"exact_executor", "exact_route_name"}:
        return base_reason
    if match_kind == "exact_executor_model_hint":
        return f"{base_reason} Strategy router matched executor and model hint."
    if match_kind == "family_site":
        return f"{base_reason} Strategy router matched executor family and execution site."
    if match_kind == "capability":
        return f"{base_reason} Strategy router matched route capabilities."
    if match_kind == "summary_fallback":
        return "No registered route matched the requested executor profile; selected the local summary fallback."
    return f"{base_reason} Strategy router used the default summary fallback."


def select_route(
    state: TaskState,
    executor_override: str | None = None,
    route_mode_override: str | None = None,
) -> RouteSelection:
    explicit_executor = normalize_executor_name(executor_override)
    configured_executor = normalize_executor_name(state.executor_name)
    legacy_executor = normalize_executor_name(os.environ.get("AIWF_EXECUTOR_MODE"))
    selected_mode = normalize_route_mode(route_mode_override or state.route_mode)

    selected_executor = configured_executor
    reason = "Selected the task-configured route."
    if executor_override is not None:
        selected_executor = explicit_executor
        reason = "Selected the route from the run-time executor override."
    elif selected_mode != "auto":
        if selected_mode == "detached":
            route = build_detached_route(route_for_executor(selected_executor))
            return RouteSelection(
                route=route,
                reason="Selected the detached local execution variant from the routing policy mode.",
                policy_inputs={
                    "executor_override": executor_override or "",
                    "route_mode_override": route_mode_override or "",
                    "task_executor": state.executor_name,
                    "task_route_mode": state.route_mode,
                    "legacy_executor_mode": os.environ.get("AIWF_EXECUTOR_MODE", ""),
                },
            )
        mode_route = route_for_mode(selected_mode)
        if mode_route is not None:
            return RouteSelection(
                route=mode_route,
                reason="Selected the route from the routing policy mode.",
                policy_inputs={
                    "executor_override": executor_override or "",
                    "route_mode_override": route_mode_override or "",
                    "task_executor": state.executor_name,
                    "task_route_mode": state.route_mode,
                    "legacy_executor_mode": os.environ.get("AIWF_EXECUTOR_MODE", ""),
                },
            )
    elif configured_executor == DEFAULT_EXECUTOR and legacy_executor != DEFAULT_EXECUTOR:
        selected_executor = legacy_executor
        reason = "Selected the route from legacy executor mode because the task kept the default executor."

    candidates, match_kind = ROUTE_REGISTRY.candidate_routes(
        executor_name=selected_executor,
        model_hint=state.route_model_hint,
        executor_family=state.route_executor_family,
        execution_site=state.route_execution_site,
        required_capabilities=state.route_capabilities,
    )
    route = candidates[0] if candidates else route_for_executor(selected_executor)
    return RouteSelection(
        route=route,
        reason=_reason_with_strategy_match(reason, match_kind),
        policy_inputs={
            "executor_override": executor_override or "",
            "route_mode_override": route_mode_override or "",
            "task_executor": state.executor_name,
            "task_route_mode": state.route_mode,
            "legacy_executor_mode": os.environ.get("AIWF_EXECUTOR_MODE", ""),
        },
    )
