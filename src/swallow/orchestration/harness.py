from __future__ import annotations

import asyncio
from dataclasses import replace
import json
from pathlib import Path
from time import perf_counter

from swallow.orchestration.checkpoint_snapshot import build_checkpoint_snapshot_report, evaluate_checkpoint_snapshot
from swallow.orchestration.compatibility import build_compatibility_report, evaluate_route_compatibility
from swallow.provider_router.cost_estimation import DEFAULT_COST_ESTIMATOR, CostEstimator
from swallow.orchestration.execution_budget_policy import (
    build_execution_budget_policy_report,
    evaluate_execution_budget_policy,
    normalize_token_cost_limit,
)
from swallow.orchestration.execution_fit import build_execution_fit_report, evaluate_execution_fit
from swallow.orchestration.executor import build_failure_recommendations, run_executor
from swallow.knowledge_retrieval.grounding import build_grounding_evidence, build_grounding_evidence_report, extract_grounding_entries
from swallow.knowledge_retrieval.knowledge_index import build_knowledge_index, build_knowledge_index_report
from swallow.knowledge_retrieval.knowledge_objects import (
    summarize_canonicalization,
    summarize_knowledge_evidence,
    summarize_knowledge_reuse,
    summarize_knowledge_stages,
)
from swallow.knowledge_retrieval.knowledge_policy import build_knowledge_policy_report, evaluate_knowledge_policy
from swallow.knowledge_retrieval.knowledge_suggestions import persist_executor_side_effects
from swallow.orchestration.models import (
    CompatibilityResult,
    EVENT_EXECUTOR_COMPLETED,
    EVENT_EXECUTOR_FAILED,
    EVENT_RETRIEVAL_COMPLETED,
    ExecutionFitResult,
    Event,
    ExecutionBudgetPolicyResult,
    ExecutorResult,
    HandoffContractSchema,
    KnowledgePolicyResult,
    RetrievalItem,
    RetrievalRequest,
    RetryPolicyResult,
    StopPolicyResult,
    TaskState,
    build_telemetry_fields,
    ValidationResult,
)
from swallow.knowledge_retrieval.retrieval import retrieve_context, summarize_reused_knowledge
from swallow.orchestration.retry_policy import build_retry_policy_report, evaluate_retry_policy
from swallow.orchestration.stop_policy import build_stop_policy_report, evaluate_stop_policy
from swallow.truth_governance.store import (
    append_event,
    save_compatibility,
    save_checkpoint_snapshot,
    save_dispatch,
    save_execution_budget_policy,
    save_execution_site,
    save_execution_fit,
    save_handoff,
    save_knowledge_index,
    save_knowledge_policy,
    save_memory,
    save_remote_handoff_contract,
    save_retrieval,
    save_retry_policy,
    save_route,
    save_stop_policy,
    save_topology,
    save_validation,
    write_artifact,
)
from swallow.orchestration.validator import build_validation_report, validate_run_outputs


def run_retrieval(base_dir: Path, state: TaskState, request: RetrievalRequest) -> list[RetrievalItem]:
    retrieval_items = retrieve_context(Path(state.workspace_root), request=request)
    reused_knowledge = summarize_reused_knowledge(retrieval_items)
    save_retrieval(base_dir, state.task_id, retrieval_items)
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type=EVENT_RETRIEVAL_COMPLETED,
            message="Retrieved local repository and note context.",
            payload={
                "count": len(retrieval_items),
                "query": request.query,
                "source_types_requested": request.source_types,
                "context_layers": request.context_layers,
                "limit": request.limit,
                "strategy": request.strategy,
                "top_paths": [item.path for item in retrieval_items[:3]],
                "top_citations": [item.reference() for item in retrieval_items[:3]],
                "source_types": sorted({item.source_type for item in retrieval_items}),
                "reused_knowledge_count": reused_knowledge["count"],
                "reused_knowledge_current_task_count": reused_knowledge["current_task_count"],
                "reused_knowledge_cross_task_count": reused_knowledge["cross_task_count"],
                "reused_knowledge_references": reused_knowledge["references"],
            },
        ),
    )
    return retrieval_items


async def run_retrieval_async(
    base_dir: Path,
    state: TaskState,
    request: RetrievalRequest,
) -> list[RetrievalItem]:
    return await asyncio.to_thread(run_retrieval, base_dir, state, request)


def run_execution(
    base_dir: Path,
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    *,
    cost_estimator: CostEstimator = DEFAULT_COST_ESTIMATOR,
) -> ExecutorResult:
    started_at = perf_counter()
    executor_result = run_executor(state, retrieval_items)
    executor_result = replace(
        executor_result,
        latency_ms=max(int((perf_counter() - started_at) * 1000), 0),
    )
    prompt_body = executor_result.prompt
    token_cost = cost_estimator.estimate(
        state.route_model_hint,
        executor_result.estimated_input_tokens,
        executor_result.estimated_output_tokens,
    )
    prompt_with_dialect = f"dialect: {executor_result.dialect or state.route_dialect or 'plain_text'}\n\n{prompt_body}"
    write_artifact(base_dir, state.task_id, "executor_prompt.md", prompt_with_dialect)
    write_artifact(base_dir, state.task_id, "executor_output.md", executor_result.output or executor_result.message)
    write_artifact(base_dir, state.task_id, "executor_stdout.txt", executor_result.stdout)
    write_artifact(base_dir, state.task_id, "executor_stderr.txt", executor_result.stderr)
    persist_executor_side_effects(base_dir, state.task_id, executor_result.side_effects)
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type=EVENT_EXECUTOR_COMPLETED if executor_result.status == "completed" else EVENT_EXECUTOR_FAILED,
            message=executor_result.message,
            payload={
                "status": executor_result.status,
                "executor_name": executor_result.executor_name,
                "route_mode": state.route_mode,
                "route_name": state.route_name,
                "route_backend": state.route_backend,
                "route_executor_family": state.route_executor_family,
                "route_execution_site": state.route_execution_site,
                "route_remote_capable": state.route_remote_capable,
                "route_transport_kind": state.route_transport_kind,
                "route_dialect": state.route_dialect,
                "route_capabilities": state.route_capabilities,
                "attempt_id": state.current_attempt_id,
                "attempt_number": state.current_attempt_number,
                "attempt_owner_kind": state.current_attempt_owner_kind,
                "attempt_owner_ref": state.current_attempt_owner_ref,
                "attempt_ownership_status": state.current_attempt_ownership_status,
                "attempt_owner_assigned_at": state.current_attempt_owner_assigned_at,
                "attempt_transfer_reason": state.current_attempt_transfer_reason,
                "topology_route_name": state.topology_route_name,
                "topology_executor_family": state.topology_executor_family,
                "topology_execution_site": state.topology_execution_site,
                "topology_transport_kind": state.topology_transport_kind,
                "topology_remote_capable_intent": state.topology_remote_capable_intent,
                "topology_dispatch_status": state.topology_dispatch_status,
                "execution_site_contract_kind": state.execution_site_contract_kind,
                "execution_site_boundary": state.execution_site_boundary,
                "execution_site_contract_status": state.execution_site_contract_status,
                "execution_site_handoff_required": state.execution_site_handoff_required,
                "execution_site_contract_reason": state.execution_site_contract_reason,
                "dispatch_requested_at": state.dispatch_requested_at,
                "dispatch_started_at": state.dispatch_started_at,
                "execution_lifecycle": state.execution_lifecycle,
                "dialect": executor_result.dialect or state.route_dialect,
                "failure_kind": executor_result.failure_kind,
                "review_feedback": executor_result.review_feedback,
                "degraded": executor_result.degraded or state.route_is_fallback,
                "original_route_name": executor_result.original_route_name,
                "fallback_route_name": executor_result.fallback_route_name,
                "output_written": [
                    "executor_prompt.md",
                    "executor_output.md",
                    "executor_stdout.txt",
                    "executor_stderr.txt",
                ],
            }
            | build_telemetry_fields(
                state,
                latency_ms=executor_result.latency_ms,
                degraded=executor_result.degraded or state.route_is_fallback,
                token_cost=token_cost,
                error_code=executor_result.failure_kind if executor_result.status == "failed" else "",
            ).to_dict(),
        ),
    )
    return executor_result


def write_task_artifacts(
    base_dir: Path,
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    executor_result: ExecutorResult,
    grounding_evidence_override: dict[str, object] | None = None,
) -> tuple[
    CompatibilityResult,
    ExecutionFitResult,
    KnowledgePolicyResult,
    ValidationResult,
    RetryPolicyResult,
    StopPolicyResult,
    ExecutionBudgetPolicyResult,
]:
    # Persist policy records separately so operators can inspect execution control without reading raw handoff text.
    knowledge_index = build_knowledge_index(state.knowledge_objects)
    save_route(base_dir, state.task_id, build_route_record(state))
    save_topology(base_dir, state.task_id, build_topology_record(state))
    save_execution_site(base_dir, state.task_id, build_execution_site_record(state))
    save_dispatch(base_dir, state.task_id, build_dispatch_record(state))
    remote_handoff_contract_record = build_remote_handoff_contract_record(state)
    save_remote_handoff_contract(base_dir, state.task_id, remote_handoff_contract_record)
    write_artifact(
        base_dir,
        state.task_id,
        "route_report.md",
        build_route_report(state),
    )
    write_artifact(
        base_dir,
        state.task_id,
        "topology_report.md",
        build_topology_report(state),
    )
    write_artifact(
        base_dir,
        state.task_id,
        "execution_site_report.md",
        build_execution_site_report(state),
    )
    write_artifact(
        base_dir,
        state.task_id,
        "dispatch_report.md",
        build_dispatch_report(state),
    )
    write_artifact(
        base_dir,
        state.task_id,
        "remote_handoff_contract_report.md",
        build_remote_handoff_contract_report(remote_handoff_contract_record),
    )
    write_artifact(
        base_dir,
        state.task_id,
        "knowledge_index_report.md",
        build_knowledge_index_report(knowledge_index),
    )
    save_knowledge_index(base_dir, state.task_id, knowledge_index)
    write_artifact(
        base_dir,
        state.task_id,
        "source_grounding.md",
        build_source_grounding(retrieval_items),
    )
    grounding_evidence = grounding_evidence_override
    if grounding_evidence is None:
        grounding_entries = extract_grounding_entries(retrieval_items)
        grounding_evidence = build_grounding_evidence(grounding_entries)
    write_artifact(
        base_dir,
        state.task_id,
        "grounding_evidence.json",
        json.dumps(grounding_evidence, indent=2) + "\n",
    )
    write_artifact(
        base_dir,
        state.task_id,
        "grounding_evidence_report.md",
        build_grounding_evidence_report(grounding_evidence),
    )
    write_artifact(
        base_dir,
        state.task_id,
        "retrieval_report.md",
        build_retrieval_report(state, retrieval_items),
    )
    provisional_state = replace(state, status="running")
    write_artifact(
        base_dir,
        state.task_id,
        "summary.md",
        build_summary(provisional_state, retrieval_items, executor_result, None, None, None, None, None, None, None),
    )
    write_artifact(
        base_dir,
        state.task_id,
        "resume_note.md",
        build_resume_note(provisional_state, retrieval_items, executor_result, None, None, None, None, None, None, None),
    )

    compatibility_result = evaluate_route_compatibility(state, executor_result)
    save_compatibility(base_dir, state.task_id, build_compatibility_record(state, executor_result, compatibility_result))
    write_artifact(
        base_dir,
        state.task_id,
        "compatibility_report.md",
        build_compatibility_report(compatibility_result),
    )
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="compatibility.completed",
            message=compatibility_result.message,
            payload={
                "status": compatibility_result.status,
                "finding_counts": compatibility_counts(compatibility_result),
            },
        ),
    )

    execution_fit_result = evaluate_execution_fit(state, executor_result)
    save_execution_fit(base_dir, state.task_id, execution_fit_result.to_dict())
    write_artifact(
        base_dir,
        state.task_id,
        "execution_fit_report.md",
        build_execution_fit_report(execution_fit_result),
    )
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="execution_fit.completed",
            message=execution_fit_result.message,
            payload={
                "status": execution_fit_result.status,
                "finding_counts": execution_fit_counts(execution_fit_result),
            },
        ),
    )

    knowledge_policy_result = evaluate_knowledge_policy(state)
    save_knowledge_policy(base_dir, state.task_id, knowledge_policy_result.to_dict())
    write_artifact(
        base_dir,
        state.task_id,
        "knowledge_policy_report.md",
        build_knowledge_policy_report(knowledge_policy_result),
    )
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="knowledge_policy.completed",
            message=knowledge_policy_result.message,
            payload={
                "status": knowledge_policy_result.status,
                "finding_counts": knowledge_policy_counts(knowledge_policy_result),
            },
        ),
    )

    validation_result = validate_run_outputs(state, retrieval_items, executor_result, state.artifact_paths)
    save_validation(base_dir, state.task_id, validation_result)
    write_artifact(base_dir, state.task_id, "validation_report.md", build_validation_report(validation_result))
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="validation.completed",
            message=validation_result.message,
            payload={
                "status": validation_result.status,
                "finding_counts": validation_counts(validation_result),
            },
        ),
    )

    retry_policy_result = evaluate_retry_policy(
        state,
        executor_result,
        compatibility_result,
        execution_fit_result,
        knowledge_policy_result,
        validation_result,
    )
    save_retry_policy(base_dir, state.task_id, retry_policy_result.to_dict())
    write_artifact(
        base_dir,
        state.task_id,
        "retry_policy_report.md",
        build_retry_policy_report(retry_policy_result),
    )
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="retry_policy.completed",
            message=retry_policy_result.message,
            payload={
                "status": retry_policy_result.status,
                "retryable": retry_policy_result.retryable,
                "retry_decision": retry_policy_result.retry_decision,
                "remaining_attempts": retry_policy_result.remaining_attempts,
                "checkpoint_required": retry_policy_result.checkpoint_required,
            },
        ),
    )

    execution_budget_policy_result = evaluate_execution_budget_policy(
        retry_policy_result,
        base_dir=base_dir,
        task_id=state.task_id,
        token_cost_limit=normalize_token_cost_limit(
            state.task_semantics.get("token_cost_limit", 0.0) if state.task_semantics else 0.0
        ),
    )
    save_execution_budget_policy(base_dir, state.task_id, execution_budget_policy_result.to_dict())
    write_artifact(
        base_dir,
        state.task_id,
        "execution_budget_policy_report.md",
        build_execution_budget_policy_report(execution_budget_policy_result),
    )
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="execution_budget_policy.completed",
            message=execution_budget_policy_result.message,
            payload={
                "status": execution_budget_policy_result.status,
                "timeout_seconds": execution_budget_policy_result.timeout_seconds,
                "budget_state": execution_budget_policy_result.budget_state,
                "timeout_state": execution_budget_policy_result.timeout_state,
                "remaining_attempts": execution_budget_policy_result.remaining_attempts,
                "current_token_cost": execution_budget_policy_result.current_token_cost,
                "token_cost_limit": execution_budget_policy_result.token_cost_limit,
            },
        ),
    )

    stop_policy_result = evaluate_stop_policy(state, executor_result, retry_policy_result)
    save_stop_policy(base_dir, state.task_id, stop_policy_result.to_dict())
    write_artifact(
        base_dir,
        state.task_id,
        "stop_policy_report.md",
        build_stop_policy_report(stop_policy_result),
    )
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="stop_policy.completed",
            message=stop_policy_result.message,
            payload={
                "status": stop_policy_result.status,
                "stop_required": stop_policy_result.stop_required,
                "continue_allowed": stop_policy_result.continue_allowed,
                "stop_decision": stop_policy_result.stop_decision,
                "escalation_level": stop_policy_result.escalation_level,
                "checkpoint_kind": stop_policy_result.checkpoint_kind,
            },
        ),
    )

    if state.status == "waiting_human":
        final_status = "waiting_human"
        final_execution_lifecycle = "waiting_human"
    else:
        final_status = (
            "completed"
            if executor_result.status == "completed"
            and compatibility_result.status != "failed"
            and execution_fit_result.status != "failed"
            and knowledge_policy_result.status != "failed"
            and validation_result.status != "failed"
            else "failed"
        )
        final_execution_lifecycle = "completed" if final_status == "completed" else "failed"
    render_state = replace(
        state,
        status=final_status,
        execution_lifecycle=final_execution_lifecycle,
    )
    handoff_record = build_handoff_record(
        render_state,
        executor_result,
        compatibility_result,
        execution_fit_result,
        knowledge_policy_result,
        validation_result,
        retry_policy_result,
        stop_policy_result,
        execution_budget_policy_result,
    )
    save_handoff(base_dir, state.task_id, handoff_record)
    write_artifact(
        base_dir,
        state.task_id,
        "handoff_report.md",
        build_handoff_report(handoff_record),
    )
    checkpoint_snapshot_result = evaluate_checkpoint_snapshot(
        render_state,
        handoff_record,
        retry_policy_result.to_dict(),
        stop_policy_result.to_dict(),
        execution_budget_policy_result.to_dict(),
    )
    save_checkpoint_snapshot(base_dir, state.task_id, checkpoint_snapshot_result.to_dict())
    write_artifact(
        base_dir,
        state.task_id,
        "checkpoint_snapshot_report.md",
        build_checkpoint_snapshot_report(checkpoint_snapshot_result),
    )
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="checkpoint_snapshot.completed",
            message=checkpoint_snapshot_result.message,
            payload={
                "status": checkpoint_snapshot_result.status,
                "checkpoint_state": checkpoint_snapshot_result.checkpoint_state,
                "execution_phase": checkpoint_snapshot_result.execution_phase,
                "last_phase_checkpoint_at": checkpoint_snapshot_result.last_phase_checkpoint_at,
                "recommended_path": checkpoint_snapshot_result.recommended_path,
                "resume_ready": checkpoint_snapshot_result.resume_ready,
            },
        ),
    )
    save_memory(
        base_dir,
        state.task_id,
        build_task_memory(
            render_state,
            retrieval_items,
            executor_result,
            compatibility_result,
            execution_fit_result,
            knowledge_policy_result,
            validation_result,
            retry_policy_result,
            stop_policy_result,
            execution_budget_policy_result,
            handoff_record,
            checkpoint_snapshot_result.to_dict(),
        ),
    )
    write_artifact(
        base_dir,
        state.task_id,
        "summary.md",
        build_summary(
            render_state,
            retrieval_items,
            executor_result,
            compatibility_result,
            execution_fit_result,
            knowledge_policy_result,
            validation_result,
            retry_policy_result,
            stop_policy_result,
            execution_budget_policy_result,
        ),
    )
    write_artifact(
        base_dir,
        state.task_id,
        "resume_note.md",
        build_resume_note(
            render_state,
            retrieval_items,
            executor_result,
            compatibility_result,
            execution_fit_result,
            knowledge_policy_result,
            validation_result,
            retry_policy_result,
            stop_policy_result,
            execution_budget_policy_result,
        ),
    )
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="artifacts.written",
            message="Wrote summary, resume note, compatibility, and validation artifacts.",
            payload={
                "status": final_status,
                "phase": state.phase,
                "artifact_paths": {
                    "task_semantics_report": state.artifact_paths.get("task_semantics_report", ""),
                    "knowledge_objects_report": state.artifact_paths.get("knowledge_objects_report", ""),
                    "knowledge_partition_report": state.artifact_paths.get("knowledge_partition_report", ""),
                    "knowledge_index_report": state.artifact_paths.get("knowledge_index_report", ""),
                    "summary": state.artifact_paths.get("summary", ""),
                    "resume_note": state.artifact_paths.get("resume_note", ""),
                    "route_report": state.artifact_paths.get("route_report", ""),
                    "topology_report": state.artifact_paths.get("topology_report", ""),
                    "execution_site_report": state.artifact_paths.get("execution_site_report", ""),
                    "dispatch_report": state.artifact_paths.get("dispatch_report", ""),
                    "handoff_report": state.artifact_paths.get("handoff_report", ""),
                    "execution_fit_report": state.artifact_paths.get("execution_fit_report", ""),
                    "retry_policy_report": state.artifact_paths.get("retry_policy_report", ""),
                    "execution_budget_policy_report": state.artifact_paths.get("execution_budget_policy_report", ""),
                    "stop_policy_report": state.artifact_paths.get("stop_policy_report", ""),
                    "compatibility_report": state.artifact_paths.get("compatibility_report", ""),
                    "knowledge_policy_report": state.artifact_paths.get("knowledge_policy_report", ""),
                    "source_grounding": state.artifact_paths.get("source_grounding", ""),
                    "grounding_evidence_json": state.artifact_paths.get("grounding_evidence_json", ""),
                    "grounding_evidence_report": state.artifact_paths.get("grounding_evidence_report", ""),
                    "retrieval_report": state.artifact_paths.get("retrieval_report", ""),
                    "validation_report": state.artifact_paths.get("validation_report", ""),
                    "task_memory": state.artifact_paths.get("task_memory", ""),
                },
            },
        ),
    )
    return (
        compatibility_result,
        execution_fit_result,
        knowledge_policy_result,
        validation_result,
        retry_policy_result,
        stop_policy_result,
        execution_budget_policy_result,
    )


async def write_task_artifacts_async(
    base_dir: Path,
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    executor_result: ExecutorResult,
    grounding_evidence_override: dict[str, object] | None = None,
) -> tuple[
    CompatibilityResult,
    ExecutionFitResult,
    KnowledgePolicyResult,
    ValidationResult,
    RetryPolicyResult,
    StopPolicyResult,
    ExecutionBudgetPolicyResult,
]:
    return await asyncio.to_thread(
        write_task_artifacts,
        base_dir,
        state,
        retrieval_items,
        executor_result,
        grounding_evidence_override,
    )


def validation_counts(result: ValidationResult) -> dict[str, int]:
    counts = {"pass": 0, "warn": 0, "fail": 0}
    for finding in result.findings:
        counts[finding.level] = counts.get(finding.level, 0) + 1
    return counts


def compatibility_counts(result: CompatibilityResult) -> dict[str, int]:
    counts = {"pass": 0, "warn": 0, "fail": 0}
    for finding in result.findings:
        counts[finding.level] = counts.get(finding.level, 0) + 1
    return counts


def execution_fit_counts(result: ExecutionFitResult) -> dict[str, int]:
    counts = {"pass": 0, "warn": 0, "fail": 0}
    for finding in result.findings:
        counts[finding.level] = counts.get(finding.level, 0) + 1
    return counts


def knowledge_policy_counts(result: KnowledgePolicyResult) -> dict[str, int]:
    counts = {"pass": 0, "warn": 0, "fail": 0}
    for finding in result.findings:
        counts[finding.level] = counts.get(finding.level, 0) + 1
    return counts


def format_route_capabilities(capabilities: dict[str, object]) -> str:
    if not capabilities:
        return "none"
    ordered_keys = [
        "execution_kind",
        "supports_tool_loop",
        "filesystem_access",
        "network_access",
        "deterministic",
        "resumable",
    ]
    return ", ".join(f"{key}={capabilities.get(key)}" for key in ordered_keys if key in capabilities)


def build_source_grounding(retrieval_items: list[RetrievalItem]) -> str:
    lines = ["# Source Grounding", "", "## Top Retrieved Sources"]
    if not retrieval_items:
        lines.append("- No retrieval matches were available for this run.")
        return "\n".join(lines)

    for item in retrieval_items:
        score_context = ", ".join(f"{key}={value}" for key, value in item.score_breakdown.items()) or "none"
        matched_terms = ", ".join(item.matched_terms) or "none"
        lines.extend(
            [
                f"- [{item.source_type}] {item.reference()}",
                f"  title: {item.display_title()}",
                f"  storage_scope: {item.metadata.get('storage_scope', 'unknown')}",
                f"  knowledge_task_relation: {item.metadata.get('knowledge_task_relation', 'n/a')}",
                f"  canonical_id: {item.metadata.get('canonical_id', '') or 'none'}",
                f"  canonical_policy: {item.metadata.get('canonical_policy', '') or 'none'}",
                f"  source_ref: {item.metadata.get('source_ref', '') or 'none'}",
                f"  artifact_ref: {item.metadata.get('artifact_ref', '') or 'none'}",
                f"  score: {item.score}",
                f"  matched_terms: {matched_terms}",
                f"  score_breakdown: {score_context}",
                f"  preview: {item.preview or '(empty)'}",
            ]
        )
    return "\n".join(lines)


def build_retrieval_report(state: TaskState, retrieval_items: list[RetrievalItem]) -> str:
    reused_knowledge = summarize_reused_knowledge(retrieval_items)
    lines = [
        "# Retrieval Report",
        "",
        f"- retrieval_count: {len(retrieval_items)}",
        f"- reused_knowledge_count: {reused_knowledge['count']}",
        f"- reused_task_knowledge_count: {reused_knowledge.get('task_knowledge_count', 0)}",
        f"- reused_canonical_registry_count: {reused_knowledge.get('canonical_registry_count', 0)}",
        f"- reused_knowledge_current_task_count: {reused_knowledge['current_task_count']}",
        f"- reused_knowledge_cross_task_count: {reused_knowledge['cross_task_count']}",
        f"- reused_knowledge_references: {', '.join(reused_knowledge['references']) or 'none'}",
        f"- retrieval_record_path: {state.artifact_paths.get('retrieval_json', '') or 'pending'}",
        f"- source_grounding_artifact: {state.artifact_paths.get('source_grounding', '') or 'pending'}",
        f"- task_memory_path: {state.artifact_paths.get('task_memory', '') or 'pending'}",
        "",
        "## Top References",
    ]
    if not retrieval_items:
        lines.append("- No retrieval matches were available for this run.")
        return "\n".join(lines)

    for item in retrieval_items[:8]:
        lines.extend(
            [
                f"- [{item.source_type}] {item.reference()}",
                f"  title: {item.display_title()}",
                f"  score: {item.score}",
                f"  adapter: {item.metadata.get('adapter_name', 'unknown')}",
                f"  chunk_kind: {item.metadata.get('chunk_kind', 'unknown')}",
                f"  storage_scope: {item.metadata.get('storage_scope', 'unknown')}",
                f"  knowledge_task_relation: {item.metadata.get('knowledge_task_relation', 'n/a')}",
                f"  canonical_id: {item.metadata.get('canonical_id', '') or 'none'}",
                f"  canonical_policy: {item.metadata.get('canonical_policy', '') or 'none'}",
                f"  source_ref: {item.metadata.get('source_ref', '') or 'none'}",
                f"  artifact_ref: {item.metadata.get('artifact_ref', '') or 'none'}",
            ]
        )
    return "\n".join(lines)


def build_task_memory(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    executor_result: ExecutorResult,
    compatibility_result: CompatibilityResult,
    execution_fit_result: ExecutionFitResult,
    knowledge_policy_result: KnowledgePolicyResult,
    validation_result: ValidationResult,
    retry_policy_result: RetryPolicyResult,
    stop_policy_result: StopPolicyResult,
    execution_budget_policy_result: ExecutionBudgetPolicyResult,
    handoff_record: dict[str, object],
    checkpoint_snapshot: dict[str, object],
) -> dict[str, object]:
    reused_knowledge = summarize_reused_knowledge(retrieval_items)
    knowledge_index = build_knowledge_index(state.knowledge_objects)
    canonicalization_counts = summarize_canonicalization(state.knowledge_objects)
    return {
        "task_id": state.task_id,
        "task_title": state.title,
        "goal": state.goal,
        "phase": state.phase,
        "status": state.status,
        "execution_phase": state.execution_phase,
        "last_phase_checkpoint_at": state.last_phase_checkpoint_at,
        "workspace_root": state.workspace_root,
        "task_semantics": state.task_semantics,
        "knowledge_objects": {
            "count": len(state.knowledge_objects),
            "stage_counts": summarize_knowledge_stages(state.knowledge_objects),
            "evidence_counts": summarize_knowledge_evidence(state.knowledge_objects),
            "reuse_counts": summarize_knowledge_reuse(state.knowledge_objects),
            "canonicalization_counts": canonicalization_counts,
            "items": state.knowledge_objects[:5],
        },
        "knowledge_partition": {
            "task_linked_count": len(state.knowledge_objects),
            "reusable_candidate_count": summarize_knowledge_reuse(state.knowledge_objects).get("retrieval_candidate", 0),
        },
        "knowledge_index": {
            "active_reusable_count": knowledge_index["active_reusable_count"],
            "inactive_reusable_count": knowledge_index["inactive_reusable_count"],
            "refreshed_at": knowledge_index["refreshed_at"],
            "reusable_records": knowledge_index["reusable_records"][:5],
            "inactive_records": knowledge_index["inactive_records"][:5],
        },
        "executor": {
            "name": executor_result.executor_name,
            "status": executor_result.status,
            "message": executor_result.message,
            "failure_kind": executor_result.failure_kind,
        },
        "execution_attempt": {
            "attempt_id": state.current_attempt_id,
            "attempt_number": state.current_attempt_number,
            "owner_kind": state.current_attempt_owner_kind,
            "owner_ref": state.current_attempt_owner_ref,
            "ownership_status": state.current_attempt_ownership_status,
            "owner_assigned_at": state.current_attempt_owner_assigned_at,
            "transfer_reason": state.current_attempt_transfer_reason,
            "dispatch_requested_at": state.dispatch_requested_at,
            "dispatch_started_at": state.dispatch_started_at,
            "execution_lifecycle": state.execution_lifecycle,
        },
        "route": {
            "mode": state.route_mode,
            "name": state.route_name,
            "backend": state.route_backend,
            "executor_family": state.route_executor_family,
            "execution_site": state.route_execution_site,
            "remote_capable": state.route_remote_capable,
            "transport_kind": state.route_transport_kind,
            "model_hint": state.route_model_hint,
            "reason": state.route_reason,
            "capabilities": state.route_capabilities,
        },
        "topology": build_topology_record(state),
        "execution_site": build_execution_site_record(state),
        "dispatch": build_dispatch_record(state),
        "handoff": handoff_record,
        "compatibility": compatibility_result.to_dict(),
        "execution_fit": execution_fit_result.to_dict(),
        "retry_policy": retry_policy_result.to_dict(),
        "execution_budget_policy": execution_budget_policy_result.to_dict(),
        "stop_policy": stop_policy_result.to_dict(),
        "checkpoint_snapshot": checkpoint_snapshot,
        "knowledge_policy": knowledge_policy_result.to_dict(),
        "validation": validation_result.to_dict(),
        "retrieval": {
            "count": len(retrieval_items),
            "top_references": [item.reference() for item in retrieval_items[:5]],
            "reused_knowledge_count": reused_knowledge["count"],
            "reused_task_knowledge_count": reused_knowledge.get("task_knowledge_count", 0),
            "reused_canonical_registry_count": reused_knowledge.get("canonical_registry_count", 0),
            "reused_knowledge_current_task_count": reused_knowledge["current_task_count"],
            "reused_knowledge_cross_task_count": reused_knowledge["cross_task_count"],
            "reused_knowledge_references": reused_knowledge["references"],
            "reused_knowledge_object_ids": reused_knowledge["object_ids"],
            "reused_knowledge_evidence_counts": reused_knowledge["evidence_counts"],
            "grounding_artifact": state.artifact_paths.get("source_grounding", ""),
            "retrieval_record_path": state.artifact_paths.get("retrieval_json", ""),
            "retrieval_report_artifact": state.artifact_paths.get("retrieval_report", ""),
            "reuse_ready": bool(retrieval_items),
            "top_items": [
                {
                    "path": item.path,
                    "citation": item.reference(),
                    "title": item.display_title(),
                    "source_type": item.source_type,
                    "score": item.score,
                    "storage_scope": item.metadata.get("storage_scope", ""),
                    "canonical_id": item.metadata.get("canonical_id", ""),
                    "canonical_policy": item.metadata.get("canonical_policy", ""),
                    "source_ref": item.metadata.get("source_ref", ""),
                    "artifact_ref": item.metadata.get("artifact_ref", ""),
                }
                for item in retrieval_items[:5]
            ],
        },
        "artifact_paths": {
            "task_semantics_json": state.artifact_paths.get("task_semantics_json", ""),
            "task_semantics_report": state.artifact_paths.get("task_semantics_report", ""),
            "knowledge_objects_json": state.artifact_paths.get("knowledge_objects_json", ""),
            "knowledge_objects_report": state.artifact_paths.get("knowledge_objects_report", ""),
            "knowledge_partition_json": state.artifact_paths.get("knowledge_partition_json", ""),
            "knowledge_partition_report": state.artifact_paths.get("knowledge_partition_report", ""),
            "knowledge_index_json": state.artifact_paths.get("knowledge_index_json", ""),
            "knowledge_index_report": state.artifact_paths.get("knowledge_index_report", ""),
            "summary": state.artifact_paths.get("summary", ""),
            "resume_note": state.artifact_paths.get("resume_note", ""),
            "route_report": state.artifact_paths.get("route_report", ""),
            "route_json": state.artifact_paths.get("route_json", ""),
            "topology_report": state.artifact_paths.get("topology_report", ""),
            "topology_json": state.artifact_paths.get("topology_json", ""),
            "execution_site_report": state.artifact_paths.get("execution_site_report", ""),
            "execution_site_json": state.artifact_paths.get("execution_site_json", ""),
            "dispatch_report": state.artifact_paths.get("dispatch_report", ""),
            "dispatch_json": state.artifact_paths.get("dispatch_json", ""),
            "handoff_report": state.artifact_paths.get("handoff_report", ""),
            "handoff_json": state.artifact_paths.get("handoff_json", ""),
            "execution_fit_report": state.artifact_paths.get("execution_fit_report", ""),
            "execution_fit_json": state.artifact_paths.get("execution_fit_json", ""),
            "retry_policy_report": state.artifact_paths.get("retry_policy_report", ""),
            "retry_policy_json": state.artifact_paths.get("retry_policy_json", ""),
            "execution_budget_policy_report": state.artifact_paths.get("execution_budget_policy_report", ""),
            "execution_budget_policy_json": state.artifact_paths.get("execution_budget_policy_json", ""),
            "stop_policy_report": state.artifact_paths.get("stop_policy_report", ""),
            "stop_policy_json": state.artifact_paths.get("stop_policy_json", ""),
            "checkpoint_snapshot_report": state.artifact_paths.get("checkpoint_snapshot_report", ""),
            "checkpoint_snapshot_json": state.artifact_paths.get("checkpoint_snapshot_json", ""),
            "compatibility_report": state.artifact_paths.get("compatibility_report", ""),
            "compatibility_json": state.artifact_paths.get("compatibility_json", ""),
            "knowledge_policy_report": state.artifact_paths.get("knowledge_policy_report", ""),
            "knowledge_policy_json": state.artifact_paths.get("knowledge_policy_json", ""),
            "source_grounding": state.artifact_paths.get("source_grounding", ""),
            "grounding_evidence_json": state.artifact_paths.get("grounding_evidence_json", ""),
            "grounding_evidence_report": state.artifact_paths.get("grounding_evidence_report", ""),
            "retrieval_report": state.artifact_paths.get("retrieval_report", ""),
            "retrieval_json": state.artifact_paths.get("retrieval_json", ""),
            "validation_report": state.artifact_paths.get("validation_report", ""),
            "validation_json": state.artifact_paths.get("validation_json", ""),
        },
    }


def build_route_record(state: TaskState) -> dict[str, object]:
    return {
        "mode": state.route_mode,
        "name": state.route_name,
        "backend": state.route_backend,
        "executor_family": state.route_executor_family,
        "execution_site": state.route_execution_site,
        "remote_capable": state.route_remote_capable,
        "transport_kind": state.route_transport_kind,
        "model_hint": state.route_model_hint,
        "dialect": state.route_dialect,
        "reason": state.route_reason,
        "capabilities": state.route_capabilities,
    }


def build_route_report(state: TaskState) -> str:
    return "\n".join(
        [
            "# Route Report",
            "",
            f"- mode: {state.route_mode}",
            f"- name: {state.route_name}",
            f"- backend: {state.route_backend}",
            f"- executor_family: {state.route_executor_family}",
            f"- execution_site: {state.route_execution_site}",
            f"- remote_capable: {'yes' if state.route_remote_capable else 'no'}",
            f"- transport_kind: {state.route_transport_kind}",
            f"- model_hint: {state.route_model_hint}",
            f"- dialect: {state.route_dialect}",
            f"- reason: {state.route_reason}",
            f"- capabilities: {format_route_capabilities(state.route_capabilities)}",
        ]
    )


def build_topology_record(state: TaskState) -> dict[str, object]:
    return {
        "route_name": state.topology_route_name,
        "executor_family": state.topology_executor_family,
        "execution_site": state.topology_execution_site,
        "transport_kind": state.topology_transport_kind,
        "remote_capable_intent": state.topology_remote_capable_intent,
        "dispatch_status": state.topology_dispatch_status,
        "execution_lifecycle": state.execution_lifecycle,
    }


def build_topology_report(state: TaskState) -> str:
    return "\n".join(
        [
            "# Topology Report",
            "",
            f"- route_name: {state.topology_route_name}",
            f"- executor_family: {state.topology_executor_family}",
            f"- execution_site: {state.topology_execution_site}",
            f"- transport_kind: {state.topology_transport_kind}",
            f"- remote_capable_intent: {'yes' if state.topology_remote_capable_intent else 'no'}",
            f"- dispatch_status: {state.topology_dispatch_status}",
            f"- execution_lifecycle: {state.execution_lifecycle}",
        ]
    )


def build_execution_site_record(state: TaskState) -> dict[str, object]:
    remote_handoff = build_remote_handoff_contract_record(state)
    return {
        "contract_kind": state.execution_site_contract_kind,
        "boundary": state.execution_site_boundary,
        "contract_status": state.execution_site_contract_status,
        "handoff_required": state.execution_site_handoff_required,
        "reason": state.execution_site_contract_reason,
        "execution_site": state.topology_execution_site,
        "executor_family": state.topology_executor_family,
        "transport_kind": state.topology_transport_kind,
        "remote_capable_intent": state.topology_remote_capable_intent,
        "dispatch_status": state.topology_dispatch_status,
        "execution_lifecycle": state.execution_lifecycle,
        "remote_handoff_contract_kind": remote_handoff["contract_kind"],
        "remote_handoff_contract_status": remote_handoff["contract_status"],
        "remote_handoff_boundary": remote_handoff["handoff_boundary"],
        "remote_handoff_dispatch_readiness": remote_handoff["dispatch_readiness"],
        "remote_handoff_operator_ack_required": remote_handoff["operator_ack_required"],
    }


def build_execution_site_report(state: TaskState) -> str:
    remote_handoff = build_remote_handoff_contract_record(state)
    return "\n".join(
        [
            "# Execution Site Report",
            "",
            f"- contract_kind: {state.execution_site_contract_kind}",
            f"- boundary: {state.execution_site_boundary}",
            f"- contract_status: {state.execution_site_contract_status}",
            f"- handoff_required: {'yes' if state.execution_site_handoff_required else 'no'}",
            f"- reason: {state.execution_site_contract_reason}",
            f"- execution_site: {state.topology_execution_site}",
            f"- executor_family: {state.topology_executor_family}",
            f"- transport_kind: {state.topology_transport_kind}",
            f"- remote_capable_intent: {'yes' if state.topology_remote_capable_intent else 'no'}",
            f"- dispatch_status: {state.topology_dispatch_status}",
            f"- execution_lifecycle: {state.execution_lifecycle}",
            "",
            "## Remote Handoff Contract",
            f"- contract_kind: {remote_handoff['contract_kind']}",
            f"- contract_status: {remote_handoff['contract_status']}",
            f"- handoff_boundary: {remote_handoff['handoff_boundary']}",
            f"- transport_truth: {remote_handoff['transport_truth']}",
            f"- ownership_required: {remote_handoff['ownership_required']}",
            f"- dispatch_readiness: {remote_handoff['dispatch_readiness']}",
            f"- operator_ack_required: {'yes' if remote_handoff['operator_ack_required'] else 'no'}",
        ]
    )


def build_dispatch_record(state: TaskState) -> dict[str, object]:
    remote_handoff = build_remote_handoff_contract_record(state)
    return {
        "attempt_id": state.current_attempt_id,
        "attempt_number": state.current_attempt_number,
        "attempt_owner_kind": state.current_attempt_owner_kind,
        "attempt_owner_ref": state.current_attempt_owner_ref,
        "attempt_ownership_status": state.current_attempt_ownership_status,
        "attempt_owner_assigned_at": state.current_attempt_owner_assigned_at,
        "attempt_transfer_reason": state.current_attempt_transfer_reason,
        "route_name": state.route_name,
        "execution_site_contract_kind": state.execution_site_contract_kind,
        "execution_site_boundary": state.execution_site_boundary,
        "executor_family": state.topology_executor_family,
        "execution_site": state.topology_execution_site,
        "transport_kind": state.topology_transport_kind,
        "dispatch_status": state.topology_dispatch_status,
        "dispatch_requested_at": state.dispatch_requested_at,
        "dispatch_started_at": state.dispatch_started_at,
        "execution_lifecycle": state.execution_lifecycle,
        "remote_handoff_contract_kind": remote_handoff["contract_kind"],
        "remote_handoff_contract_status": remote_handoff["contract_status"],
        "remote_handoff_boundary": remote_handoff["handoff_boundary"],
        "remote_handoff_transport_truth": remote_handoff["transport_truth"],
        "remote_handoff_ownership_required": remote_handoff["ownership_required"],
        "remote_handoff_dispatch_readiness": remote_handoff["dispatch_readiness"],
        "remote_handoff_operator_ack_required": remote_handoff["operator_ack_required"],
    }


def build_dispatch_report(state: TaskState) -> str:
    remote_handoff = build_remote_handoff_contract_record(state)
    return "\n".join(
        [
            "# Dispatch Report",
            "",
            f"- attempt_id: {state.current_attempt_id or 'pending'}",
            f"- attempt_number: {state.current_attempt_number}",
            f"- attempt_owner_kind: {state.current_attempt_owner_kind}",
            f"- attempt_owner_ref: {state.current_attempt_owner_ref}",
            f"- attempt_ownership_status: {state.current_attempt_ownership_status}",
            f"- attempt_owner_assigned_at: {state.current_attempt_owner_assigned_at or 'pending'}",
            f"- attempt_transfer_reason: {state.current_attempt_transfer_reason or 'none'}",
            f"- route_name: {state.route_name}",
            f"- execution_site_contract_kind: {state.execution_site_contract_kind}",
            f"- execution_site_boundary: {state.execution_site_boundary}",
            f"- executor_family: {state.topology_executor_family}",
            f"- execution_site: {state.topology_execution_site}",
            f"- transport_kind: {state.topology_transport_kind}",
            f"- dispatch_status: {state.topology_dispatch_status}",
            f"- dispatch_requested_at: {state.dispatch_requested_at or 'pending'}",
            f"- dispatch_started_at: {state.dispatch_started_at or 'pending'}",
            f"- execution_lifecycle: {state.execution_lifecycle}",
            "",
            "## Remote Handoff Contract",
            f"- contract_kind: {remote_handoff['contract_kind']}",
            f"- contract_status: {remote_handoff['contract_status']}",
            f"- handoff_boundary: {remote_handoff['handoff_boundary']}",
            f"- transport_truth: {remote_handoff['transport_truth']}",
            f"- ownership_required: {remote_handoff['ownership_required']}",
            f"- dispatch_readiness: {remote_handoff['dispatch_readiness']}",
            f"- operator_ack_required: {'yes' if remote_handoff['operator_ack_required'] else 'no'}",
        ]
    )


def build_remote_handoff_contract_record(state: TaskState) -> dict[str, object]:
    remote_candidate = (
        state.execution_site_contract_kind == "remote_candidate"
        or state.execution_site_boundary == "cross_site_candidate"
        or state.topology_execution_site != "local"
        or state.topology_transport_kind not in {"local_process", "local_detached_process"}
        or state.topology_remote_capable_intent
    )
    context_pointers = [
        path
        for path in [
            state.artifact_paths.get("task_semantics_json", ""),
            state.artifact_paths.get("execution_site_report", ""),
            state.artifact_paths.get("dispatch_report", ""),
            state.artifact_paths.get("remote_handoff_contract_report", ""),
        ]
        if path
    ]
    constraints = [str(item) for item in state.task_semantics.get("constraints", []) if str(item)]
    if not remote_candidate:
        schema = HandoffContractSchema(
            goal=state.goal,
            constraints=constraints,
            done=["Current route remains inside the local execution baseline."],
            next_steps=["Continue through the existing local execution path."],
            context_pointers=context_pointers,
        )
        return {
            "contract_kind": "not_applicable",
            "contract_status": "not_needed",
            "handoff_boundary": "local_baseline",
            "contract_reason": "Current route remains inside the local execution baseline and does not require remote handoff planning.",
            "remote_candidate": False,
            "remote_capable_intent": state.topology_remote_capable_intent,
            "execution_site": state.topology_execution_site,
            "execution_site_contract_kind": state.execution_site_contract_kind,
            "execution_site_contract_status": state.execution_site_contract_status,
            "transport_kind": state.topology_transport_kind,
            "transport_truth": "local_only",
            "ownership_required": "no",
            "ownership_truth": "local_orchestrator_owned",
            "dispatch_readiness": "not_applicable",
            "dispatch_truth": state.topology_dispatch_status or "not_requested",
            "operator_ack_required": False,
            "next_owner_kind": state.current_attempt_owner_kind,
            "next_owner_ref": state.current_attempt_owner_ref,
            "blocking_reason": "",
            "recommended_next_action": "Continue through the existing local execution path.",
            **schema.to_dict(),
        }

    if state.topology_transport_kind == "mock_remote_transport":
        schema = HandoffContractSchema(
            goal=state.goal,
            constraints=constraints,
            done=["Mock remote dispatch contract approved for topology validation."],
            next_steps=["Run the mock remote executor and persist the resulting artifacts."],
            context_pointers=context_pointers,
        )
        return {
            "contract_kind": "remote_handoff_candidate",
            "contract_status": "ready",
            "handoff_boundary": "cross_site_candidate",
            "contract_reason": (
                "Current route targets the mock remote executor used for topology validation without introducing real transport."
            ),
            "remote_candidate": True,
            "remote_capable_intent": state.topology_remote_capable_intent,
            "execution_site": state.topology_execution_site,
            "execution_site_contract_kind": state.execution_site_contract_kind,
            "execution_site_contract_status": "ready",
            "transport_kind": state.topology_transport_kind,
            "transport_truth": "mock_remote_transport",
            "ownership_required": "yes",
            "ownership_truth": "mock_remote_executor_assigned",
            "dispatch_readiness": "ready",
            "dispatch_truth": state.topology_dispatch_status or "planned",
            "operator_ack_required": False,
            "next_owner_kind": "remote_executor",
            "next_owner_ref": "mock-remote-node",
            "blocking_reason": "",
            "recommended_next_action": "Dispatch to the mock remote executor.",
            **schema.to_dict(),
        }

    schema = HandoffContractSchema(
        goal=state.goal,
        constraints=constraints,
        done=["Remote candidate contract detected; dispatch remains blocked until contract review is complete."],
        next_steps=["Review the remote handoff contract before treating this task as ready for remote dispatch."],
        context_pointers=context_pointers,
    )
    return {
        "contract_kind": "remote_handoff_candidate",
        "contract_status": "planned",
        "handoff_boundary": "cross_site_candidate",
        "contract_reason": (
            "Current route declares a remote-capable or cross-site execution boundary, so an explicit remote handoff contract"
            " is required before any non-local dispatch."
        ),
        "remote_candidate": True,
        "remote_capable_intent": state.topology_remote_capable_intent,
        "execution_site": state.topology_execution_site,
        "execution_site_contract_kind": state.execution_site_contract_kind,
        "execution_site_contract_status": state.execution_site_contract_status,
        "transport_kind": state.topology_transport_kind,
        "transport_truth": "explicit_remote_transport_required",
        "ownership_required": "yes",
        "ownership_truth": "transfer_required_before_remote_dispatch",
        "dispatch_readiness": "contract_required",
        "dispatch_truth": state.topology_dispatch_status or "not_requested",
        "operator_ack_required": True,
        "next_owner_kind": "remote_executor",
        "next_owner_ref": "unassigned",
        "blocking_reason": (
            "Remote candidate execution cannot proceed until transport, ownership, and dispatch contract details are made explicit."
        ),
        "recommended_next_action": (
            "Review the remote handoff contract before treating this task as ready for remote dispatch."
        ),
        **schema.to_dict(),
    }


def build_remote_handoff_contract_report(record: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Remote Handoff Contract Report",
            "",
            f"- contract_kind: {record.get('contract_kind', 'pending')}",
            f"- contract_status: {record.get('contract_status', 'pending')}",
            f"- handoff_boundary: {record.get('handoff_boundary', 'pending')}",
            f"- contract_reason: {record.get('contract_reason', 'pending')}",
            f"- remote_candidate: {'yes' if record.get('remote_candidate', False) else 'no'}",
            f"- remote_capable_intent: {'yes' if record.get('remote_capable_intent', False) else 'no'}",
            f"- execution_site: {record.get('execution_site', 'pending')}",
            f"- execution_site_contract_kind: {record.get('execution_site_contract_kind', 'pending')}",
            f"- execution_site_contract_status: {record.get('execution_site_contract_status', 'pending')}",
            f"- transport_kind: {record.get('transport_kind', 'pending')}",
            f"- transport_truth: {record.get('transport_truth', 'pending')}",
            f"- ownership_required: {record.get('ownership_required', 'pending')}",
            f"- ownership_truth: {record.get('ownership_truth', 'pending')}",
            f"- dispatch_readiness: {record.get('dispatch_readiness', 'pending')}",
            f"- dispatch_truth: {record.get('dispatch_truth', 'pending')}",
            f"- operator_ack_required: {'yes' if record.get('operator_ack_required', False) else 'no'}",
            f"- next_owner_kind: {record.get('next_owner_kind', 'pending')}",
            f"- next_owner_ref: {record.get('next_owner_ref', 'pending')}",
            f"- blocking_reason: {record.get('blocking_reason', '') or 'none'}",
            f"- recommended_next_action: {record.get('recommended_next_action', 'pending')}",
            "",
            "## Unified Handoff Schema",
            f"- goal: {record.get('goal', 'pending')}",
            f"- constraints: {', '.join(record.get('constraints', [])) or 'none'}",
            f"- done: {', '.join(record.get('done', [])) or 'none'}",
            f"- next_steps: {', '.join(record.get('next_steps', [])) or 'none'}",
            f"- context_pointers: {', '.join(record.get('context_pointers', [])) or 'none'}",
        ]
    )


def build_handoff_record(
    state: TaskState,
    executor_result: ExecutorResult,
    compatibility_result: CompatibilityResult,
    execution_fit_result: ExecutionFitResult,
    knowledge_policy_result: KnowledgePolicyResult,
    validation_result: ValidationResult,
    retry_policy_result: RetryPolicyResult,
    stop_policy_result: StopPolicyResult,
    execution_budget_policy_result: ExecutionBudgetPolicyResult,
) -> dict[str, object]:
    remote_handoff = build_remote_handoff_contract_record(state)
    required_inputs = [
        state.artifact_paths.get("summary", ""),
        state.artifact_paths.get("resume_note", ""),
        state.artifact_paths.get("executor_output", ""),
        state.artifact_paths.get("handoff_report", ""),
    ]
    required_inputs = [path for path in required_inputs if path]
    if (
        executor_result.status == "completed"
        and compatibility_result.status != "failed"
        and knowledge_policy_result.status != "failed"
        and validation_result.status != "failed"
    ):
        handoff_status = "review_completed_run"
        blocking_reason = ""
        next_operator_action = "Review summary.md and executor_output.md before starting the next task iteration."
        handoff_contract_status = "ready"
        handoff_contract_kind = "operator_review"
        handoff_contract_reason = "Completed run is ready for operator review and next-step selection."
        next_owner_kind = "operator"
        next_owner_ref = "swl_cli"
        expected_outputs = [
            "review decision recorded by the operator",
            "next task iteration selection",
        ]
    else:
        handoff_status = "resume_from_failure"
        blocking_reason = executor_result.failure_kind or executor_result.message
        failure_steps = build_failure_recommendations(executor_result.failure_kind)
        next_operator_action = failure_steps[0].lstrip("- ").strip() if failure_steps else "Resume from the latest failure context."
        handoff_contract_status = "ready"
        handoff_contract_kind = "failure_resume"
        handoff_contract_reason = "Failure handoff is ready for operator-guided recovery from the latest attempt context."
        next_owner_kind = "operator"
        next_owner_ref = "swl_cli"
        expected_outputs = [
            "failure recovery decision",
            "corrected rerun or route adjustment",
        ]

    return {
        "status": handoff_status,
        "contract_status": handoff_contract_status,
        "contract_kind": handoff_contract_kind,
        "contract_reason": handoff_contract_reason,
        "task_status": state.status,
        "attempt_id": state.current_attempt_id,
        "attempt_number": state.current_attempt_number,
        "attempt_owner_kind": state.current_attempt_owner_kind,
        "attempt_owner_ref": state.current_attempt_owner_ref,
        "attempt_ownership_status": state.current_attempt_ownership_status,
        "attempt_owner_assigned_at": state.current_attempt_owner_assigned_at,
        "attempt_transfer_reason": state.current_attempt_transfer_reason,
        "execution_site_contract_kind": state.execution_site_contract_kind,
        "execution_site_boundary": state.execution_site_boundary,
        "execution_site_contract_status": state.execution_site_contract_status,
        "execution_site_handoff_required": state.execution_site_handoff_required,
        "execution_site": state.topology_execution_site,
        "executor_family": state.topology_executor_family,
        "dispatch_status": state.topology_dispatch_status,
        "execution_lifecycle": state.execution_lifecycle,
        "remote_handoff_contract_kind": remote_handoff["contract_kind"],
        "remote_handoff_contract_status": remote_handoff["contract_status"],
        "remote_handoff_boundary": remote_handoff["handoff_boundary"],
        "remote_handoff_transport_truth": remote_handoff["transport_truth"],
        "remote_handoff_ownership_required": remote_handoff["ownership_required"],
        "remote_handoff_dispatch_readiness": remote_handoff["dispatch_readiness"],
        "remote_handoff_operator_ack_required": remote_handoff["operator_ack_required"],
        "required_inputs": required_inputs,
        "expected_outputs": expected_outputs,
        "next_owner_kind": next_owner_kind,
        "next_owner_ref": next_owner_ref,
        "blocking_reason": blocking_reason,
        "next_operator_action": next_operator_action,
        "executor_status": executor_result.status,
        "failure_kind": executor_result.failure_kind,
        "compatibility_status": compatibility_result.status,
        "execution_fit_status": execution_fit_result.status,
        "retry_policy_status": retry_policy_result.status,
        "retryable": retry_policy_result.retryable,
        "retry_decision": retry_policy_result.retry_decision,
        "remaining_attempts": retry_policy_result.remaining_attempts,
        "checkpoint_required": retry_policy_result.checkpoint_required,
        "retry_recommended_action": retry_policy_result.recommended_action,
        "execution_budget_policy_status": execution_budget_policy_result.status,
        "timeout_seconds": execution_budget_policy_result.timeout_seconds,
        "budget_state": execution_budget_policy_result.budget_state,
        "timeout_state": execution_budget_policy_result.timeout_state,
        "budget_recommended_action": execution_budget_policy_result.recommended_action,
        "stop_policy_status": stop_policy_result.status,
        "stop_required": stop_policy_result.stop_required,
        "continue_allowed": stop_policy_result.continue_allowed,
        "stop_decision": stop_policy_result.stop_decision,
        "escalation_level": stop_policy_result.escalation_level,
        "checkpoint_kind": stop_policy_result.checkpoint_kind,
        "stop_recommended_action": stop_policy_result.recommended_action,
        "knowledge_policy_status": knowledge_policy_result.status,
        "validation_status": validation_result.status,
    }


def build_handoff_report(handoff_record: dict[str, object]) -> str:
    lines = [
        "# Handoff Report",
        "",
        f"- status: {handoff_record.get('status', 'pending')}",
        f"- contract_status: {handoff_record.get('contract_status', 'pending')}",
        f"- contract_kind: {handoff_record.get('contract_kind', 'pending')}",
        f"- contract_reason: {handoff_record.get('contract_reason', 'pending')}",
        f"- task_status: {handoff_record.get('task_status', 'pending')}",
        f"- attempt_id: {handoff_record.get('attempt_id', 'pending')}",
        f"- attempt_number: {handoff_record.get('attempt_number', 0)}",
        f"- attempt_owner_kind: {handoff_record.get('attempt_owner_kind', 'pending')}",
        f"- attempt_owner_ref: {handoff_record.get('attempt_owner_ref', 'pending')}",
        f"- attempt_ownership_status: {handoff_record.get('attempt_ownership_status', 'pending')}",
        f"- attempt_owner_assigned_at: {handoff_record.get('attempt_owner_assigned_at', 'pending')}",
        f"- attempt_transfer_reason: {handoff_record.get('attempt_transfer_reason', '') or 'none'}",
        f"- execution_site_contract_kind: {handoff_record.get('execution_site_contract_kind', 'pending')}",
        f"- execution_site_boundary: {handoff_record.get('execution_site_boundary', 'pending')}",
        f"- execution_site_contract_status: {handoff_record.get('execution_site_contract_status', 'pending')}",
        f"- execution_site_handoff_required: {'yes' if handoff_record.get('execution_site_handoff_required', False) else 'no'}",
        f"- execution_site: {handoff_record.get('execution_site', 'pending')}",
        f"- executor_family: {handoff_record.get('executor_family', 'pending')}",
        f"- dispatch_status: {handoff_record.get('dispatch_status', 'pending')}",
        f"- execution_lifecycle: {handoff_record.get('execution_lifecycle', 'pending')}",
        f"- remote_handoff_contract_kind: {handoff_record.get('remote_handoff_contract_kind', 'pending')}",
        f"- remote_handoff_contract_status: {handoff_record.get('remote_handoff_contract_status', 'pending')}",
        f"- remote_handoff_boundary: {handoff_record.get('remote_handoff_boundary', 'pending')}",
        f"- remote_handoff_transport_truth: {handoff_record.get('remote_handoff_transport_truth', 'pending')}",
        f"- remote_handoff_ownership_required: {handoff_record.get('remote_handoff_ownership_required', 'pending')}",
        f"- remote_handoff_dispatch_readiness: {handoff_record.get('remote_handoff_dispatch_readiness', 'pending')}",
        f"- remote_handoff_operator_ack_required: {'yes' if handoff_record.get('remote_handoff_operator_ack_required', False) else 'no'}",
        f"- executor_status: {handoff_record.get('executor_status', 'pending')}",
        f"- failure_kind: {handoff_record.get('failure_kind', '') or 'none'}",
        f"- compatibility_status: {handoff_record.get('compatibility_status', 'pending')}",
        f"- execution_fit_status: {handoff_record.get('execution_fit_status', 'pending')}",
        f"- retry_policy_status: {handoff_record.get('retry_policy_status', 'pending')}",
        f"- retryable: {'yes' if handoff_record.get('retryable', False) else 'no'}",
        f"- retry_decision: {handoff_record.get('retry_decision', 'pending')}",
        f"- remaining_attempts: {handoff_record.get('remaining_attempts', 0)}",
        f"- checkpoint_required: {'yes' if handoff_record.get('checkpoint_required', False) else 'no'}",
        f"- retry_recommended_action: {handoff_record.get('retry_recommended_action', 'pending')}",
        f"- execution_budget_policy_status: {handoff_record.get('execution_budget_policy_status', 'pending')}",
        f"- timeout_seconds: {handoff_record.get('timeout_seconds', 0)}",
        f"- budget_state: {handoff_record.get('budget_state', 'pending')}",
        f"- timeout_state: {handoff_record.get('timeout_state', 'pending')}",
        f"- budget_recommended_action: {handoff_record.get('budget_recommended_action', 'pending')}",
        f"- stop_policy_status: {handoff_record.get('stop_policy_status', 'pending')}",
        f"- stop_required: {'yes' if handoff_record.get('stop_required', False) else 'no'}",
        f"- continue_allowed: {'yes' if handoff_record.get('continue_allowed', False) else 'no'}",
        f"- stop_decision: {handoff_record.get('stop_decision', 'pending')}",
        f"- escalation_level: {handoff_record.get('escalation_level', 'pending')}",
        f"- checkpoint_kind: {handoff_record.get('checkpoint_kind', 'pending')}",
        f"- stop_recommended_action: {handoff_record.get('stop_recommended_action', 'pending')}",
        f"- knowledge_policy_status: {handoff_record.get('knowledge_policy_status', 'pending')}",
        f"- validation_status: {handoff_record.get('validation_status', 'pending')}",
        f"- next_owner_kind: {handoff_record.get('next_owner_kind', 'pending')}",
        f"- next_owner_ref: {handoff_record.get('next_owner_ref', 'pending')}",
        f"- blocking_reason: {handoff_record.get('blocking_reason', '') or 'none'}",
        f"- next_operator_action: {handoff_record.get('next_operator_action', 'pending')}",
        "",
        "## Required Inputs",
    ]
    required_inputs = handoff_record.get("required_inputs", [])
    if isinstance(required_inputs, list) and required_inputs:
        lines.extend([f"- {item}" for item in required_inputs])
    else:
        lines.append("- none")
    lines.extend(["", "## Expected Outputs"])
    expected_outputs = handoff_record.get("expected_outputs", [])
    if isinstance(expected_outputs, list) and expected_outputs:
        lines.extend([f"- {item}" for item in expected_outputs])
    else:
        lines.append("- none")
    return "\n".join(lines)


def build_compatibility_record(
    state: TaskState,
    executor_result: ExecutorResult,
    compatibility_result: CompatibilityResult,
) -> dict[str, object]:
    return {
        "status": compatibility_result.status,
        "message": compatibility_result.message,
        "findings": [finding.to_dict() for finding in compatibility_result.findings],
        "route": build_route_record(state),
        "executor": {
            "name": executor_result.executor_name,
            "status": executor_result.status,
            "failure_kind": executor_result.failure_kind,
        },
    }


def build_summary(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    executor_result: ExecutorResult,
    compatibility_result: CompatibilityResult | None,
    execution_fit_result: ExecutionFitResult | None,
    knowledge_policy_result: KnowledgePolicyResult | None,
    validation_result: ValidationResult | None,
    retry_policy_result: RetryPolicyResult | None,
    stop_policy_result: StopPolicyResult | None,
    execution_budget_policy_result: ExecutionBudgetPolicyResult | None,
) -> str:
    reused_knowledge = summarize_reused_knowledge(retrieval_items)
    knowledge_index = build_knowledge_index(state.knowledge_objects)
    canonicalization_counts = summarize_canonicalization(state.knowledge_objects)
    lines = [
        f"# Summary for {state.task_id}",
        "",
        "## Task",
        state.title,
        "",
        "## Goal",
        state.goal,
        "",
        "## Status",
        f"- phase: {state.phase}",
        f"- status: {state.status}",
        f"- workspace: {state.workspace_root}",
        f"- task_semantics_source_kind: {state.task_semantics.get('source_kind', 'none') if state.task_semantics else 'none'}",
        f"- task_semantics_source_ref: {state.task_semantics.get('source_ref', '') or 'none' if state.task_semantics else 'none'}",
        f"- task_semantics_report_artifact: {state.artifact_paths.get('task_semantics_report', '') or 'pending'}",
        f"- knowledge_objects_count: {len(state.knowledge_objects)}",
        f"- knowledge_evidence_artifact_backed: {summarize_knowledge_evidence(state.knowledge_objects).get('artifact_backed', 0)}",
        f"- knowledge_retrieval_candidate_count: {summarize_knowledge_reuse(state.knowledge_objects).get('retrieval_candidate', 0)}",
        f"- knowledge_canonicalization_ready_count: {canonicalization_counts.get('review_ready', 0) + canonicalization_counts.get('promotion_ready', 0)}",
        f"- knowledge_canonicalization_blocked_count: {canonicalization_counts.get('blocked_stage', 0) + canonicalization_counts.get('blocked_evidence', 0)}",
        f"- knowledge_objects_report_artifact: {state.artifact_paths.get('knowledge_objects_report', '') or 'pending'}",
        f"- knowledge_partition_report_artifact: {state.artifact_paths.get('knowledge_partition_report', '') or 'pending'}",
        f"- knowledge_index_report_artifact: {state.artifact_paths.get('knowledge_index_report', '') or 'pending'}",
        f"- knowledge_index_active_reusable_count: {knowledge_index['active_reusable_count']}",
        f"- knowledge_index_inactive_reusable_count: {knowledge_index['inactive_reusable_count']}",
        f"- knowledge_index_refreshed_at: {knowledge_index['refreshed_at']}",
        f"- retrieval_reused_knowledge_count: {reused_knowledge['count']}",
        f"- retrieval_reused_task_knowledge_count: {reused_knowledge.get('task_knowledge_count', 0)}",
        f"- retrieval_reused_canonical_registry_count: {reused_knowledge.get('canonical_registry_count', 0)}",
        f"- retrieval_reused_knowledge_current_task_count: {reused_knowledge['current_task_count']}",
        f"- retrieval_reused_knowledge_cross_task_count: {reused_knowledge['cross_task_count']}",
        f"- executor: {state.executor_name}",
        f"- executor_status: {state.executor_status}",
        f"- execution_lifecycle: {state.execution_lifecycle}",
        f"- attempt_id: {state.current_attempt_id or 'pending'}",
        f"- attempt_number: {state.current_attempt_number}",
        f"- attempt_owner_kind: {state.current_attempt_owner_kind}",
        f"- attempt_owner_ref: {state.current_attempt_owner_ref}",
        f"- attempt_ownership_status: {state.current_attempt_ownership_status}",
        f"- attempt_owner_assigned_at: {state.current_attempt_owner_assigned_at or 'pending'}",
        f"- attempt_transfer_reason: {state.current_attempt_transfer_reason or 'none'}",
        f"- route_mode: {state.route_mode}",
        f"- route_name: {state.route_name}",
        f"- route_backend: {state.route_backend}",
        f"- route_executor_family: {state.route_executor_family}",
        f"- route_execution_site: {state.route_execution_site}",
        f"- route_remote_capable: {state.route_remote_capable}",
        f"- route_transport_kind: {state.route_transport_kind}",
        f"- route_model_hint: {state.route_model_hint}",
        f"- route_dialect: {state.route_dialect}",
        f"- route_reason: {state.route_reason}",
        f"- route_capabilities: {format_route_capabilities(state.route_capabilities)}",
        f"- route_report_artifact: {state.artifact_paths.get('route_report', '') or 'pending'}",
        f"- topology_execution_site: {state.topology_execution_site}",
        f"- topology_executor_family: {state.topology_executor_family}",
        f"- topology_transport_kind: {state.topology_transport_kind}",
        f"- topology_dispatch_status: {state.topology_dispatch_status}",
        f"- topology_report_artifact: {state.artifact_paths.get('topology_report', '') or 'pending'}",
        f"- execution_site_contract_kind: {state.execution_site_contract_kind}",
        f"- execution_site_boundary: {state.execution_site_boundary}",
        f"- execution_site_contract_status: {state.execution_site_contract_status}",
        f"- execution_site_handoff_required: {state.execution_site_handoff_required}",
        f"- execution_site_report_artifact: {state.artifact_paths.get('execution_site_report', '') or 'pending'}",
        f"- dispatch_requested_at: {state.dispatch_requested_at or 'pending'}",
        f"- dispatch_started_at: {state.dispatch_started_at or 'pending'}",
        f"- dispatch_report_artifact: {state.artifact_paths.get('dispatch_report', '') or 'pending'}",
        f"- handoff_report_artifact: {state.artifact_paths.get('handoff_report', '') or 'pending'}",
        f"- compatibility_status: {compatibility_result.status if compatibility_result else 'pending'}",
        f"- execution_fit_status: {execution_fit_result.status if execution_fit_result else 'pending'}",
        f"- retry_policy_status: {retry_policy_result.status if retry_policy_result else 'pending'}",
        f"- execution_budget_policy_status: {execution_budget_policy_result.status if execution_budget_policy_result else 'pending'}",
        f"- stop_policy_status: {stop_policy_result.status if stop_policy_result else 'pending'}",
        f"- checkpoint_snapshot_report_artifact: {state.artifact_paths.get('checkpoint_snapshot_report', '') or 'pending'}",
        f"- knowledge_policy_status: {knowledge_policy_result.status if knowledge_policy_result else 'pending'}",
        f"- execution_fit_report_artifact: {state.artifact_paths.get('execution_fit_report', '') or 'pending'}",
        f"- retry_policy_report_artifact: {state.artifact_paths.get('retry_policy_report', '') or 'pending'}",
        f"- execution_budget_policy_report_artifact: {state.artifact_paths.get('execution_budget_policy_report', '') or 'pending'}",
        f"- stop_policy_report_artifact: {state.artifact_paths.get('stop_policy_report', '') or 'pending'}",
        f"- compatibility_report_artifact: {state.artifact_paths.get('compatibility_report', '') or 'pending'}",
        f"- knowledge_policy_report_artifact: {state.artifact_paths.get('knowledge_policy_report', '') or 'pending'}",
        f"- source_grounding_artifact: {state.artifact_paths.get('source_grounding', '') or 'pending'}",
        f"- retrieval_report_artifact: {state.artifact_paths.get('retrieval_report', '') or 'pending'}",
        f"- retrieval_record_path: {state.artifact_paths.get('retrieval_json', '') or 'pending'}",
        f"- task_memory_path: {state.artifact_paths.get('task_memory', '') or 'pending'}",
        "",
        "## Task Semantics",
    ]
    if state.task_semantics:
        for label, key in [
            ("constraints", "constraints"),
            ("acceptance_criteria", "acceptance_criteria"),
            ("priority_hints", "priority_hints"),
            ("next_action_proposals", "next_action_proposals"),
        ]:
            values = state.task_semantics.get(key, [])
            lines.append(f"- {label}: {'; '.join(values) if values else 'none'}")
    else:
        lines.append("- none")

    lines.extend([
        "",
        "## Knowledge Objects",
    ])
    if state.knowledge_objects:
        stage_counts = summarize_knowledge_stages(state.knowledge_objects)
        evidence_counts = summarize_knowledge_evidence(state.knowledge_objects)
        reuse_counts = summarize_knowledge_reuse(state.knowledge_objects)
        lines.extend(
            [
                f"- raw: {stage_counts.get('raw', 0)}",
                f"- candidate: {stage_counts.get('candidate', 0)}",
                f"- verified: {stage_counts.get('verified', 0)}",
                f"- canonical: {stage_counts.get('canonical', 0)}",
                f"- artifact_backed: {evidence_counts.get('artifact_backed', 0)}",
                f"- source_only: {evidence_counts.get('source_only', 0)}",
                f"- unbacked: {evidence_counts.get('unbacked', 0)}",
                f"- retrieval_candidate: {reuse_counts.get('retrieval_candidate', 0)}",
                f"- task_only: {reuse_counts.get('task_only', 0)}",
                f"- canonicalization_review_ready: {canonicalization_counts.get('review_ready', 0)}",
                f"- canonicalization_promotion_ready: {canonicalization_counts.get('promotion_ready', 0)}",
                f"- canonicalization_blocked_stage: {canonicalization_counts.get('blocked_stage', 0)}",
                f"- canonicalization_blocked_evidence: {canonicalization_counts.get('blocked_evidence', 0)}",
            ]
        )
        for item in state.knowledge_objects[:5]:
            lines.append(
                f"- [{item.get('stage', 'raw')}/{item.get('evidence_status', 'unbacked')}/{item.get('knowledge_reuse_scope', 'task_only')}/{item.get('canonicalization_intent', 'none')}] {item.get('text', '') or '(empty)'}"
            )
    else:
        lines.append("- none")

    lines.extend([
        "",
        "## Retrieved Context",
    ])
    if retrieval_items:
        if reused_knowledge["count"] > 0:
            lines.extend(
                [
                    f"- reused_verified_knowledge: {reused_knowledge['count']}",
                    f"- reused_current_task_knowledge: {reused_knowledge['current_task_count']}",
                    f"- reused_cross_task_knowledge: {reused_knowledge['cross_task_count']}",
                    f"- reused_knowledge_references: {', '.join(reused_knowledge['references'])}",
                ]
            )
        for item in retrieval_items:
            score_context = ", ".join(f"{key}={value}" for key, value in item.score_breakdown.items()) or "none"
            matched_terms = ", ".join(item.matched_terms) or "none"
            lines.extend(
                [
                    f"- [{item.source_type}] {item.reference()} (score={item.score}, title={item.display_title()})",
                    f"  matched_terms: {matched_terms}",
                    f"  score_breakdown: {score_context}",
                    f"  preview: {item.preview or '(empty)'}",
                ]
            )
    else:
        lines.append("- No matching local context was found.")

    lines.extend(["", "## Executor Result", f"- message: {executor_result.message}"])
    if executor_result.failure_kind:
        lines.append(f"- failure_kind: {executor_result.failure_kind}")
    if compatibility_result is not None:
        lines.extend(
            [
                "",
                "## Compatibility",
                f"- status: {compatibility_result.status}",
                f"- message: {compatibility_result.message}",
            ]
        )
        for finding in compatibility_result.findings:
            lines.append(f"- [{finding.level}] {finding.code}: {finding.message}")
    if execution_fit_result is not None:
        lines.extend(
            [
                "",
                "## Execution Fit",
                f"- status: {execution_fit_result.status}",
                f"- message: {execution_fit_result.message}",
            ]
        )
        for finding in execution_fit_result.findings:
            lines.append(f"- [{finding.level}] {finding.code}: {finding.message}")
    if retry_policy_result is not None:
        lines.extend(
            [
                "",
                "## Retry Policy",
                f"- status: {retry_policy_result.status}",
                f"- message: {retry_policy_result.message}",
                f"- retryable: {'yes' if retry_policy_result.retryable else 'no'}",
                f"- retry_decision: {retry_policy_result.retry_decision}",
                f"- remaining_attempts: {retry_policy_result.remaining_attempts}",
                f"- checkpoint_required: {'yes' if retry_policy_result.checkpoint_required else 'no'}",
                f"- recommended_action: {retry_policy_result.recommended_action}",
            ]
        )
        for finding in retry_policy_result.findings:
            lines.append(f"- [{finding.level}] {finding.code}: {finding.message}")
    if stop_policy_result is not None:
        lines.extend(
            [
                "",
                "## Stop Policy",
                f"- status: {stop_policy_result.status}",
                f"- message: {stop_policy_result.message}",
                f"- stop_required: {'yes' if stop_policy_result.stop_required else 'no'}",
                f"- continue_allowed: {'yes' if stop_policy_result.continue_allowed else 'no'}",
                f"- stop_decision: {stop_policy_result.stop_decision}",
                f"- escalation_level: {stop_policy_result.escalation_level}",
                f"- checkpoint_kind: {stop_policy_result.checkpoint_kind}",
                f"- recommended_action: {stop_policy_result.recommended_action}",
            ]
        )
        for finding in stop_policy_result.findings:
            lines.append(f"- [{finding.level}] {finding.code}: {finding.message}")
    if execution_budget_policy_result is not None:
        lines.extend(
            [
                "",
                "## Execution Budget Policy",
                f"- status: {execution_budget_policy_result.status}",
                f"- message: {execution_budget_policy_result.message}",
                f"- timeout_seconds: {execution_budget_policy_result.timeout_seconds}",
                f"- timeout_state: {execution_budget_policy_result.timeout_state}",
                f"- max_attempts: {execution_budget_policy_result.max_attempts}",
                f"- remaining_attempts: {execution_budget_policy_result.remaining_attempts}",
                f"- budget_state: {execution_budget_policy_result.budget_state}",
                f"- recommended_action: {execution_budget_policy_result.recommended_action}",
            ]
        )
        for finding in execution_budget_policy_result.findings:
            lines.append(f"- [{finding.level}] {finding.code}: {finding.message}")
    if knowledge_policy_result is not None:
        lines.extend(
            [
                "",
                "## Knowledge Policy",
                f"- status: {knowledge_policy_result.status}",
                f"- message: {knowledge_policy_result.message}",
            ]
        )
        for finding in knowledge_policy_result.findings:
            lines.append(f"- [{finding.level}] {finding.code}: {finding.message}")
    if validation_result is not None:
        lines.extend(
            [
                "",
                "## Validation",
                f"- status: {validation_result.status}",
                f"- message: {validation_result.message}",
            ]
        )
        for finding in validation_result.findings:
            lines.append(f"- [{finding.level}] {finding.code}: {finding.message}")
    lines.extend(["", "## Executor Output", executor_result.output or "(no executor output)"])
    return "\n".join(lines)


def build_resume_note(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    executor_result: ExecutorResult,
    compatibility_result: CompatibilityResult | None,
    execution_fit_result: ExecutionFitResult | None,
    knowledge_policy_result: KnowledgePolicyResult | None,
    validation_result: ValidationResult | None,
    retry_policy_result: RetryPolicyResult | None,
    stop_policy_result: StopPolicyResult | None,
    execution_budget_policy_result: ExecutionBudgetPolicyResult | None,
) -> str:
    top_references = ", ".join(item.reference() for item in retrieval_items[:3]) or "none"
    reused_knowledge = summarize_reused_knowledge(retrieval_items)
    knowledge_index = build_knowledge_index(state.knowledge_objects)
    canonicalization_counts = summarize_canonicalization(state.knowledge_objects)
    lines = [
        f"# Resume Note for {state.task_id}",
        "",
        "## Ready State",
        f"- task: {state.title}",
        f"- goal: {state.goal}",
        f"- status: {state.status}",
        f"- current phase: {state.phase}",
        f"- task semantics source kind: {state.task_semantics.get('source_kind', 'none') if state.task_semantics else 'none'}",
        f"- task semantics source ref: {state.task_semantics.get('source_ref', '') or 'none' if state.task_semantics else 'none'}",
        f"- task semantics report artifact: {state.artifact_paths.get('task_semantics_report', '') or 'pending'}",
        f"- knowledge objects count: {len(state.knowledge_objects)}",
        f"- artifact-backed knowledge objects: {summarize_knowledge_evidence(state.knowledge_objects).get('artifact_backed', 0)}",
        f"- retrieval-eligible knowledge objects: {summarize_knowledge_reuse(state.knowledge_objects).get('retrieval_candidate', 0)}",
        f"- canonicalization-ready knowledge objects: {canonicalization_counts.get('review_ready', 0) + canonicalization_counts.get('promotion_ready', 0)}",
        f"- canonicalization-blocked knowledge objects: {canonicalization_counts.get('blocked_stage', 0) + canonicalization_counts.get('blocked_evidence', 0)}",
        f"- reused verified knowledge records: {reused_knowledge['count']}",
        f"- reused task-knowledge records: {reused_knowledge.get('task_knowledge_count', 0)}",
        f"- reused canonical-registry records: {reused_knowledge.get('canonical_registry_count', 0)}",
        f"- reused current-task knowledge records: {reused_knowledge['current_task_count']}",
        f"- reused cross-task knowledge records: {reused_knowledge['cross_task_count']}",
        f"- knowledge objects report artifact: {state.artifact_paths.get('knowledge_objects_report', '') or 'pending'}",
        f"- knowledge partition report artifact: {state.artifact_paths.get('knowledge_partition_report', '') or 'pending'}",
        f"- knowledge index report artifact: {state.artifact_paths.get('knowledge_index_report', '') or 'pending'}",
        f"- knowledge index active reusable count: {knowledge_index['active_reusable_count']}",
        f"- knowledge index inactive reusable count: {knowledge_index['inactive_reusable_count']}",
        f"- knowledge index refreshed at: {knowledge_index['refreshed_at']}",
        f"- top retrieved references: {top_references}",
        f"- reused knowledge references: {', '.join(reused_knowledge['references']) or 'none'}",
        f"- executor: {executor_result.executor_name}",
        f"- executor status: {executor_result.status}",
        f"- execution lifecycle: {state.execution_lifecycle}",
        f"- attempt id: {state.current_attempt_id or 'pending'}",
        f"- attempt number: {state.current_attempt_number}",
        f"- attempt owner kind: {state.current_attempt_owner_kind}",
        f"- attempt owner ref: {state.current_attempt_owner_ref}",
        f"- attempt ownership status: {state.current_attempt_ownership_status}",
        f"- attempt owner assigned at: {state.current_attempt_owner_assigned_at or 'pending'}",
        f"- attempt transfer reason: {state.current_attempt_transfer_reason or 'none'}",
        f"- route mode: {state.route_mode}",
        f"- route name: {state.route_name}",
        f"- route backend: {state.route_backend}",
        f"- route executor family: {state.route_executor_family}",
        f"- route execution site: {state.route_execution_site}",
        f"- route remote capable: {'yes' if state.route_remote_capable else 'no'}",
        f"- route transport kind: {state.route_transport_kind}",
        f"- route reason: {state.route_reason}",
        f"- route report artifact: {state.artifact_paths.get('route_report', '') or 'pending'}",
        f"- topology execution site: {state.topology_execution_site}",
        f"- topology executor family: {state.topology_executor_family}",
        f"- topology transport kind: {state.topology_transport_kind}",
        f"- topology dispatch status: {state.topology_dispatch_status}",
        f"- topology report artifact: {state.artifact_paths.get('topology_report', '') or 'pending'}",
        f"- execution-site contract kind: {state.execution_site_contract_kind}",
        f"- execution-site boundary: {state.execution_site_boundary}",
        f"- execution-site contract status: {state.execution_site_contract_status}",
        f"- execution-site handoff required: {'yes' if state.execution_site_handoff_required else 'no'}",
        f"- execution-site report artifact: {state.artifact_paths.get('execution_site_report', '') or 'pending'}",
        f"- dispatch requested at: {state.dispatch_requested_at or 'pending'}",
        f"- dispatch started at: {state.dispatch_started_at or 'pending'}",
        f"- dispatch report artifact: {state.artifact_paths.get('dispatch_report', '') or 'pending'}",
        f"- handoff report artifact: {state.artifact_paths.get('handoff_report', '') or 'pending'}",
        f"- failure kind: {executor_result.failure_kind or 'none'}",
        f"- compatibility status: {compatibility_result.status if compatibility_result else 'pending'}",
        f"- execution fit status: {execution_fit_result.status if execution_fit_result else 'pending'}",
        f"- retry policy status: {retry_policy_result.status if retry_policy_result else 'pending'}",
        f"- execution budget policy status: {execution_budget_policy_result.status if execution_budget_policy_result else 'pending'}",
        f"- stop policy status: {stop_policy_result.status if stop_policy_result else 'pending'}",
        f"- checkpoint snapshot report artifact: {state.artifact_paths.get('checkpoint_snapshot_report', '') or 'pending'}",
        f"- knowledge policy status: {knowledge_policy_result.status if knowledge_policy_result else 'pending'}",
        f"- execution fit report artifact: {state.artifact_paths.get('execution_fit_report', '') or 'pending'}",
        f"- retry policy report artifact: {state.artifact_paths.get('retry_policy_report', '') or 'pending'}",
        f"- execution budget policy report artifact: {state.artifact_paths.get('execution_budget_policy_report', '') or 'pending'}",
        f"- stop policy report artifact: {state.artifact_paths.get('stop_policy_report', '') or 'pending'}",
        f"- compatibility report artifact: {state.artifact_paths.get('compatibility_report', '') or 'pending'}",
        f"- knowledge policy report artifact: {state.artifact_paths.get('knowledge_policy_report', '') or 'pending'}",
        f"- validation status: {validation_result.status if validation_result else 'pending'}",
        "",
        "## Hand-off",
        f"- latest executor message: {executor_result.message}",
        f"- source grounding artifact: {state.artifact_paths.get('source_grounding', '') or 'pending'}",
        f"- retrieval report artifact: {state.artifact_paths.get('retrieval_report', '') or 'pending'}",
        f"- retrieval record path: {state.artifact_paths.get('retrieval_json', '') or 'pending'}",
        f"- task memory path: {state.artifact_paths.get('task_memory', '') or 'pending'}",
        f"- task semantics json path: {state.artifact_paths.get('task_semantics_json', '') or 'pending'}",
        f"- knowledge objects json path: {state.artifact_paths.get('knowledge_objects_json', '') or 'pending'}",
        f"- knowledge partition json path: {state.artifact_paths.get('knowledge_partition_json', '') or 'pending'}",
        f"- knowledge index json path: {state.artifact_paths.get('knowledge_index_json', '') or 'pending'}",
    ]
    if executor_result.status == "completed":
        lines.append("- treat summary.md and executor_output.md as the record of what happened in this run")
    else:
        lines.append("- treat this run as incomplete and resume from the failure context below")

    if executor_result.status == "completed":
        next_steps = [
            "- Review summary.md to confirm the run outcome before starting the next task iteration.",
            "- Use executor_output.md as the compact record of the latest execution result.",
            "- Decide the next implementation action from the completed run instead of replaying the same step immediately.",
        ]
    else:
        next_steps = build_failure_recommendations(executor_result.failure_kind)

    if compatibility_result is not None and compatibility_result.status == "warning":
        next_steps.insert(
            0,
            "- Review compatibility_report.md before trusting this route choice because the compatibility layer recorded warnings.",
        )
    if compatibility_result is not None and compatibility_result.status == "failed":
        next_steps.insert(
            0,
            "- Treat the compatibility report as blocking and switch to a route that matches the requested policy before continuing.",
        )
    if knowledge_policy_result is not None and knowledge_policy_result.status == "warning":
        next_steps.insert(
            0,
            "- Review knowledge_policy_report.md before promoting imported knowledge because the policy recorded warnings.",
        )
    if knowledge_policy_result is not None and knowledge_policy_result.status == "failed":
        next_steps.insert(
            0,
            "- Treat the knowledge policy report as blocking and fix promotion or evidence mismatches before reusing imported knowledge.",
        )
    if validation_result is not None and validation_result.status == "warning":
        next_steps.insert(0, "- Review validation_report.md before trusting this run because the validator recorded warnings.")
    if validation_result is not None and validation_result.status == "failed":
        next_steps.insert(0, "- Treat the validation report as blocking and fix the recorded failures before continuing from this run.")
    if retry_policy_result is not None and retry_policy_result.status == "warning":
        next_steps.insert(
            0,
            "- Review retry_policy_report.md and treat the next attempt as an operator-gated retry rather than an automatic rerun.",
        )
    if retry_policy_result is not None and retry_policy_result.status == "failed":
        next_steps.insert(
            0,
            "- Treat the retry policy as blocking and change the route, environment, or task inputs before trying again.",
        )
    if stop_policy_result is not None and stop_policy_result.status == "warning":
        next_steps.insert(
            0,
            "- Treat the stop policy as a checkpoint boundary and do not continue until the operator reviews the current run state.",
        )
    if stop_policy_result is not None and stop_policy_result.status == "failed":
        next_steps.insert(
            0,
            "- Treat the stop policy as blocking and stop the run sequence until the operator changes the failing conditions.",
        )
    if execution_budget_policy_result is not None and execution_budget_policy_result.status == "warning":
        next_steps.insert(
            0,
            "- Review execution_budget_policy_report.md before continuing so timeout or attempt-budget assumptions stay explicit.",
        )

    lines.extend(
        [
            "",
            "## Next Suggested Step",
            *next_steps,
            "- Review summary.md before restarting work so the prior run is not reinterpreted from scratch.",
            "- Use retrieval_report.md to review the latest retrieval set before opening raw retrieval.json.",
            "- Use compatibility_report.md when checking whether the selected route actually matched the requested policy.",
            "- Use retry_policy_report.md when deciding whether another attempt is actually justified.",
            "- Use execution_budget_policy_report.md when deciding whether timeout or attempt budget changes are warranted.",
            "- Use stop_policy_report.md when deciding whether the system should stop here or escalate before continuing.",
            "- Use knowledge_policy_report.md when deciding whether imported knowledge is safe to promote or reuse.",
            "- Use validation_report.md when deciding whether to reuse the current run outputs.",
            "- Expand retrieval scoring when the source set grows.",
        ]
    )
    return "\n".join(lines)
