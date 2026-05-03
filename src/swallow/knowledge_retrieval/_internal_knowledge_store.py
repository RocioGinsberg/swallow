from __future__ import annotations

import json
import os
from pathlib import Path

from swallow._io_helpers import read_json_strict
from swallow.orchestration.models import utc_now
from swallow.surface_tools.paths import (
    knowledge_objects_path,
    swallow_db_path,
    task_knowledge_evidence_root,
    task_knowledge_wiki_root,
    tasks_root,
)


WIKI_ONLY_FIELDS = ("promoted_by", "promoted_at", "change_log_ref", "source_evidence_ids")
LIBRARIAN_AGENT_WRITE_AUTHORITY = "librarian-agent"
KNOWLEDGE_MIGRATION_WRITE_AUTHORITY = "knowledge-migration"
OPERATOR_CANONICAL_WRITE_AUTHORITY = "operator-gated"
TEST_FIXTURE_CANONICAL_WRITE_AUTHORITY = "test-fixture"
CANONICAL_KNOWLEDGE_WRITE_AUTHORITIES = {
    LIBRARIAN_AGENT_WRITE_AUTHORITY,
    KNOWLEDGE_MIGRATION_WRITE_AUTHORITY,
    OPERATOR_CANONICAL_WRITE_AUTHORITY,
    "canonical-promotion",
    TEST_FIXTURE_CANONICAL_WRITE_AUTHORITY,
}


def _sqlite_knowledge_enabled() -> bool:
    return str(os.environ.get("SWALLOW_STORE_BACKEND", "sqlite")).strip().lower() != "file"


def _sqlite_store():
    from swallow.truth_governance.sqlite_store import SqliteTaskStore

    return SqliteTaskStore()


def _store_entry_id(payload: dict[str, object]) -> str:
    for key in ("object_id", "source_object_id", "canonical_id"):
        value = str(payload.get(key, "")).strip()
        if value:
            return value
    return "knowledge-entry"


def normalize_evidence_entry(payload: dict[str, object]) -> dict[str, object]:
    normalized = dict(payload)
    normalized["stage"] = str(normalized.get("stage", "raw")).strip() or "raw"
    normalized["store_type"] = "evidence"
    for field_name in WIKI_ONLY_FIELDS:
        normalized.pop(field_name, None)
    return normalized


def normalize_wiki_entry(payload: dict[str, object]) -> dict[str, object]:
    normalized = dict(payload)
    normalized["stage"] = "canonical"
    normalized["store_type"] = "wiki"
    normalized["promoted_by"] = str(normalized.get("promoted_by", "")).strip()
    normalized["promoted_at"] = str(normalized.get("promoted_at", "")).strip()
    normalized["change_log_ref"] = str(normalized.get("change_log_ref", "")).strip()
    raw_source_ids = normalized.get("source_evidence_ids", [])
    if isinstance(raw_source_ids, list):
        source_ids = [str(item).strip() for item in raw_source_ids if str(item).strip()]
    else:
        source_ids = [str(raw_source_ids).strip()] if str(raw_source_ids).strip() else []
    if not source_ids:
        object_id = str(normalized.get("object_id", "")).strip()
        if object_id:
            source_ids = [object_id]
    normalized["source_evidence_ids"] = source_ids
    captured_at = str(normalized.get("captured_at", "")).strip()
    if not captured_at:
        normalized["captured_at"] = normalized["promoted_at"] or utc_now()
    return normalized


def normalize_task_knowledge_view(knowledge_objects: list[dict[str, object]]) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for item in knowledge_objects:
        payload = dict(item)
        if str(payload.get("stage", "raw")).strip() == "canonical":
            normalized.append(normalize_wiki_entry(payload))
        else:
            normalized.append(normalize_evidence_entry(payload))
    return normalized


def split_task_knowledge_view(knowledge_objects: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    evidence_entries: list[dict[str, object]] = []
    wiki_entries: list[dict[str, object]] = []
    for item in normalize_task_knowledge_view(knowledge_objects):
        if str(item.get("stage", "raw")).strip() == "canonical":
            wiki_entries.append(item)
        else:
            evidence_entries.append(item)
    return evidence_entries, wiki_entries


def is_canonical_knowledge_write_authorized(write_authority: str) -> bool:
    return str(write_authority or "").strip() in CANONICAL_KNOWLEDGE_WRITE_AUTHORITIES


def enforce_canonical_knowledge_write_authority(
    knowledge_objects: list[dict[str, object]],
    *,
    write_authority: str,
) -> None:
    _evidence_entries, wiki_entries = split_task_knowledge_view(knowledge_objects)
    if not wiki_entries:
        return
    if is_canonical_knowledge_write_authorized(write_authority):
        return
    raise PermissionError(
        "Canonical knowledge SQLite writes require LibrarianAgent or explicit gated authority "
        f"(write_authority={write_authority or 'none'})."
    )


def _load_store_entries(store_root: Path) -> list[dict[str, object]]:
    if not store_root.exists():
        return []

    entries: list[dict[str, object]] = []
    for path in sorted(store_root.glob("*.json")):
        payload = read_json_strict(path)
        if isinstance(payload, dict):
            entries.append(payload)
    return entries


def _load_legacy_knowledge_objects(base_dir: Path, task_id: str) -> list[dict[str, object]]:
    payload_path = knowledge_objects_path(base_dir, task_id)
    if not payload_path.exists():
        return []
    payload = read_json_strict(payload_path)
    if not isinstance(payload, list):
        return []
    return [dict(item) for item in payload if isinstance(item, dict)]


def _merge_task_knowledge_views(*collections: list[dict[str, object]]) -> list[dict[str, object]]:
    merged: dict[str, dict[str, object]] = {}
    order: list[str] = []
    for collection in collections:
        for item in collection:
            key = _store_entry_id(item)
            if key not in merged:
                order.append(key)
            existing = merged.get(key)
            if existing is not None and str(existing.get("store_type", "evidence")) == "wiki":
                if str(item.get("store_type", "evidence")) != "wiki":
                    continue
            merged[key] = dict(item)
    return [merged[key] for key in order]


def load_task_knowledge_view_from_files(base_dir: Path, task_id: str) -> list[dict[str, object]]:
    legacy_entries = normalize_task_knowledge_view(_load_legacy_knowledge_objects(base_dir, task_id))
    evidence_entries = [normalize_evidence_entry(item) for item in _load_store_entries(task_knowledge_evidence_root(base_dir, task_id))]
    wiki_entries = [normalize_wiki_entry(item) for item in _load_store_entries(task_knowledge_wiki_root(base_dir, task_id))]
    return _merge_task_knowledge_views(legacy_entries, evidence_entries, wiki_entries)


def iter_file_knowledge_task_ids(base_dir: Path) -> list[str]:
    task_ids: set[str] = set()

    task_root = tasks_root(base_dir)
    if task_root.exists():
        for entry in task_root.iterdir():
            if not entry.is_dir():
                continue
            if knowledge_objects_path(base_dir, entry.name).exists():
                task_ids.add(entry.name)

    for root in (task_knowledge_evidence_root(base_dir, ""), task_knowledge_wiki_root(base_dir, "")):
        if not root.exists():
            continue
        for entry in root.iterdir():
            if not entry.is_dir():
                continue
            if any(entry.glob("*.json")):
                task_ids.add(entry.name)

    return sorted(task_ids)


def iter_knowledge_task_ids(base_dir: Path) -> list[str]:
    task_ids = set(iter_file_knowledge_task_ids(base_dir))
    if _sqlite_knowledge_enabled():
        task_ids.update(_sqlite_store().iter_knowledge_task_ids(base_dir))
    return sorted(task_ids)


def load_task_evidence_entries(base_dir: Path, task_id: str) -> list[dict[str, object]]:
    if _sqlite_knowledge_enabled():
        sqlite_store = _sqlite_store()
        if sqlite_store.task_has_knowledge(base_dir, task_id):
            return [
                item
                for item in sqlite_store.load_task_knowledge_view(base_dir, task_id)
                if str(item.get("stage", "raw")).strip() != "canonical"
            ]
    return [normalize_evidence_entry(item) for item in _load_store_entries(task_knowledge_evidence_root(base_dir, task_id))]


def load_task_wiki_entries(base_dir: Path, task_id: str) -> list[dict[str, object]]:
    if _sqlite_knowledge_enabled():
        sqlite_store = _sqlite_store()
        if sqlite_store.task_has_knowledge(base_dir, task_id):
            return [
                item
                for item in sqlite_store.load_task_knowledge_view(base_dir, task_id)
                if str(item.get("stage", "raw")).strip() == "canonical"
            ]
    return [normalize_wiki_entry(item) for item in _load_store_entries(task_knowledge_wiki_root(base_dir, task_id))]


def load_task_knowledge_view(base_dir: Path, task_id: str) -> list[dict[str, object]]:
    if _sqlite_knowledge_enabled():
        sqlite_store = _sqlite_store()
        sqlite_view = sqlite_store.load_task_knowledge_view(base_dir, task_id)
        if sqlite_view:
            return sqlite_view
    return load_task_knowledge_view_from_files(base_dir, task_id)


def _write_store_entries(store_root: Path, entries: list[dict[str, object]]) -> None:
    store_root.mkdir(parents=True, exist_ok=True)
    existing_names = {path.name for path in store_root.glob("*.json")}
    written_names: set[str] = set()
    for payload in entries:
        entry_id = _store_entry_id(payload)
        path = store_root / f"{entry_id}.json"
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        written_names.add(path.name)
    for stale_name in existing_names - written_names:
        (store_root / stale_name).unlink()


def persist_task_knowledge_view(
    base_dir: Path,
    task_id: str,
    knowledge_objects: list[dict[str, object]],
    *,
    mirror_files: bool = True,
    write_authority: str = "task-state",
) -> list[dict[str, object]]:
    normalized_view = normalize_task_knowledge_view(knowledge_objects)
    if _sqlite_knowledge_enabled():
        normalized_view = _sqlite_store().replace_task_knowledge(
            base_dir,
            task_id,
            normalized_view,
            write_authority=write_authority,
        )
    if mirror_files:
        evidence_entries, wiki_entries = split_task_knowledge_view(normalized_view)
        knowledge_objects_path(base_dir, task_id).parent.mkdir(parents=True, exist_ok=True)
        knowledge_objects_path(base_dir, task_id).write_text(
            json.dumps(normalized_view, indent=2) + "\n",
            encoding="utf-8",
        )
        _write_store_entries(task_knowledge_evidence_root(base_dir, task_id), evidence_entries)
        _write_store_entries(task_knowledge_wiki_root(base_dir, task_id), wiki_entries)
    return normalized_view


def build_wiki_entry_from_canonical_record(record: dict[str, object]) -> dict[str, object]:
    source_task_id = str(record.get("source_task_id", "")).strip()
    source_object_id = str(record.get("source_object_id", "")).strip()
    promoted_at = str(record.get("promoted_at", "")).strip() or utc_now()
    canonical_id = str(record.get("canonical_id", "")).strip()
    decision_ref = str(record.get("decision_ref", "")).strip()
    return normalize_wiki_entry(
        {
            "object_id": source_object_id or canonical_id or "canonical-entry",
            "text": str(record.get("text", "")),
            "stage": "canonical",
            "source_kind": "staged_canonical_promotion" if "staged_knowledge" in decision_ref else "canonical_promotion",
            "source_ref": str(record.get("source_ref", "")).strip(),
            "task_linked": bool(source_task_id),
            "captured_at": promoted_at,
            "evidence_status": str(record.get("evidence_status", "unbacked")).strip() or "unbacked",
            "artifact_ref": str(record.get("artifact_ref", "")).strip(),
            "retrieval_eligible": False,
            "knowledge_reuse_scope": "task_only",
            "canonicalization_intent": "promote",
            "promoted_by": str(record.get("promoted_by", "")).strip(),
            "promoted_at": promoted_at,
            "change_log_ref": decision_ref,
            "source_evidence_ids": [source_object_id] if source_object_id else [],
        }
    )


def persist_wiki_entry_from_record(
    base_dir: Path,
    record: dict[str, object],
    *,
    mirror_files: bool = True,
    write_authority: str = LIBRARIAN_AGENT_WRITE_AUTHORITY,
) -> dict[str, object]:
    source_task_id = str(record.get("source_task_id", "")).strip()
    if not source_task_id:
        raise ValueError("Canonical record is missing source_task_id.")

    wiki_entry = build_wiki_entry_from_canonical_record(record)
    merged_view = _merge_task_knowledge_views(load_task_knowledge_view(base_dir, source_task_id), [wiki_entry])
    persist_task_knowledge_view(
        base_dir,
        source_task_id,
        merged_view,
        mirror_files=mirror_files,
        write_authority=write_authority,
    )
    return wiki_entry


def migrate_file_knowledge_to_sqlite(
    base_dir: Path,
    *,
    dry_run: bool = False,
) -> dict[str, object]:
    sqlite_store = _sqlite_store()
    scanned_task_ids = iter_file_knowledge_task_ids(base_dir)
    migrated_task_ids: list[str] = []
    skipped_task_ids: list[str] = []
    failed_task_ids: list[str] = []
    errors: dict[str, str] = {}
    knowledge_object_count_migrated = 0
    knowledge_object_count_skipped = 0
    knowledge_object_count_failed = 0

    for task_id in scanned_task_ids:
        try:
            file_view = load_task_knowledge_view_from_files(base_dir, task_id)
        except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
            failed_task_ids.append(task_id)
            errors[task_id] = str(exc)
            continue

        if not file_view:
            skipped_task_ids.append(task_id)
            continue

        if sqlite_store.task_has_knowledge(base_dir, task_id):
            skipped_task_ids.append(task_id)
            knowledge_object_count_skipped += len(file_view)
            continue

        migrated_task_ids.append(task_id)
        knowledge_object_count_migrated += len(file_view)
        if dry_run:
            continue

        normalized_view = sqlite_store.replace_task_knowledge(
            base_dir,
            task_id,
            file_view,
            write_authority=KNOWLEDGE_MIGRATION_WRITE_AUTHORITY,
        )
        sqlite_store.record_knowledge_migration(
            base_dir,
            task_id,
            {
                "task_id": task_id,
                "object_count": len(normalized_view),
                "source": "file_knowledge",
            },
        )

    for task_id in failed_task_ids:
        try:
            knowledge_object_count_failed += len(load_task_knowledge_view_from_files(base_dir, task_id))
        except Exception:
            continue

    return {
        "db_path": str(swallow_db_path(base_dir)),
        "dry_run": dry_run,
        "task_count_scanned": len(scanned_task_ids),
        "task_count_migrated": len(migrated_task_ids),
        "task_count_skipped": len(skipped_task_ids),
        "task_count_failed": len(failed_task_ids),
        "knowledge_object_count_migrated": knowledge_object_count_migrated,
        "knowledge_object_count_skipped": knowledge_object_count_skipped,
        "knowledge_object_count_failed": knowledge_object_count_failed,
        "migrated_task_ids": migrated_task_ids,
        "skipped_task_ids": skipped_task_ids,
        "failed_task_ids": failed_task_ids,
        "errors": errors,
    }
