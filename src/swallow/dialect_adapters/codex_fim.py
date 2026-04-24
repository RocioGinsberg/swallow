from __future__ import annotations

from ..dialect_data import collect_prompt_data
from ..models import DialectSpec, RetrievalItem, TaskState


def _escape_fim_markers(value: str) -> str:
    return value.replace("<fim_prefix>", "[fim_prefix]").replace("<fim_suffix>", "[fim_suffix]")


class FIMDialect:
    spec = DialectSpec(
        name="codex_fim",
        description="FIM-style prompt layout for code-oriented executor routes.",
        supported_model_hints=["codex", "deepseek", "deepseek-coder"],
    )

    def format_prompt(self, raw_prompt: str, state: TaskState, retrieval_items: list[RetrievalItem]) -> str:
        prompt_data = collect_prompt_data(state, retrieval_items)
        execution_kind = str((state.route_capabilities or {}).get("execution_kind", "")).strip().lower()
        if execution_kind != "code_execution":
            return raw_prompt

        retrieval_lines = [f"- {entry}" for entry in prompt_data.retrieval_entries] or ["- No retrieval matches were found."]

        prefix_lines = [
            "# Swallow FIM Task",
            "",
            f"Task ID: {_escape_fim_markers(prompt_data.task.task_id)}",
            f"Title: {_escape_fim_markers(prompt_data.task.title)}",
            f"Goal: {_escape_fim_markers(prompt_data.task.goal)}",
            f"Route: {prompt_data.route.route_name}",
            f"Model Hint: {prompt_data.route.route_model_hint}",
            "",
            "Retrieved Context:",
            *retrieval_lines,
            "",
            "Raw Executor Prompt:",
            _escape_fim_markers(raw_prompt.strip()),
        ]
        suffix_lines = [
            "Return a concise execution update with:",
            "1. what you would do next,",
            "2. the main risks or gaps,",
            "3. the first concrete implementation action.",
            "Do not assume hidden context outside the provided task and retrieved sources.",
        ]
        return "\n".join(
            [
                "<fim_prefix>",
                *prefix_lines,
                "<fim_suffix>",
                *suffix_lines,
            ]
        )


# Backward-compatible alias for existing imports and historical references.
CodexFIMDialect = FIMDialect
