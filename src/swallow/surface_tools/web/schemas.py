from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool


class WebRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CreateTaskRequest(WebRequestModel):
    title: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    executor_name: str = Field(default="local", min_length=1)
    input_context: dict[str, Any] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    priority_hints: list[str] = Field(default_factory=list)
    next_action_proposals: list[str] = Field(default_factory=list)
    planning_source: str = Field(default="web", min_length=1)
    complexity_hint: str = ""
    knowledge_items: list[str] = Field(default_factory=list)
    knowledge_stage: str = Field(default="raw", min_length=1)
    knowledge_source: str = Field(default="operator", min_length=1)
    knowledge_artifact_refs: list[str] = Field(default_factory=list)
    knowledge_retrieval_eligible: StrictBool = False
    knowledge_canonicalization_intent: str = Field(default="none", min_length=1)
    capability_refs: list[str] = Field(default_factory=list)
    route_mode: str | None = None


class TaskActionRequest(WebRequestModel):
    executor_name: str | None = None
    capability_refs: list[str] = Field(default_factory=list)
    route_mode: str | None = None
    from_phase: str = Field(default="retrieval", min_length=1)


class StageDecisionRequest(WebRequestModel):
    note: str = ""
    refined_text: str = ""
    force: StrictBool = False


class ProposalReviewRequest(WebRequestModel):
    bundle_path: str = Field(min_length=1)
    decision: Literal["approved", "rejected", "deferred"]
    proposal_ids: list[str] = Field(default_factory=list)
    note: str = ""
    reviewer: str = Field(default="swl_cli", min_length=1)


class ProposalApplyRequest(WebRequestModel):
    review_path: str = Field(min_length=1)
    proposal_id: str | None = None
