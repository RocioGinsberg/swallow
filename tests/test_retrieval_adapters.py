from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import swallow.knowledge_retrieval.retrieval as retrieval_module
from swallow.knowledge_retrieval.canonical_reuse import build_canonical_reuse_summary
from swallow.knowledge_retrieval.retrieval import KNOWLEDGE_SOURCE_TYPE, prepare_query_plan, rerank_retrieval_items, retrieve_context
from swallow.knowledge_retrieval.retrieval_config import DEFAULT_RELATION_EXPANSION_CONFIG, RetrievalRerankConfig
from swallow.knowledge_retrieval.retrieval_adapters import (
    DedicatedRerankAdapter,
    DedicatedRerankResult,
    DedicatedRerankUnavailable,
    EmbeddingAPIUnavailable,
    build_markdown_chunks,
    build_repo_chunks,
    RetrievalSearchDocument,
    RetrievalSearchMatch,
    TextFallbackAdapter,
    VectorRetrievalAdapter,
    VectorRetrievalUnavailable,
    build_api_embedding,
)
from swallow.knowledge_retrieval.knowledge_relations import create_knowledge_relation
from swallow.knowledge_retrieval.knowledge_store import TEST_FIXTURE_CANONICAL_WRITE_AUTHORITY, persist_wiki_entry_from_record
from swallow.orchestration.models import RetrievalRequest
from swallow.truth_governance.store import append_canonical_record, save_canonical_reuse_policy, save_knowledge_objects


class RetrievalAdaptersTest(unittest.TestCase):
    def test_build_markdown_chunks_adds_overlap_between_sections(self) -> None:
        chunks = build_markdown_chunks(
            Path("notes.md"),
            "\n".join(
                [
                    "# Intro",
                    "line 1",
                    "line 2",
                    "# Next",
                    "line 3",
                    "line 4",
                ]
            ),
            overlap_lines=2,
            max_chunk_size=80,
        )

        self.assertEqual([chunk.chunk_id for chunk in chunks], ["section-1", "section-2"])
        self.assertEqual(chunks[0].line_start, 1)
        self.assertEqual(chunks[0].line_end, 3)
        self.assertEqual(chunks[1].line_start, 2)
        self.assertEqual(chunks[1].metadata["base_line_start"], 4)
        self.assertEqual(chunks[1].metadata["overlap_lines"], 2)
        self.assertIn("line 2", chunks[1].text)
        self.assertIn("# Next", chunks[1].text)

    def test_build_markdown_chunks_splits_long_section_by_paragraphs(self) -> None:
        text = "\n".join(
            [
                "# Long",
                "alpha 1",
                "alpha 2",
                "",
                "beta 1",
                "beta 2",
                "",
                "gamma 1",
                "gamma 2",
            ]
        )

        chunks = build_markdown_chunks(
            Path("notes.md"),
            text,
            overlap_lines=1,
            max_chunk_size=4,
        )

        self.assertEqual([chunk.chunk_id for chunk in chunks], ["section-1-1", "section-1-2", "section-1-3"])
        self.assertEqual(chunks[0].metadata["segment_count"], 3)
        self.assertEqual(chunks[1].line_start, 3)
        self.assertEqual(chunks[1].metadata["base_line_start"], 5)
        self.assertIn("alpha 2", chunks[1].text)
        self.assertIn("beta 1", chunks[1].text)
        self.assertIn("gamma 1", chunks[2].text)

    def test_build_markdown_chunks_splits_plain_text_files(self) -> None:
        text = "\n".join([f"line {index}" for index in range(1, 8)])

        chunks = build_markdown_chunks(
            Path("plain.md"),
            text,
            overlap_lines=1,
            max_chunk_size=3,
        )

        self.assertEqual([chunk.chunk_id for chunk in chunks], ["full-file-1", "full-file-2", "full-file-3"])
        self.assertEqual(chunks[1].line_start, 3)
        self.assertEqual(chunks[1].metadata["base_line_start"], 4)
        self.assertIn("line 3", chunks[1].text)

    def test_build_repo_chunks_adds_overlap_without_changing_base_chunk_ids(self) -> None:
        text = "\n".join([f"line {index}" for index in range(1, 46)])

        chunks = build_repo_chunks(
            Path("module.py"),
            text,
            overlap_lines=2,
        )

        self.assertEqual([chunk.chunk_id for chunk in chunks], ["lines-1-40", "lines-41-45"])
        self.assertEqual(chunks[0].line_start, 1)
        self.assertEqual(chunks[0].line_end, 40)
        self.assertEqual(chunks[1].line_start, 39)
        self.assertEqual(chunks[1].metadata["base_line_start"], 41)
        self.assertIn("line 39", chunks[1].text)

    def test_rerank_retrieval_items_reorders_top_candidates(self) -> None:
        items = [
            RetrievalSearchMatch(
                document=RetrievalSearchDocument(
                    path="results/knowledge.md",
                    path_name="knowledge.md",
                    source_type="notes",
                    chunk_id="notes-1",
                    title="Notes",
                    citation="results/knowledge.md#L1",
                    text="Noisy notes first.",
                ),
                score=100,
                score_breakdown={"content_hits": 10},
                matched_terms=["knowledge"],
                adapter_name="text_fallback",
            ),
            RetrievalSearchMatch(
                document=RetrievalSearchDocument(
                    path=".swl/canonical_knowledge/reuse_policy.json",
                    path_name="reuse_policy.json",
                    source_type=KNOWLEDGE_SOURCE_TYPE,
                    chunk_id="canonical-1",
                    title="Canonical 1",
                    citation=".swl/canonical_knowledge/reuse_policy.json#canonical-1",
                    text="Canonical truth layer.",
                ),
                score=90,
                score_breakdown={"content_hits": 8},
                matched_terms=["truth"],
                adapter_name="sqlite_vec",
            ),
        ]
        retrieval_items = [
            retrieval_module.RetrievalItem(
                path=match.document.path,
                source_type=match.document.source_type,
                score=match.score,
                preview=match.document.text,
                chunk_id=match.document.chunk_id,
                title=match.document.title,
                citation=match.document.citation,
                matched_terms=match.matched_terms,
                score_breakdown=match.score_breakdown,
                metadata=dict(match.document.metadata),
            )
            for match in items
        ]

        with patch(
            "swallow.knowledge_retrieval.retrieval.DedicatedRerankAdapter.rerank",
            return_value=DedicatedRerankResult(
                ordered_indexes=[1, 0],
                model="bge-reranker",
                scores_by_index={1: 0.92, 0: 0.14},
            ),
        ):
            reranked = rerank_retrieval_items(
                retrieval_items,
                query="knowledge truth",
                config=RetrievalRerankConfig(
                    enabled=True,
                    top_n=2,
                    model="bge-reranker",
                    url="http://rerank.example/v1/rerank",
                ),
            )

        self.assertEqual(reranked[0].chunk_id, "canonical-1")
        self.assertTrue(reranked[0].metadata["rerank_applied"])
        self.assertEqual(reranked[0].metadata["rerank_backend"], "dedicated_http")
        self.assertEqual(reranked[0].metadata["rerank_model"], "bge-reranker")
        self.assertEqual(reranked[0].metadata["rerank_position"], 1)
        self.assertEqual(reranked[0].metadata["rerank_score"], 0.92)
        self.assertEqual(reranked[0].metadata["final_order_basis"], "dedicated_rerank")

    def test_rerank_retrieval_items_keeps_raw_order_on_dedicated_rerank_failure(self) -> None:
        items = [
            retrieval_module.RetrievalItem(
                path="results/knowledge.md",
                source_type="notes",
                score=100,
                preview="Noisy notes first.",
                chunk_id="notes-1",
                title="Notes",
                citation="results/knowledge.md#L1",
                matched_terms=["knowledge"],
                score_breakdown={"content_hits": 10},
                metadata={},
            ),
            retrieval_module.RetrievalItem(
                path=".swl/canonical_knowledge/reuse_policy.json",
                source_type=KNOWLEDGE_SOURCE_TYPE,
                score=90,
                preview="Canonical truth layer.",
                chunk_id="canonical-1",
                title="Canonical 1",
                citation=".swl/canonical_knowledge/reuse_policy.json#canonical-1",
                matched_terms=["truth"],
                score_breakdown={"content_hits": 8},
                metadata={},
            ),
        ]

        with patch(
            "swallow.knowledge_retrieval.retrieval.DedicatedRerankAdapter.rerank",
            side_effect=DedicatedRerankUnavailable("timeout"),
        ):
            reranked = rerank_retrieval_items(
                items,
                query="knowledge truth",
                config=RetrievalRerankConfig(
                    enabled=True,
                    top_n=2,
                    model="bge-reranker",
                    url="http://rerank.example/v1/rerank",
                ),
            )

        self.assertEqual([item.chunk_id for item in reranked], ["notes-1", "canonical-1"])
        self.assertTrue(reranked[0].metadata["rerank_attempted"])
        self.assertFalse(reranked[0].metadata["rerank_applied"])
        self.assertEqual(reranked[0].metadata["rerank_failure_reason"], "timeout")
        self.assertEqual(reranked[0].metadata["final_order_basis"], "raw_score")

    def test_rerank_retrieval_items_does_not_use_chat_when_dedicated_rerank_is_unconfigured(self) -> None:
        items = [
            retrieval_module.RetrievalItem(path="notes.md", source_type="notes", score=2, preview="notes"),
            retrieval_module.RetrievalItem(path="truth.md", source_type="knowledge", score=1, preview="truth"),
        ]

        with patch("swallow.provider_router.agent_llm.call_agent_llm") as chat_rerank_mock:
            with patch("swallow.knowledge_retrieval.retrieval.DedicatedRerankAdapter.rerank") as dedicated_rerank_mock:
                reranked = rerank_retrieval_items(
                    items,
                    query="knowledge truth",
                    config=RetrievalRerankConfig(enabled=True, top_n=2),
                )

        chat_rerank_mock.assert_not_called()
        dedicated_rerank_mock.assert_not_called()
        self.assertEqual([item.path for item in reranked], ["notes.md", "truth.md"])
        self.assertFalse(reranked[0].metadata["rerank_configured"])
        self.assertEqual(reranked[0].metadata["rerank_failure_reason"], "not_configured")

    def test_build_api_embedding_reads_openai_compatible_response(self) -> None:
        class _FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return {"data": [{"embedding": [0.1, 0.2, 0.3]}]}

        with patch("swallow.knowledge_retrieval.retrieval_adapters.httpx.post", return_value=_FakeResponse()) as http_post:
            embedding = build_api_embedding(
                "semantic retrieval",
                model="text-embedding-3-small",
                base_url="http://localhost:3000",
                api_key="test-key",
                dimensions=3,
            )

        self.assertEqual(embedding, [0.1, 0.2, 0.3])
        self.assertEqual(http_post.call_args.kwargs["json"]["model"], "text-embedding-3-small")

    def test_dedicated_rerank_adapter_uses_explicit_rerank_endpoint(self) -> None:
        class _FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return {
                    "model": "bge-reranker",
                    "results": [
                        {"index": 1, "relevance_score": 0.95},
                        {"index": 0, "relevance_score": 0.12},
                    ],
                }

        documents = [
            RetrievalSearchDocument(
                path="notes.md",
                path_name="notes.md",
                source_type="notes",
                chunk_id="notes-1",
                title="Noisy notes",
                citation="notes.md#L1",
                text="Noisy notes.",
            ),
            RetrievalSearchDocument(
                path="truth.md",
                path_name="truth.md",
                source_type=KNOWLEDGE_SOURCE_TYPE,
                chunk_id="truth-1",
                title="Canonical truth",
                citation="truth.md#truth-1",
                text="Canonical truth.",
            ),
        ]

        with patch.dict("os.environ", {"SWL_API_KEY": "test-key"}, clear=False):
            with patch("swallow.knowledge_retrieval.retrieval_adapters.httpx.post", return_value=_FakeResponse()) as http_post:
                result = DedicatedRerankAdapter().rerank(
                    query_text="knowledge truth",
                    documents=documents,
                    config=RetrievalRerankConfig(
                        enabled=True,
                        top_n=2,
                        model="bge-reranker",
                        url="http://rerank.example/v1/rerank",
                    ),
                )

        self.assertEqual(result.ordered_indexes, [1, 0])
        self.assertEqual(result.model, "bge-reranker")
        self.assertEqual(result.scores_by_index[1], 0.95)
        self.assertEqual(http_post.call_args.args[0], "http://rerank.example/v1/rerank")
        self.assertEqual(http_post.call_args.kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(http_post.call_args.kwargs["json"]["model"], "bge-reranker")
        self.assertEqual(http_post.call_args.kwargs["json"]["query"], "knowledge truth")
        self.assertNotIn("messages", http_post.call_args.kwargs["json"])

    def test_vector_adapter_raises_when_embedding_api_is_unavailable(self) -> None:
        adapter = VectorRetrievalAdapter(embedding_dimensions=3)

        with patch("swallow.knowledge_retrieval.retrieval_adapters.VectorRetrievalAdapter._connect") as connect_mock:
            with patch(
                "swallow.knowledge_retrieval.retrieval_adapters.build_api_embedding",
                side_effect=EmbeddingAPIUnavailable("embedding gateway unavailable"),
            ):
                with self.assertRaises(EmbeddingAPIUnavailable):
                    adapter.search(
                        [
                            RetrievalSearchDocument(
                                path="notes.md",
                                path_name="notes.md",
                                source_type="notes",
                                chunk_id="full-file",
                                title="Notes",
                                citation="notes.md#L1",
                                text="retrieval baseline",
                            )
                        ],
                        query_text="retrieval baseline",
                        query_plan=prepare_query_plan("retrieval baseline"),
                        limit=1,
                    )

        connect_mock.assert_not_called()

    def test_text_fallback_adapter_prefers_relevant_document(self) -> None:
        adapter = TextFallbackAdapter()
        query_plan = prepare_query_plan("reviewer consensus budget gate")
        documents = [
            RetrievalSearchDocument(
                path=".swl/tasks/demo/knowledge_objects.json",
                path_name="knowledge_objects.json",
                source_type=KNOWLEDGE_SOURCE_TYPE,
                chunk_id="knowledge-0001",
                title="Knowledge knowledge-0001",
                citation=".swl/tasks/demo/knowledge_objects.json#knowledge-0001",
                text="Reviewer consensus budget gate remains visible in the current task.",
            ),
            RetrievalSearchDocument(
                path=".swl/tasks/demo/knowledge_objects.json",
                path_name="knowledge_objects.json",
                source_type=KNOWLEDGE_SOURCE_TYPE,
                chunk_id="knowledge-0002",
                title="Knowledge knowledge-0002",
                citation=".swl/tasks/demo/knowledge_objects.json#knowledge-0002",
                text="Artifact timeline and route provenance only.",
            ),
        ]

        matches = adapter.search(documents, query_plan=query_plan, limit=2)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].document.chunk_id, "knowledge-0001")
        self.assertEqual(matches[0].adapter_name, "text_fallback")

    def test_vector_adapter_raises_when_sqlite_vec_is_missing(self) -> None:
        adapter = VectorRetrievalAdapter()

        with patch("swallow.knowledge_retrieval.retrieval_adapters.build_api_embedding", return_value=[0.1, 0.2, 0.3]):
            with patch("swallow.knowledge_retrieval.retrieval_adapters.importlib.import_module", side_effect=ImportError("sqlite_vec missing")):
                with self.assertRaises(VectorRetrievalUnavailable):
                    adapter.search(
                        [
                            RetrievalSearchDocument(
                                path="notes.md",
                                path_name="notes.md",
                                source_type="notes",
                                chunk_id="full-file",
                                title="Notes",
                                citation="notes.md#L1",
                                text="retrieval baseline",
                            )
                        ],
                        query_text="retrieval baseline",
                        query_plan=prepare_query_plan("retrieval baseline"),
                        limit=1,
                    )

    def test_retrieve_context_falls_back_to_text_search_when_sqlite_vec_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            save_knowledge_objects(
                tmp_path,
                "knowledge-task",
                [
                    {
                        "object_id": "knowledge-0001",
                        "text": "SQLite truth keeps reviewer consensus budget gating explicit.",
                        "stage": "verified",
                        "evidence_status": "artifact_backed",
                        "artifact_ref": ".swl/tasks/knowledge-task/artifacts/summary.md",
                        "retrieval_eligible": True,
                        "knowledge_reuse_scope": "retrieval_candidate",
                    }
                ],
            )
            (tmp_path / ".swl" / "tasks" / "knowledge-task" / "knowledge_objects.json").write_text(
                """[
  {
    "object_id": "knowledge-0001",
    "text": "stale file mirror should not win",
    "stage": "verified",
    "store_type": "evidence"
  }
]
""",
                encoding="utf-8",
            )

            retrieval_module._sqlite_vec_warning_emitted = False
            with self.assertLogs("swallow.knowledge_retrieval.retrieval", level="WARNING") as logs:
                with patch(
                    "swallow.knowledge_retrieval.retrieval.VectorRetrievalAdapter.search",
                    side_effect=VectorRetrievalUnavailable("sqlite_vec missing"),
                ):
                    items = retrieve_context(
                        tmp_path,
                        query="reviewer consensus budget gating",
                        source_types=[KNOWLEDGE_SOURCE_TYPE],
                        limit=4,
                    )

        self.assertEqual(len(items), 1)
        self.assertIn("[WARN] sqlite-vec unavailable, falling back to text search", logs.output[0])
        self.assertEqual(items[0].path, ".swl/tasks/knowledge-task/knowledge_objects.json")
        self.assertIn("SQLite truth keeps reviewer consensus budget gating explicit.", items[0].preview)
        self.assertEqual(items[0].metadata["knowledge_retrieval_mode"], "text_fallback")
        self.assertEqual(items[0].metadata["knowledge_retrieval_adapter"], "text_fallback")

    def test_retrieve_context_falls_back_to_text_search_when_embedding_api_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            save_knowledge_objects(
                tmp_path,
                "knowledge-task",
                [
                    {
                        "object_id": "knowledge-0001",
                        "text": "Embedding fallback should keep verified knowledge retrieval available.",
                        "stage": "verified",
                        "evidence_status": "artifact_backed",
                        "artifact_ref": ".swl/tasks/knowledge-task/artifacts/summary.md",
                        "retrieval_eligible": True,
                        "knowledge_reuse_scope": "retrieval_candidate",
                    }
                ],
            )

            retrieval_module._embedding_api_warning_emitted = False
            with self.assertLogs("swallow.knowledge_retrieval.retrieval", level="WARNING") as logs:
                with patch(
                    "swallow.knowledge_retrieval.retrieval.VectorRetrievalAdapter.search",
                    side_effect=EmbeddingAPIUnavailable("SWL_API_KEY is not configured."),
                ):
                    items = retrieve_context(
                        tmp_path,
                        query="embedding fallback verified knowledge",
                        source_types=[KNOWLEDGE_SOURCE_TYPE],
                        limit=4,
                    )

        self.assertEqual(len(items), 1)
        self.assertIn("[WARN] embedding API unavailable, falling back to text search", logs.output[0])
        self.assertEqual(items[0].path, ".swl/tasks/knowledge-task/knowledge_objects.json")
        self.assertEqual(items[0].metadata["knowledge_retrieval_mode"], "text_fallback")
        self.assertEqual(items[0].metadata["knowledge_retrieval_adapter"], "text_fallback")

    def test_retrieve_context_uses_vector_adapter_results_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            save_knowledge_objects(
                tmp_path,
                "knowledge-task",
                [
                    {
                        "object_id": "knowledge-0001",
                        "text": "Vector retrieval should surface this verified knowledge first.",
                        "stage": "verified",
                        "evidence_status": "artifact_backed",
                        "artifact_ref": ".swl/tasks/knowledge-task/artifacts/summary.md",
                        "retrieval_eligible": True,
                        "knowledge_reuse_scope": "retrieval_candidate",
                    }
                ],
            )

            def _mock_vector_search(documents, *, query_text, query_plan, limit):
                self.assertEqual(query_text, "vector retrieval verified knowledge")
                self.assertEqual(query_plan["token_count"], 4)
                self.assertEqual(limit, 4)
                self.assertEqual(len(documents), 1)
                return [
                    RetrievalSearchMatch(
                        document=documents[0],
                        score=19,
                        score_breakdown={"vector_bonus": 4, "content_hits": 3},
                        matched_terms=["knowledge", "retrieval", "vector"],
                        adapter_name="sqlite_vec",
                    )
                ]

            with patch("swallow.knowledge_retrieval.retrieval.VectorRetrievalAdapter.search", side_effect=_mock_vector_search):
                items = retrieve_context(
                    tmp_path,
                    query="vector retrieval verified knowledge",
                    source_types=[KNOWLEDGE_SOURCE_TYPE],
                    limit=4,
                )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].metadata["knowledge_retrieval_mode"], "vector")
        self.assertEqual(items[0].metadata["knowledge_retrieval_adapter"], "sqlite_vec")
        self.assertEqual(items[0].chunk_id, "knowledge-0001")

    def test_retrieve_context_can_disable_rerank_via_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            save_knowledge_objects(
                tmp_path,
                "knowledge-task",
                [
                    {
                        "object_id": "knowledge-0001",
                        "text": "Vector retrieval should surface this verified knowledge first.",
                        "stage": "verified",
                        "evidence_status": "artifact_backed",
                        "artifact_ref": ".swl/tasks/knowledge-task/artifacts/summary.md",
                        "retrieval_eligible": True,
                        "knowledge_reuse_scope": "retrieval_candidate",
                    }
                ],
            )

            def _mock_vector_search(documents, *, query_text, query_plan, limit):
                return [
                    RetrievalSearchMatch(
                        document=documents[0],
                        score=19,
                        score_breakdown={"vector_bonus": 4, "content_hits": 3},
                        matched_terms=["knowledge", "retrieval", "vector"],
                        adapter_name="sqlite_vec",
                    )
                ]

            with patch.dict("os.environ", {"SWL_RETRIEVAL_RERANK_ENABLED": "false"}, clear=False):
                with patch("swallow.knowledge_retrieval.retrieval.VectorRetrievalAdapter.search", side_effect=_mock_vector_search):
                    with patch("swallow.knowledge_retrieval.retrieval.DedicatedRerankAdapter.rerank") as rerank_mock:
                        items = retrieve_context(
                            tmp_path,
                            query="vector retrieval verified knowledge",
                            source_types=[KNOWLEDGE_SOURCE_TYPE],
                            limit=4,
                        )

        rerank_mock.assert_not_called()
        self.assertEqual(items[0].chunk_id, "knowledge-0001")

    def test_retrieve_context_relation_expansion_includes_linked_objects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            save_knowledge_objects(
                tmp_path,
                "task-a",
                [
                    {
                        "object_id": "knowledge-a",
                        "text": "Seed knowledge about retrieval graph expansion.",
                        "stage": "verified",
                        "evidence_status": "artifact_backed",
                        "artifact_ref": ".swl/tasks/task-a/artifacts/summary.md",
                        "retrieval_eligible": True,
                        "knowledge_reuse_scope": "retrieval_candidate",
                    }
                ],
            )
            save_knowledge_objects(
                tmp_path,
                "task-b",
                [
                    {
                        "object_id": "knowledge-b",
                        "text": "Linked knowledge should appear through relation expansion.",
                        "stage": "verified",
                        "evidence_status": "artifact_backed",
                        "artifact_ref": ".swl/tasks/task-b/artifacts/summary.md",
                        "retrieval_eligible": True,
                        "knowledge_reuse_scope": "retrieval_candidate",
                    }
                ],
            )
            create_knowledge_relation(
                tmp_path,
                source_object_id="knowledge-a",
                target_object_id="knowledge-b",
                relation_type="cites",
                confidence=1.0,
            )

            def _mock_vector_search(documents, *, query_text, query_plan, limit):
                seed = next(document for document in documents if document.chunk_id == "knowledge-a")
                return [
                    RetrievalSearchMatch(
                        document=seed,
                        score=20,
                        score_breakdown={"vector_bonus": 4},
                        matched_terms=["retrieval", "graph"],
                        adapter_name="sqlite_vec",
                    )
                ]

            with patch("swallow.knowledge_retrieval.retrieval.VectorRetrievalAdapter.search", side_effect=_mock_vector_search):
                items = retrieve_context(
                    tmp_path,
                    query="retrieval graph expansion",
                    source_types=[KNOWLEDGE_SOURCE_TYPE],
                    limit=8,
                )

        self.assertEqual(items[0].chunk_id, "knowledge-a")
        expanded = next(item for item in items if item.chunk_id == "knowledge-b")
        self.assertEqual(expanded.metadata["expansion_source"], "relation")
        self.assertEqual(expanded.metadata["expansion_depth"], 1)
        self.assertEqual(expanded.metadata["expansion_relation_type"], "cites")

    def test_retrieve_context_relation_expansion_respects_depth_limit_and_decay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            for task_id, object_id, text in [
                ("task-a", "knowledge-a", "Seed retrieval knowledge."),
                ("task-b", "knowledge-b", "First hop linked knowledge."),
                ("task-c", "knowledge-c", "Second hop linked knowledge."),
                ("task-d", "knowledge-d", "Third hop linked knowledge."),
            ]:
                save_knowledge_objects(
                    tmp_path,
                    task_id,
                    [
                        {
                            "object_id": object_id,
                            "text": text,
                            "stage": "verified",
                            "evidence_status": "artifact_backed",
                            "artifact_ref": f".swl/tasks/{task_id}/artifacts/summary.md",
                            "retrieval_eligible": True,
                            "knowledge_reuse_scope": "retrieval_candidate",
                        }
                    ],
                )
            create_knowledge_relation(tmp_path, source_object_id="knowledge-a", target_object_id="knowledge-b", relation_type="related_to")
            create_knowledge_relation(tmp_path, source_object_id="knowledge-b", target_object_id="knowledge-c", relation_type="extends")
            create_knowledge_relation(tmp_path, source_object_id="knowledge-c", target_object_id="knowledge-d", relation_type="refines")

            def _mock_vector_search(documents, *, query_text, query_plan, limit):
                seed = next(document for document in documents if document.chunk_id == "knowledge-a")
                return [
                    RetrievalSearchMatch(
                        document=seed,
                        score=20,
                        score_breakdown={"vector_bonus": 4},
                        matched_terms=["retrieval"],
                        adapter_name="sqlite_vec",
                    )
                ]

            with patch("swallow.knowledge_retrieval.retrieval.VectorRetrievalAdapter.search", side_effect=_mock_vector_search):
                items = retrieve_context(
                    tmp_path,
                    request=RetrievalRequest(
                        query="seed retrieval knowledge",
                        source_types=[KNOWLEDGE_SOURCE_TYPE],
                        context_layers=["task", "history"],
                        current_task_id="task-a",
                        limit=8,
                        strategy="system_baseline",
                    ),
                )

        item_ids = [item.chunk_id for item in items]
        self.assertIn("knowledge-b", item_ids)
        self.assertIn("knowledge-c", item_ids)
        self.assertNotIn("knowledge-d", item_ids)
        hop_one = next(item for item in items if item.chunk_id == "knowledge-b")
        hop_two = next(item for item in items if item.chunk_id == "knowledge-c")
        self.assertGreater(hop_one.score, hop_two.score)
        self.assertEqual(hop_two.metadata["expansion_depth"], DEFAULT_RELATION_EXPANSION_CONFIG.depth_limit)

    def test_retrieve_context_prioritizes_canonical_reuse_and_expands_relations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            canonical_records = [
                {
                    "canonical_id": "canonical-a",
                    "canonical_key": "task-object:task-a:knowledge-a",
                    "source_task_id": "task-a",
                    "source_object_id": "knowledge-a",
                    "promoted_at": "2026-04-25T00:00:00+00:00",
                    "promoted_by": "test",
                    "decision_note": "",
                    "decision_ref": ".swl/tasks/task-a/knowledge_decisions.jsonl#knowledge-a",
                    "artifact_ref": "",
                    "source_ref": "file://task-a",
                    "text": "Knowledge Truth Layer and retrieval architecture stay connected.",
                    "evidence_status": "source_only",
                    "canonical_stage": "canonical",
                    "canonical_status": "active",
                    "superseded_by": "",
                    "superseded_at": "",
                },
                {
                    "canonical_id": "canonical-b",
                    "canonical_key": "task-object:task-b:knowledge-b",
                    "source_task_id": "task-b",
                    "source_object_id": "knowledge-b",
                    "promoted_at": "2026-04-25T00:00:00+00:00",
                    "promoted_by": "test",
                    "decision_note": "",
                    "decision_ref": ".swl/tasks/task-b/knowledge_decisions.jsonl#knowledge-b",
                    "artifact_ref": "",
                    "source_ref": "file://task-b",
                    "text": "Memory Authority constrains the surrounding system role decisions.",
                    "evidence_status": "source_only",
                    "canonical_stage": "canonical",
                    "canonical_status": "active",
                    "superseded_by": "",
                    "superseded_at": "",
                },
            ]
            for record in canonical_records:
                append_canonical_record(tmp_path, record)
                persist_wiki_entry_from_record(
                    tmp_path,
                    record,
                    write_authority=TEST_FIXTURE_CANONICAL_WRITE_AUTHORITY,
                )
            save_canonical_reuse_policy(tmp_path, build_canonical_reuse_summary(canonical_records))
            (tmp_path / "notes.md").write_text(
                "# Notes\n\nGeneric notes mention knowledge and retrieval but are not authoritative.\n",
                encoding="utf-8",
            )
            create_knowledge_relation(
                tmp_path,
                source_object_id="canonical-a",
                target_object_id="canonical-b",
                relation_type="related_to",
            )

            def _mock_vector_search(documents, *, query_text, query_plan, limit):
                seed = next(document for document in documents if document.chunk_id == "canonical-a")
                return [
                    RetrievalSearchMatch(
                        document=seed,
                        score=20,
                        score_breakdown={"vector_bonus": 4},
                        matched_terms=["retrieval", "truth"],
                        adapter_name="sqlite_vec",
                    )
                ]

            with patch("swallow.knowledge_retrieval.retrieval.VectorRetrievalAdapter.search", side_effect=_mock_vector_search):
                items = retrieve_context(
                    tmp_path,
                    query="truth layer retrieval architecture",
                    source_types=[KNOWLEDGE_SOURCE_TYPE, "notes"],
                    limit=8,
                )

        self.assertEqual(items[0].source_type, KNOWLEDGE_SOURCE_TYPE)
        self.assertEqual(items[0].metadata["storage_scope"], "canonical_registry")
        expanded = next(item for item in items if item.metadata.get("expansion_source") == "relation")
        self.assertEqual(expanded.metadata["storage_scope"], "canonical_registry")
        self.assertEqual(expanded.metadata["knowledge_object_id"], "knowledge-b")

    def test_retrieve_context_uses_vector_adapter_for_canonical_reuse_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            canonical_record = {
                "canonical_id": "canonical-a",
                "canonical_key": "task-object:task-a:knowledge-a",
                "source_task_id": "task-a",
                "source_object_id": "knowledge-a",
                "promoted_at": "2026-04-25T00:00:00+00:00",
                "promoted_by": "test",
                "decision_note": "",
                "decision_ref": ".swl/tasks/task-a/knowledge_decisions.jsonl#knowledge-a",
                "artifact_ref": "",
                "source_ref": "file://task-a",
                "text": "Knowledge Truth Layer and retrieval architecture stay connected.",
                "evidence_status": "source_only",
                "canonical_stage": "canonical",
                "canonical_status": "active",
                "superseded_by": "",
                "superseded_at": "",
            }
            append_canonical_record(tmp_path, canonical_record)
            save_canonical_reuse_policy(tmp_path, build_canonical_reuse_summary([canonical_record]))

            def _mock_vector_search(documents, *, query_text, query_plan, limit):
                self.assertEqual(len(documents), 1)
                self.assertEqual(documents[0].chunk_id, "canonical-a")
                return [
                    RetrievalSearchMatch(
                        document=documents[0],
                        score=18,
                        score_breakdown={"vector_bonus": 5},
                        matched_terms=["architecture", "retrieval"],
                        adapter_name="sqlite_vec",
                    )
                ]

            with patch("swallow.knowledge_retrieval.retrieval.VectorRetrievalAdapter.search", side_effect=_mock_vector_search):
                items = retrieve_context(
                    tmp_path,
                    query="truth layer retrieval architecture",
                    source_types=[KNOWLEDGE_SOURCE_TYPE],
                    limit=4,
                )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].metadata["storage_scope"], "canonical_registry")
        self.assertEqual(items[0].metadata["knowledge_retrieval_mode"], "vector")
        self.assertEqual(items[0].metadata["knowledge_retrieval_adapter"], "sqlite_vec")

    def test_retrieve_context_falls_back_to_text_search_for_canonical_reuse_when_embedding_api_is_unavailable(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            canonical_record = {
                "canonical_id": "canonical-a",
                "canonical_key": "task-object:task-a:knowledge-a",
                "source_task_id": "task-a",
                "source_object_id": "knowledge-a",
                "promoted_at": "2026-04-25T00:00:00+00:00",
                "promoted_by": "test",
                "decision_note": "",
                "decision_ref": ".swl/tasks/task-a/knowledge_decisions.jsonl#knowledge-a",
                "artifact_ref": "",
                "source_ref": "file://task-a",
                "text": "Canonical reuse should stay searchable when embedding is unavailable.",
                "evidence_status": "source_only",
                "canonical_stage": "canonical",
                "canonical_status": "active",
                "superseded_by": "",
                "superseded_at": "",
            }
            append_canonical_record(tmp_path, canonical_record)
            save_canonical_reuse_policy(tmp_path, build_canonical_reuse_summary([canonical_record]))

            retrieval_module._embedding_api_warning_emitted = False
            with self.assertLogs("swallow.knowledge_retrieval.retrieval", level="WARNING") as logs:
                with patch(
                    "swallow.knowledge_retrieval.retrieval.VectorRetrievalAdapter.search",
                    side_effect=EmbeddingAPIUnavailable("SWL_API_KEY is not configured."),
                ):
                    items = retrieve_context(
                        tmp_path,
                        query="canonical reuse embedding fallback",
                        source_types=[KNOWLEDGE_SOURCE_TYPE],
                        limit=4,
                    )

        self.assertEqual(len(items), 1)
        self.assertIn("[WARN] embedding API unavailable, falling back to text search", logs.output[0])
        self.assertEqual(items[0].metadata["storage_scope"], "canonical_registry")
        self.assertEqual(items[0].metadata["knowledge_retrieval_mode"], "text_fallback")
        self.assertEqual(items[0].metadata["knowledge_retrieval_adapter"], "text_fallback")

    def test_retrieve_context_relation_expansion_does_not_duplicate_seed_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            for task_id, object_id, text in [
                ("task-a", "knowledge-a", "Seed retrieval knowledge."),
                ("task-b", "knowledge-b", "Linked retrieval knowledge also directly matches."),
            ]:
                save_knowledge_objects(
                    tmp_path,
                    task_id,
                    [
                        {
                            "object_id": object_id,
                            "text": text,
                            "stage": "verified",
                            "evidence_status": "artifact_backed",
                            "artifact_ref": f".swl/tasks/{task_id}/artifacts/summary.md",
                            "retrieval_eligible": True,
                            "knowledge_reuse_scope": "retrieval_candidate",
                        }
                    ],
                )
            create_knowledge_relation(tmp_path, source_object_id="knowledge-a", target_object_id="knowledge-b", relation_type="cites")

            def _mock_vector_search(documents, *, query_text, query_plan, limit):
                seed_a = next(document for document in documents if document.chunk_id == "knowledge-a")
                seed_b = next(document for document in documents if document.chunk_id == "knowledge-b")
                return [
                    RetrievalSearchMatch(
                        document=seed_a,
                        score=20,
                        score_breakdown={"vector_bonus": 4},
                        matched_terms=["seed"],
                        adapter_name="sqlite_vec",
                    ),
                    RetrievalSearchMatch(
                        document=seed_b,
                        score=18,
                        score_breakdown={"vector_bonus": 3},
                        matched_terms=["linked"],
                        adapter_name="sqlite_vec",
                    ),
                ]

            with patch("swallow.knowledge_retrieval.retrieval.VectorRetrievalAdapter.search", side_effect=_mock_vector_search):
                items = retrieve_context(
                    tmp_path,
                    query="seed linked retrieval knowledge",
                    source_types=[KNOWLEDGE_SOURCE_TYPE],
                    limit=8,
                )

        self.assertEqual([item.chunk_id for item in items].count("knowledge-b"), 1)


if __name__ == "__main__":
    unittest.main()
