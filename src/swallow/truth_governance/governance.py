from __future__ import annotations

from swallow.truth_governance.apply_canonical import _apply_canonical
from swallow.truth_governance.apply_policy import _apply_policy
from swallow.truth_governance.apply_outbox import _emit_event
from swallow.truth_governance.apply_route_metadata import _apply_route_metadata
from swallow.truth_governance.governance_models import ApplyResult, OperatorToken, ProposalTarget
from swallow.truth_governance.proposal_registry import (
    DuplicateProposalError,
    load_mps_policy,
    load_proposal_artifact,
    register_canonical_proposal,
    register_mps_policy_proposal,
    register_policy_proposal,
    register_route_metadata_proposal,
    validate_target,
)


def apply_proposal(
    proposal_id: str,
    operator_token: OperatorToken,
    target: ProposalTarget,
) -> ApplyResult:
    """Canonical knowledge / route metadata / policy write boundary."""

    if not isinstance(operator_token, OperatorToken):
        raise TypeError("operator_token must be an OperatorToken.")
    if not isinstance(target, ProposalTarget):
        raise TypeError("target must be a ProposalTarget.")

    proposal = load_proposal_artifact(proposal_id, target)
    validate_target(proposal, target)

    if target == ProposalTarget.CANONICAL_KNOWLEDGE:
        result = _apply_canonical(proposal, operator_token, proposal_id=proposal_id)
    elif target == ProposalTarget.ROUTE_METADATA:
        result = _apply_route_metadata(proposal, operator_token, proposal_id=proposal_id)
    elif target == ProposalTarget.POLICY:
        result = _apply_policy(proposal, operator_token, proposal_id=proposal_id)
    else:  # pragma: no cover - enum exhaustiveness guard
        raise ValueError(f"Unsupported proposal target: {target}")

    _emit_event(operator_token, target, result)
    return result
