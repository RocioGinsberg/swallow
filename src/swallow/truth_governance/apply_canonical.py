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
        supersede_target_ids=proposal.supersede_target_ids,
    )
    canonical_id = str(proposal.canonical_record.get("canonical_id", "")).strip()
    detail = f"canonical_applied canonical_id={canonical_id or '-'}"
    payload: dict[str, object] = {}
    if proposal.supersede_target_ids:
        payload["supersede_target_ids"] = list(proposal.supersede_target_ids)
        payload["superseded_canonical_ids"] = list(applied_writes.superseded_canonical_ids)
    if applied_writes.source_evidence_ids:
        payload["source_evidence_ids"] = list(applied_writes.source_evidence_ids)
    if applied_writes.derived_relation_ids:
        payload["derived_relation_ids"] = list(applied_writes.derived_relation_ids)
    if applied_writes.superseded_canonical_ids:
        detail = (
            f"{detail} superseded_canonical_ids="
            f"{','.join(applied_writes.superseded_canonical_ids)}"
        )
    return ApplyResult(
        proposal_id=proposal_id,
        target=ProposalTarget.CANONICAL_KNOWLEDGE,
        success=True,
        detail=detail,
        applied_writes=applied_writes.applied_writes,
        payload=payload or None,
    )
