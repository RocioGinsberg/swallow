from __future__ import annotations

import asyncio
from pathlib import Path

from .models import ExecutorResult, RetrievalItem, TaskCard, TaskState
from .validator import build_validation_report, validate_run_outputs


VALIDATOR_EXECUTOR_NAME = "validator"
VALIDATOR_SYSTEM_ROLE = "validator"
VALIDATOR_MEMORY_AUTHORITY = "stateless"


class ValidatorAgent:
    agent_name = VALIDATOR_EXECUTOR_NAME
    system_role = VALIDATOR_SYSTEM_ROLE
    memory_authority = VALIDATOR_MEMORY_AUTHORITY

    def _resolve_artifact_paths(self, state: TaskState, card: TaskCard) -> dict[str, str]:
        raw_artifact_paths = card.input_context.get("artifact_paths")
        if raw_artifact_paths is None:
            return dict(state.artifact_paths)
        if not isinstance(raw_artifact_paths, dict):
            raise ValueError("ValidatorAgent input_context.artifact_paths must be a mapping when provided.")
        return {str(key): str(value) for key, value in raw_artifact_paths.items()}

    def _resolve_executor_result(self, state: TaskState, card: TaskCard, artifact_paths: dict[str, str]) -> ExecutorResult:
        raw_executor_result = card.input_context.get("executor_result")
        if isinstance(raw_executor_result, ExecutorResult):
            return raw_executor_result
        if isinstance(raw_executor_result, dict):
            return ExecutorResult(
                executor_name=str(raw_executor_result.get("executor_name", state.executor_name)).strip() or state.executor_name,
                status=str(raw_executor_result.get("status", "completed")).strip() or "completed",
                message=str(raw_executor_result.get("message", "ValidatorAgent reconstructed executor result.")).strip()
                or "ValidatorAgent reconstructed executor result.",
                output=str(raw_executor_result.get("output", "") or ""),
                failure_kind=str(raw_executor_result.get("failure_kind", "") or ""),
            )

        output_path = Path(artifact_paths.get("executor_output", ""))
        output_text = ""
        if output_path.is_file():
            output_text = output_path.read_text(encoding="utf-8", errors="replace")
        return ExecutorResult(
            executor_name=str(card.input_context.get("executor_name", state.executor_name)).strip() or state.executor_name,
            status=str(card.input_context.get("executor_status", "completed")).strip() or "completed",
            message="ValidatorAgent reconstructed executor result from artifact paths.",
            output=output_text,
            failure_kind=str(card.input_context.get("failure_kind", "") or ""),
        )

    def _build_prompt(self, state: TaskState, card: TaskCard, *, artifact_paths: dict[str, str]) -> str:
        return "\n".join(
            [
                "# Validator Task",
                "",
                f"- task_id: {state.task_id}",
                f"- agent_name: {self.agent_name}",
                f"- executor_role: {self.system_role}",
                f"- memory_authority: {self.memory_authority}",
                f"- artifact_count: {len(artifact_paths)}",
                f"- goal: {card.goal or state.goal}",
                "- workflow: inspect task-level artifacts and executor output consistency without mutating task state",
            ]
        )

    def execute(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[RetrievalItem],
    ) -> ExecutorResult:
        del base_dir

        artifact_paths = self._resolve_artifact_paths(state, card)
        executor_result = self._resolve_executor_result(state, card, artifact_paths)
        prompt = self._build_prompt(state, card, artifact_paths=artifact_paths)
        validation_result = validate_run_outputs(state, retrieval_items, executor_result, artifact_paths)
        return ExecutorResult(
            executor_name=self.agent_name,
            status="completed" if validation_result.status != "failed" else "failed",
            message=validation_result.message,
            output=build_validation_report(validation_result) + "\n",
            prompt=prompt,
            dialect="plain_text",
            side_effects={
                "kind": "validation_report",
                "validation_result": validation_result.to_dict(),
            },
        )

    async def execute_async(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[RetrievalItem],
    ) -> ExecutorResult:
        return await asyncio.to_thread(self.execute, base_dir, state, card, retrieval_items)


class ValidatorExecutor(ValidatorAgent):
    """Compatibility wrapper that preserves executor semantics while delegating to ValidatorAgent."""
