from __future__ import annotations

import json

import pytest

from swallow.truth_governance.governance import OperatorToken, ProposalTarget, apply_proposal, register_mps_policy_proposal
from swallow.orchestration.models import ExecutorResult, SynthesisConfig, SynthesisParticipant, TaskState
from swallow.provider_router.router import resolve_fallback_chain
from swallow.application.infrastructure.paths import artifacts_dir
from swallow.truth_governance.store import load_events, load_state, save_state
from swallow.orchestration.synthesis import (
    _participant_state_for_call,
    _resolve_participant_route,
    run_synthesis,
    synthesis_config_from_dict,
)


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
    monkeypatch.setattr("swallow.orchestration.synthesis.run_http_executor", _mock_http_executor)

    with pytest.raises(ValueError, match="exceed mps_participant_limit 1"):
        run_synthesis(tmp_path, state, _config(participant_count=2))


def test_mps_participant_state_gets_route_specific_fallback_chain() -> None:
    state = _state()
    state.fallback_route_chain = ("local-aider", "local-summary")
    participant = SynthesisParticipant(
        participant_id="participant-http",
        role_prompt="Use the HTTP route.",
        route_hint="http-claude",
    )

    route = _resolve_participant_route(participant, state)
    participant_state = _participant_state_for_call(state, route)

    assert participant_state.route_name == "http-claude"
    assert participant_state.fallback_route_chain == resolve_fallback_chain("http-claude")


def test_mps_arbiter_artifact_required(tmp_path, monkeypatch) -> None:
    state = _state()
    save_state(tmp_path, state)
    monkeypatch.setattr("swallow.orchestration.synthesis.run_http_executor", _mock_http_executor)

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
        for artifact in participant["round_artifacts"]:
            participant_payload = json.loads((tmp_path / artifact["path"]).read_text(encoding="utf-8"))
            assert participant_payload["role_prompt_hash"]
            assert "prompt" not in participant_payload

    events = load_events(tmp_path, state.task_id)
    mps_events = [event for event in events if event["event_type"] == "task.mps_completed"]
    assert len(mps_events) == 1
    assert mps_events[0]["payload"]["config_id"] == "config-mps"
    assert mps_events[0]["payload"]["arbitration_artifact_id"] == "synthesis_arbitration"
    assert load_state(tmp_path, state.task_id).status == "created"


def test_synthesis_run_rejects_if_arbitration_exists(tmp_path, monkeypatch) -> None:
    state = _state()
    save_state(tmp_path, state)
    monkeypatch.setattr("swallow.orchestration.synthesis.run_http_executor", _mock_http_executor)
    config = _config()
    run_synthesis(tmp_path, state, config)

    with pytest.raises(RuntimeError, match="synthesis already completed"):
        run_synthesis(tmp_path, state, config)


def test_synthesis_does_not_mutate_main_task_state(tmp_path, monkeypatch) -> None:
    state = _state()
    save_state(tmp_path, state)
    before = state.to_dict()
    persisted_before = load_state(tmp_path, state.task_id).to_dict()
    monkeypatch.setattr("swallow.orchestration.synthesis.run_http_executor", _mock_http_executor)

    run_synthesis(tmp_path, state, _config())

    assert state.to_dict() == before
    persisted = load_state(tmp_path, state.task_id)
    assert persisted.to_dict() == persisted_before


def test_mps_aborts_on_participant_failure(tmp_path, monkeypatch) -> None:
    state = _state()
    save_state(tmp_path, state)

    def failing_http_executor(state, retrieval_items, prompt=None, **kwargs):
        del state, retrieval_items, prompt, kwargs
        return ExecutorResult(
            executor_name="http",
            status="failed",
            message="upstream unavailable",
        )

    monkeypatch.setattr("swallow.orchestration.synthesis.run_http_executor", failing_http_executor)

    with pytest.raises(RuntimeError, match="participant participant-1 round 1"):
        run_synthesis(tmp_path, state, _config())

    artifact_dir = artifacts_dir(tmp_path, state.task_id)
    assert not (artifact_dir / "synthesis_arbitration.json").exists()
    if artifact_dir.exists():
        assert not list(artifact_dir.glob("synthesis_round_*_participant_*.json"))


def test_config_rejects_duplicate_participant_id() -> None:
    payload = {
        "config_id": "config-mps",
        "rounds": 1,
        "participants": [
            {"participant_id": "same", "role_prompt": "First perspective."},
            {"participant_id": "same", "role_prompt": "Second perspective."},
        ],
        "arbiter": {"participant_id": "arbiter", "role_prompt": "Arbitrate."},
    }

    with pytest.raises(ValueError, match=r"participants\[\]\.participant_id must be unique"):
        synthesis_config_from_dict(payload)

    payload["participants"][1]["participant_id"] = "other"
    payload["arbiter"]["participant_id"] = "same"

    with pytest.raises(ValueError, match=r"arbiter\.participant_id must differ"):
        synthesis_config_from_dict(payload)
