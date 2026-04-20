from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable, Protocol

from .knowledge_store import load_task_knowledge_view, persist_task_knowledge_view
from .models import (
    Event,
    RetrievalItem,
    TaskState,
    ValidationResult,
    utc_now,
    validate_remote_handoff_contract_payload,
)
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
    remote_handoff_contract_path,
    knowledge_evidence_root,
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
    knowledge_wiki_root,
)


def _atomic_tmp_path(path: Path, *, kind: str = "tmp") -> Path:
    return path.with_name(f".{path.name}.{kind}")


def apply_atomic_text_updates(
    updates: dict[Path, str],
    *,
    deletes: Iterable[Path] = (),
) -> None:
    planned_updates = {path: content for path, content in updates.items()}
    planned_deletes = list(dict.fromkeys(Path(path) for path in deletes if Path(path) not in planned_updates))
    if not planned_updates and not planned_deletes:
        return

    original_contents: dict[Path, str | None] = {}
    staged_paths: dict[Path, Path] = {}
    replaced_paths: list[Path] = []
    deleted_paths: list[Path] = []

    touched_paths = list(planned_updates) + planned_deletes
    for path in touched_paths:
        original_contents[path] = path.read_text(encoding="utf-8") if path.exists() else None
        for suffix in ("tmp", "restore"):
            tmp_path = _atomic_tmp_path(path, kind=suffix)
            if tmp_path.exists():
                tmp_path.unlink()

    try:
        for path, content in planned_updates.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = _atomic_tmp_path(path)
            tmp_path.write_text(content, encoding="utf-8")
            staged_paths[path] = tmp_path

        for path, tmp_path in staged_paths.items():
            os.replace(tmp_path, path)
            replaced_paths.append(path)

        for path in planned_deletes:
            if path.exists():
                path.unlink()
                deleted_paths.append(path)
    except Exception:
        for path in reversed(deleted_paths):
            original = original_contents.get(path)
            if original is None:
                continue
            restore_path = _atomic_tmp_path(path, kind="restore")
            restore_path.parent.mkdir(parents=True, exist_ok=True)
            restore_path.write_text(original, encoding="utf-8")
            os.replace(restore_path, path)
        for path in reversed(replaced_paths):
            original = original_contents.get(path)
            if original is None:
                if path.exists():
                    path.unlink()
                continue
            restore_path = _atomic_tmp_path(path, kind="restore")
            restore_path.parent.mkdir(parents=True, exist_ok=True)
            restore_path.write_text(original, encoding="utf-8")
            os.replace(restore_path, path)
        raise
    finally:
        restore_paths = [_atomic_tmp_path(path, kind="restore") for path in touched_paths]
        for path in list(staged_paths.values()) + restore_paths:
            if path.exists():
                path.unlink()


def ensure_task_layout(base_dir: Path, task_id: str) -> None:
    task_root(base_dir, task_id).mkdir(parents=True, exist_ok=True)
    artifacts_dir(base_dir, task_id).mkdir(parents=True, exist_ok=True)
    tasks_root(base_dir).mkdir(parents=True, exist_ok=True)
    canonical_registry_root(base_dir).mkdir(parents=True, exist_ok=True)
    knowledge_evidence_root(base_dir).mkdir(parents=True, exist_ok=True)
    knowledge_wiki_root(base_dir).mkdir(parents=True, exist_ok=True)


def _load_json_lines(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []

    records: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            records.append(payload)
    return records


class TaskStoreProtocol(Protocol):
    def save_state(self, base_dir: Path, state: TaskState) -> None: ...

    def load_state(self, base_dir: Path, task_id: str) -> TaskState: ...

    def iter_task_states(self, base_dir: Path) -> Iterable[TaskState]: ...

    def append_event(self, base_dir: Path, event: Event) -> None: ...

    def load_events(self, base_dir: Path, task_id: str) -> list[dict[str, object]]: ...

    def iter_recent_task_events(self, base_dir: Path, last_n: int) -> list[tuple[str, list[dict[str, object]]]]: ...


def _save_state_file(base_dir: Path, state: TaskState) -> None:
    ensure_task_layout(base_dir, state.task_id)
    state.updated_at = utc_now()
    state_path(base_dir, state.task_id).write_text(
        json.dumps(state.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )


def _load_state_file(base_dir: Path, task_id: str) -> TaskState:
    data = json.loads(state_path(base_dir, task_id).read_text(encoding="utf-8"))
    return TaskState.from_dict(data)


def _iter_task_states_file(base_dir: Path) -> Iterable[TaskState]:
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


def _append_event_file(base_dir: Path, event: Event) -> None:
    ensure_task_layout(base_dir, event.task_id)
    with events_path(base_dir, event.task_id).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event.to_dict()) + "\n")


def _load_events_file(base_dir: Path, task_id: str) -> list[dict[str, object]]:
    return _load_json_lines(events_path(base_dir, task_id))


def _iter_recent_task_events_file(base_dir: Path, last_n: int) -> list[tuple[str, list[dict[str, object]]]]:
    if last_n <= 0:
        return []

    root = tasks_root(base_dir)
    if not root.exists():
        return []

    task_event_paths: list[tuple[str, Path]] = []
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        event_path = entry / "events.jsonl"
        if not event_path.exists():
            continue
        task_event_paths.append((entry.name, event_path))

    task_event_paths.sort(
        key=lambda item: (item[1].stat().st_mtime, item[0]),
        reverse=True,
    )
    return [(task_id, _load_json_lines(path)) for task_id, path in task_event_paths[:last_n]]


class FileTaskStore:
    def save_state(self, base_dir: Path, state: TaskState) -> None:
        _save_state_file(base_dir, state)

    def load_state(self, base_dir: Path, task_id: str) -> TaskState:
        return _load_state_file(base_dir, task_id)

    def iter_task_states(self, base_dir: Path) -> Iterable[TaskState]:
        return _iter_task_states_file(base_dir)

    def append_event(self, base_dir: Path, event: Event) -> None:
        _append_event_file(base_dir, event)

    def load_events(self, base_dir: Path, task_id: str) -> list[dict[str, object]]:
        return _load_events_file(base_dir, task_id)

    def iter_recent_task_events(self, base_dir: Path, last_n: int) -> list[tuple[str, list[dict[str, object]]]]:
        return _iter_recent_task_events_file(base_dir, last_n)


def normalize_store_backend(raw_backend: object) -> str:
    normalized = str(raw_backend or "file").strip().lower()
    return normalized if normalized in {"file", "sqlite"} else "file"


def resolve_task_store(base_dir: Path) -> TaskStoreProtocol:
    del base_dir
    backend = normalize_store_backend(os.environ.get("SWALLOW_STORE_BACKEND", "file"))
    if backend == "sqlite":
        from .sqlite_store import SqliteTaskStore

        return SqliteTaskStore()
    return FileTaskStore()


def save_state(base_dir: Path, state: TaskState) -> None:
    resolve_task_store(base_dir).save_state(base_dir, state)


def load_state(base_dir: Path, task_id: str) -> TaskState:
    return resolve_task_store(base_dir).load_state(base_dir, task_id)


def iter_task_states(base_dir: Path) -> Iterable[TaskState]:
    return resolve_task_store(base_dir).iter_task_states(base_dir)


def append_event(base_dir: Path, event: Event) -> None:
    resolve_task_store(base_dir).append_event(base_dir, event)


def load_events(base_dir: Path, task_id: str) -> list[dict[str, object]]:
    return resolve_task_store(base_dir).load_events(base_dir, task_id)


def iter_recent_task_events(base_dir: Path, last_n: int) -> list[tuple[str, list[dict[str, object]]]]:
    return resolve_task_store(base_dir).iter_recent_task_events(base_dir, last_n)


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
    normalized_payload = persist_task_knowledge_view(base_dir, task_id, payload)
    knowledge_objects_path(base_dir, task_id).write_text(
        json.dumps(normalized_payload, indent=2) + "\n",
        encoding="utf-8",
    )


def load_knowledge_objects(base_dir: Path, task_id: str) -> list[dict[str, object]]:
    return load_task_knowledge_view(base_dir, task_id)


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


def save_remote_handoff_contract(base_dir: Path, task_id: str, payload: dict[str, object]) -> None:
    errors = validate_remote_handoff_contract_payload(payload)
    if errors:
        raise ValueError(f"Invalid remote handoff contract payload: {'; '.join(errors)}")
    ensure_task_layout(base_dir, task_id)
    remote_handoff_contract_path(base_dir, task_id).write_text(
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
