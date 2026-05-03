from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from swallow.knowledge_retrieval.retrieval import ARTIFACTS_SOURCE_TYPE
from swallow.orchestration import retrieval_flow
from swallow.orchestration.models import (
    Event,
    ExecutorResult,
    RetrievalItem,
    RetrievalRequest,
    TaskState,
    ValidationResult,
)
from swallow.orchestration.orchestrator import run_task
from swallow.surface_tools.paths import retrieval_path


def _task_state(**overrides: object) -> TaskState:
    fields: dict[str, object] = {
        "task_id": "retrieval-flow-test",
        "title": "Retrieval flow",
        "goal": "Preserve source policy",
        "workspace_root": ".",
    }
    fields.update(overrides)
    return TaskState(**fields)


def _retrieval_item() -> RetrievalItem:
    return RetrievalItem(
        path="notes.md",
        source_type="notes",
        score=3,
        preview="retrieval flow",
    )


def _write_retrieval_payload(base_dir: Path, task_id: str, payload: object) -> None:
    path = retrieval_path(base_dir, task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _validation_tuple() -> tuple[ValidationResult, ...]:
    return (
        ValidationResult(status="passed", message="Compatibility passed."),
        ValidationResult(status="passed", message="Execution fit passed."),
        ValidationResult(status="passed", message="Knowledge policy passed."),
        ValidationResult(status="passed", message="Validation passed."),
        ValidationResult(status="passed", message="Retry policy passed."),
        ValidationResult(status="passed", message="Execution budget policy passed."),
        ValidationResult(status="warning", message="Stop policy warning."),
    )


def test_retrieval_request_uses_knowledge_only_for_autonomous_cli_coding_routes() -> None:
    state = _task_state(
        route_executor_family="cli",
        route_taxonomy_role="general-executor",
        route_capabilities={
            "execution_kind": "code_execution",
            "supports_tool_loop": True,
            "deterministic": False,
        },
    )

    request = retrieval_flow.build_task_retrieval_request(state)

    assert request.source_types == ["knowledge"]


def test_retrieval_request_keeps_api_routes_off_repo_by_default() -> None:
    state = _task_state(
        route_executor_family="api",
        route_taxonomy_role="general-executor",
        route_capabilities={"execution_kind": "model_call"},
    )

    request = retrieval_flow.build_task_retrieval_request(state)

    assert request.source_types == ["knowledge", "notes"]


def test_retrieval_request_preserves_legacy_local_fallback_sources() -> None:
    state = _task_state(
        route_executor_family="cli",
        route_taxonomy_role="general-executor",
        route_capabilities={
            "execution_kind": "script",
            "supports_tool_loop": False,
            "deterministic": True,
        },
    )

    request = retrieval_flow.build_task_retrieval_request(state)

    assert request.source_types == ["repo", "notes", "knowledge"]


def test_retrieval_request_prefers_explicit_source_override() -> None:
    state = _task_state(
        route_executor_family="cli",
        route_taxonomy_role="general-executor",
        route_capabilities={
            "execution_kind": "code_execution",
            "supports_tool_loop": True,
        },
        task_semantics={
            "retrieval_source_types": ["repo", "knowledge", "repo", ARTIFACTS_SOURCE_TYPE],
        },
    )

    request = retrieval_flow.build_task_retrieval_request(state)

    assert request.source_types == ["repo", "knowledge", ARTIFACTS_SOURCE_TYPE]


def test_retrieval_request_rejects_invalid_explicit_source_override() -> None:
    state = _task_state(task_semantics={"retrieval_source_types": ["repo", "unsupported-source"]})

    with pytest.raises(ValueError, match="Invalid retrieval source type"):
        retrieval_flow.build_task_retrieval_request(state)


def test_load_previous_retrieval_items_returns_none_for_missing_or_invalid_artifacts(tmp_path: Path) -> None:
    task_id = "previous-retrieval-invalid"

    assert retrieval_flow.load_previous_retrieval_items(tmp_path, task_id) is None

    path = retrieval_path(tmp_path, task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{", encoding="utf-8")
    assert retrieval_flow.load_previous_retrieval_items(tmp_path, task_id) is None

    _write_retrieval_payload(tmp_path, task_id, {"not": "a-list"})
    assert retrieval_flow.load_previous_retrieval_items(tmp_path, task_id) is None

    _write_retrieval_payload(tmp_path, task_id, ["not-a-dict"])
    assert retrieval_flow.load_previous_retrieval_items(tmp_path, task_id) is None

    _write_retrieval_payload(tmp_path, task_id, [{"path": "notes.md"}])
    assert retrieval_flow.load_previous_retrieval_items(tmp_path, task_id) is None


def test_load_previous_retrieval_items_returns_items_for_valid_artifact(tmp_path: Path) -> None:
    task_id = "previous-retrieval-valid"
    expected = _retrieval_item()
    _write_retrieval_payload(tmp_path, task_id, [expected.to_dict()])

    items = retrieval_flow.load_previous_retrieval_items(tmp_path, task_id)

    assert items == [expected]


def test_selective_retry_reruns_retrieval_when_previous_retrieval_artifact_is_invalid(tmp_path: Path) -> None:
    state = _task_state(
        task_id="selective-retry-invalid-retrieval",
        title="Selective retry",
        goal="Fall back to retrieval",
        workspace_root=str(tmp_path),
    )
    retrieval_path(tmp_path, state.task_id).parent.mkdir(parents=True, exist_ok=True)
    retrieval_path(tmp_path, state.task_id).write_text("{", encoding="utf-8")
    retrieval_items = [_retrieval_item()]
    executor_result = ExecutorResult(
        executor_name="mock",
        status="completed",
        message="Execution finished.",
        output="done",
    )
    captured_events: list[Event] = []
    captured_requests: list[RetrievalRequest] = []

    def run_retrieval_spy(
        _base_dir: Path,
        _state: TaskState,
        request: RetrievalRequest,
    ) -> list[RetrievalItem]:
        captured_requests.append(request)
        return retrieval_items

    def append_event_spy(_base_dir: Path, event: Event) -> None:
        captured_events.append(event)

    with patch("swallow.orchestration.orchestrator.load_state", return_value=state):
        with patch("swallow.orchestration.orchestrator.save_state"):
            with patch("swallow.orchestration.orchestrator.append_event", side_effect=append_event_spy):
                with patch("swallow.orchestration.orchestrator.run_retrieval", side_effect=run_retrieval_spy):
                    with patch("swallow.orchestration.orchestrator._execute_task_card", return_value=executor_result):
                        with patch(
                            "swallow.orchestration.orchestrator.write_task_artifacts",
                            return_value=_validation_tuple(),
                        ):
                            run_task(tmp_path, state.task_id, skip_to_phase="execution")

    assert len(captured_requests) == 1
    assert any(event.event_type == "task.phase_recovery_fallback" for event in captured_events)
    assert any(
        event.event_type == "task.phase_checkpoint"
        and event.payload.get("execution_phase") == "retrieval_done"
        and event.payload.get("skipped") is False
        and event.payload.get("source") == "live_retrieval"
        for event in captured_events
    )


def test_retrieval_flow_module_has_no_control_plane_write_surface() -> None:
    source = Path(retrieval_flow.__file__).read_text(encoding="utf-8")
    public_names = {name for name in dir(retrieval_flow) if not name.startswith("_")}

    assert "save_state" not in source
    assert "orchestration.harness" not in source
    assert "orchestration.executor" not in source
    assert "state_transitioned" not in source
    assert "entered_waiting_human" not in source
    assert public_names.isdisjoint(
        {
            "create_task",
            "run_task",
            "run_task_async",
            "advance",
            "transition",
            "waiting_human",
        }
    )
