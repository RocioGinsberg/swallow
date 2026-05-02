from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from swallow.surface_tools.meta_optimizer import (
    OptimizationProposalApplicationRecord,
    OptimizationProposalReviewRecord,
    load_optimization_proposal_review,
    review_optimization_proposals,
)
from swallow.truth_governance.governance import (
    OperatorToken,
    ProposalTarget,
    apply_proposal,
    register_route_metadata_proposal,
)

ProposalApplyIdStrategy = Literal["review_id", "unique"]


@dataclass(frozen=True)
class ProposalReviewCommandResult:
    review_record: OptimizationProposalReviewRecord
    record_path: Path


@dataclass(frozen=True)
class ProposalApplyCommandResult:
    application_record: OptimizationProposalApplicationRecord
    record_path: Path
    proposal_id: str


def review_proposals_command(
    base_dir: Path,
    bundle_path: Path,
    *,
    decision: str,
    proposal_ids: list[str] | None = None,
    note: str = "",
    reviewer: str = "swl_cli",
) -> ProposalReviewCommandResult:
    review_record, record_path = review_optimization_proposals(
        base_dir,
        bundle_path,
        decision=decision,
        proposal_ids=proposal_ids,
        note=note,
        reviewer=reviewer,
    )
    return ProposalReviewCommandResult(review_record=review_record, record_path=record_path)


def _proposal_id_for_review(
    review_record: OptimizationProposalReviewRecord,
    review_path: Path,
    *,
    strategy: ProposalApplyIdStrategy,
) -> str:
    base_proposal_id = review_record.review_id or review_path.stem
    if strategy == "review_id":
        return base_proposal_id
    if strategy == "unique":
        return f"{base_proposal_id}-apply-{time.time_ns():x}"
    raise ValueError(f"Unsupported proposal apply id strategy: {strategy}")


def apply_reviewed_proposals_command(
    base_dir: Path,
    review_path: Path,
    *,
    proposal_id: str | None = None,
    proposal_id_strategy: ProposalApplyIdStrategy = "unique",
) -> ProposalApplyCommandResult:
    review_record = load_optimization_proposal_review(review_path)
    route_proposal_id = proposal_id or _proposal_id_for_review(
        review_record,
        review_path,
        strategy=proposal_id_strategy,
    )
    registered_proposal_id = register_route_metadata_proposal(
        base_dir=base_dir,
        proposal_id=route_proposal_id,
        review_path=review_path,
    )
    result = apply_proposal(
        registered_proposal_id,
        OperatorToken(source="cli"),
        ProposalTarget.ROUTE_METADATA,
    )
    if not isinstance(result.payload, tuple) or len(result.payload) != 2:
        raise RuntimeError("Route metadata apply result did not include an application record payload.")
    application_record, record_path = result.payload
    if not isinstance(application_record, OptimizationProposalApplicationRecord) or not isinstance(record_path, Path):
        raise RuntimeError("Route metadata apply result payload has an unexpected shape.")
    return ProposalApplyCommandResult(
        application_record=application_record,
        record_path=record_path,
        proposal_id=registered_proposal_id,
    )
