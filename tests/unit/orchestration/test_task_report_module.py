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


def test_reports_surface_source_anchor_dedup_missing_pointer_and_stored_preview(tmp_path: Path) -> None:
    state = _state(workspace_root=str(tmp_path))
    items = [
        _retrieval_item(
            path=".swl/tasks/task-1/knowledge/evidence-src-anchor-1.json",
            source_type="knowledge",
            preview="Retrieval preview from stored support.",
            citation=".swl/tasks/task-1/knowledge/evidence-src-anchor-1.json#evidence-src-anchor-1",
            metadata={
                "source_policy_label": "supporting_evidence",
                "source_policy_flags": ["source_anchor_support"],
                "storage_scope": "task_knowledge",
                "knowledge_object_id": "evidence-src-anchor-1",
                "source_ref": "file://workspace/docs/missing-source.md",
                "source_anchor_key": "anchor-1",
                "source_anchor_version": "source-anchor-v1",
                "content_hash": "sha256:abc",
                "parser_version": "wiki-compiler-v1",
                "span": "line:10-12",
                "heading_path": "Design > Anchors",
                "source_preview": "Stored source preview excerpt.",
            },
        ),
        _retrieval_item(
            path=".swl/tasks/task-2/artifacts/missing-source.md",
            source_type="artifacts",
            preview="Duplicate fallback preview.",
            citation=".swl/tasks/task-2/artifacts/missing-source.md#L10-L12",
            metadata={
                "source_policy_label": "artifact_source",
                "source_policy_flags": ["fallback_text_hit"],
                "source_ref": "file://workspace/docs/missing-source.md",
                "source_anchor_key": "anchor-1",
                "source_anchor_version": "source-anchor-v1",
                "content_hash": "sha256:abc",
                "parser_version": "wiki-compiler-v1",
                "span": "line:10-12",
                "heading_path": "Design > Anchors",
            },
        ),
    ]

    source_grounding = task_report.build_source_grounding(items, workspace_root=tmp_path, base_dir=tmp_path)
    retrieval_report = task_report.build_retrieval_report(state, items, base_dir=tmp_path)

    assert "source_anchor_key: anchor-1" in source_grounding
    assert "source_anchor_version: source-anchor-v1" in source_grounding
    assert "duplicate_anchor_count: 1" in source_grounding
    assert "source_pointer_status: missing" in source_grounding
    assert "source_pointer_reason: raw_material_missing" in source_grounding
    assert "source_preview_excerpt: Stored source preview excerpt." in source_grounding

    assert "evidence_pack_deduped_supporting_evidence_count: 1" in retrieval_report
    assert "evidence_pack_deduped_source_pointer_count: 1" in retrieval_report
    assert "deduped_total: 2" in retrieval_report
    assert "## EvidencePack Source Pointers" in retrieval_report
    assert "source_anchor_key: anchor-1" in retrieval_report
    assert "duplicate_anchor_count: 1" in retrieval_report
    assert "status: missing" in retrieval_report
    assert "reason: raw_material_missing" in retrieval_report
    assert "source_preview_excerpt: Stored source preview excerpt." in retrieval_report
