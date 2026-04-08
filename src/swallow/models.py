from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


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


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


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
    executor_name: str = "codex"
    route_mode: str = "auto"
    route_name: str = "local-codex"
    route_backend: str = "local_cli"
    route_execution_site: str = "local"
    route_remote_capable: bool = False
    route_transport_kind: str = "local_process"
    route_model_hint: str = "codex"
    route_reason: str = "Default local Codex route."
    route_capabilities: dict[str, Any] = field(default_factory=dict)
    executor_status: str = "pending"
    artifact_paths: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskState":
        return cls(**data)


@dataclass(slots=True)
class Event:
    task_id: str
    event_type: str
    message: str
    created_at: str = field(default_factory=utc_now)
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RetrievalRequest:
    query: str
    source_types: list[str] = field(default_factory=lambda: ["repo", "notes"])
    context_layers: list[str] = field(default_factory=lambda: ["workspace", "task"])
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
class ExecutorResult:
    executor_name: str
    status: str
    message: str
    output: str = ""
    prompt: str = ""
    failure_kind: str = ""
    stdout: str = ""
    stderr: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
class RouteSpec:
    name: str
    executor_name: str
    backend_kind: str
    model_hint: str
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

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["capabilities"] = self.capabilities.to_dict()
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
