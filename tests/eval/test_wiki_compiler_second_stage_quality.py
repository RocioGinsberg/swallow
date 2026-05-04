from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from swallow.adapters.http.schemas import WikiRefineRequest
from swallow.application.commands.knowledge import (
    StagedCandidate,
    build_stage_promote_preflight_notices,
    promote_stage_candidate_command,
)
from swallow.application.commands.wiki import WikiCompilerRunResult
from swallow.application.infrastructure.paths import artifacts_dir, canonical_registry_path
from swallow.application.services.wiki_compiler import WikiCompilerAgent
from swallow.application.services.wiki_jobs import create_wiki_draft_job, load_wiki_job_result, run_wiki_job
from swallow.knowledge_retrieval.knowledge_plane import (
    build_source_anchor_identity,
    list_knowledge_relations,
    load_task_knowledge_view,
    submit_staged_knowledge,
)
from swallow.orchestration.orchestrator import create_task


pytestmark = pytest.mark.eval


def test_second_stage_eval_source_pack_materializes_matching_evidence_objects(tmp_path: Path) -> None:
    state = create_task(
        base_dir=tmp_path,
        title="Second-stage evidence eval",
        goal="Promote resolved source anchors into evidence objects.",
        workspace_root=tmp_path,
    )
    candidate = submit_staged_knowledge(
        tmp_path,
        StagedCandidate(
            candidate_id="staged-stage2-source",
            text="Second-stage wiki text backed by two resolved source anchors.",
            source_task_id=state.task_id,
            source_object_id="wiki-stage2-source",
            submitted_by="eval",
            wiki_mode="draft",
            source_pack=[
                {
                    "reference": "source-1",
                    "source_ref": "file://workspace/source-a.md",
                    "resolution_status": "resolved",
                    "content_hash": "sha256:source-a",
                    "parser_version": "wiki-compiler-v1",
                    "span": "L1-L4",
                    "preview": "Source A preview.",
                },
                {
                    "reference": "source-2",
                    "source_ref": "artifact://task/source-b.md",
                    "resolution_status": "resolved",
                    "content_hash": "sha256:source-b",
                    "parser_version": "wiki-compiler-v1",
                    "heading_path": "Design / Evidence",
                    "preview": "Source B preview.",
                },
                {
                    "reference": "source-3",
                    "source_ref": "file://workspace/missing.md",
                    "resolution_status": "missing",
                    "content_hash": "sha256:missing",
                    "parser_version": "wiki-compiler-v1",
                    "span": "L1-L1",
                    "preview": "Missing source should not materialize.",
                },
            ],
            relation_metadata=[
                {"relation_type": "derived_from", "target_ref": "file://workspace/source-a.md"},
                {"relation_type": "derived_from", "target_ref": "artifact://task/source-b.md"},
            ],
        ),
    )

    promote_stage_candidate_command(tmp_path, candidate.candidate_id, note="Eval approval.")

    view = load_task_knowledge_view(tmp_path, state.task_id)
    evidence_entries = [
        item
        for item in view
        if item.get("store_type") == "evidence" and item.get("candidate_id") == candidate.candidate_id
    ]
    wiki_entry = next(item for item in view if item.get("object_id") == "wiki-stage2-source")
    relations = list_knowledge_relations(tmp_path, "wiki-stage2-source")
    registry_record = next(
        record
        for record in (
            json.loads(line)
            for line in canonical_registry_path(tmp_path).read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
        if record["canonical_id"] == f"canonical-{candidate.candidate_id}"
    )

    expected_evidence_ids = [
        build_source_anchor_identity(candidate.source_pack[0])["evidence_id"],
        build_source_anchor_identity(candidate.source_pack[1])["evidence_id"],
    ]
    assert [item["object_id"] for item in evidence_entries] == expected_evidence_ids
    assert wiki_entry["source_evidence_ids"] == [item["object_id"] for item in evidence_entries]
    assert registry_record["source_evidence_ids"] == [item["object_id"] for item in evidence_entries]
    assert {relation["target_object_id"] for relation in relations} == set(expected_evidence_ids)
    assert all(str(relation.get("target_object_id", "")).startswith("evidence-") for relation in relations)
    assert all("://" not in str(relation.get("target_object_id", "")) for relation in relations)


def test_second_stage_eval_supersedes_requires_target_and_draft_does_not_supersede() -> None:
    with pytest.raises(ValidationError):
        WikiRefineRequest(
            task_id="task-1",
            mode="supersede",
            target_object_id="",
            source_refs=["file://workspace/source.md"],
        )

    draft = WikiCompilerAgent()._draft_from_payload(
        {
            "title": "Draft should not supersede",
            "text": "Draft text.",
            "rationale": "source-1 supports the draft.",
            "relation_metadata": [
                {"relation_type": "supersedes", "target_object_id": "wiki-old"},
                {"relation_type": "derived_from", "target_ref": "file://workspace/source.md"},
            ],
            "conflict_flag": "",
        },
        action="draft",
        mode="draft",
        target_object_id="",
    )

    relation_types = {item["relation_type"] for item in draft.relation_metadata}
    assert "derived_from" in relation_types
    assert "supersedes" not in relation_types


def test_second_stage_eval_conflict_payload_remains_visible_to_review_response() -> None:
    candidate = StagedCandidate(
        candidate_id="staged-stage2-conflict",
        text="Candidate with a visible conflict signal.",
        source_task_id="task-stage2-conflict",
        source_object_id="wiki-stage2-conflict",
        submitted_by="eval",
        wiki_mode="draft",
        conflict_flag="contradicts(wiki-old)",
    )

    notices = build_stage_promote_preflight_notices([], candidate)

    assert notices == [
        {
            "notice_type": "conflict",
            "canonical_id": "wiki-stage2-conflict",
            "conflict_flag": "contradicts(wiki-old)",
            "text_preview": "contradicts(wiki-old)",
        }
    ]


def test_second_stage_eval_job_payload_carries_source_anchors_and_candidate_id(tmp_path: Path) -> None:
    state = create_task(
        base_dir=tmp_path,
        title="Second-stage job eval",
        goal="Persist completed Wiki Compiler job payload shape.",
        workspace_root=tmp_path,
    )
    job = create_wiki_draft_job(
        tmp_path,
        task_id=state.task_id,
        topic="stage2 jobs",
        source_refs=["file://workspace/job-source.md"],
    )
    candidate = StagedCandidate(
        candidate_id="staged-stage2-job",
        text="Job-created candidate.",
        source_task_id=state.task_id,
        source_object_id="wiki-stage2-job",
        submitted_by="eval",
        wiki_mode="draft",
        source_pack=[
            {
                "reference": "source-1",
                "source_ref": "file://workspace/job-source.md",
                "content_hash": "sha256:job-source",
                "parser_version": "wiki-compiler-v1",
                "span": "L1-L2",
            }
        ],
    )
    fake_result = WikiCompilerRunResult(
        candidate=candidate,
        prompt_pack={"kind": "wiki_compiler_prompt_pack_v1"},
        compiler_result={"status": "completed", "draft": {"text": candidate.text}},
        source_pack=[dict(candidate.source_pack[0])],
        prompt_artifact=artifacts_dir(tmp_path, state.task_id) / "wiki_compiler_prompt_pack.json",
        result_artifact=artifacts_dir(tmp_path, state.task_id) / "wiki_compiler_result.json",
    )

    with patch("swallow.application.services.wiki_jobs.draft_wiki_command", return_value=fake_result):
        completed = run_wiki_job(tmp_path, job.job_id)

    payload = load_wiki_job_result(tmp_path, job.job_id)

    assert completed.status == "completed"
    assert payload["result_ready"] is True
    assert payload["job"]["candidate_id"] == "staged-stage2-job"
    assert payload["candidate"]["candidate_id"] == "staged-stage2-job"
    assert payload["job"]["source_refs"] == ["file://workspace/job-source.md"]
    assert payload["source_pack"][0]["source_ref"] == "file://workspace/job-source.md"
    assert payload["source_pack"][0]["parser_version"] == "wiki-compiler-v1"
