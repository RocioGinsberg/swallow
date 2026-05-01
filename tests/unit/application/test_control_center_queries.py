from __future__ import annotations

from pathlib import Path

from swallow.application.queries.control_center import (
    build_task_events_payload,
    build_task_knowledge_payload,
    build_task_payload,
    build_tasks_payload,
)
from swallow.orchestration.models import Event
from swallow.orchestration.orchestrator import create_task
from swallow.truth_governance.store import append_event, load_state, save_knowledge_objects, save_state


def test_control_center_queries_build_task_read_models(tmp_path: Path) -> None:
    created = create_task(
        base_dir=tmp_path,
        title="Application query task",
        goal="Expose control center read models from application layer",
        workspace_root=tmp_path,
        executor_name="local",
    )
    state = load_state(tmp_path, created.task_id)
    state.status = "running"
    save_state(tmp_path, state)
    append_event(
        tmp_path,
        Event(
            task_id=created.task_id,
            event_type="task.test_event",
            message="application query event",
            payload={"kind": "query"},
        ),
    )
    save_knowledge_objects(
        tmp_path,
        created.task_id,
        [
            {
                "object_id": "knowledge-0001",
                "text": "Application query knowledge",
                "stage": "verified",
                "evidence_status": "artifact_backed",
                "artifact_ref": ".swl/tasks/demo/artifacts/evidence.md",
            }
        ],
    )

    tasks_payload = build_tasks_payload(tmp_path, focus="active")
    task_payload = build_task_payload(tmp_path, created.task_id)
    events_payload = build_task_events_payload(tmp_path, created.task_id)
    knowledge_payload = build_task_knowledge_payload(tmp_path, created.task_id)

    assert tasks_payload["focus"] == "active"
    assert tasks_payload["count"] == 1
    assert tasks_payload["tasks"][0]["task_id"] == created.task_id
    assert task_payload["task_id"] == created.task_id
    assert task_payload["status"] == "running"
    assert events_payload["count"] == 2
    assert events_payload["events"][-1]["event_type"] == "task.test_event"
    assert knowledge_payload["count"] == 1
    assert knowledge_payload["knowledge_objects"][0]["object_id"] == "knowledge-0001"
