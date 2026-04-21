from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .models import Event, TaskState, utc_now
from .paths import app_root, artifacts_dir, swallow_db_path, task_root, tasks_root


CREATE_TASKS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    state_json TEXT NOT NULL,
    status TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

CREATE_EVENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    event_json TEXT NOT NULL,
    kind TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
)
"""

CREATE_EVENTS_TASK_INDEX_SQL = "CREATE INDEX IF NOT EXISTS idx_events_task_id ON events(task_id)"
CREATE_TASKS_STATUS_INDEX_SQL = "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)"


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


class SqliteTaskStore:
    def _ensure_layout(self, base_dir: Path, task_id: str = "") -> None:
        app_root(base_dir).mkdir(parents=True, exist_ok=True)
        tasks_root(base_dir).mkdir(parents=True, exist_ok=True)
        if task_id:
            task_root(base_dir, task_id).mkdir(parents=True, exist_ok=True)
            artifacts_dir(base_dir, task_id).mkdir(parents=True, exist_ok=True)

    def _connect(self, base_dir: Path) -> sqlite3.Connection:
        self._ensure_layout(base_dir)
        connection = sqlite3.connect(swallow_db_path(base_dir), timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute(CREATE_TASKS_TABLE_SQL)
        connection.execute(CREATE_EVENTS_TABLE_SQL)
        connection.execute(CREATE_EVENTS_TASK_INDEX_SQL)
        connection.execute(CREATE_TASKS_STATUS_INDEX_SQL)
        return connection

    def _connect_existing(self, base_dir: Path) -> sqlite3.Connection | None:
        db_path = swallow_db_path(base_dir)
        if not db_path.exists():
            return None
        connection = sqlite3.connect(f"file:{db_path}?mode=ro&immutable=1", timeout=5.0, uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _checkpoint(self, base_dir: Path) -> None:
        db_path = swallow_db_path(base_dir)
        if not db_path.exists():
            return
        with sqlite3.connect(db_path, timeout=5.0) as connection:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    def save_state(self, base_dir: Path, state: TaskState) -> None:
        self._ensure_layout(base_dir, state.task_id)
        state.updated_at = utc_now()
        payload = json.dumps(state.to_dict(), indent=2)
        with self._connect(base_dir) as connection:
            connection.execute(
                """
                INSERT INTO tasks (task_id, state_json, status, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    state_json = excluded.state_json,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                (
                    state.task_id,
                    payload,
                    state.status,
                    state.updated_at,
                ),
            )
        self._checkpoint(base_dir)

    def load_state(self, base_dir: Path, task_id: str) -> TaskState:
        connection = self._connect_existing(base_dir)
        if connection is None:
            raise FileNotFoundError(f"No task state found for task_id={task_id}")
        try:
            if not _table_exists(connection, "tasks"):
                raise FileNotFoundError(f"No task state found for task_id={task_id}")
            row = connection.execute(
                "SELECT state_json FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise FileNotFoundError(f"No task state found for task_id={task_id}")
        payload = json.loads(str(row["state_json"]))
        return TaskState.from_dict(payload)

    def iter_task_states(self, base_dir: Path) -> Iterable[TaskState]:
        connection = self._connect_existing(base_dir)
        if connection is None:
            return []
        try:
            if not _table_exists(connection, "tasks"):
                return []
            rows = connection.execute(
                "SELECT state_json FROM tasks ORDER BY updated_at DESC, task_id DESC"
            ).fetchall()
        finally:
            connection.close()
        return [TaskState.from_dict(json.loads(str(row["state_json"]))) for row in rows]

    def append_event(self, base_dir: Path, event: Event) -> None:
        self._ensure_layout(base_dir, event.task_id)
        payload = json.dumps(event.to_dict())
        with self._connect(base_dir) as connection:
            connection.execute(
                """
                INSERT INTO events (task_id, event_json, kind, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    event.task_id,
                    payload,
                    event.event_type,
                    event.created_at,
                ),
            )
        self._checkpoint(base_dir)

    def load_events(self, base_dir: Path, task_id: str) -> list[dict[str, object]]:
        connection = self._connect_existing(base_dir)
        if connection is None:
            return []
        try:
            if not _table_exists(connection, "events"):
                return []
            rows = connection.execute(
                """
                SELECT event_json
                FROM events
                WHERE task_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (task_id,),
            ).fetchall()
        finally:
            connection.close()
        return [dict(json.loads(str(row["event_json"]))) for row in rows]

    def iter_recent_task_events(self, base_dir: Path, last_n: int) -> list[tuple[str, list[dict[str, object]]]]:
        if last_n <= 0:
            return []
        connection = self._connect_existing(base_dir)
        if connection is None:
            return []
        try:
            if not _table_exists(connection, "events"):
                return []
            rows = connection.execute(
                """
                SELECT task_id, MAX(created_at) AS last_event_at
                FROM events
                GROUP BY task_id
                ORDER BY last_event_at DESC, task_id DESC
                LIMIT ?
                """,
                (last_n,),
            ).fetchall()
        finally:
            connection.close()
        return [(str(row["task_id"]), self.load_events(base_dir, str(row["task_id"]))) for row in rows]

    def task_exists(self, base_dir: Path, task_id: str) -> bool:
        connection = self._connect_existing(base_dir)
        if connection is None:
            return False
        try:
            if not _table_exists(connection, "tasks"):
                return False
            row = connection.execute(
                "SELECT 1 FROM tasks WHERE task_id = ? LIMIT 1",
                (task_id,),
            ).fetchone()
            return row is not None
        finally:
            connection.close()

    def event_count(self, base_dir: Path, task_id: str) -> int:
        connection = self._connect_existing(base_dir)
        if connection is None:
            return 0
        try:
            if not _table_exists(connection, "events"):
                return 0
            row = connection.execute(
                "SELECT COUNT(*) FROM events WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            return int(row[0]) if row is not None else 0
        finally:
            connection.close()

    def database_health(self, base_dir: Path) -> dict[str, object]:
        db_path = swallow_db_path(base_dir)
        if not db_path.exists():
            return {
                "db_path": str(db_path),
                "db_exists": False,
                "schema_ok": False,
                "tasks_table": False,
                "events_table": False,
                "task_count": 0,
                "event_count": 0,
                "integrity_ok": False,
                "details": "SQLite database has not been created yet.",
            }

        try:
            with sqlite3.connect(db_path, timeout=5.0) as connection:
                connection.row_factory = sqlite3.Row
                tasks_table = _table_exists(connection, "tasks")
                events_table = _table_exists(connection, "events")
                task_count = (
                    int(connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0])
                    if tasks_table
                    else 0
                )
                event_count = (
                    int(connection.execute("SELECT COUNT(*) FROM events").fetchone()[0])
                    if events_table
                    else 0
                )
                integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        except sqlite3.Error as exc:
            return {
                "db_path": str(db_path),
                "db_exists": True,
                "schema_ok": False,
                "tasks_table": False,
                "events_table": False,
                "task_count": 0,
                "event_count": 0,
                "integrity_ok": False,
                "details": str(exc),
            }

        return {
            "db_path": str(db_path),
            "db_exists": True,
            "schema_ok": tasks_table and events_table,
            "tasks_table": tasks_table,
            "events_table": events_table,
            "task_count": task_count,
            "event_count": event_count,
            "integrity_ok": integrity == "ok",
            "details": integrity,
        }
