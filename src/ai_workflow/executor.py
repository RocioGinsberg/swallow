from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .models import ExecutorResult, RetrievalItem, TaskState


def run_executor(state: TaskState, retrieval_items: list[RetrievalItem]) -> ExecutorResult:
    mode = os.environ.get("AIWF_EXECUTOR_MODE", "codex").strip().lower()
    if mode == "mock":
        prompt = build_executor_prompt(state, retrieval_items)
        return ExecutorResult(
            executor_name="mock-codex",
            status="completed",
            message="Mock executor completed.",
            output="Mock executor output for Phase 0 verification.",
            prompt=prompt,
        )

    return run_codex_executor(state, retrieval_items)


def build_executor_prompt(state: TaskState, retrieval_items: list[RetrievalItem]) -> str:
    lines = [
        "You are the executor for a Phase 0 AI workflow task.",
        f"Task ID: {state.task_id}",
        f"Task Title: {state.title}",
        f"Goal: {state.goal}",
        "",
        "Retrieved context:",
    ]
    if retrieval_items:
        for item in retrieval_items:
            lines.append(f"- [{item.source_type}] {item.path}: {item.preview}")
    else:
        lines.append("- No retrieval matches were found.")

    lines.extend(
        [
            "",
            "Return a concise execution update with:",
            "1. what you would do next,",
            "2. the main risks or gaps,",
            "3. the first concrete implementation action.",
            "Do not assume hidden context outside the provided task and retrieved sources.",
        ]
    )
    return "\n".join(lines)


def run_codex_executor(state: TaskState, retrieval_items: list[RetrievalItem]) -> ExecutorResult:
    prompt = build_executor_prompt(state, retrieval_items)
    codex_bin = os.environ.get("AIWF_CODEX_BIN", "codex").strip()
    timeout_seconds = parse_timeout_seconds(os.environ.get("AIWF_EXECUTOR_TIMEOUT_SECONDS", "20"))
    if not shutil.which(codex_bin):
        return ExecutorResult(
            executor_name="codex",
            status="failed",
            message=f"Codex binary not found: {codex_bin}",
            prompt=prompt,
        )

    command = [
        codex_bin,
        "exec",
        "--skip-git-repo-check",
        "--full-auto",
        "--cd",
        state.workspace_root,
        prompt,
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return ExecutorResult(
            executor_name="codex",
            status="failed",
            message=f"Codex executor timed out after {timeout_seconds} seconds.",
            prompt=prompt,
        )
    except OSError as exc:
        return ExecutorResult(
            executor_name="codex",
            status="failed",
            message=f"Failed to launch Codex: {exc}",
            prompt=prompt,
        )

    output = (completed.stdout or "").strip()
    error_output = (completed.stderr or "").strip()
    if completed.returncode != 0:
        message = f"Codex executor failed with exit code {completed.returncode}."
        if error_output:
            message = f"{message} {error_output}"
        return ExecutorResult(
            executor_name="codex",
            status="failed",
            message=message,
            output=output,
            prompt=prompt,
        )

    return ExecutorResult(
        executor_name="codex",
        status="completed",
        message="Codex executor completed.",
        output=output or "Codex completed without a final text response.",
        prompt=prompt,
    )


def parse_timeout_seconds(raw_value: str) -> int:
    try:
        parsed = int(raw_value)
    except ValueError:
        return 20
    return parsed if parsed > 0 else 20
