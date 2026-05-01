from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from swallow.orchestration.models import RouteCapabilities, RouteSpec, TaskState, TaxonomyProfile
from swallow.provider_router import route_selection
from swallow.provider_router.router import RouteRegistry, select_route


def _route(
    *,
    name: str,
    executor_name: str,
    backend_kind: str,
    fallback_route_name: str = "",
    execution_site: str = "local",
    executor_family: str = "cli",
    execution_kind: str = "artifact_generation",
    supports_tool_loop: bool = False,
) -> RouteSpec:
    return RouteSpec(
        name=name,
        executor_name=executor_name,
        backend_kind=backend_kind,
        model_hint=executor_name,
        fallback_route_name=fallback_route_name,
        executor_family=executor_family,
        execution_site=execution_site,
        remote_capable=execution_site == "remote",
        transport_kind="http" if executor_family == "api" else "local_process",
        capabilities=RouteCapabilities(
            execution_kind=execution_kind,
            supports_tool_loop=supports_tool_loop,
            filesystem_access="workspace_write" if supports_tool_loop else "workspace_read",
            network_access="optional" if supports_tool_loop else "none",
            deterministic=not supports_tool_loop,
            resumable=True,
        ),
        taxonomy=TaxonomyProfile(system_role="general-executor", memory_authority="task-state"),
    )


def test_route_selection_module_matches_router_facade_with_registry_override() -> None:
    registry = RouteRegistry(
        [
            _route(
                name="family-local",
                executor_name="cursor",
                backend_kind="local_cursor",
                execution_kind="code_execution",
                supports_tool_loop=True,
            ),
            _route(name="local-summary", executor_name="local", backend_kind="local_summary"),
        ]
    )
    state = TaskState(
        task_id="selection-module-001",
        title="Selection module",
        goal="Selection module should match router facade registry patch behavior",
        workspace_root="/tmp",
        executor_name="aider",
        route_executor_family="cli",
        route_execution_site="local",
    )

    direct_selection = route_selection.select_route(state, registry=registry)
    with patch("swallow.provider_router.router.ROUTE_REGISTRY", registry):
        facade_selection = select_route(state)

    assert direct_selection.route.name == "family-local"
    assert facade_selection.route.name == direct_selection.route.name
    assert facade_selection.reason == direct_selection.reason


def test_route_selection_module_resolves_detached_routes_and_fallback_chain() -> None:
    registry = RouteRegistry(
        [
            _route(
                name="primary",
                executor_name="primary",
                backend_kind="local_primary",
                fallback_route_name="local-summary",
            ),
            _route(name="local-summary", executor_name="local", backend_kind="local_summary"),
        ]
    )

    detached = route_selection.route_by_name("primary-detached", registry=registry)
    chain = route_selection.resolve_fallback_chain("primary", registry=registry)

    assert detached is not None
    assert detached.name == "primary-detached"
    assert detached.transport_kind == "local_detached_process"
    assert chain == ("primary", "local-summary")


def test_route_selection_module_does_not_import_orchestration_executor() -> None:
    source = Path(route_selection.__file__).read_text(encoding="utf-8")

    assert "swallow.orchestration.executor" not in source
    assert "swallow.knowledge_retrieval.dialect_data" in source
