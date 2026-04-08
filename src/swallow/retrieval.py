from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .knowledge_objects import is_retrieval_reuse_ready
from .models import RetrievalItem, RetrievalRequest
from .retrieval_adapters import select_retrieval_adapter

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
    tokens = list(query_plan.get("tokens", []))
    phrase = str(query_plan.get("phrase", ""))
    token_bigrams = list(query_plan.get("token_bigrams", []))
    path_haystack = relative_path.lower()
    filename_haystack = path_name.lower()
    title_haystack = title.lower()
    content_haystack = chunk_text.lower()
    path_hits = sum(path_haystack.count(token) for token in tokens)
    filename_hits = sum(filename_haystack.count(token) for token in tokens)
    title_hits = sum(title_haystack.count(token) for token in tokens)
    content_hits = sum(content_haystack.count(token) for token in tokens)
    title_phrase_hits = 1 if phrase and phrase in title_haystack else 0
    content_phrase_hits = 1 if phrase and phrase in content_haystack else 0
    bigram_hits = sum(1 for bigram in token_bigrams if bigram in title_haystack or bigram in content_haystack)
    matched_terms = matched_terms_for(tokens, path_haystack, title_haystack, content_haystack)
    coverage_hits = len(matched_terms)
    source_kind_bonus = 2 if relative_path.endswith(".md") and title_hits > 0 else 0
    rerank_bonus = (coverage_hits * 2) + (title_phrase_hits * 4) + (content_phrase_hits * 3) + bigram_hits + source_kind_bonus
    score = (title_hits * 5) + (filename_hits * 4) + (path_hits * 2) + content_hits + rerank_bonus
    return (
        score,
        {
            "path_hits": path_hits,
            "filename_hits": filename_hits,
            "title_hits": title_hits,
            "content_hits": content_hits,
            "title_phrase_hits": title_phrase_hits,
            "content_phrase_hits": content_phrase_hits,
            "bigram_hits": bigram_hits,
            "coverage_hits": coverage_hits,
            "source_kind_bonus": source_kind_bonus,
            "rerank_bonus": rerank_bonus,
        },
        matched_terms,
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


def summarize_reused_knowledge(retrieval_items: list[RetrievalItem]) -> dict[str, Any]:
    knowledge_items = [item for item in retrieval_items if item.source_type == KNOWLEDGE_SOURCE_TYPE]
    evidence_counts = {"artifact_backed": 0, "source_only": 0, "unbacked": 0}
    for item in knowledge_items:
        evidence_status = str(item.metadata.get("evidence_status", "unbacked"))
        evidence_counts[evidence_status] = evidence_counts.get(evidence_status, 0) + 1
    return {
        "count": len(knowledge_items),
        "references": [item.reference() for item in knowledge_items[:5]],
        "object_ids": [str(item.metadata.get("knowledge_object_id", item.chunk_id)) for item in knowledge_items[:5]],
        "evidence_counts": evidence_counts,
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
    if KNOWLEDGE_SOURCE_TYPE not in allowed_sources:
        return []

    items: list[RetrievalItem] = []
    allow_current_task = "task" in request.context_layers
    allow_cross_task = "history" in request.context_layers
    for path in sorted(workspace_root.glob(".swl/tasks/*/knowledge_objects.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, list):
            continue

        relative_path = str(path.relative_to(workspace_root))
        task_id = path.parent.name
        if request.current_task_id:
            if task_id == request.current_task_id and not allow_current_task:
                continue
            if task_id != request.current_task_id and not allow_cross_task:
                continue
        for knowledge_object in payload:
            if not isinstance(knowledge_object, dict):
                continue
            if not is_retrieval_reuse_ready(knowledge_object):
                continue

            knowledge_text = str(knowledge_object.get("text", "")).strip()
            if not knowledge_text:
                continue

            object_id = str(knowledge_object.get("object_id", "knowledge-object"))
            title = f"Knowledge {object_id}"
            score, score_breakdown, matched_terms = score_chunk(
                query_plan=query_plan,
                relative_path=relative_path,
                path_name=path.name,
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
                    chunk_id=object_id,
                    title=title,
                    citation=f"{relative_path}#{object_id}",
                    matched_terms=matched_terms,
                    score_breakdown=score_breakdown,
                    metadata=build_knowledge_item_metadata(
                        knowledge_object=knowledge_object,
                        query_plan=query_plan,
                        knowledge_task_id=task_id,
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
