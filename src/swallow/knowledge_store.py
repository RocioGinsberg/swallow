from __future__ import annotations

import json
from pathlib import Path

from .models import utc_now
from .paths import (
    knowledge_evidence_entry_path,
    knowledge_objects_path,
    knowledge_wiki_entry_path,
    task_knowledge_evidence_root,
    task_knowledge_wiki_root,
)


WIKI_ONLY_FIELDS = ("promoted_by", "promoted_at", "change_log_ref", "source_evidence_ids")


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


def _load_store_entries(store_root: Path) -> list[dict[str, object]]:
    if not store_root.exists():
        return []

    entries: list[dict[str, object]] = []
    for path in sorted(store_root.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            entries.append(payload)
    return entries


def _load_legacy_knowledge_objects(base_dir: Path, task_id: str) -> list[dict[str, object]]:
    payload_path = knowledge_objects_path(base_dir, task_id)
    if not payload_path.exists():
        return []
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
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


def load_task_evidence_entries(base_dir: Path, task_id: str) -> list[dict[str, object]]:
    return [normalize_evidence_entry(item) for item in _load_store_entries(task_knowledge_evidence_root(base_dir, task_id))]


def load_task_wiki_entries(base_dir: Path, task_id: str) -> list[dict[str, object]]:
    return [normalize_wiki_entry(item) for item in _load_store_entries(task_knowledge_wiki_root(base_dir, task_id))]


def load_task_knowledge_view(base_dir: Path, task_id: str) -> list[dict[str, object]]:
    legacy_entries = normalize_task_knowledge_view(_load_legacy_knowledge_objects(base_dir, task_id))
    evidence_entries = load_task_evidence_entries(base_dir, task_id)
    wiki_entries = load_task_wiki_entries(base_dir, task_id)
    return _merge_task_knowledge_views(legacy_entries, evidence_entries, wiki_entries)


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
) -> list[dict[str, object]]:
    normalized_view = normalize_task_knowledge_view(knowledge_objects)
    evidence_entries, wiki_entries = split_task_knowledge_view(normalized_view)
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


def persist_wiki_entry_from_record(base_dir: Path, record: dict[str, object]) -> dict[str, object]:
    source_task_id = str(record.get("source_task_id", "")).strip()
    if not source_task_id:
        raise ValueError("Canonical record is missing source_task_id.")

    wiki_entry = build_wiki_entry_from_canonical_record(record)
    entry_id = _store_entry_id(wiki_entry)
    wiki_path = knowledge_wiki_entry_path(base_dir, source_task_id, entry_id)
    wiki_path.parent.mkdir(parents=True, exist_ok=True)
    wiki_path.write_text(json.dumps(wiki_entry, indent=2) + "\n", encoding="utf-8")

    object_id = str(wiki_entry.get("object_id", "")).strip()
    if object_id:
        evidence_path = knowledge_evidence_entry_path(base_dir, source_task_id, object_id)
        if evidence_path.exists():
            evidence_path.unlink()
    return wiki_entry
