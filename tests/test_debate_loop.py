from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.models import Event, ExecutorResult, ValidationResult
from swallow.orchestrator import create_task, run_task
from swallow.store import append_event


def _load_json_lines(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []

    records: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _passing_validation_tuple() -> tuple[ValidationResult, ...]:
    return (
        ValidationResult(status="passed", message="Compatibility passed."),
        ValidationResult(status="passed", message="Execution fit passed."),
        ValidationResult(status="passed", message="Knowledge policy passed."),
        ValidationResult(status="passed", message="Validation passed."),
        ValidationResult(status="passed", message="Retry policy passed."),
        ValidationResult(status="warning", message="Stop policy warning."),
        ValidationResult(status="passed", message="Execution budget policy passed."),
    )


class DebateLoopTest(unittest.TestCase):
    def test_run_task_retries_single_task_with_review_feedback_and_completes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            created = create_task(
                base_dir=tmp_path,
                title="Debate loop retry",
                goal="Retry once after a failed review gate result",
                workspace_root=tmp_path,
                executor_name="local",
            )
            task_dir = tmp_path / ".swl" / "tasks" / created.task_id
            artifacts_dir = task_dir / "artifacts"
            prompts: list[str] = []
            call_count = 0

            def run_local(_state: object, _retrieval_items: list[object], prompt: str) -> ExecutorResult:
                nonlocal call_count
                call_count += 1
                prompts.append(prompt)
                return ExecutorResult(
                    executor_name="local",
                    status="completed",
                    message=f"attempt {call_count}",
                    output="" if call_count == 1 else "resolved output",
                    prompt=prompt,
                    dialect="plain_text",
                )

            with patch("swallow.orchestrator.run_retrieval", return_value=[]):
                with patch("swallow.orchestrator.write_task_artifacts", return_value=_passing_validation_tuple()):
                    with patch("swallow.executor.run_local_executor", side_effect=run_local):
                        final_state = run_task(tmp_path, created.task_id, executor_name="local")

            events = _load_json_lines(task_dir / "events.jsonl")
            debate_event = next(event for event in events if event["event_type"] == "task.debate_round")
            review_gate_event = next(event for event in events if event["event_type"] == "task.review_gate")
            executor_events = [event for event in events if event["event_type"] == "executor.completed"]
            feedback_payload = json.loads((artifacts_dir / "review_feedback_round_1.json").read_text(encoding="utf-8"))

        self.assertEqual(final_state.status, "completed")
        self.assertEqual(call_count, 2)
        self.assertEqual(final_state.review_feedback_ref, "")
        self.assertNotIn("## Review Feedback", prompts[0])
        self.assertIn("## Review Feedback (Round 1)", prompts[1])
        self.assertIn("Return a non-empty output payload that directly addresses the task goal.", prompts[1])
        self.assertEqual(feedback_payload["round_number"], 1)
        self.assertEqual(debate_event["payload"]["round_number"], 1)
        self.assertTrue(debate_event["payload"]["retry_scheduled"])
        self.assertEqual(review_gate_event["payload"]["status"], "passed")
        self.assertEqual(len(executor_events), 2)
        self.assertEqual(executor_events[1]["payload"]["review_feedback"], feedback_payload and debate_event["payload"]["feedback_ref"])

    def test_run_task_trips_debate_circuit_breaker_after_three_retries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            created = create_task(
                base_dir=tmp_path,
                title="Debate loop exhausted",
                goal="Escalate to human after repeated review failures",
                workspace_root=tmp_path,
                executor_name="local",
            )
            task_dir = tmp_path / ".swl" / "tasks" / created.task_id
            artifacts_dir = task_dir / "artifacts"
            prompts: list[str] = []

            def run_local(_state: object, _retrieval_items: list[object], prompt: str) -> ExecutorResult:
                prompts.append(prompt)
                return ExecutorResult(
                    executor_name="local",
                    status="completed",
                    message="still empty",
                    output="",
                    prompt=prompt,
                    dialect="plain_text",
                )

            with patch("swallow.orchestrator.run_retrieval", return_value=[]):
                with patch("swallow.orchestrator.write_task_artifacts", return_value=_passing_validation_tuple()):
                    with patch("swallow.executor.run_local_executor", side_effect=run_local):
                        final_state = run_task(tmp_path, created.task_id, executor_name="local")

            events = _load_json_lines(task_dir / "events.jsonl")
            debate_events = [event for event in events if event["event_type"] == "task.debate_round"]
            breaker_event = next(event for event in events if event["event_type"] == "task.debate_circuit_breaker")
            waiting_event = next(event for event in events if event["event_type"] == "task.waiting_human")
            review_gate_event = next(event for event in events if event["event_type"] == "task.review_gate")
            feedback_round_3 = json.loads((artifacts_dir / "review_feedback_round_3.json").read_text(encoding="utf-8"))
            debate_exhausted = json.loads((artifacts_dir / "debate_exhausted.json").read_text(encoding="utf-8"))

        self.assertEqual(final_state.status, "waiting_human")
        self.assertEqual(final_state.phase, "waiting_human")
        self.assertEqual(final_state.execution_lifecycle, "waiting_human")
        self.assertEqual(len(prompts), 4)
        self.assertIn("## Review Feedback (Round 3)", prompts[3])
        self.assertEqual(len(debate_events), 3)
        self.assertEqual([event["payload"]["round_number"] for event in debate_events], [1, 2, 3])
        self.assertEqual(review_gate_event["payload"]["status"], "failed")
        self.assertEqual(feedback_round_3["round_number"], 3)
        self.assertEqual(len(debate_exhausted["feedback_refs"]), 3)
        self.assertEqual(breaker_event["payload"]["max_rounds"], 3)
        self.assertEqual(waiting_event["payload"]["status"], "waiting_human")
        self.assertFalse(any(event["event_type"] in {"task.completed", "task.failed"} for event in events))

    def test_run_task_uses_consensus_review_gate_when_task_card_requests_reviewers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            created = create_task(
                base_dir=tmp_path,
                title="Consensus debate loop",
                goal="Require reviewer consensus before passing",
                workspace_root=tmp_path,
                executor_name="local",
                reviewer_routes=["http-claude", "http-qwen"],
                consensus_policy="majority",
            )
            task_dir = tmp_path / ".swl" / "tasks" / created.task_id

            reviewer_outputs = [
                ExecutorResult(
                    executor_name="http",
                    status="completed",
                    message="review ok",
                    output='{"status":"passed","message":"approved","checks":[{"name":"goal_alignment","passed":true,"detail":"goal met"}]}',
                ),
                ExecutorResult(
                    executor_name="http",
                    status="completed",
                    message="review ok",
                    output='{"status":"passed","message":"approved","checks":[{"name":"material_risk","passed":true,"detail":"risk acceptable"}]}',
                ),
            ]

            with patch("swallow.orchestrator.run_retrieval", return_value=[]):
                with patch("swallow.orchestrator.write_task_artifacts", return_value=_passing_validation_tuple()):
                    with patch(
                        "swallow.executor.run_local_executor",
                        return_value=ExecutorResult(
                            executor_name="local",
                            status="completed",
                            message="ok",
                            output="candidate output",
                            prompt="prompt",
                            dialect="plain_text",
                        ),
                    ):
                        with patch("swallow.review_gate.run_prompt_executor_async", new=AsyncMock(side_effect=reviewer_outputs)):
                            final_state = run_task(tmp_path, created.task_id, executor_name="local")

            events = _load_json_lines(task_dir / "events.jsonl")
            review_gate_event = next(event for event in events if event["event_type"] == "task.review_gate")
            planned_event = next(event for event in events if event["event_type"] == "task.planned")

        self.assertEqual(final_state.status, "completed")
        self.assertEqual(planned_event["payload"]["reviewer_routes"], ["http-claude", "http-qwen"])
        self.assertEqual(planned_event["payload"]["consensus_policy"], "majority")
        self.assertEqual(review_gate_event["payload"]["status"], "passed")
        self.assertEqual(review_gate_event["payload"]["reviewer_routes"], ["http-claude", "http-qwen"])

    def test_run_task_waits_for_human_when_token_cost_budget_is_exhausted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            created = create_task(
                base_dir=tmp_path,
                title="Budget exhausted",
                goal="Stop before execution when token cost budget is already spent",
                workspace_root=tmp_path,
                executor_name="local",
                token_cost_limit=0.05,
            )
            task_dir = tmp_path / ".swl" / "tasks" / created.task_id

            append_event(
                tmp_path,
                Event(
                    task_id=created.task_id,
                    event_type="executor.completed",
                    message="prior execution cost",
                    payload={"token_cost": 0.10},
                ),
            )
            append_event(
                tmp_path,
                Event(
                    task_id=created.task_id,
                    event_type="task.execution_fallback",
                    message="fallback cost should not be double-counted",
                    payload={"token_cost": 9.99},
                ),
            )

            with patch("swallow.orchestrator.run_retrieval", return_value=[]):
                with patch("swallow.orchestrator.write_task_artifacts", return_value=_passing_validation_tuple()):
                    with patch(
                        "swallow.executor.run_local_executor",
                        side_effect=AssertionError("executor should not run when budget is exhausted"),
                    ):
                        final_state = run_task(tmp_path, created.task_id, executor_name="local")

            events = _load_json_lines(task_dir / "events.jsonl")
            budget_event = next(event for event in events if event["event_type"] == "task.budget_exhausted")
            waiting_event = next(event for event in events if event["event_type"] == "task.waiting_human")
            review_gate_event = next(event for event in events if event["event_type"] == "task.review_gate")

        self.assertEqual(final_state.status, "waiting_human")
        self.assertEqual(final_state.phase, "waiting_human")
        self.assertEqual(final_state.execution_lifecycle, "waiting_human")
        self.assertEqual(waiting_event["payload"]["waiting_reason"], "budget_exhausted")
        self.assertEqual(waiting_event["payload"]["failure_kind"], "budget_exhausted")
        self.assertEqual(review_gate_event["payload"]["status"], "failed")
        self.assertEqual(review_gate_event["payload"]["token_cost_limit"], 0.05)
        self.assertEqual(review_gate_event["payload"]["checks"][0]["name"], "token_cost_budget")
        self.assertAlmostEqual(budget_event["payload"]["current_token_cost"], 0.10)
        self.assertAlmostEqual(budget_event["payload"]["token_cost_limit"], 0.05)
        self.assertFalse(any(event["event_type"] == "task.debate_round" for event in events))
        self.assertFalse(any(event["event_type"] in {"task.completed", "task.failed"} for event in events))


if __name__ == "__main__":
    unittest.main()
