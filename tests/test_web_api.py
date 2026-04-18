from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.orchestrator import create_task, run_task
from swallow.models import Event
from swallow.paths import app_root
from swallow.store import append_event, load_state, save_state
from swallow.web.api import (
    build_task_artifact_payload,
    build_task_artifacts_payload,
    build_task_events_payload,
    build_task_knowledge_payload,
    build_task_subtask_tree_payload,
    build_task_payload,
    build_tasks_payload,
    create_fastapi_app,
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
    def test_control_center_static_index_contains_dashboard_sections(self) -> None:
        index_path = Path(__file__).resolve().parents[1] / "src" / "swallow" / "web" / "static" / "index.html"
        payload = index_path.read_text(encoding="utf-8")

        self.assertIn("Swallow Control Center", payload)
        self.assertIn("id=\"task-list\"", payload)
        self.assertIn("id=\"event-list\"", payload)
        self.assertIn("id=\"artifact-list\"", payload)
        self.assertIn("/api/tasks?focus=", payload)
        self.assertIn("/api/tasks/${encodeURIComponent(state.selectedTaskId)}/events", payload)
        self.assertIn("/api/tasks/${encodeURIComponent(state.selectedTaskId)}/subtask-tree", payload)
        self.assertIn("Refresh", payload)
        self.assertIn("id=\"subtask-tree-list\"", payload)
        self.assertIn("artifact-left-select", payload)
        self.assertIn("artifact-right-select", payload)
        self.assertIn("artifact-left-content", payload)
        self.assertIn("artifact-right-content", payload)
        self.assertIn("Left Artifact", payload)
        self.assertIn("Right Artifact", payload)

    def test_create_fastapi_app_exposes_root_dashboard_when_optional_dependency_is_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            try:
                app = create_fastapi_app(tmp_path)
            except RuntimeError as exc:
                self.assertIn("FastAPI is required", str(exc))
                return

        route_paths = {getattr(route, "path", "") for route in app.routes}
        self.assertIn("/", route_paths)
        self.assertIn("/api/tasks", route_paths)
        self.assertIn("/api/health", route_paths)
        self.assertIn("/api/tasks/{task_id}/subtask-tree", route_paths)

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
            subtask_tree_payload = build_task_subtask_tree_payload(tmp_path, created.task_id)
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
        self.assertEqual(subtask_tree_payload["task_id"], created.task_id)
        self.assertEqual(subtask_tree_payload["children"], [])

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

            review_needed = create_task(
                base_dir=tmp_path,
                title="Review task",
                goal="Represent needs-review focus",
                workspace_root=tmp_path,
                executor_name="local",
            )
            review_state = load_state(tmp_path, review_needed.task_id)
            review_state.status = "running"
            review_state.phase = "executing"
            review_state.executor_status = "pending"
            save_state(tmp_path, review_state)

            active_payload = build_tasks_payload(tmp_path, focus="active")
            failed_payload = build_tasks_payload(tmp_path, focus="failed")
            review_payload = build_tasks_payload(tmp_path, focus="needs-review")
            all_payload = build_tasks_payload(tmp_path, focus="all")

        self.assertEqual(
            {item["task_id"] for item in active_payload["tasks"]},
            {created.task_id, review_needed.task_id},
        )
        self.assertEqual([item["task_id"] for item in failed_payload["tasks"]], [failed.task_id])
        self.assertEqual(
            {item["task_id"] for item in review_payload["tasks"]},
            {created.task_id, failed.task_id, review_needed.task_id},
        )
        self.assertEqual(
            {item["task_id"] for item in all_payload["tasks"]},
            {created.task_id, failed.task_id, review_needed.task_id},
        )

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

    def test_build_task_artifact_payload_rejects_parent_traversal_segments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            created = create_task(
                base_dir=tmp_path,
                title="Artifact task",
                goal="Reject traversal artifact requests",
                workspace_root=tmp_path,
                executor_name="local",
            )

            with self.assertRaises(ValueError):
                build_task_artifact_payload(tmp_path, created.task_id, "../state.json")

    def test_build_task_subtask_tree_payload_aggregates_subtask_attempts_and_debate_rounds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            created = create_task(
                base_dir=tmp_path,
                title="Subtask tree task",
                goal="Render subtask execution hierarchy",
                workspace_root=tmp_path,
                executor_name="local",
            )

            append_event(
                tmp_path,
                Event(
                    task_id=created.task_id,
                    event_type="task.planned",
                    message="Task planned into runtime task cards.",
                    payload={
                        "card_count": 2,
                        "card_id": "card-a",
                        "card_ids": ["card-a", "card-b"],
                        "subtask_indices": [1, 2],
                    },
                ),
            )
            append_event(
                tmp_path,
                Event(
                    task_id=created.task_id,
                    event_type="subtask.1.execution",
                    message="Subtask 1 execution completed.",
                    payload={
                        "attempt_number": 1,
                        "card_id": "card-a",
                        "goal": "Prepare changes",
                        "subtask_index": 1,
                        "executor_name": "local",
                        "status": "completed",
                    },
                ),
            )
            append_event(
                tmp_path,
                Event(
                    task_id=created.task_id,
                    event_type="subtask.2.execution",
                    message="Subtask 2 execution completed.",
                    payload={
                        "attempt_number": 1,
                        "card_id": "card-b",
                        "goal": "Verify results",
                        "subtask_index": 2,
                        "executor_name": "local",
                        "status": "failed",
                    },
                ),
            )
            append_event(
                tmp_path,
                Event(
                    task_id=created.task_id,
                    event_type="subtask.2.debate_round",
                    message="Review feedback generated for subtask 2 debate round 1.",
                    payload={
                        "card_id": "card-b",
                        "goal": "Verify results",
                        "subtask_index": 2,
                        "round_number": 1,
                    },
                ),
            )
            append_event(
                tmp_path,
                Event(
                    task_id=created.task_id,
                    event_type="subtask.2.execution",
                    message="Subtask 2 execution completed.",
                    payload={
                        "attempt_number": 2,
                        "card_id": "card-b",
                        "goal": "Verify results",
                        "subtask_index": 2,
                        "executor_name": "local",
                        "status": "completed",
                    },
                ),
            )

            payload = build_task_subtask_tree_payload(tmp_path, created.task_id)

        self.assertEqual(payload["task_id"], created.task_id)
        self.assertEqual(len(payload["children"]), 2)
        self.assertEqual(payload["children"][0]["goal"], "Prepare changes")
        self.assertEqual(payload["children"][0]["status"], "completed")
        self.assertEqual(payload["children"][0]["attempts"], 1)
        self.assertEqual(payload["children"][1]["goal"], "Verify results")
        self.assertEqual(payload["children"][1]["status"], "completed")
        self.assertEqual(payload["children"][1]["attempts"], 2)
        self.assertEqual(payload["children"][1]["debate_rounds"], 1)


if __name__ == "__main__":
    unittest.main()
