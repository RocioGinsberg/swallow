from __future__ import annotations

from pathlib import Path

from swallow.orchestration.orchestrator import create_task, load_state, run_task
from swallow.truth_governance.store import save_state
from tests.helpers.cli_runner import run_cli


def test_task_create_and_list_characterization_stdout_stderr_exit_code(tmp_path: Path) -> None:
    create_result = run_cli(
        tmp_path,
        "task",
        "create",
        "--title",
        "Focused CLI task",
        "--goal",
        "Freeze task create output before dispatch migration.",
        "--executor",
        "note-only",
        "--route-mode",
        "offline",
    )

    create_result.assert_success()
    assert create_result.stderr == ""
    task_id = create_result.stdout.strip()
    assert task_id
    state = load_state(tmp_path, task_id)
    assert state.title == "Focused CLI task"
    assert state.goal == "Freeze task create output before dispatch migration."
    assert state.executor_name == "note-only"
    assert state.route_mode == "offline"

    list_result = run_cli(tmp_path, "task", "list")

    list_result.assert_success()
    assert list_result.stderr == ""
    assert "task_id\tstatus\tphase\tattempt\tupdated_at\ttitle\tfocus=all" in list_result.stdout
    assert task_id in list_result.stdout
    assert "Focused CLI task" in list_result.stdout


def test_task_acknowledge_characterization_stdout_stderr_exit_code(tmp_path: Path) -> None:
    created = create_task(
        base_dir=tmp_path,
        title="Dispatch blocked task",
        goal="Allow operator acknowledgement from CLI.",
        workspace_root=tmp_path,
    )
    persisted = load_state(tmp_path, created.task_id)
    persisted.artifact_paths["task_semantics_json"] = "missing-artifact.md"
    save_state(tmp_path, persisted)
    blocked = run_task(tmp_path, created.task_id, executor_name="mock-remote")
    assert blocked.status == "dispatch_blocked"

    result = run_cli(tmp_path, "task", "acknowledge", created.task_id)

    result.assert_success()
    assert result.stderr == ""
    assert f"{created.task_id} dispatch_acknowledged" in result.stdout
    assert "status=running" in result.stdout
    assert "phase=retrieval" in result.stdout
    assert "dispatch_status=acknowledged" in result.stdout
