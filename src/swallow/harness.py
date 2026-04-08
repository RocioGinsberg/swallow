from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .compatibility import build_compatibility_report, evaluate_route_compatibility
from .executor import build_failure_recommendations, run_executor
from .models import (
    CompatibilityResult,
    Event,
    ExecutorResult,
    RetrievalItem,
    RetrievalRequest,
    TaskState,
    ValidationResult,
)
from .retrieval import retrieve_context
from .store import append_event, save_compatibility, save_memory, save_retrieval, save_route, save_validation, write_artifact
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
) -> tuple[CompatibilityResult, ValidationResult]:
    save_route(base_dir, state.task_id, build_route_record(state))
    write_artifact(
        base_dir,
        state.task_id,
        "route_report.md",
        build_route_report(state),
    )
    write_artifact(
        base_dir,
        state.task_id,
        "source_grounding.md",
        build_source_grounding(retrieval_items),
    )
    provisional_state = replace(state, status="running")
    write_artifact(
        base_dir,
        state.task_id,
        "summary.md",
        build_summary(provisional_state, retrieval_items, executor_result, None, None),
    )
    write_artifact(
        base_dir,
        state.task_id,
        "resume_note.md",
        build_resume_note(provisional_state, retrieval_items, executor_result, None, None),
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
        and validation_result.status != "failed"
        else "failed"
    )
    render_state = replace(state, status=final_status)
    save_memory(
        base_dir,
        state.task_id,
        build_task_memory(render_state, retrieval_items, executor_result, compatibility_result, validation_result),
    )
    write_artifact(
        base_dir,
        state.task_id,
        "summary.md",
        build_summary(render_state, retrieval_items, executor_result, compatibility_result, validation_result),
    )
    write_artifact(
        base_dir,
        state.task_id,
        "resume_note.md",
        build_resume_note(render_state, retrieval_items, executor_result, compatibility_result, validation_result),
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
                    "compatibility_report": state.artifact_paths.get("compatibility_report", ""),
                    "source_grounding": state.artifact_paths.get("source_grounding", ""),
                    "validation_report": state.artifact_paths.get("validation_report", ""),
                    "task_memory": state.artifact_paths.get("task_memory", ""),
                },
            },
        ),
    )
    return compatibility_result, validation_result


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


def build_task_memory(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    executor_result: ExecutorResult,
    compatibility_result: CompatibilityResult,
    validation_result: ValidationResult,
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
        "compatibility": compatibility_result.to_dict(),
        "validation": validation_result.to_dict(),
        "retrieval": {
            "count": len(retrieval_items),
            "top_references": [item.reference() for item in retrieval_items[:5]],
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
            "compatibility_report": state.artifact_paths.get("compatibility_report", ""),
            "compatibility_json": state.artifact_paths.get("compatibility_json", ""),
            "source_grounding": state.artifact_paths.get("source_grounding", ""),
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
        f"- compatibility_status: {compatibility_result.status if compatibility_result else 'pending'}",
        f"- compatibility_report_artifact: {state.artifact_paths.get('compatibility_report', '') or 'pending'}",
        f"- source_grounding_artifact: {state.artifact_paths.get('source_grounding', '') or 'pending'}",
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
        f"- route mode: {state.route_mode}",
        f"- route name: {state.route_name}",
        f"- route backend: {state.route_backend}",
        f"- route execution site: {state.route_execution_site}",
        f"- route remote capable: {'yes' if state.route_remote_capable else 'no'}",
        f"- route transport kind: {state.route_transport_kind}",
        f"- route reason: {state.route_reason}",
        f"- route report artifact: {state.artifact_paths.get('route_report', '') or 'pending'}",
        f"- failure kind: {executor_result.failure_kind or 'none'}",
        f"- compatibility status: {compatibility_result.status if compatibility_result else 'pending'}",
        f"- compatibility report artifact: {state.artifact_paths.get('compatibility_report', '') or 'pending'}",
        f"- validation status: {validation_result.status if validation_result else 'pending'}",
        "",
        "## Hand-off",
        f"- latest executor message: {executor_result.message}",
        f"- source grounding artifact: {state.artifact_paths.get('source_grounding', '') or 'pending'}",
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
            "- Use compatibility_report.md when checking whether the selected route actually matched the requested policy.",
            "- Use validation_report.md when deciding whether to reuse the current run outputs.",
            "- Expand retrieval scoring when the source set grows.",
        ]
    )
    return "\n".join(lines)
