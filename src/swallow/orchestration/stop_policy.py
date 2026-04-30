from __future__ import annotations

from swallow.orchestration.models import ExecutorResult, RetryPolicyResult, StopPolicyFinding, StopPolicyResult, TaskState


def evaluate_stop_policy(
    state: TaskState,
    executor_result: ExecutorResult,
    retry_policy_result: RetryPolicyResult,
) -> StopPolicyResult:
    findings: list[StopPolicyFinding] = []
    is_detached = state.execution_site_contract_kind == "local_detached"

    if is_detached:
        findings.append(
            StopPolicyFinding(
                code="stop_policy.detached_checkpoint_visible",
                level="pass",
                message="Detached local execution remains visible to the stop-policy layer.",
                details={"execution_site_contract_kind": state.execution_site_contract_kind},
            )
        )
        findings.append(
            StopPolicyFinding(
                code="stop_policy.detached_operator_checkpoint_required",
                level="warn",
                message="Detached local execution requires an explicit operator checkpoint before continuation.",
                details={"transport_kind": state.topology_transport_kind},
            )
        )
    else:
        findings.append(
            StopPolicyFinding(
                code="stop_policy.inline_checkpoint_visible",
                level="pass",
                message="Inline local execution remains visible to the stop-policy layer.",
                details={"execution_site_contract_kind": state.execution_site_contract_kind},
            )
        )

    if executor_result.status == "completed":
        findings.append(
            StopPolicyFinding(
                code="stop_policy.completed_checkpoint",
                level="warn",
                message="Completed runs stop at an operator review checkpoint before any further continuation.",
                details={"executor_status": executor_result.status},
            )
        )
        status = "warning"
        stop_required = True
        continue_allowed = False
        if is_detached:
            stop_decision = "detached_checkpoint_review"
            escalation_level = "operator_detached_review"
            checkpoint_kind = "detached_completed_run_review"
            recommended_action = (
                "Stop after this detached run and let the operator review ownership, dispatch, and output artifacts before continuing."
            )
        else:
            stop_decision = "checkpoint_review"
            escalation_level = "operator_review"
            checkpoint_kind = "completed_run_review"
            recommended_action = "Stop after this run and let the operator review the completed artifacts before continuing."
    elif retry_policy_result.retryable:
        findings.append(
            StopPolicyFinding(
                code="stop_policy.retry_checkpoint",
                level="warn",
                message="Retryable failures still require a stop-and-review checkpoint before another attempt.",
                details={"retry_decision": retry_policy_result.retry_decision},
            )
        )
        status = "warning"
        stop_required = True
        continue_allowed = False
        if is_detached:
            stop_decision = "detached_checkpoint_before_retry"
            escalation_level = "operator_detached_recovery"
            checkpoint_kind = "detached_retry_review"
            recommended_action = (
                "Stop detached automatic continuation and escalate to the operator for a gated retry decision with dispatch review."
            )
        else:
            stop_decision = "checkpoint_before_retry"
            escalation_level = "operator_recovery"
            checkpoint_kind = "retry_review"
            recommended_action = "Stop automatic continuation and escalate to the operator for a gated retry decision."
    else:
        findings.append(
            StopPolicyFinding(
                code="stop_policy.blocking_stop",
                level="fail",
                message="Current run must stop and escalate because no automatic continuation is allowed.",
                details={
                    "executor_status": executor_result.status,
                    "retry_decision": retry_policy_result.retry_decision,
                },
            )
        )
        status = "failed"
        stop_required = True
        continue_allowed = False
        if is_detached:
            stop_decision = "detached_stop_and_escalate"
            escalation_level = "operator_detached_blocking"
            checkpoint_kind = "detached_blocking_failure_review"
            recommended_action = (
                "Stop the detached run sequence here and review dispatch, ownership, and environment conditions before any further attempt."
            )
        else:
            stop_decision = "stop_and_escalate"
            escalation_level = "operator_blocking"
            checkpoint_kind = "blocking_failure_review"
            recommended_action = "Stop the run sequence here and change route, environment, or task inputs before any further attempt."

    message_map = {
        "warning": "Stop policy requires an operator checkpoint before any continuation.",
        "failed": "Stop policy blocks continuation until the operator changes conditions.",
    }
    return StopPolicyResult(
        status=status,
        message=message_map[status],
        stop_required=stop_required,
        continue_allowed=continue_allowed,
        stop_decision=stop_decision,
        escalation_level=escalation_level,
        checkpoint_kind=checkpoint_kind,
        recommended_action=recommended_action,
        findings=findings,
    )


def build_stop_policy_report(result: StopPolicyResult) -> str:
    lines = [
        "# Stop Policy Report",
        "",
        f"- status: {result.status}",
        f"- message: {result.message}",
        f"- stop_required: {'yes' if result.stop_required else 'no'}",
        f"- continue_allowed: {'yes' if result.continue_allowed else 'no'}",
        f"- stop_decision: {result.stop_decision}",
        f"- escalation_level: {result.escalation_level}",
        f"- checkpoint_kind: {result.checkpoint_kind}",
        f"- recommended_action: {result.recommended_action}",
        "",
        "## Findings",
    ]
    for finding in result.findings:
        lines.append(f"- [{finding.level}] {finding.code}: {finding.message}")
        if finding.details:
            details = ", ".join(f"{key}={value}" for key, value in finding.details.items())
            lines.append(f"  details: {details}")
    return "\n".join(lines)
