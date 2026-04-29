from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

SYSTEM_ROLES: tuple[str, ...] = (
    "orchestrator",
    "general-executor",
    "specialist",
    "validator",
    "human-operator",
)

MEMORY_AUTHORITIES: tuple[str, ...] = (
    "stateless",
    "task-state",
    "task-memory",
    "staged-knowledge",
    "canonical-write-forbidden",
    "canonical-promotion",
)

MEMORY_AUTHORITY_SEMANTICS: dict[str, dict[str, object]] = {
    "stateless": {
        "description": "No cross-call memory authority beyond the explicit task inputs supplied for the current run.",
        "allowed_side_effects": (),
    },
    "task-state": {
        "description": "May read and write task truth and event truth within the current task lifecycle.",
        "allowed_side_effects": ("task_artifacts", "task_events", "task_state_updates"),
    },
    "task-memory": {
        "description": "May read and write local task memory artifacts such as summaries or reusable within-task notes.",
        "allowed_side_effects": ("task_artifacts", "resume_notes", "compressed_summaries"),
    },
    "staged-knowledge": {
        "description": "May generate or modify staged knowledge candidates that remain behind operator or reviewer gates.",
        "allowed_side_effects": ("task_artifacts", "staged_candidates", "ingestion_reports"),
    },
    "canonical-write-forbidden": {
        "description": "May not write to canonical knowledge truth, but may still emit proposals, reports, and audit artifacts.",
        "allowed_side_effects": ("task_artifacts", "reports", "audit_artifacts", "proposal_bundles"),
    },
    "canonical-promotion": {
        "description": "May promote staged knowledge into canonical truth and emit the accompanying audit trail.",
        "allowed_side_effects": ("task_artifacts", "change_logs", "canonical_records", "knowledge_decisions"),
    },
}
# memory_authority describes mutation scope over task/canonical knowledge surfaces.
# It does not redefine the basic ability to return an executor result to the orchestrator.

LIBRARIAN_SYSTEM_ROLE = "specialist"
LIBRARIAN_MEMORY_AUTHORITY = "canonical-promotion"
META_OPTIMIZER_SYSTEM_ROLE = "specialist"
META_OPTIMIZER_MEMORY_AUTHORITY = "canonical-write-forbidden"


@dataclass(slots=True)
class RouteCapabilities:
    execution_kind: str
    supports_tool_loop: bool
    filesystem_access: str
    network_access: str
    deterministic: bool
    resumable: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def summary(self) -> str:
        return ", ".join(
            [
                f"execution_kind={self.execution_kind}",
                f"tool_loop={'yes' if self.supports_tool_loop else 'no'}",
                f"filesystem_access={self.filesystem_access}",
                f"network_access={self.network_access}",
                f"deterministic={'yes' if self.deterministic else 'no'}",
                f"resumable={'yes' if self.resumable else 'no'}",
            ]
        )


@dataclass(slots=True)
class DialectSpec:
    name: str
    description: str
    supported_model_hints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass(slots=True)
class CapabilityManifest:
    profile_refs: list[str] = field(default_factory=list)
    workflow_refs: list[str] = field(default_factory=list)
    validator_refs: list[str] = field(default_factory=list)
    skill_refs: list[str] = field(default_factory=list)
    tool_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def has_entries(self) -> bool:
        return any(
            [
                self.profile_refs,
                self.workflow_refs,
                self.validator_refs,
                self.skill_refs,
                self.tool_refs,
            ]
        )


@dataclass(slots=True)
class CapabilityAssembly:
    requested: dict[str, Any] = field(default_factory=dict)
    effective: dict[str, Any] = field(default_factory=dict)
    assembly_status: str = "assembled"
    resolver: str = "local_baseline"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TaxonomyProfile:
    system_role: str
    memory_authority: str

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.system_role not in SYSTEM_ROLES:
            raise ValueError(
                f"Invalid system_role: {self.system_role}. Expected one of: {', '.join(SYSTEM_ROLES)}"
            )
        if self.memory_authority not in MEMORY_AUTHORITIES:
            raise ValueError(
                "Invalid memory_authority: "
                f"{self.memory_authority}. Expected one of: {', '.join(MEMORY_AUTHORITIES)}"
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_librarian_taxonomy_profile() -> TaxonomyProfile:
    return TaxonomyProfile(
        system_role=LIBRARIAN_SYSTEM_ROLE,
        memory_authority=LIBRARIAN_MEMORY_AUTHORITY,
    )


def build_meta_optimizer_taxonomy_profile() -> TaxonomyProfile:
    return TaxonomyProfile(
        system_role=META_OPTIMIZER_SYSTEM_ROLE,
        memory_authority=META_OPTIMIZER_MEMORY_AUTHORITY,
    )


def describe_memory_authority(memory_authority: str) -> str:
    normalized = str(memory_authority).strip()
    semantics = MEMORY_AUTHORITY_SEMANTICS.get(normalized)
    if semantics is None:
        raise ValueError(
            "Invalid memory_authority: "
            f"{memory_authority}. Expected one of: {', '.join(MEMORY_AUTHORITIES)}"
        )
    return str(semantics["description"])


def allowed_memory_authority_side_effects(memory_authority: str) -> tuple[str, ...]:
    normalized = str(memory_authority).strip()
    semantics = MEMORY_AUTHORITY_SEMANTICS.get(normalized)
    if semantics is None:
        raise ValueError(
            "Invalid memory_authority: "
            f"{memory_authority}. Expected one of: {', '.join(MEMORY_AUTHORITIES)}"
        )
    return tuple(str(item) for item in semantics["allowed_side_effects"])


@dataclass(slots=True)
class TaskSemantics:
    title: str
    goal: str
    constraints: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    priority_hints: list[str] = field(default_factory=list)
    next_action_proposals: list[str] = field(default_factory=list)
    source_kind: str = "operator_entry"
    source_ref: str = ""
    complexity_hint: str = ""
    retrieval_source_types: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class HandoffContractSchema:
    """Unified handoff vocabulary across orchestration, retrieval, and interaction design docs.

    Field mapping:
    - orchestration handoff note: Goal / Done / Next_Steps / Context_Pointers
    - knowledge intake extraction: Goals / Constraints / Context
    - interaction task object: Goal / Constraints / Context Ref
    """

    goal: str
    constraints: list[str] = field(default_factory=list)
    done: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    context_pointers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DispatchVerdict:
    action: str
    reason: str
    blocking_detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


REMOTE_HANDOFF_REQUIRED_STRING_FIELDS = {
    "contract_kind",
    "contract_status",
    "handoff_boundary",
    "contract_reason",
    "execution_site",
    "execution_site_contract_kind",
    "execution_site_contract_status",
    "transport_kind",
    "transport_truth",
    "ownership_required",
    "ownership_truth",
    "dispatch_readiness",
    "dispatch_truth",
    "next_owner_kind",
    "next_owner_ref",
    "recommended_next_action",
    "goal",
}
REMOTE_HANDOFF_OPTIONAL_STRING_FIELDS = {
    "blocking_reason",
}
REMOTE_HANDOFF_REQUIRED_BOOL_FIELDS = {
    "remote_candidate",
    "remote_capable_intent",
    "operator_ack_required",
}
REMOTE_HANDOFF_REQUIRED_LIST_FIELDS = {
    "constraints",
    "done",
    "next_steps",
    "context_pointers",
}


def validate_remote_handoff_contract_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field_name in sorted(REMOTE_HANDOFF_REQUIRED_STRING_FIELDS):
        value = payload.get(field_name)
        if not isinstance(value, str) or not value:
            errors.append(f"{field_name} must be a non-empty string")
    for field_name in sorted(REMOTE_HANDOFF_OPTIONAL_STRING_FIELDS):
        if not isinstance(payload.get(field_name), str):
            errors.append(f"{field_name} must be a string")
    for field_name in sorted(REMOTE_HANDOFF_REQUIRED_BOOL_FIELDS):
        if not isinstance(payload.get(field_name), bool):
            errors.append(f"{field_name} must be a boolean")
    for field_name in sorted(REMOTE_HANDOFF_REQUIRED_LIST_FIELDS):
        value = payload.get(field_name)
        if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
            errors.append(f"{field_name} must be a list of non-empty strings")
    return errors


def evaluate_dispatch_verdict(contract: dict[str, Any]) -> DispatchVerdict:
    if not bool(contract.get("remote_candidate", False)):
        return DispatchVerdict(
            action="local",
            reason="handoff contract stays within the local execution baseline",
        )

    validation_errors = validate_remote_handoff_contract_payload(contract)
    if validation_errors:
        detail = "; ".join(validation_errors)
        return DispatchVerdict(
            action="blocked",
            reason="remote handoff contract is invalid",
            blocking_detail=detail,
        )

    if bool(contract.get("operator_ack_required", False)):
        return DispatchVerdict(
            action="blocked",
            reason="remote handoff contract still requires operator acknowledgment",
            blocking_detail=str(contract.get("recommended_next_action", "")).strip()
            or "Review the remote handoff contract before dispatch.",
        )

    return DispatchVerdict(
        action="mock_remote",
        reason="remote handoff contract is valid and no operator acknowledgment is pending",
    )


@dataclass(slots=True)
class KnowledgeObject:
    object_id: str
    text: str
    stage: str = "raw"
    source_kind: str = "operator_capture"
    source_ref: str = ""
    task_linked: bool = True
    captured_at: str = field(default_factory=utc_now)
    evidence_status: str = "unbacked"
    artifact_ref: str = ""
    retrieval_eligible: bool = False
    knowledge_reuse_scope: str = "task_only"
    canonicalization_intent: str = "none"
    store_type: str = "evidence"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KnowledgeObject":
        return cls(**data)


@dataclass(slots=True)
class WikiEntry(KnowledgeObject):
    promoted_by: str = ""
    promoted_at: str = ""
    change_log_ref: str = ""
    source_evidence_ids: list[str] = field(default_factory=list)
    store_type: str = "wiki"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WikiEntry":
        return cls(**data)


@dataclass(slots=True)
class TaskState:
    task_id: str
    title: str
    goal: str
    workspace_root: str
    status: str = "created"
    phase: str = "intake"
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    retrieval_count: int = 0
    executor_name: str = "aider"
    input_context: dict[str, Any] = field(default_factory=dict)
    task_semantics: dict[str, Any] = field(default_factory=dict)
    knowledge_objects: list[dict[str, Any]] = field(default_factory=list)
    capability_manifest: dict[str, Any] = field(default_factory=dict)
    capability_assembly: dict[str, Any] = field(default_factory=dict)
    route_mode: str = "auto"
    route_name: str = "local-aider"
    route_backend: str = "local_cli"
    route_executor_family: str = "cli"
    route_execution_site: str = "local"
    route_remote_capable: bool = False
    route_transport_kind: str = "local_process"
    route_taxonomy_role: str = ""
    route_taxonomy_memory_authority: str = ""
    route_model_hint: str = "aider"
    route_dialect: str = "plain_text"
    route_reason: str = "Default local Aider route."
    route_is_fallback: bool = False
    route_capabilities: dict[str, Any] = field(default_factory=dict)
    fallback_route_chain: tuple[str, ...] = ()
    topology_route_name: str = "local-aider"
    topology_executor_family: str = "cli"
    topology_execution_site: str = "local"
    topology_transport_kind: str = "local_process"
    topology_remote_capable_intent: bool = False
    topology_dispatch_status: str = "not_requested"
    execution_site_contract_kind: str = "local_inline"
    execution_site_boundary: str = "same_process"
    execution_site_contract_status: str = "active"
    execution_site_handoff_required: bool = False
    execution_site_contract_reason: str = "Current baseline executes inline on the local machine."
    run_attempt_count: int = 0
    current_attempt_id: str = ""
    current_attempt_number: int = 0
    current_attempt_owner_kind: str = "local_orchestrator"
    current_attempt_owner_ref: str = "swl_cli"
    current_attempt_ownership_status: str = "unassigned"
    current_attempt_owner_assigned_at: str = ""
    current_attempt_transfer_reason: str = ""
    dispatch_requested_at: str = ""
    dispatch_started_at: str = ""
    execution_lifecycle: str = "idle"
    executor_status: str = "pending"
    execution_phase: str = "pending"
    last_phase_checkpoint_at: str = ""
    grounding_refs: list[str] = field(default_factory=list)
    grounding_locked: bool = False
    review_feedback_markdown: str = ""
    review_feedback_ref: str = ""
    artifact_paths: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskState":
        normalized = dict(data)
        fallback_route_chain = normalized.get("fallback_route_chain", ())
        if isinstance(fallback_route_chain, (list, tuple)):
            normalized["fallback_route_chain"] = tuple(str(item) for item in fallback_route_chain)
        elif fallback_route_chain in {"", None}:
            normalized["fallback_route_chain"] = ()
        else:
            normalized["fallback_route_chain"] = (str(fallback_route_chain),)
        return cls(**normalized)


@dataclass(frozen=True, slots=True)
class SynthesisParticipant:
    participant_id: str
    role_prompt: str
    route_hint: str | None = None


@dataclass(frozen=True, slots=True)
class SynthesisConfig:
    config_id: str
    participants: tuple[SynthesisParticipant, ...]
    rounds: int
    arbiter: SynthesisParticipant
    arbiter_prompt_extra: str | None = None


@dataclass(slots=True)
class Event:
    task_id: str
    event_type: str
    message: str
    created_at: str = field(default_factory=utc_now)
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


EVENT_RETRIEVAL_COMPLETED = "retrieval.completed"
EVENT_EXECUTOR_COMPLETED = "executor.completed"
EVENT_EXECUTOR_FAILED = "executor.failed"
EVENT_TASK_EXECUTION_FALLBACK = "task.execution_fallback"


@dataclass(slots=True)
class TelemetryFields:
    task_family: str
    logical_model: str
    physical_route: str
    latency_ms: int
    degraded: bool
    token_cost: float = 0.0
    error_code: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OptimizationProposal:
    proposal_type: str
    severity: str
    route_name: str | None
    description: str
    suggested_action: str
    suggested_weight: float | None = None
    task_family: str | None = None
    suggested_task_family_score: float | None = None
    mark_task_family_unsupported: bool = False
    proposal_id: str = ""
    priority: str = ""
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OptimizationProposal":
        raw_weight = data.get("suggested_weight")
        suggested_weight: float | None
        if raw_weight in {"", None}:
            suggested_weight = None
        else:
            try:
                suggested_weight = float(raw_weight)
            except (TypeError, ValueError):
                suggested_weight = None
        raw_task_family_score = data.get("suggested_task_family_score")
        suggested_task_family_score: float | None
        if raw_task_family_score in {"", None}:
            suggested_task_family_score = None
        else:
            try:
                suggested_task_family_score = max(float(raw_task_family_score), 0.0)
            except (TypeError, ValueError):
                suggested_task_family_score = None
        route_name = data.get("route_name")
        normalized_route_name = None if route_name in {"", None} else str(route_name)
        task_family = data.get("task_family")
        normalized_task_family = None if task_family in {"", None} else str(task_family).strip().lower()
        mark_task_family_unsupported = data.get("mark_task_family_unsupported", False)
        if not isinstance(mark_task_family_unsupported, bool):
            mark_task_family_unsupported = str(mark_task_family_unsupported).strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
        return cls(
            proposal_type=str(data.get("proposal_type", "")).strip(),
            severity=str(data.get("severity", "")).strip(),
            route_name=normalized_route_name,
            description=str(data.get("description", "")).strip(),
            suggested_action=str(data.get("suggested_action", "")).strip(),
            suggested_weight=suggested_weight,
            task_family=normalized_task_family,
            suggested_task_family_score=suggested_task_family_score,
            mark_task_family_unsupported=mark_task_family_unsupported,
            proposal_id=str(data.get("proposal_id", "")).strip(),
            priority=str(data.get("priority", "")).strip(),
            rationale=str(data.get("rationale", "")).strip(),
        )


@dataclass(slots=True)
class AuditTriggerPolicy:
    enabled: bool = False
    trigger_on_degraded: bool = True
    trigger_on_cost_above: float | None = None
    auditor_route: str = "http-claude"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuditTriggerPolicy":
        enabled = data.get("enabled", False)
        if not isinstance(enabled, bool):
            enabled = str(enabled).strip().lower() in {"1", "true", "yes", "on"}

        trigger_on_degraded = data.get("trigger_on_degraded", True)
        if not isinstance(trigger_on_degraded, bool):
            trigger_on_degraded = str(trigger_on_degraded).strip().lower() in {"1", "true", "yes", "on"}

        raw_cost_threshold = data.get("trigger_on_cost_above")
        trigger_on_cost_above: float | None
        if raw_cost_threshold in {"", None}:
            trigger_on_cost_above = None
        else:
            try:
                trigger_on_cost_above = max(float(raw_cost_threshold), 0.0)
            except (TypeError, ValueError):
                trigger_on_cost_above = None

        auditor_route = str(data.get("auditor_route", "http-claude")).strip() or "http-claude"
        return cls(
            enabled=enabled,
            trigger_on_degraded=trigger_on_degraded,
            trigger_on_cost_above=trigger_on_cost_above,
            auditor_route=auditor_route,
        )


@dataclass(slots=True)
class RetrievalRequest:
    query: str
    source_types: list[str] = field(default_factory=lambda: ["repo", "notes"])
    context_layers: list[str] = field(default_factory=lambda: ["workspace", "task"])
    current_task_id: str = ""
    limit: int = 8
    strategy: str = "system_baseline"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RetrievalItem:
    path: str
    source_type: str
    score: int
    preview: str
    chunk_id: str = "full-file"
    title: str = ""
    citation: str = ""
    matched_terms: list[str] = field(default_factory=list)
    score_breakdown: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def reference(self) -> str:
        return self.citation or self.path

    def display_title(self) -> str:
        return self.title or self.path

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TaskCard:
    card_id: str = field(default_factory=lambda: uuid4().hex[:12])
    goal: str = ""
    input_context: dict[str, Any] = field(default_factory=dict)
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    route_hint: str = ""
    executor_type: str = "cli"
    # Under veto, reviewer_routes[0] owns veto authority and later routes are advisory.
    reviewer_routes: list[str] = field(default_factory=list)
    consensus_policy: str = "majority"
    reviewer_timeout_seconds: int = 60
    token_cost_limit: float = 0.0
    constraints: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    subtask_index: int = 1
    parent_task_id: str = ""
    status: str = "planned"
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskCard":
        return cls(**data)


@dataclass(slots=True)
class ExecutorResult:
    executor_name: str
    status: str
    message: str
    output: str = ""
    prompt: str = ""
    dialect: str = "plain_text"
    failure_kind: str = ""
    latency_ms: int = 0
    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 0
    stdout: str = ""
    stderr: str = ""
    review_feedback: str = ""
    degraded: bool = False
    original_route_name: str = ""
    fallback_route_name: str = ""
    side_effects: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def infer_task_family(state: TaskState) -> str:
    semantics = state.task_semantics if isinstance(state.task_semantics, dict) else {}
    source_kind = str(semantics.get("source_kind", "")).strip().lower()
    if "planning" in source_kind:
        return "planning"
    if "review" in source_kind:
        return "review"
    if any(token in source_kind for token in ("extraction", "extract", "knowledge_capture", "capture")):
        return "extraction"
    if "retrieval" in source_kind:
        return "retrieval"
    return "execution"


def build_telemetry_fields(
    state: TaskState,
    *,
    latency_ms: int,
    degraded: bool,
    token_cost: float = 0.0,
    error_code: str = "",
) -> TelemetryFields:
    logical_model = str(state.route_model_hint or state.executor_name or "unknown").strip() or "unknown"
    physical_route = str(state.route_name or "pending").strip() or "pending"
    return TelemetryFields(
        task_family=infer_task_family(state),
        logical_model=logical_model,
        physical_route=physical_route,
        latency_ms=max(int(latency_ms or 0), 0),
        degraded=bool(degraded),
        token_cost=max(float(token_cost or 0.0), 0.0),
        error_code=str(error_code).strip(),
    )


@dataclass(slots=True)
class ValidationFinding:
    code: str
    level: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ValidationResult:
    status: str
    message: str
    findings: list[ValidationFinding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "findings": [finding.to_dict() for finding in self.findings],
        }


@dataclass(slots=True)
class RetryPolicyFinding:
    code: str
    level: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RetryPolicyResult:
    status: str
    message: str
    retryable: bool
    retry_decision: str
    max_attempts: int
    remaining_attempts: int
    checkpoint_required: bool
    recommended_action: str
    findings: list[RetryPolicyFinding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "retryable": self.retryable,
            "retry_decision": self.retry_decision,
            "max_attempts": self.max_attempts,
            "remaining_attempts": self.remaining_attempts,
            "checkpoint_required": self.checkpoint_required,
            "recommended_action": self.recommended_action,
            "findings": [finding.to_dict() for finding in self.findings],
        }


@dataclass(slots=True)
class StopPolicyFinding:
    code: str
    level: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class StopPolicyResult:
    status: str
    message: str
    stop_required: bool
    continue_allowed: bool
    stop_decision: str
    escalation_level: str
    checkpoint_kind: str
    recommended_action: str
    findings: list[StopPolicyFinding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "stop_required": self.stop_required,
            "continue_allowed": self.continue_allowed,
            "stop_decision": self.stop_decision,
            "escalation_level": self.escalation_level,
            "checkpoint_kind": self.checkpoint_kind,
            "recommended_action": self.recommended_action,
            "findings": [finding.to_dict() for finding in self.findings],
        }


@dataclass(slots=True)
class ExecutionBudgetPolicyFinding:
    code: str
    level: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExecutionBudgetPolicyResult:
    status: str
    message: str
    timeout_seconds: int
    max_attempts: int
    remaining_attempts: int
    budget_state: str
    timeout_state: str
    recommended_action: str
    current_token_cost: float = 0.0
    token_cost_limit: float = 0.0
    findings: list[ExecutionBudgetPolicyFinding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "timeout_seconds": self.timeout_seconds,
            "max_attempts": self.max_attempts,
            "remaining_attempts": self.remaining_attempts,
            "budget_state": self.budget_state,
            "timeout_state": self.timeout_state,
            "current_token_cost": self.current_token_cost,
            "token_cost_limit": self.token_cost_limit,
            "recommended_action": self.recommended_action,
            "findings": [finding.to_dict() for finding in self.findings],
        }


@dataclass(slots=True)
class CheckpointSnapshotFinding:
    code: str
    level: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CheckpointSnapshotResult:
    status: str
    message: str
    checkpoint_state: str
    checkpoint_kind: str
    handoff_status: str
    execution_phase: str
    last_phase_checkpoint_at: str
    recovery_semantics: str
    interruption_kind: str
    recommended_path: str
    recommended_reason: str
    resume_ready: bool
    retry_ready: bool
    review_ready: bool
    rerun_ready: bool
    monitor_needed: bool
    required_artifacts: list[str] = field(default_factory=list)
    findings: list[CheckpointSnapshotFinding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "checkpoint_state": self.checkpoint_state,
            "checkpoint_kind": self.checkpoint_kind,
            "handoff_status": self.handoff_status,
            "execution_phase": self.execution_phase,
            "last_phase_checkpoint_at": self.last_phase_checkpoint_at,
            "recovery_semantics": self.recovery_semantics,
            "interruption_kind": self.interruption_kind,
            "recommended_path": self.recommended_path,
            "recommended_reason": self.recommended_reason,
            "resume_ready": self.resume_ready,
            "retry_ready": self.retry_ready,
            "review_ready": self.review_ready,
            "rerun_ready": self.rerun_ready,
            "monitor_needed": self.monitor_needed,
            "required_artifacts": self.required_artifacts,
            "findings": [finding.to_dict() for finding in self.findings],
        }


@dataclass(slots=True)
class CompatibilityFinding:
    code: str
    level: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CompatibilityResult:
    status: str
    message: str
    findings: list[CompatibilityFinding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "findings": [finding.to_dict() for finding in self.findings],
        }


@dataclass(slots=True)
class ExecutionFitFinding:
    code: str
    level: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExecutionFitResult:
    status: str
    message: str
    findings: list[ExecutionFitFinding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "findings": [finding.to_dict() for finding in self.findings],
        }


@dataclass(slots=True)
class KnowledgePolicyFinding:
    code: str
    level: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class KnowledgePolicyResult:
    status: str
    message: str
    findings: list[KnowledgePolicyFinding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "findings": [finding.to_dict() for finding in self.findings],
        }


@dataclass(slots=True)
class RouteSpec:
    name: str
    executor_name: str
    backend_kind: str
    model_hint: str
    dialect_hint: str = ""
    fallback_route_name: str = ""
    quality_weight: float = 1.0
    task_family_scores: dict[str, float] = field(default_factory=dict)
    unsupported_task_types: list[str] = field(default_factory=list)
    executor_family: str = "cli"
    execution_site: str = "local"
    remote_capable: bool = False
    transport_kind: str = "local_process"
    capabilities: RouteCapabilities = field(
        default_factory=lambda: RouteCapabilities(
            execution_kind="unknown",
            supports_tool_loop=False,
            filesystem_access="none",
            network_access="none",
            deterministic=False,
            resumable=False,
        )
    )
    taxonomy: TaxonomyProfile = field(
        default_factory=lambda: TaxonomyProfile(
            system_role="general-executor",
            memory_authority="task-state",
        )
    )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["capabilities"] = self.capabilities.to_dict()
        payload["taxonomy"] = self.taxonomy.to_dict()
        payload["task_family_scores"] = {
            str(task_family): float(score)
            for task_family, score in sorted(self.task_family_scores.items())
        }
        payload["unsupported_task_types"] = sorted({str(item).strip() for item in self.unsupported_task_types if str(item).strip()})
        return payload


@dataclass(slots=True)
class RouteSelection:
    route: RouteSpec
    reason: str
    policy_inputs: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "route": self.route.to_dict(),
            "reason": self.reason,
            "policy_inputs": self.policy_inputs,
        }
