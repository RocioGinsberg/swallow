from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import swallow.retrieval as retrieval_module
from swallow.retrieval import KNOWLEDGE_SOURCE_TYPE, prepare_query_plan, retrieve_context
from swallow.retrieval_adapters import (
    RetrievalSearchDocument,
    RetrievalSearchMatch,
    TextFallbackAdapter,
    VectorRetrievalAdapter,
    VectorRetrievalUnavailable,
)
from swallow.store import save_knowledge_objects


class RetrievalAdaptersTest(unittest.TestCase):
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

        with patch("swallow.retrieval_adapters.importlib.import_module", side_effect=ImportError("sqlite_vec missing")):
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
            with self.assertLogs("swallow.retrieval", level="WARNING") as logs:
                with patch(
                    "swallow.retrieval.VectorRetrievalAdapter.search",
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

            with patch("swallow.retrieval.VectorRetrievalAdapter.search", side_effect=_mock_vector_search):
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


if __name__ == "__main__":
    unittest.main()
