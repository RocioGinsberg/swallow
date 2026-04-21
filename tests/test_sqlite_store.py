from __future__ import annotations

import asyncio
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
import swallow.store as store_module
from swallow.store import (
    append_event,
    iter_recent_task_events,
    iter_task_states,
    load_events,
    load_state,
    migrate_file_tasks_to_sqlite,
    normalize_store_backend,
    save_state,
)
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
    def test_default_backend_uses_sqlite_with_file_mirror(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            state = _sqlite_state("default-sqlite-task")

            with patch.dict("os.environ", {"SWALLOW_STORE_BACKEND": ""}, clear=False):
                save_state(base_dir, state)
                append_event(
                    base_dir,
                    Event(
                        task_id=state.task_id,
                        event_type="task.created",
                        message="default sqlite write",
                        payload={"status": "created"},
                    ),
                )
                restored = load_state(base_dir, state.task_id)
                events = load_events(base_dir, state.task_id)
                db_exists = swallow_db_path(base_dir).exists()
                state_file_exists = (base_dir / ".swl" / "tasks" / state.task_id / "state.json").exists()
                events_file_exists = (base_dir / ".swl" / "tasks" / state.task_id / "events.jsonl").exists()

        self.assertEqual(normalize_store_backend(None), "sqlite")
        self.assertEqual(restored.task_id, state.task_id)
        self.assertEqual(len(events), 1)
        self.assertTrue(db_exists)
        self.assertTrue(state_file_exists)
        self.assertTrue(events_file_exists)

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

    def test_default_backend_reads_legacy_file_only_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            state = _sqlite_state("legacy-file-task")

            with patch.dict("os.environ", {"SWALLOW_STORE_BACKEND": "file"}, clear=False):
                save_state(base_dir, state)
                append_event(
                    base_dir,
                    Event(
                        task_id=state.task_id,
                        event_type="task.created",
                        message="legacy file write",
                        payload={"status": "created"},
                    ),
                )

            with patch.dict("os.environ", {"SWALLOW_STORE_BACKEND": ""}, clear=False):
                restored = load_state(base_dir, state.task_id)
                events = load_events(base_dir, state.task_id)
                states = list(iter_task_states(base_dir))
                recent = iter_recent_task_events(base_dir, 5)

        self.assertEqual(restored.task_id, state.task_id)
        self.assertEqual(events[0]["message"], "legacy file write")
        self.assertEqual(states[0].task_id, state.task_id)
        self.assertEqual(recent[0][0], state.task_id)

    def test_migrate_file_tasks_to_sqlite_dry_run_does_not_create_db(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            state = _sqlite_state("dry-run-task")

            with patch.dict("os.environ", {"SWALLOW_STORE_BACKEND": "file"}, clear=False):
                save_state(base_dir, state)
                append_event(
                    base_dir,
                    Event(
                        task_id=state.task_id,
                        event_type="task.created",
                        message="dry run candidate",
                        payload={"status": "created"},
                    ),
                )

            summary = migrate_file_tasks_to_sqlite(base_dir, dry_run=True)
            db_exists = swallow_db_path(base_dir).exists()

        self.assertEqual(summary["task_count_scanned"], 1)
        self.assertEqual(summary["task_count_migrated"], 1)
        self.assertEqual(summary["event_count_migrated"], 1)
        self.assertFalse(db_exists)

    def test_migrate_file_tasks_to_sqlite_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            state = _sqlite_state("migrate-task")

            with patch.dict("os.environ", {"SWALLOW_STORE_BACKEND": "file"}, clear=False):
                save_state(base_dir, state)
                append_event(
                    base_dir,
                    Event(
                        task_id=state.task_id,
                        event_type="task.created",
                        message="migrate me",
                        payload={"status": "created"},
                    ),
                )

            first = migrate_file_tasks_to_sqlite(base_dir)
            second = migrate_file_tasks_to_sqlite(base_dir)
            sqlite_store = SqliteTaskStore()
            restored = sqlite_store.load_state(base_dir, state.task_id)
            sqlite_events = sqlite_store.load_events(base_dir, state.task_id)
            state_file_exists = (base_dir / ".swl" / "tasks" / state.task_id / "state.json").exists()

        self.assertEqual(first["task_count_migrated"], 1)
        self.assertEqual(first["event_count_migrated"], 1)
        self.assertEqual(second["task_count_migrated"], 0)
        self.assertEqual(second["task_count_skipped"], 1)
        self.assertEqual(restored.task_id, state.task_id)
        self.assertEqual(len(sqlite_events), 1)
        self.assertTrue(state_file_exists)

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
        self.assertTrue(state_file_exists)

    def test_default_backend_recent_events_only_loads_file_only_tasks_from_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            sqlite_state_1 = _sqlite_state("sqlite-task-1")
            sqlite_state_2 = _sqlite_state("sqlite-task-2")
            file_only_state = _sqlite_state("file-only-task")

            with patch.dict("os.environ", {"SWALLOW_STORE_BACKEND": ""}, clear=False):
                save_state(base_dir, sqlite_state_1)
                append_event(
                    base_dir,
                    Event(
                        task_id=sqlite_state_1.task_id,
                        event_type="task.created",
                        message="sqlite 1",
                        created_at="2026-01-01T00:00:01+00:00",
                    ),
                )
                save_state(base_dir, sqlite_state_2)
                append_event(
                    base_dir,
                    Event(
                        task_id=sqlite_state_2.task_id,
                        event_type="task.created",
                        message="sqlite 2",
                        created_at="2026-01-01T00:00:02+00:00",
                    ),
                )

            with patch.dict("os.environ", {"SWALLOW_STORE_BACKEND": "file"}, clear=False):
                save_state(base_dir, file_only_state)
                append_event(
                    base_dir,
                    Event(
                        task_id=file_only_state.task_id,
                        event_type="task.created",
                        message="file only",
                        created_at="2026-01-01T00:00:03+00:00",
                    ),
                )

            loaded_paths: list[str] = []
            original_load_json_lines = store_module._load_json_lines

            def _spy_load_json_lines(path: Path) -> list[dict[str, object]]:
                loaded_paths.append(path.parent.name)
                return original_load_json_lines(path)

            with patch("swallow.store._load_json_lines", side_effect=_spy_load_json_lines):
                recent = iter_recent_task_events(base_dir, 2)

        self.assertEqual([task_id for task_id, _events in recent], ["file-only-task", "sqlite-task-2"])
        self.assertEqual(loaded_paths, ["file-only-task"])


class RunTaskRuntimeGuardTest(unittest.TestCase):
    def test_run_task_inside_running_loop_has_actionable_error(self) -> None:
        async def exercise() -> None:
            with self.assertRaisesRegex(RuntimeError, "Await run_task_async"):
                run_task(Path("."), "task-in-running-loop")

        asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
