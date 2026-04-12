from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.dispatch_policy import validate_handoff_semantics
from swallow.orchestrator import create_task, run_task
from swallow.store import load_state, save_state


class DispatchPolicyTest(unittest.TestCase):
    def test_validate_handoff_semantics_accepts_existing_relative_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_dir = tmp_path / ".swl" / "tasks" / "task-relative-pointer"
            artifacts_dir = task_dir / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            (artifacts_dir / "dispatch_report.md").write_text("dispatch ok\n", encoding="utf-8")

            result = validate_handoff_semantics(
                {"context_pointers": ["dispatch_report.md"]},
                task_dir,
            )

        self.assertTrue(result.valid)
        self.assertEqual(result.errors, [])

    def test_validate_handoff_semantics_rejects_missing_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_dir = tmp_path / ".swl" / "tasks" / "task-missing-pointer"
            task_dir.mkdir(parents=True, exist_ok=True)

            result = validate_handoff_semantics(
                {"context_pointers": ["missing-artifact.md"]},
                task_dir,
            )

        self.assertFalse(result.valid)
        self.assertEqual(result.errors, ["context pointer not found: missing-artifact.md"])

    def test_validate_handoff_semantics_allows_empty_context_pointers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_dir = tmp_path / ".swl" / "tasks" / "task-empty-pointers"
            task_dir.mkdir(parents=True, exist_ok=True)

            result = validate_handoff_semantics(
                {"context_pointers": []},
                task_dir,
            )

        self.assertTrue(result.valid)
        self.assertEqual(result.errors, [])

    def test_run_task_blocks_remote_dispatch_when_context_pointer_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Semantic validation block",
                goal="Block mock remote dispatch when context pointers are dead links",
                workspace_root=tmp_path,
            )
            task_dir = tmp_path / ".swl" / "tasks" / state.task_id
            persisted = load_state(tmp_path, state.task_id)
            persisted.artifact_paths["task_semantics_json"] = "missing-artifact.md"
            save_state(tmp_path, persisted)

            final_state = run_task(tmp_path, state.task_id, executor_name="mock-remote")
            events = [
                json.loads(line)
                for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(final_state.status, "dispatch_blocked")
        self.assertEqual(final_state.phase, "dispatch")
        self.assertEqual(events[-1]["event_type"], "task.dispatch_blocked")
        self.assertEqual(events[-1]["payload"]["dispatch_verdict"]["action"], "blocked")
        self.assertEqual(
            events[-1]["payload"]["dispatch_verdict"]["reason"],
            "remote handoff contract failed semantic validation",
        )
        self.assertIn("context pointer not found: missing-artifact.md", events[-1]["payload"]["dispatch_verdict"]["blocking_detail"])
