"""Functional facade for Knowledge Plane APIs used by upper layers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from swallow.knowledge_retrieval import _internal_canonical_registry as _canonical_registry
from swallow.knowledge_retrieval import _internal_ingestion_pipeline as _ingestion_pipeline
from swallow.knowledge_retrieval import _internal_knowledge_relations as _knowledge_relations
from swallow.knowledge_retrieval import _internal_knowledge_store as _knowledge_store
from swallow.knowledge_retrieval import _internal_knowledge_suggestions as _knowledge_suggestions
from swallow.knowledge_retrieval import _internal_staged_knowledge as _staged_knowledge
from swallow.knowledge_retrieval import canonical_reuse as _canonical_reuse
from swallow.knowledge_retrieval import canonical_reuse_eval as _canonical_reuse_eval
from swallow.knowledge_retrieval import dialect_data as _dialect_data
from swallow.knowledge_retrieval import evidence_pack as _evidence_pack
from swallow.knowledge_retrieval import grounding as _grounding
from swallow.knowledge_retrieval import knowledge_index as _knowledge_index
from swallow.knowledge_retrieval import knowledge_objects as _knowledge_objects
from swallow.knowledge_retrieval import knowledge_partition as _knowledge_partition
from swallow.knowledge_retrieval import knowledge_policy as _knowledge_policy
from swallow.knowledge_retrieval import knowledge_review as _knowledge_review
from swallow.knowledge_retrieval import retrieval as _retrieval
from swallow.knowledge_retrieval.dialect_adapters import ClaudeXMLDialect, FIMDialect
from swallow.orchestration.models import RetrievalItem, RetrievalRequest, TaskState

StagedCandidate = _staged_knowledge.StagedCandidate
IngestionPipelineResult = _ingestion_pipeline.IngestionPipelineResult
EvidencePack = _evidence_pack.EvidencePack
SourcePointer = _evidence_pack.SourcePointer
GroundingEntry = _grounding.GroundingEntry

CANONICAL_KNOWLEDGE_WRITE_AUTHORITIES = _knowledge_store.CANONICAL_KNOWLEDGE_WRITE_AUTHORITIES
LIBRARIAN_AGENT_WRITE_AUTHORITY = _knowledge_store.LIBRARIAN_AGENT_WRITE_AUTHORITY
KNOWLEDGE_MIGRATION_WRITE_AUTHORITY = _knowledge_store.KNOWLEDGE_MIGRATION_WRITE_AUTHORITY
OPERATOR_CANONICAL_WRITE_AUTHORITY = _knowledge_store.OPERATOR_CANONICAL_WRITE_AUTHORITY
TEST_FIXTURE_CANONICAL_WRITE_AUTHORITY = _knowledge_store.TEST_FIXTURE_CANONICAL_WRITE_AUTHORITY
KNOWLEDGE_RELATION_TYPES = _knowledge_relations.KNOWLEDGE_RELATION_TYPES
EXTERNAL_SESSION_SOURCE_KIND = _ingestion_pipeline.EXTERNAL_SESSION_SOURCE_KIND
DEFAULT_EXECUTOR = _dialect_data.DEFAULT_EXECUTOR
ARTIFACTS_SOURCE_TYPE = _retrieval.ARTIFACTS_SOURCE_TYPE
KNOWLEDGE_SOURCE_TYPE = _retrieval.KNOWLEDGE_SOURCE_TYPE


def list_staged_knowledge(base_dir: Path) -> list[StagedCandidate]:
    return _staged_knowledge.load_staged_candidates(base_dir)


def submit_staged_knowledge(base_dir: Path, candidate: StagedCandidate) -> StagedCandidate:
    return _staged_knowledge.submit_staged_candidate(base_dir, candidate)


def decide_staged_knowledge(
    base_dir: Path,
    candidate_id: str,
    status: str,
    decided_by: str,
    note: str = "",
) -> StagedCandidate:
    return _staged_knowledge.update_staged_candidate(base_dir, candidate_id, status, decided_by, note)


def build_task_canonical_record(
    *,
    task_id: str,
    object_id: str,
    knowledge_object: dict[str, object],
    decision_record: dict[str, object],
) -> dict[str, object]:
    return _canonical_registry.build_canonical_record(
        task_id=task_id,
        object_id=object_id,
        knowledge_object=knowledge_object,
        decision_record=decision_record,
    )


def build_staged_canonical_record(candidate: StagedCandidate, *, refined_text: str = "") -> dict[str, object]:
    canonical_key = _canonical_registry.build_staged_canonical_key(
        source_task_id=candidate.source_task_id,
        source_object_id=candidate.source_object_id,
        candidate_id=candidate.candidate_id,
    )
    canonical_text = refined_text.strip() or candidate.text
    return {
        "canonical_id": f"canonical-{candidate.candidate_id}",
        "canonical_key": canonical_key,
        "source_task_id": candidate.source_task_id,
        "source_object_id": candidate.source_object_id,
        "promoted_at": candidate.decided_at,
        "promoted_by": candidate.decided_by or "swl_cli",
        "decision_note": candidate.decision_note,
        "decision_ref": f".swl/staged_knowledge/registry.jsonl#{candidate.candidate_id}",
        "artifact_ref": "",
        "source_ref": candidate.source_ref,
        "text": canonical_text,
        "evidence_status": "source_only",
        "canonical_stage": "canonical",
        "canonical_status": "active",
        "superseded_by": "",
        "superseded_at": "",
    }


def build_canonical_record(
    *,
    task_id: str,
    object_id: str,
    knowledge_object: dict[str, object],
    decision_record: dict[str, object],
) -> dict[str, object]:
    return build_task_canonical_record(
        task_id=task_id,
        object_id=object_id,
        knowledge_object=knowledge_object,
        decision_record=decision_record,
    )


def build_canonical_key(*, knowledge_object: dict[str, object], task_id: str, object_id: str) -> str:
    return _canonical_registry.build_canonical_key(
        knowledge_object=knowledge_object,
        task_id=task_id,
        object_id=object_id,
    )


def build_staged_canonical_key(*, source_task_id: str, source_object_id: str, candidate_id: str) -> str:
    return _canonical_registry.build_staged_canonical_key(
        source_task_id=source_task_id,
        source_object_id=source_object_id,
        candidate_id=candidate_id,
    )


def resolve_knowledge_object_id(base_dir: Path, object_id: str, **kwargs: Any) -> str:
    return _canonical_registry.resolve_knowledge_object_id(base_dir, object_id, **kwargs)


def build_canonical_registry_index(records: list[dict[str, object]]) -> dict[str, object]:
    return _canonical_registry.build_canonical_registry_index(records)


def render_canonical_registry_index_report(index_record: dict[str, object]) -> str:
    return _canonical_registry.build_canonical_registry_index_report(index_record)


def build_canonical_registry_index_report(index_record: dict[str, object]) -> str:
    return render_canonical_registry_index_report(index_record)


def render_canonical_registry_report(records: list[dict[str, object]]) -> str:
    return _canonical_registry.build_canonical_registry_report(records)


def build_canonical_registry_report(records: list[dict[str, object]]) -> str:
    return render_canonical_registry_report(records)


def normalize_task_knowledge_view(knowledge_objects: list[dict[str, object]]) -> list[dict[str, object]]:
    return _knowledge_store.normalize_task_knowledge_view(knowledge_objects)


def split_task_knowledge_view(knowledge_objects: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    return _knowledge_store.split_task_knowledge_view(knowledge_objects)


def load_task_knowledge_view(base_dir: Path, task_id: str) -> list[dict[str, object]]:
    return _knowledge_store.load_task_knowledge_view(base_dir, task_id)


def load_task_knowledge_view_from_files(base_dir: Path, task_id: str) -> list[dict[str, object]]:
    return _knowledge_store.load_task_knowledge_view_from_files(base_dir, task_id)


def load_task_evidence_entries(base_dir: Path, task_id: str) -> list[dict[str, object]]:
    return _knowledge_store.load_task_evidence_entries(base_dir, task_id)


def load_task_wiki_entries(base_dir: Path, task_id: str) -> list[dict[str, object]]:
    return _knowledge_store.load_task_wiki_entries(base_dir, task_id)


def normalize_evidence_entry(payload: dict[str, object]) -> dict[str, object]:
    return _knowledge_store.normalize_evidence_entry(payload)


def normalize_wiki_entry(payload: dict[str, object]) -> dict[str, object]:
    return _knowledge_store.normalize_wiki_entry(payload)


def is_canonical_knowledge_write_authorized(write_authority: str) -> bool:
    return _knowledge_store.is_canonical_knowledge_write_authorized(write_authority)


def enforce_canonical_knowledge_write_authority(
    knowledge_objects: list[dict[str, object]],
    *,
    write_authority: str,
) -> None:
    return _knowledge_store.enforce_canonical_knowledge_write_authority(
        knowledge_objects,
        write_authority=write_authority,
    )


def persist_task_knowledge_view(
    base_dir: Path,
    task_id: str,
    knowledge_objects: list[dict[str, object]],
    *,
    mirror_files: bool = True,
    write_authority: str = "task-state",
) -> list[dict[str, object]]:
    return _knowledge_store.persist_task_knowledge_view(
        base_dir,
        task_id,
        knowledge_objects,
        mirror_files=mirror_files,
        write_authority=write_authority,
    )


def build_wiki_entry_from_canonical_record(record: dict[str, object]) -> dict[str, object]:
    return _knowledge_store.build_wiki_entry_from_canonical_record(record)


def persist_wiki_entry_from_canonical_record(
    base_dir: Path,
    record: dict[str, object],
    *,
    mirror_files: bool = True,
    write_authority: str = LIBRARIAN_AGENT_WRITE_AUTHORITY,
) -> dict[str, object]:
    return _knowledge_store.persist_wiki_entry_from_record(
        base_dir,
        record,
        mirror_files=mirror_files,
        write_authority=write_authority,
    )


def iter_file_knowledge_task_ids(base_dir: Path) -> list[str]:
    return _knowledge_store.iter_file_knowledge_task_ids(base_dir)


def migrate_file_knowledge_to_sqlite(base_dir: Path, *, dry_run: bool = False) -> dict[str, object]:
    return _knowledge_store.migrate_file_knowledge_to_sqlite(base_dir, dry_run=dry_run)


def ingest_operator_note(
    base_dir: Path,
    text: str,
    *,
    topic: str = "",
    dry_run: bool = False,
    submitted_by: str = "swl_note",
    taxonomy_role: str = _ingestion_pipeline.DEFAULT_INGESTION_TAXONOMY_ROLE,
    taxonomy_memory_authority: str = _ingestion_pipeline.DEFAULT_INGESTION_TAXONOMY_MEMORY_AUTHORITY,
) -> IngestionPipelineResult:
    return _ingestion_pipeline.ingest_operator_note(
        base_dir,
        text,
        topic=topic,
        dry_run=dry_run,
        submitted_by=submitted_by,
        taxonomy_role=taxonomy_role,
        taxonomy_memory_authority=taxonomy_memory_authority,
    )


def ingest_local_file(
    base_dir: Path,
    source_path: Path,
    *,
    dry_run: bool = False,
    submitted_by: str = _ingestion_pipeline.DEFAULT_INGESTION_SUBMITTED_BY,
    taxonomy_role: str = _ingestion_pipeline.DEFAULT_INGESTION_TAXONOMY_ROLE,
    taxonomy_memory_authority: str = _ingestion_pipeline.DEFAULT_INGESTION_TAXONOMY_MEMORY_AUTHORITY,
) -> IngestionPipelineResult:
    return _ingestion_pipeline.ingest_local_file(
        base_dir,
        source_path,
        dry_run=dry_run,
        submitted_by=submitted_by,
        taxonomy_role=taxonomy_role,
        taxonomy_memory_authority=taxonomy_memory_authority,
    )


def run_knowledge_ingestion_pipeline(
    base_dir: Path,
    source_path: Path,
    *,
    format_hint: str | None = None,
    dry_run: bool = False,
    submitted_by: str = _ingestion_pipeline.DEFAULT_INGESTION_SUBMITTED_BY,
    taxonomy_role: str = _ingestion_pipeline.DEFAULT_INGESTION_TAXONOMY_ROLE,
    taxonomy_memory_authority: str = _ingestion_pipeline.DEFAULT_INGESTION_TAXONOMY_MEMORY_AUTHORITY,
) -> IngestionPipelineResult:
    return _ingestion_pipeline.run_ingestion_pipeline(
        base_dir,
        source_path,
        format_hint=format_hint,
        dry_run=dry_run,
        submitted_by=submitted_by,
        taxonomy_role=taxonomy_role,
        taxonomy_memory_authority=taxonomy_memory_authority,
    )


def run_knowledge_ingestion_bytes_pipeline(
    base_dir: Path,
    source_bytes: bytes,
    *,
    source_name: str,
    source_ref: str,
    source_task_id: str,
    format_hint: str | None = None,
    dry_run: bool = False,
    submitted_by: str = _ingestion_pipeline.DEFAULT_INGESTION_SUBMITTED_BY,
    taxonomy_role: str = _ingestion_pipeline.DEFAULT_INGESTION_TAXONOMY_ROLE,
    taxonomy_memory_authority: str = _ingestion_pipeline.DEFAULT_INGESTION_TAXONOMY_MEMORY_AUTHORITY,
) -> IngestionPipelineResult:
    return _ingestion_pipeline.run_ingestion_bytes_pipeline(
        base_dir,
        source_bytes,
        source_name=source_name,
        source_ref=source_ref,
        source_task_id=source_task_id,
        format_hint=format_hint,
        dry_run=dry_run,
        submitted_by=submitted_by,
        taxonomy_role=taxonomy_role,
        taxonomy_memory_authority=taxonomy_memory_authority,
    )


def render_ingestion_report(result: IngestionPipelineResult) -> str:
    return _ingestion_pipeline.build_ingestion_report(result)


def build_ingestion_report(result: IngestionPipelineResult) -> str:
    return render_ingestion_report(result)


def render_ingestion_summary(result: IngestionPipelineResult) -> str:
    return _ingestion_pipeline.build_ingestion_summary(result)


def build_ingestion_summary(result: IngestionPipelineResult) -> str:
    return render_ingestion_summary(result)


def create_knowledge_relation(
    base_dir: Path,
    *,
    source_object_id: str,
    target_object_id: str,
    relation_type: str,
    confidence: float = 1.0,
    context: str = "",
    created_by: str = "operator",
) -> dict[str, object]:
    return _knowledge_relations.create_knowledge_relation(
        base_dir,
        source_object_id=source_object_id,
        target_object_id=target_object_id,
        relation_type=relation_type,
        confidence=confidence,
        context=context,
        created_by=created_by,
    )


def list_knowledge_relations(base_dir: Path, object_id: str) -> list[dict[str, object]]:
    return _knowledge_relations.list_knowledge_relations(base_dir, object_id)


def delete_knowledge_relation(base_dir: Path, relation_id: str) -> None:
    return _knowledge_relations.delete_knowledge_relation(base_dir, relation_id)


def render_knowledge_relation_report(relation: dict[str, object]) -> str:
    return _knowledge_relations.build_knowledge_relation_report(relation)


def build_knowledge_relation_report(relation: dict[str, object]) -> str:
    return render_knowledge_relation_report(relation)


def render_knowledge_relations_report(object_id: str, relations: list[dict[str, object]]) -> str:
    return _knowledge_relations.build_knowledge_relations_report(object_id, relations)


def build_knowledge_relations_report(object_id: str, relations: list[dict[str, object]]) -> str:
    return render_knowledge_relations_report(object_id, relations)


def persist_executor_side_effects(base_dir: Path, task_id: str, side_effects: dict[str, object]) -> Path:
    return _knowledge_suggestions.persist_executor_side_effects(base_dir, task_id, side_effects)


def apply_relation_suggestions(base_dir: Path, task_id: str, *, dry_run: bool = False) -> dict[str, object]:
    return _knowledge_suggestions.apply_relation_suggestions(base_dir, task_id, dry_run=dry_run)


def render_relation_suggestion_application_report(report: dict[str, object]) -> str:
    return _knowledge_suggestions.build_relation_suggestion_application_report(report)


def build_relation_suggestion_application_report(report: dict[str, object]) -> str:
    return render_relation_suggestion_application_report(report)


def build_knowledge_objects(**kwargs: Any) -> list[Any]:
    return _knowledge_objects.build_knowledge_objects(**kwargs)


def build_knowledge_index(knowledge_objects: list[dict[str, object]]) -> dict[str, object]:
    return _knowledge_index.build_knowledge_index(knowledge_objects)


def render_knowledge_index_report(index_record: dict[str, object]) -> str:
    return _knowledge_index.build_knowledge_index_report(index_record)


def build_knowledge_index_report(index_record: dict[str, object]) -> str:
    return render_knowledge_index_report(index_record)


def build_knowledge_partition(knowledge_objects: list[dict[str, object]]) -> dict[str, object]:
    return _knowledge_partition.build_knowledge_partition(knowledge_objects)


def render_knowledge_partition_report(partition: dict[str, object]) -> str:
    return _knowledge_partition.build_knowledge_partition_report(partition)


def build_knowledge_partition_report(partition: dict[str, object]) -> str:
    return render_knowledge_partition_report(partition)


def apply_knowledge_review_decision(
    knowledge_objects: list[dict[str, object]],
    *,
    object_id: str,
    decision_type: str,
    decision_target: str,
    caller_authority: str,
    note: str = "",
    decided_by: str = "swl_cli",
) -> tuple[list[dict[str, object]], dict[str, object]]:
    return _knowledge_review.apply_knowledge_decision(
        knowledge_objects,
        object_id=object_id,
        decision_type=decision_type,
        decision_target=decision_target,
        caller_authority=caller_authority,
        note=note,
        decided_by=decided_by,
    )


def apply_knowledge_decision(
    knowledge_objects: list[dict[str, object]],
    *,
    object_id: str,
    decision_type: str,
    decision_target: str,
    caller_authority: str,
    note: str = "",
    decided_by: str = "swl_cli",
) -> tuple[list[dict[str, object]], dict[str, object]]:
    return apply_knowledge_review_decision(
        knowledge_objects,
        object_id=object_id,
        decision_type=decision_type,
        decision_target=decision_target,
        caller_authority=caller_authority,
        note=note,
        decided_by=decided_by,
    )


def render_knowledge_decisions_report(decisions: list[dict[str, object]]) -> str:
    return _knowledge_review.build_knowledge_decisions_report(decisions)


def build_knowledge_decisions_report(decisions: list[dict[str, object]]) -> str:
    return render_knowledge_decisions_report(decisions)


def build_review_queue(
    knowledge_objects: list[dict[str, object]],
    decisions: list[dict[str, object]],
) -> dict[str, object]:
    return _knowledge_review.build_review_queue(knowledge_objects, decisions)


def render_review_queue_report(queue: dict[str, object]) -> str:
    return _knowledge_review.build_review_queue_report(queue)


def build_review_queue_report(queue: dict[str, object]) -> str:
    return render_review_queue_report(queue)


def audit_canonical_registry(base_dir: Path, records: list[dict[str, object]]) -> Any:
    from swallow.knowledge_retrieval import canonical_audit

    return canonical_audit.audit_canonical_registry(base_dir, records)


def render_canonical_audit_report(result: Any) -> str:
    from swallow.knowledge_retrieval import canonical_audit

    return canonical_audit.build_canonical_audit_report(result)


def build_canonical_audit_report(result: Any) -> str:
    return render_canonical_audit_report(result)


def build_canonical_reuse_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    return _canonical_reuse.build_canonical_reuse_summary(records)


def render_canonical_reuse_report(summary: dict[str, Any]) -> str:
    return _canonical_reuse.build_canonical_reuse_report(summary)


def build_canonical_reuse_report(summary: dict[str, Any]) -> str:
    return render_canonical_reuse_report(summary)


def is_canonical_reuse_visible(record: dict[str, Any]) -> bool:
    return _canonical_reuse.is_canonical_reuse_visible(record)


def resolve_canonical_reuse_citations(**kwargs: Any) -> tuple[list[dict[str, Any]], list[str]]:
    return _canonical_reuse_eval.resolve_canonical_reuse_citations(**kwargs)


def match_retrieval_items_for_citations(**kwargs: Any) -> list[dict[str, Any]]:
    return _canonical_reuse_eval.match_retrieval_items_for_citations(**kwargs)


def build_canonical_reuse_evaluation_record(**kwargs: Any) -> dict[str, Any]:
    return _canonical_reuse_eval.build_canonical_reuse_evaluation_record(**kwargs)


def build_canonical_reuse_evaluation_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    return _canonical_reuse_eval.build_canonical_reuse_evaluation_summary(records)


def build_canonical_reuse_evaluation_report(records: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    return _canonical_reuse_eval.build_canonical_reuse_evaluation_report(records, summary)


def build_canonical_reuse_regression_baseline(**kwargs: Any) -> dict[str, Any]:
    return _canonical_reuse_eval.build_canonical_reuse_regression_baseline(**kwargs)


def build_canonical_reuse_regression_current(**kwargs: Any) -> dict[str, Any]:
    return _canonical_reuse_eval.build_canonical_reuse_regression_current(**kwargs)


def compare_canonical_reuse_regression(**kwargs: Any) -> dict[str, Any]:
    return _canonical_reuse_eval.compare_canonical_reuse_regression(**kwargs)


def build_canonical_reuse_regression_report(**kwargs: Any) -> str:
    return _canonical_reuse_eval.build_canonical_reuse_regression_report(**kwargs)


def evaluate_knowledge_policy(state: TaskState) -> Any:
    return _knowledge_policy.evaluate_knowledge_policy(state)


def render_knowledge_policy_report(result: Any) -> str:
    return _knowledge_policy.build_knowledge_policy_report(result)


def build_knowledge_policy_report(result: Any) -> str:
    return render_knowledge_policy_report(result)


def summarize_canonicalization(objects: list[dict[str, object]] | list[Any]) -> dict[str, int]:
    return _knowledge_objects.summarize_canonicalization(objects)


def summarize_knowledge_evidence(objects: list[dict[str, object]] | list[Any]) -> dict[str, int]:
    return _knowledge_objects.summarize_knowledge_evidence(objects)


def summarize_knowledge_reuse(objects: list[dict[str, object]] | list[Any]) -> dict[str, int]:
    return _knowledge_objects.summarize_knowledge_reuse(objects)


def summarize_knowledge_stages(objects: list[dict[str, object]] | list[Any]) -> dict[str, int]:
    return _knowledge_objects.summarize_knowledge_stages(objects)


def canonicalization_status_for(item: dict[str, object] | Any) -> str:
    return _knowledge_objects.canonicalization_status_for(item)


def is_retrieval_reuse_ready(item: dict[str, object] | Any) -> bool:
    return _knowledge_objects.is_retrieval_reuse_ready(item)


def normalize_canonicalization_intent(intent: str | None) -> str:
    return _knowledge_objects.normalize_canonicalization_intent(intent)


def build_retrieval_request(
    query: str,
    limit: int = 8,
    source_types: list[str] | None = None,
    context_layers: list[str] | None = None,
    current_task_id: str = "",
    strategy: str = "system_baseline",
) -> RetrievalRequest:
    return _retrieval.build_retrieval_request(
        query=query,
        limit=limit,
        source_types=source_types,
        context_layers=context_layers,
        current_task_id=current_task_id,
        strategy=strategy,
    )


def retrieve_knowledge_context(
    workspace_root: Path,
    query: str | None = None,
    limit: int = 8,
    source_types: list[str] | None = None,
    request: RetrievalRequest | None = None,
) -> list[RetrievalItem]:
    return _retrieval.retrieve_context(
        workspace_root,
        query=query,
        limit=limit,
        source_types=source_types,
        request=request,
    )


def summarize_reused_knowledge(retrieval_items: list[RetrievalItem]) -> dict[str, Any]:
    return _retrieval.summarize_reused_knowledge(retrieval_items)


def summarize_retrieval_trace(retrieval_items: list[RetrievalItem]) -> dict[str, Any]:
    return _retrieval.summarize_retrieval_trace(retrieval_items)


def source_policy_label_for(item: RetrievalItem) -> str:
    return _retrieval.source_policy_label_for(item)


def source_policy_flags_for(item: RetrievalItem, label: str | None = None) -> list[str]:
    return _retrieval.source_policy_flags_for(item, label)


def summarize_source_policy_warnings(retrieval_items: list[RetrievalItem]) -> list[str]:
    return _retrieval.summarize_source_policy_warnings(retrieval_items)


def build_evidence_pack(
    retrieval_items: list[RetrievalItem],
    *,
    workspace_root: str | Path | None = None,
    base_dir: str | Path | None = None,
) -> EvidencePack:
    return _evidence_pack.build_evidence_pack(
        retrieval_items,
        workspace_root=workspace_root,
        base_dir=base_dir,
    )


def extract_grounding_entries(retrieval_items: list[RetrievalItem]) -> list[GroundingEntry]:
    return _grounding.extract_grounding_entries(retrieval_items)


def build_grounding_evidence(entries: list[GroundingEntry]) -> dict[str, object]:
    return _grounding.build_grounding_evidence(entries)


def render_grounding_evidence_report(evidence: dict[str, object]) -> str:
    return _grounding.build_grounding_evidence_report(evidence)


def build_grounding_evidence_report(evidence: dict[str, object]) -> str:
    return render_grounding_evidence_report(evidence)


def collect_executor_prompt_data(state: TaskState, retrieval_items: list[RetrievalItem]) -> Any:
    return _dialect_data.collect_prompt_data(state, retrieval_items)


def normalize_executor_name(raw_name: str | None) -> str:
    return _dialect_data.normalize_executor_name(raw_name)


def resolve_executor_name(state: TaskState) -> str:
    return _dialect_data.resolve_executor_name(state)
