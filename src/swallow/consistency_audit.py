from __future__ import annotations

import json
import re
import threading
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .executor import run_prompt_executor
from .models import AuditTriggerPolicy, EVENT_EXECUTOR_COMPLETED, EVENT_EXECUTOR_FAILED, TaskState
from .paths import artifacts_dir, audit_policy_path
from .router import route_by_name
from .store import apply_atomic_text_updates, load_events, load_state, write_artifact


AUDIT_INPUT_CHAR_LIMIT = 12000
_VERDICT_PATTERN = re.compile(r"^\s*-\s*verdict:\s*(pass|fail|inconclusive)\b", re.IGNORECASE | re.MULTILINE)
_FAIL_SIGNAL_PATTERNS = (
    re.compile(r"\binconsistent\b", re.IGNORECASE),
    re.compile(r"\bcritical\b", re.IGNORECASE),
    re.compile(r"\bfail(?:ed|ure)?\b", re.IGNORECASE),
)
_PASS_SIGNAL_PATTERNS = (
    re.compile(r"\bconsistent\b", re.IGNORECASE),
    re.compile(r"\bno issues?\b", re.IGNORECASE),
    re.compile(r"\bpass(?:ed)?\b", re.IGNORECASE),
)


@dataclass(slots=True)
class ConsistencyAuditResult:
    status: str
    verdict: str
    message: str
    task_id: str
    auditor_route: str
    sample_artifact_path: str
    audit_artifact: str
    raw_output: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _timestamp_slug() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _resolve_sample_artifact_path(base_dir: Path, task_id: str, sample_artifact_path: str) -> Path:
    raw_path = str(sample_artifact_path or "").strip() or "executor_output.md"
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return artifacts_dir(base_dir, task_id) / raw_path


def _truncate_artifact_text(text: str, *, limit: int = AUDIT_INPUT_CHAR_LIMIT) -> tuple[str, bool]:
    normalized = text.strip()
    if len(normalized) <= limit:
        return normalized, False
    truncated = normalized[: max(limit - 3, 0)].rstrip() + "..."
    return truncated, True


def _build_auditor_state(base_state: TaskState, auditor_route: str) -> tuple[TaskState | None, str]:
    route = route_by_name(auditor_route)
    if route is None:
        return None, f"Unknown auditor route: {auditor_route}"

    state = TaskState.from_dict(base_state.to_dict())
    state.executor_name = route.executor_name
    state.route_name = route.name
    state.route_backend = route.backend_kind
    state.route_executor_family = route.executor_family
    state.route_execution_site = route.execution_site
    state.route_remote_capable = route.remote_capable
    state.route_transport_kind = route.transport_kind
    state.route_taxonomy_role = route.taxonomy.system_role
    state.route_taxonomy_memory_authority = route.taxonomy.memory_authority
    state.route_model_hint = route.model_hint
    state.route_dialect = route.dialect_hint
    state.route_reason = f"Consistency audit route '{route.name}' selected."
    state.route_is_fallback = False
    state.route_capabilities = route.capabilities.to_dict()
    state.topology_route_name = route.name
    state.topology_executor_family = route.executor_family
    state.topology_execution_site = route.execution_site
    state.topology_transport_kind = route.transport_kind
    state.topology_remote_capable_intent = route.remote_capable
    return state, ""


def _build_audit_prompt(
    state: TaskState,
    *,
    auditor_route: str,
    sample_artifact_path: Path,
    artifact_text: str,
    truncated: bool,
) -> str:
    semantics = state.task_semantics if isinstance(state.task_semantics, dict) else {}
    constraints = [str(item).strip() for item in semantics.get("constraints", []) if str(item).strip()]
    lines = [
        "You are auditing a Swallow task artifact for consistency and material risk.",
        "Check whether the artifact content actually satisfies the task goal and whether it contains obvious hallucinations, contradictions, or critical omissions.",
        "Return Markdown only.",
        "Use this structure:",
        "# Consistency Audit",
        "- verdict: pass | fail",
        "- risk_level: low | medium | high",
        "## Findings",
        "- concise findings",
        "## Recommended Next Step",
        "- concise operator guidance",
        "",
        "Task Context:",
        f"- task_id: {state.task_id}",
        f"- title: {state.title}",
        f"- goal: {state.goal}",
        f"- auditor_route: {auditor_route}",
        f"- sample_artifact: {sample_artifact_path.name}",
        f"- artifact_truncated: {'yes' if truncated else 'no'}",
    ]
    if constraints:
        lines.extend(f"- constraint: {constraint}" for constraint in constraints)
    lines.extend(
        [
            "",
            "Artifact Content:",
            "```text",
            artifact_text or "(empty)",
            "```",
        ]
    )
    return "\n".join(lines)


def _build_audit_report(
    *,
    status: str,
    verdict: str,
    message: str,
    task_id: str,
    auditor_route: str,
    sample_artifact_path: Path,
    raw_output: str,
) -> str:
    lines = [
        "# Consistency Audit",
        "",
        f"- status: {status}",
        f"- verdict: {verdict}",
        f"- message: {message}",
        f"- task_id: {task_id}",
        f"- auditor_route: {auditor_route}",
        f"- sample_artifact_path: {sample_artifact_path}",
        "",
        "## Auditor Output",
    ]
    if raw_output.strip():
        lines.append(raw_output.strip())
    else:
        lines.append("(no auditor output)")
    return "\n".join(lines) + "\n"


def parse_consistency_audit_verdict(raw_output: str) -> str:
    match = _VERDICT_PATTERN.search(raw_output or "")
    if match is not None:
        return match.group(1).strip().lower()

    normalized_output = raw_output or ""
    if any(pattern.search(normalized_output) for pattern in _FAIL_SIGNAL_PATTERNS):
        return "fail"
    if any(pattern.search(normalized_output) for pattern in _PASS_SIGNAL_PATTERNS):
        return "pass"
    return "inconclusive"


def load_audit_trigger_policy(base_dir: Path) -> AuditTriggerPolicy:
    path = audit_policy_path(base_dir)
    if not path.exists():
        return AuditTriggerPolicy()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AuditTriggerPolicy()
    if not isinstance(payload, dict):
        return AuditTriggerPolicy()
    return AuditTriggerPolicy.from_dict(payload)


def save_audit_trigger_policy(base_dir: Path, policy: AuditTriggerPolicy) -> Path:
    path = audit_policy_path(base_dir)
    apply_atomic_text_updates({path: json.dumps(policy.to_dict(), indent=2) + "\n"})
    return path


def build_audit_trigger_policy_report(policy: AuditTriggerPolicy) -> str:
    threshold = f"{policy.trigger_on_cost_above:.6f}" if policy.trigger_on_cost_above is not None else "-"
    return "\n".join(
        [
            "# Audit Trigger Policy",
            "",
            f"- enabled: {'yes' if policy.enabled else 'no'}",
            f"- trigger_on_degraded: {'yes' if policy.trigger_on_degraded else 'no'}",
            f"- trigger_on_cost_above: {threshold}",
            f"- auditor_route: {policy.auditor_route}",
        ]
    ) + "\n"


def _coerce_nonnegative_float(value: object) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, int | float):
        return max(float(value), 0.0)
    if isinstance(value, str):
        try:
            return max(float(value.strip()), 0.0)
        except ValueError:
            return 0.0
    return 0.0


def load_latest_executor_event_payload(base_dir: Path, task_id: str) -> dict[str, object]:
    for event in reversed(load_events(base_dir, task_id)):
        event_type = str(event.get("event_type", "")).strip()
        if event_type not in {EVENT_EXECUTOR_COMPLETED, EVENT_EXECUTOR_FAILED}:
            continue
        payload = event.get("payload", {})
        return payload if isinstance(payload, dict) else {}
    return {}


def evaluate_audit_trigger(policy: AuditTriggerPolicy, executor_payload: dict[str, object]) -> list[str]:
    if not policy.enabled or not executor_payload:
        return []

    reasons: list[str] = []
    if policy.trigger_on_degraded and bool(executor_payload.get("degraded", False)):
        reasons.append("degraded")

    threshold = policy.trigger_on_cost_above
    token_cost = _coerce_nonnegative_float(executor_payload.get("token_cost", 0.0))
    if threshold is not None and token_cost >= threshold:
        reasons.append("cost")
    return reasons


def _run_consistency_audit_background(
    base_dir: Path,
    task_id: str,
    *,
    auditor_route: str,
    sample_artifact_path: str,
) -> None:
    try:
        run_consistency_audit(
            base_dir,
            task_id,
            auditor_route=auditor_route,
            sample_artifact_path=sample_artifact_path,
        )
    except Exception:
        return


def schedule_consistency_audit(
    base_dir: Path,
    task_id: str,
    *,
    auditor_route: str,
    sample_artifact_path: str = "executor_output.md",
) -> str:
    thread = threading.Thread(
        target=_run_consistency_audit_background,
        kwargs={
            "base_dir": base_dir,
            "task_id": task_id,
            "auditor_route": auditor_route,
            "sample_artifact_path": sample_artifact_path,
        },
        daemon=True,
        name=f"swallow-audit-{task_id[:8]}",
    )
    thread.start()
    return thread.name


def run_consistency_audit(
    base_dir: Path,
    task_id: str,
    *,
    auditor_route: str,
    sample_artifact_path: str = "executor_output.md",
) -> ConsistencyAuditResult:
    audit_artifact_name = f"consistency_audit_{_timestamp_slug()}.md"
    audit_artifact_ref = f".swl/tasks/{task_id}/artifacts/{audit_artifact_name}"
    resolved_artifact_path = _resolve_sample_artifact_path(base_dir, task_id, sample_artifact_path)
    try:
        state = load_state(base_dir, task_id)
    except FileNotFoundError:
        return ConsistencyAuditResult(
            status="failed",
            verdict="inconclusive",
            message=f"Task state is missing for task_id: {task_id}",
            task_id=task_id,
            auditor_route=auditor_route,
            sample_artifact_path=str(resolved_artifact_path),
            audit_artifact="",
        )
    except Exception as exc:
        return ConsistencyAuditResult(
            status="failed",
            verdict="inconclusive",
            message=f"Task state could not be loaded for task_id {task_id}: {exc}",
            task_id=task_id,
            auditor_route=auditor_route,
            sample_artifact_path=str(resolved_artifact_path),
            audit_artifact="",
        )

    if not resolved_artifact_path.exists():
        message = f"Sample artifact is missing: {resolved_artifact_path}"
        write_artifact(
            base_dir,
            task_id,
            audit_artifact_name,
            _build_audit_report(
                status="failed",
                verdict="inconclusive",
                message=message,
                task_id=task_id,
                auditor_route=auditor_route,
                sample_artifact_path=resolved_artifact_path,
                raw_output="",
            ),
        )
        return ConsistencyAuditResult(
            status="failed",
            verdict="inconclusive",
            message=message,
            task_id=task_id,
            auditor_route=auditor_route,
            sample_artifact_path=str(resolved_artifact_path),
            audit_artifact=audit_artifact_ref,
        )

    artifact_text, truncated = _truncate_artifact_text(
        resolved_artifact_path.read_text(encoding="utf-8", errors="replace")
    )
    auditor_state, error_message = _build_auditor_state(state, auditor_route)
    if auditor_state is None:
        write_artifact(
            base_dir,
            task_id,
            audit_artifact_name,
            _build_audit_report(
                status="failed",
                verdict="inconclusive",
                message=error_message,
                task_id=task_id,
                auditor_route=auditor_route,
                sample_artifact_path=resolved_artifact_path,
                raw_output="",
            ),
        )
        return ConsistencyAuditResult(
            status="failed",
            verdict="inconclusive",
            message=error_message,
            task_id=task_id,
            auditor_route=auditor_route,
            sample_artifact_path=str(resolved_artifact_path),
            audit_artifact=audit_artifact_ref,
        )

    prompt = _build_audit_prompt(
        state,
        auditor_route=auditor_route,
        sample_artifact_path=resolved_artifact_path,
        artifact_text=artifact_text,
        truncated=truncated,
    )
    execution = run_prompt_executor(auditor_state, [], prompt)
    if execution.status == "completed":
        status = "completed"
        verdict = parse_consistency_audit_verdict(execution.output)
        message = "Consistency audit completed."
        raw_output = execution.output
    else:
        status = "failed"
        verdict = "inconclusive"
        message = execution.message or "Consistency audit failed before producing an auditor response."
        raw_output = execution.output or execution.stderr

    write_artifact(
        base_dir,
        task_id,
        audit_artifact_name,
        _build_audit_report(
            status=status,
            verdict=verdict,
            message=message,
            task_id=task_id,
            auditor_route=auditor_route,
            sample_artifact_path=resolved_artifact_path,
            raw_output=raw_output,
        ),
    )
    return ConsistencyAuditResult(
        status=status,
        verdict=verdict,
        message=message,
        task_id=task_id,
        auditor_route=auditor_route,
        sample_artifact_path=str(resolved_artifact_path),
        audit_artifact=audit_artifact_ref,
        raw_output=raw_output,
    )
