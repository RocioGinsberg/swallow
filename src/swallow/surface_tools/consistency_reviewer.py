from __future__ import annotations

import asyncio
import json
from pathlib import Path

from swallow.surface_tools.consistency_audit import run_consistency_audit
from swallow.orchestration.models import ExecutorResult, TaskCard, TaskState


CONSISTENCY_REVIEWER_EXECUTOR_NAME = "consistency-reviewer"
CONSISTENCY_REVIEWER_SYSTEM_ROLE = "validator"
CONSISTENCY_REVIEWER_MEMORY_AUTHORITY = "stateless"


class ConsistencyReviewerAgent:
    agent_name = CONSISTENCY_REVIEWER_EXECUTOR_NAME
    system_role = CONSISTENCY_REVIEWER_SYSTEM_ROLE
    memory_authority = CONSISTENCY_REVIEWER_MEMORY_AUTHORITY

    def _resolve_task_id(self, state: TaskState, card: TaskCard) -> str:
        task_id = str(card.input_context.get("task_id", "")).strip() or state.task_id
        if not task_id:
            raise ValueError("ConsistencyReviewerAgent requires task_id from state or input_context.")
        return task_id

    def _resolve_auditor_route(self, card: TaskCard) -> str:
        auditor_route = str(card.input_context.get("auditor_route", "")).strip()
        if not auditor_route:
            raise ValueError("ConsistencyReviewerAgent input_context.auditor_route is required.")
        return auditor_route

    def _build_prompt(
        self,
        state: TaskState,
        card: TaskCard,
        *,
        task_id: str,
        auditor_route: str,
        sample_artifact_path: str,
    ) -> str:
        return "\n".join(
            [
                "# Consistency Reviewer Task",
                "",
                f"- task_id: {task_id}",
                f"- agent_name: {self.agent_name}",
                f"- executor_role: {self.system_role}",
                f"- memory_authority: {self.memory_authority}",
                f"- auditor_route: {auditor_route}",
                f"- sample_artifact_path: {sample_artifact_path}",
                f"- goal: {card.goal or state.goal}",
                "- workflow: run a read-only consistency audit over an existing artifact and summarize the verdict",
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

        task_id = self._resolve_task_id(state, card)
        auditor_route = self._resolve_auditor_route(card)
        sample_artifact_path = str(card.input_context.get("sample_artifact_path", "executor_output.md")).strip()
        prompt = self._build_prompt(
            state,
            card,
            task_id=task_id,
            auditor_route=auditor_route,
            sample_artifact_path=sample_artifact_path or "executor_output.md",
        )
        result = run_consistency_audit(
            base_dir,
            task_id,
            auditor_route=auditor_route,
            sample_artifact_path=sample_artifact_path or "executor_output.md",
        )
        return ExecutorResult(
            executor_name=self.agent_name,
            status=result.status,
            message=result.message,
            output=json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n",
            prompt=prompt,
            dialect="plain_text",
            side_effects={
                "kind": "consistency_audit",
                "audit_artifact": result.audit_artifact,
                "verdict": result.verdict,
                "auditor_route": result.auditor_route,
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


class ConsistencyReviewerExecutor(ConsistencyReviewerAgent):
    """Compatibility wrapper that preserves executor semantics while delegating to ConsistencyReviewerAgent."""
