from __future__ import annotations

import json
from pathlib import Path

from swallow.orchestration.models import ExecutorResult
from swallow.orchestration.subtask_orchestrator import SubtaskRunRecord
from swallow.surface_tools.paths import artifacts_dir
from swallow.truth_governance.store import write_artifact


STANDARD_SUBTASK_ARTIFACT_NAMES = {
    "executor_prompt.md",
    "executor_output.md",
    "executor_stdout.txt",
    "executor_stderr.txt",
}


def write_subtask_attempt_artifacts(
    base_dir: Path,
    task_id: str,
    record: SubtaskRunRecord,
    *,
    attempt_number: int,
    extra_artifacts: dict[str, str] | None = None,
) -> None:
    executor_result = record.executor_result or ExecutorResult(
        executor_name="subtask-orchestrator",
        status="failed",
        message="Missing subtask executor result.",
    )
    review_gate_result = record.review_gate_result
    prompt_with_dialect = f"dialect: {executor_result.dialect or 'plain_text'}\n\n{executor_result.prompt}"
    prefix = f"subtask_{record.subtask_index}_attempt{attempt_number}"
    write_artifact(base_dir, task_id, f"{prefix}_executor_prompt.md", prompt_with_dialect)
    write_artifact(
        base_dir,
        task_id,
        f"{prefix}_executor_output.md",
        executor_result.output or executor_result.message or "(no executor output)",
    )
    write_artifact(base_dir, task_id, f"{prefix}_executor_stdout.txt", executor_result.stdout or "")
    write_artifact(base_dir, task_id, f"{prefix}_executor_stderr.txt", executor_result.stderr or "")
    if review_gate_result is not None:
        write_artifact(
            base_dir,
            task_id,
            f"{prefix}_review_gate.json",
            json.dumps(review_gate_result.to_dict(), indent=2),
        )
    for artifact_name, content in sorted((extra_artifacts or {}).items()):
        write_artifact(base_dir, task_id, f"{prefix}_{artifact_name}", content)


def collect_subtask_extra_artifacts(
    subtask_base_dir: Path,
    task_id: str,
) -> dict[str, str]:
    subtask_artifacts_dir = artifacts_dir(subtask_base_dir, task_id)
    if not subtask_artifacts_dir.exists():
        return {}

    extra_artifacts: dict[str, str] = {}
    for artifact_path in sorted(subtask_artifacts_dir.rglob("*")):
        if not artifact_path.is_file():
            continue
        relative_name = artifact_path.relative_to(subtask_artifacts_dir).as_posix().replace("/", "__")
        if relative_name in STANDARD_SUBTASK_ARTIFACT_NAMES:
            continue
        extra_artifacts[relative_name] = artifact_path.read_text(encoding="utf-8", errors="replace")
    return extra_artifacts


def subtask_artifact_ref(task_id: str, artifact_name: str) -> str:
    return f".swl/tasks/{task_id}/artifacts/{artifact_name}"


def collect_subtask_attempt_artifact_refs(
    base_dir: Path,
    task_id: str,
    *,
    subtask_index: int,
    attempt_number: int,
) -> list[str]:
    artifact_root = artifacts_dir(base_dir, task_id)
    if not artifact_root.exists():
        return []

    prefix = f"subtask_{subtask_index}_attempt{attempt_number}_"
    artifact_names = sorted(
        path.relative_to(artifact_root).as_posix()
        for path in artifact_root.glob(f"{prefix}*")
        if path.is_file()
    )
    return [subtask_artifact_ref(task_id, artifact_name) for artifact_name in artifact_names]
