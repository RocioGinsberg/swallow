from __future__ import annotations

import os

from .executor import DEFAULT_EXECUTOR, normalize_executor_name
from .models import RouteCapabilities, RouteSelection, RouteSpec, TaskState


BUILTIN_ROUTES: dict[str, RouteSpec] = {
    "local-codex": RouteSpec(
        name="local-codex",
        executor_name="codex",
        backend_kind="local_cli",
        model_hint="codex",
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
    ),
    "local-mock": RouteSpec(
        name="local-mock",
        executor_name="mock",
        backend_kind="deterministic_test",
        model_hint="mock",
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
    ),
    "local-note": RouteSpec(
        name="local-note",
        executor_name="note-only",
        backend_kind="local_fallback",
        model_hint="codex",
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
    ),
    "local-summary": RouteSpec(
        name="local-summary",
        executor_name="local",
        backend_kind="local_summary",
        model_hint="local",
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
    ),
}

ROUTE_MODE_ALIASES = {
    "": "auto",
    "auto": "auto",
    "live": "live",
    "deterministic": "deterministic",
    "offline": "offline",
    "summary": "summary",
}


def normalize_route_mode(raw_mode: str | None) -> str:
    normalized = (raw_mode or "").strip().lower()
    return ROUTE_MODE_ALIASES.get(normalized, "auto")


def route_for_executor(executor_name: str) -> RouteSpec:
    normalized = normalize_executor_name(executor_name)
    mapping = {
        "codex": "local-codex",
        "mock": "local-mock",
        "note-only": "local-note",
        "local": "local-summary",
    }
    return BUILTIN_ROUTES[mapping.get(normalized, "local-codex")]


def route_for_mode(route_mode: str) -> RouteSpec | None:
    mapping = {
        "live": "local-codex",
        "deterministic": "local-mock",
        "offline": "local-note",
        "summary": "local-summary",
    }
    route_name = mapping.get(route_mode)
    return BUILTIN_ROUTES[route_name] if route_name else None


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

    route = route_for_executor(selected_executor)
    return RouteSelection(
        route=route,
        reason=reason,
        policy_inputs={
            "executor_override": executor_override or "",
            "route_mode_override": route_mode_override or "",
            "task_executor": state.executor_name,
            "task_route_mode": state.route_mode,
            "legacy_executor_mode": os.environ.get("AIWF_EXECUTOR_MODE", ""),
        },
    )
