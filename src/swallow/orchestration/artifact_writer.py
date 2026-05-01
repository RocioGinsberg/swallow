from __future__ import annotations

from pathlib import Path

from swallow.knowledge_retrieval.knowledge_suggestions import persist_executor_side_effects
from swallow.orchestration.models import ExecutorResult, TaskState
from swallow.surface_tools.paths import (
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
from swallow.surface_tools.workspace import resolve_path
from swallow.truth_governance.store import write_artifact


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
