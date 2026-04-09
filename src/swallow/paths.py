from __future__ import annotations

from pathlib import Path


APP_DIR_NAME = ".swl"


def app_root(base_dir: Path) -> Path:
    return base_dir / APP_DIR_NAME


def canonical_registry_root(base_dir: Path) -> Path:
    return app_root(base_dir) / "canonical_knowledge"


def tasks_root(base_dir: Path) -> Path:
    return app_root(base_dir) / "tasks"


def task_root(base_dir: Path, task_id: str) -> Path:
    return tasks_root(base_dir) / task_id


def artifacts_dir(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "artifacts"


def state_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "state.json"


def events_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "events.jsonl"


def retrieval_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "retrieval.json"


def validation_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "validation.json"


def compatibility_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "compatibility.json"


def memory_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "memory.json"


def task_semantics_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "task_semantics.json"


def knowledge_objects_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "knowledge_objects.json"


def knowledge_policy_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "knowledge_policy.json"


def knowledge_partition_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "knowledge_partition.json"


def knowledge_index_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "knowledge_index.json"


def knowledge_decisions_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "knowledge_decisions.jsonl"


def capability_assembly_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "capability_assembly.json"


def capability_manifest_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "capability_manifest.json"


def route_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "route.json"


def topology_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "topology.json"


def execution_site_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "execution_site.json"


def dispatch_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "dispatch.json"


def handoff_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "handoff.json"


def execution_fit_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "execution_fit.json"


def retry_policy_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "retry_policy.json"


def stop_policy_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "stop_policy.json"


def execution_budget_policy_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "execution_budget_policy.json"


def checkpoint_snapshot_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "checkpoint_snapshot.json"


def canonical_registry_path(base_dir: Path) -> Path:
    return canonical_registry_root(base_dir) / "registry.jsonl"
