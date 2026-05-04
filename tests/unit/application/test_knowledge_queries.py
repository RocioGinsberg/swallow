from __future__ import annotations

from pathlib import Path

import pytest

from swallow.application.queries.knowledge import (
    KnowledgeObjectNotFoundError,
    build_canonical_knowledge_payload,
    build_knowledge_detail_payload,
    build_knowledge_relations_payload,
    build_staged_knowledge_payload,
    build_wiki_knowledge_payload,
)
from swallow.knowledge_retrieval.knowledge_plane import (
    TEST_FIXTURE_CANONICAL_WRITE_AUTHORITY,
    StagedCandidate,
    create_knowledge_relation,
    persist_task_knowledge_view,
    submit_staged_knowledge,
)
from swallow.truth_governance.store import append_canonical_record


def _canonical_record(
    *,
    canonical_id: str,
    source_object_id: str,
    text: str,
    relation_metadata: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "canonical_id": canonical_id,
        "canonical_key": "topic:wiki-compiler",
        "source_task_id": "task-knowledge",
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
        "conflict_flag": "",
    }


def _seed_knowledge(base_dir: Path) -> None:
    persist_task_knowledge_view(
        base_dir,
        "task-knowledge",
        [
            {
                "object_id": "evidence-source",
                "text": "Evidence source text.",
                "stage": "raw",
                "source_ref": "file://workspace/evidence.md",
                "evidence_status": "source_only",
            },
            {
                "object_id": "wiki-old",
                "text": "Old wiki text.",
                "stage": "canonical",
                "source_ref": "file://workspace/wiki-old.md",
                "evidence_status": "source_only",
            },
            {
                "object_id": "wiki-new",
                "text": "New wiki text with relation metadata.",
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
            text="Old wiki text.",
        ),
    )
    append_canonical_record(
        base_dir,
        _canonical_record(
            canonical_id="canonical-new",
            source_object_id="wiki-new",
            text="New wiki text with relation metadata.",
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
        context="new wiki refines old wiki",
    )
    create_knowledge_relation(
        base_dir,
        source_object_id="wiki-new",
        target_object_id="evidence-source",
        relation_type="derived_from",
        context="new wiki derives from evidence",
    )
    submit_staged_knowledge(
        base_dir,
        StagedCandidate(
            candidate_id="staged-pending",
            text="Pending staged draft.",
            source_task_id="task-knowledge",
            submitted_by="test",
            relation_metadata=[{"relation_type": "refers_to", "target_object_id": "wiki-new"}],
        ),
    )
    submit_staged_knowledge(
        base_dir,
        StagedCandidate(
            candidate_id="staged-rejected",
            text="Rejected staged draft.",
            source_task_id="task-knowledge",
            submitted_by="test",
            status="rejected",
            decided_at="2026-05-04T01:00:00+00:00",
            decided_by="test",
        ),
    )


def test_knowledge_list_queries_filter_wiki_canonical_and_staged(tmp_path: Path) -> None:
    _seed_knowledge(tmp_path)

    wiki_active = build_wiki_knowledge_payload(tmp_path, status="active")
    wiki_all = build_wiki_knowledge_payload(tmp_path, status="all")
    canonical_superseded = build_canonical_knowledge_payload(tmp_path, status="superseded")
    staged_pending = build_staged_knowledge_payload(tmp_path, status="pending")

    assert wiki_active["filters"] == {"object_kind": "wiki", "status": "active", "limit": 50}
    assert {item["object_id"] for item in wiki_active["items"]} == {"wiki-new"}
    assert {item["object_id"] for item in wiki_all["items"]} == {"wiki-old", "wiki-new"}
    assert canonical_superseded["items"][0]["object_id"] == "canonical-old"
    assert canonical_superseded["items"][0]["status"] == "superseded"
    assert staged_pending["items"][0]["object_id"] == "staged-pending"


def test_knowledge_detail_resolves_canonical_wiki_staged_and_evidence(tmp_path: Path) -> None:
    _seed_knowledge(tmp_path)

    canonical_detail = build_knowledge_detail_payload(tmp_path, "canonical-new")["detail"]
    wiki_detail = build_knowledge_detail_payload(tmp_path, "wiki-new")["detail"]
    staged_detail = build_knowledge_detail_payload(tmp_path, "staged-pending")["detail"]
    evidence_detail = build_knowledge_detail_payload(tmp_path, "evidence-source")["detail"]

    assert canonical_detail["object_kind"] == "canonical"
    assert canonical_detail["source_pack"][0]["parser_version"] == "wiki-compiler-v1"
    assert canonical_detail["relation_metadata"][0]["relation_type"] == "supersedes"
    assert wiki_detail["object_kind"] == "wiki"
    assert wiki_detail["canonical_id"] == "canonical-new"
    assert wiki_detail["rationale"] == "wiki-new rationale"
    assert staged_detail["object_kind"] == "staged"
    assert staged_detail["relation_metadata"][0]["relation_type"] == "refers_to"
    assert evidence_detail["object_kind"] == "evidence"


def test_knowledge_relations_groups_persisted_and_metadata_edges(tmp_path: Path) -> None:
    _seed_knowledge(tmp_path)

    payload = build_knowledge_relations_payload(tmp_path, "canonical-new")
    groups = payload["groups"]

    assert payload["object_id"] == "canonical-new"
    assert groups["refines"][0]["edge_source"] == "persisted"
    assert groups["refines"][0]["counterparty_object_id"] == "wiki-old"
    assert groups["supersedes"][0]["edge_source"] == "metadata"
    assert groups["supersedes"][0]["target_object_id"] == "wiki-old"
    assert groups["derived_from"][0]["edge_source"] == "persisted"
    assert groups["derived_from"][0]["target_object_id"] == "evidence-source"
    assert groups["derived_from"][1]["edge_source"] == "metadata"
    assert groups["derived_from"][1]["target_ref"] == "file://workspace/wiki-new.md"


def test_knowledge_query_validation_and_missing_detail(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="status must be one of"):
        build_wiki_knowledge_payload(tmp_path, status="pending")
    with pytest.raises(ValueError, match="limit must be between"):
        build_staged_knowledge_payload(tmp_path, limit=0)
    with pytest.raises(KnowledgeObjectNotFoundError, match="Unknown knowledge object"):
        build_knowledge_detail_payload(tmp_path, "missing")
