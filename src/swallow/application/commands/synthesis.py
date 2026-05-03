from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from swallow.knowledge_retrieval.staged_knowledge import StagedCandidate, load_staged_candidates, submit_staged_candidate
from swallow.orchestration.models import Event
from swallow.orchestration.synthesis import load_synthesis_config, run_synthesis
from swallow.surface_tools.paths import artifacts_dir
from swallow.truth_governance.store import append_event, load_state


@dataclass(frozen=True)
class SynthesisRunCommandResult:
    task_id: str
    config_id: str
    artifact_path: Path
    summary: str


@dataclass(frozen=True)
class SynthesisStageCommandResult:
    candidate: StagedCandidate | None
    duplicate: StagedCandidate | None
    config_id: str


def run_synthesis_command(base_dir: Path, *, task_id: str, config_path: Path) -> SynthesisRunCommandResult:
    state = load_state(base_dir, task_id)
    config = load_synthesis_config(config_path)
    result = run_synthesis(base_dir, state, config)
    summary = str(result.payload.get("arbiter_decision", {}).get("synthesis_summary", "")).strip()
    return SynthesisRunCommandResult(
        task_id=state.task_id,
        config_id=config.config_id,
        artifact_path=result.path,
        summary=summary,
    )


def stage_synthesis_command(base_dir: Path, *, task_id: str) -> SynthesisStageCommandResult:
    normalized_task_id = task_id.strip()
    if not normalized_task_id:
        raise ValueError("--task must be a non-empty task id.")
    load_state(base_dir, normalized_task_id)
    arbitration_path = artifacts_dir(base_dir, normalized_task_id) / "synthesis_arbitration.json"
    if not arbitration_path.exists():
        raise ValueError(f"Missing synthesis arbitration artifact: {arbitration_path}")
    arbitration_data = json.loads(arbitration_path.read_text(encoding="utf-8"))
    if not isinstance(arbitration_data, dict):
        raise ValueError("synthesis_arbitration.json must contain a JSON object.")
    config_id = str(arbitration_data.get("config_id", "")).strip()
    if not config_id:
        raise ValueError("synthesis arbitration artifact is missing config_id.")
    arbiter_decision = arbitration_data.get("arbiter_decision", {})
    if not isinstance(arbiter_decision, dict):
        raise ValueError("synthesis arbitration artifact is missing arbiter_decision.")
    synthesis_summary = str(arbiter_decision.get("synthesis_summary", "")).strip()
    if not synthesis_summary:
        raise ValueError("synthesis arbitration summary must be non-empty.")
    duplicate = next(
        (
            candidate
            for candidate in load_staged_candidates(base_dir)
            if candidate.source_task_id == normalized_task_id
            and candidate.source_object_id == config_id
            and candidate.status == "pending"
        ),
        None,
    )
    if duplicate is not None:
        return SynthesisStageCommandResult(candidate=None, duplicate=duplicate, config_id=config_id)
    candidate = StagedCandidate(
        candidate_id="",
        text=synthesis_summary,
        source_task_id=normalized_task_id,
        topic=str(arbitration_data.get("topic", "")).strip(),
        source_kind="synthesis",
        source_ref=str(arbitration_path.relative_to(base_dir)),
        source_object_id=config_id,
        submitted_by="cli",
        taxonomy_role="",
        taxonomy_memory_authority="",
    )
    persisted = submit_staged_candidate(base_dir, candidate)
    append_event(
        base_dir,
        Event(
            task_id=normalized_task_id,
            event_type="task.synthesis_staged",
            message="Synthesis arbitration artifact was staged for knowledge review.",
            payload={
                "candidate_id": persisted.candidate_id,
                "config_id": config_id,
                "source_ref": persisted.source_ref,
            },
        ),
    )
    return SynthesisStageCommandResult(candidate=persisted, duplicate=None, config_id=config_id)
