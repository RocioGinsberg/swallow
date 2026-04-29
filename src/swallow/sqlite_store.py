from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from .identity import local_actor
from .knowledge_store import (
    enforce_canonical_knowledge_write_authority,
    normalize_task_knowledge_view,
    split_task_knowledge_view,
)
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
    created_at TEXT NOT NULL
)
"""

CREATE_EVENTS_TASK_INDEX_SQL = "CREATE INDEX IF NOT EXISTS idx_events_task_id ON events(task_id)"
CREATE_TASKS_STATUS_INDEX_SQL = "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)"
CREATE_KNOWLEDGE_EVIDENCE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS knowledge_evidence (
    task_id TEXT NOT NULL,
    object_id TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    entry_json TEXT NOT NULL,
    stage TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    embedding_blob BLOB,
    PRIMARY KEY (task_id, object_id)
)
"""
CREATE_KNOWLEDGE_WIKI_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS knowledge_wiki (
    task_id TEXT NOT NULL,
    entry_id TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    entry_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    embedding_blob BLOB,
    PRIMARY KEY (task_id, entry_id)
)
"""
CREATE_KNOWLEDGE_EVIDENCE_TASK_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_knowledge_evidence_task_id ON knowledge_evidence(task_id, sort_order)"
)
CREATE_KNOWLEDGE_WIKI_TASK_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_knowledge_wiki_task_id ON knowledge_wiki(task_id, sort_order)"
)
CREATE_KNOWLEDGE_MIGRATIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS knowledge_migrations (
    task_id TEXT PRIMARY KEY,
    migration_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""
CREATE_KNOWLEDGE_RELATIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS knowledge_relations (
    relation_id TEXT PRIMARY KEY,
    source_object_id TEXT NOT NULL,
    target_object_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    context TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'operator'
)
"""
CREATE_KNOWLEDGE_RELATIONS_SOURCE_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_knowledge_relations_source ON knowledge_relations(source_object_id)"
)
CREATE_KNOWLEDGE_RELATIONS_TARGET_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_knowledge_relations_target ON knowledge_relations(target_object_id)"
)
CREATE_KNOWLEDGE_RELATIONS_TYPE_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_knowledge_relations_type ON knowledge_relations(relation_type)"
)
CREATE_EVENT_LOG_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS event_log (
    event_id TEXT PRIMARY KEY,
    task_id TEXT,
    timestamp TEXT NOT NULL,
    actor TEXT NOT NULL DEFAULT 'local',
    kind TEXT NOT NULL,
    payload TEXT NOT NULL
)
"""
CREATE_EVENT_TELEMETRY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS event_telemetry (
    telemetry_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    step_id TEXT,
    executor_id TEXT NOT NULL,
    logical_path TEXT NOT NULL,
    physical_route TEXT,
    latency_ms INTEGER,
    token_input INTEGER,
    token_output INTEGER,
    cost_usd REAL,
    degraded INTEGER NOT NULL DEFAULT 0,
    error_code TEXT,
    timestamp TEXT NOT NULL,
    actor TEXT NOT NULL DEFAULT 'local'
)
"""
CREATE_ROUTE_HEALTH_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS route_health (
    health_id TEXT PRIMARY KEY,
    route_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    status TEXT NOT NULL,
    error_code TEXT,
    sample_size INTEGER
)
"""
CREATE_KNOW_CHANGE_LOG_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS know_change_log (
    change_id TEXT PRIMARY KEY,
    target_kind TEXT NOT NULL,
    target_id TEXT NOT NULL,
    action TEXT NOT NULL,
    rationale TEXT,
    timestamp TEXT NOT NULL,
    actor TEXT NOT NULL
)
"""
CREATE_ROUTE_REGISTRY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS route_registry (
    route_id TEXT PRIMARY KEY,
    model_family TEXT NOT NULL,
    model_hint TEXT NOT NULL,
    dialect_hint TEXT,
    backend_kind TEXT NOT NULL,
    transport_kind TEXT,
    fallback_route_id TEXT,
    quality_weight REAL NOT NULL DEFAULT 1.0,
    unsupported_task_types TEXT NOT NULL DEFAULT '[]',
    cost_profile TEXT NOT NULL DEFAULT 'null',
    updated_at TEXT NOT NULL,
    updated_by TEXT NOT NULL,
    capabilities_json TEXT NOT NULL DEFAULT '{}',
    taxonomy_json TEXT NOT NULL DEFAULT '{}',
    execution_site TEXT NOT NULL,
    executor_family TEXT NOT NULL,
    executor_name TEXT NOT NULL,
    remote_capable INTEGER NOT NULL DEFAULT 0
)
"""
CREATE_POLICY_RECORDS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS policy_records (
    policy_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    scope TEXT NOT NULL,
    scope_value TEXT,
    payload TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    updated_by TEXT NOT NULL
)
"""
CREATE_ROUTE_CHANGE_LOG_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS route_change_log (
    change_id TEXT PRIMARY KEY,
    proposal_id TEXT,
    target_kind TEXT NOT NULL,
    target_id TEXT,
    action TEXT NOT NULL,
    before_payload TEXT,
    after_payload TEXT,
    timestamp TEXT NOT NULL,
    actor TEXT NOT NULL DEFAULT 'local'
)
"""
CREATE_POLICY_CHANGE_LOG_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS policy_change_log (
    change_id TEXT PRIMARY KEY,
    proposal_id TEXT,
    target_kind TEXT NOT NULL,
    target_id TEXT,
    action TEXT NOT NULL,
    before_payload TEXT,
    after_payload TEXT,
    timestamp TEXT NOT NULL,
    actor TEXT NOT NULL DEFAULT 'local'
)
"""
CREATE_SCHEMA_VERSION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL,
    slug TEXT NOT NULL
)
"""
CREATE_EVENT_LOG_TASK_TIME_INDEX_SQL = "CREATE INDEX IF NOT EXISTS idx_event_task_time ON event_log(task_id, timestamp)"
CREATE_EVENT_LOG_KIND_TIME_INDEX_SQL = "CREATE INDEX IF NOT EXISTS idx_event_kind_time ON event_log(kind, timestamp)"
CREATE_POLICY_RECORDS_KIND_SCOPE_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_policy_records_kind_scope ON policy_records(kind, scope, scope_value)"
)
APPEND_ONLY_TABLES = (
    "event_log",
    "event_telemetry",
    "route_health",
    "know_change_log",
    "route_change_log",
    "policy_change_log",
)
APPEND_ONLY_TRIGGER_SQLS = tuple(
    sql
    for table in APPEND_ONLY_TABLES
    for sql in (
        f"""
        CREATE TRIGGER IF NOT EXISTS {table}_no_update
        BEFORE UPDATE ON {table}
        BEGIN SELECT RAISE(FAIL, '{table} is append-only'); END
        """,
        f"""
        CREATE TRIGGER IF NOT EXISTS {table}_no_delete
        BEFORE DELETE ON {table}
        BEGIN SELECT RAISE(FAIL, '{table} is append-only'); END
        """,
    )
)
EXPECTED_SCHEMA_VERSION = 1
SCHEMA_VERSION_SLUG = "phase65_initial"
_CONNECTION_CACHE: dict[str, sqlite3.Connection] = {}


def _knowledge_entry_id(payload: dict[str, object]) -> str:
    for key in ("object_id", "source_object_id", "canonical_id"):
        value = str(payload.get(key, "")).strip()
        if value:
            return value
    return "knowledge-entry"


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _connection_cache_key(base_dir: Path) -> str:
    return str(base_dir)


def _ensure_schema_version(connection: sqlite3.Connection) -> None:
    row = connection.execute("SELECT MAX(version) AS version FROM schema_version").fetchone()
    current_version = int(row["version"] or 0) if row is not None else 0
    if current_version < EXPECTED_SCHEMA_VERSION:
        connection.execute(
            """
            INSERT OR IGNORE INTO schema_version (version, applied_at, slug)
            VALUES (?, ?, ?)
            """,
            (EXPECTED_SCHEMA_VERSION, utc_now(), SCHEMA_VERSION_SLUG),
        )


def _initialize_schema(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute(CREATE_TASKS_TABLE_SQL)
    connection.execute(CREATE_EVENTS_TABLE_SQL)
    connection.execute(CREATE_EVENTS_TASK_INDEX_SQL)
    connection.execute(CREATE_TASKS_STATUS_INDEX_SQL)
    connection.execute(CREATE_KNOWLEDGE_EVIDENCE_TABLE_SQL)
    connection.execute(CREATE_KNOWLEDGE_WIKI_TABLE_SQL)
    connection.execute(CREATE_KNOWLEDGE_EVIDENCE_TASK_INDEX_SQL)
    connection.execute(CREATE_KNOWLEDGE_WIKI_TASK_INDEX_SQL)
    connection.execute(CREATE_KNOWLEDGE_MIGRATIONS_TABLE_SQL)
    connection.execute(CREATE_KNOWLEDGE_RELATIONS_TABLE_SQL)
    connection.execute(CREATE_KNOWLEDGE_RELATIONS_SOURCE_INDEX_SQL)
    connection.execute(CREATE_KNOWLEDGE_RELATIONS_TARGET_INDEX_SQL)
    connection.execute(CREATE_KNOWLEDGE_RELATIONS_TYPE_INDEX_SQL)
    connection.execute(CREATE_EVENT_LOG_TABLE_SQL)
    connection.execute(CREATE_EVENT_TELEMETRY_TABLE_SQL)
    connection.execute(CREATE_ROUTE_HEALTH_TABLE_SQL)
    connection.execute(CREATE_KNOW_CHANGE_LOG_TABLE_SQL)
    connection.execute(CREATE_ROUTE_REGISTRY_TABLE_SQL)
    connection.execute(CREATE_POLICY_RECORDS_TABLE_SQL)
    connection.execute(CREATE_ROUTE_CHANGE_LOG_TABLE_SQL)
    connection.execute(CREATE_POLICY_CHANGE_LOG_TABLE_SQL)
    connection.execute(CREATE_SCHEMA_VERSION_TABLE_SQL)
    connection.execute(CREATE_EVENT_LOG_TASK_TIME_INDEX_SQL)
    connection.execute(CREATE_EVENT_LOG_KIND_TIME_INDEX_SQL)
    connection.execute(CREATE_POLICY_RECORDS_KIND_SCOPE_INDEX_SQL)
    _ensure_schema_version(connection)
    for trigger_sql in APPEND_ONLY_TRIGGER_SQLS:
        connection.execute(trigger_sql)


def get_connection(base_dir: Path) -> sqlite3.Connection:
    """Return the process-local route/policy SQLite connection for base_dir.

    This connection runs in autocommit mode so Repository methods can own
    explicit BEGIN IMMEDIATE / COMMIT / ROLLBACK transaction lifecycles.
    """

    key = _connection_cache_key(base_dir)
    cached = _CONNECTION_CACHE.get(key)
    if cached is not None:
        return cached
    store = SqliteTaskStore()
    store._ensure_layout(base_dir)
    connection = sqlite3.connect(
        swallow_db_path(base_dir),
        timeout=5.0,
        isolation_level=None,
        check_same_thread=False,
    )
    connection.row_factory = sqlite3.Row
    _initialize_schema(connection)
    _CONNECTION_CACHE[key] = connection
    return connection


def get_schema_status(base_dir: Path) -> dict[str, int]:
    connection = get_connection(base_dir)
    row = connection.execute("SELECT MAX(version) AS version FROM schema_version").fetchone()
    current_version = int(row["version"] or 0) if row is not None else 0
    return {
        "schema_version": current_version,
        "expected_schema_version": EXPECTED_SCHEMA_VERSION,
        "pending": max(EXPECTED_SCHEMA_VERSION - current_version, 0),
    }


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
        _initialize_schema(connection)
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
            connection.execute("PRAGMA wal_checkpoint(PASSIVE)")

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
            connection.execute(
                """
                INSERT INTO event_log (event_id, task_id, timestamp, actor, kind, payload)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    f"event-{uuid4().hex}",
                    event.task_id,
                    event.created_at,
                    local_actor(),
                    event.event_type,
                    json.dumps(event.payload),
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

    def replace_task_knowledge(
        self,
        base_dir: Path,
        task_id: str,
        knowledge_objects: list[dict[str, object]],
        *,
        write_authority: str = "task-state",
    ) -> list[dict[str, object]]:
        self._ensure_layout(base_dir, task_id)
        normalized_view = normalize_task_knowledge_view(knowledge_objects)
        enforce_canonical_knowledge_write_authority(normalized_view, write_authority=write_authority)
        evidence_entries, wiki_entries = split_task_knowledge_view(normalized_view)
        sort_order_by_id = {
            _knowledge_entry_id(entry): position
            for position, entry in enumerate(normalized_view)
        }
        updated_at = utc_now()

        with self._connect(base_dir) as connection:
            connection.execute("DELETE FROM knowledge_evidence WHERE task_id = ?", (task_id,))
            connection.execute("DELETE FROM knowledge_wiki WHERE task_id = ?", (task_id,))
            if evidence_entries:
                connection.executemany(
                    """
                    INSERT INTO knowledge_evidence (
                        task_id,
                        object_id,
                        sort_order,
                        entry_json,
                        stage,
                        updated_at,
                        embedding_blob
                    )
                    VALUES (?, ?, ?, ?, ?, ?, NULL)
                    """,
                    [
                        (
                            task_id,
                            _knowledge_entry_id(entry),
                            sort_order_by_id.get(_knowledge_entry_id(entry), 0),
                            json.dumps(entry, indent=2),
                            str(entry.get("stage", "raw")).strip() or "raw",
                            updated_at,
                        )
                        for entry in evidence_entries
                    ],
                )
            if wiki_entries:
                connection.executemany(
                    """
                    INSERT INTO knowledge_wiki (
                        task_id,
                        entry_id,
                        sort_order,
                        entry_json,
                        updated_at,
                        embedding_blob
                    )
                    VALUES (?, ?, ?, ?, ?, NULL)
                    """,
                    [
                        (
                            task_id,
                            _knowledge_entry_id(entry),
                            sort_order_by_id.get(_knowledge_entry_id(entry), 0),
                            json.dumps(entry, indent=2),
                            updated_at,
                        )
                        for entry in wiki_entries
                    ],
                )
        self._checkpoint(base_dir)
        return normalized_view

    def load_task_knowledge_view(self, base_dir: Path, task_id: str) -> list[dict[str, object]]:
        connection = self._connect_existing(base_dir)
        if connection is None:
            return []
        try:
            evidence_table = _table_exists(connection, "knowledge_evidence")
            wiki_table = _table_exists(connection, "knowledge_wiki")
            if not evidence_table and not wiki_table:
                return []

            entries: list[tuple[int, dict[str, object]]] = []
            if evidence_table:
                evidence_rows = connection.execute(
                    """
                    SELECT sort_order, entry_json
                    FROM knowledge_evidence
                    WHERE task_id = ?
                    ORDER BY sort_order ASC, object_id ASC
                    """,
                    (task_id,),
                ).fetchall()
                entries.extend(
                    (
                        int(row["sort_order"]),
                        dict(json.loads(str(row["entry_json"]))),
                    )
                    for row in evidence_rows
                )
            if wiki_table:
                wiki_rows = connection.execute(
                    """
                    SELECT sort_order, entry_json
                    FROM knowledge_wiki
                    WHERE task_id = ?
                    ORDER BY sort_order ASC, entry_id ASC
                    """,
                    (task_id,),
                ).fetchall()
                entries.extend(
                    (
                        int(row["sort_order"]),
                        dict(json.loads(str(row["entry_json"]))),
                    )
                    for row in wiki_rows
                )
        finally:
            connection.close()
        entries.sort(key=lambda item: item[0])
        return normalize_task_knowledge_view([payload for _, payload in entries])

    def task_has_knowledge(self, base_dir: Path, task_id: str) -> bool:
        connection = self._connect_existing(base_dir)
        if connection is None:
            return False
        try:
            evidence_table = _table_exists(connection, "knowledge_evidence")
            wiki_table = _table_exists(connection, "knowledge_wiki")
            if evidence_table:
                row = connection.execute(
                    "SELECT 1 FROM knowledge_evidence WHERE task_id = ? LIMIT 1",
                    (task_id,),
                ).fetchone()
                if row is not None:
                    return True
            if wiki_table:
                row = connection.execute(
                    "SELECT 1 FROM knowledge_wiki WHERE task_id = ? LIMIT 1",
                    (task_id,),
                ).fetchone()
                if row is not None:
                    return True
            return False
        finally:
            connection.close()

    def iter_knowledge_task_ids(self, base_dir: Path) -> list[str]:
        connection = self._connect_existing(base_dir)
        if connection is None:
            return []
        try:
            evidence_table = _table_exists(connection, "knowledge_evidence")
            wiki_table = _table_exists(connection, "knowledge_wiki")
            task_ids: set[str] = set()
            if evidence_table:
                rows = connection.execute("SELECT DISTINCT task_id FROM knowledge_evidence").fetchall()
                task_ids.update(str(row["task_id"]) for row in rows)
            if wiki_table:
                rows = connection.execute("SELECT DISTINCT task_id FROM knowledge_wiki").fetchall()
                task_ids.update(str(row["task_id"]) for row in rows)
            return sorted(task_ids)
        finally:
            connection.close()

    def delete_task_knowledge(self, base_dir: Path, task_id: str) -> None:
        with self._connect(base_dir) as connection:
            connection.execute("DELETE FROM knowledge_evidence WHERE task_id = ?", (task_id,))
            connection.execute("DELETE FROM knowledge_wiki WHERE task_id = ?", (task_id,))
        self._checkpoint(base_dir)

    def knowledge_object_exists(self, base_dir: Path, object_id: str) -> bool:
        normalized_id = str(object_id).strip()
        if not normalized_id:
            return False
        connection = self._connect_existing(base_dir)
        if connection is None:
            return False
        try:
            evidence_table = _table_exists(connection, "knowledge_evidence")
            wiki_table = _table_exists(connection, "knowledge_wiki")
            if evidence_table:
                row = connection.execute(
                    "SELECT 1 FROM knowledge_evidence WHERE object_id = ? LIMIT 1",
                    (normalized_id,),
                ).fetchone()
                if row is not None:
                    return True
            if wiki_table:
                row = connection.execute(
                    "SELECT 1 FROM knowledge_wiki WHERE entry_id = ? LIMIT 1",
                    (normalized_id,),
                ).fetchone()
                if row is not None:
                    return True
            return False
        finally:
            connection.close()

    def create_knowledge_relation(
        self,
        base_dir: Path,
        relation: dict[str, object],
    ) -> dict[str, object]:
        payload = dict(relation)
        with self._connect(base_dir) as connection:
            connection.execute(
                """
                INSERT INTO knowledge_relations (
                    relation_id,
                    source_object_id,
                    target_object_id,
                    relation_type,
                    confidence,
                    context,
                    created_at,
                    created_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(payload.get("relation_id", "")).strip(),
                    str(payload.get("source_object_id", "")).strip(),
                    str(payload.get("target_object_id", "")).strip(),
                    str(payload.get("relation_type", "")).strip(),
                    float(payload.get("confidence", 1.0)),
                    str(payload.get("context", "")).strip(),
                    str(payload.get("created_at", "")).strip(),
                    str(payload.get("created_by", "operator")).strip() or "operator",
                ),
            )
        self._checkpoint(base_dir)
        return payload

    def delete_knowledge_relation(self, base_dir: Path, relation_id: str) -> bool:
        normalized_id = str(relation_id).strip()
        if not normalized_id:
            return False
        with self._connect(base_dir) as connection:
            cursor = connection.execute(
                "DELETE FROM knowledge_relations WHERE relation_id = ?",
                (normalized_id,),
            )
        self._checkpoint(base_dir)
        return int(cursor.rowcount) > 0

    def list_knowledge_relations(self, base_dir: Path, object_id: str) -> list[dict[str, object]]:
        normalized_id = str(object_id).strip()
        if not normalized_id:
            return []
        connection = self._connect_existing(base_dir)
        if connection is None:
            return []
        try:
            if not _table_exists(connection, "knowledge_relations"):
                return []
            rows = connection.execute(
                """
                SELECT
                    relation_id,
                    source_object_id,
                    target_object_id,
                    relation_type,
                    confidence,
                    context,
                    created_at,
                    created_by
                FROM knowledge_relations
                WHERE source_object_id = ? OR target_object_id = ?
                ORDER BY created_at ASC, relation_id ASC
                """,
                (normalized_id, normalized_id),
            ).fetchall()
        finally:
            connection.close()

        relations: list[dict[str, object]] = []
        for row in rows:
            source_object_id = str(row["source_object_id"])
            target_object_id = str(row["target_object_id"])
            direction = "outgoing" if source_object_id == normalized_id else "incoming"
            counterparty_object_id = target_object_id if direction == "outgoing" else source_object_id
            relations.append(
                {
                    "relation_id": str(row["relation_id"]),
                    "source_object_id": source_object_id,
                    "target_object_id": target_object_id,
                    "relation_type": str(row["relation_type"]),
                    "confidence": float(row["confidence"]),
                    "context": str(row["context"]),
                    "created_at": str(row["created_at"]),
                    "created_by": str(row["created_by"]),
                    "direction": direction,
                    "counterparty_object_id": counterparty_object_id,
                }
            )
        return relations

    def record_knowledge_migration(
        self,
        base_dir: Path,
        task_id: str,
        payload: dict[str, object],
    ) -> None:
        migration_payload = dict(payload)
        migration_payload.setdefault("task_id", task_id)
        migration_payload.setdefault("updated_at", utc_now())
        updated_at = str(migration_payload.get("updated_at", "")).strip() or utc_now()
        migration_payload["updated_at"] = updated_at

        with self._connect(base_dir) as connection:
            connection.execute(
                """
                INSERT INTO knowledge_migrations (task_id, migration_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    migration_json = excluded.migration_json,
                    updated_at = excluded.updated_at
                """,
                (
                    task_id,
                    json.dumps(migration_payload, indent=2),
                    updated_at,
                ),
            )
        self._checkpoint(base_dir)

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
                knowledge_evidence_table = _table_exists(connection, "knowledge_evidence")
                knowledge_wiki_table = _table_exists(connection, "knowledge_wiki")
                knowledge_migrations_table = _table_exists(connection, "knowledge_migrations")
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
                knowledge_evidence_count = (
                    int(connection.execute("SELECT COUNT(*) FROM knowledge_evidence").fetchone()[0])
                    if knowledge_evidence_table
                    else 0
                )
                knowledge_wiki_count = (
                    int(connection.execute("SELECT COUNT(*) FROM knowledge_wiki").fetchone()[0])
                    if knowledge_wiki_table
                    else 0
                )
                knowledge_migration_count = (
                    int(connection.execute("SELECT COUNT(*) FROM knowledge_migrations").fetchone()[0])
                    if knowledge_migrations_table
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
                "knowledge_evidence_table": False,
                "knowledge_wiki_table": False,
                "knowledge_migrations_table": False,
                "task_count": 0,
                "event_count": 0,
                "knowledge_evidence_count": 0,
                "knowledge_wiki_count": 0,
                "knowledge_migration_count": 0,
                "integrity_ok": False,
                "details": str(exc),
            }

        return {
            "db_path": str(db_path),
            "db_exists": True,
            "schema_ok": tasks_table and events_table,
            "tasks_table": tasks_table,
            "events_table": events_table,
            "knowledge_evidence_table": knowledge_evidence_table,
            "knowledge_wiki_table": knowledge_wiki_table,
            "knowledge_migrations_table": knowledge_migrations_table,
            "task_count": task_count,
            "event_count": event_count,
            "knowledge_evidence_count": knowledge_evidence_count,
            "knowledge_wiki_count": knowledge_wiki_count,
            "knowledge_migration_count": knowledge_migration_count,
            "integrity_ok": integrity == "ok",
            "details": integrity,
        }
