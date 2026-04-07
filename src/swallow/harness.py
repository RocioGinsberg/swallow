from __future__ import annotations

from pathlib import Path
from dataclasses import replace

from .executor import build_failure_recommendations, run_executor
from .models import Event, ExecutorResult, RetrievalItem, TaskState
from .retrieval import retrieve_context
from .store import append_event, save_retrieval, write_artifact


def run_retrieval(base_dir: Path, state: TaskState) -> list[RetrievalItem]:
    query = f"{state.title} {state.goal}"
    retrieval_items = retrieve_context(Path(state.workspace_root), query=query)
    save_retrieval(base_dir, state.task_id, retrieval_items)
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="retrieval.completed",
            message="Retrieved local repository and note context.",
            payload={
                "count": len(retrieval_items),
                "top_paths": [item.path for item in retrieval_items[:3]],
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
) -> None:
    final_status = "completed" if executor_result.status == "completed" else "failed"
    render_state = replace(state, status=final_status)
    summary_body = build_summary(render_state, retrieval_items, executor_result)
    resume_note_body = build_resume_note(render_state, retrieval_items, executor_result)
    write_artifact(base_dir, state.task_id, "summary.md", summary_body)
    write_artifact(base_dir, state.task_id, "resume_note.md", resume_note_body)
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="artifacts.written",
            message="Wrote summary and resume note artifacts.",
            payload={
                "status": final_status,
                "phase": state.phase,
                "artifact_paths": {
                    "summary": state.artifact_paths.get("summary", ""),
                    "resume_note": state.artifact_paths.get("resume_note", ""),
                },
            },
        ),
    )


def build_summary(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    executor_result: ExecutorResult,
) -> str:
    lines = [
        f"# Summary for {state.task_id}",
        "",
        f"## Task",
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
        "",
        "## Retrieved Context",
    ]
    if retrieval_items:
        for item in retrieval_items:
            lines.extend(
                [
                    f"- [{item.source_type}] {item.path} (score={item.score})",
                    f"  preview: {item.preview or '(empty)'}",
                ]
            )
    else:
        lines.append("- No matching local context was found.")

    lines.extend(["", "## Executor Result", f"- message: {executor_result.message}", "", "## Executor Output"])
    if executor_result.failure_kind:
        lines.insert(len(lines) - 2, f"- failure_kind: {executor_result.failure_kind}")
    lines.append(executor_result.output or "(no executor output)")
    return "\n".join(lines)


def build_resume_note(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    executor_result: ExecutorResult,
) -> str:
    top_paths = ", ".join(item.path for item in retrieval_items[:3]) or "none"
    lines = [
        f"# Resume Note for {state.task_id}",
        "",
        "## Ready State",
        f"- task: {state.title}",
        f"- goal: {state.goal}",
        f"- status: {state.status}",
        f"- current phase: {state.phase}",
        f"- top retrieved sources: {top_paths}",
        f"- executor: {executor_result.executor_name}",
        f"- executor status: {executor_result.status}",
        f"- failure kind: {executor_result.failure_kind or 'none'}",
        "",
        "## Hand-off",
        f"- latest executor message: {executor_result.message}",
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

    lines.extend(
        [
            "",
            "## Next Suggested Step",
            *next_steps,
            "- Review summary.md before restarting work so the prior run is not reinterpreted from scratch.",
            "- Add validators once the first workflow is concrete.",
            "- Expand retrieval scoring when the source set grows.",
        ]
    )
    return "\n".join(lines)
