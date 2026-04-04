from __future__ import annotations

from pathlib import Path

from .models import Event, RetrievalItem, TaskState
from .retrieval import retrieve_context
from .store import append_event, save_retrieval, write_artifact


def run_harness(base_dir: Path, state: TaskState) -> list[RetrievalItem]:
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
    return retrieval_items


def write_task_artifacts(base_dir: Path, state: TaskState, retrieval_items: list[RetrievalItem]) -> None:
    summary_body = build_summary(state, retrieval_items)
    handoff_body = build_handoff(state, retrieval_items)
    write_artifact(base_dir, state.task_id, "summary.md", summary_body)
    write_artifact(base_dir, state.task_id, "handoff.md", handoff_body)
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type="artifacts.written",
            message="Wrote summary and handoff artifacts.",
        ),
    )


def build_summary(state: TaskState, retrieval_items: list[RetrievalItem]) -> str:
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

    lines.extend(
        [
            "",
            "## Next Suggested Step",
            "Run a concrete executor adapter after replacing the Phase 0 placeholder harness output.",
        ]
    )
    return "\n".join(lines)


def build_handoff(state: TaskState, retrieval_items: list[RetrievalItem]) -> str:
    top_paths = ", ".join(item.path for item in retrieval_items[:3]) or "none"
    return "\n".join(
        [
            f"# Handoff for {state.task_id}",
            "",
            "## Ready State",
            f"- task: {state.title}",
            f"- goal: {state.goal}",
            f"- current phase: {state.phase}",
            f"- top retrieved sources: {top_paths}",
            "",
            "## Follow-up",
            "- Replace the placeholder execution step with a real executor adapter.",
            "- Add validators once the first workflow is concrete.",
            "- Expand retrieval scoring when the source set grows.",
        ]
    )
