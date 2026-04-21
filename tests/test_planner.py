from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.models import TaskCard, TaskState
from swallow.planner import plan


class PlannerTest(unittest.TestCase):
    def test_plan_builds_single_runtime_v0_task_card(self) -> None:
        state = TaskState(
            task_id="task-123",
            title="Implement planner",
            goal="Introduce runtime task cards",
            workspace_root="/tmp/workspace",
            task_semantics={
                "constraints": [
                    "Keep v0 planner rule-driven",
                    "Do not fan out into multiple cards yet",
                ],
                "acceptance_criteria": ["Return one task card"],
            },
            route_name="local-codex",
            route_executor_family="cli",
        )

        cards = plan(state)

        self.assertEqual(len(cards), 1)
        card = cards[0]
        self.assertEqual(card.goal, state.goal)
        self.assertEqual(card.parent_task_id, state.task_id)
        self.assertEqual(card.route_hint, "local-codex")
        self.assertEqual(card.executor_type, "cli")
        self.assertEqual(card.constraints, state.task_semantics["constraints"])
        self.assertEqual(
            card.input_context,
            {
                "title": state.title,
                "workspace_root": state.workspace_root,
                "task_semantics": state.task_semantics,
            },
        )
        self.assertEqual(card.status, "planned")
        self.assertEqual(card.output_schema, {})
        self.assertEqual(card.depends_on, [])
        self.assertEqual(card.subtask_index, 1)
        self.assertEqual(card.reviewer_routes, [])
        self.assertEqual(card.consensus_policy, "majority")
        self.assertTrue(card.card_id)
        self.assertTrue(card.created_at)

    def test_plan_propagates_consensus_review_configuration(self) -> None:
        state = TaskState(
            task_id="task-consensus",
            title="Consensus plan",
            goal="Fan out to multiple reviewers",
            workspace_root="/tmp/workspace",
            task_semantics={
                "constraints": ["Keep the gate conservative"],
                "reviewer_routes": ["http-claude", "http-qwen", "http-claude", ""],
                "consensus_policy": "veto",
                "reviewer_timeout_seconds": 45,
                "token_cost_limit": 1.25,
            },
            route_name="local-http",
            route_executor_family="api",
        )

        cards = plan(state)

        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].reviewer_routes, ["http-claude", "http-qwen"])
        self.assertEqual(cards[0].consensus_policy, "veto")
        self.assertEqual(cards[0].reviewer_timeout_seconds, 45)
        self.assertEqual(cards[0].token_cost_limit, 1.25)

    def test_plan_builds_librarian_task_card_for_local_promotion_ready_evidence(self) -> None:
        state = TaskState(
            task_id="task-librarian",
            title="Promote verified knowledge",
            goal="Hand verified canonical-ready evidence to the librarian",
            workspace_root="/tmp/workspace",
            task_semantics={
                "constraints": [
                    "Only promote artifact-backed verified evidence",
                ],
            },
            knowledge_objects=[
                {
                    "object_id": "knowledge-0001",
                    "text": "Canonical-ready fact",
                    "stage": "verified",
                    "source_kind": "external_knowledge_capture",
                    "source_ref": "chat://promotion-ready",
                    "task_linked": True,
                    "captured_at": "2026-04-16T00:00:00+00:00",
                    "evidence_status": "artifact_backed",
                    "artifact_ref": ".swl/tasks/task-librarian/artifacts/evidence.md",
                    "retrieval_eligible": False,
                    "knowledge_reuse_scope": "task_only",
                    "canonicalization_intent": "promote",
                }
            ],
            route_name="local-codex",
            route_executor_family="cli",
            route_execution_site="local",
            route_taxonomy_memory_authority="task-state",
        )

        cards = plan(state)

        self.assertEqual(len(cards), 1)
        card = cards[0]
        self.assertEqual(card.executor_type, "librarian")
        self.assertEqual(card.route_hint, "librarian-local")
        self.assertEqual(card.parent_task_id, state.task_id)
        self.assertEqual(card.input_context["promotion_ready_object_ids"], ["knowledge-0001"])
        self.assertEqual(card.input_context["librarian_taxonomy"]["system_role"], "specialist")
        self.assertEqual(card.input_context["librarian_taxonomy"]["memory_authority"], "canonical-promotion")
        self.assertEqual(card.output_schema["const"]["kind"], "librarian_change_log_v0")
        self.assertEqual(card.depends_on, [])
        self.assertEqual(card.subtask_index, 1)

    def test_plan_builds_sequential_subtask_cards_from_multiple_next_actions(self) -> None:
        state = TaskState(
            task_id="task-sequential",
            title="Decompose runtime work",
            goal="Implement a bounded multi-card planner",
            workspace_root="/tmp/workspace",
            task_semantics={
                "constraints": ["Keep planning rule-driven"],
                "next_action_proposals": [
                    "Extract TaskCard dependency metadata",
                    "Teach planner to emit multiple task cards",
                    "Add planner regression coverage",
                ],
            },
            route_name="local-codex",
            route_executor_family="cli",
        )

        cards = plan(state)

        self.assertEqual(len(cards), 3)
        self.assertEqual([card.subtask_index for card in cards], [1, 2, 3])
        self.assertEqual([card.goal for card in cards], state.task_semantics["next_action_proposals"])
        self.assertEqual(cards[0].depends_on, [])
        self.assertEqual(cards[1].depends_on, [cards[0].card_id])
        self.assertEqual(cards[2].depends_on, [cards[1].card_id])
        self.assertTrue(all(card.input_context["planning_mode"] == "sequential" for card in cards))
        self.assertTrue(all(card.input_context["parent_goal"] == state.goal for card in cards))

    def test_plan_builds_parallel_subtask_cards_when_parallel_hint_present(self) -> None:
        state = TaskState(
            task_id="task-parallel",
            title="Parallel runtime work",
            goal="Fan out independent subtask cards",
            workspace_root="/tmp/workspace",
            task_semantics={
                "constraints": [
                    "parallel_subtasks",
                    "Limit the planner to a bounded split",
                ],
                "next_action_proposals": [
                    "Implement TaskCard dependency fields",
                    "Add planner fan-out logic",
                    "Write multi-card planner tests",
                    "Document slice validation",
                    "Ignore overflow action",
                ],
            },
            route_name="local-codex",
            route_executor_family="cli",
        )

        cards = plan(state)

        self.assertEqual(len(cards), 4)
        self.assertEqual([card.subtask_index for card in cards], [1, 2, 3, 4])
        self.assertEqual(
            [card.goal for card in cards],
            state.task_semantics["next_action_proposals"][:4],
        )
        self.assertTrue(all(card.depends_on == [] for card in cards))
        self.assertTrue(all(card.input_context["planning_mode"] == "parallel" for card in cards))

    def test_task_card_serializes_round_trip(self) -> None:
        card = TaskCard(
            goal="Keep planner output serializable",
            route_hint="local-mock",
            executor_type="mock",
            constraints=["Do not persist task cards in v0"],
            depends_on=["card-a"],
            subtask_index=2,
            parent_task_id="task-456",
            input_context={"title": "Planner serialization"},
            input_schema={"kind": "task_input_v0"},
            output_schema={"kind": "executor_output_v0"},
        )

        restored = TaskCard.from_dict(card.to_dict())

        self.assertEqual(restored, card)


if __name__ == "__main__":
    unittest.main()
