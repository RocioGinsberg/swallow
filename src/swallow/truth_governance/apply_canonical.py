from __future__ import annotations

from swallow.truth_governance.governance_models import ApplyResult, OperatorToken, ProposalTarget
from swallow.truth_governance.proposal_registry import require_canonical_proposal
from swallow.truth_governance.truth import KnowledgeRepo


def _apply_canonical(proposal: object, _operator_token: OperatorToken, *, proposal_id: str) -> ApplyResult:
    proposal = require_canonical_proposal(proposal)

    applied_writes = KnowledgeRepo()._promote_canonical(
        base_dir=proposal.base_dir,
        canonical_record=proposal.canonical_record,
        write_authority=proposal.write_authority,
        mirror_files=proposal.mirror_files,
        persist_wiki=proposal.persist_wiki,
        persist_wiki_first=proposal.persist_wiki_first,
        refresh_derived=proposal.refresh_derived,
    )
    canonical_id = str(proposal.canonical_record.get("canonical_id", "")).strip()
    return ApplyResult(
        proposal_id=proposal_id,
        target=ProposalTarget.CANONICAL_KNOWLEDGE,
        success=True,
        detail=f"canonical_applied canonical_id={canonical_id or '-'}",
        applied_writes=applied_writes,
    )
