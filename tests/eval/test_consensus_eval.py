from __future__ import annotations

import tempfile
from pathlib import Path
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from swallow.models import Event, ExecutorResult, TaskCard, TaskState, ValidationResult
from swallow.orchestrator import create_task, run_task
from swallow.review_gate import run_review_gate
from swallow.store import append_event


pytestmark = pytest.mark.eval


def _review_state() -> TaskState:
    return TaskState(
        task_id="phase47-eval-review",
        title="Phase47 eval review",
        goal="Evaluate reviewer consensus behavior",
        workspace_root="/tmp/workspace",
        executor_name="http",
        route_name="local-http",
        route_backend="http_api",
        route_executor_family="api",
        route_execution_site="local",
        route_transport_kind="http",
        route_model_hint="deepseek-chat",
        route_dialect="plain_text",
    )


def _passing_validation_tuple() -> tuple[ValidationResult, ...]:
    return (
        ValidationResult(status="passed", message="Compatibility passed."),
        ValidationResult(status="passed", message="Execution fit passed."),
        ValidationResult(status="passed", message="Knowledge policy passed."),
        ValidationResult(status="passed", message="Validation passed."),
        ValidationResult(status="passed", message="Retry policy passed."),
        ValidationResult(status="warning", message="Stop policy warning."),
        ValidationResult(status="passed", message="Execution budget policy passed."),
    )


def test_phase47_eval_majority_consensus_requires_actual_majority() -> None:
    state = _review_state()
    card = TaskCard(
        goal="Require majority approval before passing",
        parent_task_id=state.task_id,
        reviewer_routes=["http-claude", "http-qwen", "http-gemini"],
        consensus_policy="majority",
    )
    reviewer_outputs = [
        ExecutorResult(
            executor_name="http",
            status="completed",
            message="review ok",
            output='{"status":"passed","message":"approved","checks":[{"name":"goal_alignment","passed":true,"detail":"goal met"}]}',
        ),
        ExecutorResult(
            executor_name="http",
            status="completed",
            message="review ok",
            output='{"status":"passed","message":"approved","checks":[{"name":"constraint_adherence","passed":true,"detail":"constraints met"}]}',
        ),
        ExecutorResult(
            executor_name="http",
            status="completed",
            message="review ok",
            output='{"status":"failed","message":"needs work","checks":[{"name":"material_risk","passed":false,"detail":"too risky"}]}',
        ),
    ]

    with patch("swallow.review_gate.run_prompt_executor_async", new=AsyncMock(side_effect=reviewer_outputs)):
        result = run_review_gate(
            state,
            ExecutorResult(
                executor_name="local",
                status="completed",
                message="ok",
                output="candidate output",
            ),
            card,
        )

    reviewer_checks = [check for check in result.checks if str(check.get("name", "")).startswith("reviewer_route:")]
    consensus_check = next(check for check in result.checks if check["name"] == "consensus_policy")

    assert result.status == "passed"
    assert len(reviewer_checks) == 3
    assert consensus_check["passed"] is True
    assert "required=2" in str(consensus_check["detail"])


def test_phase47_eval_veto_consensus_respects_primary_reviewer_rejection() -> None:
    state = _review_state()
    card = TaskCard(
        goal="Let the primary reviewer veto risky output",
        parent_task_id=state.task_id,
        reviewer_routes=["http-claude", "http-qwen"],
        consensus_policy="veto",
    )
    reviewer_outputs = [
        ExecutorResult(
            executor_name="http",
            status="completed",
            message="review ok",
            output='{"status":"failed","message":"blocked by strong reviewer","checks":[{"name":"material_risk","passed":false,"detail":"unsupported claim"}]}',
        ),
        ExecutorResult(
            executor_name="http",
            status="completed",
            message="review ok",
            output='{"status":"passed","message":"approved","checks":[{"name":"secondary_view","passed":true,"detail":"acceptable"}]}',
        ),
    ]

    with patch("swallow.review_gate.run_prompt_executor_async", new=AsyncMock(side_effect=reviewer_outputs)):
        result = run_review_gate(
            state,
            ExecutorResult(
                executor_name="local",
                status="completed",
                message="ok",
                output="candidate output",
            ),
            card,
        )

    consensus_check = next(check for check in result.checks if check["name"] == "consensus_policy")

    assert result.status == "failed"
    assert consensus_check["passed"] is False
    assert "veto route 'http-claude' rejected" in str(consensus_check["detail"])


def test_phase47_eval_budget_guard_moves_task_to_waiting_human() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        created = create_task(
            base_dir=tmp_path,
            title="Phase47 eval budget exhausted",
            goal="Escalate to human when token cost budget is already spent",
            workspace_root=tmp_path,
            executor_name="local",
            token_cost_limit=0.05,
        )
        task_dir = tmp_path / ".swl" / "tasks" / created.task_id

        append_event(
            tmp_path,
            Event(
                task_id=created.task_id,
                event_type="executor.completed",
                message="prior execution cost",
                payload={"token_cost": 0.10},
            ),
        )

        with patch("swallow.orchestrator.run_retrieval", return_value=[]):
            with patch("swallow.orchestrator.write_task_artifacts", return_value=_passing_validation_tuple()):
                with patch(
                    "swallow.executor.run_local_executor",
                    side_effect=AssertionError("executor should not run once the budget is exhausted"),
                ):
                    final_state = run_task(tmp_path, created.task_id, executor_name="local")

        events = (task_dir / "events.jsonl").read_text(encoding="utf-8")

    assert final_state.status == "waiting_human"
    assert final_state.phase == "waiting_human"
    assert final_state.execution_lifecycle == "waiting_human"
    assert "task.budget_exhausted" in events
    assert "task.waiting_human" in events
    assert "budget_exhausted" in events
