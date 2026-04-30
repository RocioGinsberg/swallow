from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.knowledge_retrieval.ingestion.filters import filter_conversation_turns, merge_conversation_turns
from swallow.knowledge_retrieval.ingestion.parsers import ConversationTurn


class IngestionFiltersTest(unittest.TestCase):
    def test_merge_conversation_turns_combines_adjacent_same_role_messages(self) -> None:
        merged = merge_conversation_turns(
            [
                ConversationTurn(role="user", content="First constraint.", turn_id="u1", timestamp="1"),
                ConversationTurn(role="user", content="Second constraint.", turn_id="u2", timestamp="2"),
                ConversationTurn(role="assistant", content="Acknowledged.", turn_id="a1", timestamp="3"),
            ]
        )

        self.assertEqual(len(merged), 2)
        self.assertIn("Second constraint.", merged[0].content)
        self.assertEqual(merged[0].metadata["merged_turn_ids"], "u1,u2")
        self.assertEqual(merged[0].metadata["merged_timestamps"], "1,2")

    def test_filter_conversation_turns_drops_short_chatter(self) -> None:
        fragments = filter_conversation_turns(
            [
                ConversationTurn(role="assistant", content="好的", turn_id="a1"),
                ConversationTurn(role="assistant", content="谢谢", turn_id="a2"),
            ]
        )

        self.assertEqual(fragments, [])

    def test_filter_conversation_turns_keeps_keyword_and_code_signals(self) -> None:
        fragments = filter_conversation_turns(
            [
                ConversationTurn(role="assistant", content="决定：保持 staged review 手动执行。", turn_id="a1"),
                ConversationTurn(role="assistant", content="```python\nprint('keep')\n```", turn_id="a2"),
            ]
        )

        self.assertEqual(len(fragments), 1)
        self.assertIn("keyword", fragments[0].signals)
        self.assertIn("code_block", fragments[0].signals)

    def test_filter_conversation_turns_keeps_lists(self) -> None:
        fragments = filter_conversation_turns(
            [
                ConversationTurn(
                    role="assistant",
                    content="- Non-goal: no realtime sync\n- Constraint: keep CLI-only",
                    turn_id="a1",
                )
            ]
        )

        self.assertEqual(len(fragments), 1)
        self.assertIn("list", fragments[0].signals)

    def test_filter_conversation_turns_dedupes_normalized_duplicates(self) -> None:
        fragments = filter_conversation_turns(
            [
                ConversationTurn(role="assistant", content="Decision: keep staged review manual.", turn_id="a1"),
                ConversationTurn(role="assistant", content="Decision:   keep staged review manual.", turn_id="a2"),
            ]
        )

        self.assertEqual(len(fragments), 1)

    def test_filter_conversation_turns_carries_merged_ids_into_fragment(self) -> None:
        fragments = filter_conversation_turns(
            [
                ConversationTurn(role="user", content="Constraint one", turn_id="u1", timestamp="1"),
                ConversationTurn(role="user", content="Constraint two", turn_id="u2", timestamp="2"),
            ]
        )

        self.assertEqual(len(fragments), 1)
        self.assertEqual(fragments[0].source_turn_ids, ["u1", "u2"])
        self.assertEqual(fragments[0].source_timestamps, ["1", "2"])

    def test_filter_conversation_turns_returns_empty_on_empty_input(self) -> None:
        self.assertEqual(filter_conversation_turns([]), [])

    def test_filter_conversation_turns_marks_document_sections(self) -> None:
        fragments = filter_conversation_turns(
            [
                ConversationTurn(
                    role="document",
                    content="Architecture Constraints\n\nDo not expand the web surface.",
                    turn_id="d1",
                    metadata={"heading": "Architecture Constraints"},
                )
            ]
        )

        self.assertEqual(len(fragments), 1)
        self.assertIn("document", fragments[0].signals)

    def test_merge_conversation_turns_does_not_cross_branch_boundaries(self) -> None:
        merged = merge_conversation_turns(
            [
                ConversationTurn(role="assistant", content="Primary path turn.", turn_id="a1"),
                ConversationTurn(
                    role="assistant",
                    content="Abandoned branch turn.",
                    turn_id="a2",
                    metadata={"branch": "abandoned"},
                ),
            ]
        )

        self.assertEqual(len(merged), 2)

    def test_filter_conversation_turns_drops_abandoned_branch_without_rejection_signal(self) -> None:
        fragments = filter_conversation_turns(
            [
                ConversationTurn(
                    role="assistant",
                    content="Alternative draft with extra implementation detail only.",
                    turn_id="a1",
                    metadata={"branch": "abandoned"},
                )
            ]
        )

        self.assertEqual(fragments, [])

    def test_filter_conversation_turns_keeps_abandoned_branch_when_it_records_rejection(self) -> None:
        fragments = filter_conversation_turns(
            [
                ConversationTurn(
                    role="assistant",
                    content="Reject plan A and switch to plan B.",
                    turn_id="a1",
                    metadata={"branch": "abandoned"},
                )
            ]
        )

        self.assertEqual(len(fragments), 1)
        self.assertIn("abandoned_branch", fragments[0].signals)
        self.assertIn("rejected_alternative", fragments[0].signals)


if __name__ == "__main__":
    unittest.main()
