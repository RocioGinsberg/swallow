from __future__ import annotations

import asyncio
import json

from dataclasses import asdict, dataclass, field
from typing import Any

from .executor import run_prompt_executor_async
from .models import ExecutorResult, TaskCard, TaskState
from .router import route_by_name


REVIEW_OUTPUT_CHAR_LIMIT = 6000
CONSENSUS_POLICIES = {"majority", "veto"}
DEFAULT_REVIEWER_TIMEOUT_SECONDS = 60


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
    if name == "consensus_policy":
        return "Revise the output until the configured reviewer policy passes, then re-run the review gate."
    if name.startswith("reviewer_route:"):
        route_name = name.split(":", 1)[1] or "unknown reviewer"
        return f"Address the issues raised by reviewer route '{route_name}' before retrying."
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


def render_review_feedback_markdown(feedback: ReviewFeedback) -> str:
    lines = [
        f"## Review Feedback (Round {feedback.round_number})",
        "",
        f"- max_rounds: {feedback.max_rounds}",
        "",
        "### Failed Checks",
    ]
    if feedback.failed_checks:
        for check in feedback.failed_checks:
            lines.append(
                f"- {str(check.get('name', 'unknown')).strip() or 'unknown'}: "
                f"{str(check.get('detail', '')).strip() or 'no detail'}"
            )
    else:
        lines.append("- none")
    lines.extend(["", "### Suggestions"])
    if feedback.suggestions:
        for suggestion in feedback.suggestions:
            lines.append(f"- {suggestion}")
    else:
        lines.append("- none")
    lines.extend(["", "### Original Output Snippet"])
    if feedback.original_output_snippet:
        lines.extend(["```text", feedback.original_output_snippet, "```"])
    else:
        lines.append("(empty)")
    return "\n".join(lines)


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


def _normalize_consensus_policy(raw_policy: str) -> str:
    normalized = str(raw_policy or "majority").strip().lower()
    return normalized if normalized in CONSENSUS_POLICIES else "majority"


def _normalized_reviewer_routes(reviewer_routes: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in reviewer_routes:
        route_name = str(item).strip()
        if not route_name or route_name in seen:
            continue
        normalized.append(route_name)
        seen.add(route_name)
    return normalized


def _truncate_review_output(text: str, *, limit: int = REVIEW_OUTPUT_CHAR_LIMIT) -> str:
    normalized = str(text or "").strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(limit - 3, 0)].rstrip() + "..."


def _strip_json_fences(raw_output: str) -> str:
    stripped = raw_output.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _extract_json_payload(raw_output: str) -> dict[str, Any]:
    stripped = _strip_json_fences(raw_output)
    if not stripped:
        raise ValueError("reviewer returned an empty response")
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        payload = json.loads(stripped[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("reviewer response must decode to a JSON object")
    return payload


def _normalize_reviewer_checks(raw_checks: object) -> list[dict[str, Any]]:
    if not isinstance(raw_checks, list):
        return []

    checks: list[dict[str, Any]] = []
    for index, item in enumerate(raw_checks, start=1):
        if not isinstance(item, dict):
            checks.append(
                {
                    "name": f"review_check_{index}",
                    "passed": False,
                    "detail": f"reviewer returned a non-object check entry: {item}",
                }
            )
            continue
        name = str(item.get("name", f"review_check_{index}")).strip() or f"review_check_{index}"
        passed = bool(item.get("passed", False))
        detail = str(item.get("detail", "")).strip() or "no detail"
        checks.append({"name": name, "passed": passed, "detail": detail})
    return checks


def _reviewer_result_from_output(route_name: str, raw_output: str) -> ReviewGateResult:
    try:
        payload = _extract_json_payload(raw_output)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return ReviewGateResult(
            status="failed",
            message=f"Reviewer route '{route_name}' returned an unreadable review payload.",
            checks=[
                {
                    "name": "review_payload",
                    "passed": False,
                    "detail": f"failed to parse reviewer output: {exc}",
                }
            ],
        )

    status = str(payload.get("status", "")).strip().lower()
    if status not in {"passed", "failed"}:
        return ReviewGateResult(
            status="failed",
            message=f"Reviewer route '{route_name}' returned an invalid review status.",
            checks=[
                {
                    "name": "review_status",
                    "passed": False,
                    "detail": f"reviewer status must be 'passed' or 'failed', got: {payload.get('status')!r}",
                }
            ],
        )

    checks = _normalize_reviewer_checks(payload.get("checks", []))
    if not checks:
        checks = [
            {
                "name": "review_status",
                "passed": status == "passed",
                "detail": "reviewer provided no structured checks",
            }
        ]
    message = str(payload.get("message", "")).strip() or f"Reviewer route '{route_name}' returned {status}."
    return ReviewGateResult(status=status, message=message, checks=checks)


def _build_reviewer_prompt(
    executor_result: ExecutorResult,
    card: TaskCard,
    *,
    route_name: str,
    consensus_policy: str,
) -> str:
    constraints = [str(item).strip() for item in card.constraints if str(item).strip()]
    output_schema = json.dumps(card.output_schema, indent=2, ensure_ascii=True) if card.output_schema else "{}"
    output_text = _truncate_review_output(executor_result.output or "")
    lines = [
        "You are the review gate for a Swallow workflow task.",
        "Evaluate whether the executor output should pass this review.",
        "Return JSON only with keys: status, message, checks.",
        "Allowed status values: passed, failed.",
        "If the output is incomplete, risky, hallucinated, or does not satisfy the goal, return failed.",
        f"Consensus policy for this review set: {consensus_policy}.",
        f"Reviewer route: {route_name}.",
        "",
        "Task:",
        f"- goal: {card.goal}",
        f"- parent_task_id: {card.parent_task_id}",
        f"- constraint_count: {len(constraints)}",
    ]
    if constraints:
        lines.extend(f"- constraint: {constraint}" for constraint in constraints)
    lines.extend(
        [
            "",
            "Executor Result:",
            f"- executor_name: {executor_result.executor_name}",
            f"- status: {executor_result.status}",
            f"- message: {executor_result.message}",
            "",
            "Output Schema:",
            output_schema,
            "",
            "Executor Output:",
            "```text",
            output_text or "(empty)",
            "```",
            "",
            "Respond with JSON in this shape:",
            '{"status":"passed","message":"short summary","checks":[{"name":"goal_alignment","passed":true,"detail":"why"},{"name":"constraint_adherence","passed":true,"detail":"why"},{"name":"material_risk","passed":true,"detail":"why"}]}',
        ]
    )
    return "\n".join(lines)


def _reviewer_check(route_name: str, result: ReviewGateResult) -> dict[str, Any]:
    return {
        "name": f"reviewer_route:{route_name}",
        "passed": result.status == "passed",
        "detail": result.message,
        "reviewer_status": result.status,
        "reviewer_checks": [dict(check) for check in result.checks],
    }


def _consensus_check(
    *,
    policy: str,
    passed_count: int,
    total_count: int,
    required_count: int,
    veto_route: str,
    veto_passed: bool,
) -> dict[str, Any]:
    if policy == "veto":
        detail = (
            f"veto route '{veto_route}' {'approved' if veto_passed else 'rejected'} the output; "
            f"reference reviewers passed={passed_count}/{total_count}"
        )
        return {"name": "consensus_policy", "passed": veto_passed, "detail": detail}

    detail = f"reviewer passes={passed_count}/{total_count}; required={required_count}"
    return {"name": "consensus_policy", "passed": passed_count >= required_count, "detail": detail}


def _reviewer_timeout_seconds(card: TaskCard) -> int:
    raw_timeout = getattr(card, "reviewer_timeout_seconds", DEFAULT_REVIEWER_TIMEOUT_SECONDS)
    try:
        parsed = int(raw_timeout)
    except (TypeError, ValueError):
        return DEFAULT_REVIEWER_TIMEOUT_SECONDS
    return parsed if parsed > 0 else DEFAULT_REVIEWER_TIMEOUT_SECONDS


def _build_reviewer_state(base_state: TaskState, route_name: str) -> tuple[TaskState | None, str]:
    route = route_by_name(route_name)
    if route is None:
        return None, f"Unknown reviewer route: {route_name}"

    state = TaskState.from_dict(base_state.to_dict())
    state.executor_name = route.executor_name
    state.route_name = f"review-{route.name}"
    state.route_backend = route.backend_kind
    state.route_executor_family = route.executor_family
    state.route_execution_site = route.execution_site
    state.route_remote_capable = route.remote_capable
    state.route_transport_kind = route.transport_kind
    state.route_taxonomy_role = route.taxonomy.system_role
    state.route_taxonomy_memory_authority = route.taxonomy.memory_authority
    state.route_model_hint = route.model_hint
    state.route_dialect = route.dialect_hint
    state.route_reason = f"Consensus reviewer route '{route.name}' selected."
    state.route_is_fallback = False
    state.route_capabilities = route.capabilities.to_dict()
    state.topology_route_name = route.name
    state.topology_executor_family = route.executor_family
    state.topology_execution_site = route.execution_site
    state.topology_transport_kind = route.transport_kind
    state.topology_remote_capable_intent = route.remote_capable
    return state, ""


async def _execute_reviewer_async(
    state: TaskState,
    executor_result: ExecutorResult,
    card: TaskCard,
    *,
    route_name: str,
    consensus_policy: str,
) -> ReviewGateResult:
    reviewer_state, error_message = _build_reviewer_state(state, route_name)
    if reviewer_state is None:
        return ReviewGateResult(
            status="failed",
            message=error_message or f"Reviewer route '{route_name}' is unavailable.",
            checks=[
                {
                    "name": "reviewer_route",
                    "passed": False,
                    "detail": error_message or f"Reviewer route '{route_name}' is unavailable.",
                }
            ],
        )

    prompt = _build_reviewer_prompt(
        executor_result,
        card,
        route_name=route_name,
        consensus_policy=consensus_policy,
    )
    timeout_seconds = _reviewer_timeout_seconds(card)
    try:
        review_execution = await asyncio.wait_for(
            run_prompt_executor_async(reviewer_state, [], prompt),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        return ReviewGateResult(
            status="failed",
            message=f"Reviewer route '{route_name}' timed out before returning a usable review.",
            checks=[
                {
                    "name": "reviewer_timeout",
                    "passed": False,
                    "detail": f"reviewer timed out after {timeout_seconds} seconds",
                }
            ],
        )

    if review_execution.status != "completed":
        return ReviewGateResult(
            status="failed",
            message=f"Reviewer route '{route_name}' failed before returning a usable review.",
            checks=[
                {
                    "name": "reviewer_execution",
                    "passed": False,
                    "detail": review_execution.message,
                }
            ],
        )

    return _reviewer_result_from_output(route_name, review_execution.output)


def _reviewer_result_from_exception(route_name: str, error: Exception) -> ReviewGateResult:
    return ReviewGateResult(
        status="failed",
        message=f"Reviewer route '{route_name}' raised before returning a usable review.",
        checks=[
            {
                "name": "reviewer_execution",
                "passed": False,
                "detail": f"reviewer raised {type(error).__name__}: {error}",
            }
        ],
    )


async def run_consensus_review_async(
    state: TaskState,
    executor_result: ExecutorResult,
    card: TaskCard,
    reviewer_routes: list[str],
    consensus_policy: str,
) -> ReviewGateResult:
    normalized_routes = _normalized_reviewer_routes(reviewer_routes)
    if not normalized_routes:
        return review_executor_output(executor_result, card)

    normalized_policy = _normalize_consensus_policy(consensus_policy)
    baseline_result = review_executor_output(executor_result, card)
    if baseline_result.status != "passed":
        return baseline_result

    checks: list[dict[str, Any]] = [
        {
            "name": "baseline_review_gate",
            "passed": True,
            "detail": "Local structural review gate checks passed before consensus review.",
            "baseline_checks": [dict(check) for check in baseline_result.checks],
        }
    ]
    reviewer_tasks = [
        _execute_reviewer_async(
            state,
            executor_result,
            card,
            route_name=route_name,
            consensus_policy=normalized_policy,
        )
        for route_name in normalized_routes
    ]
    gathered_results = await asyncio.gather(*reviewer_tasks, return_exceptions=True)

    reviewer_results: list[tuple[str, ReviewGateResult]] = []
    for route_name, gathered_result in zip(normalized_routes, gathered_results):
        reviewer_result = (
            _reviewer_result_from_exception(route_name, gathered_result)
            if isinstance(gathered_result, Exception)
            else gathered_result
        )
        reviewer_results.append((route_name, reviewer_result))
        checks.append(_reviewer_check(route_name, reviewer_result))

    passed_count = sum(1 for _route_name, result in reviewer_results if result.status == "passed")
    total_count = len(reviewer_results)
    required_count = (total_count // 2) + 1
    veto_route_name = reviewer_results[0][0]
    veto_passed = reviewer_results[0][1].status == "passed"
    checks.append(
        _consensus_check(
            policy=normalized_policy,
            passed_count=passed_count,
            total_count=total_count,
            required_count=required_count,
            veto_route=veto_route_name,
            veto_passed=veto_passed,
        )
    )

    if normalized_policy == "veto":
        status = "passed" if veto_passed else "failed"
        message = (
            f"Consensus review passed: veto route '{veto_route_name}' approved the output."
            if veto_passed
            else f"Consensus review failed: veto route '{veto_route_name}' rejected the output."
        )
    else:
        status = "passed" if passed_count >= required_count else "failed"
        message = (
            f"Consensus review passed by majority vote ({passed_count}/{total_count})."
            if status == "passed"
            else f"Consensus review failed under majority vote ({passed_count}/{total_count}; required {required_count})."
        )
    return ReviewGateResult(status=status, message=message, checks=checks)


def _run_review_gate_sync(coro: Any) -> ReviewGateResult:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    close = getattr(coro, "close", None)
    if callable(close):
        close()
    raise RuntimeError("run_review_gate() cannot be used inside a running event loop; use run_review_gate_async().")


async def run_review_gate_async(state: TaskState, executor_result: ExecutorResult, card: TaskCard) -> ReviewGateResult:
    reviewer_routes = _normalized_reviewer_routes(card.reviewer_routes)
    if not reviewer_routes:
        return review_executor_output(executor_result, card)
    return await run_consensus_review_async(
        state,
        executor_result,
        card,
        reviewer_routes,
        card.consensus_policy,
    )


def run_review_gate(state: TaskState, executor_result: ExecutorResult, card: TaskCard) -> ReviewGateResult:
    return _run_review_gate_sync(run_review_gate_async(state, executor_result, card))
