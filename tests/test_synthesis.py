from __future__ import annotations

import json

import pytest

from swallow.governance import OperatorToken, ProposalTarget, apply_proposal, register_mps_policy_proposal
from swallow.models import ExecutorResult, SynthesisConfig, SynthesisParticipant, TaskState
from swallow.paths import artifacts_dir
from swallow.store import load_events, load_state, save_state
from swallow.synthesis import run_synthesis


def _state() -> TaskState:
    return TaskState(
        task_id="task-mps",
        title="MPS test",
        goal="Synthesize multiple perspectives.",
        workspace_root=".",
        task_semantics={"source_kind": "planning", "goal": "Choose a path."},
    )


def _config(*, participant_count: int = 1, rounds: int = 1) -> SynthesisConfig:
    participants = tuple(
        SynthesisParticipant(
            participant_id=f"participant-{index}",
            role_prompt=f"Perspective {index}",
        )
        for index in range(1, participant_count + 1)
    )
    return SynthesisConfig(
        config_id="config-mps",
        participants=participants,
        rounds=rounds,
        arbiter=SynthesisParticipant(
            participant_id="arbiter",
            role_prompt="Arbitrate the participant artifacts.",
        ),
    )


def _mock_http_executor(state, retrieval_items, prompt=None, **kwargs):
    del retrieval_items, kwargs
    state.route_name = "http-qwen"
    return ExecutorResult(
        executor_name="http",
        status="completed",
        message="HTTP executor completed.",
        output=f"synthesized: {str(prompt or '').splitlines()[0]}",
    )


def test_mps_participants_within_policy_cap(tmp_path, monkeypatch) -> None:
    state = _state()
    save_state(tmp_path, state)
    register_mps_policy_proposal(
        base_dir=tmp_path,
        proposal_id="mps-limit",
        kind="mps_participant_limit",
        value=1,
    )
    apply_proposal("mps-limit", OperatorToken(source="cli"), ProposalTarget.POLICY)
    monkeypatch.setattr("swallow.synthesis.run_http_executor", _mock_http_executor)

    with pytest.raises(ValueError, match="exceed mps_participant_limit 1"):
        run_synthesis(tmp_path, state, _config(participant_count=2))


def test_mps_arbiter_artifact_required(tmp_path, monkeypatch) -> None:
    state = _state()
    save_state(tmp_path, state)
    monkeypatch.setattr("swallow.synthesis.run_http_executor", _mock_http_executor)

    result = run_synthesis(tmp_path, state, _config(participant_count=2, rounds=2))

    assert result.path == artifacts_dir(tmp_path, state.task_id) / "synthesis_arbitration.json"
    payload = json.loads(result.path.read_text(encoding="utf-8"))
    assert payload["schema"] == "synthesis_arbitration_v1"
    assert payload["config_id"] == "config-mps"
    assert payload["rounds_executed"] == 2
    assert payload["arbiter_decision"]["synthesis_summary"]
    assert len(payload["participants"]) == 2
    for participant in payload["participants"]:
        assert len(participant["round_artifacts"]) == 2

    events = load_events(tmp_path, state.task_id)
    mps_events = [event for event in events if event["event_type"] == "task.mps_completed"]
    assert len(mps_events) == 1
    assert mps_events[0]["payload"]["config_id"] == "config-mps"
    assert mps_events[0]["payload"]["arbitration_artifact_id"] == "synthesis_arbitration"
    assert load_state(tmp_path, state.task_id).status == "created"


def test_synthesis_run_rejects_if_arbitration_exists(tmp_path, monkeypatch) -> None:
    state = _state()
    save_state(tmp_path, state)
    monkeypatch.setattr("swallow.synthesis.run_http_executor", _mock_http_executor)
    config = _config()
    run_synthesis(tmp_path, state, config)

    with pytest.raises(RuntimeError, match="synthesis already completed"):
        run_synthesis(tmp_path, state, config)


def test_synthesis_does_not_mutate_main_task_state(tmp_path, monkeypatch) -> None:
    state = _state()
    before = {
        "route_name": state.route_name,
        "route_model_hint": state.route_model_hint,
        "route_transport_kind": state.route_transport_kind,
        "route_taxonomy_role": state.route_taxonomy_role,
        "route_taxonomy_memory_authority": state.route_taxonomy_memory_authority,
    }
    save_state(tmp_path, state)
    monkeypatch.setattr("swallow.synthesis.run_http_executor", _mock_http_executor)

    run_synthesis(tmp_path, state, _config())

    after = {
        "route_name": state.route_name,
        "route_model_hint": state.route_model_hint,
        "route_transport_kind": state.route_transport_kind,
        "route_taxonomy_role": state.route_taxonomy_role,
        "route_taxonomy_memory_authority": state.route_taxonomy_memory_authority,
    }
    assert after == before
    persisted = load_state(tmp_path, state.task_id)
    assert persisted.route_name == before["route_name"]
