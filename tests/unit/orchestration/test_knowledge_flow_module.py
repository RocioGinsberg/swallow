from __future__ import annotations

import json

from pathlib import Path

from swallow.orchestration import knowledge_flow
from swallow.surface_tools.paths import (
    knowledge_evidence_entry_path,
    knowledge_objects_path,
    knowledge_wiki_entry_path,
)


def _knowledge_objects() -> list[dict[str, object]]:
    return [
        {
            "object_id": "knowledge-evidence",
            "stage": "verified",
            "source_kind": "note",
            "source_ref": "notes.md",
            "captured_at": "2026-05-02T00:00:00Z",
            "task_linked": True,
            "evidence_status": "artifact_backed",
            "artifact_ref": ".swl/tasks/t/artifacts/evidence.md",
            "retrieval_eligible": True,
            "knowledge_reuse_scope": "retrieval_candidate",
            "canonicalization_intent": "promote",
            "promoted_by": "should-be-dropped-from-evidence",
            "text": "Reusable verified evidence.",
        },
        {
            "object_id": "knowledge-canonical",
            "stage": "canonical",
            "source_kind": "note",
            "source_ref": "notes.md",
            "captured_at": "2026-05-02T00:01:00Z",
            "task_linked": True,
            "evidence_status": "artifact_backed",
            "artifact_ref": ".swl/tasks/t/artifacts/canonical.md",
            "retrieval_eligible": True,
            "knowledge_reuse_scope": "retrieval_candidate",
            "canonicalization_intent": "promote",
            "canonical_id": "canonical-1",
            "promoted_by": "librarian",
            "promoted_at": "2026-05-02T00:02:00Z",
            "change_log_ref": ".swl/tasks/t/artifacts/librarian_change_log.json",
            "source_evidence_ids": ["knowledge-evidence"],
            "text": "Canonical knowledge.",
        },
    ]


def test_knowledge_store_write_plan_preserves_mirror_paths_and_stale_deletes(tmp_path: Path) -> None:
    task_id = "knowledge-flow-task"
    stale_evidence_path = knowledge_evidence_entry_path(tmp_path, task_id, "stale-evidence")
    stale_wiki_path = knowledge_wiki_entry_path(tmp_path, task_id, "stale-wiki")
    stale_evidence_path.parent.mkdir(parents=True)
    stale_wiki_path.parent.mkdir(parents=True)
    stale_evidence_path.write_text("{}", encoding="utf-8")
    stale_wiki_path.write_text("{}", encoding="utf-8")

    normalized_view, updates, deletes = knowledge_flow.build_knowledge_store_write_plan(
        tmp_path,
        task_id,
        _knowledge_objects(),
    )

    evidence_path = knowledge_evidence_entry_path(tmp_path, task_id, "knowledge-evidence")
    wiki_path = knowledge_wiki_entry_path(tmp_path, task_id, "knowledge-canonical")

    assert knowledge_objects_path(tmp_path, task_id) in updates
    assert evidence_path in updates
    assert wiki_path in updates
    assert set(deletes) == {stale_evidence_path, stale_wiki_path}
    assert normalized_view[0]["store_type"] == "evidence"
    assert normalized_view[0]["stage"] == "verified"
    assert "promoted_by" not in normalized_view[0]
    assert normalized_view[1]["store_type"] == "wiki"
    assert normalized_view[1]["stage"] == "canonical"
    assert normalized_view[1]["source_evidence_ids"] == ["knowledge-evidence"]
    assert json.loads(updates[evidence_path])["object_id"] == "knowledge-evidence"
    assert json.loads(updates[wiki_path])["object_id"] == "knowledge-canonical"


def test_knowledge_summary_payload_preserves_event_shape() -> None:
    payload = knowledge_flow.build_knowledge_summary_payload(
        _knowledge_objects(),
        knowledge_partition={
            "task_linked_count": 2,
            "reusable_candidate_count": 2,
            "task_linked": [],
            "reusable_candidates": [],
        },
        knowledge_index={
            "active_reusable_count": 1,
            "inactive_reusable_count": 1,
            "refreshed_at": "2026-05-02T00:03:00Z",
            "reusable_records": [],
            "inactive_records": [],
        },
    )

    assert payload == {
        "knowledge_objects_count": 2,
        "knowledge_stage_counts": {
            "raw": 0,
            "candidate": 0,
            "verified": 1,
            "canonical": 1,
        },
        "knowledge_evidence_counts": {
            "artifact_backed": 2,
            "source_only": 0,
            "unbacked": 0,
        },
        "knowledge_reuse_counts": {
            "retrieval_candidate": 2,
            "task_only": 0,
        },
        "knowledge_canonicalization_counts": {
            "not_requested": 0,
            "review_ready": 0,
            "promotion_ready": 1,
            "blocked_stage": 0,
            "blocked_evidence": 0,
            "canonical": 1,
        },
        "knowledge_partition": {
            "task_linked_count": 2,
            "reusable_candidate_count": 2,
        },
        "knowledge_index": {
            "active_reusable_count": 1,
            "inactive_reusable_count": 1,
            "refreshed_at": "2026-05-02T00:03:00Z",
        },
    }


def test_knowledge_objects_report_matches_orchestrator_report_contract() -> None:
    report = knowledge_flow.build_knowledge_objects_report(_knowledge_objects())

    assert "# Knowledge Objects Report" in report
    assert "- count: 2" in report
    assert "- verified: 1" in report
    assert "- canonical: 1" in report
    assert "- retrieval_candidate: 2" in report
    assert "- canonicalization_promotion_ready: 1" in report
    assert "- canonicalization_canonical: 1" in report
    assert "- id: knowledge-evidence" in report
    assert "  canonicalization_status: promotion_ready" in report
    assert "- id: knowledge-canonical" in report
    assert "  canonicalization_status: canonical" in report
    assert "  text: Canonical knowledge." in report


def test_knowledge_flow_module_has_no_control_plane_write_surface() -> None:
    source = Path(knowledge_flow.__file__).read_text(encoding="utf-8")
    public_names = {name for name in dir(knowledge_flow) if not name.startswith("_")}

    assert "save_state" not in source
    assert "append_event" not in source
    assert "apply_proposal" not in source
    assert "orchestration.harness" not in source
    assert "orchestration.executor" not in source
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
