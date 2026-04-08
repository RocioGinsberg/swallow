from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import Event, RetrievalItem, TaskState, ValidationResult, utc_now
from .paths import (
    artifacts_dir,
    compatibility_path,
    dispatch_path,
    execution_fit_path,
    events_path,
    handoff_path,
    memory_path,
    retrieval_path,
    route_path,
    state_path,
    task_root,
    tasks_root,
    topology_path,
    validation_path,
)


def ensure_task_layout(base_dir: Path, task_id: str) -> None:
    task_root(base_dir, task_id).mkdir(parents=True, exist_ok=True)
    artifacts_dir(base_dir, task_id).mkdir(parents=True, exist_ok=True)
    tasks_root(base_dir).mkdir(parents=True, exist_ok=True)


def save_state(base_dir: Path, state: TaskState) -> None:
    ensure_task_layout(base_dir, state.task_id)
    state.updated_at = utc_now()
    state_path(base_dir, state.task_id).write_text(
        json.dumps(state.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )


def load_state(base_dir: Path, task_id: str) -> TaskState:
    data = json.loads(state_path(base_dir, task_id).read_text(encoding="utf-8"))
    return TaskState.from_dict(data)


def iter_task_states(base_dir: Path) -> Iterable[TaskState]:
    root = tasks_root(base_dir)
    if not root.exists():
        return []

    states: list[TaskState] = []
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        state_file = entry / "state.json"
        if not state_file.exists():
            continue
        data = json.loads(state_file.read_text(encoding="utf-8"))
        states.append(TaskState.from_dict(data))
    return states


def append_event(base_dir: Path, event: Event) -> None:
    ensure_task_layout(base_dir, event.task_id)
    with events_path(base_dir, event.task_id).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event.to_dict()) + "\n")


def save_retrieval(base_dir: Path, task_id: str, items: list[RetrievalItem]) -> None:
    ensure_task_layout(base_dir, task_id)
    payload = [item.to_dict() for item in items]
    retrieval_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_validation(base_dir: Path, task_id: str, result: ValidationResult) -> None:
    ensure_task_layout(base_dir, task_id)
    validation_path(base_dir, task_id).write_text(
        json.dumps(result.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )


def save_compatibility(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    compatibility_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_memory(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    memory_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_route(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    route_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_topology(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    topology_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_dispatch(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    dispatch_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_handoff(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    handoff_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_execution_fit(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    execution_fit_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def write_artifact(base_dir: Path, task_id: str, name: str, content: str) -> Path:
    ensure_task_layout(base_dir, task_id)
    path = artifacts_dir(base_dir, task_id) / name
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return path
