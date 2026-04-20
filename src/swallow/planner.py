from __future__ import annotations

from .knowledge_objects import canonicalization_status_for
from .models import TaskCard, TaskState, build_librarian_taxonomy_profile


LIBRARIAN_BLOCKED_AUTHORITIES = {"canonical-write-forbidden", "staged-knowledge"}
MAX_SUBTASK_CARDS = 4


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


def _normalized_constraints(state: TaskState) -> list[str]:
    raw_constraints = state.task_semantics.get("constraints", []) if state.task_semantics else []
    return [str(item).strip() for item in raw_constraints if str(item).strip()]


def _next_action_proposals(state: TaskState) -> list[str]:
    semantics = state.task_semantics if state.task_semantics else {}
    raw_actions = semantics.get("next_action_proposals", [])
    proposals: list[str] = []
    seen: set[str] = set()
    for item in raw_actions:
        normalized = str(item).strip()
        if not normalized or normalized in seen:
            continue
        proposals.append(normalized)
        seen.add(normalized)
        if len(proposals) >= MAX_SUBTASK_CARDS:
            break
    return proposals


def _reviewer_routes(state: TaskState) -> list[str]:
    semantics = state.task_semantics if state.task_semantics else {}
    raw_routes = semantics.get("reviewer_routes", [])
    if not isinstance(raw_routes, list):
        return []

    routes: list[str] = []
    seen: set[str] = set()
    for item in raw_routes:
        normalized = str(item).strip()
        if not normalized or normalized in seen:
            continue
        routes.append(normalized)
        seen.add(normalized)
    return routes


def _consensus_policy(state: TaskState) -> str:
    semantics = state.task_semantics if state.task_semantics else {}
    raw_policy = str(semantics.get("consensus_policy", "majority")).strip().lower()
    return raw_policy if raw_policy in {"majority", "veto"} else "majority"


def _token_cost_limit(state: TaskState) -> float:
    semantics = state.task_semantics if state.task_semantics else {}
    raw_limit = semantics.get("token_cost_limit", 0.0)
    try:
        parsed = float(raw_limit)
    except (TypeError, ValueError):
        return 0.0
    return parsed if parsed > 0 else 0.0


def _parallel_subtasks_requested(constraints: list[str]) -> bool:
    for item in constraints:
        normalized = item.lower()
        if "parallel_subtasks" in normalized or "parallel subtasks" in normalized:
            return True
    return False


def _build_subtask_cards(
    state: TaskState,
    *,
    constraints: list[str],
    input_context: dict[str, object],
    next_actions: list[str],
    parallel_requested: bool,
) -> list[TaskCard]:
    cards: list[TaskCard] = []
    reviewer_routes = _reviewer_routes(state)
    consensus_policy = _consensus_policy(state)
    token_cost_limit = _token_cost_limit(state)
    for index, action in enumerate(next_actions, start=1):
        depends_on = [] if parallel_requested or index == 1 else [cards[-1].card_id]
        cards.append(
            TaskCard(
                goal=action,
                input_context={
                    **input_context,
                    "parent_goal": state.goal,
                    "subtask_goal": action,
                    "planning_mode": "parallel" if parallel_requested else "sequential",
                },
                input_schema={},
                output_schema={},
                route_hint=state.route_name,
                executor_type=state.route_executor_family,
                reviewer_routes=list(reviewer_routes),
                consensus_policy=consensus_policy,
                token_cost_limit=token_cost_limit,
                constraints=list(constraints),
                depends_on=depends_on,
                subtask_index=index,
                parent_task_id=state.task_id,
            )
        )
    return cards


def plan(state: TaskState) -> list[TaskCard]:
    """Build Runtime v0 task cards from the current task state.

    Phase 33 keeps planning rule-driven but extends the Runtime v0 baseline with
    a bounded 1:N split. Librarian promotion still wins over generic subtask
    decomposition so knowledge writeback remains explicitly gated.
    """

    constraints = _normalized_constraints(state)
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
            depends_on=[],
            subtask_index=1,
            parent_task_id=state.task_id,
        )
        return [card]

    next_actions = _next_action_proposals(state)
    reviewer_routes = _reviewer_routes(state)
    consensus_policy = _consensus_policy(state)
    token_cost_limit = _token_cost_limit(state)
    if len(next_actions) > 1:
        parallel_requested = _parallel_subtasks_requested(constraints)
        return _build_subtask_cards(
            state,
            constraints=constraints,
            input_context=input_context,
            next_actions=next_actions,
            parallel_requested=parallel_requested,
        )

    card = TaskCard(
        goal=state.goal,
        input_context=input_context,
        input_schema={},
        output_schema={},
        route_hint=state.route_name,
        executor_type=state.route_executor_family,
        reviewer_routes=reviewer_routes,
        consensus_policy=consensus_policy,
        token_cost_limit=token_cost_limit,
        constraints=list(constraints),
        depends_on=[],
        subtask_index=1,
        parent_task_id=state.task_id,
    )
    return [card]
