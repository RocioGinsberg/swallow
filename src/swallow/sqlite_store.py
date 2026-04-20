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

    def load_state(self, base_dir: Path, task_id: str) -> TaskState:
        with self._connect(base_dir) as connection:
            row = connection.execute(
                "SELECT state_json FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        if row is None:
            raise FileNotFoundError(f"No task state found for task_id={task_id}")
        payload = json.loads(str(row["state_json"]))
        return TaskState.from_dict(payload)

    def iter_task_states(self, base_dir: Path) -> Iterable[TaskState]:
        with self._connect(base_dir) as connection:
            rows = connection.execute(
                "SELECT state_json FROM tasks ORDER BY updated_at DESC, task_id DESC"
            ).fetchall()
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

    def load_events(self, base_dir: Path, task_id: str) -> list[dict[str, object]]:
        with self._connect(base_dir) as connection:
            rows = connection.execute(
                """
                SELECT event_json
                FROM events
                WHERE task_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (task_id,),
            ).fetchall()
        return [dict(json.loads(str(row["event_json"]))) for row in rows]

    def iter_recent_task_events(self, base_dir: Path, last_n: int) -> list[tuple[str, list[dict[str, object]]]]:
        if last_n <= 0:
            return []
        with self._connect(base_dir) as connection:
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
        return [(str(row["task_id"]), self.load_events(base_dir, str(row["task_id"]))) for row in rows]
