from __future__ import annotations

import os

from .executor import parse_timeout_seconds
from .models import ExecutionBudgetPolicyFinding, ExecutionBudgetPolicyResult, RetryPolicyResult


DEFAULT_TIMEOUT_SECONDS = 20


def evaluate_execution_budget_policy(retry_policy_result: RetryPolicyResult) -> ExecutionBudgetPolicyResult:
    findings: list[ExecutionBudgetPolicyFinding] = []
    timeout_seconds = parse_timeout_seconds(os.environ.get("AIWF_EXECUTOR_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))

    if timeout_seconds == DEFAULT_TIMEOUT_SECONDS:
        findings.append(
            ExecutionBudgetPolicyFinding(
                code="execution_budget_policy.timeout_default",
                level="pass",
                message="Execution timeout is using the current default baseline.",
                details={"timeout_seconds": timeout_seconds},
            )
        )
        timeout_state = "default"
    else:
        findings.append(
            ExecutionBudgetPolicyFinding(
                code="execution_budget_policy.timeout_override",
                level="warn",
                message="Execution timeout is using an explicit environment override.",
                details={"timeout_seconds": timeout_seconds},
            )
        )
        timeout_state = "override"

    if retry_policy_result.remaining_attempts > 0:
        findings.append(
            ExecutionBudgetPolicyFinding(
                code="execution_budget_policy.attempt_budget_available",
                level="pass",
                message="Attempt budget still has remaining capacity.",
                details={
                    "max_attempts": retry_policy_result.max_attempts,
                    "remaining_attempts": retry_policy_result.remaining_attempts,
                },
            )
        )
        budget_state = "available"
    else:
        findings.append(
            ExecutionBudgetPolicyFinding(
                code="execution_budget_policy.attempt_budget_exhausted",
                level="warn",
                message="Attempt budget is exhausted for the current baseline.",
                details={
                    "max_attempts": retry_policy_result.max_attempts,
                    "remaining_attempts": retry_policy_result.remaining_attempts,
                },
            )
        )
        budget_state = "exhausted"

    if retry_policy_result.retry_decision == "attempt_limit_reached":
        status = "warning"
        recommended_action = "Do not continue without changing the attempt budget or task conditions."
    elif timeout_state == "override":
        status = "warning"
        recommended_action = "Review the timeout override and confirm it matches the intended execution budget."
    else:
        status = "passed"
        recommended_action = "Current timeout and attempt budget remain within the baseline policy."

    message_map = {
        "passed": "Execution budget policy is within the current baseline.",
        "warning": "Execution budget policy requires operator attention.",
    }
    return ExecutionBudgetPolicyResult(
        status=status,
        message=message_map[status],
        timeout_seconds=timeout_seconds,
        max_attempts=retry_policy_result.max_attempts,
        remaining_attempts=retry_policy_result.remaining_attempts,
        budget_state=budget_state,
        timeout_state=timeout_state,
        recommended_action=recommended_action,
        findings=findings,
    )


def build_execution_budget_policy_report(result: ExecutionBudgetPolicyResult) -> str:
    lines = [
        "# Execution Budget Policy Report",
        "",
        f"- status: {result.status}",
        f"- message: {result.message}",
        f"- timeout_seconds: {result.timeout_seconds}",
        f"- timeout_state: {result.timeout_state}",
        f"- max_attempts: {result.max_attempts}",
        f"- remaining_attempts: {result.remaining_attempts}",
        f"- budget_state: {result.budget_state}",
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
