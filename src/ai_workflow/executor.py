from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
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
            failure_kind="",
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
        result = ExecutorResult(
            executor_name="codex",
            status="failed",
            message=f"Codex binary not found: {codex_bin}",
            prompt=prompt,
            failure_kind="launch_error",
        )
        return apply_fallback_if_enabled(state, retrieval_items, result)

    with tempfile.TemporaryDirectory(prefix="swl-codex-") as temp_dir:
        output_path = Path(temp_dir) / "last_message.txt"
        command = [
            codex_bin,
            "exec",
            "--skip-git-repo-check",
            "--full-auto",
            "--ephemeral",
            "--color",
            "never",
            "--output-last-message",
            str(output_path),
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
        except subprocess.TimeoutExpired as exc:
            output = read_last_message(output_path) or clean_output(exc.stdout) or clean_output(exc.stderr)
            result = ExecutorResult(
                executor_name="codex",
                status="failed",
                message=f"Codex executor timed out after {timeout_seconds} seconds.",
                output=output,
                prompt=prompt,
                failure_kind="timeout",
            )
            return apply_fallback_if_enabled(state, retrieval_items, result)
        except OSError as exc:
            result = ExecutorResult(
                executor_name="codex",
                status="failed",
                message=f"Failed to launch Codex: {exc}",
                prompt=prompt,
                failure_kind="launch_error",
            )
            return apply_fallback_if_enabled(state, retrieval_items, result)

        output = read_last_message(output_path) or clean_output(completed.stdout)
        error_output = clean_output(completed.stderr)
        if completed.returncode != 0:
            combined_output = output or error_output
            failure_kind = classify_failure_kind(completed.returncode, error_output, combined_output)
            message = f"Codex executor failed with exit code {completed.returncode}."
            if error_output:
                message = f"{message} {error_output}"
            result = ExecutorResult(
                executor_name="codex",
                status="failed",
                message=message,
                output=combined_output,
                prompt=prompt,
                failure_kind=failure_kind,
            )
            return apply_fallback_if_enabled(state, retrieval_items, result)

        return ExecutorResult(
            executor_name="codex",
            status="completed",
            message="Codex executor completed.",
            output=output or "Codex completed without a final text response.",
            prompt=prompt,
            failure_kind="",
        )


def parse_timeout_seconds(raw_value: str) -> int:
    try:
        parsed = int(raw_value)
    except ValueError:
        return 20
    return parsed if parsed > 0 else 20


def read_last_message(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def clean_output(raw: str | bytes | None) -> str:
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="ignore").strip()
    return raw.strip()


def classify_failure_kind(returncode: int, error_output: str, output: str) -> str:
    haystack = f"{error_output}\n{output}".lower()
    unreachable_markers = [
        "operation not permitted",
        "failed to connect to websocket",
        "reconnecting...",
        "transport channel closed",
        "connectfailed",
        "tcp open error",
    ]
    if any(marker in haystack for marker in unreachable_markers):
        return "unreachable_backend"
    if returncode != 0:
        return "generic_failure"
    return ""


def apply_fallback_if_enabled(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    result: ExecutorResult,
) -> ExecutorResult:
    fallback_mode = os.environ.get("AIWF_EXECUTOR_FALLBACK", "structured-note").strip().lower()
    if fallback_mode in {"", "off", "disabled", "none"}:
        return result

    fallback_output = build_fallback_output(state, retrieval_items, result)
    combined_output = fallback_output
    if result.output:
        combined_output = f"{fallback_output}\n\n## Captured Executor Output\n{result.output}"

    return ExecutorResult(
        executor_name=result.executor_name,
        status=result.status,
        message=f"{result.message} Structured fallback note generated.",
        output=combined_output,
        prompt=result.prompt,
        failure_kind=result.failure_kind,
    )


def build_fallback_output(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    result: ExecutorResult,
) -> str:
    lines = [
        "# Executor Fallback Note",
        "",
        "## Live Executor Status",
        f"- executor: {result.executor_name}",
        f"- status: {result.status}",
        f"- failure_kind: {result.failure_kind or 'none'}",
        f"- reason: {result.message}",
        "",
        "## Task",
        f"- id: {state.task_id}",
        f"- title: {state.title}",
        f"- goal: {state.goal}",
        "",
        "## Retrieved Context To Reuse",
    ]
    if retrieval_items:
        for item in retrieval_items[:5]:
            lines.append(f"- [{item.source_type}] {item.path} (score={item.score})")
    else:
        lines.append("- No retrieval matches were available.")

    lines.extend(["", "## Recommended Next Action"])
    lines.extend(build_failure_recommendations(result.failure_kind))
    return "\n".join(lines)


def build_failure_recommendations(failure_kind: str) -> list[str]:
    common_tail = [
        "- Treat this run as a failed live execution attempt, not a completed execution.",
        "- Use this note and `executor_prompt.md` as the persisted continuation context.",
    ]

    if failure_kind == "unreachable_backend":
        return [
            "- Verify that the execution environment allows outbound network and websocket access for the Codex backend.",
            "- Re-run after restoring backend connectivity, or continue manually from the retrieved context if connectivity cannot be restored now.",
            *common_tail,
        ]
    if failure_kind == "timeout":
        return [
            "- Re-run with a longer `AIWF_EXECUTOR_TIMEOUT_SECONDS` value if the backend is reachable but slow.",
            "- Review the captured partial output before retrying so the next run can resume from the latest visible progress.",
            *common_tail,
        ]
    if failure_kind == "launch_error":
        return [
            "- Verify that the Codex binary is installed and reachable in the current environment.",
            "- Re-run after fixing the local launch configuration.",
            *common_tail,
        ]
    return [
        "- Re-run when the Codex backend is reachable, or continue manually from the retrieved context.",
        *common_tail,
    ]
