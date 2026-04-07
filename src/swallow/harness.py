from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .executor import build_failure_recommendations, run_executor
from .models import (
    Event,
    ExecutorResult,
    RetrievalItem,
    RetrievalRequest,
    TaskState,
    ValidationResult,
)
from .retrieval import retrieve_context
from .store import append_event, save_memory, save_retrieval, save_validation, write_artifact
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
) -> ValidationResult:
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
        build_summary(provisional_state, retrieval_items, executor_result, None),
    )
    write_artifact(
        base_dir,
        state.task_id,
        "resume_note.md",
        build_resume_note(provisional_state, retrieval_items, executor_result, None),
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
        if executor_result.status == "completed" and validation_result.status != "failed"
        else "failed"
    )
    render_state = replace(state, status=final_status)
    save_memory(
        base_dir,
        state.task_id,
        build_task_memory(render_state, retrieval_items, executor_result, validation_result),
    )
    write_artifact(
        base_dir,
        state.task_id,
        "summary.md",
        build_summary(render_state, retrieval_items, executor_result, validation_result),
    )
    write_artifact(
        base_dir,
        state.task_id,
        "resume_note.md",
        build_resume_note(render_state, retrieval_items, executor_result, validation_result),
    )
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="artifacts.written",
            message="Wrote summary, resume note, and validation artifacts.",
            payload={
                "status": final_status,
                "phase": state.phase,
                "artifact_paths": {
                    "summary": state.artifact_paths.get("summary", ""),
                    "resume_note": state.artifact_paths.get("resume_note", ""),
                    "source_grounding": state.artifact_paths.get("source_grounding", ""),
                    "validation_report": state.artifact_paths.get("validation_report", ""),
                    "task_memory": state.artifact_paths.get("task_memory", ""),
                },
            },
        ),
    )
    return validation_result


def validation_counts(result: ValidationResult) -> dict[str, int]:
    counts = {"pass": 0, "warn": 0, "fail": 0}
    for finding in result.findings:
        counts[finding.level] = counts.get(finding.level, 0) + 1
    return counts


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
            "source_grounding": state.artifact_paths.get("source_grounding", ""),
            "validation_report": state.artifact_paths.get("validation_report", ""),
        },
    }


def build_summary(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    executor_result: ExecutorResult,
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
        f"- failure kind: {executor_result.failure_kind or 'none'}",
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
            "- Use validation_report.md when deciding whether to reuse the current run outputs.",
            "- Expand retrieval scoring when the source set grows.",
        ]
    )
    return "\n".join(lines)
