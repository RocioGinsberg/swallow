from __future__ import annotations

import inspect

from swallow.knowledge_retrieval import knowledge_plane as kp
from swallow.orchestration.models import RetrievalItem, TaskState


def _knowledge_object(object_id: str, text: str) -> dict[str, object]:
    return {
        "object_id": object_id,
        "text": text,
        "stage": "verified",
        "source_kind": "test",
        "source_ref": f"test://{object_id}",
        "task_linked": True,
        "evidence_status": "artifact_backed",
        "artifact_ref": f".swl/tasks/task-facade/artifacts/{object_id}.md",
        "retrieval_eligible": True,
        "knowledge_reuse_scope": "retrieval_candidate",
        "canonicalization_intent": "promote",
    }


def test_knowledge_plane_is_functional_facade_not_all_barrel() -> None:
    assert "__all__" not in vars(kp)
    assert inspect.isfunction(kp.list_staged_knowledge)
    assert inspect.isfunction(kp.retrieve_knowledge_context)
    assert kp.list_staged_knowledge.__module__ == "swallow.knowledge_retrieval.knowledge_plane"
    assert kp.render_knowledge_index_report.__module__ == "swallow.knowledge_retrieval.knowledge_plane"


def test_staged_lifecycle_and_canonical_record_facade(tmp_path) -> None:
    candidate = kp.submit_staged_knowledge(
        tmp_path,
        kp.StagedCandidate(
            candidate_id="staged-facade",
            text="Promote explicit knowledge-plane facade calls.",
            source_task_id="task-facade",
            source_object_id="knowledge-facade",
            source_ref="test://facade",
            submitted_by="test",
        ),
    )

    assert [item.candidate_id for item in kp.list_staged_knowledge(tmp_path)] == ["staged-facade"]

    decided = kp.decide_staged_knowledge(
        tmp_path,
        candidate.candidate_id,
        "promoted",
        "human-operator",
        "Approved through facade.",
    )
    staged_record = kp.build_staged_canonical_record(decided, refined_text="Canonical facade contract.")
    task_record = kp.build_task_canonical_record(
        task_id="task-facade",
        object_id="knowledge-facade",
        knowledge_object=_knowledge_object("knowledge-facade", "Task object text."),
        decision_record={"decided_at": "2026-05-03T00:00:00+00:00", "decided_by": "test", "note": "ok"},
    )

    assert decided.status == "promoted"
    assert staged_record["canonical_key"] == "task-object:task-facade:knowledge-facade"
    assert staged_record["text"] == "Canonical facade contract."
    assert task_record["canonical_id"] == "canonical-task-facade-knowledge-facade"


def test_task_knowledge_view_facade_keeps_output_shapes_distinct(tmp_path) -> None:
    evidence_object = _knowledge_object("knowledge-facade", "Evidence text.")
    normalized = kp.persist_task_knowledge_view(tmp_path, "task-facade", [evidence_object])
    flat_view = kp.load_task_knowledge_view(tmp_path, "task-facade")
    evidence_entries = kp.load_task_evidence_entries(tmp_path, "task-facade")
    wiki_entries = kp.load_task_wiki_entries(tmp_path, "task-facade")

    assert normalized[0]["store_type"] == "evidence"
    assert flat_view[0]["object_id"] == "knowledge-facade"
    assert evidence_entries[0]["object_id"] == "knowledge-facade"
    assert wiki_entries == []

    wiki_entry = kp.persist_wiki_entry_from_canonical_record(
        tmp_path,
        {
            "canonical_id": "canonical-task-facade-knowledge-facade",
            "source_task_id": "task-facade",
            "source_object_id": "knowledge-facade",
            "promoted_at": "2026-05-03T00:00:00+00:00",
            "promoted_by": "human-operator",
            "decision_ref": ".swl/staged_knowledge/registry.jsonl#staged-facade",
            "artifact_ref": ".swl/tasks/task-facade/artifacts/knowledge-facade.md",
            "source_ref": "test://facade",
            "text": "Canonical facade text.",
            "evidence_status": "artifact_backed",
        },
        write_authority=kp.LIBRARIAN_AGENT_WRITE_AUTHORITY,
    )

    assert wiki_entry["store_type"] == "wiki"
    assert kp.load_task_wiki_entries(tmp_path, "task-facade")[0]["object_id"] == "knowledge-facade"


def test_ingestion_facade_exposes_operator_note_bytes_pipeline_and_reports(tmp_path) -> None:
    note_result = kp.ingest_operator_note(tmp_path, "Decision: keep facade explicit.", topic="architecture")
    bytes_result = kp.run_knowledge_ingestion_bytes_pipeline(
        tmp_path,
        b"# Constraints\nConstraint: no selector mode.",
        source_name="session.md",
        source_ref="clipboard://facade",
        source_task_id="ingest-facade",
        dry_run=True,
    )

    assert note_result.detected_format == "operator_note"
    assert kp.list_staged_knowledge(tmp_path)[0].topic == "architecture"
    assert bytes_result.source_path == "clipboard://facade"
    assert "Constraint: no selector mode." in kp.render_ingestion_summary(bytes_result)
    assert "# Ingestion Report" in kp.render_ingestion_report(bytes_result)


def test_relation_and_executor_suggestion_facade(tmp_path) -> None:
    kp.persist_task_knowledge_view(
        tmp_path,
        "task-facade",
        [
            _knowledge_object("knowledge-a", "A cites B."),
            _knowledge_object("knowledge-b", "B supports A."),
        ],
    )

    relation = kp.create_knowledge_relation(
        tmp_path,
        source_object_id="knowledge-a",
        target_object_id="knowledge-b",
        relation_type="cites",
        confidence=0.8,
        context="Facade relation test.",
    )
    relations = kp.list_knowledge_relations(tmp_path, "knowledge-a")

    side_effect_path = kp.persist_executor_side_effects(
        tmp_path,
        "task-facade",
        {
            "relation_suggestions": [
                {
                    "source_object_id": "knowledge-a",
                    "target_object_id": "knowledge-b",
                    "relation_type": "extends",
                    "confidence": 0.7,
                    "context": "dry run",
                }
            ]
        },
    )
    suggestion_report = kp.apply_relation_suggestions(tmp_path, "task-facade", dry_run=True)

    assert relation["relation_id"].startswith("relation-")
    assert relations[0]["direction"] == "outgoing"
    assert "Knowledge Relation" in kp.render_knowledge_relation_report(relation)
    assert side_effect_path.name == "executor_side_effects.json"
    assert suggestion_report["applied_count"] == 1
    assert "Knowledge Suggestion Application" in kp.render_relation_suggestion_application_report(suggestion_report)


def test_projection_review_policy_retrieval_and_prompt_facade(tmp_path) -> None:
    knowledge_objects = [
        item.to_dict()
        for item in kp.build_knowledge_objects(
            items=["Reusable facade knowledge."],
            stage="verified",
            artifact_refs=[".swl/tasks/task-facade/artifacts/evidence.md"],
            retrieval_eligible=True,
            canonicalization_intent="promote",
        )
    ]
    updated_objects, decision = kp.apply_knowledge_review_decision(
        knowledge_objects,
        object_id="knowledge-0001",
        decision_type="promote",
        decision_target="canonical",
        caller_authority=kp.OPERATOR_CANONICAL_WRITE_AUTHORITY,
    )
    index = kp.build_knowledge_index(knowledge_objects)
    partition = kp.build_knowledge_partition(knowledge_objects)
    queue = kp.build_review_queue(knowledge_objects, [decision])
    canonical_summary = kp.build_canonical_reuse_summary(
        [
            {
                "canonical_id": "canonical-task-facade-knowledge-0001",
                "canonical_key": "task-object:task-facade:knowledge-0001",
                "canonical_status": "active",
                "source_task_id": "task-facade",
                "source_object_id": "knowledge-0001",
            }
        ]
    )
    evaluation = kp.build_canonical_reuse_evaluation_record(
        task_id="task-facade",
        citations=[".swl/canonical_knowledge/reuse_policy.json#canonical-task-facade-knowledge-0001"],
        judgment="useful",
    )
    request = kp.build_retrieval_request("facade", current_task_id="task-facade")
    retrieval_item = RetrievalItem(
        path=".swl/canonical_knowledge/registry.jsonl",
        source_type="knowledge",
        score=9,
        preview="Reusable facade knowledge.",
        metadata={
            "storage_scope": "canonical_registry",
            "canonical_id": "canonical-task-facade-knowledge-0001",
            "canonical_key": "task-object:task-facade:knowledge-0001",
            "knowledge_task_id": "task-facade",
            "evidence_status": "artifact_backed",
        },
    )
    evidence_pack = kp.build_evidence_pack([retrieval_item], workspace_root=tmp_path)
    grounding_entries = kp.extract_grounding_entries([retrieval_item])
    grounding_evidence = kp.build_grounding_evidence(grounding_entries)
    state = TaskState(
        task_id="task-facade",
        title="Facade",
        goal="Use facade",
        workspace_root=str(tmp_path),
        knowledge_objects=knowledge_objects,
    )

    assert updated_objects[0]["stage"] == "canonical"
    assert index["active_reusable_count"] == 1
    assert partition["reusable_candidate_count"] == 1
    assert queue["count"] == 1
    assert canonical_summary["reuse_visible_count"] == 1
    assert kp.build_canonical_reuse_evaluation_summary([evaluation])["evaluation_count"] == 1
    assert request.current_task_id == "task-facade"
    assert evidence_pack.summary()["primary_object_count"] == 1
    assert grounding_evidence["entry_count"] == 1
    assert "Grounding Evidence" in kp.render_grounding_evidence_report(grounding_evidence)
    assert kp.normalize_executor_name(None) == kp.DEFAULT_EXECUTOR
    assert kp.resolve_executor_name(state) == kp.DEFAULT_EXECUTOR
    assert kp.collect_executor_prompt_data(state, [retrieval_item]).task.task_id == "task-facade"
