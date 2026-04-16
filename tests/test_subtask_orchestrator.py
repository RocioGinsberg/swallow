from __future__ import annotations

import tempfile
import threading
import time
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.models import ExecutorResult, TaskCard, TaskState
from swallow.review_gate import ReviewGateResult
from swallow.subtask_orchestrator import SubtaskOrchestrator, build_subtask_levels


def _build_card(goal: str, *, subtask_index: int, depends_on: list[str] | None = None) -> TaskCard:
    return TaskCard(
        goal=goal,
        route_hint="local-codex",
        executor_type="cli",
        parent_task_id="task-subtasks",
        subtask_index=subtask_index,
        depends_on=list(depends_on or []),
    )


class SubtaskOrchestratorTest(unittest.TestCase):
    def test_build_subtask_levels_rejects_unknown_and_cyclic_dependencies(self) -> None:
        card_a = _build_card("A", subtask_index=1, depends_on=["missing-card"])
        with self.assertRaisesRegex(ValueError, "unknown card"):
            build_subtask_levels([card_a])

        card_b = _build_card("B", subtask_index=1)
        card_c = _build_card("C", subtask_index=2, depends_on=[card_b.card_id])
        card_b.depends_on = [card_c.card_id]
        with self.assertRaisesRegex(ValueError, "cyclic dependencies"):
            build_subtask_levels([card_b, card_c])

    def test_run_executes_sequential_cards_in_dependency_order(self) -> None:
        state = TaskState(
            task_id="task-sequential",
            title="Sequential subtasks",
            goal="Run subtasks in order",
            workspace_root="/tmp",
        )
        card_a = _build_card("A", subtask_index=1)
        card_b = _build_card("B", subtask_index=2, depends_on=[card_a.card_id])
        card_c = _build_card("C", subtask_index=3, depends_on=[card_b.card_id])
        started_order: list[str] = []

        def execute_card(_base_dir: Path, _state: TaskState, card: TaskCard, _retrieval_items: list[object]) -> ExecutorResult:
            started_order.append(card.goal)
            return ExecutorResult(
                executor_name="mock",
                status="completed",
                message="ok",
                output=card.goal,
            )

        def review_card(result: ExecutorResult, card: TaskCard) -> ReviewGateResult:
            return ReviewGateResult(
                status="passed",
                message=f"{card.goal} ok",
                checks=[{"name": "executor_status", "passed": result.status == "completed", "detail": "ok"}],
            )

        with tempfile.TemporaryDirectory() as tmp:
            result = SubtaskOrchestrator(execute_card, review_card).run(
                Path(tmp),
                state,
                [card_a, card_b, card_c],
                [],
            )

        self.assertEqual(result.status, "completed")
        self.assertEqual(started_order, ["A", "B", "C"])
        self.assertEqual(result.levels, [[card_a.card_id], [card_b.card_id], [card_c.card_id]])
        self.assertEqual(result.completed_count, 3)
        self.assertEqual(result.failed_count, 0)
        self.assertEqual([record.goal for record in result.records], ["A", "B", "C"])

    def test_run_executes_independent_cards_concurrently(self) -> None:
        state = TaskState(
            task_id="task-parallel",
            title="Parallel subtasks",
            goal="Run subtasks in parallel",
            workspace_root="/tmp",
        )
        card_a = _build_card("A", subtask_index=1)
        card_b = _build_card("B", subtask_index=2)
        active_count = 0
        max_active = 0
        lock = threading.Lock()

        def execute_card(_base_dir: Path, _state: TaskState, card: TaskCard, _retrieval_items: list[object]) -> ExecutorResult:
            nonlocal active_count, max_active
            with lock:
                active_count += 1
                max_active = max(max_active, active_count)
            time.sleep(0.05)
            with lock:
                active_count -= 1
            return ExecutorResult(
                executor_name="mock",
                status="completed",
                message="ok",
                output=card.goal,
            )

        def review_card(_result: ExecutorResult, card: TaskCard) -> ReviewGateResult:
            return ReviewGateResult(status="passed", message=f"{card.goal} ok", checks=[])

        with tempfile.TemporaryDirectory() as tmp:
            result = SubtaskOrchestrator(execute_card, review_card).run(
                Path(tmp),
                state,
                [card_a, card_b],
                [],
            )

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.levels, [[card_a.card_id, card_b.card_id]])
        self.assertEqual(result.max_parallelism, 2)
        self.assertGreaterEqual(max_active, 2)

    def test_run_waits_for_all_dependencies_before_downstream_card(self) -> None:
        state = TaskState(
            task_id="task-join",
            title="Joined subtasks",
            goal="Wait for all dependencies",
            workspace_root="/tmp",
        )
        card_a = _build_card("A", subtask_index=1)
        card_b = _build_card("B", subtask_index=2)
        card_c = _build_card("C", subtask_index=3, depends_on=[card_a.card_id, card_b.card_id])
        completed: set[str] = set()
        lock = threading.Lock()

        def execute_card(_base_dir: Path, _state: TaskState, card: TaskCard, _retrieval_items: list[object]) -> ExecutorResult:
            if card.card_id == card_c.card_id:
                with lock:
                    self.assertEqual(completed, {card_a.card_id, card_b.card_id})
            time.sleep(0.02)
            with lock:
                completed.add(card.card_id)
            return ExecutorResult(
                executor_name="mock",
                status="completed",
                message="ok",
                output=card.goal,
            )

        def review_card(_result: ExecutorResult, card: TaskCard) -> ReviewGateResult:
            return ReviewGateResult(status="passed", message=f"{card.goal} ok", checks=[])

        with tempfile.TemporaryDirectory() as tmp:
            result = SubtaskOrchestrator(execute_card, review_card).run(
                Path(tmp),
                state,
                [card_a, card_b, card_c],
                [],
            )

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.levels, [[card_a.card_id, card_b.card_id], [card_c.card_id]])

    def test_run_marks_failed_when_review_or_execution_fails(self) -> None:
        state = TaskState(
            task_id="task-failed",
            title="Failed subtasks",
            goal="Aggregate failures",
            workspace_root="/tmp",
        )
        card_a = _build_card("A", subtask_index=1)
        card_b = _build_card("B", subtask_index=2)

        def execute_card(_base_dir: Path, _state: TaskState, card: TaskCard, _retrieval_items: list[object]) -> ExecutorResult:
            status = "failed" if card.card_id == card_b.card_id else "completed"
            output = "" if status == "failed" else card.goal
            return ExecutorResult(
                executor_name="mock",
                status=status,
                message=status,
                output=output,
            )

        def review_card(result: ExecutorResult, card: TaskCard) -> ReviewGateResult:
            status = "passed" if card.card_id == card_a.card_id and result.status == "completed" else "failed"
            return ReviewGateResult(status=status, message=f"{card.goal} {status}", checks=[])

        with tempfile.TemporaryDirectory() as tmp:
            result = SubtaskOrchestrator(execute_card, review_card).run(
                Path(tmp),
                state,
                [card_a, card_b],
                [],
            )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.completed_count, 1)
        self.assertEqual(result.failed_count, 1)
        self.assertEqual(result.failed_card_ids, [card_b.card_id])
        self.assertEqual(result.records[1].status, "failed")


if __name__ == "__main__":
    unittest.main()
