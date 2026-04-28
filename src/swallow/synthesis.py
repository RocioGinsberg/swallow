from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from .executor import resolve_dialect_name, run_http_executor
from .governance import load_mps_policy
from .models import ExecutorResult, Event, RouteSpec, SynthesisConfig, SynthesisParticipant, TaskState, utc_now
from .paths import artifacts_dir
from .router import route_by_name, select_route
from .store import append_event, write_artifact


ROUND_DEFAULT = 2
PARTICIPANT_DEFAULT = 4
_MPS_DEFAULT_HTTP_ROUTE = "local-http"
ARBITRATION_ARTIFACT_NAME = "synthesis_arbitration.json"


@dataclass(frozen=True, slots=True)
class ParticipantArtifact:
    artifact_id: str
    round_n: int
    participant_id: str
    path: str
    output: str
    status: str
    route_name: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_prompt_dict(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "round": self.round_n,
            "participant_id": self.participant_id,
            "path": self.path,
            "status": self.status,
            "output": self.output,
        }


@dataclass(frozen=True, slots=True)
class ArbitrationResult:
    artifact_id: str
    path: Path
    payload: dict[str, object]


def _coerce_participant(payload: object, *, field_name: str) -> SynthesisParticipant:
    if not isinstance(payload, dict):
        raise ValueError(f"{field_name} must be a JSON object.")
    participant_id = str(payload.get("participant_id", "") or payload.get("id", "")).strip()
    role_prompt = str(payload.get("role_prompt", "")).strip()
    route_hint = str(payload.get("route_hint", "") or "").strip() or None
    if not participant_id:
        raise ValueError(f"{field_name}.participant_id must be a non-empty string.")
    if not role_prompt:
        raise ValueError(f"{field_name}.role_prompt must be a non-empty string.")
    return SynthesisParticipant(
        participant_id=participant_id,
        role_prompt=role_prompt,
        route_hint=route_hint,
    )


def synthesis_config_from_dict(payload: dict[str, object]) -> SynthesisConfig:
    config_id = str(payload.get("config_id", "")).strip()
    if not config_id:
        raise ValueError("config_id must be a non-empty string.")
    participants_payload = payload.get("participants", [])
    if not isinstance(participants_payload, list):
        raise ValueError("participants must be a list.")
    participants = tuple(
        _coerce_participant(item, field_name=f"participants[{index}]")
        for index, item in enumerate(participants_payload)
    )
    if not participants:
        raise ValueError("participants must contain at least one participant.")
    try:
        rounds = int(payload.get("rounds", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("rounds must be an integer.") from exc
    arbiter = _coerce_participant(payload.get("arbiter", {}), field_name="arbiter")
    _validate_participant_ids(participants, arbiter)
    arbiter_prompt_extra = str(payload.get("arbiter_prompt_extra", "") or "").strip() or None
    return SynthesisConfig(
        config_id=config_id,
        participants=participants,
        rounds=rounds,
        arbiter=arbiter,
        arbiter_prompt_extra=arbiter_prompt_extra,
    )


def load_synthesis_config(path: Path) -> SynthesisConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("synthesis config must contain a JSON object.")
    return synthesis_config_from_dict(payload)


def _resolve_round_limit(base_dir: Path) -> int:
    return load_mps_policy(base_dir, "mps_round_limit") or ROUND_DEFAULT


def _resolve_participant_limit(base_dir: Path) -> int:
    return load_mps_policy(base_dir, "mps_participant_limit") or PARTICIPANT_DEFAULT


def _route_is_path_a(route: RouteSpec) -> bool:
    return route.executor_name == "http" and route.transport_kind == "http"


def _default_path_a_route() -> RouteSpec:
    route = route_by_name(_MPS_DEFAULT_HTTP_ROUTE)
    if route is None or not _route_is_path_a(route):
        raise RuntimeError(f"MPS default route must resolve to a Path A HTTP route: {_MPS_DEFAULT_HTTP_ROUTE}")
    return route


def _resolve_participant_route(participant: SynthesisParticipant, base_state: TaskState) -> RouteSpec:
    if participant.route_hint:
        route = route_by_name(participant.route_hint)
        if route is None:
            raise ValueError(f"unknown route_hint {participant.route_hint!r} for participant {participant.participant_id}")
        if not _route_is_path_a(route):
            raise ValueError(f"route {route.name!r} is not a Path A HTTP route; MPS participants require Path A")
        return route

    selection = select_route(base_state)
    if _route_is_path_a(selection.route):
        return selection.route
    return _default_path_a_route()


def _participant_state_for_call(base_state: TaskState, route: RouteSpec) -> TaskState:
    return replace(
        base_state,
        executor_name=route.executor_name,
        route_name=route.name,
        route_backend=route.backend_kind,
        route_executor_family=route.executor_family,
        route_execution_site=route.execution_site,
        route_remote_capable=route.remote_capable,
        route_transport_kind=route.transport_kind,
        route_taxonomy_role=route.taxonomy.system_role,
        route_taxonomy_memory_authority=route.taxonomy.memory_authority,
        route_model_hint=route.model_hint,
        route_dialect=resolve_dialect_name(route.dialect_hint, route.model_hint),
        route_reason="MPS Path A route resolved for a transient synthesis call.",
        route_is_fallback=False,
        route_capabilities=route.capabilities.to_dict(),
        topology_route_name=route.name,
        topology_executor_family=route.executor_family,
        topology_execution_site=route.execution_site,
        topology_transport_kind=route.transport_kind,
        topology_remote_capable_intent=route.remote_capable,
    )


def compose_participant_prompt(
    participant: SynthesisParticipant,
    task_semantics: dict[str, object],
    prior_artifacts: list[dict[str, object]],
) -> str:
    lines = [
        participant.role_prompt.strip(),
        "",
        "---",
        "",
        "## Task Semantics",
        json.dumps(task_semantics, indent=2, sort_keys=True),
        "",
        "## Prior round artifacts",
    ]
    if not prior_artifacts:
        lines.append("- none")
    else:
        for artifact in prior_artifacts:
            lines.extend(
                [
                    f"- artifact_id: {artifact.get('artifact_id', '')}",
                    f"  round: {artifact.get('round', '')}",
                    f"  participant_id: {artifact.get('participant_id', '')}",
                    f"  path: {artifact.get('path', '')}",
                    f"  status: {artifact.get('status', '')}",
                    "  output: |",
                ]
            )
            output = str(artifact.get("output", "")).strip()
            lines.extend(f"    {line}" for line in output.splitlines() or [""])
    return "\n".join(lines).strip()


def _artifact_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def _role_prompt_hash(role_prompt: str) -> str:
    return sha256(role_prompt.encode("utf-8")).hexdigest()


def _validate_participant_ids(
    participants: tuple[SynthesisParticipant, ...],
    arbiter: SynthesisParticipant,
) -> None:
    seen: set[str] = set()
    duplicates: list[str] = []
    for participant in participants:
        participant_id = participant.participant_id.strip()
        if participant_id in seen and participant_id not in duplicates:
            duplicates.append(participant_id)
        seen.add(participant_id)
    if duplicates:
        duplicate_ids = ", ".join(sorted(duplicates))
        raise ValueError(f"participants[].participant_id must be unique: {duplicate_ids}")
    arbiter_id = arbiter.participant_id.strip()
    if arbiter_id in seen:
        raise ValueError(f"arbiter.participant_id must differ from participant ids: {arbiter_id}")


def _require_completed_executor_result(
    executor_result: ExecutorResult,
    *,
    actor_label: str,
) -> None:
    if executor_result.status == "completed":
        return
    detail = (executor_result.message or executor_result.output or "").strip()
    suffix = f": {detail}" if detail else "."
    raise RuntimeError(
        f"MPS executor failed for {actor_label} with status={executor_result.status!r}{suffix}"
    )


def persist_participant_artifact(
    base_dir: Path,
    task_id: str,
    round_n: int,
    participant: SynthesisParticipant,
    executor_result: ExecutorResult,
    route_name: str,
) -> ParticipantArtifact:
    artifact_id = _artifact_id("synthesis")
    artifact_name = f"synthesis_round_{round_n}_participant_{participant.participant_id}.json"
    output = (executor_result.output or executor_result.message).strip()
    payload = {
        "schema": "synthesis_participant_v1",
        "artifact_id": artifact_id,
        "task_id": task_id,
        "round": round_n,
        "participant_id": participant.participant_id,
        "role_prompt_hash": _role_prompt_hash(participant.role_prompt),
        "route_name": route_name,
        "status": executor_result.status,
        "output": output,
        "completed_at": utc_now(),
    }
    path = write_artifact(base_dir, task_id, artifact_name, json.dumps(payload, indent=2, sort_keys=True))
    return ParticipantArtifact(
        artifact_id=artifact_id,
        round_n=round_n,
        participant_id=participant.participant_id,
        path=str(path.relative_to(base_dir)),
        output=output,
        status=executor_result.status,
        route_name=route_name,
    )


def run_synthesis_round(
    config: SynthesisConfig,
    round_n: int,
    prior_artifacts: list[ParticipantArtifact],
    base_dir: Path,
    base_state: TaskState,
) -> list[ParticipantArtifact]:
    artifacts: list[ParticipantArtifact] = []
    prompt_artifacts = [artifact.to_prompt_dict() for artifact in prior_artifacts]
    for participant in config.participants:
        route = _resolve_participant_route(participant, base_state)
        transient_state = _participant_state_for_call(base_state, route)
        prompt = compose_participant_prompt(participant, base_state.task_semantics, prompt_artifacts)
        executor_result = run_http_executor(transient_state, [], prompt=prompt)
        _require_completed_executor_result(
            executor_result,
            actor_label=f"participant {participant.participant_id} round {round_n}",
        )
        artifacts.append(
            persist_participant_artifact(
                base_dir,
                base_state.task_id,
                round_n,
                participant,
                executor_result,
                route.name,
            )
        )
    return artifacts


def _participant_summaries(
    config: SynthesisConfig,
    artifacts: list[ParticipantArtifact],
) -> list[dict[str, object]]:
    by_participant: dict[str, list[ParticipantArtifact]] = {
        participant.participant_id: [] for participant in config.participants
    }
    for artifact in artifacts:
        by_participant.setdefault(artifact.participant_id, []).append(artifact)

    summaries: list[dict[str, object]] = []
    for participant in config.participants:
        participant_artifacts = by_participant.get(participant.participant_id, [])
        summaries.append(
            {
                "participant_id": participant.participant_id,
                "role_prompt_hash": _role_prompt_hash(participant.role_prompt),
                "round_artifacts": [
                    {
                        "round": artifact.round_n,
                        "artifact_id": artifact.artifact_id,
                        "path": artifact.path,
                        "status": artifact.status,
                        "route_name": artifact.route_name,
                    }
                    for artifact in participant_artifacts
                ],
            }
        )
    return summaries


def _validate_config(base_dir: Path, config: SynthesisConfig) -> None:
    _validate_participant_ids(config.participants, config.arbiter)
    if config.rounds < 1:
        raise ValueError("synthesis rounds must be >= 1.")
    round_limit = _resolve_round_limit(base_dir)
    if config.rounds > round_limit:
        raise ValueError(f"synthesis rounds {config.rounds} exceed mps_round_limit {round_limit}.")
    participant_limit = _resolve_participant_limit(base_dir)
    if len(config.participants) > participant_limit:
        raise ValueError(
            f"synthesis participants {len(config.participants)} exceed mps_participant_limit {participant_limit}."
        )
    if not config.arbiter.participant_id.strip() or not config.arbiter.role_prompt.strip():
        raise ValueError("synthesis arbiter must have participant_id and role_prompt.")


def _arbitration_prompt(
    config: SynthesisConfig,
    task_semantics: dict[str, object],
    all_artifacts: list[ParticipantArtifact],
) -> str:
    prior_artifacts = [artifact.to_prompt_dict() for artifact in all_artifacts]
    base_prompt = config.arbiter.role_prompt
    if config.arbiter_prompt_extra:
        base_prompt = f"{base_prompt}\n\n{config.arbiter_prompt_extra}"
    return compose_participant_prompt(
        SynthesisParticipant(
            participant_id=config.arbiter.participant_id,
            role_prompt=base_prompt,
            route_hint=config.arbiter.route_hint,
        ),
        task_semantics,
        prior_artifacts,
    )


def run_synthesis(base_dir: Path, base_state: TaskState, config: SynthesisConfig) -> ArbitrationResult:
    arbitration_path = artifacts_dir(base_dir, base_state.task_id) / ARBITRATION_ARTIFACT_NAME
    if arbitration_path.exists():
        raise RuntimeError("synthesis already completed for task; re-run requires new task")
    _validate_config(base_dir, config)

    all_artifacts: list[ParticipantArtifact] = []
    prior_artifacts: list[ParticipantArtifact] = []
    for round_n in range(1, config.rounds + 1):
        current_round = run_synthesis_round(config, round_n, prior_artifacts, base_dir, base_state)
        all_artifacts.extend(current_round)
        prior_artifacts = current_round

    arbiter_route = _resolve_participant_route(config.arbiter, base_state)
    arbiter_state = _participant_state_for_call(base_state, arbiter_route)
    prompt = _arbitration_prompt(config, base_state.task_semantics, all_artifacts)
    arbiter_result = run_http_executor(arbiter_state, [], prompt=prompt)
    _require_completed_executor_result(
        arbiter_result,
        actor_label=f"arbiter {config.arbiter.participant_id}",
    )
    synthesis_summary = (arbiter_result.output or arbiter_result.message).strip()
    if not synthesis_summary:
        raise ValueError("arbiter synthesis_summary must be non-empty.")

    arbitration_artifact_id = "synthesis_arbitration"
    payload: dict[str, object] = {
        "schema": "synthesis_arbitration_v1",
        "config_id": config.config_id,
        "task_id": base_state.task_id,
        "rounds_executed": config.rounds,
        "participants": _participant_summaries(config, all_artifacts),
        "arbiter": {
            "participant_id": config.arbiter.participant_id,
            "role_prompt_hash": _role_prompt_hash(config.arbiter.role_prompt),
            "route_name": arbiter_route.name,
        },
        "arbiter_decision": {
            "selected_artifact_refs": [artifact.artifact_id for artifact in all_artifacts],
            "synthesis_summary": synthesis_summary,
            "rationale": arbiter_result.message,
        },
        "raw_arbiter_output": arbiter_result.output,
        "completed_at": utc_now(),
    }
    path = write_artifact(
        base_dir,
        base_state.task_id,
        ARBITRATION_ARTIFACT_NAME,
        json.dumps(payload, indent=2, sort_keys=True),
    )
    append_event(
        base_dir,
        Event(
            task_id=base_state.task_id,
            event_type="task.mps_completed",
            message="Multi-perspective synthesis completed.",
            payload={
                "config_id": config.config_id,
                "arbitration_artifact_id": arbitration_artifact_id,
                "arbitration_artifact_path": str(path.relative_to(base_dir)),
                "rounds_executed": config.rounds,
                "participant_count": len(config.participants),
            },
        ),
    )
    return ArbitrationResult(artifact_id=arbitration_artifact_id, path=path, payload=payload)
