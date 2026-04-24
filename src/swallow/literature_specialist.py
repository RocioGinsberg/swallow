from __future__ import annotations

import asyncio
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .models import ExecutorResult, TaskCard, TaskState


LITERATURE_SPECIALIST_EXECUTOR_NAME = "literature-specialist"
LITERATURE_SPECIALIST_SYSTEM_ROLE = "specialist"
LITERATURE_SPECIALIST_MEMORY_AUTHORITY = "task-memory"

_HEADING_PATTERN = re.compile(r"^\s{0,3}#{1,6}\s+(?P<title>.+?)\s*$", re.MULTILINE)
_TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9_-]{2,}")
_STOP_WORDS = {
    "about",
    "after",
    "agent",
    "analysis",
    "artifact",
    "artifacts",
    "before",
    "between",
    "could",
    "document",
    "documents",
    "from",
    "into",
    "phase",
    "section",
    "sections",
    "should",
    "system",
    "task",
    "that",
    "their",
    "them",
    "there",
    "these",
    "this",
    "those",
    "through",
    "with",
}


@dataclass(slots=True)
class _DocumentAnalysis:
    path: Path
    exists: bool
    headings: list[str]
    key_terms: list[str]
    token_count: int
    preview: str


class LiteratureSpecialistAgent:
    agent_name = LITERATURE_SPECIALIST_EXECUTOR_NAME
    system_role = LITERATURE_SPECIALIST_SYSTEM_ROLE
    memory_authority = LITERATURE_SPECIALIST_MEMORY_AUTHORITY

    def _resolve_document_paths(self, card: TaskCard) -> list[Path]:
        raw_paths = card.input_context.get("document_paths")
        if not isinstance(raw_paths, list):
            raise ValueError("LiteratureSpecialistAgent input_context.document_paths must be a non-empty list.")
        resolved = [Path(str(item).strip()) for item in raw_paths if str(item).strip()]
        if not resolved:
            raise ValueError("LiteratureSpecialistAgent input_context.document_paths must be a non-empty list.")
        return resolved

    def _resolve_path(self, base_dir: Path, raw_path: Path) -> Path:
        if raw_path.is_absolute():
            return raw_path
        return (base_dir / raw_path).resolve()

    def _normalize_token(self, token: str) -> str:
        if token.isascii():
            return token.lower()
        return token

    def _extract_key_terms(self, text: str) -> list[str]:
        counter: Counter[str] = Counter()
        for token in _TOKEN_PATTERN.findall(text):
            normalized = self._normalize_token(token)
            if normalized in _STOP_WORDS:
                continue
            counter[normalized] += 1
        return [term for term, _count in counter.most_common(8)]

    def _analyze_document(self, base_dir: Path, raw_path: Path) -> _DocumentAnalysis:
        resolved = self._resolve_path(base_dir, raw_path)
        if not resolved.exists() or not resolved.is_file():
            return _DocumentAnalysis(
                path=resolved,
                exists=False,
                headings=[],
                key_terms=[],
                token_count=0,
                preview="",
            )

        text = resolved.read_text(encoding="utf-8", errors="replace")
        headings = [match.group("title").strip() for match in _HEADING_PATTERN.finditer(text) if match.group("title").strip()]
        key_terms = self._extract_key_terms(text)
        preview_lines = [line.strip() for line in text.splitlines() if line.strip()]
        preview = " ".join(preview_lines[:3])
        if len(preview) > 180:
            preview = preview[:177].rstrip() + "..."
        token_count = len(_TOKEN_PATTERN.findall(text))
        return _DocumentAnalysis(
            path=resolved,
            exists=True,
            headings=headings,
            key_terms=key_terms,
            token_count=token_count,
            preview=preview,
        )

    def _build_prompt(self, state: TaskState, card: TaskCard, *, document_paths: list[Path]) -> str:
        return "\n".join(
            [
                "# Literature Specialist Task",
                "",
                f"- task_id: {state.task_id}",
                f"- agent_name: {self.agent_name}",
                f"- executor_role: {self.system_role}",
                f"- memory_authority: {self.memory_authority}",
                f"- document_count: {len(document_paths)}",
                f"- goal: {card.goal or state.goal}",
                "- workflow: inspect local documents, summarize their structure, extract recurring terms, and compare overlap",
            ]
        )

    def _build_report(self, analyses: list[_DocumentAnalysis], *, goal: str) -> str:
        available = [item for item in analyses if item.exists]
        shared_headings = sorted(set.intersection(*(set(item.headings) for item in available))) if len(available) >= 2 else []
        shared_terms = sorted(set.intersection(*(set(item.key_terms) for item in available))) if len(available) >= 2 else []

        lines = [
            "# Literature Analysis",
            "",
            "- analysis_method: heuristic",
            f"- goal: {goal or '(none)'}",
            f"- analyzed_documents: {len(available)}",
            f"- missing_documents: {len(analyses) - len(available)}",
            "",
            "## Documents",
        ]
        for item in analyses:
            if item.exists:
                lines.append(
                    f"- {item.path.name}: {len(item.headings)} headings, {item.token_count} terms, preview={item.preview or '(empty)'}"
                )
            else:
                lines.append(f"- {item.path.name}: missing")

        lines.extend(["", "## Structure Summary"])
        for item in analyses:
            if not item.exists:
                continue
            summary = ", ".join(item.headings[:6]) if item.headings else "(no headings detected)"
            lines.append(f"- {item.path.name}: {summary}")

        lines.extend(["", "## Key Terms"])
        for item in analyses:
            if not item.exists:
                continue
            terms = ", ".join(item.key_terms) if item.key_terms else "(no recurring terms detected)"
            lines.append(f"- {item.path.name}: {terms}")

        lines.extend(
            [
                "",
                "## Cross-Document Overlap",
                f"- shared_headings: {', '.join(shared_headings) if shared_headings else '(none)'}",
                f"- shared_terms: {', '.join(shared_terms[:10]) if shared_terms else '(none)'}",
            ]
        )
        return "\n".join(lines) + "\n"

    def execute(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[object],
    ) -> ExecutorResult:
        del retrieval_items

        document_paths = self._resolve_document_paths(card)
        prompt = self._build_prompt(state, card, document_paths=document_paths)
        analyses = [self._analyze_document(base_dir, path) for path in document_paths]
        analyzed_count = sum(1 for item in analyses if item.exists)
        output = self._build_report(analyses, goal=card.goal or state.goal)
        if analyzed_count == 0:
            status = "failed"
            message = "LiteratureSpecialistAgent could not analyze any existing documents."
        else:
            status = "completed"
            message = f"LiteratureSpecialistAgent analyzed {analyzed_count} document(s)."
        return ExecutorResult(
            executor_name=self.agent_name,
            status=status,
            message=message,
            output=output,
            prompt=prompt,
            dialect="plain_text",
            side_effects={
                "kind": "literature_analysis",
                "analysis_method": "heuristic",
                "analyzed_document_count": analyzed_count,
                "missing_document_count": len(analyses) - analyzed_count,
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


class LiteratureSpecialistExecutor(LiteratureSpecialistAgent):
    """Compatibility wrapper that preserves executor semantics while delegating to LiteratureSpecialistAgent."""
