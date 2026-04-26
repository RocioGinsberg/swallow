from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable
from uuid import uuid4

from ..models import LIBRARIAN_SYSTEM_ROLE
from ..staged_knowledge import StagedCandidate, submit_staged_candidate
from .filters import ExtractedFragment, filter_conversation_turns
from .parsers import (
    ConversationTurn,
    detect_ingestion_format,
    normalize_ingestion_format_hint,
    parse_ingestion_bytes,
    parse_ingestion_path,
)


EXTERNAL_SESSION_SOURCE_KIND = "external_session_ingestion"
LOCAL_FILE_SOURCE_KIND = "local_file_capture"
OPERATOR_NOTE_SOURCE_KIND = "operator_note"
DEFAULT_INGESTION_SUBMITTED_BY = "swl_ingest"
DEFAULT_INGESTION_TAXONOMY_ROLE = LIBRARIAN_SYSTEM_ROLE
DEFAULT_INGESTION_TAXONOMY_MEMORY_AUTHORITY = "staged-knowledge"
LOCAL_MARKDOWN_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


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
        source_ref=str(resolved_source),
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
        detected_format=_resolve_detected_format(source_name=resolved_source.name, format_hint=format_hint, source_bytes=None),
        turns=turns,
        fragments=fragments,
        staged_candidates=persisted_candidates,
        dry_run=dry_run,
    )


def run_ingestion_bytes_pipeline(
    base_dir: Path,
    source_bytes: bytes,
    *,
    source_name: str,
    source_ref: str,
    source_task_id: str,
    format_hint: str | None = None,
    dry_run: bool = False,
    submitted_by: str = DEFAULT_INGESTION_SUBMITTED_BY,
    taxonomy_role: str = DEFAULT_INGESTION_TAXONOMY_ROLE,
    taxonomy_memory_authority: str = DEFAULT_INGESTION_TAXONOMY_MEMORY_AUTHORITY,
) -> IngestionPipelineResult:
    turns = parse_ingestion_bytes(source_bytes, format_hint=format_hint, source_name=source_name)
    fragments = filter_conversation_turns(turns)
    staged_candidates = build_staged_candidates(
        fragments,
        source_ref=source_ref,
        source_task_id=source_task_id,
        submitted_by=submitted_by,
        taxonomy_role=taxonomy_role,
        taxonomy_memory_authority=taxonomy_memory_authority,
    )

    persisted_candidates = staged_candidates
    if not dry_run:
        persisted_candidates = [submit_staged_candidate(base_dir, candidate) for candidate in staged_candidates]

    return IngestionPipelineResult(
        source_path=source_ref,
        detected_format=_resolve_detected_format(source_name=source_name, format_hint=format_hint, source_bytes=source_bytes),
        turns=turns,
        fragments=fragments,
        staged_candidates=persisted_candidates,
        dry_run=dry_run,
    )


def ingest_local_file(
    base_dir: Path,
    source_path: Path,
    *,
    dry_run: bool = False,
    submitted_by: str = DEFAULT_INGESTION_SUBMITTED_BY,
    taxonomy_role: str = DEFAULT_INGESTION_TAXONOMY_ROLE,
    taxonomy_memory_authority: str = DEFAULT_INGESTION_TAXONOMY_MEMORY_AUTHORITY,
) -> IngestionPipelineResult:
    resolved_source = source_path.resolve()
    candidate_texts = parse_local_file(resolved_source)
    source_task_id = _build_source_task_id(resolved_source)
    source_ref = f"file://{resolved_source}"

    staged_candidates = [
        StagedCandidate(
            candidate_id="",
            text=text,
            source_task_id=source_task_id,
            source_kind=LOCAL_FILE_SOURCE_KIND,
            source_ref=source_ref,
            source_object_id=_build_source_object_id(source_task_id, index),
            submitted_by=submitted_by,
            taxonomy_role=taxonomy_role,
            taxonomy_memory_authority=taxonomy_memory_authority,
        )
        for index, text in enumerate(candidate_texts, start=1)
        if text.strip()
    ]

    persisted_candidates = staged_candidates
    if not dry_run:
        persisted_candidates = [submit_staged_candidate(base_dir, candidate) for candidate in staged_candidates]

    return IngestionPipelineResult(
        source_path=str(resolved_source),
        detected_format=_resolve_local_file_format(resolved_source),
        staged_candidates=persisted_candidates,
        dry_run=dry_run,
    )


def ingest_operator_note(
    base_dir: Path,
    text: str,
    *,
    topic: str = "",
    dry_run: bool = False,
    submitted_by: str = "swl_note",
    taxonomy_role: str = DEFAULT_INGESTION_TAXONOMY_ROLE,
    taxonomy_memory_authority: str = DEFAULT_INGESTION_TAXONOMY_MEMORY_AUTHORITY,
) -> IngestionPipelineResult:
    normalized_text = text.strip()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    source_task_id = f"note-{timestamp}"
    candidate = StagedCandidate(
        candidate_id="",
        text=normalized_text,
        source_task_id=source_task_id,
        topic=topic,
        source_kind=OPERATOR_NOTE_SOURCE_KIND,
        source_ref="note://operator",
        source_object_id=f"note-{uuid4().hex[:12]}",
        submitted_by=submitted_by,
        taxonomy_role=taxonomy_role,
        taxonomy_memory_authority=taxonomy_memory_authority,
    )

    persisted_candidate = candidate if dry_run else submit_staged_candidate(base_dir, candidate)
    return IngestionPipelineResult(
        source_path="note://operator",
        detected_format="operator_note",
        staged_candidates=[persisted_candidate],
        dry_run=dry_run,
    )


def build_staged_candidates(
    fragments: list[ExtractedFragment],
    *,
    source_ref: str,
    source_task_id: str,
    submitted_by: str,
    taxonomy_role: str,
    taxonomy_memory_authority: str,
) -> list[StagedCandidate]:
    candidates: list[StagedCandidate] = []
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


def parse_local_file(source_path: Path) -> list[str]:
    text = source_path.read_text(encoding="utf-8", errors="replace")
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []
    if source_path.suffix.lower() in {".md", ".markdown"}:
        sections = _split_local_markdown(normalized)
        return sections or [normalized]
    return [normalized]


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


def _resolve_detected_format(source_name: str, format_hint: str | None, source_bytes: bytes | None) -> str:
    normalized_hint = normalize_ingestion_format_hint(format_hint)
    if normalized_hint:
        return normalized_hint
    if source_name.lower().endswith((".md", ".markdown")):
        return "markdown"
    if source_bytes is not None:
        try:
            text = source_bytes.decode("utf-8")
            stripped = text.lstrip()
            if stripped and not stripped.startswith(("{", "[")):
                has_heading = any(LOCAL_MARKDOWN_HEADING_PATTERN.match(line.strip()) for line in text.splitlines())
                if has_heading:
                    return "markdown"
            payload = json.loads(text)
            return detect_ingestion_format(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError):
            return "auto"
    return "auto"


def _resolve_local_file_format(source_path: Path) -> str:
    if source_path.suffix.lower() in {".md", ".markdown"}:
        return "local_markdown"
    return "local_text"


def _split_local_markdown(text: str) -> list[str]:
    lines = text.split("\n")
    headings: list[tuple[str, int]] = []
    for index, line in enumerate(lines):
        match = LOCAL_MARKDOWN_HEADING_PATTERN.match(line.strip())
        if match:
            headings.append((match.group(2).strip(), index))

    if not headings:
        return []

    sections: list[str] = []
    for current_index, (heading, line_index) in enumerate(headings):
        next_line_index = headings[current_index + 1][1] if current_index + 1 < len(headings) else len(lines)
        body = "\n".join(lines[line_index + 1 : next_line_index]).strip()
        section = f"{heading}\n\n{body}".strip() if body else heading
        if section:
            sections.append(section)
    return sections
