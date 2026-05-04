from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from swallow._io_helpers import read_json_lines_or_empty
from swallow.knowledge_retrieval.knowledge_plane import (
    IngestionPipelineResult,
    OPERATOR_CANONICAL_WRITE_AUTHORITY,
    StagedCandidate,
    apply_relation_suggestions,
    build_staged_canonical_key,
    create_knowledge_relation,
    decide_staged_knowledge,
    delete_knowledge_relation,
    ingest_local_file,
    list_staged_knowledge,
    migrate_file_knowledge_to_sqlite,
)
from swallow.application.infrastructure.paths import canonical_registry_path
from swallow.truth_governance.governance import (
    OperatorToken,
    ProposalTarget,
    apply_proposal,
    register_canonical_proposal,
)
from swallow.truth_governance.store import load_state


__all__ = [
    "IngestionPipelineResult",
    "StagePromoteCommandResult",
    "StagePromotePreflightError",
    "StagedCandidate",
    "UnknownStagedCandidateError",
    "apply_relation_suggestions_command",
    "build_stage_canonical_record",
    "build_stage_promote_preflight_notices",
    "create_knowledge_relation_command",
    "delete_knowledge_relation_command",
    "ingest_knowledge_file_command",
    "migrate_knowledge_command",
    "promote_stage_candidate_command",
    "reject_stage_candidate_command",
    "resolve_stage_candidate",
    "summarize_text_preview",
]


@dataclass(frozen=True)
class StagePromoteCommandResult:
    candidate: StagedCandidate
    notices: list[dict[str, str]]
    relation_records: list[dict[str, object]] = field(default_factory=list)


class StagePromotePreflightError(ValueError):
    def __init__(self, message: str, notices: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.notices = notices


class UnknownStagedCandidateError(ValueError):
    pass


def resolve_stage_candidate(base_dir: Path, candidate_id: str) -> StagedCandidate:
    normalized_id = candidate_id.strip()
    for candidate in list_staged_knowledge(base_dir):
        if candidate.candidate_id == normalized_id:
            return candidate
    raise UnknownStagedCandidateError(f"Unknown staged candidate: {normalized_id}")


def summarize_text_preview(text: str, limit: int) -> str:
    normalized = " ".join(text.split())
    if not normalized:
        return "(empty)"
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(limit - 3, 0)].rstrip() + "..."


def build_stage_canonical_record(
    candidate: StagedCandidate,
    *,
    refined_text: str = "",
) -> dict[str, object]:
    canonical_key = build_staged_canonical_key(
        source_task_id=candidate.source_task_id,
        source_object_id=candidate.source_object_id,
        candidate_id=candidate.candidate_id,
    )
    canonical_text = refined_text.strip() or candidate.text
    return {
        "canonical_id": f"canonical-{candidate.candidate_id}",
        "canonical_key": canonical_key,
        "source_task_id": candidate.source_task_id,
        "source_object_id": candidate.source_object_id,
        "promoted_at": candidate.decided_at,
        "promoted_by": candidate.decided_by or "swl_cli",
        "decision_note": candidate.decision_note,
        "decision_ref": f".swl/staged_knowledge/registry.jsonl#{candidate.candidate_id}",
        "artifact_ref": "",
        "source_ref": candidate.source_ref,
        "text": canonical_text,
        "evidence_status": "source_only",
        "canonical_stage": "canonical",
        "canonical_status": "active",
        "superseded_by": "",
        "superseded_at": "",
        "source_pack": candidate.source_pack,
        "rationale": candidate.rationale,
        "relation_metadata": candidate.relation_metadata,
        "conflict_flag": candidate.conflict_flag,
    }


def build_stage_promote_preflight_notices(
    canonical_records: list[dict[str, object]],
    candidate: StagedCandidate,
) -> list[dict[str, str]]:
    preview_record = build_stage_canonical_record(candidate)
    canonical_id = str(preview_record.get("canonical_id", "")).strip()
    canonical_key = str(preview_record.get("canonical_key", "")).strip()

    notices: list[dict[str, str]] = []
    existing_record = next(
        (
            record
            for record in canonical_records
            if str(record.get("canonical_id", "")).strip() == canonical_id
        ),
        None,
    )
    if canonical_id and existing_record is not None:
        notices.append(
            {
                "notice_type": "idempotent",
                "canonical_id": canonical_id,
                "text_preview": summarize_text_preview(str(existing_record.get("text", "")), 60),
            }
        )

    if canonical_key:
        active_match = next(
            (
                record
                for record in canonical_records
                if str(record.get("canonical_key", "")).strip() == canonical_key
                and str(record.get("canonical_id", "")).strip() != canonical_id
                and str(record.get("canonical_status", "active")).strip() != "superseded"
            ),
            None,
        )
        if active_match is not None:
            notices.append(
                {
                    "notice_type": "supersede",
                    "canonical_id": str(active_match.get("canonical_id", "")).strip() or "unknown",
                    "text_preview": summarize_text_preview(str(active_match.get("text", "")), 60),
                }
            )
    if candidate.conflict_flag or any(
        str(item.get("relation_type", "")).strip() == "contradicts" for item in candidate.relation_metadata
    ):
        notices.append(
            {
                "notice_type": "conflict",
                "canonical_id": candidate.target_object_id or candidate.source_object_id or candidate.candidate_id,
                "text_preview": summarize_text_preview(candidate.conflict_flag or candidate.text, 60),
            }
        )
    return notices


def promote_stage_candidate_command(
    base_dir: Path,
    candidate_id: str,
    *,
    note: str,
    refined_text: str = "",
    force: bool = False,
) -> StagePromoteCommandResult:
    candidate = resolve_stage_candidate(base_dir, candidate_id)
    if candidate.status != "pending":
        raise ValueError(f"Staged candidate is already decided: {candidate.candidate_id} ({candidate.status})")
    canonical_records = read_json_lines_or_empty(canonical_registry_path(base_dir))
    notices = build_stage_promote_preflight_notices(canonical_records, candidate)
    if any(notice.get("notice_type") == "supersede" for notice in notices) and not force:
        raise StagePromotePreflightError("Supersede notice detected; rerun with --force to confirm promotion.", notices)
    if any(notice.get("notice_type") == "conflict" for notice in notices) and not force:
        raise StagePromotePreflightError("Conflict notice detected; rerun with --force to confirm promotion.", notices)
    decision_note = note.strip()
    if refined_text.strip():
        decision_note = f"{decision_note} [refined]".strip() if decision_note else "[refined]"
    updated = decide_staged_knowledge(
        base_dir,
        candidate.candidate_id,
        "promoted",
        "swl_cli",
        decision_note,
    )
    canonical_record = build_stage_canonical_record(updated, refined_text=refined_text)
    register_canonical_proposal(
        base_dir=base_dir,
        proposal_id=updated.candidate_id,
        canonical_record=canonical_record,
        write_authority=OPERATOR_CANONICAL_WRITE_AUTHORITY,
        refresh_derived=True,
    )
    apply_proposal(updated.candidate_id, OperatorToken(source="cli"), ProposalTarget.CANONICAL_KNOWLEDGE)
    relation_records = _create_promoted_relation_records(base_dir, updated)
    return StagePromoteCommandResult(candidate=updated, notices=notices, relation_records=relation_records)


def reject_stage_candidate_command(base_dir: Path, candidate_id: str, *, note: str) -> StagedCandidate:
    candidate = resolve_stage_candidate(base_dir, candidate_id)
    if candidate.status != "pending":
        raise ValueError(f"Staged candidate is already decided: {candidate.candidate_id} ({candidate.status})")
    return decide_staged_knowledge(
        base_dir,
        candidate.candidate_id,
        "rejected",
        "swl_cli",
        note,
    )


def ingest_knowledge_file_command(
    base_dir: Path,
    source_path: Path,
    *,
    dry_run: bool = False,
) -> IngestionPipelineResult:
    return ingest_local_file(base_dir, source_path, dry_run=dry_run)


def create_knowledge_relation_command(
    base_dir: Path,
    *,
    source_object_id: str,
    target_object_id: str,
    relation_type: str,
    confidence: float,
    context: str,
) -> dict[str, object]:
    return create_knowledge_relation(
        base_dir,
        source_object_id=source_object_id,
        target_object_id=target_object_id,
        relation_type=relation_type,
        confidence=float(confidence),
        context=context,
        created_by="swl_cli",
    )


def delete_knowledge_relation_command(base_dir: Path, relation_id: str) -> None:
    delete_knowledge_relation(base_dir, relation_id)


def apply_relation_suggestions_command(base_dir: Path, task_id: str, *, dry_run: bool = False) -> dict[str, object]:
    load_state(base_dir, task_id)
    return apply_relation_suggestions(base_dir, task_id, dry_run=dry_run)


def migrate_knowledge_command(base_dir: Path, *, dry_run: bool = False) -> dict[str, object]:
    return migrate_file_knowledge_to_sqlite(base_dir, dry_run=dry_run)


def _create_promoted_relation_records(base_dir: Path, candidate: StagedCandidate) -> list[dict[str, object]]:
    source_object_id = candidate.source_object_id.strip() or f"canonical-{candidate.candidate_id}"
    created: list[dict[str, object]] = []
    for item in candidate.relation_metadata:
        relation_type = str(item.get("relation_type", "")).strip()
        if relation_type != "refines":
            continue
        target_object_id = str(item.get("target_object_id", "")).strip()
        if not target_object_id:
            continue
        created.append(
            create_knowledge_relation(
                base_dir,
                source_object_id=source_object_id,
                target_object_id=target_object_id,
                relation_type="refines",
                confidence=1.0,
                context=f"Operator promoted staged candidate {candidate.candidate_id}.",
                created_by="swl_cli",
            )
        )
    return created
