from __future__ import annotations

import json
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.models import ExecutorResult, TaskCard
from swallow.review_gate import ReviewGateResult, review_executor_output


class ReviewGateTest(unittest.TestCase):
    def test_review_gate_passes_for_completed_non_empty_output(self) -> None:
        result = review_executor_output(
            ExecutorResult(
                executor_name="mock",
                status="completed",
                message="ok",
                output="generated output",
            ),
            TaskCard(goal="Review output", parent_task_id="task-1"),
        )

        self.assertEqual(result.status, "passed")
        self.assertEqual(result.message, "All review gate checks passed.")
        self.assertEqual([check["name"] for check in result.checks], ["executor_status", "output_non_empty"])
        self.assertEqual(result.to_dict()["status"], "passed")

    def test_review_gate_fails_for_failed_executor_and_empty_output(self) -> None:
        result = review_executor_output(
            ExecutorResult(
                executor_name="mock",
                status="failed",
                message="not ok",
                output="",
            ),
            TaskCard(goal="Review output", parent_task_id="task-2"),
        )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.message, "One or more review gate checks failed.")
        self.assertFalse(result.checks[0]["passed"])
        self.assertFalse(result.checks[1]["passed"])

    def test_review_gate_emits_schema_placeholder_check_when_schema_present(self) -> None:
        result = review_executor_output(
            ExecutorResult(
                executor_name="local",
                status="completed",
                message="ok",
                output="formatted response",
            ),
            TaskCard(
                goal="Schema placeholder",
                parent_task_id="task-3",
                output_schema={"type": "object"},
            ),
        )

        self.assertEqual(result.checks[-1]["name"], "output_schema")
        self.assertTrue(result.checks[-1]["passed"])
        self.assertEqual(result.checks[-1]["detail"], "schema validation skipped in v0")
        self.assertIsInstance(result, ReviewGateResult)

    def test_review_gate_validates_librarian_change_log_schema(self) -> None:
        result = review_executor_output(
            ExecutorResult(
                executor_name="librarian",
                status="completed",
                message="ok",
                output=json.dumps(
                    {
                        "kind": "librarian_change_log_v0",
                        "task_id": "task-4",
                        "generated_at": "2026-04-16T00:00:00+00:00",
                        "candidate_count": 1,
                        "promoted_count": 1,
                        "skipped_count": 0,
                        "entries": [],
                        "change_log_artifact": ".swl/tasks/task-4/artifacts/librarian_change_log.json",
                    }
                ),
            ),
            TaskCard(
                goal="Validate librarian output",
                parent_task_id="task-4",
                output_schema={
                    "required": [
                        "kind",
                        "task_id",
                        "generated_at",
                        "candidate_count",
                        "promoted_count",
                        "skipped_count",
                        "entries",
                        "change_log_artifact",
                    ],
                    "const": {"kind": "librarian_change_log_v0"},
                },
            ),
        )

        self.assertEqual(result.status, "passed")
        self.assertEqual(result.checks[-1]["name"], "output_schema")
        self.assertTrue(result.checks[-1]["passed"])
        self.assertIn("validated structured output schema", result.checks[-1]["detail"])

    def test_review_gate_fails_librarian_change_log_schema_mismatch(self) -> None:
        result = review_executor_output(
            ExecutorResult(
                executor_name="librarian",
                status="completed",
                message="not ok",
                output=json.dumps(
                    {
                        "kind": "unexpected_kind",
                        "task_id": "task-5",
                        "generated_at": "2026-04-16T00:00:00+00:00",
                        "candidate_count": 1,
                        "promoted_count": 0,
                    }
                ),
            ),
            TaskCard(
                goal="Validate librarian output mismatch",
                parent_task_id="task-5",
                output_schema={
                    "required": [
                        "kind",
                        "task_id",
                        "generated_at",
                        "candidate_count",
                        "promoted_count",
                        "skipped_count",
                        "entries",
                        "change_log_artifact",
                    ],
                    "const": {"kind": "librarian_change_log_v0"},
                },
            ),
        )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.checks[-1]["name"], "output_schema")
        self.assertFalse(result.checks[-1]["passed"])
        self.assertIn("missing required fields", result.checks[-1]["detail"])


if __name__ == "__main__":
    unittest.main()
