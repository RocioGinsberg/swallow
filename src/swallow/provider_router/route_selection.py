from __future__ import annotations

import os

from swallow.knowledge_retrieval.dialect_data import DEFAULT_EXECUTOR, normalize_executor_name
from swallow.orchestration.models import RouteSelection, RouteSpec, TaskState, infer_task_family
from swallow.provider_router import route_policy as route_policy_module
from swallow.provider_router import route_registry as route_registry_module


def _active_registry(registry: route_registry_module.RouteRegistry | None = None) -> route_registry_module.RouteRegistry:
    return registry or route_registry_module.ROUTE_REGISTRY


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
    return route_policy_module._normalize_route_mode_value(raw_mode)


def normalize_route_name(raw_name: str | None) -> str:
    return route_policy_module._normalize_route_name_value(raw_name)


def route_for_executor(
    executor_name: str,
    *,
    registry: route_registry_module.RouteRegistry | None = None,
) -> RouteSpec:
    return _active_registry(registry).route_for_executor(executor_name)


def route_for_mode(
    route_mode: str,
    *,
    registry: route_registry_module.RouteRegistry | None = None,
) -> RouteSpec | None:
    return _active_registry(registry).route_for_mode(route_mode)


def route_by_name(
    route_name: str,
    *,
    registry: route_registry_module.RouteRegistry | None = None,
) -> RouteSpec | None:
    active_registry = _active_registry(registry)
    normalized_route_name = normalize_route_name(route_name)
    route = active_registry.maybe_get(normalized_route_name)
    if route is not None:
        return route
    if normalized_route_name.endswith("-detached"):
        base_route = active_registry.maybe_get(normalized_route_name[: -len("-detached")])
        if base_route is not None:
            return build_detached_route(base_route)
    return None


def lookup_route_by_name(
    route_name: str,
    *,
    registry: route_registry_module.RouteRegistry | None = None,
) -> RouteSpec | None:
    """Return static route metadata by name without performing route selection."""

    return route_by_name(route_name, registry=registry)


def fallback_route_for(
    route_name: str,
    *,
    registry: route_registry_module.RouteRegistry | None = None,
) -> RouteSpec | None:
    route = route_by_name(route_name, registry=registry)
    if route is None or not route.fallback_route_name:
        return None
    return route_by_name(route.fallback_route_name, registry=registry)


def resolve_fallback_chain(
    primary_route_name: str,
    *,
    registry: route_registry_module.RouteRegistry | None = None,
) -> tuple[str, ...]:
    """Return the static fallback route-name chain for a primary route."""

    route = route_by_name(primary_route_name, registry=registry)
    if route is None:
        return ()

    chain: list[str] = []
    seen: set[str] = set()
    current_name = route.name
    while current_name and current_name not in seen:
        chain.append(current_name)
        seen.add(current_name)
        fallback_route = fallback_route_for(current_name, registry=registry)
        current_name = fallback_route.name if fallback_route is not None else ""
    return tuple(chain)


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
    preferred = route_policy_module.ROUTE_COMPLEXITY_BIAS_ROUTES.get(complexity_hint)
    if not preferred:
        return candidates
    return sorted(
        candidates,
        key=lambda route: (0 if route.name == preferred else 1, -route.quality_weight, route.name),
    )


def select_route(
    state: TaskState,
    executor_override: str | None = None,
    route_mode_override: str | None = None,
    *,
    registry: route_registry_module.RouteRegistry | None = None,
) -> RouteSelection:
    active_registry = _active_registry(registry)
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
            route = build_detached_route(route_for_executor(selected_executor, registry=active_registry))
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
        mode_route = route_for_mode(selected_mode, registry=active_registry)
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
    candidates, match_kind = active_registry.candidate_routes(
        executor_name=selected_executor,
        model_hint=state.route_model_hint,
        executor_family=state.route_executor_family,
        execution_site=state.route_execution_site,
        required_capabilities=state.route_capabilities,
        task_family=task_family,
    )
    if (
        complexity_hint in route_policy_module.ROUTE_STRATEGY_COMPLEXITY_HINTS
        and executor_override is None
        and selected_mode == "auto"
        and configured_executor == DEFAULT_EXECUTOR
    ):
        strategy_candidates, strategy_match_kind = active_registry.candidate_routes(
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
    route = candidates[0] if candidates else route_for_executor(selected_executor, registry=active_registry)
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
            "parallel_intent": complexity_hint in route_policy_module.ROUTE_PARALLEL_INTENT_HINTS,
        },
    )
