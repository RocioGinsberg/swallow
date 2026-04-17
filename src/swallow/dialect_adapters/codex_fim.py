from __future__ import annotations

from ..models import DialectSpec, RetrievalItem, TaskState


class CodexFIMDialect:
    spec = DialectSpec(
        name="codex_fim",
        description="FIM-style prompt layout for code-oriented executor routes.",
        supported_model_hints=["codex", "deepseek-coder"],
    )

    def format_prompt(self, raw_prompt: str, state: TaskState, retrieval_items: list[RetrievalItem]) -> str:
        execution_kind = str((state.route_capabilities or {}).get("execution_kind", "")).strip().lower()
        if execution_kind != "code_execution":
            return raw_prompt

        retrieval_lines = [
            f"- [{item.source_type}] {item.reference()} title={item.display_title()}: {item.preview}"
            for item in retrieval_items
        ] or ["- No retrieval matches were found."]

        prefix_lines = [
            "# Swallow Codex FIM Task",
            "",
            f"Task ID: {state.task_id}",
            f"Title: {state.title}",
            f"Goal: {state.goal}",
            f"Route: {state.route_name}",
            f"Model Hint: {state.route_model_hint}",
            "",
            "Retrieved Context:",
            *retrieval_lines,
            "",
            "Raw Executor Prompt:",
            raw_prompt.strip(),
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
