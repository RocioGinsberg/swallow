from __future__ import annotations

from tests.helpers.assertions import assert_file_exists, assert_jsonl_event_kind
from tests.helpers.builders import KnowledgeBuilder, TaskBuilder, WorkspaceBuilder
from tests.helpers.workspace import read_json


def test_workspace_builder_writes_text_json_and_jsonl(workspace_builder: WorkspaceBuilder) -> None:
    note_path = workspace_builder.write_text("notes/source.md", "# Source\n")
    json_path = workspace_builder.write_json(".swl/tasks/demo/state.json", {"task_id": "demo"})
    events_path = workspace_builder.write_jsonl(
        ".swl/tasks/demo/events.jsonl",
        [{"event_type": "task.created", "payload": {"task_id": "demo"}}],
    )

    assert note_path.read_text(encoding="utf-8") == "# Source\n"
    assert read_json(json_path) == {"task_id": "demo"}
    assert_jsonl_event_kind(events_path, "task.created")


def test_task_builder_creates_task_with_defaults(task_builder: TaskBuilder) -> None:
    state = task_builder.create(title="Helper task")

    assert state.title == "Helper task"
    assert state.goal == "Exercise Swallow task behavior."
    assert state.workspace_root == str(task_builder.base_dir)
    assert_file_exists(task_builder.base_dir / ".swl" / "tasks" / state.task_id / "state.json")


def test_knowledge_builder_submits_staged_candidate(knowledge_builder: KnowledgeBuilder) -> None:
    candidate = knowledge_builder.staged_candidate(
        text="Reusable staged knowledge.",
        source_task_id="task-builder",
        source_object_id="knowledge-1",
    )

    assert candidate.candidate_id.startswith("staged-")
    assert candidate.text == "Reusable staged knowledge."
    assert candidate.source_task_id == "task-builder"
    assert candidate.source_object_id == "knowledge-1"


def test_workspace_builder_delegates_task_and_knowledge_builders(workspace_builder: WorkspaceBuilder) -> None:
    state = workspace_builder.task(title="Delegated task")
    candidate = workspace_builder.staged_candidate(source_task_id=state.task_id, text="Delegated knowledge.")

    assert state.title == "Delegated task"
    assert candidate.source_task_id == state.task_id
