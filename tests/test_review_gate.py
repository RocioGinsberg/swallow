from __future__ import annotations

import json
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from unittest.mock import patch

from swallow.models import ExecutorResult, TaskCard, TaskState
from swallow.review_gate import ReviewFeedback, ReviewGateResult, build_review_feedback, review_executor_output, run_review_gate


def _review_state() -> TaskState:
    return TaskState(
        task_id="task-review",
        title="Review task",
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

    def test_build_review_feedback_returns_none_when_review_passes(self) -> None:
        gate_result = review_executor_output(
            ExecutorResult(
                executor_name="mock",
                status="completed",
                message="ok",
                output="done",
            ),
            TaskCard(goal="Review output", parent_task_id="task-pass"),
        )

        feedback = build_review_feedback(
            gate_result,
            ExecutorResult(
                executor_name="mock",
                status="completed",
                message="ok",
                output="done",
            ),
            round_number=1,
            max_rounds=3,
        )

        self.assertIsNone(feedback)

    def test_build_review_feedback_collects_failed_checks_and_suggestions(self) -> None:
        executor_result = ExecutorResult(
            executor_name="mock",
            status="failed",
            message="not ok",
            output="",
        )
        gate_result = review_executor_output(
            executor_result,
            TaskCard(goal="Review output", parent_task_id="task-fail"),
        )

        feedback = build_review_feedback(gate_result, executor_result, round_number=1, max_rounds=3)

        self.assertIsInstance(feedback, ReviewFeedback)
        assert feedback is not None
        self.assertEqual(feedback.round_number, 1)
        self.assertEqual(feedback.max_rounds, 3)
        self.assertEqual([check["name"] for check in feedback.failed_checks], ["executor_status", "output_non_empty"])
        self.assertIn(
            "Ensure the executor finishes with status=completed before returning to the review gate.",
            feedback.suggestions,
        )
        self.assertIn(
            "Return a non-empty output payload that directly addresses the task goal.",
            feedback.suggestions,
        )
        self.assertEqual(feedback.original_output_snippet, "")

    def test_build_review_feedback_truncates_output_snippet_to_500_chars(self) -> None:
        oversized_output = "x" * 700
        executor_result = ExecutorResult(
            executor_name="librarian",
            status="completed",
            message="not ok",
            output=oversized_output,
        )
        gate_result = review_executor_output(
            executor_result,
            TaskCard(
                goal="Validate schema mismatch",
                parent_task_id="task-schema",
                output_schema={"required": ["kind"], "const": {"kind": "expected"}},
            ),
        )

        feedback = build_review_feedback(gate_result, executor_result, round_number=2, max_rounds=3)

        self.assertIsNotNone(feedback)
        assert feedback is not None
        self.assertEqual(feedback.round_number, 2)
        self.assertLessEqual(len(feedback.original_output_snippet), 500)
        self.assertTrue(feedback.original_output_snippet.endswith("..."))
        self.assertIn(
            "Return a structured JSON object that satisfies the required schema fields and constant values.",
            feedback.suggestions,
        )

    def test_run_review_gate_passes_when_majority_reviewers_pass(self) -> None:
        state = _review_state()
        card = TaskCard(
            goal="Review output",
            parent_task_id=state.task_id,
            reviewer_routes=["http-claude", "http-qwen", "http-gemini"],
            consensus_policy="majority",
        )
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
                output='{"status":"passed","message":"approved","checks":[{"name":"constraint_adherence","passed":true,"detail":"constraints met"}]}',
            ),
            ExecutorResult(
                executor_name="http",
                status="completed",
                message="review ok",
                output='{"status":"failed","message":"needs tightening","checks":[{"name":"material_risk","passed":false,"detail":"too hand-wavy"}]}',
            ),
        ]

        with patch("swallow.review_gate.run_prompt_executor", side_effect=reviewer_outputs):
            result = run_review_gate(
                state,
                ExecutorResult(
                    executor_name="local",
                    status="completed",
                    message="ok",
                    output="bounded implementation details",
                ),
                card,
            )

        self.assertEqual(result.status, "passed")
        self.assertIn("majority vote", result.message)
        self.assertTrue(any(check["name"] == "consensus_policy" and check["passed"] for check in result.checks))

    def test_run_review_gate_fails_tie_under_majority_policy(self) -> None:
        state = _review_state()
        card = TaskCard(
            goal="Review output",
            parent_task_id=state.task_id,
            reviewer_routes=["http-claude", "http-qwen"],
            consensus_policy="majority",
        )
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
                output='{"status":"failed","message":"not enough evidence","checks":[{"name":"material_risk","passed":false,"detail":"insufficient support"}]}',
            ),
        ]

        with patch("swallow.review_gate.run_prompt_executor", side_effect=reviewer_outputs):
            result = run_review_gate(
                state,
                ExecutorResult(
                    executor_name="local",
                    status="completed",
                    message="ok",
                    output="candidate output",
                ),
                card,
            )

        self.assertEqual(result.status, "failed")
        self.assertIn("required 2", result.message)
        self.assertTrue(any(check["name"] == "reviewer_route:http-qwen" and not check["passed"] for check in result.checks))

    def test_run_review_gate_fails_when_veto_route_rejects(self) -> None:
        state = _review_state()
        card = TaskCard(
            goal="Review output",
            parent_task_id=state.task_id,
            reviewer_routes=["http-claude", "http-qwen"],
            consensus_policy="veto",
        )
        reviewer_outputs = [
            ExecutorResult(
                executor_name="http",
                status="completed",
                message="review ok",
                output='{"status":"failed","message":"strong reviewer rejects","checks":[{"name":"goal_alignment","passed":false,"detail":"goal not met"}]}',
            ),
            ExecutorResult(
                executor_name="http",
                status="completed",
                message="review ok",
                output='{"status":"passed","message":"secondary reviewer accepts","checks":[{"name":"material_risk","passed":true,"detail":"acceptable"}]}',
            ),
        ]

        with patch("swallow.review_gate.run_prompt_executor", side_effect=reviewer_outputs):
            result = run_review_gate(
                state,
                ExecutorResult(
                    executor_name="local",
                    status="completed",
                    message="ok",
                    output="candidate output",
                ),
                card,
            )

        self.assertEqual(result.status, "failed")
        self.assertIn("veto route 'http-claude' rejected", result.message)

    def test_run_review_gate_treats_unreadable_reviewer_payload_as_failed(self) -> None:
        state = _review_state()
        card = TaskCard(
            goal="Review output",
            parent_task_id=state.task_id,
            reviewer_routes=["http-claude"],
            consensus_policy="majority",
        )

        with patch(
            "swallow.review_gate.run_prompt_executor",
            return_value=ExecutorResult(
                executor_name="http",
                status="completed",
                message="review ok",
                output="not-json",
            ),
        ):
            result = run_review_gate(
                state,
                ExecutorResult(
                    executor_name="local",
                    status="completed",
                    message="ok",
                    output="candidate output",
                ),
                card,
            )

        self.assertEqual(result.status, "failed")
        self.assertTrue(any(check["name"] == "reviewer_route:http-claude" and not check["passed"] for check in result.checks))

    def test_run_review_gate_skips_consensus_when_local_checks_fail(self) -> None:
        state = _review_state()
        card = TaskCard(
            goal="Review output",
            parent_task_id=state.task_id,
            reviewer_routes=["http-claude", "http-qwen"],
            consensus_policy="majority",
        )

        with patch("swallow.review_gate.run_prompt_executor") as reviewer_call:
            result = run_review_gate(
                state,
                ExecutorResult(
                    executor_name="local",
                    status="failed",
                    message="executor failed",
                    output="",
                ),
                card,
            )

        self.assertEqual(result.status, "failed")
        reviewer_call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
