from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.cli import main
from swallow.consistency_audit import run_consistency_audit
from swallow.models import ExecutorResult
from swallow.orchestrator import create_task
from swallow.store import write_artifact


class ConsistencyAuditTest(unittest.TestCase):
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
        self.assertEqual(result.auditor_route, "http-claude")
        self.assertIn("status: completed", report)
        self.assertIn("sample_artifact_path:", report)
        self.assertIn("verdict: pass", report)

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
        self.assertIn("route=http-claude", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
