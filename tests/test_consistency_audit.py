from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.cli import main
from swallow.consistency_audit import (
    evaluate_audit_trigger,
    load_audit_trigger_policy,
    run_consistency_audit,
    save_audit_trigger_policy,
)
from swallow.models import AuditTriggerPolicy, ExecutorResult, ValidationResult
from swallow.orchestrator import create_task, run_task
from swallow.store import write_artifact


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


def _load_events(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class ConsistencyAuditTest(unittest.TestCase):
    def test_run_consistency_audit_fails_gracefully_when_task_state_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            result = run_consistency_audit(
                tmp_path,
                "missing-task",
                auditor_route="http-claude",
            )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.verdict, "inconclusive")
        self.assertEqual(result.audit_artifact, "")
        self.assertIn("Task state is missing", result.message)

    def test_run_consistency_audit_writes_markdown_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            created = create_task(
                base_dir=tmp_path,
                title="Consistency audit task",
                goal="Audit the executor output with a stronger route",
                workspace_root=tmp_path,
                executor_name="local",
            )
            write_artifact(tmp_path, created.task_id, "executor_output.md", "candidate output for audit")

            with patch(
                "swallow.consistency_audit.run_prompt_executor",
                return_value=ExecutorResult(
                    executor_name="http",
                    status="completed",
                    message="audit complete",
                    output="# Consistency Audit\n- verdict: pass\n- risk_level: low\n",
                ),
            ):
                result = run_consistency_audit(
                    tmp_path,
                    created.task_id,
                    auditor_route="http-claude",
                )

            artifact_path = tmp_path / ".swl" / "tasks" / created.task_id / "artifacts" / Path(result.audit_artifact).name
            report = artifact_path.read_text(encoding="utf-8")

            self.assertTrue(artifact_path.exists())

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.verdict, "pass")
        self.assertEqual(result.auditor_route, "http-claude")
        self.assertIn("status: completed", report)
        self.assertIn("verdict: pass", report)
        self.assertIn("sample_artifact_path:", report)

    def test_run_consistency_audit_degrades_gracefully_for_unknown_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            created = create_task(
                base_dir=tmp_path,
                title="Consistency audit missing route",
                goal="Fail gracefully when the auditor route is missing",
                workspace_root=tmp_path,
                executor_name="local",
            )
            write_artifact(tmp_path, created.task_id, "executor_output.md", "candidate output for audit")

            result = run_consistency_audit(
                tmp_path,
                created.task_id,
                auditor_route="missing-route",
            )

            artifact_path = tmp_path / ".swl" / "tasks" / created.task_id / "artifacts" / Path(result.audit_artifact).name
            report = artifact_path.read_text(encoding="utf-8")

            self.assertTrue(artifact_path.exists())

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.verdict, "inconclusive")
        self.assertIn("Unknown auditor route", result.message)
        self.assertIn("status: failed", report)
        self.assertIn("missing-route", report)

    def test_cli_task_consistency_audit_prints_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            created = create_task(
                base_dir=tmp_path,
                title="CLI audit task",
                goal="Expose consistency audit through the CLI",
                workspace_root=tmp_path,
                executor_name="local",
            )
            write_artifact(tmp_path, created.task_id, "executor_output.md", "candidate output for audit")
            stdout = io.StringIO()

            with patch(
                "swallow.consistency_audit.run_prompt_executor",
                return_value=ExecutorResult(
                    executor_name="http",
                    status="completed",
                    message="audit complete",
                    output="# Consistency Audit\n- verdict: pass\n- risk_level: low\n",
                ),
            ):
                with redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "task",
                            "consistency-audit",
                            created.task_id,
                            "--auditor-route",
                            "http-claude",
                        ]
                    )

        self.assertEqual(exit_code, 0)
        self.assertIn("consistency_audit", stdout.getvalue())
        self.assertIn("status=completed", stdout.getvalue())
        self.assertIn("verdict=pass", stdout.getvalue())
        self.assertIn("route=http-claude", stdout.getvalue())

    def test_cli_task_consistency_audit_reports_missing_task_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "consistency-audit",
                        "missing-task",
                        "--auditor-route",
                        "http-claude",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("status=failed", stdout.getvalue())
        self.assertIn("verdict=inconclusive", stdout.getvalue())
        self.assertIn("artifact=-", stdout.getvalue())

    def test_evaluate_audit_trigger_matches_degraded_and_cost_thresholds(self) -> None:
        policy = AuditTriggerPolicy(
            enabled=True,
            trigger_on_degraded=True,
            trigger_on_cost_above=0.25,
            auditor_route="http-claude",
        )

        reasons = evaluate_audit_trigger(
            policy,
            {
                "degraded": True,
                "token_cost": 0.30,
            },
        )

        self.assertEqual(reasons, ["degraded", "cost"])

    def test_evaluate_audit_trigger_returns_empty_when_policy_does_not_match(self) -> None:
        policy = AuditTriggerPolicy(
            enabled=True,
            trigger_on_degraded=False,
            trigger_on_cost_above=0.50,
            auditor_route="http-claude",
        )

        reasons = evaluate_audit_trigger(
            policy,
            {
                "degraded": True,
                "token_cost": 0.10,
            },
        )

        self.assertEqual(reasons, [])

    def test_audit_policy_round_trips_through_disk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            expected = AuditTriggerPolicy(
                enabled=True,
                trigger_on_degraded=False,
                trigger_on_cost_above=0.75,
                auditor_route="http-qwen",
            )

            save_audit_trigger_policy(tmp_path, expected)
            loaded = load_audit_trigger_policy(tmp_path)

        self.assertEqual(loaded, expected)

    def test_cli_audit_policy_show_and_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "audit",
                        "policy",
                        "set",
                        "--enabled",
                        "--no-trigger-on-degraded",
                        "--trigger-on-cost-above",
                        "0.5",
                        "--auditor-route",
                        "http-qwen",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("enabled: yes", stdout.getvalue())
            self.assertIn("trigger_on_degraded: no", stdout.getvalue())
            self.assertIn("trigger_on_cost_above: 0.500000", stdout.getvalue())
            self.assertIn("auditor_route: http-qwen", stdout.getvalue())

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "audit",
                        "policy",
                        "show",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("enabled: yes", stdout.getvalue())
        self.assertIn("trigger_on_degraded: no", stdout.getvalue())
        self.assertIn("trigger_on_cost_above: 0.500000", stdout.getvalue())
        self.assertIn("auditor_route: http-qwen", stdout.getvalue())

    def test_run_task_schedules_consistency_audit_when_policy_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            created = create_task(
                base_dir=tmp_path,
                title="Auto audit trigger",
                goal="Schedule a consistency audit after a degraded run",
                workspace_root=tmp_path,
                executor_name="local",
            )
            save_audit_trigger_policy(
                tmp_path,
                AuditTriggerPolicy(
                    enabled=True,
                    trigger_on_degraded=True,
                    trigger_on_cost_above=None,
                    auditor_route="http-claude",
                ),
            )

            def run_local(_state: object, _retrieval_items: list[object], prompt: str) -> ExecutorResult:
                return ExecutorResult(
                    executor_name="local",
                    status="completed",
                    message="completed with degraded path",
                    output="resolved output",
                    prompt=prompt,
                    dialect="plain_text",
                    degraded=True,
                )

            with patch("swallow.orchestrator.run_retrieval", return_value=[]):
                with patch("swallow.orchestrator.write_task_artifacts", return_value=_passing_validation_tuple()):
                    with patch("swallow.executor.run_local_executor", side_effect=run_local):
                        with patch("swallow.orchestrator.schedule_consistency_audit", return_value="audit-thread") as schedule:
                            final_state = run_task(tmp_path, created.task_id, executor_name="local")

            events = _load_events(tmp_path / ".swl" / "tasks" / created.task_id / "events.jsonl")
            scheduled_event = next(event for event in events if event["event_type"] == "task.consistency_audit_scheduled")

        self.assertEqual(final_state.status, "completed")
        self.assertTrue(schedule.called)
        self.assertEqual(schedule.call_args.kwargs["auditor_route"], "http-claude")
        self.assertEqual(scheduled_event["payload"]["trigger_reasons"], ["degraded"])
        self.assertEqual(events[-1]["event_type"], "task.completed")

    def test_run_task_does_not_schedule_consistency_audit_when_policy_does_not_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            created = create_task(
                base_dir=tmp_path,
                title="No auto audit trigger",
                goal="Do not schedule a consistency audit when no trigger matches",
                workspace_root=tmp_path,
                executor_name="local",
            )
            save_audit_trigger_policy(
                tmp_path,
                AuditTriggerPolicy(
                    enabled=True,
                    trigger_on_degraded=False,
                    trigger_on_cost_above=0.5,
                    auditor_route="http-claude",
                ),
            )

            def run_local(_state: object, _retrieval_items: list[object], prompt: str) -> ExecutorResult:
                return ExecutorResult(
                    executor_name="local",
                    status="completed",
                    message="healthy completion",
                    output="resolved output",
                    prompt=prompt,
                    dialect="plain_text",
                    degraded=False,
                )

            with patch("swallow.orchestrator.run_retrieval", return_value=[]):
                with patch("swallow.orchestrator.write_task_artifacts", return_value=_passing_validation_tuple()):
                    with patch("swallow.executor.run_local_executor", side_effect=run_local):
                        with patch("swallow.orchestrator.schedule_consistency_audit", return_value="audit-thread") as schedule:
                            final_state = run_task(tmp_path, created.task_id, executor_name="local")

            events = _load_events(tmp_path / ".swl" / "tasks" / created.task_id / "events.jsonl")

        self.assertEqual(final_state.status, "completed")
        self.assertFalse(schedule.called)
        self.assertFalse(any(event["event_type"] == "task.consistency_audit_scheduled" for event in events))


if __name__ == "__main__":
    unittest.main()
