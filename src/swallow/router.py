from __future__ import annotations

import json
import os
from collections.abc import Iterable
from pathlib import Path

from .executor import DEFAULT_EXECUTOR, normalize_executor_name
from .models import RouteCapabilities, RouteSelection, RouteSpec, TaskState, TaxonomyProfile, infer_task_family
from .paths import route_capabilities_path, route_weights_path


CAPABILITY_MATCH_FIELDS = (
    "execution_kind",
    "supports_tool_loop",
    "filesystem_access",
    "network_access",
    "deterministic",
    "resumable",
)

ROUTE_MODE_TO_ROUTE_NAME = {
    "live": "local-aider",
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

ROUTE_NAME_ALIASES: dict[str, str] = {}


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
    return sorted(route_list, key=lambda route: (-route.quality_weight, route.name))


def _normalize_task_type(value: object) -> str:
    return str(value or "").strip().lower()


def _normalize_task_family_scores(scores: object) -> dict[str, float]:
    if not isinstance(scores, dict):
        return {}
    normalized: dict[str, float] = {}
    for task_type, raw_score in scores.items():
        normalized_task_type = _normalize_task_type(task_type)
        if not normalized_task_type:
            continue
        normalized[normalized_task_type] = round(_normalize_quality_weight(raw_score), 6)
    return normalized


def _normalize_unsupported_task_types(task_types: object) -> list[str]:
    if not isinstance(task_types, list):
        return []
    normalized = {_normalize_task_type(item) for item in task_types}
    normalized.discard("")
    return sorted(normalized)


def _normalize_route_capability_profile(profile: object) -> dict[str, object]:
    if not isinstance(profile, dict):
        return {"task_family_scores": {}, "unsupported_task_types": []}
    return {
        "task_family_scores": _normalize_task_family_scores(profile.get("task_family_scores", {})),
        "unsupported_task_types": _normalize_unsupported_task_types(profile.get("unsupported_task_types", [])),
    }


def _task_family_score(route: RouteSpec, task_family: str) -> float:
    normalized_task_family = _normalize_task_type(task_family)
    if not normalized_task_family:
        return 0.0
    return _normalize_quality_weight(route.task_family_scores.get(normalized_task_family, 0.0))


def _route_supports_task_family(route: RouteSpec, task_family: str) -> bool:
    normalized_task_family = _normalize_task_type(task_family)
    if not normalized_task_family:
        return True
    unsupported = {_normalize_task_type(item) for item in route.unsupported_task_types}
    return normalized_task_family not in unsupported


def _sort_routes_by_preference(routes: Iterable[RouteSpec], task_family: str = "") -> list[RouteSpec]:
    route_list = list(routes)
    return sorted(
        route_list,
        key=lambda route: (-_task_family_score(route, task_family), -route.quality_weight, route.name),
    )


def _filter_supported_task_family(routes: Iterable[RouteSpec], task_family: str) -> list[RouteSpec]:
    return [route for route in routes if _route_supports_task_family(route, task_family)]


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
        summary = self.maybe_get(SUMMARY_FALLBACK_ROUTE_NAME)
        if summary is not None:
            return summary
        return next(iter(self.values()))

    def candidate_routes(
        self,
        *,
        route_name_hint: str = "",
        executor_name: str = "",
        model_hint: str = "",
        executor_family: str = "",
        execution_site: str = "",
        required_capabilities: dict[str, object] | None = None,
        task_family: str = "",
    ) -> tuple[list[RouteSpec], str]:
        if route_name_hint:
            hinted = self.maybe_get(route_name_hint)
            if hinted is not None:
                supported_hinted = _filter_supported_task_family([hinted], task_family)
                if supported_hinted:
                    return supported_hinted, "exact_route_name"

        normalized_executor = normalize_executor_name(executor_name)
        exact_executor_matches = [
            route
            for route in self.values()
            if _registered_executor_name(route.executor_name) == normalized_executor
        ]
        if exact_executor_matches:
            exact_executor_matches = _filter_supported_task_family(exact_executor_matches, task_family)
            model_matches = _filter_supported_task_family(
                _filter_model_hint_matches(exact_executor_matches, model_hint),
                task_family,
            )
            if model_matches:
                return _sort_routes_by_preference(model_matches, task_family), "exact_executor_model_hint"
            if exact_executor_matches:
                return _sort_routes_by_preference(exact_executor_matches, task_family), "exact_executor"

        family_site_matches = [
            route
            for route in self.values()
            if route.executor_family == executor_family and route.execution_site == execution_site
        ]
        if family_site_matches:
            family_site_matches = _filter_supported_task_family(family_site_matches, task_family)
            capability_matches = _filter_capability_matches(family_site_matches, required_capabilities)
            if capability_matches:
                capability_matches = _filter_supported_task_family(capability_matches, task_family)
                if capability_matches:
                    return _sort_routes_by_preference(capability_matches, task_family), "family_site"
            if not required_capabilities:
                return _sort_routes_by_preference(family_site_matches, task_family), "family_site"

        capability_matches = _filter_capability_matches(self.values(), required_capabilities)
        if capability_matches:
            capability_matches = _filter_supported_task_family(capability_matches, task_family)
            if capability_matches:
                return _sort_routes_by_preference(capability_matches, task_family), "capability"

        summary_route = self.maybe_get(SUMMARY_FALLBACK_ROUTE_NAME)
        if summary_route is not None and _route_supports_task_family(summary_route, task_family):
            return [summary_route], "summary_fallback"
        supported_routes = _filter_supported_task_family(self.values(), task_family)
        if supported_routes:
            return _sort_routes_by_preference(supported_routes, task_family), "no_match"
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
                name="local-aider",
                executor_name="aider",
                backend_kind="local_cli",
                model_hint="aider",
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
                name="local-codex",
                executor_name="codex",
                backend_kind="local_cli",
                model_hint="codex",
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
                name="local-http",
                executor_name="http",
                backend_kind="http_api",
                model_hint="http-default",
                dialect_hint="plain_text",
                fallback_route_name="local-claude-code",
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
                fallback_route_name="local-claude-code",
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
                dialect_hint="fim",
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
                name="local-claude-code",
                executor_name="claude-code",
                backend_kind="local_cli",
                model_hint="claude-code",
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
                model_hint="aider",
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


def normalize_route_name(raw_name: str | None) -> str:
    normalized = str(raw_name or "").strip()
    if not normalized:
        return ""
    if normalized.endswith("-detached"):
        base_name = normalized[: -len("-detached")]
        return f"{ROUTE_NAME_ALIASES.get(base_name, base_name)}-detached"
    return ROUTE_NAME_ALIASES.get(normalized, normalized)


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
        normalized_name = normalize_route_name(route_name)
        if not normalized_name:
            continue
        weights[normalized_name] = _normalize_quality_weight(raw_weight)
    return weights


def save_route_weights(base_dir: Path, weights: dict[str, float]) -> Path:
    path = route_weights_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized_weights = {
        normalize_route_name(route_name): round(_normalize_quality_weight(weight), 6)
        for route_name, weight in sorted(weights.items())
        if normalize_route_name(route_name)
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


def load_route_capability_profiles(base_dir: Path) -> dict[str, dict[str, object]]:
    path = route_capabilities_path(base_dir)
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}

    profiles: dict[str, dict[str, object]] = {}
    for route_name, raw_profile in payload.items():
        normalized_name = normalize_route_name(route_name)
        if not normalized_name:
            continue
        profiles[normalized_name] = _normalize_route_capability_profile(raw_profile)
    return profiles


def save_route_capability_profiles(base_dir: Path, profiles: dict[str, dict[str, object]]) -> Path:
    path = route_capabilities_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized_profiles = {
        normalize_route_name(route_name): _normalize_route_capability_profile(profile)
        for route_name, profile in sorted(profiles.items())
        if normalize_route_name(route_name)
    }
    path.write_text(json.dumps(normalized_profiles, indent=2) + "\n", encoding="utf-8")
    return path


def apply_route_capability_profiles(base_dir: Path, registry: RouteRegistry | None = None) -> dict[str, dict[str, object]]:
    active_registry = registry or ROUTE_REGISTRY
    persisted_profiles = load_route_capability_profiles(base_dir)
    for route in active_registry.values():
        profile = persisted_profiles.get(route.name, {})
        route.task_family_scores = _normalize_task_family_scores(profile.get("task_family_scores", {}))
        route.unsupported_task_types = _normalize_unsupported_task_types(profile.get("unsupported_task_types", []))
    return current_route_capability_profiles(active_registry)


def current_route_capability_profiles(registry: RouteRegistry | None = None) -> dict[str, dict[str, object]]:
    active_registry = registry or ROUTE_REGISTRY
    return {
        route.name: {
            "task_family_scores": _normalize_task_family_scores(route.task_family_scores),
            "unsupported_task_types": _normalize_unsupported_task_types(route.unsupported_task_types),
        }
        for route in active_registry.values()
    }


def build_route_capability_profiles_report(base_dir: Path, registry: RouteRegistry | None = None) -> str:
    active_registry = registry or ROUTE_REGISTRY
    profiles = current_route_capability_profiles(active_registry)
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


def route_for_executor(executor_name: str) -> RouteSpec:
    return ROUTE_REGISTRY.route_for_executor(executor_name)


def route_for_mode(route_mode: str) -> RouteSpec | None:
    return ROUTE_REGISTRY.route_for_mode(route_mode)


def route_by_name(route_name: str) -> RouteSpec | None:
    normalized_route_name = normalize_route_name(route_name)
    route = ROUTE_REGISTRY.maybe_get(normalized_route_name)
    if route is not None:
        return route
    if normalized_route_name.endswith("-detached"):
        base_route = ROUTE_REGISTRY.maybe_get(normalized_route_name[: -len("-detached")])
        if base_route is not None:
            return build_detached_route(base_route)
    return None


def lookup_route_by_name(route_name: str) -> RouteSpec | None:
    """Return static route metadata by name without performing route selection."""

    return route_by_name(route_name)


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


def _resolve_complexity_hint(state: TaskState) -> str:
    semantics = state.task_semantics or {}
    return str(semantics.get("complexity_hint", "")).strip().lower()


def _apply_complexity_bias(candidates: list[RouteSpec], complexity_hint: str) -> list[RouteSpec]:
    if not candidates:
        return candidates
    if complexity_hint in {"low", "routine"}:
        preferred = "local-aider"
    elif complexity_hint == "high":
        preferred = "local-claude-code"
    else:
        return candidates
    return sorted(
        candidates,
        key=lambda route: (0 if route.name == preferred else 1, -route.quality_weight, route.name),
    )


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

    task_family = infer_task_family(state)
    complexity_hint = _resolve_complexity_hint(state)
    candidates, match_kind = ROUTE_REGISTRY.candidate_routes(
        executor_name=selected_executor,
        model_hint=state.route_model_hint,
        executor_family=state.route_executor_family,
        execution_site=state.route_execution_site,
        required_capabilities=state.route_capabilities,
        task_family=task_family,
    )
    if (
        complexity_hint in {"high", "low", "routine"}
        and executor_override is None
        and selected_mode == "auto"
        and configured_executor == DEFAULT_EXECUTOR
    ):
        strategy_candidates, strategy_match_kind = ROUTE_REGISTRY.candidate_routes(
            executor_name="__strategy_router__",
            model_hint="",
            executor_family=state.route_executor_family,
            execution_site=state.route_execution_site,
            required_capabilities=state.route_capabilities,
            task_family=task_family,
        )
        if strategy_candidates:
            candidates = strategy_candidates
            match_kind = strategy_match_kind
    candidates = _apply_complexity_bias(candidates, complexity_hint)
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
            "complexity_hint": complexity_hint,
            "parallel_intent": complexity_hint == "parallel",
        },
    )
