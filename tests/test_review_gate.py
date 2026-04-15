from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
