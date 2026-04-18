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
                            "task_family": "execution",
                            "latency_ms": 12,
                            "token_cost": 0.0,
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
                            "task_family": "execution",
                            "latency_ms": 4,
                            "token_cost": 0.0,
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
                            "task_family": "execution",
                            "latency_ms": 8,
                            "token_cost": 0.0,
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
            self.assertIn("## Cost Summary", report)
            self.assertIn("local-summary: total_cost=$0.000000 avg_cost=$0.000000 task_families=execution", report)
            self.assertIn("Review route `local-codex`", report)
            self.assertIn("Investigate repeated failure fingerprint `launch_error/launch_error`", report)
            self.assertEqual(artifact_path.read_text(encoding="utf-8"), report)

    def test_run_meta_optimizer_generates_cost_proposals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task_a = base_dir / ".swl" / "tasks" / "cost-a"
            task_b = base_dir / ".swl" / "tasks" / "cost-b"
            task_c = base_dir / ".swl" / "tasks" / "cost-c"
            _write_events(
                task_a,
                [
                    {
                        "task_id": "cost-a",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
                        "message": "Claude review done.",
                        "payload": {
                            "physical_route": "api-claude-review",
                            "logical_model": "claude",
                            "task_family": "review",
                            "latency_ms": 30,
                            "token_cost": 0.12,
                            "degraded": False,
                            "error_code": "",
                        },
                    },
                    {
                        "task_id": "cost-a",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
                        "message": "Claude review done again.",
                        "payload": {
                            "physical_route": "api-claude-review",
                            "logical_model": "claude",
                            "task_family": "review",
                            "latency_ms": 35,
                            "token_cost": 0.18,
                            "degraded": False,
                            "error_code": "",
                        },
                    },
                ],
            )
            _write_events(
                task_b,
                [
                    {
                        "task_id": "cost-b",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
                        "message": "Claude review spiked.",
                        "payload": {
                            "physical_route": "api-claude-review",
                            "logical_model": "claude",
                            "task_family": "review",
                            "latency_ms": 36,
                            "token_cost": 0.42,
                            "degraded": False,
                            "error_code": "",
                        },
                    },
                    {
                        "task_id": "cost-b",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
                        "message": "Claude review spiked again.",
                        "payload": {
                            "physical_route": "api-claude-review",
                            "logical_model": "claude",
                            "task_family": "review",
                            "latency_ms": 39,
                            "token_cost": 0.48,
                            "degraded": False,
                            "error_code": "",
                        },
                    },
                ],
            )
            _write_events(
                task_c,
                [
                    {
                        "task_id": "cost-c",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
                        "message": "Local review summary done.",
                        "payload": {
                            "physical_route": "local-summary-review",
                            "logical_model": "local",
                            "task_family": "review",
                            "latency_ms": 5,
                            "token_cost": 0.0,
                            "degraded": False,
                            "error_code": "",
                        },
                    },
                ],
            )

            snapshot, _artifact_path, report = run_meta_optimizer(base_dir, last_n=100)
            expensive_route = next(stats for stats in snapshot.route_stats if stats.route_name == "api-claude-review")
            self.assertAlmostEqual(expensive_route.total_cost, 1.2)
            self.assertAlmostEqual(expensive_route.average_cost(), 0.3)
            self.assertIn("api-claude-review: total_cost=$1.200000 avg_cost=$0.300000 task_families=review", report)
            self.assertIn(
                "Review route `api-claude-review`: average estimated cost is $0.30/task across 4 executor events.",
                report,
            )
            self.assertIn(
                "Compare cost for task_family `review`: route `api-claude-review` averages $0.30/task versus `local-summary-review` at $0.00/task.",
                report,
            )
            self.assertIn(
                "Watch cost trend on `api-claude-review`: recent estimated cost rose from $0.15 to $0.45 per executor event.",
                report,
            )

    def test_run_meta_optimizer_counts_fallback_token_cost_on_previous_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task_dir = base_dir / ".swl" / "tasks" / "fallback-cost"
            _write_events(
                task_dir,
                [
                    {
                        "task_id": "fallback-cost",
                        "event_type": EVENT_EXECUTOR_FAILED,
                        "message": "Primary route failed.",
                        "payload": {
                            "physical_route": "local-codex",
                            "logical_model": "codex",
                            "task_family": "execution",
                            "latency_ms": 12,
                            "token_cost": 0.0,
                            "degraded": False,
                            "failure_kind": "launch_error",
                            "error_code": "launch_error",
                        },
                    },
                    {
                        "task_id": "fallback-cost",
                        "event_type": EVENT_TASK_EXECUTION_FALLBACK,
                        "message": "Fallback executed.",
                        "payload": {
                            "previous_route_name": "local-codex",
                            "fallback_route_name": "local-summary",
                            "latency_ms": 4,
                            "degraded": True,
                            "token_cost": 0.25,
                        },
                    },
                    {
                        "task_id": "fallback-cost",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
                        "message": "Fallback completed.",
                        "payload": {
                            "physical_route": "local-summary",
                            "logical_model": "local",
                            "task_family": "execution",
                            "latency_ms": 4,
                            "token_cost": 0.0,
                            "degraded": True,
                            "error_code": "",
                        },
                    },
                ],
            )

            snapshot = build_meta_optimizer_snapshot(base_dir, last_n=100)
            previous_route = next(stats for stats in snapshot.route_stats if stats.route_name == "local-codex")

            self.assertEqual(previous_route.fallback_trigger_count, 1)
            self.assertAlmostEqual(previous_route.total_cost, 0.25)
            self.assertEqual(previous_route.cost_samples, [0.0, 0.25])
            self.assertAlmostEqual(previous_route.average_cost(), 0.25)

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
                            "task_family": "execution",
                            "latency_ms": 3,
                            "token_cost": 0.0,
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
