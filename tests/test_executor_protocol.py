from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import httpx

from swallow.executor import (
    CLIAgentExecutor,
    CLINE_CONFIG,
    CODEX_CONFIG,
    ExecutorProtocol,
    HTTPExecutor,
    LocalCLIExecutor,
    MockExecutor,
    UnknownExecutorError,
    resolve_executor,
    run_executor_inline,
    run_http_executor,
)
from swallow.librarian_executor import LibrarianExecutor
from swallow.models import ExecutorResult, RetrievalItem, TaskCard, TaskState


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


class ExecutorProtocolTest(unittest.TestCase):
    def test_runtime_v0_executors_satisfy_protocol(self) -> None:
        self.assertIsInstance(LocalCLIExecutor(), ExecutorProtocol)
        self.assertIsInstance(MockExecutor(), ExecutorProtocol)
        self.assertIsInstance(HTTPExecutor(), ExecutorProtocol)
        self.assertIsInstance(CLIAgentExecutor(CODEX_CONFIG), ExecutorProtocol)
        self.assertIsInstance(LibrarianExecutor(), ExecutorProtocol)

    def test_resolve_executor_routes_mock_names_to_mock_executor(self) -> None:
        self.assertIsInstance(resolve_executor("cli", "mock"), MockExecutor)
        self.assertIsInstance(resolve_executor("cli", "mock-remote"), MockExecutor)

    def test_resolve_executor_routes_http_and_cli_agent_names(self) -> None:
        self.assertIsInstance(resolve_executor("http", "http"), HTTPExecutor)
        self.assertIsInstance(resolve_executor("cli", "codex"), CLIAgentExecutor)
        self.assertIsInstance(resolve_executor("cli", "cline"), CLIAgentExecutor)

    def test_resolve_executor_keeps_local_summary_paths_on_local_cli_adapter(self) -> None:
        self.assertIsInstance(resolve_executor("cli", "local"), LocalCLIExecutor)
        self.assertIsInstance(resolve_executor("cli", "note-only"), LocalCLIExecutor)

    def test_resolve_executor_routes_librarian_type_to_librarian_executor(self) -> None:
        self.assertIsInstance(resolve_executor("librarian", "local"), LibrarianExecutor)
        self.assertIsInstance(resolve_executor("cli", "librarian"), LibrarianExecutor)

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
            executor_name="codex",
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
            executor_name="codex",
        )
        card = TaskCard(goal=state.goal, parent_task_id=state.task_id)
        expected = ExecutorResult(
            executor_name="codex",
            status="completed",
            message="Delegated.",
            output="ok",
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with patch("swallow.harness.run_execution", return_value=expected) as execution_mock:
                result = CLIAgentExecutor(CODEX_CONFIG).execute(tmp_path, state, card, [])

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

    def test_run_http_executor_includes_authorization_header_when_key_is_configured(self) -> None:
        state = TaskState(
            task_id="task-http-auth",
            title="HTTP auth",
            goal="Forward the configured new-api token",
            workspace_root="/tmp",
            executor_name="http",
            route_name="local-http",
            route_model_hint="claude",
            route_dialect="claude_xml",
        )
        response = _FakeHTTPResponse(
            payload={"choices": [{"message": {"content": "ok"}}]},
        )

        with patch.dict("os.environ", {"AIWF_NEW_API_KEY": "phase46-test-token"}, clear=False):
            with patch("swallow.executor.httpx.post", return_value=response) as http_post:
                run_http_executor(state, [])

        self.assertEqual(http_post.call_args.kwargs["headers"]["Authorization"], "Bearer phase46-test-token")

    def test_run_http_executor_resolves_compatibility_alias_to_default_model(self) -> None:
        state = TaskState(
            task_id="task-http-default-model",
            title="HTTP default model",
            goal="Use the configured default model for the local-http compatibility route",
            workspace_root="/tmp",
            executor_name="http",
            route_name="local-http",
            route_model_hint="http-default",
            route_dialect="plain_text",
        )
        response = _FakeHTTPResponse(
            payload={"choices": [{"message": {"content": "ok"}}]},
        )

        with patch.dict("os.environ", {"AIWF_NEW_API_DEFAULT_MODEL": "deepseek-chat"}, clear=False):
            with patch("swallow.executor.httpx.post", return_value=response) as http_post:
                result = run_http_executor(state, [])

        self.assertEqual(result.status, "completed")
        self.assertEqual(http_post.call_args.kwargs["json"]["model"], "deepseek-chat")

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

    def test_cli_agent_configs_cover_codex_and_cline(self) -> None:
        self.assertEqual(CODEX_CONFIG.executor_name, "codex")
        self.assertEqual(CLINE_CONFIG.executor_name, "cline")


if __name__ == "__main__":
    unittest.main()
