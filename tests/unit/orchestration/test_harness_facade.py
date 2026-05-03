from __future__ import annotations

from pathlib import Path

from swallow.orchestration import harness, orchestrator
from swallow.orchestration.models import ExecutorResult, RetrievalItem, TaskState


FACADE_COMPATIBILITY_EXPORTS = (
    "run_execution",
    "run_retrieval",
    "run_retrieval_async",
    "write_task_artifacts",
    "write_task_artifacts_async",
    "build_remote_handoff_contract_record",
    "build_remote_handoff_contract_report",
    "build_resume_note",
    "build_retrieval_report",
    "build_source_grounding",
)


def _state(**overrides: object) -> TaskState:
    fields: dict[str, object] = {
        "task_id": "harness-facade-test",
        "title": "Harness facade",
        "goal": "Keep facade imports stable",
        "workspace_root": ".",
        "status": "running",
        "phase": "execution",
        "executor_name": "mock-executor",
        "executor_status": "completed",
        "execution_lifecycle": "completed",
        "task_semantics": {
            "source_kind": "operator_entry",
            "source_ref": "cli",
            "constraints": ["stay compatible"],
        },
        "artifact_paths": {
            "retrieval_json": ".swl/tasks/harness-facade-test/retrieval.json",
            "source_grounding": ".swl/tasks/harness-facade-test/artifacts/source_grounding.md",
            "retrieval_report": ".swl/tasks/harness-facade-test/artifacts/retrieval_report.md",
            "task_memory": ".swl/tasks/harness-facade-test/memory.json",
            "task_semantics_report": ".swl/tasks/harness-facade-test/artifacts/task_semantics_report.md",
            "summary": ".swl/tasks/harness-facade-test/artifacts/summary.md",
            "resume_note": ".swl/tasks/harness-facade-test/artifacts/resume_note.md",
        },
    }
    fields.update(overrides)
    return TaskState(**fields)


def _retrieval_item(**overrides: object) -> RetrievalItem:
    fields: dict[str, object] = {
        "path": "docs/example.md",
        "source_type": "knowledge",
        "score": 7,
        "preview": "Reusable context for the harness facade.",
        "title": "Harness Context",
        "citation": "docs/example.md#harness",
        "matched_terms": ["harness", "facade"],
        "score_breakdown": {"keyword": 7},
        "metadata": {
            "source_policy_label": "knowledge",
            "source_policy_flags": [],
            "storage_scope": "workspace",
        },
    }
    fields.update(overrides)
    return RetrievalItem(**fields)


def _executor_result(**overrides: object) -> ExecutorResult:
    fields: dict[str, object] = {
        "executor_name": "mock-executor",
        "status": "completed",
        "message": "Execution completed.",
        "output": "Executor output.",
        "prompt": "Executor prompt.",
        "dialect": "plain_text",
    }
    fields.update(overrides)
    return ExecutorResult(**fields)


def test_harness_facade_exports_external_compatibility_names() -> None:
    for name in FACADE_COMPATIBILITY_EXPORTS:
        assert hasattr(harness, name), f"missing harness compatibility export: {name}"


def test_orchestrator_keeps_patch_target_names_for_retrieval_and_artifact_pipeline() -> None:
    assert hasattr(orchestrator, "run_retrieval")
    assert hasattr(orchestrator, "write_task_artifacts")


def test_harness_facade_has_no_task_state_or_governance_write_surface() -> None:
    source = Path(harness.__file__).read_text(encoding="utf-8")

    assert "save_state" not in source
    assert "apply_proposal" not in source


def test_source_grounding_report_preserves_top_source_shape(tmp_path: Path) -> None:
    report = harness.build_source_grounding([_retrieval_item()], workspace_root=tmp_path, base_dir=tmp_path)

    assert "# Source Grounding" in report
    assert "- [knowledge] docs/example.md#harness" in report
    assert "  title: Harness Context" in report
    assert "  source_policy_label: knowledge" in report
    assert "  matched_terms: harness, facade" in report
    assert "  preview: Reusable context for the harness facade." in report


def test_retrieval_report_preserves_summary_and_reference_shape(tmp_path: Path) -> None:
    state = _state(workspace_root=str(tmp_path))

    report = harness.build_retrieval_report(state, [_retrieval_item()], base_dir=tmp_path)

    assert "# Retrieval Report" in report
    assert "- retrieval_count: 1" in report
    assert "- retrieval_record_path: .swl/tasks/harness-facade-test/retrieval.json" in report
    assert "- source_grounding_artifact: .swl/tasks/harness-facade-test/artifacts/source_grounding.md" in report
    assert "## Top References" in report
    assert "- [knowledge] docs/example.md#harness" in report
    assert "  title: Harness Context" in report


def test_remote_handoff_contract_local_route_shape_is_stable() -> None:
    record = harness.build_remote_handoff_contract_record(_state())
    report = harness.build_remote_handoff_contract_report(record)

    assert record["contract_kind"] == "not_applicable"
    assert record["contract_status"] == "not_needed"
    assert record["remote_candidate"] is False
    assert record["transport_truth"] == "local_only"
    assert "- contract_kind: not_applicable" in report
    assert "- remote_candidate: no" in report
    assert "- transport_truth: local_only" in report


def test_resume_note_preserves_ready_state_and_handoff_sections() -> None:
    note = harness.build_resume_note(
        _state(),
        [_retrieval_item()],
        _executor_result(),
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    )

    assert "# Resume Note for harness-facade-test" in note
    assert "## Ready State" in note
    assert "- task: Harness facade" in note
    assert "- top retrieved references: docs/example.md#harness" in note
    assert "- executor: mock-executor" in note
    assert "## Hand-off" in note
    assert "- latest executor message: Execution completed." in note
