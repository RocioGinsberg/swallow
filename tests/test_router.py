from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.models import RouteCapabilities, RouteSpec, TaskState, TaxonomyProfile
from swallow.paths import route_capabilities_path
from swallow.router import (
    RouteRegistry,
    apply_route_capability_profiles,
    apply_route_weights,
    build_detached_route,
    current_route_capability_profiles,
    current_route_weights,
    route_by_name,
    route_for_executor,
    route_for_mode,
    save_route_capability_profiles,
    save_route_weights,
    select_route,
)


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
        task_family_scores=dict(task_family_scores or {}),
        unsupported_task_types=list(unsupported_task_types or []),
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

    def test_route_for_executor_returns_builtin_cline_route(self) -> None:
        route = route_for_executor("cline")

        self.assertEqual(route.name, "local-cline")
        self.assertEqual(route.fallback_route_name, "local-summary")

    def test_route_for_mode_supports_http_mode(self) -> None:
        route = route_for_mode("http")

        self.assertIsNotNone(route)
        self.assertEqual(route.name, "local-http")

    def test_builtin_multi_model_http_routes_are_registered(self) -> None:
        self.assertEqual(route_by_name("http-claude").dialect_hint, "claude_xml")
        self.assertEqual(route_by_name("http-qwen").dialect_hint, "plain_text")
        self.assertEqual(route_by_name("http-glm").fallback_route_name, "local-cline")
        self.assertEqual(route_by_name("http-gemini").fallback_route_name, "http-qwen")
        self.assertEqual(route_by_name("http-deepseek").dialect_hint, "codex_fim")
        self.assertEqual(route_by_name("local-cline").dialect_hint, "plain_text")

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

    def test_candidate_routes_prioritizes_higher_quality_weight(self) -> None:
        registry = RouteRegistry(
            [
                _route(
                    name="http-low",
                    executor_name="http",
                    backend_kind="http_api",
                    execution_site="local",
                    executor_family="api",
                ),
                _route(
                    name="http-high",
                    executor_name="http",
                    backend_kind="http_api",
                    execution_site="local",
                    executor_family="api",
                ),
            ]
        )
        registry.get("http-low").quality_weight = 0.4
        registry.get("http-high").quality_weight = 1.0

        candidates, match_kind = registry.candidate_routes(executor_name="http")

        self.assertEqual(match_kind, "exact_executor")
        self.assertEqual([route.name for route in candidates], ["http-high", "http-low"])

    def test_candidate_routes_prioritizes_higher_task_family_score(self) -> None:
        registry = RouteRegistry(
            [
                _route(
                    name="http-review-low",
                    executor_name="http",
                    backend_kind="http_api",
                    execution_site="local",
                    executor_family="api",
                    task_family_scores={"review": 0.2},
                ),
                _route(
                    name="http-review-high",
                    executor_name="http",
                    backend_kind="http_api",
                    execution_site="local",
                    executor_family="api",
                    task_family_scores={"review": 0.9},
                ),
            ]
        )

        candidates, match_kind = registry.candidate_routes(executor_name="http", task_family="review")

        self.assertEqual(match_kind, "exact_executor")
        self.assertEqual([route.name for route in candidates], ["http-review-high", "http-review-low"])

    def test_select_route_skips_routes_marked_unsupported_for_task_family(self) -> None:
        registry = RouteRegistry(
            [
                _route(
                    name="http-review-blocked",
                    executor_name="http",
                    backend_kind="http_api",
                    execution_site="local",
                    executor_family="api",
                    unsupported_task_types=["review"],
                ),
                _route(
                    name="http-review-ok",
                    executor_name="http",
                    backend_kind="http_api",
                    execution_site="local",
                    executor_family="api",
                    task_family_scores={"review": 0.4},
                ),
                _route(
                    name="local-summary",
                    executor_name="local",
                    backend_kind="local_summary",
                ),
            ]
        )
        state = TaskState(
            task_id="unsupported-review-001",
            title="Review route guard",
            goal="Avoid routes that explicitly do not support review work",
            workspace_root="/tmp",
            executor_name="http",
            route_executor_family="api",
            route_execution_site="local",
            task_semantics={"source_kind": "review"},
        )

        with patch("swallow.router.ROUTE_REGISTRY", registry):
            selection = select_route(state)

        self.assertEqual(selection.route.name, "http-review-ok")

    def test_apply_route_capability_profiles_loads_persisted_values_for_registry(self) -> None:
        registry = RouteRegistry(
            [
                _route(
                    name="http-claude",
                    executor_name="http",
                    backend_kind="http_api",
                    execution_site="local",
                    executor_family="api",
                ),
                _route(
                    name="local-summary",
                    executor_name="local",
                    backend_kind="local_summary",
                ),
            ]
        )

        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            save_route_capability_profiles(
                base_dir,
                {
                    "http-claude": {
                        "task_family_scores": {"review": 0.85},
                        "unsupported_task_types": ["execution"],
                    }
                },
            )

            applied = apply_route_capability_profiles(base_dir, registry)
            current = current_route_capability_profiles(registry)

        self.assertEqual(applied["http-claude"]["task_family_scores"]["review"], 0.85)
        self.assertEqual(current["http-claude"]["unsupported_task_types"], ["execution"])
        self.assertTrue(route_capabilities_path(base_dir).name.endswith("route_capabilities.json"))

    def test_apply_route_weights_loads_persisted_values_for_registry(self) -> None:
        registry = RouteRegistry(
            [
                _route(
                    name="http-claude",
                    executor_name="http",
                    backend_kind="http_api",
                    execution_site="local",
                    executor_family="api",
                ),
                _route(
                    name="local-summary",
                    executor_name="local",
                    backend_kind="local_summary",
                ),
            ]
        )

        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            save_route_weights(
                base_dir,
                {
                    "http-claude": 0.55,
                },
            )

            applied = apply_route_weights(base_dir, registry)
            current = current_route_weights(registry)

        self.assertEqual(applied["http-claude"], 0.55)
        self.assertEqual(current["http-claude"], 0.55)
        self.assertEqual(current["local-summary"], 1.0)


if __name__ == "__main__":
    unittest.main()
