from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.ingestion.parsers import (
    IngestionParseError,
    detect_ingestion_format,
    parse_chatgpt_export,
    parse_claude_export,
    parse_generic_chat_export,
    parse_ingestion_bytes,
    parse_markdown_text,
    parse_open_webui_export,
)


class IngestionParsersTest(unittest.TestCase):
    def test_parse_chatgpt_export_extracts_sorted_turns(self) -> None:
        payload = [
            {
                "title": "Routing discussion",
                "mapping": {
                    "node-2": {
                        "message": {
                            "author": {"role": "assistant"},
                            "content": {"content_type": "text", "parts": ["Prefer explicit route guards."]},
                            "create_time": 20,
                        }
                    },
                    "node-1": {
                        "message": {
                            "author": {"role": "user"},
                            "content": {"content_type": "text", "parts": ["How should routing fallback behave?"]},
                            "create_time": 10,
                        }
                    },
                },
            }
        ]

        turns = parse_chatgpt_export(payload)

        self.assertEqual([turn.role for turn in turns], ["user", "assistant"])
        self.assertEqual(turns[0].timestamp, "10")
        self.assertEqual(turns[1].metadata["conversation_title"], "Routing discussion")

    def test_parse_chatgpt_export_marks_non_primary_branch_as_abandoned(self) -> None:
        payload = {
            "title": "Branching discussion",
            "mapping": {
                "root": {"id": "root", "message": None},
                "u1": {
                    "id": "u1",
                    "parent": "root",
                    "message": {
                        "author": {"role": "user"},
                        "content": {"content_type": "text", "parts": ["Need a routing plan."]},
                        "create_time": 1,
                    },
                },
                "a1": {
                    "id": "a1",
                    "parent": "u1",
                    "message": {
                        "author": {"role": "assistant"},
                        "content": {"content_type": "text", "parts": ["Plan A keeps broad fallback behavior."]},
                        "create_time": 2,
                    },
                },
                "a2": {
                    "id": "a2",
                    "parent": "u1",
                    "message": {
                        "author": {"role": "assistant"},
                        "content": {"content_type": "text", "parts": ["Plan B keeps explicit route guards."]},
                        "create_time": 4,
                    },
                },
                "u2": {
                    "id": "u2",
                    "parent": "a2",
                    "message": {
                        "author": {"role": "user"},
                        "content": {"content_type": "text", "parts": ["Continue with plan B."]},
                        "create_time": 5,
                    },
                },
            },
        }

        turns = parse_chatgpt_export(payload)

        abandoned = next(turn for turn in turns if turn.turn_id == "a1")
        primary = next(turn for turn in turns if turn.turn_id == "a2")
        self.assertEqual(abandoned.metadata["branch"], "abandoned")
        self.assertNotIn("branch", primary.metadata)
        self.assertEqual(primary.metadata["parent_turn_id"], "u1")

    def test_parse_claude_export_extracts_text_blocks(self) -> None:
        payload = {
            "name": "Taxonomy sync",
            "chat_messages": [
                {
                    "uuid": "m-1",
                    "sender": "human",
                    "content": [{"type": "text", "text": "Summarize the design constraints."}],
                    "created_at": "2026-04-18T10:00:00Z",
                },
                {
                    "uuid": "m-2",
                    "sender": "assistant",
                    "content": [
                        {"type": "text", "text": "Do not expand the workbench scope."},
                        {"type": "text", "text": "Keep the CLI surface narrow."},
                    ],
                    "created_at": "2026-04-18T10:01:00Z",
                },
            ],
        }

        turns = parse_claude_export(payload)

        self.assertEqual(turns[0].role, "human")
        self.assertIn("Keep the CLI surface narrow.", turns[1].content)
        self.assertEqual(turns[1].metadata["conversation_name"], "Taxonomy sync")

    def test_parse_open_webui_export_supports_openai_compatible_messages(self) -> None:
        payload = {
            "messages": [
                {"id": "1", "role": "system", "content": "You are a routing specialist."},
                {"id": "2", "role": "user", "content": "List the non-goals."},
                {"id": "3", "role": "assistant", "content": ["No realtime sync.", "No auto promotion."]},
            ]
        }

        turns = parse_open_webui_export(payload)

        self.assertEqual([turn.role for turn in turns], ["system", "user", "assistant"])
        self.assertEqual(turns[2].content, "No realtime sync.\nNo auto promotion.")

    def test_parse_markdown_text_splits_by_heading(self) -> None:
        turns = parse_markdown_text(
            "# Decisions\nKeep staged promotion manual.\n\n## Non-goals\nNo realtime API sync.",
            source_name="notes.md",
        )

        self.assertEqual(len(turns), 2)
        self.assertEqual(turns[0].role, "document")
        self.assertEqual(turns[0].metadata["heading"], "Decisions")
        self.assertIn("No realtime API sync.", turns[1].content)

    def test_parse_generic_chat_export_supports_flat_message_array(self) -> None:
        payload = [
            {"role": "user", "content": "Capture the main decision."},
            {"role": "assistant", "content": ["Decision: keep staged promotion manual.", "Constraint: stay local-first."]},
        ]

        turns = parse_generic_chat_export(payload)

        self.assertEqual([turn.role for turn in turns], ["user", "assistant"])
        self.assertIn("Constraint: stay local-first.", turns[1].content)

    def test_parse_generic_chat_export_supports_messages_wrapper_and_aliases(self) -> None:
        payload = {
            "messages": [
                {"sender": "human", "text": "Summarize the outcome."},
                {"from": "assistant", "message": "Decision: support generic chat JSON."},
            ]
        }

        turns = parse_generic_chat_export(payload)

        self.assertEqual([turn.role for turn in turns], ["human", "assistant"])
        self.assertEqual(turns[1].content, "Decision: support generic chat JSON.")

    def test_parse_generic_chat_export_supports_openai_style_text_parts(self) -> None:
        payload = [
            {
                "author": {"role": "assistant"},
                "content": [
                    {"type": "text", "text": "Decision: add clipboard transport."},
                    {"type": "text", "text": "Constraint: do not add URL ingestion."},
                ],
            }
        ]

        turns = parse_generic_chat_export(payload)

        self.assertEqual(turns[0].role, "assistant")
        self.assertIn("Constraint: do not add URL ingestion.", turns[0].content)

    def test_detect_ingestion_format_distinguishes_supported_payloads(self) -> None:
        self.assertEqual(detect_ingestion_format({"chat_messages": []}), "claude_json")
        self.assertEqual(detect_ingestion_format({"messages": []}), "open_webui_json")
        self.assertEqual(detect_ingestion_format([{"mapping": {}}]), "chatgpt_json")
        self.assertEqual(detect_ingestion_format([{"role": "user", "content": "hello"}]), "generic_chat_json")

    def test_detect_ingestion_format_rejects_empty_json_array(self) -> None:
        with self.assertRaisesRegex(IngestionParseError, "Unsupported ingestion payload"):
            detect_ingestion_format([])

    def test_parse_ingestion_bytes_auto_detects_json_and_markdown(self) -> None:
        markdown_turns = parse_ingestion_bytes(b"# Summary\nUse staged review.", source_name="handoff.md")
        json_turns = parse_ingestion_bytes(
            json.dumps({"messages": [{"role": "user", "content": "hello"}]}).encode("utf-8"),
            source_name="open-webui.json",
        )

        self.assertEqual(markdown_turns[0].metadata["source_name"], "handoff.md")
        self.assertEqual(json_turns[0].role, "user")

    def test_parse_ingestion_bytes_honors_format_hint(self) -> None:
        turns = parse_ingestion_bytes(
            json.dumps({"chat_messages": [{"sender": "assistant", "content": [{"type": "text", "text": "ok"}]}]}).encode(
                "utf-8"
            ),
            format_hint="claude_json",
        )

        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0].role, "assistant")

    def test_parse_ingestion_bytes_supports_generic_chat_json_format_hint(self) -> None:
        turns = parse_ingestion_bytes(
            json.dumps({"messages": [{"sender": "user", "text": "hello"}]}).encode("utf-8"),
            format_hint="generic_chat_json",
            source_name="clipboard.json",
        )

        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0].role, "user")

    def test_parse_ingestion_bytes_reports_meaningful_errors(self) -> None:
        with self.assertRaisesRegex(IngestionParseError, "valid JSON or Markdown"):
            parse_ingestion_bytes(b"{not-json", source_name="broken.json")

    def test_parsers_reject_unparseable_exports(self) -> None:
        with self.assertRaisesRegex(IngestionParseError, "ChatGPT export did not contain any parseable messages"):
            parse_chatgpt_export({"mapping": {}})
        with self.assertRaisesRegex(IngestionParseError, "Claude export is missing 'chat_messages'"):
            parse_claude_export({})
        with self.assertRaisesRegex(IngestionParseError, "Open WebUI export must contain a top-level 'messages' array"):
            parse_open_webui_export({})

    def test_parse_markdown_path_uses_file_extension_for_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "handoff.md"
            note.write_text("# Constraints\nStay local-first.", encoding="utf-8")

            turns = parse_ingestion_bytes(note.read_bytes(), source_name=note.name)

        self.assertEqual(turns[0].metadata["heading"], "Constraints")


if __name__ == "__main__":
    unittest.main()
