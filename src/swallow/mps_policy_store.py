from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from . import sqlite_store
from .identity import local_actor
from .models import utc_now
from .paths import mps_policy_path


MPS_ROUND_LIMIT_KIND = "mps_round_limit"
MPS_PARTICIPANT_LIMIT_KIND = "mps_participant_limit"
MPS_POLICY_KINDS = {MPS_ROUND_LIMIT_KIND, MPS_PARTICIPANT_LIMIT_KIND}


def normalize_mps_policy_kind(kind: str) -> str:
    normalized = kind.strip()
    if normalized not in MPS_POLICY_KINDS:
        expected = ", ".join(sorted(MPS_POLICY_KINDS))
        raise ValueError(f"unknown MPS policy kind: {kind!r}. Expected one of: {expected}")
    return normalized


def validate_mps_policy_value(kind: str, value: int) -> int:
    normalized_kind = normalize_mps_policy_kind(kind)
    try:
        normalized_value = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{normalized_kind} value must be an integer.") from exc
    if normalized_value < 1:
        raise ValueError(f"{normalized_kind} value must be >= 1, got {normalized_value}")
    if normalized_kind == MPS_ROUND_LIMIT_KIND and normalized_value > 3:
        raise ValueError("mps_round_limit value must be <= 3 (ORCHESTRATION section 5.3 hard max)")
    return normalized_value


def _read_policy_payload(base_dir: Path) -> dict[str, int]:
    path = mps_policy_path(base_dir)
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"MPS policy file must contain a JSON object: {path}")
    policies: dict[str, int] = {}
    for raw_kind, raw_value in payload.items():
        kind = normalize_mps_policy_kind(str(raw_kind))
        try:
            value = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{kind} value must be an integer.") from exc
        policies[kind] = validate_mps_policy_value(kind, value)
    return policies


def read_mps_policy(base_dir: Path, kind: str) -> int | None:
    normalized_kind = normalize_mps_policy_kind(kind)
    _bootstrap_mps_policy_from_legacy_json(base_dir)
    connection = sqlite_store.get_connection(base_dir)
    row = connection.execute(
        "SELECT payload FROM policy_records WHERE policy_id = ?",
        (_mps_policy_id(normalized_kind),),
    ).fetchone()
    if row is None:
        return None
    try:
        payload = json.loads(str(row["payload"]))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    value = payload.get("value")
    return validate_mps_policy_value(normalized_kind, int(value)) if value is not None else None


def save_mps_policy(base_dir: Path, kind: str, value: int) -> Path:
    normalized_kind = normalize_mps_policy_kind(kind)
    normalized_value = validate_mps_policy_value(normalized_kind, value)
    _bootstrap_mps_policy_from_legacy_json(base_dir)
    path = mps_policy_path(base_dir)
    _run_policy_write(
        base_dir,
        lambda connection: _upsert_mps_policy(connection, normalized_kind, normalized_value),
    )
    return path


def _mps_policy_id(kind: str) -> str:
    return f"mps:{kind}"


def _run_policy_write(base_dir: Path, writer) -> None:
    connection = sqlite_store.get_connection(base_dir)
    if connection.in_transaction:
        writer(connection)
        return
    connection.execute("BEGIN IMMEDIATE")
    try:
        writer(connection)
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise


def _upsert_mps_policy(connection: sqlite3.Connection, kind: str, value: int) -> None:
    normalized_kind = normalize_mps_policy_kind(kind)
    normalized_value = validate_mps_policy_value(normalized_kind, value)
    connection.execute(
        """
        INSERT INTO policy_records (
            policy_id, kind, scope, scope_value, payload, updated_at, updated_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(policy_id) DO UPDATE SET
            kind = excluded.kind,
            scope = excluded.scope,
            scope_value = excluded.scope_value,
            payload = excluded.payload,
            updated_at = excluded.updated_at,
            updated_by = excluded.updated_by
        """,
        (
            _mps_policy_id(normalized_kind),
            "mps",
            "mps_kind",
            normalized_kind,
            json.dumps({"value": normalized_value}, sort_keys=True),
            utc_now(),
            local_actor(),
        ),
    )


def _mps_policy_rows_exist(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        "SELECT 1 FROM policy_records WHERE kind = 'mps' LIMIT 1",
    ).fetchone()
    return row is not None


def _bootstrap_mps_policy_from_legacy_json(base_dir: Path) -> None:
    connection = sqlite_store.get_connection(base_dir)
    if _mps_policy_rows_exist(connection):
        return
    path = mps_policy_path(base_dir)
    if not path.exists():
        return
    connection.execute("BEGIN IMMEDIATE")
    try:
        if _mps_policy_rows_exist(connection):
            connection.execute("COMMIT")
            return
        payload = _read_policy_payload(base_dir)
        for kind, value in payload.items():
            _upsert_mps_policy(connection, kind, value)
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
