from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from swallow.provider_router.router import route_by_name
from swallow.surface_tools.consistency_audit import AuditTriggerPolicy, load_audit_trigger_policy
from swallow.truth_governance.governance import (
    OperatorToken,
    ProposalTarget,
    apply_proposal,
    register_mps_policy_proposal,
    register_policy_proposal,
)


def _unique_policy_proposal_id(prefix: str) -> str:
    return f"{prefix}:{time.time_ns():x}"


@dataclass(frozen=True)
class AuditPolicySetCommandResult:
    policy: AuditTriggerPolicy
    proposal_id: str


@dataclass(frozen=True)
class MpsPolicySetCommandResult:
    kind: str
    value: int
    proposal_id: str
    applied: bool


def set_audit_trigger_policy_command(
    base_dir: Path,
    *,
    enabled: bool | None = None,
    trigger_on_degraded: bool | None = None,
    trigger_on_cost_above: float | None = None,
    clear_trigger_on_cost_above: bool = False,
    auditor_route: str | None = None,
) -> AuditPolicySetCommandResult:
    policy = load_audit_trigger_policy(base_dir)
    if enabled is not None:
        policy.enabled = bool(enabled)
    if trigger_on_degraded is not None:
        policy.trigger_on_degraded = bool(trigger_on_degraded)
    if clear_trigger_on_cost_above:
        policy.trigger_on_cost_above = None
    elif trigger_on_cost_above is not None:
        if trigger_on_cost_above < 0:
            raise ValueError("--trigger-on-cost-above must be non-negative.")
        policy.trigger_on_cost_above = float(trigger_on_cost_above)
    if auditor_route is not None:
        normalized_auditor_route = auditor_route.strip()
        if not normalized_auditor_route:
            raise ValueError("--auditor-route must be a non-empty route name.")
        if route_by_name(normalized_auditor_route) is None:
            raise ValueError(f"Unknown auditor route: {normalized_auditor_route}")
        policy.auditor_route = normalized_auditor_route
    proposal_id = register_policy_proposal(
        base_dir=base_dir,
        proposal_id=_unique_policy_proposal_id("audit-trigger-policy"),
        audit_trigger_policy=policy,
    )
    apply_proposal(proposal_id, OperatorToken(source="cli"), ProposalTarget.POLICY)
    return AuditPolicySetCommandResult(policy=policy, proposal_id=proposal_id)


def set_mps_policy_command(base_dir: Path, *, kind: str, value: int) -> MpsPolicySetCommandResult:
    proposal_id = register_mps_policy_proposal(
        base_dir=base_dir,
        proposal_id=_unique_policy_proposal_id(f"mps-policy:{kind}"),
        kind=kind,
        value=int(value),
    )
    result = apply_proposal(proposal_id, OperatorToken(source="cli"), ProposalTarget.POLICY)
    return MpsPolicySetCommandResult(
        kind=kind,
        value=int(value),
        proposal_id=proposal_id,
        applied=bool(result.success),
    )
