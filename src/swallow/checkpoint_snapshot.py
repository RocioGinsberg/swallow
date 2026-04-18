from __future__ import annotations

from .models import CheckpointSnapshotFinding, CheckpointSnapshotResult, TaskState


def evaluate_checkpoint_snapshot(
    state: TaskState,
    handoff_record: dict[str, object],
    retry_policy: dict[str, object],
    stop_policy: dict[str, object],
    execution_budget_policy: dict[str, object],
) -> CheckpointSnapshotResult:
    handoff_status = str(handoff_record.get("status", "pending"))
    failure_kind = str(handoff_record.get("failure_kind", "")).strip()
    checkpoint_kind = str(stop_policy.get("checkpoint_kind", "pending"))
    retry_ready = bool(retry_policy.get("retryable", False)) and bool(stop_policy.get("continue_allowed", False))
    review_ready = handoff_status == "review_completed_run"
    resume_ready = handoff_status == "resume_from_failure"
    rerun_ready = state.status in {"completed", "failed"}
    monitor_needed = state.status == "running"
    recommended_reason = checkpoint_kind if checkpoint_kind != "pending" else handoff_status
    findings: list[CheckpointSnapshotFinding] = []
    recovery_semantics = "checkpoint_pending"
    interruption_kind = "none"

    required_artifacts = [
        state.artifact_paths.get("summary", ""),
        state.artifact_paths.get("resume_note", ""),
        state.artifact_paths.get("handoff_report", ""),
        state.artifact_paths.get("retry_policy_report", ""),
        state.artifact_paths.get("execution_budget_policy_report", ""),
        state.artifact_paths.get("stop_policy_report", ""),
    ]
    required_artifacts = [path for path in required_artifacts if path]

    if state.status == "created":
        status = "warning"
        checkpoint_state = "run_not_started"
        recovery_semantics = "not_started"
        recommended_path = "run"
        message = "Task has not started yet; begin the first run before any recovery path exists."
        findings.append(
            CheckpointSnapshotFinding(
                code="checkpoint.run_not_started",
                level="warning",
                message="No checkpoint exists yet because the task has not started.",
            )
        )
    elif monitor_needed:
        status = "warning"
        checkpoint_state = "run_in_progress"
        recovery_semantics = "active_attempt_monitoring"
        recommended_path = "monitor"
        message = "Latest attempt is still running; monitor current execution before choosing recovery."
        findings.append(
            CheckpointSnapshotFinding(
                code="checkpoint.run_in_progress",
                level="warning",
                message="Current attempt is still active, so recovery should wait for a terminal checkpoint.",
            )
        )
    elif retry_ready and checkpoint_kind in {"retry_review", "detached_retry_review"}:
        status = "warning"
        checkpoint_state = "retry_ready"
        recovery_semantics = "retry_checkpoint_recovery"
        recommended_path = "retry"
        message = "Latest checkpoint allows an operator-gated retry on the accepted run path."
        findings.append(
            CheckpointSnapshotFinding(
                code="checkpoint.retry_ready",
                level="warning",
                message="Retry remains available and should follow the accepted task run path.",
            )
        )
    elif state.status == "waiting_human":
        status = "warning"
        checkpoint_state = "waiting_human"
        recovery_semantics = "human_gate_debate_exhausted"
        recommended_path = "run"
        message = "Debate loop exhausted its review rounds and now requires explicit human-guided rerun."
        findings.append(
            CheckpointSnapshotFinding(
                code="checkpoint.waiting_human",
                level="warning",
                message="Debate circuit breaker tripped, so the next step is an explicit operator rerun after review feedback inspection.",
            )
        )
    elif review_ready:
        status = "passed"
        checkpoint_state = "review_ready"
        recovery_semantics = "completed_run_review"
        recommended_path = "review"
        message = "Latest completed run is checkpointed and ready for operator review."
    elif resume_ready:
        status = "warning"
        checkpoint_state = "resume_ready"
        recommended_path = "resume"
        message = "Latest failure is checkpointed for operator-guided recovery from persisted task context."
        if failure_kind in {"timeout", "launch_error", "unreachable_backend"}:
            recovery_semantics = "interruption_recovery"
            interruption_kind = failure_kind
        else:
            recovery_semantics = "failure_recovery"
            interruption_kind = failure_kind or "none"
        findings.append(
            CheckpointSnapshotFinding(
                code="checkpoint.resume_ready",
                level="warning",
                message="Recovery should begin from the failure handoff and resume note, not from hidden state.",
            )
        )
        if interruption_kind != "none":
            findings.append(
                CheckpointSnapshotFinding(
                    code="checkpoint.interruption_recovery",
                    level="warning",
                    message=f"Latest checkpoint records interruption recovery for failure_kind={interruption_kind}.",
                )
            )
    elif rerun_ready:
        status = "passed"
        checkpoint_state = "rerun_ready"
        recovery_semantics = "explicit_rerun_recovery"
        recommended_path = "rerun"
        message = "Task can be started again with an explicit operator-triggered rerun."
    else:
        status = "failed"
        checkpoint_state = "checkpoint_missing"
        recovery_semantics = "checkpoint_missing"
        recommended_path = "inspect"
        message = "Checkpoint state is incomplete; inspect task artifacts before continuing."
        findings.append(
            CheckpointSnapshotFinding(
                code="checkpoint.missing",
                level="error",
                message="Checkpoint truth is incomplete or missing for this task state.",
            )
        )

    if str(execution_budget_policy.get("budget_state", "available")) == "exhausted":
        findings.append(
            CheckpointSnapshotFinding(
                code="checkpoint.budget_exhausted",
                level="warning",
                message="Execution budget is exhausted, so recovery may require an explicit rerun decision.",
            )
        )

    return CheckpointSnapshotResult(
        status=status,
        message=message,
        checkpoint_state=checkpoint_state,
        checkpoint_kind=checkpoint_kind,
        handoff_status=handoff_status,
        execution_phase=state.execution_phase,
        last_phase_checkpoint_at=state.last_phase_checkpoint_at,
        recovery_semantics=recovery_semantics,
        interruption_kind=interruption_kind,
        recommended_path=recommended_path,
        recommended_reason=recommended_reason or checkpoint_state,
        resume_ready=resume_ready,
        retry_ready=retry_ready,
        review_ready=review_ready,
        rerun_ready=rerun_ready,
        monitor_needed=monitor_needed,
        required_artifacts=required_artifacts,
        findings=findings,
    )


def build_checkpoint_snapshot_report(result: CheckpointSnapshotResult) -> str:
    lines = [
        "# Checkpoint Snapshot Report",
        "",
        f"- status: {result.status}",
        f"- message: {result.message}",
        f"- checkpoint_state: {result.checkpoint_state}",
        f"- checkpoint_kind: {result.checkpoint_kind}",
        f"- handoff_status: {result.handoff_status}",
        f"- execution_phase: {result.execution_phase}",
        f"- last_phase_checkpoint_at: {result.last_phase_checkpoint_at or 'none'}",
        f"- recovery_semantics: {result.recovery_semantics}",
        f"- interruption_kind: {result.interruption_kind}",
        f"- recommended_path: {result.recommended_path}",
        f"- recommended_reason: {result.recommended_reason}",
        f"- resume_ready: {'yes' if result.resume_ready else 'no'}",
        f"- retry_ready: {'yes' if result.retry_ready else 'no'}",
        f"- review_ready: {'yes' if result.review_ready else 'no'}",
        f"- rerun_ready: {'yes' if result.rerun_ready else 'no'}",
        f"- monitor_needed: {'yes' if result.monitor_needed else 'no'}",
        "",
        "## Required Artifacts",
    ]
    if result.required_artifacts:
        lines.extend([f"- {item}" for item in result.required_artifacts])
    else:
        lines.append("- none")
    lines.extend(["", "## Findings"])
    if result.findings:
        for finding in result.findings:
            lines.append(f"- [{finding.level}] {finding.code}: {finding.message}")
    else:
        lines.append("- none")
    return "\n".join(lines)
