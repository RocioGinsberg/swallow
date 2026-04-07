from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from .models import RetrievalItem, RetrievalRequest


TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".sh",
}
MARKDOWN_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(?P<title>.+?)\s*$")
REPO_SYMBOL_RE = re.compile(r"^\s*(?:def|class|function)\s+([A-Za-z0-9_]+)")
REPO_CHUNK_LINE_COUNT = 40


def markdown_heading_level(line: str) -> int:
    stripped = line.lstrip()
    return len(stripped) - len(stripped.lstrip("#"))


def citation_for_lines(relative_path: str, line_start: int, line_end: int) -> str:
    if line_start == line_end:
        return f"{relative_path}#L{line_start}"
    return f"{relative_path}#L{line_start}-L{line_end}"


def build_markdown_chunks(path: Path, text: str) -> list[dict[str, object]]:
    lines = text.splitlines()
    if not lines:
        return []

    headings: list[tuple[int, str, int]] = []
    for index, line in enumerate(lines, start=1):
        match = MARKDOWN_HEADING_RE.match(line)
        if match:
            headings.append((index, match.group("title").strip(), markdown_heading_level(line)))

    if not headings:
        return [
            {
                "chunk_id": "full-file",
                "title": path.name,
                "title_source": "filename",
                "chunk_kind": "full_file",
                "line_start": 1,
                "line_end": len(lines),
                "text": text,
                "metadata": {
                    "heading_level": 0,
                },
            }
        ]

    chunks: list[dict[str, object]] = []
    if headings[0][0] > 1:
        preface_end = headings[0][0] - 1
        preface_text = "\n".join(lines[:preface_end]).strip()
        if preface_text:
            chunks.append(
                {
                    "chunk_id": "preface",
                    "title": path.name,
                    "title_source": "filename",
                    "chunk_kind": "markdown_preface",
                    "line_start": 1,
                    "line_end": preface_end,
                    "text": preface_text,
                    "metadata": {
                        "heading_level": 0,
                    },
                }
            )

    for index, (line_start, title, heading_level) in enumerate(headings, start=1):
        line_end = headings[index][0] - 1 if index < len(headings) else len(lines)
        chunk_lines = lines[line_start - 1 : line_end]
        chunk_text = "\n".join(chunk_lines).strip()
        if not chunk_text:
            continue
        chunks.append(
            {
                "chunk_id": f"section-{index}",
                "title": title,
                "title_source": "heading",
                "chunk_kind": "markdown_section",
                "line_start": line_start,
                "line_end": line_end,
                "text": chunk_text,
                "metadata": {
                    "heading_level": heading_level,
                },
            }
        )

    return chunks


def infer_repo_chunk_title(path: Path, chunk_lines: Iterable[str]) -> tuple[str, str]:
    for line in chunk_lines:
        match = REPO_SYMBOL_RE.match(line)
        if match:
            return match.group(1), "symbol"
    return path.name, "filename"


def build_repo_chunks(path: Path, text: str) -> list[dict[str, object]]:
    lines = text.splitlines()
    if not lines:
        return []

    chunks: list[dict[str, object]] = []
    for start_index in range(0, len(lines), REPO_CHUNK_LINE_COUNT):
        line_start = start_index + 1
        line_end = min(start_index + REPO_CHUNK_LINE_COUNT, len(lines))
        chunk_lines = lines[start_index:line_end]
        chunk_text = "\n".join(chunk_lines).strip()
        if not chunk_text:
            continue
        title, title_source = infer_repo_chunk_title(path, chunk_lines)
        chunks.append(
            {
                "chunk_id": f"lines-{line_start}-{line_end}",
                "title": title,
                "title_source": title_source,
                "chunk_kind": "repo_lines",
                "line_start": line_start,
                "line_end": line_end,
                "text": chunk_text,
                "metadata": {},
            }
        )

    return chunks


def matched_terms_for(token_list: list[str], *haystacks: str) -> list[str]:
    return sorted({token for token in token_list if any(haystack.count(token) > 0 for haystack in haystacks)})


def score_chunk(
    tokens: list[str],
    relative_path: str,
    path_name: str,
    title: str,
    chunk_text: str,
) -> tuple[int, dict[str, int], list[str]]:
    path_haystack = relative_path.lower()
    filename_haystack = path_name.lower()
    title_haystack = title.lower()
    content_haystack = chunk_text.lower()
    path_hits = sum(path_haystack.count(token) for token in tokens)
    filename_hits = sum(filename_haystack.count(token) for token in tokens)
    title_hits = sum(title_haystack.count(token) for token in tokens)
    content_hits = sum(content_haystack.count(token) for token in tokens)
    phrase_hits = 1 if tokens and " ".join(tokens) in content_haystack else 0
    score = (title_hits * 5) + (filename_hits * 4) + (path_hits * 2) + content_hits + (phrase_hits * 3)
    matched_terms = matched_terms_for(tokens, path_haystack, title_haystack, content_haystack)
    return (
        score,
        {
            "path_hits": path_hits,
            "filename_hits": filename_hits,
            "title_hits": title_hits,
            "content_hits": content_hits,
            "phrase_hits": phrase_hits,
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


def retrieve_context(
    workspace_root: Path,
    query: str | None = None,
    limit: int = 8,
    source_types: list[str] | None = None,
    request: RetrievalRequest | None = None,
) -> list[RetrievalItem]:
    retrieval_request = request or build_retrieval_request(query=query or "", limit=limit, source_types=source_types)
    tokens = [token for token in re.split(r"[^a-zA-Z0-9]+", retrieval_request.query.lower()) if len(token) > 2]
    allowed_sources = set(retrieval_request.source_types)
    items: list[RetrievalItem] = []

    for path in sorted(workspace_root.rglob("*")):
        if not path.is_file():
            continue
        if ".swl" in path.parts or ".git" in path.parts:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        source_type = "notes" if path.suffix.lower() == ".md" else "repo"
        if source_type not in allowed_sources:
            continue
        relative_path = str(path.relative_to(workspace_root))
        chunks = build_markdown_chunks(path, text) if source_type == "notes" else build_repo_chunks(path, text)
        for chunk in chunks:
            chunk_text = str(chunk["text"])
            score, score_breakdown, matched_terms = score_chunk(
                tokens=tokens,
                relative_path=relative_path,
                path_name=path.name,
                title=str(chunk["title"]),
                chunk_text=chunk_text[:4000],
            )
            if score <= 0:
                continue

            line_start = int(chunk["line_start"])
            line_end = int(chunk["line_end"])
            preview = " ".join(chunk_text.split())[:220]
            items.append(
                RetrievalItem(
                    path=relative_path,
                    source_type=source_type,
                    score=score,
                    preview=preview,
                    chunk_id=str(chunk["chunk_id"]),
                    title=str(chunk["title"]),
                    citation=citation_for_lines(relative_path, line_start, line_end),
                    matched_terms=matched_terms,
                    score_breakdown=score_breakdown,
                    metadata={
                        "extension": path.suffix.lower(),
                        "chunk_kind": str(chunk["chunk_kind"]),
                        "line_start": line_start,
                        "line_end": line_end,
                        "title_source": str(chunk["title_source"]),
                        **dict(chunk["metadata"]),
                    },
                )
            )

    items.sort(key=lambda item: (-item.score, item.path, item.chunk_id))
    return items[: retrieval_request.limit]
