from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import Event, RetrievalItem, TaskState, ValidationResult, utc_now
from .paths import (
    canonical_reuse_policy_path,
    canonical_reuse_eval_path,
    canonical_reuse_regression_path,
    canonical_registry_index_path,
    artifacts_dir,
    canonical_registry_path,
    canonical_registry_root,
    capability_assembly_path,
    capability_manifest_path,
    compatibility_path,
    checkpoint_snapshot_path,
    dispatch_path,
    execution_site_path,
    execution_fit_path,
    events_path,
    handoff_path,
    knowledge_decisions_path,
    knowledge_index_path,
    knowledge_objects_path,
    knowledge_partition_path,
    knowledge_policy_path,
    memory_path,
    retry_policy_path,
    execution_budget_policy_path,
    stop_policy_path,
    task_semantics_path,
    retrieval_path,
    route_path,
    state_path,
    task_root,
    tasks_root,
    topology_path,
    validation_path,
)


def ensure_task_layout(base_dir: Path, task_id: str) -> None:
    task_root(base_dir, task_id).mkdir(parents=True, exist_ok=True)
    artifacts_dir(base_dir, task_id).mkdir(parents=True, exist_ok=True)
    tasks_root(base_dir).mkdir(parents=True, exist_ok=True)
    canonical_registry_root(base_dir).mkdir(parents=True, exist_ok=True)


def save_state(base_dir: Path, state: TaskState) -> None:
    ensure_task_layout(base_dir, state.task_id)
    state.updated_at = utc_now()
    state_path(base_dir, state.task_id).write_text(
        json.dumps(state.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )


def load_state(base_dir: Path, task_id: str) -> TaskState:
    data = json.loads(state_path(base_dir, task_id).read_text(encoding="utf-8"))
    return TaskState.from_dict(data)


def iter_task_states(base_dir: Path) -> Iterable[TaskState]:
    root = tasks_root(base_dir)
    if not root.exists():
        return []

    states: list[TaskState] = []
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        state_file = entry / "state.json"
        if not state_file.exists():
            continue
        data = json.loads(state_file.read_text(encoding="utf-8"))
        states.append(TaskState.from_dict(data))
    return states


def append_event(base_dir: Path, event: Event) -> None:
    ensure_task_layout(base_dir, event.task_id)
    with events_path(base_dir, event.task_id).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event.to_dict()) + "\n")


def save_retrieval(base_dir: Path, task_id: str, items: list[RetrievalItem]) -> None:
    ensure_task_layout(base_dir, task_id)
    payload = [item.to_dict() for item in items]
    retrieval_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_validation(base_dir: Path, task_id: str, result: ValidationResult) -> None:
    ensure_task_layout(base_dir, task_id)
    validation_path(base_dir, task_id).write_text(
        json.dumps(result.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )


def save_compatibility(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    compatibility_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_memory(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    memory_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_task_semantics(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    task_semantics_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_knowledge_objects(base_dir: Path, task_id: str, payload: list[dict[str, object]]) -> None:
    ensure_task_layout(base_dir, task_id)
    knowledge_objects_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_knowledge_policy(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    knowledge_policy_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_knowledge_partition(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    knowledge_partition_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_knowledge_index(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    knowledge_index_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def append_knowledge_decision(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    with knowledge_decisions_path(base_dir, task_id).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def append_canonical_record(base_dir: Path, payload: dict[str, object]) -> None:
    canonical_registry_root(base_dir).mkdir(parents=True, exist_ok=True)
    registry_file = canonical_registry_path(base_dir)
    records: list[dict[str, object]] = []
    canonical_id = str(payload.get("canonical_id", "")).strip()
    canonical_key = str(payload.get("canonical_key", "")).strip()
    promoted_at = str(payload.get("promoted_at", "")).strip()
    replaced = False
    if registry_file.exists():
        for line in registry_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
            if canonical_id and str(record.get("canonical_id", "")).strip() == canonical_id:
                records.append(payload)
                replaced = True
            elif (
                canonical_key
                and str(record.get("canonical_key", "")).strip() == canonical_key
                and str(record.get("canonical_id", "")).strip() != canonical_id
                and str(record.get("canonical_status", "active")).strip() != "superseded"
            ):
                updated_record = dict(record)
                updated_record["canonical_status"] = "superseded"
                updated_record["superseded_by"] = canonical_id
                updated_record["superseded_at"] = promoted_at
                records.append(updated_record)
            else:
                records.append(record)
    if not replaced:
        records.append(payload)
    registry_file.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


def save_canonical_registry_index(base_dir: Path, payload: dict[str, object]) -> None:
    canonical_registry_root(base_dir).mkdir(parents=True, exist_ok=True)
    canonical_registry_index_path(base_dir).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_canonical_reuse_policy(base_dir: Path, payload: dict[str, object]) -> None:
    canonical_registry_root(base_dir).mkdir(parents=True, exist_ok=True)
    canonical_reuse_policy_path(base_dir).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def append_canonical_reuse_evaluation(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    with canonical_reuse_eval_path(base_dir, task_id).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def save_canonical_reuse_regression(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    canonical_reuse_regression_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_capability_assembly(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    capability_assembly_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_capability_manifest(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    capability_manifest_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_route(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    route_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_topology(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    topology_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_execution_site(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    execution_site_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_dispatch(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    dispatch_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_handoff(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    handoff_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_execution_fit(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    execution_fit_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_retry_policy(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    retry_policy_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_stop_policy(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    stop_policy_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_execution_budget_policy(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    execution_budget_policy_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def save_checkpoint_snapshot(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    ensure_task_layout(base_dir, task_id)
    checkpoint_snapshot_path(base_dir, task_id).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def write_artifact(base_dir: Path, task_id: str, name: str, content: str) -> Path:
    ensure_task_layout(base_dir, task_id)
    path = artifacts_dir(base_dir, task_id) / name
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return path
