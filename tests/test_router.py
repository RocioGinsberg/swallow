from __future__ import annotations

import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.models import RouteCapabilities, RouteSpec, TaskState, TaxonomyProfile
from swallow.router import RouteRegistry, build_detached_route, route_by_name, route_for_executor, route_for_mode, select_route


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
    execution_kind: str = "artifact_generation",
    supports_tool_loop: bool = False,
) -> RouteSpec:
    return RouteSpec(
        name=name,
        executor_name=executor_name,
        backend_kind=backend_kind,
        model_hint=model_hint or executor_name,
        dialect_hint=dialect_hint,
        fallback_route_name=fallback_route_name,
        executor_family=executor_family,
        execution_site=execution_site,
        remote_capable=execution_site == "remote",
        transport_kind="mock_remote_transport" if execution_site == "remote" else "local_process",
        capabilities=RouteCapabilities(
            execution_kind=execution_kind,
            supports_tool_loop=supports_tool_loop,
            filesystem_access="workspace_write" if supports_tool_loop else "workspace_read",
            network_access="optional" if supports_tool_loop else "none",
            deterministic=not supports_tool_loop,
            resumable=True,
        ),
        taxonomy=TaxonomyProfile(
            system_role="general-executor",
            memory_authority="task-state",
        ),
    )


class RouteRegistryTest(unittest.TestCase):
    def test_route_for_executor_returns_builtin_codex_route(self) -> None:
        route = route_for_executor("codex")

        self.assertEqual(route.name, "local-codex")
        self.assertEqual(route.fallback_route_name, "local-summary")

    def test_route_for_executor_returns_builtin_http_route(self) -> None:
        route = route_for_executor("http")

        self.assertEqual(route.name, "local-http")
        self.assertEqual(route.backend_kind, "http_api")
        self.assertEqual(route.transport_kind, "http")

    def test_route_for_mode_supports_http_mode(self) -> None:
        route = route_for_mode("http")

        self.assertIsNotNone(route)
        self.assertEqual(route.name, "local-http")

    def test_builtin_multi_model_http_routes_are_registered(self) -> None:
        self.assertEqual(route_by_name("http-claude").dialect_hint, "claude_xml")
        self.assertEqual(route_by_name("http-qwen").dialect_hint, "plain_text")
        self.assertEqual(route_by_name("http-glm").fallback_route_name, "local-summary")
        self.assertEqual(route_by_name("http-gemini").fallback_route_name, "http-qwen")
        self.assertEqual(route_by_name("http-deepseek").dialect_hint, "codex_fim")

    def test_build_detached_route_preserves_fallback_target(self) -> None:
        detached = build_detached_route(route_for_executor("codex"))

        self.assertEqual(detached.name, "local-codex-detached")
        self.assertEqual(detached.transport_kind, "local_detached_process")
        self.assertEqual(detached.fallback_route_name, "local-summary")

    def test_select_route_uses_family_site_match_when_exact_executor_missing(self) -> None:
        registry = RouteRegistry(
            [
                _route(
                    name="family-local",
                    executor_name="cursor",
                    backend_kind="local_cursor",
                    execution_kind="code_execution",
                    supports_tool_loop=True,
                ),
                _route(
                    name="local-summary",
                    executor_name="local",
                    backend_kind="local_summary",
                ),
            ]
        )
        state = TaskState(
            task_id="family-site-001",
            title="Family site fallback",
            goal="Prefer family/site when no exact executor exists",
            workspace_root="/tmp",
            executor_name="codex",
            route_executor_family="cli",
            route_execution_site="local",
        )

        with patch("swallow.router.ROUTE_REGISTRY", registry):
            selection = select_route(state)

        self.assertEqual(selection.route.name, "family-local")
        self.assertIn("executor family and execution site", selection.reason)

    def test_select_route_uses_capability_match_when_family_site_is_missing(self) -> None:
        registry = RouteRegistry(
            [
                _route(
                    name="capability-match",
                    executor_name="cursor-remote",
                    backend_kind="remote_cursor",
                    execution_site="remote",
                    executor_family="api",
                    execution_kind="code_execution",
                    supports_tool_loop=True,
                ),
                _route(
                    name="local-summary",
                    executor_name="local",
                    backend_kind="local_summary",
                ),
            ]
        )
        state = TaskState(
            task_id="capability-001",
            title="Capability fallback",
            goal="Prefer capability tier when family/site is unavailable",
            workspace_root="/tmp",
            executor_name="codex",
            route_executor_family="cli",
            route_execution_site="local",
            route_capabilities={
                "execution_kind": "code_execution",
                "supports_tool_loop": True,
                "filesystem_access": "workspace_write",
                "network_access": "optional",
                "deterministic": False,
                "resumable": True,
            },
        )

        with patch("swallow.router.ROUTE_REGISTRY", registry):
            selection = select_route(state)

        self.assertEqual(selection.route.name, "capability-match")
        self.assertIn("matched route capabilities", selection.reason)

    def test_select_route_uses_summary_route_when_registry_has_no_match(self) -> None:
        registry = RouteRegistry(
            [
                _route(
                    name="remote-only",
                    executor_name="cursor-remote",
                    backend_kind="remote_cursor",
                    execution_site="remote",
                    executor_family="api",
                ),
                _route(
                    name="local-summary",
                    executor_name="local",
                    backend_kind="local_summary",
                ),
            ]
        )
        state = TaskState(
            task_id="summary-fallback-001",
            title="Summary fallback",
            goal="Use final local summary fallback when nothing matches",
            workspace_root="/tmp",
            executor_name="codex",
            route_executor_family="api",
            route_execution_site="local",
            route_capabilities={"execution_kind": "code_execution"},
        )

        with patch("swallow.router.ROUTE_REGISTRY", registry):
            selection = select_route(state)

        self.assertEqual(selection.route.name, "local-summary")
        self.assertIn("local summary fallback", selection.reason)

    def test_select_route_prefers_http_route_matching_model_hint(self) -> None:
        registry = RouteRegistry(
            [
                _route(
                    name="local-http",
                    executor_name="http",
                    backend_kind="http_api",
                    model_hint="http-default",
                    dialect_hint="plain_text",
                    execution_site="local",
                    executor_family="api",
                ),
                _route(
                    name="http-claude",
                    executor_name="http",
                    backend_kind="http_api",
                    model_hint="claude-3-7-sonnet",
                    dialect_hint="claude_xml",
                    fallback_route_name="http-qwen",
                    execution_site="local",
                    executor_family="api",
                ),
                _route(
                    name="http-deepseek",
                    executor_name="http",
                    backend_kind="http_api",
                    model_hint="deepseek-chat",
                    dialect_hint="codex_fim",
                    fallback_route_name="http-qwen",
                    execution_site="local",
                    executor_family="api",
                    execution_kind="code_execution",
                ),
                _route(
                    name="local-summary",
                    executor_name="local",
                    backend_kind="local_summary",
                ),
            ]
        )
        state = TaskState(
            task_id="http-model-match-001",
            title="HTTP model selection",
            goal="Route HTTP executor by logical model hint",
            workspace_root="/tmp",
            executor_name="http",
            route_executor_family="api",
            route_execution_site="local",
            route_model_hint="deepseek",
        )

        with patch("swallow.router.ROUTE_REGISTRY", registry):
            selection = select_route(state)

        self.assertEqual(selection.route.name, "http-deepseek")
        self.assertEqual(selection.route.dialect_hint, "codex_fim")
        self.assertIn("model hint", selection.reason)


if __name__ == "__main__":
    unittest.main()
