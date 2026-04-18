from __future__ import annotations

import json

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


@dataclass(slots=True)
class ReviewFeedback:
    round_number: int
    failed_checks: list[dict[str, Any]] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    original_output_snippet: str = ""
    max_rounds: int = 3

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _validate_output_schema(executor_result: ExecutorResult, output_schema: dict[str, Any]) -> dict[str, Any]:
    required_fields = output_schema.get("required")
    const_fields = output_schema.get("const")
    if not isinstance(required_fields, list) and not isinstance(const_fields, dict):
        return {
            "name": "output_schema",
            "passed": True,
            "detail": "schema validation skipped in v0",
        }

    try:
        payload = json.loads(executor_result.output or "")
    except json.JSONDecodeError:
        return {
            "name": "output_schema",
            "passed": False,
            "detail": "executor output is not valid JSON",
        }

    if not isinstance(payload, dict):
        return {
            "name": "output_schema",
            "passed": False,
            "detail": "executor output schema validation requires a JSON object payload",
        }

    missing_fields: list[str] = []
    if isinstance(required_fields, list):
        for field_name in required_fields:
            normalized_field = str(field_name).strip()
            if normalized_field and normalized_field not in payload:
                missing_fields.append(normalized_field)
    if missing_fields:
        return {
            "name": "output_schema",
            "passed": False,
            "detail": f"missing required fields: {', '.join(missing_fields)}",
        }

    mismatched_fields: list[str] = []
    if isinstance(const_fields, dict):
        for field_name, expected_value in const_fields.items():
            if payload.get(field_name) != expected_value:
                mismatched_fields.append(field_name)
    if mismatched_fields:
        return {
            "name": "output_schema",
            "passed": False,
            "detail": f"constant field mismatch: {', '.join(mismatched_fields)}",
        }

    validated_fields = [
        f"required={len(required_fields) if isinstance(required_fields, list) else 0}",
        f"const={len(const_fields) if isinstance(const_fields, dict) else 0}",
    ]
    return {
        "name": "output_schema",
        "passed": True,
        "detail": "validated structured output schema (" + ", ".join(validated_fields) + ")",
    }


def _truncate_output_snippet(text: str, limit: int = 500) -> str:
    normalized = text.strip()
    if len(normalized) <= limit:
        return normalized
    truncated = max(limit - 3, 0)
    return normalized[:truncated].rstrip() + "..."


def _suggestion_for_failed_check(check: dict[str, Any]) -> str:
    name = str(check.get("name", "")).strip()
    detail = str(check.get("detail", "")).strip()
    if name == "executor_status":
        return "Ensure the executor finishes with status=completed before returning to the review gate."
    if name == "output_non_empty":
        return "Return a non-empty output payload that directly addresses the task goal."
    if name == "output_schema":
        return "Return a structured JSON object that satisfies the required schema fields and constant values."
    if detail:
        return f"Address review check '{name or 'unknown'}': {detail}"
    return f"Address review check '{name or 'unknown'}' before retrying."


def build_review_feedback(
    review_gate_result: ReviewGateResult,
    executor_result: ExecutorResult,
    *,
    round_number: int,
    max_rounds: int,
) -> ReviewFeedback | None:
    failed_checks = [dict(check) for check in review_gate_result.checks if not bool(check.get("passed", False))]
    if review_gate_result.status == "passed" or not failed_checks:
        return None

    suggestions: list[str] = []
    seen_suggestions: set[str] = set()
    for check in failed_checks:
        suggestion = _suggestion_for_failed_check(check)
        if suggestion not in seen_suggestions:
            suggestions.append(suggestion)
            seen_suggestions.add(suggestion)

    return ReviewFeedback(
        round_number=max(int(round_number), 1),
        failed_checks=failed_checks,
        suggestions=suggestions,
        original_output_snippet=_truncate_output_snippet(executor_result.output or ""),
        max_rounds=max(int(max_rounds), 1),
    )


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
        checks.append(_validate_output_schema(executor_result, card.output_schema))

    all_passed = all(check["passed"] for check in checks)
    return ReviewGateResult(
        status="passed" if all_passed else "failed",
        message="All review gate checks passed." if all_passed else "One or more review gate checks failed.",
        checks=checks,
    )
