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
