from __future__ import annotations

import json
import logging
import re
from collections import deque
from dataclasses import replace
from pathlib import Path
from typing import Any

from swallow._io_helpers import read_json_or_empty
from swallow.knowledge_retrieval.canonical_reuse import is_canonical_reuse_visible
from swallow.knowledge_retrieval._internal_knowledge_store import iter_file_knowledge_task_ids, load_task_knowledge_view
from swallow.knowledge_retrieval.knowledge_objects import (
    is_retrieval_reuse_ready,
    summarize_knowledge_evidence,
    summarize_knowledge_reuse,
    summarize_knowledge_stages,
)
from swallow.orchestration.models import RetrievalItem, RetrievalRequest
from swallow.application.infrastructure.paths import canonical_reuse_policy_path
from swallow.knowledge_retrieval.retrieval_adapters import (
    DedicatedRerankAdapter,
    DedicatedRerankUnavailable,
    EmbeddingAPIUnavailable,
    SQLITE_VEC_FALLBACK_WARNING,
    RetrievalSearchDocument,
    TextFallbackAdapter,
    VectorRetrievalAdapter,
    VectorRetrievalUnavailable,
    score_search_document,
    select_retrieval_adapter,
)
from swallow.knowledge_retrieval.retrieval_config import (
    DEFAULT_RELATION_EXPANSION_CONFIG,
    DEFAULT_RETRIEVAL_RERANK_CONFIG,
    KNOWLEDGE_PRIORITY_BONUS,
    RelationExpansionConfig,
    RETRIEVAL_PREVIEW_LIMIT,
    RetrievalRerankConfig,
    RETRIEVAL_SCORING_TEXT_LIMIT,
    resolve_retrieval_rerank_config,
)
from swallow.truth_governance.sqlite_store import SqliteTaskStore

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "into",
    "over",
    "than",
    "then",
    "when",
    "will",
    "would",
    "should",
    "have",
    "has",
    "had",
    "are",
    "was",
    "were",
    "use",
    "using",
    "task",
}
ARTIFACTS_SOURCE_TYPE = "artifacts"
KNOWLEDGE_SOURCE_TYPE = "knowledge"
TASK_ARTIFACT_FILE_NAMES = {
    "memory.json",
    "retrieval.json",
    "route.json",
    "compatibility.json",
    "validation.json",
}
TASK_ARTIFACT_MARKDOWN_NAMES = {
    "summary.md",
    "resume_note.md",
    "source_grounding.md",
    "route_report.md",
    "compatibility_report.md",
    "validation_report.md",
    "executor_output.md",
    "executor_prompt.md",
}
SOURCE_POLICY_NOISE_LABELS = {
    "archive_note",
    "build_cache",
    "current_state",
    "generated_artifact",
    "generated_metadata",
    "observation_doc",
}
SUPPORTING_EVIDENCE_LABELS = {"supporting_evidence"}
DECLARED_DOCUMENT_PRIORITY_BONUS = 1000
SOURCE_POLICY_NOISE_PENALTY = 250
logger = logging.getLogger(__name__)
_sqlite_vec_warning_emitted = False
_embedding_api_warning_emitted = False


def citation_for_lines(relative_path: str, line_start: int, line_end: int) -> str:
    if line_start == line_end:
        return f"{relative_path}#L{line_start}"
    return f"{relative_path}#L{line_start}-L{line_end}"


def matched_terms_for(token_list: list[str], *haystacks: str) -> list[str]:
    return sorted({token for token in token_list if any(haystack.count(token) > 0 for haystack in haystacks)})


def prepare_query_plan(raw_query: str) -> dict[str, Any]:
    normalized_query = " ".join(raw_query.lower().split())
    raw_tokens = [token for token in re.split(r"[^a-zA-Z0-9_./-]+", normalized_query) if token]
    tokens = [token for token in raw_tokens if len(token) > 2 and token not in STOPWORDS]
    unique_tokens = list(dict.fromkeys(tokens))
    phrase = " ".join(unique_tokens)
    token_bigrams = [
        f"{unique_tokens[index]} {unique_tokens[index + 1]}"
        for index in range(len(unique_tokens) - 1)
        if unique_tokens[index] != unique_tokens[index + 1]
    ]
    return {
        "normalized_query": normalized_query,
        "tokens": unique_tokens,
        "phrase": phrase,
        "token_bigrams": token_bigrams,
        "token_count": len(unique_tokens),
    }


def score_chunk(
    query_plan: dict[str, Any],
    relative_path: str,
    path_name: str,
    title: str,
    chunk_text: str,
) -> tuple[int, dict[str, int], list[str]]:
    return score_search_document(
        query_plan,
        relative_path=relative_path,
        path_name=path_name,
        title=title,
        chunk_text=chunk_text,
    )


def build_retrieval_request(
    query: str,
    limit: int = 8,
    source_types: list[str] | None = None,
    context_layers: list[str] | None = None,
    current_task_id: str = "",
    strategy: str = "system_baseline",
    declared_document_paths: tuple[str, ...] | list[str] | None = None,
) -> RetrievalRequest:
    normalized_declared_paths = tuple(
        str(path).replace("\\", "/").strip()
        for path in (declared_document_paths or ())
        if str(path).strip()
    )
    return RetrievalRequest(
        query=query,
        source_types=source_types or ["repo", "notes"],
        context_layers=context_layers or ["workspace", "task"],
        current_task_id=current_task_id,
        limit=limit,
        strategy=strategy,
        declared_document_paths=normalized_declared_paths,
    )


def classify_source_type(path: Path, allowed_sources: set[str]) -> str | None:
    if ".git" in path.parts:
        return None

    if ".swl" in path.parts:
        if ARTIFACTS_SOURCE_TYPE not in allowed_sources:
            return None
        return classify_artifact_source_type(path)

    adapter = select_retrieval_adapter(path)
    if adapter is None:
        return None
    return adapter.source_type if adapter.source_type in allowed_sources else None


def classify_artifact_source_type(path: Path) -> str | None:
    if "tasks" not in path.parts:
        return None
    if path.name in TASK_ARTIFACT_FILE_NAMES or path.name in TASK_ARTIFACT_MARKDOWN_NAMES:
        return ARTIFACTS_SOURCE_TYPE
    if "artifacts" in path.parts and path.suffix.lower() in {".md", ".txt"}:
        return ARTIFACTS_SOURCE_TYPE
    return None


def build_item_metadata(
    path: Path,
    source_type: str,
    adapter_name: str,
    chunk: object,
    line_start: int,
    line_end: int,
    query_plan: dict[str, Any],
) -> dict[str, Any]:
    metadata = {
        "extension": path.suffix.lower(),
        "adapter_name": adapter_name,
        "chunk_kind": chunk.chunk_kind,
        "line_start": line_start,
        "line_end": line_end,
        "title_source": chunk.title_source,
        "query_token_count": query_plan["token_count"],
        **dict(chunk.metadata),
    }
    if source_type == ARTIFACTS_SOURCE_TYPE:
        metadata["storage_scope"] = "task_artifacts"
        metadata["artifact_name"] = path.name
    return metadata


def _citation_line_range(chunk: object) -> tuple[int, int]:
    metadata = getattr(chunk, "metadata", {})
    if not isinstance(metadata, dict):
        return chunk.line_start, chunk.line_end
    base_line_start = metadata.get("base_line_start")
    base_line_end = metadata.get("base_line_end")
    if isinstance(base_line_start, int) and isinstance(base_line_end, int):
        return base_line_start, base_line_end
    return chunk.line_start, chunk.line_end


def build_knowledge_item_metadata(
    knowledge_object: dict[str, Any],
    query_plan: dict[str, Any],
    knowledge_task_id: str,
    current_task_id: str,
) -> dict[str, Any]:
    task_relation = "unknown_task"
    if current_task_id:
        task_relation = "current_task" if knowledge_task_id == current_task_id else "cross_task"
    return {
        "extension": ".json",
        "adapter_name": "verified_knowledge_records",
        "chunk_kind": "knowledge_object",
        "line_start": 1,
        "line_end": 1,
        "title_source": "knowledge_object",
        "query_token_count": query_plan["token_count"],
        "storage_scope": "task_knowledge",
        "knowledge_object_id": knowledge_object.get("object_id", ""),
        "knowledge_stage": knowledge_object.get("stage", ""),
        "knowledge_source_kind": knowledge_object.get("source_kind", ""),
        "knowledge_reuse_scope": knowledge_object.get("knowledge_reuse_scope", ""),
        "canonicalization_intent": knowledge_object.get("canonicalization_intent", ""),
        "evidence_status": knowledge_object.get("evidence_status", ""),
        "artifact_ref": knowledge_object.get("artifact_ref", ""),
        "source_ref": knowledge_object.get("source_ref", ""),
        "content_hash": knowledge_object.get("content_hash", ""),
        "parser_version": knowledge_object.get("parser_version", ""),
        "span": knowledge_object.get("span", ""),
        "heading_path": knowledge_object.get("heading_path", ""),
        "source_anchor_key": knowledge_object.get("source_anchor_key", ""),
        "source_anchor_version": knowledge_object.get("source_anchor_version", ""),
        "source_pack_reference": knowledge_object.get("source_pack_reference", ""),
        "source_pack_index": knowledge_object.get("source_pack_index", 0),
        "source_preview": knowledge_object.get("preview", ""),
        "task_linked": bool(knowledge_object.get("task_linked", False)),
        "retrieval_eligible": bool(knowledge_object.get("retrieval_eligible", False)),
        "knowledge_task_id": knowledge_task_id,
        "knowledge_task_relation": task_relation,
    }


def _iter_known_task_ids(workspace_root: Path) -> list[str]:
    task_ids: set[str] = set(iter_file_knowledge_task_ids(workspace_root))
    try:
        task_ids.update(SqliteTaskStore().iter_knowledge_task_ids(workspace_root))
    except OSError:
        return sorted(task_ids)
    return sorted(task_ids)


def _warn_sqlite_vec_fallback_once() -> None:
    global _sqlite_vec_warning_emitted
    if _sqlite_vec_warning_emitted:
        return
    logger.warning(SQLITE_VEC_FALLBACK_WARNING)
    _sqlite_vec_warning_emitted = True


def _warn_embedding_api_fallback_once() -> None:
    global _embedding_api_warning_emitted
    if _embedding_api_warning_emitted:
        return
    logger.warning("[WARN] embedding API unavailable, falling back to text search")
    _embedding_api_warning_emitted = True


def build_verified_knowledge_documents(
    workspace_root: Path,
    request: RetrievalRequest,
    query_plan: dict[str, Any],
) -> list[RetrievalSearchDocument]:
    documents: list[RetrievalSearchDocument] = []
    allow_current_task = "task" in request.context_layers
    allow_cross_task = "history" in request.context_layers
    for task_id in _iter_known_task_ids(workspace_root):
        if request.current_task_id:
            if task_id == request.current_task_id and not allow_current_task:
                continue
            if task_id != request.current_task_id and not allow_cross_task:
                continue
        knowledge_objects = load_task_knowledge_view(workspace_root, task_id)
        if not knowledge_objects:
            continue

        relative_path = f".swl/tasks/{task_id}/knowledge_objects.json"
        for knowledge_object in knowledge_objects:
            if not isinstance(knowledge_object, dict):
                continue
            if not is_retrieval_reuse_ready(knowledge_object):
                continue

            knowledge_text = str(knowledge_object.get("text", "")).strip()
            if not knowledge_text:
                continue

            object_id = str(knowledge_object.get("object_id", "knowledge-object"))
            title = f"Knowledge {object_id}"
            documents.append(
                RetrievalSearchDocument(
                    path=relative_path,
                    path_name="knowledge_objects.json",
                    source_type=KNOWLEDGE_SOURCE_TYPE,
                    chunk_id=object_id,
                    title=title,
                    citation=f"{relative_path}#{object_id}",
                    text=knowledge_text,
                    metadata=build_knowledge_item_metadata(
                        knowledge_object=knowledge_object,
                        query_plan=query_plan,
                        knowledge_task_id=task_id,
                        current_task_id=request.current_task_id,
                    ),
                )
            )
    return documents


def build_canonical_reuse_item_metadata(
    canonical_record: dict[str, Any],
    query_plan: dict[str, Any],
    current_task_id: str,
) -> dict[str, Any]:
    knowledge_task_id = str(canonical_record.get("source_task_id", ""))
    task_relation = "unknown_task"
    if current_task_id:
        task_relation = "current_task" if knowledge_task_id == current_task_id else "cross_task"
    return {
        "extension": ".json",
        "adapter_name": "canonical_registry_records",
        "chunk_kind": "canonical_record",
        "line_start": 1,
        "line_end": 1,
        "title_source": "canonical_record",
        "query_token_count": query_plan["token_count"],
        "storage_scope": "canonical_registry",
        "knowledge_object_id": canonical_record.get("source_object_id", ""),
        "knowledge_stage": canonical_record.get("canonical_stage", "canonical"),
        "knowledge_reuse_scope": "canonical_registry",
        "evidence_status": canonical_record.get("evidence_status", ""),
        "artifact_ref": canonical_record.get("artifact_ref", ""),
        "source_ref": canonical_record.get("source_ref", ""),
        "task_linked": False,
        "retrieval_eligible": True,
        "knowledge_task_id": knowledge_task_id,
        "knowledge_task_relation": task_relation,
        "canonical_id": canonical_record.get("canonical_id", ""),
        "canonical_key": canonical_record.get("canonical_key", ""),
        "canonical_status": canonical_record.get("canonical_status", "active"),
        "canonical_policy": "reuse_visible",
    }


def summarize_reused_knowledge(retrieval_items: list[RetrievalItem]) -> dict[str, Any]:
    knowledge_items = [item for item in retrieval_items if item.source_type == KNOWLEDGE_SOURCE_TYPE]
    evidence_counts = {"artifact_backed": 0, "source_only": 0, "unbacked": 0}
    storage_scope_counts = {"task_knowledge": 0, "canonical_registry": 0}
    for item in knowledge_items:
        evidence_status = str(item.metadata.get("evidence_status", "unbacked"))
        evidence_counts[evidence_status] = evidence_counts.get(evidence_status, 0) + 1
        storage_scope = str(item.metadata.get("storage_scope", "task_knowledge"))
        storage_scope_counts[storage_scope] = storage_scope_counts.get(storage_scope, 0) + 1
    return {
        "count": len(knowledge_items),
        "references": [item.reference() for item in knowledge_items[:5]],
        "object_ids": [str(item.metadata.get("knowledge_object_id", item.chunk_id)) for item in knowledge_items[:5]],
        "evidence_counts": evidence_counts,
        "storage_scope_counts": storage_scope_counts,
        "canonical_registry_count": storage_scope_counts.get("canonical_registry", 0),
        "task_knowledge_count": storage_scope_counts.get("task_knowledge", 0),
        "current_task_count": sum(
            1 for item in knowledge_items if str(item.metadata.get("knowledge_task_relation", "")) == "current_task"
        ),
        "cross_task_count": sum(
            1 for item in knowledge_items if str(item.metadata.get("knowledge_task_relation", "")) == "cross_task"
        ),
    }


def summarize_truth_reuse_visibility(
    retrieval_items: list[RetrievalItem],
    *,
    task_knowledge_objects: list[dict[str, Any]] | None = None,
    base_dir: Path | None = None,
) -> dict[str, Any]:
    reused_knowledge = summarize_reused_knowledge(retrieval_items)
    task_objects = list(task_knowledge_objects or [])
    task_matched_count = reused_knowledge.get("task_knowledge_count", 0)
    task_considered_count = max(len(task_objects), task_matched_count)
    task_skipped_count = max(task_considered_count - task_matched_count, 0)
    matched_task_object_ids = _matched_task_knowledge_object_ids(retrieval_items)
    task_reason_counts = _task_truth_skip_reason_counts(
        task_objects,
        matched_object_ids=matched_task_object_ids,
        skipped_count=task_skipped_count,
    )

    visible_canonical_records = _load_visible_canonical_records(base_dir)
    canonical_matched_count = reused_knowledge.get("canonical_registry_count", 0)
    canonical_considered_count = max(len(visible_canonical_records), canonical_matched_count)
    canonical_skipped_count = max(canonical_considered_count - canonical_matched_count, 0)

    return {
        "task_knowledge": {
            "status": _reuse_visibility_status(task_considered_count, task_matched_count),
            "considered_count": task_considered_count,
            "matched_count": task_matched_count,
            "skipped_count": task_skipped_count,
            "absent_count": 0 if task_considered_count else 1,
            "reason_counts": task_reason_counts,
        },
        "canonical_registry": {
            "status": _reuse_visibility_status(canonical_considered_count, canonical_matched_count),
            "considered_count": canonical_considered_count,
            "matched_count": canonical_matched_count,
            "skipped_count": canonical_skipped_count,
            "absent_count": 0 if canonical_considered_count else 1,
            "reason_counts": {
                "query_no_match": canonical_skipped_count,
            },
        },
    }


def _reuse_visibility_status(considered_count: int, matched_count: int) -> str:
    if considered_count <= 0:
        return "absent"
    if matched_count > 0:
        return "matched"
    return "considered"


def _matched_task_knowledge_object_ids(retrieval_items: list[RetrievalItem]) -> set[str]:
    object_ids: set[str] = set()
    for item in retrieval_items:
        if item.source_type != KNOWLEDGE_SOURCE_TYPE:
            continue
        storage_scope = str(item.metadata.get("storage_scope", "")).strip()
        task_relation = str(item.metadata.get("knowledge_task_relation", "")).strip()
        if storage_scope != "task_knowledge" and task_relation != "current_task":
            continue
        object_id = str(item.metadata.get("knowledge_object_id", item.chunk_id)).strip()
        if object_id:
            object_ids.add(object_id)
    return object_ids


def _task_truth_skip_reason_counts(
    task_objects: list[dict[str, Any]],
    *,
    matched_object_ids: set[str],
    skipped_count: int,
) -> dict[str, int]:
    if skipped_count <= 0:
        return {}
    reason_counts: dict[str, int] = {}
    counted = 0
    for obj in task_objects:
        object_id = str(obj.get("object_id", "")).strip()
        if object_id and object_id in matched_object_ids:
            continue
        reason = _primary_task_truth_skip_reason(obj)
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
        counted += 1
        if counted >= skipped_count:
            break
    return reason_counts


def _primary_task_truth_skip_reason(obj: dict[str, Any]) -> str:
    reuse_scope = str(obj.get("knowledge_reuse_scope", "task_only")).strip() or "task_only"
    if reuse_scope != "retrieval_candidate":
        return "policy_excluded"
    stage = str(obj.get("stage", "raw")).strip() or "raw"
    if stage in {"raw", "candidate"}:
        return "status_not_active"
    evidence_status = str(obj.get("evidence_status", "unbacked")).strip() or "unbacked"
    if evidence_status in {"unbacked", "source_only"}:
        return "missing_source_pointer"
    return "query_no_match"


def _load_visible_canonical_records(base_dir: Path | None) -> list[dict[str, Any]]:
    if base_dir is None:
        return []
    policy_path = canonical_reuse_policy_path(base_dir)
    if not policy_path.exists():
        return []
    try:
        payload = read_json_or_empty(policy_path)
    except (OSError, json.JSONDecodeError):
        return []
    visible_records = payload.get("visible_records", [])
    if not isinstance(visible_records, list):
        return []
    return [
        record
        for record in visible_records
        if isinstance(record, dict) and is_canonical_reuse_visible(record)
    ]


def summarize_retrieval_trace(retrieval_items: list[RetrievalItem]) -> dict[str, Any]:
    if not retrieval_items:
        return {
            "retrieval_mode": "none",
            "retrieval_adapter": "none",
            "embedding_backend": "none",
            "fallback_reason": "none",
            "rerank_backend": "none",
            "rerank_model": "none",
            "rerank_enabled": False,
            "rerank_configured": False,
            "rerank_attempted": False,
            "rerank_applied": False,
            "rerank_failure_reason": "none",
            "final_order_basis": "none",
        }

    def _unique_metadata_values(*keys: str) -> list[str]:
        values: list[str] = []
        for item in retrieval_items:
            for key in keys:
                value = str(item.metadata.get(key, "")).strip()
                if value:
                    if value not in values:
                        values.append(value)
                    break
        return values

    def _single_or_mixed(values: list[str], default: str = "unknown") -> str:
        if not values:
            return default
        if len(values) == 1:
            return values[0]
        return "mixed:" + ",".join(values)

    first_metadata = retrieval_items[0].metadata
    return {
        "retrieval_mode": _single_or_mixed(_unique_metadata_values("knowledge_retrieval_mode"), "lexical"),
        "retrieval_adapter": _single_or_mixed(
            _unique_metadata_values("knowledge_retrieval_adapter", "adapter_name"),
            "unknown",
        ),
        "embedding_backend": _single_or_mixed(_unique_metadata_values("embedding_backend"), "none"),
        "fallback_reason": _single_or_mixed(_unique_metadata_values("retrieval_fallback_reason"), "none"),
        "rerank_backend": str(first_metadata.get("rerank_backend", "unknown") or "unknown"),
        "rerank_model": str(first_metadata.get("rerank_model", "") or "none"),
        "rerank_enabled": bool(first_metadata.get("rerank_enabled", False)),
        "rerank_configured": bool(first_metadata.get("rerank_configured", False)),
        "rerank_attempted": bool(first_metadata.get("rerank_attempted", False)),
        "rerank_applied": bool(first_metadata.get("rerank_applied", False)),
        "rerank_failure_reason": str(first_metadata.get("rerank_failure_reason", "") or "none"),
        "final_order_basis": str(first_metadata.get("final_order_basis", "") or "unknown"),
    }


def source_policy_label_for(item: RetrievalItem) -> str:
    path = item.path.replace("\\", "/").strip()
    storage_scope = str(item.metadata.get("storage_scope", "")).strip()
    if item.source_type == KNOWLEDGE_SOURCE_TYPE:
        if _is_source_anchor_support(item):
            return "supporting_evidence"
        if storage_scope == "canonical_registry" or str(item.metadata.get("canonical_id", "")).strip():
            return "canonical_truth"
        return "task_knowledge_truth"
    if item.source_type == ARTIFACTS_SOURCE_TYPE:
        return "artifact_source"
    if path in {"current_state.md", "docs/active_context.md"}:
        return "current_state"
    if path.startswith("docs/archive/") or path.startswith("docs/archive_phases/"):
        return "archive_note"
    if _is_generated_metadata_path(path):
        return "generated_metadata"
    if _is_build_cache_path(path):
        return "build_cache"
    if _is_generated_artifact_path(path):
        return "generated_artifact"
    if _is_observation_doc_path(path):
        return "observation_doc"
    if item.source_type == "repo":
        return "repo_source"
    if item.source_type == "notes":
        return "active_note"
    return f"{item.source_type or 'unknown'}_source"


def source_policy_flags_for(item: RetrievalItem, label: str | None = None) -> list[str]:
    resolved_label = label or source_policy_label_for(item)
    flags: list[str] = []
    if resolved_label in SOURCE_POLICY_NOISE_LABELS:
        flags.append("operator_context_noise")
    if resolved_label == "supporting_evidence":
        flags.append("source_anchor_support")
    if resolved_label not in {"canonical_truth", "task_knowledge_truth", *SUPPORTING_EVIDENCE_LABELS}:
        flags.append("fallback_text_hit")
    if str(item.metadata.get("knowledge_retrieval_mode", "")).strip() == "text_fallback":
        flags.append("text_fallback_retrieval")
    if resolved_label == "canonical_truth":
        flags.append("primary_truth_candidate")
    return flags


def annotate_source_policy(items: list[RetrievalItem]) -> list[RetrievalItem]:
    annotated_items: list[RetrievalItem] = []
    for item in items:
        label = source_policy_label_for(item)
        metadata = dict(item.metadata)
        metadata["source_policy_label"] = label
        metadata["source_policy_flags"] = source_policy_flags_for(item, label)
        annotated_items.append(replace(item, metadata=metadata))
    return annotated_items


def summarize_source_policy_warnings(
    retrieval_items: list[RetrievalItem],
    *,
    truth_reuse_visibility: dict[str, Any] | None = None,
) -> list[str]:
    warnings: list[str] = []
    ranked_items = list(enumerate(retrieval_items, start=1))
    canonical_ranks = [
        _item_rank(index, item)
        for index, item in ranked_items
        if str(item.metadata.get("source_policy_label", source_policy_label_for(item))) == "canonical_truth"
    ]
    first_canonical_rank = min(canonical_ranks) if canonical_ranks else 0
    noisy_before_canonical: list[str] = []
    for index, item in ranked_items:
        label = str(item.metadata.get("source_policy_label", source_policy_label_for(item)))
        rank = _item_rank(index, item)
        if label in SOURCE_POLICY_NOISE_LABELS and first_canonical_rank and rank < first_canonical_rank:
            noisy_before_canonical.append(f"{label}:{item.reference()}")
    if noisy_before_canonical:
        warnings.append(
            "operational_doc_outranks_canonical_truth: "
            + ", ".join(noisy_before_canonical[:3])
        )

    observation_hits = [
        item.reference()
        for _index, item in ranked_items
        if str(item.metadata.get("source_policy_label", source_policy_label_for(item))) == "observation_doc"
    ]
    if observation_hits:
        warnings.append("observation_doc_self_reference_risk: " + ", ".join(observation_hits[:3]))

    fallback_hits = [
        item
        for _index, item in ranked_items
        if "fallback_text_hit" in list(item.metadata.get("source_policy_flags", source_policy_flags_for(item)))
    ]
    truth_hits = [
        item
        for _index, item in ranked_items
        if str(item.metadata.get("source_policy_label", source_policy_label_for(item)))
        in {"canonical_truth", "task_knowledge_truth"}
    ]
    if fallback_hits and not truth_hits:
        task_considered = _visibility_considered_count(truth_reuse_visibility, "task_knowledge")
        canonical_considered = _visibility_considered_count(truth_reuse_visibility, "canonical_registry")
        if task_considered or canonical_considered:
            warnings.append(
                "fallback_hits_without_reused_truth_objects: "
                "canonical or task knowledge exists but did not match retrieval"
            )
        else:
            warnings.append("fallback_hits_without_truth_objects: no canonical or task knowledge item is present")
    return warnings


def _visibility_considered_count(visibility: dict[str, Any] | None, section_name: str) -> int:
    if not isinstance(visibility, dict):
        return 0
    section = visibility.get(section_name, {})
    if not isinstance(section, dict):
        return 0
    try:
        return int(section.get("considered_count", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _is_observation_doc_path(path: str) -> bool:
    if path.startswith("results/"):
        return True
    if not path.startswith("docs/plans/"):
        return False
    return path.endswith("/observations.md") or path.endswith("/closeout.md") or "/candidate-r/" in path


def _is_generated_metadata_path(path: str) -> bool:
    normalized = path.replace("\\", "/").strip()
    return ".egg-info/" in normalized or normalized.endswith(".egg-info")


def _is_build_cache_path(path: str) -> bool:
    normalized = path.replace("\\", "/").strip()
    prefixes = (
        ".mypy_cache/",
        ".pytest_cache/",
        ".ruff_cache/",
        "__pycache__/",
        "build/",
        "dist/",
    )
    if normalized.startswith(prefixes):
        return True
    return "/__pycache__/" in normalized or "/build/" in normalized or "/dist/" in normalized


def _is_generated_artifact_path(path: str) -> bool:
    normalized = path.replace("\\", "/").strip()
    return normalized.startswith(".swl/tasks/") and "/artifacts/" in normalized


def _is_source_anchor_support(item: RetrievalItem) -> bool:
    if str(item.metadata.get("source_anchor_key", "")).strip():
        return True
    if str(item.metadata.get("canonicalization_intent", "")).strip() == "support":
        return True
    if str(item.metadata.get("knowledge_source_kind", "")).strip() == "wiki_compiler_source_pack":
        return True
    object_id = str(item.metadata.get("knowledge_object_id", item.chunk_id)).strip()
    return object_id.startswith("evidence-src-")


def _matches_declared_document_path(item: RetrievalItem, declared_paths: set[str]) -> str:
    path = item.path.replace("\\", "/").strip()
    if not path or not declared_paths:
        return ""
    if path in declared_paths:
        return path
    return ""


def apply_source_scoping_policy(items: list[RetrievalItem], request: RetrievalRequest) -> list[RetrievalItem]:
    declared_paths = {path.replace("\\", "/").strip() for path in request.declared_document_paths if path.strip()}
    scoped_items: list[RetrievalItem] = []
    for item in items:
        metadata = dict(item.metadata)
        score_breakdown = dict(item.score_breakdown)
        adjusted_score = item.score

        matched_declared_path = _matches_declared_document_path(item, declared_paths)
        if matched_declared_path:
            adjusted_score += DECLARED_DOCUMENT_PRIORITY_BONUS
            score_breakdown["declared_document_priority"] = DECLARED_DOCUMENT_PRIORITY_BONUS
            metadata["declared_document_path_status"] = "matched"
            metadata["declared_document_path"] = matched_declared_path
        elif declared_paths:
            metadata.setdefault("declared_document_path_status", "not_declared_source")

        source_policy_label = source_policy_label_for(replace(item, metadata=metadata))
        if source_policy_label in SOURCE_POLICY_NOISE_LABELS:
            adjusted_score -= SOURCE_POLICY_NOISE_PENALTY
            score_breakdown["source_noise_penalty"] = -SOURCE_POLICY_NOISE_PENALTY
            metadata["source_scope_policy"] = "noise_downgraded"

        scoped_items.append(
            replace(
                item,
                score=adjusted_score,
                score_breakdown=score_breakdown,
                metadata=metadata,
            )
        )
    return scoped_items


def _item_rank(default_rank: int, item: RetrievalItem) -> int:
    raw_rank = item.metadata.get("final_rank", default_rank)
    try:
        rank = int(raw_rank)
    except (TypeError, ValueError):
        return default_rank
    return rank if rank > 0 else default_rank


def iter_verified_knowledge_items(
    workspace_root: Path,
    request: RetrievalRequest,
    query_plan: dict[str, Any],
) -> list[RetrievalItem]:
    allowed_sources = set(request.source_types)
    if KNOWLEDGE_SOURCE_TYPE not in allowed_sources or int(query_plan.get("token_count", 0)) <= 0:
        return []

    documents = build_verified_knowledge_documents(
        workspace_root=workspace_root,
        request=request,
        query_plan=query_plan,
    )
    if not documents:
        return []

    try:
        matches = VectorRetrievalAdapter().search(
            documents,
            query_text=request.query,
            query_plan=query_plan,
            limit=request.limit,
        )
        retrieval_mode = "vector"
        fallback_reason = ""
    except VectorRetrievalUnavailable:
        _warn_sqlite_vec_fallback_once()
        matches = TextFallbackAdapter().search(
            documents,
            query_plan=query_plan,
            limit=request.limit,
        )
        retrieval_mode = "text_fallback"
        fallback_reason = "sqlite_vec_unavailable"
    except EmbeddingAPIUnavailable:
        _warn_embedding_api_fallback_once()
        matches = TextFallbackAdapter().search(
            documents,
            query_plan=query_plan,
            limit=request.limit,
        )
        retrieval_mode = "text_fallback"
        fallback_reason = "embedding_api_unavailable"

    items: list[RetrievalItem] = []
    for match in matches:
        preview = " ".join(match.document.text.split())[:RETRIEVAL_PREVIEW_LIMIT]
        metadata = dict(match.document.metadata)
        metadata["knowledge_retrieval_adapter"] = match.adapter_name
        metadata["knowledge_retrieval_mode"] = retrieval_mode
        metadata["retrieval_fallback_reason"] = fallback_reason
        score_breakdown = dict(match.score_breakdown)
        score_breakdown["knowledge_priority_bonus"] = KNOWLEDGE_PRIORITY_BONUS
        items.append(
            RetrievalItem(
                path=match.document.path,
                source_type=KNOWLEDGE_SOURCE_TYPE,
                score=match.score + KNOWLEDGE_PRIORITY_BONUS,
                preview=preview,
                chunk_id=match.document.chunk_id,
                title=match.document.title,
                citation=match.document.citation,
                matched_terms=match.matched_terms,
                score_breakdown=score_breakdown,
                metadata=metadata,
            )
        )
    return items


def _vector_or_text_matches(
    documents: list[RetrievalSearchDocument],
    *,
    request: RetrievalRequest,
    query_plan: dict[str, Any],
    limit: int,
) -> tuple[list[RetrievalSearchMatch], str, str]:
    try:
        return (
            VectorRetrievalAdapter().search(
                documents,
                query_text=request.query,
                query_plan=query_plan,
                limit=limit,
            ),
            "vector",
            "",
        )
    except VectorRetrievalUnavailable:
        _warn_sqlite_vec_fallback_once()
        return (
            TextFallbackAdapter().search(
                documents,
                query_plan=query_plan,
                limit=limit,
            ),
            "text_fallback",
            "sqlite_vec_unavailable",
        )
    except EmbeddingAPIUnavailable:
        _warn_embedding_api_fallback_once()
        return (
            TextFallbackAdapter().search(
                documents,
                query_plan=query_plan,
                limit=limit,
            ),
            "text_fallback",
            "embedding_api_unavailable",
        )


def rerank_retrieval_items(
    items: list[RetrievalItem],
    *,
    query: str,
    config: RetrievalRerankConfig | None = None,
) -> list[RetrievalItem]:
    rerank_config = config or DEFAULT_RETRIEVAL_RERANK_CONFIG
    if not rerank_config.enabled:
        return _annotate_rerank_trace(items, config=rerank_config, final_order_basis="raw_score", failure_reason="disabled")
    if not rerank_config.configured:
        return _annotate_rerank_trace(
            items,
            config=rerank_config,
            final_order_basis="raw_score",
            failure_reason="not_configured",
        )
    if len(items) < 2:
        return _annotate_rerank_trace(
            items,
            config=rerank_config,
            final_order_basis="raw_score",
            failure_reason="not_enough_candidates",
        )
    if not query.strip():
        return _annotate_rerank_trace(
            items,
            config=rerank_config,
            final_order_basis="raw_score",
            failure_reason="empty_query",
        )

    top_n = min(rerank_config.top_n, len(items))
    if top_n < 2:
        return _annotate_rerank_trace(
            items,
            config=rerank_config,
            final_order_basis="raw_score",
            failure_reason="not_enough_candidates",
        )

    candidate_items = items[:top_n]
    documents = [
        RetrievalSearchDocument(
            path=item.path,
            path_name=Path(item.path).name,
            source_type=item.source_type,
            chunk_id=item.chunk_id,
            title=item.display_title(),
            citation=item.reference(),
            text=item.preview,
            metadata=dict(item.metadata),
        )
        for item in candidate_items
    ]
    try:
        rerank_response = DedicatedRerankAdapter().rerank(
            query_text=query,
            documents=documents,
            config=rerank_config,
        )
    except DedicatedRerankUnavailable as exc:
        return _annotate_rerank_trace(
            items,
            config=rerank_config,
            attempted=True,
            final_order_basis="raw_score",
            failure_reason=str(exc) or "dedicated_rerank_unavailable",
        )

    reranked_items: list[RetrievalItem] = []
    for rerank_position, item_index in enumerate(rerank_response.ordered_indexes, start=1):
        item = candidate_items[item_index]
        metadata = dict(item.metadata)
        metadata["rerank_position"] = rerank_position
        if item_index in rerank_response.scores_by_index:
            metadata["rerank_score"] = rerank_response.scores_by_index[item_index]
        score_breakdown = dict(item.score_breakdown)
        score_breakdown["dedicated_rerank_applied"] = 1
        reranked_items.append(
            replace(
                item,
                metadata=metadata,
                score_breakdown=score_breakdown,
            )
        )

    return _annotate_rerank_trace(
        reranked_items + items[top_n:],
        config=rerank_config,
        attempted=True,
        applied=True,
        model=rerank_response.model,
        final_order_basis="dedicated_rerank",
    )


def _annotate_rerank_trace(
    items: list[RetrievalItem],
    *,
    config: RetrievalRerankConfig,
    attempted: bool = False,
    applied: bool = False,
    model: str = "",
    final_order_basis: str,
    failure_reason: str = "",
) -> list[RetrievalItem]:
    annotated_items: list[RetrievalItem] = []
    configured = config.configured
    for final_rank, item in enumerate(items, start=1):
        metadata = dict(item.metadata)
        metadata.setdefault("raw_score", item.score)
        metadata["final_rank"] = final_rank
        metadata["final_order_basis"] = final_order_basis
        metadata["rerank_backend"] = "dedicated_http" if configured else "none"
        metadata["rerank_model"] = model or config.model
        metadata["rerank_enabled"] = config.enabled
        metadata["rerank_configured"] = configured
        metadata["rerank_attempted"] = attempted
        metadata["rerank_applied"] = applied
        metadata["rerank_failure_reason"] = failure_reason
        metadata["rerank_top_n"] = config.top_n
        annotated_items.append(replace(item, metadata=metadata))
    return annotated_items


def iter_canonical_reuse_items(
    workspace_root: Path,
    request: RetrievalRequest,
    query_plan: dict[str, Any],
) -> list[RetrievalItem]:
    policy_path = canonical_reuse_policy_path(workspace_root)
    if not policy_path.exists():
        return []
    try:
        payload = read_json_or_empty(policy_path)
    except (OSError, json.JSONDecodeError):
        return []
    visible_records = payload.get("visible_records", [])
    if not isinstance(visible_records, list):
        return []

    documents: list[RetrievalSearchDocument] = []
    for canonical_record in visible_records:
        if not isinstance(canonical_record, dict):
            continue
        if not is_canonical_reuse_visible(canonical_record):
            continue
        knowledge_text = str(canonical_record.get("text", "")).strip()
        if not knowledge_text:
            continue
        relative_path = ".swl/canonical_knowledge/reuse_policy.json"
        canonical_id = str(canonical_record.get("canonical_id", "canonical-record"))
        title = f"Canonical {canonical_id}"
        documents.append(
            RetrievalSearchDocument(
                path=relative_path,
                path_name="reuse_policy.json",
                source_type=KNOWLEDGE_SOURCE_TYPE,
                chunk_id=canonical_id,
                title=title,
                citation=f"{relative_path}#{canonical_id}",
                text=knowledge_text,
                metadata=build_canonical_reuse_item_metadata(
                    canonical_record=canonical_record,
                    query_plan=query_plan,
                    current_task_id=request.current_task_id,
                ),
            )
        )

    if not documents:
        return []

    matches, retrieval_mode, fallback_reason = _vector_or_text_matches(
        documents,
        request=request,
        query_plan=query_plan,
        limit=request.limit,
    )

    items: list[RetrievalItem] = []
    for match in matches:
        preview = " ".join(match.document.text.split())[:RETRIEVAL_PREVIEW_LIMIT]
        metadata = dict(match.document.metadata)
        metadata["knowledge_retrieval_adapter"] = match.adapter_name
        metadata["knowledge_retrieval_mode"] = retrieval_mode
        metadata["retrieval_fallback_reason"] = fallback_reason
        score_breakdown = dict(match.score_breakdown)
        score_breakdown["knowledge_priority_bonus"] = KNOWLEDGE_PRIORITY_BONUS
        items.append(
            RetrievalItem(
                path=match.document.path,
                source_type=KNOWLEDGE_SOURCE_TYPE,
                score=match.score + KNOWLEDGE_PRIORITY_BONUS,
                preview=preview,
                chunk_id=match.document.chunk_id,
                title=match.document.title,
                citation=match.document.citation,
                matched_terms=match.matched_terms,
                score_breakdown=score_breakdown,
                metadata=metadata,
            )
        )
    return items


def _build_retrieval_ready_knowledge_lookup(
    workspace_root: Path,
    request: RetrievalRequest,
    query_plan: dict[str, Any],
) -> dict[str, RetrievalSearchDocument]:
    documents = build_verified_knowledge_documents(
        workspace_root=workspace_root,
        request=request,
        query_plan=query_plan,
    )
    lookup = {str(document.chunk_id): document for document in documents if str(document.chunk_id).strip()}

    policy_path = canonical_reuse_policy_path(workspace_root)
    if not policy_path.exists():
        return lookup
    try:
        payload = read_json_or_empty(policy_path)
    except (OSError, json.JSONDecodeError):
        return lookup
    visible_records = payload.get("visible_records", [])
    if not isinstance(visible_records, list):
        return lookup

    relative_path = ".swl/canonical_knowledge/reuse_policy.json"
    for canonical_record in visible_records:
        if not isinstance(canonical_record, dict):
            continue
        if not is_canonical_reuse_visible(canonical_record):
            continue
        object_id = str(canonical_record.get("source_object_id", "")).strip()
        knowledge_text = str(canonical_record.get("text", "")).strip()
        canonical_id = str(canonical_record.get("canonical_id", "")).strip()
        if not object_id or not knowledge_text or not canonical_id:
            continue
        lookup.setdefault(
            object_id,
            RetrievalSearchDocument(
                path=relative_path,
                path_name="reuse_policy.json",
                source_type=KNOWLEDGE_SOURCE_TYPE,
                chunk_id=canonical_id,
                title=f"Canonical {canonical_id}",
                citation=f"{relative_path}#{canonical_id}",
                text=knowledge_text,
                metadata=build_canonical_reuse_item_metadata(
                    canonical_record=canonical_record,
                    query_plan=query_plan,
                    current_task_id=request.current_task_id,
                ),
            ),
        )
    return lookup


def expand_by_relations(
    workspace_root: Path,
    seed_items: list[RetrievalItem],
    *,
    request: RetrievalRequest,
    query_plan: dict[str, Any],
    config: RelationExpansionConfig = DEFAULT_RELATION_EXPANSION_CONFIG,
) -> list[RetrievalItem]:
    depth_limit = int(config.depth_limit)
    min_confidence = float(config.min_confidence)
    decay_factor = float(config.decay_factor)
    if depth_limit <= 0 or decay_factor <= 0:
        return []

    lookup = _build_retrieval_ready_knowledge_lookup(
        workspace_root=workspace_root,
        request=request,
        query_plan=query_plan,
    )
    if not lookup:
        return []

    seen_object_ids: set[str] = set()
    queue: deque[tuple[str, float, int]] = deque()
    for item in seed_items:
        object_id = str(item.metadata.get("knowledge_object_id", item.chunk_id)).strip()
        if not object_id:
            continue
        seen_object_ids.add(object_id)
        queue.append((object_id, float(item.score), 0))

    if not queue:
        return []

    store = SqliteTaskStore()
    expanded_items: list[RetrievalItem] = []
    expanded_index_by_object_id: dict[str, int] = {}
    traversed: set[tuple[str, str]] = set()

    while queue:
        source_object_id, source_score, depth = queue.popleft()
        if depth >= depth_limit:
            continue
        try:
            relations = store.list_knowledge_relations(workspace_root, source_object_id)
        except OSError:
            return []
        for relation in relations:
            target_object_id = str(relation.get("counterparty_object_id", "")).strip()
            if not target_object_id:
                continue
            edge_key = (source_object_id, target_object_id)
            if edge_key in traversed:
                continue
            traversed.add(edge_key)

            relation_confidence = float(relation.get("confidence", 1.0))
            expanded_score = float(source_score) * decay_factor * relation_confidence
            next_depth = depth + 1
            if expanded_score < min_confidence:
                continue

            if target_object_id not in seen_object_ids:
                document = lookup.get(target_object_id)
                if document is not None:
                    preview = " ".join(document.text.split())[:RETRIEVAL_PREVIEW_LIMIT]
                    metadata = dict(document.metadata)
                    metadata.update(
                        {
                            "knowledge_retrieval_adapter": "relation_expansion",
                            "knowledge_retrieval_mode": "relation_expansion",
                            "expansion_source": "relation",
                            "expansion_depth": next_depth,
                            "expansion_relation_type": str(relation.get("relation_type", "")).strip(),
                            "expansion_parent_object_id": source_object_id,
                            "expansion_parent_object_ids": [source_object_id],
                            "expansion_relation_types": [str(relation.get("relation_type", "")).strip()],
                            "expansion_path_count": 1,
                            "expansion_confidence": relation_confidence,
                        }
                    )
                    expanded_items.append(
                        RetrievalItem(
                            path=document.path,
                            source_type=KNOWLEDGE_SOURCE_TYPE,
                            score=expanded_score,
                            preview=preview,
                            chunk_id=document.chunk_id,
                            title=document.title,
                            citation=document.citation,
                            matched_terms=[],
                            score_breakdown={"relation_expansion": next_depth},
                            metadata=metadata,
                        )
                    )
                    expanded_index_by_object_id[target_object_id] = len(expanded_items) - 1
                seen_object_ids.add(target_object_id)
                queue.append((target_object_id, expanded_score, next_depth))
            else:
                expanded_index = expanded_index_by_object_id.get(target_object_id)
                if expanded_index is not None:
                    expanded_items[expanded_index] = _mark_duplicate_expansion_path(
                        expanded_items[expanded_index],
                        parent_object_id=source_object_id,
                        relation_type=str(relation.get("relation_type", "")).strip(),
                    )
                if next_depth < depth_limit:
                    queue.append((target_object_id, expanded_score, next_depth))
    return expanded_items


def _mark_duplicate_expansion_path(
    item: RetrievalItem,
    *,
    parent_object_id: str,
    relation_type: str,
) -> RetrievalItem:
    metadata = dict(item.metadata)
    metadata["dedup_reason"] = "duplicate_relation_path"
    metadata["expansion_path_count"] = _positive_int_metadata(metadata, "expansion_path_count", default=1) + 1

    parent_ids = _metadata_string_list(metadata.get("expansion_parent_object_ids", []))
    if parent_object_id and parent_object_id not in parent_ids:
        parent_ids.append(parent_object_id)
    metadata["expansion_parent_object_ids"] = parent_ids

    relation_types = _metadata_string_list(metadata.get("expansion_relation_types", []))
    if relation_type and relation_type not in relation_types:
        relation_types.append(relation_type)
    metadata["expansion_relation_types"] = relation_types
    return replace(item, metadata=metadata)


def _positive_int_metadata(metadata: dict[str, Any], key: str, *, default: int) -> int:
    try:
        value = int(metadata.get(key, default) or default)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _metadata_string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def retrieve_context(
    workspace_root: Path,
    query: str | None = None,
    limit: int = 8,
    source_types: list[str] | None = None,
    request: RetrievalRequest | None = None,
) -> list[RetrievalItem]:
    retrieval_request = request or build_retrieval_request(query=query or "", limit=limit, source_types=source_types)
    query_plan = prepare_query_plan(retrieval_request.query)
    allowed_sources = set(retrieval_request.source_types)
    items: list[RetrievalItem] = iter_verified_knowledge_items(
        workspace_root=workspace_root,
        request=retrieval_request,
        query_plan=query_plan,
    )
    items.extend(
        iter_canonical_reuse_items(
            workspace_root=workspace_root,
            request=retrieval_request,
            query_plan=query_plan,
        )
    )
    items.extend(
        expand_by_relations(
            workspace_root=workspace_root,
            seed_items=list(items),
            request=retrieval_request,
            query_plan=query_plan,
        )
    )

    for path in sorted(workspace_root.rglob("*")):
        if not path.is_file():
            continue
        source_type = classify_source_type(path, allowed_sources)
        if source_type is None:
            continue
        adapter = select_retrieval_adapter(path)
        if adapter is None:
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        relative_path = str(path.relative_to(workspace_root))
        chunks = adapter.build_chunks(path, text)
        for chunk in chunks:
            chunk_text = chunk.text
            score, score_breakdown, matched_terms = score_chunk(
                query_plan=query_plan,
                relative_path=relative_path,
                path_name=path.name,
                title=chunk.title,
                chunk_text=chunk_text[:RETRIEVAL_SCORING_TEXT_LIMIT],
            )
            if score <= 0:
                continue

            line_start = chunk.line_start
            line_end = chunk.line_end
            citation_line_start, citation_line_end = _citation_line_range(chunk)
            preview = " ".join(chunk_text.split())[:RETRIEVAL_PREVIEW_LIMIT]
            items.append(
                RetrievalItem(
                    path=relative_path,
                    source_type=source_type,
                    score=score,
                    preview=preview,
                    chunk_id=chunk.chunk_id,
                    title=chunk.title,
                    citation=citation_for_lines(relative_path, citation_line_start, citation_line_end),
                    matched_terms=matched_terms,
                    score_breakdown=score_breakdown,
                    metadata=build_item_metadata(
                        path=path,
                        source_type=source_type,
                        adapter_name=adapter.name,
                        chunk=chunk,
                        line_start=line_start,
                        line_end=line_end,
                        query_plan=query_plan,
                    ),
                )
            )

    items = apply_source_scoping_policy(items, retrieval_request)
    items.sort(key=lambda item: (-item.score, item.path, item.chunk_id))
    items = rerank_retrieval_items(
        items,
        query=retrieval_request.query,
        config=resolve_retrieval_rerank_config(),
    )
    items = annotate_source_policy(items)
    return items[: retrieval_request.limit]
