from __future__ import annotations

import json
from pathlib import Path

from swallow.orchestration import subtask_flow
from swallow.orchestration.models import ExecutorResult
from swallow.orchestration.review_gate import ReviewGateResult
from swallow.orchestration.subtask_orchestrator import SubtaskRunRecord
from swallow.surface_tools.paths import artifacts_dir


def _record() -> SubtaskRunRecord:
    return SubtaskRunRecord(
        card_id="card-1",
        subtask_index=2,
        goal="Write subtask artifact",
        depends_on=["card-0"],
        status="completed",
        executor_result=ExecutorResult(
            executor_name="mock",
            status="completed",
            message="done",
            output="executor output",
            prompt="executor prompt",
            stdout="stdout text",
            stderr="stderr text",
            dialect="markdown",
        ),
        review_gate_result=ReviewGateResult(
            status="passed",
            message="Review passed.",
            checks=[{"name": "output", "passed": True, "detail": "ok"}],
        ),
    )


def test_write_subtask_attempt_artifacts_preserves_attempt_file_names(tmp_path: Path) -> None:
    subtask_flow.write_subtask_attempt_artifacts(
        tmp_path,
        "parent-task",
        _record(),
        attempt_number=3,
        extra_artifacts={"custom_trace.md": "trace"},
    )

    root = artifacts_dir(tmp_path, "parent-task")
    prefix = "subtask_2_attempt3"
    assert (root / f"{prefix}_executor_prompt.md").read_text(
        encoding="utf-8"
    ) == "dialect: markdown\n\nexecutor prompt\n"
    assert (root / f"{prefix}_executor_output.md").read_text(encoding="utf-8") == "executor output\n"
    assert (root / f"{prefix}_executor_stdout.txt").read_text(encoding="utf-8") == "stdout text\n"
    assert (root / f"{prefix}_executor_stderr.txt").read_text(encoding="utf-8") == "stderr text\n"
    assert (root / f"{prefix}_custom_trace.md").read_text(encoding="utf-8") == "trace\n"
    review_payload = json.loads((root / f"{prefix}_review_gate.json").read_text(encoding="utf-8"))
    assert review_payload["status"] == "passed"


def test_collect_subtask_extra_artifacts_ignores_standard_executor_artifacts(tmp_path: Path) -> None:
    root = artifacts_dir(tmp_path, "subtask-task")
    (root / "nested").mkdir(parents=True)
    (root / "executor_prompt.md").write_text("standard prompt", encoding="utf-8")
    (root / "executor_output.md").write_text("standard output", encoding="utf-8")
    (root / "custom_trace.md").write_text("trace", encoding="utf-8")
    (root / "nested" / "evidence.md").write_text("evidence", encoding="utf-8")

    extra_artifacts = subtask_flow.collect_subtask_extra_artifacts(tmp_path, "subtask-task")

    assert extra_artifacts == {
        "custom_trace.md": "trace",
        "nested__evidence.md": "evidence",
    }


def test_collect_subtask_attempt_artifact_refs_returns_stable_task_artifact_refs(tmp_path: Path) -> None:
    root = artifacts_dir(tmp_path, "parent-task")
    root.mkdir(parents=True)
    (root / "subtask_2_attempt3_executor_output.md").write_text("output", encoding="utf-8")
    (root / "subtask_2_attempt3_custom_trace.md").write_text("trace", encoding="utf-8")
    (root / "subtask_2_attempt2_executor_output.md").write_text("old output", encoding="utf-8")
    (root / "subtask_1_attempt3_executor_output.md").write_text("other subtask", encoding="utf-8")

    refs = subtask_flow.collect_subtask_attempt_artifact_refs(
        tmp_path,
        "parent-task",
        subtask_index=2,
        attempt_number=3,
    )

    assert refs == [
        ".swl/tasks/parent-task/artifacts/subtask_2_attempt3_custom_trace.md",
        ".swl/tasks/parent-task/artifacts/subtask_2_attempt3_executor_output.md",
    ]


def test_subtask_flow_module_has_no_control_plane_write_surface() -> None:
    source = Path(subtask_flow.__file__).read_text(encoding="utf-8")
    public_names = {name for name in dir(subtask_flow) if not name.startswith("_")}

    assert "save_state" not in source
    assert "append_event" not in source
    assert "orchestration.harness" not in source
    assert "orchestration.executor" not in source
    assert public_names.isdisjoint(
        {
            "create_task",
            "run_task",
            "run_task_async",
            "advance",
            "transition",
            "waiting_human",
        }
    )
