from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from swallow.application.commands.knowledge import StagedCandidate, promote_stage_candidate_command
from swallow.knowledge_retrieval.knowledge_plane import (
    build_evidence_pack,
    build_source_anchor_identity,
    create_knowledge_relation,
    list_knowledge_relations,
    load_task_knowledge_view,
    submit_staged_knowledge,
)
from swallow.knowledge_retrieval.retrieval import KNOWLEDGE_SOURCE_TYPE, retrieve_context
from swallow.knowledge_retrieval.retrieval_adapters import RetrievalSearchMatch
from swallow.orchestration.orchestrator import create_task
from swallow.orchestration.task_report import build_source_grounding
from swallow.truth_governance.store import save_knowledge_objects


pytestmark = pytest.mark.eval


def test_lto2_eval_duplicate_source_anchor_reuses_one_evidence_object(tmp_path: Path) -> None:
    state = create_task(
        base_dir=tmp_path,
        title="LTO-2 duplicate evidence eval",
        goal="Promote two wiki candidates sharing one source anchor.",
        workspace_root=tmp_path,
    )
    anchor = {
        "reference": "source-1",
        "source_ref": "file://workspace/docs/source.md",
        "resolution_status": "resolved",
        "content_hash": "sha256:shared-source",
        "parser_version": "wiki-compiler-v1",
        "span": "line:10-12",
        "heading_path": ["Design", "Evidence"],
        "preview": "Stored source preview for shared anchor.",
    }
    expected_identity = build_source_anchor_identity(anchor)
    candidates = [
        StagedCandidate(
            candidate_id="staged-lto2-a",
            text="First wiki entry backed by shared evidence.",
            source_task_id=state.task_id,
            source_object_id="wiki-lto2-a",
            submitted_by="eval",
            wiki_mode="draft",
            source_pack=[dict(anchor)],
        ),
        StagedCandidate(
            candidate_id="staged-lto2-b",
            text="Second wiki entry backed by the same evidence.",
            source_task_id=state.task_id,
            source_object_id="wiki-lto2-b",
            submitted_by="eval",
            wiki_mode="draft",
            source_pack=[dict(anchor)],
        ),
    ]

    for candidate in candidates:
        submit_staged_knowledge(tmp_path, candidate)
        result = promote_stage_candidate_command(tmp_path, candidate.candidate_id, note="Eval approval.")
        assert result.candidate.status == "promoted"

    view = load_task_knowledge_view(tmp_path, state.task_id)
    evidence_entries = [
        item
        for item in view
        if item.get("store_type") == "evidence" and item.get("object_id") == expected_identity["evidence_id"]
    ]
    wiki_entries = {item["object_id"]: item for item in view if item.get("store_type") == "wiki"}

    assert len(evidence_entries) == 1
    assert evidence_entries[0]["source_anchor_key"] == expected_identity["source_anchor_key"]
    assert evidence_entries[0]["source_anchor_version"] == "source-anchor-v1"
    assert wiki_entries["wiki-lto2-a"]["source_evidence_ids"] == [expected_identity["evidence_id"]]
    assert wiki_entries["wiki-lto2-b"]["source_evidence_ids"] == [expected_identity["evidence_id"]]
    assert {
        relation["target_object_id"]
        for relation in list_knowledge_relations(tmp_path, "wiki-lto2-a")
    } == {expected_identity["evidence_id"]}
    assert {
        relation["target_object_id"]
        for relation in list_knowledge_relations(tmp_path, "wiki-lto2-b")
    } == {expected_identity["evidence_id"]}


def test_lto2_eval_source_anchor_identity_discriminates_all_hash_inputs() -> None:
    anchor = {
        "source_ref": "file://workspace/docs/source.md",
        "content_hash": "sha256:base",
        "parser_version": "wiki-compiler-v1",
        "span": "line:10-12",
        "heading_path": ["Design", "Evidence"],
    }
    base_key = build_source_anchor_identity(anchor)["source_anchor_key"]
    variants = [
        {**anchor, "source_ref": "file://workspace/docs/other-source.md"},
        {**anchor, "content_hash": "sha256:changed"},
        {**anchor, "parser_version": "wiki-compiler-v2"},
        {**anchor, "span": "line:13-15"},
        {**anchor, "heading_path": ["Design", "Other Evidence"]},
    ]

    variant_keys = {build_source_anchor_identity(variant)["source_anchor_key"] for variant in variants}

    assert len(variant_keys) == len(variants)
    assert base_key not in variant_keys


def test_lto2_eval_relation_expansion_dedupes_shared_evidence_support_and_reports_preview(
    tmp_path: Path,
) -> None:
    anchor = {
        "source_ref": "file://workspace/docs/missing-source.md",
        "content_hash": "sha256:shared-support",
        "parser_version": "wiki-compiler-v1",
        "span": "line:20-24",
        "heading_path": "Retrieval > Evidence",
    }
    identity = build_source_anchor_identity(anchor)
    evidence_id = identity["evidence_id"]
    for task_id, object_id, text in [
        ("task-a", "knowledge-a", "Seed A retrieval knowledge."),
        ("task-b", "knowledge-b", "Seed B retrieval knowledge."),
        ("task-evidence", evidence_id, "Shared source anchored support."),
    ]:
        payload = {
            "object_id": object_id,
            "text": text,
            "stage": "verified",
            "evidence_status": "artifact_backed",
            "artifact_ref": f".swl/tasks/{task_id}/artifacts/summary.md",
            "retrieval_eligible": True,
            "knowledge_reuse_scope": "retrieval_candidate",
        }
        if object_id == evidence_id:
            payload.update(
                {
                    "source_kind": "wiki_compiler_source_pack",
                    "source_ref": anchor["source_ref"],
                    "content_hash": anchor["content_hash"],
                    "parser_version": anchor["parser_version"],
                    "span": anchor["span"],
                    "heading_path": anchor["heading_path"],
                    "source_anchor_key": identity["source_anchor_key"],
                    "source_anchor_version": identity["source_anchor_version"],
                    "canonicalization_intent": "support",
                    "preview": "Stored eval preview excerpt.",
                }
            )
        save_knowledge_objects(tmp_path, task_id, [payload])

    create_knowledge_relation(tmp_path, source_object_id="knowledge-a", target_object_id=evidence_id, relation_type="cites")
    create_knowledge_relation(tmp_path, source_object_id="knowledge-b", target_object_id=evidence_id, relation_type="related_to")

    def _mock_vector_search(documents, *, query_text, query_plan, limit):
        seed_a = next(document for document in documents if document.chunk_id == "knowledge-a")
        seed_b = next(document for document in documents if document.chunk_id == "knowledge-b")
        return [
            RetrievalSearchMatch(
                document=seed_a,
                score=20,
                score_breakdown={"vector_bonus": 4},
                matched_terms=["seed"],
                adapter_name="sqlite_vec",
            ),
            RetrievalSearchMatch(
                document=seed_b,
                score=18,
                score_breakdown={"vector_bonus": 3},
                matched_terms=["seed"],
                adapter_name="sqlite_vec",
            ),
        ]

    with patch.dict("os.environ", {"SWL_RETRIEVAL_RERANK_ENABLED": "false"}, clear=False):
        with patch("swallow.knowledge_retrieval.retrieval.VectorRetrievalAdapter.search", side_effect=_mock_vector_search):
            items = retrieve_context(
                tmp_path,
                query="shared evidence support retrieval",
                source_types=[KNOWLEDGE_SOURCE_TYPE],
                limit=8,
            )

    expanded_support = [item for item in items if item.chunk_id == evidence_id]
    assert len(expanded_support) == 1
    support_item = expanded_support[0]
    assert support_item.metadata["source_policy_label"] == "supporting_evidence"
    assert support_item.metadata["source_anchor_key"] == identity["source_anchor_key"]
    assert support_item.metadata["source_preview"] == "Stored eval preview excerpt."
    assert support_item.metadata["expansion_path_count"] == 2
    assert support_item.metadata["dedup_reason"] == "duplicate_relation_path"

    pack = build_evidence_pack(items)
    assert pack.summary()["supporting_evidence_count"] == 1
    assert pack.supporting_evidence[0]["source_preview_excerpt"] == "Stored eval preview excerpt."

    source_grounding = build_source_grounding(items, workspace_root=tmp_path, base_dir=tmp_path)
    assert "source_anchor_key: " + identity["source_anchor_key"] in source_grounding
    assert "source_pointer_status: missing" in source_grounding
    assert "source_pointer_reason: raw_material_missing" in source_grounding
    assert "source_preview_excerpt: Stored eval preview excerpt." in source_grounding
