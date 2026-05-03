from __future__ import annotations

import json
from pathlib import Path

from swallow.knowledge_retrieval.knowledge_plane import list_staged_knowledge as load_staged_candidates
from swallow.orchestration.orchestrator import create_task
from swallow.orchestration.models import ExecutorResult
from swallow.surface_tools.mps_policy_store import read_mps_policy
from swallow.surface_tools.paths import artifacts_dir, mps_policy_path
from tests.helpers.cli_runner import run_cli


def test_synthesis_policy_set_writes_mps_policy(tmp_path: Path) -> None:
    result = run_cli(
        tmp_path,
        "synthesis",
        "policy",
        "set",
        "--kind",
        "mps_round_limit",
        "--value",
        "3",
    )

    result.assert_success()
    assert "mps_round_limit: 3" in result.stdout
    assert read_mps_policy(tmp_path, "mps_round_limit") == 3
    assert not mps_policy_path(tmp_path).exists()


def test_synthesis_run_and_stage_characterization_stdout_stderr_exit_code(tmp_path: Path, monkeypatch) -> None:
    state = create_task(
        base_dir=tmp_path,
        title="MPS baseline",
        goal="Freeze synthesis run and stage behavior before CLI migration.",
        workspace_root=tmp_path,
    )
    config_path = tmp_path / "synthesis-config.json"
    config_path.write_text(
        json.dumps(
            {
                "config_id": "config-mps",
                "rounds": 1,
                "participants": [
                    {
                        "participant_id": "participant-1",
                        "role_prompt": "Consider the baseline route.",
                    }
                ],
                "arbiter": {
                    "participant_id": "arbiter",
                    "role_prompt": "Resolve the synthesis result.",
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    def _mock_http_executor(state, retrieval_items, prompt=None, **kwargs):
        del state, retrieval_items, kwargs
        return ExecutorResult(
            executor_name="http",
            status="completed",
            message="HTTP executor completed.",
            output=f"synthesized: {str(prompt or '').splitlines()[0]}",
        )

    monkeypatch.setattr("swallow.orchestration.synthesis.run_http_executor", _mock_http_executor)

    run_result = run_cli(tmp_path, "synthesis", "run", "--task", state.task_id, "--config", str(config_path))

    run_result.assert_success()
    assert run_result.stderr == ""
    assert f"{state.task_id} synthesis_completed config_id=config-mps" in run_result.stdout
    assert "artifact=" in run_result.stdout
    arbitration_path = artifacts_dir(tmp_path, state.task_id) / "synthesis_arbitration.json"
    assert arbitration_path.exists()

    stage_result = run_cli(tmp_path, "synthesis", "stage", "--task", state.task_id)

    stage_result.assert_success()
    assert stage_result.stderr == ""
    assert "synthesis_staged config_id=config-mps" in stage_result.stdout
    staged = load_staged_candidates(tmp_path)
    assert len(staged) == 1
    assert staged[0].source_kind == "synthesis"
    assert staged[0].source_object_id == "config-mps"
