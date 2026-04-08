from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .models import ExecutorResult, RetrievalItem, TaskState
from .knowledge_objects import (
    summarize_canonicalization,
    summarize_knowledge_evidence,
    summarize_knowledge_reuse,
    summarize_knowledge_stages,
)
from .retrieval import summarize_reused_knowledge


DEFAULT_EXECUTOR = "codex"
EXECUTOR_ALIASES = {
    "": DEFAULT_EXECUTOR,
    "codex": "codex",
    "mock": "mock",
    "note-only": "note-only",
    "note_only": "note-only",
    "local": "local",
    "local-summary": "local",
    "local_summary": "local",
}


def normalize_executor_name(raw_name: str | None) -> str:
    normalized = (raw_name or "").strip().lower()
    return EXECUTOR_ALIASES.get(normalized, DEFAULT_EXECUTOR)


def resolve_executor_name(state: TaskState) -> str:
    configured = normalize_executor_name(state.executor_name)
    legacy_mode = normalize_executor_name(os.environ.get("AIWF_EXECUTOR_MODE"))
    if configured != DEFAULT_EXECUTOR:
        return configured
    return legacy_mode


def run_executor(state: TaskState, retrieval_items: list[RetrievalItem]) -> ExecutorResult:
    executor_name = resolve_executor_name(state)
    prompt = build_executor_prompt(state, retrieval_items)

    if executor_name == "mock":
        return run_mock_executor(prompt)
    if executor_name == "note-only":
        return run_note_only_executor(state, retrieval_items, prompt)
    if executor_name == "local":
        return run_local_executor(state, retrieval_items, prompt)
    return run_codex_executor(state, retrieval_items, prompt)


def run_mock_executor(prompt: str) -> ExecutorResult:
    return ExecutorResult(
        executor_name="mock",
        status="completed",
        message="Mock executor completed.",
        output="Mock executor output for deterministic verification.",
        prompt=prompt,
        failure_kind="",
        stdout="",
        stderr="",
    )


def run_note_only_executor(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    prompt: str,
) -> ExecutorResult:
    base_result = ExecutorResult(
        executor_name="note-only",
        status="failed",
        message="Operator selected note-only non-live mode; live Codex execution was skipped.",
        prompt=prompt,
        failure_kind="unreachable_backend",
        stdout="",
        stderr="",
    )
    return ExecutorResult(
        executor_name=base_result.executor_name,
        status=base_result.status,
        message=base_result.message,
        output=build_fallback_output(state, retrieval_items, base_result),
        prompt=base_result.prompt,
        failure_kind=base_result.failure_kind,
        stdout="",
        stderr="",
    )


def run_local_executor(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    prompt: str,
) -> ExecutorResult:
    top_references = [item.reference() for item in retrieval_items[:3]]
    top_reference_text = ", ".join(top_references) if top_references else "none"
    next_action = (
        f"Inspect {top_references[0]} and implement the smallest change that advances '{state.goal}'."
        if top_references
        else f"Inspect the workspace manually and define the smallest next change for '{state.goal}'."
    )
    risks = (
        "Retrieval may not include enough grounding yet; verify the cited sources before making code changes."
        if retrieval_items
        else "No retrieval context was found; any execution would be speculative until the workspace is reviewed."
    )
    output = "\n".join(
        [
            "# Local Executor Update",
            "",
            f"- task: {state.title}",
            f"- goal: {state.goal}",
            f"- top_references: {top_reference_text}",
            "",
            "## Next Action",
            next_action,
            "",
            "## Risks",
            risks,
            "",
            "## First Concrete Step",
            "Open the highest-ranked source, confirm the target module, and then apply one bounded change.",
        ]
    )
    return ExecutorResult(
        executor_name="local",
        status="completed",
        message="Local summary executor completed.",
        output=output,
        prompt=prompt,
        failure_kind="",
        stdout="",
        stderr="",
    )


def build_executor_prompt(state: TaskState, retrieval_items: list[RetrievalItem]) -> str:
    lines = [
        "You are the executor for a swallow workflow task.",
        f"Task ID: {state.task_id}",
        f"Task Title: {state.title}",
        f"Goal: {state.goal}",
        f"Executor: {resolve_executor_name(state)}",
        f"Route Mode: {state.route_mode or 'auto'}",
        f"Route: {state.route_name or 'pending'}",
        f"Route Backend: {state.route_backend or 'pending'}",
        f"Route Executor Family: {state.route_executor_family or 'pending'}",
        f"Route Execution Site: {state.route_execution_site or 'pending'}",
        f"Route Remote Capable: {'yes' if state.route_remote_capable else 'no'}",
        f"Route Transport Kind: {state.route_transport_kind or 'pending'}",
        f"Route Model Hint: {state.route_model_hint or 'pending'}",
        f"Route Capabilities: {format_route_capabilities(state.route_capabilities)}",
        "",
    ]
    semantics = state.task_semantics or {}
    if semantics:
        lines.extend(
            [
                "Task semantics:",
                f"- source_kind: {semantics.get('source_kind', 'unknown')}",
                f"- source_ref: {semantics.get('source_ref', '') or 'none'}",
            ]
        )
        for label, key in [
            ("constraints", "constraints"),
            ("acceptance_criteria", "acceptance_criteria"),
            ("priority_hints", "priority_hints"),
            ("next_action_proposals", "next_action_proposals"),
        ]:
            values = semantics.get(key, [])
            if values:
                lines.append(f"- {label}: {'; '.join(values)}")
        lines.append("")
    knowledge_objects = state.knowledge_objects or []
    if knowledge_objects:
        stage_counts = summarize_knowledge_stages(knowledge_objects)
        evidence_counts = summarize_knowledge_evidence(knowledge_objects)
        reuse_counts = summarize_knowledge_reuse(knowledge_objects)
        canonicalization_counts = summarize_canonicalization(knowledge_objects)
        lines.extend(
            [
                "Knowledge objects:",
                f"- count: {len(knowledge_objects)}",
                f"- raw: {stage_counts.get('raw', 0)}",
                f"- candidate: {stage_counts.get('candidate', 0)}",
                f"- verified: {stage_counts.get('verified', 0)}",
                f"- canonical: {stage_counts.get('canonical', 0)}",
                f"- artifact_backed: {evidence_counts.get('artifact_backed', 0)}",
                f"- source_only: {evidence_counts.get('source_only', 0)}",
                f"- unbacked: {evidence_counts.get('unbacked', 0)}",
                f"- retrieval_candidate: {reuse_counts.get('retrieval_candidate', 0)}",
                f"- canonicalization_review_ready: {canonicalization_counts.get('review_ready', 0)}",
                f"- canonicalization_promotion_ready: {canonicalization_counts.get('promotion_ready', 0)}",
                f"- canonicalization_blocked: {canonicalization_counts.get('blocked_stage', 0) + canonicalization_counts.get('blocked_evidence', 0)}",
            ]
        )
        top_items = [item.get("text", "") for item in knowledge_objects[:3]]
        if top_items:
            lines.append(f"- top_items: {'; '.join(item for item in top_items if item)}")
        lines.append("")
    reused_knowledge = summarize_reused_knowledge(retrieval_items)
    if reused_knowledge["count"] > 0:
        lines.extend(
            [
                "Reused verified knowledge in current retrieval:",
                f"- count: {reused_knowledge['count']}",
                f"- references: {', '.join(reused_knowledge['references'])}",
                "",
            ]
        )
    previous_memory_artifacts = [
        state.artifact_paths.get("task_memory", ""),
        state.artifact_paths.get("source_grounding", ""),
        state.artifact_paths.get("summary", ""),
        state.artifact_paths.get("resume_note", ""),
    ]
    previous_memory_artifacts = [path for path in previous_memory_artifacts if path]
    if previous_memory_artifacts:
        lines.extend(
            [
                "Prior persisted context:",
                *[f"- {path}" for path in previous_memory_artifacts],
                "",
            ]
        )
    prior_retrieval_snapshot = load_prior_retrieval_snapshot(state)
    if prior_retrieval_snapshot is not None:
        lines.extend(
            [
                "Prior retrieval memory:",
                f"- previous_retrieval_count: {prior_retrieval_snapshot['count']}",
                f"- previous_top_references: {prior_retrieval_snapshot['top_references']}",
                f"- previous_reused_knowledge_count: {prior_retrieval_snapshot['reused_knowledge_count']}",
                f"- previous_reused_current_task_knowledge_count: {prior_retrieval_snapshot['reused_knowledge_current_task_count']}",
                f"- previous_reused_cross_task_knowledge_count: {prior_retrieval_snapshot['reused_knowledge_cross_task_count']}",
                f"- previous_reused_knowledge_references: {prior_retrieval_snapshot['reused_knowledge_references']}",
                f"- previous_grounding_artifact: {prior_retrieval_snapshot['grounding_artifact']}",
                f"- previous_retrieval_record: {prior_retrieval_snapshot['retrieval_record_path']}",
                "",
            ]
        )

    lines.extend(
        [
        "Retrieved context:",
        ]
    )
    if retrieval_items:
        for item in retrieval_items:
            lines.append(
                f"- [{item.source_type}] {item.reference()} title={item.display_title()}: {item.preview}"
            )
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


def load_prior_retrieval_snapshot(state: TaskState) -> dict[str, str] | None:
    task_memory_path = state.artifact_paths.get("task_memory", "")
    if not task_memory_path:
        return None
    try:
        payload = json.loads(Path(task_memory_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    retrieval = payload.get("retrieval", {})
    top_references = retrieval.get("top_references", [])
    if not retrieval and not top_references:
        return None
    return {
        "count": str(retrieval.get("count", 0)),
        "top_references": ", ".join(top_references) if top_references else "none",
        "reused_knowledge_count": str(retrieval.get("reused_knowledge_count", 0)),
        "reused_knowledge_current_task_count": str(retrieval.get("reused_knowledge_current_task_count", 0)),
        "reused_knowledge_cross_task_count": str(retrieval.get("reused_knowledge_cross_task_count", 0)),
        "reused_knowledge_references": ", ".join(retrieval.get("reused_knowledge_references", [])) or "none",
        "grounding_artifact": str(retrieval.get("grounding_artifact", "")),
        "retrieval_record_path": str(retrieval.get("retrieval_record_path", "")),
    }


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


def run_codex_executor(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    prompt: str | None = None,
) -> ExecutorResult:
    prompt = prompt or build_executor_prompt(state, retrieval_items)
    codex_bin = os.environ.get("AIWF_CODEX_BIN", "codex").strip()
    timeout_seconds = parse_timeout_seconds(os.environ.get("AIWF_EXECUTOR_TIMEOUT_SECONDS", "20"))
    if not shutil.which(codex_bin):
        result = ExecutorResult(
            executor_name="codex",
            status="failed",
            message=f"Codex binary not found: {codex_bin}",
            prompt=prompt,
            failure_kind="launch_error",
            stdout="",
            stderr=f"Codex binary not found: {codex_bin}",
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
                stdout=clean_timeout_stream(getattr(exc, "stdout", None), getattr(exc, "output", None)),
                stderr=clean_timeout_stream(getattr(exc, "stderr", None), None),
            )
            return apply_fallback_if_enabled(state, retrieval_items, result)
        except OSError as exc:
            result = ExecutorResult(
                executor_name="codex",
                status="failed",
                message=f"Failed to launch Codex: {exc}",
                prompt=prompt,
                failure_kind="launch_error",
                stdout="",
                stderr=str(exc),
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
                stdout=clean_output(completed.stdout),
                stderr=error_output,
            )
            return apply_fallback_if_enabled(state, retrieval_items, result)

        return ExecutorResult(
            executor_name="codex",
            status="completed",
            message="Codex executor completed.",
            output=output or "Codex completed without a final text response.",
            prompt=prompt,
            failure_kind="",
            stdout=clean_output(completed.stdout),
            stderr=error_output,
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


def clean_timeout_stream(primary: str | bytes | None, fallback: str | bytes | None) -> str:
    cleaned_primary = clean_output(primary)
    if cleaned_primary:
        return cleaned_primary
    return clean_output(fallback)


def classify_failure_kind(returncode: int, error_output: str, output: str) -> str:
    haystack = f"{error_output}\n{output}".lower()
    unreachable_markers = [
        "operation not permitted",
        "failed to connect to websocket",
        "reconnecting...",
        "transport channel closed",
        "connectfailed",
        "tcp open error",
        "websocket",
        "connection failed",
        "request failed",
        "https://chatgpt.com/backend-api/wham/apps",
        "wss://chatgpt.com/backend-api/codex/responses",
        "连接失败",
        "请求失败",
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
        stdout=result.stdout,
        stderr=result.stderr,
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
            lines.append(
                f"- [{item.source_type}] {item.reference()} (score={item.score}, title={item.display_title()})"
            )
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
