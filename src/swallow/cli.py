from __future__ import annotations

import argparse
import json
from pathlib import Path

from .checkpoint_snapshot import evaluate_checkpoint_snapshot
from .doctor import diagnose_codex, format_codex_doctor_result
from .knowledge_objects import summarize_canonicalization
from .orchestrator import (
    append_task_knowledge_capture,
    create_task,
    run_task,
    update_task_planning_handoff,
)
from .paths import (
    artifacts_dir,
    capability_assembly_path,
    capability_manifest_path,
    checkpoint_snapshot_path,
    compatibility_path,
    dispatch_path,
    execution_budget_policy_path,
    execution_site_path,
    execution_fit_path,
    handoff_path,
    knowledge_index_path,
    knowledge_objects_path,
    knowledge_partition_path,
    knowledge_policy_path,
    memory_path,
    retry_policy_path,
    stop_policy_path,
    task_semantics_path,
    retrieval_path,
    route_path,
    topology_path,
)
from .store import iter_task_states, load_state


ARTIFACT_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Core Run Record", ("task_semantics_report", "summary", "resume_note", "executor_output", "executor_prompt")),
    ("Routing And Topology", ("route_report", "topology_report", "execution_site_report", "dispatch_report", "handoff_report")),
    (
        "Retrieval And Grounding",
        (
            "knowledge_objects_report",
            "knowledge_partition_report",
            "knowledge_index_report",
            "retrieval_report",
            "retrieval_json",
            "source_grounding",
        ),
    ),
    (
        "Validation",
        (
            "validation_report",
            "validation_json",
            "compatibility_report",
            "compatibility_json",
            "execution_fit_report",
            "execution_fit_json",
            "knowledge_policy_report",
            "knowledge_policy_json",
        ),
    ),
    (
        "Execution Control Policy",
        (
            "retry_policy_report",
            "retry_policy_json",
            "execution_budget_policy_report",
            "execution_budget_policy_json",
            "stop_policy_report",
            "stop_policy_json",
            "checkpoint_snapshot_report",
            "checkpoint_snapshot_json",
        ),
    ),
    (
        "Memory And Reuse",
        (
            "task_memory",
            "knowledge_objects_json",
            "knowledge_partition_json",
            "knowledge_index_json",
            "route_json",
            "topology_json",
            "execution_site_json",
            "dispatch_json",
            "handoff_json",
            "retry_policy_json",
            "execution_budget_policy_json",
            "stop_policy_json",
            "checkpoint_snapshot_json",
        ),
    ),
)


def build_grouped_artifact_index(artifact_paths: dict[str, str]) -> str:
    lines = ["Task Artifact Index", ""]
    for heading, keys in ARTIFACT_GROUPS:
        lines.append(heading)
        for key in keys:
            path = artifact_paths.get(key)
            if path:
                lines.append(f"{key}: {path}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_policy_snapshot(
    retry_policy: dict[str, object],
    execution_budget_policy: dict[str, object],
    stop_policy: dict[str, object],
) -> list[str]:
    return [
        "Policy Controls",
        f"retry_policy_status: {retry_policy.get('status', 'pending')}",
        f"retryable: {'yes' if retry_policy.get('retryable', False) else 'no'}",
        f"retry_decision: {retry_policy.get('retry_decision', 'pending')}",
        f"remaining_attempts: {retry_policy.get('remaining_attempts', 0)}",
        f"execution_budget_policy_status: {execution_budget_policy.get('status', 'pending')}",
        f"timeout_seconds: {execution_budget_policy.get('timeout_seconds', 0)}",
        f"budget_state: {execution_budget_policy.get('budget_state', 'pending')}",
        f"timeout_state: {execution_budget_policy.get('timeout_state', 'pending')}",
        f"stop_policy_status: {stop_policy.get('status', 'pending')}",
        f"stop_required: {'yes' if stop_policy.get('stop_required', False) else 'no'}",
        f"continue_allowed: {'yes' if stop_policy.get('continue_allowed', False) else 'no'}",
        f"stop_decision: {stop_policy.get('stop_decision', 'pending')}",
        f"checkpoint_kind: {stop_policy.get('checkpoint_kind', 'pending')}",
        f"escalation_level: {stop_policy.get('escalation_level', 'pending')}",
    ]


def build_intake_snapshot(base_dir: Path, task_id: str) -> list[str]:
    state = load_state(base_dir, task_id)
    task_semantics = load_json_if_exists(task_semantics_path(base_dir, task_id))
    knowledge_objects = load_json_if_exists(knowledge_objects_path(base_dir, task_id))
    if not isinstance(knowledge_objects, list):
        knowledge_objects = []
    knowledge_stage_counts = {"raw": 0, "candidate": 0, "verified": 0, "canonical": 0}
    knowledge_evidence_counts = {"artifact_backed": 0, "source_only": 0, "unbacked": 0}
    knowledge_reuse_counts = {"task_only": 0, "retrieval_candidate": 0}
    for item in knowledge_objects:
        stage = str(item.get("stage", "raw"))
        knowledge_stage_counts[stage] = knowledge_stage_counts.get(stage, 0) + 1
        evidence_status = str(item.get("evidence_status", "unbacked"))
        knowledge_evidence_counts[evidence_status] = knowledge_evidence_counts.get(evidence_status, 0) + 1
        reuse_scope = str(item.get("knowledge_reuse_scope", "task_only"))
        knowledge_reuse_counts[reuse_scope] = knowledge_reuse_counts.get(reuse_scope, 0) + 1

    return [
        f"Task Intake: {task_id}",
        f"title: {state.title}",
        "",
        "Planning Handoff",
        f"task_semantics_source_kind: {task_semantics.get('source_kind', state.task_semantics.get('source_kind', 'none') if state.task_semantics else 'none')}",
        f"task_semantics_source_ref: {task_semantics.get('source_ref', state.task_semantics.get('source_ref', '') if state.task_semantics else '') or '-'}",
        f"constraints_count: {len(task_semantics.get('constraints', state.task_semantics.get('constraints', []) if state.task_semantics else []))}",
        f"acceptance_criteria_count: {len(task_semantics.get('acceptance_criteria', state.task_semantics.get('acceptance_criteria', []) if state.task_semantics else []))}",
        f"priority_hints_count: {len(task_semantics.get('priority_hints', state.task_semantics.get('priority_hints', []) if state.task_semantics else []))}",
        f"next_action_proposals_count: {len(task_semantics.get('next_action_proposals', state.task_semantics.get('next_action_proposals', []) if state.task_semantics else []))}",
        "",
        "Staged Knowledge Capture",
        f"knowledge_objects_count: {len(knowledge_objects)}",
        f"knowledge_stage_counts: raw={knowledge_stage_counts.get('raw', 0)} candidate={knowledge_stage_counts.get('candidate', 0)} verified={knowledge_stage_counts.get('verified', 0)} canonical={knowledge_stage_counts.get('canonical', 0)}",
        f"knowledge_evidence_counts: artifact_backed={knowledge_evidence_counts.get('artifact_backed', 0)} source_only={knowledge_evidence_counts.get('source_only', 0)} unbacked={knowledge_evidence_counts.get('unbacked', 0)}",
        f"knowledge_reuse_counts: retrieval_candidate={knowledge_reuse_counts.get('retrieval_candidate', 0)} task_only={knowledge_reuse_counts.get('task_only', 0)}",
        "",
        "Boundary",
        "task_semantics_role: execution_intent",
        "knowledge_objects_role: staged_evidence",
        "",
        "Intake Artifacts",
        f"task_semantics_report: {state.artifact_paths.get('task_semantics_report', '-')}",
        f"knowledge_objects_report: {state.artifact_paths.get('knowledge_objects_report', '-')}",
        f"knowledge_partition_report: {state.artifact_paths.get('knowledge_partition_report', '-')}",
        f"knowledge_index_report: {state.artifact_paths.get('knowledge_index_report', '-')}",
    ]


def load_json_if_exists(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_json_lines_if_exists(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    items: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        items.append(json.loads(stripped))
    return items


def filter_task_states(states: list[object], focus: str) -> list[object]:
    if focus == "all":
        return states
    if focus == "active":
        return [state for state in states if state.status in {"created", "running"}]
    if focus == "failed":
        return [state for state in states if state.status == "failed"]
    if focus == "needs-review":
        return [
            state
            for state in states
            if state.status == "failed" or state.phase == "summarize" or state.executor_status != "completed"
        ]
    if focus == "recent":
        return states
    return states


def build_task_queue_entry(base_dir: Path, state: object) -> dict[str, str] | None:
    handoff = load_json_if_exists(handoff_path(base_dir, state.task_id))
    retry_policy = load_json_if_exists(retry_policy_path(base_dir, state.task_id))
    stop_policy = load_json_if_exists(stop_policy_path(base_dir, state.task_id))
    checkpoint_snapshot = load_checkpoint_snapshot(base_dir, state)

    handoff_status = str(handoff.get("status", "pending"))
    next_operator_action = str(handoff.get("next_operator_action", "")).strip()
    checkpoint_kind = str(stop_policy.get("checkpoint_kind", "pending"))
    retryable = bool(retry_policy.get("retryable", False))
    continue_allowed = bool(stop_policy.get("continue_allowed", False))
    stop_required = bool(stop_policy.get("stop_required", False))

    action = ""
    reason = ""
    if state.status == "created":
        action = "run"
        reason = "task_created"
    elif state.status == "running":
        action = "monitor"
        reason = state.execution_lifecycle or state.executor_status or "running"
    elif bool(checkpoint_snapshot.get("resume_ready", False)) and str(checkpoint_snapshot.get("recommended_path", "")) == "resume":
        action = "resume"
        reason = str(checkpoint_snapshot.get("recommended_reason", recommended_reason_for_checkpoint(checkpoint_snapshot, handoff_status)))
    elif retryable and continue_allowed:
        action = "retry"
        reason = checkpoint_kind if checkpoint_kind != "pending" else str(retry_policy.get("retry_decision", "retryable"))
    elif handoff_status == "review_completed_run":
        action = "review"
        reason = checkpoint_kind if checkpoint_kind != "pending" else handoff_status
    elif state.status == "failed" or stop_required or handoff_status == "resume_from_failure":
        action = "inspect"
        reason = checkpoint_kind if checkpoint_kind != "pending" else str(stop_policy.get("stop_decision", handoff_status))
    else:
        return None

    return {
        "task_id": state.task_id,
        "action": action,
        "status": state.status,
        "attempt": state.current_attempt_id or "-",
        "updated_at": state.updated_at,
        "reason": reason or "pending",
        "next": next_operator_action or "-",
        "title": state.title,
    }


def recommended_reason_for_checkpoint(checkpoint_snapshot: dict[str, object], handoff_status: str) -> str:
    return str(
        checkpoint_snapshot.get("recommended_reason")
        or checkpoint_snapshot.get("checkpoint_state")
        or handoff_status
        or "pending"
    )


def path_boundary_status(
    *,
    path_name: str,
    allowed: bool,
    reason: str,
    suggested_path: str,
) -> str:
    boundary = "allowed" if allowed else "blocked"
    if suggested_path and suggested_path != path_name:
        return f"{boundary} reason={reason} suggested_path={suggested_path}"
    return f"{boundary} reason={reason}"


def build_control_boundaries(
    state: object,
    checkpoint_snapshot: dict[str, object],
    retry_policy: dict[str, object],
    stop_policy: dict[str, object],
    handoff: dict[str, object],
) -> dict[str, str]:
    suggested_path = str(checkpoint_snapshot.get("recommended_path", "none"))
    suggested_reason = str(
        checkpoint_snapshot.get("recommended_reason")
        or checkpoint_snapshot.get("checkpoint_state")
        or handoff.get("status", "pending")
    )
    retry_allowed = bool(retry_policy.get("retryable", False)) and str(stop_policy.get("checkpoint_kind", "")) in {
        "retry_review",
        "detached_retry_review",
    }
    resume_allowed = bool(checkpoint_snapshot.get("resume_ready", False)) and suggested_path == "resume"
    rerun_allowed = state.status in {"completed", "failed"}
    return {
        "resume": path_boundary_status(
            path_name="resume",
            allowed=resume_allowed,
            reason=suggested_reason if resume_allowed else str(checkpoint_snapshot.get("checkpoint_state", "pending")),
            suggested_path=suggested_path,
        ),
        "retry": path_boundary_status(
            path_name="retry",
            allowed=retry_allowed,
            reason=str(retry_policy.get("retry_decision", suggested_reason)),
            suggested_path=suggested_path,
        ),
        "rerun": path_boundary_status(
            path_name="rerun",
            allowed=rerun_allowed,
            reason="explicit_operator_override" if rerun_allowed else "task_not_terminal",
            suggested_path=suggested_path,
        ),
    }


def load_checkpoint_snapshot(base_dir: Path, state: object) -> dict[str, object]:
    checkpoint_snapshot = load_json_if_exists(checkpoint_snapshot_path(base_dir, state.task_id))
    if checkpoint_snapshot:
        return checkpoint_snapshot
    handoff = load_json_if_exists(handoff_path(base_dir, state.task_id))
    retry_policy = load_json_if_exists(retry_policy_path(base_dir, state.task_id))
    stop_policy = load_json_if_exists(stop_policy_path(base_dir, state.task_id))
    execution_budget_policy = load_json_if_exists(execution_budget_policy_path(base_dir, state.task_id))
    return evaluate_checkpoint_snapshot(state, handoff, retry_policy, stop_policy, execution_budget_policy).to_dict()


def build_task_control_snapshot(base_dir: Path, state: object) -> list[str]:
    handoff = load_json_if_exists(handoff_path(base_dir, state.task_id))
    retry_policy = load_json_if_exists(retry_policy_path(base_dir, state.task_id))
    execution_budget_policy = load_json_if_exists(execution_budget_policy_path(base_dir, state.task_id))
    stop_policy = load_json_if_exists(stop_policy_path(base_dir, state.task_id))
    checkpoint_snapshot = load_checkpoint_snapshot(base_dir, state)
    queue_entry = build_task_queue_entry(base_dir, state)
    boundaries = build_control_boundaries(
        state,
        checkpoint_snapshot,
        retry_policy,
        stop_policy,
        handoff,
    )

    lines = [
        f"Task Control: {state.task_id}",
        f"title: {state.title}",
        "",
        "Control Snapshot",
        f"recommended_action: {checkpoint_snapshot.get('recommended_path', queue_entry['action'] if queue_entry else 'none')}",
        f"recommended_reason: {checkpoint_snapshot.get('recommended_reason', queue_entry['reason'] if queue_entry else 'no_action_needed')}",
        f"checkpoint_state: {checkpoint_snapshot.get('checkpoint_state', 'pending')}",
        f"recovery_semantics: {checkpoint_snapshot.get('recovery_semantics', 'pending')}",
        f"interruption_kind: {checkpoint_snapshot.get('interruption_kind', 'none')}",
        f"resume_ready: {'yes' if checkpoint_snapshot.get('resume_ready', False) else 'no'}",
        f"next_operator_action: {handoff.get('next_operator_action', 'Inspect task artifacts.')}",
        f"retry_ready: {'yes' if retry_policy.get('retryable', False) and stop_policy.get('continue_allowed', False) else 'no'}",
        f"review_ready: {'yes' if handoff.get('status', '') == 'review_completed_run' else 'no'}",
        f"rerun_ready: {'yes' if state.status in {'completed', 'failed'} else 'no'}",
        f"monitor_needed: {'yes' if state.status == 'running' else 'no'}",
        f"stop_required: {'yes' if stop_policy.get('stop_required', False) else 'no'}",
        f"continue_allowed: {'yes' if stop_policy.get('continue_allowed', False) else 'no'}",
        "",
        "Control Boundaries",
        f"resume_path: {boundaries['resume']}",
        f"retry_path: {boundaries['retry']}",
        f"rerun_path: {boundaries['rerun']}",
        "",
    ]
    lines.extend(build_policy_snapshot(retry_policy, execution_budget_policy, stop_policy))
    lines.extend(
        [
            "",
            "Control Artifacts",
            f"review: swl task review {state.task_id}",
            f"resume: swl task resume {state.task_id}",
            f"policy: swl task policy {state.task_id}",
            f"checkpoint: swl task checkpoint {state.task_id}",
            f"inspect: swl task inspect {state.task_id}",
            f"run: swl task run {state.task_id}",
            f"resume_note: {state.artifact_paths.get('resume_note', '-')}",
            f"handoff_report: {state.artifact_paths.get('handoff_report', '-')}",
            f"retry_policy_report: {state.artifact_paths.get('retry_policy_report', '-')}",
            f"execution_budget_policy_report: {state.artifact_paths.get('execution_budget_policy_report', '-')}",
            f"stop_policy_report: {state.artifact_paths.get('stop_policy_report', '-')}",
            f"checkpoint_snapshot_report: {state.artifact_paths.get('checkpoint_snapshot_report', '-')}",
        ]
    )
    return lines


def build_attempt_summaries(base_dir: Path, task_id: str) -> list[dict[str, str]]:
    events = load_json_lines_if_exists(base_dir / ".swl" / "tasks" / task_id / "events.jsonl")
    attempts: dict[str, dict[str, str]] = {}
    attempt_order: list[str] = []
    for event in events:
        payload = event.get("payload", {})
        if not isinstance(payload, dict):
            payload = {}
        attempt_id = str(payload.get("attempt_id", "")).strip()
        if not attempt_id:
            continue
        if attempt_id not in attempts:
            attempts[attempt_id] = {
                "attempt_id": attempt_id,
                "attempt_number": str(payload.get("attempt_number", 0)),
                "started_at": str(event.get("created_at", "-")),
                "finished_at": "-",
                "status": "running",
                "executor_status": str(payload.get("executor_status", "pending")),
                "execution_lifecycle": str(payload.get("execution_lifecycle", "pending")),
                "retrieval_count": str(payload.get("retrieval_count", 0)),
                "compatibility_status": str(payload.get("compatibility_status", "pending")),
                "execution_fit_status": str(payload.get("execution_fit_status", "pending")),
                "retry_policy_status": str(payload.get("retry_policy_status", "pending")),
                "stop_policy_status": str(payload.get("stop_policy_status", "pending")),
                "handoff_status": "pending",
            }
            attempt_order.append(attempt_id)
        summary = attempts[attempt_id]
        event_type = str(event.get("event_type", ""))
        summary["attempt_number"] = str(payload.get("attempt_number", summary["attempt_number"]))
        if event_type == "task.run_started":
            summary["started_at"] = str(event.get("created_at", summary["started_at"]))
            summary["executor_status"] = str(payload.get("executor_status", summary["executor_status"]))
            summary["execution_lifecycle"] = str(payload.get("execution_lifecycle", summary["execution_lifecycle"]))
        elif event_type in {"task.completed", "task.failed"}:
            summary["finished_at"] = str(event.get("created_at", summary["finished_at"]))
            summary["status"] = str(payload.get("status", summary["status"]))
            summary["executor_status"] = str(payload.get("executor_status", summary["executor_status"]))
            summary["execution_lifecycle"] = str(payload.get("execution_lifecycle", summary["execution_lifecycle"]))
            summary["retrieval_count"] = str(payload.get("retrieval_count", summary["retrieval_count"]))
            summary["compatibility_status"] = str(payload.get("compatibility_status", summary["compatibility_status"]))
            summary["execution_fit_status"] = str(payload.get("execution_fit_status", summary["execution_fit_status"]))
            summary["retry_policy_status"] = str(payload.get("retry_policy_status", summary["retry_policy_status"]))
            summary["stop_policy_status"] = str(payload.get("stop_policy_status", summary["stop_policy_status"]))

    handoff = load_json_if_exists(handoff_path(base_dir, task_id))
    latest_handoff_attempt = str(handoff.get("attempt_id", "")).strip()
    if latest_handoff_attempt in attempts:
        attempts[latest_handoff_attempt]["handoff_status"] = str(handoff.get("status", "pending"))

    return [attempts[attempt_id] for attempt_id in reversed(attempt_order)]


def resolve_attempt_pair(attempts: list[dict[str, str]], left: str | None, right: str | None) -> tuple[dict[str, str], dict[str, str]]:
    by_id = {attempt["attempt_id"]: attempt for attempt in attempts}
    if left and right:
        if left not in by_id or right not in by_id:
            raise ValueError("Unknown attempt id for comparison.")
        return by_id[left], by_id[right]
    if len(attempts) < 2:
        raise ValueError("At least two attempts are required for comparison.")
    return attempts[1], attempts[0]


def execute_task_run(
    base_dir: Path,
    task_id: str,
    executor_name: str | None,
    capability_refs: list[str] | None,
    route_mode: str | None,
) -> int:
    state = run_task(
        base_dir=base_dir,
        task_id=task_id,
        executor_name=executor_name,
        capability_refs=capability_refs,
        route_mode=route_mode,
    )
    print(f"{state.task_id} {state.status} retrieval={state.retrieval_count}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="swl",
        description="CLI for the swallow stateful AI workflow system.",
    )
    parser.add_argument(
        "--base-dir",
        default=".",
        help="Directory that stores the .swl task state and artifacts. Defaults to the current directory.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    task_parser = subparsers.add_parser("task", help="Task workbench and lifecycle commands.")
    task_subparsers = task_parser.add_subparsers(dest="task_command", required=True)
    doctor_parser = subparsers.add_parser("doctor", help="Diagnostic commands.")
    doctor_subparsers = doctor_parser.add_subparsers(dest="doctor_command", required=True)

    create_parser = task_subparsers.add_parser("create", help="Create a task.")
    create_parser.add_argument("--title", required=True, help="Short task title.")
    create_parser.add_argument("--goal", required=True, help="Concrete task goal.")
    create_parser.add_argument(
        "--workspace-root",
        default=".",
        help="Workspace to retrieve context from. Defaults to the current directory.",
    )
    create_parser.add_argument(
        "--executor",
        default="codex",
        help="Executor to persist for the task. Defaults to codex.",
    )
    create_parser.add_argument(
        "--constraint",
        action="append",
        default=[],
        help="Imported planning constraint to attach to task semantics. Repeatable.",
    )
    create_parser.add_argument(
        "--acceptance-criterion",
        action="append",
        default=[],
        help="Imported acceptance criterion to attach to task semantics. Repeatable.",
    )
    create_parser.add_argument(
        "--priority-hint",
        action="append",
        default=[],
        help="Imported priority hint to attach to task semantics. Repeatable.",
    )
    create_parser.add_argument(
        "--next-action-proposal",
        action="append",
        default=[],
        help="Imported next action proposal to attach to task semantics. Repeatable.",
    )
    create_parser.add_argument(
        "--planning-source",
        default="",
        help="Optional external planning source reference for task semantics.",
    )
    create_parser.add_argument(
        "--knowledge-item",
        action="append",
        default=[],
        help="External knowledge fragment to attach as a staged knowledge object. Repeatable.",
    )
    create_parser.add_argument(
        "--knowledge-stage",
        default="raw",
        choices=["raw", "candidate", "verified", "canonical"],
        help="Initial stage for imported knowledge objects. Defaults to raw.",
    )
    create_parser.add_argument(
        "--knowledge-source",
        default="",
        help="Optional external source reference for imported knowledge objects.",
    )
    create_parser.add_argument(
        "--knowledge-artifact-ref",
        action="append",
        default=[],
        help="Optional artifact-backed evidence reference for each imported knowledge object. Repeatable and aligned by order.",
    )
    create_parser.add_argument(
        "--knowledge-retrieval-eligible",
        action="store_true",
        help="Declare imported knowledge objects as retrieval-eligible candidates without automatically enabling retrieval reuse.",
    )
    create_parser.add_argument(
        "--knowledge-canonicalization-intent",
        default="none",
        choices=["none", "review", "promote"],
        help="Optional canonicalization intent for imported knowledge objects. This does not promote them automatically.",
    )
    create_parser.add_argument(
        "--capability",
        action="append",
        default=[],
        help="Capability reference to persist with the task, for example profile:baseline_local or validator:run_output_validation. Repeatable.",
    )
    create_parser.add_argument(
        "--route-mode",
        default="auto",
        choices=["auto", "live", "deterministic", "detached", "offline", "summary"],
        help="Routing policy mode to persist for the task. Defaults to auto.",
    )
    planning_handoff_parser = task_subparsers.add_parser(
        "planning-handoff",
        help="Attach or tighten imported planning semantics for an existing task.",
        description="Attach or tighten imported planning semantics for an existing task.",
    )
    planning_handoff_parser.add_argument("task_id", help="Task identifier.")
    planning_handoff_parser.add_argument(
        "--planning-source",
        default="",
        help="Optional external planning source reference for task semantics.",
    )
    planning_handoff_parser.add_argument(
        "--constraint",
        action="append",
        default=[],
        help="Imported planning constraint to attach to task semantics. Repeatable.",
    )
    planning_handoff_parser.add_argument(
        "--acceptance-criterion",
        action="append",
        default=[],
        help="Imported acceptance criterion to attach to task semantics. Repeatable.",
    )
    planning_handoff_parser.add_argument(
        "--priority-hint",
        action="append",
        default=[],
        help="Imported priority hint to attach to task semantics. Repeatable.",
    )
    planning_handoff_parser.add_argument(
        "--next-action-proposal",
        action="append",
        default=[],
        help="Imported next action proposal to attach to task semantics. Repeatable.",
    )
    knowledge_capture_parser = task_subparsers.add_parser(
        "knowledge-capture",
        help="Attach staged knowledge objects to an existing task.",
        description="Attach staged knowledge objects to an existing task.",
    )
    knowledge_capture_parser.add_argument("task_id", help="Task identifier.")
    knowledge_capture_parser.add_argument(
        "--knowledge-item",
        action="append",
        default=[],
        help="External knowledge fragment to attach as a staged knowledge object. Repeatable.",
    )
    knowledge_capture_parser.add_argument(
        "--knowledge-stage",
        default="raw",
        choices=["raw", "candidate", "verified", "canonical"],
        help="Stage for imported knowledge objects. Defaults to raw.",
    )
    knowledge_capture_parser.add_argument(
        "--knowledge-source",
        default="",
        help="Optional external source reference for imported knowledge objects.",
    )
    knowledge_capture_parser.add_argument(
        "--knowledge-artifact-ref",
        action="append",
        default=[],
        help="Optional artifact-backed evidence reference for each imported knowledge object. Repeatable and aligned by order.",
    )
    knowledge_capture_parser.add_argument(
        "--knowledge-retrieval-eligible",
        action="store_true",
        help="Declare imported knowledge objects as retrieval-eligible candidates without automatically enabling retrieval reuse.",
    )
    knowledge_capture_parser.add_argument(
        "--knowledge-canonicalization-intent",
        default="none",
        choices=["none", "review", "promote"],
        help="Optional canonicalization intent for imported knowledge objects. This does not promote them automatically.",
    )

    run_parser = task_subparsers.add_parser("run", help="Run a task through the current workflow loop.")
    run_parser.add_argument("task_id", help="Task identifier.")
    run_parser.add_argument(
        "--executor",
        default=None,
        help="Override the task executor for this run.",
    )
    run_parser.add_argument(
        "--capability",
        action="append",
        default=[],
        help="Override the task capability manifest for this run with repeatable kind:ref entries.",
    )
    run_parser.add_argument(
        "--route-mode",
        default=None,
        choices=["auto", "live", "deterministic", "detached", "offline", "summary"],
        help="Override the task routing policy mode for this run.",
    )
    retry_parser = task_subparsers.add_parser(
        "retry",
        help="Retry a task on the accepted run path when retry and stop policy allow it.",
        description="Retry a task on the accepted run path when retry and stop policy allow it.",
    )
    retry_parser.add_argument("task_id", help="Task identifier.")
    retry_parser.add_argument(
        "--executor",
        default=None,
        help="Override the task executor for this retry.",
    )
    retry_parser.add_argument(
        "--capability",
        action="append",
        default=None,
        help="Override the task capability manifest for this retry with repeatable kind:ref entries.",
    )
    retry_parser.add_argument(
        "--route-mode",
        default=None,
        choices=["auto", "live", "deterministic", "detached", "offline", "summary"],
        help="Override the task routing policy mode for this retry.",
    )
    resume_parser = task_subparsers.add_parser(
        "resume",
        help="Resume a task on the accepted run path when checkpoint recovery truth allows it.",
        description="Resume a task on the accepted run path when checkpoint recovery truth allows it.",
    )
    resume_parser.add_argument("task_id", help="Task identifier.")
    resume_parser.add_argument(
        "--executor",
        default=None,
        help="Override the task executor for this resume attempt.",
    )
    resume_parser.add_argument(
        "--capability",
        action="append",
        default=None,
        help="Override the task capability manifest for this resume attempt with repeatable kind:ref entries.",
    )
    resume_parser.add_argument(
        "--route-mode",
        default=None,
        choices=["auto", "live", "deterministic", "detached", "offline", "summary"],
        help="Override the task routing policy mode for this resume attempt.",
    )
    rerun_parser = task_subparsers.add_parser(
        "rerun",
        help="Start a new explicit operator-triggered run even when retry or resume stay blocked.",
        description="Start a new explicit operator-triggered run even when retry or resume stay blocked.",
    )
    rerun_parser.add_argument("task_id", help="Task identifier.")
    rerun_parser.add_argument(
        "--executor",
        default=None,
        help="Override the task executor for this rerun.",
    )
    rerun_parser.add_argument(
        "--capability",
        action="append",
        default=None,
        help="Override the task capability manifest for this rerun with repeatable kind:ref entries.",
    )
    rerun_parser.add_argument(
        "--route-mode",
        default=None,
        choices=["auto", "live", "deterministic", "detached", "offline", "summary"],
        help="Override the task routing policy mode for this rerun.",
    )

    list_parser = task_subparsers.add_parser("list", help="List tasks with compact status summaries.")
    list_parser.add_argument(
        "--focus",
        default="all",
        choices=["all", "active", "failed", "needs-review", "recent"],
        help="Restrict the list to a simple operator attention view. Defaults to all.",
    )
    list_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of tasks to print after filtering.",
    )
    queue_parser = task_subparsers.add_parser(
        "queue", help="List tasks that currently need operator action, including resume/retry/review."
    )
    queue_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of queue entries to print.",
    )
    attempts_parser = task_subparsers.add_parser("attempts", help="Print compact attempt history for a task.")
    attempts_parser.add_argument("task_id", help="Task identifier.")
    compare_attempts_parser = task_subparsers.add_parser(
        "compare-attempts", help="Compare two task attempts using compact control-relevant fields."
    )
    compare_attempts_parser.add_argument("task_id", help="Task identifier.")
    compare_attempts_parser.add_argument("--left", default=None, help="Left attempt id. Defaults to the prior attempt.")
    compare_attempts_parser.add_argument("--right", default=None, help="Right attempt id. Defaults to the latest attempt.")
    control_parser = task_subparsers.add_parser(
        "control", help="Print a compact per-task recovery and control snapshot."
    )
    control_parser.add_argument("task_id", help="Task identifier.")
    intake_parser = task_subparsers.add_parser(
        "intake",
        help="Print a compact planning-handoff and staged-knowledge intake snapshot.",
        description="Print a compact planning-handoff and staged-knowledge intake snapshot.",
    )
    intake_parser.add_argument("task_id", help="Task identifier.")
    inspect_parser = task_subparsers.add_parser("inspect", help="Print a compact per-task overview.")
    inspect_parser.add_argument("task_id", help="Task identifier.")
    semantics_parser = task_subparsers.add_parser("semantics", help="Print the task semantics report artifact.")
    semantics_parser.add_argument("task_id", help="Task identifier.")
    capabilities_parser = task_subparsers.add_parser("capabilities", help="Print the task capability assembly summary.")
    capabilities_parser.add_argument("task_id", help="Task identifier.")
    knowledge_objects_parser = task_subparsers.add_parser(
        "knowledge-objects", help="Print the task knowledge-objects report artifact."
    )
    knowledge_objects_parser.add_argument("task_id", help="Task identifier.")
    knowledge_partition_parser = task_subparsers.add_parser(
        "knowledge-partition", help="Print the task knowledge-partition report artifact."
    )
    knowledge_partition_parser.add_argument("task_id", help="Task identifier.")
    knowledge_index_parser = task_subparsers.add_parser(
        "knowledge-index", help="Print the task knowledge-index report artifact."
    )
    knowledge_index_parser.add_argument("task_id", help="Task identifier.")
    knowledge_policy_parser = task_subparsers.add_parser(
        "knowledge-policy", help="Print the task knowledge-policy report artifact."
    )
    knowledge_policy_parser.add_argument("task_id", help="Task identifier.")
    review_parser = task_subparsers.add_parser("review", help="Print a review-focused task handoff summary.")
    review_parser.add_argument("task_id", help="Task identifier.")
    checkpoint_parser = task_subparsers.add_parser(
        "checkpoint",
        help="Print the task checkpoint snapshot report used for resume, retry, review, and rerun guidance.",
        description="Print the task checkpoint snapshot report used for resume, retry, review, and rerun guidance.",
    )
    checkpoint_parser.add_argument("task_id", help="Task identifier.")
    policy_parser = task_subparsers.add_parser("policy", help="Print a compact execution-control policy summary.")
    policy_parser.add_argument("task_id", help="Task identifier.")
    artifacts_parser = task_subparsers.add_parser("artifacts", help="Print grouped task artifact paths.")
    artifacts_parser.add_argument("task_id", help="Task identifier.")

    summarize_parser = task_subparsers.add_parser("summarize", help="Print the task summary artifact.")
    summarize_parser.add_argument("task_id", help="Task identifier.")

    resume_note_parser = task_subparsers.add_parser(
        "resume-note",
        help="Print the task resume note artifact.",
    )
    resume_note_parser.add_argument("task_id", help="Task identifier.")
    validation_parser = task_subparsers.add_parser("validation", help="Print the task validation report artifact.")
    validation_parser.add_argument("task_id", help="Task identifier.")
    compatibility_parser = task_subparsers.add_parser(
        "compatibility",
        help="Print the task compatibility report artifact.",
    )
    compatibility_parser.add_argument("task_id", help="Task identifier.")
    grounding_parser = task_subparsers.add_parser("grounding", help="Print the task source grounding artifact.")
    grounding_parser.add_argument("task_id", help="Task identifier.")
    retrieval_parser = task_subparsers.add_parser("retrieval", help="Print the task retrieval report artifact.")
    retrieval_parser.add_argument("task_id", help="Task identifier.")
    topology_parser = task_subparsers.add_parser("topology", help="Print the task topology report artifact.")
    topology_parser.add_argument("task_id", help="Task identifier.")
    execution_site_parser = task_subparsers.add_parser(
        "execution-site",
        help="Print the task execution-site report artifact.",
    )
    execution_site_parser.add_argument("task_id", help="Task identifier.")
    dispatch_parser = task_subparsers.add_parser("dispatch", help="Print the task dispatch report artifact.")
    dispatch_parser.add_argument("task_id", help="Task identifier.")
    handoff_parser = task_subparsers.add_parser("handoff", help="Print the task handoff report artifact.")
    handoff_parser.add_argument("task_id", help="Task identifier.")
    execution_fit_parser = task_subparsers.add_parser(
        "execution-fit",
        help="Print the task execution-fit report artifact.",
    )
    execution_fit_parser.add_argument("task_id", help="Task identifier.")
    retry_policy_parser = task_subparsers.add_parser(
        "retry-policy",
        help="Print the task retry-policy report artifact.",
    )
    retry_policy_parser.add_argument("task_id", help="Task identifier.")
    execution_budget_policy_parser = task_subparsers.add_parser(
        "execution-budget-policy",
        help="Print the task execution-budget-policy report artifact.",
    )
    execution_budget_policy_parser.add_argument("task_id", help="Task identifier.")
    stop_policy_parser = task_subparsers.add_parser(
        "stop-policy",
        help="Print the task stop-policy report artifact.",
    )
    stop_policy_parser.add_argument("task_id", help="Task identifier.")
    memory_parser = task_subparsers.add_parser("memory", help="Print the task memory record.")
    memory_parser.add_argument("task_id", help="Task identifier.")
    route_parser = task_subparsers.add_parser("route", help="Print the task route report artifact.")
    route_parser.add_argument("task_id", help="Task identifier.")
    compatibility_json_parser = task_subparsers.add_parser(
        "compatibility-json",
        help="Print the task compatibility record.",
    )
    compatibility_json_parser.add_argument("task_id", help="Task identifier.")
    route_json_parser = task_subparsers.add_parser("route-json", help="Print the task route record.")
    route_json_parser.add_argument("task_id", help="Task identifier.")
    topology_json_parser = task_subparsers.add_parser("topology-json", help="Print the task topology record.")
    topology_json_parser.add_argument("task_id", help="Task identifier.")
    execution_site_json_parser = task_subparsers.add_parser(
        "execution-site-json",
        help="Print the task execution-site record.",
    )
    execution_site_json_parser.add_argument("task_id", help="Task identifier.")
    dispatch_json_parser = task_subparsers.add_parser("dispatch-json", help="Print the task dispatch record.")
    dispatch_json_parser.add_argument("task_id", help="Task identifier.")
    handoff_json_parser = task_subparsers.add_parser("handoff-json", help="Print the task handoff record.")
    handoff_json_parser.add_argument("task_id", help="Task identifier.")
    execution_fit_json_parser = task_subparsers.add_parser(
        "execution-fit-json",
        help="Print the task execution-fit record.",
    )
    execution_fit_json_parser.add_argument("task_id", help="Task identifier.")
    retry_policy_json_parser = task_subparsers.add_parser(
        "retry-policy-json",
        help="Print the task retry-policy record.",
    )
    retry_policy_json_parser.add_argument("task_id", help="Task identifier.")
    execution_budget_policy_json_parser = task_subparsers.add_parser(
        "execution-budget-policy-json",
        help="Print the task execution-budget-policy record.",
    )
    execution_budget_policy_json_parser.add_argument("task_id", help="Task identifier.")
    stop_policy_json_parser = task_subparsers.add_parser(
        "stop-policy-json",
        help="Print the task stop-policy record.",
    )
    stop_policy_json_parser.add_argument("task_id", help="Task identifier.")
    checkpoint_json_parser = task_subparsers.add_parser(
        "checkpoint-json",
        help="Print the task checkpoint snapshot record.",
    )
    checkpoint_json_parser.add_argument("task_id", help="Task identifier.")
    capabilities_json_parser = task_subparsers.add_parser(
        "capabilities-json",
        help="Print the task capability assembly record.",
    )
    capabilities_json_parser.add_argument("task_id", help="Task identifier.")
    semantics_json_parser = task_subparsers.add_parser("semantics-json", help="Print the task semantics record.")
    semantics_json_parser.add_argument("task_id", help="Task identifier.")
    knowledge_objects_json_parser = task_subparsers.add_parser(
        "knowledge-objects-json",
        help="Print the task knowledge-objects record.",
    )
    knowledge_objects_json_parser.add_argument("task_id", help="Task identifier.")
    knowledge_partition_json_parser = task_subparsers.add_parser(
        "knowledge-partition-json",
        help="Print the task knowledge-partition record.",
    )
    knowledge_partition_json_parser.add_argument("task_id", help="Task identifier.")
    knowledge_index_json_parser = task_subparsers.add_parser(
        "knowledge-index-json",
        help="Print the task knowledge-index record.",
    )
    knowledge_index_json_parser.add_argument("task_id", help="Task identifier.")
    knowledge_policy_json_parser = task_subparsers.add_parser(
        "knowledge-policy-json",
        help="Print the task knowledge-policy record.",
    )
    knowledge_policy_json_parser.add_argument("task_id", help="Task identifier.")
    retrieval_json_parser = task_subparsers.add_parser("retrieval-json", help="Print the task retrieval record.")
    retrieval_json_parser.add_argument("task_id", help="Task identifier.")

    doctor_subparsers.add_parser("codex", help="Run a minimal Codex executor preflight.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    base_dir = Path(args.base_dir).resolve()

    if args.command == "task" and args.task_command == "create":
        state = create_task(
            base_dir=base_dir,
            title=args.title.strip(),
            goal=args.goal.strip(),
            workspace_root=Path(args.workspace_root).resolve(),
            executor_name=args.executor.strip(),
            constraints=args.constraint,
            acceptance_criteria=args.acceptance_criterion,
            priority_hints=args.priority_hint,
            next_action_proposals=args.next_action_proposal,
            planning_source=args.planning_source,
            knowledge_items=args.knowledge_item,
            knowledge_stage=args.knowledge_stage,
            knowledge_source=args.knowledge_source,
            knowledge_artifact_refs=args.knowledge_artifact_ref,
            knowledge_retrieval_eligible=args.knowledge_retrieval_eligible,
            knowledge_canonicalization_intent=args.knowledge_canonicalization_intent,
            capability_refs=args.capability,
            route_mode=args.route_mode,
        )
        print(state.task_id)
        return 0

    if args.command == "task" and args.task_command == "planning-handoff":
        state = update_task_planning_handoff(
            base_dir=base_dir,
            task_id=args.task_id,
            constraints=args.constraint,
            acceptance_criteria=args.acceptance_criterion,
            priority_hints=args.priority_hint,
            next_action_proposals=args.next_action_proposal,
            planning_source=args.planning_source,
        )
        print(
            f"{state.task_id} planning_handoff_updated "
            f"constraints={len(state.task_semantics.get('constraints', []))} "
            f"next_actions={len(state.task_semantics.get('next_action_proposals', []))}"
        )
        return 0

    if args.command == "task" and args.task_command == "knowledge-capture":
        state = append_task_knowledge_capture(
            base_dir=base_dir,
            task_id=args.task_id,
            knowledge_items=args.knowledge_item,
            knowledge_stage=args.knowledge_stage,
            knowledge_source=args.knowledge_source,
            knowledge_artifact_refs=args.knowledge_artifact_ref,
            knowledge_retrieval_eligible=args.knowledge_retrieval_eligible,
            knowledge_canonicalization_intent=args.knowledge_canonicalization_intent,
        )
        print(f"{state.task_id} knowledge_capture_added added={len(args.knowledge_item)} total={len(state.knowledge_objects)}")
        return 0

    if args.command == "task" and args.task_command == "run":
        return execute_task_run(base_dir, args.task_id, args.executor, args.capability, args.route_mode)

    if args.command == "task" and args.task_command == "retry":
        state = load_state(base_dir, args.task_id)
        retry_policy = load_json_if_exists(retry_policy_path(base_dir, args.task_id))
        stop_policy = load_json_if_exists(stop_policy_path(base_dir, args.task_id))
        checkpoint_snapshot = load_checkpoint_snapshot(base_dir, state)
        if not (retry_policy.get("retryable", False) and stop_policy.get("checkpoint_kind", "") in {"retry_review", "detached_retry_review"}):
            print(
                f"{state.task_id} retry_blocked "
                f"retry_decision={retry_policy.get('retry_decision', 'pending')} "
                f"checkpoint_kind={stop_policy.get('checkpoint_kind', 'pending')} "
                f"suggested_path={checkpoint_snapshot.get('recommended_path', 'pending')}"
            )
            return 1
        return execute_task_run(base_dir, args.task_id, args.executor, args.capability, args.route_mode)

    if args.command == "task" and args.task_command == "resume":
        state = load_state(base_dir, args.task_id)
        checkpoint_snapshot = load_checkpoint_snapshot(base_dir, state)
        if not (checkpoint_snapshot.get("resume_ready", False) and checkpoint_snapshot.get("recommended_path", "") == "resume"):
            print(
                f"{state.task_id} resume_blocked "
                f"checkpoint_state={checkpoint_snapshot.get('checkpoint_state', 'pending')} "
                f"recommended_path={checkpoint_snapshot.get('recommended_path', 'pending')} "
                f"suggested_reason={checkpoint_snapshot.get('recommended_reason', 'pending')}"
            )
            return 1
        return execute_task_run(base_dir, args.task_id, args.executor, args.capability, args.route_mode)

    if args.command == "task" and args.task_command == "rerun":
        return execute_task_run(base_dir, args.task_id, args.executor, args.capability, args.route_mode)

    if args.command == "task" and args.task_command == "list":
        states = sorted(
            iter_task_states(base_dir),
            key=lambda state: (state.updated_at, state.task_id),
            reverse=True,
        )
        states = filter_task_states(states, args.focus)
        if args.limit is not None:
            states = states[: max(args.limit, 0)]
        print(f"task_id\tstatus\tphase\tattempt\tupdated_at\ttitle\tfocus={args.focus}")
        for state in states:
            attempt_label = state.current_attempt_id or "-"
            print(
                "\t".join(
                    [
                        state.task_id,
                        state.status,
                        state.phase,
                        attempt_label,
                        state.updated_at,
                        state.title,
                    ]
                )
            )
        return 0

    if args.command == "task" and args.task_command == "queue":
        states = sorted(
            iter_task_states(base_dir),
            key=lambda state: (state.updated_at, state.task_id),
            reverse=True,
        )
        queue_entries = [entry for state in states if (entry := build_task_queue_entry(base_dir, state)) is not None]
        if args.limit is not None:
            queue_entries = queue_entries[: max(args.limit, 0)]
        print("task_id\taction\tstatus\tattempt\tupdated_at\treason\tnext\ttitle")
        for entry in queue_entries:
            print(
                "\t".join(
                    [
                        entry["task_id"],
                        entry["action"],
                        entry["status"],
                        entry["attempt"],
                        entry["updated_at"],
                        entry["reason"],
                        entry["next"],
                        entry["title"],
                    ]
                )
            )
        return 0

    if args.command == "task" and args.task_command == "attempts":
        state = load_state(base_dir, args.task_id)
        attempts = build_attempt_summaries(base_dir, args.task_id)
        print("attempt_id\tattempt_number\tstatus\texecutor_status\texecution_lifecycle\tretrieval_count\thandoff_status\tstarted_at\tfinished_at")
        for attempt in attempts:
            print(
                "\t".join(
                    [
                        attempt["attempt_id"],
                        attempt["attempt_number"],
                        attempt["status"],
                        attempt["executor_status"],
                        attempt["execution_lifecycle"],
                        attempt["retrieval_count"],
                        attempt["handoff_status"],
                        attempt["started_at"],
                        attempt["finished_at"],
                    ]
                )
            )
        if not attempts and state.current_attempt_id:
            print(
                "\t".join(
                    [
                        state.current_attempt_id,
                        str(state.current_attempt_number or 0),
                        state.status,
                        state.executor_status,
                        state.execution_lifecycle,
                        str(state.retrieval_count),
                        "pending",
                        state.updated_at,
                        "-",
                    ]
                )
            )
        return 0

    if args.command == "task" and args.task_command == "compare-attempts":
        attempts = build_attempt_summaries(base_dir, args.task_id)
        left_attempt, right_attempt = resolve_attempt_pair(attempts, args.left, args.right)
        lines = [
            f"Task Attempt Compare: {args.task_id}",
            f"left_attempt: {left_attempt['attempt_id']}",
            f"right_attempt: {right_attempt['attempt_id']}",
            "",
            "Comparison",
            f"status: {left_attempt['status']} -> {right_attempt['status']}",
            f"executor_status: {left_attempt['executor_status']} -> {right_attempt['executor_status']}",
            f"execution_lifecycle: {left_attempt['execution_lifecycle']} -> {right_attempt['execution_lifecycle']}",
            f"retrieval_count: {left_attempt['retrieval_count']} -> {right_attempt['retrieval_count']}",
            f"handoff_status: {left_attempt['handoff_status']} -> {right_attempt['handoff_status']}",
            f"compatibility_status: {left_attempt['compatibility_status']} -> {right_attempt['compatibility_status']}",
            f"execution_fit_status: {left_attempt['execution_fit_status']} -> {right_attempt['execution_fit_status']}",
            f"retry_policy_status: {left_attempt['retry_policy_status']} -> {right_attempt['retry_policy_status']}",
            f"stop_policy_status: {left_attempt['stop_policy_status']} -> {right_attempt['stop_policy_status']}",
        ]
        print("\n".join(lines))
        return 0

    if args.command == "task" and args.task_command == "control":
        state = load_state(base_dir, args.task_id)
        print("\n".join(build_task_control_snapshot(base_dir, state)))
        return 0

    if args.command == "task" and args.task_command == "intake":
        print("\n".join(build_intake_snapshot(base_dir, args.task_id)))
        return 0

    if args.command == "task" and args.task_command == "inspect":
        state = load_state(base_dir, args.task_id)

        compatibility = load_json_if_exists(compatibility_path(base_dir, args.task_id))
        topology = load_json_if_exists(topology_path(base_dir, args.task_id))
        execution_site = load_json_if_exists(execution_site_path(base_dir, args.task_id))
        dispatch = load_json_if_exists(dispatch_path(base_dir, args.task_id))
        handoff = load_json_if_exists(handoff_path(base_dir, args.task_id))
        execution_fit = load_json_if_exists(execution_fit_path(base_dir, args.task_id))
        retry_policy = load_json_if_exists(retry_policy_path(base_dir, args.task_id))
        execution_budget_policy = load_json_if_exists(execution_budget_policy_path(base_dir, args.task_id))
        stop_policy = load_json_if_exists(stop_policy_path(base_dir, args.task_id))
        checkpoint_snapshot = load_checkpoint_snapshot(base_dir, state)
        knowledge_policy = load_json_if_exists(knowledge_policy_path(base_dir, args.task_id))
        knowledge_partition = load_json_if_exists(knowledge_partition_path(base_dir, args.task_id))
        knowledge_index = load_json_if_exists(knowledge_index_path(base_dir, args.task_id))
        retrieval = load_json_if_exists(retrieval_path(base_dir, args.task_id))
        task_semantics = load_json_if_exists(task_semantics_path(base_dir, args.task_id))
        knowledge_objects = load_json_if_exists(knowledge_objects_path(base_dir, args.task_id))
        if not isinstance(knowledge_objects, list):
            knowledge_objects = []
        if not isinstance(retrieval, list):
            retrieval = []
        knowledge_stage_counts = {"raw": 0, "candidate": 0, "verified": 0, "canonical": 0}
        knowledge_evidence_counts = {"artifact_backed": 0, "source_only": 0, "unbacked": 0}
        knowledge_reuse_counts = {"task_only": 0, "retrieval_candidate": 0}
        canonicalization_counts = summarize_canonicalization(knowledge_objects)
        reused_knowledge_references: list[str] = []
        for item in knowledge_objects:
            stage = str(item.get("stage", "raw"))
            knowledge_stage_counts[stage] = knowledge_stage_counts.get(stage, 0) + 1
            evidence_status = str(item.get("evidence_status", "unbacked"))
            knowledge_evidence_counts[evidence_status] = knowledge_evidence_counts.get(evidence_status, 0) + 1
            reuse_scope = str(item.get("knowledge_reuse_scope", "task_only"))
            knowledge_reuse_counts[reuse_scope] = knowledge_reuse_counts.get(reuse_scope, 0) + 1
        for item in retrieval:
            if str(item.get("source_type", "")) == "knowledge":
                reused_knowledge_references.append(str(item.get("citation", item.get("path", ""))))

        lines = [
            f"Task Overview: {state.task_id}",
            f"title: {state.title}",
            f"goal: {state.goal}",
            "",
            "State",
            f"status: {state.status}",
            f"phase: {state.phase}",
            f"updated_at: {state.updated_at}",
            f"attempt_id: {state.current_attempt_id or '-'}",
            f"attempt_number: {state.current_attempt_number or 0}",
            f"attempt_owner_kind: {state.current_attempt_owner_kind}",
            f"attempt_owner_ref: {state.current_attempt_owner_ref}",
            f"attempt_ownership_status: {state.current_attempt_ownership_status}",
            f"execution_lifecycle: {state.execution_lifecycle}",
            f"task_semantics_source_kind: {task_semantics.get('source_kind', state.task_semantics.get('source_kind', 'none') if state.task_semantics else 'none')}",
            f"task_semantics_source_ref: {task_semantics.get('source_ref', state.task_semantics.get('source_ref', '') if state.task_semantics else '') or '-'}",
            f"task_semantics_constraints: {len(task_semantics.get('constraints', state.task_semantics.get('constraints', []) if state.task_semantics else []))}",
            f"task_semantics_acceptance_criteria: {len(task_semantics.get('acceptance_criteria', state.task_semantics.get('acceptance_criteria', []) if state.task_semantics else []))}",
            f"knowledge_objects_count: {len(knowledge_objects)}",
            f"knowledge_object_stages: raw={knowledge_stage_counts.get('raw', 0)} candidate={knowledge_stage_counts.get('candidate', 0)} verified={knowledge_stage_counts.get('verified', 0)} canonical={knowledge_stage_counts.get('canonical', 0)}",
            f"knowledge_object_evidence: artifact_backed={knowledge_evidence_counts.get('artifact_backed', 0)} source_only={knowledge_evidence_counts.get('source_only', 0)} unbacked={knowledge_evidence_counts.get('unbacked', 0)}",
            f"knowledge_object_reuse: retrieval_candidate={knowledge_reuse_counts.get('retrieval_candidate', 0)} task_only={knowledge_reuse_counts.get('task_only', 0)}",
            f"knowledge_object_canonicalization: ready={canonicalization_counts.get('review_ready', 0) + canonicalization_counts.get('promotion_ready', 0)} blocked={canonicalization_counts.get('blocked_stage', 0) + canonicalization_counts.get('blocked_evidence', 0)} canonical={canonicalization_counts.get('canonical', 0)}",
            f"knowledge_partition: task_linked={knowledge_partition.get('task_linked_count', len(knowledge_objects))} reusable_candidate={knowledge_partition.get('reusable_candidate_count', 0)}",
            f"knowledge_index: active_reusable={knowledge_index.get('active_reusable_count', 0)} inactive_reusable={knowledge_index.get('inactive_reusable_count', 0)}",
            f"knowledge_index_refreshed_at: {knowledge_index.get('refreshed_at', '-')}",
            "",
            "Route And Topology",
            f"route_mode: {state.route_mode}",
            f"route_name: {state.route_name}",
            f"route_backend: {state.route_backend}",
            f"route_executor_family: {state.route_executor_family}",
            f"route_execution_site: {state.route_execution_site}",
            f"execution_site_contract_kind: {execution_site.get('contract_kind', state.execution_site_contract_kind)}",
            f"execution_site_boundary: {execution_site.get('boundary', state.execution_site_boundary)}",
            f"execution_site_contract_status: {execution_site.get('contract_status', state.execution_site_contract_status)}",
            f"execution_site_handoff_required: {'yes' if execution_site.get('handoff_required', state.execution_site_handoff_required) else 'no'}",
            f"topology_executor_family: {topology.get('executor_family', state.topology_executor_family)}",
            f"topology_execution_site: {topology.get('execution_site', state.topology_execution_site)}",
            f"topology_transport_kind: {topology.get('transport_kind', state.topology_transport_kind)}",
            f"topology_dispatch_status: {topology.get('dispatch_status', state.topology_dispatch_status)}",
            "",
            "Checks",
            f"compatibility_status: {compatibility.get('status', 'pending')}",
            f"execution_fit_status: {execution_fit.get('status', 'pending')}",
            f"knowledge_policy_status: {knowledge_policy.get('status', 'pending')}",
            f"validation_status: {load_json_if_exists(Path(state.artifact_paths.get('validation_json', ''))).get('status', 'pending') if state.artifact_paths.get('validation_json') else 'pending'}",
            "",
            *build_policy_snapshot(retry_policy, execution_budget_policy, stop_policy),
            "",
            "Retrieval And Memory",
            f"retrieval_count: {state.retrieval_count}",
            f"retrieval_record_available: {'yes' if isinstance(retrieval, list) and bool(retrieval) else 'no'}",
            f"reused_knowledge_in_retrieval: {len(reused_knowledge_references)}",
            f"reused_current_task_knowledge: {sum(1 for item in retrieval if str(item.get('metadata', {}).get('knowledge_task_relation', '')) == 'current_task') if isinstance(retrieval, list) else 0}",
            f"reused_cross_task_knowledge: {sum(1 for item in retrieval if str(item.get('metadata', {}).get('knowledge_task_relation', '')) == 'cross_task') if isinstance(retrieval, list) else 0}",
            f"reused_knowledge_references: {', '.join(reused_knowledge_references) or '-'}",
            f"grounding_available: {'yes' if state.artifact_paths.get('source_grounding') else 'no'}",
            f"memory_available: {'yes' if memory_path(base_dir, args.task_id).exists() else 'no'}",
            "",
            "Operator Guidance",
            f"handoff_status: {handoff.get('status', 'pending')}",
            f"handoff_contract_status: {handoff.get('contract_status', 'pending')}",
            f"handoff_contract_kind: {handoff.get('contract_kind', 'pending')}",
            f"checkpoint_state: {checkpoint_snapshot.get('checkpoint_state', 'pending')}",
            f"recovery_semantics: {checkpoint_snapshot.get('recovery_semantics', 'pending')}",
            f"interruption_kind: {checkpoint_snapshot.get('interruption_kind', 'none')}",
            f"recommended_path: {checkpoint_snapshot.get('recommended_path', 'pending')}",
            f"handoff_next_owner_kind: {handoff.get('next_owner_kind', 'pending')}",
            f"handoff_next_owner_ref: {handoff.get('next_owner_ref', 'pending')}",
            f"blocking_reason: {handoff.get('blocking_reason', '') or '-'}",
            f"next_operator_action: {handoff.get('next_operator_action', 'Inspect task artifacts.')}",
            "",
            "Artifacts",
            f"task_semantics_report: {state.artifact_paths.get('task_semantics_report', '-')}",
            f"knowledge_objects_report: {state.artifact_paths.get('knowledge_objects_report', '-')}",
            f"knowledge_partition_report: {state.artifact_paths.get('knowledge_partition_report', '-')}",
            f"knowledge_index_report: {state.artifact_paths.get('knowledge_index_report', '-')}",
            f"summary: {state.artifact_paths.get('summary', '-')}",
            f"resume_note: {state.artifact_paths.get('resume_note', '-')}",
            f"route_report: {state.artifact_paths.get('route_report', '-')}",
            f"topology_report: {state.artifact_paths.get('topology_report', '-')}",
            f"execution_site_report: {state.artifact_paths.get('execution_site_report', '-')}",
            f"dispatch_report: {state.artifact_paths.get('dispatch_report', '-')}",
            f"handoff_report: {state.artifact_paths.get('handoff_report', '-')}",
            f"retrieval_report: {state.artifact_paths.get('retrieval_report', '-')}",
            f"retry_policy_report: {state.artifact_paths.get('retry_policy_report', '-')}",
            f"execution_budget_policy_report: {state.artifact_paths.get('execution_budget_policy_report', '-')}",
            f"stop_policy_report: {state.artifact_paths.get('stop_policy_report', '-')}",
            f"checkpoint_snapshot_report: {state.artifact_paths.get('checkpoint_snapshot_report', '-')}",
            f"knowledge_policy_report: {state.artifact_paths.get('knowledge_policy_report', '-')}",
            f"validation_report: {state.artifact_paths.get('validation_report', '-')}",
        ]
        print("\n".join(lines))
        return 0

    if args.command == "task" and args.task_command == "capabilities":
        state = load_state(base_dir, args.task_id)
        manifest = json.loads(capability_manifest_path(base_dir, args.task_id).read_text(encoding="utf-8"))
        assembly = json.loads(capability_assembly_path(base_dir, args.task_id).read_text(encoding="utf-8"))
        lines = [
            f"Task Capabilities: {state.task_id}",
            "",
            "Requested Manifest",
            f"profile_refs: {', '.join(manifest.get('profile_refs', [])) or '-'}",
            f"workflow_refs: {', '.join(manifest.get('workflow_refs', [])) or '-'}",
            f"validator_refs: {', '.join(manifest.get('validator_refs', [])) or '-'}",
            f"skill_refs: {', '.join(manifest.get('skill_refs', [])) or '-'}",
            f"tool_refs: {', '.join(manifest.get('tool_refs', [])) or '-'}",
            "",
            "Effective Assembly",
            f"assembly_status: {assembly.get('assembly_status', 'pending')}",
            f"resolver: {assembly.get('resolver', 'unknown')}",
            f"effective_profiles: {', '.join(assembly.get('effective', {}).get('profile_refs', [])) or '-'}",
            f"effective_workflows: {', '.join(assembly.get('effective', {}).get('workflow_refs', [])) or '-'}",
            f"effective_validators: {', '.join(assembly.get('effective', {}).get('validator_refs', [])) or '-'}",
            f"notes: {'; '.join(assembly.get('notes', [])) or '-'}",
        ]
        print("\n".join(lines))
        return 0

    if args.command == "task" and args.task_command == "review":
        state = load_state(base_dir, args.task_id)

        handoff = load_json_if_exists(handoff_path(base_dir, args.task_id))
        compatibility = load_json_if_exists(compatibility_path(base_dir, args.task_id))
        execution_fit = load_json_if_exists(execution_fit_path(base_dir, args.task_id))
        retry_policy = load_json_if_exists(retry_policy_path(base_dir, args.task_id))
        execution_budget_policy = load_json_if_exists(execution_budget_policy_path(base_dir, args.task_id))
        stop_policy = load_json_if_exists(stop_policy_path(base_dir, args.task_id))
        checkpoint_snapshot = load_checkpoint_snapshot(base_dir, state)
        knowledge_policy = load_json_if_exists(knowledge_policy_path(base_dir, args.task_id))
        knowledge_index = load_json_if_exists(knowledge_index_path(base_dir, args.task_id))
        knowledge_objects = load_json_if_exists(knowledge_objects_path(base_dir, args.task_id))
        canonicalization_counts = summarize_canonicalization(knowledge_objects if isinstance(knowledge_objects, list) else [])
        retrieval = load_json_if_exists(retrieval_path(base_dir, args.task_id))
        reused_knowledge_references = []
        if isinstance(retrieval, list):
            for item in retrieval:
                if str(item.get("source_type", "")) == "knowledge":
                    reused_knowledge_references.append(str(item.get("citation", item.get("path", ""))))
        reused_current_task = (
            sum(1 for item in retrieval if str(item.get("metadata", {}).get("knowledge_task_relation", "")) == "current_task")
            if isinstance(retrieval, list)
            else 0
        )
        reused_cross_task = (
            sum(1 for item in retrieval if str(item.get("metadata", {}).get("knowledge_task_relation", "")) == "cross_task")
            if isinstance(retrieval, list)
            else 0
        )
        validation = load_json_if_exists(Path(state.artifact_paths.get("validation_json", ""))) if state.artifact_paths.get("validation_json") else {}
        lines = [
            f"Task Review: {state.task_id}",
            f"title: {state.title}",
            "",
            "Latest Attempt",
            f"attempt_id: {state.current_attempt_id or '-'}",
            f"attempt_number: {state.current_attempt_number or 0}",
            f"attempt_owner_kind: {state.current_attempt_owner_kind}",
            f"attempt_owner_ref: {state.current_attempt_owner_ref}",
            f"attempt_ownership_status: {state.current_attempt_ownership_status}",
            f"status: {state.status}",
            f"executor_status: {state.executor_status}",
            f"execution_lifecycle: {state.execution_lifecycle}",
            "",
            "Handoff",
            f"handoff_status: {handoff.get('status', 'pending')}",
            f"handoff_contract_status: {handoff.get('contract_status', 'pending')}",
            f"handoff_contract_kind: {handoff.get('contract_kind', 'pending')}",
            f"checkpoint_state: {checkpoint_snapshot.get('checkpoint_state', 'pending')}",
            f"recovery_semantics: {checkpoint_snapshot.get('recovery_semantics', 'pending')}",
            f"interruption_kind: {checkpoint_snapshot.get('interruption_kind', 'none')}",
            f"recommended_path: {checkpoint_snapshot.get('recommended_path', 'pending')}",
            f"handoff_next_owner_kind: {handoff.get('next_owner_kind', 'pending')}",
            f"handoff_next_owner_ref: {handoff.get('next_owner_ref', 'pending')}",
            f"blocking_reason: {handoff.get('blocking_reason', '') or '-'}",
            f"next_operator_action: {handoff.get('next_operator_action', 'Review resume_note.md and summary.md.')}",
            "",
            "Checks",
            f"compatibility_status: {compatibility.get('status', 'pending')}",
            f"execution_fit_status: {execution_fit.get('status', 'pending')}",
            f"knowledge_policy_status: {knowledge_policy.get('status', 'pending')}",
            f"knowledge_canonicalization_ready: {canonicalization_counts.get('review_ready', 0) + canonicalization_counts.get('promotion_ready', 0)}",
            f"knowledge_canonicalization_blocked: {canonicalization_counts.get('blocked_stage', 0) + canonicalization_counts.get('blocked_evidence', 0)}",
            f"knowledge_canonicalization_canonical: {canonicalization_counts.get('canonical', 0)}",
            f"validation_status: {validation.get('status', 'pending')}",
            f"knowledge_index_active_reusable: {knowledge_index.get('active_reusable_count', 0)}",
            f"knowledge_index_inactive_reusable: {knowledge_index.get('inactive_reusable_count', 0)}",
            f"knowledge_index_refreshed_at: {knowledge_index.get('refreshed_at', '-')}",
            f"reused_knowledge_in_retrieval: {len(reused_knowledge_references)}",
            f"reused_current_task_knowledge: {reused_current_task}",
            f"reused_cross_task_knowledge: {reused_cross_task}",
            f"reused_knowledge_references: {', '.join(reused_knowledge_references) or '-'}",
            "",
            *build_policy_snapshot(retry_policy, execution_budget_policy, stop_policy),
            "",
            "Review Artifacts",
            f"task_semantics_report: {state.artifact_paths.get('task_semantics_report', '-')}",
            f"knowledge_objects_report: {state.artifact_paths.get('knowledge_objects_report', '-')}",
            f"knowledge_partition_report: {state.artifact_paths.get('knowledge_partition_report', '-')}",
            f"knowledge_index_report: {state.artifact_paths.get('knowledge_index_report', '-')}",
            f"retrieval_report: {state.artifact_paths.get('retrieval_report', '-')}",
            f"source_grounding: {state.artifact_paths.get('source_grounding', '-')}",
            f"resume_note: {state.artifact_paths.get('resume_note', '-')}",
            f"summary: {state.artifact_paths.get('summary', '-')}",
            f"handoff_report: {state.artifact_paths.get('handoff_report', '-')}",
            f"validation_report: {state.artifact_paths.get('validation_report', '-')}",
            f"compatibility_report: {state.artifact_paths.get('compatibility_report', '-')}",
            f"execution_fit_report: {state.artifact_paths.get('execution_fit_report', '-')}",
            f"retry_policy_report: {state.artifact_paths.get('retry_policy_report', '-')}",
            f"execution_budget_policy_report: {state.artifact_paths.get('execution_budget_policy_report', '-')}",
            f"stop_policy_report: {state.artifact_paths.get('stop_policy_report', '-')}",
            f"checkpoint_snapshot_report: {state.artifact_paths.get('checkpoint_snapshot_report', '-')}",
            f"knowledge_policy_report: {state.artifact_paths.get('knowledge_policy_report', '-')}",
        ]
        print("\n".join(lines))
        return 0

    if args.command == "task" and args.task_command == "checkpoint":
        print((artifacts_dir(base_dir, args.task_id) / "checkpoint_snapshot_report.md").read_text(encoding="utf-8"), end="")
        return 0

    if args.command == "task" and args.task_command == "policy":
        state = load_state(base_dir, args.task_id)

        retry_policy = load_json_if_exists(retry_policy_path(base_dir, args.task_id))
        execution_budget_policy = load_json_if_exists(execution_budget_policy_path(base_dir, args.task_id))
        stop_policy = load_json_if_exists(stop_policy_path(base_dir, args.task_id))
        lines = [f"Task Policy: {state.task_id}", f"title: {state.title}", ""]
        lines.extend(build_policy_snapshot(retry_policy, execution_budget_policy, stop_policy))
        lines.extend(
            [
                "",
                "Policy Artifacts",
                f"retry_policy_report: {state.artifact_paths.get('retry_policy_report', '-')}",
                f"execution_budget_policy_report: {state.artifact_paths.get('execution_budget_policy_report', '-')}",
                f"stop_policy_report: {state.artifact_paths.get('stop_policy_report', '-')}",
            ]
        )
        print("\n".join(lines))
        return 0

    if args.command == "task" and args.task_command == "artifacts":
        state = load_state(base_dir, args.task_id)
        print(build_grouped_artifact_index(state.artifact_paths), end="")
        return 0

    if args.command == "task" and args.task_command in {
        "summarize",
        "semantics",
        "resume-note",
        "validation",
        "compatibility",
        "grounding",
        "knowledge-objects",
        "knowledge-partition",
        "knowledge-index",
        "knowledge-policy",
        "retrieval",
        "topology",
        "execution-site",
        "dispatch",
        "handoff",
        "execution-fit",
        "retry-policy",
        "execution-budget-policy",
        "stop-policy",
        "route",
    }:
        artifact_name = {
            "summarize": "summary.md",
            "semantics": "task_semantics_report.md",
            "resume-note": "resume_note.md",
            "validation": "validation_report.md",
            "compatibility": "compatibility_report.md",
            "grounding": "source_grounding.md",
            "knowledge-objects": "knowledge_objects_report.md",
            "knowledge-partition": "knowledge_partition_report.md",
            "knowledge-index": "knowledge_index_report.md",
            "knowledge-policy": "knowledge_policy_report.md",
            "retrieval": "retrieval_report.md",
            "topology": "topology_report.md",
            "execution-site": "execution_site_report.md",
            "dispatch": "dispatch_report.md",
            "handoff": "handoff_report.md",
            "execution-fit": "execution_fit_report.md",
            "retry-policy": "retry_policy_report.md",
            "execution-budget-policy": "execution_budget_policy_report.md",
            "stop-policy": "stop_policy_report.md",
            "route": "route_report.md",
        }[args.task_command]
        print((artifacts_dir(base_dir, args.task_id) / artifact_name).read_text(encoding="utf-8"), end="")
        return 0

    if args.command == "task" and args.task_command == "memory":
        print(json.dumps(json.loads(memory_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "compatibility-json":
        print(json.dumps(json.loads(compatibility_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "route-json":
        print(json.dumps(json.loads(route_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "topology-json":
        print(json.dumps(json.loads(topology_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "execution-site-json":
        print(json.dumps(json.loads(execution_site_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "dispatch-json":
        print(json.dumps(json.loads(dispatch_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "handoff-json":
        print(json.dumps(json.loads(handoff_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "execution-fit-json":
        print(json.dumps(json.loads(execution_fit_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "retry-policy-json":
        print(json.dumps(json.loads(retry_policy_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "execution-budget-policy-json":
        print(
            json.dumps(
                json.loads(execution_budget_policy_path(base_dir, args.task_id).read_text(encoding="utf-8")),
                indent=2,
            )
        )
        return 0

    if args.command == "task" and args.task_command == "stop-policy-json":
        print(json.dumps(json.loads(stop_policy_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "checkpoint-json":
        print(json.dumps(json.loads(checkpoint_snapshot_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "capabilities-json":
        print(json.dumps(json.loads(capability_assembly_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "semantics-json":
        print(json.dumps(json.loads(task_semantics_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "knowledge-objects-json":
        print(json.dumps(json.loads(knowledge_objects_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "knowledge-partition-json":
        print(json.dumps(json.loads(knowledge_partition_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "knowledge-index-json":
        print(json.dumps(json.loads(knowledge_index_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "knowledge-policy-json":
        print(json.dumps(json.loads(knowledge_policy_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "retrieval-json":
        print(json.dumps(json.loads(retrieval_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "doctor" and args.doctor_command == "codex":
        exit_code, result = diagnose_codex()
        print(format_codex_doctor_result(result))
        return exit_code

    parser.error("Unsupported command.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
