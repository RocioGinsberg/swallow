from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from swallow.adapters.http.api import create_fastapi_app
from swallow.knowledge_retrieval.knowledge_plane import (
    TEST_FIXTURE_CANONICAL_WRITE_AUTHORITY,
    StagedCandidate,
    create_knowledge_relation,
    persist_task_knowledge_view,
    submit_staged_knowledge,
)
from swallow.truth_governance.store import append_canonical_record


def _client(base_dir: Path) -> TestClient:
    return TestClient(create_fastapi_app(base_dir))


def _canonical_record(
    *,
    canonical_id: str,
    source_object_id: str,
    text: str,
    relation_metadata: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "canonical_id": canonical_id,
        "canonical_key": "topic:http-knowledge",
        "source_task_id": "task-http-knowledge",
        "source_object_id": source_object_id,
        "promoted_at": "2026-05-04T00:00:00+00:00",
        "promoted_by": "test",
        "decision_note": "seed",
        "decision_ref": f".swl/staged_knowledge/registry.jsonl#{canonical_id}",
        "artifact_ref": "",
        "source_ref": f"file://workspace/{source_object_id}.md",
        "text": text,
        "evidence_status": "source_only",
        "canonical_stage": "canonical",
        "canonical_status": "active",
        "superseded_by": "",
        "superseded_at": "",
        "source_pack": [
            {
                "source_ref": f"file://workspace/{source_object_id}.md",
                "content_hash": f"sha256:{source_object_id}",
                "parser_version": "wiki-compiler-v1",
                "span": "L1-L2",
                "preview": text,
            }
        ],
        "rationale": f"{source_object_id} rationale",
        "relation_metadata": relation_metadata or [],
        "conflict_flag": "contradicts(wiki-old)" if source_object_id == "wiki-new" else "",
    }


def _seed_knowledge(base_dir: Path) -> None:
    persist_task_knowledge_view(
        base_dir,
        "task-http-knowledge",
        [
            {
                "object_id": "wiki-old",
                "text": "Old HTTP wiki text.",
                "stage": "canonical",
                "source_ref": "file://workspace/wiki-old.md",
                "evidence_status": "source_only",
            },
            {
                "object_id": "wiki-new",
                "text": "New HTTP wiki text.",
                "stage": "canonical",
                "source_ref": "file://workspace/wiki-new.md",
                "evidence_status": "source_only",
            },
        ],
        write_authority=TEST_FIXTURE_CANONICAL_WRITE_AUTHORITY,
    )
    append_canonical_record(
        base_dir,
        _canonical_record(
            canonical_id="canonical-old",
            source_object_id="wiki-old",
            text="Old HTTP wiki text.",
        ),
    )
    append_canonical_record(
        base_dir,
        _canonical_record(
            canonical_id="canonical-new",
            source_object_id="wiki-new",
            text="New HTTP wiki text.",
            relation_metadata=[
                {"relation_type": "supersedes", "target_object_id": "wiki-old"},
                {"relation_type": "derived_from", "target_ref": "file://workspace/wiki-new.md"},
            ],
        ),
    )
    create_knowledge_relation(
        base_dir,
        source_object_id="wiki-new",
        target_object_id="wiki-old",
        relation_type="refines",
        context="HTTP relation",
    )
    submit_staged_knowledge(
        base_dir,
        StagedCandidate(
            candidate_id="staged-http",
            text="HTTP staged draft.",
            source_task_id="task-http-knowledge",
            submitted_by="test",
            relation_metadata=[{"relation_type": "refers_to", "target_object_id": "wiki-new"}],
        ),
    )


def test_knowledge_browse_routes_return_typed_envelopes(tmp_path: Path) -> None:
    _seed_knowledge(tmp_path)
    client = _client(tmp_path)

    wiki_response = client.get("/api/knowledge/wiki", params={"status": "active"})
    canonical_response = client.get("/api/knowledge/canonical", params={"status": "superseded"})
    staged_response = client.get("/api/knowledge/staged", params={"status": "pending"})

    assert wiki_response.status_code == 200
    assert wiki_response.json()["ok"] is True
    assert wiki_response.json()["data"]["filters"] == {"object_kind": "wiki", "status": "active", "limit": 50}
    assert wiki_response.json()["data"]["items"][0]["object_id"] == "wiki-new"
    assert canonical_response.status_code == 200
    assert canonical_response.json()["data"]["items"][0]["object_id"] == "canonical-old"
    assert canonical_response.json()["data"]["items"][0]["status"] == "superseded"
    assert staged_response.status_code == 200
    assert staged_response.json()["data"]["items"][0]["object_id"] == "staged-http"


def test_knowledge_detail_and_relations_routes_include_metadata_edges(tmp_path: Path) -> None:
    _seed_knowledge(tmp_path)
    client = _client(tmp_path)

    detail_response = client.get("/api/knowledge/canonical-new")
    relations_response = client.get("/api/knowledge/canonical-new/relations")

    assert detail_response.status_code == 200
    detail = detail_response.json()["data"]["detail"]
    assert detail["object_kind"] == "canonical"
    assert detail["source_pack"][0]["parser_version"] == "wiki-compiler-v1"
    assert detail["rationale"] == "wiki-new rationale"
    assert detail["conflict_flag"] == "contradicts(wiki-old)"

    assert relations_response.status_code == 200
    groups = relations_response.json()["data"]["groups"]
    assert groups["refines"][0]["edge_source"] == "persisted"
    assert groups["supersedes"][0]["edge_source"] == "metadata"
    assert groups["derived_from"][0]["target_ref"] == "file://workspace/wiki-new.md"


def test_knowledge_routes_report_validation_and_not_found_errors(tmp_path: Path) -> None:
    client = _client(tmp_path)

    invalid_status = client.get("/api/knowledge/wiki", params={"status": "pending"})
    invalid_limit = client.get("/api/knowledge/staged", params={"limit": 0})
    missing_detail = client.get("/api/knowledge/missing-object")

    assert invalid_status.status_code == 400
    assert invalid_limit.status_code == 400
    assert missing_detail.status_code == 404
    assert "Unknown knowledge object" in missing_detail.json()["detail"]
