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
        self.assertTrue(card.card_id)
        self.assertTrue(card.created_at)

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

    def test_task_card_serializes_round_trip(self) -> None:
        card = TaskCard(
            goal="Keep planner output serializable",
            route_hint="local-mock",
            executor_type="mock",
            constraints=["Do not persist task cards in v0"],
            parent_task_id="task-456",
            input_context={"title": "Planner serialization"},
            input_schema={"kind": "task_input_v0"},
            output_schema={"kind": "executor_output_v0"},
        )

        restored = TaskCard.from_dict(card.to_dict())

        self.assertEqual(restored, card)


if __name__ == "__main__":
    unittest.main()
