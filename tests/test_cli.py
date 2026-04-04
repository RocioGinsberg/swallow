from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys
import subprocess
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.cli import main
from swallow.executor import build_fallback_output, classify_failure_kind, run_codex_executor
from swallow.models import ExecutorResult, TaskState


class CliLifecycleTest(unittest.TestCase):
    def test_task_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\norchestrator harness task memory\n", encoding="utf-8")

            with patch.dict("os.environ", {"AIWF_EXECUTOR_MODE": "mock"}, clear=False):
                exit_code = main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Design orchestrator",
                        "--goal",
                        "Create a phase 0 harness",
                        "--workspace-root",
                        str(tmp_path),
                    ]
                )
                self.assertEqual(exit_code, 0)

                tasks_dir = tmp_path / ".swl" / "tasks"
                created = [entry.name for entry in tasks_dir.iterdir() if entry.is_dir()]
                self.assertEqual(len(created), 1)
                task_id = created[0]

                exit_code = main(["--base-dir", str(tmp_path), "task", "run", task_id])
                self.assertEqual(exit_code, 0)

                summary = (tasks_dir / task_id / "artifacts" / "summary.md").read_text(encoding="utf-8")
                resume_note = (tasks_dir / task_id / "artifacts" / "resume_note.md").read_text(encoding="utf-8")
                executor_output = (tasks_dir / task_id / "artifacts" / "executor_output.md").read_text(
                    encoding="utf-8"
                )

                self.assertIn("Summary for", summary)
                self.assertIn("notes.md", summary)
                self.assertIn("mock-codex", summary)
                self.assertIn("Resume Note for", resume_note)
                self.assertIn("Mock executor output", executor_output)

    def test_task_failure_when_codex_binary_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\nexecutor failure coverage\n", encoding="utf-8")

            with patch.dict(
                "os.environ",
                {"AIWF_CODEX_BIN": "definitely-not-a-real-codex-binary", "AIWF_EXECUTOR_MODE": "codex"},
                clear=False,
            ):
                exit_code = main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Failing executor",
                        "--goal",
                        "Exercise codex adapter failure handling",
                        "--workspace-root",
                        str(tmp_path),
                    ]
                )
                self.assertEqual(exit_code, 0)

                tasks_dir = tmp_path / ".swl" / "tasks"
                task_id = next(entry.name for entry in tasks_dir.iterdir() if entry.is_dir())

                exit_code = main(["--base-dir", str(tmp_path), "task", "run", task_id])
                self.assertEqual(exit_code, 0)

                state = (tasks_dir / task_id / "state.json").read_text(encoding="utf-8")
                summary = (tasks_dir / task_id / "artifacts" / "summary.md").read_text(encoding="utf-8")
                executor_output = (tasks_dir / task_id / "artifacts" / "executor_output.md").read_text(
                    encoding="utf-8"
                )
                executor_stdout = (tasks_dir / task_id / "artifacts" / "executor_stdout.txt").read_text(
                    encoding="utf-8"
                )
                executor_stderr = (tasks_dir / task_id / "artifacts" / "executor_stderr.txt").read_text(
                    encoding="utf-8"
                )

                self.assertIn('"status": "failed"', state)
                self.assertIn("Codex binary not found", summary)
                self.assertIn("Codex binary not found", executor_output)
                self.assertEqual(executor_stdout.strip(), "")
                self.assertIn("definitely-not-a-real-codex-binary", executor_stderr)

    def test_codex_timeout_preserves_partial_output(self) -> None:
        state = TaskState(
            task_id="timeout123",
            title="Timeout executor",
            goal="Keep partial output on timeout",
            workspace_root="/tmp",
        )
        timeout_exc = subprocess.TimeoutExpired(
            cmd=["codex", "exec"],
            timeout=5,
            output="partial stdout",
            stderr="partial stderr",
        )

        with patch("swallow.executor.shutil.which", return_value="/usr/bin/codex"):
            with patch("swallow.executor.subprocess.run", side_effect=timeout_exc):
                result = run_codex_executor(state, [])

        self.assertEqual(result.status, "failed")
        self.assertIn("timed out", result.message)
        self.assertIn("Structured fallback note generated", result.message)
        self.assertEqual(result.failure_kind, "timeout")
        self.assertIn("# Executor Fallback Note", result.output)
        self.assertIn("partial stdout", result.output)
        self.assertEqual(result.stdout, "partial stdout")
        self.assertEqual(result.stderr, "partial stderr")

    def test_failure_classifier_marks_unreachable_backend(self) -> None:
        failure_kind = classify_failure_kind(
            1,
            "failed to connect to websocket: Operation not permitted",
            "ERROR: Reconnecting... 2/5",
        )
        self.assertEqual(failure_kind, "unreachable_backend")

    def test_failure_classifier_expanded_unreachable_markers(self) -> None:
        failure_kind = classify_failure_kind(
            1,
            "Request failed while connecting to wss://chatgpt.com/backend-api/codex/responses",
            "连接失败；请求失败；https://chatgpt.com/backend-api/wham/apps",
        )
        self.assertEqual(failure_kind, "unreachable_backend")

    def test_note_only_mode_skips_subprocess(self) -> None:
        state = TaskState(
            task_id="note123",
            title="Note only",
            goal="Skip live execution",
            workspace_root="/tmp",
        )
        with patch.dict("os.environ", {"AIWF_EXECUTOR_MODE": "note-only"}, clear=False):
            with patch("swallow.executor.subprocess.run") as mocked_run:
                from swallow.executor import run_executor

                result = run_executor(state, [])

        mocked_run.assert_not_called()
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.failure_kind, "unreachable_backend")
        self.assertIn("non-live mode", result.message)
        self.assertIn("# Executor Fallback Note", result.output)

    def test_unreachable_backend_fallback_includes_connectivity_guidance(self) -> None:
        state = TaskState(
            task_id="net123",
            title="Connectivity failure",
            goal="Classify unreachable backend correctly",
            workspace_root="/tmp",
        )
        unreachable_result = ExecutorResult(
            executor_name="codex",
            status="failed",
            message="Backend connection failed.",
            output="failed to connect to websocket",
            prompt="prompt",
            failure_kind="unreachable_backend",
        )
        note = build_fallback_output(state, [], unreachable_result)
        self.assertIn("outbound network and websocket access", note)
        self.assertIn("backend connectivity", note)

    def test_doctor_codex_missing_binary_returns_nonzero(self) -> None:
        stdout = StringIO()
        with patch("swallow.doctor.shutil.which", return_value=None):
            with redirect_stdout(stdout):
                exit_code = main(["doctor", "codex"])
        self.assertNotEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("binary_found=no", output)
        self.assertIn("launch_ok=no", output)
        self.assertIn("note_only_recommended=yes", output)

    def test_doctor_codex_success_returns_zero(self) -> None:
        stdout = StringIO()
        completed = subprocess.CompletedProcess(
            args=["codex", "--version"],
            returncode=0,
            stdout="codex 1.2.3",
            stderr="",
        )
        with patch("swallow.doctor.shutil.which", return_value="/usr/bin/codex"):
            with patch("swallow.doctor.subprocess.run", return_value=completed):
                with redirect_stdout(stdout):
                    exit_code = main(["doctor", "codex"])
        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("binary_found=yes", output)
        self.assertIn("launch_ok=yes", output)
        self.assertIn("note_only_recommended=no", output)

    def test_task_run_artifact_paths_include_executor_streams(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\nartifact path coverage\n", encoding="utf-8")

            with patch.dict("os.environ", {"AIWF_EXECUTOR_MODE": "mock"}, clear=False):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "task",
                            "create",
                            "--title",
                            "Artifact paths",
                            "--goal",
                            "Ensure artifact_paths include executor streams",
                            "--workspace-root",
                            str(tmp_path),
                        ]
                    ),
                    0,
                )
                task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)
                state = (tmp_path / ".swl" / "tasks" / task_id / "state.json").read_text(encoding="utf-8")

        self.assertIn('"executor_prompt"', state)
        self.assertIn('"executor_output"', state)
        self.assertIn('"executor_stdout"', state)
        self.assertIn('"executor_stderr"', state)
        self.assertIn('"summary"', state)
        self.assertIn('"resume_note"', state)


if __name__ == "__main__":
    unittest.main()
