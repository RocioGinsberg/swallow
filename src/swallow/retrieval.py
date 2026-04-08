from __future__ import annotations

import re
from pathlib import Path
from typing import Any

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
    strategy: str = "system_baseline",
) -> RetrievalRequest:
    return RetrievalRequest(
        query=query,
        source_types=source_types or ["repo", "notes"],
        context_layers=context_layers or ["workspace", "task"],
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
    items: list[RetrievalItem] = []

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
