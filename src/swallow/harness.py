from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .compatibility import build_compatibility_report, evaluate_route_compatibility
from .execution_fit import build_execution_fit_report, evaluate_execution_fit
from .executor import build_failure_recommendations, run_executor
from .models import (
    CompatibilityResult,
    ExecutionFitResult,
    Event,
    ExecutorResult,
    RetrievalItem,
    RetrievalRequest,
    TaskState,
    ValidationResult,
)
from .retrieval import retrieve_context
from .store import (
    append_event,
    save_compatibility,
    save_dispatch,
    save_execution_fit,
    save_handoff,
    save_memory,
    save_retrieval,
    save_route,
    save_topology,
    save_validation,
    write_artifact,
)
from .validator import build_validation_report, validate_run_outputs


def run_retrieval(base_dir: Path, state: TaskState, request: RetrievalRequest) -> list[RetrievalItem]:
    retrieval_items = retrieve_context(Path(state.workspace_root), request=request)
    save_retrieval(base_dir, state.task_id, retrieval_items)
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="retrieval.completed",
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
            },
        ),
    )
    return retrieval_items


def run_execution(base_dir: Path, state: TaskState, retrieval_items: list[RetrievalItem]) -> ExecutorResult:
    executor_result = run_executor(state, retrieval_items)
    write_artifact(base_dir, state.task_id, "executor_prompt.md", executor_result.prompt)
    write_artifact(base_dir, state.task_id, "executor_output.md", executor_result.output or executor_result.message)
    write_artifact(base_dir, state.task_id, "executor_stdout.txt", executor_result.stdout)
    write_artifact(base_dir, state.task_id, "executor_stderr.txt", executor_result.stderr)
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type=f"executor.{executor_result.status}",
            message=executor_result.message,
            payload={
                "status": executor_result.status,
                "executor_name": executor_result.executor_name,
                "route_mode": state.route_mode,
                "route_name": state.route_name,
                "route_backend": state.route_backend,
                "route_execution_site": state.route_execution_site,
                "route_remote_capable": state.route_remote_capable,
                "route_transport_kind": state.route_transport_kind,
                "route_capabilities": state.route_capabilities,
                "attempt_id": state.current_attempt_id,
                "attempt_number": state.current_attempt_number,
                "topology_route_name": state.topology_route_name,
                "topology_execution_site": state.topology_execution_site,
                "topology_transport_kind": state.topology_transport_kind,
                "topology_remote_capable_intent": state.topology_remote_capable_intent,
                "topology_dispatch_status": state.topology_dispatch_status,
                "dispatch_requested_at": state.dispatch_requested_at,
                "dispatch_started_at": state.dispatch_started_at,
                "execution_lifecycle": state.execution_lifecycle,
                "failure_kind": executor_result.failure_kind,
                "output_written": [
                    "executor_prompt.md",
                    "executor_output.md",
                    "executor_stdout.txt",
                    "executor_stderr.txt",
                ],
            },
        ),
    )
    return executor_result


def write_task_artifacts(
    base_dir: Path,
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    executor_result: ExecutorResult,
) -> tuple[CompatibilityResult, ExecutionFitResult, ValidationResult]:
    save_route(base_dir, state.task_id, build_route_record(state))
    save_topology(base_dir, state.task_id, build_topology_record(state))
    save_dispatch(base_dir, state.task_id, build_dispatch_record(state))
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
        "dispatch_report.md",
        build_dispatch_report(state),
    )
    write_artifact(
        base_dir,
        state.task_id,
        "source_grounding.md",
        build_source_grounding(retrieval_items),
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
        build_summary(provisional_state, retrieval_items, executor_result, None, None, None),
    )
    write_artifact(
        base_dir,
        state.task_id,
        "resume_note.md",
        build_resume_note(provisional_state, retrieval_items, executor_result, None, None, None),
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

    final_status = (
        "completed"
        if executor_result.status == "completed"
        and compatibility_result.status != "failed"
        and execution_fit_result.status != "failed"
        and validation_result.status != "failed"
        else "failed"
    )
    render_state = replace(
        state,
        status=final_status,
        execution_lifecycle="completed" if final_status == "completed" else "failed",
    )
    handoff_record = build_handoff_record(
        render_state,
        executor_result,
        compatibility_result,
        execution_fit_result,
        validation_result,
    )
    save_handoff(base_dir, state.task_id, handoff_record)
    write_artifact(
        base_dir,
        state.task_id,
        "handoff_report.md",
        build_handoff_report(handoff_record),
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
            validation_result,
            handoff_record,
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
            validation_result,
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
            validation_result,
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
                    "summary": state.artifact_paths.get("summary", ""),
                    "resume_note": state.artifact_paths.get("resume_note", ""),
                    "route_report": state.artifact_paths.get("route_report", ""),
                    "topology_report": state.artifact_paths.get("topology_report", ""),
                    "dispatch_report": state.artifact_paths.get("dispatch_report", ""),
                    "handoff_report": state.artifact_paths.get("handoff_report", ""),
                    "execution_fit_report": state.artifact_paths.get("execution_fit_report", ""),
                    "compatibility_report": state.artifact_paths.get("compatibility_report", ""),
                    "source_grounding": state.artifact_paths.get("source_grounding", ""),
                    "retrieval_report": state.artifact_paths.get("retrieval_report", ""),
                    "validation_report": state.artifact_paths.get("validation_report", ""),
                    "task_memory": state.artifact_paths.get("task_memory", ""),
                },
            },
        ),
    )
    return compatibility_result, execution_fit_result, validation_result


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
                f"  score: {item.score}",
                f"  matched_terms: {matched_terms}",
                f"  score_breakdown: {score_context}",
                f"  preview: {item.preview or '(empty)'}",
            ]
        )
    return "\n".join(lines)


def build_retrieval_report(state: TaskState, retrieval_items: list[RetrievalItem]) -> str:
    lines = [
        "# Retrieval Report",
        "",
        f"- retrieval_count: {len(retrieval_items)}",
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
            ]
        )
    return "\n".join(lines)


def build_task_memory(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    executor_result: ExecutorResult,
    compatibility_result: CompatibilityResult,
    execution_fit_result: ExecutionFitResult,
    validation_result: ValidationResult,
    handoff_record: dict[str, object],
) -> dict[str, object]:
    return {
        "task_id": state.task_id,
        "task_title": state.title,
        "goal": state.goal,
        "phase": state.phase,
        "status": state.status,
        "workspace_root": state.workspace_root,
        "executor": {
            "name": executor_result.executor_name,
            "status": executor_result.status,
            "message": executor_result.message,
            "failure_kind": executor_result.failure_kind,
        },
        "execution_attempt": {
            "attempt_id": state.current_attempt_id,
            "attempt_number": state.current_attempt_number,
            "dispatch_requested_at": state.dispatch_requested_at,
            "dispatch_started_at": state.dispatch_started_at,
            "execution_lifecycle": state.execution_lifecycle,
        },
        "route": {
            "mode": state.route_mode,
            "name": state.route_name,
            "backend": state.route_backend,
            "execution_site": state.route_execution_site,
            "remote_capable": state.route_remote_capable,
            "transport_kind": state.route_transport_kind,
            "model_hint": state.route_model_hint,
            "reason": state.route_reason,
            "capabilities": state.route_capabilities,
        },
        "topology": build_topology_record(state),
        "dispatch": build_dispatch_record(state),
        "handoff": handoff_record,
        "compatibility": compatibility_result.to_dict(),
        "execution_fit": execution_fit_result.to_dict(),
        "validation": validation_result.to_dict(),
        "retrieval": {
            "count": len(retrieval_items),
            "top_references": [item.reference() for item in retrieval_items[:5]],
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
                }
                for item in retrieval_items[:5]
            ],
        },
        "artifact_paths": {
            "summary": state.artifact_paths.get("summary", ""),
            "resume_note": state.artifact_paths.get("resume_note", ""),
            "route_report": state.artifact_paths.get("route_report", ""),
            "route_json": state.artifact_paths.get("route_json", ""),
            "topology_report": state.artifact_paths.get("topology_report", ""),
            "topology_json": state.artifact_paths.get("topology_json", ""),
            "dispatch_report": state.artifact_paths.get("dispatch_report", ""),
            "dispatch_json": state.artifact_paths.get("dispatch_json", ""),
            "handoff_report": state.artifact_paths.get("handoff_report", ""),
            "handoff_json": state.artifact_paths.get("handoff_json", ""),
            "execution_fit_report": state.artifact_paths.get("execution_fit_report", ""),
            "execution_fit_json": state.artifact_paths.get("execution_fit_json", ""),
            "compatibility_report": state.artifact_paths.get("compatibility_report", ""),
            "compatibility_json": state.artifact_paths.get("compatibility_json", ""),
            "source_grounding": state.artifact_paths.get("source_grounding", ""),
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
        "execution_site": state.route_execution_site,
        "remote_capable": state.route_remote_capable,
        "transport_kind": state.route_transport_kind,
        "model_hint": state.route_model_hint,
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
            f"- execution_site: {state.route_execution_site}",
            f"- remote_capable: {'yes' if state.route_remote_capable else 'no'}",
            f"- transport_kind: {state.route_transport_kind}",
            f"- model_hint: {state.route_model_hint}",
            f"- reason: {state.route_reason}",
            f"- capabilities: {format_route_capabilities(state.route_capabilities)}",
        ]
    )


def build_topology_record(state: TaskState) -> dict[str, object]:
    return {
        "route_name": state.topology_route_name,
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
            f"- execution_site: {state.topology_execution_site}",
            f"- transport_kind: {state.topology_transport_kind}",
            f"- remote_capable_intent: {'yes' if state.topology_remote_capable_intent else 'no'}",
            f"- dispatch_status: {state.topology_dispatch_status}",
            f"- execution_lifecycle: {state.execution_lifecycle}",
        ]
    )


def build_dispatch_record(state: TaskState) -> dict[str, object]:
    return {
        "attempt_id": state.current_attempt_id,
        "attempt_number": state.current_attempt_number,
        "route_name": state.route_name,
        "execution_site": state.topology_execution_site,
        "transport_kind": state.topology_transport_kind,
        "dispatch_status": state.topology_dispatch_status,
        "dispatch_requested_at": state.dispatch_requested_at,
        "dispatch_started_at": state.dispatch_started_at,
        "execution_lifecycle": state.execution_lifecycle,
    }


def build_dispatch_report(state: TaskState) -> str:
    return "\n".join(
        [
            "# Dispatch Report",
            "",
            f"- attempt_id: {state.current_attempt_id or 'pending'}",
            f"- attempt_number: {state.current_attempt_number}",
            f"- route_name: {state.route_name}",
            f"- execution_site: {state.topology_execution_site}",
            f"- transport_kind: {state.topology_transport_kind}",
            f"- dispatch_status: {state.topology_dispatch_status}",
            f"- dispatch_requested_at: {state.dispatch_requested_at or 'pending'}",
            f"- dispatch_started_at: {state.dispatch_started_at or 'pending'}",
            f"- execution_lifecycle: {state.execution_lifecycle}",
        ]
    )


def build_handoff_record(
    state: TaskState,
    executor_result: ExecutorResult,
    compatibility_result: CompatibilityResult,
    execution_fit_result: ExecutionFitResult,
    validation_result: ValidationResult,
) -> dict[str, object]:
    if executor_result.status == "completed" and compatibility_result.status != "failed" and validation_result.status != "failed":
        handoff_status = "review_completed_run"
        blocking_reason = ""
        next_operator_action = "Review summary.md and executor_output.md before starting the next task iteration."
    else:
        handoff_status = "resume_from_failure"
        blocking_reason = executor_result.failure_kind or executor_result.message
        failure_steps = build_failure_recommendations(executor_result.failure_kind)
        next_operator_action = failure_steps[0].lstrip("- ").strip() if failure_steps else "Resume from the latest failure context."

    return {
        "status": handoff_status,
        "task_status": state.status,
        "attempt_id": state.current_attempt_id,
        "attempt_number": state.current_attempt_number,
        "execution_site": state.topology_execution_site,
        "dispatch_status": state.topology_dispatch_status,
        "execution_lifecycle": state.execution_lifecycle,
        "blocking_reason": blocking_reason,
        "next_operator_action": next_operator_action,
        "executor_status": executor_result.status,
        "failure_kind": executor_result.failure_kind,
        "compatibility_status": compatibility_result.status,
        "execution_fit_status": execution_fit_result.status,
        "validation_status": validation_result.status,
    }


def build_handoff_report(handoff_record: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Handoff Report",
            "",
            f"- status: {handoff_record.get('status', 'pending')}",
            f"- task_status: {handoff_record.get('task_status', 'pending')}",
            f"- attempt_id: {handoff_record.get('attempt_id', 'pending')}",
            f"- attempt_number: {handoff_record.get('attempt_number', 0)}",
            f"- execution_site: {handoff_record.get('execution_site', 'pending')}",
            f"- dispatch_status: {handoff_record.get('dispatch_status', 'pending')}",
            f"- execution_lifecycle: {handoff_record.get('execution_lifecycle', 'pending')}",
            f"- executor_status: {handoff_record.get('executor_status', 'pending')}",
            f"- failure_kind: {handoff_record.get('failure_kind', '') or 'none'}",
            f"- compatibility_status: {handoff_record.get('compatibility_status', 'pending')}",
            f"- execution_fit_status: {handoff_record.get('execution_fit_status', 'pending')}",
            f"- validation_status: {handoff_record.get('validation_status', 'pending')}",
            f"- blocking_reason: {handoff_record.get('blocking_reason', '') or 'none'}",
            f"- next_operator_action: {handoff_record.get('next_operator_action', 'pending')}",
        ]
    )


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
    validation_result: ValidationResult | None,
) -> str:
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
        f"- executor: {state.executor_name}",
        f"- executor_status: {state.executor_status}",
        f"- execution_lifecycle: {state.execution_lifecycle}",
        f"- attempt_id: {state.current_attempt_id or 'pending'}",
        f"- attempt_number: {state.current_attempt_number}",
        f"- route_mode: {state.route_mode}",
        f"- route_name: {state.route_name}",
        f"- route_backend: {state.route_backend}",
        f"- route_execution_site: {state.route_execution_site}",
        f"- route_remote_capable: {state.route_remote_capable}",
        f"- route_transport_kind: {state.route_transport_kind}",
        f"- route_model_hint: {state.route_model_hint}",
        f"- route_reason: {state.route_reason}",
        f"- route_capabilities: {format_route_capabilities(state.route_capabilities)}",
        f"- route_report_artifact: {state.artifact_paths.get('route_report', '') or 'pending'}",
        f"- topology_execution_site: {state.topology_execution_site}",
        f"- topology_transport_kind: {state.topology_transport_kind}",
        f"- topology_dispatch_status: {state.topology_dispatch_status}",
        f"- topology_report_artifact: {state.artifact_paths.get('topology_report', '') or 'pending'}",
        f"- dispatch_requested_at: {state.dispatch_requested_at or 'pending'}",
        f"- dispatch_started_at: {state.dispatch_started_at or 'pending'}",
        f"- dispatch_report_artifact: {state.artifact_paths.get('dispatch_report', '') or 'pending'}",
        f"- handoff_report_artifact: {state.artifact_paths.get('handoff_report', '') or 'pending'}",
        f"- compatibility_status: {compatibility_result.status if compatibility_result else 'pending'}",
        f"- execution_fit_status: {execution_fit_result.status if execution_fit_result else 'pending'}",
        f"- execution_fit_report_artifact: {state.artifact_paths.get('execution_fit_report', '') or 'pending'}",
        f"- compatibility_report_artifact: {state.artifact_paths.get('compatibility_report', '') or 'pending'}",
        f"- source_grounding_artifact: {state.artifact_paths.get('source_grounding', '') or 'pending'}",
        f"- retrieval_report_artifact: {state.artifact_paths.get('retrieval_report', '') or 'pending'}",
        f"- retrieval_record_path: {state.artifact_paths.get('retrieval_json', '') or 'pending'}",
        f"- task_memory_path: {state.artifact_paths.get('task_memory', '') or 'pending'}",
        "",
        "## Retrieved Context",
    ]
    if retrieval_items:
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
    validation_result: ValidationResult | None,
) -> str:
    top_references = ", ".join(item.reference() for item in retrieval_items[:3]) or "none"
    lines = [
        f"# Resume Note for {state.task_id}",
        "",
        "## Ready State",
        f"- task: {state.title}",
        f"- goal: {state.goal}",
        f"- status: {state.status}",
        f"- current phase: {state.phase}",
        f"- top retrieved references: {top_references}",
        f"- executor: {executor_result.executor_name}",
        f"- executor status: {executor_result.status}",
        f"- execution lifecycle: {state.execution_lifecycle}",
        f"- attempt id: {state.current_attempt_id or 'pending'}",
        f"- attempt number: {state.current_attempt_number}",
        f"- route mode: {state.route_mode}",
        f"- route name: {state.route_name}",
        f"- route backend: {state.route_backend}",
        f"- route execution site: {state.route_execution_site}",
        f"- route remote capable: {'yes' if state.route_remote_capable else 'no'}",
        f"- route transport kind: {state.route_transport_kind}",
        f"- route reason: {state.route_reason}",
        f"- route report artifact: {state.artifact_paths.get('route_report', '') or 'pending'}",
        f"- topology execution site: {state.topology_execution_site}",
        f"- topology transport kind: {state.topology_transport_kind}",
        f"- topology dispatch status: {state.topology_dispatch_status}",
        f"- topology report artifact: {state.artifact_paths.get('topology_report', '') or 'pending'}",
        f"- dispatch requested at: {state.dispatch_requested_at or 'pending'}",
        f"- dispatch started at: {state.dispatch_started_at or 'pending'}",
        f"- dispatch report artifact: {state.artifact_paths.get('dispatch_report', '') or 'pending'}",
        f"- handoff report artifact: {state.artifact_paths.get('handoff_report', '') or 'pending'}",
        f"- failure kind: {executor_result.failure_kind or 'none'}",
        f"- compatibility status: {compatibility_result.status if compatibility_result else 'pending'}",
        f"- execution fit status: {execution_fit_result.status if execution_fit_result else 'pending'}",
        f"- execution fit report artifact: {state.artifact_paths.get('execution_fit_report', '') or 'pending'}",
        f"- compatibility report artifact: {state.artifact_paths.get('compatibility_report', '') or 'pending'}",
        f"- validation status: {validation_result.status if validation_result else 'pending'}",
        "",
        "## Hand-off",
        f"- latest executor message: {executor_result.message}",
        f"- source grounding artifact: {state.artifact_paths.get('source_grounding', '') or 'pending'}",
        f"- retrieval report artifact: {state.artifact_paths.get('retrieval_report', '') or 'pending'}",
        f"- retrieval record path: {state.artifact_paths.get('retrieval_json', '') or 'pending'}",
        f"- task memory path: {state.artifact_paths.get('task_memory', '') or 'pending'}",
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
    if validation_result is not None and validation_result.status == "warning":
        next_steps.insert(0, "- Review validation_report.md before trusting this run because the validator recorded warnings.")
    if validation_result is not None and validation_result.status == "failed":
        next_steps.insert(0, "- Treat the validation report as blocking and fix the recorded failures before continuing from this run.")

    lines.extend(
        [
            "",
            "## Next Suggested Step",
            *next_steps,
            "- Review summary.md before restarting work so the prior run is not reinterpreted from scratch.",
            "- Use retrieval_report.md to review the latest retrieval set before opening raw retrieval.json.",
            "- Use compatibility_report.md when checking whether the selected route actually matched the requested policy.",
            "- Use validation_report.md when deciding whether to reuse the current run outputs.",
            "- Expand retrieval scoring when the source set grows.",
        ]
    )
    return "\n".join(lines)
