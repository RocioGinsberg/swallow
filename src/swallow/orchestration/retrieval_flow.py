from __future__ import annotations

import json
from pathlib import Path

from swallow._io_helpers import read_json_strict
from swallow.knowledge_retrieval.retrieval import build_retrieval_request
from swallow.orchestration.models import (
    RetrievalItem,
    RetrievalRequest,
    TaskState,
    infer_task_family,
)
from swallow.orchestration.task_semantics import normalize_retrieval_source_types
from swallow.surface_tools.paths import retrieval_path


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
