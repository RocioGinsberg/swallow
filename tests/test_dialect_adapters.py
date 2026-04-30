from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.knowledge_retrieval.dialect_data import collect_prompt_data
from swallow.orchestration.executor import build_formatted_executor_prompt, resolve_dialect_name
from swallow.knowledge_retrieval.knowledge_objects import build_knowledge_objects
from swallow.orchestration.models import RetrievalItem, TaskState


class DialectAdaptersTest(unittest.TestCase):
    def test_collect_prompt_data_aggregates_shared_prompt_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_memory = tmp_path / "task_memory.json"
            task_memory.write_text(
                json.dumps(
                    {
                        "retrieval": {
                            "count": 2,
                            "top_references": ["docs/plan.md#L1-L4"],
                            "reused_knowledge_count": 1,
                            "reused_knowledge_current_task_count": 1,
                            "reused_knowledge_cross_task_count": 0,
                            "reused_knowledge_references": [".swl/tasks/task-1/knowledge_objects.json#knowledge-0001"],
                            "grounding_artifact": ".swl/tasks/task-1/artifacts/source_grounding.md",
                            "retrieval_record_path": ".swl/tasks/task-1/retrieval.json",
                        }
                    }
                ),
                encoding="utf-8",
            )
            knowledge_objects = [
                item.to_dict()
                for item in build_knowledge_objects(
                    items=["Persist shared prompt facts"],
                    stage="verified",
                    source_ref="docs://phase35",
                    artifact_refs=["artifacts/knowledge.md"],
                    retrieval_eligible=True,
                    canonicalization_intent="review",
                )
            ]
            state = TaskState(
                task_id="structured-data-001",
                title="Prompt data aggregation",
                goal="Collect prompt sections once and reuse them across dialects",
                workspace_root=str(tmp_path),
                executor_name="local",
                route_name="local-summary",
                route_backend="local_cli",
                route_executor_family="cli",
                route_execution_site="local",
                route_model_hint="local",
                route_dialect="structured_markdown",
                route_capabilities={"execution_kind": "artifact_generation", "supports_tool_loop": False},
                task_semantics={
                    "source_kind": "external_planning_handoff",
                    "source_ref": "chat://phase35",
                    "constraints": ["Keep formatting stable"],
                    "acceptance_criteria": ["Expose one shared prompt data layer"],
                    "priority_hints": ["Prefer extraction over new abstractions"],
                    "next_action_proposals": ["Update executor and adapters to reuse collected sections"],
                },
                knowledge_objects=knowledge_objects,
                artifact_paths={
                    "task_memory": str(task_memory),
                    "summary": "artifacts/summary.md",
                },
            )
            retrieval_items = [
                RetrievalItem(
                    path=".swl/tasks/task-1/knowledge_objects.json",
                    source_type="knowledge",
                    score=9,
                    preview="Persist shared prompt facts",
                    citation=".swl/tasks/task-1/knowledge_objects.json#knowledge-0001",
                    title="Knowledge knowledge-0001",
                    metadata={
                        "knowledge_object_id": "knowledge-0001",
                        "evidence_status": "artifact_backed",
                        "storage_scope": "task_knowledge",
                        "knowledge_task_relation": "current_task",
                    },
                ),
                RetrievalItem(
                    path="docs/plan.md",
                    source_type="notes",
                    score=4,
                    preview="Extract a reusable prompt data layer.",
                    citation="docs/plan.md#L1-L4",
                    title="Plan",
                ),
            ]

            prompt_data = collect_prompt_data(state, retrieval_items)

        self.assertEqual(prompt_data.task.executor, "local")
        self.assertEqual(prompt_data.route.route_name, "local-summary")
        self.assertEqual(prompt_data.route.route_capabilities, "execution_kind=artifact_generation, supports_tool_loop=False")
        self.assertEqual(prompt_data.semantics.source_ref, "chat://phase35")
        self.assertEqual(prompt_data.semantics.constraints, ["Keep formatting stable"])
        self.assertEqual(prompt_data.knowledge.count, 1)
        self.assertEqual(prompt_data.knowledge.top_items, ["Persist shared prompt facts"])
        self.assertEqual(prompt_data.reused_knowledge.count, 1)
        self.assertEqual(
            prompt_data.previous_memory_artifacts,
            [str(task_memory), "artifacts/summary.md"],
        )
        self.assertEqual(prompt_data.prior_retrieval.count, "2")
        self.assertEqual(prompt_data.prior_retrieval.top_references, "docs/plan.md#L1-L4")
        self.assertIn(
            "[knowledge] .swl/tasks/task-1/knowledge_objects.json#knowledge-0001",
            prompt_data.retrieval_entries[0],
        )

    def test_resolve_dialect_name_matches_provider_model_hint_matrix(self) -> None:
        self.assertEqual(resolve_dialect_name("", "claude-3-7-sonnet"), "claude_xml")
        self.assertEqual(resolve_dialect_name("", "fim"), "fim")
        self.assertEqual(resolve_dialect_name("", "deepseek-chat"), "fim")
        self.assertEqual(resolve_dialect_name("", "deepseek-coder-v2"), "fim")
        self.assertEqual(resolve_dialect_name("", "qwen2.5-coder-32b-instruct"), "plain_text")
        self.assertEqual(resolve_dialect_name("", "glm-4.5-air"), "plain_text")
        self.assertEqual(resolve_dialect_name("", "gemini-2.5-pro"), "plain_text")
        self.assertEqual(resolve_dialect_name("codex_fim", ""), "codex_fim")

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

    def test_build_formatted_executor_prompt_includes_review_feedback_in_claude_xml_raw_prompt(self) -> None:
        state = TaskState(
            task_id="claude-xml-feedback-001",
            title="Claude XML feedback",
            goal="Render review feedback inside the raw prompt payload",
            workspace_root="/tmp",
            route_name="claude-local",
            route_backend="api_stub",
            route_model_hint="claude-3-5-sonnet",
            route_dialect="claude_xml",
            review_feedback_markdown="## Review Feedback (Round 1)\n\n- Return valid JSON.",
        )

        prompt = build_formatted_executor_prompt(state, [])

        self.assertIn("<raw_prompt>", prompt)
        self.assertIn("Review Feedback (Round 1)", prompt)
        self.assertIn("Return valid JSON.", prompt)

    def test_build_formatted_executor_prompt_uses_shared_data_for_structured_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_memory = tmp_path / "task_memory.json"
            task_memory.write_text(
                json.dumps(
                    {
                        "retrieval": {
                            "count": 3,
                            "top_references": ["docs/plan.md#L1-L3", "notes.md#L2-L5"],
                            "reused_knowledge_count": 1,
                            "reused_knowledge_current_task_count": 1,
                            "reused_knowledge_cross_task_count": 0,
                            "reused_knowledge_references": [".swl/tasks/task-1/knowledge_objects.json#knowledge-0001"],
                            "grounding_artifact": ".swl/tasks/task-1/artifacts/source_grounding.md",
                            "retrieval_record_path": ".swl/tasks/task-1/retrieval.json",
                        }
                    }
                ),
                encoding="utf-8",
            )
            knowledge_objects = [
                item.to_dict()
                for item in build_knowledge_objects(
                    items=["Shared data layer is now centralized"],
                    stage="verified",
                    source_ref="docs://phase35",
                    artifact_refs=["artifacts/knowledge.md"],
                    retrieval_eligible=True,
                    canonicalization_intent="review",
                )
            ]
            state = TaskState(
                task_id="structured-markdown-001",
                title="Structured markdown formatting",
                goal="Render markdown from the shared prompt data layer",
                workspace_root=str(tmp_path),
                executor_name="local",
                route_name="local-summary",
                route_backend="local_cli",
                route_executor_family="cli",
                route_execution_site="local",
                route_model_hint="local",
                route_dialect="structured_markdown",
                route_capabilities={"execution_kind": "artifact_generation", "supports_tool_loop": False},
                task_semantics={
                    "source_kind": "external_planning_handoff",
                    "source_ref": "chat://phase35",
                    "constraints": ["Keep formatting stable"],
                    "acceptance_criteria": ["Include prior retrieval memory"],
                },
                knowledge_objects=knowledge_objects,
                artifact_paths={
                    "task_memory": str(task_memory),
                    "summary": "artifacts/summary.md",
                },
            )
            retrieval_items = [
                RetrievalItem(
                    path=".swl/tasks/task-1/knowledge_objects.json",
                    source_type="knowledge",
                    score=9,
                    preview="Shared data layer is now centralized",
                    citation=".swl/tasks/task-1/knowledge_objects.json#knowledge-0001",
                    title="Knowledge knowledge-0001",
                    metadata={
                        "knowledge_object_id": "knowledge-0001",
                        "evidence_status": "artifact_backed",
                        "storage_scope": "task_knowledge",
                        "knowledge_task_relation": "current_task",
                    },
                ),
                RetrievalItem(
                    path="docs/plan.md",
                    source_type="notes",
                    score=4,
                    preview="Use one collector for prompt sections.",
                    citation="docs/plan.md#L1-L3",
                    title="Plan",
                ),
            ]

            prompt = build_formatted_executor_prompt(state, retrieval_items)

        self.assertIn("## Task Semantics", prompt)
        self.assertIn("- constraints: Keep formatting stable", prompt)
        self.assertIn("## Knowledge", prompt)
        self.assertIn("- top_items: Shared data layer is now centralized", prompt)
        self.assertIn("## Reused Verified Knowledge", prompt)
        self.assertIn("## Prior Persisted Context", prompt)
        self.assertIn("## Prior Retrieval Memory", prompt)
        self.assertIn("- previous_retrieval_count: 3", prompt)
        self.assertIn(".swl/tasks/task-1/knowledge_objects.json#knowledge-0001", prompt)
        self.assertIn("docs/plan.md#L1-L3", prompt)
        self.assertIn("## Instructions", prompt)

    def test_structured_markdown_prompt_appends_review_feedback_section(self) -> None:
        state = TaskState(
            task_id="structured-feedback-001",
            title="Structured feedback",
            goal="Carry review feedback into the next retry prompt",
            workspace_root="/tmp",
            executor_name="local",
            route_name="local-summary",
            route_backend="local_cli",
            route_executor_family="cli",
            route_execution_site="local",
            route_model_hint="local",
            route_dialect="structured_markdown",
            route_capabilities={"execution_kind": "artifact_generation", "supports_tool_loop": False},
            review_feedback_markdown="## Review Feedback (Round 2)\n\n- Return a non-empty output payload.",
        )

        prompt = build_formatted_executor_prompt(state, [])

        self.assertIn("## Review Feedback (Round 2)", prompt)
        self.assertIn("Return a non-empty output payload.", prompt)

    def test_fim_falls_back_to_raw_prompt_for_non_code_routes(self) -> None:
        state = TaskState(
            task_id="fim-plain-001",
            title="FIM fallback",
            goal="Keep non-code routes in raw form",
            workspace_root="/tmp",
            route_model_hint="fim",
            route_dialect="fim",
            route_capabilities={"execution_kind": "artifact_generation"},
        )

        prompt = build_formatted_executor_prompt(state, [])

        self.assertNotIn("<fim_prefix>", prompt)
        self.assertIn("You are the executor for a swallow workflow task.", prompt)

    def test_fim_escapes_user_controlled_fim_markers(self) -> None:
        state = TaskState(
            task_id="task-<fim_prefix>-001",
            title="Escape <fim_prefix> in title",
            goal="Keep <fim_suffix> markers inside task metadata from breaking the wrapper",
            workspace_root="/tmp",
            route_name="local-codex",
            route_model_hint="fim",
            route_dialect="fim",
            route_capabilities={"execution_kind": "code_execution"},
        )

        prompt = build_formatted_executor_prompt(state, [])

        self.assertTrue(prompt.startswith("<fim_prefix>\n"))
        self.assertEqual(prompt.count("<fim_prefix>"), 1)
        self.assertEqual(prompt.count("<fim_suffix>"), 1)
        self.assertIn("Task ID: task-[fim_prefix]-001", prompt)
        self.assertIn("Title: Escape [fim_prefix] in title", prompt)
        self.assertIn("Goal: Keep [fim_suffix] markers inside task metadata", prompt)

    def test_fim_prompt_keeps_review_feedback_inside_raw_prompt_section(self) -> None:
        state = TaskState(
            task_id="fim-feedback-001",
            title="FIM feedback",
            goal="Retry with concrete review feedback",
            workspace_root="/tmp",
            route_name="local-codex",
            route_model_hint="fim",
            route_dialect="fim",
            route_capabilities={"execution_kind": "code_execution"},
            review_feedback_markdown="## Review Feedback (Round 1)\n\n- Fix the failing schema fields.",
        )

        prompt = build_formatted_executor_prompt(state, [])

        self.assertIn("<fim_prefix>", prompt)
        self.assertIn("Review Feedback (Round 1)", prompt)
        self.assertIn("Fix the failing schema fields.", prompt)

    def test_build_formatted_executor_prompt_uses_fim_for_deepseek_code_route(self) -> None:
        state = TaskState(
            task_id="deepseek-fim-001",
            title="DeepSeek code route",
            goal="Use the code-oriented HTTP dialect for DeepSeek routes",
            workspace_root="/tmp",
            route_name="http-deepseek",
            route_backend="http_api",
            route_executor_family="api",
            route_execution_site="local",
            route_model_hint="deepseek-chat",
            route_dialect="fim",
            route_capabilities={"execution_kind": "code_execution", "supports_tool_loop": False},
        )

        prompt = build_formatted_executor_prompt(state, [])

        self.assertTrue(prompt.startswith("<fim_prefix>\n"))
        self.assertIn("Route: http-deepseek", prompt)
        self.assertIn("Model Hint: deepseek-chat", prompt)


if __name__ == "__main__":
    unittest.main()
