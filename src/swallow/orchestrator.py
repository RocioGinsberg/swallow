from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from .executor import normalize_executor_name
from .harness import run_execution, run_retrieval, write_task_artifacts
from .models import Event, RetrievalRequest, TaskState
from .paths import artifacts_dir, memory_path, validation_path
from .retrieval import build_retrieval_request
from .store import append_event, load_state, save_state


def create_task(
    base_dir: Path,
    title: str,
    goal: str,
    workspace_root: Path,
    executor_name: str = "codex",
) -> TaskState:
    task_id = uuid4().hex[:12]
    state = TaskState(
        task_id=task_id,
        title=title,
        goal=goal,
        workspace_root=str(workspace_root.resolve()),
        executor_name=normalize_executor_name(executor_name),
    )
    save_state(base_dir, state)
    append_event(
        base_dir,
        Event(
            task_id=task_id,
            event_type="task.created",
            message="Task created.",
            payload={
                "status": state.status,
                "phase": state.phase,
                "workspace_root": state.workspace_root,
                "executor_name": state.executor_name,
            },
        ),
    )
    return state


def _set_phase(base_dir: Path, state: TaskState, phase: str) -> None:
    state.phase = phase
    save_state(base_dir, state)
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="task.phase",
            message=f"Entering {phase} phase.",
            payload={
                "phase": state.phase,
                "status": state.status,
                "executor_status": state.executor_status,
            },
        ),
    )


def build_task_retrieval_request(state: TaskState) -> RetrievalRequest:
    return build_retrieval_request(
        query=f"{state.title} {state.goal}".strip(),
        source_types=["repo", "notes"],
        context_layers=["workspace", "task"],
        limit=8,
        strategy="system_baseline",
    )


def run_task(base_dir: Path, task_id: str, executor_name: str | None = None) -> TaskState:
    state = load_state(base_dir, task_id)
    previous_status = state.status
    previous_phase = state.phase
    selected_executor = normalize_executor_name(executor_name or state.executor_name)
    state.executor_name = selected_executor
    state.executor_status = "running"
    state.status = "running"
    state.phase = "intake"
    save_state(base_dir, state)
    append_event(
        base_dir,
        Event(
            task_id=task_id,
            event_type="task.run_started",
            message="Task run started.",
            payload={
                "previous_status": previous_status,
                "previous_phase": previous_phase,
                "status": state.status,
                "phase": state.phase,
                "executor_name": state.executor_name,
                "executor_status": state.executor_status,
            },
        ),
    )

    retrieval_request = build_task_retrieval_request(state)
    _set_phase(base_dir, state, "retrieval")
    retrieval_items = run_retrieval(base_dir, state, retrieval_request)
    state.retrieval_count = len(retrieval_items)

    _set_phase(base_dir, state, "executing")
    executor_result = run_execution(base_dir, state, retrieval_items)
    state.executor_name = executor_result.executor_name
    state.executor_status = executor_result.status
    save_state(base_dir, state)

    _set_phase(base_dir, state, "summarize")
    state.artifact_paths = {
        "executor_prompt": str((artifacts_dir(base_dir, task_id) / "executor_prompt.md").resolve()),
        "executor_output": str((artifacts_dir(base_dir, task_id) / "executor_output.md").resolve()),
        "executor_stdout": str((artifacts_dir(base_dir, task_id) / "executor_stdout.txt").resolve()),
        "executor_stderr": str((artifacts_dir(base_dir, task_id) / "executor_stderr.txt").resolve()),
        "summary": str((artifacts_dir(base_dir, task_id) / "summary.md").resolve()),
        "resume_note": str((artifacts_dir(base_dir, task_id) / "resume_note.md").resolve()),
        "source_grounding": str((artifacts_dir(base_dir, task_id) / "source_grounding.md").resolve()),
        "validation_report": str((artifacts_dir(base_dir, task_id) / "validation_report.md").resolve()),
        "validation_json": str(validation_path(base_dir, task_id).resolve()),
        "task_memory": str(memory_path(base_dir, task_id).resolve()),
    }
    validation_result = write_task_artifacts(base_dir, replace(state), retrieval_items, executor_result)

    state.status = "completed" if executor_result.status == "completed" and validation_result.status != "failed" else "failed"
    save_state(base_dir, state)
    append_event(
        base_dir,
        Event(
            task_id=task_id,
            event_type="task.completed" if state.status == "completed" else "task.failed",
            message="Task run completed." if state.status == "completed" else "Task run failed.",
            payload={
                "status": state.status,
                "phase": state.phase,
                "retrieval_count": state.retrieval_count,
                "executor_name": state.executor_name,
                "executor_status": state.executor_status,
                "validation_status": validation_result.status,
                "artifact_paths": state.artifact_paths,
            },
        ),
    )
    return state
