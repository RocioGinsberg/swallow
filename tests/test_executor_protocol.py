from __future__ import annotations

import tempfile
import unittest
import asyncio
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import httpx

from swallow.executor import (
    AIDER_CONFIG,
    AsyncCLIAgentExecutor,
    CLAUDE_CODE_CONFIG,
    CODEX_CONFIG,
    EXECUTOR_REGISTRY,
    ExecutorProtocol,
    HTTPExecutor,
    LocalCLIExecutor,
    MockExecutor,
    UnknownExecutorError,
    _attach_estimated_usage,
    resolve_executor,
    resolve_new_api_chat_completions_url,
    run_prompt_executor,
    run_prompt_executor_async,
    run_executor_inline,
    run_http_executor,
)
from swallow.consistency_reviewer import ConsistencyReviewerAgent, ConsistencyReviewerExecutor
from swallow.ingestion_specialist import IngestionSpecialistAgent, IngestionSpecialistExecutor
from swallow.librarian_executor import LibrarianAgent, LibrarianExecutor
from swallow.literature_specialist import LiteratureSpecialistAgent, LiteratureSpecialistExecutor
from swallow.meta_optimizer import MetaOptimizerAgent, MetaOptimizerExecutor
from swallow.models import ExecutorResult, RetrievalItem, TaskCard, TaskState
from swallow.orchestrator import _resolve_fallback_chain
from swallow.quality_reviewer import QualityReviewerAgent, QualityReviewerExecutor
from swallow.validator_agent import ValidatorAgent, ValidatorExecutor


class _FakeHTTPResponse:
    def __init__(self, *, status_code: int = 200, payload: dict[str, object] | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://localhost:3000/v1/chat/completions")
            response = httpx.Response(self.status_code, request=request, text=self.text)
            raise httpx.HTTPStatusError("http failure", request=request, response=response)

    def json(self) -> dict[str, object]:
        return dict(self._payload)


def _http_state(
    *,
    route_name: str,
    route_model_hint: str,
    route_dialect: str,
    execution_kind: str = "artifact_generation",
) -> TaskState:
    return TaskState(
        task_id=f"task-{route_name}",
        title=f"State for {route_name}",
        goal="Exercise HTTP route behavior",
        workspace_root="/tmp",
        executor_name="http",
        route_name=route_name,
        route_backend="http_api",
        route_executor_family="api",
        route_execution_site="local",
        route_transport_kind="http",
        route_model_hint=route_model_hint,
        route_dialect=route_dialect,
        route_capabilities={"execution_kind": execution_kind, "supports_tool_loop": False},
        fallback_route_chain=_resolve_fallback_chain(route_name),
    )


class ExecutorProtocolTest(unittest.TestCase):
    def test_runtime_v0_executors_satisfy_protocol(self) -> None:
        self.assertIsInstance(LocalCLIExecutor(), ExecutorProtocol)
        self.assertIsInstance(MockExecutor(), ExecutorProtocol)
        self.assertIsInstance(HTTPExecutor(), ExecutorProtocol)
        self.assertIsInstance(AsyncCLIAgentExecutor(AIDER_CONFIG), ExecutorProtocol)
        self.assertIsInstance(IngestionSpecialistAgent(), ExecutorProtocol)
        self.assertIsInstance(IngestionSpecialistExecutor(), ExecutorProtocol)
        self.assertIsInstance(LibrarianAgent(), ExecutorProtocol)
        self.assertIsInstance(LibrarianExecutor(), ExecutorProtocol)
        self.assertIsInstance(LiteratureSpecialistAgent(), ExecutorProtocol)
        self.assertIsInstance(LiteratureSpecialistExecutor(), ExecutorProtocol)
        self.assertIsInstance(ConsistencyReviewerAgent(), ExecutorProtocol)
        self.assertIsInstance(ConsistencyReviewerExecutor(), ExecutorProtocol)
        self.assertIsInstance(MetaOptimizerAgent(), ExecutorProtocol)
        self.assertIsInstance(MetaOptimizerExecutor(), ExecutorProtocol)
        self.assertIsInstance(QualityReviewerAgent(), ExecutorProtocol)
        self.assertIsInstance(QualityReviewerExecutor(), ExecutorProtocol)
        self.assertIsInstance(ValidatorAgent(), ExecutorProtocol)
        self.assertIsInstance(ValidatorExecutor(), ExecutorProtocol)

    def test_resolve_executor_routes_mock_names_to_mock_executor(self) -> None:
        self.assertIsInstance(resolve_executor("cli", "mock"), MockExecutor)
        self.assertIsInstance(resolve_executor("cli", "mock-remote"), MockExecutor)

    def test_resolve_executor_routes_http_and_cli_agent_names(self) -> None:
        self.assertIsInstance(resolve_executor("http", "http"), HTTPExecutor)
        self.assertIsInstance(resolve_executor("cli", "aider"), AsyncCLIAgentExecutor)
        self.assertIsInstance(resolve_executor("cli", "codex"), AsyncCLIAgentExecutor)
        self.assertIsInstance(resolve_executor("cli", "claude-code"), AsyncCLIAgentExecutor)

    def test_run_prompt_executor_dispatches_codex_to_cli_agent_config(self) -> None:
        state = TaskState(
            task_id="task-codex-inline",
            title="Codex inline dispatch",
            goal="Dispatch codex executor through CODEX_CONFIG",
            workspace_root="/tmp",
            executor_name="codex",
        )
        expected = ExecutorResult(
            executor_name="codex",
            status="completed",
            message="Codex executor completed.",
            output="done",
        )

        with patch("swallow.executor.run_cli_agent_executor", return_value=expected) as cli_mock:
            result = run_prompt_executor(state, [], "prompt")

        cli_mock.assert_called_once()
        self.assertIs(cli_mock.call_args.args[0], CODEX_CONFIG)
        self.assertEqual(result, expected)

    def test_run_prompt_executor_async_dispatches_codex_to_cli_agent_config(self) -> None:
        state = TaskState(
            task_id="task-codex-async",
            title="Codex async dispatch",
            goal="Dispatch codex executor through CODEX_CONFIG",
            workspace_root="/tmp",
            executor_name="codex",
        )
        expected = ExecutorResult(
            executor_name="codex",
            status="completed",
            message="Codex executor completed.",
            output="done",
        )

        async def _run() -> ExecutorResult:
            with patch("swallow.executor.run_cli_agent_executor_async", return_value=expected) as cli_mock:
                result = await run_prompt_executor_async(state, [], "prompt")
            cli_mock.assert_called_once()
            self.assertIs(cli_mock.call_args.args[0], CODEX_CONFIG)
            return result

        result = asyncio.run(_run())
        self.assertEqual(result, expected)

    def test_resolve_executor_keeps_local_summary_paths_on_local_cli_adapter(self) -> None:
        self.assertIsInstance(resolve_executor("cli", "local"), LocalCLIExecutor)
        self.assertIsInstance(resolve_executor("cli", "note-only"), LocalCLIExecutor)

    def test_resolve_executor_routes_librarian_type_to_librarian_executor(self) -> None:
        self.assertIsInstance(resolve_executor("librarian", "local"), LibrarianExecutor)
        self.assertIsInstance(resolve_executor("cli", "librarian"), LibrarianExecutor)

    def test_resolve_executor_routes_meta_optimizer_type_to_meta_optimizer_executor(self) -> None:
        self.assertIsInstance(resolve_executor("meta-optimizer", "local"), MetaOptimizerExecutor)
        self.assertIsInstance(resolve_executor("cli", "meta-optimizer"), MetaOptimizerExecutor)

    def test_executor_registry_contains_all_specialist_and_validator_agents(self) -> None:
        self.assertEqual(
            set(EXECUTOR_REGISTRY),
            {
                "consistency-reviewer",
                "ingestion-specialist",
                "librarian",
                "literature-specialist",
                "meta-optimizer",
                "meta_optimizer",
                "quality-reviewer",
                "validator",
            },
        )

    def test_resolve_executor_routes_phase53_specialist_and_validator_agents(self) -> None:
        self.assertIsInstance(resolve_executor("cli", "ingestion-specialist"), IngestionSpecialistExecutor)
        self.assertIsInstance(resolve_executor("ingestion-specialist", "local"), IngestionSpecialistExecutor)
        self.assertIsInstance(resolve_executor("cli", "literature-specialist"), LiteratureSpecialistExecutor)
        self.assertIsInstance(resolve_executor("literature-specialist", "local"), LiteratureSpecialistExecutor)
        self.assertIsInstance(resolve_executor("cli", "consistency-reviewer"), ConsistencyReviewerExecutor)
        self.assertIsInstance(resolve_executor("consistency-reviewer", "local"), ConsistencyReviewerExecutor)
        self.assertIsInstance(resolve_executor("cli", "quality-reviewer"), QualityReviewerExecutor)
        self.assertIsInstance(resolve_executor("quality-reviewer", "local"), QualityReviewerExecutor)
        self.assertIsInstance(resolve_executor("validator", "local"), ValidatorExecutor)

    def test_local_cli_executor_delegates_to_harness_run_execution(self) -> None:
        state = TaskState(
            task_id="task-local",
            title="Local execution adapter",
            goal="Delegate through harness",
            workspace_root="/tmp",
        )
        card = TaskCard(goal=state.goal, parent_task_id=state.task_id)
        retrieval_items = [
            RetrievalItem(path="README.md", source_type="repo", score=1, preview="planner protocol"),
        ]
        expected = ExecutorResult(
            executor_name="aider",
            status="completed",
            message="Delegated.",
            output="ok",
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with patch("swallow.harness.run_execution", return_value=expected) as execution_mock:
                result = LocalCLIExecutor().execute(tmp_path, state, card, retrieval_items)

        execution_mock.assert_called_once_with(tmp_path, state, retrieval_items)
        self.assertEqual(result, expected)

    def test_http_executor_delegates_to_harness_run_execution(self) -> None:
        state = TaskState(
            task_id="task-http",
            title="HTTP execution adapter",
            goal="Delegate through harness",
            workspace_root="/tmp",
            executor_name="http",
        )
        card = TaskCard(goal=state.goal, parent_task_id=state.task_id, executor_type="http")
        expected = ExecutorResult(
            executor_name="http",
            status="completed",
            message="Delegated.",
            output="ok",
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with patch("swallow.harness.run_execution", return_value=expected) as execution_mock:
                result = HTTPExecutor().execute(tmp_path, state, card, [])

        execution_mock.assert_called_once_with(tmp_path, state, [])
        self.assertEqual(result, expected)

    def test_cli_agent_executor_delegates_to_harness_run_execution(self) -> None:
        state = TaskState(
            task_id="task-cli-agent",
            title="CLI agent execution adapter",
            goal="Delegate through harness",
            workspace_root="/tmp",
            executor_name="aider",
        )
        card = TaskCard(goal=state.goal, parent_task_id=state.task_id)
        expected = ExecutorResult(
            executor_name="aider",
            status="completed",
            message="Delegated.",
            output="ok",
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with patch("swallow.harness.run_execution", return_value=expected) as execution_mock:
                result = AsyncCLIAgentExecutor(AIDER_CONFIG).execute(tmp_path, state, card, [])

        execution_mock.assert_called_once_with(tmp_path, state, [])
        self.assertEqual(result, expected)

    def test_mock_executor_delegates_to_harness_run_execution(self) -> None:
        state = TaskState(
            task_id="task-mock",
            title="Mock execution adapter",
            goal="Delegate mock path through harness",
            workspace_root="/tmp",
        )
        card = TaskCard(goal=state.goal, parent_task_id=state.task_id)
        expected = ExecutorResult(
            executor_name="mock",
            status="completed",
            message="Mock delegated.",
            output="mock-ok",
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with patch("swallow.harness.run_execution", return_value=expected) as execution_mock:
                result = MockExecutor().execute(tmp_path, state, card, [])

        execution_mock.assert_called_once_with(tmp_path, state, [])
        self.assertEqual(result, expected)

    def test_run_http_executor_parses_openai_compatible_response(self) -> None:
        state = TaskState(
            task_id="task-http-inline",
            title="HTTP inline",
            goal="Parse a chat completion response",
            workspace_root="/tmp",
            executor_name="http",
            route_name="local-http",
            route_model_hint="claude",
            route_dialect="claude_xml",
        )
        response = _FakeHTTPResponse(
            payload={
                "choices": [
                    {
                        "message": {
                            "content": "Gateway response",
                        }
                    }
                ]
            }
        )

        with patch("swallow.executor.httpx.post", return_value=response) as http_post:
            result = run_http_executor(state, [])

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.executor_name, "http")
        self.assertEqual(result.output, "Gateway response")
        http_post.assert_called_once()
        self.assertEqual(http_post.call_args.kwargs["json"]["model"], "claude")

    def test_run_http_executor_uses_api_usage_when_available(self) -> None:
        state = _http_state(
            route_name="local-http",
            route_model_hint="claude",
            route_dialect="claude_xml",
        )
        response = _FakeHTTPResponse(
            payload={
                "choices": [{"message": {"content": "Gateway response"}}],
                "usage": {"prompt_tokens": 123, "completion_tokens": 45},
            }
        )

        with patch("swallow.executor.httpx.post", return_value=response):
            result = run_http_executor(state, [])

        self.assertEqual(result.estimated_input_tokens, 123)
        self.assertEqual(result.estimated_output_tokens, 45)

    def test_attach_estimated_usage_skips_when_already_populated(self) -> None:
        result = ExecutorResult(
            executor_name="http",
            status="completed",
            message="done",
            prompt="abcd efgh ijkl",
            output="mnop qrst uvwx",
            estimated_input_tokens=99,
            estimated_output_tokens=33,
        )

        attached = _attach_estimated_usage(result)

        self.assertEqual(attached.estimated_input_tokens, 99)
        self.assertEqual(attached.estimated_output_tokens, 33)

    def test_attach_estimated_usage_falls_back_for_non_http(self) -> None:
        result = ExecutorResult(
            executor_name="mock",
            status="completed",
            message="done",
            prompt="abcd efgh",
            output="ijkl mnop",
        )

        attached = _attach_estimated_usage(result)

        self.assertEqual(attached.estimated_input_tokens, 2)
        self.assertEqual(attached.estimated_output_tokens, 2)

    def test_run_http_executor_includes_authorization_header_when_key_is_configured(self) -> None:
        state = TaskState(
            task_id="task-http-auth",
            title="HTTP auth",
            goal="Forward the configured swl token",
            workspace_root="/tmp",
            executor_name="http",
            route_name="local-http",
            route_model_hint="claude",
            route_dialect="claude_xml",
        )
        response = _FakeHTTPResponse(
            payload={"choices": [{"message": {"content": "ok"}}]},
        )

        with patch.dict("os.environ", {"SWL_API_KEY": "phase56-test-token"}, clear=False):
            with patch("swallow.executor.httpx.post", return_value=response) as http_post:
                run_http_executor(state, [])

        self.assertEqual(http_post.call_args.kwargs["headers"]["Authorization"], "Bearer phase56-test-token")

    def test_run_http_executor_uses_swl_chat_model_when_configured(self) -> None:
        state = _http_state(
            route_name="local-http",
            route_model_hint="http-default",
            route_dialect="plain_text",
        )
        response = _FakeHTTPResponse(
            payload={"choices": [{"message": {"content": "ok"}}]},
        )

        with patch.dict("os.environ", {"SWL_CHAT_MODEL": "google/gemma-4-26b-a4b-it"}, clear=False):
            with patch("swallow.executor.httpx.post", return_value=response) as http_post:
                result = run_http_executor(state, [])

        self.assertEqual(result.status, "completed")
        self.assertEqual(http_post.call_args.kwargs["json"]["model"], "google/gemma-4-26b-a4b-it")

    def test_run_http_executor_defaults_to_gpt_4o_mini_without_swl_chat_model(self) -> None:
        state = _http_state(
            route_name="local-http",
            route_model_hint="http-default",
            route_dialect="plain_text",
        )
        response = _FakeHTTPResponse(payload={"choices": [{"message": {"content": "ok"}}]})

        with patch.dict("os.environ", {"SWL_CHAT_MODEL": ""}, clear=False):
            with patch("swallow.executor.httpx.post", return_value=response) as http_post:
                result = run_http_executor(state, [])

        self.assertEqual(result.status, "completed")
        self.assertEqual(http_post.call_args.kwargs["json"]["model"], "gpt-4o-mini")

    def test_resolve_new_api_chat_completions_url_accepts_swl_base_url_alias(self) -> None:
        with patch.dict("os.environ", {"SWL_API_BASE_URL": "http://localhost:3001"}, clear=False):
            resolved = resolve_new_api_chat_completions_url()

        self.assertEqual(resolved, "http://localhost:3001/v1/chat/completions")

    def test_run_http_executor_falls_back_to_next_http_route_after_timeout(self) -> None:
        state = _http_state(
            route_name="http-claude",
            route_model_hint="claude-3-7-sonnet",
            route_dialect="claude_xml",
        )
        qwen_response = _FakeHTTPResponse(
            payload={"choices": [{"message": {"content": "qwen fallback ok"}}]},
        )

        with patch(
            "swallow.executor.httpx.post",
            side_effect=[httpx.TimeoutException("slow gateway"), qwen_response],
        ) as http_post:
            result = run_http_executor(state, [])

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.output, "qwen fallback ok")
        self.assertTrue(result.degraded)
        self.assertEqual(result.original_route_name, "http-claude")
        self.assertEqual(result.fallback_route_name, "http-qwen")
        self.assertEqual(state.route_name, "http-qwen")
        self.assertEqual(state.route_dialect, "plain_text")
        self.assertEqual(state.fallback_route_chain, _resolve_fallback_chain("http-claude"))
        self.assertEqual(http_post.call_count, 2)
        self.assertEqual(http_post.call_args.kwargs["json"]["model"], "qwen2.5-coder-32b-instruct")

    def test_run_http_executor_keeps_same_route_on_rate_limit(self) -> None:
        state = _http_state(
            route_name="http-claude",
            route_model_hint="claude-3-7-sonnet",
            route_dialect="claude_xml",
        )
        rate_limited = _FakeHTTPResponse(status_code=429, text="rate limited")

        with patch("swallow.executor.httpx.post", return_value=rate_limited) as http_post:
            result = run_http_executor(state, [])

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.failure_kind, "http_rate_limited")
        self.assertFalse(result.degraded)
        self.assertEqual(state.route_name, "http-claude")
        self.assertEqual(http_post.call_count, 1)

    def test_run_executor_inline_falls_back_from_http_to_local_summary_when_cli_fallback_is_unavailable(self) -> None:
        state = _http_state(
            route_name="http-glm",
            route_model_hint="glm-4.5-air",
            route_dialect="plain_text",
        )
        http_failure = _FakeHTTPResponse(status_code=503, text="gateway unavailable")

        with patch("swallow.executor.httpx.post", return_value=http_failure):
            with patch("swallow.executor.shutil.which", return_value=None):
                result = run_executor_inline(state, [])

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.executor_name, "local")
        self.assertTrue(result.degraded)
        self.assertEqual(result.original_route_name, "http-glm")
        self.assertEqual(result.fallback_route_name, "local-summary")
        self.assertEqual(state.route_name, "local-summary")
        self.assertEqual(state.executor_name, "local")
        self.assertEqual(state.route_dialect, "plain_text")
        self.assertEqual(state.fallback_route_chain, _resolve_fallback_chain("http-glm"))
        self.assertIn("Route: local-summary", result.prompt)

    def test_run_executor_inline_raises_for_unknown_executor(self) -> None:
        state = TaskState(
            task_id="task-unknown-inline",
            title="Unknown executor",
            goal="Fail loudly when executor dispatch is unknown",
            workspace_root="/tmp",
            executor_name="unknown-executor",
        )

        with self.assertRaises(UnknownExecutorError):
            run_executor_inline(state, [])

    def test_cli_agent_configs_cover_aider_and_claude_code(self) -> None:
        self.assertEqual(AIDER_CONFIG.executor_name, "aider")
        self.assertEqual(CODEX_CONFIG.executor_name, "codex")
        self.assertEqual(CODEX_CONFIG.fixed_args, ("exec",))
        self.assertEqual(CODEX_CONFIG.output_path_flags, ("-o",))
        self.assertEqual(CLAUDE_CODE_CONFIG.executor_name, "claude-code")


if __name__ == "__main__":
    unittest.main()
