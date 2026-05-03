from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from swallow._io_helpers import read_json_or_empty
from swallow.knowledge_retrieval.knowledge_store import OPERATOR_CANONICAL_WRITE_AUTHORITY
from swallow.orchestration.checkpoint_snapshot import evaluate_checkpoint_snapshot
from swallow.orchestration.models import TaskState
from swallow.orchestration.orchestrator import (
    acknowledge_task,
    append_task_knowledge_capture,
    create_task,
    decide_task_knowledge,
    evaluate_task_canonical_reuse,
    run_task,
    update_task_planning_handoff,
)
from swallow.surface_tools.consistency_audit import ConsistencyAuditResult, run_consistency_audit
from swallow.surface_tools.paths import (
    checkpoint_snapshot_path,
    execution_budget_policy_path,
    handoff_path,
    retry_policy_path,
    stop_policy_path,
)
from swallow.truth_governance.store import load_state


@dataclass(frozen=True)
class TaskRunCommandResult:
    state: TaskState


@dataclass(frozen=True)
class TaskAcknowledgeCommandResult:
    state: TaskState
    blocked_reason: str = ""

    @property
    def blocked(self) -> bool:
        return bool(self.blocked_reason)


@dataclass(frozen=True)
class TaskRecoveryCommandResult:
    state: TaskState
    run_state: TaskState | None = None
    blocked_kind: str = ""
    retry_policy: dict[str, object] | None = None
    stop_policy: dict[str, object] | None = None
    checkpoint_snapshot: dict[str, object] | None = None

    @property
    def blocked(self) -> bool:
        return bool(self.blocked_kind)


def create_task_command(
    *,
    base_dir: Path,
    title: str,
    goal: str,
    workspace_root: Path,
    executor_name: str,
    input_context: dict[str, object] | None = None,
    constraints: list[str] | None = None,
    acceptance_criteria: list[str] | None = None,
    priority_hints: list[str] | None = None,
    next_action_proposals: list[str] | None = None,
    planning_source: str = "cli",
    complexity_hint: str = "",
    knowledge_items: list[str] | None = None,
    knowledge_stage: str = "raw",
    knowledge_source: str = "operator",
    knowledge_artifact_refs: list[str] | None = None,
    knowledge_retrieval_eligible: bool = False,
    knowledge_canonicalization_intent: str = "none",
    capability_refs: list[str] | None = None,
    route_mode: str | None = None,
) -> TaskState:
    return create_task(
        base_dir=base_dir,
        title=title,
        goal=goal,
        workspace_root=workspace_root,
        executor_name=executor_name,
        input_context=input_context or {},
        constraints=constraints or [],
        acceptance_criteria=acceptance_criteria or [],
        priority_hints=priority_hints or [],
        next_action_proposals=next_action_proposals or [],
        planning_source=planning_source,
        complexity_hint=complexity_hint,
        knowledge_items=knowledge_items or [],
        knowledge_stage=knowledge_stage,
        knowledge_source=knowledge_source,
        knowledge_artifact_refs=knowledge_artifact_refs or [],
        knowledge_retrieval_eligible=knowledge_retrieval_eligible,
        knowledge_canonicalization_intent=knowledge_canonicalization_intent,
        capability_refs=capability_refs or [],
        route_mode=route_mode,
    )


def update_planning_handoff_command(
    base_dir: Path,
    task_id: str,
    *,
    constraints: list[str] | None = None,
    acceptance_criteria: list[str] | None = None,
    priority_hints: list[str] | None = None,
    next_action_proposals: list[str] | None = None,
    planning_source: str = "cli",
    complexity_hint: str = "",
) -> TaskState:
    return update_task_planning_handoff(
        base_dir=base_dir,
        task_id=task_id,
        constraints=constraints or [],
        acceptance_criteria=acceptance_criteria or [],
        priority_hints=priority_hints or [],
        next_action_proposals=next_action_proposals or [],
        planning_source=planning_source,
        complexity_hint=complexity_hint,
    )


def append_task_knowledge_capture_command(
    base_dir: Path,
    task_id: str,
    *,
    knowledge_items: list[str] | None = None,
    knowledge_stage: str = "raw",
    knowledge_source: str = "operator",
    knowledge_artifact_refs: list[str] | None = None,
    knowledge_retrieval_eligible: bool = False,
    knowledge_canonicalization_intent: str = "none",
) -> TaskState:
    return append_task_knowledge_capture(
        base_dir=base_dir,
        task_id=task_id,
        knowledge_items=knowledge_items or [],
        knowledge_stage=knowledge_stage,
        knowledge_source=knowledge_source,
        knowledge_artifact_refs=knowledge_artifact_refs or [],
        knowledge_retrieval_eligible=knowledge_retrieval_eligible,
        knowledge_canonicalization_intent=knowledge_canonicalization_intent,
    )


def decide_task_knowledge_command(
    base_dir: Path,
    task_id: str,
    *,
    object_id: str,
    decision_type: str,
    decision_target: str,
    note: str,
) -> TaskState:
    caller_authority = OPERATOR_CANONICAL_WRITE_AUTHORITY if decision_target == "canonical" else "task-state"
    if decision_type == "promote":
        return decide_task_knowledge(
            base_dir,
            task_id,
            object_id=object_id,
            decision_type=decision_type,
            decision_target=decision_target,
            caller_authority=caller_authority,
            note=note,
        )
    return decide_task_knowledge(
        base_dir,
        task_id,
        object_id=object_id,
        decision_type=decision_type,
        decision_target=decision_target,
        note=note,
    )


def run_task_command(
    *,
    base_dir: Path,
    task_id: str,
    executor_name: str | None,
    capability_refs: list[str] | None,
    route_mode: str | None,
    reset_grounding: bool = False,
    skip_to_phase: str = "retrieval",
) -> TaskRunCommandResult:
    state = run_task(
        base_dir=base_dir,
        task_id=task_id,
        executor_name=executor_name,
        capability_refs=capability_refs,
        route_mode=route_mode,
        reset_grounding=reset_grounding,
        skip_to_phase=skip_to_phase,
    )
    return TaskRunCommandResult(state=state)


def acknowledge_task_command(base_dir: Path, task_id: str) -> TaskAcknowledgeCommandResult:
    try:
        state = acknowledge_task(base_dir, task_id)
    except ValueError as exc:
        state = load_state(base_dir, task_id)
        return TaskAcknowledgeCommandResult(state=state, blocked_reason=str(exc))
    return TaskAcknowledgeCommandResult(state=state)


def retry_task_command(
    *,
    base_dir: Path,
    task_id: str,
    executor_name: str | None,
    capability_refs: list[str] | None,
    route_mode: str | None,
    from_phase: str = "retrieval",
) -> TaskRecoveryCommandResult:
    state = load_state(base_dir, task_id)
    if is_acknowledged_dispatch_reentry(state):
        run_result = run_task_command(
            base_dir=base_dir,
            task_id=task_id,
            executor_name=executor_name,
            capability_refs=capability_refs,
            route_mode=route_mode,
            skip_to_phase=from_phase,
        )
        return TaskRecoveryCommandResult(state=state, run_state=run_result.state)
    retry_policy = read_json_or_empty(retry_policy_path(base_dir, task_id))
    stop_policy = read_json_or_empty(stop_policy_path(base_dir, task_id))
    checkpoint_snapshot = load_checkpoint_snapshot(base_dir, state)
    if not (
        retry_policy.get("retryable", False)
        and stop_policy.get("checkpoint_kind", "") in {"retry_review", "detached_retry_review"}
    ):
        return TaskRecoveryCommandResult(
            state=state,
            blocked_kind="retry",
            retry_policy=retry_policy,
            stop_policy=stop_policy,
            checkpoint_snapshot=checkpoint_snapshot,
        )
    run_result = run_task_command(
        base_dir=base_dir,
        task_id=task_id,
        executor_name=executor_name,
        capability_refs=capability_refs,
        route_mode=route_mode,
        reset_grounding=True,
        skip_to_phase=from_phase,
    )
    return TaskRecoveryCommandResult(state=state, run_state=run_result.state)


def resume_task_command(
    *,
    base_dir: Path,
    task_id: str,
    executor_name: str | None,
    capability_refs: list[str] | None,
    route_mode: str | None,
) -> TaskRecoveryCommandResult:
    state = load_state(base_dir, task_id)
    if is_acknowledged_dispatch_reentry(state):
        run_result = run_task_command(
            base_dir=base_dir,
            task_id=task_id,
            executor_name=executor_name,
            capability_refs=capability_refs,
            route_mode=route_mode,
        )
        return TaskRecoveryCommandResult(state=state, run_state=run_result.state)
    checkpoint_snapshot = load_checkpoint_snapshot(base_dir, state)
    if not (checkpoint_snapshot.get("resume_ready", False) and checkpoint_snapshot.get("recommended_path", "") == "resume"):
        return TaskRecoveryCommandResult(
            state=state,
            blocked_kind="resume",
            checkpoint_snapshot=checkpoint_snapshot,
        )
    run_result = run_task_command(
        base_dir=base_dir,
        task_id=task_id,
        executor_name=executor_name,
        capability_refs=capability_refs,
        route_mode=route_mode,
    )
    return TaskRecoveryCommandResult(state=state, run_state=run_result.state)


def rerun_task_command(
    *,
    base_dir: Path,
    task_id: str,
    executor_name: str | None,
    capability_refs: list[str] | None,
    route_mode: str | None,
    from_phase: str = "retrieval",
) -> TaskRunCommandResult:
    return run_task_command(
        base_dir=base_dir,
        task_id=task_id,
        executor_name=executor_name,
        capability_refs=capability_refs,
        route_mode=route_mode,
        reset_grounding=True,
        skip_to_phase=from_phase,
    )


def evaluate_task_canonical_reuse_command(
    base_dir: Path,
    task_id: str,
    *,
    citations: list[str],
    judgment: str,
    note: str,
) -> dict[str, object]:
    return evaluate_task_canonical_reuse(
        base_dir=base_dir,
        task_id=task_id,
        citations=citations,
        judgment=judgment,
        note=note,
    )


def run_task_consistency_audit_command(
    base_dir: Path,
    task_id: str,
    *,
    auditor_route: str,
    sample_artifact_path: str,
) -> ConsistencyAuditResult:
    return run_consistency_audit(
        base_dir,
        task_id,
        auditor_route=auditor_route,
        sample_artifact_path=sample_artifact_path,
    )


def is_acknowledged_dispatch_reentry(state: object) -> bool:
    return (
        getattr(state, "status", "") == "running"
        and getattr(state, "phase", "") == "retrieval"
        and getattr(state, "topology_dispatch_status", "") == "acknowledged"
    )


def load_checkpoint_snapshot(base_dir: Path, state: object) -> dict[str, object]:
    checkpoint_snapshot = read_json_or_empty(checkpoint_snapshot_path(base_dir, state.task_id))
    if checkpoint_snapshot:
        return checkpoint_snapshot
    handoff = read_json_or_empty(handoff_path(base_dir, state.task_id))
    retry_policy = read_json_or_empty(retry_policy_path(base_dir, state.task_id))
    stop_policy = read_json_or_empty(stop_policy_path(base_dir, state.task_id))
    execution_budget_policy = read_json_or_empty(execution_budget_policy_path(base_dir, state.task_id))
    return evaluate_checkpoint_snapshot(state, handoff, retry_policy, stop_policy, execution_budget_policy).to_dict()
