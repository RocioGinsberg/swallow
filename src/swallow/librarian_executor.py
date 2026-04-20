from __future__ import annotations

import asyncio
import json
from pathlib import Path

from .canonical_registry import (
    build_canonical_record,
    build_canonical_registry_index,
    build_canonical_registry_index_report,
    build_canonical_registry_report,
)
from .canonical_reuse import build_canonical_reuse_report, build_canonical_reuse_summary
from .knowledge_index import build_knowledge_index, build_knowledge_index_report
from .knowledge_objects import (
    canonicalization_status_for,
    summarize_canonicalization,
    summarize_knowledge_evidence,
    summarize_knowledge_reuse,
    summarize_knowledge_stages,
)
from .knowledge_partition import build_knowledge_partition, build_knowledge_partition_report
from .knowledge_review import apply_knowledge_decision, build_knowledge_decisions_report
from .models import (
    ExecutorResult,
    LIBRARIAN_MEMORY_AUTHORITY,
    LIBRARIAN_SYSTEM_ROLE,
    TaskCard,
    TaskState,
    utc_now,
)
from .store import load_knowledge_objects


LIBRARIAN_EXECUTOR_NAME = "librarian"
LIBRARIAN_CHANGE_LOG_KIND = "librarian_change_log_v0"


def _artifact_exists(base_dir: Path, artifact_ref: str) -> bool:
    normalized = artifact_ref.strip()
    if not normalized:
        return False
    return (base_dir / normalized).exists()


def _normalize_text(text: str) -> str:
    return " ".join(text.split())


def _load_json_lines(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []

    records: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _build_change_log_ref(task_id: str, object_id: str) -> str:
    return f".swl/tasks/{task_id}/artifacts/librarian_change_log.json#{object_id}"


def build_librarian_change_log_report(payload: dict[str, object]) -> str:
    lines = [
        "# Librarian Change Log",
        "",
        f"- kind: {payload.get('kind', LIBRARIAN_CHANGE_LOG_KIND)}",
        f"- task_id: {payload.get('task_id', 'unknown')}",
        f"- generated_at: {payload.get('generated_at', 'unknown')}",
        f"- candidate_count: {payload.get('candidate_count', 0)}",
        f"- promoted_count: {payload.get('promoted_count', 0)}",
        f"- skipped_count: {payload.get('skipped_count', 0)}",
        "",
        "## Entries",
    ]
    entries = payload.get("entries", [])
    if not isinstance(entries, list) or not entries:
        lines.append("- none")
        return "\n".join(lines)

    for entry in entries:
        lines.extend(
            [
                f"- {entry.get('object_id', 'unknown')}",
                f"  action: {entry.get('action', 'unknown')}",
                f"  reason: {entry.get('reason', 'none')}",
                f"  canonical_key: {entry.get('canonical_key', '') or 'none'}",
                f"  canonical_id: {entry.get('canonical_id', '') or 'none'}",
                f"  artifact_ref: {entry.get('artifact_ref', '') or 'none'}",
                f"  source_ref: {entry.get('source_ref', '') or 'none'}",
                f"  before_text: {entry.get('before_text', '') or '(empty)'}",
                f"  after_text: {entry.get('after_text', '') or '(empty)'}",
            ]
        )
    return "\n".join(lines)


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


class LibrarianExecutor:
    """Rule-driven canonical promotion executor for Phase 32."""

    def execute(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[object],
    ) -> ExecutorResult:
        del retrieval_items

        prompt = "\n".join(
            [
                "# Librarian Executor Task",
                "",
                f"- task_id: {state.task_id}",
                f"- executor_role: {LIBRARIAN_SYSTEM_ROLE}",
                f"- memory_authority: {LIBRARIAN_MEMORY_AUTHORITY}",
                f"- promotion_ready_object_ids: {', '.join(card.input_context.get('promotion_ready_object_ids', [])) or '-'}",
                "- workflow: dedupe, normalize, verify evidence pointers, promote canonical-ready entries, emit change log",
            ]
        )
        knowledge_objects = load_knowledge_objects(base_dir, state.task_id)
        if not knowledge_objects:
            knowledge_objects = [dict(item) for item in (state.knowledge_objects or [])]

        promotion_ready_ids = {
            str(item).strip()
            for item in card.input_context.get("promotion_ready_object_ids", [])
            if str(item).strip()
        }
        candidates = [
            dict(item)
            for item in knowledge_objects
            if canonicalization_status_for(item) == "promotion_ready"
            and (not promotion_ready_ids or str(item.get("object_id", "")).strip() in promotion_ready_ids)
        ]

        entries: list[dict[str, object]] = []
        updated_objects = [dict(item) for item in knowledge_objects]
        seen_canonical_keys: set[str] = set()
        decision_records: list[dict[str, object]] = []
        canonical_records: list[dict[str, object]] = []

        for candidate in candidates:
            object_id = str(candidate.get("object_id", "")).strip()
            artifact_ref = str(candidate.get("artifact_ref", "")).strip()
            source_ref = str(candidate.get("source_ref", "")).strip()
            before_text = str(candidate.get("text", ""))
            after_text = _normalize_text(before_text)

            if not object_id:
                entries.append(
                    {
                        "object_id": "unknown",
                        "action": "skipped",
                        "reason": "missing_object_id",
                        "artifact_ref": artifact_ref,
                        "source_ref": source_ref,
                        "before_text": before_text,
                        "after_text": after_text,
                    }
                )
                continue

            if artifact_ref and not _artifact_exists(base_dir, artifact_ref):
                entries.append(
                    {
                        "object_id": object_id,
                        "action": "skipped",
                        "reason": "artifact_ref_missing",
                        "artifact_ref": artifact_ref,
                        "source_ref": source_ref,
                        "before_text": before_text,
                        "after_text": after_text,
                    }
                )
                continue

            canonical_key = (
                f"artifact:{artifact_ref}"
                if artifact_ref
                else f"source:{source_ref}"
                if source_ref
                else f"task-object:{state.task_id}:{object_id}"
            )
            if canonical_key in seen_canonical_keys:
                entries.append(
                    {
                        "object_id": object_id,
                        "action": "skipped",
                        "reason": "duplicate_canonical_key_in_batch",
                        "canonical_key": canonical_key,
                        "artifact_ref": artifact_ref,
                        "source_ref": source_ref,
                        "before_text": before_text,
                        "after_text": after_text,
                    }
                )
                continue
            seen_canonical_keys.add(canonical_key)

            for item in updated_objects:
                if str(item.get("object_id", "")).strip() == object_id:
                    item["text"] = after_text
                    break

            updated_objects, decision_record = apply_knowledge_decision(
                updated_objects,
                object_id=object_id,
                decision_type="promote",
                decision_target="canonical",
                caller_authority=LIBRARIAN_MEMORY_AUTHORITY,
                note="Promoted by LibrarianExecutor after rule-driven normalization.",
                decided_by=LIBRARIAN_EXECUTOR_NAME,
            )
            decision_records.append(decision_record)
            promoted_object = next(item for item in updated_objects if str(item.get("object_id", "")).strip() == object_id)
            canonical_record = build_canonical_record(
                task_id=state.task_id,
                object_id=object_id,
                knowledge_object=promoted_object,
                decision_record=decision_record,
            )
            canonical_record["decision_ref"] = _build_change_log_ref(state.task_id, object_id)
            canonical_records.append(canonical_record)
            entries.append(
                {
                    "object_id": object_id,
                    "action": "promoted",
                    "reason": "promotion_ready_verified",
                    "canonical_key": canonical_record["canonical_key"],
                    "canonical_id": canonical_record["canonical_id"],
                    "artifact_ref": artifact_ref,
                    "source_ref": source_ref,
                    "before_text": before_text,
                    "after_text": after_text,
                }
            )

        promoted_count = sum(1 for entry in entries if entry.get("action") == "promoted")
        change_log_payload = {
            "kind": LIBRARIAN_CHANGE_LOG_KIND,
            "task_id": state.task_id,
            "generated_at": utc_now(),
            "candidate_count": len(candidates),
            "promoted_count": promoted_count,
            "skipped_count": len(entries) - promoted_count,
            "entries": entries,
            "change_log_artifact": f".swl/tasks/{state.task_id}/artifacts/librarian_change_log.json",
        }
        output = json.dumps(change_log_payload, indent=2)

        message = (
            "Librarian promoted canonical evidence."
            if promoted_count
            else "Librarian found no promotion-ready evidence to promote."
        )
        return ExecutorResult(
            executor_name=LIBRARIAN_EXECUTOR_NAME,
            status="completed",
            message=message,
            output=output,
            prompt=prompt,
            dialect="plain_text",
            stdout="",
            stderr="",
            side_effects={
                "kind": LIBRARIAN_CHANGE_LOG_KIND,
                "updated_knowledge_objects": updated_objects,
                "knowledge_decision_records": decision_records,
                "canonical_records": canonical_records,
                "change_log_payload": change_log_payload,
            },
        )

    async def execute_async(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[object],
    ) -> ExecutorResult:
        return await asyncio.to_thread(self.execute, base_dir, state, card, retrieval_items)
