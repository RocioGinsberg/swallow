from __future__ import annotations

from pathlib import Path

from swallow.application.commands.route_metadata import (
    apply_route_policy_command,
    apply_route_registry_command,
    select_route_command,
)
from swallow.orchestration.models import RouteSelection
from swallow.provider_router.router import (
    apply_route_capability_profiles,
    apply_route_fallbacks,
    apply_route_policy,
    apply_route_registry,
    apply_route_weights,
    build_route_policy_report,
    build_route_registry_report,
)
from swallow.application.infrastructure.workspace import resolve_path


def handle_route_command(base_dir: Path, args: object) -> int | None:
    if getattr(args, "command", None) != "route":
        return None

    route_command = getattr(args, "route_command", None)
    if route_command == "registry":
        return _handle_route_registry_command(base_dir, args)
    if route_command == "policy":
        return _handle_route_policy_command(base_dir, args)
    if route_command == "select":
        return _handle_route_select_command(base_dir, args)
    return None


def _handle_route_registry_command(base_dir: Path, args: object) -> int | None:
    route_registry_command = getattr(args, "route_registry_command", None)
    if route_registry_command == "show":
        print(build_route_registry_report(base_dir), end="")
        return 0
    if route_registry_command == "apply":
        apply_route_registry_command(base_dir, resolve_path(getattr(args, "registry_file")))
        print(build_route_registry_report(base_dir), end="")
        return 0
    return None


def _handle_route_policy_command(base_dir: Path, args: object) -> int | None:
    route_policy_command = getattr(args, "route_policy_command", None)
    if route_policy_command == "show":
        print(build_route_policy_report(base_dir), end="")
        return 0
    if route_policy_command == "apply":
        apply_route_policy_command(base_dir, resolve_path(getattr(args, "policy_file")))
        print(build_route_policy_report(base_dir), end="")
        return 0
    return None


def _handle_route_select_command(base_dir: Path, args: object) -> int:
    apply_route_registry(base_dir)
    apply_route_policy(base_dir)
    apply_route_weights(base_dir)
    apply_route_fallbacks(base_dir)
    apply_route_capability_profiles(base_dir)
    result = select_route_command(
        base_dir,
        getattr(args, "task_id"),
        executor=getattr(args, "executor"),
        route_mode=getattr(args, "route_mode"),
    )
    print(
        build_route_selection_report(
            result.task_id,
            result.selection,
            executor_override=result.executor_override,
            route_mode_override=result.route_mode_override,
        ),
        end="",
    )
    return 0


def _format_route_selection_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    normalized = str(value or "").strip()
    return normalized or "none"


def build_route_selection_report(
    task_id: str,
    selection: RouteSelection,
    *,
    executor_override: str = "",
    route_mode_override: str = "",
) -> str:
    lines = [
        "# Route Selection",
        "",
        f"- task_id: {task_id}",
        f"- override_executor: {executor_override or 'none'}",
        f"- override_route_mode: {route_mode_override or 'none'}",
        f"- selected_route: {selection.route.name}",
        f"- executor_name: {selection.route.executor_name}",
        f"- backend_kind: {selection.route.backend_kind}",
        f"- execution_site: {selection.route.execution_site}",
        f"- executor_family: {selection.route.executor_family}",
        f"- transport_kind: {selection.route.transport_kind}",
        f"- model_hint: {selection.route.model_hint or 'none'}",
        f"- dialect: {selection.route.dialect_hint or 'none'}",
        f"- fallback_route: {selection.route.fallback_route_name or 'none'}",
        f"- reason: {selection.reason}",
        f"- capabilities: {selection.route.capabilities.summary()}",
        "",
        "## Policy Inputs",
    ]
    if selection.policy_inputs:
        for key in sorted(selection.policy_inputs):
            lines.append(f"- {key}: {_format_route_selection_value(selection.policy_inputs[key])}")
    else:
        lines.append("- none")
    return "\n".join(lines)
