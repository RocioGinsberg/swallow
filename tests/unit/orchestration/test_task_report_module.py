from __future__ import annotations

from pathlib import Path

from swallow.orchestration import task_report
from swallow.orchestration.models import RetrievalItem, TaskState


def _state(**overrides: object) -> TaskState:
    fields: dict[str, object] = {
        "task_id": "task-report-test",
        "title": "Task report",
        "goal": "Render retrieval reports",
        "workspace_root": ".",
        "artifact_paths": {
            "retrieval_json": ".swl/tasks/task-report-test/retrieval.json",
            "source_grounding": ".swl/tasks/task-report-test/artifacts/source_grounding.md",
            "task_memory": ".swl/tasks/task-report-test/memory.json",
        },
    }
    fields.update(overrides)
    return TaskState(**fields)


def _retrieval_item(**overrides: object) -> RetrievalItem:
    fields: dict[str, object] = {
        "path": "docs/example.md",
        "source_type": "knowledge",
        "score": 5,
        "preview": "Task report preview.",
        "title": "Task Report Source",
        "citation": "docs/example.md#task-report",
        "matched_terms": ["report"],
        "score_breakdown": {"keyword": 5},
        "metadata": {
            "source_policy_label": "knowledge",
            "source_policy_flags": [],
            "storage_scope": "workspace",
        },
    }
    fields.update(overrides)
    return RetrievalItem(**fields)


def test_task_report_module_exports_and_shape_are_stable(tmp_path: Path) -> None:
    source = Path(task_report.__file__).read_text(encoding="utf-8")

    assert "save_state" not in source
    assert "apply_proposal" not in source

    state = _state(workspace_root=str(tmp_path))
    item = _retrieval_item()

    source_grounding = task_report.build_source_grounding([item], workspace_root=tmp_path, base_dir=tmp_path)
    retrieval_report = task_report.build_retrieval_report(state, [item], base_dir=tmp_path)

    assert "# Source Grounding" in source_grounding
    assert "- [knowledge] docs/example.md#task-report" in source_grounding
    assert "  title: Task Report Source" in source_grounding
    assert "  source_policy_label: knowledge" in source_grounding

    assert "# Retrieval Report" in retrieval_report
    assert "- retrieval_count: 1" in retrieval_report
    assert "- retrieval_record_path: .swl/tasks/task-report-test/retrieval.json" in retrieval_report
    assert "- source_grounding_artifact: .swl/tasks/task-report-test/artifacts/source_grounding.md" in retrieval_report
    assert "## Top References" in retrieval_report
