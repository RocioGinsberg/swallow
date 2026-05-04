from __future__ import annotations

import json
from pathlib import Path

from swallow.provider_router.router import load_route_capability_profiles, load_route_weights, route_by_name
from swallow.application.infrastructure.paths import route_capabilities_path, route_weights_path
from tests.helpers.cli_runner import run_cli


def _write_events(task_dir: Path, records: list[dict[str, object]]) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "events.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


def _write_route_weight_signal(base_dir: Path) -> None:
    _write_events(
        base_dir / ".swl" / "tasks" / "cli-route-weight-task",
        [
            {
                "task_id": "cli-route-weight-task",
                "event_type": "executor.failed",
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
                "task_id": "cli-route-weight-task",
                "event_type": "executor.failed",
                "message": "Primary route failed again.",
                "payload": {
                    "physical_route": "local-codex",
                    "logical_model": "codex",
                    "task_family": "execution",
                    "latency_ms": 10,
                    "token_cost": 0.0,
                    "degraded": False,
                    "failure_kind": "launch_error",
                    "error_code": "launch_error",
                },
            },
            {
                "task_id": "cli-route-weight-task",
                "event_type": "executor.completed",
                "message": "Primary route recovered once.",
                "payload": {
                    "physical_route": "local-codex",
                    "logical_model": "codex",
                    "task_family": "execution",
                    "latency_ms": 8,
                    "token_cost": 0.0,
                    "degraded": False,
                    "error_code": "",
                },
            },
        ],
    )


def test_route_weights_show_apply_characterization_stdout_stderr_exit_code(tmp_path: Path) -> None:
    route = route_by_name("local-codex")
    assert route is not None
    original_weight = route.quality_weight
    try:
        show_before = run_cli(tmp_path, "route", "weights", "show")
        show_before.assert_success()
        assert show_before.stderr == ""
        assert "# Route Quality Weights" in show_before.stdout
        assert "local-codex:" in show_before.stdout

        _write_route_weight_signal(tmp_path)
        optimize_result = run_cli(tmp_path, "meta-optimize", "--last-n", "100")
        optimize_result.assert_success()
        artifact_path = next(
            line.removeprefix("artifact: ").strip()
            for line in optimize_result.stdout.splitlines()
            if line.startswith("artifact: ")
        )

        apply_result = run_cli(tmp_path, "route", "weights", "apply", artifact_path)

        apply_result.assert_success()
        assert apply_result.stderr == ""
        assert "# Route Quality Weights" in apply_result.stdout
        assert "local-codex: 0.330000" in apply_result.stdout
        assert load_route_weights(tmp_path)["local-codex"] == 0.33
        assert not route_weights_path(tmp_path).exists()

        show_after = run_cli(tmp_path, "route", "weights", "show")
        show_after.assert_success()
        assert show_after.stderr == ""
        assert "local-codex: 0.330000" in show_after.stdout
    finally:
        route.quality_weight = original_weight


def test_route_capabilities_show_update_characterization_stdout_stderr_exit_code(tmp_path: Path) -> None:
    route = route_by_name("local-http")
    assert route is not None
    original_scores = dict(route.task_family_scores)
    original_unsupported = list(route.unsupported_task_types)
    try:
        show_before = run_cli(tmp_path, "route", "capabilities", "show")
        show_before.assert_success()
        assert show_before.stderr == ""
        assert "# Route Capability Profiles" in show_before.stdout
        assert "local-http" in show_before.stdout

        update_result = run_cli(
            tmp_path,
            "route",
            "capabilities",
            "update",
            "local-http",
            "--task-type",
            "review",
            "--score",
            "0.75",
            "--mark-unsupported",
            "execution",
        )

        update_result.assert_success()
        assert update_result.stderr == ""
        assert "# Route Capability Profiles" in update_result.stdout
        assert "local-http" in update_result.stdout
        assert "task_family_scores: review=0.750000" in update_result.stdout
        assert "unsupported_task_types: execution" in update_result.stdout
        persisted = load_route_capability_profiles(tmp_path)
        assert persisted["local-http"]["task_family_scores"]["review"] == 0.75
        assert persisted["local-http"]["unsupported_task_types"] == ["execution"]
        assert not route_capabilities_path(tmp_path).exists()

        show_after = run_cli(tmp_path, "route", "capabilities", "show")
        show_after.assert_success()
        assert show_after.stderr == ""
        assert "task_family_scores: review=0.750000" in show_after.stdout
    finally:
        route.task_family_scores = original_scores
        route.unsupported_task_types = original_unsupported
