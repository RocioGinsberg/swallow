from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from swallow.knowledge_retrieval.knowledge_plane import StagedCandidate, submit_staged_knowledge
from swallow.orchestration.models import TaskState
from swallow.orchestration.orchestrator import create_task


@dataclass(slots=True)
class WorkspaceBuilder:
    base_dir: Path

    def path(self, relative_path: str | Path) -> Path:
        path = Path(relative_path)
        if path.is_absolute():
            return path
        return self.base_dir / path

    def write_text(self, relative_path: str | Path, content: str) -> Path:
        path = self.path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_json(self, relative_path: str | Path, payload: object) -> Path:
        return self.write_text(
            relative_path,
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
        )

    def write_jsonl(self, relative_path: str | Path, records: list[dict[str, object]]) -> Path:
        return self.write_text(
            relative_path,
            "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        )

    def task(self, **overrides: Any) -> TaskState:
        return TaskBuilder(self.base_dir).create(**overrides)

    def staged_candidate(self, **overrides: Any) -> StagedCandidate:
        return KnowledgeBuilder(self.base_dir).staged_candidate(**overrides)


@dataclass(slots=True)
class TaskBuilder:
    base_dir: Path
    title: str = "Test task"
    goal: str = "Exercise Swallow task behavior."
    executor_name: str = "aider"
    route_mode: str = "auto"
    workspace_root: Path | None = None
    input_context: dict[str, object] | None = None
    constraints: list[str] | None = None
    acceptance_criteria: list[str] | None = None

    def create(self, **overrides: Any) -> TaskState:
        params: dict[str, Any] = {
            "base_dir": self.base_dir,
            "title": self.title,
            "goal": self.goal,
            "workspace_root": self.workspace_root or self.base_dir,
            "executor_name": self.executor_name,
            "route_mode": self.route_mode,
            "input_context": self.input_context,
            "constraints": self.constraints,
            "acceptance_criteria": self.acceptance_criteria,
        }
        params.update(overrides)
        return create_task(**params)


@dataclass(slots=True)
class KnowledgeBuilder:
    base_dir: Path
    source_task_id: str = "task-test"
    submitted_by: str = "integration-test"
    default_metadata: dict[str, object] = field(default_factory=dict)

    def staged_candidate(self, **overrides: Any) -> StagedCandidate:
        params: dict[str, Any] = {
            "candidate_id": "",
            "text": "Staged knowledge candidate.",
            "source_task_id": self.source_task_id,
            "submitted_by": self.submitted_by,
        }
        params.update(self.default_metadata)
        params.update(overrides)
        return submit_staged_knowledge(self.base_dir, StagedCandidate(**params))
