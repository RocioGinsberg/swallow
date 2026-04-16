from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.models import ExecutorResult, ValidationResult
from swallow.orchestrator import create_task, run_task
from swallow.store import write_artifact


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

            with patch("swallow.orchestrator.run_retrieval", return_value=[]):
                with patch("swallow.orchestrator._execute_task_card", side_effect=execute_card):
                    with patch(
                        "swallow.orchestrator.write_task_artifacts",
                        return_value=_passing_validation_tuple(),
                    ):
                        final_state = run_task(tmp_path, created.task_id, executor_name="local")

            events = _load_json_lines(task_dir / "events.jsonl")
            planned_event = next(event for event in events if event["event_type"] == "task.planned")
            review_gate_event = next(event for event in events if event["event_type"] == "task.review_gate")
            executor_event = next(event for event in events if event["event_type"] == "executor.completed")
            retry_event = next(event for event in events if event["event_type"] == "subtask.2.retry_requested")
            subtask2_review_events = [
                event for event in events if event["event_type"] == "subtask.2.review_gate"
            ]
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
            self.assertEqual(retry_event["payload"]["previous_status"], "failed")
            self.assertEqual(len(subtask2_review_events), 2)
            self.assertEqual(subtask2_review_events[0]["payload"]["status"], "failed")
            self.assertEqual(subtask2_review_events[1]["payload"]["status"], "passed")
            self.assertEqual(subtask2_attempt1_review["status"], "failed")
            self.assertEqual(subtask2_attempt2_review["status"], "passed")
            self.assertTrue((artifacts_dir / "executor_output.md").exists())
            self.assertTrue((artifacts_dir / "subtask_1_attempt1_executor_output.md").exists())
            self.assertTrue((artifacts_dir / "subtask_2_attempt1_executor_output.md").exists())
            self.assertTrue((artifacts_dir / "subtask_2_attempt2_executor_output.md").exists())
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

            with patch("swallow.orchestrator.run_retrieval", return_value=[]):
                with patch("swallow.orchestrator._execute_task_card", side_effect=execute_card):
                    with patch(
                        "swallow.orchestrator.write_task_artifacts",
                        return_value=_passing_validation_tuple(),
                    ):
                        final_state = run_task(tmp_path, created.task_id, executor_name="local")

            events = _load_json_lines(task_dir / "events.jsonl")
            review_gate_event = next(event for event in events if event["event_type"] == "task.review_gate")
            executor_event = next(event for event in events if event["event_type"] == "executor.failed")
            exhausted_event = next(
                event for event in events if event["event_type"] == "subtask.2.review_gate_retry_exhausted"
            )
            subtask2_attempt2_review = json.loads(
                (artifacts_dir / "subtask_2_attempt2_review_gate.json").read_text(encoding="utf-8")
            )
            self.assertEqual(final_state.status, "failed")
            self.assertEqual(final_state.executor_name, "subtask-orchestrator")
            self.assertEqual(final_state.executor_status, "failed")
            self.assertEqual(attempts, {1: 1, 2: 2})
            self.assertEqual(review_gate_event["payload"]["status"], "failed")
            self.assertEqual(len(review_gate_event["payload"]["failed_card_ids"]), 1)
            self.assertEqual(executor_event["payload"]["failure_kind"], "review_gate_retry_exhausted")
            self.assertEqual(exhausted_event["payload"]["attempt_count"], 2)
            self.assertEqual(subtask2_attempt2_review["status"], "failed")
            self.assertEqual(events[-1]["event_type"], "task.failed")
            self.assertTrue((artifacts_dir / "executor_output.md").exists())
            self.assertIn(
                "failed_count: 1",
                (artifacts_dir / "executor_output.md").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
