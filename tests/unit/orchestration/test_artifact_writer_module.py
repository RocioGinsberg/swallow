from __future__ import annotations

from pathlib import Path

from swallow.orchestration import artifact_writer
from swallow.orchestration.models import (
    CompatibilityResult,
    ExecutionBudgetPolicyResult,
    ExecutionFitResult,
    ExecutorResult,
    KnowledgePolicyResult,
    RetryPolicyResult,
    StopPolicyResult,
    TaskState,
    ValidationResult,
)
from swallow.surface_tools.paths import artifacts_dir


def test_create_task_artifact_paths_preserve_initial_path_keys(tmp_path: Path) -> None:
    paths = artifact_writer.build_create_task_artifact_paths(tmp_path, "artifact-task")

    assert paths["task_semantics_json"].endswith(".swl/tasks/artifact-task/task_semantics.json")
    assert paths["task_semantics_report"].endswith(
        ".swl/tasks/artifact-task/artifacts/task_semantics_report.md"
    )
    assert paths["knowledge_decisions_json"].endswith(".swl/tasks/artifact-task/knowledge_decisions.jsonl")
    assert paths["canonical_registry_json"].endswith(".swl/canonical_knowledge/registry.jsonl")
    assert paths["canonical_reuse_eval_report"].endswith(
        ".swl/tasks/artifact-task/artifacts/canonical_reuse_eval_report.md"
    )
    assert paths["remote_handoff_contract_report"].endswith(
        ".swl/tasks/artifact-task/artifacts/remote_handoff_contract_report.md"
    )
    assert "executor_output" not in paths


def test_run_task_artifact_paths_preserve_executor_and_optional_subtask_paths(tmp_path: Path) -> None:
    single_card_paths = artifact_writer.build_run_task_artifact_paths(tmp_path, "artifact-task")
    multi_card_paths = artifact_writer.build_run_task_artifact_paths(
        tmp_path,
        "artifact-task",
        multi_card_plan=True,
    )

    assert single_card_paths["executor_prompt"].endswith(
        ".swl/tasks/artifact-task/artifacts/executor_prompt.md"
    )
    assert single_card_paths["executor_output"].endswith(
        ".swl/tasks/artifact-task/artifacts/executor_output.md"
    )
    assert single_card_paths["executor_stdout"].endswith(
        ".swl/tasks/artifact-task/artifacts/executor_stdout.txt"
    )
    assert single_card_paths["executor_stderr"].endswith(
        ".swl/tasks/artifact-task/artifacts/executor_stderr.txt"
    )
    assert single_card_paths["summary"].endswith(".swl/tasks/artifact-task/artifacts/summary.md")
    assert single_card_paths["retrieval_json"].endswith(".swl/tasks/artifact-task/retrieval.json")
    assert "subtask_summary" not in single_card_paths
    assert multi_card_paths["subtask_summary"].endswith(
        ".swl/tasks/artifact-task/artifacts/subtask_summary.md"
    )


def test_write_parent_executor_artifacts_preserves_file_names_and_side_effects(tmp_path: Path) -> None:
    state = TaskState(
        task_id="artifact-task",
        title="Artifacts",
        goal="Write parent executor artifacts",
        workspace_root=str(tmp_path),
        route_dialect="markdown",
    )
    executor_result = ExecutorResult(
        executor_name="mock",
        status="completed",
        message="done",
        output="executor output",
        prompt="executor prompt",
        dialect="",
        stdout="stdout text",
        stderr="stderr text",
        side_effects={"relation_suggestions": []},
    )

    artifact_writer.write_parent_executor_artifacts(tmp_path, state, executor_result)

    root = artifacts_dir(tmp_path, state.task_id)
    assert (root / "executor_prompt.md").read_text(encoding="utf-8") == "dialect: markdown\n\nexecutor prompt\n"
    assert (root / "executor_output.md").read_text(encoding="utf-8") == "executor output\n"
    assert (root / "executor_stdout.txt").read_text(encoding="utf-8") == "stdout text\n"
    assert (root / "executor_stderr.txt").read_text(encoding="utf-8") == "stderr text\n"
    assert "relation_suggestions" in (root / "executor_side_effects.json").read_text(encoding="utf-8")


def test_write_prefixed_executor_artifacts_copies_only_executor_stream_files(tmp_path: Path) -> None:
    root = artifacts_dir(tmp_path, "artifact-task")
    root.mkdir(parents=True)
    (root / "executor_prompt.md").write_text("prompt", encoding="utf-8")
    (root / "executor_output.md").write_text("output", encoding="utf-8")
    (root / "executor_stdout.txt").write_text("stdout", encoding="utf-8")
    (root / "executor_stderr.txt").write_text("stderr", encoding="utf-8")
    (root / "summary.md").write_text("summary", encoding="utf-8")

    written = artifact_writer.write_prefixed_executor_artifacts(
        tmp_path,
        "artifact-task",
        prefix="fallback_primary",
    )

    assert written == [
        "fallback_primary_executor_prompt.md",
        "fallback_primary_executor_output.md",
        "fallback_primary_executor_stdout.txt",
        "fallback_primary_executor_stderr.txt",
    ]
    assert (root / "fallback_primary_executor_prompt.md").read_text(encoding="utf-8") == "prompt\n"
    assert (root / "fallback_primary_executor_output.md").read_text(encoding="utf-8") == "output\n"
    assert not (root / "fallback_primary_summary.md").exists()


def test_route_topology_execution_site_and_dispatch_builders_preserve_remote_shape() -> None:
    state = TaskState(
        task_id="artifact-record-task",
        title="Artifact records",
        goal="Build route and dispatch records",
        workspace_root=".",
        task_semantics={"constraints": ["preserve record shape"]},
        route_mode="mock-remote",
        route_name="mock-remote",
        route_backend="mock",
        route_executor_family="mock",
        route_execution_site="remote",
        route_remote_capable=True,
        route_transport_kind="mock_remote_transport",
        route_dialect="plain_text",
        route_reason="test route",
        route_capabilities={"execution_kind": "mock", "resumable": True},
        topology_route_name="mock-remote",
        topology_executor_family="mock",
        topology_execution_site="remote",
        topology_transport_kind="mock_remote_transport",
        topology_remote_capable_intent=True,
        topology_dispatch_status="planned",
        execution_site_contract_kind="remote_candidate",
        execution_site_boundary="cross_site_candidate",
        execution_site_contract_status="ready",
        execution_site_handoff_required=True,
        execution_site_contract_reason="remote candidate",
        current_attempt_id="attempt-0001",
        current_attempt_number=1,
        current_attempt_owner_kind="remote_executor",
        current_attempt_owner_ref="mock-remote-node",
        current_attempt_ownership_status="assigned",
        dispatch_requested_at="2026-05-03T00:00:00+00:00",
        dispatch_started_at="2026-05-03T00:01:00+00:00",
        artifact_paths={
            "task_semantics_json": ".swl/tasks/artifact-record-task/task_semantics.json",
            "execution_site_report": ".swl/tasks/artifact-record-task/artifacts/execution_site_report.md",
            "dispatch_report": ".swl/tasks/artifact-record-task/artifacts/dispatch_report.md",
            "remote_handoff_contract_report": ".swl/tasks/artifact-record-task/artifacts/remote_handoff_contract_report.md",
        },
    )

    route_record = artifact_writer.build_route_record(state)
    topology_record = artifact_writer.build_topology_record(state)
    execution_site_record = artifact_writer.build_execution_site_record(state)
    dispatch_record = artifact_writer.build_dispatch_record(state)
    remote_record = artifact_writer.build_remote_handoff_contract_record(state)

    assert route_record["name"] == "mock-remote"
    assert "resumable=True" in artifact_writer.build_route_report(state)
    assert topology_record["execution_site"] == "remote"
    assert execution_site_record["remote_handoff_contract_status"] == "ready"
    assert dispatch_record["remote_handoff_transport_truth"] == "mock_remote_transport"
    assert remote_record["contract_kind"] == "remote_handoff_candidate"
    assert remote_record["contract_status"] == "ready"
    assert remote_record["operator_ack_required"] is False
    assert "- transport_truth: mock_remote_transport" in artifact_writer.build_dispatch_report(state)
    assert "- contract_status: ready" in artifact_writer.build_remote_handoff_contract_report(remote_record)


def test_handoff_and_compatibility_builders_preserve_failure_guidance_shape() -> None:
    state = TaskState(
        task_id="artifact-handoff-task",
        title="Artifact handoff",
        goal="Build handoff records",
        workspace_root=".",
        status="failed",
        current_attempt_id="attempt-0001",
        current_attempt_number=1,
        artifact_paths={
            "summary": ".swl/tasks/artifact-handoff-task/artifacts/summary.md",
            "resume_note": ".swl/tasks/artifact-handoff-task/artifacts/resume_note.md",
            "executor_output": ".swl/tasks/artifact-handoff-task/artifacts/executor_output.md",
            "handoff_report": ".swl/tasks/artifact-handoff-task/artifacts/handoff_report.md",
        },
    )
    executor_result = ExecutorResult(
        executor_name="mock",
        status="failed",
        message="Execution failed.",
        failure_kind="launch_error",
    )
    compatibility_result = CompatibilityResult(status="passed", message="Compatibility passed.")
    execution_fit_result = ExecutionFitResult(status="passed", message="Execution fit passed.")
    knowledge_policy_result = KnowledgePolicyResult(status="passed", message="Knowledge policy passed.")
    validation_result = ValidationResult(status="failed", message="Validation failed.")
    retry_policy_result = RetryPolicyResult(
        status="passed",
        message="Retry allowed.",
        retryable=True,
        retry_decision="retry",
        max_attempts=3,
        remaining_attempts=2,
        checkpoint_required=True,
        recommended_action="Retry from checkpoint.",
    )
    stop_policy_result = StopPolicyResult(
        status="passed",
        message="Continue allowed.",
        stop_required=False,
        continue_allowed=True,
        stop_decision="continue",
        escalation_level="none",
        checkpoint_kind="retry",
        recommended_action="Continue.",
    )
    execution_budget_policy_result = ExecutionBudgetPolicyResult(
        status="passed",
        message="Budget available.",
        timeout_seconds=0,
        max_attempts=3,
        remaining_attempts=2,
        budget_state="available",
        timeout_state="not_configured",
        recommended_action="Continue.",
    )

    handoff_record = artifact_writer.build_handoff_record(
        state,
        executor_result,
        compatibility_result,
        execution_fit_result,
        knowledge_policy_result,
        validation_result,
        retry_policy_result,
        stop_policy_result,
        execution_budget_policy_result,
        failure_recommendation_builder=lambda _failure_kind: ["- Check configured executor binary."],
    )
    compatibility_record = artifact_writer.build_compatibility_record(
        state,
        executor_result,
        compatibility_result,
    )
    handoff_report = artifact_writer.build_handoff_report(handoff_record)

    assert handoff_record["status"] == "resume_from_failure"
    assert handoff_record["next_operator_action"] == "Check configured executor binary."
    assert handoff_record["required_inputs"] == [
        ".swl/tasks/artifact-handoff-task/artifacts/summary.md",
        ".swl/tasks/artifact-handoff-task/artifacts/resume_note.md",
        ".swl/tasks/artifact-handoff-task/artifacts/executor_output.md",
        ".swl/tasks/artifact-handoff-task/artifacts/handoff_report.md",
    ]
    assert "- status: resume_from_failure" in handoff_report
    assert compatibility_record["route"]["mode"] == state.route_mode
    assert compatibility_record["executor"]["failure_kind"] == "launch_error"


def test_artifact_writer_module_has_no_control_plane_write_surface() -> None:
    source = Path(artifact_writer.__file__).read_text(encoding="utf-8")
    public_names = {name for name in dir(artifact_writer) if not name.startswith("_")}

    assert "save_state" not in source
    assert "orchestration.harness" not in source
    assert "orchestration.executor" not in source
    assert "state_transitioned" not in source
    assert "entered_waiting_human" not in source
    assert public_names.isdisjoint(
        {
            "create_task",
            "run_task",
            "run_task_async",
            "advance",
            "transition",
            "waiting_human",
        }
    )
