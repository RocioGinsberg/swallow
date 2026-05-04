from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from swallow.knowledge_retrieval.knowledge_plane import (
    StagedCandidate,
    TEST_FIXTURE_CANONICAL_WRITE_AUTHORITY,
    build_source_anchor_identity,
    load_canonical_registry_records,
    load_task_knowledge_view,
    list_knowledge_relations,
    list_staged_knowledge,
    persist_task_knowledge_view,
    submit_staged_knowledge,
)
from swallow.orchestration.orchestrator import create_task
from swallow.provider_router.agent_llm import AgentLLMResponse
from swallow.application.infrastructure.paths import artifacts_dir
from tests.helpers.assertions import assert_artifact_exists, assert_cli_success
from tests.helpers.builders import TaskBuilder, WorkspaceBuilder
from tests.helpers.cli_runner import run_cli


def _expected_derived_from_relation_id(source_object_id: str, evidence_id: str) -> str:
    payload = ["derived-from-v1", source_object_id, evidence_id]
    token = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()[:16]
    return f"relation-derived-from-{token}"


def test_wiki_draft_cli_stages_candidate_with_source_pack_and_artifacts(
    tmp_path: Path,
    task_builder: TaskBuilder,
    workspace_builder: WorkspaceBuilder,
) -> None:
    state = task_builder.create(
        title="Compile wiki note",
        goal="Draft a wiki entry from raw notes.",
    )
    workspace_builder.write_text(
        "compiler-source.md",
        "# Compiler\n\nUse staged review before canonical promotion.\n",
    )
    source_ref = "file://workspace/compiler-source.md"

    with patch(
        "swallow.application.services.wiki_compiler.call_agent_llm",
        return_value=AgentLLMResponse(
            content=json.dumps(
                {
                    "title": "Wiki Compiler Boundary",
                    "text": "Wiki Compiler drafts staged knowledge and leaves promotion to Operator review.",
                    "rationale": "source-1 states the staged review boundary.",
                    "relation_metadata": [{"relation_type": "derived_from", "target_ref": source_ref}],
                    "conflict_flag": "",
                }
            ),
            input_tokens=10,
            output_tokens=20,
            model="mock-model",
        ),
    ) as llm_mock:
        result = run_cli(
            tmp_path,
            "wiki",
            "draft",
            "--task-id",
            state.task_id,
            "--topic",
            "compiler",
            "--source-ref",
            source_ref,
        )

    assert_cli_success(result)
    llm_mock.assert_called_once()
    assert "wiki_draft_staged" in result.stdout

    candidates = list_staged_knowledge(tmp_path)
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.submitted_by == "wiki-compiler"
    assert candidate.wiki_mode == "draft"
    assert candidate.topic == "compiler"
    assert candidate.rationale == "source-1 states the staged review boundary."
    assert candidate.relation_metadata == [{"relation_type": "derived_from", "target_ref": source_ref}]
    assert candidate.source_pack[0]["source_ref"] == source_ref
    assert str(candidate.source_pack[0]["content_hash"]).startswith("sha256:")
    assert candidate.source_pack[0]["parser_version"] == "wiki-compiler-v1"
    assert candidate.source_pack[0]["span"] == "L1-L3"

    assert_artifact_exists(tmp_path, state.task_id, "wiki_compiler_prompt_pack.json")
    assert_artifact_exists(tmp_path, state.task_id, "wiki_compiler_result.json")


def test_wiki_refine_cli_records_requested_relation_metadata(
    tmp_path: Path,
    task_builder: TaskBuilder,
    workspace_builder: WorkspaceBuilder,
) -> None:
    state = task_builder.create(
        title="Refine wiki note",
        goal="Draft a wiki refinement.",
    )
    workspace_builder.write_text(
        "refine-source.md",
        "The existing wiki entry needs a narrower follow-up.\n",
    )

    with patch(
        "swallow.application.services.wiki_compiler.call_agent_llm",
        return_value=AgentLLMResponse(
            content=json.dumps(
                {
                    "title": "Refined Wiki",
                    "text": "A narrower wiki entry that refines the target.",
                    "rationale": "The source narrows the target wiki.",
                    "relation_metadata": [],
                    "conflict_flag": "",
                }
            ),
            input_tokens=7,
            output_tokens=9,
            model="mock-model",
        ),
    ):
        result = run_cli(
            tmp_path,
            "wiki",
            "refine",
            "--task-id",
            state.task_id,
            "--mode",
            "refines",
            "--target",
            "wiki-target",
            "--source-ref",
            "file://workspace/refine-source.md",
        )

    assert_cli_success(result)
    candidate = list_staged_knowledge(tmp_path)[0]
    assert candidate.wiki_mode == "refines"
    assert candidate.target_object_id == "wiki-target"
    assert candidate.relation_metadata[0] == {"relation_type": "refines", "target_object_id": "wiki-target"}


def test_wiki_refresh_evidence_updates_anchor_without_llm(
    tmp_path: Path,
    task_builder: TaskBuilder,
    workspace_builder: WorkspaceBuilder,
) -> None:
    state = task_builder.create(
        title="Refresh evidence",
        goal="Refresh one evidence source anchor.",
    )
    workspace_builder.write_text("evidence.md", "# Evidence\n\nFresh source anchor.\n")
    persist_task_knowledge_view(
        tmp_path,
        state.task_id,
        [
            {
                "object_id": "evidence-1",
                "text": "Old evidence text.",
                "stage": "raw",
                "source_kind": "operator",
                "source_ref": "",
                "evidence_status": "unbacked",
            }
        ],
    )

    with patch("swallow.application.services.wiki_compiler.call_agent_llm", side_effect=AssertionError("LLM must not run")):
        result = run_cli(
            tmp_path,
            "wiki",
            "refresh-evidence",
            "--task-id",
            state.task_id,
            "--target",
            "evidence-1",
            "--source-ref",
            "file://workspace/evidence.md",
            "--parser-version",
            "parser-v2",
            "--span",
            "L1-L3",
        )

    assert_cli_success(result)
    assert "evidence-1 evidence_refreshed" in result.stdout
    view = [
        item
        for item in load_task_knowledge_view(tmp_path, state.task_id)
        if item["object_id"] == "evidence-1"
    ]
    assert len(view) == 1
    assert view[0]["parser_version"] == "parser-v2"
    assert view[0]["span"] == "L1-L3"
    assert str(view[0]["content_hash"]).startswith("sha256:")
    assert view[0]["source_ref"] == "file://workspace/evidence.md"


def test_stage_promote_creates_refines_relation_from_operator_approved_metadata(tmp_path: Path) -> None:
    state = create_task(
        base_dir=tmp_path,
        title="Promote refinement",
        goal="Approve a staged wiki refinement.",
        workspace_root=tmp_path,
    )
    persist_task_knowledge_view(
        tmp_path,
        state.task_id,
        [
            {
                "object_id": "wiki-target",
                "text": "Existing wiki entry.",
                "stage": "canonical",
                "source_kind": "test",
                "source_ref": "",
                "evidence_status": "source_only",
            }
        ],
        write_authority=TEST_FIXTURE_CANONICAL_WRITE_AUTHORITY,
    )
    candidate = submit_staged_knowledge(
        tmp_path,
        StagedCandidate(
            candidate_id="",
            text="Approved refinement.",
            source_task_id=state.task_id,
            submitted_by="wiki-compiler",
            wiki_mode="refines",
            target_object_id="wiki-target",
            relation_metadata=[{"relation_type": "refines", "target_object_id": "wiki-target"}],
        ),
    )

    result = run_cli(
        tmp_path,
        "knowledge",
        "stage-promote",
        candidate.candidate_id,
        "--note",
        "Approved refinement relation.",
    )

    result.assert_success()
    relations = list_knowledge_relations(tmp_path, f"canonical-{candidate.candidate_id}")
    assert len(relations) == 1
    assert relations[0]["relation_type"] == "refines"
    assert relations[0]["counterparty_object_id"] == "wiki-target"


def test_stage_promote_materializes_source_pack_evidence_and_derived_relation(tmp_path: Path) -> None:
    state = create_task(
        base_dir=tmp_path,
        title="Promote source-backed draft",
        goal="Approve a staged wiki draft with source evidence.",
        workspace_root=tmp_path,
    )
    source_ref = "file://workspace/source-evidence.md"
    candidate = submit_staged_knowledge(
        tmp_path,
        StagedCandidate(
            candidate_id="staged-evidence",
            text="Approved source-backed wiki draft.",
            source_task_id=state.task_id,
            submitted_by="wiki-compiler",
            wiki_mode="draft",
            source_ref=source_ref,
            source_pack=[
                {
                    "reference": "source-1",
                    "path": "source-evidence.md",
                    "source_type": "raw_material",
                    "source_ref": source_ref,
                    "resolved_ref": source_ref,
                    "resolved_path": "source-evidence.md",
                    "resolution_status": "resolved",
                    "line_start": 1,
                    "line_end": 2,
                    "content_hash": "sha256:source-evidence",
                    "parser_version": "wiki-compiler-v1",
                    "span": "L1-L2",
                    "preview": "Source preview for evidence materialization.",
                }
            ],
            relation_metadata=[{"relation_type": "derived_from", "target_ref": source_ref}],
        ),
    )

    result = run_cli(
        tmp_path,
        "knowledge",
        "stage-promote",
        candidate.candidate_id,
        "--note",
        "Approved evidence relation.",
    )

    result.assert_success()
    expected_identity = build_source_anchor_identity(candidate.source_pack[0])
    expected_evidence_id = expected_identity["evidence_id"]
    view = load_task_knowledge_view(tmp_path, state.task_id)
    evidence = next(item for item in view if item["object_id"] == expected_evidence_id)
    wiki = next(item for item in view if item["object_id"] == "canonical-staged-evidence")
    registry_record = next(
        item
        for item in load_canonical_registry_records(tmp_path)
        if item["canonical_id"] == "canonical-staged-evidence"
    )
    relations = list_knowledge_relations(tmp_path, "canonical-staged-evidence")

    assert evidence["store_type"] == "evidence"
    assert evidence["source_ref"] == source_ref
    assert evidence["content_hash"] == "sha256:source-evidence"
    assert evidence["parser_version"] == "wiki-compiler-v1"
    assert evidence["span"] == "L1-L2"
    assert evidence["text"] == "Source preview for evidence materialization."
    assert evidence["source_type"] == "raw_material"
    assert evidence["display_path"] == "source-evidence.md"
    assert evidence["source_anchor_key"] == expected_identity["source_anchor_key"]
    assert evidence["source_anchor_version"] == "source-anchor-v1"
    assert wiki["source_evidence_ids"] == [expected_evidence_id]
    assert registry_record["source_evidence_ids"] == [expected_evidence_id]
    assert registry_record["relation_metadata"] == [{"relation_type": "derived_from", "target_ref": source_ref}]
    assert len(relations) == 1
    assert relations[0]["relation_id"] == _expected_derived_from_relation_id(
        "canonical-staged-evidence",
        expected_evidence_id,
    )
    assert relations[0]["relation_type"] == "derived_from"
    assert relations[0]["target_object_id"] == expected_evidence_id
