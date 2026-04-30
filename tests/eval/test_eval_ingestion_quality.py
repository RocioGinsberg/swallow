from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from swallow.knowledge_retrieval.ingestion.filters import filter_conversation_turns
from swallow.knowledge_retrieval.ingestion.parsers import parse_ingestion_bytes


pytestmark = pytest.mark.eval


def _predicted_turn_ids(case: dict[str, object]) -> set[str]:
    payload = case["payload"]
    format_hint = str(case["format"])
    turns = parse_ingestion_bytes(
        json.dumps(payload).encode("utf-8"),
        format_hint=format_hint,
        source_name=f"{case['case_id']}.json",
    )
    fragments = filter_conversation_turns(turns)
    predicted: set[str] = set()
    for fragment in fragments:
        predicted.update(fragment.source_turn_ids)
    return predicted


def test_ingestion_eval_precision_and_recall_meet_baseline(ingestion_eval_cases: list[dict[str, object]]) -> None:
    true_positive = 0
    false_positive = 0
    false_negative = 0

    for case in ingestion_eval_cases:
        expected = set(str(item) for item in case["expected_keep_turn_ids"])
        predicted = _predicted_turn_ids(case)
        true_positive += len(predicted & expected)
        false_positive += len(predicted - expected)
        false_negative += len(expected - predicted)

    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else 0.0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else 0.0

    assert precision >= 0.80, f"precision {precision:.2%} fell below 80%"
    assert recall >= 0.70, f"recall {recall:.2%} fell below 70%"
