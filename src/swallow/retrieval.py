from __future__ import annotations

import json
import logging
import re
from collections import deque
from dataclasses import replace
from pathlib import Path
from typing import Any

from .canonical_reuse import is_canonical_reuse_visible
from .knowledge_store import iter_file_knowledge_task_ids, load_task_knowledge_view
from .knowledge_objects import is_retrieval_reuse_ready
from .models import RetrievalItem, RetrievalRequest
from .paths import canonical_reuse_policy_path
from .retrieval_adapters import (
    EmbeddingAPIUnavailable,
    SQLITE_VEC_FALLBACK_WARNING,
    RetrievalSearchDocument,
    TextFallbackAdapter,
    VectorRetrievalAdapter,
    VectorRetrievalUnavailable,
    score_search_document,
    select_retrieval_adapter,
)
from .retrieval_config import (
    DEFAULT_RELATION_EXPANSION_CONFIG,
    DEFAULT_RETRIEVAL_RERANK_CONFIG,
    KNOWLEDGE_PRIORITY_BONUS,
    RelationExpansionConfig,
    RETRIEVAL_PREVIEW_LIMIT,
    RetrievalRerankConfig,
    RETRIEVAL_SCORING_TEXT_LIMIT,
    resolve_retrieval_rerank_config,
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
    except EmbeddingAPIUnavailable:
        _warn_embedding_api_fallback_once()
        matches = TextFallbackAdapter().search(
            documents,
            query_plan=query_plan,
            limit=request.limit,
        )
        retrieval_mode = "text_fallback"

    items: list[RetrievalItem] = []
    for match in matches:
        preview = " ".join(match.document.text.split())[:RETRIEVAL_PREVIEW_LIMIT]
        metadata = dict(match.document.metadata)
        metadata["knowledge_retrieval_adapter"] = match.adapter_name
        metadata["knowledge_retrieval_mode"] = retrieval_mode
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
) -> tuple[list[RetrievalSearchMatch], str]:
    try:
        return (
            VectorRetrievalAdapter().search(
                documents,
                query_text=request.query,
                query_plan=query_plan,
                limit=limit,
            ),
            "vector",
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
        )


def _rerank_system_prompt() -> str:
    return (
        "You are ranking retrieval results for Swallow. "
        "Return strict JSON only with key ordered_indexes containing a list of 0-based item indexes "
        "sorted from most relevant to least relevant."
    )


def _build_rerank_prompt(query: str, items: list[RetrievalItem]) -> str:
    lines = [
        "# Retrieval Rerank",
        "",
        f"query: {query}",
        "Return JSON only: {\"ordered_indexes\": [ ... ]}",
        "",
        "## Candidates",
    ]
    for index, item in enumerate(items):
        lines.extend(
            [
                f"- index: {index}",
                f"  title: {item.title or item.path}",
                f"  path: {item.path}",
                f"  source_type: {item.source_type}",
                f"  score: {item.score}",
                f"  preview: {item.preview}",
            ]
        )
    return "\n".join(lines)


def _parse_rerank_indexes(payload: dict[str, object], *, item_count: int) -> list[int]:
    ordered_indexes = payload.get("ordered_indexes", [])
    if not isinstance(ordered_indexes, list):
        raise ValueError("rerank payload missing ordered_indexes list")
    normalized: list[int] = []
    seen: set[int] = set()
    for value in ordered_indexes:
        if isinstance(value, bool):
            continue
        try:
            index = int(value)
        except (TypeError, ValueError):
            continue
        if index < 0 or index >= item_count or index in seen:
            continue
        seen.add(index)
        normalized.append(index)
    if not normalized:
        raise ValueError("rerank payload did not contain usable indexes")
    for index in range(item_count):
        if index not in seen:
            normalized.append(index)
    return normalized


def rerank_retrieval_items(
    items: list[RetrievalItem],
    *,
    query: str,
    config: RetrievalRerankConfig | None = None,
) -> list[RetrievalItem]:
    from .agent_llm import AgentLLMUnavailable, call_agent_llm, extract_json_object

    rerank_config = config or DEFAULT_RETRIEVAL_RERANK_CONFIG
    if not rerank_config.enabled or len(items) < 2 or not query.strip():
        return items

    top_n = min(rerank_config.top_n, len(items))
    if top_n < 2:
        return items

    candidate_items = items[:top_n]
    try:
        llm_response = call_agent_llm(
            _build_rerank_prompt(query, candidate_items),
            system=_rerank_system_prompt(),
        )
        payload = extract_json_object(llm_response.content)
        ordered_indexes = _parse_rerank_indexes(payload, item_count=len(candidate_items))
    except (AgentLLMUnavailable, ValueError):
        return items

    reranked_items: list[RetrievalItem] = []
    for rerank_position, item_index in enumerate(ordered_indexes, start=1):
        item = candidate_items[item_index]
        metadata = dict(item.metadata)
        metadata["rerank_applied"] = True
        metadata["rerank_model"] = llm_response.model
        metadata["rerank_position"] = rerank_position
        score_breakdown = dict(item.score_breakdown)
        score_breakdown["llm_rerank_applied"] = 1
        reranked_items.append(
            replace(
                item,
                metadata=metadata,
                score_breakdown=score_breakdown,
            )
        )

    return reranked_items + items[top_n:]


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

    matches, retrieval_mode = _vector_or_text_matches(
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
        payload = json.loads(policy_path.read_text(encoding="utf-8"))
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
                seen_object_ids.add(target_object_id)
                queue.append((target_object_id, expanded_score, next_depth))
            elif next_depth < depth_limit:
                queue.append((target_object_id, expanded_score, next_depth))
    return expanded_items


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

    items.sort(key=lambda item: (-item.score, item.path, item.chunk_id))
    items = rerank_retrieval_items(
        items,
        query=retrieval_request.query,
        config=resolve_retrieval_rerank_config(),
    )
    return items[: retrieval_request.limit]
