from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from .harness import run_harness, write_task_artifacts
from .models import Event, TaskState
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

    retrieval_items = run_harness(base_dir, state)
    state.retrieval_count = len(retrieval_items)
    state.phase = "summarize"
    save_state(base_dir, state)
    append_event(
        base_dir,
        Event(task_id=task_id, event_type="task.phase", message="Entering summarize phase."),
    )

    state.phase = "completed"
    state.status = "completed"
    state.artifact_paths = {
        "summary": str((base_dir / ".aiwf" / "tasks" / task_id / "artifacts" / "summary.md").resolve()),
        "handoff": str((base_dir / ".aiwf" / "tasks" / task_id / "artifacts" / "handoff.md").resolve()),
    }
    write_task_artifacts(base_dir, state, retrieval_items)
    save_state(base_dir, state)
    append_event(
        base_dir,
        Event(task_id=task_id, event_type="task.completed", message="Task run completed."),
    )
    return state
