from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from .capabilities import build_capability_assembly, parse_capability_refs, validate_capability_manifest
from .executor import normalize_executor_name
from .harness import run_execution, run_retrieval, write_task_artifacts
from .knowledge_objects import (
    build_knowledge_objects,
    canonicalization_status_for,
    summarize_canonicalization,
    summarize_knowledge_evidence,
    summarize_knowledge_reuse,
    summarize_knowledge_stages,
)
from .knowledge_index import build_knowledge_index, build_knowledge_index_report
from .knowledge_partition import build_knowledge_partition, build_knowledge_partition_report
from .models import Event, RetrievalRequest, TaskState
from .paths import (
    artifacts_dir,
    capability_assembly_path,
    capability_manifest_path,
    checkpoint_snapshot_path,
    compatibility_path,
    dispatch_path,
    execution_site_path,
    execution_fit_path,
    execution_budget_policy_path,
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
    validation_path,
)
from .retrieval import build_retrieval_request
from .router import normalize_route_mode, select_route
from .store import (
    append_event,
    load_state,
    save_capability_assembly,
    save_capability_manifest,
    save_knowledge_index,
    save_knowledge_objects,
    save_knowledge_partition,
    save_state,
    save_task_semantics,
    write_artifact,
)
from .task_semantics import build_task_semantics
from .models import utc_now


def _apply_execution_topology(
    state: TaskState,
    *,
    dispatch_status: str,
) -> None:
    state.topology_route_name = state.route_name
    state.topology_executor_family = state.route_executor_family
    state.topology_execution_site = state.route_execution_site
    state.topology_transport_kind = state.route_transport_kind
    state.topology_remote_capable_intent = state.route_remote_capable
    state.topology_dispatch_status = dispatch_status


def _apply_execution_site_contract(state: TaskState) -> None:
    if state.topology_execution_site == "local" and state.topology_transport_kind == "local_process":
        state.execution_site_contract_kind = "local_inline"
        state.execution_site_boundary = "same_process"
        state.execution_site_contract_status = "active"
        state.execution_site_handoff_required = False
        state.execution_site_contract_reason = "Current route executes inline on the local machine."
        return

    if state.topology_execution_site == "local" and state.topology_transport_kind == "local_detached_process":
        state.execution_site_contract_kind = "local_detached"
        state.execution_site_boundary = "same_machine_detached"
        state.execution_site_contract_status = "active"
        state.execution_site_handoff_required = False
        state.execution_site_contract_reason = "Current route executes through a detached child process on the local machine."
        return

    if state.topology_execution_site == "local":
        state.execution_site_contract_kind = "local_detached"
        state.execution_site_boundary = "same_machine_detached"
        state.execution_site_contract_status = "planned"
        state.execution_site_handoff_required = False
        state.execution_site_contract_reason = (
            "Execution remains local but expects a detached runtime boundary instead of the inline baseline."
        )
        return

    state.execution_site_contract_kind = "remote_candidate"
    state.execution_site_boundary = "cross_site_candidate"
    state.execution_site_contract_status = "planned"
    state.execution_site_handoff_required = True
    state.execution_site_contract_reason = (
        "Execution site is outside the current local inline baseline and would require an explicit handoff boundary."
    )


def _begin_execution_attempt(state: TaskState) -> None:
    state.run_attempt_count += 1
    state.current_attempt_number = state.run_attempt_count
    state.current_attempt_id = f"attempt-{state.current_attempt_number:04d}"
    state.current_attempt_owner_kind = "local_orchestrator"
    state.current_attempt_owner_ref = "swl_cli"
    state.current_attempt_ownership_status = "owned"
    state.current_attempt_owner_assigned_at = utc_now()
    state.current_attempt_transfer_reason = ""
    state.dispatch_requested_at = utc_now()
    state.dispatch_started_at = ""
    state.execution_lifecycle = "prepared"


def create_task(
    base_dir: Path,
    title: str,
    goal: str,
    workspace_root: Path,
    executor_name: str = "codex",
    constraints: list[str] | None = None,
    acceptance_criteria: list[str] | None = None,
    priority_hints: list[str] | None = None,
    next_action_proposals: list[str] | None = None,
    planning_source: str | None = None,
    knowledge_items: list[str] | None = None,
    knowledge_stage: str = "raw",
    knowledge_source: str | None = None,
    knowledge_artifact_refs: list[str] | None = None,
    knowledge_retrieval_eligible: bool = False,
    knowledge_canonicalization_intent: str = "none",
    capability_refs: list[str] | None = None,
    route_mode: str = "auto",
) -> TaskState:
    task_id = uuid4().hex[:12]
    capability_manifest = parse_capability_refs(capability_refs)
    capability_errors = validate_capability_manifest(capability_manifest)
    if capability_errors:
        raise ValueError("; ".join(capability_errors))
    capability_assembly = build_capability_assembly(capability_manifest)
    task_semantics = build_task_semantics(
        title=title,
        goal=goal,
        constraints=constraints,
        acceptance_criteria=acceptance_criteria,
        priority_hints=priority_hints,
        next_action_proposals=next_action_proposals,
        planning_source=planning_source,
    )
    knowledge_objects = build_knowledge_objects(
        items=knowledge_items,
        stage=knowledge_stage,
        source_ref=knowledge_source,
        artifact_refs=knowledge_artifact_refs,
        retrieval_eligible=knowledge_retrieval_eligible,
        canonicalization_intent=knowledge_canonicalization_intent,
    )
    state = TaskState(
        task_id=task_id,
        title=title,
        goal=goal,
        workspace_root=str(workspace_root.resolve()),
        executor_name=normalize_executor_name(executor_name),
        task_semantics=task_semantics.to_dict(),
        knowledge_objects=[item.to_dict() for item in knowledge_objects],
        capability_manifest=capability_manifest.to_dict(),
        capability_assembly=capability_assembly.to_dict(),
        route_mode=normalize_route_mode(route_mode),
    )
    initial_route = select_route(state, route_mode_override=state.route_mode)
    state.route_name = initial_route.route.name
    state.route_backend = initial_route.route.backend_kind
    state.route_executor_family = initial_route.route.executor_family
    state.route_execution_site = initial_route.route.execution_site
    state.route_remote_capable = initial_route.route.remote_capable
    state.route_transport_kind = initial_route.route.transport_kind
    state.route_model_hint = initial_route.route.model_hint
    state.route_reason = initial_route.reason
    state.route_capabilities = initial_route.route.capabilities.to_dict()
    _apply_execution_topology(state, dispatch_status="not_requested")
    _apply_execution_site_contract(state)
    state.artifact_paths = {
        "task_semantics_json": str(task_semantics_path(base_dir, task_id).resolve()),
        "task_semantics_report": str((artifacts_dir(base_dir, task_id) / "task_semantics_report.md").resolve()),
        "knowledge_objects_json": str(knowledge_objects_path(base_dir, task_id).resolve()),
        "knowledge_objects_report": str((artifacts_dir(base_dir, task_id) / "knowledge_objects_report.md").resolve()),
        "knowledge_partition_json": str(knowledge_partition_path(base_dir, task_id).resolve()),
        "knowledge_partition_report": str((artifacts_dir(base_dir, task_id) / "knowledge_partition_report.md").resolve()),
        "knowledge_index_json": str(knowledge_index_path(base_dir, task_id).resolve()),
        "knowledge_index_report": str((artifacts_dir(base_dir, task_id) / "knowledge_index_report.md").resolve()),
        "checkpoint_snapshot_json": str(checkpoint_snapshot_path(base_dir, task_id).resolve()),
        "checkpoint_snapshot_report": str((artifacts_dir(base_dir, task_id) / "checkpoint_snapshot_report.md").resolve()),
    }
    knowledge_partition = build_knowledge_partition(state.knowledge_objects)
    knowledge_index = build_knowledge_index(state.knowledge_objects)
    save_state(base_dir, state)
    save_task_semantics(base_dir, task_id, state.task_semantics)
    save_knowledge_objects(base_dir, task_id, state.knowledge_objects)
    save_knowledge_partition(base_dir, task_id, knowledge_partition)
    save_knowledge_index(base_dir, task_id, knowledge_index)
    save_capability_manifest(base_dir, task_id, state.capability_manifest)
    save_capability_assembly(base_dir, task_id, state.capability_assembly)
    write_artifact(base_dir, task_id, "task_semantics_report.md", build_task_semantics_report(state))
    write_artifact(base_dir, task_id, "knowledge_objects_report.md", build_knowledge_objects_report(state))
    write_artifact(base_dir, task_id, "knowledge_partition_report.md", build_knowledge_partition_report(knowledge_partition))
    write_artifact(base_dir, task_id, "knowledge_index_report.md", build_knowledge_index_report(knowledge_index))
    append_event(
        base_dir,
        Event(
            task_id=task_id,
            event_type="task.created",
            message="Task created.",
            payload={
                "status": state.status,
                "phase": state.phase,
                "workspace_root": state.workspace_root,
                "executor_name": state.executor_name,
                "task_semantics": state.task_semantics,
                "knowledge_objects_count": len(state.knowledge_objects),
                "knowledge_stage_counts": summarize_knowledge_stages(state.knowledge_objects),
                "knowledge_evidence_counts": summarize_knowledge_evidence(state.knowledge_objects),
                "knowledge_reuse_counts": summarize_knowledge_reuse(state.knowledge_objects),
                "knowledge_canonicalization_counts": summarize_canonicalization(state.knowledge_objects),
                "knowledge_partition": {
                    "task_linked_count": knowledge_partition["task_linked_count"],
                    "reusable_candidate_count": knowledge_partition["reusable_candidate_count"],
                },
                "knowledge_index": {
                    "active_reusable_count": knowledge_index["active_reusable_count"],
                    "inactive_reusable_count": knowledge_index["inactive_reusable_count"],
                    "refreshed_at": knowledge_index["refreshed_at"],
                },
                "capability_manifest": state.capability_manifest,
                "capability_assembly": state.capability_assembly,
                "route_mode": state.route_mode,
                "route_name": state.route_name,
                "route_backend": state.route_backend,
                "route_executor_family": state.route_executor_family,
                "route_execution_site": state.route_execution_site,
                "route_remote_capable": state.route_remote_capable,
                "route_transport_kind": state.route_transport_kind,
                "topology_route_name": state.topology_route_name,
                "topology_executor_family": state.topology_executor_family,
                "topology_execution_site": state.topology_execution_site,
                "topology_transport_kind": state.topology_transport_kind,
                "topology_remote_capable_intent": state.topology_remote_capable_intent,
                "topology_dispatch_status": state.topology_dispatch_status,
                "execution_site_contract_kind": state.execution_site_contract_kind,
                "execution_site_boundary": state.execution_site_boundary,
                "execution_site_contract_status": state.execution_site_contract_status,
                "execution_site_handoff_required": state.execution_site_handoff_required,
                "execution_site_contract_reason": state.execution_site_contract_reason,
                "execution_lifecycle": state.execution_lifecycle,
            },
        ),
    )
    return state


def _merge_unique_items(existing: list[str] | None, incoming: list[str] | None) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for item in (existing or []) + (incoming or []):
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(normalized)
    return merged


def update_task_planning_handoff(
    base_dir: Path,
    task_id: str,
    *,
    constraints: list[str] | None = None,
    acceptance_criteria: list[str] | None = None,
    priority_hints: list[str] | None = None,
    next_action_proposals: list[str] | None = None,
    planning_source: str | None = None,
) -> TaskState:
    state = load_state(base_dir, task_id)
    current_semantics = state.task_semantics or {}
    effective_planning_source = (planning_source or str(current_semantics.get("source_ref", ""))).strip()
    merged_semantics = build_task_semantics(
        title=state.title,
        goal=state.goal,
        constraints=_merge_unique_items(list(current_semantics.get("constraints", [])), constraints),
        acceptance_criteria=_merge_unique_items(
            list(current_semantics.get("acceptance_criteria", [])), acceptance_criteria
        ),
        priority_hints=_merge_unique_items(list(current_semantics.get("priority_hints", [])), priority_hints),
        next_action_proposals=_merge_unique_items(
            list(current_semantics.get("next_action_proposals", [])), next_action_proposals
        ),
        planning_source=effective_planning_source or None,
    )
    state.task_semantics = merged_semantics.to_dict()
    save_state(base_dir, state)
    save_task_semantics(base_dir, task_id, state.task_semantics)
    write_artifact(base_dir, task_id, "task_semantics_report.md", build_task_semantics_report(state))
    append_event(
        base_dir,
        Event(
            task_id=task_id,
            event_type="task.planning_handoff_added",
            message="Planning handoff updated.",
            payload={
                "task_semantics": state.task_semantics,
                "constraints_count": len(state.task_semantics.get("constraints", [])),
                "acceptance_criteria_count": len(state.task_semantics.get("acceptance_criteria", [])),
                "priority_hints_count": len(state.task_semantics.get("priority_hints", [])),
                "next_action_proposals_count": len(state.task_semantics.get("next_action_proposals", [])),
            },
        ),
    )
    return state


def append_task_knowledge_capture(
    base_dir: Path,
    task_id: str,
    *,
    knowledge_items: list[str] | None = None,
    knowledge_stage: str = "raw",
    knowledge_source: str | None = None,
    knowledge_artifact_refs: list[str] | None = None,
    knowledge_retrieval_eligible: bool = False,
    knowledge_canonicalization_intent: str = "none",
) -> TaskState:
    state = load_state(base_dir, task_id)
    existing_objects = list(state.knowledge_objects or [])
    new_objects = build_knowledge_objects(
        items=knowledge_items,
        stage=knowledge_stage,
        source_ref=knowledge_source,
        artifact_refs=knowledge_artifact_refs,
        retrieval_eligible=knowledge_retrieval_eligible,
        canonicalization_intent=knowledge_canonicalization_intent,
        starting_index=len(existing_objects) + 1,
    )
    state.knowledge_objects = existing_objects + [item.to_dict() for item in new_objects]
    knowledge_partition = build_knowledge_partition(state.knowledge_objects)
    knowledge_index = build_knowledge_index(state.knowledge_objects)
    save_state(base_dir, state)
    save_knowledge_objects(base_dir, task_id, state.knowledge_objects)
    save_knowledge_partition(base_dir, task_id, knowledge_partition)
    save_knowledge_index(base_dir, task_id, knowledge_index)
    write_artifact(base_dir, task_id, "knowledge_objects_report.md", build_knowledge_objects_report(state))
    write_artifact(base_dir, task_id, "knowledge_partition_report.md", build_knowledge_partition_report(knowledge_partition))
    write_artifact(base_dir, task_id, "knowledge_index_report.md", build_knowledge_index_report(knowledge_index))
    append_event(
        base_dir,
        Event(
            task_id=task_id,
            event_type="task.knowledge_capture_added",
            message="Knowledge capture updated.",
            payload={
                "added_count": len(new_objects),
                "knowledge_objects_count": len(state.knowledge_objects),
                "knowledge_stage_counts": summarize_knowledge_stages(state.knowledge_objects),
                "knowledge_evidence_counts": summarize_knowledge_evidence(state.knowledge_objects),
                "knowledge_reuse_counts": summarize_knowledge_reuse(state.knowledge_objects),
                "knowledge_canonicalization_counts": summarize_canonicalization(state.knowledge_objects),
                "knowledge_partition": {
                    "task_linked_count": knowledge_partition["task_linked_count"],
                    "reusable_candidate_count": knowledge_partition["reusable_candidate_count"],
                },
                "knowledge_index": {
                    "active_reusable_count": knowledge_index["active_reusable_count"],
                    "inactive_reusable_count": knowledge_index["inactive_reusable_count"],
                    "refreshed_at": knowledge_index["refreshed_at"],
                },
            },
        ),
    )
    return state


def _set_phase(base_dir: Path, state: TaskState, phase: str) -> None:
    state.phase = phase
    save_state(base_dir, state)
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="task.phase",
            message=f"Entering {phase} phase.",
            payload={
                "phase": state.phase,
                "status": state.status,
                "execution_lifecycle": state.execution_lifecycle,
                "executor_status": state.executor_status,
            },
        ),
    )


def build_task_retrieval_request(state: TaskState) -> RetrievalRequest:
    return build_retrieval_request(
        query=f"{state.title} {state.goal}".strip(),
        source_types=["repo", "notes"],
        context_layers=["workspace", "task"],
        current_task_id=state.task_id,
        limit=8,
        strategy="system_baseline",
    )


def run_task(
    base_dir: Path,
    task_id: str,
    executor_name: str | None = None,
    capability_refs: list[str] | None = None,
    route_mode: str | None = None,
) -> TaskState:
    state = load_state(base_dir, task_id)
    previous_status = state.status
    previous_phase = state.phase
    if capability_refs:
        capability_manifest = parse_capability_refs(capability_refs)
        capability_errors = validate_capability_manifest(capability_manifest)
        if capability_errors:
            raise ValueError("; ".join(capability_errors))
        capability_assembly = build_capability_assembly(capability_manifest)
        state.capability_manifest = capability_manifest.to_dict()
        state.capability_assembly = capability_assembly.to_dict()
        save_capability_manifest(base_dir, task_id, state.capability_manifest)
        save_capability_assembly(base_dir, task_id, state.capability_assembly)
    state.route_mode = normalize_route_mode(route_mode or state.route_mode)
    route_selection = select_route(state, executor_name, route_mode)
    state.executor_name = route_selection.route.executor_name
    state.route_name = route_selection.route.name
    state.route_backend = route_selection.route.backend_kind
    state.route_executor_family = route_selection.route.executor_family
    state.route_execution_site = route_selection.route.execution_site
    state.route_remote_capable = route_selection.route.remote_capable
    state.route_transport_kind = route_selection.route.transport_kind
    state.route_model_hint = route_selection.route.model_hint
    state.route_reason = route_selection.reason
    state.route_capabilities = route_selection.route.capabilities.to_dict()
    _begin_execution_attempt(state)
    _apply_execution_topology(state, dispatch_status="planned")
    _apply_execution_site_contract(state)
    state.executor_status = "running"
    state.status = "running"
    state.phase = "intake"
    save_state(base_dir, state)
    append_event(
        base_dir,
        Event(
            task_id=task_id,
            event_type="task.run_started",
            message="Task run started.",
            payload={
                "previous_status": previous_status,
                "previous_phase": previous_phase,
                "status": state.status,
                "phase": state.phase,
                "executor_name": state.executor_name,
                "capability_manifest": state.capability_manifest,
                "capability_assembly": state.capability_assembly,
                "route_mode": state.route_mode,
                "route_name": state.route_name,
                "route_backend": state.route_backend,
                "route_executor_family": state.route_executor_family,
                "route_execution_site": state.route_execution_site,
                "route_remote_capable": state.route_remote_capable,
                "route_transport_kind": state.route_transport_kind,
                "route_reason": state.route_reason,
                "route_capabilities": state.route_capabilities,
                "attempt_id": state.current_attempt_id,
                "attempt_number": state.current_attempt_number,
                "attempt_owner_kind": state.current_attempt_owner_kind,
                "attempt_owner_ref": state.current_attempt_owner_ref,
                "attempt_ownership_status": state.current_attempt_ownership_status,
                "attempt_owner_assigned_at": state.current_attempt_owner_assigned_at,
                "attempt_transfer_reason": state.current_attempt_transfer_reason,
                "topology_route_name": state.topology_route_name,
                "topology_executor_family": state.topology_executor_family,
                "topology_execution_site": state.topology_execution_site,
                "topology_transport_kind": state.topology_transport_kind,
                "topology_remote_capable_intent": state.topology_remote_capable_intent,
                "topology_dispatch_status": state.topology_dispatch_status,
                "execution_site_contract_kind": state.execution_site_contract_kind,
                "execution_site_boundary": state.execution_site_boundary,
                "execution_site_contract_status": state.execution_site_contract_status,
                "execution_site_handoff_required": state.execution_site_handoff_required,
                "execution_site_contract_reason": state.execution_site_contract_reason,
                "dispatch_requested_at": state.dispatch_requested_at,
                "dispatch_started_at": state.dispatch_started_at,
                "execution_lifecycle": state.execution_lifecycle,
                "executor_status": state.executor_status,
            },
        ),
    )

    retrieval_request = build_task_retrieval_request(state)
    _set_phase(base_dir, state, "retrieval")
    retrieval_items = run_retrieval(base_dir, state, retrieval_request)
    state.retrieval_count = len(retrieval_items)

    state.dispatch_started_at = utc_now()
    state.topology_dispatch_status = (
        "detached_dispatched" if state.topology_transport_kind == "local_detached_process" else "local_dispatched"
    )
    state.execution_lifecycle = "dispatched"
    _set_phase(base_dir, state, "executing")
    executor_result = run_execution(base_dir, state, retrieval_items)
    state.executor_name = executor_result.executor_name
    state.executor_status = executor_result.status
    save_state(base_dir, state)

    _set_phase(base_dir, state, "summarize")
    state.artifact_paths = {
        "executor_prompt": str((artifacts_dir(base_dir, task_id) / "executor_prompt.md").resolve()),
        "executor_output": str((artifacts_dir(base_dir, task_id) / "executor_output.md").resolve()),
        "executor_stdout": str((artifacts_dir(base_dir, task_id) / "executor_stdout.txt").resolve()),
        "executor_stderr": str((artifacts_dir(base_dir, task_id) / "executor_stderr.txt").resolve()),
        "task_semantics_json": str(task_semantics_path(base_dir, task_id).resolve()),
        "task_semantics_report": str((artifacts_dir(base_dir, task_id) / "task_semantics_report.md").resolve()),
        "knowledge_objects_json": str(knowledge_objects_path(base_dir, task_id).resolve()),
        "knowledge_objects_report": str((artifacts_dir(base_dir, task_id) / "knowledge_objects_report.md").resolve()),
        "knowledge_partition_json": str(knowledge_partition_path(base_dir, task_id).resolve()),
        "knowledge_partition_report": str((artifacts_dir(base_dir, task_id) / "knowledge_partition_report.md").resolve()),
        "knowledge_index_json": str(knowledge_index_path(base_dir, task_id).resolve()),
        "knowledge_index_report": str((artifacts_dir(base_dir, task_id) / "knowledge_index_report.md").resolve()),
        "knowledge_policy_json": str(knowledge_policy_path(base_dir, task_id).resolve()),
        "knowledge_policy_report": str((artifacts_dir(base_dir, task_id) / "knowledge_policy_report.md").resolve()),
        "summary": str((artifacts_dir(base_dir, task_id) / "summary.md").resolve()),
        "resume_note": str((artifacts_dir(base_dir, task_id) / "resume_note.md").resolve()),
        "route_report": str((artifacts_dir(base_dir, task_id) / "route_report.md").resolve()),
        "compatibility_report": str((artifacts_dir(base_dir, task_id) / "compatibility_report.md").resolve()),
        "source_grounding": str((artifacts_dir(base_dir, task_id) / "source_grounding.md").resolve()),
        "retrieval_report": str((artifacts_dir(base_dir, task_id) / "retrieval_report.md").resolve()),
        "retrieval_json": str(retrieval_path(base_dir, task_id).resolve()),
        "validation_report": str((artifacts_dir(base_dir, task_id) / "validation_report.md").resolve()),
        "compatibility_json": str(compatibility_path(base_dir, task_id).resolve()),
        "validation_json": str(validation_path(base_dir, task_id).resolve()),
        "task_memory": str(memory_path(base_dir, task_id).resolve()),
        "capability_manifest_json": str(capability_manifest_path(base_dir, task_id).resolve()),
        "capability_assembly_json": str(capability_assembly_path(base_dir, task_id).resolve()),
        "route_json": str(route_path(base_dir, task_id).resolve()),
        "topology_report": str((artifacts_dir(base_dir, task_id) / "topology_report.md").resolve()),
        "topology_json": str(topology_path(base_dir, task_id).resolve()),
        "execution_site_report": str((artifacts_dir(base_dir, task_id) / "execution_site_report.md").resolve()),
        "execution_site_json": str(execution_site_path(base_dir, task_id).resolve()),
        "dispatch_report": str((artifacts_dir(base_dir, task_id) / "dispatch_report.md").resolve()),
        "dispatch_json": str(dispatch_path(base_dir, task_id).resolve()),
        "handoff_report": str((artifacts_dir(base_dir, task_id) / "handoff_report.md").resolve()),
        "handoff_json": str(handoff_path(base_dir, task_id).resolve()),
        "execution_fit_report": str((artifacts_dir(base_dir, task_id) / "execution_fit_report.md").resolve()),
        "execution_fit_json": str(execution_fit_path(base_dir, task_id).resolve()),
        "retry_policy_report": str((artifacts_dir(base_dir, task_id) / "retry_policy_report.md").resolve()),
        "retry_policy_json": str(retry_policy_path(base_dir, task_id).resolve()),
        "execution_budget_policy_report": str((artifacts_dir(base_dir, task_id) / "execution_budget_policy_report.md").resolve()),
        "execution_budget_policy_json": str(execution_budget_policy_path(base_dir, task_id).resolve()),
        "stop_policy_report": str((artifacts_dir(base_dir, task_id) / "stop_policy_report.md").resolve()),
        "stop_policy_json": str(stop_policy_path(base_dir, task_id).resolve()),
        "checkpoint_snapshot_report": str((artifacts_dir(base_dir, task_id) / "checkpoint_snapshot_report.md").resolve()),
        "checkpoint_snapshot_json": str(checkpoint_snapshot_path(base_dir, task_id).resolve()),
    }
    (
        compatibility_result,
        execution_fit_result,
        knowledge_policy_result,
        validation_result,
        retry_policy_result,
        stop_policy_result,
        execution_budget_policy_result,
    ) = write_task_artifacts(
        base_dir, replace(state), retrieval_items, executor_result
    )

    state.status = (
        "completed"
        if executor_result.status == "completed"
        and compatibility_result.status != "failed"
        and execution_fit_result.status != "failed"
        and knowledge_policy_result.status != "failed"
        and validation_result.status != "failed"
        else "failed"
    )
    state.execution_lifecycle = "completed" if state.status == "completed" else "failed"
    save_state(base_dir, state)
    append_event(
        base_dir,
        Event(
            task_id=task_id,
            event_type="task.completed" if state.status == "completed" else "task.failed",
            message="Task run completed." if state.status == "completed" else "Task run failed.",
            payload={
                "status": state.status,
                "phase": state.phase,
                "retrieval_count": state.retrieval_count,
                "executor_name": state.executor_name,
                "route_mode": state.route_mode,
                "route_name": state.route_name,
                "route_backend": state.route_backend,
                "route_executor_family": state.route_executor_family,
                "route_execution_site": state.route_execution_site,
                "route_remote_capable": state.route_remote_capable,
                "route_transport_kind": state.route_transport_kind,
                "route_reason": state.route_reason,
                "route_capabilities": state.route_capabilities,
                "attempt_id": state.current_attempt_id,
                "attempt_number": state.current_attempt_number,
                "attempt_owner_kind": state.current_attempt_owner_kind,
                "attempt_owner_ref": state.current_attempt_owner_ref,
                "attempt_ownership_status": state.current_attempt_ownership_status,
                "attempt_owner_assigned_at": state.current_attempt_owner_assigned_at,
                "attempt_transfer_reason": state.current_attempt_transfer_reason,
                "topology_route_name": state.topology_route_name,
                "topology_executor_family": state.topology_executor_family,
                "topology_execution_site": state.topology_execution_site,
                "topology_transport_kind": state.topology_transport_kind,
                "topology_remote_capable_intent": state.topology_remote_capable_intent,
                "topology_dispatch_status": state.topology_dispatch_status,
                "execution_site_contract_kind": state.execution_site_contract_kind,
                "execution_site_boundary": state.execution_site_boundary,
                "execution_site_contract_status": state.execution_site_contract_status,
                "execution_site_handoff_required": state.execution_site_handoff_required,
                "execution_site_contract_reason": state.execution_site_contract_reason,
                "dispatch_requested_at": state.dispatch_requested_at,
                "dispatch_started_at": state.dispatch_started_at,
                "execution_lifecycle": state.execution_lifecycle,
                "executor_status": state.executor_status,
                "compatibility_status": compatibility_result.status,
                "execution_fit_status": execution_fit_result.status,
                "retry_policy_status": retry_policy_result.status,
                "execution_budget_policy_status": execution_budget_policy_result.status,
                "stop_policy_status": stop_policy_result.status,
                "knowledge_policy_status": knowledge_policy_result.status,
                "validation_status": validation_result.status,
                "artifact_paths": state.artifact_paths,
            },
        ),
    )
    return state


def build_task_semantics_report(state: TaskState) -> str:
    semantics = state.task_semantics or {}
    lines = [
        "# Task Semantics Report",
        "",
        f"- title: {semantics.get('title', state.title)}",
        f"- goal: {semantics.get('goal', state.goal)}",
        f"- source_kind: {semantics.get('source_kind', 'unknown')}",
        f"- source_ref: {semantics.get('source_ref', '') or 'none'}",
        "",
        "## Imported Planning Constraints",
    ]
    constraints = semantics.get("constraints", [])
    if constraints:
        lines.extend([f"- {item}" for item in constraints])
    else:
        lines.append("- none")

    lines.extend(["", "## Acceptance Criteria"])
    acceptance_criteria = semantics.get("acceptance_criteria", [])
    if acceptance_criteria:
        lines.extend([f"- {item}" for item in acceptance_criteria])
    else:
        lines.append("- none")

    lines.extend(["", "## Priority Hints"])
    priority_hints = semantics.get("priority_hints", [])
    if priority_hints:
        lines.extend([f"- {item}" for item in priority_hints])
    else:
        lines.append("- none")

    lines.extend(["", "## Next Action Proposals"])
    next_actions = semantics.get("next_action_proposals", [])
    if next_actions:
        lines.extend([f"- {item}" for item in next_actions])
    else:
        lines.append("- none")
    return "\n".join(lines)


def build_knowledge_objects_report(state: TaskState) -> str:
    knowledge_objects = state.knowledge_objects or []
    stage_counts = summarize_knowledge_stages(knowledge_objects)
    evidence_counts = summarize_knowledge_evidence(knowledge_objects)
    reuse_counts = summarize_knowledge_reuse(knowledge_objects)
    canonicalization_counts = summarize_canonicalization(knowledge_objects)
    lines = [
        "# Knowledge Objects Report",
        "",
        f"- count: {len(knowledge_objects)}",
        f"- raw: {stage_counts.get('raw', 0)}",
        f"- candidate: {stage_counts.get('candidate', 0)}",
        f"- verified: {stage_counts.get('verified', 0)}",
        f"- canonical: {stage_counts.get('canonical', 0)}",
        f"- artifact_backed: {evidence_counts.get('artifact_backed', 0)}",
        f"- source_only: {evidence_counts.get('source_only', 0)}",
        f"- unbacked: {evidence_counts.get('unbacked', 0)}",
        f"- retrieval_candidate: {reuse_counts.get('retrieval_candidate', 0)}",
        f"- task_only: {reuse_counts.get('task_only', 0)}",
        f"- canonicalization_not_requested: {canonicalization_counts.get('not_requested', 0)}",
        f"- canonicalization_review_ready: {canonicalization_counts.get('review_ready', 0)}",
        f"- canonicalization_promotion_ready: {canonicalization_counts.get('promotion_ready', 0)}",
        f"- canonicalization_blocked_stage: {canonicalization_counts.get('blocked_stage', 0)}",
        f"- canonicalization_blocked_evidence: {canonicalization_counts.get('blocked_evidence', 0)}",
        f"- canonicalization_canonical: {canonicalization_counts.get('canonical', 0)}",
        "",
        "## Objects",
    ]
    if not knowledge_objects:
        lines.append("- none")
        return "\n".join(lines)

    for item in knowledge_objects:
        lines.extend(
            [
                f"- id: {item.get('object_id', 'unknown')}",
                f"  stage: {item.get('stage', 'raw')}",
                f"  source_kind: {item.get('source_kind', 'unknown')}",
                f"  source_ref: {item.get('source_ref', '') or 'none'}",
                f"  captured_at: {item.get('captured_at', 'unknown')}",
                f"  task_linked: {'yes' if item.get('task_linked', False) else 'no'}",
                f"  evidence_status: {item.get('evidence_status', 'unbacked')}",
                f"  artifact_ref: {item.get('artifact_ref', '') or 'none'}",
                f"  retrieval_eligible: {'yes' if item.get('retrieval_eligible', False) else 'no'}",
                f"  knowledge_reuse_scope: {item.get('knowledge_reuse_scope', 'task_only')}",
                f"  canonicalization_intent: {item.get('canonicalization_intent', 'none')}",
                f"  canonicalization_status: {canonicalization_status_for(item)}",
                f"  text: {item.get('text', '') or '(empty)'}",
            ]
        )
    return "\n".join(lines)
