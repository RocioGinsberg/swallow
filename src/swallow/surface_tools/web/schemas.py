from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from swallow.application.commands.knowledge import StagedCandidate
from swallow.application.commands.proposals import ProposalApplyCommandResult, ProposalReviewCommandResult
from swallow.application.commands.tasks import (
    TaskAcknowledgeCommandResult,
    TaskRecoveryCommandResult,
    TaskRunCommandResult,
)
from swallow.orchestration.models import TaskState


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


class ProposalReviewRequest(WebRequestModel):
    bundle_path: str = Field(min_length=1)
    decision: Literal["approved", "rejected", "deferred"]
    proposal_ids: list[str] = Field(default_factory=list)
    note: str = ""
    reviewer: str = Field(default="swl_cli", min_length=1)


class ProposalApplyRequest(WebRequestModel):
    review_path: str = Field(min_length=1)
    proposal_id: str | None = None


class WebResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskResponse(WebResponseModel):
    task_id: str
    status: str
    phase: str
    title: str
    goal: str
    executor_name: str
    route_name: str
    attempt_id: str
    attempt_number: int

    @classmethod
    def from_state(cls, state: TaskState) -> "TaskResponse":
        return cls(
            task_id=state.task_id,
            status=state.status,
            phase=state.phase,
            title=state.title,
            goal=state.goal,
            executor_name=state.executor_name,
            route_name=state.route_name,
            attempt_id=state.current_attempt_id,
            attempt_number=state.current_attempt_number,
        )


class TaskEnvelopeData(WebResponseModel):
    task: TaskResponse


class TaskRecoveryEnvelopeData(WebResponseModel):
    task: TaskResponse
    previous_task: TaskResponse


class TaskEnvelope(WebResponseModel):
    ok: Literal[True] = True
    data: TaskEnvelopeData

    @classmethod
    def from_state(cls, state: TaskState) -> "TaskEnvelope":
        return cls(data=TaskEnvelopeData(task=TaskResponse.from_state(state)))

    @classmethod
    def from_run_result(cls, result: TaskRunCommandResult) -> "TaskEnvelope":
        return cls.from_state(result.state)

    @classmethod
    def from_acknowledge_result(cls, result: TaskAcknowledgeCommandResult) -> "TaskEnvelope":
        return cls.from_state(result.state)


class TaskRecoveryEnvelope(WebResponseModel):
    ok: Literal[True] = True
    data: TaskRecoveryEnvelopeData

    @classmethod
    def from_result(cls, result: TaskRecoveryCommandResult) -> "TaskRecoveryEnvelope":
        return cls(
            data=TaskRecoveryEnvelopeData(
                task=TaskResponse.from_state(result.run_state or result.state),
                previous_task=TaskResponse.from_state(result.state),
            )
        )


class CandidateEnvelopeData(WebResponseModel):
    candidate: dict[str, Any]


class StagePromoteEnvelopeData(WebResponseModel):
    candidate: dict[str, Any]
    notices: list[dict[str, str]]


class CandidateEnvelope(WebResponseModel):
    ok: Literal[True] = True
    data: CandidateEnvelopeData

    @classmethod
    def from_candidate(cls, candidate: StagedCandidate) -> "CandidateEnvelope":
        return cls(data=CandidateEnvelopeData(candidate=candidate.to_dict()))


class StagePromoteEnvelope(WebResponseModel):
    ok: Literal[True] = True
    data: StagePromoteEnvelopeData

    @classmethod
    def from_result(cls, result: Any) -> "StagePromoteEnvelope":
        return cls(
            data=StagePromoteEnvelopeData(
                candidate=result.candidate.to_dict(),
                notices=list(result.notices),
            )
        )


class ProposalReviewEnvelopeData(WebResponseModel):
    review_record: dict[str, Any]
    record_path: str


class ProposalApplyEnvelopeData(WebResponseModel):
    application_record: dict[str, Any]
    record_path: str
    proposal_id: str


class ProposalReviewEnvelope(WebResponseModel):
    ok: Literal[True] = True
    data: ProposalReviewEnvelopeData

    @classmethod
    def from_result(cls, result: ProposalReviewCommandResult, base_dir: Path) -> "ProposalReviewEnvelope":
        return cls(
            data=ProposalReviewEnvelopeData(
                review_record=result.review_record.to_dict(),
                record_path=_relative_or_absolute(base_dir, result.record_path),
            )
        )


class ProposalApplyEnvelope(WebResponseModel):
    ok: Literal[True] = True
    data: ProposalApplyEnvelopeData

    @classmethod
    def from_result(cls, result: ProposalApplyCommandResult, base_dir: Path) -> "ProposalApplyEnvelope":
        return cls(
            data=ProposalApplyEnvelopeData(
                application_record=result.application_record.to_dict(),
                record_path=_relative_or_absolute(base_dir, result.record_path),
                proposal_id=result.proposal_id,
            )
        )


def _relative_or_absolute(base_dir: Path, path: Path) -> str:
    try:
        return path.relative_to(base_dir).as_posix()
    except ValueError:
        return path.as_posix()
