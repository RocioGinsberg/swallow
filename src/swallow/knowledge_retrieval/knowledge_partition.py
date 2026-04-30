from __future__ import annotations


def build_knowledge_partition(knowledge_objects: list[dict[str, object]]) -> dict[str, object]:
    task_linked: list[dict[str, object]] = []
    reusable_candidates: list[dict[str, object]] = []

    for item in knowledge_objects:
        record = {
            "object_id": item.get("object_id", "unknown"),
            "stage": item.get("stage", "raw"),
            "evidence_status": item.get("evidence_status", "unbacked"),
            "retrieval_eligible": bool(item.get("retrieval_eligible", False)),
            "knowledge_reuse_scope": item.get("knowledge_reuse_scope", "task_only"),
            "artifact_ref": item.get("artifact_ref", ""),
            "source_ref": item.get("source_ref", ""),
            "text": item.get("text", ""),
        }
        if bool(item.get("task_linked", False)):
            task_linked.append(record)
        if record["knowledge_reuse_scope"] == "retrieval_candidate":
            reusable_candidates.append(record)

    return {
        "task_linked_count": len(task_linked),
        "reusable_candidate_count": len(reusable_candidates),
        "task_linked": task_linked,
        "reusable_candidates": reusable_candidates,
    }


def build_knowledge_partition_report(partition: dict[str, object]) -> str:
    lines = [
        "# Knowledge Partition Report",
        "",
        f"- task_linked_count: {partition.get('task_linked_count', 0)}",
        f"- reusable_candidate_count: {partition.get('reusable_candidate_count', 0)}",
        "",
        "## Task-Linked Knowledge",
    ]
    task_linked = partition.get("task_linked", [])
    if not task_linked:
        lines.append("- none")
    else:
        for item in task_linked:
            lines.append(
                f"- {item.get('object_id', 'unknown')} [{item.get('stage', 'raw')}/{item.get('knowledge_reuse_scope', 'task_only')}] {item.get('text', '') or '(empty)'}"
            )

    lines.extend(["", "## Reusable Retrieval Candidates"])
    reusable_candidates = partition.get("reusable_candidates", [])
    if not reusable_candidates:
        lines.append("- none")
    else:
        for item in reusable_candidates:
            lines.append(
                f"- {item.get('object_id', 'unknown')} [{item.get('stage', 'raw')}/{item.get('evidence_status', 'unbacked')}] {item.get('text', '') or '(empty)'}"
            )
    return "\n".join(lines)
