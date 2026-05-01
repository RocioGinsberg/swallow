from __future__ import annotations

from swallow.orchestration.models import TaskState


def build_phase_event_payload(state: TaskState) -> dict[str, object]:
    return {
        "phase": state.phase,
        "status": state.status,
        "execution_lifecycle": state.execution_lifecycle,
        "executor_status": state.executor_status,
    }


def build_phase_checkpoint_payload(
    state: TaskState,
    *,
    skipped: bool = False,
    source: str = "",
) -> dict[str, object]:
    return {
        "phase": state.phase,
        "status": state.status,
        "execution_phase": state.execution_phase,
        "last_phase_checkpoint_at": state.last_phase_checkpoint_at,
        "skipped": skipped,
        "source": source or ("reused_artifacts" if skipped else "live_run"),
    }


def build_phase_recovery_fallback_payload(
    *,
    requested_skip_to_phase: str,
    fallback_phase: str,
    reason: str,
) -> dict[str, object]:
    return {
        "requested_skip_to_phase": requested_skip_to_phase,
        "fallback_phase": fallback_phase,
        "reason": reason,
    }
