from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.orchestrator import create_task, run_task
from swallow.paths import app_root
from swallow.store import load_state, save_state
from swallow.web.api import (
    build_task_artifact_payload,
    build_task_artifacts_payload,
    build_task_events_payload,
    build_task_knowledge_payload,
    build_task_payload,
    build_tasks_payload,
)


def _tree_checksum(path: Path) -> str:
    if not path.exists():
        return "missing"

    digest = hashlib.sha256()
    for file_path in sorted(item for item in path.rglob("*") if item.is_file()):
        digest.update(file_path.relative_to(path).as_posix().encode("utf-8"))
        digest.update(file_path.read_bytes())
    return digest.hexdigest()


class WebApiPayloadsTest(unittest.TestCase):
    def test_web_api_payloads_are_read_only_and_return_expected_task_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\ncontrol center baseline\n", encoding="utf-8")

            created = create_task(
                base_dir=tmp_path,
                title="Control center task",
                goal="Expose task state through a read-only API",
                workspace_root=tmp_path,
                executor_name="local",
            )
            run_task(tmp_path, created.task_id)

            app_checksum_before = _tree_checksum(app_root(tmp_path))
            tasks_payload = build_tasks_payload(tmp_path, focus="recent")
            task_payload = build_task_payload(tmp_path, created.task_id)
            events_payload = build_task_events_payload(tmp_path, created.task_id)
            artifacts_payload = build_task_artifacts_payload(tmp_path, created.task_id)
            artifact_payload = build_task_artifact_payload(tmp_path, created.task_id, "summary.md")
            knowledge_payload = build_task_knowledge_payload(tmp_path, created.task_id)
            app_checksum_after = _tree_checksum(app_root(tmp_path))

        self.assertEqual(app_checksum_before, app_checksum_after)
        self.assertEqual(tasks_payload["count"], 1)
        self.assertEqual(tasks_payload["tasks"][0]["task_id"], created.task_id)
        self.assertEqual(task_payload["task_id"], created.task_id)
        self.assertEqual(task_payload["status"], "completed")
        self.assertGreater(events_payload["count"], 0)
        self.assertEqual(events_payload["events"][0]["event_type"], "task.created")
        self.assertGreater(artifacts_payload["count"], 0)
        self.assertTrue(any(item["name"] == "summary.md" for item in artifacts_payload["artifacts"]))
        self.assertEqual(artifact_payload["name"], "summary.md")
        self.assertIn("Local summary executor completed.", artifact_payload["content"])
        self.assertEqual(knowledge_payload["task_id"], created.task_id)

    def test_build_tasks_payload_honors_focus_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            created = create_task(
                base_dir=tmp_path,
                title="Created task",
                goal="Stay active",
                workspace_root=tmp_path,
                executor_name="local",
            )
            failed = create_task(
                base_dir=tmp_path,
                title="Failed task",
                goal="Represent failed focus",
                workspace_root=tmp_path,
                executor_name="local",
            )
            failed_state = load_state(tmp_path, failed.task_id)
            failed_state.status = "failed"
            failed_state.phase = "summarize"
            save_state(tmp_path, failed_state)

            active_payload = build_tasks_payload(tmp_path, focus="active")
            failed_payload = build_tasks_payload(tmp_path, focus="failed")

        self.assertEqual([item["task_id"] for item in active_payload["tasks"]], [created.task_id])
        self.assertEqual([item["task_id"] for item in failed_payload["tasks"]], [failed.task_id])

    def test_build_task_artifact_payload_rejects_unknown_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            created = create_task(
                base_dir=tmp_path,
                title="Artifact task",
                goal="Reject missing artifact requests",
                workspace_root=tmp_path,
                executor_name="local",
            )

            with self.assertRaises(FileNotFoundError):
                build_task_artifact_payload(tmp_path, created.task_id, "missing.md")


if __name__ == "__main__":
    unittest.main()
