from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.cost_estimation import CostEstimator, StaticCostEstimator, estimate_cost, estimate_tokens
from swallow.harness import run_execution
from swallow.models import ExecutorResult, TaskState


class CostEstimationTest(unittest.TestCase):
    def test_estimate_tokens_uses_local_approximation(self) -> None:
        self.assertEqual(estimate_tokens(""), 0)
        self.assertEqual(estimate_tokens("abcd"), 1)
        self.assertEqual(estimate_tokens("abcdefgh"), 2)

    def test_estimate_cost_uses_static_model_pricing(self) -> None:
        self.assertEqual(estimate_cost("local", 1000, 1000), 0.0)
        self.assertEqual(estimate_cost("codex", 1000, 1000), 0.0)
        self.assertAlmostEqual(estimate_cost("claude-3-5-sonnet", 1_000_000, 1_000_000), 18.0)
        self.assertGreater(estimate_cost("gemini-2.5-pro", 1_000_000, 1_000_000), 0.0)
        self.assertGreater(estimate_cost("qwen3-coder", 1_000_000, 1_000_000), 0.0)
        self.assertEqual(estimate_cost("unknown-model", 1000, 1000), 0.0)

    def test_static_cost_estimator_satisfies_protocol(self) -> None:
        estimator = StaticCostEstimator()
        self.assertIsInstance(estimator, CostEstimator)
        self.assertAlmostEqual(estimator.estimate("claude", 1_000_000, 1_000_000), 18.0)

    def test_run_execution_accepts_injected_cost_estimator(self) -> None:
        class FixedCostEstimator:
            def estimate(self, model_hint: str, input_tokens: int, output_tokens: int) -> float:
                del model_hint, input_tokens, output_tokens
                return 0.123456

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = TaskState(
                task_id="task-cost-estimator",
                title="Cost estimator injection",
                goal="Verify injected cost estimator is used",
                workspace_root=str(tmp_path),
                route_name="local-summary",
                route_model_hint="local",
                current_attempt_id="attempt-0001",
                current_attempt_number=1,
                current_attempt_ownership_status="owned",
                current_attempt_owner_assigned_at="2026-04-18T00:00:00+08:00",
                dispatch_requested_at="2026-04-18T00:00:00+08:00",
                dispatch_started_at="2026-04-18T00:00:01+08:00",
                execution_lifecycle="dispatched",
            )

            with patch(
                "swallow.harness.run_executor",
                return_value=ExecutorResult(
                    executor_name="local",
                    status="completed",
                    message="Completed.",
                    output="executor output",
                    prompt="executor prompt",
                    estimated_input_tokens=10,
                    estimated_output_tokens=20,
                ),
            ):
                run_execution(tmp_path, state, [], cost_estimator=FixedCostEstimator())

            events_path = tmp_path / ".swl" / "tasks" / state.task_id / "events.jsonl"
            events = [
                json.loads(line)
                for line in events_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(events[-1]["payload"]["token_cost"], 0.123456)


if __name__ == "__main__":
    unittest.main()
