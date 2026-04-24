from __future__ import annotations

from pathlib import Path


APP_DIR_NAME = ".swl"


def app_root(base_dir: Path) -> Path:
    return base_dir / APP_DIR_NAME


def swallow_db_path(base_dir: Path) -> Path:
    return app_root(base_dir) / "swallow.db"


def canonical_registry_root(base_dir: Path) -> Path:
    return app_root(base_dir) / "canonical_knowledge"


def staged_knowledge_root(base_dir: Path) -> Path:
    return app_root(base_dir) / "staged_knowledge"


def knowledge_root(base_dir: Path) -> Path:
    return app_root(base_dir) / "knowledge"


def meta_optimizer_root(base_dir: Path) -> Path:
    return app_root(base_dir) / "meta_optimizer"


def knowledge_evidence_root(base_dir: Path) -> Path:
    return knowledge_root(base_dir) / "evidence"


def knowledge_wiki_root(base_dir: Path) -> Path:
    return knowledge_root(base_dir) / "wiki"


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


def task_knowledge_evidence_root(base_dir: Path, task_id: str) -> Path:
    return knowledge_evidence_root(base_dir) / task_id


def task_knowledge_wiki_root(base_dir: Path, task_id: str) -> Path:
    return knowledge_wiki_root(base_dir) / task_id


def knowledge_evidence_entry_path(base_dir: Path, task_id: str, object_id: str) -> Path:
    return task_knowledge_evidence_root(base_dir, task_id) / f"{object_id}.json"


def knowledge_wiki_entry_path(base_dir: Path, task_id: str, entry_id: str) -> Path:
    return task_knowledge_wiki_root(base_dir, task_id) / f"{entry_id}.json"


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


def remote_handoff_contract_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "remote_handoff_contract.json"


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


def optimization_proposals_path(base_dir: Path) -> Path:
    return meta_optimizer_root(base_dir) / "optimization_proposals.md"


def optimization_proposal_bundles_root(base_dir: Path) -> Path:
    return meta_optimizer_root(base_dir) / "proposal_bundles"


def latest_optimization_proposal_bundle_path(base_dir: Path) -> Path:
    return optimization_proposal_bundles_root(base_dir) / "latest.json"


def optimization_proposal_bundle_path(base_dir: Path, bundle_id: str) -> Path:
    return optimization_proposal_bundles_root(base_dir) / f"{bundle_id}.json"


def optimization_proposal_reviews_root(base_dir: Path) -> Path:
    return meta_optimizer_root(base_dir) / "proposal_reviews"


def optimization_proposal_review_path(base_dir: Path, review_id: str) -> Path:
    return optimization_proposal_reviews_root(base_dir) / f"{review_id}.json"


def optimization_proposal_applications_root(base_dir: Path) -> Path:
    return meta_optimizer_root(base_dir) / "proposal_applications"


def optimization_proposal_application_path(base_dir: Path, application_id: str) -> Path:
    return optimization_proposal_applications_root(base_dir) / f"{application_id}.json"


def audit_policy_path(base_dir: Path) -> Path:
    return app_root(base_dir) / "audit_policy.json"


def route_weights_path(base_dir: Path) -> Path:
    return app_root(base_dir) / "route_weights.json"


def route_capabilities_path(base_dir: Path) -> Path:
    return app_root(base_dir) / "route_capabilities.json"


def canonical_registry_path(base_dir: Path) -> Path:
    return canonical_registry_root(base_dir) / "registry.jsonl"


def staged_knowledge_registry_path(base_dir: Path) -> Path:
    return staged_knowledge_root(base_dir) / "registry.jsonl"


def canonical_registry_index_path(base_dir: Path) -> Path:
    return canonical_registry_root(base_dir) / "index.json"


def canonical_reuse_policy_path(base_dir: Path) -> Path:
    return canonical_registry_root(base_dir) / "reuse_policy.json"


def canonical_reuse_eval_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "canonical_reuse_eval.jsonl"


def canonical_reuse_regression_path(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "canonical_reuse_regression.json"
