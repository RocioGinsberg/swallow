from __future__ import annotations

from .knowledge_objects import canonicalization_status_for
from .models import TaskCard, TaskState, build_librarian_taxonomy_profile


LIBRARIAN_BLOCKED_AUTHORITIES = {"canonical-write-forbidden", "staged-knowledge"}


def _base_input_context(state: TaskState) -> dict[str, object]:
    return {
        "title": state.title,
        "workspace_root": state.workspace_root,
        "task_semantics": dict(state.task_semantics),
    }


def _promotion_ready_object_ids(state: TaskState) -> list[str]:
    object_ids: list[str] = []
    for item in state.knowledge_objects or []:
        object_id = str(item.get("object_id", "")).strip()
        if object_id and canonicalization_status_for(item) == "promotion_ready":
            object_ids.append(object_id)
    return object_ids


def _should_plan_librarian_card(state: TaskState, promotion_ready_ids: list[str]) -> bool:
    if not promotion_ready_ids:
        return False
    if state.route_execution_site != "local":
        return False
    return state.route_taxonomy_memory_authority not in LIBRARIAN_BLOCKED_AUTHORITIES


def plan(state: TaskState) -> list[TaskCard]:
    """Build Runtime v0 task cards from the current task state.

    Phase 31 keeps planning intentionally static: one task state maps to one task
    card so the later executor/review integration can adopt a stable interface
    without changing orchestration semantics.
    """

    constraints = state.task_semantics.get("constraints", []) if state.task_semantics else []
    input_context = _base_input_context(state)
    promotion_ready_ids = _promotion_ready_object_ids(state)
    if _should_plan_librarian_card(state, promotion_ready_ids):
        librarian_taxonomy = build_librarian_taxonomy_profile()
        card = TaskCard(
            goal=state.goal,
            input_context={
                **input_context,
                "promotion_ready_object_ids": promotion_ready_ids,
                "librarian_taxonomy": librarian_taxonomy.to_dict(),
            },
            input_schema={"kind": "librarian_promotion_request_v0"},
            output_schema={
                "kind": "librarian_change_log_v0",
                "required": [
                    "kind",
                    "task_id",
                    "generated_at",
                    "candidate_count",
                    "promoted_count",
                    "skipped_count",
                    "entries",
                    "change_log_artifact",
                ],
                "const": {
                    "kind": "librarian_change_log_v0",
                },
            },
            route_hint="librarian-local",
            executor_type="librarian",
            constraints=list(constraints),
            parent_task_id=state.task_id,
        )
        return [card]

    card = TaskCard(
        goal=state.goal,
        input_context=input_context,
        input_schema={},
        output_schema={},
        route_hint=state.route_name,
        executor_type=state.route_executor_family,
        constraints=list(constraints),
        parent_task_id=state.task_id,
    )
    return [card]
