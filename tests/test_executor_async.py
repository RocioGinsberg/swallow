from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.executor import HTTPExecutor, run_http_executor_async
from swallow.models import ExecutorResult, TaskCard, TaskState


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


class _FakeAsyncClient:
    def __init__(self, responses: list[object]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, object]] = []

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def post(self, *args: object, **kwargs: object) -> object:
        self.calls.append({"args": args, "kwargs": kwargs})
        if not self._responses:
            raise AssertionError("No fake async HTTP response configured.")
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _http_state(
    *,
    route_name: str,
    route_model_hint: str,
    route_dialect: str,
) -> TaskState:
    return TaskState(
        task_id=f"task-{route_name}",
        title=f"State for {route_name}",
        goal="Exercise async HTTP route behavior",
        workspace_root="/tmp",
        executor_name="http",
        route_name=route_name,
        route_backend="http_api",
        route_executor_family="api",
        route_execution_site="local",
        route_transport_kind="http",
        route_model_hint=route_model_hint,
        route_dialect=route_dialect,
        route_capabilities={"execution_kind": "artifact_generation", "supports_tool_loop": False},
    )


class ExecutorAsyncProtocolTest(unittest.IsolatedAsyncioTestCase):
    async def test_http_executor_execute_async_delegates_to_harness_run_execution(self) -> None:
        state = TaskState(
            task_id="task-http-async",
            title="HTTP async adapter",
            goal="Delegate through harness asynchronously",
            workspace_root="/tmp",
            executor_name="http",
        )
        card = TaskCard(goal=state.goal, parent_task_id=state.task_id, executor_type="http")
        expected = ExecutorResult(
            executor_name="http",
            status="completed",
            message="Delegated asynchronously.",
            output="ok",
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with patch("swallow.harness.run_execution", return_value=expected) as execution_mock:
                result = await HTTPExecutor().execute_async(tmp_path, state, card, [])

        execution_mock.assert_called_once_with(tmp_path, state, [])
        self.assertEqual(result, expected)

    async def test_run_http_executor_async_parses_openai_compatible_response(self) -> None:
        state = _http_state(
            route_name="local-http",
            route_model_hint="claude",
            route_dialect="claude_xml",
        )
        response = _FakeHTTPResponse(
            payload={
                "choices": [
                    {
                        "message": {
                            "content": "Async gateway response",
                        }
                    }
                ]
            }
        )
        client = _FakeAsyncClient([response])

        with patch("swallow.executor.httpx.AsyncClient", return_value=client):
            result = await run_http_executor_async(state, [])

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.executor_name, "http")
        self.assertEqual(result.output, "Async gateway response")
        self.assertEqual(client.calls[0]["kwargs"]["json"]["model"], "claude")

    async def test_run_http_executor_async_uses_api_usage_when_available(self) -> None:
        state = _http_state(
            route_name="local-http",
            route_model_hint="claude",
            route_dialect="claude_xml",
        )
        client = _FakeAsyncClient(
            [
                _FakeHTTPResponse(
                    payload={
                        "choices": [{"message": {"content": "Async gateway response"}}],
                        "usage": {"prompt_tokens": 210, "completion_tokens": 34},
                    }
                )
            ]
        )

        with patch("swallow.executor.httpx.AsyncClient", return_value=client):
            result = await run_http_executor_async(state, [])

        self.assertEqual(result.estimated_input_tokens, 210)
        self.assertEqual(result.estimated_output_tokens, 34)

    async def test_run_http_executor_async_falls_back_to_next_http_route_after_timeout(self) -> None:
        state = _http_state(
            route_name="http-claude",
            route_model_hint="claude-3-7-sonnet",
            route_dialect="claude_xml",
        )
        primary_client = _FakeAsyncClient([httpx.TimeoutException("slow gateway")])
        fallback_client = _FakeAsyncClient(
            [_FakeHTTPResponse(payload={"choices": [{"message": {"content": "async qwen fallback ok"}}]})]
        )

        with patch("swallow.executor.httpx.AsyncClient", side_effect=[primary_client, fallback_client]):
            result = await run_http_executor_async(state, [])

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.output, "async qwen fallback ok")
        self.assertTrue(result.degraded)
        self.assertEqual(result.original_route_name, "http-claude")
        self.assertEqual(result.fallback_route_name, "http-qwen")
        self.assertEqual(state.route_name, "http-qwen")
        self.assertEqual(state.route_dialect, "plain_text")
        self.assertEqual(primary_client.calls[0]["kwargs"]["json"]["model"], "claude-3-7-sonnet")
        self.assertEqual(fallback_client.calls[0]["kwargs"]["json"]["model"], "qwen2.5-coder-32b-instruct")


if __name__ == "__main__":
    unittest.main()
