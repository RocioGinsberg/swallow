from __future__ import annotations

from .models import TaskCard, TaskState


def plan(state: TaskState) -> list[TaskCard]:
    """Build Runtime v0 task cards from the current task state.

    Phase 31 keeps planning intentionally static: one task state maps to one task
    card so the later executor/review integration can adopt a stable interface
    without changing orchestration semantics.
    """

    constraints = state.task_semantics.get("constraints", []) if state.task_semantics else []
    card = TaskCard(
        goal=state.goal,
        input_context={
            "title": state.title,
            "workspace_root": state.workspace_root,
            "task_semantics": dict(state.task_semantics),
        },
        input_schema={},
        output_schema={},
        route_hint=state.route_name,
        executor_type=state.route_executor_family,
        constraints=list(constraints),
        parent_task_id=state.task_id,
    )
    return [card]
