from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.executor import ExecutorProtocol, LocalCLIExecutor, MockExecutor, resolve_executor
from swallow.models import ExecutorResult, RetrievalItem, TaskCard, TaskState


class ExecutorProtocolTest(unittest.TestCase):
    def test_runtime_v0_executors_satisfy_protocol(self) -> None:
        self.assertIsInstance(LocalCLIExecutor(), ExecutorProtocol)
        self.assertIsInstance(MockExecutor(), ExecutorProtocol)

    def test_resolve_executor_routes_mock_names_to_mock_executor(self) -> None:
        self.assertIsInstance(resolve_executor("cli", "mock"), MockExecutor)
        self.assertIsInstance(resolve_executor("cli", "mock-remote"), MockExecutor)

    def test_resolve_executor_defaults_to_local_cli_executor(self) -> None:
        self.assertIsInstance(resolve_executor("cli", "codex"), LocalCLIExecutor)
        self.assertIsInstance(resolve_executor("cli", "local"), LocalCLIExecutor)
        self.assertIsInstance(resolve_executor("cli", "note-only"), LocalCLIExecutor)

    def test_local_cli_executor_delegates_to_harness_run_execution(self) -> None:
        state = TaskState(
            task_id="task-local",
            title="Local execution adapter",
            goal="Delegate through harness",
            workspace_root="/tmp",
        )
        card = TaskCard(goal=state.goal, parent_task_id=state.task_id)
        retrieval_items = [
            RetrievalItem(path="README.md", source_type="repo", score=1, preview="planner protocol"),
        ]
        expected = ExecutorResult(
            executor_name="codex",
            status="completed",
            message="Delegated.",
            output="ok",
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with patch("swallow.harness.run_execution", return_value=expected) as execution_mock:
                result = LocalCLIExecutor().execute(tmp_path, state, card, retrieval_items)

        execution_mock.assert_called_once_with(tmp_path, state, retrieval_items)
        self.assertEqual(result, expected)

    def test_mock_executor_delegates_to_harness_run_execution(self) -> None:
        state = TaskState(
            task_id="task-mock",
            title="Mock execution adapter",
            goal="Delegate mock path through harness",
            workspace_root="/tmp",
        )
        card = TaskCard(goal=state.goal, parent_task_id=state.task_id)
        expected = ExecutorResult(
            executor_name="mock",
            status="completed",
            message="Mock delegated.",
            output="mock-ok",
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with patch("swallow.harness.run_execution", return_value=expected) as execution_mock:
                result = MockExecutor().execute(tmp_path, state, card, [])

        execution_mock.assert_called_once_with(tmp_path, state, [])
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
