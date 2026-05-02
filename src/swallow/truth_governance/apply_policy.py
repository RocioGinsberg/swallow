from __future__ import annotations

from swallow.truth_governance.governance_models import ApplyResult, OperatorToken, ProposalTarget
from swallow.truth_governance.proposal_registry import (
    is_mps_policy_proposal,
    require_mps_policy_proposal,
    require_policy_proposal,
)
from swallow.truth_governance.truth import PolicyRepo


def _apply_policy(proposal: object, _operator_token: OperatorToken, *, proposal_id: str) -> ApplyResult:
    if is_mps_policy_proposal(proposal):
        proposal = require_mps_policy_proposal(proposal)
        applied_write, policy_path = PolicyRepo()._apply_policy_change(
            base_dir=proposal.base_dir,
            mps_kind=proposal.kind,
            mps_value=proposal.value,
            proposal_id=proposal_id,
        )
        return ApplyResult(
            proposal_id=proposal_id,
            target=ProposalTarget.POLICY,
            success=True,
            detail=f"mps_policy_applied kind={proposal.kind} path={policy_path}",
            applied_writes=(applied_write,),
            payload=policy_path,
        )

    proposal = require_policy_proposal(proposal)

    applied_write, policy_path = PolicyRepo()._apply_policy_change(
        base_dir=proposal.base_dir,
        audit_trigger_policy=proposal.audit_trigger_policy,
        proposal_id=proposal_id,
    )
    return ApplyResult(
        proposal_id=proposal_id,
        target=ProposalTarget.POLICY,
        success=True,
        detail=f"policy_applied path={policy_path}",
        applied_writes=(applied_write,),
        payload=policy_path,
    )
