from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from swallow._io_helpers import read_json_strict
from swallow.orchestration.models import utc_now
from swallow.application.infrastructure.paths import (
    knowledge_objects_path,
    swallow_db_path,
    task_knowledge_evidence_root,
    task_knowledge_wiki_root,
    tasks_root,
)


WIKI_ONLY_FIELDS = ("promoted_by", "promoted_at", "change_log_ref", "source_evidence_ids")
SOURCE_EVIDENCE_PREVIEW_LIMIT = 1000
SOURCE_ANCHOR_VERSION = "source-anchor-v1"
SOURCE_ANCHOR_KEY_LENGTH = 16
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


def build_source_anchor_identity(anchor: dict[str, object]) -> dict[str, str]:
    normalized = _normalized_source_anchor_fields(anchor)
    payload = [
        SOURCE_ANCHOR_VERSION,
        normalized["source_ref"],
        normalized["content_hash"],
        normalized["parser_version"],
        normalized["span"],
        normalized["heading_path"],
    ]
    key = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()[:SOURCE_ANCHOR_KEY_LENGTH]
    return {
        **normalized,
        "source_anchor_version": SOURCE_ANCHOR_VERSION,
        "source_anchor_key": key,
        "evidence_id": f"evidence-src-{key}",
    }


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
    source_evidence_ids = _source_evidence_ids_from_record(
        record,
        fallback_source_object_id=source_object_id,
    )
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
            "source_evidence_ids": source_evidence_ids,
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


def materialize_source_evidence_from_canonical_record(
    base_dir: Path,
    record: dict[str, object],
    *,
    mirror_files: bool = True,
    write_authority: str = LIBRARIAN_AGENT_WRITE_AUTHORITY,
) -> list[str]:
    source_task_id = str(record.get("source_task_id", "")).strip()
    if not source_task_id:
        return []

    source_pack = _resolved_source_pack_entries(record.get("source_pack", []))
    if not source_pack:
        return []

    candidate_id = _candidate_id_from_canonical_record(record)
    evidence_entries = [
        _source_pack_evidence_entry(record, anchor, candidate_id=candidate_id, index=index)
        for index, anchor in enumerate(source_pack, start=1)
    ]
    merged_view = _merge_task_knowledge_views(
        load_task_knowledge_view(base_dir, source_task_id),
        evidence_entries,
    )
    persist_task_knowledge_view(
        base_dir,
        source_task_id,
        merged_view,
        mirror_files=mirror_files,
        write_authority=write_authority,
    )
    return [
        str(entry.get("object_id", "")).strip()
        for entry in evidence_entries
        if str(entry.get("object_id", "")).strip()
    ]


def _source_evidence_ids_from_record(
    record: dict[str, object],
    *,
    fallback_source_object_id: str,
) -> list[str]:
    raw_source_ids = record.get("source_evidence_ids", [])
    source_ids: list[str] = []
    if isinstance(raw_source_ids, list):
        source_ids = [str(item).strip() for item in raw_source_ids if str(item).strip()]
    elif str(raw_source_ids).strip():
        source_ids = [str(raw_source_ids).strip()]
    if not source_ids and fallback_source_object_id:
        source_ids = [fallback_source_object_id]
    return source_ids


def _resolved_source_pack_entries(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []

    entries: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        payload = dict(item)
        resolution_status = str(payload.get("resolution_status", "resolved")).strip() or "resolved"
        if resolution_status != "resolved":
            continue
        source_ref = _source_ref_from_anchor(payload)
        if not source_ref:
            continue
        entries.append(payload)
    return entries


def _source_pack_evidence_entry(
    record: dict[str, object],
    anchor: dict[str, object],
    *,
    candidate_id: str,
    index: int,
) -> dict[str, object]:
    canonical_id = str(record.get("canonical_id", "")).strip()
    promoted_at = str(record.get("promoted_at", "")).strip() or utc_now()
    source_anchor = build_source_anchor_identity(anchor)
    source_ref = source_anchor["source_ref"]
    preview = _bounded_source_preview(anchor.get("preview", "") or source_ref)
    display_path = _display_path_from_anchor(anchor)
    return normalize_evidence_entry(
        {
            "object_id": source_anchor["evidence_id"],
            "text": preview,
            "stage": "raw",
            "source_kind": "wiki_compiler_source_pack",
            "source_ref": source_ref,
            "task_linked": True,
            "captured_at": promoted_at,
            "evidence_status": "source_only",
            "artifact_ref": str(anchor.get("artifact_ref", "")).strip(),
            "retrieval_eligible": False,
            "knowledge_reuse_scope": "task_only",
            "canonicalization_intent": "support",
            "content_hash": source_anchor["content_hash"],
            "parser_version": source_anchor["parser_version"],
            "span": source_anchor["span"],
            "heading_path": source_anchor["heading_path"],
            "source_anchor_key": source_anchor["source_anchor_key"],
            "source_anchor_version": source_anchor["source_anchor_version"],
            "line_start": _int_value(anchor.get("line_start", 0)),
            "line_end": _int_value(anchor.get("line_end", 0)),
            "source_type": str(anchor.get("source_type", "")).strip(),
            "display_path": display_path,
            "path": str(anchor.get("path", "")).strip(),
            "resolved_ref": str(anchor.get("resolved_ref", "")).strip(),
            "resolved_path": str(anchor.get("resolved_path", "")).strip(),
            "source_pack_reference": str(anchor.get("reference", "")).strip(),
            "source_pack_index": index,
            "candidate_id": candidate_id,
            "canonical_id": canonical_id,
            "preview": preview,
        }
    )


def _normalized_source_anchor_fields(anchor: dict[str, object]) -> dict[str, str]:
    return {
        "source_ref": _source_ref_from_anchor(anchor),
        "content_hash": str(anchor.get("content_hash", "")).strip(),
        "parser_version": str(anchor.get("parser_version", "")).strip(),
        "span": _normalize_anchor_span(anchor),
        "heading_path": _normalize_heading_path(anchor.get("heading_path", "")),
    }


def _normalize_anchor_span(anchor: dict[str, object]) -> str:
    value = anchor.get("span", "")
    if isinstance(value, (dict, list, tuple)):
        normalized = _canonical_json(value)
    else:
        normalized = str(value).strip()
    if normalized:
        return normalized

    line_start = _int_value(anchor.get("line_start", 0))
    line_end = _int_value(anchor.get("line_end", 0))
    if not line_start and not line_end:
        return ""
    if line_start and not line_end:
        line_end = line_start
    if line_end and not line_start:
        line_start = line_end
    return f"line:{line_start}-{line_end}"


def _normalize_heading_path(value: object) -> str:
    if isinstance(value, (list, tuple)):
        return " > ".join(str(item).strip() for item in value if str(item).strip())

    text = str(value).strip()
    if not text:
        return ""
    if ">" not in text:
        return text
    return " > ".join(part.strip() for part in text.split(">") if part.strip())


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _candidate_id_from_canonical_record(record: dict[str, object]) -> str:
    decision_ref = str(record.get("decision_ref", "")).strip()
    if "#" in decision_ref:
        fragment = decision_ref.rsplit("#", 1)[1].strip()
        if fragment:
            return fragment

    canonical_id = str(record.get("canonical_id", "")).strip()
    if canonical_id.startswith("canonical-"):
        return canonical_id.removeprefix("canonical-")
    return canonical_id or "canonical-entry"


def _source_ref_from_anchor(anchor: dict[str, object]) -> str:
    for key in ("source_ref", "resolved_ref", "target_ref", "artifact_ref"):
        value = str(anchor.get(key, "")).strip()
        if value:
            return value
    return ""


def _display_path_from_anchor(anchor: dict[str, object]) -> str:
    for key in (
        "path",
        "resolved_path",
        "display_path",
        "artifact_ref",
        "source_ref",
        "resolved_ref",
    ):
        value = str(anchor.get(key, "")).strip()
        if value:
            return value
    return ""


def _bounded_source_preview(value: object) -> str:
    normalized = " ".join(str(value or "").split())
    if len(normalized) <= SOURCE_EVIDENCE_PREVIEW_LIMIT:
        return normalized
    return normalized[: SOURCE_EVIDENCE_PREVIEW_LIMIT - 3].rstrip() + "..."


def _safe_id_token(value: str) -> str:
    chars: list[str] = []
    for char in str(value).strip():
        lower = char.lower()
        if ("a" <= lower <= "z") or char.isdigit() or char in "._-":
            chars.append(char)
        else:
            chars.append("-")
    return "".join(chars).strip("-") or "canonical-entry"


def _int_value(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


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
