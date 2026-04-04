from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from .harness import run_harness, write_task_artifacts
from .models import Event, TaskState
from .paths import artifacts_dir
from .store import append_event, load_state, save_state


def create_task(base_dir: Path, title: str, goal: str, workspace_root: Path) -> TaskState:
    task_id = uuid4().hex[:12]
    state = TaskState(
        task_id=task_id,
        title=title,
        goal=goal,
        workspace_root=str(workspace_root.resolve()),
    )
    save_state(base_dir, state)
    append_event(
        base_dir,
        Event(task_id=task_id, event_type="task.created", message="Task created."),
    )
    return state


def run_task(base_dir: Path, task_id: str) -> TaskState:
    state = load_state(base_dir, task_id)
    state.executor_name = "codex"
    state.executor_status = "running"

    state.phase = "retrieval"
    state.status = "running"
    save_state(base_dir, state)
    append_event(
        base_dir,
        Event(task_id=task_id, event_type="task.phase", message="Entering retrieval phase."),
    )

    state.phase = "executing"
    save_state(base_dir, state)
    append_event(
        base_dir,
        Event(task_id=task_id, event_type="task.phase", message="Entering execution phase."),
    )

    retrieval_items, executor_result = run_harness(base_dir, state)
    state.retrieval_count = len(retrieval_items)
    state.executor_name = executor_result.executor_name
    state.executor_status = executor_result.status
    state.phase = "summarize"
    save_state(base_dir, state)
    append_event(
        base_dir,
        Event(task_id=task_id, event_type="task.phase", message="Entering summarize phase."),
    )

    state.phase = "completed" if executor_result.status == "completed" else "failed"
    state.status = "completed" if executor_result.status == "completed" else "failed"
    state.artifact_paths = {
        "executor_prompt": str((artifacts_dir(base_dir, task_id) / "executor_prompt.md").resolve()),
        "executor_output": str((artifacts_dir(base_dir, task_id) / "executor_output.md").resolve()),
        "summary": str((artifacts_dir(base_dir, task_id) / "summary.md").resolve()),
        "handoff": str((artifacts_dir(base_dir, task_id) / "handoff.md").resolve()),
    }
    write_task_artifacts(base_dir, state, retrieval_items, executor_result)
    save_state(base_dir, state)
    append_event(
        base_dir,
        Event(
            task_id=task_id,
            event_type="task.completed" if state.status == "completed" else "task.failed",
            message="Task run completed." if state.status == "completed" else "Task run failed.",
        ),
    )
    return state
