from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.cli import main
from swallow.meta_optimizer import build_meta_optimizer_snapshot, run_meta_optimizer
from swallow.models import EVENT_EXECUTOR_COMPLETED, EVENT_EXECUTOR_FAILED, EVENT_TASK_EXECUTION_FALLBACK
from swallow.paths import optimization_proposals_path


def _write_events(task_dir: Path, records: list[dict[str, object]]) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "events.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


class MetaOptimizerTest(unittest.TestCase):
    def test_run_meta_optimizer_aggregates_route_health_and_failure_fingerprints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task_a = base_dir / ".swl" / "tasks" / "task-a"
            task_b = base_dir / ".swl" / "tasks" / "task-b"
            _write_events(
                task_a,
                [
                    {
                        "task_id": "task-a",
                        "event_type": EVENT_EXECUTOR_FAILED,
                        "message": "Codex launch failed.",
                        "payload": {
                            "physical_route": "local-codex",
                            "logical_model": "codex",
                            "latency_ms": 12,
                            "degraded": False,
                            "failure_kind": "launch_error",
                            "error_code": "launch_error",
                        },
                    },
                    {
                        "task_id": "task-a",
                        "event_type": EVENT_TASK_EXECUTION_FALLBACK,
                        "message": "Fallback executed.",
                        "payload": {
                            "previous_route_name": "local-codex",
                            "fallback_route_name": "local-summary",
                            "latency_ms": 4,
                            "degraded": True,
                        },
                    },
                    {
                        "task_id": "task-a",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
                        "message": "Fallback completed.",
                        "payload": {
                            "physical_route": "local-summary",
                            "logical_model": "local",
                            "latency_ms": 4,
                            "degraded": True,
                            "error_code": "",
                        },
                    },
                ],
            )
            _write_events(
                task_b,
                [
                    {
                        "task_id": "task-b",
                        "event_type": EVENT_EXECUTOR_FAILED,
                        "message": "Codex launch failed again.",
                        "payload": {
                            "physical_route": "local-codex",
                            "logical_model": "codex",
                            "latency_ms": 8,
                            "degraded": False,
                            "failure_kind": "launch_error",
                            "error_code": "launch_error",
                        },
                    }
                ],
            )

            snapshot, artifact_path, report = run_meta_optimizer(base_dir, last_n=100)
            self.assertEqual(len(snapshot.scanned_task_ids), 2)
            self.assertEqual(snapshot.scanned_event_count, 4)
            self.assertEqual(artifact_path, optimization_proposals_path(base_dir))
            self.assertTrue(artifact_path.exists())
            self.assertIn("## Route Health", report)
            self.assertIn("local-codex: success_rate=0% failure_rate=100% fallback_rate=50%", report)
            self.assertIn("local-summary: success_rate=100% failure_rate=0% fallback_rate=0%", report)
            self.assertIn("failure_kind=launch_error error_code=launch_error count=2 routes=local-codex", report)
            self.assertIn("degraded_executor_events: 1/3", report)
            self.assertIn("Review route `local-codex`", report)
            self.assertIn("Investigate repeated failure fingerprint `launch_error/launch_error`", report)
            self.assertEqual(artifact_path.read_text(encoding="utf-8"), report)

    def test_run_meta_optimizer_handles_empty_task_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)

            snapshot, artifact_path, report = run_meta_optimizer(base_dir, last_n=100)
            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(base_dir), "meta-optimize"]), 0)
            self.assertEqual(snapshot.scanned_task_ids, [])
            self.assertTrue(artifact_path.exists())
            self.assertIn("- no data", report)
            self.assertIn("# Meta-Optimizer Proposals", stdout.getvalue())
            self.assertIn("artifact:", stdout.getvalue())

    def test_meta_optimizer_scan_is_read_only_for_task_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task_dir = base_dir / ".swl" / "tasks" / "readonly-task"
            task_dir.mkdir(parents=True, exist_ok=True)
            state_path = task_dir / "state.json"
            events_path = task_dir / "events.jsonl"
            state_path.write_text(json.dumps({"task_id": "readonly-task", "status": "completed"}) + "\n", encoding="utf-8")
            events_path.write_text(
                json.dumps(
                    {
                        "task_id": "readonly-task",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
                        "message": "Completed.",
                        "payload": {
                            "physical_route": "local-summary",
                            "logical_model": "local",
                            "latency_ms": 3,
                            "degraded": False,
                            "error_code": "",
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            original_state = state_path.read_text(encoding="utf-8")
            original_events = events_path.read_text(encoding="utf-8")

            snapshot = build_meta_optimizer_snapshot(base_dir, last_n=100)
            _, artifact_path, _report = run_meta_optimizer(base_dir, last_n=100)
            self.assertEqual(snapshot.scanned_task_ids, ["readonly-task"])
            self.assertEqual(state_path.read_text(encoding="utf-8"), original_state)
            self.assertEqual(events_path.read_text(encoding="utf-8"), original_events)
            self.assertTrue(artifact_path.exists())


if __name__ == "__main__":
    unittest.main()
