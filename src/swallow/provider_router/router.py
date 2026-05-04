from __future__ import annotations

import json
from pathlib import Path

from swallow.orchestration.models import RouteSelection, RouteSpec, TaskState
from swallow.provider_router import route_metadata_store as route_metadata_store_module
from swallow.provider_router import route_policy as route_policy_module
from swallow.provider_router import route_registry as route_registry_module
from swallow.provider_router import route_selection as route_selection_module
from swallow.provider_router.completion_gateway import invoke_completion
from swallow.provider_router.route_reports import (
    build_route_capability_profiles_report,
    build_route_policy_report,
    build_route_registry_report,
    build_route_weights_report,
)
from swallow.application.infrastructure.paths import route_fallbacks_path


CAPABILITY_MATCH_FIELDS = route_registry_module.CAPABILITY_MATCH_FIELDS
DEFAULT_ROUTE_REGISTRY_PATH = route_registry_module.DEFAULT_ROUTE_REGISTRY_PATH
DEFAULT_ROUTE_POLICY_PATH = route_policy_module.DEFAULT_ROUTE_POLICY_PATH

SUMMARY_FALLBACK_ROUTE_NAME = route_policy_module.SUMMARY_FALLBACK_ROUTE_NAME
ROUTE_MODE_ALIASES = route_policy_module.ROUTE_MODE_ALIASES
ROUTE_NAME_ALIASES = route_policy_module.ROUTE_NAME_ALIASES
ROUTE_MODE_TO_ROUTE_NAME = route_policy_module.ROUTE_MODE_TO_ROUTE_NAME
ROUTE_COMPLEXITY_BIAS_ROUTES = route_policy_module.ROUTE_COMPLEXITY_BIAS_ROUTES
ROUTE_STRATEGY_COMPLEXITY_HINTS = route_policy_module.ROUTE_STRATEGY_COMPLEXITY_HINTS
ROUTE_PARALLEL_INTENT_HINTS = route_policy_module.ROUTE_PARALLEL_INTENT_HINTS

RouteRegistry = route_registry_module.RouteRegistry
ROUTE_REGISTRY = route_registry_module.ROUTE_REGISTRY

normalize_route_policy_payload = route_policy_module.normalize_route_policy_payload
load_route_policy_from_path = route_policy_module.load_route_policy_from_path
load_default_route_policy = route_policy_module.load_default_route_policy

route_spec_from_dict = route_registry_module.route_spec_from_dict
normalize_route_registry_payload = route_registry_module.normalize_route_registry_payload
load_route_registry_from_path = route_registry_module.load_route_registry_from_path
load_default_route_registry = route_registry_module.load_default_route_registry


def _sync_route_policy_exports() -> None:
    global SUMMARY_FALLBACK_ROUTE_NAME

    SUMMARY_FALLBACK_ROUTE_NAME = route_policy_module.SUMMARY_FALLBACK_ROUTE_NAME


route_policy_module.apply_route_policy_payload(load_default_route_policy())
_sync_route_policy_exports()


def build_detached_route(route: RouteSpec) -> RouteSpec:
    return route_selection_module.build_detached_route(route)


def normalize_route_mode(raw_mode: str | None) -> str:
    return route_selection_module.normalize_route_mode(raw_mode)


def normalize_route_name(raw_name: str | None) -> str:
    return route_selection_module.normalize_route_name(raw_name)


def load_route_registry(base_dir: Path) -> dict[str, dict[str, object]]:
    return route_metadata_store_module.load_route_registry(base_dir)


def load_route_policy(base_dir: Path) -> dict[str, object]:
    return route_metadata_store_module.load_route_policy(base_dir)


def save_route_registry(base_dir: Path, route_registry: object) -> Path:
    return route_metadata_store_module.save_route_registry(base_dir, route_registry)


def save_route_policy(base_dir: Path, route_policy: object) -> Path:
    return route_metadata_store_module.save_route_policy(base_dir, route_policy)


def route_metadata_snapshot(base_dir: Path) -> dict[str, object]:
    return route_metadata_store_module.route_metadata_snapshot(base_dir)


def current_route_registry(registry: RouteRegistry | None = None) -> dict[str, dict[str, object]]:
    active_registry = registry or ROUTE_REGISTRY
    return route_registry_module.current_route_registry(active_registry)


def apply_route_registry(base_dir: Path, registry: RouteRegistry | None = None) -> dict[str, dict[str, object]]:
    active_registry = registry or ROUTE_REGISTRY
    route_registry = load_route_registry(base_dir)
    return route_registry_module.replace_route_registry_from_payload(active_registry, route_registry)


def apply_route_policy(base_dir: Path) -> dict[str, object]:
    applied = route_policy_module.apply_route_policy(base_dir)
    _sync_route_policy_exports()
    return applied


def current_route_policy() -> dict[str, object]:
    return route_policy_module.current_route_policy()


def load_route_weights(base_dir: Path) -> dict[str, float]:
    return route_metadata_store_module.load_route_weights(base_dir)


def save_route_weights(base_dir: Path, weights: dict[str, float]) -> Path:
    return route_metadata_store_module.save_route_weights(base_dir, weights)


def apply_route_weights(base_dir: Path, registry: RouteRegistry | None = None) -> dict[str, float]:
    active_registry = registry or ROUTE_REGISTRY
    persisted_weights = load_route_weights(base_dir)
    for route in active_registry.values():
        route.quality_weight = persisted_weights.get(route.name, 1.0)
    return current_route_weights(active_registry)


def current_route_weights(registry: RouteRegistry | None = None) -> dict[str, float]:
    active_registry = registry or ROUTE_REGISTRY
    return {route.name: route.quality_weight for route in active_registry.values()}


def load_route_capability_profiles(base_dir: Path) -> dict[str, dict[str, object]]:
    return route_metadata_store_module.load_route_capability_profiles(base_dir)


def save_route_capability_profiles(base_dir: Path, profiles: dict[str, dict[str, object]]) -> Path:
    return route_metadata_store_module.save_route_capability_profiles(base_dir, profiles)


def apply_route_capability_profiles(base_dir: Path, registry: RouteRegistry | None = None) -> dict[str, dict[str, object]]:
    active_registry = registry or ROUTE_REGISTRY
    persisted_profiles = load_route_capability_profiles(base_dir)
    for route in active_registry.values():
        profile = persisted_profiles.get(route.name, {})
        route.task_family_scores = route_registry_module.normalize_task_family_scores(
            profile.get("task_family_scores", {})
        )
        route.unsupported_task_types = route_registry_module.normalize_unsupported_task_types(
            profile.get("unsupported_task_types", [])
        )
    return current_route_capability_profiles(active_registry)


def current_route_capability_profiles(registry: RouteRegistry | None = None) -> dict[str, dict[str, object]]:
    active_registry = registry or ROUTE_REGISTRY
    return {
        route.name: {
            "task_family_scores": route_registry_module.normalize_task_family_scores(route.task_family_scores),
            "unsupported_task_types": route_registry_module.normalize_unsupported_task_types(
                route.unsupported_task_types
            ),
        }
        for route in active_registry.values()
    }


def load_route_fallbacks(base_dir: Path) -> dict[str, str]:
    path = route_fallbacks_path(base_dir)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}

    fallbacks: dict[str, str] = {}
    for route_name, raw_fallback in payload.items():
        normalized_name = normalize_route_name(route_name)
        if not normalized_name:
            continue
        fallback_name = normalize_route_name(str(raw_fallback or ""))
        fallbacks[normalized_name] = fallback_name
    return fallbacks


def apply_route_fallbacks(base_dir: Path, registry: RouteRegistry | None = None) -> dict[str, str]:
    active_registry = registry or ROUTE_REGISTRY
    persisted_fallbacks = load_route_fallbacks(base_dir)
    known_routes = {route.name for route in active_registry.values()}
    baseline = route_registry_module.builtin_route_fallbacks(active_registry)

    for route in active_registry.values():
        fallback_name = baseline.get(route.name, "")
        if route.name in persisted_fallbacks:
            configured_fallback = persisted_fallbacks[route.name]
            if not configured_fallback or configured_fallback in known_routes:
                fallback_name = configured_fallback
        route.fallback_route_name = fallback_name
    return {route.name: route.fallback_route_name for route in active_registry.values()}


def route_for_executor(executor_name: str) -> RouteSpec:
    return route_selection_module.route_for_executor(executor_name, registry=ROUTE_REGISTRY)


def route_for_mode(route_mode: str) -> RouteSpec | None:
    return route_selection_module.route_for_mode(route_mode, registry=ROUTE_REGISTRY)


def route_by_name(route_name: str) -> RouteSpec | None:
    return route_selection_module.route_by_name(route_name, registry=ROUTE_REGISTRY)


def lookup_route_by_name(route_name: str) -> RouteSpec | None:
    """Return static route metadata by name without performing route selection."""

    return route_selection_module.lookup_route_by_name(route_name, registry=ROUTE_REGISTRY)


def fallback_route_for(route_name: str) -> RouteSpec | None:
    return route_selection_module.fallback_route_for(route_name, registry=ROUTE_REGISTRY)


def resolve_fallback_chain(primary_route_name: str) -> tuple[str, ...]:
    """Return the static fallback route-name chain for a primary route."""

    return route_selection_module.resolve_fallback_chain(primary_route_name, registry=ROUTE_REGISTRY)


def select_route(
    state: TaskState,
    executor_override: str | None = None,
    route_mode_override: str | None = None,
) -> RouteSelection:
    return route_selection_module.select_route(
        state,
        executor_override=executor_override,
        route_mode_override=route_mode_override,
        registry=ROUTE_REGISTRY,
    )
