from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from pathlib import Path
from time import perf_counter
from typing import Awaitable, Callable, TypeVar

from swallow.orchestration.executor import run_executor
from swallow.orchestration.models import (
    EVENT_EXECUTOR_COMPLETED,
    EVENT_EXECUTOR_FAILED,
    Event,
    ExecutorResult,
    RetrievalItem,
    TaskCard,
    TaskState,
    build_telemetry_fields,
)
from swallow.provider_router.cost_estimation import DEFAULT_COST_ESTIMATOR, CostEstimator
from swallow.truth_governance.store import append_event, write_artifact


DEBATE_MAX_ROUNDS = 3
ReviewGateResultT = TypeVar("ReviewGateResultT")
ReviewFeedbackT = TypeVar("ReviewFeedbackT")


@dataclass(frozen=True, slots=True)
class ExecutionAttemptMetadata:
    run_attempt_count: int
    current_attempt_number: int
    current_attempt_id: str
    current_attempt_owner_kind: str
    current_attempt_owner_ref: str
    current_attempt_ownership_status: str
    current_attempt_owner_assigned_at: str
    current_attempt_transfer_reason: str
    dispatch_requested_at: str
    dispatch_started_at: str
    execution_lifecycle: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReviewGateResultFields:
    status: str
    message: str
    checks: list[dict[str, object]]

    def to_kwargs(self) -> dict[str, object]:
        return asdict(self)


def run_execution(
    base_dir: Path,
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    *,
    cost_estimator: CostEstimator = DEFAULT_COST_ESTIMATOR,
    run_executor_fn: Callable[[TaskState, list[RetrievalItem]], ExecutorResult] = run_executor,
    persist_side_effects: Callable[[Path, str, dict[str, object]], None] | None = None,
) -> ExecutorResult:
    started_at = perf_counter()
    executor_result = run_executor_fn(state, retrieval_items)
    executor_result = replace(
        executor_result,
        latency_ms=max(int((perf_counter() - started_at) * 1000), 0),
    )
    prompt_body = executor_result.prompt
    token_cost = cost_estimator.estimate(
        state.route_model_hint,
        executor_result.estimated_input_tokens,
        executor_result.estimated_output_tokens,
    )
    prompt_with_dialect = f"dialect: {executor_result.dialect or state.route_dialect or 'plain_text'}\n\n{prompt_body}"
    write_artifact(base_dir, state.task_id, "executor_prompt.md", prompt_with_dialect)
    write_artifact(base_dir, state.task_id, "executor_output.md", executor_result.output or executor_result.message)
    write_artifact(base_dir, state.task_id, "executor_stdout.txt", executor_result.stdout)
    write_artifact(base_dir, state.task_id, "executor_stderr.txt", executor_result.stderr)
    if persist_side_effects is not None:
        persist_side_effects(base_dir, state.task_id, executor_result.side_effects)
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type=EVENT_EXECUTOR_COMPLETED if executor_result.status == "completed" else EVENT_EXECUTOR_FAILED,
            message=executor_result.message,
            payload={
                "status": executor_result.status,
                "executor_name": executor_result.executor_name,
                "route_mode": state.route_mode,
                "route_name": state.route_name,
                "route_backend": state.route_backend,
                "route_executor_family": state.route_executor_family,
                "route_execution_site": state.route_execution_site,
                "route_remote_capable": state.route_remote_capable,
                "route_transport_kind": state.route_transport_kind,
                "route_dialect": state.route_dialect,
                "route_capabilities": state.route_capabilities,
                "attempt_id": state.current_attempt_id,
                "attempt_number": state.current_attempt_number,
                "attempt_owner_kind": state.current_attempt_owner_kind,
                "attempt_owner_ref": state.current_attempt_owner_ref,
                "attempt_ownership_status": state.current_attempt_ownership_status,
                "attempt_owner_assigned_at": state.current_attempt_owner_assigned_at,
                "attempt_transfer_reason": state.current_attempt_transfer_reason,
                "topology_route_name": state.topology_route_name,
                "topology_executor_family": state.topology_executor_family,
                "topology_execution_site": state.topology_execution_site,
                "topology_transport_kind": state.topology_transport_kind,
                "topology_remote_capable_intent": state.topology_remote_capable_intent,
                "topology_dispatch_status": state.topology_dispatch_status,
                "execution_site_contract_kind": state.execution_site_contract_kind,
                "execution_site_boundary": state.execution_site_boundary,
                "execution_site_contract_status": state.execution_site_contract_status,
                "execution_site_handoff_required": state.execution_site_handoff_required,
                "execution_site_contract_reason": state.execution_site_contract_reason,
                "dispatch_requested_at": state.dispatch_requested_at,
                "dispatch_started_at": state.dispatch_started_at,
                "execution_lifecycle": state.execution_lifecycle,
                "dialect": executor_result.dialect or state.route_dialect,
                "failure_kind": executor_result.failure_kind,
                "review_feedback": executor_result.review_feedback,
                "degraded": executor_result.degraded or state.route_is_fallback,
                "original_route_name": executor_result.original_route_name,
                "fallback_route_name": executor_result.fallback_route_name,
                "output_written": [
                    "executor_prompt.md",
                    "executor_output.md",
                    "executor_stdout.txt",
                    "executor_stderr.txt",
                ],
            }
            | build_telemetry_fields(
                state,
                latency_ms=executor_result.latency_ms,
                degraded=executor_result.degraded or state.route_is_fallback,
                token_cost=token_cost,
                error_code=executor_result.failure_kind if executor_result.status == "failed" else "",
            ).to_dict(),
        ),
    )
    return executor_result


def build_next_execution_attempt_metadata(
    state: TaskState,
    *,
    owner_assigned_at: str,
    dispatch_requested_at: str,
) -> ExecutionAttemptMetadata:
    attempt_number = state.run_attempt_count + 1
    return ExecutionAttemptMetadata(
        run_attempt_count=attempt_number,
        current_attempt_number=attempt_number,
        current_attempt_id=f"attempt-{attempt_number:04d}",
        current_attempt_owner_kind="local_orchestrator",
        current_attempt_owner_ref="swl_cli",
        current_attempt_ownership_status="owned",
        current_attempt_owner_assigned_at=owner_assigned_at,
        current_attempt_transfer_reason="",
        dispatch_requested_at=dispatch_requested_at,
        dispatch_started_at="",
        execution_lifecycle="prepared",
    )


def build_budget_exhausted_executor_result(
    state: TaskState,
    *,
    current_token_cost: float,
    token_cost_limit: float,
) -> ExecutorResult:
    return ExecutorResult(
        executor_name=state.executor_name,
        status="failed",
        message=(
            "TaskCard token cost budget is exhausted; waiting for human intervention before continuing "
            f"(current={current_token_cost:.8f}, limit={token_cost_limit:.8f})."
        ),
        failure_kind="budget_exhausted",
        review_feedback=str(getattr(state, "review_feedback_ref", "") or "").strip(),
        output="",
        prompt="",
        dialect=state.route_dialect or "plain_text",
        stdout="",
        stderr="",
    )


def build_budget_exhausted_review_gate_fields(
    *,
    current_token_cost: float,
    token_cost_limit: float,
) -> ReviewGateResultFields:
    return ReviewGateResultFields(
        status="failed",
        message="TaskCard token cost budget is exhausted before execution can continue.",
        checks=[
            {
                "name": "token_cost_budget",
                "passed": False,
                "detail": (
                    f"current_token_cost={current_token_cost:.8f}; "
                    f"token_cost_limit={token_cost_limit:.8f}"
                ),
            }
        ],
    )


def budget_exhausted_event_type(*, subtask_index: int | None = None) -> str:
    return "task.budget_exhausted" if subtask_index is None else f"subtask.{subtask_index}.budget_exhausted"


def build_budget_exhausted_event_payload(
    card: TaskCard,
    *,
    retry_round: int,
    attempt_number: int,
    current_token_cost: float,
    token_cost_limit: float,
    subtask_index: int | None = None,
) -> dict[str, object]:
    return {
        "card_id": card.card_id,
        "goal": card.goal,
        "retry_round": retry_round,
        "attempt_number": attempt_number,
        "current_token_cost": current_token_cost,
        "token_cost_limit": token_cost_limit,
        "consensus_policy": card.consensus_policy,
        "reviewer_routes": card.reviewer_routes,
        "subtask_index": subtask_index or card.subtask_index,
    }


def build_debate_exhausted_executor_result(
    executor_result: ExecutorResult,
    *,
    review_feedback_ref: str,
) -> ExecutorResult:
    return replace(
        executor_result,
        status="failed",
        message="Debate loop exhausted the maximum review rounds; waiting for human intervention.",
        failure_kind="debate_circuit_breaker",
        review_feedback=review_feedback_ref,
    )


def debate_loop_core(
    *,
    run_attempt: Callable[[int], tuple[ExecutorResult, ReviewGateResultT]],
    clear_feedback_state: Callable[[], None],
    build_feedback: Callable[[ReviewGateResultT, ExecutorResult, int], ReviewFeedbackT | None],
    build_last_feedback: Callable[[ReviewGateResultT, ExecutorResult, int], ReviewFeedbackT],
    store_feedback: Callable[[ReviewFeedbackT], str],
    apply_feedback: Callable[[str, ReviewFeedbackT], None],
    record_round: Callable[[str, ReviewFeedbackT, ExecutorResult, ReviewGateResultT], None],
    persist_exhausted: Callable[[list[str], ReviewFeedbackT, ReviewGateResultT], str],
    record_exhausted: Callable[[list[str], str, ExecutorResult, ReviewGateResultT], None],
) -> tuple[ExecutorResult, ReviewGateResultT, bool]:
    feedback_refs: list[str] = []
    retry_round = 0
    clear_feedback_state()

    while True:
        executor_result, review_gate_result = run_attempt(retry_round)

        if getattr(review_gate_result, "status", "") == "passed":
            clear_feedback_state()
            return executor_result, review_gate_result, False
        if executor_result.status != "completed":
            clear_feedback_state()
            return executor_result, review_gate_result, False

        if retry_round >= DEBATE_MAX_ROUNDS:
            last_feedback = build_last_feedback(
                review_gate_result,
                executor_result,
                retry_round,
            )
            debate_exhausted_ref = persist_exhausted(feedback_refs, last_feedback, review_gate_result)
            record_exhausted(feedback_refs, debate_exhausted_ref, executor_result, review_gate_result)
            return executor_result, review_gate_result, True

        feedback = build_feedback(
            review_gate_result,
            executor_result,
            retry_round + 1,
        )
        if feedback is None:
            clear_feedback_state()
            return executor_result, review_gate_result, False

        feedback_ref = store_feedback(feedback)
        feedback_refs.append(feedback_ref)
        apply_feedback(feedback_ref, feedback)
        record_round(feedback_ref, feedback, executor_result, review_gate_result)
        retry_round += 1


async def debate_loop_core_async(
    *,
    run_attempt: Callable[[int], Awaitable[tuple[ExecutorResult, ReviewGateResultT]]],
    clear_feedback_state: Callable[[], None],
    build_feedback: Callable[[ReviewGateResultT, ExecutorResult, int], ReviewFeedbackT | None],
    build_last_feedback: Callable[[ReviewGateResultT, ExecutorResult, int], ReviewFeedbackT],
    store_feedback: Callable[[ReviewFeedbackT], str],
    apply_feedback: Callable[[str, ReviewFeedbackT], None],
    record_round: Callable[[str, ReviewFeedbackT, ExecutorResult, ReviewGateResultT], None],
    persist_exhausted: Callable[[list[str], ReviewFeedbackT, ReviewGateResultT], str],
    record_exhausted: Callable[[list[str], str, ExecutorResult, ReviewGateResultT], None],
) -> tuple[ExecutorResult, ReviewGateResultT, bool]:
    feedback_refs: list[str] = []
    retry_round = 0
    clear_feedback_state()

    while True:
        executor_result, review_gate_result = await run_attempt(retry_round)

        if getattr(review_gate_result, "status", "") == "passed":
            clear_feedback_state()
            return executor_result, review_gate_result, False
        if executor_result.status != "completed":
            clear_feedback_state()
            return executor_result, review_gate_result, False

        if retry_round >= DEBATE_MAX_ROUNDS:
            last_feedback = build_last_feedback(
                review_gate_result,
                executor_result,
                retry_round,
            )
            debate_exhausted_ref = persist_exhausted(feedback_refs, last_feedback, review_gate_result)
            record_exhausted(feedback_refs, debate_exhausted_ref, executor_result, review_gate_result)
            return executor_result, review_gate_result, True

        feedback = build_feedback(
            review_gate_result,
            executor_result,
            retry_round + 1,
        )
        if feedback is None:
            clear_feedback_state()
            return executor_result, review_gate_result, False

        feedback_ref = store_feedback(feedback)
        feedback_refs.append(feedback_ref)
        apply_feedback(feedback_ref, feedback)
        record_round(feedback_ref, feedback, executor_result, review_gate_result)
        retry_round += 1
