from __future__ import annotations

import asyncio
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from unittest.mock import patch

from swallow.orchestration.models import ExecutorResult, TaskCard, TaskState
from swallow.orchestration.review_gate import run_review_gate_async


def _review_state() -> TaskState:
    return TaskState(
        task_id="task-review-async",
        title="Review task async",
        goal="Review the latest executor output",
        workspace_root="/tmp/workspace",
        executor_name="http",
        route_name="local-http",
        route_backend="http_api",
        route_executor_family="api",
        route_execution_site="local",
        route_transport_kind="http",
        route_model_hint="deepseek-chat",
        route_dialect="plain_text",
    )


class AsyncReviewGateTest(unittest.IsolatedAsyncioTestCase):
    async def test_run_review_gate_async_fans_out_reviewers_concurrently(self) -> None:
        state = _review_state()
        card = TaskCard(
            goal="Review output",
            parent_task_id=state.task_id,
            reviewer_routes=["http-claude", "http-qwen", "http-gemini"],
            consensus_policy="majority",
        )
        all_started = asyncio.Event()
        started_routes: list[str] = []

        async def fake_run_prompt_executor_async(reviewer_state: TaskState, _items: list[object], _prompt: str) -> ExecutorResult:
            started_routes.append(reviewer_state.topology_route_name or reviewer_state.route_name)
            if len(started_routes) == 3:
                all_started.set()
            await all_started.wait()
            return ExecutorResult(
                executor_name="http",
                status="completed",
                message="review ok",
                output='{"status":"passed","message":"approved","checks":[{"name":"goal_alignment","passed":true,"detail":"goal met"}]}',
            )

        with patch("swallow.orchestration.review_gate.run_prompt_executor_async", side_effect=fake_run_prompt_executor_async):
            result = await asyncio.wait_for(
                run_review_gate_async(
                    state,
                    ExecutorResult(
                        executor_name="local",
                        status="completed",
                        message="ok",
                        output="candidate output",
                    ),
                    card,
                ),
                timeout=0.5,
            )

        self.assertEqual(result.status, "passed")
        self.assertCountEqual(started_routes, ["http-claude", "http-qwen", "http-gemini"])

    async def test_run_review_gate_async_marks_timed_out_reviewer_failed_without_blocking_others(self) -> None:
        state = _review_state()
        card = TaskCard(
            goal="Review output",
            parent_task_id=state.task_id,
            reviewer_routes=["http-claude", "http-qwen", "http-gemini"],
            consensus_policy="majority",
            reviewer_timeout_seconds=1,
        )

        async def fake_run_prompt_executor_async(reviewer_state: TaskState, _items: list[object], _prompt: str) -> ExecutorResult:
            route_name = reviewer_state.topology_route_name or reviewer_state.route_name
            if route_name == "http-claude":
                await asyncio.sleep(1.5)
            return ExecutorResult(
                executor_name="http",
                status="completed",
                message="review ok",
                output='{"status":"passed","message":"approved","checks":[{"name":"goal_alignment","passed":true,"detail":"goal met"}]}',
            )

        with patch("swallow.orchestration.review_gate.run_prompt_executor_async", side_effect=fake_run_prompt_executor_async):
            result = await run_review_gate_async(
                state,
                ExecutorResult(
                    executor_name="local",
                    status="completed",
                    message="ok",
                    output="candidate output",
                ),
                card,
            )

        self.assertEqual(result.status, "passed")
        timed_out_check = next(check for check in result.checks if check["name"] == "reviewer_route:http-claude")
        self.assertFalse(timed_out_check["passed"])
        self.assertIn("timed out", timed_out_check["detail"])
        consensus_check = next(check for check in result.checks if check["name"] == "consensus_policy")
        self.assertTrue(consensus_check["passed"])


if __name__ == "__main__":
    unittest.main()
