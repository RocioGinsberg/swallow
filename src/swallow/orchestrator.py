from __future__ import annotations

import json

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from .capabilities import build_capability_assembly, parse_capability_refs, validate_capability_manifest
from .canonical_registry import (
    build_canonical_record,
    build_canonical_registry_index,
    build_canonical_registry_index_report,
    build_canonical_registry_report,
)
from .canonical_reuse_eval import (
    build_canonical_reuse_evaluation_record,
    build_canonical_reuse_evaluation_report,
    build_canonical_reuse_regression_baseline,
    build_canonical_reuse_evaluation_summary,
    match_retrieval_items_for_citations,
    resolve_canonical_reuse_citations,
)
from .canonical_reuse import build_canonical_reuse_report, build_canonical_reuse_summary
from .capability_enforcement import CapabilityConstraint, enforce_capability_constraints
from .executor import normalize_executor_name, resolve_dialect_name, resolve_executor
from .dispatch_policy import validate_handoff_semantics, validate_taxonomy_dispatch
from .grounding import build_grounding_evidence, extract_grounding_entries
from .harness import (
    build_remote_handoff_contract_record,
    build_remote_handoff_contract_report,
    run_retrieval,
    write_task_artifacts,
)
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
from .knowledge_review import apply_knowledge_decision, build_knowledge_decisions_report
from .models import Event, ExecutorResult, RetrievalItem, RetrievalRequest, TaskCard, TaskState
from .models import DispatchVerdict, evaluate_dispatch_verdict
from .paths import (
    artifacts_dir,
    capability_assembly_path,
    capability_manifest_path,
    checkpoint_snapshot_path,
    canonical_registry_index_path,
    canonical_registry_path,
    canonical_reuse_policy_path,
    canonical_reuse_eval_path,
    canonical_reuse_regression_path,
    compatibility_path,
    dispatch_path,
    execution_site_path,
    execution_fit_path,
    execution_budget_policy_path,
    handoff_path,
    knowledge_decisions_path,
    knowledge_index_path,
    knowledge_objects_path,
    knowledge_partition_path,
    knowledge_policy_path,
    memory_path,
    retry_policy_path,
    stop_policy_path,
    task_root,
    task_semantics_path,
    retrieval_path,
    remote_handoff_contract_path,
    route_path,
    topology_path,
    validation_path,
)
from .retrieval import build_retrieval_request
from .router import normalize_route_mode, select_route
from .planner import plan
from .review_gate import review_executor_output
from .staged_knowledge import StagedCandidate, submit_staged_candidate
from .store import (
    append_event,
    append_canonical_record,
    append_canonical_reuse_evaluation,
    append_knowledge_decision,
    load_knowledge_objects,
    load_state,
    save_capability_assembly,
    save_capability_manifest,
    save_canonical_reuse_policy,
    save_canonical_reuse_regression,
    save_canonical_registry_index,
    save_knowledge_index,
    save_knowledge_objects,
    save_knowledge_partition,
    save_remote_handoff_contract,
    save_state,
    save_task_semantics,
    write_artifact,
)
from .task_semantics import build_task_semantics
from .models import utc_now


def _apply_capability_enforcement(state: TaskState) -> list[CapabilityConstraint]:
    enforced_capabilities, applied_constraints = enforce_capability_constraints(
        state.route_taxonomy_role,
        state.route_taxonomy_memory_authority,
        state.route_capabilities,
    )
    state.route_capabilities = enforced_capabilities
    return applied_constraints


def _serialize_capability_constraints(constraints: list[CapabilityConstraint]) -> list[dict[str, object]]:
    return [constraint.to_dict() for constraint in constraints]


def _execute_task_card(
    base_dir: Path,
    state: TaskState,
    card: TaskCard,
    retrieval_items: list[RetrievalItem],
) -> ExecutorResult:
    executor = resolve_executor(card.executor_type, state.executor_name)
    return executor.execute(base_dir, state, card, retrieval_items)


def _load_locked_grounding_evidence(base_dir: Path, state: TaskState) -> dict[str, object] | None:
    evidence_path = artifacts_dir(base_dir, state.task_id) / "grounding_evidence.json"
    if not evidence_path.exists():
        return None
    try:
        payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _resolve_grounding_state(
    base_dir: Path,
    state: TaskState,
    retrieval_items: list[object],
) -> tuple[dict[str, object], bool]:
    if state.grounding_locked:
        locked_payload = _load_locked_grounding_evidence(base_dir, state)
        if locked_payload is not None:
            citations = locked_payload.get("citations", [])
            state.grounding_refs = [str(item).strip() for item in citations if str(item).strip()]
            state.grounding_locked = True
            return locked_payload, True

    grounding_entries = extract_grounding_entries(retrieval_items)
    grounding_evidence = build_grounding_evidence(grounding_entries)
    citations = grounding_evidence.get("citations", [])
    state.grounding_refs = [str(item).strip() for item in citations if str(item).strip()]
    state.grounding_locked = True
    return grounding_evidence, False


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


def _evaluate_dispatch_for_run(base_dir: Path, state: TaskState) -> tuple[dict[str, object], DispatchVerdict]:
    contract_record = build_remote_handoff_contract_record(state)
    save_remote_handoff_contract(base_dir, state.task_id, contract_record)
    write_artifact(
        base_dir,
        state.task_id,
        "remote_handoff_contract_report.md",
        build_remote_handoff_contract_report(contract_record),
    )
    if bool(contract_record.get("remote_candidate", False)):
        policy_result = validate_handoff_semantics(contract_record, task_root(base_dir, state.task_id))
    else:
        policy_result = None
    if policy_result is not None and not policy_result.valid:
        return contract_record, DispatchVerdict(
            action="blocked",
            reason="remote handoff contract failed semantic validation",
            blocking_detail="; ".join(policy_result.errors),
        )
    taxonomy_result = validate_taxonomy_dispatch(state, contract_record)
    if not taxonomy_result.valid:
        return contract_record, DispatchVerdict(
            action="blocked",
            reason="route taxonomy rejected dispatch contract",
            blocking_detail="; ".join(taxonomy_result.errors),
        )
    return contract_record, evaluate_dispatch_verdict(contract_record)


def _apply_blocked_dispatch_verdict(
    base_dir: Path,
    state: TaskState,
    contract_record: dict[str, object],
    verdict: DispatchVerdict,
) -> TaskState:
    state.topology_dispatch_status = "blocked"
    state.execution_lifecycle = "blocked"
    state.executor_status = "blocked"
    state.status = "dispatch_blocked"
    state.phase = "dispatch"
    save_state(base_dir, state)
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="task.dispatch_blocked",
            message="Task dispatch blocked before executor handoff.",
            payload={
                "status": state.status,
                "phase": state.phase,
                "route_name": state.route_name,
                "route_execution_site": state.route_execution_site,
                "route_transport_kind": state.route_transport_kind,
                "topology_dispatch_status": state.topology_dispatch_status,
                "execution_lifecycle": state.execution_lifecycle,
                "dispatch_verdict": verdict.to_dict(),
                "remote_handoff_contract_kind": contract_record.get("contract_kind", ""),
                "remote_handoff_contract_status": contract_record.get("contract_status", ""),
            },
        ),
    )
    return state


def acknowledge_task(base_dir: Path, task_id: str) -> TaskState:
    state = load_state(base_dir, task_id)
    if state.status != "dispatch_blocked":
        raise ValueError(f"Only dispatch_blocked tasks can be acknowledged; current status is {state.status}.")

    previous_status = state.status
    previous_phase = state.phase
    state.executor_name = "local"
    state.route_mode = "summary"
    route_selection = select_route(state, executor_override=state.executor_name, route_mode_override=state.route_mode)
    state.route_name = route_selection.route.name
    state.route_backend = route_selection.route.backend_kind
    state.route_executor_family = route_selection.route.executor_family
    state.route_execution_site = route_selection.route.execution_site
    state.route_remote_capable = route_selection.route.remote_capable
    state.route_transport_kind = route_selection.route.transport_kind
    state.route_taxonomy_role = route_selection.route.taxonomy.system_role
    state.route_taxonomy_memory_authority = route_selection.route.taxonomy.memory_authority
    state.route_model_hint = route_selection.route.model_hint
    state.route_dialect = resolve_dialect_name(route_selection.route.dialect_hint, route_selection.route.model_hint)
    state.route_reason = "Operator acknowledged blocked dispatch and forced a local execution path."
    state.route_capabilities = route_selection.route.capabilities.to_dict()
    applied_constraints = _apply_capability_enforcement(state)
    _apply_execution_topology(state, dispatch_status="acknowledged")
    _apply_execution_site_contract(state)
    state.status = "running"
    state.phase = "retrieval"
    state.execution_lifecycle = "prepared"
    state.executor_status = "pending"
    state.dispatch_started_at = ""
    save_state(base_dir, state)
    append_event(
        base_dir,
        Event(
            task_id=task_id,
            event_type="task.dispatch_acknowledged",
            message="Blocked dispatch acknowledged for local execution.",
            payload={
                "previous_status": previous_status,
                "previous_phase": previous_phase,
                "status": state.status,
                "phase": state.phase,
                "executor_name": state.executor_name,
                "route_mode": state.route_mode,
                "route_name": state.route_name,
                "route_execution_site": state.route_execution_site,
                "route_transport_kind": state.route_transport_kind,
                "route_dialect": state.route_dialect,
                "route_capabilities": state.route_capabilities,
                "capability_constraints_applied": _serialize_capability_constraints(applied_constraints),
                "topology_dispatch_status": state.topology_dispatch_status,
                "execution_lifecycle": state.execution_lifecycle,
            },
        ),
    )
    return state


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
    state.route_taxonomy_role = initial_route.route.taxonomy.system_role
    state.route_taxonomy_memory_authority = initial_route.route.taxonomy.memory_authority
    state.route_model_hint = initial_route.route.model_hint
    state.route_dialect = resolve_dialect_name(initial_route.route.dialect_hint, initial_route.route.model_hint)
    state.route_reason = initial_route.reason
    state.route_capabilities = initial_route.route.capabilities.to_dict()
    _apply_execution_topology(state, dispatch_status="not_requested")
    _apply_execution_site_contract(state)
    state.artifact_paths = {
        "task_semantics_json": str(task_semantics_path(base_dir, task_id).resolve()),
        "task_semantics_report": str((artifacts_dir(base_dir, task_id) / "task_semantics_report.md").resolve()),
        "knowledge_objects_json": str(knowledge_objects_path(base_dir, task_id).resolve()),
        "knowledge_objects_report": str((artifacts_dir(base_dir, task_id) / "knowledge_objects_report.md").resolve()),
        "librarian_change_log": str((artifacts_dir(base_dir, task_id) / "librarian_change_log.json").resolve()),
        "librarian_change_log_report": str(
            (artifacts_dir(base_dir, task_id) / "librarian_change_log_report.md").resolve()
        ),
        "knowledge_partition_json": str(knowledge_partition_path(base_dir, task_id).resolve()),
        "knowledge_partition_report": str((artifacts_dir(base_dir, task_id) / "knowledge_partition_report.md").resolve()),
        "knowledge_index_json": str(knowledge_index_path(base_dir, task_id).resolve()),
        "knowledge_index_report": str((artifacts_dir(base_dir, task_id) / "knowledge_index_report.md").resolve()),
        "knowledge_decisions_json": str(knowledge_decisions_path(base_dir, task_id).resolve()),
        "knowledge_decisions_report": str((artifacts_dir(base_dir, task_id) / "knowledge_decisions_report.md").resolve()),
        "canonical_registry_json": str(canonical_registry_path(base_dir).resolve()),
        "canonical_registry_report": str((artifacts_dir(base_dir, task_id) / "canonical_registry_report.md").resolve()),
        "canonical_registry_index_json": str(canonical_registry_index_path(base_dir).resolve()),
        "canonical_registry_index_report": str((artifacts_dir(base_dir, task_id) / "canonical_registry_index_report.md").resolve()),
        "canonical_reuse_policy_json": str(canonical_reuse_policy_path(base_dir).resolve()),
        "canonical_reuse_policy_report": str((artifacts_dir(base_dir, task_id) / "canonical_reuse_policy_report.md").resolve()),
        "canonical_reuse_eval_json": str(canonical_reuse_eval_path(base_dir, task_id).resolve()),
        "canonical_reuse_eval_report": str((artifacts_dir(base_dir, task_id) / "canonical_reuse_eval_report.md").resolve()),
        "canonical_reuse_regression_json": str(canonical_reuse_regression_path(base_dir, task_id).resolve()),
        "remote_handoff_contract_json": str(remote_handoff_contract_path(base_dir, task_id).resolve()),
        "remote_handoff_contract_report": str(
            (artifacts_dir(base_dir, task_id) / "remote_handoff_contract_report.md").resolve()
        ),
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
    write_artifact(base_dir, task_id, "knowledge_decisions_report.md", build_knowledge_decisions_report([]))
    write_artifact(base_dir, task_id, "canonical_registry_report.md", build_canonical_registry_report([]))
    empty_canonical_index = build_canonical_registry_index([])
    save_canonical_registry_index(base_dir, empty_canonical_index)
    write_artifact(base_dir, task_id, "canonical_registry_index_report.md", build_canonical_registry_index_report(empty_canonical_index))
    empty_canonical_reuse = build_canonical_reuse_summary([])
    save_canonical_reuse_policy(base_dir, empty_canonical_reuse)
    write_artifact(base_dir, task_id, "canonical_reuse_policy_report.md", build_canonical_reuse_report(empty_canonical_reuse))
    write_artifact(
        base_dir,
        task_id,
        "canonical_reuse_eval_report.md",
        build_canonical_reuse_evaluation_report([], build_canonical_reuse_evaluation_summary([])),
    )
    save_canonical_reuse_regression(
        base_dir,
        task_id,
        build_canonical_reuse_regression_baseline(
            task_id=task_id,
            summary=build_canonical_reuse_evaluation_summary([]),
        ),
    )
    remote_handoff_contract_record = build_remote_handoff_contract_record(state)
    save_remote_handoff_contract(base_dir, task_id, remote_handoff_contract_record)
    write_artifact(
        base_dir,
        task_id,
        "remote_handoff_contract_report.md",
        build_remote_handoff_contract_report(remote_handoff_contract_record),
    )
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


def decide_task_knowledge(
    base_dir: Path,
    task_id: str,
    *,
    object_id: str,
    decision_type: str,
    decision_target: str,
    caller_authority: str = "task-state",
    note: str = "",
    decided_by: str = "swl_cli",
) -> TaskState:
    state = load_state(base_dir, task_id)
    current_objects = load_knowledge_objects(base_dir, task_id)
    if not current_objects:
        current_objects = list(state.knowledge_objects or [])
    try:
        updated_objects, decision_record = apply_knowledge_decision(
            current_objects,
            object_id=object_id,
            decision_type=decision_type,
            decision_target=decision_target,
            caller_authority=caller_authority,
            note=note,
            decided_by=decided_by,
        )
    except PermissionError as exc:
        append_event(
            base_dir,
            Event(
                task_id=task_id,
                event_type="knowledge.promotion.unauthorized",
                message="Unauthorized canonical promotion was blocked.",
                payload={
                    "object_id": object_id,
                    "decision_type": decision_type,
                    "decision_target": decision_target,
                    "caller_authority": caller_authority,
                    "decided_by": decided_by,
                    "note": note.strip(),
                    "error": str(exc),
                },
            ),
        )
        raise
    state.knowledge_objects = updated_objects
    knowledge_partition = build_knowledge_partition(state.knowledge_objects)
    knowledge_index = build_knowledge_index(state.knowledge_objects)
    save_state(base_dir, state)
    save_knowledge_objects(base_dir, task_id, state.knowledge_objects)
    save_knowledge_partition(base_dir, task_id, knowledge_partition)
    save_knowledge_index(base_dir, task_id, knowledge_index)
    append_knowledge_decision(base_dir, task_id, decision_record)
    decision_records = []
    if knowledge_decisions_path(base_dir, task_id).exists():
        for line in knowledge_decisions_path(base_dir, task_id).read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped:
                decision_records.append(json.loads(stripped))
    write_artifact(base_dir, task_id, "knowledge_objects_report.md", build_knowledge_objects_report(state))
    write_artifact(base_dir, task_id, "knowledge_partition_report.md", build_knowledge_partition_report(knowledge_partition))
    write_artifact(base_dir, task_id, "knowledge_index_report.md", build_knowledge_index_report(knowledge_index))
    write_artifact(base_dir, task_id, "knowledge_decisions_report.md", build_knowledge_decisions_report(decision_records))
    canonical_records: list[dict[str, object]] = []
    if decision_type == "promote" and decision_target == "canonical":
        canonical_record = build_canonical_record(
            task_id=task_id,
            object_id=object_id,
            knowledge_object=next(item for item in state.knowledge_objects if str(item.get("object_id", "")) == object_id),
            decision_record=decision_record,
        )
        append_canonical_record(base_dir, canonical_record)
    if canonical_registry_path(base_dir).exists():
        for line in canonical_registry_path(base_dir).read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped:
                canonical_records.append(json.loads(stripped))
    canonical_index = build_canonical_registry_index(canonical_records)
    save_canonical_registry_index(base_dir, canonical_index)
    canonical_reuse_summary = build_canonical_reuse_summary(canonical_records)
    save_canonical_reuse_policy(base_dir, canonical_reuse_summary)
    write_artifact(base_dir, task_id, "canonical_registry_report.md", build_canonical_registry_report(canonical_records))
    write_artifact(base_dir, task_id, "canonical_registry_index_report.md", build_canonical_registry_index_report(canonical_index))
    write_artifact(base_dir, task_id, "canonical_reuse_policy_report.md", build_canonical_reuse_report(canonical_reuse_summary))
    append_event(
        base_dir,
        Event(
            task_id=task_id,
            event_type=f"knowledge.{'promoted' if decision_type == 'promote' else 'rejected'}",
            message=f"Knowledge {decision_type} decision applied.",
            payload={
                "object_id": object_id,
                "decision_target": decision_target,
                "decision_record": decision_record,
                "canonical_registry_count": len(canonical_records),
                "canonical_registry_index": canonical_index,
                "canonical_reuse_policy": {
                    "reuse_visible_count": canonical_reuse_summary["reuse_visible_count"],
                    "reuse_hidden_count": canonical_reuse_summary["reuse_hidden_count"],
                    "policy_name": canonical_reuse_summary["policy_name"],
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


def _record_phase_checkpoint(
    base_dir: Path,
    state: TaskState,
    execution_phase: str,
    *,
    skipped: bool = False,
    source: str = "",
) -> None:
    state.execution_phase = execution_phase
    state.last_phase_checkpoint_at = utc_now()
    save_state(base_dir, state)
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="task.phase_checkpoint",
            message=f"Execution phase checkpoint recorded for {execution_phase}.",
            payload={
                "phase": state.phase,
                "status": state.status,
                "execution_phase": state.execution_phase,
                "last_phase_checkpoint_at": state.last_phase_checkpoint_at,
                "skipped": skipped,
                "source": source or ("reused_artifacts" if skipped else "live_run"),
            },
        ),
    )


def _append_phase_recovery_fallback(
    base_dir: Path,
    state: TaskState,
    *,
    requested_skip_to_phase: str,
    fallback_phase: str,
    reason: str,
) -> None:
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="task.phase_recovery_fallback",
            message="Selective retry fell back to an earlier execution phase.",
            payload={
                "requested_skip_to_phase": requested_skip_to_phase,
                "fallback_phase": fallback_phase,
                "reason": reason,
            },
        ),
    )


def _load_previous_retrieval_items(base_dir: Path, task_id: str) -> list[RetrievalItem] | None:
    retrieval_file = retrieval_path(base_dir, task_id)
    if not retrieval_file.exists():
        return None
    try:
        payload = json.loads(retrieval_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, list):
        return None
    items: list[RetrievalItem] = []
    try:
        for entry in payload:
            if not isinstance(entry, dict):
                return None
            items.append(RetrievalItem(**entry))
    except TypeError:
        return None
    return items


def _load_previous_executor_result(base_dir: Path, state: TaskState) -> ExecutorResult | None:
    output_path = artifacts_dir(base_dir, state.task_id) / "executor_output.md"
    if not output_path.exists():
        return None
    prompt_path = artifacts_dir(base_dir, state.task_id) / "executor_prompt.md"
    stdout_path = artifacts_dir(base_dir, state.task_id) / "executor_stdout.txt"
    stderr_path = artifacts_dir(base_dir, state.task_id) / "executor_stderr.txt"
    handoff_record: dict[str, object] = {}
    if handoff_path(base_dir, state.task_id).exists():
        try:
            loaded_handoff = json.loads(handoff_path(base_dir, state.task_id).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            loaded_handoff = {}
        if isinstance(loaded_handoff, dict):
            handoff_record = loaded_handoff
    output = output_path.read_text(encoding="utf-8")
    prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
    if prompt.startswith("dialect: "):
        _, _, prompt = prompt.partition("\n\n")
    return ExecutorResult(
        executor_name=state.executor_name,
        status=state.executor_status if state.executor_status != "pending" else str(handoff_record.get("executor_status", "completed")),
        message=str(handoff_record.get("executor_message", "")).strip() or output.strip() or "Reused previous executor result.",
        output=output,
        prompt=prompt,
        dialect=state.route_dialect,
        failure_kind=str(handoff_record.get("failure_kind", "")).strip(),
        stdout=stdout_path.read_text(encoding="utf-8") if stdout_path.exists() else "",
        stderr=stderr_path.read_text(encoding="utf-8") if stderr_path.exists() else "",
    )


def _route_knowledge_to_staged(base_dir: Path, state: TaskState) -> list[StagedCandidate]:
    if state.route_taxonomy_memory_authority not in {"canonical-write-forbidden", "staged-knowledge"}:
        return []

    knowledge_objects = load_knowledge_objects(base_dir, state.task_id)
    if not knowledge_objects and isinstance(state.knowledge_objects, list):
        knowledge_objects = list(state.knowledge_objects)

    staged_candidates: list[StagedCandidate] = []
    for item in knowledge_objects:
        if str(item.get("canonicalization_intent", "none")) != "promote":
            continue
        if str(item.get("stage", "raw")) != "verified":
            continue
        candidate = submit_staged_candidate(
            base_dir,
            StagedCandidate(
                candidate_id="",
                text=str(item.get("text", "")),
                source_task_id=state.task_id,
                source_object_id=str(item.get("object_id", "")).strip(),
                submitted_by=state.executor_name,
                taxonomy_role=state.route_taxonomy_role,
                taxonomy_memory_authority=state.route_taxonomy_memory_authority,
            ),
        )
        staged_candidates.append(candidate)

    if staged_candidates:
        append_event(
            base_dir,
            Event(
                task_id=state.task_id,
                event_type="task.knowledge_staged",
                message="Knowledge objects were routed into staged knowledge.",
                payload={
                    "candidate_count": len(staged_candidates),
                    "candidate_ids": [candidate.candidate_id for candidate in staged_candidates],
                    "source_object_ids": [candidate.source_object_id for candidate in staged_candidates],
                    "taxonomy_role": state.route_taxonomy_role,
                    "taxonomy_memory_authority": state.route_taxonomy_memory_authority,
                },
            ),
        )
    return staged_candidates


def build_task_retrieval_request(state: TaskState) -> RetrievalRequest:
    return build_retrieval_request(
        query=f"{state.title} {state.goal}".strip(),
        source_types=["repo", "notes"],
        context_layers=["workspace", "task"],
        current_task_id=state.task_id,
        limit=8,
        strategy="system_baseline",
    )


def evaluate_task_canonical_reuse(
    base_dir: Path,
    task_id: str,
    *,
    citations: list[str],
    judgment: str,
    note: str = "",
    evaluated_by: str = "swl_cli",
) -> dict[str, object]:
    state = load_state(base_dir, task_id)
    reuse_policy: dict[str, object] = {}
    retrieval_items: list[dict[str, object]] = []
    if canonical_reuse_policy_path(base_dir).exists():
        reuse_policy = json.loads(canonical_reuse_policy_path(base_dir).read_text(encoding="utf-8"))
    if retrieval_path(base_dir, task_id).exists():
        loaded_retrieval = json.loads(retrieval_path(base_dir, task_id).read_text(encoding="utf-8"))
        if isinstance(loaded_retrieval, list):
            retrieval_items = loaded_retrieval
    visible_records = reuse_policy.get("visible_records", []) if isinstance(reuse_policy, dict) else []
    if not isinstance(visible_records, list):
        visible_records = []
    resolved_citations, unresolved_citations = resolve_canonical_reuse_citations(
        task_id=task_id,
        citations=citations,
        visible_records=visible_records,
    )
    retrieval_matches = match_retrieval_items_for_citations(citations=citations, retrieval_items=retrieval_items)
    record = build_canonical_reuse_evaluation_record(
        task_id=task_id,
        citations=citations,
        judgment=judgment,
        note=note,
        evaluated_by=evaluated_by,
        resolved_citations=resolved_citations,
        unresolved_citations=unresolved_citations,
        retrieval_context_ref=f".swl/tasks/{task_id}/retrieval.json" if retrieval_items else "",
        retrieval_context_available=bool(retrieval_items),
        retrieval_context_count=len(retrieval_items),
        retrieval_matches=retrieval_matches,
    )
    append_canonical_reuse_evaluation(base_dir, task_id, record)
    records: list[dict[str, object]] = []
    if canonical_reuse_eval_path(base_dir, task_id).exists():
        for line in canonical_reuse_eval_path(base_dir, task_id).read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
    summary = build_canonical_reuse_evaluation_summary(records)
    regression_baseline = build_canonical_reuse_regression_baseline(task_id=task_id, summary=summary)
    save_canonical_reuse_regression(base_dir, task_id, regression_baseline)
    write_artifact(
        base_dir,
        task_id,
        "canonical_reuse_eval_report.md",
        build_canonical_reuse_evaluation_report(records, summary),
    )
    append_event(
        base_dir,
        Event(
            task_id=task_id,
            event_type="canonical_reuse.evaluated",
            message="Canonical reuse evaluation recorded.",
            payload={
                "record": record,
                "summary": summary,
                "regression_baseline": regression_baseline,
            },
        ),
    )
    return {"record": record, "summary": summary, "artifact_paths": state.artifact_paths}


def run_task(
    base_dir: Path,
    task_id: str,
    executor_name: str | None = None,
    capability_refs: list[str] | None = None,
    route_mode: str | None = None,
    reset_grounding: bool = False,
    skip_to_phase: str = "retrieval",
) -> TaskState:
    state = load_state(base_dir, task_id)
    previous_status = state.status
    previous_phase = state.phase
    requested_skip_to_phase = skip_to_phase.strip() or "retrieval"
    if reset_grounding:
        state.grounding_refs = []
        state.grounding_locked = False
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
    state.route_taxonomy_role = route_selection.route.taxonomy.system_role
    state.route_taxonomy_memory_authority = route_selection.route.taxonomy.memory_authority
    state.route_model_hint = route_selection.route.model_hint
    state.route_dialect = resolve_dialect_name(route_selection.route.dialect_hint, route_selection.route.model_hint)
    state.route_reason = route_selection.reason
    original_route_capabilities = route_selection.route.capabilities.to_dict()
    state.route_capabilities = dict(original_route_capabilities)
    applied_constraints = _apply_capability_enforcement(state)
    _begin_execution_attempt(state)
    _apply_execution_topology(state, dispatch_status="planned")
    _apply_execution_site_contract(state)
    state.executor_status = "running"
    state.status = "running"
    state.phase = "intake"
    state.execution_phase = "pending"
    state.last_phase_checkpoint_at = ""
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
                "route_dialect": state.route_dialect,
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
                "grounding_refs": state.grounding_refs,
                "grounding_locked": state.grounding_locked,
            },
        ),
    )
    if applied_constraints:
        append_event(
            base_dir,
            Event(
                task_id=task_id,
                event_type="task.capability_enforced",
                message="Route capabilities were downgraded by taxonomy enforcement.",
                payload={
                    "taxonomy_role": state.route_taxonomy_role,
                    "taxonomy_memory_authority": state.route_taxonomy_memory_authority,
                    "original_route_capabilities": original_route_capabilities,
                    "enforced_route_capabilities": state.route_capabilities,
                    "constraints": _serialize_capability_constraints(applied_constraints),
                },
            ),
        )
    contract_record, dispatch_verdict = _evaluate_dispatch_for_run(base_dir, state)
    if dispatch_verdict.action == "blocked":
        return _apply_blocked_dispatch_verdict(base_dir, state, contract_record, dispatch_verdict)

    cards = plan(state)
    card = cards[0]
    append_event(
        base_dir,
        Event(
            task_id=task_id,
            event_type="task.planned",
            message="Task planned into runtime task cards.",
            payload={
                "card_count": len(cards),
                "card_id": card.card_id,
                "route_hint": card.route_hint,
                "executor_type": card.executor_type,
                "parent_task_id": card.parent_task_id,
            },
        ),
    )

    _set_phase(base_dir, state, "retrieval")
    retrieval_items: list[RetrievalItem] | None = None
    if requested_skip_to_phase in {"execution", "analysis"}:
        retrieval_items = _load_previous_retrieval_items(base_dir, task_id)
        if retrieval_items is None:
            _append_phase_recovery_fallback(
                base_dir,
                state,
                requested_skip_to_phase=requested_skip_to_phase,
                fallback_phase="retrieval",
                reason="previous retrieval artifacts are missing or invalid",
            )
    if retrieval_items is None:
        retrieval_request = build_task_retrieval_request(state)
        retrieval_items = run_retrieval(base_dir, state, retrieval_request)
        retrieval_skipped = False
    else:
        retrieval_skipped = True
    assert retrieval_items is not None
    state.retrieval_count = len(retrieval_items)
    grounding_evidence, reused_grounding = _resolve_grounding_state(base_dir, state, retrieval_items)
    save_state(base_dir, state)
    append_event(
        base_dir,
        Event(
            task_id=task_id,
            event_type="grounding.locked",
            message="Grounding evidence locked for this task run."
            if not reused_grounding
            else "Grounding evidence reused from the locked artifact.",
            payload={
                "grounding_refs": state.grounding_refs,
                "grounding_refs_count": len(state.grounding_refs),
                "grounding_locked": state.grounding_locked,
                "reused_locked_artifact": reused_grounding,
            },
        ),
    )
    _record_phase_checkpoint(
        base_dir,
        state,
        "retrieval_done",
        skipped=retrieval_skipped,
        source="previous_retrieval" if retrieval_skipped else "live_retrieval",
    )

    if requested_skip_to_phase == "analysis":
        executor_result = _load_previous_executor_result(base_dir, state)
        if executor_result is None:
            _append_phase_recovery_fallback(
                base_dir,
                state,
                requested_skip_to_phase=requested_skip_to_phase,
                fallback_phase="execution",
                reason="previous executor artifacts are missing or invalid",
            )
    else:
        executor_result = None
    if executor_result is None:
        state.dispatch_started_at = utc_now()
        state.topology_dispatch_status = (
            "mock_remote_dispatched"
            if state.topology_transport_kind == "mock_remote_transport"
            else "detached_dispatched"
            if state.topology_transport_kind == "local_detached_process"
            else "local_dispatched"
        )
        state.execution_lifecycle = "dispatched"
        save_state(base_dir, state)
        _set_phase(base_dir, state, "executing")
        executor_result = _execute_task_card(base_dir, state, card, retrieval_items)
        execution_skipped = False
    else:
        state.execution_lifecycle = "reused"
        state.executor_name = executor_result.executor_name
        state.executor_status = executor_result.status
        save_state(base_dir, state)
        _set_phase(base_dir, state, "executing")
        execution_skipped = True
    state.executor_name = executor_result.executor_name
    state.executor_status = executor_result.status
    save_state(base_dir, state)
    review_gate_result = review_executor_output(executor_result, card)
    append_event(
        base_dir,
        Event(
            task_id=task_id,
            event_type="task.review_gate",
            message=review_gate_result.message,
            payload={
                "status": review_gate_result.status,
                "checks": review_gate_result.checks,
                "card_id": card.card_id,
                "executor_name": executor_result.executor_name,
                "executor_status": executor_result.status,
                "skipped_execution": execution_skipped,
                "source": "previous_execution" if execution_skipped else "live_execution",
            },
        ),
    )
    _record_phase_checkpoint(
        base_dir,
        state,
        "execution_done",
        skipped=execution_skipped,
        source="previous_execution" if execution_skipped else "live_execution",
    )

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
        "librarian_change_log": str((artifacts_dir(base_dir, task_id) / "librarian_change_log.json").resolve()),
        "librarian_change_log_report": str(
            (artifacts_dir(base_dir, task_id) / "librarian_change_log_report.md").resolve()
        ),
        "knowledge_partition_json": str(knowledge_partition_path(base_dir, task_id).resolve()),
        "knowledge_partition_report": str((artifacts_dir(base_dir, task_id) / "knowledge_partition_report.md").resolve()),
        "knowledge_index_json": str(knowledge_index_path(base_dir, task_id).resolve()),
        "knowledge_index_report": str((artifacts_dir(base_dir, task_id) / "knowledge_index_report.md").resolve()),
        "knowledge_policy_json": str(knowledge_policy_path(base_dir, task_id).resolve()),
        "canonical_reuse_policy_json": str(canonical_reuse_policy_path(base_dir).resolve()),
        "knowledge_policy_report": str((artifacts_dir(base_dir, task_id) / "knowledge_policy_report.md").resolve()),
        "canonical_reuse_policy_report": str((artifacts_dir(base_dir, task_id) / "canonical_reuse_policy_report.md").resolve()),
        "summary": str((artifacts_dir(base_dir, task_id) / "summary.md").resolve()),
        "resume_note": str((artifacts_dir(base_dir, task_id) / "resume_note.md").resolve()),
        "route_report": str((artifacts_dir(base_dir, task_id) / "route_report.md").resolve()),
        "compatibility_report": str((artifacts_dir(base_dir, task_id) / "compatibility_report.md").resolve()),
        "source_grounding": str((artifacts_dir(base_dir, task_id) / "source_grounding.md").resolve()),
        "grounding_evidence_json": str((artifacts_dir(base_dir, task_id) / "grounding_evidence.json").resolve()),
        "grounding_evidence_report": str((artifacts_dir(base_dir, task_id) / "grounding_evidence_report.md").resolve()),
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
        "remote_handoff_contract_report": str(
            (artifacts_dir(base_dir, task_id) / "remote_handoff_contract_report.md").resolve()
        ),
        "remote_handoff_contract_json": str(remote_handoff_contract_path(base_dir, task_id).resolve()),
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
    state.execution_phase = "analysis_done"
    state.last_phase_checkpoint_at = utc_now()
    save_state(base_dir, state)
    (
        compatibility_result,
        execution_fit_result,
        knowledge_policy_result,
        validation_result,
        retry_policy_result,
        stop_policy_result,
        execution_budget_policy_result,
    ) = write_task_artifacts(
        base_dir, replace(state), retrieval_items, executor_result, grounding_evidence_override=grounding_evidence
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
    staged_candidates = _route_knowledge_to_staged(base_dir, state)
    save_state(base_dir, state)
    _record_phase_checkpoint(base_dir, state, "analysis_done", source="live_analysis")
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
                "route_dialect": state.route_dialect,
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
                "staged_candidate_count": len(staged_candidates),
                "grounding_refs": state.grounding_refs,
                "grounding_locked": state.grounding_locked,
                "execution_phase": state.execution_phase,
                "last_phase_checkpoint_at": state.last_phase_checkpoint_at,
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
