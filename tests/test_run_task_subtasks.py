from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.orchestration.models import Event, ExecutorResult, ValidationResult
from swallow.orchestration.orchestrator import create_task, run_task
from swallow.truth_governance.store import write_artifact
from swallow.truth_governance.store import append_event


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


class RunTaskSubtaskIntegrationTest(unittest.TestCase):
    def test_run_task_retries_only_failed_subtask_and_completes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            created = create_task(
                base_dir=tmp_path,
                title="Multi-card review retry",
                goal="Execute two subtasks with one targeted retry",
                workspace_root=tmp_path,
                executor_name="local",
                next_action_proposals=[
                    "Prepare changes",
                    "Verify results",
                ],
            )
            task_dir = tmp_path / ".swl" / "tasks" / created.task_id
            artifacts_dir = task_dir / "artifacts"
            attempts: dict[int, int] = {}

            def execute_card(
                _base_dir: Path,
                _state: object,
                card: object,
                _retrieval_items: list[object],
            ) -> ExecutorResult:
                subtask_index = int(card.subtask_index)
                attempts[subtask_index] = attempts.get(subtask_index, 0) + 1
                attempt_number = attempts[subtask_index]
                should_fail_review = subtask_index == 2 and attempt_number == 1
                write_artifact(
                    _base_dir,
                    str(_state.task_id),
                    "custom_trace.md",
                    f"subtask {subtask_index} attempt {attempt_number} trace",
                )
                return ExecutorResult(
                    executor_name="local",
                    status="completed",
                    message=f"subtask {subtask_index} attempt {attempt_number}",
                    output=""
                    if should_fail_review
                    else f"subtask {subtask_index} completed on attempt {attempt_number}",
                    prompt=f"execute subtask {subtask_index}",
                    dialect="plain_text",
                )

            with patch("swallow.orchestration.orchestrator.run_retrieval", return_value=[]):
                with patch("swallow.orchestration.orchestrator._execute_task_card", side_effect=execute_card):
                    with patch(
                        "swallow.orchestration.orchestrator.write_task_artifacts",
                        return_value=_passing_validation_tuple(),
                    ):
                        final_state = run_task(tmp_path, created.task_id, executor_name="local")

            events = _load_json_lines(task_dir / "events.jsonl")
            planned_event = next(event for event in events if event["event_type"] == "task.planned")
            review_gate_event = next(event for event in events if event["event_type"] == "task.review_gate")
            executor_event = next(event for event in events if event["event_type"] == "executor.completed")
            debate_event = next(event for event in events if event["event_type"] == "subtask.2.debate_round")
            subtask2_review_events = [
                event for event in events if event["event_type"] == "subtask.2.review_gate"
            ]
            feedback_round_1 = json.loads(
                (artifacts_dir / "subtask_2_review_feedback_round_1.json").read_text(encoding="utf-8")
            )
            subtask2_attempt1_review = json.loads(
                (artifacts_dir / "subtask_2_attempt1_review_gate.json").read_text(encoding="utf-8")
            )
            subtask2_attempt2_review = json.loads(
                (artifacts_dir / "subtask_2_attempt2_review_gate.json").read_text(encoding="utf-8")
            )
            self.assertEqual(final_state.status, "completed")
            self.assertEqual(final_state.executor_name, "subtask-orchestrator")
            self.assertEqual(final_state.executor_status, "completed")
            self.assertEqual(attempts, {1: 1, 2: 2})
            self.assertEqual(planned_event["payload"]["card_count"], 2)
            self.assertEqual(planned_event["payload"]["subtask_indices"], [1, 2])
            self.assertEqual(review_gate_event["payload"]["status"], "passed")
            self.assertEqual(review_gate_event["payload"]["failed_card_ids"], [])
            self.assertEqual(executor_event["payload"]["executor_name"], "subtask-orchestrator")
            self.assertEqual(debate_event["payload"]["round_number"], 1)
            self.assertEqual(debate_event["payload"]["attempt_number"], 2)
            self.assertTrue(debate_event["payload"]["retry_scheduled"])
            self.assertEqual(len(subtask2_review_events), 2)
            self.assertEqual(subtask2_review_events[0]["payload"]["status"], "failed")
            self.assertEqual(subtask2_review_events[1]["payload"]["status"], "passed")
            self.assertEqual(feedback_round_1["round_number"], 1)
            self.assertEqual(subtask2_attempt1_review["status"], "failed")
            self.assertEqual(subtask2_attempt2_review["status"], "passed")
            self.assertTrue((artifacts_dir / "executor_output.md").exists())
            self.assertTrue((artifacts_dir / "subtask_1_attempt1_executor_output.md").exists())
            self.assertTrue((artifacts_dir / "subtask_2_attempt1_executor_output.md").exists())
            self.assertTrue((artifacts_dir / "subtask_2_attempt2_executor_output.md").exists())
            self.assertTrue((artifacts_dir / "subtask_summary.md").exists())
            self.assertEqual(
                (artifacts_dir / "subtask_1_attempt1_custom_trace.md").read_text(encoding="utf-8").strip(),
                "subtask 1 attempt 1 trace",
            )
            self.assertEqual(
                (artifacts_dir / "subtask_2_attempt2_custom_trace.md").read_text(encoding="utf-8").strip(),
                "subtask 2 attempt 2 trace",
            )
            self.assertIn(
                "# Subtask Orchestrator Result",
                (artifacts_dir / "executor_output.md").read_text(encoding="utf-8"),
            )
            self.assertIn(
                ".swl/tasks/"
                f"{created.task_id}"
                "/artifacts/subtask_1_attempt1_executor_output.md",
                (artifacts_dir / "subtask_summary.md").read_text(encoding="utf-8"),
            )
            self.assertIn(
                ".swl/tasks/"
                f"{created.task_id}"
                "/artifacts/subtask_2_attempt2_custom_trace.md",
                (artifacts_dir / "subtask_summary.md").read_text(encoding="utf-8"),
            )

    def test_run_task_marks_failed_when_retry_is_exhausted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            created = create_task(
                base_dir=tmp_path,
                title="Multi-card retry exhausted",
                goal="Fail after targeted retry stays red",
                workspace_root=tmp_path,
                executor_name="local",
                next_action_proposals=[
                    "Prepare changes",
                    "Verify results",
                ],
            )
            task_dir = tmp_path / ".swl" / "tasks" / created.task_id
            artifacts_dir = task_dir / "artifacts"
            attempts: dict[int, int] = {}

            def execute_card(
                _base_dir: Path,
                _state: object,
                card: object,
                _retrieval_items: list[object],
            ) -> ExecutorResult:
                subtask_index = int(card.subtask_index)
                attempts[subtask_index] = attempts.get(subtask_index, 0) + 1
                attempt_number = attempts[subtask_index]
                should_fail_review = subtask_index == 2
                return ExecutorResult(
                    executor_name="local",
                    status="completed",
                    message=f"subtask {subtask_index} attempt {attempt_number}",
                    output=""
                    if should_fail_review
                    else f"subtask {subtask_index} completed on attempt {attempt_number}",
                    prompt=f"execute subtask {subtask_index}",
                    dialect="plain_text",
                )

            with patch("swallow.orchestration.orchestrator.run_retrieval", return_value=[]):
                with patch("swallow.orchestration.orchestrator._execute_task_card", side_effect=execute_card):
                    with patch(
                        "swallow.orchestration.orchestrator.write_task_artifacts",
                        return_value=_passing_validation_tuple(),
                    ):
                        final_state = run_task(tmp_path, created.task_id, executor_name="local")

            events = _load_json_lines(task_dir / "events.jsonl")
            review_gate_event = next(event for event in events if event["event_type"] == "task.review_gate")
            executor_event = next(event for event in events if event["event_type"] == "executor.failed")
            breaker_event = next(
                event for event in events if event["event_type"] == "subtask.2.debate_circuit_breaker"
            )
            waiting_event = next(event for event in events if event["event_type"] == "task.waiting_human")
            debate_events = [event for event in events if event["event_type"] == "subtask.2.debate_round"]
            feedback_round_3 = json.loads(
                (artifacts_dir / "subtask_2_review_feedback_round_3.json").read_text(encoding="utf-8")
            )
            subtask2_attempt4_review = json.loads(
                (artifacts_dir / "subtask_2_attempt4_review_gate.json").read_text(encoding="utf-8")
            )
            debate_exhausted = json.loads((artifacts_dir / "subtask_2_debate_exhausted.json").read_text(encoding="utf-8"))
            self.assertEqual(final_state.status, "waiting_human")
            self.assertEqual(final_state.phase, "waiting_human")
            self.assertEqual(final_state.execution_lifecycle, "waiting_human")
            self.assertEqual(final_state.executor_name, "subtask-orchestrator")
            self.assertEqual(final_state.executor_status, "failed")
            self.assertEqual(attempts, {1: 1, 2: 4})
            self.assertEqual(review_gate_event["payload"]["status"], "failed")
            self.assertEqual(len(review_gate_event["payload"]["failed_card_ids"]), 1)
            self.assertEqual(executor_event["payload"]["failure_kind"], "debate_circuit_breaker")
            self.assertEqual(len(debate_events), 3)
            self.assertEqual([event["payload"]["round_number"] for event in debate_events], [1, 2, 3])
            self.assertEqual(breaker_event["payload"]["attempt_count"], 4)
            self.assertEqual(waiting_event["payload"]["status"], "waiting_human")
            self.assertEqual(feedback_round_3["round_number"], 3)
            self.assertEqual(len(debate_exhausted["feedback_refs"]), 3)
            self.assertEqual(subtask2_attempt4_review["status"], "failed")
            self.assertEqual(events[-1]["event_type"], "task.waiting_human")
            self.assertTrue((artifacts_dir / "executor_output.md").exists())
            self.assertIn(
                "failed_count: 1",
                (artifacts_dir / "executor_output.md").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "debate_exhausted_count: 1",
                (artifacts_dir / "executor_output.md").read_text(encoding="utf-8"),
            )
            self.assertFalse(any(event["event_type"] == "task.failed" for event in events))

    def test_run_task_does_not_debate_retry_subtask_executor_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            created = create_task(
                base_dir=tmp_path,
                title="Multi-card executor failure",
                goal="Fail directly when a subtask executor does not complete",
                workspace_root=tmp_path,
                executor_name="local",
                next_action_proposals=[
                    "Prepare changes",
                    "Verify results",
                ],
            )
            task_dir = tmp_path / ".swl" / "tasks" / created.task_id
            artifacts_dir = task_dir / "artifacts"
            attempts: dict[int, int] = {}

            def execute_card(
                _base_dir: Path,
                _state: object,
                card: object,
                _retrieval_items: list[object],
            ) -> ExecutorResult:
                subtask_index = int(card.subtask_index)
                attempts[subtask_index] = attempts.get(subtask_index, 0) + 1
                attempt_number = attempts[subtask_index]
                if subtask_index == 2:
                    return ExecutorResult(
                        executor_name="local",
                        status="failed",
                        message=f"subtask {subtask_index} attempt {attempt_number}",
                        output="executor failed before review",
                        prompt=f"execute subtask {subtask_index}",
                        dialect="plain_text",
                        failure_kind="subtask_executor_failure",
                    )
                return ExecutorResult(
                    executor_name="local",
                    status="completed",
                    message=f"subtask {subtask_index} attempt {attempt_number}",
                    output=f"subtask {subtask_index} completed on attempt {attempt_number}",
                    prompt=f"execute subtask {subtask_index}",
                    dialect="plain_text",
                )

            with patch("swallow.orchestration.orchestrator.run_retrieval", return_value=[]):
                with patch("swallow.orchestration.orchestrator._execute_task_card", side_effect=execute_card):
                    with patch(
                        "swallow.orchestration.orchestrator.write_task_artifacts",
                        return_value=_passing_validation_tuple(),
                    ):
                        final_state = run_task(tmp_path, created.task_id, executor_name="local")

            events = _load_json_lines(task_dir / "events.jsonl")
            review_gate_event = next(event for event in events if event["event_type"] == "task.review_gate")
            executor_event = next(event for event in events if event["event_type"] == "executor.failed")

            self.assertEqual(final_state.status, "failed")
            self.assertEqual(final_state.phase, "summarize")
            self.assertEqual(attempts, {1: 1, 2: 1})
            self.assertEqual(review_gate_event["payload"]["status"], "failed")
            self.assertEqual(executor_event["payload"]["failure_kind"], "review_gate_retry_exhausted")
            self.assertFalse(any(event["event_type"] == "subtask.2.debate_round" for event in events))
            self.assertFalse(any(event["event_type"] == "subtask.2.debate_circuit_breaker" for event in events))
            self.assertFalse((artifacts_dir / "subtask_2_attempt2_executor_output.md").exists())

    def test_run_task_waits_for_human_when_subtask_budget_is_exhausted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            created = create_task(
                base_dir=tmp_path,
                title="Multi-card budget exhausted",
                goal="Stop all subtasks when the shared token cost budget is already spent",
                workspace_root=tmp_path,
                executor_name="local",
                next_action_proposals=[
                    "Prepare changes",
                    "Verify results",
                ],
                token_cost_limit=0.05,
            )
            task_dir = tmp_path / ".swl" / "tasks" / created.task_id
            artifacts_dir = task_dir / "artifacts"

            append_event(
                tmp_path,
                Event(
                    task_id=created.task_id,
                    event_type="executor.completed",
                    message="prior execution cost",
                    payload={"token_cost": 0.10},
                ),
            )

            with patch("swallow.orchestration.orchestrator.run_retrieval", return_value=[]):
                with patch(
                    "swallow.orchestration.orchestrator._execute_task_card",
                    side_effect=AssertionError("subtask executor should not run when budget is exhausted"),
                ):
                    with patch(
                        "swallow.orchestration.orchestrator.write_task_artifacts",
                        return_value=_passing_validation_tuple(),
                    ):
                        final_state = run_task(tmp_path, created.task_id, executor_name="local")

            events = _load_json_lines(task_dir / "events.jsonl")
            review_gate_event = next(event for event in events if event["event_type"] == "task.review_gate")
            waiting_event = next(event for event in events if event["event_type"] == "task.waiting_human")
            executor_event = next(event for event in events if event["event_type"] == "executor.failed")
            subtask_budget_events = [
                event for event in events if event["event_type"] in {"subtask.1.budget_exhausted", "subtask.2.budget_exhausted"}
            ]

            self.assertEqual(final_state.status, "waiting_human")
            self.assertEqual(final_state.phase, "waiting_human")
            self.assertEqual(final_state.execution_lifecycle, "waiting_human")
            self.assertEqual(final_state.executor_name, "subtask-orchestrator")
            self.assertEqual(final_state.executor_status, "failed")
            self.assertEqual(waiting_event["payload"]["waiting_reason"], "budget_exhausted")
            self.assertEqual(review_gate_event["payload"]["status"], "failed")
            self.assertEqual(len(review_gate_event["payload"]["failed_card_ids"]), 2)
            self.assertEqual(executor_event["payload"]["failure_kind"], "budget_exhausted")
            self.assertEqual(len(subtask_budget_events), 2)
            self.assertTrue((artifacts_dir / "executor_output.md").exists())
            self.assertIn(
                "budget_exhausted_count: 2",
                (artifacts_dir / "executor_output.md").read_text(encoding="utf-8"),
            )
            self.assertFalse(any(".debate_round" in event["event_type"] for event in events))
            self.assertFalse(any(event["event_type"] == "task.failed" for event in events))

    def test_run_task_times_out_one_parallel_subtask_without_canceling_other_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            created = create_task(
                base_dir=tmp_path,
                title="Multi-card timeout isolation",
                goal="Fail one parallel subtask without canceling the other",
                workspace_root=tmp_path,
                executor_name="local",
                constraints=["parallel_subtasks"],
                next_action_proposals=[
                    "Fast subtask",
                    "Slow subtask",
                ],
                reviewer_timeout_seconds=1,
            )
            task_dir = tmp_path / ".swl" / "tasks" / created.task_id
            artifacts_dir = task_dir / "artifacts"

            async def execute_card(
                _base_dir: Path,
                _state: object,
                card: object,
                _retrieval_items: list[object],
            ) -> ExecutorResult:
                if int(card.subtask_index) == 2:
                    await asyncio.sleep(1.2)
                else:
                    await asyncio.sleep(0.05)
                    write_artifact(
                        _base_dir,
                        str(_state.task_id),
                        "custom_trace.md",
                        "fast subtask trace",
                    )
                return ExecutorResult(
                    executor_name="local",
                    status="completed",
                    message=f"subtask {card.subtask_index} completed",
                    output=f"subtask {card.subtask_index} completed",
                    prompt=f"execute subtask {card.subtask_index}",
                    dialect="plain_text",
                )

            with patch("swallow.orchestration.orchestrator.run_retrieval", return_value=[]):
                with patch("swallow.orchestration.orchestrator._execute_task_card", side_effect=execute_card):
                    with patch(
                        "swallow.orchestration.orchestrator.write_task_artifacts",
                        return_value=_passing_validation_tuple(),
                    ):
                        final_state = run_task(tmp_path, created.task_id, executor_name="local")

            events = _load_json_lines(task_dir / "events.jsonl")
            review_gate_event = next(event for event in events if event["event_type"] == "task.review_gate")
            executor_event = next(event for event in events if event["event_type"] == "executor.failed")
            subtask2_review = json.loads(
                (artifacts_dir / "subtask_2_attempt1_review_gate.json").read_text(encoding="utf-8")
            )
            subtask_summary = (artifacts_dir / "subtask_summary.md").read_text(encoding="utf-8")

            self.assertEqual(final_state.status, "failed")
            self.assertEqual(final_state.executor_name, "subtask-orchestrator")
            self.assertEqual(final_state.executor_status, "failed")
            self.assertEqual(review_gate_event["payload"]["status"], "failed")
            self.assertEqual(len(review_gate_event["payload"]["failed_card_ids"]), 1)
            self.assertEqual(executor_event["payload"]["failure_kind"], "review_gate_retry_exhausted")
            self.assertTrue((artifacts_dir / "subtask_1_attempt1_custom_trace.md").exists())
            self.assertTrue((artifacts_dir / "subtask_2_attempt1_executor_output.md").exists())
            self.assertEqual(subtask2_review["status"], "failed")
            self.assertIn("timed out after 1 seconds", subtask2_review["checks"][0]["detail"])
            self.assertIn("failure_kind: subtask_timeout", subtask_summary)
            self.assertIn(
                ".swl/tasks/"
                f"{created.task_id}"
                "/artifacts/subtask_1_attempt1_custom_trace.md",
                subtask_summary,
            )
            self.assertFalse(any(event["event_type"] == "subtask.2.debate_round" for event in events))


if __name__ == "__main__":
    unittest.main()
