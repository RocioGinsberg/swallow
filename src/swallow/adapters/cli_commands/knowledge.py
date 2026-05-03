from __future__ import annotations

from pathlib import Path

from swallow._io_helpers import read_json_lines_or_empty
from swallow.application.commands.knowledge import (
    StagePromotePreflightError,
    apply_relation_suggestions_command,
    create_knowledge_relation_command,
    delete_knowledge_relation_command,
    ingest_knowledge_file_command,
    migrate_knowledge_command,
    promote_stage_candidate_command,
    reject_stage_candidate_command,
    resolve_stage_candidate,
)
from swallow.knowledge_retrieval.knowledge_plane import (
    StagedCandidate,
    audit_canonical_registry,
    build_canonical_audit_report,
    build_ingestion_report,
    build_ingestion_summary,
    build_knowledge_relation_report,
    build_knowledge_relations_report,
    build_relation_suggestion_application_report,
    list_knowledge_relations,
    list_staged_knowledge as load_staged_candidates,
)
from swallow.surface_tools.paths import canonical_registry_path
from swallow.surface_tools.workspace import resolve_path


def handle_knowledge_command(base_dir: Path, args: object) -> int | None:
    if getattr(args, "command", None) != "knowledge":
        return None

    knowledge_command = getattr(args, "knowledge_command", None)
    if knowledge_command == "stage-list":
        return _handle_stage_list(base_dir, args)
    if knowledge_command == "stage-inspect":
        print(build_stage_candidate_inspect_report(resolve_stage_candidate(base_dir, getattr(args, "candidate_id"))))
        return 0
    if knowledge_command == "stage-promote":
        try:
            result = promote_stage_candidate_command(
                base_dir,
                getattr(args, "candidate_id"),
                note=getattr(args, "note"),
                refined_text=getattr(args, "text"),
                force=bool(getattr(args, "force")),
            )
        except StagePromotePreflightError as exc:
            _print_stage_promote_notices(exc.notices)
            raise ValueError(str(exc)) from exc
        _print_stage_promote_notices(result.notices)
        print(f"{result.candidate.candidate_id} staged_promoted canonical_id=canonical-{result.candidate.candidate_id}")
        return 0
    if knowledge_command == "stage-reject":
        updated = reject_stage_candidate_command(base_dir, getattr(args, "candidate_id"), note=getattr(args, "note"))
        print(f"{updated.candidate_id} staged_rejected status={updated.status}")
        return 0
    if knowledge_command == "canonical-audit":
        canonical_records = read_json_lines_or_empty(canonical_registry_path(base_dir))
        print(build_canonical_audit_report(audit_canonical_registry(base_dir, canonical_records)))
        return 0
    if knowledge_command == "ingest-file":
        result = ingest_knowledge_file_command(
            base_dir,
            resolve_path(getattr(args, "source_path")),
            dry_run=bool(getattr(args, "dry_run")),
        )
        output = build_ingestion_report(result)
        if bool(getattr(args, "summary")):
            output = f"{output}\n\n{build_ingestion_summary(result)}"
        print(output)
        return 0
    if knowledge_command == "link":
        relation = create_knowledge_relation_command(
            base_dir,
            source_object_id=getattr(args, "source_object_id"),
            target_object_id=getattr(args, "target_object_id"),
            relation_type=getattr(args, "relation_type"),
            confidence=float(getattr(args, "confidence")),
            context=getattr(args, "context"),
        )
        print(build_knowledge_relation_report(relation))
        return 0
    if knowledge_command == "unlink":
        relation_id = getattr(args, "relation_id")
        delete_knowledge_relation_command(base_dir, relation_id)
        print(f"deleted_relation_id: {relation_id}")
        return 0
    if knowledge_command == "links":
        object_id = getattr(args, "object_id")
        relations = list_knowledge_relations(base_dir, object_id)
        print(build_knowledge_relations_report(object_id, relations))
        return 0
    if knowledge_command == "apply-suggestions":
        report = apply_relation_suggestions_command(
            base_dir,
            getattr(args, "task_id"),
            dry_run=bool(getattr(args, "dry_run")),
        )
        print(build_relation_suggestion_application_report(report), end="")
        return 0
    if knowledge_command == "migrate":
        print(format_knowledge_migration_summary(migrate_knowledge_command(base_dir, dry_run=bool(getattr(args, "dry_run")))))
        return 0
    return None


def _handle_stage_list(base_dir: Path, args: object) -> int:
    candidates = load_staged_candidates(base_dir)
    if getattr(args, "all", False):
        lines = [
            "# Staged Knowledge Registry",
            "",
            f"- count: {len(candidates)}",
            "",
            "## Candidates",
        ]
        if not candidates:
            lines.append("- no staged candidates")
        else:
            for candidate in candidates:
                lines.extend(
                    [
                        f"- {candidate.candidate_id}",
                        f"  status: {candidate.status}",
                        f"  source_task_id: {candidate.source_task_id}",
                        f"  submitted_by: {candidate.submitted_by or 'unknown'}",
                        f"  taxonomy: {candidate.taxonomy_role or '-'} / {candidate.taxonomy_memory_authority or '-'}",
                    ]
                )
        print("\n".join(lines))
    else:
        print(build_stage_candidate_list_report(candidates))
    return 0


def _print_stage_promote_notices(notices: list[dict[str, str]]) -> None:
    for notice in notices:
        print(format_stage_promote_preflight_notice(notice))


def build_stage_candidate_list_report(candidates: list[StagedCandidate]) -> str:
    pending_candidates = [candidate for candidate in candidates if candidate.status == "pending"]
    lines = [
        "# Staged Knowledge Review Queue",
        "",
        f"- pending_count: {len(pending_candidates)}",
        "",
        "## Candidates",
    ]
    if not pending_candidates:
        lines.append("- no pending candidates")
        return "\n".join(lines)

    for candidate in pending_candidates:
        preview = candidate.text if len(candidate.text) <= 72 else candidate.text[:69] + "..."
        lines.extend(
            [
                f"- {candidate.candidate_id}",
                f"  source_task_id: {candidate.source_task_id}",
                f"  topic: {candidate.topic or '-'}",
                f"  source_kind: {candidate.source_kind or '-'}",
                f"  source_ref: {candidate.source_ref or '-'}",
                f"  source_object_id: {candidate.source_object_id or 'none'}",
                f"  submitted_by: {candidate.submitted_by or 'unknown'}",
                f"  taxonomy: {candidate.taxonomy_role or '-'} / {candidate.taxonomy_memory_authority or '-'}",
                f"  wiki_mode: {candidate.wiki_mode or '-'}",
                f"  target_object_id: {candidate.target_object_id or '-'}",
                f"  conflict_flag: {candidate.conflict_flag or '-'}",
                f"  submitted_at: {candidate.submitted_at}",
                f"  text: {preview or '(empty)'}",
            ]
        )
    return "\n".join(lines)


def build_stage_candidate_inspect_report(candidate: StagedCandidate) -> str:
    return "\n".join(
        [
            f"Staged Candidate: {candidate.candidate_id}",
            f"status: {candidate.status}",
            f"source_task_id: {candidate.source_task_id}",
            f"topic: {candidate.topic or '-'}",
            f"source_kind: {candidate.source_kind or '-'}",
            f"source_ref: {candidate.source_ref or '-'}",
            f"source_object_id: {candidate.source_object_id or '-'}",
            f"submitted_by: {candidate.submitted_by or '-'}",
            f"submitted_at: {candidate.submitted_at}",
            f"taxonomy_role: {candidate.taxonomy_role or '-'}",
            f"taxonomy_memory_authority: {candidate.taxonomy_memory_authority or '-'}",
            f"wiki_mode: {candidate.wiki_mode or '-'}",
            f"target_object_id: {candidate.target_object_id or '-'}",
            f"source_pack_count: {len(candidate.source_pack)}",
            f"relation_metadata_count: {len(candidate.relation_metadata)}",
            f"conflict_flag: {candidate.conflict_flag or '-'}",
            f"decided_at: {candidate.decided_at or '-'}",
            f"decided_by: {candidate.decided_by or '-'}",
            f"decision_note: {candidate.decision_note or '-'}",
            "",
            "Rationale",
            candidate.rationale or "(empty)",
            "",
            "Text",
            candidate.text or "(empty)",
        ]
    )


def format_stage_promote_preflight_notice(notice: dict[str, str]) -> str:
    notice_type = notice.get("notice_type", "").strip()
    canonical_id = notice.get("canonical_id", "").strip() or "unknown"
    text_preview = notice.get("text_preview", "").strip() or "(empty)"
    if notice_type == "supersede":
        return f"[SUPERSEDE] canonical_id={canonical_id} text={text_preview}"
    if notice_type == "idempotent":
        return f"[IDEMPOTENT] canonical_id={canonical_id} text={text_preview}"
    if notice_type == "conflict":
        return f"[CONFLICT] target={canonical_id} text={text_preview}"
    return f"[NOTICE] canonical_id={canonical_id} text={text_preview}"


def format_knowledge_migration_summary(summary: dict[str, object]) -> str:
    migrated_task_ids = summary.get("migrated_task_ids", [])
    skipped_task_ids = summary.get("skipped_task_ids", [])
    failed_task_ids = summary.get("failed_task_ids", [])
    error_items = summary.get("errors", {})
    lines = [
        f"db_path={summary.get('db_path', '')}",
        f"dry_run={'yes' if summary.get('dry_run', False) else 'no'}",
        f"task_count_scanned={summary.get('task_count_scanned', 0)}",
        f"task_count_migrated={summary.get('task_count_migrated', 0)}",
        f"task_count_skipped={summary.get('task_count_skipped', 0)}",
        f"task_count_failed={summary.get('task_count_failed', 0)}",
        f"knowledge_object_count_migrated={summary.get('knowledge_object_count_migrated', 0)}",
        f"knowledge_object_count_skipped={summary.get('knowledge_object_count_skipped', 0)}",
        f"knowledge_object_count_failed={summary.get('knowledge_object_count_failed', 0)}",
        "migrated_task_ids=" + ",".join(str(item) for item in migrated_task_ids),
        "skipped_task_ids=" + ",".join(str(item) for item in skipped_task_ids),
        "failed_task_ids=" + ",".join(str(item) for item in failed_task_ids),
        "errors=" + "; ".join(f"{task_id}:{message}" for task_id, message in sorted(error_items.items())),
    ]
    return "\n".join(lines)
