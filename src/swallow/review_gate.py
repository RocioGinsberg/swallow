from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .models import ExecutorResult, TaskCard


@dataclass(slots=True)
class ReviewGateResult:
    status: str
    message: str
    checks: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def review_executor_output(executor_result: ExecutorResult, card: TaskCard) -> ReviewGateResult:
    checks: list[dict[str, Any]] = [
        {
            "name": "executor_status",
            "passed": executor_result.status == "completed",
            "detail": f"executor reported status={executor_result.status}",
        },
        {
            "name": "output_non_empty",
            "passed": bool((executor_result.output or "").strip()),
            "detail": "executor output is non-empty"
            if (executor_result.output or "").strip()
            else "executor output is empty",
        },
    ]

    if card.output_schema:
        checks.append(
            {
                "name": "output_schema",
                "passed": True,
                "detail": "schema validation skipped in v0",
            }
        )

    all_passed = all(check["passed"] for check in checks)
    return ReviewGateResult(
        status="passed" if all_passed else "failed",
        message="All review gate checks passed." if all_passed else "One or more review gate checks failed.",
        checks=checks,
    )
