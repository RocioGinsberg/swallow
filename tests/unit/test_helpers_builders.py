from __future__ import annotations

from tests.helpers.assertions import assert_file_exists, assert_jsonl_event_kind
from tests.helpers.builders import KnowledgeBuilder, TaskBuilder, WorkspaceBuilder
from tests.helpers.workspace import read_json


def test_workspace_builder_writes_text_json_and_jsonl(tmp_path) -> None:
    workspace = WorkspaceBuilder(tmp_path)

    note_path = workspace.write_text("notes/source.md", "# Source\n")
    json_path = workspace.write_json(".swl/tasks/demo/state.json", {"task_id": "demo"})
    events_path = workspace.write_jsonl(
        ".swl/tasks/demo/events.jsonl",
        [{"event_type": "task.created", "payload": {"task_id": "demo"}}],
    )

    assert note_path.read_text(encoding="utf-8") == "# Source\n"
    assert read_json(json_path) == {"task_id": "demo"}
    assert_jsonl_event_kind(events_path, "task.created")


def test_task_builder_creates_task_with_defaults(tmp_path) -> None:
    state = TaskBuilder(tmp_path).create(title="Helper task")

    assert state.title == "Helper task"
    assert state.goal == "Exercise Swallow task behavior."
    assert state.workspace_root == str(tmp_path)
    assert_file_exists(tmp_path / ".swl" / "tasks" / state.task_id / "state.json")


def test_knowledge_builder_submits_staged_candidate(tmp_path) -> None:
    candidate = KnowledgeBuilder(tmp_path).staged_candidate(
        text="Reusable staged knowledge.",
        source_task_id="task-builder",
        source_object_id="knowledge-1",
    )

    assert candidate.candidate_id.startswith("staged-")
    assert candidate.text == "Reusable staged knowledge."
    assert candidate.source_task_id == "task-builder"
    assert candidate.source_object_id == "knowledge-1"


def test_workspace_builder_delegates_task_and_knowledge_builders(tmp_path) -> None:
    workspace = WorkspaceBuilder(tmp_path)

    state = workspace.task(title="Delegated task")
    candidate = workspace.staged_candidate(source_task_id=state.task_id, text="Delegated knowledge.")

    assert state.title == "Delegated task"
    assert candidate.source_task_id == state.task_id
