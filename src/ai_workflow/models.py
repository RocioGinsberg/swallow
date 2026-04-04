from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass(slots=True)
class TaskState:
    task_id: str
    title: str
    goal: str
    workspace_root: str
    status: str = "created"
    phase: str = "intake"
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    retrieval_count: int = 0
    executor_name: str = "codex"
    executor_status: str = "pending"
    artifact_paths: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskState":
        return cls(**data)


@dataclass(slots=True)
class Event:
    task_id: str
    event_type: str
    message: str
    created_at: str = field(default_factory=utc_now)
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RetrievalItem:
    path: str
    source_type: str
    score: int
    preview: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExecutorResult:
    executor_name: str
    status: str
    message: str
    output: str = ""
    prompt: str = ""
    failure_kind: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
