from __future__ import annotations

import importlib
import json
import os
import re
import sqlite3
from hashlib import blake2b
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

import httpx

from swallow.orchestration.runtime_config import (
    resolve_swl_api_key,
    resolve_swl_embedding_api_base_url,
    resolve_swl_embedding_dimensions,
    resolve_swl_embedding_model,
)
from swallow.knowledge_retrieval.retrieval_config import RETRIEVAL_SCORING_TEXT_LIMIT, RetrievalRerankConfig

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
REPO_CHUNK_OVERLAP_LINES = 0
MARKDOWN_CHUNK_OVERLAP_LINES = 0
MARKDOWN_MAX_CHUNK_LINES = 80
SEARCH_TOKEN_RE = re.compile(r"[A-Za-z0-9_./-]+")
VECTOR_EMBEDDING_DIMENSIONS = resolve_swl_embedding_dimensions()
SQLITE_VEC_FALLBACK_WARNING = "[WARN] sqlite-vec unavailable, falling back to text search"


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


@dataclass(slots=True)
class RetrievalSearchDocument:
    path: str
    path_name: str
    source_type: str
    chunk_id: str
    title: str
    citation: str
    text: str
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class RetrievalSearchMatch:
    document: RetrievalSearchDocument
    score: int
    score_breakdown: dict[str, int] = field(default_factory=dict)
    matched_terms: list[str] = field(default_factory=list)
    adapter_name: str = ""


class VectorRetrievalUnavailable(RuntimeError):
    """Raised when sqlite-vec cannot be used for vector retrieval."""


class EmbeddingAPIUnavailable(RuntimeError):
    """Raised when API-backed embeddings are unavailable."""


class DedicatedRerankUnavailable(RuntimeError):
    """Raised when a dedicated rerank endpoint cannot produce an ordering."""


@dataclass(frozen=True, slots=True)
class DedicatedRerankResult:
    ordered_indexes: list[int]
    model: str
    scores_by_index: dict[int, float] = field(default_factory=dict)


def matched_terms_for(token_list: list[str], *haystacks: str) -> list[str]:
    return sorted({token for token in token_list if any(haystack.count(token) > 0 for haystack in haystacks)})


def score_search_document(
    query_plan: dict[str, Any],
    *,
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


def tokenize_embedding_text(text: str) -> list[str]:
    return [token.lower() for token in SEARCH_TOKEN_RE.findall(text) if token]


def build_local_embedding(text: str, *, dimensions: int | None = None) -> list[float]:
    resolved_dimensions = resolve_swl_embedding_dimensions(explicit_dimensions=dimensions)
    vector = [0.0] * resolved_dimensions
    tokens = tokenize_embedding_text(text)
    if not tokens:
        return vector

    weighted_tokens = list(tokens)
    weighted_tokens.extend(
        f"{tokens[index]}::{tokens[index + 1]}"
        for index in range(len(tokens) - 1)
        if tokens[index] != tokens[index + 1]
    )
    for index, token in enumerate(weighted_tokens, start=1):
        digest = blake2b(token.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "little") % resolved_dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        weight = 1.0 if index <= len(tokens) else 0.5
        vector[bucket] += sign * weight

    magnitude = sum(component * component for component in vector) ** 0.5
    if magnitude <= 0.0:
        return vector
    return [component / magnitude for component in vector]


def build_api_embedding(
    text: str,
    *,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    dimensions: int | None = None,
    timeout_seconds: int = 20,
) -> list[float]:
    resolved_api_key = str(api_key or resolve_swl_api_key()).strip()
    if not resolved_api_key:
        raise EmbeddingAPIUnavailable("SWL_API_KEY is not configured.")

    resolved_model = resolve_swl_embedding_model(explicit_model=model)
    resolved_dimensions = resolve_swl_embedding_dimensions(explicit_dimensions=dimensions)
    resolved_base_url = str(base_url or resolve_swl_embedding_api_base_url()).strip().rstrip("/")
    if not resolved_base_url:
        raise EmbeddingAPIUnavailable("SWL_EMBEDDING_API_BASE_URL is not configured.")

    try:
        response = httpx.post(
            f"{resolved_base_url}/v1/embeddings",
            json={"model": resolved_model, "input": text},
            headers={
                "Authorization": f"Bearer {resolved_api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError as exc:
        raise EmbeddingAPIUnavailable(str(exc)) from exc
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise EmbeddingAPIUnavailable(f"Unreadable embedding payload: {exc}") from exc

    try:
        data = payload["data"]
        embedding = data[0]["embedding"]
    except (KeyError, IndexError, TypeError) as exc:
        raise EmbeddingAPIUnavailable(f"Embedding payload missing vector data: {exc}") from exc
    if not isinstance(embedding, list) or not embedding:
        raise EmbeddingAPIUnavailable("Embedding payload returned an empty vector.")

    normalized: list[float] = []
    for value in embedding:
        try:
            normalized.append(float(value))
        except (TypeError, ValueError) as exc:
            raise EmbeddingAPIUnavailable(f"Embedding payload contained a non-numeric value: {exc}") from exc
    if len(normalized) != resolved_dimensions:
        raise EmbeddingAPIUnavailable(
            f"Embedding dimensions mismatch: expected {resolved_dimensions}, got {len(normalized)}."
        )
    return normalized


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    return sum(left[index] * right[index] for index in range(min(len(left), len(right))))


def rank_documents_by_local_embedding(
    documents: list[RetrievalSearchDocument],
    *,
    query_text: str,
    query_plan: dict[str, Any],
    limit: int,
    adapter_name: str = "local_embedding",
    embedding_dimensions: int | None = None,
) -> list[RetrievalSearchMatch]:
    # eval-only: production retrieval uses TextFallbackAdapter or VectorRetrievalAdapter.
    resolved_dimensions = resolve_swl_embedding_dimensions(explicit_dimensions=embedding_dimensions)
    query_embedding = build_local_embedding(query_text, dimensions=resolved_dimensions)
    matches: list[RetrievalSearchMatch] = []
    for document in documents:
        text_score, text_breakdown, matched_terms = score_search_document(
            query_plan,
            relative_path=document.path,
            path_name=document.path_name,
            title=document.title,
            chunk_text=document.text[:RETRIEVAL_SCORING_TEXT_LIMIT],
        )
        similarity = cosine_similarity(
            query_embedding,
            build_local_embedding(
                f"{document.title}\n{document.text}",
                dimensions=resolved_dimensions,
            ),
        )
        similarity = max(-1.0, min(similarity, 1.0))
        embedding_bonus = max(1, int(round((similarity + 1.0) * 3)))
        score_breakdown = dict(text_breakdown)
        score_breakdown["embedding_bonus"] = embedding_bonus
        score_breakdown["embedding_similarity_milli"] = int(round(similarity * 1000))
        matches.append(
            RetrievalSearchMatch(
                document=document,
                score=max(text_score, 0) + embedding_bonus,
                score_breakdown=score_breakdown,
                matched_terms=matched_terms,
                adapter_name=adapter_name,
            )
        )
    matches.sort(key=lambda match: (-match.score, match.document.path, match.document.chunk_id))
    return matches[:limit]


@dataclass(slots=True)
class TextFallbackAdapter:
    name: str = "text_fallback"

    def search(
        self,
        documents: list[RetrievalSearchDocument],
        *,
        query_plan: dict[str, Any],
        limit: int,
    ) -> list[RetrievalSearchMatch]:
        matches: list[RetrievalSearchMatch] = []
        for document in documents:
            score, score_breakdown, matched_terms = score_search_document(
                query_plan,
                relative_path=document.path,
                path_name=document.path_name,
                title=document.title,
                chunk_text=document.text[:RETRIEVAL_SCORING_TEXT_LIMIT],
            )
            if score <= 0:
                continue
            matches.append(
                RetrievalSearchMatch(
                    document=document,
                    score=score,
                    score_breakdown=score_breakdown,
                    matched_terms=matched_terms,
                    adapter_name=self.name,
                )
            )
        matches.sort(key=lambda match: (-match.score, match.document.path, match.document.chunk_id))
        return matches[:limit]


@dataclass(slots=True)
class VectorRetrievalAdapter:
    name: str = "sqlite_vec"
    module_name: str = "sqlite_vec"
    embedding_dimensions: int = field(default_factory=resolve_swl_embedding_dimensions)

    def _load_module(self) -> Any:
        try:
            return importlib.import_module(self.module_name)
        except ImportError as exc:
            raise VectorRetrievalUnavailable(str(exc)) from exc

    def _connect(self) -> sqlite3.Connection:
        module = self._load_module()
        connection = sqlite3.connect(":memory:")
        try:
            connection.row_factory = sqlite3.Row
            if not hasattr(connection, "enable_load_extension"):
                raise VectorRetrievalUnavailable("sqlite3 extension loading is unavailable in this Python build")
            connection.enable_load_extension(True)
            module.load(connection)
            connection.enable_load_extension(False)
            connection.execute("SELECT vec_version()").fetchone()
            return connection
        except Exception as exc:
            connection.close()
            raise VectorRetrievalUnavailable(str(exc)) from exc

    def search(
        self,
        documents: list[RetrievalSearchDocument],
        *,
        query_text: str,
        query_plan: dict[str, Any],
        limit: int,
    ) -> list[RetrievalSearchMatch]:
        if not documents:
            return []

        query_embedding = build_api_embedding(
            query_text,
            dimensions=self.embedding_dimensions,
        )
        query_embedding_json = json.dumps(query_embedding, separators=(",", ":"))
        connection = self._connect()
        try:
            connection.execute(
                """
                CREATE TEMP TABLE swl_retrieval_vectors (
                    row_id INTEGER PRIMARY KEY,
                    document_json TEXT NOT NULL,
                    embedding_json TEXT NOT NULL
                )
                """
            )
            connection.executemany(
                """
                INSERT INTO swl_retrieval_vectors (row_id, document_json, embedding_json)
                VALUES (?, ?, ?)
                """,
                [
                    (
                        index,
                        json.dumps(
                            {
                                "path": document.path,
                                "path_name": document.path_name,
                                "source_type": document.source_type,
                                "chunk_id": document.chunk_id,
                                "title": document.title,
                                "citation": document.citation,
                                "text": document.text,
                                "metadata": document.metadata,
                            },
                            separators=(",", ":"),
                        ),
                        json.dumps(
                            build_api_embedding(
                                f"{document.title}\n{document.text}",
                                dimensions=self.embedding_dimensions,
                            ),
                            separators=(",", ":"),
                        ),
                    )
                    for index, document in enumerate(documents, start=1)
                ],
            )
            rows = connection.execute(
                """
                SELECT
                    document_json,
                    vec_distance_cosine(vec_f32(embedding_json), vec_f32(?)) AS distance
                FROM swl_retrieval_vectors
                ORDER BY distance ASC, row_id ASC
                LIMIT ?
                """,
                (query_embedding_json, limit),
            ).fetchall()
        except Exception as exc:
            raise VectorRetrievalUnavailable(str(exc)) from exc
        finally:
            connection.close()

        matches: list[RetrievalSearchMatch] = []
        for row in rows:
            payload = json.loads(str(row["document_json"]))
            document = RetrievalSearchDocument(
                path=str(payload.get("path", "")),
                path_name=str(payload.get("path_name", "")),
                source_type=str(payload.get("source_type", "")),
                chunk_id=str(payload.get("chunk_id", "")),
                title=str(payload.get("title", "")),
                citation=str(payload.get("citation", "")),
                text=str(payload.get("text", "")),
                metadata=dict(payload.get("metadata", {}))
                if isinstance(payload.get("metadata", {}), dict)
                else {},
            )
            text_score, text_breakdown, matched_terms = score_search_document(
                query_plan,
                relative_path=document.path,
                path_name=document.path_name,
                title=document.title,
                chunk_text=document.text[:RETRIEVAL_SCORING_TEXT_LIMIT],
            )
            distance = max(0.0, min(float(row["distance"]), 2.0))
            vector_bonus = max(1, int(round((2.0 - distance) * 3)))
            score_breakdown = dict(text_breakdown)
            score_breakdown["vector_bonus"] = vector_bonus
            score_breakdown["vector_distance_milli"] = int(round(distance * 1000))
            metadata = dict(document.metadata)
            metadata["embedding_backend"] = "api_embedding"
            matches.append(
                RetrievalSearchMatch(
                    document=RetrievalSearchDocument(
                        path=document.path,
                        path_name=document.path_name,
                        source_type=document.source_type,
                        chunk_id=document.chunk_id,
                        title=document.title,
                        citation=document.citation,
                        text=document.text,
                        metadata=metadata,
                    ),
                    score=max(text_score, 0) + vector_bonus,
                    score_breakdown=score_breakdown,
                    matched_terms=matched_terms,
                    adapter_name=self.name,
                )
            )
        matches.sort(key=lambda match: (-match.score, match.document.path, match.document.chunk_id))
        return matches[:limit]


@dataclass(slots=True)
class DedicatedRerankAdapter:
    name: str = "dedicated_http_rerank"

    def rerank(
        self,
        *,
        query_text: str,
        documents: list[RetrievalSearchDocument],
        config: RetrievalRerankConfig,
    ) -> DedicatedRerankResult:
        if not config.configured:
            raise DedicatedRerankUnavailable("dedicated rerank model/url is not configured")
        if not documents:
            raise DedicatedRerankUnavailable("no documents to rerank")

        api_key = os.environ.get("SWL_RETRIEVAL_RERANK_API_KEY", "").strip() or resolve_swl_api_key()
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            response = httpx.post(
                config.url,
                json={
                    "model": config.model,
                    "query": query_text,
                    "documents": [self._document_text(document) for document in documents],
                },
                headers=headers,
                timeout=config.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise DedicatedRerankUnavailable(str(exc)) from exc
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise DedicatedRerankUnavailable(f"Unreadable rerank payload: {exc}") from exc

        return self._parse_response(payload, item_count=len(documents), requested_model=config.model)

    @staticmethod
    def _document_text(document: RetrievalSearchDocument) -> str:
        title = document.title.strip()
        text = document.text.strip()
        if title and text:
            return f"{title}\n{text}"
        return title or text

    @staticmethod
    def _parse_response(payload: object, *, item_count: int, requested_model: str) -> DedicatedRerankResult:
        if not isinstance(payload, dict):
            raise DedicatedRerankUnavailable("rerank payload must be a JSON object")

        returned_model = str(payload.get("model", "") or requested_model).strip() or requested_model
        ordered_indexes = payload.get("ordered_indexes")
        if isinstance(ordered_indexes, list):
            return DedicatedRerankResult(
                ordered_indexes=_normalize_ordered_indexes(ordered_indexes, item_count=item_count),
                model=returned_model,
            )

        results = payload.get("results")
        if not isinstance(results, list):
            results = payload.get("data")
        if not isinstance(results, list):
            raise DedicatedRerankUnavailable("rerank payload missing results/data list")

        ranked: list[tuple[int, float, int]] = []
        scores_by_index: dict[int, float] = {}
        for position, result in enumerate(results):
            if not isinstance(result, dict):
                continue
            raw_index = result.get("index")
            if raw_index is None:
                raw_index = result.get("document_index")
            try:
                index = int(raw_index)
            except (TypeError, ValueError):
                continue
            if index < 0 or index >= item_count:
                continue
            raw_score = result.get("relevance_score")
            if raw_score is None:
                raw_score = result.get("score")
            try:
                score = float(raw_score)
            except (TypeError, ValueError):
                score = float(item_count - position)
            scores_by_index[index] = score
            ranked.append((index, score, position))

        if not ranked:
            raise DedicatedRerankUnavailable("rerank payload did not contain usable result indexes")
        ranked.sort(key=lambda value: (-value[1], value[2], value[0]))
        return DedicatedRerankResult(
            ordered_indexes=_normalize_ordered_indexes(
                [index for index, _score, _position in ranked],
                item_count=item_count,
            ),
            model=returned_model,
            scores_by_index=scores_by_index,
        )


def _normalize_ordered_indexes(raw_indexes: list[object], *, item_count: int) -> list[int]:
    normalized: list[int] = []
    seen: set[int] = set()
    for value in raw_indexes:
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
        raise DedicatedRerankUnavailable("rerank payload did not contain usable indexes")
    for index in range(item_count):
        if index not in seen:
            normalized.append(index)
    return normalized


def markdown_heading_level(line: str) -> int:
    stripped = line.lstrip()
    return len(stripped) - len(stripped.lstrip("#"))


def _expand_range_with_overlap(
    lines: list[str],
    line_start: int,
    line_end: int,
    *,
    overlap_lines: int,
    total_lines: int,
) -> tuple[int, int]:
    if overlap_lines <= 0:
        return line_start, line_end
    expanded_start = line_start
    remaining = overlap_lines
    while expanded_start > 1 and remaining > 0:
        expanded_start -= 1
        if lines[expanded_start - 1].strip():
            remaining -= 1
    return expanded_start, min(total_lines, line_end)


def _split_range_by_max_lines(
    lines: list[str],
    *,
    line_start: int,
    line_end: int,
    max_chunk_size: int,
) -> list[tuple[int, int]]:
    if line_end < line_start:
        return []
    if max_chunk_size <= 0 or (line_end - line_start + 1) <= max_chunk_size:
        return [(line_start, line_end)]

    ranges: list[tuple[int, int]] = []
    cursor = line_start
    while cursor <= line_end:
        hard_end = min(cursor + max_chunk_size - 1, line_end)
        split_end = hard_end
        if hard_end < line_end:
            for candidate in range(hard_end, cursor, -1):
                if not lines[candidate - 1].strip():
                    split_end = candidate - 1
                    break
            if split_end < cursor:
                split_end = hard_end

        while cursor <= split_end and not lines[cursor - 1].strip():
            cursor += 1
        while split_end >= cursor and not lines[split_end - 1].strip():
            split_end -= 1
        if cursor > split_end:
            cursor = hard_end + 1
            continue

        ranges.append((cursor, split_end))
        cursor = split_end + 1
        while cursor <= line_end and not lines[cursor - 1].strip():
            cursor += 1
    return ranges


def _build_chunk_text(lines: list[str], *, line_start: int, line_end: int) -> str:
    return "\n".join(lines[line_start - 1 : line_end]).strip()


def build_markdown_chunks(
    path: Path,
    text: str,
    *,
    overlap_lines: int = MARKDOWN_CHUNK_OVERLAP_LINES,
    max_chunk_size: int = MARKDOWN_MAX_CHUNK_LINES,
) -> list[RetrievalChunk]:
    lines = text.splitlines()
    if not lines:
        return []

    headings: list[tuple[int, str, int]] = []
    for index, line in enumerate(lines, start=1):
        match = MARKDOWN_HEADING_RE.match(line)
        if match:
            headings.append((index, match.group("title").strip(), markdown_heading_level(line)))

    if not headings:
        chunks: list[RetrievalChunk] = []
        ranges = _split_range_by_max_lines(
            lines,
            line_start=1,
            line_end=len(lines),
            max_chunk_size=max_chunk_size,
        )
        for index, (base_start, base_end) in enumerate(ranges, start=1):
            chunk_start, chunk_end = _expand_range_with_overlap(
                lines,
                base_start,
                base_end,
                overlap_lines=overlap_lines,
                total_lines=len(lines),
            )
            chunk_text = _build_chunk_text(lines, line_start=chunk_start, line_end=chunk_end)
            if not chunk_text:
                continue
            chunk_id = "full-file" if len(ranges) == 1 else f"full-file-{index}"
            chunks.append(
                RetrievalChunk(
                    chunk_id=chunk_id,
                    title=path.name,
                    title_source="filename",
                    chunk_kind="full_file",
                    line_start=chunk_start,
                    line_end=chunk_end,
                    text=chunk_text,
                    metadata={
                        "heading_level": 0,
                        "base_line_start": base_start,
                        "base_line_end": base_end,
                        "overlap_lines": overlap_lines,
                    },
                )
            )
        return chunks

    chunks: list[RetrievalChunk] = []
    if headings[0][0] > 1:
        preface_end = headings[0][0] - 1
        preface_ranges = _split_range_by_max_lines(
            lines,
            line_start=1,
            line_end=preface_end,
            max_chunk_size=max_chunk_size,
        )
        for index, (base_start, base_end) in enumerate(preface_ranges, start=1):
            chunk_start, chunk_end = _expand_range_with_overlap(
                lines,
                base_start,
                base_end,
                overlap_lines=overlap_lines,
                total_lines=len(lines),
            )
            preface_text = _build_chunk_text(lines, line_start=chunk_start, line_end=chunk_end)
            if not preface_text:
                continue
            chunk_id = "preface" if len(preface_ranges) == 1 else f"preface-{index}"
            chunks.append(
                RetrievalChunk(
                    chunk_id=chunk_id,
                    title=path.name,
                    title_source="filename",
                    chunk_kind="markdown_preface",
                    line_start=chunk_start,
                    line_end=chunk_end,
                    text=preface_text,
                    metadata={
                        "heading_level": 0,
                        "base_line_start": base_start,
                        "base_line_end": base_end,
                        "overlap_lines": overlap_lines,
                    },
                )
            )

    for index, (line_start, title, heading_level) in enumerate(headings, start=1):
        line_end = headings[index][0] - 1 if index < len(headings) else len(lines)
        section_ranges = _split_range_by_max_lines(
            lines,
            line_start=line_start,
            line_end=line_end,
            max_chunk_size=max_chunk_size,
        )
        for segment_index, (base_start, base_end) in enumerate(section_ranges, start=1):
            chunk_start, chunk_end = _expand_range_with_overlap(
                lines,
                base_start,
                base_end,
                overlap_lines=overlap_lines,
                total_lines=len(lines),
            )
            chunk_text = _build_chunk_text(lines, line_start=chunk_start, line_end=chunk_end)
            if not chunk_text:
                continue
            chunk_id = f"section-{index}"
            if len(section_ranges) > 1:
                chunk_id = f"section-{index}-{segment_index}"
            chunks.append(
                RetrievalChunk(
                    chunk_id=chunk_id,
                    title=title,
                    title_source="heading",
                    chunk_kind="markdown_section",
                    line_start=chunk_start,
                    line_end=chunk_end,
                    text=chunk_text,
                    metadata={
                        "heading_level": heading_level,
                        "base_line_start": base_start,
                        "base_line_end": base_end,
                        "overlap_lines": overlap_lines,
                        "segment_index": segment_index,
                        "segment_count": len(section_ranges),
                    },
                )
            )

    return chunks


def infer_repo_chunk_title(path: Path, chunk_lines: Iterable[str]) -> tuple[str, str]:
    for line in chunk_lines:
        match = REPO_SYMBOL_RE.match(line)
        if match:
            return match.group(1), "symbol"
    return path.name, "filename"


def build_repo_chunks(
    path: Path,
    text: str,
    *,
    overlap_lines: int = REPO_CHUNK_OVERLAP_LINES,
) -> list[RetrievalChunk]:
    lines = text.splitlines()
    if not lines:
        return []

    chunks: list[RetrievalChunk] = []
    for start_index in range(0, len(lines), REPO_CHUNK_LINE_COUNT):
        base_line_start = start_index + 1
        base_line_end = min(start_index + REPO_CHUNK_LINE_COUNT, len(lines))
        line_start, line_end = _expand_range_with_overlap(
            lines,
            base_line_start,
            base_line_end,
            overlap_lines=overlap_lines,
            total_lines=len(lines),
        )
        chunk_lines = lines[line_start - 1 : line_end]
        chunk_text = "\n".join(chunk_lines).strip()
        if not chunk_text:
            continue
        title, title_source = infer_repo_chunk_title(path, chunk_lines)
        chunks.append(
            RetrievalChunk(
                chunk_id=f"lines-{base_line_start}-{base_line_end}",
                title=title,
                title_source=title_source,
                chunk_kind="repo_lines",
                line_start=line_start,
                line_end=line_end,
                text=chunk_text,
                metadata={
                    "base_line_start": base_line_start,
                    "base_line_end": base_line_end,
                    "overlap_lines": overlap_lines,
                },
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
