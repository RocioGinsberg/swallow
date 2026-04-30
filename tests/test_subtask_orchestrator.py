from __future__ import annotations

import asyncio
import tempfile
import threading
import time
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.orchestration.models import ExecutorResult, TaskCard, TaskState
from swallow.orchestration.review_gate import ReviewGateResult
from swallow.orchestration.subtask_orchestrator import AsyncSubtaskOrchestrator, SubtaskOrchestrator, build_subtask_levels


def _build_card(goal: str, *, subtask_index: int, depends_on: list[str] | None = None) -> TaskCard:
    return TaskCard(
        goal=goal,
        route_hint="local-aider",
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


class AsyncSubtaskOrchestratorTest(unittest.IsolatedAsyncioTestCase):
    async def test_run_executes_independent_cards_concurrently(self) -> None:
        state = TaskState(
            task_id="task-parallel-async",
            title="Parallel async subtasks",
            goal="Run async subtasks in parallel",
            workspace_root="/tmp",
        )
        card_a = _build_card("A", subtask_index=1)
        card_b = _build_card("B", subtask_index=2)
        active_count = 0
        max_active = 0
        lock = asyncio.Lock()

        async def execute_card(
            _base_dir: Path,
            _state: TaskState,
            card: TaskCard,
            _retrieval_items: list[object],
        ) -> ExecutorResult:
            nonlocal active_count, max_active
            async with lock:
                active_count += 1
                max_active = max(max_active, active_count)
            await asyncio.sleep(0.05)
            async with lock:
                active_count -= 1
            return ExecutorResult(
                executor_name="mock",
                status="completed",
                message="ok",
                output=card.goal,
            )

        async def review_card(_result: ExecutorResult, card: TaskCard) -> ReviewGateResult:
            return ReviewGateResult(status="passed", message=f"{card.goal} ok", checks=[])

        with tempfile.TemporaryDirectory() as tmp:
            result = await AsyncSubtaskOrchestrator(execute_card, review_card).run(
                Path(tmp),
                state,
                [card_a, card_b],
                [],
            )

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.levels, [[card_a.card_id, card_b.card_id]])
        self.assertEqual(result.max_parallelism, 2)
        self.assertGreaterEqual(max_active, 2)

    async def test_run_marks_subtask_timeout_without_canceling_other_cards(self) -> None:
        state = TaskState(
            task_id="task-timeout-async",
            title="Timeout async subtasks",
            goal="Keep healthy subtasks running when one times out",
            workspace_root="/tmp",
        )
        card_a = _build_card("A", subtask_index=1)
        card_b = _build_card("B", subtask_index=2)
        card_a.reviewer_timeout_seconds = 1
        card_b.reviewer_timeout_seconds = 1

        async def execute_card(
            _base_dir: Path,
            _state: TaskState,
            card: TaskCard,
            _retrieval_items: list[object],
        ) -> ExecutorResult:
            if card.card_id == card_b.card_id:
                await asyncio.sleep(1.2)
            else:
                await asyncio.sleep(0.05)
            return ExecutorResult(
                executor_name="mock",
                status="completed",
                message="ok",
                output=card.goal,
            )

        async def review_card(result: ExecutorResult, card: TaskCard) -> ReviewGateResult:
            return ReviewGateResult(
                status="passed" if result.status == "completed" else "failed",
                message=f"{card.goal} {result.status}",
                checks=[],
            )

        started_at = time.perf_counter()
        with tempfile.TemporaryDirectory() as tmp:
            result = await AsyncSubtaskOrchestrator(execute_card, review_card).run(
                Path(tmp),
                state,
                [card_a, card_b],
                [],
            )
        elapsed = time.perf_counter() - started_at
        records_by_id = {record.card_id: record for record in result.records}

        self.assertLess(elapsed, 1.15)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.completed_count, 1)
        self.assertEqual(result.failed_count, 1)
        self.assertEqual(records_by_id[card_a.card_id].status, "completed")
        self.assertEqual(records_by_id[card_b.card_id].executor_result.failure_kind, "subtask_timeout")
        self.assertEqual(records_by_id[card_b.card_id].review_gate_result.status, "failed")

    async def test_run_collects_cancelled_subtask_as_failed_record(self) -> None:
        state = TaskState(
            task_id="task-cancelled-async",
            title="Cancelled async subtask",
            goal="Convert unexpected cancellations into failed records",
            workspace_root="/tmp",
        )
        card_a = _build_card("A", subtask_index=1)
        card_b = _build_card("B", subtask_index=2)

        async def execute_card(
            _base_dir: Path,
            _state: TaskState,
            card: TaskCard,
            _retrieval_items: list[object],
        ) -> ExecutorResult:
            if card.card_id == card_b.card_id:
                raise asyncio.CancelledError("synthetic cancellation")
            await asyncio.sleep(0.05)
            return ExecutorResult(
                executor_name="mock",
                status="completed",
                message="ok",
                output=card.goal,
            )

        async def review_card(result: ExecutorResult, card: TaskCard) -> ReviewGateResult:
            return ReviewGateResult(
                status="passed" if result.status == "completed" else "failed",
                message=f"{card.goal} {result.status}",
                checks=[],
            )

        with tempfile.TemporaryDirectory() as tmp:
            result = await AsyncSubtaskOrchestrator(execute_card, review_card).run(
                Path(tmp),
                state,
                [card_a, card_b],
                [],
            )
        records_by_id = {record.card_id: record for record in result.records}

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.completed_count, 1)
        self.assertEqual(result.failed_count, 1)
        self.assertEqual(records_by_id[card_a.card_id].status, "completed")
        self.assertEqual(records_by_id[card_b.card_id].status, "failed")
        self.assertEqual(records_by_id[card_b.card_id].executor_result.failure_kind, "subtask_exception")
        self.assertIn("CancelledError", records_by_id[card_b.card_id].executor_result.stderr)

    def test_orchestrator_reads_max_workers_from_environment(self) -> None:
        async def execute_card(
            _base_dir: Path,
            _state: TaskState,
            _card: TaskCard,
            _retrieval_items: list[object],
        ) -> ExecutorResult:
            return ExecutorResult(executor_name="mock", status="completed", message="ok")

        async def review_card(_result: ExecutorResult, _card: TaskCard) -> ReviewGateResult:
            return ReviewGateResult(status="passed", message="ok", checks=[])

        with patch.dict("os.environ", {"AIWF_MAX_SUBTASK_WORKERS": "2"}, clear=False):
            orchestrator = AsyncSubtaskOrchestrator(execute_card, review_card)

        self.assertEqual(orchestrator._max_workers, 2)


if __name__ == "__main__":
    unittest.main()
