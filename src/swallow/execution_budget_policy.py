from __future__ import annotations

import json
import os
from pathlib import Path

from .executor import parse_timeout_seconds
from .models import (
    EVENT_EXECUTOR_COMPLETED,
    EVENT_EXECUTOR_FAILED,
    ExecutionBudgetPolicyFinding,
    ExecutionBudgetPolicyResult,
    RetryPolicyResult,
)
from .paths import events_path


DEFAULT_TIMEOUT_SECONDS = 20


def normalize_token_cost_limit(raw_value: object) -> float:
    try:
        parsed = float(raw_value)
    except (TypeError, ValueError):
        return 0.0
    return parsed if parsed > 0 else 0.0


def calculate_task_token_cost(base_dir: Path, task_id: str) -> float:
    path = events_path(base_dir, task_id)
    if not path.exists():
        return 0.0

    total_cost = 0.0
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if not isinstance(payload, dict):
            continue
        if str(payload.get("event_type", "")).strip() not in {EVENT_EXECUTOR_COMPLETED, EVENT_EXECUTOR_FAILED}:
            continue
        event_payload = payload.get("payload", {})
        if not isinstance(event_payload, dict):
            continue
        try:
            total_cost += max(float(event_payload.get("token_cost", 0.0) or 0.0), 0.0)
        except (TypeError, ValueError):
            continue
    return total_cost


def evaluate_token_cost_budget(base_dir: Path, task_id: str, cost_limit: float) -> dict[str, float | str]:
    normalized_limit = normalize_token_cost_limit(cost_limit)
    current_token_cost = calculate_task_token_cost(base_dir, task_id)
    if normalized_limit <= 0:
        return {
            "budget_state": "available",
            "current_token_cost": current_token_cost,
            "token_cost_limit": 0.0,
        }
    return {
        "budget_state": "cost_exhausted" if current_token_cost >= normalized_limit else "available",
        "current_token_cost": current_token_cost,
        "token_cost_limit": normalized_limit,
    }


def evaluate_execution_budget_policy(
    retry_policy_result: RetryPolicyResult,
    *,
    base_dir: Path | None = None,
    task_id: str = "",
    token_cost_limit: float = 0.0,
) -> ExecutionBudgetPolicyResult:
    findings: list[ExecutionBudgetPolicyFinding] = []
    timeout_seconds = parse_timeout_seconds(os.environ.get("AIWF_EXECUTOR_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))
    normalized_token_cost_limit = normalize_token_cost_limit(token_cost_limit)
    current_token_cost = 0.0

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

    if base_dir is not None and task_id:
        token_cost_budget = evaluate_token_cost_budget(base_dir, task_id, normalized_token_cost_limit)
        current_token_cost = float(token_cost_budget.get("current_token_cost", 0.0) or 0.0)
        normalized_token_cost_limit = float(token_cost_budget.get("token_cost_limit", normalized_token_cost_limit) or 0.0)
    if normalized_token_cost_limit > 0:
        if current_token_cost >= normalized_token_cost_limit:
            findings.append(
                ExecutionBudgetPolicyFinding(
                    code="execution_budget_policy.token_cost_exhausted",
                    level="warn",
                    message="Token cost budget is exhausted for the current task card.",
                    details={
                        "current_token_cost": round(current_token_cost, 8),
                        "token_cost_limit": round(normalized_token_cost_limit, 8),
                    },
                )
            )
            budget_state = "cost_exhausted"
        else:
            findings.append(
                ExecutionBudgetPolicyFinding(
                    code="execution_budget_policy.token_cost_available",
                    level="pass",
                    message="Token cost budget remains within the configured limit.",
                    details={
                        "current_token_cost": round(current_token_cost, 8),
                        "token_cost_limit": round(normalized_token_cost_limit, 8),
                    },
                )
            )
    elif base_dir is not None and task_id:
        findings.append(
            ExecutionBudgetPolicyFinding(
                code="execution_budget_policy.token_cost_limit_disabled",
                level="pass",
                message="No token cost limit is configured for the current task card.",
                details={"current_token_cost": round(current_token_cost, 8)},
            )
        )

    if budget_state == "cost_exhausted":
        status = "warning"
        recommended_action = "Do not continue without raising token_cost_limit, choosing a cheaper route, or rerunning under operator approval."
    elif retry_policy_result.retry_decision == "attempt_limit_reached":
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
        current_token_cost=current_token_cost,
        token_cost_limit=normalized_token_cost_limit,
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
        f"- current_token_cost: {result.current_token_cost}",
        f"- token_cost_limit: {result.token_cost_limit}",
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
