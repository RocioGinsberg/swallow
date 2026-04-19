from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .executor import run_prompt_executor
from .models import TaskState
from .paths import artifacts_dir
from .router import route_by_name
from .store import load_state, write_artifact


AUDIT_INPUT_CHAR_LIMIT = 12000


@dataclass(slots=True)
class ConsistencyAuditResult:
    status: str
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


def run_consistency_audit(
    base_dir: Path,
    task_id: str,
    *,
    auditor_route: str,
    sample_artifact_path: str = "executor_output.md",
) -> ConsistencyAuditResult:
    state = load_state(base_dir, task_id)
    resolved_artifact_path = _resolve_sample_artifact_path(base_dir, task_id, sample_artifact_path)
    audit_artifact_name = f"consistency_audit_{_timestamp_slug()}.md"
    audit_artifact_ref = f".swl/tasks/{task_id}/artifacts/{audit_artifact_name}"

    if not resolved_artifact_path.exists():
        message = f"Sample artifact is missing: {resolved_artifact_path}"
        write_artifact(
            base_dir,
            task_id,
            audit_artifact_name,
            _build_audit_report(
                status="failed",
                message=message,
                task_id=task_id,
                auditor_route=auditor_route,
                sample_artifact_path=resolved_artifact_path,
                raw_output="",
            ),
        )
        return ConsistencyAuditResult(
            status="failed",
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
                message=error_message,
                task_id=task_id,
                auditor_route=auditor_route,
                sample_artifact_path=resolved_artifact_path,
                raw_output="",
            ),
        )
        return ConsistencyAuditResult(
            status="failed",
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
        message = "Consistency audit completed."
        raw_output = execution.output
    else:
        status = "failed"
        message = execution.message or "Consistency audit failed before producing an auditor response."
        raw_output = execution.output or execution.stderr

    write_artifact(
        base_dir,
        task_id,
        audit_artifact_name,
        _build_audit_report(
            status=status,
            message=message,
            task_id=task_id,
            auditor_route=auditor_route,
            sample_artifact_path=resolved_artifact_path,
            raw_output=raw_output,
        ),
    )
    return ConsistencyAuditResult(
        status=status,
        message=message,
        task_id=task_id,
        auditor_route=auditor_route,
        sample_artifact_path=str(resolved_artifact_path),
        audit_artifact=audit_artifact_ref,
        raw_output=raw_output,
    )
