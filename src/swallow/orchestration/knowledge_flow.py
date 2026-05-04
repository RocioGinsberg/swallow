from __future__ import annotations

import json

from pathlib import Path

from swallow.knowledge_retrieval.knowledge_plane import (
    canonicalization_status_for,
    normalize_task_knowledge_view,
    split_task_knowledge_view,
    summarize_canonicalization,
    summarize_knowledge_evidence,
    summarize_knowledge_reuse,
    summarize_knowledge_stages,
)
from swallow.application.infrastructure.paths import (
    knowledge_evidence_entry_path,
    knowledge_objects_path,
    knowledge_wiki_entry_path,
)


def _store_entry_id(entry: dict[str, object]) -> str:
    entry_id = str(entry.get("object_id") or entry.get("source_object_id") or entry.get("canonical_id") or "").strip()
    return entry_id or "knowledge-entry"


def build_knowledge_store_write_plan(
    base_dir: Path,
    task_id: str,
    knowledge_objects: list[dict[str, object]],
) -> tuple[list[dict[str, object]], dict[Path, str], list[Path]]:
    normalized_view = normalize_task_knowledge_view(knowledge_objects)
    evidence_entries, wiki_entries = split_task_knowledge_view(normalized_view)
    updates: dict[Path, str] = {
        knowledge_objects_path(base_dir, task_id): json.dumps(normalized_view, indent=2) + "\n",
    }
    deletes: list[Path] = []

    for entries, path_factory in (
        (evidence_entries, lambda entry_id: knowledge_evidence_entry_path(base_dir, task_id, entry_id)),
        (wiki_entries, lambda entry_id: knowledge_wiki_entry_path(base_dir, task_id, entry_id)),
    ):
        desired_names: set[str] = set()
        for entry in entries:
            entry_id = _store_entry_id(entry)
            desired_names.add(f"{entry_id}.json")
            updates[path_factory(entry_id)] = json.dumps(entry, indent=2) + "\n"
        store_root = path_factory("placeholder").parent
        if store_root.exists():
            for path in store_root.glob("*.json"):
                if path.name not in desired_names:
                    deletes.append(path)

    return normalized_view, updates, deletes


def build_knowledge_summary_payload(
    knowledge_objects: list[dict[str, object]],
    *,
    knowledge_partition: dict[str, object],
    knowledge_index: dict[str, object],
) -> dict[str, object]:
    return {
        "knowledge_objects_count": len(knowledge_objects),
        "knowledge_stage_counts": summarize_knowledge_stages(knowledge_objects),
        "knowledge_evidence_counts": summarize_knowledge_evidence(knowledge_objects),
        "knowledge_reuse_counts": summarize_knowledge_reuse(knowledge_objects),
        "knowledge_canonicalization_counts": summarize_canonicalization(knowledge_objects),
        "knowledge_partition": {
            "task_linked_count": knowledge_partition["task_linked_count"],
            "reusable_candidate_count": knowledge_partition["reusable_candidate_count"],
        },
        "knowledge_index": {
            "active_reusable_count": knowledge_index["active_reusable_count"],
            "inactive_reusable_count": knowledge_index["inactive_reusable_count"],
            "refreshed_at": knowledge_index["refreshed_at"],
        },
    }


def build_knowledge_objects_report(knowledge_objects: list[dict[str, object]]) -> str:
    stage_counts = summarize_knowledge_stages(knowledge_objects)
    evidence_counts = summarize_knowledge_evidence(knowledge_objects)
    reuse_counts = summarize_knowledge_reuse(knowledge_objects)
    canonicalization_counts = summarize_canonicalization(knowledge_objects)
    lines = [
        "# Knowledge Objects Report",
        "",
        f"- count: {len(knowledge_objects)}",
        f"- raw: {stage_counts.get('raw', 0)}",
        f"- candidate: {stage_counts.get('candidate', 0)}",
        f"- verified: {stage_counts.get('verified', 0)}",
        f"- canonical: {stage_counts.get('canonical', 0)}",
        f"- artifact_backed: {evidence_counts.get('artifact_backed', 0)}",
        f"- source_only: {evidence_counts.get('source_only', 0)}",
        f"- unbacked: {evidence_counts.get('unbacked', 0)}",
        f"- retrieval_candidate: {reuse_counts.get('retrieval_candidate', 0)}",
        f"- task_only: {reuse_counts.get('task_only', 0)}",
        f"- canonicalization_not_requested: {canonicalization_counts.get('not_requested', 0)}",
        f"- canonicalization_review_ready: {canonicalization_counts.get('review_ready', 0)}",
        f"- canonicalization_promotion_ready: {canonicalization_counts.get('promotion_ready', 0)}",
        f"- canonicalization_blocked_stage: {canonicalization_counts.get('blocked_stage', 0)}",
        f"- canonicalization_blocked_evidence: {canonicalization_counts.get('blocked_evidence', 0)}",
        f"- canonicalization_canonical: {canonicalization_counts.get('canonical', 0)}",
        "",
        "## Objects",
    ]
    if not knowledge_objects:
        lines.append("- none")
        return "\n".join(lines)

    for item in knowledge_objects:
        lines.extend(
            [
                f"- id: {item.get('object_id', 'unknown')}",
                f"  stage: {item.get('stage', 'raw')}",
                f"  source_kind: {item.get('source_kind', 'unknown')}",
                f"  source_ref: {item.get('source_ref', '') or 'none'}",
                f"  captured_at: {item.get('captured_at', 'unknown')}",
                f"  task_linked: {'yes' if item.get('task_linked', False) else 'no'}",
                f"  evidence_status: {item.get('evidence_status', 'unbacked')}",
                f"  artifact_ref: {item.get('artifact_ref', '') or 'none'}",
                f"  retrieval_eligible: {'yes' if item.get('retrieval_eligible', False) else 'no'}",
                f"  knowledge_reuse_scope: {item.get('knowledge_reuse_scope', 'task_only')}",
                f"  canonicalization_intent: {item.get('canonicalization_intent', 'none')}",
                f"  canonicalization_status: {canonicalization_status_for(item)}",
                f"  text: {item.get('text', '') or '(empty)'}",
            ]
        )
    return "\n".join(lines)
