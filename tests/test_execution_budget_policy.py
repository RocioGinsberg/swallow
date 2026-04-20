from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.execution_budget_policy import (
    calculate_task_token_cost,
    evaluate_execution_budget_policy,
    evaluate_token_cost_budget,
)
from swallow.models import Event, RetryPolicyResult
from swallow.store import append_event


def _retry_policy_result() -> RetryPolicyResult:
    return RetryPolicyResult(
        status="passed",
        message="Retry budget remains available.",
        retryable=True,
        retry_decision="retry_available",
        max_attempts=4,
        remaining_attempts=2,
        checkpoint_required=False,
        recommended_action="Continue within the configured retry budget.",
    )


class ExecutionBudgetPolicyTest(unittest.TestCase):
    def test_calculate_task_token_cost_ignores_fallback_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task_id = "task-cost-scan"
            append_event(
                base_dir,
                Event(
                    task_id=task_id,
                    event_type="executor.completed",
                    message="primary success",
                    payload={"token_cost": 0.125},
                ),
            )
            append_event(
                base_dir,
                Event(
                    task_id=task_id,
                    event_type="task.execution_fallback",
                    message="fallback executed",
                    payload={"token_cost": 9.999},
                ),
            )
            append_event(
                base_dir,
                Event(
                    task_id=task_id,
                    event_type="executor.failed",
                    message="secondary failure",
                    payload={"token_cost": 0.25},
                ),
            )

            current_token_cost = calculate_task_token_cost(base_dir, task_id)
            budget = evaluate_token_cost_budget(base_dir, task_id, 0.30)

        self.assertAlmostEqual(current_token_cost, 0.375)
        self.assertEqual(budget["budget_state"], "cost_exhausted")
        self.assertAlmostEqual(float(budget["current_token_cost"]), 0.375)
        self.assertAlmostEqual(float(budget["token_cost_limit"]), 0.30)

    def test_evaluate_execution_budget_policy_warns_when_token_cost_is_exhausted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task_id = "task-budget-warning"
            append_event(
                base_dir,
                Event(
                    task_id=task_id,
                    event_type="executor.completed",
                    message="seed cost",
                    payload={"token_cost": 0.42},
                ),
            )

            result = evaluate_execution_budget_policy(
                _retry_policy_result(),
                base_dir=base_dir,
                task_id=task_id,
                token_cost_limit=0.40,
            )

        self.assertEqual(result.status, "warning")
        self.assertEqual(result.budget_state, "cost_exhausted")
        self.assertAlmostEqual(result.current_token_cost, 0.42)
        self.assertAlmostEqual(result.token_cost_limit, 0.40)
        self.assertIn("raising token_cost_limit", result.recommended_action)
        self.assertIn(
            "execution_budget_policy.token_cost_exhausted",
            [finding.code for finding in result.findings],
        )


if __name__ == "__main__":
    unittest.main()
