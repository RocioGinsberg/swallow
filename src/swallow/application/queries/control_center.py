from __future__ import annotations

from pathlib import Path

from swallow.truth_governance.store import iter_task_states, load_events, load_knowledge_objects, load_state


def _filter_task_states(states: list[object], focus: str) -> list[object]:
    if focus == "all":
        return states
    if focus == "active":
        return [state for state in states if state.status in {"created", "running"}]
    if focus == "failed":
        return [state for state in states if state.status == "failed"]
    if focus == "needs-review":
        return [
            state
            for state in states
            if state.status == "failed" or state.phase == "summarize" or state.executor_status != "completed"
        ]
    if focus == "recent":
        return states
    return states


def build_tasks_payload(base_dir: Path, focus: str = "all") -> dict[str, object]:
    states = sorted(
        iter_task_states(base_dir),
        key=lambda state: (state.updated_at, state.task_id),
        reverse=True,
    )
    filtered = _filter_task_states(states, focus)
    return {
        "focus": focus,
        "count": len(filtered),
        "tasks": [
            {
                "task_id": state.task_id,
                "title": state.title,
                "goal": state.goal,
                "status": state.status,
                "phase": state.phase,
                "updated_at": state.updated_at,
                "executor_name": state.executor_name,
                "route_name": state.route_name,
                "attempt_id": state.current_attempt_id,
                "attempt_number": state.current_attempt_number,
            }
            for state in filtered
        ],
    }


def build_task_payload(base_dir: Path, task_id: str) -> dict[str, object]:
    return load_state(base_dir, task_id).to_dict()


def build_task_events_payload(base_dir: Path, task_id: str) -> dict[str, object]:
    payload = load_events(base_dir, task_id)
    return {"task_id": task_id, "count": len(payload), "events": payload}


def build_task_knowledge_payload(base_dir: Path, task_id: str) -> dict[str, object]:
    payload = load_knowledge_objects(base_dir, task_id)
    return {"task_id": task_id, "count": len(payload), "knowledge_objects": payload}
