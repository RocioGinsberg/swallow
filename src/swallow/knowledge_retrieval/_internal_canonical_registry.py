from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from swallow._io_helpers import read_json_lines_or_empty
from swallow.orchestration.models import utc_now
from swallow.application.infrastructure.paths import canonical_registry_path
from swallow.truth_governance.sqlite_store import SqliteTaskStore

CANONICAL_REGISTRY_DEDUPE_KEY = "canonical_id"
CANONICAL_REGISTRY_REPLACE_STRATEGY = "latest_record_wins"
CANONICAL_REGISTRY_SUPERSEDE_KEY = "canonical_key"
CANONICAL_REGISTRY_SUPERSEDE_STRATEGY = "latest_active_by_trace"


def build_canonical_key(*, knowledge_object: dict[str, object], task_id: str, object_id: str) -> str:
    artifact_ref = str(knowledge_object.get("artifact_ref", "")).strip()
    if artifact_ref:
        return f"artifact:{artifact_ref}"
    source_ref = str(knowledge_object.get("source_ref", "")).strip()
    if source_ref:
        return f"source:{source_ref}"
    return f"task-object:{task_id}:{object_id}"


def build_staged_canonical_key(*, source_task_id: str, source_object_id: str, candidate_id: str) -> str:
    normalized_task_id = source_task_id.strip()
    normalized_object_id = source_object_id.strip()
    if normalized_task_id and normalized_object_id:
        return f"task-object:{normalized_task_id}:{normalized_object_id}"
    return f"staged-candidate:{candidate_id.strip()}"


def build_canonical_record(
    *,
    task_id: str,
    object_id: str,
    knowledge_object: dict[str, object],
    decision_record: dict[str, object],
) -> dict[str, object]:
    decided_at = str(decision_record.get("decided_at", "")).strip() or utc_now()
    canonical_id = f"canonical-{task_id}-{object_id}"
    canonical_key = build_canonical_key(knowledge_object=knowledge_object, task_id=task_id, object_id=object_id)
    return {
        "canonical_id": canonical_id,
        "canonical_key": canonical_key,
        "source_task_id": task_id,
        "source_object_id": object_id,
        "promoted_at": decided_at,
        "promoted_by": decision_record.get("decided_by", "swl_cli"),
        "decision_note": decision_record.get("note", ""),
        "decision_ref": f".swl/tasks/{task_id}/knowledge_decisions.jsonl#{object_id}",
        "artifact_ref": knowledge_object.get("artifact_ref", ""),
        "source_ref": knowledge_object.get("source_ref", ""),
        "text": knowledge_object.get("text", ""),
        "evidence_status": knowledge_object.get("evidence_status", "unbacked"),
        "canonical_stage": knowledge_object.get("stage", "canonical"),
        "canonical_status": "active",
        "superseded_by": "",
        "superseded_at": "",
    }


def resolve_knowledge_object_id(base_dir: Path, object_id: str, *, store: SqliteTaskStore | None = None) -> str:
    normalized_id = str(object_id).strip()
    if not normalized_id:
        raise ValueError("knowledge object id must be a non-empty string.")

    resolved_store = store or SqliteTaskStore()
    if resolved_store.knowledge_object_exists(base_dir, normalized_id):
        return normalized_id

    registry_file = canonical_registry_path(base_dir)
    if not registry_file.exists():
        raise ValueError(f"Unknown knowledge object: {normalized_id}")

    alias_matches: list[str] = []
    for payload in read_json_lines_or_empty(registry_file):
        source_object_id = str(payload.get("source_object_id", "")).strip()
        if not source_object_id or not resolved_store.knowledge_object_exists(base_dir, source_object_id):
            continue
        if str(payload.get("canonical_id", "")).strip() == normalized_id:
            return source_object_id

        if str(payload.get("canonical_status", "active")).strip() == "superseded":
            continue

        aliases = {
            str(payload.get("source_ref", "")).strip(),
            str(payload.get("artifact_ref", "")).strip(),
        }
        source_ref = str(payload.get("source_ref", "")).strip()
        if source_ref:
            parsed = urlparse(source_ref)
            source_path = parsed.path or source_ref
            basename = Path(source_path).name.strip()
            if basename:
                aliases.add(basename)
        artifact_ref = str(payload.get("artifact_ref", "")).strip()
        if artifact_ref:
            basename = Path(artifact_ref).name.strip()
            if basename:
                aliases.add(basename)

        if normalized_id in aliases and source_object_id not in alias_matches:
            alias_matches.append(source_object_id)

    if len(alias_matches) == 1:
        return alias_matches[0]
    if len(alias_matches) > 1:
        raise ValueError(f"Ambiguous knowledge object alias: {normalized_id}")

    raise ValueError(f"Unknown knowledge object: {normalized_id}")


def load_canonical_registry_records(base_dir: Path) -> list[dict[str, object]]:
    registry_file = canonical_registry_path(base_dir)
    if not registry_file.exists():
        return []
    return [dict(record) for record in read_json_lines_or_empty(registry_file)]


def build_canonical_registry_report(records: list[dict[str, object]]) -> str:
    lines = [
        "# Canonical Knowledge Registry",
        "",
        f"- count: {len(records)}",
        "",
        "## Records",
    ]
    if not records:
        lines.append("- none")
        return "\n".join(lines)

    for record in records:
        lines.extend(
            [
                f"- {record.get('canonical_id', 'unknown')}",
                f"  canonical_key: {record.get('canonical_key', 'unknown')}",
                f"  canonical_status: {record.get('canonical_status', 'active')}",
                f"  source_task_id: {record.get('source_task_id', 'unknown')}",
                f"  source_object_id: {record.get('source_object_id', 'unknown')}",
                f"  promoted_at: {record.get('promoted_at', 'unknown')}",
                f"  promoted_by: {record.get('promoted_by', 'unknown')}",
                f"  source_ref: {record.get('source_ref', '') or 'none'}",
                f"  artifact_ref: {record.get('artifact_ref', '') or 'none'}",
                f"  decision_ref: {record.get('decision_ref', '') or 'none'}",
                f"  superseded_by: {record.get('superseded_by', '') or 'none'}",
                f"  superseded_at: {record.get('superseded_at', '') or 'none'}",
                f"  text: {record.get('text', '') or '(empty)'}",
            ]
        )
    return "\n".join(lines)


def build_canonical_registry_index(records: list[dict[str, object]]) -> dict[str, object]:
    by_task: dict[str, int] = {}
    artifact_backed_count = 0
    active_count = 0
    superseded_count = 0
    for record in records:
        source_task_id = str(record.get("source_task_id", "unknown"))
        by_task[source_task_id] = by_task.get(source_task_id, 0) + 1
        if str(record.get("artifact_ref", "")).strip():
            artifact_backed_count += 1
        if str(record.get("canonical_status", "active")).strip() == "superseded":
            superseded_count += 1
        else:
            active_count += 1
    latest = records[-1] if records else {}
    latest_active = {}
    for record in reversed(records):
        if str(record.get("canonical_status", "active")).strip() != "superseded":
            latest_active = record
            break
    return {
        "refreshed_at": utc_now(),
        "dedupe_key": CANONICAL_REGISTRY_DEDUPE_KEY,
        "replace_strategy": CANONICAL_REGISTRY_REPLACE_STRATEGY,
        "supersede_key": CANONICAL_REGISTRY_SUPERSEDE_KEY,
        "supersede_strategy": CANONICAL_REGISTRY_SUPERSEDE_STRATEGY,
        "count": len(records),
        "active_count": active_count,
        "superseded_count": superseded_count,
        "source_task_count": len(by_task),
        "artifact_backed_count": artifact_backed_count,
        "latest_canonical_id": latest.get("canonical_id", "") if records else "",
        "latest_source_task_id": latest.get("source_task_id", "") if records else "",
        "latest_source_object_id": latest.get("source_object_id", "") if records else "",
        "latest_promoted_at": latest.get("promoted_at", "") if records else "",
        "latest_active_canonical_id": latest_active.get("canonical_id", "") if latest_active else "",
        "latest_active_source_task_id": latest_active.get("source_task_id", "") if latest_active else "",
        "latest_active_source_object_id": latest_active.get("source_object_id", "") if latest_active else "",
    }


def build_canonical_registry_index_report(index_record: dict[str, object]) -> str:
    lines = [
        "# Canonical Knowledge Registry Index",
        "",
        f"- refreshed_at: {index_record.get('refreshed_at', 'unknown')}",
        f"- dedupe_key: {index_record.get('dedupe_key', CANONICAL_REGISTRY_DEDUPE_KEY)}",
        f"- replace_strategy: {index_record.get('replace_strategy', CANONICAL_REGISTRY_REPLACE_STRATEGY)}",
        f"- supersede_key: {index_record.get('supersede_key', CANONICAL_REGISTRY_SUPERSEDE_KEY)}",
        f"- supersede_strategy: {index_record.get('supersede_strategy', CANONICAL_REGISTRY_SUPERSEDE_STRATEGY)}",
        f"- count: {index_record.get('count', 0)}",
        f"- active_count: {index_record.get('active_count', 0)}",
        f"- superseded_count: {index_record.get('superseded_count', 0)}",
        f"- source_task_count: {index_record.get('source_task_count', 0)}",
        f"- artifact_backed_count: {index_record.get('artifact_backed_count', 0)}",
        f"- latest_canonical_id: {index_record.get('latest_canonical_id', '') or '-'}",
        f"- latest_active_canonical_id: {index_record.get('latest_active_canonical_id', '') or '-'}",
        f"- latest_source_task_id: {index_record.get('latest_source_task_id', '') or '-'}",
        f"- latest_source_object_id: {index_record.get('latest_source_object_id', '') or '-'}",
        f"- latest_active_source_task_id: {index_record.get('latest_active_source_task_id', '') or '-'}",
        f"- latest_active_source_object_id: {index_record.get('latest_active_source_object_id', '') or '-'}",
        f"- latest_promoted_at: {index_record.get('latest_promoted_at', '') or '-'}",
    ]
    return "\n".join(lines)
