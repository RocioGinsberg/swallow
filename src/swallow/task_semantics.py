from __future__ import annotations

from .models import TaskSemantics

ALLOWED_RETRIEVAL_SOURCE_TYPES = ("repo", "notes", "knowledge", "artifacts")


def normalize_retrieval_source_types(source_types: list[str] | tuple[str, ...] | None) -> list[str] | None:
    if source_types is None:
        return None
    if not isinstance(source_types, (list, tuple)):
        raise ValueError("retrieval_source_types must be a list of supported source type strings")

    normalized_items: list[str] = []
    seen: set[str] = set()
    for item in source_types:
        normalized = str(item).strip().lower()
        if not normalized:
            continue
        if normalized not in ALLOWED_RETRIEVAL_SOURCE_TYPES:
            raise ValueError(
                "Invalid retrieval source type: "
                f"{item}. Expected one of: {', '.join(ALLOWED_RETRIEVAL_SOURCE_TYPES)}"
            )
        if normalized in seen:
            continue
        seen.add(normalized)
        normalized_items.append(normalized)
    if not normalized_items:
        raise ValueError("retrieval_source_types must include at least one supported source type")
    return normalized_items


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
    retrieval_source_types: list[str] | tuple[str, ...] | None = None,
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
        retrieval_source_types=normalize_retrieval_source_types(retrieval_source_types),
    )
