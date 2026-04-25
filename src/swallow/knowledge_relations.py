from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from .models import utc_now
from .sqlite_store import SqliteTaskStore


KNOWLEDGE_RELATION_TYPES: tuple[str, ...] = (
    "refines",
    "contradicts",
    "cites",
    "extends",
    "related_to",
)


def create_knowledge_relation(
    base_dir: Path,
    *,
    source_object_id: str,
    target_object_id: str,
    relation_type: str,
    confidence: float = 1.0,
    context: str = "",
    created_by: str = "operator",
) -> dict[str, object]:
    normalized_source = str(source_object_id).strip()
    normalized_target = str(target_object_id).strip()
    normalized_type = str(relation_type).strip()
    normalized_context = str(context).strip()
    normalized_created_by = str(created_by).strip() or "operator"

    if not normalized_source or not normalized_target:
        raise ValueError("source_object_id and target_object_id must be non-empty strings.")
    if normalized_source == normalized_target:
        raise ValueError("source_object_id and target_object_id must be different.")
    if normalized_type not in KNOWLEDGE_RELATION_TYPES:
        raise ValueError(
            "Unsupported knowledge relation type: "
            f"{normalized_type}. Expected one of: {', '.join(KNOWLEDGE_RELATION_TYPES)}"
        )
    if confidence < 0:
        raise ValueError("confidence must be non-negative.")

    store = SqliteTaskStore()
    if not store.knowledge_object_exists(base_dir, normalized_source):
        raise ValueError(f"Unknown knowledge object: {normalized_source}")
    if not store.knowledge_object_exists(base_dir, normalized_target):
        raise ValueError(f"Unknown knowledge object: {normalized_target}")

    payload = {
        "relation_id": f"relation-{uuid4().hex[:10]}",
        "source_object_id": normalized_source,
        "target_object_id": normalized_target,
        "relation_type": normalized_type,
        "confidence": float(confidence),
        "context": normalized_context,
        "created_at": utc_now(),
        "created_by": normalized_created_by,
    }
    return store.create_knowledge_relation(base_dir, payload)


def list_knowledge_relations(base_dir: Path, object_id: str) -> list[dict[str, object]]:
    normalized_id = str(object_id).strip()
    if not normalized_id:
        raise ValueError("object_id must be a non-empty string.")
    return SqliteTaskStore().list_knowledge_relations(base_dir, normalized_id)


def delete_knowledge_relation(base_dir: Path, relation_id: str) -> None:
    normalized_id = str(relation_id).strip()
    if not normalized_id:
        raise ValueError("relation_id must be a non-empty string.")
    deleted = SqliteTaskStore().delete_knowledge_relation(base_dir, normalized_id)
    if not deleted:
        raise ValueError(f"Unknown knowledge relation: {normalized_id}")


def build_knowledge_relation_report(relation: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Knowledge Relation",
            "",
            f"relation_id: {relation.get('relation_id', '')}",
            f"source_object_id: {relation.get('source_object_id', '')}",
            f"target_object_id: {relation.get('target_object_id', '')}",
            f"relation_type: {relation.get('relation_type', '')}",
            f"confidence: {relation.get('confidence', 0.0)}",
            f"context: {relation.get('context', '') or '-'}",
            f"created_at: {relation.get('created_at', '')}",
            f"created_by: {relation.get('created_by', '') or '-'}",
        ]
    )


def build_knowledge_relations_report(object_id: str, relations: list[dict[str, object]]) -> str:
    lines = [
        "# Knowledge Relations",
        "",
        f"object_id: {object_id}",
        f"count: {len(relations)}",
        "",
        "## Relations",
    ]
    if not relations:
        lines.append("- no relations")
        return "\n".join(lines)

    for relation in relations:
        lines.extend(
            [
                f"- {relation.get('relation_id', '')}",
                f"  direction: {relation.get('direction', '')}",
                f"  relation_type: {relation.get('relation_type', '')}",
                f"  counterparty_object_id: {relation.get('counterparty_object_id', '')}",
                f"  confidence: {relation.get('confidence', 0.0)}",
                f"  context: {relation.get('context', '') or '-'}",
            ]
        )
    return "\n".join(lines)
