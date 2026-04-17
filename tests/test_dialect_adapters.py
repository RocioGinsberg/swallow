from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.executor import build_formatted_executor_prompt, resolve_dialect_name
from swallow.models import RetrievalItem, TaskState


class DialectAdaptersTest(unittest.TestCase):
    def test_resolve_dialect_name_matches_claude_and_codex_model_hints(self) -> None:
        self.assertEqual(resolve_dialect_name("", "claude-3-7-sonnet"), "claude_xml")
        self.assertEqual(resolve_dialect_name("", "codex"), "codex_fim")
        self.assertEqual(resolve_dialect_name("", "deepseek-coder-v2"), "codex_fim")

    def test_build_formatted_executor_prompt_wraps_claude_xml_prompt(self) -> None:
        state = TaskState(
            task_id="claude-xml-001",
            title="Claude XML formatting",
            goal="Render a Claude-native prompt shape",
            workspace_root="/tmp",
            route_name="claude-local",
            route_backend="api_stub",
            route_model_hint="claude-3-5-sonnet",
            route_dialect="claude_xml",
            task_semantics={
                "constraints": ["Preserve <xml> safety"],
                "acceptance_criteria": ["Explain the next action"],
            },
        )
        retrieval_items = [
            RetrievalItem(
                path="docs/plan.md",
                source_type="notes",
                score=3,
                preview="Use the approved implementation plan.",
                citation="docs/plan.md#L1-L3",
                title="Plan",
            )
        ]

        prompt = build_formatted_executor_prompt(state, retrieval_items)

        self.assertIn("<swallow_task>", prompt)
        self.assertIn("<task>", prompt)
        self.assertIn("<constraints>", prompt)
        self.assertIn("<retrieval>", prompt)
        self.assertIn("&lt;xml&gt;", prompt)
        self.assertIn("docs/plan.md#L1-L3", prompt)

    def test_codex_fim_falls_back_to_raw_prompt_for_non_code_routes(self) -> None:
        state = TaskState(
            task_id="codex-fim-plain-001",
            title="Codex FIM fallback",
            goal="Keep non-code routes in raw form",
            workspace_root="/tmp",
            route_model_hint="codex",
            route_dialect="codex_fim",
            route_capabilities={"execution_kind": "artifact_generation"},
        )

        prompt = build_formatted_executor_prompt(state, [])

        self.assertNotIn("<fim_prefix>", prompt)
        self.assertIn("You are the executor for a swallow workflow task.", prompt)


if __name__ == "__main__":
    unittest.main()
