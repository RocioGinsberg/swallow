from __future__ import annotations

from pathlib import Path

from swallow.knowledge_retrieval import knowledge_plane
from swallow.knowledge_retrieval import knowledge_store
from swallow.surface_tools.paths import knowledge_evidence_entry_path, knowledge_objects_path, knowledge_wiki_entry_path
from swallow.truth_governance.store import save_knowledge_objects
from tests.helpers.workspace import read_json


def test_knowledge_plane_facade_exports_task_knowledge_api() -> None:
    assert knowledge_plane.load_task_knowledge_view is knowledge_store.load_task_knowledge_view
    assert knowledge_plane.persist_task_knowledge_view is knowledge_store.persist_task_knowledge_view
    assert knowledge_plane.load_task_evidence_entries is knowledge_store.load_task_evidence_entries


def test_knowledge_plane_facade_persists_evidence_and_wiki_layers(tmp_path: Path) -> None:
    save_knowledge_objects(
        tmp_path,
        "task-store",
        [
            {
                "object_id": "knowledge-0001",
                "text": "Keep this as evidence.",
                "stage": "verified",
                "evidence_status": "artifact_backed",
                "artifact_ref": ".swl/tasks/task-store/artifacts/evidence.md",
            },
            {
                "object_id": "knowledge-0002",
                "text": "Promoted canonical note.",
                "stage": "canonical",
                "evidence_status": "artifact_backed",
                "artifact_ref": ".swl/tasks/task-store/artifacts/canonical.md",
            },
        ],
        write_authority=knowledge_plane.OPERATOR_CANONICAL_WRITE_AUTHORITY,
    )

    legacy_payload = read_json(knowledge_objects_path(tmp_path, "task-store"))
    evidence_payload = read_json(knowledge_evidence_entry_path(tmp_path, "task-store", "knowledge-0001"))
    wiki_payload = read_json(knowledge_wiki_entry_path(tmp_path, "task-store", "knowledge-0002"))
    merged_view = knowledge_plane.load_task_knowledge_view(tmp_path, "task-store")

    assert legacy_payload[0]["store_type"] == "evidence"
    assert legacy_payload[1]["store_type"] == "wiki"
    assert evidence_payload["store_type"] == "evidence"
    assert wiki_payload["store_type"] == "wiki"
    assert wiki_payload["source_evidence_ids"] == ["knowledge-0002"]
    assert [item["object_id"] for item in merged_view] == ["knowledge-0001", "knowledge-0002"]
    assert merged_view[1]["stage"] == "canonical"
