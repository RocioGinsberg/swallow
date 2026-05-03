from __future__ import annotations

from pathlib import Path
from typing import Any

from swallow.knowledge_retrieval.knowledge_plane import (
    StagedCandidate,
    iter_knowledge_task_ids,
    list_knowledge_relations,
    list_staged_knowledge,
    load_canonical_registry_records,
    load_task_knowledge_view,
)


DEFAULT_LIMIT = 50
MAX_LIMIT = 200
WIKI_CANONICAL_STATUSES = {"active", "superseded", "all"}
STAGED_STATUSES = {"pending", "promoted", "rejected", "all"}
RELATION_GROUPS = ("supersedes", "refines", "contradicts", "refers_to", "derived_from")
LEGACY_RELATION_TYPES = {"cites", "extends", "related_to"}


class KnowledgeObjectNotFoundError(ValueError):
    pass


def build_wiki_knowledge_payload(base_dir: Path, *, status: str = "active", limit: int = DEFAULT_LIMIT) -> dict[str, object]:
    normalized_status = _normalize_status(status, WIKI_CANONICAL_STATUSES)
    normalized_limit = _normalize_limit(limit)
    canonical_records = load_canonical_registry_records(base_dir)
    items = [
        _wiki_summary(entry, _matching_canonical_record(entry, canonical_records))
        for entry in _load_all_knowledge_entries(base_dir)
        if _entry_kind(entry) == "wiki"
    ]
    filtered = _filter_status(items, normalized_status)
    return _list_payload("wiki", normalized_status, normalized_limit, filtered)


def build_canonical_knowledge_payload(
    base_dir: Path,
    *,
    status: str = "active",
    limit: int = DEFAULT_LIMIT,
) -> dict[str, object]:
    normalized_status = _normalize_status(status, WIKI_CANONICAL_STATUSES)
    normalized_limit = _normalize_limit(limit)
    items = [_canonical_summary(record) for record in load_canonical_registry_records(base_dir)]
    filtered = _filter_status(items, normalized_status)
    return _list_payload("canonical", normalized_status, normalized_limit, filtered)


def build_staged_knowledge_payload(
    base_dir: Path,
    *,
    status: str = "pending",
    limit: int = DEFAULT_LIMIT,
) -> dict[str, object]:
    normalized_status = _normalize_status(status, STAGED_STATUSES)
    normalized_limit = _normalize_limit(limit)
    items = [_staged_summary(candidate) for candidate in list_staged_knowledge(base_dir)]
    filtered = _filter_status(items, normalized_status)
    return _list_payload("staged", normalized_status, normalized_limit, filtered)


def build_knowledge_detail_payload(base_dir: Path, object_id: str) -> dict[str, object]:
    detail = _resolve_detail(base_dir, object_id)
    return {"detail": detail}


def build_knowledge_relations_payload(base_dir: Path, object_id: str) -> dict[str, object]:
    detail = _resolve_detail(base_dir, object_id)
    equivalent_ids = _equivalent_ids(base_dir, detail, object_id)
    groups = _empty_relation_groups()
    seen_edges: set[tuple[str, str, str, str, str, str]] = set()

    for relation in _load_persisted_relations(base_dir, equivalent_ids):
        edge = _persisted_relation_edge(relation)
        _append_relation_edge(groups, edge, seen_edges)

    for edge in _metadata_relation_edges(base_dir, equivalent_ids):
        _append_relation_edge(groups, edge, seen_edges)

    return {
        "object_id": detail["object_id"],
        "object_kind": detail["object_kind"],
        "groups": groups,
        "count": sum(len(items) for items in groups.values()),
    }


def _normalize_limit(limit: int) -> int:
    try:
        normalized = int(limit)
    except (TypeError, ValueError) as exc:
        raise ValueError("limit must be an integer.") from exc
    if normalized < 1 or normalized > MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}.")
    return normalized


def _normalize_status(status: str, allowed: set[str]) -> str:
    normalized = str(status or "").strip().lower()
    if normalized not in allowed:
        raise ValueError(f"status must be one of: {', '.join(sorted(allowed))}.")
    return normalized


def _list_payload(
    object_kind: str,
    status: str,
    limit: int,
    items: list[dict[str, object]],
) -> dict[str, object]:
    ordered = sorted(items, key=_summary_sort_key, reverse=True)
    limited = ordered[:limit]
    return {
        "count": len(limited),
        "items": limited,
        "filters": {
            "object_kind": object_kind,
            "status": status,
            "limit": limit,
        },
    }


def _summary_sort_key(item: dict[str, object]) -> tuple[str, str]:
    return (str(item.get("updated_at", "")), str(item.get("object_id", "")))


def _filter_status(items: list[dict[str, object]], status: str) -> list[dict[str, object]]:
    if status == "all":
        return items
    return [item for item in items if str(item.get("status", "")).strip() == status]


def _load_all_knowledge_entries(base_dir: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for task_id in iter_knowledge_task_ids(base_dir):
        for item in load_task_knowledge_view(base_dir, task_id):
            entry = dict(item)
            entry["task_id"] = task_id
            entries.append(entry)
    return entries


def _entry_id(entry: dict[str, object]) -> str:
    for key in ("object_id", "entry_id", "source_object_id", "canonical_id"):
        value = str(entry.get(key, "")).strip()
        if value:
            return value
    return "knowledge-entry"


def _entry_kind(entry: dict[str, object]) -> str:
    if str(entry.get("store_type", "")).strip() == "wiki":
        return "wiki"
    if str(entry.get("stage", "")).strip() == "canonical":
        return "wiki"
    return "evidence"


def _text_preview(text: object, limit: int = 180) -> str:
    normalized = " ".join(str(text or "").split())
    if not normalized:
        return "(empty)"
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(limit - 3, 0)].rstrip() + "..."


def _source_refs(*payloads: dict[str, object]) -> list[str]:
    refs: list[str] = []
    for payload in payloads:
        _append_ref(refs, payload.get("source_ref", ""))
        _append_ref(refs, payload.get("artifact_ref", ""))
        _append_ref(refs, payload.get("decision_ref", ""))
        _append_ref(refs, payload.get("change_log_ref", ""))
        raw_source_ids = payload.get("source_evidence_ids", [])
        if isinstance(raw_source_ids, list):
            for item in raw_source_ids:
                _append_ref(refs, item)
        else:
            _append_ref(refs, raw_source_ids)
        for source in _dict_list(payload.get("source_pack", [])):
            for key in ("source_ref", "artifact_ref", "target_ref", "resolved_ref"):
                _append_ref(refs, source.get(key, ""))
        for metadata in _dict_list(payload.get("relation_metadata", [])):
            _append_ref(refs, metadata.get("target_ref", ""))
    return refs


def _append_ref(refs: list[str], value: object) -> None:
    normalized = str(value or "").strip()
    if normalized and normalized not in refs:
        refs.append(normalized)


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _relation_metadata(*payloads: dict[str, object]) -> list[dict[str, object]]:
    metadata: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    for payload in payloads:
        for item in _dict_list(payload.get("relation_metadata", [])):
            key = (
                str(item.get("relation_type", "")).strip(),
                str(item.get("target_object_id", "")).strip(),
                str(item.get("target_ref", "")).strip(),
            )
            if key in seen:
                continue
            seen.add(key)
            metadata.append(item)
    return metadata


def _matching_canonical_record(
    entry: dict[str, object],
    canonical_records: list[dict[str, object]],
) -> dict[str, object]:
    entry_id = _entry_id(entry)
    canonical_id = str(entry.get("canonical_id", "")).strip()
    for record in reversed(canonical_records):
        if canonical_id and str(record.get("canonical_id", "")).strip() == canonical_id:
            return dict(record)
        if str(record.get("canonical_id", "")).strip() == entry_id:
            return dict(record)
        if str(record.get("source_object_id", "")).strip() == entry_id:
            return dict(record)
    return {}


def _wiki_status(entry: dict[str, object], canonical_record: dict[str, object]) -> str:
    for payload, key in (
        (canonical_record, "canonical_status"),
        (entry, "canonical_status"),
        (entry, "status"),
    ):
        value = str(payload.get(key, "")).strip()
        if value:
            return "active" if value == "canonical" else value
    return "active"


def _wiki_summary(entry: dict[str, object], canonical_record: dict[str, object]) -> dict[str, object]:
    object_id = _entry_id(entry)
    text = entry.get("text", "") or canonical_record.get("text", "")
    return {
        "object_id": object_id,
        "object_kind": "wiki",
        "status": _wiki_status(entry, canonical_record),
        "text_preview": _text_preview(text),
        "source_refs": _source_refs(entry, canonical_record),
        "task_id": str(entry.get("task_id", "")).strip() or str(canonical_record.get("source_task_id", "")).strip(),
        "canonical_id": str(canonical_record.get("canonical_id", "")).strip(),
        "candidate_id": "",
        "topic": str(entry.get("topic", "")).strip(),
        "updated_at": _updated_at(entry, canonical_record),
    }


def _canonical_summary(record: dict[str, object]) -> dict[str, object]:
    canonical_id = str(record.get("canonical_id", "")).strip()
    return {
        "object_id": canonical_id,
        "object_kind": "canonical",
        "status": str(record.get("canonical_status", "active")).strip() or "active",
        "text_preview": _text_preview(record.get("text", "")),
        "source_refs": _source_refs(record),
        "task_id": str(record.get("source_task_id", "")).strip(),
        "canonical_id": canonical_id,
        "candidate_id": "",
        "topic": "",
        "updated_at": str(record.get("promoted_at", "")).strip(),
    }


def _staged_summary(candidate: StagedCandidate) -> dict[str, object]:
    return {
        "object_id": candidate.candidate_id,
        "object_kind": "staged",
        "status": candidate.status,
        "text_preview": _text_preview(candidate.text),
        "source_refs": _source_refs(candidate.to_dict()),
        "task_id": candidate.source_task_id,
        "canonical_id": "",
        "candidate_id": candidate.candidate_id,
        "topic": candidate.topic,
        "updated_at": candidate.decided_at or candidate.submitted_at,
    }


def _updated_at(entry: dict[str, object], canonical_record: dict[str, object]) -> str:
    for payload, key in (
        (entry, "updated_at"),
        (entry, "captured_at"),
        (entry, "promoted_at"),
        (canonical_record, "promoted_at"),
        (entry, "submitted_at"),
    ):
        value = str(payload.get(key, "")).strip()
        if value:
            return value
    return ""


def _resolve_detail(base_dir: Path, object_id: str) -> dict[str, object]:
    normalized_id = str(object_id).strip()
    if not normalized_id:
        raise KnowledgeObjectNotFoundError("Unknown knowledge object: ")

    for candidate in list_staged_knowledge(base_dir):
        if candidate.candidate_id == normalized_id:
            return _staged_detail(candidate)

    canonical_records = load_canonical_registry_records(base_dir)
    for record in reversed(canonical_records):
        if str(record.get("canonical_id", "")).strip() == normalized_id:
            return _canonical_detail(record)

    for entry in _load_all_knowledge_entries(base_dir):
        if _entry_id(entry) == normalized_id:
            return _entry_detail(entry, _matching_canonical_record(entry, canonical_records))

    for record in reversed(canonical_records):
        if str(record.get("source_object_id", "")).strip() == normalized_id:
            return _canonical_detail(record)

    raise KnowledgeObjectNotFoundError(f"Unknown knowledge object: {normalized_id}")


def _staged_detail(candidate: StagedCandidate) -> dict[str, object]:
    payload = candidate.to_dict()
    summary = _staged_summary(candidate)
    return {
        **summary,
        "text": candidate.text,
        "source_pack": _dict_list(payload.get("source_pack", [])),
        "rationale": candidate.rationale,
        "relation_metadata": _relation_metadata(payload),
        "conflict_flag": candidate.conflict_flag,
        "metadata": {
            "source_kind": candidate.source_kind,
            "source_object_id": candidate.source_object_id,
            "submitted_by": candidate.submitted_by,
            "submitted_at": candidate.submitted_at,
            "wiki_mode": candidate.wiki_mode,
            "target_object_id": candidate.target_object_id,
        },
    }


def _canonical_detail(record: dict[str, object]) -> dict[str, object]:
    summary = _canonical_summary(record)
    return {
        **summary,
        "text": str(record.get("text", "")),
        "source_pack": _dict_list(record.get("source_pack", [])),
        "rationale": str(record.get("rationale", "")).strip(),
        "relation_metadata": _relation_metadata(record),
        "conflict_flag": str(record.get("conflict_flag", "")).strip(),
        "metadata": {
            "canonical_key": str(record.get("canonical_key", "")).strip(),
            "source_object_id": str(record.get("source_object_id", "")).strip(),
            "promoted_by": str(record.get("promoted_by", "")).strip(),
            "promoted_at": str(record.get("promoted_at", "")).strip(),
            "decision_ref": str(record.get("decision_ref", "")).strip(),
            "superseded_by": str(record.get("superseded_by", "")).strip(),
            "superseded_at": str(record.get("superseded_at", "")).strip(),
        },
    }


def _entry_detail(entry: dict[str, object], canonical_record: dict[str, object]) -> dict[str, object]:
    summary = _wiki_summary(entry, canonical_record) if _entry_kind(entry) == "wiki" else _evidence_summary(entry)
    return {
        **summary,
        "text": str(entry.get("text", "") or canonical_record.get("text", "")),
        "source_pack": _dict_list(entry.get("source_pack", [])) or _dict_list(canonical_record.get("source_pack", [])),
        "rationale": str(entry.get("rationale", "") or canonical_record.get("rationale", "")).strip(),
        "relation_metadata": _relation_metadata(entry, canonical_record),
        "conflict_flag": str(entry.get("conflict_flag", "") or canonical_record.get("conflict_flag", "")).strip(),
        "metadata": {
            "source_kind": str(entry.get("source_kind", "")).strip(),
            "source_object_id": str(entry.get("source_object_id", "")).strip(),
            "evidence_status": str(entry.get("evidence_status", "")).strip(),
            "artifact_ref": str(entry.get("artifact_ref", "")).strip(),
            "canonical_id": str(canonical_record.get("canonical_id", "")).strip(),
            "canonical_key": str(canonical_record.get("canonical_key", "")).strip(),
        },
    }


def _evidence_summary(entry: dict[str, object]) -> dict[str, object]:
    object_id = _entry_id(entry)
    return {
        "object_id": object_id,
        "object_kind": "evidence",
        "status": str(entry.get("stage", "raw")).strip() or "raw",
        "text_preview": _text_preview(entry.get("text", "")),
        "source_refs": _source_refs(entry),
        "task_id": str(entry.get("task_id", "")).strip(),
        "canonical_id": "",
        "candidate_id": "",
        "topic": str(entry.get("topic", "")).strip(),
        "updated_at": _updated_at(entry, {}),
    }


def _equivalent_ids(base_dir: Path, detail: dict[str, object], requested_id: str) -> set[str]:
    ids = {
        str(requested_id).strip(),
        str(detail.get("object_id", "")).strip(),
        str(detail.get("canonical_id", "")).strip(),
        str(detail.get("candidate_id", "")).strip(),
    }
    metadata = detail.get("metadata", {})
    if isinstance(metadata, dict):
        ids.add(str(metadata.get("source_object_id", "")).strip())
    for record in load_canonical_registry_records(base_dir):
        canonical_id = str(record.get("canonical_id", "")).strip()
        source_object_id = str(record.get("source_object_id", "")).strip()
        if canonical_id in ids or source_object_id in ids:
            ids.add(canonical_id)
            ids.add(source_object_id)
    return {item for item in ids if item}


def _empty_relation_groups() -> dict[str, list[dict[str, object]]]:
    return {
        "supersedes": [],
        "refines": [],
        "contradicts": [],
        "refers_to": [],
        "derived_from": [],
        "legacy": [],
    }


def _load_persisted_relations(base_dir: Path, equivalent_ids: set[str]) -> list[dict[str, object]]:
    relations: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for object_id in sorted(equivalent_ids):
        try:
            loaded = list_knowledge_relations(base_dir, object_id)
        except ValueError:
            continue
        for relation in loaded:
            relation_id = str(relation.get("relation_id", "")).strip()
            if relation_id and relation_id in seen_ids:
                continue
            if relation_id:
                seen_ids.add(relation_id)
            relations.append(dict(relation))
    return relations


def _persisted_relation_edge(relation: dict[str, object]) -> dict[str, object]:
    return {
        "relation_id": str(relation.get("relation_id", "")).strip(),
        "relation_type": str(relation.get("relation_type", "")).strip(),
        "direction": str(relation.get("direction", "")).strip(),
        "source_object_id": str(relation.get("source_object_id", "")).strip(),
        "target_object_id": str(relation.get("target_object_id", "")).strip(),
        "counterparty_object_id": str(relation.get("counterparty_object_id", "")).strip(),
        "confidence": float(relation.get("confidence", 1.0)),
        "context": str(relation.get("context", "")).strip(),
        "created_at": str(relation.get("created_at", "")).strip(),
        "created_by": str(relation.get("created_by", "")).strip(),
        "edge_source": "persisted",
        "target_ref": "",
        "source_ref": "",
    }


def _metadata_relation_edges(base_dir: Path, equivalent_ids: set[str]) -> list[dict[str, object]]:
    edges: list[dict[str, object]] = []
    for owner in _metadata_relation_owners(base_dir):
        owner_ids = {item for item in owner["owner_ids"] if item}
        owner_is_current = bool(owner_ids & equivalent_ids)
        for metadata in owner["relation_metadata"]:
            relation_type = str(metadata.get("relation_type", "")).strip()
            if not relation_type:
                continue
            target_object_id = str(metadata.get("target_object_id", "")).strip()
            target_ref = str(metadata.get("target_ref", "")).strip()
            target_matches_current = target_object_id in equivalent_ids or target_ref in equivalent_ids
            if not owner_is_current and not target_matches_current:
                continue
            source_object_id = owner["primary_id"]
            edges.append(
                {
                    "relation_id": "",
                    "relation_type": relation_type,
                    "direction": "outgoing" if owner_is_current else "incoming",
                    "source_object_id": source_object_id,
                    "target_object_id": target_object_id,
                    "counterparty_object_id": target_object_id or target_ref,
                    "confidence": float(metadata.get("confidence", 1.0) or 1.0),
                    "context": str(metadata.get("context", "") or metadata.get("note", "")).strip(),
                    "created_at": "",
                    "created_by": str(metadata.get("created_by", "")).strip(),
                    "edge_source": "metadata",
                    "target_ref": target_ref,
                    "source_ref": str(metadata.get("source_ref", "")).strip(),
                }
            )
    return edges


def _metadata_relation_owners(base_dir: Path) -> list[dict[str, Any]]:
    owners: list[dict[str, Any]] = []
    for candidate in list_staged_knowledge(base_dir):
        metadata = _relation_metadata(candidate.to_dict())
        if not metadata:
            continue
        owners.append(
            {
                "primary_id": candidate.candidate_id,
                "owner_ids": {candidate.candidate_id, candidate.source_object_id, candidate.target_object_id},
                "relation_metadata": metadata,
            }
        )
    for record in load_canonical_registry_records(base_dir):
        metadata = _relation_metadata(record)
        if not metadata:
            continue
        canonical_id = str(record.get("canonical_id", "")).strip()
        source_object_id = str(record.get("source_object_id", "")).strip()
        owners.append(
            {
                "primary_id": canonical_id or source_object_id,
                "owner_ids": {canonical_id, source_object_id},
                "relation_metadata": metadata,
            }
        )
    for entry in _load_all_knowledge_entries(base_dir):
        metadata = _relation_metadata(entry)
        if not metadata:
            continue
        entry_id = _entry_id(entry)
        owners.append(
            {
                "primary_id": entry_id,
                "owner_ids": {entry_id, str(entry.get("canonical_id", "")).strip()},
                "relation_metadata": metadata,
            }
        )
    return owners


def _append_relation_edge(
    groups: dict[str, list[dict[str, object]]],
    edge: dict[str, object],
    seen_edges: set[tuple[str, str, str, str, str, str]],
) -> None:
    key = (
        str(edge.get("edge_source", "")).strip(),
        str(edge.get("relation_id", "")).strip(),
        str(edge.get("relation_type", "")).strip(),
        str(edge.get("source_object_id", "")).strip(),
        str(edge.get("target_object_id", "")).strip(),
        str(edge.get("target_ref", "")).strip(),
    )
    if key in seen_edges:
        return
    seen_edges.add(key)
    groups[_relation_group(str(edge.get("relation_type", "")))].append(edge)


def _relation_group(relation_type: str) -> str:
    normalized = relation_type.strip()
    if normalized in RELATION_GROUPS:
        return normalized
    if normalized in LEGACY_RELATION_TYPES:
        return "legacy"
    return "legacy"
