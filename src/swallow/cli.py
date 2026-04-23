from __future__ import annotations

import argparse
import json
from pathlib import Path

from .canonical_reuse_eval import (
    build_canonical_reuse_evaluation_report,
    build_canonical_reuse_evaluation_summary,
    build_canonical_reuse_regression_current,
    build_canonical_reuse_regression_report,
    compare_canonical_reuse_regression,
)
from .canonical_audit import audit_canonical_registry, build_canonical_audit_report
from .consistency_audit import (
    build_audit_trigger_policy_report,
    load_audit_trigger_policy,
    run_consistency_audit,
    save_audit_trigger_policy,
)
from .canonical_reuse import build_canonical_reuse_report, build_canonical_reuse_summary
from .checkpoint_snapshot import evaluate_checkpoint_snapshot
from .canonical_registry import (
    build_canonical_registry_index,
    build_canonical_registry_index_report,
    build_canonical_registry_report,
    build_staged_canonical_key,
)
from .doctor import (
    diagnose_codex,
    diagnose_local_stack,
    diagnose_sqlite_store,
    format_codex_doctor_result,
    format_local_stack_doctor_result,
    format_sqlite_doctor_result,
)
from .ingestion.pipeline import build_ingestion_report, build_ingestion_summary, run_ingestion_pipeline
from .knowledge_store import (
    OPERATOR_CANONICAL_WRITE_AUTHORITY,
    migrate_file_knowledge_to_sqlite,
    persist_wiki_entry_from_record,
)
from .meta_optimizer import extract_route_weight_proposals_from_report, run_meta_optimizer
from .knowledge_objects import summarize_canonicalization
from .knowledge_review import build_knowledge_decisions_report, build_review_queue, build_review_queue_report
from .models import LIBRARIAN_MEMORY_AUTHORITY
from .orchestrator import (
    acknowledge_task,
    append_task_knowledge_capture,
    create_task,
    decide_task_knowledge,
    evaluate_task_canonical_reuse,
    run_task,
    update_task_planning_handoff,
)
from .paths import (
    artifacts_dir,
    canonical_registry_index_path,
    canonical_registry_path,
    canonical_reuse_policy_path,
    canonical_reuse_eval_path,
    canonical_reuse_regression_path,
    capability_assembly_path,
    capability_manifest_path,
    checkpoint_snapshot_path,
    compatibility_path,
    dispatch_path,
    execution_budget_policy_path,
    execution_site_path,
    execution_fit_path,
    handoff_path,
    knowledge_decisions_path,
    knowledge_index_path,
    knowledge_partition_path,
    knowledge_policy_path,
    memory_path,
    remote_handoff_contract_path,
    retry_policy_path,
    stop_policy_path,
    task_semantics_path,
    retrieval_path,
    route_path,
    topology_path,
)
from .staged_knowledge import StagedCandidate, load_staged_candidates, update_staged_candidate
from .router import (
    apply_route_weights,
    build_route_weights_report,
    current_route_weights,
    route_by_name,
    save_route_weights,
)
from .store import (
    append_canonical_record,
    iter_task_states,
    load_events,
    load_knowledge_objects,
    load_state,
    migrate_file_tasks_to_sqlite,
    save_canonical_registry_index,
    save_canonical_reuse_policy,
)


ARTIFACT_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Core Run Record",
        (
            "task_semantics_report",
            "summary",
            "resume_note",
            "executor_output",
            "executor_prompt",
            "librarian_change_log",
            "librarian_change_log_report",
        ),
    ),
    (
        "Routing And Topology",
        (
            "route_report",
            "topology_report",
            "execution_site_report",
            "dispatch_report",
            "handoff_report",
            "remote_handoff_contract_report",
        ),
    ),
    (
        "Retrieval And Grounding",
        (
            "knowledge_objects_report",
            "knowledge_partition_report",
            "knowledge_index_report",
            "knowledge_decisions_report",
            "canonical_registry_report",
            "canonical_registry_index_report",
            "canonical_reuse_policy_report",
            "canonical_reuse_eval_report",
            "retrieval_report",
            "retrieval_json",
            "source_grounding",
            "grounding_evidence_report",
            "grounding_evidence_json",
        ),
    ),
    (
        "Validation",
        (
            "validation_report",
            "validation_json",
            "compatibility_report",
            "compatibility_json",
            "execution_fit_report",
            "execution_fit_json",
            "knowledge_policy_report",
            "knowledge_policy_json",
        ),
    ),
    (
        "Execution Control Policy",
        (
            "retry_policy_report",
            "retry_policy_json",
            "execution_budget_policy_report",
            "execution_budget_policy_json",
            "stop_policy_report",
            "stop_policy_json",
            "checkpoint_snapshot_report",
            "checkpoint_snapshot_json",
        ),
    ),
    (
        "Memory And Reuse",
        (
            "task_memory",
            "knowledge_objects_json",
            "knowledge_partition_json",
            "knowledge_index_json",
            "knowledge_decisions_json",
            "canonical_registry_json",
            "canonical_registry_index_json",
            "canonical_reuse_policy_json",
            "canonical_reuse_eval_json",
            "canonical_reuse_regression_json",
            "route_json",
            "topology_json",
            "execution_site_json",
            "dispatch_json",
            "handoff_json",
            "retry_policy_json",
            "execution_budget_policy_json",
            "stop_policy_json",
            "checkpoint_snapshot_json",
        ),
    ),
)


def is_mock_remote_task(state: object, topology: dict[str, object] | None = None) -> bool:
    topology = topology or {}
    transport_kind = str(topology.get("transport_kind", getattr(state, "topology_transport_kind", "")))
    dispatch_status = str(topology.get("dispatch_status", getattr(state, "topology_dispatch_status", "")))
    if dispatch_status == "mock_remote_dispatched":
        return True
    return transport_kind == "mock_remote_transport" and dispatch_status not in {"blocked", "acknowledged"}


def format_taxonomy_label(state: object) -> str:
    system_role = str(getattr(state, "route_taxonomy_role", "")).strip()
    memory_authority = str(getattr(state, "route_taxonomy_memory_authority", "")).strip()
    if not system_role and not memory_authority:
        return "-"
    return f"{system_role or '-'} / {memory_authority or '-'}"


def load_latest_capability_enforcement(base_dir: Path, task_id: str) -> dict[str, object]:
    events = load_events(base_dir, task_id)
    for event in reversed(events):
        if str(event.get("event_type", "")) == "task.capability_enforced":
            payload = event.get("payload", {})
            return payload if isinstance(payload, dict) else {}
    return {}


def format_capability_enforcement_summary(payload: dict[str, object]) -> tuple[str, str]:
    constraints = payload.get("constraints", [])
    if not isinstance(constraints, list) or not constraints:
        return "-", "-"

    fields: list[str] = []
    for item in constraints:
        if not isinstance(item, dict):
            continue
        field = str(item.get("field", "")).strip()
        max_value = item.get("max_value")
        if field:
            fields.append(f"{field}->{str(max_value).lower() if isinstance(max_value, bool) else max_value}")
    if not fields:
        return "-", "-"
    return "yes", ", ".join(fields)


def format_grounding_summary(state: object) -> tuple[str, str, str]:
    grounding_locked = bool(getattr(state, "grounding_locked", False))
    refs = getattr(state, "grounding_refs", [])
    if not isinstance(refs, list):
        refs = []
    normalized_refs = [str(item).strip() for item in refs if str(item).strip()]
    if not grounding_locked and not normalized_refs:
        return "-", "0", "-"
    return (
        "yes" if grounding_locked else "no",
        str(len(normalized_refs)),
        ", ".join(normalized_refs[:5]) if normalized_refs else "-",
    )


def build_grouped_artifact_index(artifact_paths: dict[str, str]) -> str:
    lines = ["Task Artifact Index", ""]
    for heading, keys in ARTIFACT_GROUPS:
        lines.append(heading)
        for key in keys:
            path = artifact_paths.get(key)
            if path:
                lines.append(f"{key}: {path}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_policy_snapshot(
    retry_policy: dict[str, object],
    execution_budget_policy: dict[str, object],
    stop_policy: dict[str, object],
) -> list[str]:
    return [
        "Policy Controls",
        f"retry_policy_status: {retry_policy.get('status', 'pending')}",
        f"retryable: {'yes' if retry_policy.get('retryable', False) else 'no'}",
        f"retry_decision: {retry_policy.get('retry_decision', 'pending')}",
        f"remaining_attempts: {retry_policy.get('remaining_attempts', 0)}",
        f"execution_budget_policy_status: {execution_budget_policy.get('status', 'pending')}",
        f"timeout_seconds: {execution_budget_policy.get('timeout_seconds', 0)}",
        f"budget_state: {execution_budget_policy.get('budget_state', 'pending')}",
        f"timeout_state: {execution_budget_policy.get('timeout_state', 'pending')}",
        f"stop_policy_status: {stop_policy.get('status', 'pending')}",
        f"stop_required: {'yes' if stop_policy.get('stop_required', False) else 'no'}",
        f"continue_allowed: {'yes' if stop_policy.get('continue_allowed', False) else 'no'}",
        f"stop_decision: {stop_policy.get('stop_decision', 'pending')}",
        f"checkpoint_kind: {stop_policy.get('checkpoint_kind', 'pending')}",
        f"escalation_level: {stop_policy.get('escalation_level', 'pending')}",
    ]


def format_store_migration_summary(summary: dict[str, object]) -> str:
    migrated_task_ids = summary.get("migrated_task_ids", [])
    skipped_task_ids = summary.get("skipped_task_ids", [])
    lines = [
        f"db_path={summary.get('db_path', '')}",
        f"dry_run={'yes' if summary.get('dry_run', False) else 'no'}",
        f"task_count_scanned={summary.get('task_count_scanned', 0)}",
        f"task_count_migrated={summary.get('task_count_migrated', 0)}",
        f"task_count_skipped={summary.get('task_count_skipped', 0)}",
        f"event_count_migrated={summary.get('event_count_migrated', 0)}",
        f"event_count_skipped={summary.get('event_count_skipped', 0)}",
        "migrated_task_ids=" + ",".join(str(item) for item in migrated_task_ids),
        "skipped_task_ids=" + ",".join(str(item) for item in skipped_task_ids),
    ]
    return "\n".join(lines)


def format_knowledge_migration_summary(summary: dict[str, object]) -> str:
    migrated_task_ids = summary.get("migrated_task_ids", [])
    skipped_task_ids = summary.get("skipped_task_ids", [])
    failed_task_ids = summary.get("failed_task_ids", [])
    error_items = summary.get("errors", {})
    lines = [
        f"db_path={summary.get('db_path', '')}",
        f"dry_run={'yes' if summary.get('dry_run', False) else 'no'}",
        f"task_count_scanned={summary.get('task_count_scanned', 0)}",
        f"task_count_migrated={summary.get('task_count_migrated', 0)}",
        f"task_count_skipped={summary.get('task_count_skipped', 0)}",
        f"task_count_failed={summary.get('task_count_failed', 0)}",
        f"knowledge_object_count_migrated={summary.get('knowledge_object_count_migrated', 0)}",
        f"knowledge_object_count_skipped={summary.get('knowledge_object_count_skipped', 0)}",
        f"knowledge_object_count_failed={summary.get('knowledge_object_count_failed', 0)}",
        "migrated_task_ids=" + ",".join(str(item) for item in migrated_task_ids),
        "skipped_task_ids=" + ",".join(str(item) for item in skipped_task_ids),
        "failed_task_ids=" + ",".join(str(item) for item in failed_task_ids),
        "errors=" + "; ".join(f"{task_id}:{message}" for task_id, message in sorted(error_items.items())),
    ]
    return "\n".join(lines)


def build_intake_snapshot(base_dir: Path, task_id: str) -> list[str]:
    state = load_state(base_dir, task_id)
    task_semantics = load_json_if_exists(task_semantics_path(base_dir, task_id))
    knowledge_objects = load_knowledge_objects(base_dir, task_id)
    knowledge_stage_counts = {"raw": 0, "candidate": 0, "verified": 0, "canonical": 0}
    knowledge_evidence_counts = {"artifact_backed": 0, "source_only": 0, "unbacked": 0}
    knowledge_reuse_counts = {"task_only": 0, "retrieval_candidate": 0}
    for item in knowledge_objects:
        stage = str(item.get("stage", "raw"))
        knowledge_stage_counts[stage] = knowledge_stage_counts.get(stage, 0) + 1
        evidence_status = str(item.get("evidence_status", "unbacked"))
        knowledge_evidence_counts[evidence_status] = knowledge_evidence_counts.get(evidence_status, 0) + 1
        reuse_scope = str(item.get("knowledge_reuse_scope", "task_only"))
        knowledge_reuse_counts[reuse_scope] = knowledge_reuse_counts.get(reuse_scope, 0) + 1

    return [
        f"Task Intake: {task_id}",
        f"title: {state.title}",
        "",
        "Planning Handoff",
        f"task_semantics_source_kind: {task_semantics.get('source_kind', state.task_semantics.get('source_kind', 'none') if state.task_semantics else 'none')}",
        f"task_semantics_source_ref: {task_semantics.get('source_ref', state.task_semantics.get('source_ref', '') if state.task_semantics else '') or '-'}",
        f"constraints_count: {len(task_semantics.get('constraints', state.task_semantics.get('constraints', []) if state.task_semantics else []))}",
        f"acceptance_criteria_count: {len(task_semantics.get('acceptance_criteria', state.task_semantics.get('acceptance_criteria', []) if state.task_semantics else []))}",
        f"priority_hints_count: {len(task_semantics.get('priority_hints', state.task_semantics.get('priority_hints', []) if state.task_semantics else []))}",
        f"next_action_proposals_count: {len(task_semantics.get('next_action_proposals', state.task_semantics.get('next_action_proposals', []) if state.task_semantics else []))}",
        "",
        "Staged Knowledge Capture",
        f"knowledge_objects_count: {len(knowledge_objects)}",
        f"knowledge_stage_counts: raw={knowledge_stage_counts.get('raw', 0)} candidate={knowledge_stage_counts.get('candidate', 0)} verified={knowledge_stage_counts.get('verified', 0)} canonical={knowledge_stage_counts.get('canonical', 0)}",
        f"knowledge_evidence_counts: artifact_backed={knowledge_evidence_counts.get('artifact_backed', 0)} source_only={knowledge_evidence_counts.get('source_only', 0)} unbacked={knowledge_evidence_counts.get('unbacked', 0)}",
        f"knowledge_reuse_counts: retrieval_candidate={knowledge_reuse_counts.get('retrieval_candidate', 0)} task_only={knowledge_reuse_counts.get('task_only', 0)}",
        "",
        "Boundary",
        "task_semantics_role: execution_intent",
        "knowledge_objects_role: staged_evidence",
        "",
        "Intake Artifacts",
        f"task_semantics_report: {state.artifact_paths.get('task_semantics_report', '-')}",
        f"knowledge_objects_report: {state.artifact_paths.get('knowledge_objects_report', '-')}",
        f"knowledge_partition_report: {state.artifact_paths.get('knowledge_partition_report', '-')}",
        f"knowledge_index_report: {state.artifact_paths.get('knowledge_index_report', '-')}",
    ]


def build_knowledge_review_snapshot(
    knowledge_objects: list[dict[str, object]],
    decisions: list[dict[str, object]],
) -> list[str]:
    queue = build_review_queue(knowledge_objects, decisions)
    entries = list(queue.get("entries", []))
    state_counts = dict(queue.get("state_counts", {}))
    blocked_reasons = sorted(
        {
            str(entry.get("blocked_reason", "")).strip()
            for entry in entries
            if str(entry.get("blocked_reason", "")).strip()
        }
    )
    latest_decisions = sum(1 for entry in entries if entry.get("latest_decision"))
    return [
        "Knowledge Review",
        f"knowledge_review_pending: {state_counts.get('pending-review', 0)}",
        f"knowledge_review_promote_ready: {state_counts.get('promote-ready', 0)}",
        f"knowledge_review_reuse_ready: {state_counts.get('reuse-ready', 0)}",
        f"knowledge_review_blocked: {state_counts.get('blocked', 0)}",
        f"knowledge_review_promoted: {state_counts.get('promoted', 0)}",
        f"knowledge_review_rejected: {state_counts.get('rejected', 0)}",
        f"knowledge_review_blocked_reasons: {', '.join(blocked_reasons) or '-'}",
        f"knowledge_review_decisions_recorded: {len(decisions)}",
        f"knowledge_review_latest_decisions_visible: {latest_decisions}",
    ]


def summarize_knowledge_attention(base_dir: Path, task_id: str) -> dict[str, str]:
    knowledge_objects = load_knowledge_objects(base_dir, task_id)
    decisions = load_json_lines_if_exists(knowledge_decisions_path(base_dir, task_id))
    queue = build_review_queue(knowledge_objects, decisions)
    state_counts = dict(queue.get("state_counts", {}))
    needs_attention = any(
        state_counts.get(key, 0) > 0 for key in ("pending-review", "promote-ready", "reuse-ready", "blocked")
    )
    summary_parts = []
    for label, key in (
        ("pending", "pending-review"),
        ("promote_ready", "promote-ready"),
        ("reuse_ready", "reuse-ready"),
        ("blocked", "blocked"),
        ("rejected", "rejected"),
    ):
        count = state_counts.get(key, 0)
        if count:
            summary_parts.append(f"{label}={count}")
    entries = list(queue.get("entries", []))
    blocked_reasons = sorted(
        {
            str(entry.get("blocked_reason", "")).strip()
            for entry in entries
            if str(entry.get("blocked_reason", "")).strip()
        }
    )
    if state_counts.get("promote-ready", 0) > 0:
        recommended_reason = "knowledge_promote_ready"
    elif state_counts.get("reuse-ready", 0) > 0:
        recommended_reason = "knowledge_reuse_ready"
    elif state_counts.get("blocked", 0) > 0:
        recommended_reason = "knowledge_blocked_review"
    elif state_counts.get("pending-review", 0) > 0:
        recommended_reason = "knowledge_pending_review"
    else:
        recommended_reason = "knowledge_no_action"
    return {
        "needs_attention": "yes" if needs_attention else "no",
        "summary": ", ".join(summary_parts) or "-",
        "blocked_reasons": ", ".join(blocked_reasons) or "-",
        "recommended_reason": recommended_reason,
        "recommended_command": f"swl task knowledge-review-queue {task_id}",
    }


def build_canonical_registry_snapshot(index_record: dict[str, object]) -> list[str]:
    return [
        "Canonical Registry",
        f"canonical_registry_count: {index_record.get('count', 0)}",
        f"canonical_registry_active_count: {index_record.get('active_count', 0)}",
        f"canonical_registry_superseded_count: {index_record.get('superseded_count', 0)}",
        f"canonical_registry_source_task_count: {index_record.get('source_task_count', 0)}",
        f"canonical_registry_artifact_backed_count: {index_record.get('artifact_backed_count', 0)}",
        f"canonical_registry_latest_id: {index_record.get('latest_canonical_id', '') or '-'}",
        f"canonical_registry_latest_active_id: {index_record.get('latest_active_canonical_id', '') or '-'}",
        f"canonical_registry_latest_source_task: {index_record.get('latest_source_task_id', '') or '-'}",
        f"canonical_registry_latest_source_object: {index_record.get('latest_source_object_id', '') or '-'}",
    ]


def build_canonical_reuse_snapshot(policy_record: dict[str, object]) -> list[str]:
    return [
        "Canonical Reuse",
        f"canonical_reuse_policy: {policy_record.get('policy_name', '-')}",
        f"canonical_reuse_visible_count: {policy_record.get('reuse_visible_count', 0)}",
        f"canonical_reuse_hidden_count: {policy_record.get('reuse_hidden_count', 0)}",
        f"canonical_reuse_latest_visible_id: {policy_record.get('latest_visible_canonical_id', '') or '-'}",
        f"canonical_reuse_latest_visible_source_task: {policy_record.get('latest_visible_source_task_id', '') or '-'}",
        f"canonical_reuse_latest_visible_source_object: {policy_record.get('latest_visible_source_object_id', '') or '-'}",
    ]


def build_canonical_reuse_eval_snapshot(records: list[dict[str, object]]) -> list[str]:
    summary = build_canonical_reuse_evaluation_summary(records)
    return [
        "Canonical Reuse Evaluation",
        f"canonical_reuse_eval_count: {summary.get('evaluation_count', 0)}",
        f"canonical_reuse_eval_useful: {summary.get('judgment_counts', {}).get('useful', 0)}",
        f"canonical_reuse_eval_noisy: {summary.get('judgment_counts', {}).get('noisy', 0)}",
        f"canonical_reuse_eval_needs_review: {summary.get('judgment_counts', {}).get('needs_review', 0)}",
        f"canonical_reuse_eval_resolved: {summary.get('resolved_citation_count', 0)}",
        f"canonical_reuse_eval_unresolved: {summary.get('unresolved_citation_count', 0)}",
        f"canonical_reuse_eval_retrieval_matches: {summary.get('retrieval_match_count', 0)}",
        f"canonical_reuse_eval_latest_judgment: {summary.get('latest_judgment', '') or '-'}",
        f"canonical_reuse_eval_latest_task: {summary.get('latest_task_id', '') or '-'}",
        f"canonical_reuse_eval_latest_citations: {', '.join(summary.get('latest_citations', [])) or '-'}",
        f"canonical_reuse_eval_latest_retrieval_context: {summary.get('latest_retrieval_context_ref', '') or '-'}",
    ]


def build_canonical_reuse_regression_snapshot(baseline: dict[str, object]) -> list[str]:
    judgment_counts = baseline.get("judgment_counts", {})
    if not isinstance(judgment_counts, dict):
        judgment_counts = {}
    return [
        "Canonical Reuse Regression",
        f"canonical_reuse_regression_generated_at: {baseline.get('baseline_generated_at', '-')}",
        f"canonical_reuse_regression_task: {baseline.get('task_id', '') or '-'}",
        f"canonical_reuse_regression_eval_count: {baseline.get('evaluation_count', 0)}",
        f"canonical_reuse_regression_useful: {judgment_counts.get('useful', 0)}",
        f"canonical_reuse_regression_noisy: {judgment_counts.get('noisy', 0)}",
        f"canonical_reuse_regression_needs_review: {judgment_counts.get('needs_review', 0)}",
        f"canonical_reuse_regression_resolved: {baseline.get('resolved_citation_count', 0)}",
        f"canonical_reuse_regression_unresolved: {baseline.get('unresolved_citation_count', 0)}",
        f"canonical_reuse_regression_retrieval_matches: {baseline.get('retrieval_match_count', 0)}",
        f"canonical_reuse_regression_latest_judgment: {baseline.get('latest_judgment', '') or '-'}",
        f"canonical_reuse_regression_latest_citations: {', '.join(baseline.get('latest_citations', [])) or '-'}",
        f"canonical_reuse_regression_latest_retrieval_context: {baseline.get('latest_retrieval_context_ref', '') or '-'}",
    ]


def build_canonical_reuse_regression_attention(base_dir: Path, task_id: str) -> dict[str, str]:
    baseline = load_json_if_exists(canonical_reuse_regression_path(base_dir, task_id))
    records = load_json_lines_if_exists(canonical_reuse_eval_path(base_dir, task_id))
    current = build_canonical_reuse_regression_current(
        task_id=task_id,
        summary=build_canonical_reuse_evaluation_summary(records),
    )
    comparison = compare_canonical_reuse_regression(baseline=baseline, current=current)
    status = str(comparison.get("status", "match") or "match")
    mismatches = [str(item).strip() for item in comparison.get("mismatches", []) if str(item).strip()]
    mismatch_summary = ", ".join(mismatches[:3]) if mismatches else "-"
    return {
        "status": status,
        "mismatch_count": str(comparison.get("mismatch_count", 0)),
        "summary": "match" if status == "match" else f"mismatch:{comparison.get('mismatch_count', 0)}",
        "mismatches": mismatch_summary,
        "recommended_reason": "canonical_reuse_regression_mismatch" if status != "match" else "canonical_reuse_regression_match",
        "recommended_command": f"swl task canonical-reuse-regression {task_id}",
        "next_operator_action": (
            f"Inspect canonical reuse regression via swl task canonical-reuse-regression {task_id}."
            if status != "match"
            else "No regression mismatch currently detected."
        ),
    }


def build_remote_handoff_attention(base_dir: Path, task_id: str) -> dict[str, object]:
    contract = load_json_if_exists(remote_handoff_contract_path(base_dir, task_id))
    contract_kind = str(contract.get("contract_kind", "not_available") or "not_available")
    contract_status = str(contract.get("contract_status", "not_available") or "not_available")
    handoff_boundary = str(contract.get("handoff_boundary", "unknown") or "unknown")
    dispatch_readiness = str(contract.get("dispatch_readiness", "unknown") or "unknown")
    operator_ack_required = bool(contract.get("operator_ack_required", False))
    needs_attention = contract_kind == "remote_handoff_candidate"
    return {
        "needs_attention": "yes" if needs_attention else "no",
        "contract_kind": contract_kind,
        "contract_status": contract_status,
        "handoff_boundary": handoff_boundary,
        "dispatch_readiness": dispatch_readiness,
        "operator_ack_required": "yes" if operator_ack_required else "no",
        "recommended_reason": (
            "remote_handoff_contract_required" if needs_attention else "remote_handoff_not_needed"
        ),
        "recommended_command": f"swl task remote-handoff {task_id}",
        "next_operator_action": str(contract.get("recommended_next_action", "")).strip() or "Inspect task artifacts.",
        "summary": (
            f"{contract_status}:{handoff_boundary}:{dispatch_readiness}"
            if needs_attention
            else f"{contract_status}:{handoff_boundary}"
        ),
    }


def load_json_if_exists(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_json_lines_if_exists(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    items: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        items.append(json.loads(stripped))
    return items


def build_stage_candidate_list_report(candidates: list[StagedCandidate]) -> str:
    pending_candidates = [candidate for candidate in candidates if candidate.status == "pending"]
    lines = [
        "# Staged Knowledge Review Queue",
        "",
        f"- pending_count: {len(pending_candidates)}",
        "",
        "## Candidates",
    ]
    if not pending_candidates:
        lines.append("- no pending candidates")
        return "\n".join(lines)

    for candidate in pending_candidates:
        preview = candidate.text if len(candidate.text) <= 72 else candidate.text[:69] + "..."
        lines.extend(
            [
                f"- {candidate.candidate_id}",
                f"  source_task_id: {candidate.source_task_id}",
                f"  source_kind: {candidate.source_kind or '-'}",
                f"  source_ref: {candidate.source_ref or '-'}",
                f"  source_object_id: {candidate.source_object_id or 'none'}",
                f"  submitted_by: {candidate.submitted_by or 'unknown'}",
                f"  taxonomy: {candidate.taxonomy_role or '-'} / {candidate.taxonomy_memory_authority or '-'}",
                f"  submitted_at: {candidate.submitted_at}",
                f"  text: {preview or '(empty)'}",
            ]
        )
    return "\n".join(lines)


def build_stage_candidate_inspect_report(candidate: StagedCandidate) -> str:
    return "\n".join(
        [
            f"Staged Candidate: {candidate.candidate_id}",
            f"status: {candidate.status}",
            f"source_task_id: {candidate.source_task_id}",
            f"source_kind: {candidate.source_kind or '-'}",
            f"source_ref: {candidate.source_ref or '-'}",
            f"source_object_id: {candidate.source_object_id or '-'}",
            f"submitted_by: {candidate.submitted_by or '-'}",
            f"submitted_at: {candidate.submitted_at}",
            f"taxonomy_role: {candidate.taxonomy_role or '-'}",
            f"taxonomy_memory_authority: {candidate.taxonomy_memory_authority or '-'}",
            f"decided_at: {candidate.decided_at or '-'}",
            f"decided_by: {candidate.decided_by or '-'}",
            f"decision_note: {candidate.decision_note or '-'}",
            "",
            "Text",
            candidate.text or "(empty)",
        ]
    )


def resolve_stage_candidate(base_dir: Path, candidate_id: str) -> StagedCandidate:
    normalized_id = candidate_id.strip()
    for candidate in load_staged_candidates(base_dir):
        if candidate.candidate_id == normalized_id:
            return candidate
    raise ValueError(f"Unknown staged candidate: {normalized_id}")


def summarize_text_preview(text: str, limit: int) -> str:
    normalized = " ".join(text.split())
    if not normalized:
        return "(empty)"
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(limit - 3, 0)].rstrip() + "..."


def build_task_staged_report(
    candidates: list[StagedCandidate],
    *,
    status_filter: str,
    task_filter: str,
) -> str:
    lines = [
        "# Task Staged Knowledge",
        "",
        f"- count: {len(candidates)}",
        f"- status_filter: {status_filter}",
        f"- task_filter: {task_filter or 'all'}",
        "",
        "## Candidates",
    ]
    if not candidates:
        lines.append("- no matching staged candidates")
        return "\n".join(lines)

    for candidate in candidates:
        lines.extend(
            [
                f"- {candidate.candidate_id}",
                f"  status: {candidate.status}",
                f"  source_task_id: {candidate.source_task_id}",
                f"  submitted_at: {candidate.submitted_at}",
                f"  text: {summarize_text_preview(candidate.text, 80)}",
            ]
        )
    return "\n".join(lines)


def build_stage_canonical_record(
    candidate: StagedCandidate,
    *,
    refined_text: str = "",
) -> dict[str, object]:
    canonical_key = build_staged_canonical_key(
        source_task_id=candidate.source_task_id,
        source_object_id=candidate.source_object_id,
        candidate_id=candidate.candidate_id,
    )
    canonical_text = refined_text.strip() or candidate.text
    return {
        "canonical_id": f"canonical-{candidate.candidate_id}",
        "canonical_key": canonical_key,
        "source_task_id": candidate.source_task_id,
        "source_object_id": candidate.source_object_id,
        "promoted_at": candidate.decided_at,
        "promoted_by": candidate.decided_by or "swl_cli",
        "decision_note": candidate.decision_note,
        "decision_ref": f".swl/staged_knowledge/registry.jsonl#{candidate.candidate_id}",
        "artifact_ref": "",
        "source_ref": candidate.source_ref,
        "text": canonical_text,
        "evidence_status": "source_only",
        "canonical_stage": "canonical",
        "canonical_status": "active",
        "superseded_by": "",
        "superseded_at": "",
    }


def build_stage_promote_preflight_notices(
    canonical_records: list[dict[str, object]],
    candidate: StagedCandidate,
) -> list[dict[str, str]]:
    """Build structured preflight notices for stage promotion decisions.

    The return shape is intentionally `list[dict[str, str]]`. Earlier drafts used
    plain strings, but the CLI has already standardized on structured notice
    records so downstream formatting can stay explicit and stable.
    """
    preview_record = build_stage_canonical_record(candidate)
    canonical_id = str(preview_record.get("canonical_id", "")).strip()
    canonical_key = str(preview_record.get("canonical_key", "")).strip()

    notices: list[dict[str, str]] = []
    existing_record = next(
        (
            record
            for record in canonical_records
            if str(record.get("canonical_id", "")).strip() == canonical_id
        ),
        None,
    )
    if canonical_id and existing_record is not None:
        notices.append(
            {
                "notice_type": "idempotent",
                "canonical_id": canonical_id,
                "text_preview": summarize_text_preview(str(existing_record.get("text", "")), 60),
            }
        )

    if canonical_key:
        active_match = next(
            (
                record
                for record in canonical_records
                if str(record.get("canonical_key", "")).strip() == canonical_key
                and str(record.get("canonical_id", "")).strip() != canonical_id
                and str(record.get("canonical_status", "active")).strip() != "superseded"
            ),
            None,
        )
        if active_match is not None:
            notices.append(
                {
                    "notice_type": "supersede",
                    "canonical_id": str(active_match.get("canonical_id", "")).strip() or "unknown",
                    "text_preview": summarize_text_preview(str(active_match.get("text", "")), 60),
                }
            )
    return notices


def format_stage_promote_preflight_notice(notice: dict[str, str]) -> str:
    notice_type = notice.get("notice_type", "").strip()
    canonical_id = notice.get("canonical_id", "").strip() or "unknown"
    text_preview = notice.get("text_preview", "").strip() or "(empty)"
    if notice_type == "supersede":
        return f"[SUPERSEDE] canonical_id={canonical_id} text={text_preview}"
    if notice_type == "idempotent":
        return f"[IDEMPOTENT] canonical_id={canonical_id} text={text_preview}"
    return f"[NOTICE] canonical_id={canonical_id} text={text_preview}"


def filter_task_states(states: list[object], focus: str) -> list[object]:
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


def build_task_queue_entry(base_dir: Path, state: object) -> dict[str, str] | None:
    handoff = load_json_if_exists(handoff_path(base_dir, state.task_id))
    retry_policy = load_json_if_exists(retry_policy_path(base_dir, state.task_id))
    stop_policy = load_json_if_exists(stop_policy_path(base_dir, state.task_id))
    checkpoint_snapshot = load_checkpoint_snapshot(base_dir, state)
    knowledge_attention = summarize_knowledge_attention(base_dir, state.task_id)
    regression_attention = build_canonical_reuse_regression_attention(base_dir, state.task_id)

    handoff_status = str(handoff.get("status", "pending"))
    next_operator_action = str(handoff.get("next_operator_action", "")).strip()
    checkpoint_kind = str(stop_policy.get("checkpoint_kind", "pending"))
    retryable = bool(retry_policy.get("retryable", False))
    continue_allowed = bool(stop_policy.get("continue_allowed", False))
    stop_required = bool(stop_policy.get("stop_required", False))

    action = ""
    reason = ""
    if regression_attention["status"] != "match":
        action = "inspect"
        reason = regression_attention["recommended_reason"]
        next_operator_action = regression_attention["next_operator_action"]
    elif state.status == "created":
        action = "run"
        reason = "task_created"
    elif state.status == "running":
        action = "monitor"
        reason = state.execution_lifecycle or state.executor_status or "running"
    elif bool(checkpoint_snapshot.get("resume_ready", False)) and str(checkpoint_snapshot.get("recommended_path", "")) == "resume":
        action = "resume"
        reason = str(checkpoint_snapshot.get("recommended_reason", recommended_reason_for_checkpoint(checkpoint_snapshot, handoff_status)))
    elif retryable and continue_allowed:
        action = "retry"
        reason = checkpoint_kind if checkpoint_kind != "pending" else str(retry_policy.get("retry_decision", "retryable"))
    elif handoff_status == "review_completed_run":
        action = "review"
        reason = checkpoint_kind if checkpoint_kind != "pending" else handoff_status
    elif state.status == "failed" or stop_required or handoff_status == "resume_from_failure":
        action = "inspect"
        reason = checkpoint_kind if checkpoint_kind != "pending" else str(stop_policy.get("stop_decision", handoff_status))
    elif knowledge_attention["needs_attention"] == "yes":
        action = "knowledge-review"
        reason = knowledge_attention["recommended_reason"]
        next_operator_action = f"Inspect staged knowledge via {knowledge_attention['recommended_command']}."
    else:
        return None

    if knowledge_attention["needs_attention"] == "yes" and action != "knowledge-review":
        knowledge_next = f"Knowledge review pending via {knowledge_attention['recommended_command']}."
        next_operator_action = f"{next_operator_action} {knowledge_next}".strip()

    return {
        "task_id": state.task_id,
        "action": action,
        "status": state.status,
        "attempt": state.current_attempt_id or "-",
        "updated_at": state.updated_at,
        "reason": reason or "pending",
        "regression": regression_attention["summary"],
        "knowledge": knowledge_attention["summary"],
        "next": next_operator_action or "-",
        "title": state.title,
    }


def recommended_reason_for_checkpoint(checkpoint_snapshot: dict[str, object], handoff_status: str) -> str:
    return str(
        checkpoint_snapshot.get("recommended_reason")
        or checkpoint_snapshot.get("checkpoint_state")
        or handoff_status
        or "pending"
    )


def path_boundary_status(
    *,
    path_name: str,
    allowed: bool,
    reason: str,
    suggested_path: str,
) -> str:
    boundary = "allowed" if allowed else "blocked"
    if suggested_path and suggested_path != path_name:
        return f"{boundary} reason={reason} suggested_path={suggested_path}"
    return f"{boundary} reason={reason}"


def build_control_boundaries(
    state: object,
    checkpoint_snapshot: dict[str, object],
    retry_policy: dict[str, object],
    stop_policy: dict[str, object],
    handoff: dict[str, object],
) -> dict[str, str]:
    suggested_path = str(checkpoint_snapshot.get("recommended_path", "none"))
    suggested_reason = str(
        checkpoint_snapshot.get("recommended_reason")
        or checkpoint_snapshot.get("checkpoint_state")
        or handoff.get("status", "pending")
    )
    retry_allowed = bool(retry_policy.get("retryable", False)) and str(stop_policy.get("checkpoint_kind", "")) in {
        "retry_review",
        "detached_retry_review",
    }
    resume_allowed = bool(checkpoint_snapshot.get("resume_ready", False)) and suggested_path == "resume"
    rerun_allowed = state.status in {"completed", "failed"}
    return {
        "resume": path_boundary_status(
            path_name="resume",
            allowed=resume_allowed,
            reason=suggested_reason if resume_allowed else str(checkpoint_snapshot.get("checkpoint_state", "pending")),
            suggested_path=suggested_path,
        ),
        "retry": path_boundary_status(
            path_name="retry",
            allowed=retry_allowed,
            reason=str(retry_policy.get("retry_decision", suggested_reason)),
            suggested_path=suggested_path,
        ),
        "rerun": path_boundary_status(
            path_name="rerun",
            allowed=rerun_allowed,
            reason="explicit_operator_override" if rerun_allowed else "task_not_terminal",
            suggested_path=suggested_path,
        ),
    }


def load_checkpoint_snapshot(base_dir: Path, state: object) -> dict[str, object]:
    checkpoint_snapshot = load_json_if_exists(checkpoint_snapshot_path(base_dir, state.task_id))
    if checkpoint_snapshot:
        return checkpoint_snapshot
    handoff = load_json_if_exists(handoff_path(base_dir, state.task_id))
    retry_policy = load_json_if_exists(retry_policy_path(base_dir, state.task_id))
    stop_policy = load_json_if_exists(stop_policy_path(base_dir, state.task_id))
    execution_budget_policy = load_json_if_exists(execution_budget_policy_path(base_dir, state.task_id))
    return evaluate_checkpoint_snapshot(state, handoff, retry_policy, stop_policy, execution_budget_policy).to_dict()


def build_task_control_snapshot(base_dir: Path, state: object) -> list[str]:
    handoff = load_json_if_exists(handoff_path(base_dir, state.task_id))
    retry_policy = load_json_if_exists(retry_policy_path(base_dir, state.task_id))
    execution_budget_policy = load_json_if_exists(execution_budget_policy_path(base_dir, state.task_id))
    stop_policy = load_json_if_exists(stop_policy_path(base_dir, state.task_id))
    checkpoint_snapshot = load_checkpoint_snapshot(base_dir, state)
    queue_entry = build_task_queue_entry(base_dir, state)
    knowledge_attention = summarize_knowledge_attention(base_dir, state.task_id)
    regression_attention = build_canonical_reuse_regression_attention(base_dir, state.task_id)
    remote_handoff_attention = build_remote_handoff_attention(base_dir, state.task_id)
    boundaries = build_control_boundaries(
        state,
        checkpoint_snapshot,
        retry_policy,
        stop_policy,
        handoff,
    )

    lines = [
        f"Task Control: {state.task_id}",
        f"title: {state.title}",
        "",
        "Control Snapshot",
        f"recommended_action: {checkpoint_snapshot.get('recommended_path', queue_entry['action'] if queue_entry else 'none')}",
        f"recommended_reason: {checkpoint_snapshot.get('recommended_reason', queue_entry['reason'] if queue_entry else 'no_action_needed')}",
        f"checkpoint_state: {checkpoint_snapshot.get('checkpoint_state', 'pending')}",
        f"execution_phase: {checkpoint_snapshot.get('execution_phase', getattr(state, 'execution_phase', 'pending') or 'pending')}",
        f"last_phase_checkpoint_at: {checkpoint_snapshot.get('last_phase_checkpoint_at', getattr(state, 'last_phase_checkpoint_at', '') or '-')}",
        f"recovery_semantics: {checkpoint_snapshot.get('recovery_semantics', 'pending')}",
        f"interruption_kind: {checkpoint_snapshot.get('interruption_kind', 'none')}",
        f"resume_ready: {'yes' if checkpoint_snapshot.get('resume_ready', False) else 'no'}",
        f"next_operator_action: {handoff.get('next_operator_action', 'Inspect task artifacts.')}",
        f"retry_ready: {'yes' if retry_policy.get('retryable', False) and stop_policy.get('continue_allowed', False) else 'no'}",
        f"review_ready: {'yes' if handoff.get('status', '') == 'review_completed_run' else 'no'}",
        f"rerun_ready: {'yes' if state.status in {'completed', 'failed'} else 'no'}",
        f"monitor_needed: {'yes' if state.status == 'running' else 'no'}",
        f"stop_required: {'yes' if stop_policy.get('stop_required', False) else 'no'}",
        f"continue_allowed: {'yes' if stop_policy.get('continue_allowed', False) else 'no'}",
        "",
        "Knowledge Control",
        f"knowledge_review_needed: {knowledge_attention['needs_attention']}",
        f"knowledge_review_summary: {knowledge_attention['summary']}",
        f"knowledge_review_blocked_reasons: {knowledge_attention['blocked_reasons']}",
        f"knowledge_review_reason: {knowledge_attention['recommended_reason']}",
        f"knowledge_review_command: {knowledge_attention['recommended_command']}",
        "",
        "Regression Control",
        f"canonical_reuse_regression_status: {regression_attention['status']}",
        f"canonical_reuse_regression_mismatch_count: {regression_attention['mismatch_count']}",
        f"canonical_reuse_regression_mismatches: {regression_attention['mismatches']}",
        f"canonical_reuse_regression_reason: {regression_attention['recommended_reason']}",
        f"canonical_reuse_regression_command: {regression_attention['recommended_command']}",
        "",
        "Remote Handoff Control",
        f"remote_handoff_needed: {remote_handoff_attention['needs_attention']}",
        f"remote_handoff_summary: {remote_handoff_attention['summary']}",
        f"remote_handoff_contract_kind: {remote_handoff_attention['contract_kind']}",
        f"remote_handoff_contract_status: {remote_handoff_attention['contract_status']}",
        f"remote_handoff_boundary: {remote_handoff_attention['handoff_boundary']}",
        f"remote_handoff_dispatch_readiness: {remote_handoff_attention['dispatch_readiness']}",
        f"remote_handoff_operator_ack_required: {remote_handoff_attention['operator_ack_required']}",
        f"remote_handoff_reason: {remote_handoff_attention['recommended_reason']}",
        f"remote_handoff_command: {remote_handoff_attention['recommended_command']}",
        "",
        "Control Boundaries",
        f"resume_path: {boundaries['resume']}",
        f"retry_path: {boundaries['retry']}",
        f"rerun_path: {boundaries['rerun']}",
        "",
    ]
    lines.extend(build_policy_snapshot(retry_policy, execution_budget_policy, stop_policy))
    lines.extend(
        [
            "",
            "Control Artifacts",
            f"review: swl task review {state.task_id}",
            f"knowledge_review: swl task knowledge-review-queue {state.task_id}",
            f"canonical_reuse_regression: swl task canonical-reuse-regression {state.task_id}",
            f"remote_handoff: swl task remote-handoff {state.task_id}",
            f"resume: swl task resume {state.task_id}",
            f"policy: swl task policy {state.task_id}",
            f"checkpoint: swl task checkpoint {state.task_id}",
            f"inspect: swl task inspect {state.task_id}",
            f"run: swl task run {state.task_id}",
            f"resume_note: {state.artifact_paths.get('resume_note', '-')}",
            f"handoff_report: {state.artifact_paths.get('handoff_report', '-')}",
            f"remote_handoff_contract_report: {state.artifact_paths.get('remote_handoff_contract_report', '-')}",
            f"retry_policy_report: {state.artifact_paths.get('retry_policy_report', '-')}",
            f"execution_budget_policy_report: {state.artifact_paths.get('execution_budget_policy_report', '-')}",
            f"stop_policy_report: {state.artifact_paths.get('stop_policy_report', '-')}",
            f"checkpoint_snapshot_report: {state.artifact_paths.get('checkpoint_snapshot_report', '-')}",
        ]
    )
    return lines


def build_attempt_summaries(base_dir: Path, task_id: str) -> list[dict[str, str]]:
    events = load_events(base_dir, task_id)
    attempts: dict[str, dict[str, str]] = {}
    attempt_order: list[str] = []
    for event in events:
        payload = event.get("payload", {})
        if not isinstance(payload, dict):
            payload = {}
        attempt_id = str(payload.get("attempt_id", "")).strip()
        if not attempt_id:
            continue
        if attempt_id not in attempts:
            attempts[attempt_id] = {
                "attempt_id": attempt_id,
                "attempt_number": str(payload.get("attempt_number", 0)),
                "started_at": str(event.get("created_at", "-")),
                "finished_at": "-",
                "status": "running",
                "executor_status": str(payload.get("executor_status", "pending")),
                "execution_lifecycle": str(payload.get("execution_lifecycle", "pending")),
                "retrieval_count": str(payload.get("retrieval_count", 0)),
                "compatibility_status": str(payload.get("compatibility_status", "pending")),
                "execution_fit_status": str(payload.get("execution_fit_status", "pending")),
                "retry_policy_status": str(payload.get("retry_policy_status", "pending")),
                "stop_policy_status": str(payload.get("stop_policy_status", "pending")),
                "handoff_status": "pending",
            }
            attempt_order.append(attempt_id)
        summary = attempts[attempt_id]
        event_type = str(event.get("event_type", ""))
        summary["attempt_number"] = str(payload.get("attempt_number", summary["attempt_number"]))
        if event_type == "task.run_started":
            summary["started_at"] = str(event.get("created_at", summary["started_at"]))
            summary["executor_status"] = str(payload.get("executor_status", summary["executor_status"]))
            summary["execution_lifecycle"] = str(payload.get("execution_lifecycle", summary["execution_lifecycle"]))
        elif event_type in {"task.completed", "task.failed"}:
            summary["finished_at"] = str(event.get("created_at", summary["finished_at"]))
            summary["status"] = str(payload.get("status", summary["status"]))
            summary["executor_status"] = str(payload.get("executor_status", summary["executor_status"]))
            summary["execution_lifecycle"] = str(payload.get("execution_lifecycle", summary["execution_lifecycle"]))
            summary["retrieval_count"] = str(payload.get("retrieval_count", summary["retrieval_count"]))
            summary["compatibility_status"] = str(payload.get("compatibility_status", summary["compatibility_status"]))
            summary["execution_fit_status"] = str(payload.get("execution_fit_status", summary["execution_fit_status"]))
            summary["retry_policy_status"] = str(payload.get("retry_policy_status", summary["retry_policy_status"]))
            summary["stop_policy_status"] = str(payload.get("stop_policy_status", summary["stop_policy_status"]))

    handoff = load_json_if_exists(handoff_path(base_dir, task_id))
    latest_handoff_attempt = str(handoff.get("attempt_id", "")).strip()
    if latest_handoff_attempt in attempts:
        attempts[latest_handoff_attempt]["handoff_status"] = str(handoff.get("status", "pending"))

    return [attempts[attempt_id] for attempt_id in reversed(attempt_order)]


def resolve_attempt_pair(attempts: list[dict[str, str]], left: str | None, right: str | None) -> tuple[dict[str, str], dict[str, str]]:
    by_id = {attempt["attempt_id"]: attempt for attempt in attempts}
    if left and right:
        if left not in by_id or right not in by_id:
            raise ValueError("Unknown attempt id for comparison.")
        return by_id[left], by_id[right]
    if len(attempts) < 2:
        raise ValueError("At least two attempts are required for comparison.")
    return attempts[1], attempts[0]


def execute_task_run(
    base_dir: Path,
    task_id: str,
    executor_name: str | None,
    capability_refs: list[str] | None,
    route_mode: str | None,
    reset_grounding: bool = False,
    skip_to_phase: str = "retrieval",
) -> int:
    state = run_task(
        base_dir=base_dir,
        task_id=task_id,
        executor_name=executor_name,
        capability_refs=capability_refs,
        route_mode=route_mode,
        reset_grounding=reset_grounding,
        skip_to_phase=skip_to_phase,
    )
    print(
        f"{state.task_id} {state.status} retrieval={state.retrieval_count} "
        f"execution_phase={state.execution_phase}"
    )
    return 0


def is_acknowledged_dispatch_reentry(state: object) -> bool:
    return (
        getattr(state, "status", "") == "running"
        and getattr(state, "phase", "") == "retrieval"
        and getattr(state, "topology_dispatch_status", "") == "acknowledged"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="swl",
        description="CLI for the swallow stateful AI workflow system.",
    )
    parser.add_argument(
        "--base-dir",
        default=".",
        help="Directory that stores the .swl task state and artifacts. Defaults to the current directory.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser("audit", help="Consistency audit policy and operator commands.")
    audit_subparsers = audit_parser.add_subparsers(dest="audit_command", required=True)
    audit_policy_parser = audit_subparsers.add_parser(
        "policy",
        help="Inspect or update the automatic consistency-audit trigger policy.",
    )
    audit_policy_subparsers = audit_policy_parser.add_subparsers(dest="audit_policy_command", required=True)
    audit_policy_subparsers.add_parser("show", help="Print the current audit trigger policy.")
    audit_policy_set_parser = audit_policy_subparsers.add_parser(
        "set",
        help="Update the automatic consistency-audit trigger policy.",
    )
    audit_policy_set_parser.set_defaults(enabled=None, trigger_on_degraded=None)
    audit_policy_set_parser.add_argument(
        "--enabled",
        dest="enabled",
        action="store_true",
        help="Enable automatic consistency-audit triggering.",
    )
    audit_policy_set_parser.add_argument(
        "--disabled",
        dest="enabled",
        action="store_false",
        help="Disable automatic consistency-audit triggering.",
    )
    audit_policy_set_parser.add_argument(
        "--trigger-on-degraded",
        dest="trigger_on_degraded",
        action="store_true",
        help="Trigger audits when the latest executor event is degraded.",
    )
    audit_policy_set_parser.add_argument(
        "--no-trigger-on-degraded",
        dest="trigger_on_degraded",
        action="store_false",
        help="Stop triggering audits on degraded executor events.",
    )
    audit_policy_set_parser.add_argument(
        "--trigger-on-cost-above",
        type=float,
        default=None,
        help="Trigger audits when the latest executor event token_cost meets or exceeds this threshold.",
    )
    audit_policy_set_parser.add_argument(
        "--clear-trigger-on-cost-above",
        action="store_true",
        help="Clear any configured token_cost threshold.",
    )
    audit_policy_set_parser.add_argument(
        "--auditor-route",
        default=None,
        help="Route name used for automatic consistency audits.",
    )

    route_parser = subparsers.add_parser("route", help="Route registry and operator weight commands.")
    route_subparsers = route_parser.add_subparsers(dest="route_command", required=True)
    route_weights_parser = route_subparsers.add_parser(
        "weights",
        help="Inspect or apply per-route quality weights.",
    )
    route_weights_subparsers = route_weights_parser.add_subparsers(dest="route_weights_command", required=True)
    route_weights_subparsers.add_parser("show", help="Print current route quality weights.")
    route_weights_apply_parser = route_weights_subparsers.add_parser(
        "apply",
        help="Apply route_weight proposals from a meta-optimizer proposal file.",
    )
    route_weights_apply_parser.add_argument("proposal_file", help="Path to a meta-optimizer proposal markdown file.")

    task_parser = subparsers.add_parser("task", help="Task workbench and lifecycle commands.")
    task_subparsers = task_parser.add_subparsers(dest="task_command", required=True)
    knowledge_parser = subparsers.add_parser("knowledge", help="Global staged knowledge review commands.")
    knowledge_subparsers = knowledge_parser.add_subparsers(dest="knowledge_command", required=True)
    doctor_parser = subparsers.add_parser("doctor", help="Diagnostic commands.")
    doctor_parser.add_argument(
        "--skip-stack",
        action="store_true",
        help="Skip local Docker / WireGuard / proxy health checks.",
    )
    doctor_subparsers = doctor_parser.add_subparsers(dest="doctor_command", required=False)
    migrate_parser = subparsers.add_parser(
        "migrate",
        help="Backfill file-based task state into the SQLite store.",
        description="Backfill legacy file-based task state and events into the SQLite store.",
    )
    migrate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan file-based task state and report migration candidates without writing SQLite records.",
    )
    meta_optimize_parser = subparsers.add_parser(
        "meta-optimize",
        help="Scan recent task event logs and emit a read-only optimization proposal report.",
        description="Scan recent task event logs and emit a read-only optimization proposal report.",
    )
    meta_optimize_parser.add_argument(
        "--last-n",
        type=int,
        default=100,
        help="Maximum number of recent task event logs to scan. Defaults to 100.",
    )
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Ingest an external session export into staged knowledge.",
        description="Parse an external session export, filter it into staged candidates, and optionally persist them.",
    )
    ingest_parser.add_argument("source_path", help="Path to the source export file.")
    ingest_parser.add_argument(
        "--format",
        choices=("chatgpt_json", "claude_json", "open_webui_json", "markdown"),
        default=None,
        help="Optional explicit input format override.",
    )
    ingest_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and filter the source, but do not write staged candidates.",
    )
    ingest_parser.add_argument(
        "--summary",
        action="store_true",
        help="Append a structured ingestion summary after the standard report.",
    )
    serve_parser = subparsers.add_parser(
        "serve",
        help="Run the read-only control center API server.",
        description="Run the read-only control center API server.",
    )
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind. Defaults to 127.0.0.1.")
    serve_parser.add_argument("--port", type=int, default=8037, help="Port to bind. Defaults to 8037.")

    knowledge_stage_list_parser = knowledge_subparsers.add_parser(
        "stage-list",
        help="List pending staged knowledge candidates.",
        description="List pending staged knowledge candidates.",
    )
    knowledge_stage_list_parser.add_argument(
        "--all",
        action="store_true",
        help="Include decided staged candidates in the output.",
    )
    knowledge_stage_inspect_parser = knowledge_subparsers.add_parser(
        "stage-inspect",
        help="Inspect one staged knowledge candidate.",
        description="Inspect one staged knowledge candidate.",
    )
    knowledge_stage_inspect_parser.add_argument("candidate_id", help="Staged candidate identifier.")
    knowledge_stage_promote_parser = knowledge_subparsers.add_parser(
        "stage-promote",
        help="Promote one pending staged candidate into the canonical registry.",
        description="Promote one pending staged candidate into the canonical registry.",
    )
    knowledge_stage_promote_parser.add_argument("candidate_id", help="Staged candidate identifier.")
    knowledge_stage_promote_parser.add_argument("--note", default="", help="Optional operator note for the promotion record.")
    knowledge_stage_promote_parser.add_argument(
        "--text",
        default="",
        help="Optional refined canonical text to use for this promotion without mutating the staged candidate.",
    )
    knowledge_stage_promote_parser.add_argument(
        "--force",
        action="store_true",
        help="Allow promotion to proceed when it would supersede an existing active canonical record.",
    )
    knowledge_stage_reject_parser = knowledge_subparsers.add_parser(
        "stage-reject",
        help="Reject one pending staged candidate.",
        description="Reject one pending staged candidate.",
    )
    knowledge_stage_reject_parser.add_argument("candidate_id", help="Staged candidate identifier.")
    knowledge_stage_reject_parser.add_argument("--note", default="", help="Optional operator note for the rejection record.")
    knowledge_subparsers.add_parser(
        "canonical-audit",
        help="Audit canonical registry health.",
        description="Audit canonical registry health.",
    )
    knowledge_migrate_parser = knowledge_subparsers.add_parser(
        "migrate",
        help="Backfill file-based knowledge into the SQLite knowledge store.",
        description="Backfill legacy file-based knowledge objects into the SQLite knowledge store.",
    )
    knowledge_migrate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan file-based knowledge and report migration candidates without writing SQLite records.",
    )

    create_parser = task_subparsers.add_parser("create", help="Create a task.")
    create_parser.add_argument("--title", required=True, help="Short task title.")
    create_parser.add_argument("--goal", required=True, help="Concrete task goal.")
    create_parser.add_argument(
        "--workspace-root",
        default=".",
        help="Workspace to retrieve context from. Defaults to the current directory.",
    )
    create_parser.add_argument(
        "--executor",
        default="codex",
        help="Executor to persist for the task. Defaults to codex.",
    )
    create_parser.add_argument(
        "--constraint",
        action="append",
        default=[],
        help="Imported planning constraint to attach to task semantics. Repeatable.",
    )
    create_parser.add_argument(
        "--acceptance-criterion",
        action="append",
        default=[],
        help="Imported acceptance criterion to attach to task semantics. Repeatable.",
    )
    create_parser.add_argument(
        "--priority-hint",
        action="append",
        default=[],
        help="Imported priority hint to attach to task semantics. Repeatable.",
    )
    create_parser.add_argument(
        "--next-action-proposal",
        action="append",
        default=[],
        help="Imported next action proposal to attach to task semantics. Repeatable.",
    )
    create_parser.add_argument(
        "--planning-source",
        default="",
        help="Optional external planning source reference for task semantics.",
    )
    create_parser.add_argument(
        "--knowledge-item",
        action="append",
        default=[],
        help="External knowledge fragment to attach as a staged knowledge object. Repeatable.",
    )
    create_parser.add_argument(
        "--knowledge-stage",
        default="raw",
        choices=["raw", "candidate", "verified", "canonical"],
        help="Initial stage for imported knowledge objects. Defaults to raw.",
    )
    create_parser.add_argument(
        "--knowledge-source",
        default="",
        help="Optional external source reference for imported knowledge objects.",
    )
    create_parser.add_argument(
        "--knowledge-artifact-ref",
        action="append",
        default=[],
        help="Optional artifact-backed evidence reference for each imported knowledge object. Repeatable and aligned by order.",
    )
    create_parser.add_argument(
        "--knowledge-retrieval-eligible",
        action="store_true",
        help="Declare imported knowledge objects as retrieval-eligible candidates without automatically enabling retrieval reuse.",
    )
    create_parser.add_argument(
        "--knowledge-canonicalization-intent",
        default="none",
        choices=["none", "review", "promote"],
        help="Optional canonicalization intent for imported knowledge objects. This does not promote them automatically.",
    )
    create_parser.add_argument(
        "--capability",
        action="append",
        default=[],
        help="Capability reference to persist with the task, for example profile:baseline_local or validator:run_output_validation. Repeatable.",
    )
    create_parser.add_argument(
        "--route-mode",
        default="auto",
        choices=["auto", "live", "deterministic", "detached", "offline", "summary"],
        help="Routing policy mode to persist for the task. Defaults to auto.",
    )
    planning_handoff_parser = task_subparsers.add_parser(
        "planning-handoff",
        help="Attach or tighten imported planning semantics for an existing task.",
        description="Attach or tighten imported planning semantics for an existing task.",
    )
    planning_handoff_parser.add_argument("task_id", help="Task identifier.")
    planning_handoff_parser.add_argument(
        "--planning-source",
        default="",
        help="Optional external planning source reference for task semantics.",
    )
    planning_handoff_parser.add_argument(
        "--constraint",
        action="append",
        default=[],
        help="Imported planning constraint to attach to task semantics. Repeatable.",
    )
    planning_handoff_parser.add_argument(
        "--acceptance-criterion",
        action="append",
        default=[],
        help="Imported acceptance criterion to attach to task semantics. Repeatable.",
    )
    planning_handoff_parser.add_argument(
        "--priority-hint",
        action="append",
        default=[],
        help="Imported priority hint to attach to task semantics. Repeatable.",
    )
    planning_handoff_parser.add_argument(
        "--next-action-proposal",
        action="append",
        default=[],
        help="Imported next action proposal to attach to task semantics. Repeatable.",
    )
    knowledge_capture_parser = task_subparsers.add_parser(
        "knowledge-capture",
        help="Attach staged knowledge objects to an existing task.",
        description="Attach staged knowledge objects to an existing task.",
    )
    knowledge_capture_parser.add_argument("task_id", help="Task identifier.")
    knowledge_capture_parser.add_argument(
        "--knowledge-item",
        action="append",
        default=[],
        help="External knowledge fragment to attach as a staged knowledge object. Repeatable.",
    )
    knowledge_capture_parser.add_argument(
        "--knowledge-stage",
        default="raw",
        choices=["raw", "candidate", "verified", "canonical"],
        help="Stage for imported knowledge objects. Defaults to raw.",
    )
    knowledge_capture_parser.add_argument(
        "--knowledge-source",
        default="",
        help="Optional external source reference for imported knowledge objects.",
    )
    knowledge_capture_parser.add_argument(
        "--knowledge-artifact-ref",
        action="append",
        default=[],
        help="Optional artifact-backed evidence reference for each imported knowledge object. Repeatable and aligned by order.",
    )
    knowledge_capture_parser.add_argument(
        "--knowledge-retrieval-eligible",
        action="store_true",
        help="Declare imported knowledge objects as retrieval-eligible candidates without automatically enabling retrieval reuse.",
    )
    knowledge_capture_parser.add_argument(
        "--knowledge-canonicalization-intent",
        default="none",
        choices=["none", "review", "promote"],
        help="Optional canonicalization intent for imported knowledge objects. This does not promote them automatically.",
    )

    run_parser = task_subparsers.add_parser("run", help="Run a task through the current workflow loop.")
    run_parser.add_argument("task_id", help="Task identifier.")
    run_parser.add_argument(
        "--executor",
        default=None,
        help="Override the task executor for this run.",
    )
    run_parser.add_argument(
        "--capability",
        action="append",
        default=[],
        help="Override the task capability manifest for this run with repeatable kind:ref entries.",
    )
    run_parser.add_argument(
        "--route-mode",
        default=None,
        choices=["auto", "live", "deterministic", "detached", "offline", "summary"],
        help="Override the task routing policy mode for this run.",
    )
    retry_parser = task_subparsers.add_parser(
        "retry",
        help="Retry a task on the accepted run path when retry and stop policy allow it.",
        description="Retry a task on the accepted run path when retry and stop policy allow it.",
    )
    retry_parser.add_argument("task_id", help="Task identifier.")
    retry_parser.add_argument(
        "--executor",
        default=None,
        help="Override the task executor for this retry.",
    )
    retry_parser.add_argument(
        "--capability",
        action="append",
        default=None,
        help="Override the task capability manifest for this retry with repeatable kind:ref entries.",
    )
    retry_parser.add_argument(
        "--route-mode",
        default=None,
        choices=["auto", "live", "deterministic", "detached", "offline", "summary"],
        help="Override the task routing policy mode for this retry.",
    )
    retry_parser.add_argument(
        "--from-phase",
        default="retrieval",
        choices=["retrieval", "execution", "analysis"],
        help="Selective retry checkpoint to restart from. Defaults to retrieval.",
    )
    resume_parser = task_subparsers.add_parser(
        "resume",
        help="Resume a task on the accepted run path when checkpoint recovery truth allows it.",
        description="Resume a task on the accepted run path when checkpoint recovery truth allows it.",
    )
    resume_parser.add_argument("task_id", help="Task identifier.")
    resume_parser.add_argument(
        "--executor",
        default=None,
        help="Override the task executor for this resume attempt.",
    )
    resume_parser.add_argument(
        "--capability",
        action="append",
        default=None,
        help="Override the task capability manifest for this resume attempt with repeatable kind:ref entries.",
    )
    resume_parser.add_argument(
        "--route-mode",
        default=None,
        choices=["auto", "live", "deterministic", "detached", "offline", "summary"],
        help="Override the task routing policy mode for this resume attempt.",
    )
    rerun_parser = task_subparsers.add_parser(
        "rerun",
        help="Start a new explicit operator-triggered run even when retry or resume stay blocked.",
        description="Start a new explicit operator-triggered run even when retry or resume stay blocked.",
    )
    rerun_parser.add_argument("task_id", help="Task identifier.")
    rerun_parser.add_argument(
        "--executor",
        default=None,
        help="Override the task executor for this rerun.",
    )
    rerun_parser.add_argument(
        "--capability",
        action="append",
        default=None,
        help="Override the task capability manifest for this rerun with repeatable kind:ref entries.",
    )
    rerun_parser.add_argument(
        "--route-mode",
        default=None,
        choices=["auto", "live", "deterministic", "detached", "offline", "summary"],
        help="Override the task routing policy mode for this rerun.",
    )
    rerun_parser.add_argument(
        "--from-phase",
        default="retrieval",
        choices=["retrieval", "execution", "analysis"],
        help="Selective rerun checkpoint to restart from. Defaults to retrieval.",
    )
    acknowledge_parser = task_subparsers.add_parser(
        "acknowledge",
        help="Force a dispatch_blocked task onto the local execution path after operator review.",
        description="Force a dispatch_blocked task onto the local execution path after operator review.",
    )
    acknowledge_parser.add_argument("task_id", help="Task identifier.")

    list_parser = task_subparsers.add_parser("list", help="List tasks with compact status summaries.")
    list_parser.add_argument(
        "--focus",
        default="all",
        choices=["all", "active", "failed", "needs-review", "recent"],
        help="Restrict the list to a simple operator attention view. Defaults to all.",
    )
    list_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of tasks to print after filtering.",
    )
    queue_parser = task_subparsers.add_parser(
        "queue", help="List tasks that currently need operator action, including resume/retry/review."
    )
    queue_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of queue entries to print.",
    )
    attempts_parser = task_subparsers.add_parser("attempts", help="Print compact attempt history for a task.")
    attempts_parser.add_argument("task_id", help="Task identifier.")
    compare_attempts_parser = task_subparsers.add_parser(
        "compare-attempts", help="Compare two task attempts using compact control-relevant fields."
    )
    compare_attempts_parser.add_argument("task_id", help="Task identifier.")
    compare_attempts_parser.add_argument("--left", default=None, help="Left attempt id. Defaults to the prior attempt.")
    compare_attempts_parser.add_argument("--right", default=None, help="Right attempt id. Defaults to the latest attempt.")
    control_parser = task_subparsers.add_parser(
        "control", help="Print a compact per-task recovery and control snapshot."
    )
    control_parser.add_argument("task_id", help="Task identifier.")
    intake_parser = task_subparsers.add_parser(
        "intake",
        help="Print a compact planning-handoff and staged-knowledge intake snapshot.",
        description="Print a compact planning-handoff and staged-knowledge intake snapshot.",
    )
    intake_parser.add_argument("task_id", help="Task identifier.")
    task_staged_parser = task_subparsers.add_parser(
        "staged",
        help="Print a compact staged knowledge queue with optional task and status filters.",
        description="Print a compact staged knowledge queue with optional task and status filters.",
    )
    task_staged_parser.add_argument(
        "--status",
        default="pending",
        choices=["pending", "promoted", "rejected", "all"],
        help="Restrict the queue to one staged candidate status. Defaults to pending.",
    )
    task_staged_parser.add_argument(
        "--task",
        default="",
        help="Restrict the queue to one source task identifier.",
    )
    inspect_parser = task_subparsers.add_parser("inspect", help="Print a compact per-task overview.")
    inspect_parser.add_argument("task_id", help="Task identifier.")
    semantics_parser = task_subparsers.add_parser("semantics", help="Print the task semantics report artifact.")
    semantics_parser.add_argument("task_id", help="Task identifier.")
    capabilities_parser = task_subparsers.add_parser("capabilities", help="Print the task capability assembly summary.")
    capabilities_parser.add_argument("task_id", help="Task identifier.")
    knowledge_objects_parser = task_subparsers.add_parser(
        "knowledge-objects", help="Print the task knowledge-objects report artifact."
    )
    knowledge_objects_parser.add_argument("task_id", help="Task identifier.")
    knowledge_partition_parser = task_subparsers.add_parser(
        "knowledge-partition", help="Print the task knowledge-partition report artifact."
    )
    knowledge_partition_parser.add_argument("task_id", help="Task identifier.")
    knowledge_index_parser = task_subparsers.add_parser(
        "knowledge-index", help="Print the task knowledge-index report artifact."
    )
    knowledge_index_parser.add_argument("task_id", help="Task identifier.")
    knowledge_policy_parser = task_subparsers.add_parser(
        "knowledge-policy", help="Print the task knowledge-policy report artifact."
    )
    knowledge_policy_parser.add_argument("task_id", help="Task identifier.")
    knowledge_review_queue_parser = task_subparsers.add_parser(
        "knowledge-review-queue",
        help="Print a compact review queue for staged knowledge objects.",
        description="Print a compact review queue for staged knowledge objects.",
    )
    knowledge_review_queue_parser.add_argument("task_id", help="Task identifier.")
    knowledge_promote_parser = task_subparsers.add_parser(
        "knowledge-promote",
        help="Explicitly promote one knowledge object toward reusable or canonical state.",
        description="Explicitly promote one knowledge object toward reusable or canonical state.",
    )
    knowledge_promote_parser.add_argument("task_id", help="Task identifier.")
    knowledge_promote_parser.add_argument("object_id", help="Knowledge object identifier.")
    knowledge_promote_parser.add_argument(
        "--target",
        required=True,
        choices=["reuse", "canonical"],
        help="Promotion target.",
    )
    knowledge_promote_parser.add_argument("--note", default="", help="Optional operator note for the decision record.")
    knowledge_reject_parser = task_subparsers.add_parser(
        "knowledge-reject",
        help="Explicitly reject one knowledge object from reusable or canonical promotion.",
        description="Explicitly reject one knowledge object from reusable or canonical promotion.",
    )
    knowledge_reject_parser.add_argument("task_id", help="Task identifier.")
    knowledge_reject_parser.add_argument("object_id", help="Knowledge object identifier.")
    knowledge_reject_parser.add_argument(
        "--target",
        required=True,
        choices=["reuse", "canonical"],
        help="Rejection target.",
    )
    knowledge_reject_parser.add_argument("--note", default="", help="Optional operator note for the decision record.")
    knowledge_decisions_parser = task_subparsers.add_parser(
        "knowledge-decisions", help="Print the task knowledge decision record artifact."
    )
    knowledge_decisions_parser.add_argument("task_id", help="Task identifier.")
    canonical_registry_parser = task_subparsers.add_parser(
        "canonical-registry",
        help="Print the canonical knowledge registry report.",
        description="Print the canonical knowledge registry report.",
    )
    canonical_registry_parser.add_argument("task_id", help="Task identifier used for workspace selection.")
    canonical_registry_index_parser = task_subparsers.add_parser(
        "canonical-registry-index",
        help="Print the canonical knowledge registry index report.",
        description="Print the canonical knowledge registry index report.",
    )
    canonical_registry_index_parser.add_argument("task_id", help="Task identifier used for workspace selection.")
    canonical_reuse_parser = task_subparsers.add_parser(
        "canonical-reuse",
        help="Print the canonical reuse policy report.",
        description="Print the canonical reuse policy report.",
    )
    canonical_reuse_parser.add_argument("task_id", help="Task identifier used for workspace selection.")
    canonical_reuse_regression_parser = task_subparsers.add_parser(
        "canonical-reuse-regression",
        help="Print the canonical reuse regression compare report.",
        description="Print the canonical reuse regression compare report.",
    )
    canonical_reuse_regression_parser.add_argument("task_id", help="Task identifier used for workspace selection.")
    canonical_reuse_eval_parser = task_subparsers.add_parser(
        "canonical-reuse-eval",
        help="Print the canonical reuse evaluation report.",
        description="Print the canonical reuse evaluation report.",
    )
    canonical_reuse_eval_parser.add_argument("task_id", help="Task identifier used for workspace selection.")
    canonical_reuse_evaluate_parser = task_subparsers.add_parser(
        "canonical-reuse-evaluate",
        help="Record an explicit canonical reuse evaluation judgment for this task.",
        description="Record an explicit canonical reuse evaluation judgment for this task.",
    )
    canonical_reuse_evaluate_parser.add_argument("task_id", help="Task identifier.")
    canonical_reuse_evaluate_parser.add_argument(
        "--citation",
        action="append",
        required=True,
        help="Canonical retrieval citation to evaluate. Repeat to record multiple citations in one judgment.",
    )
    canonical_reuse_evaluate_parser.add_argument(
        "--judgment",
        required=True,
        choices=["useful", "noisy", "needs_review"],
        help="Evaluation judgment.",
    )
    canonical_reuse_evaluate_parser.add_argument("--note", default="", help="Optional operator note for the evaluation record.")
    consistency_audit_parser = task_subparsers.add_parser(
        "consistency-audit",
        help="Run a manual cross-model consistency audit against an existing task artifact.",
        description="Run a manual cross-model consistency audit against an existing task artifact.",
    )
    consistency_audit_parser.add_argument("task_id", help="Task identifier.")
    consistency_audit_parser.add_argument(
        "--auditor-route",
        required=True,
        help="Route name used for the audit request, for example http-claude.",
    )
    consistency_audit_parser.add_argument(
        "--artifact",
        default="executor_output.md",
        help="Artifact filename or path to audit. Relative paths resolve under the task artifacts directory.",
    )
    review_parser = task_subparsers.add_parser("review", help="Print a review-focused task handoff summary.")
    review_parser.add_argument("task_id", help="Task identifier.")
    checkpoint_parser = task_subparsers.add_parser(
        "checkpoint",
        help="Print the task checkpoint snapshot report used for resume, retry, review, and rerun guidance.",
        description="Print the task checkpoint snapshot report used for resume, retry, review, and rerun guidance.",
    )
    checkpoint_parser.add_argument("task_id", help="Task identifier.")
    policy_parser = task_subparsers.add_parser("policy", help="Print a compact execution-control policy summary.")
    policy_parser.add_argument("task_id", help="Task identifier.")
    artifacts_parser = task_subparsers.add_parser("artifacts", help="Print grouped task artifact paths.")
    artifacts_parser.add_argument("task_id", help="Task identifier.")

    summarize_parser = task_subparsers.add_parser("summarize", help="Print the task summary artifact.")
    summarize_parser.add_argument("task_id", help="Task identifier.")

    resume_note_parser = task_subparsers.add_parser(
        "resume-note",
        help="Print the task resume note artifact.",
    )
    resume_note_parser.add_argument("task_id", help="Task identifier.")
    validation_parser = task_subparsers.add_parser("validation", help="Print the task validation report artifact.")
    validation_parser.add_argument("task_id", help="Task identifier.")
    compatibility_parser = task_subparsers.add_parser(
        "compatibility",
        help="Print the task compatibility report artifact.",
    )
    compatibility_parser.add_argument("task_id", help="Task identifier.")
    grounding_parser = task_subparsers.add_parser("grounding", help="Print the task source grounding artifact.")
    grounding_parser.add_argument("task_id", help="Task identifier.")
    retrieval_parser = task_subparsers.add_parser("retrieval", help="Print the task retrieval report artifact.")
    retrieval_parser.add_argument("task_id", help="Task identifier.")
    topology_parser = task_subparsers.add_parser("topology", help="Print the task topology report artifact.")
    topology_parser.add_argument("task_id", help="Task identifier.")
    execution_site_parser = task_subparsers.add_parser(
        "execution-site",
        help="Print the task execution-site report artifact.",
    )
    execution_site_parser.add_argument("task_id", help="Task identifier.")
    dispatch_parser = task_subparsers.add_parser("dispatch", help="Print the task dispatch report artifact.")
    dispatch_parser.add_argument("task_id", help="Task identifier.")
    handoff_parser = task_subparsers.add_parser("handoff", help="Print the task handoff report artifact.")
    handoff_parser.add_argument("task_id", help="Task identifier.")
    remote_handoff_parser = task_subparsers.add_parser(
        "remote-handoff",
        help="Print the task remote handoff contract report artifact.",
    )
    remote_handoff_parser.add_argument("task_id", help="Task identifier.")
    execution_fit_parser = task_subparsers.add_parser(
        "execution-fit",
        help="Print the task execution-fit report artifact.",
    )
    execution_fit_parser.add_argument("task_id", help="Task identifier.")
    retry_policy_parser = task_subparsers.add_parser(
        "retry-policy",
        help="Print the task retry-policy report artifact.",
    )
    retry_policy_parser.add_argument("task_id", help="Task identifier.")
    execution_budget_policy_parser = task_subparsers.add_parser(
        "execution-budget-policy",
        help="Print the task execution-budget-policy report artifact.",
    )
    execution_budget_policy_parser.add_argument("task_id", help="Task identifier.")
    stop_policy_parser = task_subparsers.add_parser(
        "stop-policy",
        help="Print the task stop-policy report artifact.",
    )
    stop_policy_parser.add_argument("task_id", help="Task identifier.")
    memory_parser = task_subparsers.add_parser("memory", help="Print the task memory record.")
    memory_parser.add_argument("task_id", help="Task identifier.")
    route_parser = task_subparsers.add_parser("route", help="Print the task route report artifact.")
    route_parser.add_argument("task_id", help="Task identifier.")
    compatibility_json_parser = task_subparsers.add_parser(
        "compatibility-json",
        help="Print the task compatibility record.",
    )
    compatibility_json_parser.add_argument("task_id", help="Task identifier.")
    route_json_parser = task_subparsers.add_parser("route-json", help="Print the task route record.")
    route_json_parser.add_argument("task_id", help="Task identifier.")
    topology_json_parser = task_subparsers.add_parser("topology-json", help="Print the task topology record.")
    topology_json_parser.add_argument("task_id", help="Task identifier.")
    execution_site_json_parser = task_subparsers.add_parser(
        "execution-site-json",
        help="Print the task execution-site record.",
    )
    execution_site_json_parser.add_argument("task_id", help="Task identifier.")
    dispatch_json_parser = task_subparsers.add_parser("dispatch-json", help="Print the task dispatch record.")
    dispatch_json_parser.add_argument("task_id", help="Task identifier.")
    handoff_json_parser = task_subparsers.add_parser("handoff-json", help="Print the task handoff record.")
    handoff_json_parser.add_argument("task_id", help="Task identifier.")
    remote_handoff_json_parser = task_subparsers.add_parser(
        "remote-handoff-json",
        help="Print the task remote handoff contract record.",
    )
    remote_handoff_json_parser.add_argument("task_id", help="Task identifier.")
    execution_fit_json_parser = task_subparsers.add_parser(
        "execution-fit-json",
        help="Print the task execution-fit record.",
    )
    execution_fit_json_parser.add_argument("task_id", help="Task identifier.")
    retry_policy_json_parser = task_subparsers.add_parser(
        "retry-policy-json",
        help="Print the task retry-policy record.",
    )
    retry_policy_json_parser.add_argument("task_id", help="Task identifier.")
    execution_budget_policy_json_parser = task_subparsers.add_parser(
        "execution-budget-policy-json",
        help="Print the task execution-budget-policy record.",
    )
    execution_budget_policy_json_parser.add_argument("task_id", help="Task identifier.")
    stop_policy_json_parser = task_subparsers.add_parser(
        "stop-policy-json",
        help="Print the task stop-policy record.",
    )
    stop_policy_json_parser.add_argument("task_id", help="Task identifier.")
    checkpoint_json_parser = task_subparsers.add_parser(
        "checkpoint-json",
        help="Print the task checkpoint snapshot record.",
    )
    checkpoint_json_parser.add_argument("task_id", help="Task identifier.")
    capabilities_json_parser = task_subparsers.add_parser(
        "capabilities-json",
        help="Print the task capability assembly record.",
    )
    capabilities_json_parser.add_argument("task_id", help="Task identifier.")
    semantics_json_parser = task_subparsers.add_parser("semantics-json", help="Print the task semantics record.")
    semantics_json_parser.add_argument("task_id", help="Task identifier.")
    knowledge_objects_json_parser = task_subparsers.add_parser(
        "knowledge-objects-json",
        help="Print the task knowledge-objects record.",
    )
    knowledge_objects_json_parser.add_argument("task_id", help="Task identifier.")
    knowledge_partition_json_parser = task_subparsers.add_parser(
        "knowledge-partition-json",
        help="Print the task knowledge-partition record.",
    )
    knowledge_partition_json_parser.add_argument("task_id", help="Task identifier.")
    knowledge_index_json_parser = task_subparsers.add_parser(
        "knowledge-index-json",
        help="Print the task knowledge-index record.",
    )
    knowledge_index_json_parser.add_argument("task_id", help="Task identifier.")
    knowledge_policy_json_parser = task_subparsers.add_parser(
        "knowledge-policy-json",
        help="Print the task knowledge-policy record.",
    )
    knowledge_policy_json_parser.add_argument("task_id", help="Task identifier.")
    knowledge_decisions_json_parser = task_subparsers.add_parser(
        "knowledge-decisions-json",
        help="Print the task knowledge decision records.",
    )
    knowledge_decisions_json_parser.add_argument("task_id", help="Task identifier.")
    canonical_registry_json_parser = task_subparsers.add_parser(
        "canonical-registry-json",
        help="Print the canonical knowledge registry records.",
    )
    canonical_registry_json_parser.add_argument("task_id", help="Task identifier used for workspace selection.")
    canonical_registry_index_json_parser = task_subparsers.add_parser(
        "canonical-registry-index-json",
        help="Print the canonical knowledge registry index record.",
    )
    canonical_registry_index_json_parser.add_argument("task_id", help="Task identifier used for workspace selection.")
    canonical_reuse_json_parser = task_subparsers.add_parser(
        "canonical-reuse-json",
        help="Print the canonical reuse policy record.",
    )
    canonical_reuse_json_parser.add_argument("task_id", help="Task identifier used for workspace selection.")
    canonical_reuse_eval_json_parser = task_subparsers.add_parser(
        "canonical-reuse-eval-json",
        help="Print the canonical reuse evaluation records.",
    )
    canonical_reuse_eval_json_parser.add_argument("task_id", help="Task identifier used for workspace selection.")
    canonical_reuse_regression_json_parser = task_subparsers.add_parser(
        "canonical-reuse-regression-json",
        help="Print the canonical reuse regression baseline record.",
        description="Print the canonical reuse regression baseline record.",
    )
    canonical_reuse_regression_json_parser.add_argument("task_id", help="Task identifier used for workspace selection.")
    retrieval_json_parser = task_subparsers.add_parser("retrieval-json", help="Print the task retrieval record.")
    retrieval_json_parser.add_argument("task_id", help="Task identifier.")

    doctor_subparsers.add_parser("codex", help="Run a minimal Codex executor preflight.")
    doctor_subparsers.add_parser("sqlite", help="Inspect the SQLite store and migration status.")
    doctor_subparsers.add_parser("stack", help="Run local Docker / WireGuard / proxy health checks.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    base_dir = Path(args.base_dir).resolve()
    apply_route_weights(base_dir)

    if args.command == "knowledge" and args.knowledge_command == "stage-list":
        candidates = load_staged_candidates(base_dir)
        if getattr(args, "all", False):
            lines = [
                "# Staged Knowledge Registry",
                "",
                f"- count: {len(candidates)}",
                "",
                "## Candidates",
            ]
            if not candidates:
                lines.append("- no staged candidates")
            else:
                for candidate in candidates:
                    lines.extend(
                        [
                            f"- {candidate.candidate_id}",
                            f"  status: {candidate.status}",
                            f"  source_task_id: {candidate.source_task_id}",
                            f"  submitted_by: {candidate.submitted_by or 'unknown'}",
                            f"  taxonomy: {candidate.taxonomy_role or '-'} / {candidate.taxonomy_memory_authority or '-'}",
                        ]
                    )
            print("\n".join(lines))
        else:
            print(build_stage_candidate_list_report(candidates))
        return 0

    if args.command == "knowledge" and args.knowledge_command == "stage-inspect":
        print(build_stage_candidate_inspect_report(resolve_stage_candidate(base_dir, args.candidate_id)))
        return 0

    if args.command == "knowledge" and args.knowledge_command == "stage-promote":
        candidate = resolve_stage_candidate(base_dir, args.candidate_id)
        if candidate.status != "pending":
            raise ValueError(f"Staged candidate is already decided: {candidate.candidate_id} ({candidate.status})")
        canonical_records = load_json_lines_if_exists(canonical_registry_path(base_dir))
        preflight_notices = build_stage_promote_preflight_notices(canonical_records, candidate)
        for notice in preflight_notices:
            print(format_stage_promote_preflight_notice(notice))
        if any(notice.get("notice_type") == "supersede" for notice in preflight_notices) and not getattr(args, "force", False):
            raise ValueError("Supersede notice detected; rerun with --force to confirm promotion.")
        decision_note = args.note.strip()
        if args.text.strip():
            decision_note = f"{decision_note} [refined]".strip() if decision_note else "[refined]"
        updated = update_staged_candidate(
            base_dir,
            candidate.candidate_id,
            "promoted",
            "swl_cli",
            decision_note,
        )
        canonical_record = build_stage_canonical_record(updated, refined_text=args.text)
        persist_wiki_entry_from_record(
            base_dir,
            canonical_record,
            write_authority=OPERATOR_CANONICAL_WRITE_AUTHORITY,
        )
        append_canonical_record(base_dir, canonical_record)
        canonical_records = load_json_lines_if_exists(canonical_registry_path(base_dir))
        canonical_index = build_canonical_registry_index(canonical_records)
        canonical_reuse_summary = build_canonical_reuse_summary(canonical_records)
        save_canonical_registry_index(base_dir, canonical_index)
        save_canonical_reuse_policy(base_dir, canonical_reuse_summary)
        print(f"{updated.candidate_id} staged_promoted canonical_id=canonical-{updated.candidate_id}")
        return 0

    if args.command == "knowledge" and args.knowledge_command == "stage-reject":
        candidate = resolve_stage_candidate(base_dir, args.candidate_id)
        if candidate.status != "pending":
            raise ValueError(f"Staged candidate is already decided: {candidate.candidate_id} ({candidate.status})")
        updated = update_staged_candidate(
            base_dir,
            candidate.candidate_id,
            "rejected",
            "swl_cli",
            args.note,
        )
        print(f"{updated.candidate_id} staged_rejected status={updated.status}")
        return 0

    if args.command == "knowledge" and args.knowledge_command == "canonical-audit":
        canonical_records = load_json_lines_if_exists(canonical_registry_path(base_dir))
        print(build_canonical_audit_report(audit_canonical_registry(base_dir, canonical_records)))
        return 0

    if args.command == "knowledge" and args.knowledge_command == "migrate":
        print(format_knowledge_migration_summary(migrate_file_knowledge_to_sqlite(base_dir, dry_run=args.dry_run)))
        return 0

    if args.command == "meta-optimize":
        _snapshot, artifact_path, report = run_meta_optimizer(base_dir, last_n=args.last_n)
        print(report, end="")
        print(f"artifact: {artifact_path}")
        return 0

    if args.command == "audit" and args.audit_command == "policy" and args.audit_policy_command == "show":
        print(build_audit_trigger_policy_report(load_audit_trigger_policy(base_dir)), end="")
        return 0

    if args.command == "audit" and args.audit_command == "policy" and args.audit_policy_command == "set":
        policy = load_audit_trigger_policy(base_dir)
        if args.enabled is not None:
            policy.enabled = bool(args.enabled)
        if args.trigger_on_degraded is not None:
            policy.trigger_on_degraded = bool(args.trigger_on_degraded)
        if args.clear_trigger_on_cost_above:
            policy.trigger_on_cost_above = None
        elif args.trigger_on_cost_above is not None:
            if args.trigger_on_cost_above < 0:
                raise ValueError("--trigger-on-cost-above must be non-negative.")
            policy.trigger_on_cost_above = float(args.trigger_on_cost_above)
        if args.auditor_route is not None:
            auditor_route = args.auditor_route.strip()
            if not auditor_route:
                raise ValueError("--auditor-route must be a non-empty route name.")
            if route_by_name(auditor_route) is None:
                raise ValueError(f"Unknown auditor route: {auditor_route}")
            policy.auditor_route = auditor_route
        save_audit_trigger_policy(base_dir, policy)
        print(build_audit_trigger_policy_report(policy), end="")
        return 0

    if args.command == "route" and args.route_command == "weights" and args.route_weights_command == "show":
        print(build_route_weights_report(base_dir), end="")
        return 0

    if args.command == "route" and args.route_command == "weights" and args.route_weights_command == "apply":
        proposal_path = Path(args.proposal_file).resolve()
        proposals = extract_route_weight_proposals_from_report(proposal_path.read_text(encoding="utf-8"))
        if not proposals:
            raise ValueError(f"No route_weight proposals found in {proposal_path}")

        updated_weights = current_route_weights()
        for proposal in proposals:
            route_name = str(proposal.route_name or "").strip()
            if not route_name:
                continue
            if route_by_name(route_name) is None:
                raise ValueError(f"Unknown route in proposal file: {route_name}")
            updated_weights[route_name] = float(proposal.suggested_weight or 1.0)

        persisted_weights = {
            route_name: weight
            for route_name, weight in updated_weights.items()
            if abs(weight - 1.0) > 1e-9
        }
        save_route_weights(base_dir, persisted_weights)
        apply_route_weights(base_dir)
        print(build_route_weights_report(base_dir), end="")
        return 0

    if args.command == "ingest":
        result = run_ingestion_pipeline(
            base_dir,
            Path(args.source_path).resolve(),
            format_hint=args.format,
            dry_run=bool(args.dry_run),
        )
        output = build_ingestion_report(result)
        if bool(args.summary):
            output = f"{output}\n\n{build_ingestion_summary(result)}"
        print(output)
        return 0

    if args.command == "serve":
        try:
            from .web.server import serve_control_center

            serve_control_center(base_dir, host=args.host, port=args.port)
        except RuntimeError as exc:
            print(str(exc))
            return 1
        return 0

    if args.command == "task" and args.task_command == "create":
        state = create_task(
            base_dir=base_dir,
            title=args.title.strip(),
            goal=args.goal.strip(),
            workspace_root=Path(args.workspace_root).resolve(),
            executor_name=args.executor.strip(),
            constraints=args.constraint,
            acceptance_criteria=args.acceptance_criterion,
            priority_hints=args.priority_hint,
            next_action_proposals=args.next_action_proposal,
            planning_source=args.planning_source,
            knowledge_items=args.knowledge_item,
            knowledge_stage=args.knowledge_stage,
            knowledge_source=args.knowledge_source,
            knowledge_artifact_refs=args.knowledge_artifact_ref,
            knowledge_retrieval_eligible=args.knowledge_retrieval_eligible,
            knowledge_canonicalization_intent=args.knowledge_canonicalization_intent,
            capability_refs=args.capability,
            route_mode=args.route_mode,
        )
        print(state.task_id)
        return 0

    if args.command == "task" and args.task_command == "planning-handoff":
        state = update_task_planning_handoff(
            base_dir=base_dir,
            task_id=args.task_id,
            constraints=args.constraint,
            acceptance_criteria=args.acceptance_criterion,
            priority_hints=args.priority_hint,
            next_action_proposals=args.next_action_proposal,
            planning_source=args.planning_source,
        )
        print(
            f"{state.task_id} planning_handoff_updated "
            f"constraints={len(state.task_semantics.get('constraints', []))} "
            f"next_actions={len(state.task_semantics.get('next_action_proposals', []))}"
        )
        return 0

    if args.command == "task" and args.task_command == "knowledge-capture":
        state = append_task_knowledge_capture(
            base_dir=base_dir,
            task_id=args.task_id,
            knowledge_items=args.knowledge_item,
            knowledge_stage=args.knowledge_stage,
            knowledge_source=args.knowledge_source,
            knowledge_artifact_refs=args.knowledge_artifact_ref,
            knowledge_retrieval_eligible=args.knowledge_retrieval_eligible,
            knowledge_canonicalization_intent=args.knowledge_canonicalization_intent,
        )
        print(f"{state.task_id} knowledge_capture_added added={len(args.knowledge_item)} total={len(state.knowledge_objects)}")
        return 0

    if args.command == "task" and args.task_command == "knowledge-promote":
        state = decide_task_knowledge(
            base_dir,
            args.task_id,
            object_id=args.object_id,
            decision_type="promote",
            decision_target=args.target,
            caller_authority=LIBRARIAN_MEMORY_AUTHORITY,
            note=args.note,
        )
        print(f"{state.task_id} knowledge_promoted object={args.object_id} target={args.target}")
        return 0

    if args.command == "task" and args.task_command == "knowledge-reject":
        state = decide_task_knowledge(
            base_dir,
            args.task_id,
            object_id=args.object_id,
            decision_type="reject",
            decision_target=args.target,
            note=args.note,
        )
        print(f"{state.task_id} knowledge_rejected object={args.object_id} target={args.target}")
        return 0

    if args.command == "task" and args.task_command == "run":
        return execute_task_run(base_dir, args.task_id, args.executor, args.capability, args.route_mode)

    if args.command == "task" and args.task_command == "acknowledge":
        try:
            state = acknowledge_task(base_dir, args.task_id)
        except ValueError as exc:
            state = load_state(base_dir, args.task_id)
            print(
                f"{state.task_id} acknowledge_blocked "
                f"status={state.status} "
                f"phase={state.phase} "
                f"dispatch_status={state.topology_dispatch_status} "
                f"reason={str(exc)}"
            )
            return 1
        print(
            f"{state.task_id} dispatch_acknowledged "
            f"status={state.status} "
            f"phase={state.phase} "
            f"dispatch_status={state.topology_dispatch_status} "
            f"route={state.route_name}"
        )
        return 0

    if args.command == "task" and args.task_command == "retry":
        state = load_state(base_dir, args.task_id)
        if is_acknowledged_dispatch_reentry(state):
            return execute_task_run(
                base_dir,
                args.task_id,
                args.executor,
                args.capability,
                args.route_mode,
                skip_to_phase=args.from_phase,
            )
        retry_policy = load_json_if_exists(retry_policy_path(base_dir, args.task_id))
        stop_policy = load_json_if_exists(stop_policy_path(base_dir, args.task_id))
        checkpoint_snapshot = load_checkpoint_snapshot(base_dir, state)
        if not (retry_policy.get("retryable", False) and stop_policy.get("checkpoint_kind", "") in {"retry_review", "detached_retry_review"}):
            print(
                f"{state.task_id} retry_blocked "
                f"retry_decision={retry_policy.get('retry_decision', 'pending')} "
                f"checkpoint_kind={stop_policy.get('checkpoint_kind', 'pending')} "
                f"suggested_path={checkpoint_snapshot.get('recommended_path', 'pending')}"
            )
            return 1
        return execute_task_run(
            base_dir,
            args.task_id,
            args.executor,
            args.capability,
            args.route_mode,
            reset_grounding=True,
            skip_to_phase=args.from_phase,
        )

    if args.command == "task" and args.task_command == "resume":
        state = load_state(base_dir, args.task_id)
        if is_acknowledged_dispatch_reentry(state):
            return execute_task_run(base_dir, args.task_id, args.executor, args.capability, args.route_mode)
        checkpoint_snapshot = load_checkpoint_snapshot(base_dir, state)
        if not (checkpoint_snapshot.get("resume_ready", False) and checkpoint_snapshot.get("recommended_path", "") == "resume"):
            print(
                f"{state.task_id} resume_blocked "
                f"checkpoint_state={checkpoint_snapshot.get('checkpoint_state', 'pending')} "
                f"recommended_path={checkpoint_snapshot.get('recommended_path', 'pending')} "
                f"suggested_reason={checkpoint_snapshot.get('recommended_reason', 'pending')}"
            )
            return 1
        return execute_task_run(base_dir, args.task_id, args.executor, args.capability, args.route_mode)

    if args.command == "task" and args.task_command == "rerun":
        return execute_task_run(
            base_dir,
            args.task_id,
            args.executor,
            args.capability,
            args.route_mode,
            reset_grounding=True,
            skip_to_phase=args.from_phase,
        )

    if args.command == "task" and args.task_command == "list":
        states = sorted(
            iter_task_states(base_dir),
            key=lambda state: (state.updated_at, state.task_id),
            reverse=True,
        )
        states = filter_task_states(states, args.focus)
        if args.limit is not None:
            states = states[: max(args.limit, 0)]
        print(f"task_id\tstatus\tphase\tattempt\tupdated_at\ttitle\tfocus={args.focus}")
        for state in states:
            attempt_label = state.current_attempt_id or "-"
            print(
                "\t".join(
                    [
                        state.task_id,
                        state.status,
                        state.phase,
                        attempt_label,
                        state.updated_at,
                        state.title,
                    ]
                )
            )
        return 0

    if args.command == "task" and args.task_command == "queue":
        states = sorted(
            iter_task_states(base_dir),
            key=lambda state: (state.updated_at, state.task_id),
            reverse=True,
        )
        queue_entries = [entry for state in states if (entry := build_task_queue_entry(base_dir, state)) is not None]
        if args.limit is not None:
            queue_entries = queue_entries[: max(args.limit, 0)]
        print("task_id\taction\tstatus\tattempt\tupdated_at\treason\tregression\tknowledge\tnext\ttitle")
        for entry in queue_entries:
            print(
                "\t".join(
                    [
                        entry["task_id"],
                        entry["action"],
                        entry["status"],
                        entry["attempt"],
                        entry["updated_at"],
                        entry["reason"],
                        entry["regression"],
                        entry["knowledge"],
                        entry["next"],
                        entry["title"],
                    ]
                )
            )
        return 0

    if args.command == "task" and args.task_command == "attempts":
        state = load_state(base_dir, args.task_id)
        attempts = build_attempt_summaries(base_dir, args.task_id)
        print("attempt_id\tattempt_number\tstatus\texecutor_status\texecution_lifecycle\tretrieval_count\thandoff_status\tstarted_at\tfinished_at")
        for attempt in attempts:
            print(
                "\t".join(
                    [
                        attempt["attempt_id"],
                        attempt["attempt_number"],
                        attempt["status"],
                        attempt["executor_status"],
                        attempt["execution_lifecycle"],
                        attempt["retrieval_count"],
                        attempt["handoff_status"],
                        attempt["started_at"],
                        attempt["finished_at"],
                    ]
                )
            )
        if not attempts and state.current_attempt_id:
            print(
                "\t".join(
                    [
                        state.current_attempt_id,
                        str(state.current_attempt_number or 0),
                        state.status,
                        state.executor_status,
                        state.execution_lifecycle,
                        str(state.retrieval_count),
                        "pending",
                        state.updated_at,
                        "-",
                    ]
                )
            )
        return 0

    if args.command == "task" and args.task_command == "compare-attempts":
        attempts = build_attempt_summaries(base_dir, args.task_id)
        left_attempt, right_attempt = resolve_attempt_pair(attempts, args.left, args.right)
        lines = [
            f"Task Attempt Compare: {args.task_id}",
            f"left_attempt: {left_attempt['attempt_id']}",
            f"right_attempt: {right_attempt['attempt_id']}",
            "",
            "Comparison",
            f"status: {left_attempt['status']} -> {right_attempt['status']}",
            f"executor_status: {left_attempt['executor_status']} -> {right_attempt['executor_status']}",
            f"execution_lifecycle: {left_attempt['execution_lifecycle']} -> {right_attempt['execution_lifecycle']}",
            f"retrieval_count: {left_attempt['retrieval_count']} -> {right_attempt['retrieval_count']}",
            f"handoff_status: {left_attempt['handoff_status']} -> {right_attempt['handoff_status']}",
            f"compatibility_status: {left_attempt['compatibility_status']} -> {right_attempt['compatibility_status']}",
            f"execution_fit_status: {left_attempt['execution_fit_status']} -> {right_attempt['execution_fit_status']}",
            f"retry_policy_status: {left_attempt['retry_policy_status']} -> {right_attempt['retry_policy_status']}",
            f"stop_policy_status: {left_attempt['stop_policy_status']} -> {right_attempt['stop_policy_status']}",
        ]
        print("\n".join(lines))
        return 0

    if args.command == "task" and args.task_command == "control":
        state = load_state(base_dir, args.task_id)
        print("\n".join(build_task_control_snapshot(base_dir, state)))
        return 0

    if args.command == "task" and args.task_command == "intake":
        print("\n".join(build_intake_snapshot(base_dir, args.task_id)))
        return 0

    if args.command == "task" and args.task_command == "staged":
        candidates = load_staged_candidates(base_dir)
        task_filter = args.task.strip()
        if args.status != "all":
            candidates = [candidate for candidate in candidates if candidate.status == args.status]
        if task_filter:
            candidates = [candidate for candidate in candidates if candidate.source_task_id == task_filter]
        print(build_task_staged_report(candidates, status_filter=args.status, task_filter=task_filter))
        return 0

    if args.command == "task" and args.task_command == "knowledge-review-queue":
        knowledge_objects = load_knowledge_objects(base_dir, args.task_id)
        decisions = load_json_lines_if_exists(knowledge_decisions_path(base_dir, args.task_id))
        print(build_review_queue_report(build_review_queue(knowledge_objects, decisions)))
        return 0

    if args.command == "task" and args.task_command == "canonical-reuse-evaluate":
        result = evaluate_task_canonical_reuse(
            base_dir=base_dir,
            task_id=args.task_id,
            citations=args.citation,
            judgment=args.judgment,
            note=args.note,
        )
        print(
            f"{result['record']['task_id']} canonical_reuse_evaluated judgment={result['record']['judgment']} citations={result['record']['citation_count']}"
        )
        return 0

    if args.command == "task" and args.task_command == "consistency-audit":
        result = run_consistency_audit(
            base_dir,
            args.task_id,
            auditor_route=args.auditor_route,
            sample_artifact_path=args.artifact,
        )
        artifact_ref = result.audit_artifact or "-"
        print(
            f"{result.task_id} consistency_audit status={result.status} verdict={result.verdict} route={result.auditor_route} artifact={artifact_ref}"
        )
        return 0

    if args.command == "task" and args.task_command == "inspect":
        state = load_state(base_dir, args.task_id)

        compatibility = load_json_if_exists(compatibility_path(base_dir, args.task_id))
        topology = load_json_if_exists(topology_path(base_dir, args.task_id))
        execution_site = load_json_if_exists(execution_site_path(base_dir, args.task_id))
        dispatch = load_json_if_exists(dispatch_path(base_dir, args.task_id))
        handoff = load_json_if_exists(handoff_path(base_dir, args.task_id))
        execution_fit = load_json_if_exists(execution_fit_path(base_dir, args.task_id))
        retry_policy = load_json_if_exists(retry_policy_path(base_dir, args.task_id))
        execution_budget_policy = load_json_if_exists(execution_budget_policy_path(base_dir, args.task_id))
        stop_policy = load_json_if_exists(stop_policy_path(base_dir, args.task_id))
        checkpoint_snapshot = load_checkpoint_snapshot(base_dir, state)
        knowledge_policy = load_json_if_exists(knowledge_policy_path(base_dir, args.task_id))
        knowledge_partition = load_json_if_exists(knowledge_partition_path(base_dir, args.task_id))
        knowledge_index = load_json_if_exists(knowledge_index_path(base_dir, args.task_id))
        knowledge_decisions = load_json_lines_if_exists(knowledge_decisions_path(base_dir, args.task_id))
        canonical_reuse_eval = load_json_lines_if_exists(canonical_reuse_eval_path(base_dir, args.task_id))
        canonical_reuse_regression = load_json_if_exists(canonical_reuse_regression_path(base_dir, args.task_id))
        regression_attention = build_canonical_reuse_regression_attention(base_dir, args.task_id)
        remote_handoff_attention = build_remote_handoff_attention(base_dir, args.task_id)
        canonical_registry_index = load_json_if_exists(canonical_registry_index_path(base_dir))
        canonical_reuse_policy = load_json_if_exists(canonical_reuse_policy_path(base_dir))
        retrieval = load_json_if_exists(retrieval_path(base_dir, args.task_id))
        task_semantics = load_json_if_exists(task_semantics_path(base_dir, args.task_id))
        knowledge_objects = load_knowledge_objects(base_dir, args.task_id)
        if not isinstance(retrieval, list):
            retrieval = []
        mock_remote_label = "[MOCK-REMOTE]" if is_mock_remote_task(state, topology) else ""
        taxonomy_label = format_taxonomy_label(state)
        capability_enforcement = load_latest_capability_enforcement(base_dir, args.task_id)
        capability_enforced, capability_enforced_fields = format_capability_enforcement_summary(capability_enforcement)
        grounding_locked, grounding_refs_count, grounding_refs = format_grounding_summary(state)
        knowledge_stage_counts = {"raw": 0, "candidate": 0, "verified": 0, "canonical": 0}
        knowledge_evidence_counts = {"artifact_backed": 0, "source_only": 0, "unbacked": 0}
        knowledge_reuse_counts = {"task_only": 0, "retrieval_candidate": 0}
        canonicalization_counts = summarize_canonicalization(knowledge_objects)
        reused_knowledge_references: list[str] = []
        for item in knowledge_objects:
            stage = str(item.get("stage", "raw"))
            knowledge_stage_counts[stage] = knowledge_stage_counts.get(stage, 0) + 1
            evidence_status = str(item.get("evidence_status", "unbacked"))
            knowledge_evidence_counts[evidence_status] = knowledge_evidence_counts.get(evidence_status, 0) + 1
            reuse_scope = str(item.get("knowledge_reuse_scope", "task_only"))
            knowledge_reuse_counts[reuse_scope] = knowledge_reuse_counts.get(reuse_scope, 0) + 1
        for item in retrieval:
            if str(item.get("source_type", "")) == "knowledge":
                reused_knowledge_references.append(str(item.get("citation", item.get("path", ""))))

        lines = [
            f"Task Overview: {state.task_id}",
            f"title: {state.title}",
            f"goal: {state.goal}",
            "",
            "State",
            f"status: {state.status}",
            f"phase: {state.phase}",
            f"updated_at: {state.updated_at}",
            f"attempt_id: {state.current_attempt_id or '-'}",
            f"attempt_number: {state.current_attempt_number or 0}",
            f"attempt_owner_kind: {state.current_attempt_owner_kind}",
            f"attempt_owner_ref: {state.current_attempt_owner_ref}",
            f"attempt_ownership_status: {state.current_attempt_ownership_status}",
            f"execution_lifecycle: {state.execution_lifecycle}",
            f"execution_phase: {state.execution_phase or 'pending'}",
            f"last_phase_checkpoint_at: {state.last_phase_checkpoint_at or '-'}",
            f"task_semantics_source_kind: {task_semantics.get('source_kind', state.task_semantics.get('source_kind', 'none') if state.task_semantics else 'none')}",
            f"task_semantics_source_ref: {task_semantics.get('source_ref', state.task_semantics.get('source_ref', '') if state.task_semantics else '') or '-'}",
            f"task_semantics_constraints: {len(task_semantics.get('constraints', state.task_semantics.get('constraints', []) if state.task_semantics else []))}",
            f"task_semantics_acceptance_criteria: {len(task_semantics.get('acceptance_criteria', state.task_semantics.get('acceptance_criteria', []) if state.task_semantics else []))}",
            f"knowledge_objects_count: {len(knowledge_objects)}",
            f"knowledge_object_stages: raw={knowledge_stage_counts.get('raw', 0)} candidate={knowledge_stage_counts.get('candidate', 0)} verified={knowledge_stage_counts.get('verified', 0)} canonical={knowledge_stage_counts.get('canonical', 0)}",
            f"knowledge_object_evidence: artifact_backed={knowledge_evidence_counts.get('artifact_backed', 0)} source_only={knowledge_evidence_counts.get('source_only', 0)} unbacked={knowledge_evidence_counts.get('unbacked', 0)}",
            f"knowledge_object_reuse: retrieval_candidate={knowledge_reuse_counts.get('retrieval_candidate', 0)} task_only={knowledge_reuse_counts.get('task_only', 0)}",
            f"knowledge_object_canonicalization: ready={canonicalization_counts.get('review_ready', 0) + canonicalization_counts.get('promotion_ready', 0)} blocked={canonicalization_counts.get('blocked_stage', 0) + canonicalization_counts.get('blocked_evidence', 0)} canonical={canonicalization_counts.get('canonical', 0)}",
            f"knowledge_partition: task_linked={knowledge_partition.get('task_linked_count', len(knowledge_objects))} reusable_candidate={knowledge_partition.get('reusable_candidate_count', 0)}",
            f"knowledge_index: active_reusable={knowledge_index.get('active_reusable_count', 0)} inactive_reusable={knowledge_index.get('inactive_reusable_count', 0)}",
            f"knowledge_index_refreshed_at: {knowledge_index.get('refreshed_at', '-')}",
            "",
            "Route And Topology",
            f"route_label: {mock_remote_label or '-'}",
            f"taxonomy: {taxonomy_label}",
            f"capability_enforced: {capability_enforced}",
            f"capability_enforced_fields: {capability_enforced_fields}",
            f"grounding_locked: {grounding_locked}",
            f"grounding_refs_count: {grounding_refs_count}",
            f"grounding_refs: {grounding_refs}",
            f"route_mode: {state.route_mode}",
            f"route_name: {state.route_name}",
            f"route_backend: {state.route_backend}",
            f"route_executor_family: {state.route_executor_family}",
            f"route_execution_site: {state.route_execution_site}",
            f"dialect: {state.route_dialect or '-'}",
            f"execution_site_contract_kind: {execution_site.get('contract_kind', state.execution_site_contract_kind)}",
            f"execution_site_boundary: {execution_site.get('boundary', state.execution_site_boundary)}",
            f"execution_site_contract_status: {execution_site.get('contract_status', state.execution_site_contract_status)}",
            f"execution_site_handoff_required: {'yes' if execution_site.get('handoff_required', state.execution_site_handoff_required) else 'no'}",
            f"topology_executor_family: {topology.get('executor_family', state.topology_executor_family)}",
            f"topology_execution_site: {topology.get('execution_site', state.topology_execution_site)}",
            f"topology_transport_kind: {topology.get('transport_kind', state.topology_transport_kind)}",
            f"topology_dispatch_status: {topology.get('dispatch_status', state.topology_dispatch_status)}",
            "",
            "Checks",
            f"compatibility_status: {compatibility.get('status', 'pending')}",
            f"execution_fit_status: {execution_fit.get('status', 'pending')}",
            f"knowledge_policy_status: {knowledge_policy.get('status', 'pending')}",
            f"validation_status: {load_json_if_exists(Path(state.artifact_paths.get('validation_json', ''))).get('status', 'pending') if state.artifact_paths.get('validation_json') else 'pending'}",
            "",
            *build_knowledge_review_snapshot(knowledge_objects, knowledge_decisions),
            "",
            *build_canonical_registry_snapshot(canonical_registry_index),
            "",
            *build_canonical_reuse_snapshot(canonical_reuse_policy),
            "",
            *build_canonical_reuse_eval_snapshot(canonical_reuse_eval),
            "",
            *build_canonical_reuse_regression_snapshot(canonical_reuse_regression),
            "",
            *build_policy_snapshot(retry_policy, execution_budget_policy, stop_policy),
            "",
            "Retrieval And Memory",
            f"retrieval_count: {state.retrieval_count}",
            f"retrieval_record_available: {'yes' if isinstance(retrieval, list) and bool(retrieval) else 'no'}",
            f"reused_knowledge_in_retrieval: {len(reused_knowledge_references)}",
            f"reused_current_task_knowledge: {sum(1 for item in retrieval if str(item.get('metadata', {}).get('knowledge_task_relation', '')) == 'current_task') if isinstance(retrieval, list) else 0}",
            f"reused_cross_task_knowledge: {sum(1 for item in retrieval if str(item.get('metadata', {}).get('knowledge_task_relation', '')) == 'cross_task') if isinstance(retrieval, list) else 0}",
            f"reused_knowledge_references: {', '.join(reused_knowledge_references) or '-'}",
            f"grounding_available: {'yes' if state.artifact_paths.get('source_grounding') else 'no'}",
            f"memory_available: {'yes' if memory_path(base_dir, args.task_id).exists() else 'no'}",
            "",
            "Operator Guidance",
            f"handoff_status: {handoff.get('status', 'pending')}",
            f"handoff_contract_status: {handoff.get('contract_status', 'pending')}",
            f"handoff_contract_kind: {handoff.get('contract_kind', 'pending')}",
            f"checkpoint_state: {checkpoint_snapshot.get('checkpoint_state', 'pending')}",
            f"execution_phase: {checkpoint_snapshot.get('execution_phase', state.execution_phase or 'pending')}",
            f"last_phase_checkpoint_at: {checkpoint_snapshot.get('last_phase_checkpoint_at', state.last_phase_checkpoint_at or '-')}",
            f"recovery_semantics: {checkpoint_snapshot.get('recovery_semantics', 'pending')}",
            f"interruption_kind: {checkpoint_snapshot.get('interruption_kind', 'none')}",
            f"recommended_path: {checkpoint_snapshot.get('recommended_path', 'pending')}",
            f"handoff_next_owner_kind: {handoff.get('next_owner_kind', 'pending')}",
            f"handoff_next_owner_ref: {handoff.get('next_owner_ref', 'pending')}",
            f"blocking_reason: {handoff.get('blocking_reason', '') or '-'}",
            f"next_operator_action: {handoff.get('next_operator_action', 'Inspect task artifacts.')}",
            f"canonical_reuse_regression_status: {regression_attention['status']}",
            f"canonical_reuse_regression_mismatch_count: {regression_attention['mismatch_count']}",
            f"canonical_reuse_regression_mismatches: {regression_attention['mismatches']}",
            f"canonical_reuse_regression_command: {regression_attention['recommended_command']}",
            f"remote_handoff_needed: {remote_handoff_attention['needs_attention']}",
            f"remote_handoff_summary: {remote_handoff_attention['summary']}",
            f"remote_handoff_contract_kind: {remote_handoff_attention['contract_kind']}",
            f"remote_handoff_contract_status: {remote_handoff_attention['contract_status']}",
            f"remote_handoff_boundary: {remote_handoff_attention['handoff_boundary']}",
            f"remote_handoff_dispatch_readiness: {remote_handoff_attention['dispatch_readiness']}",
            f"remote_handoff_operator_ack_required: {remote_handoff_attention['operator_ack_required']}",
            f"remote_handoff_command: {remote_handoff_attention['recommended_command']}",
            "",
            "Artifacts",
            f"task_semantics_report: {state.artifact_paths.get('task_semantics_report', '-')}",
            f"knowledge_objects_report: {state.artifact_paths.get('knowledge_objects_report', '-')}",
            f"knowledge_partition_report: {state.artifact_paths.get('knowledge_partition_report', '-')}",
            f"knowledge_index_report: {state.artifact_paths.get('knowledge_index_report', '-')}",
            f"knowledge_decisions_report: {state.artifact_paths.get('knowledge_decisions_report', '-')}",
            f"canonical_registry_report: {state.artifact_paths.get('canonical_registry_report', '-')}",
            f"canonical_registry_index_report: {state.artifact_paths.get('canonical_registry_index_report', '-')}",
            f"canonical_reuse_policy_report: {state.artifact_paths.get('canonical_reuse_policy_report', '-')}",
            f"canonical_reuse_eval_report: {state.artifact_paths.get('canonical_reuse_eval_report', '-')}",
            f"canonical_reuse_regression_json: {state.artifact_paths.get('canonical_reuse_regression_json', '-')}",
            f"summary: {state.artifact_paths.get('summary', '-')}",
            f"resume_note: {state.artifact_paths.get('resume_note', '-')}",
            f"route_report: {state.artifact_paths.get('route_report', '-')}",
            f"topology_report: {state.artifact_paths.get('topology_report', '-')}",
            f"execution_site_report: {state.artifact_paths.get('execution_site_report', '-')}",
            f"dispatch_report: {state.artifact_paths.get('dispatch_report', '-')}",
            f"handoff_report: {state.artifact_paths.get('handoff_report', '-')}",
            f"remote_handoff_contract_report: {state.artifact_paths.get('remote_handoff_contract_report', '-')}",
            f"retrieval_report: {state.artifact_paths.get('retrieval_report', '-')}",
            f"grounding_evidence_report: {state.artifact_paths.get('grounding_evidence_report', '-')}",
            f"retry_policy_report: {state.artifact_paths.get('retry_policy_report', '-')}",
            f"execution_budget_policy_report: {state.artifact_paths.get('execution_budget_policy_report', '-')}",
            f"stop_policy_report: {state.artifact_paths.get('stop_policy_report', '-')}",
            f"checkpoint_snapshot_report: {state.artifact_paths.get('checkpoint_snapshot_report', '-')}",
            f"knowledge_policy_report: {state.artifact_paths.get('knowledge_policy_report', '-')}",
            f"validation_report: {state.artifact_paths.get('validation_report', '-')}",
        ]
        print("\n".join(lines))
        return 0

    if args.command == "task" and args.task_command == "capabilities":
        state = load_state(base_dir, args.task_id)
        manifest = json.loads(capability_manifest_path(base_dir, args.task_id).read_text(encoding="utf-8"))
        assembly = json.loads(capability_assembly_path(base_dir, args.task_id).read_text(encoding="utf-8"))
        lines = [
            f"Task Capabilities: {state.task_id}",
            "",
            "Requested Manifest",
            f"profile_refs: {', '.join(manifest.get('profile_refs', [])) or '-'}",
            f"workflow_refs: {', '.join(manifest.get('workflow_refs', [])) or '-'}",
            f"validator_refs: {', '.join(manifest.get('validator_refs', [])) or '-'}",
            f"skill_refs: {', '.join(manifest.get('skill_refs', [])) or '-'}",
            f"tool_refs: {', '.join(manifest.get('tool_refs', [])) or '-'}",
            "",
            "Effective Assembly",
            f"assembly_status: {assembly.get('assembly_status', 'pending')}",
            f"resolver: {assembly.get('resolver', 'unknown')}",
            f"effective_profiles: {', '.join(assembly.get('effective', {}).get('profile_refs', [])) or '-'}",
            f"effective_workflows: {', '.join(assembly.get('effective', {}).get('workflow_refs', [])) or '-'}",
            f"effective_validators: {', '.join(assembly.get('effective', {}).get('validator_refs', [])) or '-'}",
            f"notes: {'; '.join(assembly.get('notes', [])) or '-'}",
        ]
        print("\n".join(lines))
        return 0

    if args.command == "task" and args.task_command == "review":
        state = load_state(base_dir, args.task_id)

        handoff = load_json_if_exists(handoff_path(base_dir, args.task_id))
        compatibility = load_json_if_exists(compatibility_path(base_dir, args.task_id))
        execution_fit = load_json_if_exists(execution_fit_path(base_dir, args.task_id))
        retry_policy = load_json_if_exists(retry_policy_path(base_dir, args.task_id))
        execution_budget_policy = load_json_if_exists(execution_budget_policy_path(base_dir, args.task_id))
        stop_policy = load_json_if_exists(stop_policy_path(base_dir, args.task_id))
        checkpoint_snapshot = load_checkpoint_snapshot(base_dir, state)
        knowledge_policy = load_json_if_exists(knowledge_policy_path(base_dir, args.task_id))
        knowledge_index = load_json_if_exists(knowledge_index_path(base_dir, args.task_id))
        knowledge_objects = load_knowledge_objects(base_dir, args.task_id)
        knowledge_decisions = load_json_lines_if_exists(knowledge_decisions_path(base_dir, args.task_id))
        canonical_reuse_eval = load_json_lines_if_exists(canonical_reuse_eval_path(base_dir, args.task_id))
        canonical_reuse_regression = load_json_if_exists(canonical_reuse_regression_path(base_dir, args.task_id))
        regression_attention = build_canonical_reuse_regression_attention(base_dir, args.task_id)
        remote_handoff_attention = build_remote_handoff_attention(base_dir, args.task_id)
        canonical_registry_index = load_json_if_exists(canonical_registry_index_path(base_dir))
        canonical_reuse_policy = load_json_if_exists(canonical_reuse_policy_path(base_dir))
        canonicalization_counts = summarize_canonicalization(knowledge_objects if isinstance(knowledge_objects, list) else [])
        retrieval = load_json_if_exists(retrieval_path(base_dir, args.task_id))
        reused_knowledge_references = []
        if isinstance(retrieval, list):
            for item in retrieval:
                if str(item.get("source_type", "")) == "knowledge":
                    reused_knowledge_references.append(str(item.get("citation", item.get("path", ""))))
        reused_current_task = (
            sum(1 for item in retrieval if str(item.get("metadata", {}).get("knowledge_task_relation", "")) == "current_task")
            if isinstance(retrieval, list)
            else 0
        )
        reused_cross_task = (
            sum(1 for item in retrieval if str(item.get("metadata", {}).get("knowledge_task_relation", "")) == "cross_task")
            if isinstance(retrieval, list)
            else 0
        )
        validation = load_json_if_exists(Path(state.artifact_paths.get("validation_json", ""))) if state.artifact_paths.get("validation_json") else {}
        mock_remote_label = "[MOCK-REMOTE]" if is_mock_remote_task(state) else ""
        taxonomy_label = format_taxonomy_label(state)
        grounding_locked, grounding_refs_count, grounding_refs = format_grounding_summary(state)
        lines = [
            f"Task Review: {state.task_id}",
            f"title: {state.title}",
            "",
            "Latest Attempt",
            f"attempt_id: {state.current_attempt_id or '-'}",
            f"attempt_number: {state.current_attempt_number or 0}",
            f"attempt_owner_kind: {state.current_attempt_owner_kind}",
            f"attempt_owner_ref: {state.current_attempt_owner_ref}",
            f"attempt_ownership_status: {state.current_attempt_ownership_status}",
            f"status: {state.status}",
            f"executor_status: {state.executor_status}",
            f"execution_lifecycle: {state.execution_lifecycle}",
            f"execution_phase: {state.execution_phase or 'pending'}",
            f"last_phase_checkpoint_at: {state.last_phase_checkpoint_at or '-'}",
            "",
            "Handoff",
            f"route_label: {mock_remote_label or '-'}",
            f"taxonomy: {taxonomy_label}",
            f"grounding_locked: {grounding_locked}",
            f"grounding_refs_count: {grounding_refs_count}",
            f"grounding_refs: {grounding_refs}",
            f"dialect: {state.route_dialect or '-'}",
            f"handoff_status: {handoff.get('status', 'pending')}",
            f"handoff_contract_status: {handoff.get('contract_status', 'pending')}",
            f"handoff_contract_kind: {handoff.get('contract_kind', 'pending')}",
            f"checkpoint_state: {checkpoint_snapshot.get('checkpoint_state', 'pending')}",
            f"execution_phase: {checkpoint_snapshot.get('execution_phase', state.execution_phase or 'pending')}",
            f"last_phase_checkpoint_at: {checkpoint_snapshot.get('last_phase_checkpoint_at', state.last_phase_checkpoint_at or '-')}",
            f"recovery_semantics: {checkpoint_snapshot.get('recovery_semantics', 'pending')}",
            f"interruption_kind: {checkpoint_snapshot.get('interruption_kind', 'none')}",
            f"recommended_path: {checkpoint_snapshot.get('recommended_path', 'pending')}",
            f"handoff_next_owner_kind: {handoff.get('next_owner_kind', 'pending')}",
            f"handoff_next_owner_ref: {handoff.get('next_owner_ref', 'pending')}",
            f"blocking_reason: {handoff.get('blocking_reason', '') or '-'}",
            f"next_operator_action: {handoff.get('next_operator_action', 'Review resume_note.md and summary.md.')}",
            f"canonical_reuse_regression_status: {regression_attention['status']}",
            f"canonical_reuse_regression_mismatch_count: {regression_attention['mismatch_count']}",
            f"canonical_reuse_regression_mismatches: {regression_attention['mismatches']}",
            f"canonical_reuse_regression_command: {regression_attention['recommended_command']}",
            f"remote_handoff_needed: {remote_handoff_attention['needs_attention']}",
            f"remote_handoff_summary: {remote_handoff_attention['summary']}",
            f"remote_handoff_contract_kind: {remote_handoff_attention['contract_kind']}",
            f"remote_handoff_contract_status: {remote_handoff_attention['contract_status']}",
            f"remote_handoff_boundary: {remote_handoff_attention['handoff_boundary']}",
            f"remote_handoff_dispatch_readiness: {remote_handoff_attention['dispatch_readiness']}",
            f"remote_handoff_operator_ack_required: {remote_handoff_attention['operator_ack_required']}",
            f"remote_handoff_command: {remote_handoff_attention['recommended_command']}",
            "",
            "Checks",
            f"compatibility_status: {compatibility.get('status', 'pending')}",
            f"execution_fit_status: {execution_fit.get('status', 'pending')}",
            f"knowledge_policy_status: {knowledge_policy.get('status', 'pending')}",
            f"knowledge_canonicalization_ready: {canonicalization_counts.get('review_ready', 0) + canonicalization_counts.get('promotion_ready', 0)}",
            f"knowledge_canonicalization_blocked: {canonicalization_counts.get('blocked_stage', 0) + canonicalization_counts.get('blocked_evidence', 0)}",
            f"knowledge_canonicalization_canonical: {canonicalization_counts.get('canonical', 0)}",
            f"validation_status: {validation.get('status', 'pending')}",
            f"knowledge_index_active_reusable: {knowledge_index.get('active_reusable_count', 0)}",
            f"knowledge_index_inactive_reusable: {knowledge_index.get('inactive_reusable_count', 0)}",
            f"knowledge_index_refreshed_at: {knowledge_index.get('refreshed_at', '-')}",
            f"reused_knowledge_in_retrieval: {len(reused_knowledge_references)}",
            f"reused_current_task_knowledge: {reused_current_task}",
            f"reused_cross_task_knowledge: {reused_cross_task}",
            f"reused_knowledge_references: {', '.join(reused_knowledge_references) or '-'}",
            "",
            *build_knowledge_review_snapshot(
                knowledge_objects if isinstance(knowledge_objects, list) else [],
                knowledge_decisions,
            ),
            "",
            *build_canonical_registry_snapshot(canonical_registry_index),
            "",
            *build_canonical_reuse_snapshot(canonical_reuse_policy),
            "",
            *build_canonical_reuse_eval_snapshot(canonical_reuse_eval),
            "",
            *build_canonical_reuse_regression_snapshot(canonical_reuse_regression),
            "",
            *build_policy_snapshot(retry_policy, execution_budget_policy, stop_policy),
            "",
            "Review Artifacts",
            f"task_semantics_report: {state.artifact_paths.get('task_semantics_report', '-')}",
            f"knowledge_objects_report: {state.artifact_paths.get('knowledge_objects_report', '-')}",
            f"knowledge_partition_report: {state.artifact_paths.get('knowledge_partition_report', '-')}",
            f"knowledge_index_report: {state.artifact_paths.get('knowledge_index_report', '-')}",
            f"knowledge_decisions_report: {state.artifact_paths.get('knowledge_decisions_report', '-')}",
            f"canonical_registry_report: {state.artifact_paths.get('canonical_registry_report', '-')}",
            f"canonical_registry_index_report: {state.artifact_paths.get('canonical_registry_index_report', '-')}",
            f"canonical_reuse_policy_report: {state.artifact_paths.get('canonical_reuse_policy_report', '-')}",
            f"canonical_reuse_eval_report: {state.artifact_paths.get('canonical_reuse_eval_report', '-')}",
            f"canonical_reuse_regression_json: {state.artifact_paths.get('canonical_reuse_regression_json', '-')}",
            f"retrieval_report: {state.artifact_paths.get('retrieval_report', '-')}",
            f"source_grounding: {state.artifact_paths.get('source_grounding', '-')}",
            f"grounding_evidence_report: {state.artifact_paths.get('grounding_evidence_report', '-')}",
            f"resume_note: {state.artifact_paths.get('resume_note', '-')}",
            f"summary: {state.artifact_paths.get('summary', '-')}",
            f"handoff_report: {state.artifact_paths.get('handoff_report', '-')}",
            f"remote_handoff_contract_report: {state.artifact_paths.get('remote_handoff_contract_report', '-')}",
            f"validation_report: {state.artifact_paths.get('validation_report', '-')}",
            f"compatibility_report: {state.artifact_paths.get('compatibility_report', '-')}",
            f"execution_fit_report: {state.artifact_paths.get('execution_fit_report', '-')}",
            f"retry_policy_report: {state.artifact_paths.get('retry_policy_report', '-')}",
            f"execution_budget_policy_report: {state.artifact_paths.get('execution_budget_policy_report', '-')}",
            f"stop_policy_report: {state.artifact_paths.get('stop_policy_report', '-')}",
            f"checkpoint_snapshot_report: {state.artifact_paths.get('checkpoint_snapshot_report', '-')}",
            f"knowledge_policy_report: {state.artifact_paths.get('knowledge_policy_report', '-')}",
        ]
        print("\n".join(lines))
        return 0

    if args.command == "task" and args.task_command == "checkpoint":
        print((artifacts_dir(base_dir, args.task_id) / "checkpoint_snapshot_report.md").read_text(encoding="utf-8"), end="")
        return 0

    if args.command == "task" and args.task_command == "policy":
        state = load_state(base_dir, args.task_id)

        retry_policy = load_json_if_exists(retry_policy_path(base_dir, args.task_id))
        execution_budget_policy = load_json_if_exists(execution_budget_policy_path(base_dir, args.task_id))
        stop_policy = load_json_if_exists(stop_policy_path(base_dir, args.task_id))
        lines = [f"Task Policy: {state.task_id}", f"title: {state.title}", ""]
        lines.extend(build_policy_snapshot(retry_policy, execution_budget_policy, stop_policy))
        lines.extend(
            [
                "",
                "Policy Artifacts",
                f"retry_policy_report: {state.artifact_paths.get('retry_policy_report', '-')}",
                f"execution_budget_policy_report: {state.artifact_paths.get('execution_budget_policy_report', '-')}",
                f"stop_policy_report: {state.artifact_paths.get('stop_policy_report', '-')}",
            ]
        )
        print("\n".join(lines))
        return 0

    if args.command == "task" and args.task_command == "artifacts":
        state = load_state(base_dir, args.task_id)
        print(build_grouped_artifact_index(state.artifact_paths), end="")
        return 0

    if args.command == "task" and args.task_command in {
        "summarize",
        "semantics",
        "resume-note",
        "validation",
        "compatibility",
        "grounding",
        "knowledge-objects",
        "knowledge-partition",
        "knowledge-index",
        "knowledge-policy",
        "retrieval",
        "topology",
        "execution-site",
        "dispatch",
        "handoff",
        "remote-handoff",
        "execution-fit",
        "retry-policy",
        "execution-budget-policy",
        "stop-policy",
        "route",
    }:
        artifact_name = {
            "summarize": "summary.md",
            "semantics": "task_semantics_report.md",
            "resume-note": "resume_note.md",
            "validation": "validation_report.md",
            "compatibility": "compatibility_report.md",
            "grounding": "grounding_evidence_report.md",
            "knowledge-objects": "knowledge_objects_report.md",
            "knowledge-partition": "knowledge_partition_report.md",
            "knowledge-index": "knowledge_index_report.md",
            "knowledge-policy": "knowledge_policy_report.md",
            "retrieval": "retrieval_report.md",
            "topology": "topology_report.md",
            "execution-site": "execution_site_report.md",
            "dispatch": "dispatch_report.md",
            "handoff": "handoff_report.md",
            "remote-handoff": "remote_handoff_contract_report.md",
            "execution-fit": "execution_fit_report.md",
            "retry-policy": "retry_policy_report.md",
            "execution-budget-policy": "execution_budget_policy_report.md",
            "stop-policy": "stop_policy_report.md",
            "route": "route_report.md",
        }[args.task_command]
        artifact_output = (artifacts_dir(base_dir, args.task_id) / artifact_name).read_text(encoding="utf-8")
        if args.task_command == "dispatch":
            state = load_state(base_dir, args.task_id)
            topology = load_json_if_exists(topology_path(base_dir, args.task_id))
            if is_mock_remote_task(state, topology):
                print("[MOCK-REMOTE]")
        print(artifact_output, end="")
        return 0

    if args.command == "task" and args.task_command == "memory":
        print(json.dumps(json.loads(memory_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "compatibility-json":
        print(json.dumps(json.loads(compatibility_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "route-json":
        print(json.dumps(json.loads(route_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "topology-json":
        print(json.dumps(json.loads(topology_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "execution-site-json":
        print(json.dumps(json.loads(execution_site_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "dispatch-json":
        print(json.dumps(json.loads(dispatch_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "handoff-json":
        print(json.dumps(json.loads(handoff_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "remote-handoff-json":
        print(json.dumps(json.loads(remote_handoff_contract_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "execution-fit-json":
        print(json.dumps(json.loads(execution_fit_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "retry-policy-json":
        print(json.dumps(json.loads(retry_policy_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "execution-budget-policy-json":
        print(
            json.dumps(
                json.loads(execution_budget_policy_path(base_dir, args.task_id).read_text(encoding="utf-8")),
                indent=2,
            )
        )
        return 0

    if args.command == "task" and args.task_command == "stop-policy-json":
        print(json.dumps(json.loads(stop_policy_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "checkpoint-json":
        print(json.dumps(json.loads(checkpoint_snapshot_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "capabilities-json":
        print(json.dumps(json.loads(capability_assembly_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "semantics-json":
        print(json.dumps(json.loads(task_semantics_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "knowledge-objects-json":
        print(json.dumps(load_knowledge_objects(base_dir, args.task_id), indent=2))
        return 0

    if args.command == "task" and args.task_command == "knowledge-partition-json":
        print(json.dumps(json.loads(knowledge_partition_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "knowledge-index-json":
        print(json.dumps(json.loads(knowledge_index_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "knowledge-policy-json":
        print(json.dumps(json.loads(knowledge_policy_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "knowledge-decisions":
        print(build_knowledge_decisions_report(load_json_lines_if_exists(knowledge_decisions_path(base_dir, args.task_id))))
        return 0

    if args.command == "task" and args.task_command == "canonical-registry":
        print(build_canonical_registry_report(load_json_lines_if_exists(canonical_registry_path(base_dir))))
        return 0

    if args.command == "task" and args.task_command == "canonical-registry-index":
        print(build_canonical_registry_index_report(load_json_if_exists(canonical_registry_index_path(base_dir))))
        return 0

    if args.command == "task" and args.task_command == "canonical-reuse":
        print(build_canonical_reuse_report(load_json_if_exists(canonical_reuse_policy_path(base_dir))))
        return 0

    if args.command == "task" and args.task_command == "canonical-reuse-regression":
        baseline = load_json_if_exists(canonical_reuse_regression_path(base_dir, args.task_id))
        records = load_json_lines_if_exists(canonical_reuse_eval_path(base_dir, args.task_id))
        current = build_canonical_reuse_regression_current(
            task_id=args.task_id,
            summary=build_canonical_reuse_evaluation_summary(records),
        )
        comparison = compare_canonical_reuse_regression(baseline=baseline, current=current)
        print(build_canonical_reuse_regression_report(baseline=baseline, current=current, comparison=comparison))
        return 0

    if args.command == "task" and args.task_command == "canonical-reuse-eval":
        records = load_json_lines_if_exists(canonical_reuse_eval_path(base_dir, args.task_id))
        print(build_canonical_reuse_evaluation_report(records, build_canonical_reuse_evaluation_summary(records)))
        return 0

    if args.command == "task" and args.task_command == "knowledge-decisions-json":
        print(json.dumps(load_json_lines_if_exists(knowledge_decisions_path(base_dir, args.task_id)), indent=2))
        return 0

    if args.command == "task" and args.task_command == "canonical-registry-json":
        print(json.dumps(load_json_lines_if_exists(canonical_registry_path(base_dir)), indent=2))
        return 0

    if args.command == "task" and args.task_command == "canonical-registry-index-json":
        print(json.dumps(load_json_if_exists(canonical_registry_index_path(base_dir)), indent=2))
        return 0

    if args.command == "task" and args.task_command == "canonical-reuse-json":
        print(json.dumps(load_json_if_exists(canonical_reuse_policy_path(base_dir)), indent=2))
        return 0

    if args.command == "task" and args.task_command == "canonical-reuse-eval-json":
        print(json.dumps(load_json_lines_if_exists(canonical_reuse_eval_path(base_dir, args.task_id)), indent=2))
        return 0

    if args.command == "task" and args.task_command == "canonical-reuse-regression-json":
        print(json.dumps(load_json_if_exists(canonical_reuse_regression_path(base_dir, args.task_id)), indent=2))
        return 0

    if args.command == "task" and args.task_command == "retrieval-json":
        print(json.dumps(json.loads(retrieval_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "migrate":
        print(format_store_migration_summary(migrate_file_tasks_to_sqlite(base_dir, dry_run=args.dry_run)))
        return 0

    if args.command == "doctor":
        if args.doctor_command == "codex":
            exit_code, result = diagnose_codex()
            print(format_codex_doctor_result(result))
            return exit_code
        if args.doctor_command == "sqlite":
            exit_code, result = diagnose_sqlite_store(base_dir)
            print(format_sqlite_doctor_result(result))
            return exit_code
        if args.doctor_command == "stack":
            exit_code, result = diagnose_local_stack()
            print(format_local_stack_doctor_result(result))
            return exit_code

        codex_exit_code, codex_result = diagnose_codex()
        print(format_codex_doctor_result(codex_result))

        sqlite_exit_code, sqlite_result = diagnose_sqlite_store(base_dir)
        print()
        print(format_sqlite_doctor_result(sqlite_result))

        if args.skip_stack:
            return 0 if codex_exit_code == 0 and sqlite_exit_code == 0 else 1

        stack_exit_code, stack_result = diagnose_local_stack()
        print()
        print(format_local_stack_doctor_result(stack_result))
        return 0 if codex_exit_code == 0 and sqlite_exit_code == 0 and stack_exit_code == 0 else 1

    parser.error("Unsupported command.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
