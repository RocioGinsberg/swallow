from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass, field
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
from .paths import canonical_registry_path
from .store import load_knowledge_objects


LIBRARIAN_EXECUTOR_NAME = "librarian"
LIBRARIAN_AGENT_NAME = LIBRARIAN_EXECUTOR_NAME
LIBRARIAN_CHANGE_LOG_KIND = "librarian_change_log_v0"


def _artifact_exists(base_dir: Path, artifact_ref: str) -> bool:
    normalized = artifact_ref.strip()
    if not normalized:
        return False
    return (base_dir / normalized).exists()


def _normalize_text(text: str) -> str:
    return " ".join(text.split())


def _text_hash(text: str) -> str:
    return _normalize_text(text).casefold()


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


@dataclass(slots=True)
class KnowledgeChangeEntry:
    object_id: str
    action: str
    reason: str
    source: str = LIBRARIAN_AGENT_NAME
    timestamp: str = field(default_factory=utc_now)
    canonical_key: str = ""
    canonical_id: str = ""
    artifact_ref: str = ""
    source_ref: str = ""
    before_text: str = ""
    after_text: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class KnowledgeChangeLog:
    task_id: str
    generated_at: str
    candidate_count: int
    promoted_count: int
    skipped_count: int
    entries: list[KnowledgeChangeEntry] = field(default_factory=list)
    kind: str = LIBRARIAN_CHANGE_LOG_KIND
    agent_name: str = LIBRARIAN_AGENT_NAME
    change_log_artifact: str = ""
    write_authority: str = LIBRARIAN_MEMORY_AUTHORITY

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "task_id": self.task_id,
            "generated_at": self.generated_at,
            "candidate_count": self.candidate_count,
            "promoted_count": self.promoted_count,
            "skipped_count": self.skipped_count,
            "entries": [entry.to_dict() for entry in self.entries],
            "agent_name": self.agent_name,
            "change_log_artifact": self.change_log_artifact,
            "write_authority": self.write_authority,
        }


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
                f"  source: {entry.get('source', LIBRARIAN_AGENT_NAME)}",
                f"  timestamp: {entry.get('timestamp', payload.get('generated_at', 'unknown'))}",
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


class LibrarianAgent:
    """Stateful specialist entity for canonical knowledge promotion."""

    agent_name = LIBRARIAN_AGENT_NAME
    system_role = LIBRARIAN_SYSTEM_ROLE
    memory_authority = LIBRARIAN_MEMORY_AUTHORITY

    def _build_prompt(self, state: TaskState, card: TaskCard) -> str:
        return "\n".join(
            [
                "# Librarian Agent Task",
                "",
                f"- task_id: {state.task_id}",
                f"- agent_name: {self.agent_name}",
                f"- executor_role: {self.system_role}",
                f"- memory_authority: {self.memory_authority}",
                f"- promotion_ready_object_ids: {', '.join(card.input_context.get('promotion_ready_object_ids', [])) or '-'}",
                "- workflow: detect conflicts, dedupe explicit duplicates, normalize text, verify evidence pointers, promote canonical-ready entries, emit change log",
            ]
        )

    def _load_active_canonical_records(self, base_dir: Path) -> list[dict[str, object]]:
        return [
            record
            for record in _load_json_lines(canonical_registry_path(base_dir))
            if str(record.get("canonical_status", "active")).strip() != "superseded"
        ]

    def execute(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[object],
    ) -> ExecutorResult:
        del retrieval_items

        prompt = self._build_prompt(state, card)
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

        generated_at = utc_now()
        entries: list[KnowledgeChangeEntry] = []
        updated_objects = [dict(item) for item in knowledge_objects]
        seen_canonical_keys: set[str] = set()
        seen_text_hashes: set[str] = set()
        decision_records: list[dict[str, object]] = []
        canonical_records: list[dict[str, object]] = []
        active_canonical_records = self._load_active_canonical_records(base_dir)
        active_canonical_ids = {
            str(record.get("canonical_id", "")).strip()
            for record in active_canonical_records
            if str(record.get("canonical_id", "")).strip()
        }
        active_canonical_keys = {
            str(record.get("canonical_key", "")).strip(): dict(record)
            for record in active_canonical_records
            if str(record.get("canonical_key", "")).strip()
        }
        active_text_hashes = {
            _text_hash(str(record.get("text", "")))
            for record in active_canonical_records
            if _text_hash(str(record.get("text", "")))
        }

        for candidate in candidates:
            object_id = str(candidate.get("object_id", "")).strip()
            artifact_ref = str(candidate.get("artifact_ref", "")).strip()
            source_ref = str(candidate.get("source_ref", "")).strip()
            before_text = str(candidate.get("text", ""))
            after_text = _normalize_text(before_text)
            normalized_text_hash = _text_hash(after_text)

            if not object_id:
                entries.append(
                    KnowledgeChangeEntry(
                        object_id="unknown",
                        action="skipped",
                        reason="missing_object_id",
                        source=self.agent_name,
                        timestamp=generated_at,
                        artifact_ref=artifact_ref,
                        source_ref=source_ref,
                        before_text=before_text,
                        after_text=after_text,
                    )
                )
                continue

            if artifact_ref and not _artifact_exists(base_dir, artifact_ref):
                entries.append(
                    KnowledgeChangeEntry(
                        object_id=object_id,
                        action="skipped",
                        reason="artifact_ref_missing",
                        source=self.agent_name,
                        timestamp=generated_at,
                        artifact_ref=artifact_ref,
                        source_ref=source_ref,
                        before_text=before_text,
                        after_text=after_text,
                    )
                )
                continue

            canonical_key = (
                f"artifact:{artifact_ref}"
                if artifact_ref
                else f"source:{source_ref}"
                if source_ref
                else f"task-object:{state.task_id}:{object_id}"
            )
            prospective_canonical_id = f"canonical-{state.task_id}-{object_id}"
            existing_key_record = active_canonical_keys.get(canonical_key)
            if prospective_canonical_id in active_canonical_ids:
                entries.append(
                    KnowledgeChangeEntry(
                        object_id=object_id,
                        action="skipped",
                        reason="duplicate_canonical_id_existing",
                        source=self.agent_name,
                        timestamp=generated_at,
                        canonical_key=canonical_key,
                        canonical_id=prospective_canonical_id,
                        artifact_ref=artifact_ref,
                        source_ref=source_ref,
                        before_text=before_text,
                        after_text=after_text,
                    )
                )
                continue
            if existing_key_record is not None:
                entries.append(
                    KnowledgeChangeEntry(
                        object_id=object_id,
                        action="skipped",
                        reason="conflict_existing_canonical_key",
                        source=self.agent_name,
                        timestamp=generated_at,
                        canonical_key=canonical_key,
                        canonical_id=str(existing_key_record.get("canonical_id", "")).strip(),
                        artifact_ref=artifact_ref,
                        source_ref=source_ref,
                        before_text=before_text,
                        after_text=after_text,
                    )
                )
                continue
            if normalized_text_hash and normalized_text_hash in active_text_hashes:
                entries.append(
                    KnowledgeChangeEntry(
                        object_id=object_id,
                        action="skipped",
                        reason="duplicate_content_hash_existing",
                        source=self.agent_name,
                        timestamp=generated_at,
                        canonical_key=canonical_key,
                        artifact_ref=artifact_ref,
                        source_ref=source_ref,
                        before_text=before_text,
                        after_text=after_text,
                    )
                )
                continue
            if canonical_key in seen_canonical_keys:
                entries.append(
                    KnowledgeChangeEntry(
                        object_id=object_id,
                        action="skipped",
                        reason="duplicate_canonical_key_in_batch",
                        source=self.agent_name,
                        timestamp=generated_at,
                        canonical_key=canonical_key,
                        artifact_ref=artifact_ref,
                        source_ref=source_ref,
                        before_text=before_text,
                        after_text=after_text,
                    )
                )
                continue
            seen_canonical_keys.add(canonical_key)
            if normalized_text_hash and normalized_text_hash in seen_text_hashes:
                entries.append(
                    KnowledgeChangeEntry(
                        object_id=object_id,
                        action="skipped",
                        reason="duplicate_content_hash_in_batch",
                        source=self.agent_name,
                        timestamp=generated_at,
                        canonical_key=canonical_key,
                        artifact_ref=artifact_ref,
                        source_ref=source_ref,
                        before_text=before_text,
                        after_text=after_text,
                    )
                )
                continue
            if normalized_text_hash:
                seen_text_hashes.add(normalized_text_hash)

            for item in updated_objects:
                if str(item.get("object_id", "")).strip() == object_id:
                    item["text"] = after_text
                    break

            updated_objects, decision_record = apply_knowledge_decision(
                updated_objects,
                object_id=object_id,
                decision_type="promote",
                decision_target="canonical",
                caller_authority=self.memory_authority,
                note="Promoted by LibrarianAgent after conflict detection and rule-driven normalization.",
                decided_by=self.agent_name,
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
            active_canonical_ids.add(str(canonical_record["canonical_id"]))
            active_canonical_keys[str(canonical_record["canonical_key"])] = dict(canonical_record)
            if normalized_text_hash:
                active_text_hashes.add(normalized_text_hash)
            entries.append(
                KnowledgeChangeEntry(
                    object_id=object_id,
                    action="promoted",
                    reason="promotion_ready_verified",
                    source=self.agent_name,
                    timestamp=generated_at,
                    canonical_key=str(canonical_record["canonical_key"]),
                    canonical_id=str(canonical_record["canonical_id"]),
                    artifact_ref=artifact_ref,
                    source_ref=source_ref,
                    before_text=before_text,
                    after_text=after_text,
                )
            )

        promoted_count = sum(1 for entry in entries if entry.action == "promoted")
        change_log = KnowledgeChangeLog(
            task_id=state.task_id,
            generated_at=generated_at,
            candidate_count=len(candidates),
            promoted_count=promoted_count,
            skipped_count=len(entries) - promoted_count,
            entries=entries,
            change_log_artifact=f".swl/tasks/{state.task_id}/artifacts/librarian_change_log.json",
            write_authority=self.memory_authority,
        )
        change_log_payload = change_log.to_dict()
        output = json.dumps(change_log_payload, indent=2)

        message = (
            "LibrarianAgent promoted canonical evidence."
            if promoted_count
            else "LibrarianAgent found no promotion-ready evidence to promote."
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
                "agent_name": self.agent_name,
                "write_authority": self.memory_authority,
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


class LibrarianExecutor(LibrarianAgent):
    """Compatibility wrapper that preserves the historical executor name while delegating to LibrarianAgent."""
