from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.models import ExecutorResult, ValidationResult
from swallow.orchestrator import create_task, run_task


def _load_json_lines(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []

    records: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _passing_validation_tuple() -> tuple[ValidationResult, ...]:
    return (
        ValidationResult(status="passed", message="Compatibility passed."),
        ValidationResult(status="passed", message="Execution fit passed."),
        ValidationResult(status="passed", message="Knowledge policy passed."),
        ValidationResult(status="passed", message="Validation passed."),
        ValidationResult(status="passed", message="Retry policy passed."),
        ValidationResult(status="warning", message="Stop policy warning."),
        ValidationResult(status="passed", message="Execution budget policy passed."),
    )


class BinaryFallbackTest(unittest.TestCase):
    def test_run_task_switches_to_fallback_route_after_primary_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            created = create_task(
                base_dir=tmp_path,
                title="Binary fallback success",
                goal="Retry with local summary after codex failure",
                workspace_root=tmp_path,
            )
            task_dir = tmp_path / ".swl" / "tasks" / created.task_id
            artifacts_dir = task_dir / "artifacts"

            def fail_codex(_state: object, _retrieval_items: list[object], prompt: str | None = None) -> ExecutorResult:
                return ExecutorResult(
                    executor_name="codex",
                    status="failed",
                    message="Codex route failed.",
                    output="primary executor output",
                    prompt=prompt or "",
                    dialect="codex_fim",
                    failure_kind="launch_error",
                    stderr="codex unavailable",
                )

            def complete_local(_state: object, _retrieval_items: list[object], prompt: str) -> ExecutorResult:
                return ExecutorResult(
                    executor_name="local",
                    status="completed",
                    message="Fallback route completed.",
                    output="fallback executor output",
                    prompt=prompt,
                    dialect="plain_text",
                )

            with patch("swallow.orchestrator.run_retrieval", return_value=[]):
                with patch(
                    "swallow.orchestrator.write_task_artifacts",
                    return_value=_passing_validation_tuple(),
                ):
                    with patch("swallow.executor.run_codex_executor", side_effect=fail_codex):
                        with patch("swallow.executor.run_local_executor", side_effect=complete_local):
                            final_state = run_task(tmp_path, created.task_id)

            events = _load_json_lines(task_dir / "events.jsonl")
            fallback_event = next(event for event in events if event["event_type"] == "task.execution_fallback")
            executor_completed = next(event for event in events if event["event_type"] == "executor.completed")
            self.assertEqual(final_state.status, "completed")
            self.assertEqual(final_state.executor_name, "local")
            self.assertEqual(final_state.route_name, "local-summary")
            self.assertEqual(fallback_event["payload"]["previous_route_name"], "local-codex")
            self.assertEqual(fallback_event["payload"]["fallback_route_name"], "local-summary")
            self.assertEqual(fallback_event["payload"]["fallback_status"], "completed")
            self.assertEqual(executor_completed["payload"]["route_name"], "local-summary")
            self.assertTrue((artifacts_dir / "fallback_primary_executor_output.md").exists())
            self.assertTrue((artifacts_dir / "fallback_executor_output.md").exists())
            self.assertEqual(
                (artifacts_dir / "fallback_primary_executor_output.md").read_text(encoding="utf-8").strip(),
                "primary executor output",
            )
            self.assertEqual(
                (artifacts_dir / "fallback_executor_output.md").read_text(encoding="utf-8").strip(),
                "fallback executor output",
            )
            self.assertEqual(
                (artifacts_dir / "executor_output.md").read_text(encoding="utf-8").strip(),
                "fallback executor output",
            )

    def test_run_task_stops_after_single_fallback_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            created = create_task(
                base_dir=tmp_path,
                title="Binary fallback failure",
                goal="Fail after the single fallback route also fails",
                workspace_root=tmp_path,
            )
            task_dir = tmp_path / ".swl" / "tasks" / created.task_id
            artifacts_dir = task_dir / "artifacts"

            def fail_codex(_state: object, _retrieval_items: list[object], prompt: str | None = None) -> ExecutorResult:
                return ExecutorResult(
                    executor_name="codex",
                    status="failed",
                    message="Codex route failed.",
                    output="primary executor output",
                    prompt=prompt or "",
                    dialect="codex_fim",
                    failure_kind="launch_error",
                    stderr="codex unavailable",
                )

            def fail_local(_state: object, _retrieval_items: list[object], prompt: str) -> ExecutorResult:
                return ExecutorResult(
                    executor_name="local",
                    status="failed",
                    message="Fallback route failed.",
                    output="fallback executor output",
                    prompt=prompt,
                    dialect="plain_text",
                    failure_kind="local_failure",
                    stderr="fallback route still failed",
                )

            with patch("swallow.orchestrator.run_retrieval", return_value=[]):
                with patch(
                    "swallow.orchestrator.write_task_artifacts",
                    return_value=_passing_validation_tuple(),
                ):
                    with patch("swallow.executor.run_codex_executor", side_effect=fail_codex):
                        with patch("swallow.executor.run_local_executor", side_effect=fail_local):
                            final_state = run_task(tmp_path, created.task_id)

            events = _load_json_lines(task_dir / "events.jsonl")
            fallback_events = [event for event in events if event["event_type"] == "task.execution_fallback"]
            executor_failures = [event for event in events if event["event_type"] == "executor.failed"]
            self.assertEqual(final_state.status, "failed")
            self.assertEqual(final_state.route_name, "local-summary")
            self.assertEqual(len(fallback_events), 1)
            self.assertEqual(len(executor_failures), 2)
            self.assertEqual(fallback_events[0]["payload"]["fallback_status"], "failed")
            self.assertTrue((artifacts_dir / "fallback_primary_executor_output.md").exists())
            self.assertTrue((artifacts_dir / "fallback_executor_output.md").exists())
            self.assertEqual(
                (artifacts_dir / "executor_output.md").read_text(encoding="utf-8").strip(),
                "fallback executor output",
            )


if __name__ == "__main__":
    unittest.main()
