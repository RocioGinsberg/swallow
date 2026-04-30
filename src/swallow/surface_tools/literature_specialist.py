from __future__ import annotations

import asyncio
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from swallow.provider_router.agent_llm import AgentLLMUnavailable, call_agent_llm, extract_json_object
from swallow.knowledge_retrieval.knowledge_relations import KNOWLEDGE_RELATION_TYPES
from swallow.orchestration.models import ExecutorResult, RetrievalItem, TaskCard, TaskState
from swallow.surface_tools.workspace import resolve_path


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
        return resolve_path(raw_path, base=base_dir)

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

    def _system_prompt(self) -> str:
        return (
            "You are the Swallow Literature Specialist. Return strict JSON only. "
            "Summarize the provided documents, extract key concepts, and suggest up to 5 high-value knowledge relations."
        )

    def _normalize_alias(self, value: str) -> str:
        return str(value or "").strip()

    def _build_object_alias_map(self, retrieval_items: list[object]) -> dict[str, str]:
        unique_aliases: dict[str, str] = {}
        ambiguous_aliases: set[str] = set()

        for item in retrieval_items:
            if isinstance(item, RetrievalItem):
                metadata = item.metadata if isinstance(item.metadata, dict) else {}
                aliases = {item.chunk_id, item.title, item.path, Path(item.path).name}
            elif isinstance(item, dict):
                metadata = item.get("metadata", {})
                aliases = {
                    str(item.get("chunk_id", "")).strip(),
                    str(item.get("title", "")).strip(),
                    str(item.get("path", "")).strip(),
                    Path(str(item.get("path", "")).strip()).name,
                }
            else:
                continue

            if not isinstance(metadata, dict):
                metadata = {}
            object_id = str(metadata.get("knowledge_object_id", "")).strip()
            canonical_id = str(metadata.get("canonical_id", "")).strip()
            source_ref = str(metadata.get("source_ref", "")).strip()
            if not object_id:
                continue

            aliases.add(object_id)
            aliases.add(canonical_id)
            aliases.add(source_ref)
            if source_ref:
                parsed = urlparse(source_ref)
                source_path = parsed.path or source_ref
                aliases.add(Path(source_path).name)

            for raw_alias in aliases:
                alias = self._normalize_alias(raw_alias)
                if not alias or alias == object_id or alias in ambiguous_aliases:
                    continue
                existing = unique_aliases.get(alias)
                if existing and existing != object_id:
                    ambiguous_aliases.add(alias)
                    unique_aliases.pop(alias, None)
                    continue
                unique_aliases[alias] = object_id

        return unique_aliases

    def _build_llm_prompt(
        self,
        state: TaskState,
        card: TaskCard,
        analyses: list[_DocumentAnalysis],
        *,
        object_aliases: dict[str, str],
    ) -> str:
        lines = [
            "# Literature Specialist LLM Task",
            "",
            f"task_id: {state.task_id}",
            f"goal: {card.goal or state.goal}",
            "Return JSON with keys: summary, key_concepts, relation_suggestions.",
            "relation_suggestions must be a list of objects with: source_object_id, target_object_id, relation_type, confidence, context.",
            "source_object_id and target_object_id must use the exact knowledge object ids listed below when available.",
            f"Allowed relation_type values: {', '.join(KNOWLEDGE_RELATION_TYPES)}",
            "",
        ]
        if object_aliases:
            lines.extend(["## Available Knowledge Objects"])
            for alias, object_id in sorted(object_aliases.items()):
                if alias == object_id:
                    continue
                lines.append(f"- alias: {alias} -> object_id: {object_id}")
            lines.append("")
        lines.extend(
            [
            "## Documents",
            ]
        )
        for item in analyses:
            if not item.exists:
                lines.append(f"- path: {item.path} (missing)")
                continue
            headings = ", ".join(item.headings[:6]) if item.headings else "(none)"
            terms = ", ".join(item.key_terms[:8]) if item.key_terms else "(none)"
            lines.extend(
                [
                    f"- path: {item.path}",
                    f"  headings: {headings}",
                    f"  key_terms: {terms}",
                    f"  preview: {item.preview or '(empty)'}",
                ]
            )
        return "\n".join(lines)

    def _normalize_relation_suggestions(
        self,
        raw_suggestions: object,
        *,
        object_aliases: dict[str, str] | None = None,
    ) -> list[dict[str, object]]:
        if not isinstance(raw_suggestions, list):
            return []
        alias_map = object_aliases or {}
        normalized: list[dict[str, object]] = []
        for item in raw_suggestions[:5]:
            if not isinstance(item, dict):
                continue
            source_object_id = str(item.get("source_object_id", "")).strip()
            target_object_id = str(item.get("target_object_id", "")).strip()
            source_object_id = alias_map.get(source_object_id, source_object_id)
            target_object_id = alias_map.get(target_object_id, target_object_id)
            relation_type = str(item.get("relation_type", "")).strip()
            context = str(item.get("context", "")).strip()
            if not source_object_id or not target_object_id or source_object_id == target_object_id:
                continue
            if relation_type not in KNOWLEDGE_RELATION_TYPES:
                continue
            try:
                confidence = float(item.get("confidence", 0.0) or 0.0)
            except (TypeError, ValueError):
                confidence = 0.0
            normalized.append(
                {
                    "source_object_id": source_object_id,
                    "target_object_id": target_object_id,
                    "relation_type": relation_type,
                    "confidence": max(confidence, 0.0),
                    "context": context,
                }
            )
        return normalized

    def _build_llm_report(
        self,
        analyses: list[_DocumentAnalysis],
        *,
        goal: str,
        summary: str,
        key_concepts: list[str],
        relation_suggestions: list[dict[str, object]],
    ) -> str:
        available = [item for item in analyses if item.exists]
        lines = [
            "# Literature Analysis",
            "",
            "- analysis_method: llm",
            f"- goal: {goal or '(none)'}",
            f"- analyzed_documents: {len(available)}",
            f"- missing_documents: {len(analyses) - len(available)}",
            "",
            "## LLM Summary",
            summary or "(empty)",
            "",
            "## Key Concepts",
        ]
        if key_concepts:
            lines.extend(f"- {item}" for item in key_concepts)
        else:
            lines.append("- (none)")
        lines.extend(["", "## Relation Suggestions"])
        if relation_suggestions:
            for item in relation_suggestions:
                lines.append(
                    "- "
                    f"{item['source_object_id']} -> {item['target_object_id']} "
                    f"[{item['relation_type']}, confidence={item['confidence']}] "
                    f"{item['context'] or ''}".rstrip()
                )
        else:
            lines.append("- (none)")
        return "\n".join(lines) + "\n"

    def execute(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[object],
    ) -> ExecutorResult:
        document_paths = self._resolve_document_paths(card)
        prompt = self._build_prompt(state, card, document_paths=document_paths)
        analyses = [self._analyze_document(base_dir, path) for path in document_paths]
        object_aliases = self._build_object_alias_map(retrieval_items)
        analyzed_count = sum(1 for item in analyses if item.exists)
        if analyzed_count == 0:
            status = "failed"
            message = "LiteratureSpecialistAgent could not analyze any existing documents."
            output = self._build_report(analyses, goal=card.goal or state.goal)
            analysis_method = "heuristic"
            llm_usage: dict[str, object] = {}
            relation_suggestions: list[dict[str, object]] = []
        else:
            try:
                llm_response = call_agent_llm(
                    self._build_llm_prompt(state, card, analyses, object_aliases=object_aliases),
                    system=self._system_prompt(),
                )
                payload = extract_json_object(llm_response.content)
                key_concepts = payload.get("key_concepts", [])
                if not isinstance(key_concepts, list):
                    key_concepts = []
                relation_suggestions = self._normalize_relation_suggestions(
                    payload.get("relation_suggestions", []),
                    object_aliases=object_aliases,
                )
                output = self._build_llm_report(
                    analyses,
                    goal=card.goal or state.goal,
                    summary=str(payload.get("summary", "")).strip(),
                    key_concepts=[str(item).strip() for item in key_concepts if str(item).strip()][:10],
                    relation_suggestions=relation_suggestions,
                )
                status = "completed"
                message = f"LiteratureSpecialistAgent analyzed {analyzed_count} document(s) with LLM enhancement."
                analysis_method = "llm"
                llm_usage = {
                    "input_tokens": llm_response.input_tokens,
                    "output_tokens": llm_response.output_tokens,
                    "model": llm_response.model,
                }
            except (AgentLLMUnavailable, ValueError):
                output = self._build_report(analyses, goal=card.goal or state.goal)
                status = "completed"
                message = f"LiteratureSpecialistAgent analyzed {analyzed_count} document(s)."
                analysis_method = "heuristic"
                llm_usage = {}
                relation_suggestions = []
        return ExecutorResult(
            executor_name=self.agent_name,
            status=status,
            message=message,
            output=output,
            prompt=prompt,
            dialect="plain_text",
            estimated_input_tokens=int(llm_usage.get("input_tokens", 0) or 0),
            estimated_output_tokens=int(llm_usage.get("output_tokens", 0) or 0),
            side_effects={
                "kind": "literature_analysis",
                "analysis_method": analysis_method,
                "analyzed_document_count": analyzed_count,
                "missing_document_count": len(analyses) - analyzed_count,
                "relation_suggestions": relation_suggestions,
                "llm_usage": llm_usage,
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
