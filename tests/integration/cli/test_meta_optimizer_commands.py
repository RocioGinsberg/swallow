from __future__ import annotations

import json
from pathlib import Path

from swallow.surface_tools.paths import latest_optimization_proposal_bundle_path, optimization_proposals_path
from tests.helpers.cli_runner import run_cli


def _write_events(task_dir: Path, records: list[dict[str, object]]) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "events.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


def test_meta_optimize_characterization_stdout_stderr_exit_code(tmp_path: Path) -> None:
    _write_events(
        tmp_path / ".swl" / "tasks" / "cli-meta-optimize-task",
        [
            {
                "task_id": "cli-meta-optimize-task",
                "event_type": "executor.failed",
                "message": "Local codex failed.",
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
                "task_id": "cli-meta-optimize-task",
                "event_type": "executor.failed",
                "message": "Local codex failed again.",
                "payload": {
                    "physical_route": "local-codex",
                    "logical_model": "codex",
                    "task_family": "execution",
                    "latency_ms": 9,
                    "token_cost": 0.0,
                    "degraded": False,
                    "failure_kind": "launch_error",
                    "error_code": "launch_error",
                },
            },
        ],
    )

    result = run_cli(tmp_path, "meta-optimize", "--last-n", "100")

    result.assert_success()
    assert result.stderr == ""
    assert "# Meta-Optimizer Proposals" in result.stdout
    assert "scanned_task_count: 1" in result.stdout
    assert "local-codex: success_rate=0%" in result.stdout
    assert "artifact: " in result.stdout
    assert f"proposal_bundle: {latest_optimization_proposal_bundle_path(tmp_path)}" in result.stdout
    assert optimization_proposals_path(tmp_path).exists()
    assert latest_optimization_proposal_bundle_path(tmp_path).exists()
