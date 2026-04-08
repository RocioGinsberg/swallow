from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable


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


@dataclass(slots=True)
class RetrievalChunk:
    chunk_id: str
    title: str
    title_source: str
    chunk_kind: str
    line_start: int
    line_end: int
    text: str
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "chunk_id": self.chunk_id,
            "title": self.title,
            "title_source": self.title_source,
            "chunk_kind": self.chunk_kind,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "text": self.text,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class RetrievalSourceAdapter:
    name: str
    source_type: str
    supported_suffixes: set[str]
    build_chunks: Callable[[Path, str], list[RetrievalChunk]]


def markdown_heading_level(line: str) -> int:
    stripped = line.lstrip()
    return len(stripped) - len(stripped.lstrip("#"))


def build_markdown_chunks(path: Path, text: str) -> list[RetrievalChunk]:
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
            RetrievalChunk(
                chunk_id="full-file",
                title=path.name,
                title_source="filename",
                chunk_kind="full_file",
                line_start=1,
                line_end=len(lines),
                text=text,
                metadata={"heading_level": 0},
            )
        ]

    chunks: list[RetrievalChunk] = []
    if headings[0][0] > 1:
        preface_end = headings[0][0] - 1
        preface_text = "\n".join(lines[:preface_end]).strip()
        if preface_text:
            chunks.append(
                RetrievalChunk(
                    chunk_id="preface",
                    title=path.name,
                    title_source="filename",
                    chunk_kind="markdown_preface",
                    line_start=1,
                    line_end=preface_end,
                    text=preface_text,
                    metadata={"heading_level": 0},
                )
            )

    for index, (line_start, title, heading_level) in enumerate(headings, start=1):
        line_end = headings[index][0] - 1 if index < len(headings) else len(lines)
        chunk_lines = lines[line_start - 1 : line_end]
        chunk_text = "\n".join(chunk_lines).strip()
        if not chunk_text:
            continue
        chunks.append(
            RetrievalChunk(
                chunk_id=f"section-{index}",
                title=title,
                title_source="heading",
                chunk_kind="markdown_section",
                line_start=line_start,
                line_end=line_end,
                text=chunk_text,
                metadata={"heading_level": heading_level},
            )
        )

    return chunks


def infer_repo_chunk_title(path: Path, chunk_lines: Iterable[str]) -> tuple[str, str]:
    for line in chunk_lines:
        match = REPO_SYMBOL_RE.match(line)
        if match:
            return match.group(1), "symbol"
    return path.name, "filename"


def build_repo_chunks(path: Path, text: str) -> list[RetrievalChunk]:
    lines = text.splitlines()
    if not lines:
        return []

    chunks: list[RetrievalChunk] = []
    for start_index in range(0, len(lines), REPO_CHUNK_LINE_COUNT):
        line_start = start_index + 1
        line_end = min(start_index + REPO_CHUNK_LINE_COUNT, len(lines))
        chunk_lines = lines[start_index:line_end]
        chunk_text = "\n".join(chunk_lines).strip()
        if not chunk_text:
            continue
        title, title_source = infer_repo_chunk_title(path, chunk_lines)
        chunks.append(
            RetrievalChunk(
                chunk_id=f"lines-{line_start}-{line_end}",
                title=title,
                title_source=title_source,
                chunk_kind="repo_lines",
                line_start=line_start,
                line_end=line_end,
                text=chunk_text,
                metadata={},
            )
        )

    return chunks


MARKDOWN_ADAPTER = RetrievalSourceAdapter(
    name="markdown_notes",
    source_type="notes",
    supported_suffixes={".md"},
    build_chunks=build_markdown_chunks,
)

REPO_TEXT_ADAPTER = RetrievalSourceAdapter(
    name="repo_text",
    source_type="repo",
    supported_suffixes=TEXT_SUFFIXES - {".md"},
    build_chunks=build_repo_chunks,
)

BUILTIN_RETRIEVAL_ADAPTERS = [MARKDOWN_ADAPTER, REPO_TEXT_ADAPTER]


def select_retrieval_adapter(path: Path) -> RetrievalSourceAdapter | None:
    suffix = path.suffix.lower()
    for adapter in BUILTIN_RETRIEVAL_ADAPTERS:
        if suffix in adapter.supported_suffixes:
            return adapter
    return None
