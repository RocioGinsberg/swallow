from __future__ import annotations

import asyncio

from dataclasses import dataclass, field
from pathlib import Path

from swallow.orchestration import execution_attempts
from swallow.orchestration.models import ExecutorResult, TaskCard, TaskState


@dataclass(slots=True)
class FakeReviewResult:
    status: str
    checks: list[dict[str, object]] = field(default_factory=list)


@dataclass(slots=True)
class FakeFeedback:
    round_number: int
    failed_checks: list[dict[str, object]] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    max_rounds: int = execution_attempts.DEBATE_MAX_ROUNDS


def _state(**overrides: object) -> TaskState:
    fields: dict[str, object] = {
        "task_id": "execution-attempts-test",
        "title": "Execution attempts",
        "goal": "Keep execution attempt helpers pure",
        "workspace_root": ".",
        "executor_name": "mock-executor",
        "route_dialect": "markdown",
        "review_feedback_ref": ".swl/tasks/execution-attempts-test/artifacts/review_feedback.json",
    }
    fields.update(overrides)
    return TaskState(**fields)


def _card(**overrides: object) -> TaskCard:
    fields: dict[str, object] = {
        "card_id": "card-1",
        "goal": "Run the card",
        "reviewer_routes": ["reviewer-a", "reviewer-b"],
        "consensus_policy": "veto",
        "subtask_index": 4,
    }
    fields.update(overrides)
    return TaskCard(**fields)


def _completed_executor(output: str = "executor output") -> ExecutorResult:
    return ExecutorResult(
        executor_name="mock",
        status="completed",
        message="done",
        output=output,
        prompt="prompt",
        dialect="markdown",
        latency_ms=12,
        estimated_input_tokens=3,
        estimated_output_tokens=5,
        stdout="stdout",
        stderr="stderr",
        degraded=True,
        original_route_name="primary",
        fallback_route_name="fallback",
        side_effects={"relation_suggestions": []},
    )


def _failed_review() -> FakeReviewResult:
    return FakeReviewResult(
        status="failed",
        checks=[{"name": "output_schema", "passed": False, "detail": "missing result"}],
    )


def _feedback_builder(
    review_gate_result: FakeReviewResult,
    _executor_result: ExecutorResult,
    round_number: int,
) -> FakeFeedback | None:
    failed_checks = [dict(check) for check in review_gate_result.checks if not bool(check.get("passed", False))]
    if review_gate_result.status == "passed" or not failed_checks:
        return None
    return FakeFeedback(
        round_number=round_number,
        failed_checks=failed_checks,
        suggestions=["Fix the failed checks."],
    )


def _last_feedback_builder(
    review_gate_result: FakeReviewResult,
    executor_result: ExecutorResult,
    retry_round: int,
) -> FakeFeedback:
    return _feedback_builder(review_gate_result, executor_result, retry_round) or FakeFeedback(
        round_number=retry_round,
    )


def test_next_execution_attempt_metadata_preserves_attempt_numbering_and_owner_fields() -> None:
    metadata = execution_attempts.build_next_execution_attempt_metadata(
        _state(run_attempt_count=0),
        owner_assigned_at="2026-05-02T01:00:00Z",
        dispatch_requested_at="2026-05-02T01:00:01Z",
    )

    assert metadata.to_dict() == {
        "run_attempt_count": 1,
        "current_attempt_number": 1,
        "current_attempt_id": "attempt-0001",
        "current_attempt_owner_kind": "local_orchestrator",
        "current_attempt_owner_ref": "swl_cli",
        "current_attempt_ownership_status": "owned",
        "current_attempt_owner_assigned_at": "2026-05-02T01:00:00Z",
        "current_attempt_transfer_reason": "",
        "dispatch_requested_at": "2026-05-02T01:00:01Z",
        "dispatch_started_at": "",
        "execution_lifecycle": "prepared",
    }

    second = execution_attempts.build_next_execution_attempt_metadata(
        _state(run_attempt_count=1),
        owner_assigned_at="2026-05-02T01:00:02Z",
        dispatch_requested_at="2026-05-02T01:00:03Z",
    )

    assert second.run_attempt_count == 2
    assert second.current_attempt_number == 2
    assert second.current_attempt_id == "attempt-0002"


def test_budget_exhausted_event_type_and_payload_preserve_task_and_subtask_shapes() -> None:
    card = _card()

    task_payload = execution_attempts.build_budget_exhausted_event_payload(
        card,
        retry_round=2,
        attempt_number=3,
        current_token_cost=7.5,
        token_cost_limit=7.0,
    )
    subtask_payload = execution_attempts.build_budget_exhausted_event_payload(
        card,
        retry_round=1,
        attempt_number=2,
        current_token_cost=7.5,
        token_cost_limit=7.0,
        subtask_index=9,
    )

    assert execution_attempts.budget_exhausted_event_type(subtask_index=None) == "task.budget_exhausted"
    assert execution_attempts.budget_exhausted_event_type(subtask_index=9) == "subtask.9.budget_exhausted"
    assert task_payload == {
        "card_id": "card-1",
        "goal": "Run the card",
        "retry_round": 2,
        "attempt_number": 3,
        "current_token_cost": 7.5,
        "token_cost_limit": 7.0,
        "consensus_policy": "veto",
        "reviewer_routes": ["reviewer-a", "reviewer-b"],
        "subtask_index": 4,
    }
    assert subtask_payload["subtask_index"] == 9


def test_budget_exhausted_result_builders_preserve_failure_contract() -> None:
    state = _state()

    executor_result = execution_attempts.build_budget_exhausted_executor_result(
        state,
        current_token_cost=10.25,
        token_cost_limit=10.0,
    )
    review_fields = execution_attempts.build_budget_exhausted_review_gate_fields(
        current_token_cost=10.25,
        token_cost_limit=10.0,
    )

    assert executor_result.executor_name == "mock-executor"
    assert executor_result.status == "failed"
    assert executor_result.failure_kind == "budget_exhausted"
    assert executor_result.review_feedback == ".swl/tasks/execution-attempts-test/artifacts/review_feedback.json"
    assert executor_result.dialect == "markdown"
    assert "current=10.25000000, limit=10.00000000" in executor_result.message
    assert review_fields.to_kwargs() == {
        "status": "failed",
        "message": "TaskCard token cost budget is exhausted before execution can continue.",
        "checks": [
            {
                "name": "token_cost_budget",
                "passed": False,
                "detail": "current_token_cost=10.25000000; token_cost_limit=10.00000000",
            }
        ],
    }


def test_debate_exhausted_executor_result_preserves_original_execution_fields() -> None:
    original = _completed_executor()

    exhausted = execution_attempts.build_debate_exhausted_executor_result(
        original,
        review_feedback_ref=".swl/tasks/t/artifacts/debate_exhausted.json",
    )

    assert exhausted.status == "failed"
    assert exhausted.failure_kind == "debate_circuit_breaker"
    assert exhausted.review_feedback == ".swl/tasks/t/artifacts/debate_exhausted.json"
    assert exhausted.output == original.output
    assert exhausted.prompt == original.prompt
    assert exhausted.degraded is True
    assert exhausted.original_route_name == "primary"
    assert exhausted.fallback_route_name == "fallback"
    assert exhausted.side_effects == {"relation_suggestions": []}


def test_debate_loop_core_returns_immediately_when_review_passes() -> None:
    clear_calls = 0
    attempts: list[int] = []

    def clear_feedback_state() -> None:
        nonlocal clear_calls
        clear_calls += 1

    executor_result, review_result, debate_exhausted = execution_attempts.debate_loop_core(
        run_attempt=lambda retry_round: (
            attempts.append(retry_round) or _completed_executor(),
            FakeReviewResult(status="passed"),
        ),
        clear_feedback_state=clear_feedback_state,
        build_feedback=_feedback_builder,
        build_last_feedback=_last_feedback_builder,
        store_feedback=lambda _feedback: "unused",
        apply_feedback=lambda _feedback_ref, _feedback: None,
        record_round=lambda _feedback_ref, _feedback, _executor_result, _review_gate_result: None,
        persist_exhausted=lambda _feedback_refs, _last_feedback, _review_gate_result: "unused",
        record_exhausted=lambda _feedback_refs, _ref, _executor_result, _review_gate_result: None,
    )

    assert attempts == [0]
    assert clear_calls == 2
    assert executor_result.status == "completed"
    assert review_result.status == "passed"
    assert debate_exhausted is False


def test_debate_loop_core_stores_feedback_and_retries_until_pass() -> None:
    attempts: list[int] = []
    applied_feedback_refs: list[str] = []
    recorded_rounds: list[tuple[str, int]] = []

    def run_attempt(retry_round: int) -> tuple[ExecutorResult, FakeReviewResult]:
        attempts.append(retry_round)
        if retry_round == 0:
            return _completed_executor(), _failed_review()
        return _completed_executor("fixed output"), FakeReviewResult(status="passed")

    executor_result, review_result, debate_exhausted = execution_attempts.debate_loop_core(
        run_attempt=run_attempt,
        clear_feedback_state=lambda: None,
        build_feedback=_feedback_builder,
        build_last_feedback=_last_feedback_builder,
        store_feedback=lambda feedback: f"feedback-{feedback.round_number}",
        apply_feedback=lambda feedback_ref, _feedback: applied_feedback_refs.append(feedback_ref),
        record_round=lambda feedback_ref, feedback, _executor_result, _review_gate_result: recorded_rounds.append(
            (feedback_ref, feedback.round_number)
        ),
        persist_exhausted=lambda _feedback_refs, _last_feedback, _review_gate_result: "unused",
        record_exhausted=lambda _feedback_refs, _ref, _executor_result, _review_gate_result: None,
    )

    assert attempts == [0, 1]
    assert applied_feedback_refs == ["feedback-1"]
    assert recorded_rounds == [("feedback-1", 1)]
    assert executor_result.output == "fixed output"
    assert review_result.status == "passed"
    assert debate_exhausted is False


def test_debate_loop_core_exhausts_after_max_rounds_and_records_breaker() -> None:
    attempts: list[int] = []
    stored_feedback_refs: list[str] = []
    exhausted_records: list[tuple[list[str], str, str]] = []

    def run_attempt(retry_round: int) -> tuple[ExecutorResult, FakeReviewResult]:
        attempts.append(retry_round)
        return _completed_executor(), _failed_review()

    executor_result, review_result, debate_exhausted = execution_attempts.debate_loop_core(
        run_attempt=run_attempt,
        clear_feedback_state=lambda: None,
        build_feedback=_feedback_builder,
        build_last_feedback=_last_feedback_builder,
        store_feedback=lambda feedback: f"feedback-{feedback.round_number}",
        apply_feedback=lambda feedback_ref, _feedback: stored_feedback_refs.append(feedback_ref),
        record_round=lambda _feedback_ref, _feedback, _executor_result, _review_gate_result: None,
        persist_exhausted=lambda feedback_refs, _last_feedback, _review_gate_result: "debate-exhausted-ref",
        record_exhausted=lambda feedback_refs, ref, executor_result, _review_gate_result: exhausted_records.append(
            (list(feedback_refs), ref, executor_result.status)
        ),
    )

    assert attempts == [0, 1, 2, 3]
    assert stored_feedback_refs == ["feedback-1", "feedback-2", "feedback-3"]
    assert exhausted_records == [
        (["feedback-1", "feedback-2", "feedback-3"], "debate-exhausted-ref", "completed")
    ]
    assert executor_result.status == "completed"
    assert review_result.status == "failed"
    assert debate_exhausted is True


def test_debate_loop_core_async_matches_retry_path() -> None:
    attempts: list[int] = []
    recorded_rounds: list[tuple[str, int]] = []

    async def run_attempt(retry_round: int) -> tuple[ExecutorResult, FakeReviewResult]:
        attempts.append(retry_round)
        if retry_round == 0:
            return _completed_executor(), _failed_review()
        return _completed_executor("async fixed output"), FakeReviewResult(status="passed")

    async def run_case() -> tuple[ExecutorResult, FakeReviewResult, bool]:
        return await execution_attempts.debate_loop_core_async(
            run_attempt=run_attempt,
            clear_feedback_state=lambda: None,
            build_feedback=_feedback_builder,
            build_last_feedback=_last_feedback_builder,
            store_feedback=lambda feedback: f"feedback-{feedback.round_number}",
            apply_feedback=lambda _feedback_ref, _feedback: None,
            record_round=lambda feedback_ref, feedback, _executor_result, _review_gate_result: recorded_rounds.append(
                (feedback_ref, feedback.round_number)
            ),
            persist_exhausted=lambda _feedback_refs, _last_feedback, _review_gate_result: "unused",
            record_exhausted=lambda _feedback_refs, _ref, _executor_result, _review_gate_result: None,
        )

    executor_result, review_result, debate_exhausted = asyncio.run(run_case())

    assert attempts == [0, 1]
    assert recorded_rounds == [("feedback-1", 1)]
    assert executor_result.output == "async fixed output"
    assert review_result.status == "passed"
    assert debate_exhausted is False


def test_execution_attempts_module_has_no_control_plane_write_surface() -> None:
    source = Path(execution_attempts.__file__).read_text(encoding="utf-8")
    public_names = {name for name in dir(execution_attempts) if not name.startswith("_")}

    assert "save_state" not in source
    assert "append_event" not in source
    assert "orchestration.harness" not in source
    assert "orchestration.executor" not in source
    assert "orchestration.review_gate" not in source
    assert public_names.isdisjoint(
        {
            "create_task",
            "run_task",
            "run_task_async",
            "advance",
            "transition",
            "waiting_human",
        }
    )
