from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.execution_budget_policy import calculate_task_token_cost
from swallow.meta_optimizer import build_meta_optimizer_snapshot
from swallow.models import Event, TaskState
from swallow.orchestrator import create_task, run_task
from swallow.paths import swallow_db_path
from swallow.sqlite_store import SqliteTaskStore
from swallow.store import append_event, load_events, load_state
from swallow.web.api import build_task_events_payload, build_tasks_payload


def _sqlite_state(task_id: str = "sqlite-task") -> TaskState:
    return TaskState(
        task_id=task_id,
        title="SQLite state",
        goal="Round-trip task state through the sqlite backend",
        workspace_root="/tmp/workspace",
        executor_name="local",
        route_name="local-summary",
        route_executor_family="cli",
    )


class SqliteTaskStoreTest(unittest.TestCase):
    def test_sqlite_task_store_round_trips_state_and_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            store = SqliteTaskStore()
            state = _sqlite_state()

            store.save_state(base_dir, state)
            store.append_event(
                base_dir,
                Event(
                    task_id=state.task_id,
                    event_type="task.created",
                    message="sqlite created",
                    payload={"status": "created"},
                ),
            )

            restored = store.load_state(base_dir, state.task_id)
            events = store.load_events(base_dir, state.task_id)
            recent = store.iter_recent_task_events(base_dir, 10)
            all_states = list(store.iter_task_states(base_dir))

            self.assertEqual(restored.task_id, state.task_id)
            self.assertEqual(len(all_states), 1)
            self.assertEqual(all_states[0].task_id, state.task_id)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["event_type"], "task.created")
            self.assertEqual(recent[0][0], state.task_id)
            self.assertEqual(recent[0][1][0]["message"], "sqlite created")
            self.assertTrue(swallow_db_path(base_dir).exists())

            with sqlite3.connect(swallow_db_path(base_dir)) as connection:
                journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0]).lower()

        self.assertEqual(journal_mode, "wal")

    def test_sqlite_backend_keeps_event_only_budget_scans_working(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            with patch.dict("os.environ", {"SWALLOW_STORE_BACKEND": "sqlite"}, clear=False):
                append_event(
                    base_dir,
                    Event(
                        task_id="event-only-task",
                        event_type="executor.completed",
                        message="seed cost",
                        payload={"token_cost": 0.42},
                    ),
                )
                append_event(
                    base_dir,
                    Event(
                        task_id="event-only-task",
                        event_type="task.execution_fallback",
                        message="ignored fallback cost",
                        payload={"token_cost": 9.99},
                    ),
                )
                token_cost = calculate_task_token_cost(base_dir, "event-only-task")
                events = load_events(base_dir, "event-only-task")
                db_exists = swallow_db_path(base_dir).exists()

        self.assertAlmostEqual(token_cost, 0.42)
        self.assertEqual(len(events), 2)
        self.assertTrue(db_exists)

    def test_sqlite_backend_supports_create_run_and_operator_reads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            with patch.dict("os.environ", {"SWALLOW_STORE_BACKEND": "sqlite"}, clear=False):
                created = create_task(
                    base_dir=base_dir,
                    title="SQLite run task",
                    goal="Execute a task with sqlite state storage",
                    workspace_root=base_dir,
                    executor_name="local",
                )
                final_state = run_task(base_dir, created.task_id, executor_name="local")
                persisted = load_state(base_dir, created.task_id)
                tasks_payload = build_tasks_payload(base_dir, focus="all")
                events_payload = build_task_events_payload(base_dir, created.task_id)
                snapshot = build_meta_optimizer_snapshot(base_dir, last_n=10)
                state_file_exists = (base_dir / ".swl" / "tasks" / created.task_id / "state.json").exists()
                db_exists = swallow_db_path(base_dir).exists()

        self.assertEqual(final_state.status, "completed")
        self.assertEqual(persisted.status, "completed")
        self.assertEqual(tasks_payload["count"], 1)
        self.assertEqual(tasks_payload["tasks"][0]["task_id"], created.task_id)
        self.assertGreater(events_payload["count"], 0)
        self.assertIn(created.task_id, snapshot.scanned_task_ids)
        self.assertTrue(db_exists)
        self.assertFalse(state_file_exists)


if __name__ == "__main__":
    unittest.main()
