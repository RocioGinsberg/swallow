from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from swallow.retrieval import KNOWLEDGE_SOURCE_TYPE, prepare_query_plan
from swallow.retrieval_adapters import RetrievalSearchDocument, rank_documents_by_local_embedding


pytestmark = pytest.mark.eval


DOCUMENTS = [
    RetrievalSearchDocument(
        path=".swl/tasks/demo/knowledge_objects.json",
        path_name="knowledge_objects.json",
        source_type=KNOWLEDGE_SOURCE_TYPE,
        chunk_id="knowledge-budget",
        title="Knowledge knowledge-budget",
        citation=".swl/tasks/demo/knowledge_objects.json#knowledge-budget",
        text="Human gate budget exhaustion should pause reviewer consensus loops and move the task into waiting_human.",
    ),
    RetrievalSearchDocument(
        path=".swl/tasks/demo/knowledge_objects.json",
        path_name="knowledge_objects.json",
        source_type=KNOWLEDGE_SOURCE_TYPE,
        chunk_id="knowledge-route",
        title="Knowledge knowledge-route",
        citation=".swl/tasks/demo/knowledge_objects.json#knowledge-route",
        text="The route degradation matrix keeps fallback ordering explicit across http-claude, qwen, glm, local-cline, and local-summary.",
    ),
    RetrievalSearchDocument(
        path=".swl/tasks/demo/knowledge_objects.json",
        path_name="knowledge_objects.json",
        source_type=KNOWLEDGE_SOURCE_TYPE,
        chunk_id="knowledge-migration",
        title="Knowledge knowledge-migration",
        citation=".swl/tasks/demo/knowledge_objects.json#knowledge-migration",
        text="Knowledge migrate dry run and idempotent SQLite backfill keep file mirrors safe while promoting SQLite truth.",
    ),
    RetrievalSearchDocument(
        path=".swl/tasks/demo/knowledge_objects.json",
        path_name="knowledge_objects.json",
        source_type=KNOWLEDGE_SOURCE_TYPE,
        chunk_id="knowledge-grounding",
        title="Knowledge knowledge-grounding",
        citation=".swl/tasks/demo/knowledge_objects.json#knowledge-grounding",
        text="Grounding evidence artifacts lock canonical refs during reruns so retrieval remains resume-stable.",
    ),
]


def test_local_vector_ranking_meets_precision_and_recall_baseline() -> None:
    cases = [
        {
            "query": "consensus budget exhaustion human gate",
            "expected": {"knowledge-budget"},
        },
        {
            "query": "migration dry run sqlite truth backfill",
            "expected": {"knowledge-migration"},
        },
        {
            "query": "grounding canonical refs reruns",
            "expected": {"knowledge-grounding"},
        },
        {
            "query": "route degradation fallback ordering",
            "expected": {"knowledge-route"},
        },
    ]

    true_positive = 0
    false_positive = 0
    false_negative = 0

    for case in cases:
        matches = rank_documents_by_local_embedding(
            DOCUMENTS,
            query_text=case["query"],
            query_plan=prepare_query_plan(case["query"]),
            limit=1,
        )
        predicted = {match.document.chunk_id for match in matches}
        expected = case["expected"]
        true_positive += len(predicted & expected)
        false_positive += len(predicted - expected)
        false_negative += len(expected - predicted)

    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else 0.0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else 0.0

    assert precision >= 0.70, f"precision {precision:.2%} fell below 70%"
    assert recall >= 0.60, f"recall {recall:.2%} fell below 60%"
