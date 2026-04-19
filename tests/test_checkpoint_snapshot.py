from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.checkpoint_snapshot import evaluate_checkpoint_snapshot
from swallow.models import TaskState


class CheckpointSnapshotTest(unittest.TestCase):
    def test_http_rate_limited_maps_to_interruption_recovery(self) -> None:
        state = TaskState(
            task_id="checkpoint-http-rate-limit",
            title="Checkpoint rate limit",
            goal="Preserve retry semantics for HTTP 429 failures",
            workspace_root="/tmp",
            status="failed",
            execution_phase="execution_done",
        )
        handoff_record = {
            "status": "resume_from_failure",
            "failure_kind": "http_rate_limited",
        }
        retry_policy = {"retryable": True}
        stop_policy = {"checkpoint_kind": "retry_review", "continue_allowed": True}
        execution_budget_policy = {"budget_state": "available"}

        result = evaluate_checkpoint_snapshot(
            state,
            handoff_record,
            retry_policy,
            stop_policy,
            execution_budget_policy,
        )

        self.assertEqual(result.checkpoint_state, "retry_ready")
        self.assertEqual(result.recovery_semantics, "interruption_recovery")
        self.assertEqual(result.interruption_kind, "http_rate_limited")

    def test_waiting_human_budget_exhausted_maps_to_budget_recovery(self) -> None:
        state = TaskState(
            task_id="checkpoint-budget-exhausted",
            title="Checkpoint budget exhausted",
            goal="Preserve waiting_human semantics for token cost guardrails",
            workspace_root="/tmp",
            status="waiting_human",
            phase="waiting_human",
            execution_phase="analysis_done",
        )
        handoff_record = {
            "status": "resume_from_failure",
            "failure_kind": "budget_exhausted",
        }
        retry_policy = {"retryable": False}
        stop_policy = {"checkpoint_kind": "pending", "continue_allowed": False}
        execution_budget_policy = {"budget_state": "cost_exhausted"}

        result = evaluate_checkpoint_snapshot(
            state,
            handoff_record,
            retry_policy,
            stop_policy,
            execution_budget_policy,
        )

        self.assertEqual(result.checkpoint_state, "waiting_human")
        self.assertEqual(result.recovery_semantics, "human_gate_budget_exhausted")
        self.assertEqual(result.recommended_path, "run")
        self.assertIn("checkpoint.budget_exhausted", [finding.code for finding in result.findings])


if __name__ == "__main__":
    unittest.main()
