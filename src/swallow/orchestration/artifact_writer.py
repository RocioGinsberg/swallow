from __future__ import annotations

from pathlib import Path
from typing import Callable

from swallow.orchestration.checkpoint_snapshot import build_checkpoint_snapshot_report, evaluate_checkpoint_snapshot
from swallow.orchestration.compatibility import build_compatibility_report, evaluate_route_compatibility
from swallow.orchestration.execution_budget_policy import (
    build_execution_budget_policy_report,
    evaluate_execution_budget_policy,
    normalize_token_cost_limit,
)
from swallow.orchestration.execution_fit import build_execution_fit_report, evaluate_execution_fit
from swallow.knowledge_retrieval.knowledge_plane import (
    evaluate_knowledge_policy,
    persist_executor_side_effects,
    render_knowledge_policy_report as render_knowledge_policy_report,
)
from swallow.orchestration.models import (
    CheckpointSnapshotResult,
    CompatibilityResult,
    Event,
    ExecutionBudgetPolicyResult,
    ExecutionFitResult,
    ExecutorResult,
    HandoffContractSchema,
    KnowledgePolicyResult,
    RetryPolicyResult,
    StopPolicyResult,
    TaskState,
    ValidationResult,
)
from swallow.orchestration.retry_policy import build_retry_policy_report, evaluate_retry_policy
from swallow.orchestration.stop_policy import build_stop_policy_report, evaluate_stop_policy
from swallow.application.infrastructure.paths import (
    artifacts_dir,
    capability_assembly_path,
    capability_manifest_path,
    canonical_registry_index_path,
    canonical_registry_path,
    canonical_reuse_eval_path,
    canonical_reuse_policy_path,
    canonical_reuse_regression_path,
    checkpoint_snapshot_path,
    compatibility_path,
    dispatch_path,
    execution_budget_policy_path,
    execution_fit_path,
    execution_site_path,
    handoff_path,
    knowledge_decisions_path,
    knowledge_index_path,
    knowledge_objects_path,
    knowledge_partition_path,
    knowledge_policy_path,
    memory_path,
    remote_handoff_contract_path,
    retry_policy_path,
    retrieval_path,
    route_path,
    stop_policy_path,
    task_semantics_path,
    topology_path,
    validation_path,
)
from swallow.application.infrastructure.workspace import resolve_path
from swallow.truth_governance.store import (
    append_event,
    save_checkpoint_snapshot,
    save_compatibility,
    save_execution_budget_policy,
    save_execution_fit,
    save_knowledge_policy,
    save_retry_policy,
    save_stop_policy,
    save_validation,
    write_artifact,
)
from swallow.orchestration.validator import build_validation_report, validate_run_outputs


EXECUTOR_ARTIFACT_NAMES = (
    "executor_prompt.md",
    "executor_output.md",
    "executor_stdout.txt",
    "executor_stderr.txt",
)


def _resolved_path_string(path: Path) -> str:
    return str(resolve_path(path))


def build_create_task_artifact_paths(base_dir: Path, task_id: str) -> dict[str, str]:
    return {
        "task_semantics_json": _resolved_path_string(task_semantics_path(base_dir, task_id)),
        "task_semantics_report": _resolved_path_string(artifacts_dir(base_dir, task_id) / "task_semantics_report.md"),
        "knowledge_objects_json": _resolved_path_string(knowledge_objects_path(base_dir, task_id)),
        "knowledge_objects_report": _resolved_path_string(artifacts_dir(base_dir, task_id) / "knowledge_objects_report.md"),
        "librarian_change_log": _resolved_path_string(artifacts_dir(base_dir, task_id) / "librarian_change_log.json"),
        "librarian_change_log_report": _resolved_path_string(
            artifacts_dir(base_dir, task_id) / "librarian_change_log_report.md"
        ),
        "wiki_compiler_prompt_pack": _resolved_path_string(
            artifacts_dir(base_dir, task_id) / "wiki_compiler_prompt_pack.json"
        ),
        "wiki_compiler_result": _resolved_path_string(artifacts_dir(base_dir, task_id) / "wiki_compiler_result.json"),
        "knowledge_partition_json": _resolved_path_string(knowledge_partition_path(base_dir, task_id)),
        "knowledge_partition_report": _resolved_path_string(
            artifacts_dir(base_dir, task_id) / "knowledge_partition_report.md"
        ),
        "knowledge_index_json": _resolved_path_string(knowledge_index_path(base_dir, task_id)),
        "knowledge_index_report": _resolved_path_string(artifacts_dir(base_dir, task_id) / "knowledge_index_report.md"),
        "knowledge_decisions_json": _resolved_path_string(knowledge_decisions_path(base_dir, task_id)),
        "knowledge_decisions_report": _resolved_path_string(
            artifacts_dir(base_dir, task_id) / "knowledge_decisions_report.md"
        ),
        "canonical_registry_json": _resolved_path_string(canonical_registry_path(base_dir)),
        "canonical_registry_report": _resolved_path_string(artifacts_dir(base_dir, task_id) / "canonical_registry_report.md"),
        "canonical_registry_index_json": _resolved_path_string(canonical_registry_index_path(base_dir)),
        "canonical_registry_index_report": _resolved_path_string(
            artifacts_dir(base_dir, task_id) / "canonical_registry_index_report.md"
        ),
        "canonical_reuse_policy_json": _resolved_path_string(canonical_reuse_policy_path(base_dir)),
        "canonical_reuse_policy_report": _resolved_path_string(
            artifacts_dir(base_dir, task_id) / "canonical_reuse_policy_report.md"
        ),
        "canonical_reuse_eval_json": _resolved_path_string(canonical_reuse_eval_path(base_dir, task_id)),
        "canonical_reuse_eval_report": _resolved_path_string(
            artifacts_dir(base_dir, task_id) / "canonical_reuse_eval_report.md"
        ),
        "canonical_reuse_regression_json": _resolved_path_string(canonical_reuse_regression_path(base_dir, task_id)),
        "remote_handoff_contract_json": _resolved_path_string(remote_handoff_contract_path(base_dir, task_id)),
        "remote_handoff_contract_report": _resolved_path_string(
            artifacts_dir(base_dir, task_id) / "remote_handoff_contract_report.md"
        ),
        "checkpoint_snapshot_json": _resolved_path_string(checkpoint_snapshot_path(base_dir, task_id)),
        "checkpoint_snapshot_report": _resolved_path_string(
            artifacts_dir(base_dir, task_id) / "checkpoint_snapshot_report.md"
        ),
    }


def build_run_task_artifact_paths(
    base_dir: Path,
    task_id: str,
    *,
    multi_card_plan: bool = False,
) -> dict[str, str]:
    artifact_paths = {
        "executor_prompt": _resolved_path_string(artifacts_dir(base_dir, task_id) / "executor_prompt.md"),
        "executor_output": _resolved_path_string(artifacts_dir(base_dir, task_id) / "executor_output.md"),
        "executor_stdout": _resolved_path_string(artifacts_dir(base_dir, task_id) / "executor_stdout.txt"),
        "executor_stderr": _resolved_path_string(artifacts_dir(base_dir, task_id) / "executor_stderr.txt"),
        "task_semantics_json": _resolved_path_string(task_semantics_path(base_dir, task_id)),
        "task_semantics_report": _resolved_path_string(artifacts_dir(base_dir, task_id) / "task_semantics_report.md"),
        "knowledge_objects_json": _resolved_path_string(knowledge_objects_path(base_dir, task_id)),
        "knowledge_objects_report": _resolved_path_string(artifacts_dir(base_dir, task_id) / "knowledge_objects_report.md"),
        "librarian_change_log": _resolved_path_string(artifacts_dir(base_dir, task_id) / "librarian_change_log.json"),
        "librarian_change_log_report": _resolved_path_string(
            artifacts_dir(base_dir, task_id) / "librarian_change_log_report.md"
        ),
        "wiki_compiler_prompt_pack": _resolved_path_string(
            artifacts_dir(base_dir, task_id) / "wiki_compiler_prompt_pack.json"
        ),
        "wiki_compiler_result": _resolved_path_string(artifacts_dir(base_dir, task_id) / "wiki_compiler_result.json"),
        "knowledge_partition_json": _resolved_path_string(knowledge_partition_path(base_dir, task_id)),
        "knowledge_partition_report": _resolved_path_string(
            artifacts_dir(base_dir, task_id) / "knowledge_partition_report.md"
        ),
        "knowledge_index_json": _resolved_path_string(knowledge_index_path(base_dir, task_id)),
        "knowledge_index_report": _resolved_path_string(artifacts_dir(base_dir, task_id) / "knowledge_index_report.md"),
        "knowledge_policy_json": _resolved_path_string(knowledge_policy_path(base_dir, task_id)),
        "canonical_reuse_policy_json": _resolved_path_string(canonical_reuse_policy_path(base_dir)),
        "knowledge_policy_report": _resolved_path_string(artifacts_dir(base_dir, task_id) / "knowledge_policy_report.md"),
        "canonical_reuse_policy_report": _resolved_path_string(
            artifacts_dir(base_dir, task_id) / "canonical_reuse_policy_report.md"
        ),
        "summary": _resolved_path_string(artifacts_dir(base_dir, task_id) / "summary.md"),
        "resume_note": _resolved_path_string(artifacts_dir(base_dir, task_id) / "resume_note.md"),
        "route_report": _resolved_path_string(artifacts_dir(base_dir, task_id) / "route_report.md"),
        "compatibility_report": _resolved_path_string(artifacts_dir(base_dir, task_id) / "compatibility_report.md"),
        "source_grounding": _resolved_path_string(artifacts_dir(base_dir, task_id) / "source_grounding.md"),
        "grounding_evidence_json": _resolved_path_string(artifacts_dir(base_dir, task_id) / "grounding_evidence.json"),
        "grounding_evidence_report": _resolved_path_string(
            artifacts_dir(base_dir, task_id) / "grounding_evidence_report.md"
        ),
        "retrieval_report": _resolved_path_string(artifacts_dir(base_dir, task_id) / "retrieval_report.md"),
        "retrieval_json": _resolved_path_string(retrieval_path(base_dir, task_id)),
        "validation_report": _resolved_path_string(artifacts_dir(base_dir, task_id) / "validation_report.md"),
        "compatibility_json": _resolved_path_string(compatibility_path(base_dir, task_id)),
        "validation_json": _resolved_path_string(validation_path(base_dir, task_id)),
        "task_memory": _resolved_path_string(memory_path(base_dir, task_id)),
        "capability_manifest_json": _resolved_path_string(capability_manifest_path(base_dir, task_id)),
        "capability_assembly_json": _resolved_path_string(capability_assembly_path(base_dir, task_id)),
        "route_json": _resolved_path_string(route_path(base_dir, task_id)),
        "topology_report": _resolved_path_string(artifacts_dir(base_dir, task_id) / "topology_report.md"),
        "topology_json": _resolved_path_string(topology_path(base_dir, task_id)),
        "execution_site_report": _resolved_path_string(artifacts_dir(base_dir, task_id) / "execution_site_report.md"),
        "execution_site_json": _resolved_path_string(execution_site_path(base_dir, task_id)),
        "dispatch_report": _resolved_path_string(artifacts_dir(base_dir, task_id) / "dispatch_report.md"),
        "dispatch_json": _resolved_path_string(dispatch_path(base_dir, task_id)),
        "handoff_report": _resolved_path_string(artifacts_dir(base_dir, task_id) / "handoff_report.md"),
        "handoff_json": _resolved_path_string(handoff_path(base_dir, task_id)),
        "remote_handoff_contract_report": _resolved_path_string(
            artifacts_dir(base_dir, task_id) / "remote_handoff_contract_report.md"
        ),
        "remote_handoff_contract_json": _resolved_path_string(remote_handoff_contract_path(base_dir, task_id)),
        "execution_fit_report": _resolved_path_string(artifacts_dir(base_dir, task_id) / "execution_fit_report.md"),
        "execution_fit_json": _resolved_path_string(execution_fit_path(base_dir, task_id)),
        "retry_policy_report": _resolved_path_string(artifacts_dir(base_dir, task_id) / "retry_policy_report.md"),
        "retry_policy_json": _resolved_path_string(retry_policy_path(base_dir, task_id)),
        "execution_budget_policy_report": _resolved_path_string(
            artifacts_dir(base_dir, task_id) / "execution_budget_policy_report.md"
        ),
        "execution_budget_policy_json": _resolved_path_string(execution_budget_policy_path(base_dir, task_id)),
        "stop_policy_report": _resolved_path_string(artifacts_dir(base_dir, task_id) / "stop_policy_report.md"),
        "stop_policy_json": _resolved_path_string(stop_policy_path(base_dir, task_id)),
        "checkpoint_snapshot_report": _resolved_path_string(
            artifacts_dir(base_dir, task_id) / "checkpoint_snapshot_report.md"
        ),
        "checkpoint_snapshot_json": _resolved_path_string(checkpoint_snapshot_path(base_dir, task_id)),
    }
    if multi_card_plan:
        artifact_paths["subtask_summary"] = _resolved_path_string(
            artifacts_dir(base_dir, task_id) / "subtask_summary.md"
        )
    return artifact_paths


def write_parent_executor_artifacts(
    base_dir: Path,
    state: TaskState,
    executor_result: ExecutorResult,
) -> None:
    prompt_with_dialect = (
        f"dialect: {executor_result.dialect or state.route_dialect or 'plain_text'}\n\n{executor_result.prompt}"
    )
    write_artifact(base_dir, state.task_id, "executor_prompt.md", prompt_with_dialect)
    write_artifact(base_dir, state.task_id, "executor_output.md", executor_result.output or executor_result.message)
    write_artifact(base_dir, state.task_id, "executor_stdout.txt", executor_result.stdout)
    write_artifact(base_dir, state.task_id, "executor_stderr.txt", executor_result.stderr)
    persist_executor_side_effects(base_dir, state.task_id, executor_result.side_effects)


def write_prefixed_executor_artifacts(
    base_dir: Path,
    task_id: str,
    *,
    prefix: str,
) -> list[str]:
    written: list[str] = []
    task_artifacts_dir = artifacts_dir(base_dir, task_id)
    for artifact_name in EXECUTOR_ARTIFACT_NAMES:
        source_path = task_artifacts_dir / artifact_name
        if not source_path.exists():
            continue
        prefixed_name = f"{prefix}_{artifact_name}"
        write_artifact(
            base_dir,
            task_id,
            prefixed_name,
            source_path.read_text(encoding="utf-8", errors="replace"),
        )
        written.append(prefixed_name)
    return written


def format_route_capabilities(capabilities: dict[str, object]) -> str:
    if not capabilities:
        return "none"
    ordered_keys = [
        "execution_kind",
        "supports_tool_loop",
        "filesystem_access",
        "network_access",
        "deterministic",
        "resumable",
    ]
    return ", ".join(f"{key}={capabilities.get(key)}" for key in ordered_keys if key in capabilities)


def build_route_record(state: TaskState) -> dict[str, object]:
    return {
        "mode": state.route_mode,
        "name": state.route_name,
        "backend": state.route_backend,
        "executor_family": state.route_executor_family,
        "execution_site": state.route_execution_site,
        "remote_capable": state.route_remote_capable,
        "transport_kind": state.route_transport_kind,
        "model_hint": state.route_model_hint,
        "dialect": state.route_dialect,
        "reason": state.route_reason,
        "capabilities": state.route_capabilities,
    }


def build_route_report(state: TaskState) -> str:
    return "\n".join(
        [
            "# Route Report",
            "",
            f"- mode: {state.route_mode}",
            f"- name: {state.route_name}",
            f"- backend: {state.route_backend}",
            f"- executor_family: {state.route_executor_family}",
            f"- execution_site: {state.route_execution_site}",
            f"- remote_capable: {'yes' if state.route_remote_capable else 'no'}",
            f"- transport_kind: {state.route_transport_kind}",
            f"- model_hint: {state.route_model_hint}",
            f"- dialect: {state.route_dialect}",
            f"- reason: {state.route_reason}",
            f"- capabilities: {format_route_capabilities(state.route_capabilities)}",
        ]
    )


def build_topology_record(state: TaskState) -> dict[str, object]:
    return {
        "route_name": state.topology_route_name,
        "executor_family": state.topology_executor_family,
        "execution_site": state.topology_execution_site,
        "transport_kind": state.topology_transport_kind,
        "remote_capable_intent": state.topology_remote_capable_intent,
        "dispatch_status": state.topology_dispatch_status,
        "execution_lifecycle": state.execution_lifecycle,
    }


def build_topology_report(state: TaskState) -> str:
    return "\n".join(
        [
            "# Topology Report",
            "",
            f"- route_name: {state.topology_route_name}",
            f"- executor_family: {state.topology_executor_family}",
            f"- execution_site: {state.topology_execution_site}",
            f"- transport_kind: {state.topology_transport_kind}",
            f"- remote_capable_intent: {'yes' if state.topology_remote_capable_intent else 'no'}",
            f"- dispatch_status: {state.topology_dispatch_status}",
            f"- execution_lifecycle: {state.execution_lifecycle}",
        ]
    )


def build_execution_site_record(state: TaskState) -> dict[str, object]:
    remote_handoff = build_remote_handoff_contract_record(state)
    return {
        "contract_kind": state.execution_site_contract_kind,
        "boundary": state.execution_site_boundary,
        "contract_status": state.execution_site_contract_status,
        "handoff_required": state.execution_site_handoff_required,
        "reason": state.execution_site_contract_reason,
        "execution_site": state.topology_execution_site,
        "executor_family": state.topology_executor_family,
        "transport_kind": state.topology_transport_kind,
        "remote_capable_intent": state.topology_remote_capable_intent,
        "dispatch_status": state.topology_dispatch_status,
        "execution_lifecycle": state.execution_lifecycle,
        "remote_handoff_contract_kind": remote_handoff["contract_kind"],
        "remote_handoff_contract_status": remote_handoff["contract_status"],
        "remote_handoff_boundary": remote_handoff["handoff_boundary"],
        "remote_handoff_dispatch_readiness": remote_handoff["dispatch_readiness"],
        "remote_handoff_operator_ack_required": remote_handoff["operator_ack_required"],
    }


def build_execution_site_report(state: TaskState) -> str:
    remote_handoff = build_remote_handoff_contract_record(state)
    return "\n".join(
        [
            "# Execution Site Report",
            "",
            f"- contract_kind: {state.execution_site_contract_kind}",
            f"- boundary: {state.execution_site_boundary}",
            f"- contract_status: {state.execution_site_contract_status}",
            f"- handoff_required: {'yes' if state.execution_site_handoff_required else 'no'}",
            f"- reason: {state.execution_site_contract_reason}",
            f"- execution_site: {state.topology_execution_site}",
            f"- executor_family: {state.topology_executor_family}",
            f"- transport_kind: {state.topology_transport_kind}",
            f"- remote_capable_intent: {'yes' if state.topology_remote_capable_intent else 'no'}",
            f"- dispatch_status: {state.topology_dispatch_status}",
            f"- execution_lifecycle: {state.execution_lifecycle}",
            "",
            "## Remote Handoff Contract",
            f"- contract_kind: {remote_handoff['contract_kind']}",
            f"- contract_status: {remote_handoff['contract_status']}",
            f"- handoff_boundary: {remote_handoff['handoff_boundary']}",
            f"- transport_truth: {remote_handoff['transport_truth']}",
            f"- ownership_required: {remote_handoff['ownership_required']}",
            f"- dispatch_readiness: {remote_handoff['dispatch_readiness']}",
            f"- operator_ack_required: {'yes' if remote_handoff['operator_ack_required'] else 'no'}",
        ]
    )


def build_dispatch_record(state: TaskState) -> dict[str, object]:
    remote_handoff = build_remote_handoff_contract_record(state)
    return {
        "attempt_id": state.current_attempt_id,
        "attempt_number": state.current_attempt_number,
        "attempt_owner_kind": state.current_attempt_owner_kind,
        "attempt_owner_ref": state.current_attempt_owner_ref,
        "attempt_ownership_status": state.current_attempt_ownership_status,
        "attempt_owner_assigned_at": state.current_attempt_owner_assigned_at,
        "attempt_transfer_reason": state.current_attempt_transfer_reason,
        "route_name": state.route_name,
        "execution_site_contract_kind": state.execution_site_contract_kind,
        "execution_site_boundary": state.execution_site_boundary,
        "executor_family": state.topology_executor_family,
        "execution_site": state.topology_execution_site,
        "transport_kind": state.topology_transport_kind,
        "dispatch_status": state.topology_dispatch_status,
        "dispatch_requested_at": state.dispatch_requested_at,
        "dispatch_started_at": state.dispatch_started_at,
        "execution_lifecycle": state.execution_lifecycle,
        "remote_handoff_contract_kind": remote_handoff["contract_kind"],
        "remote_handoff_contract_status": remote_handoff["contract_status"],
        "remote_handoff_boundary": remote_handoff["handoff_boundary"],
        "remote_handoff_transport_truth": remote_handoff["transport_truth"],
        "remote_handoff_ownership_required": remote_handoff["ownership_required"],
        "remote_handoff_dispatch_readiness": remote_handoff["dispatch_readiness"],
        "remote_handoff_operator_ack_required": remote_handoff["operator_ack_required"],
    }


def build_dispatch_report(state: TaskState) -> str:
    remote_handoff = build_remote_handoff_contract_record(state)
    return "\n".join(
        [
            "# Dispatch Report",
            "",
            f"- attempt_id: {state.current_attempt_id or 'pending'}",
            f"- attempt_number: {state.current_attempt_number}",
            f"- attempt_owner_kind: {state.current_attempt_owner_kind}",
            f"- attempt_owner_ref: {state.current_attempt_owner_ref}",
            f"- attempt_ownership_status: {state.current_attempt_ownership_status}",
            f"- attempt_owner_assigned_at: {state.current_attempt_owner_assigned_at or 'pending'}",
            f"- attempt_transfer_reason: {state.current_attempt_transfer_reason or 'none'}",
            f"- route_name: {state.route_name}",
            f"- execution_site_contract_kind: {state.execution_site_contract_kind}",
            f"- execution_site_boundary: {state.execution_site_boundary}",
            f"- executor_family: {state.topology_executor_family}",
            f"- execution_site: {state.topology_execution_site}",
            f"- transport_kind: {state.topology_transport_kind}",
            f"- dispatch_status: {state.topology_dispatch_status}",
            f"- dispatch_requested_at: {state.dispatch_requested_at or 'pending'}",
            f"- dispatch_started_at: {state.dispatch_started_at or 'pending'}",
            f"- execution_lifecycle: {state.execution_lifecycle}",
            "",
            "## Remote Handoff Contract",
            f"- contract_kind: {remote_handoff['contract_kind']}",
            f"- contract_status: {remote_handoff['contract_status']}",
            f"- handoff_boundary: {remote_handoff['handoff_boundary']}",
            f"- transport_truth: {remote_handoff['transport_truth']}",
            f"- ownership_required: {remote_handoff['ownership_required']}",
            f"- dispatch_readiness: {remote_handoff['dispatch_readiness']}",
            f"- operator_ack_required: {'yes' if remote_handoff['operator_ack_required'] else 'no'}",
        ]
    )


def build_remote_handoff_contract_record(state: TaskState) -> dict[str, object]:
    remote_candidate = (
        state.execution_site_contract_kind == "remote_candidate"
        or state.execution_site_boundary == "cross_site_candidate"
        or state.topology_execution_site != "local"
        or state.topology_transport_kind not in {"local_process", "local_detached_process"}
        or state.topology_remote_capable_intent
    )
    context_pointers = [
        path
        for path in [
            state.artifact_paths.get("task_semantics_json", ""),
            state.artifact_paths.get("execution_site_report", ""),
            state.artifact_paths.get("dispatch_report", ""),
            state.artifact_paths.get("remote_handoff_contract_report", ""),
        ]
        if path
    ]
    constraints = [str(item) for item in state.task_semantics.get("constraints", []) if str(item)]
    if not remote_candidate:
        schema = HandoffContractSchema(
            goal=state.goal,
            constraints=constraints,
            done=["Current route remains inside the local execution baseline."],
            next_steps=["Continue through the existing local execution path."],
            context_pointers=context_pointers,
        )
        return {
            "contract_kind": "not_applicable",
            "contract_status": "not_needed",
            "handoff_boundary": "local_baseline",
            "contract_reason": "Current route remains inside the local execution baseline and does not require remote handoff planning.",
            "remote_candidate": False,
            "remote_capable_intent": state.topology_remote_capable_intent,
            "execution_site": state.topology_execution_site,
            "execution_site_contract_kind": state.execution_site_contract_kind,
            "execution_site_contract_status": state.execution_site_contract_status,
            "transport_kind": state.topology_transport_kind,
            "transport_truth": "local_only",
            "ownership_required": "no",
            "ownership_truth": "local_orchestrator_owned",
            "dispatch_readiness": "not_applicable",
            "dispatch_truth": state.topology_dispatch_status or "not_requested",
            "operator_ack_required": False,
            "next_owner_kind": state.current_attempt_owner_kind,
            "next_owner_ref": state.current_attempt_owner_ref,
            "blocking_reason": "",
            "recommended_next_action": "Continue through the existing local execution path.",
            **schema.to_dict(),
        }

    if state.topology_transport_kind == "mock_remote_transport":
        schema = HandoffContractSchema(
            goal=state.goal,
            constraints=constraints,
            done=["Mock remote dispatch contract approved for topology validation."],
            next_steps=["Run the mock remote executor and persist the resulting artifacts."],
            context_pointers=context_pointers,
        )
        return {
            "contract_kind": "remote_handoff_candidate",
            "contract_status": "ready",
            "handoff_boundary": "cross_site_candidate",
            "contract_reason": (
                "Current route targets the mock remote executor used for topology validation without introducing real transport."
            ),
            "remote_candidate": True,
            "remote_capable_intent": state.topology_remote_capable_intent,
            "execution_site": state.topology_execution_site,
            "execution_site_contract_kind": state.execution_site_contract_kind,
            "execution_site_contract_status": "ready",
            "transport_kind": state.topology_transport_kind,
            "transport_truth": "mock_remote_transport",
            "ownership_required": "yes",
            "ownership_truth": "mock_remote_executor_assigned",
            "dispatch_readiness": "ready",
            "dispatch_truth": state.topology_dispatch_status or "planned",
            "operator_ack_required": False,
            "next_owner_kind": "remote_executor",
            "next_owner_ref": "mock-remote-node",
            "blocking_reason": "",
            "recommended_next_action": "Dispatch to the mock remote executor.",
            **schema.to_dict(),
        }

    schema = HandoffContractSchema(
        goal=state.goal,
        constraints=constraints,
        done=["Remote candidate contract detected; dispatch remains blocked until contract review is complete."],
        next_steps=["Review the remote handoff contract before treating this task as ready for remote dispatch."],
        context_pointers=context_pointers,
    )
    return {
        "contract_kind": "remote_handoff_candidate",
        "contract_status": "planned",
        "handoff_boundary": "cross_site_candidate",
        "contract_reason": (
            "Current route declares a remote-capable or cross-site execution boundary, so an explicit remote handoff contract"
            " is required before any non-local dispatch."
        ),
        "remote_candidate": True,
        "remote_capable_intent": state.topology_remote_capable_intent,
        "execution_site": state.topology_execution_site,
        "execution_site_contract_kind": state.execution_site_contract_kind,
        "execution_site_contract_status": state.execution_site_contract_status,
        "transport_kind": state.topology_transport_kind,
        "transport_truth": "explicit_remote_transport_required",
        "ownership_required": "yes",
        "ownership_truth": "transfer_required_before_remote_dispatch",
        "dispatch_readiness": "contract_required",
        "dispatch_truth": state.topology_dispatch_status or "not_requested",
        "operator_ack_required": True,
        "next_owner_kind": "remote_executor",
        "next_owner_ref": "unassigned",
        "blocking_reason": (
            "Remote candidate execution cannot proceed until transport, ownership, and dispatch contract details are made explicit."
        ),
        "recommended_next_action": (
            "Review the remote handoff contract before treating this task as ready for remote dispatch."
        ),
        **schema.to_dict(),
    }


def build_remote_handoff_contract_report(record: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Remote Handoff Contract Report",
            "",
            f"- contract_kind: {record.get('contract_kind', 'pending')}",
            f"- contract_status: {record.get('contract_status', 'pending')}",
            f"- handoff_boundary: {record.get('handoff_boundary', 'pending')}",
            f"- contract_reason: {record.get('contract_reason', 'pending')}",
            f"- remote_candidate: {'yes' if record.get('remote_candidate', False) else 'no'}",
            f"- remote_capable_intent: {'yes' if record.get('remote_capable_intent', False) else 'no'}",
            f"- execution_site: {record.get('execution_site', 'pending')}",
            f"- execution_site_contract_kind: {record.get('execution_site_contract_kind', 'pending')}",
            f"- execution_site_contract_status: {record.get('execution_site_contract_status', 'pending')}",
            f"- transport_kind: {record.get('transport_kind', 'pending')}",
            f"- transport_truth: {record.get('transport_truth', 'pending')}",
            f"- ownership_required: {record.get('ownership_required', 'pending')}",
            f"- ownership_truth: {record.get('ownership_truth', 'pending')}",
            f"- dispatch_readiness: {record.get('dispatch_readiness', 'pending')}",
            f"- dispatch_truth: {record.get('dispatch_truth', 'pending')}",
            f"- operator_ack_required: {'yes' if record.get('operator_ack_required', False) else 'no'}",
            f"- next_owner_kind: {record.get('next_owner_kind', 'pending')}",
            f"- next_owner_ref: {record.get('next_owner_ref', 'pending')}",
            f"- blocking_reason: {record.get('blocking_reason', '') or 'none'}",
            f"- recommended_next_action: {record.get('recommended_next_action', 'pending')}",
            "",
            "## Unified Handoff Schema",
            f"- goal: {record.get('goal', 'pending')}",
            f"- constraints: {', '.join(record.get('constraints', [])) or 'none'}",
            f"- done: {', '.join(record.get('done', [])) or 'none'}",
            f"- next_steps: {', '.join(record.get('next_steps', [])) or 'none'}",
            f"- context_pointers: {', '.join(record.get('context_pointers', [])) or 'none'}",
        ]
    )


def build_handoff_record(
    state: TaskState,
    executor_result: ExecutorResult,
    compatibility_result: CompatibilityResult,
    execution_fit_result: ExecutionFitResult,
    knowledge_policy_result: KnowledgePolicyResult,
    validation_result: ValidationResult,
    retry_policy_result: RetryPolicyResult,
    stop_policy_result: StopPolicyResult,
    execution_budget_policy_result: ExecutionBudgetPolicyResult,
    *,
    failure_recommendation_builder: Callable[[str], list[str]] | None = None,
) -> dict[str, object]:
    remote_handoff = build_remote_handoff_contract_record(state)
    required_inputs = [
        state.artifact_paths.get("summary", ""),
        state.artifact_paths.get("resume_note", ""),
        state.artifact_paths.get("executor_output", ""),
        state.artifact_paths.get("handoff_report", ""),
    ]
    required_inputs = [path for path in required_inputs if path]
    knowledge_policy_review_required = is_knowledge_policy_review_required(
        executor_result,
        compatibility_result,
        execution_fit_result,
        knowledge_policy_result,
        validation_result,
    )
    if (
        executor_result.status == "completed"
        and compatibility_result.status != "failed"
        and execution_fit_result.status != "failed"
        and knowledge_policy_result.status != "failed"
        and validation_result.status != "failed"
    ):
        handoff_status = "review_completed_run"
        blocking_reason = ""
        next_operator_action = "Review summary.md and executor_output.md before starting the next task iteration."
        handoff_contract_status = "ready"
        handoff_contract_kind = "operator_review"
        handoff_contract_reason = "Completed run is ready for operator review and next-step selection."
        next_owner_kind = "operator"
        next_owner_ref = "swl_cli"
        expected_outputs = [
            "review decision recorded by the operator",
            "next task iteration selection",
        ]
    elif knowledge_policy_review_required:
        handoff_status = "knowledge_policy_review"
        blocking_reason = knowledge_policy_result.message
        next_operator_action = (
            "Review knowledge_policy_report.md and resolve blocked task knowledge before relying on retrieval reuse."
        )
        handoff_contract_status = "ready"
        handoff_contract_kind = "knowledge_policy_review"
        handoff_contract_reason = (
            "Executor completed, but knowledge policy requires operator review before the run can be treated as complete."
        )
        next_owner_kind = "operator"
        next_owner_ref = "swl_cli"
        expected_outputs = [
            "blocked knowledge reviewed by the operator",
            "knowledge object verified, rejected, or made non-reusable before rerun",
        ]
    else:
        handoff_status = "resume_from_failure"
        blocking_reason = executor_result.failure_kind or executor_result.message
        failure_steps = failure_recommendation_builder(executor_result.failure_kind) if failure_recommendation_builder else []
        next_operator_action = (
            failure_steps[0].lstrip("- ").strip() if failure_steps else "Resume from the latest failure context."
        )
        handoff_contract_status = "ready"
        handoff_contract_kind = "failure_resume"
        handoff_contract_reason = "Failure handoff is ready for operator-guided recovery from the latest attempt context."
        next_owner_kind = "operator"
        next_owner_ref = "swl_cli"
        expected_outputs = [
            "failure recovery decision",
            "corrected rerun or route adjustment",
        ]

    return {
        "status": handoff_status,
        "contract_status": handoff_contract_status,
        "contract_kind": handoff_contract_kind,
        "contract_reason": handoff_contract_reason,
        "task_status": state.status,
        "attempt_id": state.current_attempt_id,
        "attempt_number": state.current_attempt_number,
        "attempt_owner_kind": state.current_attempt_owner_kind,
        "attempt_owner_ref": state.current_attempt_owner_ref,
        "attempt_ownership_status": state.current_attempt_ownership_status,
        "attempt_owner_assigned_at": state.current_attempt_owner_assigned_at,
        "attempt_transfer_reason": state.current_attempt_transfer_reason,
        "execution_site_contract_kind": state.execution_site_contract_kind,
        "execution_site_boundary": state.execution_site_boundary,
        "execution_site_contract_status": state.execution_site_contract_status,
        "execution_site_handoff_required": state.execution_site_handoff_required,
        "execution_site": state.topology_execution_site,
        "executor_family": state.topology_executor_family,
        "dispatch_status": state.topology_dispatch_status,
        "execution_lifecycle": state.execution_lifecycle,
        "remote_handoff_contract_kind": remote_handoff["contract_kind"],
        "remote_handoff_contract_status": remote_handoff["contract_status"],
        "remote_handoff_boundary": remote_handoff["handoff_boundary"],
        "remote_handoff_transport_truth": remote_handoff["transport_truth"],
        "remote_handoff_ownership_required": remote_handoff["ownership_required"],
        "remote_handoff_dispatch_readiness": remote_handoff["dispatch_readiness"],
        "remote_handoff_operator_ack_required": remote_handoff["operator_ack_required"],
        "required_inputs": required_inputs,
        "expected_outputs": expected_outputs,
        "next_owner_kind": next_owner_kind,
        "next_owner_ref": next_owner_ref,
        "blocking_reason": blocking_reason,
        "next_operator_action": next_operator_action,
        "executor_status": executor_result.status,
        "failure_kind": executor_result.failure_kind,
        "compatibility_status": compatibility_result.status,
        "execution_fit_status": execution_fit_result.status,
        "retry_policy_status": retry_policy_result.status,
        "retryable": retry_policy_result.retryable,
        "retry_decision": retry_policy_result.retry_decision,
        "remaining_attempts": retry_policy_result.remaining_attempts,
        "checkpoint_required": retry_policy_result.checkpoint_required,
        "retry_recommended_action": retry_policy_result.recommended_action,
        "execution_budget_policy_status": execution_budget_policy_result.status,
        "timeout_seconds": execution_budget_policy_result.timeout_seconds,
        "budget_state": execution_budget_policy_result.budget_state,
        "timeout_state": execution_budget_policy_result.timeout_state,
        "budget_recommended_action": execution_budget_policy_result.recommended_action,
        "stop_policy_status": stop_policy_result.status,
        "stop_required": stop_policy_result.stop_required,
        "continue_allowed": stop_policy_result.continue_allowed,
        "stop_decision": stop_policy_result.stop_decision,
        "escalation_level": stop_policy_result.escalation_level,
        "checkpoint_kind": stop_policy_result.checkpoint_kind,
        "stop_recommended_action": stop_policy_result.recommended_action,
        "knowledge_policy_status": knowledge_policy_result.status,
        "validation_status": validation_result.status,
    }


def is_knowledge_policy_review_required(
    executor_result: ExecutorResult,
    compatibility_result: CompatibilityResult,
    execution_fit_result: ExecutionFitResult,
    knowledge_policy_result: KnowledgePolicyResult,
    validation_result: ValidationResult,
) -> bool:
    return (
        executor_result.status == "completed"
        and compatibility_result.status != "failed"
        and execution_fit_result.status != "failed"
        and knowledge_policy_result.status == "failed"
        and validation_result.status != "failed"
    )


def classify_task_terminal_state(
    executor_result: ExecutorResult,
    compatibility_result: CompatibilityResult,
    execution_fit_result: ExecutionFitResult,
    knowledge_policy_result: KnowledgePolicyResult,
    validation_result: ValidationResult,
) -> tuple[str, str]:
    if is_knowledge_policy_review_required(
        executor_result,
        compatibility_result,
        execution_fit_result,
        knowledge_policy_result,
        validation_result,
    ):
        return "waiting_human", "completed"
    if (
        executor_result.status == "completed"
        and compatibility_result.status != "failed"
        and execution_fit_result.status != "failed"
        and knowledge_policy_result.status != "failed"
        and validation_result.status != "failed"
    ):
        return "completed", "completed"
    return "failed", "failed"


def build_handoff_report(handoff_record: dict[str, object]) -> str:
    lines = [
        "# Handoff Report",
        "",
        f"- status: {handoff_record.get('status', 'pending')}",
        f"- contract_status: {handoff_record.get('contract_status', 'pending')}",
        f"- contract_kind: {handoff_record.get('contract_kind', 'pending')}",
        f"- contract_reason: {handoff_record.get('contract_reason', 'pending')}",
        f"- task_status: {handoff_record.get('task_status', 'pending')}",
        f"- attempt_id: {handoff_record.get('attempt_id', 'pending')}",
        f"- attempt_number: {handoff_record.get('attempt_number', 0)}",
        f"- attempt_owner_kind: {handoff_record.get('attempt_owner_kind', 'pending')}",
        f"- attempt_owner_ref: {handoff_record.get('attempt_owner_ref', 'pending')}",
        f"- attempt_ownership_status: {handoff_record.get('attempt_ownership_status', 'pending')}",
        f"- attempt_owner_assigned_at: {handoff_record.get('attempt_owner_assigned_at', 'pending')}",
        f"- attempt_transfer_reason: {handoff_record.get('attempt_transfer_reason', '') or 'none'}",
        f"- execution_site_contract_kind: {handoff_record.get('execution_site_contract_kind', 'pending')}",
        f"- execution_site_boundary: {handoff_record.get('execution_site_boundary', 'pending')}",
        f"- execution_site_contract_status: {handoff_record.get('execution_site_contract_status', 'pending')}",
        f"- execution_site_handoff_required: {'yes' if handoff_record.get('execution_site_handoff_required', False) else 'no'}",
        f"- execution_site: {handoff_record.get('execution_site', 'pending')}",
        f"- executor_family: {handoff_record.get('executor_family', 'pending')}",
        f"- dispatch_status: {handoff_record.get('dispatch_status', 'pending')}",
        f"- execution_lifecycle: {handoff_record.get('execution_lifecycle', 'pending')}",
        f"- remote_handoff_contract_kind: {handoff_record.get('remote_handoff_contract_kind', 'pending')}",
        f"- remote_handoff_contract_status: {handoff_record.get('remote_handoff_contract_status', 'pending')}",
        f"- remote_handoff_boundary: {handoff_record.get('remote_handoff_boundary', 'pending')}",
        f"- remote_handoff_transport_truth: {handoff_record.get('remote_handoff_transport_truth', 'pending')}",
        f"- remote_handoff_ownership_required: {handoff_record.get('remote_handoff_ownership_required', 'pending')}",
        f"- remote_handoff_dispatch_readiness: {handoff_record.get('remote_handoff_dispatch_readiness', 'pending')}",
        f"- remote_handoff_operator_ack_required: {'yes' if handoff_record.get('remote_handoff_operator_ack_required', False) else 'no'}",
        f"- executor_status: {handoff_record.get('executor_status', 'pending')}",
        f"- failure_kind: {handoff_record.get('failure_kind', '') or 'none'}",
        f"- compatibility_status: {handoff_record.get('compatibility_status', 'pending')}",
        f"- execution_fit_status: {handoff_record.get('execution_fit_status', 'pending')}",
        f"- retry_policy_status: {handoff_record.get('retry_policy_status', 'pending')}",
        f"- retryable: {'yes' if handoff_record.get('retryable', False) else 'no'}",
        f"- retry_decision: {handoff_record.get('retry_decision', 'pending')}",
        f"- remaining_attempts: {handoff_record.get('remaining_attempts', 0)}",
        f"- checkpoint_required: {'yes' if handoff_record.get('checkpoint_required', False) else 'no'}",
        f"- retry_recommended_action: {handoff_record.get('retry_recommended_action', 'pending')}",
        f"- execution_budget_policy_status: {handoff_record.get('execution_budget_policy_status', 'pending')}",
        f"- timeout_seconds: {handoff_record.get('timeout_seconds', 0)}",
        f"- budget_state: {handoff_record.get('budget_state', 'pending')}",
        f"- timeout_state: {handoff_record.get('timeout_state', 'pending')}",
        f"- budget_recommended_action: {handoff_record.get('budget_recommended_action', 'pending')}",
        f"- stop_policy_status: {handoff_record.get('stop_policy_status', 'pending')}",
        f"- stop_required: {'yes' if handoff_record.get('stop_required', False) else 'no'}",
        f"- continue_allowed: {'yes' if handoff_record.get('continue_allowed', False) else 'no'}",
        f"- stop_decision: {handoff_record.get('stop_decision', 'pending')}",
        f"- escalation_level: {handoff_record.get('escalation_level', 'pending')}",
        f"- checkpoint_kind: {handoff_record.get('checkpoint_kind', 'pending')}",
        f"- stop_recommended_action: {handoff_record.get('stop_recommended_action', 'pending')}",
        f"- knowledge_policy_status: {handoff_record.get('knowledge_policy_status', 'pending')}",
        f"- validation_status: {handoff_record.get('validation_status', 'pending')}",
        f"- next_owner_kind: {handoff_record.get('next_owner_kind', 'pending')}",
        f"- next_owner_ref: {handoff_record.get('next_owner_ref', 'pending')}",
        f"- blocking_reason: {handoff_record.get('blocking_reason', '') or 'none'}",
        f"- next_operator_action: {handoff_record.get('next_operator_action', 'pending')}",
        "",
        "## Required Inputs",
    ]
    required_inputs = handoff_record.get("required_inputs", [])
    if isinstance(required_inputs, list) and required_inputs:
        lines.extend([f"- {item}" for item in required_inputs])
    else:
        lines.append("- none")
    lines.extend(["", "## Expected Outputs"])
    expected_outputs = handoff_record.get("expected_outputs", [])
    if isinstance(expected_outputs, list) and expected_outputs:
        lines.extend([f"- {item}" for item in expected_outputs])
    else:
        lines.append("- none")
    return "\n".join(lines)


def build_compatibility_record(
    state: TaskState,
    executor_result: ExecutorResult,
    compatibility_result: CompatibilityResult,
) -> dict[str, object]:
    return {
        "status": compatibility_result.status,
        "message": compatibility_result.message,
        "findings": [finding.to_dict() for finding in compatibility_result.findings],
        "route": build_route_record(state),
        "executor": {
            "name": executor_result.executor_name,
            "status": executor_result.status,
            "failure_kind": executor_result.failure_kind,
        },
    }


def validation_counts(result: ValidationResult) -> dict[str, int]:
    counts = {"pass": 0, "warn": 0, "fail": 0}
    for finding in result.findings:
        counts[finding.level] = counts.get(finding.level, 0) + 1
    return counts


def compatibility_counts(result: CompatibilityResult) -> dict[str, int]:
    counts = {"pass": 0, "warn": 0, "fail": 0}
    for finding in result.findings:
        counts[finding.level] = counts.get(finding.level, 0) + 1
    return counts


def execution_fit_counts(result: ExecutionFitResult) -> dict[str, int]:
    counts = {"pass": 0, "warn": 0, "fail": 0}
    for finding in result.findings:
        counts[finding.level] = counts.get(finding.level, 0) + 1
    return counts


def knowledge_policy_counts(result: KnowledgePolicyResult) -> dict[str, int]:
    counts = {"pass": 0, "warn": 0, "fail": 0}
    for finding in result.findings:
        counts[finding.level] = counts.get(finding.level, 0) + 1
    return counts


def write_compatibility_policy_artifacts(
    base_dir: Path,
    state: TaskState,
    executor_result: ExecutorResult,
) -> CompatibilityResult:
    result = evaluate_route_compatibility(state, executor_result)
    save_compatibility(base_dir, state.task_id, build_compatibility_record(state, executor_result, result))
    write_artifact(base_dir, state.task_id, "compatibility_report.md", build_compatibility_report(result))
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="compatibility.completed",
            message=result.message,
            payload={"status": result.status, "finding_counts": compatibility_counts(result)},
        ),
    )
    return result


def write_execution_fit_policy_artifacts(
    base_dir: Path,
    state: TaskState,
    executor_result: ExecutorResult,
) -> ExecutionFitResult:
    result = evaluate_execution_fit(state, executor_result)
    save_execution_fit(base_dir, state.task_id, result.to_dict())
    write_artifact(base_dir, state.task_id, "execution_fit_report.md", build_execution_fit_report(result))
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="execution_fit.completed",
            message=result.message,
            payload={"status": result.status, "finding_counts": execution_fit_counts(result)},
        ),
    )
    return result


def write_knowledge_policy_artifacts(base_dir: Path, state: TaskState) -> KnowledgePolicyResult:
    result = evaluate_knowledge_policy(state)
    save_knowledge_policy(base_dir, state.task_id, result.to_dict())
    write_artifact(base_dir, state.task_id, "knowledge_policy_report.md", render_knowledge_policy_report(result))
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="knowledge_policy.completed",
            message=result.message,
            payload={"status": result.status, "finding_counts": knowledge_policy_counts(result)},
        ),
    )
    return result


def write_validation_policy_artifacts(
    base_dir: Path,
    state: TaskState,
    retrieval_items: list[object],
    executor_result: ExecutorResult,
) -> ValidationResult:
    result = validate_run_outputs(state, retrieval_items, executor_result, state.artifact_paths)
    save_validation(base_dir, state.task_id, result)
    write_artifact(base_dir, state.task_id, "validation_report.md", build_validation_report(result))
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="validation.completed",
            message=result.message,
            payload={"status": result.status, "finding_counts": validation_counts(result)},
        ),
    )
    return result


def write_retry_policy_artifacts(
    base_dir: Path,
    state: TaskState,
    executor_result: ExecutorResult,
    compatibility_result: CompatibilityResult,
    execution_fit_result: ExecutionFitResult,
    knowledge_policy_result: KnowledgePolicyResult,
    validation_result: ValidationResult,
) -> RetryPolicyResult:
    result = evaluate_retry_policy(
        state,
        executor_result,
        compatibility_result,
        execution_fit_result,
        knowledge_policy_result,
        validation_result,
    )
    save_retry_policy(base_dir, state.task_id, result.to_dict())
    write_artifact(base_dir, state.task_id, "retry_policy_report.md", build_retry_policy_report(result))
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="retry_policy.completed",
            message=result.message,
            payload={
                "status": result.status,
                "retryable": result.retryable,
                "retry_decision": result.retry_decision,
                "remaining_attempts": result.remaining_attempts,
                "checkpoint_required": result.checkpoint_required,
            },
        ),
    )
    return result


def write_execution_budget_policy_artifacts(
    base_dir: Path,
    state: TaskState,
    retry_policy_result: RetryPolicyResult,
) -> ExecutionBudgetPolicyResult:
    result = evaluate_execution_budget_policy(
        retry_policy_result,
        base_dir=base_dir,
        task_id=state.task_id,
        token_cost_limit=normalize_token_cost_limit(
            state.task_semantics.get("token_cost_limit", 0.0) if state.task_semantics else 0.0
        ),
    )
    save_execution_budget_policy(base_dir, state.task_id, result.to_dict())
    write_artifact(
        base_dir,
        state.task_id,
        "execution_budget_policy_report.md",
        build_execution_budget_policy_report(result),
    )
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="execution_budget_policy.completed",
            message=result.message,
            payload={
                "status": result.status,
                "timeout_seconds": result.timeout_seconds,
                "budget_state": result.budget_state,
                "timeout_state": result.timeout_state,
                "remaining_attempts": result.remaining_attempts,
                "current_token_cost": result.current_token_cost,
                "token_cost_limit": result.token_cost_limit,
            },
        ),
    )
    return result


def write_stop_policy_artifacts(
    base_dir: Path,
    state: TaskState,
    executor_result: ExecutorResult,
    retry_policy_result: RetryPolicyResult,
) -> StopPolicyResult:
    result = evaluate_stop_policy(state, executor_result, retry_policy_result)
    save_stop_policy(base_dir, state.task_id, result.to_dict())
    write_artifact(base_dir, state.task_id, "stop_policy_report.md", build_stop_policy_report(result))
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="stop_policy.completed",
            message=result.message,
            payload={
                "status": result.status,
                "stop_required": result.stop_required,
                "continue_allowed": result.continue_allowed,
                "stop_decision": result.stop_decision,
                "escalation_level": result.escalation_level,
                "checkpoint_kind": result.checkpoint_kind,
            },
        ),
    )
    return result


def write_checkpoint_snapshot_artifacts(
    base_dir: Path,
    render_state: TaskState,
    handoff_record: dict[str, object],
    retry_policy_result: RetryPolicyResult,
    stop_policy_result: StopPolicyResult,
    execution_budget_policy_result: ExecutionBudgetPolicyResult,
) -> CheckpointSnapshotResult:
    result = evaluate_checkpoint_snapshot(
        render_state,
        handoff_record,
        retry_policy_result.to_dict(),
        stop_policy_result.to_dict(),
        execution_budget_policy_result.to_dict(),
    )
    save_checkpoint_snapshot(base_dir, render_state.task_id, result.to_dict())
    write_artifact(base_dir, render_state.task_id, "checkpoint_snapshot_report.md", build_checkpoint_snapshot_report(result))
    append_event(
        base_dir,
        Event(
            task_id=render_state.task_id,
            event_type="checkpoint_snapshot.completed",
            message=result.message,
            payload={
                "status": result.status,
                "checkpoint_state": result.checkpoint_state,
                "execution_phase": result.execution_phase,
                "last_phase_checkpoint_at": result.last_phase_checkpoint_at,
                "recommended_path": result.recommended_path,
                "resume_ready": result.resume_ready,
            },
        ),
    )
    return result


def append_artifacts_written_event(
    base_dir: Path,
    state: TaskState,
    *,
    final_status: str,
) -> None:
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="artifacts.written",
            message="Wrote summary, resume note, compatibility, and validation artifacts.",
            payload={
                "status": final_status,
                "phase": state.phase,
                "artifact_paths": {
                    "task_semantics_report": state.artifact_paths.get("task_semantics_report", ""),
                    "knowledge_objects_report": state.artifact_paths.get("knowledge_objects_report", ""),
                    "knowledge_partition_report": state.artifact_paths.get("knowledge_partition_report", ""),
                    "knowledge_index_report": state.artifact_paths.get("knowledge_index_report", ""),
                    "summary": state.artifact_paths.get("summary", ""),
                    "resume_note": state.artifact_paths.get("resume_note", ""),
                    "route_report": state.artifact_paths.get("route_report", ""),
                    "topology_report": state.artifact_paths.get("topology_report", ""),
                    "execution_site_report": state.artifact_paths.get("execution_site_report", ""),
                    "dispatch_report": state.artifact_paths.get("dispatch_report", ""),
                    "handoff_report": state.artifact_paths.get("handoff_report", ""),
                    "execution_fit_report": state.artifact_paths.get("execution_fit_report", ""),
                    "retry_policy_report": state.artifact_paths.get("retry_policy_report", ""),
                    "execution_budget_policy_report": state.artifact_paths.get("execution_budget_policy_report", ""),
                    "stop_policy_report": state.artifact_paths.get("stop_policy_report", ""),
                    "compatibility_report": state.artifact_paths.get("compatibility_report", ""),
                    "knowledge_policy_report": state.artifact_paths.get("knowledge_policy_report", ""),
                    "source_grounding": state.artifact_paths.get("source_grounding", ""),
                    "grounding_evidence_json": state.artifact_paths.get("grounding_evidence_json", ""),
                    "grounding_evidence_report": state.artifact_paths.get("grounding_evidence_report", ""),
                    "retrieval_report": state.artifact_paths.get("retrieval_report", ""),
                    "validation_report": state.artifact_paths.get("validation_report", ""),
                    "task_memory": state.artifact_paths.get("task_memory", ""),
                },
            },
        ),
    )
