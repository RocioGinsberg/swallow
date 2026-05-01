from __future__ import annotations

from pathlib import Path

from swallow.provider_router import (
    completion_gateway,
    route_metadata_store,
    route_policy,
    route_registry,
    route_reports,
    route_selection,
)
from swallow.provider_router import router


def test_router_facade_reexports_module_owners() -> None:
    assert router.RouteRegistry is route_registry.RouteRegistry
    assert router.ROUTE_REGISTRY is route_registry.ROUTE_REGISTRY
    assert router.normalize_route_policy_payload is route_policy.normalize_route_policy_payload
    assert router.normalize_route_registry_payload is route_registry.normalize_route_registry_payload
    assert router.load_default_route_policy is route_policy.load_default_route_policy
    assert router.load_default_route_registry is route_registry.load_default_route_registry
    assert router.invoke_completion is completion_gateway.invoke_completion
    assert router.build_route_registry_report is route_reports.build_route_registry_report
    assert callable(route_metadata_store.route_metadata_snapshot)
    assert callable(router.route_metadata_snapshot)


def test_router_facade_no_longer_owns_extracted_private_implementations() -> None:
    source = Path(router.__file__).read_text(encoding="utf-8")

    assert "class RouteRegistry" not in source
    assert "sqlite_store" not in source
    assert "sqlite3" not in source
    assert "_replace_route_registry_in_sqlite" not in source
    assert "httpx.post" not in source
    assert "resolve_swl_chat_model" not in source
    assert "def build_route_registry_report" not in source
    assert "def invoke_completion" not in source


def test_router_facade_keeps_selection_registry_patch_boundary() -> None:
    source = Path(router.__file__).read_text(encoding="utf-8")

    assert "route_selection_module.select_route(" in source
    assert "registry=ROUTE_REGISTRY" in source
