from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from swallow.knowledge_retrieval.dialect_data import DEFAULT_EXECUTOR, normalize_executor_name
from swallow.orchestration.models import RouteCapabilities, RouteSpec, TaxonomyProfile
from swallow.provider_router import route_policy as route_policy_module


DEFAULT_ROUTE_REGISTRY_PATH = Path(__file__).with_name("routes.default.json")
CAPABILITY_MATCH_FIELDS = (
    "execution_kind",
    "supports_tool_loop",
    "filesystem_access",
    "network_access",
    "deterministic",
    "resumable",
)


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


def _coerce_string(value: object, *, default: str = "") -> str:
    return str(value if value is not None else default).strip()


def _coerce_bool(value: object, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _normalize_route_name_value(raw_name: object) -> str:
    normalized = str(raw_name or "").strip()
    if not normalized:
        return ""
    if normalized.endswith("-detached"):
        base_name = normalized[: -len("-detached")]
        return f"{route_policy_module.ROUTE_NAME_ALIASES.get(base_name, base_name)}-detached"
    return route_policy_module.ROUTE_NAME_ALIASES.get(normalized, normalized)


def _route_capabilities_from_dict(payload: object) -> RouteCapabilities:
    if not isinstance(payload, dict):
        payload = {}
    return RouteCapabilities(
        execution_kind=_coerce_string(payload.get("execution_kind"), default="unknown"),
        supports_tool_loop=_coerce_bool(payload.get("supports_tool_loop")),
        filesystem_access=_coerce_string(payload.get("filesystem_access"), default="none"),
        network_access=_coerce_string(payload.get("network_access"), default="none"),
        deterministic=_coerce_bool(payload.get("deterministic")),
        resumable=_coerce_bool(payload.get("resumable")),
    )


def _route_taxonomy_from_dict(payload: object) -> TaxonomyProfile:
    if not isinstance(payload, dict):
        payload = {}
    return TaxonomyProfile(
        system_role=_coerce_string(payload.get("system_role"), default="general-executor"),
        memory_authority=_coerce_string(payload.get("memory_authority"), default="task-state"),
    )


def route_spec_from_dict(payload: object) -> RouteSpec:
    if not isinstance(payload, dict):
        raise ValueError("route metadata entry must be a JSON object.")
    route_name = _normalize_route_name_value(payload.get("name"))
    if not route_name:
        raise ValueError("route metadata entry requires a non-empty name.")
    return RouteSpec(
        name=route_name,
        executor_name=_coerce_string(payload.get("executor_name")),
        backend_kind=_coerce_string(payload.get("backend_kind")),
        model_hint=_coerce_string(payload.get("model_hint")),
        dialect_hint=_coerce_string(payload.get("dialect_hint")),
        fallback_route_name=_normalize_route_name_value(payload.get("fallback_route_name")),
        quality_weight=_normalize_quality_weight(payload.get("quality_weight", 1.0)),
        task_family_scores=_normalize_task_family_scores(payload.get("task_family_scores", {})),
        unsupported_task_types=_normalize_unsupported_task_types(payload.get("unsupported_task_types", [])),
        executor_family=_coerce_string(payload.get("executor_family"), default="cli"),
        execution_site=_coerce_string(payload.get("execution_site"), default="local"),
        remote_capable=_coerce_bool(payload.get("remote_capable")),
        transport_kind=_coerce_string(payload.get("transport_kind"), default="local_process"),
        capabilities=_route_capabilities_from_dict(payload.get("capabilities", {})),
        taxonomy=_route_taxonomy_from_dict(payload.get("taxonomy", {})),
    )


def normalize_route_registry_payload(payload: object) -> dict[str, dict[str, object]]:
    if isinstance(payload, dict):
        route_payloads = []
        for route_name, route_payload in payload.items():
            if not isinstance(route_payload, dict):
                raise ValueError(f"Route registry entry must be an object: {route_name}")
            merged_payload = dict(route_payload)
            merged_payload.setdefault("name", route_name)
            route_payloads.append(merged_payload)
    elif isinstance(payload, list):
        route_payloads = payload
    else:
        raise ValueError("Route registry metadata must be a JSON object or list.")

    routes: dict[str, dict[str, object]] = {}
    for route_payload in route_payloads:
        route = route_spec_from_dict(route_payload)
        if route.name in routes:
            raise ValueError(f"Duplicate route registry entry: {route.name}")
        routes[route.name] = route.to_dict()
    if not routes:
        raise ValueError("Route registry metadata must contain at least one route.")

    known_route_names = set(routes)
    for route_name, route_payload in routes.items():
        fallback_name = _coerce_string(route_payload.get("fallback_route_name"))
        if fallback_name and fallback_name not in known_route_names:
            raise ValueError(f"Route {route_name} references unknown fallback route: {fallback_name}")
    return dict(sorted(routes.items()))


def load_route_registry_from_path(path: Path) -> dict[str, dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return normalize_route_registry_payload(payload)


def load_default_route_registry() -> dict[str, dict[str, object]]:
    return load_route_registry_from_path(DEFAULT_ROUTE_REGISTRY_PATH)


def _routes_from_registry_payload(payload: dict[str, dict[str, object]]) -> tuple[RouteSpec, ...]:
    return tuple(route_spec_from_dict(route_payload) for route_payload in payload.values())


class RouteRegistry:
    def __init__(self, routes: Iterable[RouteSpec] = ()) -> None:
        self._routes: dict[str, RouteSpec] = {}
        for route in routes:
            self.register(route)

    def register(self, route: RouteSpec) -> None:
        self._routes[route.name] = route

    def replace(self, routes: Iterable[RouteSpec]) -> None:
        self._routes = {}
        for route in routes:
            self.register(route)

    def get(self, route_name: str) -> RouteSpec:
        return self._routes[route_name]

    def maybe_get(self, route_name: str) -> RouteSpec | None:
        return self._routes.get(route_name)

    def values(self) -> tuple[RouteSpec, ...]:
        return tuple(self._routes.values())

    def route_for_mode(self, route_mode: str) -> RouteSpec | None:
        route_name = route_policy_module.ROUTE_MODE_TO_ROUTE_NAME.get(route_mode)
        return self.maybe_get(route_name) if route_name else None

    def route_for_executor(self, executor_name: str) -> RouteSpec:
        normalized_executor = normalize_executor_name(executor_name)
        mode_route = self.route_for_mode(normalized_executor)
        if mode_route is not None and _registered_executor_name(mode_route.executor_name) == normalized_executor:
            return mode_route
        for route in self.values():
            if _registered_executor_name(route.executor_name) == normalized_executor:
                return route
        summary = self.maybe_get(route_policy_module.SUMMARY_FALLBACK_ROUTE_NAME)
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

        summary_route = self.maybe_get(route_policy_module.SUMMARY_FALLBACK_ROUTE_NAME)
        if summary_route is not None and _route_supports_task_family(summary_route, task_family):
            return [summary_route], "summary_fallback"
        supported_routes = _filter_supported_task_family(self.values(), task_family)
        if supported_routes:
            return _sort_routes_by_preference(supported_routes, task_family), "no_match"
        return list(self.values()), "no_match"


def _build_default_route_registry() -> RouteRegistry:
    return RouteRegistry(_routes_from_registry_payload(load_default_route_registry()))


ROUTE_REGISTRY = _build_default_route_registry()


def current_route_registry(registry: RouteRegistry | None = None) -> dict[str, dict[str, object]]:
    active_registry = registry or ROUTE_REGISTRY
    return {route.name: route.to_dict() for route in active_registry.values()}
