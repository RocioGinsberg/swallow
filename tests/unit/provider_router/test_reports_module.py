from __future__ import annotations

from pathlib import Path

from swallow.orchestration.models import RouteCapabilities, RouteSpec, TaxonomyProfile
from swallow.provider_router import route_reports
from swallow.provider_router.router import (
    RouteRegistry,
    build_route_capability_profiles_report,
    build_route_policy_report,
    build_route_registry_report,
    build_route_weights_report,
)
from swallow.surface_tools.paths import route_capabilities_path, route_policy_path, route_registry_path, route_weights_path


def _route(
    *,
    name: str,
    executor_name: str,
    backend_kind: str,
    model_hint: str | None = None,
    dialect_hint: str = "",
    fallback_route_name: str = "local-summary",
    execution_site: str = "local",
    executor_family: str = "cli",
    quality_weight: float = 1.0,
    task_family_scores: dict[str, float] | None = None,
    unsupported_task_types: list[str] | None = None,
) -> RouteSpec:
    return RouteSpec(
        name=name,
        executor_name=executor_name,
        backend_kind=backend_kind,
        model_hint=model_hint or executor_name,
        dialect_hint=dialect_hint,
        fallback_route_name=fallback_route_name,
        quality_weight=quality_weight,
        task_family_scores=dict(task_family_scores or {}),
        unsupported_task_types=list(unsupported_task_types or []),
        executor_family=executor_family,
        execution_site=execution_site,
        remote_capable=execution_site == "remote",
        transport_kind="http" if executor_family == "api" else "local_process",
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
    )


def test_route_reports_module_matches_router_facade_outputs(tmp_path: Path) -> None:
    registry = RouteRegistry(
        [
            _route(
                name="family-local",
                executor_name="cursor",
                backend_kind="local_cursor",
                quality_weight=0.8,
                task_family_scores={"review": 0.9},
                unsupported_task_types=["planning"],
            ),
            _route(
                name="local-summary",
                executor_name="local",
                backend_kind="local_summary",
                fallback_route_name="",
                quality_weight=1.0,
            ),
        ]
    )

    registry_report = route_reports.build_route_registry_report(tmp_path, registry=registry)
    policy_report = route_reports.build_route_policy_report(tmp_path)
    weights_report = route_reports.build_route_weights_report(tmp_path, registry=registry)
    capabilities_report = route_reports.build_route_capability_profiles_report(tmp_path, registry=registry)

    assert registry_report == build_route_registry_report(tmp_path, registry=registry)
    assert policy_report == build_route_policy_report(tmp_path)
    assert weights_report == build_route_weights_report(tmp_path, registry=registry)
    assert capabilities_report == build_route_capability_profiles_report(tmp_path, registry=registry)

    assert f"- path: {route_registry_path(tmp_path)}" in registry_report
    assert f"- path: {route_policy_path(tmp_path)}" in policy_report
    assert f"- path: {route_weights_path(tmp_path)}" in weights_report
    assert f"- path: {route_capabilities_path(tmp_path)}" in capabilities_report
    assert "- family-local" in registry_report
    assert "- family-local: 0.800000" in weights_report
    assert "task_family_scores: review=0.900000" in capabilities_report
    assert "unsupported_task_types: planning" in capabilities_report
