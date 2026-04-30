from __future__ import annotations

from swallow.orchestration.models import (
    CompatibilityResult,
    ExecutionFitResult,
    ExecutorResult,
    KnowledgePolicyResult,
    RetryPolicyFinding,
    RetryPolicyResult,
    TaskState,
    ValidationResult,
)


RETRYABLE_FAILURE_KINDS = {"timeout", "unreachable_backend", "generic_failure", "http_timeout", "http_rate_limited"}
BASELINE_MAX_ATTEMPTS = 2


def evaluate_retry_policy(
    state: TaskState,
    executor_result: ExecutorResult,
    compatibility_result: CompatibilityResult,
    execution_fit_result: ExecutionFitResult,
    knowledge_policy_result: KnowledgePolicyResult,
    validation_result: ValidationResult,
) -> RetryPolicyResult:
    findings: list[RetryPolicyFinding] = []
    blocking_checks = {
        "compatibility": compatibility_result.status == "failed",
        "execution_fit": execution_fit_result.status == "failed",
        "knowledge_policy": knowledge_policy_result.status == "failed",
        "validation": validation_result.status == "failed",
    }
    blocking_check_names = [name for name, blocked in blocking_checks.items() if blocked]
    remaining_attempts = max(0, BASELINE_MAX_ATTEMPTS - state.current_attempt_number)

    if blocking_check_names:
        findings.append(
            RetryPolicyFinding(
                code="retry_policy.blocked_by_checks",
                level="fail",
                message="Retry is blocked until the recorded policy or validation failures are addressed.",
                details={"blocking_checks": blocking_check_names},
            )
        )
    else:
        findings.append(
            RetryPolicyFinding(
                code="retry_policy.checks_clear",
                level="pass",
                message="No blocking compatibility, execution-fit, knowledge-policy, or validation failures were recorded.",
                details={"blocking_checks": []},
            )
        )

    if executor_result.status == "completed":
        findings.append(
            RetryPolicyFinding(
                code="retry_policy.completed_run",
                level="pass",
                message="Completed runs do not need an immediate retry recommendation.",
                details={"executor_status": executor_result.status},
            )
        )
        retryable = False
        retry_decision = "completed_no_retry"
        status = "passed"
        recommended_action = "Review the completed run instead of retrying it immediately."
    elif executor_result.failure_kind in RETRYABLE_FAILURE_KINDS:
        findings.append(
            RetryPolicyFinding(
                code="retry_policy.retryable_failure_kind",
                level="pass",
                message="Failure kind is retry-eligible under the current baseline retry policy.",
                details={"failure_kind": executor_result.failure_kind},
            )
        )
        if blocking_check_names:
            retryable = False
            retry_decision = "blocked_by_policy"
            status = "failed"
            recommended_action = "Resolve the blocking policy or validation failures before attempting another run."
        elif remaining_attempts > 0:
            retryable = True
            retry_decision = "operator_retry_available"
            status = "warning"
            recommended_action = "Review the failure context and retry once with an explicit operator checkpoint."
        else:
            retryable = False
            retry_decision = "attempt_limit_reached"
            status = "failed"
            recommended_action = "Do not retry again until the operator changes the route, environment, or task inputs."
    else:
        findings.append(
            RetryPolicyFinding(
                code="retry_policy.non_retryable_failure_kind",
                level="warn",
                message="Failure kind is not retry-eligible under the current baseline retry policy.",
                details={"failure_kind": executor_result.failure_kind or "none"},
            )
        )
        retryable = False
        retry_decision = "non_retryable_failure"
        status = "failed"
        recommended_action = "Change the local configuration or task setup before attempting another run."

    if remaining_attempts > 0:
        findings.append(
            RetryPolicyFinding(
                code="retry_policy.remaining_attempts_available",
                level="pass",
                message="The current baseline still allows another attempt slot.",
                details={
                    "current_attempt_number": state.current_attempt_number,
                    "max_attempts": BASELINE_MAX_ATTEMPTS,
                    "remaining_attempts": remaining_attempts,
                },
            )
        )
    else:
        findings.append(
            RetryPolicyFinding(
                code="retry_policy.remaining_attempts_exhausted",
                level="fail",
                message="The current baseline attempt budget is exhausted for this task state.",
                details={
                    "current_attempt_number": state.current_attempt_number,
                    "max_attempts": BASELINE_MAX_ATTEMPTS,
                    "remaining_attempts": remaining_attempts,
                },
            )
        )

    message_map = {
        "passed": "Retry policy does not require another attempt.",
        "warning": "Retry policy allows one more operator-gated attempt.",
        "failed": "Retry policy blocks another attempt until conditions change.",
    }
    return RetryPolicyResult(
        status=status,
        message=message_map[status],
        retryable=retryable,
        retry_decision=retry_decision,
        max_attempts=BASELINE_MAX_ATTEMPTS,
        remaining_attempts=remaining_attempts,
        checkpoint_required=retryable,
        recommended_action=recommended_action,
        findings=findings,
    )


def build_retry_policy_report(result: RetryPolicyResult) -> str:
    lines = [
        "# Retry Policy Report",
        "",
        f"- status: {result.status}",
        f"- message: {result.message}",
        f"- retryable: {'yes' if result.retryable else 'no'}",
        f"- retry_decision: {result.retry_decision}",
        f"- max_attempts: {result.max_attempts}",
        f"- remaining_attempts: {result.remaining_attempts}",
        f"- checkpoint_required: {'yes' if result.checkpoint_required else 'no'}",
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
