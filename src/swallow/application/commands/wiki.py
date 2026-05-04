from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from swallow.knowledge_retrieval.knowledge_plane import load_task_knowledge_view, persist_task_knowledge_view
from swallow.orchestration.models import TaskCard
from swallow.application.services.wiki_compiler import (
    WIKI_COMPILER_PARSER_VERSION,
    WikiCompilerAgent,
    WikiCompilerRunResult,
    build_wiki_compiler_source_pack,
)
from swallow.truth_governance.store import load_state


__all__ = [
    "EvidenceRefreshCommandResult",
    "WikiCompilerRunResult",
    "draft_wiki_command",
    "refine_wiki_command",
    "refresh_wiki_evidence_command",
]


@dataclass(frozen=True, slots=True)
class EvidenceRefreshCommandResult:
    task_id: str
    target_object_id: str
    source_ref: str
    parser_version: str
    content_hash: str
    span: str
    heading_path: str
    evidence_entry: dict[str, object]


def draft_wiki_command(
    base_dir: Path,
    *,
    task_id: str,
    topic: str,
    source_refs: list[str],
    model: str = "",
    dry_run: bool = False,
) -> WikiCompilerRunResult:
    state = load_state(base_dir, task_id)
    return WikiCompilerAgent().compile(
        base_dir,
        state,
        action="draft",
        source_refs=source_refs,
        topic=topic,
        model=model,
        dry_run=dry_run,
    )


def refine_wiki_command(
    base_dir: Path,
    *,
    task_id: str,
    mode: str,
    target_object_id: str,
    source_refs: list[str],
    model: str = "",
    dry_run: bool = False,
) -> WikiCompilerRunResult:
    state = load_state(base_dir, task_id)
    return WikiCompilerAgent().compile(
        base_dir,
        state,
        action="refine",
        source_refs=source_refs,
        topic="",
        mode=mode,
        target_object_id=target_object_id,
        model=model,
        dry_run=dry_run,
    )


def refresh_wiki_evidence_command(
    base_dir: Path,
    *,
    task_id: str,
    target_object_id: str,
    source_ref: str,
    parser_version: str,
    span: str,
    heading_path: str = "",
) -> EvidenceRefreshCommandResult:
    state = load_state(base_dir, task_id)
    normalized_parser_version = parser_version.strip() or WIKI_COMPILER_PARSER_VERSION
    normalized_span = span.strip()
    normalized_heading_path = heading_path.strip()
    if not normalized_span and not normalized_heading_path:
        raise ValueError("refresh-evidence requires --span or --heading-path.")

    source_pack = build_wiki_compiler_source_pack(
        base_dir,
        [source_ref],
        workspace_root=state.workspace_root or base_dir,
        parser_version=normalized_parser_version,
    )
    anchor = source_pack[0]
    knowledge_view = load_task_knowledge_view(base_dir, task_id)
    if not knowledge_view:
        knowledge_view = [dict(item) for item in state.knowledge_objects]

    updated_view: list[dict[str, object]] = []
    refreshed_entry: dict[str, object] | None = None
    normalized_target = target_object_id.strip()
    for entry in knowledge_view:
        payload = dict(entry)
        if str(payload.get("object_id", "")).strip() != normalized_target:
            updated_view.append(payload)
            continue
        if str(payload.get("stage", "raw")).strip() == "canonical":
            raise ValueError("refresh-evidence target must be an evidence object, not a canonical wiki entry.")
        payload.update(
            {
                "source_ref": str(anchor.get("source_ref", "")),
                "evidence_status": "source_only",
                "content_hash": str(anchor.get("content_hash", "")),
                "parser_version": normalized_parser_version,
                "span": normalized_span,
                "heading_path": normalized_heading_path,
                "line_start": int(anchor.get("line_start", 0) or 0),
                "line_end": int(anchor.get("line_end", 0) or 0),
            }
        )
        refreshed_entry = payload
        updated_view.append(payload)

    if refreshed_entry is None:
        raise ValueError(f"Unknown evidence object: {normalized_target}")

    persist_task_knowledge_view(base_dir, task_id, updated_view, write_authority="task-state")
    return EvidenceRefreshCommandResult(
        task_id=task_id,
        target_object_id=normalized_target,
        source_ref=str(anchor.get("source_ref", "")),
        parser_version=normalized_parser_version,
        content_hash=str(anchor.get("content_hash", "")),
        span=normalized_span,
        heading_path=normalized_heading_path,
        evidence_entry=refreshed_entry,
    )


def build_wiki_compiler_task_card(
    *,
    action: str,
    source_refs: list[str],
    topic: str = "",
    mode: str = "",
    target_object_id: str = "",
    model: str = "",
    dry_run: bool = False,
) -> TaskCard:
    return TaskCard(
        goal=f"Wiki Compiler {action}",
        input_context={
            "action": action,
            "source_refs": list(source_refs),
            "topic": topic,
            "mode": mode,
            "target_object_id": target_object_id,
            "model": model,
            "dry_run": dry_run,
        },
        executor_type="wiki-compiler",
    )
