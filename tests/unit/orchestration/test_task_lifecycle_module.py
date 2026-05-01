from __future__ import annotations

from pathlib import Path

from swallow.orchestration import task_lifecycle
from swallow.orchestration.models import TaskState


def _state() -> TaskState:
    return TaskState(
        task_id="task-lifecycle-test",
        title="Lifecycle payloads",
        goal="Keep orchestration lifecycle payloads pure",
        workspace_root=".",
        status="running",
        phase="retrieval",
        execution_lifecycle="dispatched",
        executor_status="running",
        execution_phase="retrieval_done",
        last_phase_checkpoint_at="2026-05-01T00:00:00Z",
    )


def test_phase_event_payload_matches_orchestrator_event_shape() -> None:
    assert task_lifecycle.build_phase_event_payload(_state()) == {
        "phase": "retrieval",
        "status": "running",
        "execution_lifecycle": "dispatched",
        "executor_status": "running",
    }


def test_phase_checkpoint_payload_preserves_source_defaults() -> None:
    state = _state()

    assert task_lifecycle.build_phase_checkpoint_payload(state) == {
        "phase": "retrieval",
        "status": "running",
        "execution_phase": "retrieval_done",
        "last_phase_checkpoint_at": "2026-05-01T00:00:00Z",
        "skipped": False,
        "source": "live_run",
    }
    assert task_lifecycle.build_phase_checkpoint_payload(state, skipped=True)["source"] == "reused_artifacts"
    assert (
        task_lifecycle.build_phase_checkpoint_payload(
            state,
            skipped=True,
            source="previous_retrieval",
        )["source"]
        == "previous_retrieval"
    )


def test_phase_recovery_fallback_payload_matches_existing_event_shape() -> None:
    assert task_lifecycle.build_phase_recovery_fallback_payload(
        requested_skip_to_phase="analysis",
        fallback_phase="retrieval",
        reason="previous retrieval artifacts are missing or invalid",
    ) == {
        "requested_skip_to_phase": "analysis",
        "fallback_phase": "retrieval",
        "reason": "previous retrieval artifacts are missing or invalid",
    }


def test_task_lifecycle_module_has_no_control_plane_write_surface() -> None:
    source = Path(task_lifecycle.__file__).read_text(encoding="utf-8")
    public_names = {name for name in dir(task_lifecycle) if not name.startswith("_")}

    assert "save_state" not in source
    assert "append_event" not in source
    assert "orchestration.harness" not in source
    assert "orchestration.executor" not in source
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
