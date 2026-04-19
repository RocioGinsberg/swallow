from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.models import (
    CompatibilityResult,
    ExecutionFitResult,
    ExecutorResult,
    KnowledgePolicyResult,
    TaskState,
    ValidationResult,
)
from swallow.retry_policy import evaluate_retry_policy


def _passing_policy_inputs() -> tuple[CompatibilityResult, ExecutionFitResult, KnowledgePolicyResult, ValidationResult]:
    return (
        CompatibilityResult(status="passed", message="Compatibility passed."),
        ExecutionFitResult(status="passed", message="Execution fit passed."),
        KnowledgePolicyResult(status="passed", message="Knowledge policy passed."),
        ValidationResult(status="passed", message="Validation passed."),
    )


class RetryPolicyTest(unittest.TestCase):
    def test_rate_limited_http_failure_is_retryable(self) -> None:
        state = TaskState(
            task_id="retry-http-rate-limit",
            title="Retry rate limit",
            goal="Allow retry after HTTP 429",
            workspace_root="/tmp",
            current_attempt_number=1,
        )
        executor_result = ExecutorResult(
            executor_name="http",
            status="failed",
            message="HTTP executor failed with status 429.",
            failure_kind="http_rate_limited",
        )

        compatibility, execution_fit, knowledge_policy, validation = _passing_policy_inputs()
        result = evaluate_retry_policy(
            state,
            executor_result,
            compatibility,
            execution_fit,
            knowledge_policy,
            validation,
        )

        self.assertEqual(result.status, "warning")
        self.assertTrue(result.retryable)
        self.assertEqual(result.retry_decision, "operator_retry_available")

    def test_generic_http_error_is_not_retryable_by_baseline_policy(self) -> None:
        state = TaskState(
            task_id="retry-http-error",
            title="Retry http error",
            goal="Require route or config changes after non-rate-limited HTTP errors",
            workspace_root="/tmp",
            current_attempt_number=1,
        )
        executor_result = ExecutorResult(
            executor_name="http",
            status="failed",
            message="HTTP executor failed with status 503.",
            failure_kind="http_error",
        )

        compatibility, execution_fit, knowledge_policy, validation = _passing_policy_inputs()
        result = evaluate_retry_policy(
            state,
            executor_result,
            compatibility,
            execution_fit,
            knowledge_policy,
            validation,
        )

        self.assertEqual(result.status, "failed")
        self.assertFalse(result.retryable)
        self.assertEqual(result.retry_decision, "non_retryable_failure")


if __name__ == "__main__":
    unittest.main()
