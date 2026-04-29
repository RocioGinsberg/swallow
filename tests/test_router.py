from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.agent_llm import call_agent_llm
from swallow.models import RouteCapabilities, RouteSpec, TaskState, TaxonomyProfile
from swallow.orchestrator import _resolve_fallback_chain
from swallow.paths import route_capabilities_path, route_fallbacks_path
from swallow.router import (
    RouteRegistry,
    apply_route_fallbacks,
    apply_route_capability_profiles,
    apply_route_weights,
    build_detached_route,
    current_route_capability_profiles,
    current_route_weights,
    lookup_route_by_name,
    normalize_route_name,
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


class _FakeCompletionResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {
            "choices": [{"message": {"content": " routed completion "}}],
            "usage": {"prompt_tokens": 7, "completion_tokens": 11},
            "model": "router-test-model",
        }


class RouteRegistryTest(unittest.TestCase):
    def test_route_for_executor_returns_builtin_aider_route(self) -> None:
        route = route_for_executor("aider")

        self.assertEqual(route.name, "local-aider")
        self.assertEqual(route.fallback_route_name, "local-summary")

    def test_route_for_executor_returns_builtin_codex_route(self) -> None:
        route = route_for_executor("codex")

        self.assertEqual(route.name, "local-codex")
        self.assertEqual(route.executor_name, "codex")
        self.assertEqual(route.fallback_route_name, "local-summary")

    def test_route_for_executor_returns_builtin_http_route(self) -> None:
        route = route_for_executor("http")

        self.assertEqual(route.name, "local-http")
        self.assertEqual(route.backend_kind, "http_api")
        self.assertEqual(route.transport_kind, "http")

    def test_route_for_executor_returns_builtin_claude_code_route(self) -> None:
        route = route_for_executor("claude-code")

        self.assertEqual(route.name, "local-claude-code")
        self.assertEqual(route.fallback_route_name, "local-summary")

    def test_normalize_route_name_keeps_local_codex_stable(self) -> None:
        self.assertEqual(normalize_route_name("local-codex"), "local-codex")
        self.assertEqual(normalize_route_name("local-codex-detached"), "local-codex-detached")

    def test_route_for_mode_supports_http_mode(self) -> None:
        route = route_for_mode("http")

        self.assertIsNotNone(route)
        self.assertEqual(route.name, "local-http")

    def test_builtin_multi_model_http_routes_are_registered(self) -> None:
        self.assertEqual(route_by_name("http-claude").dialect_hint, "claude_xml")
        self.assertEqual(route_by_name("http-qwen").dialect_hint, "plain_text")
        self.assertEqual(route_by_name("http-glm").fallback_route_name, "local-claude-code")
        self.assertEqual(route_by_name("http-gemini").fallback_route_name, "http-qwen")
        self.assertEqual(route_by_name("http-deepseek").dialect_hint, "fim")
        self.assertEqual(route_by_name("local-claude-code").dialect_hint, "plain_text")

    def test_lookup_route_by_name_is_read_only_route_metadata_lookup(self) -> None:
        self.assertIs(lookup_route_by_name("http-claude"), route_by_name("http-claude"))

    def test_call_agent_llm_invokes_router_completion_gateway(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "SWL_API_BASE_URL": "http://gateway.example",
                "SWL_API_KEY": "test-token",
                "AIWF_EXECUTOR_TIMEOUT_SECONDS": "17",
            },
            clear=False,
        ):
            with patch("swallow.router.httpx.post", return_value=_FakeCompletionResponse()) as http_post:
                response = call_agent_llm("hello", system="be terse", model="explicit-model")

        self.assertEqual(response.content, "routed completion")
        self.assertEqual(response.input_tokens, 7)
        self.assertEqual(response.output_tokens, 11)
        self.assertEqual(response.model, "router-test-model")
        http_post.assert_called_once()
        self.assertEqual(http_post.call_args.args[0], "http://gateway.example/v1/chat/completions")
        self.assertEqual(http_post.call_args.kwargs["timeout"], 17)
        self.assertEqual(http_post.call_args.kwargs["headers"]["Authorization"], "Bearer test-token")
        self.assertEqual(http_post.call_args.kwargs["json"]["model"], "explicit-model")
        self.assertEqual(
            http_post.call_args.kwargs["json"]["messages"],
            [
                {"role": "system", "content": "be terse"},
                {"role": "user", "content": "hello"},
            ],
        )

    def test_resolve_fallback_chain_covers_builtin_http_chain(self) -> None:
        chain = _resolve_fallback_chain("http-claude")

        self.assertGreaterEqual(len(chain), 1)
        self.assertEqual(chain[0], "http-claude")
        for current_name, fallback_name in zip(chain, chain[1:]):
            self.assertEqual(route_by_name(current_name).fallback_route_name, fallback_name)
        self.assertFalse(route_by_name(chain[-1]).fallback_route_name)

    def test_route_fallbacks_config_overrides_builtin_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            path = route_fallbacks_path(tmp_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"http-claude": "local-summary"}\n', encoding="utf-8")

            try:
                apply_route_fallbacks(tmp_path)
                self.assertEqual(_resolve_fallback_chain("http-claude"), ("http-claude", "local-summary"))
            finally:
                with tempfile.TemporaryDirectory() as reset_tmp:
                    apply_route_fallbacks(Path(reset_tmp))

    def test_build_detached_route_preserves_fallback_target(self) -> None:
        detached = build_detached_route(route_for_executor("aider"))

        self.assertEqual(detached.name, "local-aider-detached")
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
            executor_name="aider",
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
            executor_name="aider",
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
            executor_name="aider",
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
                    dialect_hint="fim",
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
        self.assertEqual(selection.route.dialect_hint, "fim")
        self.assertIn("model hint", selection.reason)

    def test_select_route_prefers_claude_code_for_high_complexity(self) -> None:
        state = TaskState(
            task_id="complexity-high-001",
            title="High complexity task",
            goal="Prefer claude-code for high complexity work",
            workspace_root="/tmp",
            executor_name="aider",
            route_executor_family="cli",
            route_execution_site="local",
            task_semantics={"complexity_hint": "high"},
        )

        selection = select_route(state)

        self.assertEqual(selection.route.name, "local-claude-code")
        self.assertEqual(selection.policy_inputs["complexity_hint"], "high")

    def test_select_route_prefers_aider_for_low_complexity(self) -> None:
        state = TaskState(
            task_id="complexity-low-001",
            title="Low complexity task",
            goal="Prefer aider for low complexity work",
            workspace_root="/tmp",
            executor_name="aider",
            route_executor_family="cli",
            route_execution_site="local",
            task_semantics={"complexity_hint": "low"},
        )

        selection = select_route(state)

        self.assertEqual(selection.route.name, "local-aider")
        self.assertEqual(selection.policy_inputs["complexity_hint"], "low")
        self.assertFalse(selection.policy_inputs["parallel_intent"])

    def test_select_route_prefers_aider_for_routine_complexity(self) -> None:
        state = TaskState(
            task_id="complexity-routine-001",
            title="Routine task",
            goal="Prefer aider for routine complexity work",
            workspace_root="/tmp",
            executor_name="aider",
            route_executor_family="cli",
            route_execution_site="local",
            task_semantics={"complexity_hint": "routine"},
        )

        selection = select_route(state)

        self.assertEqual(selection.route.name, "local-aider")
        self.assertEqual(selection.policy_inputs["complexity_hint"], "routine")
        self.assertFalse(selection.policy_inputs["parallel_intent"])

    def test_select_route_sets_parallel_intent_for_parallel_complexity(self) -> None:
        state = TaskState(
            task_id="complexity-parallel-001",
            title="Parallelizable task",
            goal="Record fan-out intent without changing executor family",
            workspace_root="/tmp",
            executor_name="http",
            route_executor_family="api",
            route_execution_site="local",
            task_semantics={"complexity_hint": "parallel"},
        )

        selection = select_route(state)

        self.assertTrue(selection.policy_inputs["parallel_intent"])
        self.assertEqual(selection.policy_inputs["complexity_hint"], "parallel")

    def test_select_route_keeps_empty_complexity_hint_visible_in_policy_inputs(self) -> None:
        state = TaskState(
            task_id="complexity-empty-001",
            title="Unannotated task",
            goal="Keep default route behavior when no complexity hint is present",
            workspace_root="/tmp",
            executor_name="aider",
            route_executor_family="cli",
            route_execution_site="local",
            task_semantics={},
        )

        selection = select_route(state)

        self.assertEqual(selection.route.name, "local-aider")
        self.assertEqual(selection.policy_inputs["complexity_hint"], "")
        self.assertFalse(selection.policy_inputs["parallel_intent"])

    def test_select_route_keeps_executor_override_above_complexity_bias(self) -> None:
        state = TaskState(
            task_id="complexity-override-001",
            title="Explicit override",
            goal="Executor override should beat complexity-based routing",
            workspace_root="/tmp",
            executor_name="aider",
            route_executor_family="cli",
            route_execution_site="local",
            task_semantics={"complexity_hint": "high"},
        )

        selection = select_route(state, executor_override="http")

        self.assertEqual(selection.route.executor_name, "http")
        self.assertEqual(selection.policy_inputs["executor_override"], "http")
        self.assertEqual(selection.policy_inputs["complexity_hint"], "high")

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
