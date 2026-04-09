from __future__ import annotations

from .models import utc_now


def build_canonical_record(
    *,
    task_id: str,
    object_id: str,
    knowledge_object: dict[str, object],
    decision_record: dict[str, object],
) -> dict[str, object]:
    decided_at = str(decision_record.get("decided_at", "")).strip() or utc_now()
    canonical_id = f"canonical-{task_id}-{object_id}"
    return {
        "canonical_id": canonical_id,
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
    }


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
                f"  source_task_id: {record.get('source_task_id', 'unknown')}",
                f"  source_object_id: {record.get('source_object_id', 'unknown')}",
                f"  promoted_at: {record.get('promoted_at', 'unknown')}",
                f"  promoted_by: {record.get('promoted_by', 'unknown')}",
                f"  source_ref: {record.get('source_ref', '') or 'none'}",
                f"  artifact_ref: {record.get('artifact_ref', '') or 'none'}",
                f"  decision_ref: {record.get('decision_ref', '') or 'none'}",
                f"  text: {record.get('text', '') or '(empty)'}",
            ]
        )
    return "\n".join(lines)
