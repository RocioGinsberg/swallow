from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path

from swallow.provider_router.agent_llm import AgentLLMUnavailable, call_agent_llm, extract_json_object
from swallow.orchestration.models import ExecutorResult, TaskCard, TaskState
from swallow.application.infrastructure.workspace import resolve_path


QUALITY_REVIEWER_EXECUTOR_NAME = "quality-reviewer"
QUALITY_REVIEWER_SYSTEM_ROLE = "validator"
QUALITY_REVIEWER_MEMORY_AUTHORITY = "stateless"

_ACTIONABLE_KEYWORDS = ("action", "fix", "implement", "next step", "todo", "follow-up")
_HEADING_PATTERN = re.compile(r"^\s{0,3}#{1,6}\s+\S", re.MULTILINE)
_LIST_PATTERN = re.compile(r"^\s*[-*]\s+\S", re.MULTILINE)
_CODE_BLOCK_PATTERN = re.compile(r"```")


@dataclass(slots=True)
class _CriterionVerdict:
    name: str
    verdict: str
    detail: str


class QualityReviewerAgent:
    agent_name = QUALITY_REVIEWER_EXECUTOR_NAME
    system_role = QUALITY_REVIEWER_SYSTEM_ROLE
    memory_authority = QUALITY_REVIEWER_MEMORY_AUTHORITY

    def _resolve_artifact_path(self, base_dir: Path, card: TaskCard) -> Path:
        raw_ref = str(card.input_context.get("artifact_ref", "")).strip()
        if not raw_ref:
            raise ValueError("QualityReviewerAgent input_context.artifact_ref is required.")
        artifact_path = Path(raw_ref)
        if artifact_path.is_absolute():
            return artifact_path
        return resolve_path(artifact_path, base=base_dir)

    def _resolve_quality_criteria(self, card: TaskCard) -> list[str]:
        raw_criteria = card.input_context.get("quality_criteria")
        if raw_criteria is None:
            return ["non_empty", "has_structure", "has_actionable_content", "min_length"]
        if not isinstance(raw_criteria, list):
            raise ValueError("QualityReviewerAgent input_context.quality_criteria must be a list when provided.")
        criteria = [str(item).strip() for item in raw_criteria if str(item).strip()]
        return criteria or ["non_empty", "has_structure", "has_actionable_content", "min_length"]

    def _resolve_min_length(self, card: TaskCard) -> int:
        raw_min_length = card.input_context.get("min_length", 100)
        try:
            threshold = int(raw_min_length)
        except (TypeError, ValueError):
            threshold = 100
        return max(threshold, 1)

    def _build_prompt(self, state: TaskState, card: TaskCard, *, artifact_path: Path, criteria: list[str]) -> str:
        return "\n".join(
            [
                "# Quality Reviewer Task",
                "",
                f"- task_id: {state.task_id}",
                f"- agent_name: {self.agent_name}",
                f"- executor_role: {self.system_role}",
                f"- memory_authority: {self.memory_authority}",
                f"- artifact_ref: {artifact_path}",
                f"- criteria: {', '.join(criteria)}",
                f"- goal: {card.goal or state.goal}",
                "- workflow: inspect a single artifact and report rule-based quality verdicts without mutating task state",
            ]
        )

    def _evaluate_non_empty(self, text: str) -> _CriterionVerdict:
        if text.strip():
            return _CriterionVerdict("non_empty", "pass", f"artifact contains {len(text.strip())} characters")
        return _CriterionVerdict("non_empty", "fail", "artifact is empty")

    def _evaluate_has_structure(self, text: str) -> _CriterionVerdict:
        heading_count = len(_HEADING_PATTERN.findall(text))
        if heading_count > 0:
            return _CriterionVerdict("has_structure", "pass", f"{heading_count} markdown heading(s) detected")
        return _CriterionVerdict("has_structure", "warn", "no markdown headings detected")

    def _evaluate_has_actionable_content(self, text: str) -> _CriterionVerdict:
        normalized = text.lower()
        has_list = bool(_LIST_PATTERN.search(text))
        has_code = len(_CODE_BLOCK_PATTERN.findall(text)) >= 2
        has_keyword = any(keyword in normalized for keyword in _ACTIONABLE_KEYWORDS)
        if has_list or has_code or has_keyword:
            sources: list[str] = []
            if has_list:
                sources.append("list")
            if has_code:
                sources.append("code_block")
            if has_keyword:
                sources.append("action_keyword")
            return _CriterionVerdict("has_actionable_content", "pass", f"detected {', '.join(sources)}")
        return _CriterionVerdict("has_actionable_content", "warn", "no lists, code blocks, or action keywords detected")

    def _evaluate_min_length(self, text: str, *, min_length: int) -> _CriterionVerdict:
        actual = len(text.strip())
        if actual >= min_length:
            return _CriterionVerdict("min_length", "pass", f"{actual} characters >= threshold {min_length}")
        return _CriterionVerdict("min_length", "fail", f"{actual} characters < threshold {min_length}")

    def _evaluate_criteria(self, artifact_path: Path, criteria: list[str], *, min_length: int) -> tuple[str, list[_CriterionVerdict]]:
        if not artifact_path.exists() or not artifact_path.is_file():
            verdicts = [_CriterionVerdict("artifact_exists", "fail", f"artifact is missing: {artifact_path}")]
            return "fail", verdicts

        text = artifact_path.read_text(encoding="utf-8", errors="replace")
        verdicts: list[_CriterionVerdict] = []
        for criterion in criteria:
            if criterion == "non_empty":
                verdicts.append(self._evaluate_non_empty(text))
            elif criterion == "has_structure":
                verdicts.append(self._evaluate_has_structure(text))
            elif criterion == "has_actionable_content":
                verdicts.append(self._evaluate_has_actionable_content(text))
            elif criterion == "min_length":
                verdicts.append(self._evaluate_min_length(text, min_length=min_length))
            else:
                verdicts.append(_CriterionVerdict(criterion, "warn", "unknown criterion was ignored"))

        overall = "pass"
        if any(item.verdict == "fail" for item in verdicts):
            overall = "fail"
        elif any(item.verdict == "warn" for item in verdicts):
            overall = "warn"
        return overall, verdicts

    def _build_report(self, artifact_path: Path, overall_verdict: str, verdicts: list[_CriterionVerdict]) -> str:
        lines = [
            "# Quality Review",
            "",
            "- analysis_method: heuristic",
            f"- artifact: {artifact_path}",
            f"- overall_verdict: {overall_verdict}",
            "",
            "## Criteria",
        ]
        for item in verdicts:
            lines.append(f"- {item.name}: {item.verdict} - {item.detail}")
        return "\n".join(lines) + "\n"

    def _system_prompt(self) -> str:
        return (
            "You are the Swallow Quality Reviewer. Return strict JSON only. "
            "Evaluate artifact quality semantically and produce verdicts with short details."
        )

    def _build_llm_prompt(self, state: TaskState, card: TaskCard, *, artifact_path: Path, artifact_text: str) -> str:
        preview = artifact_text.strip()
        if len(preview) > 4000:
            preview = preview[:4000]
        return "\n".join(
            [
                "# Quality Reviewer LLM Task",
                "",
                f"task_id: {state.task_id}",
                f"goal: {card.goal or state.goal}",
                f"artifact: {artifact_path}",
                "Return JSON with one key: verdicts.",
                "verdicts must be a list of objects with: name, verdict, detail.",
                "Use verdict values pass, warn, or fail.",
                "Focus on semantic quality dimensions such as coherence, completeness, and actionability.",
                "",
                "## Artifact",
                preview or "(empty)",
            ]
        )

    def _combine_overall_verdict(self, verdicts: list[_CriterionVerdict]) -> str:
        overall = "pass"
        if any(item.verdict == "fail" for item in verdicts):
            overall = "fail"
        elif any(item.verdict == "warn" for item in verdicts):
            overall = "warn"
        return overall

    def _normalize_llm_verdicts(self, raw_verdicts: object) -> list[_CriterionVerdict]:
        if not isinstance(raw_verdicts, list):
            return []
        verdicts: list[_CriterionVerdict] = []
        for item in raw_verdicts:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            verdict = str(item.get("verdict", "")).strip().lower()
            detail = str(item.get("detail", "")).strip()
            if not name or verdict not in {"pass", "warn", "fail"}:
                continue
            verdicts.append(_CriterionVerdict(name=name, verdict=verdict, detail=detail or "semantic review"))
        return verdicts

    def _build_llm_report(self, artifact_path: Path, overall_verdict: str, verdicts: list[_CriterionVerdict]) -> str:
        lines = [
            "# Quality Review",
            "",
            "- analysis_method: llm",
            f"- artifact: {artifact_path}",
            f"- overall_verdict: {overall_verdict}",
            "",
            "## Criteria",
        ]
        for item in verdicts:
            lines.append(f"- {item.name}: {item.verdict} - {item.detail}")
        return "\n".join(lines) + "\n"

    def execute(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[object],
    ) -> ExecutorResult:
        del retrieval_items

        artifact_path = self._resolve_artifact_path(base_dir, card)
        criteria = self._resolve_quality_criteria(card)
        min_length = self._resolve_min_length(card)
        prompt = self._build_prompt(state, card, artifact_path=artifact_path, criteria=criteria)
        overall_verdict, verdicts = self._evaluate_criteria(artifact_path, criteria, min_length=min_length)
        analysis_method = "heuristic"
        llm_usage: dict[str, object] = {}
        output = self._build_report(artifact_path, overall_verdict, verdicts)
        if artifact_path.exists() and artifact_path.is_file():
            artifact_text = artifact_path.read_text(encoding="utf-8", errors="replace")
            try:
                llm_response = call_agent_llm(
                    self._build_llm_prompt(state, card, artifact_path=artifact_path, artifact_text=artifact_text),
                    system=self._system_prompt(),
                )
                payload = extract_json_object(llm_response.content)
                semantic_verdicts = self._normalize_llm_verdicts(payload.get("verdicts", []))
                if semantic_verdicts:
                    verdicts = [*verdicts, *semantic_verdicts]
                    overall_verdict = self._combine_overall_verdict(verdicts)
                    output = self._build_llm_report(artifact_path, overall_verdict, verdicts)
                    analysis_method = "llm"
                    llm_usage = {
                        "input_tokens": llm_response.input_tokens,
                        "output_tokens": llm_response.output_tokens,
                        "model": llm_response.model,
                    }
            except (AgentLLMUnavailable, ValueError):
                pass
        return ExecutorResult(
            executor_name=self.agent_name,
            status="completed" if overall_verdict != "fail" else "failed",
            message=f"QualityReviewerAgent marked the artifact as {overall_verdict}.",
            output=output,
            prompt=prompt,
            dialect="plain_text",
            estimated_input_tokens=int(llm_usage.get("input_tokens", 0) or 0),
            estimated_output_tokens=int(llm_usage.get("output_tokens", 0) or 0),
            side_effects={
                "kind": "quality_review",
                "analysis_method": analysis_method,
                "overall_verdict": overall_verdict,
                "criteria_count": len(verdicts),
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


class QualityReviewerExecutor(QualityReviewerAgent):
    """Compatibility wrapper that preserves executor semantics while delegating to QualityReviewerAgent."""
