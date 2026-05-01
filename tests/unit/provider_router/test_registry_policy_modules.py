from __future__ import annotations

from swallow.provider_router import route_policy, route_registry
from swallow.provider_router.router import (
    apply_route_policy,
    current_route_policy,
    load_default_route_policy,
    load_default_route_registry,
)


def test_route_policy_module_matches_router_facade_defaults() -> None:
    assert route_policy.load_default_route_policy() == load_default_route_policy()


def test_route_policy_facade_uses_extracted_policy_state(tmp_path) -> None:
    import swallow.provider_router.router as router

    applied = apply_route_policy(tmp_path)

    assert applied == route_policy.current_route_policy()
    assert current_route_policy() == route_policy.current_route_policy()
    assert applied["summary_fallback_route_name"] == "local-summary"
    assert router.SUMMARY_FALLBACK_ROUTE_NAME == "local-summary"


def test_route_registry_module_matches_router_facade_defaults() -> None:
    module_registry = route_registry.load_default_route_registry()
    facade_registry = load_default_route_registry()

    assert module_registry == facade_registry
    assert module_registry["http-claude"]["dialect_hint"] == "claude_xml"
