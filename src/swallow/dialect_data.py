from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from .knowledge_objects import (
    summarize_canonicalization,
    summarize_knowledge_evidence,
    summarize_knowledge_reuse,
    summarize_knowledge_stages,
)
from .models import RetrievalItem, TaskState
from .retrieval import summarize_reused_knowledge


DEFAULT_EXECUTOR = "codex"
EXECUTOR_ALIASES = {
    "": DEFAULT_EXECUTOR,
    "codex": "codex",
    "cline": "cline",
    "http": "http",
    "mock": "mock",
    "mock-remote": "mock-remote",
    "mock_remote": "mock-remote",
    "note-only": "note-only",
    "note_only": "note-only",
    "local": "local",
    "local-summary": "local",
    "local_summary": "local",
}


@dataclass(slots=True)
class TaskPromptData:
    task_id: str
    title: str
    goal: str
    executor: str


@dataclass(slots=True)
class RoutePromptData:
    route_mode: str
    route_name: str
    route_backend: str
    route_executor_family: str
    route_execution_site: str
    route_remote_capable: bool
    route_transport_kind: str
    route_model_hint: str
    route_dialect: str
    route_capabilities: str


@dataclass(slots=True)
class SemanticsPromptData:
    source_kind: str
    source_ref: str
    constraints: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    priority_hints: list[str] = field(default_factory=list)
    next_action_proposals: list[str] = field(default_factory=list)


@dataclass(slots=True)
class KnowledgePromptData:
    count: int
    raw: int
    candidate: int
    verified: int
    canonical: int
    artifact_backed: int
    source_only: int
    unbacked: int
    retrieval_candidate: int
    canonicalization_review_ready: int
    canonicalization_promotion_ready: int
    canonicalization_blocked: int
    top_items: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ReusedKnowledgePromptData:
    count: int
    references: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PriorRetrievalPromptData:
    count: str
    top_references: str
    reused_knowledge_count: str
    reused_knowledge_current_task_count: str
    reused_knowledge_cross_task_count: str
    reused_knowledge_references: str
    grounding_artifact: str
    retrieval_record_path: str


@dataclass(slots=True)
class PromptData:
    task: TaskPromptData
    route: RoutePromptData
    semantics: SemanticsPromptData | None = None
    knowledge: KnowledgePromptData | None = None
    reused_knowledge: ReusedKnowledgePromptData | None = None
    previous_memory_artifacts: list[str] = field(default_factory=list)
    prior_retrieval: PriorRetrievalPromptData | None = None
    retrieval_entries: list[str] = field(default_factory=list)


def normalize_executor_name(raw_name: str | None) -> str:
    normalized = (raw_name or "").strip().lower()
    return EXECUTOR_ALIASES.get(normalized, normalized or DEFAULT_EXECUTOR)


def resolve_executor_name(state: TaskState) -> str:
    configured = normalize_executor_name(state.executor_name)
    legacy_mode = normalize_executor_name(os.environ.get("AIWF_EXECUTOR_MODE"))
    if configured != DEFAULT_EXECUTOR:
        return configured
    return legacy_mode


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


def load_prior_retrieval_snapshot(state: TaskState) -> PriorRetrievalPromptData | None:
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
    return PriorRetrievalPromptData(
        count=str(retrieval.get("count", 0)),
        top_references=", ".join(top_references) if top_references else "none",
        reused_knowledge_count=str(retrieval.get("reused_knowledge_count", 0)),
        reused_knowledge_current_task_count=str(retrieval.get("reused_knowledge_current_task_count", 0)),
        reused_knowledge_cross_task_count=str(retrieval.get("reused_knowledge_cross_task_count", 0)),
        reused_knowledge_references=", ".join(retrieval.get("reused_knowledge_references", [])) or "none",
        grounding_artifact=str(retrieval.get("grounding_artifact", "")),
        retrieval_record_path=str(retrieval.get("retrieval_record_path", "")),
    )


def collect_prompt_data(state: TaskState, retrieval_items: list[RetrievalItem]) -> PromptData:
    semantics = _collect_semantics_data(state)
    knowledge = _collect_knowledge_data(state)
    reused_knowledge = _collect_reused_knowledge_data(retrieval_items)
    previous_memory_artifacts = _collect_previous_memory_artifacts(state)
    prior_retrieval = load_prior_retrieval_snapshot(state)
    retrieval_entries = [
        f"[{item.source_type}] {item.reference()} title={item.display_title()}: {item.preview}"
        for item in retrieval_items
    ]
    return PromptData(
        task=TaskPromptData(
            task_id=state.task_id,
            title=state.title,
            goal=state.goal,
            executor=resolve_executor_name(state),
        ),
        route=RoutePromptData(
            route_mode=state.route_mode or "auto",
            route_name=state.route_name or "pending",
            route_backend=state.route_backend or "pending",
            route_executor_family=state.route_executor_family or "pending",
            route_execution_site=state.route_execution_site or "pending",
            route_remote_capable=state.route_remote_capable,
            route_transport_kind=state.route_transport_kind or "pending",
            route_model_hint=state.route_model_hint or "pending",
            route_dialect=state.route_dialect or "plain_text",
            route_capabilities=format_route_capabilities(state.route_capabilities),
        ),
        semantics=semantics,
        knowledge=knowledge,
        reused_knowledge=reused_knowledge,
        previous_memory_artifacts=previous_memory_artifacts,
        prior_retrieval=prior_retrieval,
        retrieval_entries=retrieval_entries,
    )


def _collect_semantics_data(state: TaskState) -> SemanticsPromptData | None:
    semantics = state.task_semantics or {}
    if not semantics:
        return None
    return SemanticsPromptData(
        source_kind=str(semantics.get("source_kind", "unknown")) or "unknown",
        source_ref=str(semantics.get("source_ref", "")).strip() or "none",
        constraints=_clean_string_list(semantics.get("constraints", [])),
        acceptance_criteria=_clean_string_list(semantics.get("acceptance_criteria", [])),
        priority_hints=_clean_string_list(semantics.get("priority_hints", [])),
        next_action_proposals=_clean_string_list(semantics.get("next_action_proposals", [])),
    )


def _collect_knowledge_data(state: TaskState) -> KnowledgePromptData | None:
    knowledge_objects = state.knowledge_objects or []
    if not knowledge_objects:
        return None
    stage_counts = summarize_knowledge_stages(knowledge_objects)
    evidence_counts = summarize_knowledge_evidence(knowledge_objects)
    reuse_counts = summarize_knowledge_reuse(knowledge_objects)
    canonicalization_counts = summarize_canonicalization(knowledge_objects)
    top_items = [
        str(item.get("text", "")).strip()
        for item in knowledge_objects[:3]
        if str(item.get("text", "")).strip()
    ]
    return KnowledgePromptData(
        count=len(knowledge_objects),
        raw=stage_counts.get("raw", 0),
        candidate=stage_counts.get("candidate", 0),
        verified=stage_counts.get("verified", 0),
        canonical=stage_counts.get("canonical", 0),
        artifact_backed=evidence_counts.get("artifact_backed", 0),
        source_only=evidence_counts.get("source_only", 0),
        unbacked=evidence_counts.get("unbacked", 0),
        retrieval_candidate=reuse_counts.get("retrieval_candidate", 0),
        canonicalization_review_ready=canonicalization_counts.get("review_ready", 0),
        canonicalization_promotion_ready=canonicalization_counts.get("promotion_ready", 0),
        canonicalization_blocked=canonicalization_counts.get("blocked_stage", 0)
        + canonicalization_counts.get("blocked_evidence", 0),
        top_items=top_items,
    )


def _collect_reused_knowledge_data(retrieval_items: list[RetrievalItem]) -> ReusedKnowledgePromptData | None:
    reused_knowledge = summarize_reused_knowledge(retrieval_items)
    if reused_knowledge["count"] <= 0:
        return None
    return ReusedKnowledgePromptData(
        count=reused_knowledge["count"],
        references=[str(reference).strip() for reference in reused_knowledge["references"] if str(reference).strip()],
    )


def _collect_previous_memory_artifacts(state: TaskState) -> list[str]:
    candidate_paths = [
        state.artifact_paths.get("task_memory", ""),
        state.artifact_paths.get("source_grounding", ""),
        state.artifact_paths.get("summary", ""),
        state.artifact_paths.get("resume_note", ""),
    ]
    return [path for path in candidate_paths if path]


def _clean_string_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item).strip()]
