from __future__ import annotations

from pathlib import Path

from .executor import build_failure_recommendations, run_executor
from .models import Event, ExecutorResult, RetrievalItem, TaskState
from .retrieval import retrieve_context
from .store import append_event, save_retrieval, write_artifact


def run_harness(base_dir: Path, state: TaskState) -> tuple[list[RetrievalItem], ExecutorResult]:
    query = f"{state.title} {state.goal}"
    retrieval_items = retrieve_context(Path(state.workspace_root), query=query)
    save_retrieval(base_dir, state.task_id, retrieval_items)
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="retrieval.completed",
            message="Retrieved local repository and note context.",
            payload={"count": len(retrieval_items)},
        ),
    )
    executor_result = run_executor(state, retrieval_items)
    write_artifact(base_dir, state.task_id, "executor_prompt.md", executor_result.prompt)
    write_artifact(base_dir, state.task_id, "executor_output.md", executor_result.output or executor_result.message)
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type=f"executor.{executor_result.status}",
            message=executor_result.message,
            payload={
                "executor_name": executor_result.executor_name,
                "failure_kind": executor_result.failure_kind,
            },
        ),
    )
    return retrieval_items, executor_result


def write_task_artifacts(
    base_dir: Path,
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    executor_result: ExecutorResult,
) -> None:
    summary_body = build_summary(state, retrieval_items, executor_result)
    resume_note_body = build_resume_note(state, retrieval_items, executor_result)
    write_artifact(base_dir, state.task_id, "summary.md", summary_body)
    write_artifact(base_dir, state.task_id, "resume_note.md", resume_note_body)
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="artifacts.written",
            message="Wrote summary and resume note artifacts.",
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

    lines.extend(["", "## Next Suggested Step"])
    if executor_result.status == "completed":
        lines.append("Use the executor output to decide the next implementation action.")
    else:
        lines.extend(build_failure_recommendations(executor_result.failure_kind))
    return "\n".join(lines)


def build_resume_note(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    executor_result: ExecutorResult,
) -> str:
    top_paths = ", ".join(item.path for item in retrieval_items[:3]) or "none"
    return "\n".join(
        [
            f"# Resume Note for {state.task_id}",
            "",
            "## Ready State",
            f"- task: {state.title}",
            f"- goal: {state.goal}",
            f"- current phase: {state.phase}",
            f"- top retrieved sources: {top_paths}",
            f"- executor: {executor_result.executor_name}",
            f"- executor status: {executor_result.status}",
            f"- failure kind: {executor_result.failure_kind or 'none'}",
            "",
            "## Executor Message",
            executor_result.message,
            "",
            "## Follow-up",
            *build_failure_recommendations(executor_result.failure_kind),
            "- Add validators once the first workflow is concrete.",
            "- Expand retrieval scoring when the source set grows.",
        ]
    )
