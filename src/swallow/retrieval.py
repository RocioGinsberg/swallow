from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from .canonical_reuse import is_canonical_reuse_visible
from .knowledge_store import iter_file_knowledge_task_ids, load_task_knowledge_view
from .knowledge_objects import is_retrieval_reuse_ready
from .models import RetrievalItem, RetrievalRequest
from .paths import canonical_reuse_policy_path
from .retrieval_adapters import (
    SQLITE_VEC_FALLBACK_WARNING,
    RetrievalSearchDocument,
    TextFallbackAdapter,
    VectorRetrievalAdapter,
    VectorRetrievalUnavailable,
    score_search_document,
    select_retrieval_adapter,
)
from .sqlite_store import SqliteTaskStore

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
logger = logging.getLogger(__name__)
_sqlite_vec_warning_emitted = False


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
) -> RetrievalRequest:
    return RetrievalRequest(
        query=query,
        source_types=source_types or ["repo", "notes"],
        context_layers=context_layers or ["workspace", "task"],
        current_task_id=current_task_id,
        limit=limit,
        strategy=strategy,
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
        "knowledge_reuse_scope": knowledge_object.get("knowledge_reuse_scope", ""),
        "evidence_status": knowledge_object.get("evidence_status", ""),
        "artifact_ref": knowledge_object.get("artifact_ref", ""),
        "source_ref": knowledge_object.get("source_ref", ""),
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
    except VectorRetrievalUnavailable:
        _warn_sqlite_vec_fallback_once()
        matches = TextFallbackAdapter().search(
            documents,
            query_plan=query_plan,
            limit=request.limit,
        )
        retrieval_mode = "text_fallback"

    items: list[RetrievalItem] = []
    for match in matches:
        preview = " ".join(match.document.text.split())[:220]
        metadata = dict(match.document.metadata)
        metadata["knowledge_retrieval_adapter"] = match.adapter_name
        metadata["knowledge_retrieval_mode"] = retrieval_mode
        items.append(
            RetrievalItem(
                path=match.document.path,
                source_type=KNOWLEDGE_SOURCE_TYPE,
                score=match.score,
                preview=preview,
                chunk_id=match.document.chunk_id,
                title=match.document.title,
                citation=match.document.citation,
                matched_terms=match.matched_terms,
                score_breakdown=match.score_breakdown,
                metadata=metadata,
            )
        )
    return items


def iter_canonical_reuse_items(
    workspace_root: Path,
    request: RetrievalRequest,
    query_plan: dict[str, Any],
) -> list[RetrievalItem]:
    policy_path = canonical_reuse_policy_path(workspace_root)
    if not policy_path.exists():
        return []
    try:
        payload = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    visible_records = payload.get("visible_records", [])
    if not isinstance(visible_records, list):
        return []

    items: list[RetrievalItem] = []
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
        score, score_breakdown, matched_terms = score_chunk(
            query_plan=query_plan,
            relative_path=relative_path,
            path_name="reuse_policy.json",
            title=title,
            chunk_text=knowledge_text[:4000],
        )
        if score <= 0:
            continue
        preview = " ".join(knowledge_text.split())[:220]
        items.append(
            RetrievalItem(
                path=relative_path,
                source_type=KNOWLEDGE_SOURCE_TYPE,
                score=score,
                preview=preview,
                chunk_id=canonical_id,
                title=title,
                citation=f"{relative_path}#{canonical_id}",
                matched_terms=matched_terms,
                score_breakdown=score_breakdown,
                metadata=build_canonical_reuse_item_metadata(
                    canonical_record=canonical_record,
                    query_plan=query_plan,
                    current_task_id=request.current_task_id,
                ),
            )
        )
    return items


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
                chunk_text=chunk_text[:4000],
            )
            if score <= 0:
                continue

            line_start = chunk.line_start
            line_end = chunk.line_end
            preview = " ".join(chunk_text.split())[:220]
            items.append(
                RetrievalItem(
                    path=relative_path,
                    source_type=source_type,
                    score=score,
                    preview=preview,
                    chunk_id=chunk.chunk_id,
                    title=chunk.title,
                    citation=citation_for_lines(relative_path, line_start, line_end),
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

    items.sort(key=lambda item: (-item.score, item.path, item.chunk_id))
    return items[: retrieval_request.limit]
