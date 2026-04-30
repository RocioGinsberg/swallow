from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, replace
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Protocol, runtime_checkable

import httpx

from ._http_helpers import (
    DEFAULT_NEW_API_CHAT_COMPLETIONS_URL,
    clean_output,
    extract_api_usage,
    http_request_headers as _http_request_headers,
    normalize_http_response_content as _normalize_http_response_content,
    parse_timeout_seconds,
    resolve_new_api_api_key,
    resolve_new_api_chat_completions_url,
)
from .cost_estimation import estimate_tokens
from .dialect_data import DEFAULT_EXECUTOR, collect_prompt_data, normalize_executor_name, resolve_executor_name
from .dialect_adapters import ClaudeXMLDialect, FIMDialect
from .models import DialectSpec, ExecutorResult, RetrievalItem, RouteSpec, TaskCard, TaskState
from .runtime_config import resolve_swl_chat_model
from .workspace import resolve_path

DETACHED_CHILD_ENV = "AIWF_EXECUTOR_DETACHED_CHILD"
DEFAULT_EXECUTOR_TIMEOUT_SECONDS = 20


class UnknownExecutorError(ValueError):
    """Raised when the task state points at an executor we do not implement."""


class DialectAdapter(Protocol):
    spec: DialectSpec

    def format_prompt(self, raw_prompt: str, state: TaskState, retrieval_items: list[RetrievalItem]) -> str: ...


@runtime_checkable
class ExecutorProtocol(Protocol):
    """Unified executor contract used by Runtime v0 orchestration."""

    def execute(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[RetrievalItem],
    ) -> ExecutorResult: ...

    async def execute_async(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[RetrievalItem],
    ) -> ExecutorResult: ...


def _run_harness_execution(base_dir: Path, state: TaskState, retrieval_items: list[RetrievalItem]) -> ExecutorResult:
    # Imported lazily to avoid turning executor <-> harness into a hard import cycle.
    from .harness import run_execution

    return run_execution(base_dir, state, retrieval_items)


async def _run_harness_execution_async(
    base_dir: Path,
    state: TaskState,
    retrieval_items: list[RetrievalItem],
) -> ExecutorResult:
    return await asyncio.to_thread(_run_harness_execution, base_dir, state, retrieval_items)


class LocalCLIExecutor:
    """Adapter for the existing local CLI-backed execution path."""

    def execute(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[RetrievalItem],
    ) -> ExecutorResult:
        del card  # Runtime v0 keeps task cards structural; harness semantics stay unchanged.
        return _run_harness_execution(base_dir, state, retrieval_items)

    async def execute_async(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[RetrievalItem],
    ) -> ExecutorResult:
        del card  # Runtime v0 keeps task cards structural; harness semantics stay unchanged.
        return await _run_harness_execution_async(base_dir, state, retrieval_items)


class MockExecutor:
    """Adapter for deterministic mock execution routes."""

    def execute(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[RetrievalItem],
    ) -> ExecutorResult:
        del card  # Runtime v0 keeps task cards structural; harness semantics stay unchanged.
        return _run_harness_execution(base_dir, state, retrieval_items)

    async def execute_async(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[RetrievalItem],
    ) -> ExecutorResult:
        del card  # Runtime v0 keeps task cards structural; harness semantics stay unchanged.
        return await _run_harness_execution_async(base_dir, state, retrieval_items)


class HTTPExecutor:
    """Adapter for the HTTP-backed execution path."""

    def execute(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[RetrievalItem],
    ) -> ExecutorResult:
        del card  # Runtime v0 keeps task cards structural; harness semantics stay unchanged.
        return _run_harness_execution(base_dir, state, retrieval_items)

    async def execute_async(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[RetrievalItem],
    ) -> ExecutorResult:
        del card  # Runtime v0 keeps task cards structural; harness semantics stay unchanged.
        return await _run_harness_execution_async(base_dir, state, retrieval_items)


@dataclass(frozen=True, slots=True)
class CLIAgentConfig:
    executor_name: str
    display_name: str
    bin_env_var: str
    default_bin: str
    fixed_args: tuple[str, ...]
    output_path_flags: tuple[str, ...] = ()
    workspace_root_flags: tuple[str, ...] = ()


AIDER_CONFIG = CLIAgentConfig(
    executor_name="aider",
    display_name="Aider",
    bin_env_var="AIWF_AIDER_BIN",
    default_bin="aider",
    fixed_args=("--yes-always", "--no-auto-commits"),
)

CLAUDE_CODE_CONFIG = CLIAgentConfig(
    executor_name="claude-code",
    display_name="Claude Code",
    bin_env_var="AIWF_CLAUDE_CODE_BIN",
    default_bin="claude",
    fixed_args=("--print",),
)

CODEX_CONFIG = CLIAgentConfig(
    executor_name="codex",
    display_name="Codex",
    bin_env_var="AIWF_CODEX_BIN",
    default_bin="codex",
    fixed_args=("exec",),
    output_path_flags=("-o",),
)

CLI_AGENT_CONFIGS = {
    AIDER_CONFIG.executor_name: AIDER_CONFIG,
    CLAUDE_CODE_CONFIG.executor_name: CLAUDE_CODE_CONFIG,
    CODEX_CONFIG.executor_name: CODEX_CONFIG,
}


class AsyncCLIAgentExecutor:
    """Adapter for config-driven CLI agents while runtime v0 still delegates through the harness."""

    def __init__(self, config: CLIAgentConfig) -> None:
        self.config = config

    def execute(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[RetrievalItem],
    ) -> ExecutorResult:
        del card  # Runtime v0 keeps task cards structural; harness semantics stay unchanged.
        return _run_harness_execution(base_dir, state, retrieval_items)

    async def execute_async(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[RetrievalItem],
    ) -> ExecutorResult:
        del card  # Runtime v0 keeps task cards structural; harness semantics stay unchanged.
        return await _run_harness_execution_async(base_dir, state, retrieval_items)


def _lazy_librarian() -> ExecutorProtocol:
    from .librarian_executor import LibrarianExecutor

    return LibrarianExecutor()


def _lazy_meta_optimizer() -> ExecutorProtocol:
    from .meta_optimizer import MetaOptimizerExecutor

    return MetaOptimizerExecutor()


def _lazy_ingestion_specialist() -> ExecutorProtocol:
    from .ingestion_specialist import IngestionSpecialistExecutor

    return IngestionSpecialistExecutor()


def _lazy_consistency_reviewer() -> ExecutorProtocol:
    from .consistency_reviewer import ConsistencyReviewerExecutor

    return ConsistencyReviewerExecutor()


def _lazy_validator() -> ExecutorProtocol:
    from .validator_agent import ValidatorExecutor

    return ValidatorExecutor()


def _lazy_literature_specialist() -> ExecutorProtocol:
    from .literature_specialist import LiteratureSpecialistExecutor

    return LiteratureSpecialistExecutor()


def _lazy_quality_reviewer() -> ExecutorProtocol:
    from .quality_reviewer import QualityReviewerExecutor

    return QualityReviewerExecutor()


EXECUTOR_REGISTRY: dict[str, Callable[[], ExecutorProtocol]] = {
    "consistency-reviewer": _lazy_consistency_reviewer,
    "ingestion-specialist": _lazy_ingestion_specialist,
    "librarian": _lazy_librarian,
    "literature-specialist": _lazy_literature_specialist,
    "meta-optimizer": _lazy_meta_optimizer,
    "meta_optimizer": _lazy_meta_optimizer,
    "quality-reviewer": _lazy_quality_reviewer,
    "validator": _lazy_validator,
}


def resolve_executor(executor_type: str, executor_name: str) -> ExecutorProtocol:
    raw_name = (executor_name or "").strip().lower()
    normalized_name = normalize_executor_name(executor_name)
    normalized_type = (executor_type or "").strip().lower()

    for candidate in (raw_name, normalized_name, normalized_type):
        factory = EXECUTOR_REGISTRY.get(candidate)
        if factory is not None:
            return factory()
    if normalized_name in {"mock", "mock-remote"} or normalized_type == "mock":
        return MockExecutor()
    if normalized_name == "http" or normalized_type in {"http", "api"}:
        return HTTPExecutor()
    if normalized_name in CLI_AGENT_CONFIGS:
        return AsyncCLIAgentExecutor(CLI_AGENT_CONFIGS[normalized_name])
    return LocalCLIExecutor()


class PlainTextDialect:
    spec = DialectSpec(
        name="plain_text",
        description="Default identity transform for existing plain text executor prompts.",
        supported_model_hints=["mock", "mock-remote", "local", "qwen", "glm", "gemini"],
    )

    def format_prompt(self, raw_prompt: str, state: TaskState, retrieval_items: list[RetrievalItem]) -> str:
        return raw_prompt


class StructuredMarkdownDialect:
    spec = DialectSpec(
        name="structured_markdown",
        description="Markdown-first executor prompt layout for providers that respond well to sectioned prompts.",
        supported_model_hints=[],
    )

    def format_prompt(self, raw_prompt: str, state: TaskState, retrieval_items: list[RetrievalItem]) -> str:
        del raw_prompt
        prompt_data = collect_prompt_data(state, retrieval_items)
        lines = [
            "# Swallow Executor Task",
            "",
            "## Task",
            f"- task_id: {prompt_data.task.task_id}",
            f"- title: {prompt_data.task.title}",
            f"- goal: {prompt_data.task.goal}",
            f"- executor: {prompt_data.task.executor}",
            "",
            "## Route",
            f"- route_mode: {prompt_data.route.route_mode}",
            f"- route_name: {prompt_data.route.route_name}",
            f"- route_backend: {prompt_data.route.route_backend}",
            f"- route_executor_family: {prompt_data.route.route_executor_family}",
            f"- route_execution_site: {prompt_data.route.route_execution_site}",
            f"- route_remote_capable: {'yes' if prompt_data.route.route_remote_capable else 'no'}",
            f"- route_transport_kind: {prompt_data.route.route_transport_kind}",
            f"- route_model_hint: {prompt_data.route.route_model_hint}",
            f"- route_dialect: {prompt_data.route.route_dialect}",
            f"- route_capabilities: {prompt_data.route.route_capabilities}",
            "",
        ]
        if prompt_data.semantics is not None:
            lines.extend(
                [
                    "## Task Semantics",
                    f"- source_kind: {prompt_data.semantics.source_kind}",
                    f"- source_ref: {prompt_data.semantics.source_ref}",
                ]
            )
            if prompt_data.semantics.complexity_hint:
                lines.append(f"- complexity_hint: {prompt_data.semantics.complexity_hint}")
            for label, values in [
                ("constraints", prompt_data.semantics.constraints),
                ("acceptance_criteria", prompt_data.semantics.acceptance_criteria),
                ("priority_hints", prompt_data.semantics.priority_hints),
                ("next_action_proposals", prompt_data.semantics.next_action_proposals),
            ]:
                if values:
                    lines.append(f"- {label}: {'; '.join(values)}")
            lines.append("")

        if prompt_data.knowledge is not None:
            lines.extend(
                [
                    "## Knowledge",
                    f"- count: {prompt_data.knowledge.count}",
                    f"- raw: {prompt_data.knowledge.raw}",
                    f"- candidate: {prompt_data.knowledge.candidate}",
                    f"- verified: {prompt_data.knowledge.verified}",
                    f"- canonical: {prompt_data.knowledge.canonical}",
                    f"- artifact_backed: {prompt_data.knowledge.artifact_backed}",
                    f"- source_only: {prompt_data.knowledge.source_only}",
                    f"- unbacked: {prompt_data.knowledge.unbacked}",
                    f"- retrieval_candidate: {prompt_data.knowledge.retrieval_candidate}",
                    f"- canonicalization_review_ready: {prompt_data.knowledge.canonicalization_review_ready}",
                    f"- canonicalization_promotion_ready: {prompt_data.knowledge.canonicalization_promotion_ready}",
                    f"- canonicalization_blocked: {prompt_data.knowledge.canonicalization_blocked}",
                ]
            )
            if prompt_data.knowledge.top_items:
                lines.append(f"- top_items: {'; '.join(prompt_data.knowledge.top_items)}")
            lines.append("")

        if prompt_data.reused_knowledge is not None:
            lines.extend(
                [
                    "## Reused Verified Knowledge",
                    f"- count: {prompt_data.reused_knowledge.count}",
                    f"- references: {', '.join(prompt_data.reused_knowledge.references)}",
                    "",
                ]
            )

        if prompt_data.previous_memory_artifacts:
            lines.extend(
                [
                    "## Prior Persisted Context",
                    *[f"- {path}" for path in prompt_data.previous_memory_artifacts],
                    "",
                ]
            )

        if prompt_data.prior_retrieval is not None:
            lines.extend(
                [
                    "## Prior Retrieval Memory",
                    f"- previous_retrieval_count: {prompt_data.prior_retrieval.count}",
                    f"- previous_top_references: {prompt_data.prior_retrieval.top_references}",
                    f"- previous_reused_knowledge_count: {prompt_data.prior_retrieval.reused_knowledge_count}",
                    f"- previous_reused_current_task_knowledge_count: {prompt_data.prior_retrieval.reused_knowledge_current_task_count}",
                    f"- previous_reused_cross_task_knowledge_count: {prompt_data.prior_retrieval.reused_knowledge_cross_task_count}",
                    f"- previous_reused_knowledge_references: {prompt_data.prior_retrieval.reused_knowledge_references}",
                    f"- previous_grounding_artifact: {prompt_data.prior_retrieval.grounding_artifact}",
                    f"- previous_retrieval_record: {prompt_data.prior_retrieval.retrieval_record_path}",
                    "",
                ]
            )

        lines.append("## Retrieved Context")
        if prompt_data.retrieval_entries:
            lines.extend(f"- {entry}" for entry in prompt_data.retrieval_entries)
        else:
            lines.append("- No retrieval matches were found.")

        lines.extend(
            [
                "",
                "## Instructions",
                "1. Return what you would do next.",
                "2. Call out the main risks or gaps.",
                "3. End with the first concrete implementation action.",
                "Do not assume hidden context outside the provided task and retrieved sources.",
            ]
        )
        review_feedback_markdown = str(getattr(state, "review_feedback_markdown", "") or "").strip()
        if review_feedback_markdown:
            lines.extend(["", review_feedback_markdown])
        return "\n".join(lines)


BUILTIN_DIALECTS: dict[str, DialectAdapter] = {
    "plain_text": PlainTextDialect(),
    "structured_markdown": StructuredMarkdownDialect(),
    "claude_xml": ClaudeXMLDialect(),
    "fim": FIMDialect(),
    "codex_fim": FIMDialect(),
}


def resolve_dialect_name(dialect_hint: str | None = None, model_hint: str | None = None) -> str:
    normalized_hint = (dialect_hint or "").strip().lower()
    if normalized_hint in BUILTIN_DIALECTS:
        return normalized_hint
    normalized_model_hint = (model_hint or "").strip().lower()
    for name, adapter in BUILTIN_DIALECTS.items():
        if any(hint and hint in normalized_model_hint for hint in adapter.spec.supported_model_hints):
            return name
    return "plain_text"


def resolve_dialect(dialect_hint: str | None = None, model_hint: str | None = None) -> DialectAdapter:
    return BUILTIN_DIALECTS[resolve_dialect_name(dialect_hint=dialect_hint, model_hint=model_hint)]


def run_executor(state: TaskState, retrieval_items: list[RetrievalItem]) -> ExecutorResult:
    if state.route_transport_kind == "local_detached_process" and os.environ.get(DETACHED_CHILD_ENV) != "1":
        return run_detached_executor(state, retrieval_items)
    return run_executor_inline(state, retrieval_items)


async def run_executor_async(state: TaskState, retrieval_items: list[RetrievalItem]) -> ExecutorResult:
    if state.route_transport_kind == "local_detached_process" and os.environ.get(DETACHED_CHILD_ENV) != "1":
        return await asyncio.to_thread(run_detached_executor, state, retrieval_items)
    return await run_executor_inline_async(state, retrieval_items)


def run_executor_inline(state: TaskState, retrieval_items: list[RetrievalItem]) -> ExecutorResult:
    executor_name = resolve_executor_name(state)
    prompt = build_formatted_executor_prompt(state, retrieval_items)
    result = run_prompt_executor(state, retrieval_items, prompt)
    result = replace(result, executor_name=result.executor_name or executor_name)
    result = replace(result, prompt=result.prompt or prompt)
    result = replace(result, review_feedback=str(getattr(state, "review_feedback_ref", "") or "").strip())
    result.dialect = state.route_dialect or result.dialect or resolve_dialect_name(model_hint=state.route_model_hint)
    return _attach_estimated_usage(result)


async def run_executor_inline_async(state: TaskState, retrieval_items: list[RetrievalItem]) -> ExecutorResult:
    executor_name = resolve_executor_name(state)
    prompt = build_formatted_executor_prompt(state, retrieval_items)
    result = await run_prompt_executor_async(state, retrieval_items, prompt)
    result = replace(result, executor_name=result.executor_name or executor_name)
    result = replace(result, prompt=result.prompt or prompt)
    result = replace(result, review_feedback=str(getattr(state, "review_feedback_ref", "") or "").strip())
    result.dialect = state.route_dialect or result.dialect or resolve_dialect_name(model_hint=state.route_model_hint)
    return _attach_estimated_usage(result)


def resolve_http_model_name(state: TaskState) -> str:
    configured_hint = str(state.route_model_hint or "").strip()
    if configured_hint and configured_hint not in {"http", "http-default"}:
        return configured_hint
    return resolve_swl_chat_model()


def _executor_route_fallback_enabled(state: TaskState) -> bool:
    route_name = str(state.route_name or "").strip().lower()
    return route_name.startswith("http-") or route_name in {"local-http", "local-aider", "local-claude-code"}


def _load_fallback_route(
    state: TaskState,
    current_route_name: str,
    visited_routes: set[str],
) -> RouteSpec | None:
    from .router import lookup_route_by_name

    chain = tuple(str(route_name).strip() for route_name in state.fallback_route_chain if str(route_name).strip())
    if not chain:
        return None
    try:
        current_index = chain.index(current_route_name)
    except ValueError:
        return None
    next_index = current_index + 1
    if next_index >= len(chain):
        return None
    next_route_name = chain[next_index]
    if next_route_name in visited_routes:
        return None
    return lookup_route_by_name(next_route_name)


def _apply_route_spec_for_executor_fallback(state: TaskState, route: RouteSpec, reason: str) -> None:
    # The fallback chain is an immutable execution plan from the orchestrator; do not rewrite it here.
    state.executor_name = route.executor_name
    state.route_name = route.name
    state.route_backend = route.backend_kind
    state.route_executor_family = route.executor_family
    state.route_execution_site = route.execution_site
    state.route_remote_capable = route.remote_capable
    state.route_transport_kind = route.transport_kind
    state.route_taxonomy_role = route.taxonomy.system_role
    state.route_taxonomy_memory_authority = route.taxonomy.memory_authority
    state.route_model_hint = route.model_hint
    state.route_dialect = resolve_dialect_name(route.dialect_hint, route.model_hint)
    state.route_reason = reason
    state.route_is_fallback = True
    state.route_capabilities = route.capabilities.to_dict()
    state.topology_route_name = route.name
    state.topology_executor_family = route.executor_family
    state.topology_execution_site = route.execution_site
    state.topology_transport_kind = route.transport_kind
    state.topology_remote_capable_intent = route.remote_capable


def _attach_route_fallback_metadata(
    result: ExecutorResult,
    *,
    original_route_name: str,
    fallback_route_name: str,
) -> ExecutorResult:
    return replace(
        result,
        degraded=True,
        original_route_name=result.original_route_name or original_route_name,
        fallback_route_name=result.fallback_route_name or fallback_route_name,
    )


def _run_executor_for_fallback_route(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    *,
    visited_routes: set[str],
    original_route_name: str,
) -> ExecutorResult:
    prompt = build_formatted_executor_prompt(state, retrieval_items)
    return run_prompt_executor(
        state,
        retrieval_items,
        prompt,
        visited_routes=visited_routes,
        original_route_name=original_route_name,
    )


async def _run_executor_for_fallback_route_async(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    *,
    visited_routes: set[str],
    original_route_name: str,
) -> ExecutorResult:
    prompt = build_formatted_executor_prompt(state, retrieval_items)
    return await run_prompt_executor_async(
        state,
        retrieval_items,
        prompt,
        visited_routes=visited_routes,
        original_route_name=original_route_name,
    )


def run_prompt_executor(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    prompt: str,
    *,
    visited_routes: set[str] | None = None,
    original_route_name: str | None = None,
) -> ExecutorResult:
    executor_name = resolve_executor_name(state)
    if executor_name == "mock":
        return run_mock_executor(prompt)
    if executor_name == "mock-remote":
        return run_mock_remote_executor(state, retrieval_items, prompt)
    if executor_name == "note-only":
        return run_note_only_executor(state, retrieval_items, prompt)
    if executor_name == "local":
        return run_local_executor(state, retrieval_items, prompt)
    if executor_name == "http":
        return run_http_executor(
            state,
            retrieval_items,
            prompt,
            visited_routes=visited_routes,
            original_route_name=original_route_name,
        )
    if executor_name == "aider":
        return run_cli_agent_executor(
            AIDER_CONFIG,
            state,
            retrieval_items,
            prompt,
            visited_routes=visited_routes,
            original_route_name=original_route_name,
        )
    if executor_name == "claude-code":
        return run_cli_agent_executor(
            CLAUDE_CODE_CONFIG,
            state,
            retrieval_items,
            prompt,
            visited_routes=visited_routes,
            original_route_name=original_route_name,
        )
    if executor_name == "codex":
        return run_cli_agent_executor(
            CODEX_CONFIG,
            state,
            retrieval_items,
            prompt,
            visited_routes=visited_routes,
            original_route_name=original_route_name,
        )
    raise UnknownExecutorError(f"Unknown executor name: {executor_name}")


async def run_prompt_executor_async(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    prompt: str,
    *,
    visited_routes: set[str] | None = None,
    original_route_name: str | None = None,
) -> ExecutorResult:
    executor_name = resolve_executor_name(state)
    if executor_name == "mock":
        return run_mock_executor(prompt)
    if executor_name == "mock-remote":
        return run_mock_remote_executor(state, retrieval_items, prompt)
    if executor_name == "note-only":
        return run_note_only_executor(state, retrieval_items, prompt)
    if executor_name == "local":
        return run_local_executor(state, retrieval_items, prompt)
    if executor_name == "http":
        return await run_http_executor_async(
            state,
            retrieval_items,
            prompt,
            visited_routes=visited_routes,
            original_route_name=original_route_name,
        )
    if executor_name == "aider":
        return await run_cli_agent_executor_async(
            AIDER_CONFIG,
            state,
            retrieval_items,
            prompt,
            visited_routes=visited_routes,
            original_route_name=original_route_name,
        )
    if executor_name == "claude-code":
        return await run_cli_agent_executor_async(
            CLAUDE_CODE_CONFIG,
            state,
            retrieval_items,
            prompt,
            visited_routes=visited_routes,
            original_route_name=original_route_name,
        )
    if executor_name == "codex":
        return await run_cli_agent_executor_async(
            CODEX_CONFIG,
            state,
            retrieval_items,
            prompt,
            visited_routes=visited_routes,
            original_route_name=original_route_name,
        )
    raise UnknownExecutorError(f"Unknown executor name: {executor_name}")


def _apply_executor_route_fallback(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    result: ExecutorResult,
    *,
    visited_routes: set[str] | None = None,
    original_route_name: str | None = None,
) -> ExecutorResult:
    if not _executor_route_fallback_enabled(state):
        return apply_fallback_if_enabled(state, retrieval_items, result)

    current_route_name = str(state.route_name or "").strip()
    if not current_route_name:
        return apply_fallback_if_enabled(state, retrieval_items, result)

    seen_routes = set(visited_routes or ())
    seen_routes.add(current_route_name)
    primary_route_name = str(original_route_name or current_route_name).strip() or current_route_name
    fallback_route = _load_fallback_route(state, current_route_name, seen_routes)
    if fallback_route is None or fallback_route.name in seen_routes:
        if result.degraded:
            return result
        return apply_fallback_if_enabled(state, retrieval_items, result)

    fallback_reason = (
        f"Executor-level route fallback selected '{fallback_route.name}' after '{current_route_name}' failed."
    )
    _apply_route_spec_for_executor_fallback(state, fallback_route, fallback_reason)
    fallback_result = _run_executor_for_fallback_route(
        state,
        retrieval_items,
        visited_routes=seen_routes | {fallback_route.name},
        original_route_name=primary_route_name,
    )
    return _attach_route_fallback_metadata(
        fallback_result,
        original_route_name=primary_route_name,
        fallback_route_name=str(fallback_result.fallback_route_name or state.route_name).strip() or fallback_route.name,
    )


async def _apply_executor_route_fallback_async(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    result: ExecutorResult,
    *,
    visited_routes: set[str] | None = None,
    original_route_name: str | None = None,
) -> ExecutorResult:
    if not _executor_route_fallback_enabled(state):
        return apply_fallback_if_enabled(state, retrieval_items, result)

    current_route_name = str(state.route_name or "").strip()
    if not current_route_name:
        return apply_fallback_if_enabled(state, retrieval_items, result)

    seen_routes = set(visited_routes or ())
    seen_routes.add(current_route_name)
    primary_route_name = str(original_route_name or current_route_name).strip() or current_route_name
    fallback_route = _load_fallback_route(state, current_route_name, seen_routes)
    if fallback_route is None or fallback_route.name in seen_routes:
        if result.degraded:
            return result
        return apply_fallback_if_enabled(state, retrieval_items, result)

    fallback_reason = (
        f"Executor-level route fallback selected '{fallback_route.name}' after '{current_route_name}' failed."
    )
    _apply_route_spec_for_executor_fallback(state, fallback_route, fallback_reason)
    fallback_result = await _run_executor_for_fallback_route_async(
        state,
        retrieval_items,
        visited_routes=seen_routes | {fallback_route.name},
        original_route_name=primary_route_name,
    )
    return _attach_route_fallback_metadata(
        fallback_result,
        original_route_name=primary_route_name,
        fallback_route_name=str(fallback_result.fallback_route_name or state.route_name).strip() or fallback_route.name,
    )


def run_detached_executor(state: TaskState, retrieval_items: list[RetrievalItem]) -> ExecutorResult:
    prompt = build_formatted_executor_prompt(state, retrieval_items)
    with tempfile.TemporaryDirectory(prefix="swallow-detached-") as tmp:
        tmp_path = Path(tmp)
        state_json = tmp_path / "state.json"
        retrieval_json = tmp_path / "retrieval.json"
        result_json = tmp_path / "result.json"
        state_json.write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")
        retrieval_json.write_text(
            json.dumps([item.to_dict() for item in retrieval_items], indent=2) + "\n",
            encoding="utf-8",
        )
        child_env = os.environ.copy()
        child_env[DETACHED_CHILD_ENV] = "1"
        repo_root = resolve_path(Path(__file__), base=Path.cwd()).parents[2]
        src_root = str(repo_root / "src")
        existing_pythonpath = child_env.get("PYTHONPATH", "")
        child_env["PYTHONPATH"] = src_root if not existing_pythonpath else f"{src_root}{os.pathsep}{existing_pythonpath}"
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "swallow.executor",
                "--detached-child",
                "--state-json",
                str(state_json),
                "--retrieval-json",
                str(retrieval_json),
                "--result-json",
                str(result_json),
            ],
            check=False,
            capture_output=True,
            text=True,
            env=child_env,
        )
        if completed.returncode != 0:
            return _attach_estimated_usage(
                ExecutorResult(
                    executor_name=resolve_executor_name(state),
                    status="failed",
                    message="Detached local executor child process failed.",
                    output="",
                    prompt=prompt,
                    dialect=state.route_dialect or resolve_dialect_name(model_hint=state.route_model_hint),
                    failure_kind="launch_error",
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                )
            )
        try:
            payload = json.loads(result_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return _attach_estimated_usage(
                ExecutorResult(
                    executor_name=resolve_executor_name(state),
                    status="failed",
                    message="Detached local executor did not return a readable result.",
                    output="",
                    prompt=prompt,
                    dialect=state.route_dialect or resolve_dialect_name(model_hint=state.route_model_hint),
                    failure_kind="generic_failure",
                    stdout=completed.stdout,
                    stderr=f"{completed.stderr}\n{exc}".strip(),
                )
            )
    return replace(
        ExecutorResult(**payload),
        review_feedback=str(getattr(state, "review_feedback_ref", "") or "").strip(),
    )




def _attach_estimated_usage(result: ExecutorResult) -> ExecutorResult:
    input_tokens = int(result.estimated_input_tokens or 0)
    output_tokens = int(result.estimated_output_tokens or 0)
    if input_tokens > 0 and output_tokens > 0:
        return result
    return replace(
        result,
        estimated_input_tokens=input_tokens if input_tokens > 0 else estimate_tokens(result.prompt),
        estimated_output_tokens=output_tokens if output_tokens > 0 else estimate_tokens(result.output),
    )


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


def run_mock_remote_executor(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    prompt: str,
) -> ExecutorResult:
    """Deterministic remote-dispatch stub used only for topology validation tests."""
    outcome = os.environ.get("AIWF_MOCK_REMOTE_OUTCOME", "completed").strip().lower()
    if outcome == "failed":
        return ExecutorResult(
            executor_name="mock-remote",
            status="failed",
            message="Mock remote executor reported a simulated dispatch failure.",
            output=build_fallback_output(
                state,
                retrieval_items,
                ExecutorResult(
                    executor_name="mock-remote",
                    status="failed",
                    message="Mock remote executor reported a simulated dispatch failure.",
                    prompt=prompt,
                    failure_kind="mock_remote_failure",
                    stdout="",
                    stderr="Simulated mock remote failure.",
                ),
            ),
            prompt=prompt,
            failure_kind="mock_remote_failure",
            stdout="",
            stderr="Simulated mock remote failure.",
        )

    node_ref = os.environ.get("AIWF_MOCK_REMOTE_NODE", "mock-remote-node").strip() or "mock-remote-node"
    output = "\n".join(
        [
            "# Mock Remote Executor Update",
            "",
            f"- task: {state.title}",
            f"- goal: {state.goal}",
            f"- remote_node: {node_ref}",
            f"- retrieval_items: {len(retrieval_items)}",
            "",
            "## Dispatch Result",
            "Mock remote dispatch completed without using any real network transport.",
        ]
    )
    return ExecutorResult(
        executor_name="mock-remote",
        status="completed",
        message="Mock remote executor completed.",
        output=output,
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
        message="Operator selected note-only non-live mode; live executor execution was skipped.",
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
    prompt_data = collect_prompt_data(state, retrieval_items)
    lines = [
        "You are the executor for a swallow workflow task.",
        f"Task ID: {prompt_data.task.task_id}",
        f"Task Title: {prompt_data.task.title}",
        f"Goal: {prompt_data.task.goal}",
        f"Executor: {prompt_data.task.executor}",
        f"Route Mode: {prompt_data.route.route_mode}",
        f"Route: {prompt_data.route.route_name}",
        f"Route Backend: {prompt_data.route.route_backend}",
        f"Route Executor Family: {prompt_data.route.route_executor_family}",
        f"Route Execution Site: {prompt_data.route.route_execution_site}",
        f"Route Remote Capable: {'yes' if prompt_data.route.route_remote_capable else 'no'}",
        f"Route Transport Kind: {prompt_data.route.route_transport_kind}",
        f"Route Model Hint: {prompt_data.route.route_model_hint}",
        f"Route Capabilities: {prompt_data.route.route_capabilities}",
        "",
    ]
    if prompt_data.semantics is not None:
        lines.extend(
            [
                "Task semantics:",
                f"- source_kind: {prompt_data.semantics.source_kind}",
                f"- source_ref: {prompt_data.semantics.source_ref}",
            ]
        )
        if prompt_data.semantics.complexity_hint:
            lines.append(f"- complexity_hint: {prompt_data.semantics.complexity_hint}")
        for label, values in [
            ("constraints", prompt_data.semantics.constraints),
            ("acceptance_criteria", prompt_data.semantics.acceptance_criteria),
            ("priority_hints", prompt_data.semantics.priority_hints),
            ("next_action_proposals", prompt_data.semantics.next_action_proposals),
        ]:
            if values:
                lines.append(f"- {label}: {'; '.join(values)}")
        lines.append("")
    if prompt_data.knowledge is not None:
        lines.extend(
            [
                "Knowledge objects:",
                f"- count: {prompt_data.knowledge.count}",
                f"- raw: {prompt_data.knowledge.raw}",
                f"- candidate: {prompt_data.knowledge.candidate}",
                f"- verified: {prompt_data.knowledge.verified}",
                f"- canonical: {prompt_data.knowledge.canonical}",
                f"- artifact_backed: {prompt_data.knowledge.artifact_backed}",
                f"- source_only: {prompt_data.knowledge.source_only}",
                f"- unbacked: {prompt_data.knowledge.unbacked}",
                f"- retrieval_candidate: {prompt_data.knowledge.retrieval_candidate}",
                f"- canonicalization_review_ready: {prompt_data.knowledge.canonicalization_review_ready}",
                f"- canonicalization_promotion_ready: {prompt_data.knowledge.canonicalization_promotion_ready}",
                f"- canonicalization_blocked: {prompt_data.knowledge.canonicalization_blocked}",
            ]
        )
        if prompt_data.knowledge.top_items:
            lines.append(f"- top_items: {'; '.join(prompt_data.knowledge.top_items)}")
        lines.append("")
    if prompt_data.reused_knowledge is not None:
        lines.extend(
            [
                "Reused verified knowledge in current retrieval:",
                f"- count: {prompt_data.reused_knowledge.count}",
                f"- references: {', '.join(prompt_data.reused_knowledge.references)}",
                "",
            ]
        )
    if prompt_data.previous_memory_artifacts:
        lines.extend(
            [
                "Prior persisted context:",
                *[f"- {path}" for path in prompt_data.previous_memory_artifacts],
                "",
            ]
        )
    if prompt_data.prior_retrieval is not None:
        lines.extend(
            [
                "Prior retrieval memory:",
                f"- previous_retrieval_count: {prompt_data.prior_retrieval.count}",
                f"- previous_top_references: {prompt_data.prior_retrieval.top_references}",
                f"- previous_reused_knowledge_count: {prompt_data.prior_retrieval.reused_knowledge_count}",
                f"- previous_reused_current_task_knowledge_count: {prompt_data.prior_retrieval.reused_knowledge_current_task_count}",
                f"- previous_reused_cross_task_knowledge_count: {prompt_data.prior_retrieval.reused_knowledge_cross_task_count}",
                f"- previous_reused_knowledge_references: {prompt_data.prior_retrieval.reused_knowledge_references}",
                f"- previous_grounding_artifact: {prompt_data.prior_retrieval.grounding_artifact}",
                f"- previous_retrieval_record: {prompt_data.prior_retrieval.retrieval_record_path}",
                "",
            ]
        )

    lines.extend(
        [
        "Retrieved context:",
        ]
    )
    if prompt_data.retrieval_entries:
        lines.extend(f"- {entry}" for entry in prompt_data.retrieval_entries)
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
    review_feedback_markdown = str(getattr(state, "review_feedback_markdown", "") or "").strip()
    if review_feedback_markdown:
        lines.extend(["", review_feedback_markdown])
    return "\n".join(lines)


def build_formatted_executor_prompt(state: TaskState, retrieval_items: list[RetrievalItem]) -> str:
    dialect_name = resolve_dialect_name(getattr(state, "route_dialect", ""), state.route_model_hint)
    state.route_dialect = dialect_name
    raw_prompt = build_executor_prompt(state, retrieval_items)
    adapter = resolve_dialect(dialect_name, state.route_model_hint)
    return adapter.format_prompt(raw_prompt, state, retrieval_items)


def _http_request_payload(prompt: str, state: TaskState) -> dict[str, object]:
    return {
        "model": resolve_http_model_name(state),
        "messages": [{"role": "user", "content": prompt}],
    }


def run_http_executor(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    prompt: str | None = None,
    *,
    visited_routes: set[str] | None = None,
    original_route_name: str | None = None,
) -> ExecutorResult:
    prompt = prompt or build_formatted_executor_prompt(state, retrieval_items)
    endpoint = resolve_new_api_chat_completions_url()
    headers = _http_request_headers()
    timeout_seconds = parse_timeout_seconds(
        os.environ.get("AIWF_EXECUTOR_TIMEOUT_SECONDS", str(DEFAULT_EXECUTOR_TIMEOUT_SECONDS))
    )
    payload = _http_request_payload(prompt, state)

    try:
        response = httpx.post(endpoint, json=payload, headers=headers, timeout=timeout_seconds)
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        result = ExecutorResult(
            executor_name="http",
            status="failed",
            message=f"HTTP executor timed out after {timeout_seconds} seconds.",
            prompt=prompt,
            failure_kind="http_timeout",
            stdout="",
            stderr=str(exc),
        )
        return _apply_executor_route_fallback(
            state,
            retrieval_items,
            result,
            visited_routes=visited_routes,
            original_route_name=original_route_name,
        )
    except httpx.HTTPStatusError as exc:
        response_text = clean_output(exc.response.text)
        if exc.response.status_code in {401, 403} and "Authorization" not in headers:
            response_text = (
                response_text
                or "Set SWL_API_KEY before using the HTTP executor."
            )
        failure_kind = "http_rate_limited" if exc.response.status_code == 429 else "http_error"
        result = ExecutorResult(
            executor_name="http",
            status="failed",
            message=f"HTTP executor failed with status {exc.response.status_code}.",
            output=response_text,
            prompt=prompt,
            failure_kind=failure_kind,
            stdout="",
            stderr=response_text or str(exc),
        )
        if exc.response.status_code == 429:
            return apply_fallback_if_enabled(state, retrieval_items, result)
        return _apply_executor_route_fallback(
            state,
            retrieval_items,
            result,
            visited_routes=visited_routes,
            original_route_name=original_route_name,
        )
    except httpx.RequestError as exc:
        result = ExecutorResult(
            executor_name="http",
            status="failed",
            message=f"HTTP executor request failed: {exc}",
            prompt=prompt,
            failure_kind="http_error",
            stdout="",
            stderr=str(exc),
        )
        return _apply_executor_route_fallback(
            state,
            retrieval_items,
            result,
            visited_routes=visited_routes,
            original_route_name=original_route_name,
        )

    try:
        data = response.json()
        choices = data["choices"]
        message = choices[0]["message"]
        content = _normalize_http_response_content(message.get("content"))
        input_tokens, output_tokens = extract_api_usage(data)
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        result = ExecutorResult(
            executor_name="http",
            status="failed",
            message="HTTP executor returned an unreadable chat completion payload.",
            output=clean_output(response.text),
            prompt=prompt,
            failure_kind="http_error",
            stdout="",
            stderr=str(exc),
        )
        return _apply_executor_route_fallback(
            state,
            retrieval_items,
            result,
            visited_routes=visited_routes,
            original_route_name=original_route_name,
        )

    return _attach_estimated_usage(
        ExecutorResult(
            executor_name="http",
            status="completed",
            message="HTTP executor completed.",
            output=content or "HTTP executor completed without a final text response.",
            prompt=prompt,
            failure_kind="",
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=output_tokens,
            stdout="",
            stderr="",
        )
    )


async def run_http_executor_async(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    prompt: str | None = None,
    *,
    visited_routes: set[str] | None = None,
    original_route_name: str | None = None,
) -> ExecutorResult:
    prompt = prompt or build_formatted_executor_prompt(state, retrieval_items)
    endpoint = resolve_new_api_chat_completions_url()
    headers = _http_request_headers()
    timeout_seconds = parse_timeout_seconds(
        os.environ.get("AIWF_EXECUTOR_TIMEOUT_SECONDS", str(DEFAULT_EXECUTOR_TIMEOUT_SECONDS))
    )
    payload = _http_request_payload(prompt, state)

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        result = ExecutorResult(
            executor_name="http",
            status="failed",
            message=f"HTTP executor timed out after {timeout_seconds} seconds.",
            prompt=prompt,
            failure_kind="http_timeout",
            stdout="",
            stderr=str(exc),
        )
        return await _apply_executor_route_fallback_async(
            state,
            retrieval_items,
            result,
            visited_routes=visited_routes,
            original_route_name=original_route_name,
        )
    except httpx.HTTPStatusError as exc:
        response_text = clean_output(exc.response.text)
        if exc.response.status_code in {401, 403} and "Authorization" not in headers:
            response_text = (
                response_text
                or "Set SWL_API_KEY before using the HTTP executor."
            )
        failure_kind = "http_rate_limited" if exc.response.status_code == 429 else "http_error"
        result = ExecutorResult(
            executor_name="http",
            status="failed",
            message=f"HTTP executor failed with status {exc.response.status_code}.",
            output=response_text,
            prompt=prompt,
            failure_kind=failure_kind,
            stdout="",
            stderr=response_text or str(exc),
        )
        if exc.response.status_code == 429:
            return apply_fallback_if_enabled(state, retrieval_items, result)
        return await _apply_executor_route_fallback_async(
            state,
            retrieval_items,
            result,
            visited_routes=visited_routes,
            original_route_name=original_route_name,
        )
    except httpx.RequestError as exc:
        result = ExecutorResult(
            executor_name="http",
            status="failed",
            message=f"HTTP executor request failed: {exc}",
            prompt=prompt,
            failure_kind="http_error",
            stdout="",
            stderr=str(exc),
        )
        return await _apply_executor_route_fallback_async(
            state,
            retrieval_items,
            result,
            visited_routes=visited_routes,
            original_route_name=original_route_name,
        )

    try:
        data = response.json()
        choices = data["choices"]
        message = choices[0]["message"]
        content = _normalize_http_response_content(message.get("content"))
        input_tokens, output_tokens = extract_api_usage(data)
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError, AttributeError) as exc:
        result = ExecutorResult(
            executor_name="http",
            status="failed",
            message="HTTP executor returned an unreadable chat completion payload.",
            output=clean_output(getattr(response, "text", "")),
            prompt=prompt,
            failure_kind="http_error",
            stdout="",
            stderr=str(exc),
        )
        return await _apply_executor_route_fallback_async(
            state,
            retrieval_items,
            result,
            visited_routes=visited_routes,
            original_route_name=original_route_name,
        )

    return _attach_estimated_usage(
        ExecutorResult(
            executor_name="http",
            status="completed",
            message="HTTP executor completed.",
            output=content or "HTTP executor completed without a final text response.",
            prompt=prompt,
            failure_kind="",
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=output_tokens,
            stdout="",
            stderr="",
        )
    )


def _build_cli_agent_command(
    config: CLIAgentConfig,
    *,
    workspace_root: str,
    prompt: str,
    output_path: Path | None = None,
) -> list[str]:
    command = [resolve_cli_agent_binary(config), *config.fixed_args]
    if output_path is not None and config.output_path_flags:
        command.extend([*config.output_path_flags, str(output_path)])
    if config.workspace_root_flags:
        command.extend([*config.workspace_root_flags, workspace_root])
    command.append(prompt)
    return command


def resolve_cli_agent_binary(config: CLIAgentConfig) -> str:
    return os.environ.get(config.bin_env_var, config.default_bin).strip() or config.default_bin


def run_cli_agent_executor(
    config: CLIAgentConfig,
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    prompt: str | None = None,
    *,
    visited_routes: set[str] | None = None,
    original_route_name: str | None = None,
) -> ExecutorResult:
    prompt = prompt or build_formatted_executor_prompt(state, retrieval_items)
    agent_bin = resolve_cli_agent_binary(config)
    timeout_seconds = parse_timeout_seconds(
        os.environ.get("AIWF_EXECUTOR_TIMEOUT_SECONDS", str(DEFAULT_EXECUTOR_TIMEOUT_SECONDS))
    )
    if not shutil.which(agent_bin):
        result = ExecutorResult(
            executor_name=config.executor_name,
            status="failed",
            message=f"{config.display_name} binary not found: {agent_bin}",
            prompt=prompt,
            failure_kind="launch_error",
            stdout="",
            stderr=f"{config.display_name} binary not found: {agent_bin}",
        )
        return _apply_executor_route_fallback(
            state,
            retrieval_items,
            result,
            visited_routes=visited_routes,
            original_route_name=original_route_name,
        )

    with tempfile.TemporaryDirectory(prefix=f"swl-{config.executor_name}-") as temp_dir:
        output_path = Path(temp_dir) / "last_message.txt" if config.output_path_flags else None
        command = _build_cli_agent_command(
            config,
            workspace_root=state.workspace_root,
            prompt=prompt,
            output_path=output_path,
        )
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
            output = (
                (read_last_message(output_path) if output_path is not None else "")
                or clean_output(exc.stdout)
                or clean_output(exc.stderr)
            )
            result = ExecutorResult(
                executor_name=config.executor_name,
                status="failed",
                message=f"{config.display_name} executor timed out after {timeout_seconds} seconds.",
                output=output,
                prompt=prompt,
                failure_kind="timeout",
                stdout=clean_timeout_stream(getattr(exc, "stdout", None), getattr(exc, "output", None)),
                stderr=clean_timeout_stream(getattr(exc, "stderr", None), None),
            )
            return _apply_executor_route_fallback(
                state,
                retrieval_items,
                result,
                visited_routes=visited_routes,
                original_route_name=original_route_name,
            )
        except OSError as exc:
            result = ExecutorResult(
                executor_name=config.executor_name,
                status="failed",
                message=f"Failed to launch {config.display_name}: {exc}",
                prompt=prompt,
                failure_kind="launch_error",
                stdout="",
                stderr=str(exc),
            )
            return _apply_executor_route_fallback(
                state,
                retrieval_items,
                result,
                visited_routes=visited_routes,
                original_route_name=original_route_name,
            )

        output = (read_last_message(output_path) if output_path is not None else "") or clean_output(completed.stdout)
        error_output = clean_output(completed.stderr)
        if completed.returncode != 0:
            combined_output = output or error_output
            failure_kind = classify_failure_kind(completed.returncode, error_output, combined_output)
            message = f"{config.display_name} executor failed with exit code {completed.returncode}."
            if error_output:
                message = f"{message} {error_output}"
            result = ExecutorResult(
                executor_name=config.executor_name,
                status="failed",
                message=message,
                output=combined_output,
                prompt=prompt,
                failure_kind=failure_kind,
                stdout=clean_output(completed.stdout),
                stderr=error_output,
            )
            return _apply_executor_route_fallback(
                state,
                retrieval_items,
                result,
                visited_routes=visited_routes,
                original_route_name=original_route_name,
            )

        return ExecutorResult(
            executor_name=config.executor_name,
            status="completed",
            message=f"{config.display_name} executor completed.",
            output=output or f"{config.display_name} completed without a final text response.",
            prompt=prompt,
            failure_kind="",
            stdout=clean_output(completed.stdout),
            stderr=error_output,
        )


async def run_cli_agent_executor_async(
    config: CLIAgentConfig,
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    prompt: str | None = None,
    *,
    visited_routes: set[str] | None = None,
    original_route_name: str | None = None,
) -> ExecutorResult:
    prompt = prompt or build_formatted_executor_prompt(state, retrieval_items)
    agent_bin = resolve_cli_agent_binary(config)
    timeout_seconds = parse_timeout_seconds(
        os.environ.get("AIWF_EXECUTOR_TIMEOUT_SECONDS", str(DEFAULT_EXECUTOR_TIMEOUT_SECONDS))
    )
    if not shutil.which(agent_bin):
        result = ExecutorResult(
            executor_name=config.executor_name,
            status="failed",
            message=f"{config.display_name} binary not found: {agent_bin}",
            prompt=prompt,
            failure_kind="launch_error",
            stdout="",
            stderr=f"{config.display_name} binary not found: {agent_bin}",
        )
        return _apply_executor_route_fallback(
            state,
            retrieval_items,
            result,
            visited_routes=visited_routes,
            original_route_name=original_route_name,
        )

    with tempfile.TemporaryDirectory(prefix=f"swl-{config.executor_name}-") as temp_dir:
        output_path = Path(temp_dir) / "last_message.txt" if config.output_path_flags else None
        command = _build_cli_agent_command(
            config,
            workspace_root=state.workspace_root,
            prompt=prompt,
            output_path=output_path,
        )
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=state.workspace_root,
            )
        except OSError as exc:
            result = ExecutorResult(
                executor_name=config.executor_name,
                status="failed",
                message=f"Failed to launch {config.display_name}: {exc}",
                prompt=prompt,
                failure_kind="launch_error",
                stdout="",
                stderr=str(exc),
            )
            return _apply_executor_route_fallback(
                state,
                retrieval_items,
                result,
                visited_routes=visited_routes,
                original_route_name=original_route_name,
            )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
        except asyncio.CancelledError:
            if process.returncode is None:
                process.kill()
            try:
                await process.communicate()
            except Exception:  # pragma: no cover - best-effort cancellation cleanup
                pass
            raise
        except asyncio.TimeoutError:
            process.kill()
            stdout_bytes, stderr_bytes = await process.communicate()
            output = (read_last_message(output_path) if output_path is not None else "") or clean_output(stdout_bytes)
            result = ExecutorResult(
                executor_name=config.executor_name,
                status="failed",
                message=f"{config.display_name} executor timed out after {timeout_seconds} seconds.",
                output=output or clean_output(stderr_bytes),
                prompt=prompt,
                failure_kind="timeout",
                stdout=clean_output(stdout_bytes),
                stderr=clean_output(stderr_bytes),
            )
            return _apply_executor_route_fallback(
                state,
                retrieval_items,
                result,
                visited_routes=visited_routes,
                original_route_name=original_route_name,
            )

        output = (read_last_message(output_path) if output_path is not None else "") or clean_output(stdout_bytes)
        error_output = clean_output(stderr_bytes)
        if process.returncode != 0:
            combined_output = output or error_output
            failure_kind = classify_failure_kind(process.returncode or 1, error_output, combined_output)
            message = f"{config.display_name} executor failed with exit code {process.returncode}."
            if error_output:
                message = f"{message} {error_output}"
            result = ExecutorResult(
                executor_name=config.executor_name,
                status="failed",
                message=message,
                output=combined_output,
                prompt=prompt,
                failure_kind=failure_kind,
                stdout=clean_output(stdout_bytes),
                stderr=error_output,
            )
            return _apply_executor_route_fallback(
                state,
                retrieval_items,
                result,
                visited_routes=visited_routes,
                original_route_name=original_route_name,
            )

        return ExecutorResult(
            executor_name=config.executor_name,
            status="completed",
            message=f"{config.display_name} executor completed.",
            output=output or f"{config.display_name} completed without a final text response.",
            prompt=prompt,
            failure_kind="",
            stdout=clean_output(stdout_bytes),
            stderr=error_output,
        )


def read_last_message(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


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
        dialect=result.dialect,
        failure_kind=result.failure_kind,
        stdout=result.stdout,
        stderr=result.stderr,
        review_feedback=result.review_feedback,
        degraded=result.degraded,
        original_route_name=result.original_route_name,
        fallback_route_name=result.fallback_route_name,
        side_effects=result.side_effects,
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
    ]
    if result.degraded:
        lines.extend(
            [
                f"- degraded: yes",
                f"- original_route: {result.original_route_name or 'unknown'}",
                f"- fallback_route: {result.fallback_route_name or state.route_name or 'unknown'}",
            ]
        )
    lines.extend(
        [
        "",
        "## Task",
        f"- id: {state.task_id}",
        f"- title: {state.title}",
        f"- goal: {state.goal}",
        "",
        "## Retrieved Context To Reuse",
        ]
    )
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

    if failure_kind == "http_error":
        return [
            "- Verify that the configured new-api endpoint is reachable and returns an OpenAI-compatible chat completion payload.",
            "- Confirm that the selected HTTP route resolves to a concrete model ID instead of the compatibility alias.",
            "- Re-run after checking endpoint status, credentials, and model mapping, or continue manually from the retrieved context if the HTTP path is unavailable now.",
            *common_tail,
        ]
    if failure_kind == "http_rate_limited":
        return [
            "- The HTTP gateway reported rate limiting (429); prefer retrying the same route instead of switching models immediately.",
            "- Re-run after a short backoff or adjust provider-side quota / concurrency settings before changing the route.",
            "- Keep the current route as the primary recovery path unless repeated rate limiting persists across retries.",
            *common_tail,
        ]
    if failure_kind == "http_timeout":
        return [
            "- Re-run with a longer `AIWF_EXECUTOR_TIMEOUT_SECONDS` value if the HTTP gateway is reachable but slow.",
            "- Review gateway health and model latency before retrying so the next run uses an explicit timeout assumption.",
            *common_tail,
        ]
    if failure_kind == "unreachable_backend":
        return [
            "- Verify that the execution environment allows outbound network and process execution access for the configured live executor.",
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
            "- Verify that the configured live executor binary is installed and reachable in the current environment.",
            "- Re-run after fixing the local launch configuration.",
            *common_tail,
        ]
    return [
        "- Re-run when the configured live executor is reachable, or continue manually from the retrieved context.",
        *common_tail,
    ]


def _run_detached_child(state_json_path: Path, retrieval_json_path: Path, result_json_path: Path) -> int:
    state = TaskState.from_dict(json.loads(state_json_path.read_text(encoding="utf-8")))
    retrieval_payload = json.loads(retrieval_json_path.read_text(encoding="utf-8"))
    retrieval_items = [RetrievalItem(**item) for item in retrieval_payload]
    result = run_executor_inline(state, retrieval_items)
    result_json_path.write_text(json.dumps(result.to_dict(), indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog="python -m swallow.executor")
    parser.add_argument("--detached-child", action="store_true")
    parser.add_argument("--state-json")
    parser.add_argument("--retrieval-json")
    parser.add_argument("--result-json")
    args = parser.parse_args()
    if not args.detached_child:
        parser.error("Unsupported executor entrypoint invocation.")
    raise SystemExit(
        _run_detached_child(
            Path(args.state_json),
            Path(args.retrieval_json),
            Path(args.result_json),
        )
    )
