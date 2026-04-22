from __future__ import annotations

from .knowledge_objects import canonicalization_status_for, is_retrieval_reuse_ready
from .models import utc_now
from .retrieval_adapters import VECTOR_EMBEDDING_DIMENSIONS


def invalidation_reason_for(item: dict[str, object]) -> str:
    reuse_scope = str(item.get("knowledge_reuse_scope", "task_only"))
    if reuse_scope != "retrieval_candidate":
        return "not_retrieval_candidate"
    stage = str(item.get("stage", "raw"))
    if stage != "verified":
        return "stage_not_verified"
    evidence_status = str(item.get("evidence_status", "unbacked"))
    if evidence_status != "artifact_backed":
        return "evidence_not_artifact_backed"
    return "active"


def build_knowledge_index(knowledge_objects: list[dict[str, object]]) -> dict[str, object]:
    reusable_records = []
    inactive_records = []
    for item in knowledge_objects:
        reuse_scope = item.get("knowledge_reuse_scope", "task_only")
        if reuse_scope != "retrieval_candidate":
            continue
        record = {
            "object_id": item.get("object_id", "unknown"),
            "stage": item.get("stage", "raw"),
            "knowledge_reuse_scope": reuse_scope,
            "evidence_status": item.get("evidence_status", "unbacked"),
            "canonicalization_intent": item.get("canonicalization_intent", "none"),
            "canonicalization_status": canonicalization_status_for(item),
            "source_ref": item.get("source_ref", ""),
            "artifact_ref": item.get("artifact_ref", ""),
            "text": item.get("text", ""),
        }
        if is_retrieval_reuse_ready(item):
            record["index_status"] = "active"
            record["vector_index_status"] = "ready"
            record["embedding_dimensions"] = VECTOR_EMBEDDING_DIMENSIONS
            reusable_records.append(record)
        else:
            record["index_status"] = "inactive"
            record["vector_index_status"] = "inactive"
            record["embedding_dimensions"] = VECTOR_EMBEDDING_DIMENSIONS
            record["invalidation_reason"] = invalidation_reason_for(item)
            inactive_records.append(record)
    return {
        "refreshed_at": utc_now(),
        "active_reusable_count": len(reusable_records),
        "inactive_reusable_count": len(inactive_records),
        "vector_index": {
            "backend": "sqlite_vec_optional",
            "fallback_backend": "text_fallback",
            "embedding_dimensions": VECTOR_EMBEDDING_DIMENSIONS,
            "active_candidate_count": len(reusable_records),
        },
        "reusable_records": reusable_records,
        "inactive_records": inactive_records,
    }


def build_knowledge_index_report(index_record: dict[str, object]) -> str:
    reusable_records = list(index_record.get("reusable_records", []))
    inactive_records = list(index_record.get("inactive_records", []))
    lines = [
        "# Knowledge Index Report",
        "",
        f"- refreshed_at: {index_record.get('refreshed_at', 'unknown')}",
        f"- active_reusable_count: {index_record.get('active_reusable_count', len(reusable_records))}",
        f"- inactive_reusable_count: {index_record.get('inactive_reusable_count', len(inactive_records))}",
        f"- vector_backend: {dict(index_record.get('vector_index', {})).get('backend', 'sqlite_vec_optional')}",
        f"- vector_fallback_backend: {dict(index_record.get('vector_index', {})).get('fallback_backend', 'text_fallback')}",
        f"- embedding_dimensions: {dict(index_record.get('vector_index', {})).get('embedding_dimensions', VECTOR_EMBEDDING_DIMENSIONS)}",
        "",
        "## Active Reusable Records",
    ]
    if not reusable_records:
        lines.append("- none")
    else:
        for item in reusable_records:
            lines.extend(
                [
                    f"- {item.get('object_id', 'unknown')} [{item.get('stage', 'raw')}/{item.get('evidence_status', 'unbacked')}/{item.get('knowledge_reuse_scope', 'task_only')}]",
                    f"  canonicalization: {item.get('canonicalization_intent', 'none')} / {item.get('canonicalization_status', 'not_requested')}",
                    f"  vector_index_status: {item.get('vector_index_status', 'unknown')} ({item.get('embedding_dimensions', VECTOR_EMBEDDING_DIMENSIONS)} dims)",
                    f"  artifact_ref: {item.get('artifact_ref', '') or 'none'}",
                    f"  source_ref: {item.get('source_ref', '') or 'none'}",
                    f"  text: {item.get('text', '') or '(empty)'}",
                ]
            )

    lines.extend(["", "## Inactive Reusable Records"])
    if not inactive_records:
        lines.append("- none")
        return "\n".join(lines)

    for item in inactive_records:
        lines.extend(
            [
                f"- {item.get('object_id', 'unknown')} [{item.get('stage', 'raw')}/{item.get('evidence_status', 'unbacked')}/{item.get('knowledge_reuse_scope', 'task_only')}]",
                f"  invalidation_reason: {item.get('invalidation_reason', 'unknown')}",
                f"  canonicalization: {item.get('canonicalization_intent', 'none')} / {item.get('canonicalization_status', 'not_requested')}",
                f"  vector_index_status: {item.get('vector_index_status', 'unknown')} ({item.get('embedding_dimensions', VECTOR_EMBEDDING_DIMENSIONS)} dims)",
                f"  artifact_ref: {item.get('artifact_ref', '') or 'none'}",
                f"  source_ref: {item.get('source_ref', '') or 'none'}",
                f"  text: {item.get('text', '') or '(empty)'}",
            ]
        )
    return "\n".join(lines)
