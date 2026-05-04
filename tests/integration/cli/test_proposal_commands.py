from __future__ import annotations

import json
from pathlib import Path

from swallow.provider_router.router import load_route_weights, route_by_name
from swallow.application.services.meta_optimizer import load_optimization_proposal_bundle
from swallow.application.infrastructure.paths import latest_optimization_proposal_bundle_path, route_weights_path
from tests.helpers.cli_runner import run_cli


def _write_events(task_dir: Path, records: list[dict[str, object]]) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "events.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


def test_proposal_review_apply_characterization_stdout_stderr_exit_code(tmp_path: Path) -> None:
    route = route_by_name("local-codex")
    assert route is not None
    original_weight = route.quality_weight
    try:
        _write_events(
            tmp_path / ".swl" / "tasks" / "cli-proposal-task",
            [
                {
                    "task_id": "cli-proposal-task",
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
                    "task_id": "cli-proposal-task",
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
        optimize_result = run_cli(tmp_path, "meta-optimize", "--last-n", "100")
        optimize_result.assert_success()

        bundle_path = latest_optimization_proposal_bundle_path(tmp_path)
        bundle = load_optimization_proposal_bundle(bundle_path)
        route_weight = next(
            proposal
            for proposal in bundle.proposals
            if proposal.proposal_type == "route_weight" and proposal.route_name == "local-codex"
        )

        review_result = run_cli(
            tmp_path,
            "proposal",
            "review",
            str(bundle_path),
            "--decision",
            "approved",
            "--proposal-id",
            route_weight.proposal_id,
            "--note",
            "CLI review approval.",
        )

        review_result.assert_success()
        assert review_result.stderr == ""
        assert "# Proposal Review Record" in review_result.stdout
        assert "review_id:" in review_result.stdout
        assert f"{route_weight.proposal_id}: decision=approved type=route_weight" in review_result.stdout
        review_record_path = next(
            line.removeprefix("record: ").strip()
            for line in review_result.stdout.splitlines()
            if line.startswith("record: ")
        )

        apply_result = run_cli(tmp_path, "proposal", "apply", review_record_path)

        apply_result.assert_success()
        assert apply_result.stderr == ""
        assert "# Proposal Application Record" in apply_result.stdout
        assert "applied_count: 1" in apply_result.stdout
        assert "noop_count: 0" in apply_result.stdout
        assert "skipped_count: 0" in apply_result.stdout
        assert "record: " in apply_result.stdout
        persisted_weights = load_route_weights(tmp_path)
        assert round(persisted_weights["local-codex"], 2) == round(route_weight.suggested_weight or 1.0, 2)
        assert not route_weights_path(tmp_path).exists()
    finally:
        route.quality_weight = original_weight
