from __future__ import annotations

from pathlib import Path

from swallow.orchestration import artifact_writer
from swallow.orchestration.models import ExecutorResult, TaskState
from swallow.surface_tools.paths import artifacts_dir


def test_create_task_artifact_paths_preserve_initial_path_keys(tmp_path: Path) -> None:
    paths = artifact_writer.build_create_task_artifact_paths(tmp_path, "artifact-task")

    assert paths["task_semantics_json"].endswith(".swl/tasks/artifact-task/task_semantics.json")
    assert paths["task_semantics_report"].endswith(
        ".swl/tasks/artifact-task/artifacts/task_semantics_report.md"
    )
    assert paths["knowledge_decisions_json"].endswith(".swl/tasks/artifact-task/knowledge_decisions.jsonl")
    assert paths["canonical_registry_json"].endswith(".swl/canonical_knowledge/registry.jsonl")
    assert paths["canonical_reuse_eval_report"].endswith(
        ".swl/tasks/artifact-task/artifacts/canonical_reuse_eval_report.md"
    )
    assert paths["remote_handoff_contract_report"].endswith(
        ".swl/tasks/artifact-task/artifacts/remote_handoff_contract_report.md"
    )
    assert "executor_output" not in paths


def test_run_task_artifact_paths_preserve_executor_and_optional_subtask_paths(tmp_path: Path) -> None:
    single_card_paths = artifact_writer.build_run_task_artifact_paths(tmp_path, "artifact-task")
    multi_card_paths = artifact_writer.build_run_task_artifact_paths(
        tmp_path,
        "artifact-task",
        multi_card_plan=True,
    )

    assert single_card_paths["executor_prompt"].endswith(
        ".swl/tasks/artifact-task/artifacts/executor_prompt.md"
    )
    assert single_card_paths["executor_output"].endswith(
        ".swl/tasks/artifact-task/artifacts/executor_output.md"
    )
    assert single_card_paths["executor_stdout"].endswith(
        ".swl/tasks/artifact-task/artifacts/executor_stdout.txt"
    )
    assert single_card_paths["executor_stderr"].endswith(
        ".swl/tasks/artifact-task/artifacts/executor_stderr.txt"
    )
    assert single_card_paths["summary"].endswith(".swl/tasks/artifact-task/artifacts/summary.md")
    assert single_card_paths["retrieval_json"].endswith(".swl/tasks/artifact-task/retrieval.json")
    assert "subtask_summary" not in single_card_paths
    assert multi_card_paths["subtask_summary"].endswith(
        ".swl/tasks/artifact-task/artifacts/subtask_summary.md"
    )


def test_write_parent_executor_artifacts_preserves_file_names_and_side_effects(tmp_path: Path) -> None:
    state = TaskState(
        task_id="artifact-task",
        title="Artifacts",
        goal="Write parent executor artifacts",
        workspace_root=str(tmp_path),
        route_dialect="markdown",
    )
    executor_result = ExecutorResult(
        executor_name="mock",
        status="completed",
        message="done",
        output="executor output",
        prompt="executor prompt",
        dialect="",
        stdout="stdout text",
        stderr="stderr text",
        side_effects={"relation_suggestions": []},
    )

    artifact_writer.write_parent_executor_artifacts(tmp_path, state, executor_result)

    root = artifacts_dir(tmp_path, state.task_id)
    assert (root / "executor_prompt.md").read_text(encoding="utf-8") == "dialect: markdown\n\nexecutor prompt\n"
    assert (root / "executor_output.md").read_text(encoding="utf-8") == "executor output\n"
    assert (root / "executor_stdout.txt").read_text(encoding="utf-8") == "stdout text\n"
    assert (root / "executor_stderr.txt").read_text(encoding="utf-8") == "stderr text\n"
    assert "relation_suggestions" in (root / "executor_side_effects.json").read_text(encoding="utf-8")


def test_write_prefixed_executor_artifacts_copies_only_executor_stream_files(tmp_path: Path) -> None:
    root = artifacts_dir(tmp_path, "artifact-task")
    root.mkdir(parents=True)
    (root / "executor_prompt.md").write_text("prompt", encoding="utf-8")
    (root / "executor_output.md").write_text("output", encoding="utf-8")
    (root / "executor_stdout.txt").write_text("stdout", encoding="utf-8")
    (root / "executor_stderr.txt").write_text("stderr", encoding="utf-8")
    (root / "summary.md").write_text("summary", encoding="utf-8")

    written = artifact_writer.write_prefixed_executor_artifacts(
        tmp_path,
        "artifact-task",
        prefix="fallback_primary",
    )

    assert written == [
        "fallback_primary_executor_prompt.md",
        "fallback_primary_executor_output.md",
        "fallback_primary_executor_stdout.txt",
        "fallback_primary_executor_stderr.txt",
    ]
    assert (root / "fallback_primary_executor_prompt.md").read_text(encoding="utf-8") == "prompt\n"
    assert (root / "fallback_primary_executor_output.md").read_text(encoding="utf-8") == "output\n"
    assert not (root / "fallback_primary_summary.md").exists()


def test_artifact_writer_module_has_no_control_plane_write_surface() -> None:
    source = Path(artifact_writer.__file__).read_text(encoding="utf-8")
    public_names = {name for name in dir(artifact_writer) if not name.startswith("_")}

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
