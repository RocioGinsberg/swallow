from __future__ import annotations

from pathlib import Path

from swallow.application.commands.wiki import (
    draft_wiki_command,
    refine_wiki_command,
    refresh_wiki_evidence_command,
)
from swallow.provider_router._http_helpers import AgentLLMUnavailable


def handle_wiki_command(base_dir: Path, args: object) -> int | None:
    if getattr(args, "command", None) != "wiki":
        return None

    wiki_command = getattr(args, "wiki_command", None)
    if wiki_command == "draft":
        try:
            result = draft_wiki_command(
                base_dir,
                task_id=getattr(args, "task_id"),
                topic=getattr(args, "topic"),
                source_refs=list(getattr(args, "source_refs") or []),
                model=getattr(args, "model"),
                dry_run=bool(getattr(args, "dry_run")),
            )
        except AgentLLMUnavailable as exc:
            print(_format_llm_unavailable_error("wiki draft", exc))
            return 1
        print(_format_compile_result("wiki_draft", result))
        return 0

    if wiki_command == "refine":
        try:
            result = refine_wiki_command(
                base_dir,
                task_id=getattr(args, "task_id"),
                mode=getattr(args, "mode"),
                target_object_id=getattr(args, "target"),
                source_refs=list(getattr(args, "source_refs") or []),
                model=getattr(args, "model"),
                dry_run=bool(getattr(args, "dry_run")),
            )
        except AgentLLMUnavailable as exc:
            print(_format_llm_unavailable_error("wiki refine", exc))
            return 1
        print(_format_compile_result("wiki_refine", result))
        return 0

    if wiki_command == "refresh-evidence":
        result = refresh_wiki_evidence_command(
            base_dir,
            task_id=getattr(args, "task_id"),
            target_object_id=getattr(args, "target"),
            source_ref=getattr(args, "source_ref"),
            parser_version=getattr(args, "parser_version"),
            span=getattr(args, "span"),
            heading_path=getattr(args, "heading_path"),
        )
        print(
            f"{result.target_object_id} evidence_refreshed "
            f"task_id={result.task_id} parser_version={result.parser_version} "
            f"content_hash={result.content_hash}"
        )
        return 0

    return None


def _format_llm_unavailable_error(command_label: str, exc: AgentLLMUnavailable) -> str:
    return (
        f"{command_label} failed: {exc}\n"
        "hint: source .env before running real LLM-backed wiki commands, "
        "or add --dry-run to inspect sources without calling the LLM."
    )


def _format_compile_result(label: str, result: object) -> str:
    candidate = getattr(result, "candidate", None)
    candidate_id = getattr(candidate, "candidate_id", "") if candidate is not None else ""
    status = "dry_run" if bool(getattr(result, "dry_run", False)) else "staged"
    prompt_artifact = str(getattr(result, "prompt_artifact", "") or "-")
    result_artifact = str(getattr(result, "result_artifact", "") or "-")
    source_count = len(getattr(result, "source_pack", []) or [])
    if candidate_id:
        return (
            f"{candidate_id} {label}_{status} source_count={source_count} "
            f"prompt_artifact={prompt_artifact} result_artifact={result_artifact}"
        )
    return f"{label}_{status} source_count={source_count} prompt_artifact={prompt_artifact}"
