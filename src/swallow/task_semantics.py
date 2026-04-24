from __future__ import annotations

from .models import TaskSemantics


def build_task_semantics(
    *,
    title: str,
    goal: str,
    constraints: list[str] | None = None,
    acceptance_criteria: list[str] | None = None,
    priority_hints: list[str] | None = None,
    next_action_proposals: list[str] | None = None,
    planning_source: str | None = None,
    complexity_hint: str | None = None,
) -> TaskSemantics:
    return TaskSemantics(
        title=title,
        goal=goal,
        constraints=[item.strip() for item in (constraints or []) if item and item.strip()],
        acceptance_criteria=[item.strip() for item in (acceptance_criteria or []) if item and item.strip()],
        priority_hints=[item.strip() for item in (priority_hints or []) if item and item.strip()],
        next_action_proposals=[item.strip() for item in (next_action_proposals or []) if item and item.strip()],
        source_kind="external_planning_handoff" if planning_source else "operator_entry",
        source_ref=(planning_source or "").strip(),
        complexity_hint=str(complexity_hint or "").strip().lower(),
    )
