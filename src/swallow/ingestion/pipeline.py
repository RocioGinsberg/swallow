from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..models import LIBRARIAN_SYSTEM_ROLE
from ..staged_knowledge import StagedCandidate, submit_staged_candidate
from .filters import ExtractedFragment, filter_conversation_turns
from .parsers import ConversationTurn, parse_ingestion_path


EXTERNAL_SESSION_SOURCE_KIND = "external_session_ingestion"
DEFAULT_INGESTION_SUBMITTED_BY = "swl_ingest"
DEFAULT_INGESTION_TAXONOMY_ROLE = LIBRARIAN_SYSTEM_ROLE
DEFAULT_INGESTION_TAXONOMY_MEMORY_AUTHORITY = "staged-knowledge"


@dataclass(slots=True)
class IngestionPipelineResult:
    source_path: str
    detected_format: str
    turns: list[ConversationTurn] = field(default_factory=list)
    fragments: list[ExtractedFragment] = field(default_factory=list)
    staged_candidates: list[StagedCandidate] = field(default_factory=list)
    dry_run: bool = False


def run_ingestion_pipeline(
    base_dir: Path,
    source_path: Path,
    *,
    format_hint: str | None = None,
    dry_run: bool = False,
    submitted_by: str = DEFAULT_INGESTION_SUBMITTED_BY,
    taxonomy_role: str = DEFAULT_INGESTION_TAXONOMY_ROLE,
    taxonomy_memory_authority: str = DEFAULT_INGESTION_TAXONOMY_MEMORY_AUTHORITY,
) -> IngestionPipelineResult:
    resolved_source = source_path.resolve()
    turns = parse_ingestion_path(resolved_source, format_hint=format_hint)
    fragments = filter_conversation_turns(turns)
    staged_candidates = build_staged_candidates(
        fragments,
        source_path=resolved_source,
        source_task_id=_build_source_task_id(resolved_source),
        submitted_by=submitted_by,
        taxonomy_role=taxonomy_role,
        taxonomy_memory_authority=taxonomy_memory_authority,
    )

    persisted_candidates = staged_candidates
    if not dry_run:
        persisted_candidates = [submit_staged_candidate(base_dir, candidate) for candidate in staged_candidates]

    return IngestionPipelineResult(
        source_path=str(resolved_source),
        detected_format=_resolve_detected_format(resolved_source, format_hint),
        turns=turns,
        fragments=fragments,
        staged_candidates=persisted_candidates,
        dry_run=dry_run,
    )


def build_staged_candidates(
    fragments: list[ExtractedFragment],
    *,
    source_path: Path,
    source_task_id: str,
    submitted_by: str,
    taxonomy_role: str,
    taxonomy_memory_authority: str,
) -> list[StagedCandidate]:
    candidates: list[StagedCandidate] = []
    source_ref = str(source_path)
    for index, fragment in enumerate(fragments, start=1):
        candidates.append(
            StagedCandidate(
                candidate_id="",
                text=fragment.text,
                source_task_id=source_task_id,
                source_kind=EXTERNAL_SESSION_SOURCE_KIND,
                source_ref=source_ref,
                source_object_id=_build_source_object_id(source_task_id, index),
                submitted_by=submitted_by,
                taxonomy_role=taxonomy_role,
                taxonomy_memory_authority=taxonomy_memory_authority,
            )
        )
    return candidates


def build_ingestion_summary(result: IngestionPipelineResult) -> str:
    decisions = _collect_summary_items(result.fragments, _is_decision_fragment)
    constraints = _collect_summary_items(result.fragments, _is_constraint_fragment)
    rejected = _collect_summary_items(result.fragments, _is_rejected_fragment)
    abandoned_branch_count = sum(1 for fragment in result.fragments if fragment.metadata.get("branch", "") == "abandoned")
    dropped_chatter = max(len(result.turns) - len(result.fragments), 0)

    lines = [
        "# Ingestion Summary",
        "",
        f"## Decisions ({len(decisions)})",
    ]
    lines.extend(_render_summary_section(decisions))
    lines.extend(
        [
            "",
            f"## Constraints ({len(constraints)})",
        ]
    )
    lines.extend(_render_summary_section(constraints))
    lines.extend(
        [
            "",
            f"## Rejected Alternatives ({len(rejected)})",
        ]
    )
    lines.extend(_render_summary_section(rejected))
    lines.extend(
        [
            "",
            "## Statistics",
            f"- total_turns: {len(result.turns)}",
            f"- kept_fragments: {len(result.fragments)}",
            f"- dropped_chatter: {dropped_chatter}",
            f"- abandoned_branches: {abandoned_branch_count}",
            "- precision_estimate: N/A (requires eval golden dataset)",
        ]
    )
    return "\n".join(lines)


def build_ingestion_report(result: IngestionPipelineResult) -> str:
    lines = [
        "# Ingestion Report",
        "",
        f"- source_path: {result.source_path}",
        f"- detected_format: {result.detected_format}",
        f"- turns: {len(result.turns)}",
        f"- fragments: {len(result.fragments)}",
        f"- dry_run: {'yes' if result.dry_run else 'no'}",
        f"- staged_candidates: {len(result.staged_candidates)}",
        "",
        "## Candidates",
    ]
    if not result.staged_candidates:
        lines.append("- no extracted candidates")
        return "\n".join(lines)

    for candidate in result.staged_candidates:
        preview = " ".join(candidate.text.split())
        if len(preview) > 80:
            preview = preview[:77].rstrip() + "..."
        lines.extend(
            [
                f"- {candidate.candidate_id}",
                f"  source_kind: {candidate.source_kind or '-'}",
                f"  source_task_id: {candidate.source_task_id}",
                f"  source_object_id: {candidate.source_object_id or '-'}",
                f"  submitted_by: {candidate.submitted_by or '-'}",
                f"  status: {candidate.status}",
                f"  text: {preview or '(empty)'}",
            ]
        )
    return "\n".join(lines)


def _collect_summary_items(
    fragments: list[ExtractedFragment],
    predicate: Callable[[ExtractedFragment], bool],
) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for fragment in fragments:
        if not predicate(fragment):
            continue
        normalized = " ".join(fragment.text.split())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        items.append(normalized)
    return items


def _render_summary_section(items: list[str]) -> list[str]:
    if not items:
        return ["- none"]
    return [f"- {item}" for item in items]


def _is_decision_fragment(fragment: ExtractedFragment) -> bool:
    if "keyword" not in fragment.signals:
        return False
    lowered = fragment.text.lower()
    return any(token in lowered for token in ("决定", "decision", "outcome"))


def _is_constraint_fragment(fragment: ExtractedFragment) -> bool:
    if "keyword" not in fragment.signals:
        return False
    lowered = fragment.text.lower()
    return any(token in lowered for token in ("约束", "constraint", "non-goal", "non-goals", "不做"))


def _is_rejected_fragment(fragment: ExtractedFragment) -> bool:
    if "rejected_alternative" in fragment.signals or fragment.metadata.get("branch", "") == "abandoned":
        return True
    lowered = fragment.text.lower()
    return any(token in lowered for token in ("reject", "rejected", "abandon", "abandoned", "switch to", "改用", "放弃"))


def _build_source_task_id(source_path: Path) -> str:
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "-", source_path.stem).strip("-").lower() or "session"
    return f"ingest-{stem}"


def _build_source_object_id(source_task_id: str, index: int) -> str:
    return f"{source_task_id}-fragment-{index:04d}"


def _resolve_detected_format(source_path: Path, format_hint: str | None) -> str:
    if format_hint:
        return format_hint.strip().lower()
    if source_path.suffix.lower() in {".md", ".markdown"}:
        return "markdown"
    return "auto"
