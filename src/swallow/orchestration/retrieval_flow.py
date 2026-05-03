from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Callable

from swallow._io_helpers import read_json_strict
from swallow.knowledge_retrieval.knowledge_plane import (
    build_retrieval_request,
    retrieve_knowledge_context as retrieve_context,
    summarize_reused_knowledge,
)
from swallow.orchestration.models import (
    EVENT_RETRIEVAL_COMPLETED,
    Event,
    RetrievalItem,
    RetrievalRequest,
    TaskState,
    infer_task_family,
)
from swallow.orchestration.task_semantics import normalize_retrieval_source_types
from swallow.surface_tools.paths import retrieval_path
from swallow.truth_governance.store import append_event, save_retrieval


_RETRIEVAL_SOURCE_POLICY: dict[tuple[str, str], tuple[str, ...]] = {
    ("autonomous_cli_coding", "*"): ("knowledge",),
    ("api", "*"): ("knowledge", "notes"),
    ("legacy_local_fallback", "*"): ("repo", "notes", "knowledge"),
    ("*", "*"): ("knowledge", "notes"),
}


def load_previous_retrieval_items(base_dir: Path, task_id: str) -> list[RetrievalItem] | None:
    retrieval_file = retrieval_path(base_dir, task_id)
    if not retrieval_file.exists():
        return None
    try:
        payload = read_json_strict(retrieval_file)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, list):
        return None
    items: list[RetrievalItem] = []
    try:
        for entry in payload:
            if not isinstance(entry, dict):
                return None
            items.append(RetrievalItem(**entry))
    except TypeError:
        return None
    return items


def _retrieval_policy_family(state: TaskState) -> str:
    capabilities = state.route_capabilities if isinstance(state.route_capabilities, dict) else {}
    executor_family = str(state.route_executor_family or "").strip().lower()
    taxonomy_role = str(state.route_taxonomy_role or "").strip().lower()
    execution_kind = str(capabilities.get("execution_kind", "")).strip().lower()
    supports_tool_loop = capabilities.get("supports_tool_loop") is True
    deterministic = capabilities.get("deterministic") is True

    if executor_family == "cli" and supports_tool_loop and execution_kind == "code_execution":
        if taxonomy_role in {"", "general-executor"}:
            return "autonomous_cli_coding"
    if executor_family == "api":
        return "api"
    if executor_family == "cli" and deterministic and not supports_tool_loop:
        return "legacy_local_fallback"
    return executor_family or "*"


def _select_source_types(route_policy_family: str, task_family: str) -> list[str]:
    normalized_task_family = str(task_family or "").strip().lower() or "*"
    for policy_key in (
        (route_policy_family, normalized_task_family),
        (route_policy_family, "*"),
        ("*", "*"),
    ):
        source_types = _RETRIEVAL_SOURCE_POLICY.get(policy_key)
        if source_types is not None:
            return list(source_types)
    return ["knowledge", "notes"]


def build_task_retrieval_request(state: TaskState) -> RetrievalRequest:
    semantics = state.task_semantics if isinstance(state.task_semantics, dict) else {}
    explicit_source_types = normalize_retrieval_source_types(semantics.get("retrieval_source_types"))
    route_policy_family = _retrieval_policy_family(state)
    task_family = infer_task_family(state)
    return build_retrieval_request(
        query=f"{state.title} {state.goal}".strip(),
        source_types=explicit_source_types or _select_source_types(route_policy_family, task_family),
        context_layers=["workspace", "task"],
        current_task_id=state.task_id,
        limit=8,
        strategy="system_baseline",
    )


def run_retrieval(
    base_dir: Path,
    state: TaskState,
    request: RetrievalRequest,
    *,
    retrieve_context_fn: Callable[..., list[RetrievalItem]] = retrieve_context,
) -> list[RetrievalItem]:
    retrieval_items = retrieve_context_fn(Path(state.workspace_root), request=request)
    reused_knowledge = summarize_reused_knowledge(retrieval_items)
    save_retrieval(base_dir, state.task_id, retrieval_items)
    append_event(
        base_dir,
        Event(
            task_id=state.task_id,
            event_type=EVENT_RETRIEVAL_COMPLETED,
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
                "reused_knowledge_count": reused_knowledge["count"],
                "reused_knowledge_current_task_count": reused_knowledge["current_task_count"],
                "reused_knowledge_cross_task_count": reused_knowledge["cross_task_count"],
                "reused_knowledge_references": reused_knowledge["references"],
            },
        ),
    )
    return retrieval_items


async def run_retrieval_async(
    base_dir: Path,
    state: TaskState,
    request: RetrievalRequest,
    *,
    retrieve_context_fn: Callable[..., list[RetrievalItem]] = retrieve_context,
) -> list[RetrievalItem]:
    return await asyncio.to_thread(run_retrieval, base_dir, state, request, retrieve_context_fn=retrieve_context_fn)
