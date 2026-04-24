from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import patch

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from swallow.executor import build_formatted_executor_prompt, run_executor_inline
from swallow.models import TaskState
from swallow.router import select_route


pytestmark = pytest.mark.eval


MODEL_CASES = {
    "claude": {
        "expected_route": "http-claude",
        "expected_dialect": "claude_xml",
        "expected_prompt_marker": "<swallow_task>",
    },
    "qwen": {
        "expected_route": "http-qwen",
        "expected_dialect": "plain_text",
        "expected_prompt_marker": "You are the executor for a swallow workflow task.",
    },
    "glm": {
        "expected_route": "http-glm",
        "expected_dialect": "plain_text",
        "expected_prompt_marker": "You are the executor for a swallow workflow task.",
    },
    "gemini": {
        "expected_route": "http-gemini",
        "expected_dialect": "plain_text",
        "expected_prompt_marker": "You are the executor for a swallow workflow task.",
    },
    "deepseek": {
        "expected_route": "http-deepseek",
        "expected_dialect": "fim",
        "expected_prompt_marker": "<fim_prefix>",
    },
}


class _EvalHTTPResponse:
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


def _selected_http_state(model_hint: str) -> TaskState:
    requested = TaskState(
        task_id=f"http-eval-{model_hint}",
        title=f"HTTP eval {model_hint}",
        goal="Verify HTTP route and dialect alignment",
        workspace_root="/tmp",
        executor_name="http",
        route_executor_family="api",
        route_execution_site="local",
        route_model_hint=model_hint,
    )
    selection = select_route(requested)
    route = selection.route
    return TaskState(
        task_id=requested.task_id,
        title=requested.title,
        goal=requested.goal,
        workspace_root=requested.workspace_root,
        executor_name=route.executor_name,
        route_name=route.name,
        route_backend=route.backend_kind,
        route_executor_family=route.executor_family,
        route_execution_site=route.execution_site,
        route_model_hint=route.model_hint,
        route_dialect=route.dialect_hint,
        route_capabilities=route.capabilities.to_dict(),
    )


def test_http_executor_eval_route_and_dialect_alignment_matrix() -> None:
    for model_hint, expected in MODEL_CASES.items():
        selected_state = _selected_http_state(model_hint)
        prompt = build_formatted_executor_prompt(selected_state, [])

        assert selected_state.route_name == expected["expected_route"]
        assert selected_state.route_dialect == expected["expected_dialect"]
        assert expected["expected_prompt_marker"] in prompt


def test_http_executor_eval_fallback_matrix_reaches_local_summary_when_live_backends_are_unavailable() -> None:
    selected_state = _selected_http_state("glm")

    with patch("swallow.executor.httpx.post", return_value=_EvalHTTPResponse(status_code=503, text="gateway down")):
        with patch("swallow.executor.shutil.which", return_value=None):
            result = run_executor_inline(selected_state, [])

    assert result.status == "completed"
    assert result.executor_name == "local"
    assert result.degraded is True
    assert result.original_route_name == "http-glm"
    assert result.fallback_route_name == "local-summary"
