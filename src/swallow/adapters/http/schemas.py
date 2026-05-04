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
from swallow.application.commands.wiki import EvidenceRefreshCommandResult
from swallow.application.services.wiki_jobs import WikiJobRecord
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
    confirmed_notice_types: list[Literal["supersede", "conflict"]] = Field(default_factory=list)
    confirmed_supersede_target_ids: list[str] = Field(default_factory=list)
    confirmed_conflict_flags: list[str] = Field(default_factory=list)


class ProposalReviewRequest(WebRequestModel):
    bundle_path: str = Field(min_length=1)
    decision: Literal["approved", "rejected", "deferred"]
    proposal_ids: list[str] = Field(default_factory=list)
    note: str = ""
    reviewer: str = Field(default="swl_cli", min_length=1)


class ProposalApplyRequest(WebRequestModel):
    review_path: str = Field(min_length=1)
    proposal_id: str | None = None


class WikiDraftRequest(WebRequestModel):
    task_id: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    source_refs: list[str] = Field(min_length=1)
    model: str = ""


class WikiRefineRequest(WebRequestModel):
    task_id: str = Field(min_length=1)
    mode: Literal["supersede", "refines"]
    target_object_id: str = Field(min_length=1)
    source_refs: list[str] = Field(min_length=1)
    model: str = ""


class WikiRefreshEvidenceRequest(WebRequestModel):
    task_id: str = Field(min_length=1)
    target_object_id: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    parser_version: str = ""
    span: str = ""
    heading_path: str = ""


class WebResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KnowledgeSummary(WebResponseModel):
    object_id: str
    object_kind: str
    status: str
    text_preview: str
    source_refs: list[str] = Field(default_factory=list)
    task_id: str = ""
    canonical_id: str = ""
    candidate_id: str = ""
    topic: str = ""
    updated_at: str = ""


class KnowledgeListEnvelopeData(WebResponseModel):
    count: int
    items: list[KnowledgeSummary]
    filters: dict[str, Any]


class KnowledgeListEnvelope(WebResponseModel):
    ok: Literal[True] = True
    data: KnowledgeListEnvelopeData

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "KnowledgeListEnvelope":
        return cls(data=KnowledgeListEnvelopeData(**payload))


class KnowledgeDetail(KnowledgeSummary):
    text: str = ""
    source_pack: list[dict[str, Any]] = Field(default_factory=list)
    rationale: str = ""
    relation_metadata: list[dict[str, Any]] = Field(default_factory=list)
    conflict_flag: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeDetailEnvelopeData(WebResponseModel):
    detail: KnowledgeDetail


class KnowledgeDetailEnvelope(WebResponseModel):
    ok: Literal[True] = True
    data: KnowledgeDetailEnvelopeData

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "KnowledgeDetailEnvelope":
        return cls(data=KnowledgeDetailEnvelopeData(**payload))


class KnowledgeRelationEdge(WebResponseModel):
    relation_id: str = ""
    relation_type: str
    direction: str
    source_object_id: str = ""
    target_object_id: str = ""
    counterparty_object_id: str = ""
    confidence: float = 1.0
    context: str = ""
    created_at: str = ""
    created_by: str = ""
    edge_source: str
    target_ref: str = ""
    source_ref: str = ""


class KnowledgeRelationGroups(WebResponseModel):
    supersedes: list[KnowledgeRelationEdge] = Field(default_factory=list)
    refines: list[KnowledgeRelationEdge] = Field(default_factory=list)
    contradicts: list[KnowledgeRelationEdge] = Field(default_factory=list)
    refers_to: list[KnowledgeRelationEdge] = Field(default_factory=list)
    derived_from: list[KnowledgeRelationEdge] = Field(default_factory=list)
    legacy: list[KnowledgeRelationEdge] = Field(default_factory=list)


class KnowledgeRelationsEnvelopeData(WebResponseModel):
    object_id: str
    object_kind: str
    count: int
    groups: KnowledgeRelationGroups


class KnowledgeRelationsEnvelope(WebResponseModel):
    ok: Literal[True] = True
    data: KnowledgeRelationsEnvelopeData

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "KnowledgeRelationsEnvelope":
        return cls(data=KnowledgeRelationsEnvelopeData(**payload))


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


class WikiJob(WebResponseModel):
    job_id: str
    task_id: str
    action: str
    status: str
    candidate_id: str = ""
    prompt_artifact: str = ""
    result_artifact: str = ""
    error: str = ""
    created_at: str = ""
    updated_at: str = ""
    topic: str = ""
    mode: str = ""
    target_object_id: str = ""
    source_refs: list[str] = Field(default_factory=list)
    model: str = ""

    @classmethod
    def from_record(cls, record: WikiJobRecord) -> "WikiJob":
        return cls(**_wiki_job_payload(record))


class WikiJobEnvelopeData(WebResponseModel):
    job: WikiJob


class WikiJobEnvelope(WebResponseModel):
    ok: Literal[True] = True
    data: WikiJobEnvelopeData

    @classmethod
    def from_record(cls, record: WikiJobRecord) -> "WikiJobEnvelope":
        return cls(data=WikiJobEnvelopeData(job=WikiJob.from_record(record)))


class WikiJobResultEnvelopeData(WebResponseModel):
    job: WikiJob
    result_ready: StrictBool
    candidate: dict[str, Any] = Field(default_factory=dict)
    prompt_pack: dict[str, Any] = Field(default_factory=dict)
    compiler_result: dict[str, Any] = Field(default_factory=dict)
    source_pack: list[dict[str, Any]] = Field(default_factory=list)


class WikiJobResultEnvelope(WebResponseModel):
    ok: Literal[True] = True
    data: WikiJobResultEnvelopeData

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "WikiJobResultEnvelope":
        record = WikiJobRecord.from_dict(dict(payload.get("job", {})))
        return cls(
            data=WikiJobResultEnvelopeData(
                job=WikiJob.from_record(record),
                result_ready=bool(payload.get("result_ready", False)),
                candidate=dict(payload.get("candidate", {})),
                prompt_pack=dict(payload.get("prompt_pack", {})),
                compiler_result=dict(payload.get("compiler_result", {})),
                source_pack=[dict(item) for item in payload.get("source_pack", []) if isinstance(item, dict)],
            )
        )


class WikiEvidenceRefresh(WebResponseModel):
    task_id: str
    target_object_id: str
    source_ref: str
    parser_version: str
    content_hash: str
    span: str
    heading_path: str
    evidence_entry: dict[str, Any]

    @classmethod
    def from_result(cls, result: EvidenceRefreshCommandResult) -> "WikiEvidenceRefresh":
        return cls(
            task_id=result.task_id,
            target_object_id=result.target_object_id,
            source_ref=result.source_ref,
            parser_version=result.parser_version,
            content_hash=result.content_hash,
            span=result.span,
            heading_path=result.heading_path,
            evidence_entry=dict(result.evidence_entry),
        )


class WikiEvidenceRefreshEnvelopeData(WebResponseModel):
    refresh: WikiEvidenceRefresh


class WikiEvidenceRefreshEnvelope(WebResponseModel):
    ok: Literal[True] = True
    data: WikiEvidenceRefreshEnvelopeData

    @classmethod
    def from_result(cls, result: EvidenceRefreshCommandResult) -> "WikiEvidenceRefreshEnvelope":
        return cls(data=WikiEvidenceRefreshEnvelopeData(refresh=WikiEvidenceRefresh.from_result(result)))


def _wiki_job_payload(record: WikiJobRecord) -> dict[str, Any]:
    return {
        "job_id": record.job_id,
        "task_id": record.task_id,
        "action": record.action,
        "status": record.status,
        "candidate_id": record.candidate_id,
        "prompt_artifact": record.prompt_artifact,
        "result_artifact": record.result_artifact,
        "error": record.error,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "topic": record.topic,
        "mode": record.mode,
        "target_object_id": record.target_object_id,
        "source_refs": list(record.source_refs),
        "model": record.model,
    }


def _relative_or_absolute(base_dir: Path, path: Path) -> str:
    try:
        return path.relative_to(base_dir).as_posix()
    except ValueError:
        return path.as_posix()
