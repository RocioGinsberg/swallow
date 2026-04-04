from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_workflow_codex_bootstrap.cli import main


class CliLifecycleTest(unittest.TestCase):
    def test_task_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\norchestrator harness task memory\n", encoding="utf-8")

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

            tasks_dir = tmp_path / ".aiwf" / "tasks"
            created = [entry.name for entry in tasks_dir.iterdir() if entry.is_dir()]
            self.assertEqual(len(created), 1)
            task_id = created[0]

            exit_code = main(["--base-dir", str(tmp_path), "task", "run", task_id])
            self.assertEqual(exit_code, 0)

            summary = (tasks_dir / task_id / "artifacts" / "summary.md").read_text(encoding="utf-8")
            handoff = (tasks_dir / task_id / "artifacts" / "handoff.md").read_text(encoding="utf-8")

            self.assertIn("Summary for", summary)
            self.assertIn("notes.md", summary)
            self.assertIn("Handoff for", handoff)


if __name__ == "__main__":
    unittest.main()
