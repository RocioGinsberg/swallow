from __future__ import annotations

import asyncio
from pathlib import Path

from swallow.knowledge_retrieval.ingestion.pipeline import build_ingestion_report, build_ingestion_summary, run_ingestion_pipeline
from swallow.orchestration.models import ExecutorResult, TaskCard, TaskState


INGESTION_SPECIALIST_EXECUTOR_NAME = "ingestion-specialist"
INGESTION_SPECIALIST_SYSTEM_ROLE = "specialist"
INGESTION_SPECIALIST_MEMORY_AUTHORITY = "staged-knowledge"


class IngestionSpecialistAgent:
    agent_name = INGESTION_SPECIALIST_EXECUTOR_NAME
    system_role = INGESTION_SPECIALIST_SYSTEM_ROLE
    memory_authority = INGESTION_SPECIALIST_MEMORY_AUTHORITY

    def _resolve_source_path(self, card: TaskCard) -> Path:
        raw_source_path = str(card.input_context.get("source_path", "")).strip()
        if not raw_source_path:
            raise ValueError("IngestionSpecialistAgent input_context.source_path is required.")
        return Path(raw_source_path)

    def _build_prompt(self, state: TaskState, card: TaskCard, *, source_path: Path, format_hint: str) -> str:
        return "\n".join(
            [
                "# Ingestion Specialist Task",
                "",
                f"- task_id: {state.task_id}",
                f"- agent_name: {self.agent_name}",
                f"- executor_role: {self.system_role}",
                f"- memory_authority: {self.memory_authority}",
                f"- source_path: {source_path}",
                f"- format_hint: {format_hint or 'auto'}",
                f"- goal: {card.goal or state.goal}",
                "- workflow: parse external session input, filter useful fragments, and persist staged knowledge candidates",
            ]
        )

    def execute(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[object],
    ) -> ExecutorResult:
        del retrieval_items

        source_path = self._resolve_source_path(card)
        format_hint = str(card.input_context.get("format_hint", "")).strip()
        prompt = self._build_prompt(state, card, source_path=source_path, format_hint=format_hint)
        result = run_ingestion_pipeline(
            base_dir,
            source_path,
            format_hint=format_hint or None,
        )
        output = f"{build_ingestion_report(result)}\n\n{build_ingestion_summary(result)}\n"
        return ExecutorResult(
            executor_name=self.agent_name,
            status="completed",
            message=(
                f"IngestionSpecialistAgent staged {len(result.staged_candidates)} candidate(s) "
                f"from {result.source_path}."
            ),
            output=output,
            prompt=prompt,
            dialect="plain_text",
            side_effects={
                "kind": "ingestion_pipeline",
                "source_path": result.source_path,
                "detected_format": result.detected_format,
                "staged_candidate_count": len(result.staged_candidates),
                "fragment_count": len(result.fragments),
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


class IngestionSpecialistExecutor(IngestionSpecialistAgent):
    """Compatibility wrapper that preserves executor semantics while delegating to IngestionSpecialistAgent."""
