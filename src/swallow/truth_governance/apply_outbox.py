from __future__ import annotations

from swallow.truth_governance.governance_models import ApplyResult, OperatorToken, ProposalTarget


def _emit_event(_operator_token: OperatorToken, _target: ProposalTarget, _result: ApplyResult) -> None:
    """Reserved for durable governance audit events once the event repository exists."""
