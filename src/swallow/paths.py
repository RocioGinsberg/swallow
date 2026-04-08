from __future__ import annotations

from pathlib import Path


APP_DIR_NAME = ".swl"


def app_root(base_dir: Path) -> Path:
    return base_dir / APP_DIR_NAME


def tasks_root(base_dir: Path) -> Path:
    return app_root(base_dir) / "tasks"


def task_root(base_dir: Path, task_id: str) -> Path:
    return tasks_root(base_dir) / task_id


def artifacts_dir(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "artifacts"


def state_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "state.json"


def events_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "events.jsonl"


def retrieval_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "retrieval.json"


def validation_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "validation.json"


def compatibility_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "compatibility.json"


def memory_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "memory.json"


def route_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "route.json"
