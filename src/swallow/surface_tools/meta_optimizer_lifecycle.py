from __future__ import annotations

import json
from pathlib import Path

from swallow.orchestration.models import utc_now
from swallow.surface_tools.meta_optimizer_models import (
    OptimizationProposalApplicationRecord,
    OptimizationProposalBundle,
    OptimizationProposalReviewRecord,
    ProposalReviewEntry,
    VALID_PROPOSAL_REVIEW_DECISIONS,
    MetaOptimizerSnapshot,
    _ensure_proposal_metadata,
    _timestamp_token,
)
from swallow.surface_tools.paths import (
    latest_optimization_proposal_bundle_path,
    optimization_proposal_bundle_path,
    optimization_proposal_review_path,
)

def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload




def save_optimization_proposal_bundle(
    base_dir: Path,
    snapshot: MetaOptimizerSnapshot,
    report_artifact: Path,
) -> tuple[OptimizationProposalBundle, Path]:
    bundle = OptimizationProposalBundle(
        bundle_id=f"bundle-{_timestamp_token(snapshot.generated_at)}",
        generated_at=snapshot.generated_at,
        task_limit=snapshot.task_limit,
        scanned_task_ids=list(snapshot.scanned_task_ids),
        scanned_event_count=snapshot.scanned_event_count,
        report_artifact=str(report_artifact),
        proposals=_ensure_proposal_metadata(list(snapshot.proposals)),
    )
    bundle_path = optimization_proposal_bundle_path(base_dir, bundle.bundle_id)
    payload = bundle.to_dict()
    _write_json(bundle_path, payload)
    _write_json(latest_optimization_proposal_bundle_path(base_dir), payload)
    return bundle, bundle_path


def load_optimization_proposal_bundle(bundle_path: Path) -> OptimizationProposalBundle:
    if not bundle_path.exists():
        raise FileNotFoundError(f"Proposal bundle not found: {bundle_path}")
    return OptimizationProposalBundle.from_dict(_load_json(bundle_path))


def review_optimization_proposals(
    base_dir: Path,
    bundle_path: Path,
    decision: str,
    proposal_ids: list[str] | None = None,
    note: str = "",
    reviewer: str = "swl_cli",
) -> tuple[OptimizationProposalReviewRecord, Path]:
    normalized_decision = decision.strip().lower()
    if normalized_decision not in VALID_PROPOSAL_REVIEW_DECISIONS:
        raise ValueError(f"Unsupported proposal decision: {decision}")

    bundle = load_optimization_proposal_bundle(bundle_path)
    selected_ids = {
        proposal_id.strip()
        for proposal_id in (proposal_ids or [])
        if proposal_id.strip()
    }
    known_ids = {proposal.proposal_id for proposal in bundle.proposals}
    unknown_ids = sorted(selected_ids - known_ids)
    if unknown_ids:
        raise ValueError(f"Unknown proposal ids: {', '.join(unknown_ids)}")

    review_entries: list[ProposalReviewEntry] = []
    for proposal in bundle.proposals:
        entry_decision = normalized_decision
        entry_note = note.strip()
        if selected_ids and proposal.proposal_id not in selected_ids:
            entry_decision = "deferred"
            entry_note = "not selected in this review"
        review_entries.append(
            ProposalReviewEntry(
                proposal_id=proposal.proposal_id,
                proposal_type=proposal.proposal_type,
                route_name=proposal.route_name,
                task_family=proposal.task_family,
                decision=entry_decision,
                description=proposal.description,
                suggested_action=proposal.suggested_action,
                note=entry_note,
                severity=proposal.severity,
                priority=proposal.priority or proposal.severity or "info",
                rationale=proposal.rationale or proposal.description,
                suggested_weight=proposal.suggested_weight,
                suggested_task_family_score=proposal.suggested_task_family_score,
                mark_task_family_unsupported=proposal.mark_task_family_unsupported,
            )
        )

    reviewed_at = utc_now()
    review_record = OptimizationProposalReviewRecord(
        review_id=f"review-{_timestamp_token(reviewed_at)}",
        reviewed_at=reviewed_at,
        decision=normalized_decision,
        source_bundle_path=str(bundle_path),
        source_bundle_id=bundle.bundle_id,
        reviewer=reviewer,
        note=note.strip(),
        entries=review_entries,
    )
    record_path = optimization_proposal_review_path(base_dir, review_record.review_id)
    _write_json(record_path, review_record.to_dict())
    return review_record, record_path


def load_optimization_proposal_review(review_path: Path) -> OptimizationProposalReviewRecord:
    if not review_path.exists():
        raise FileNotFoundError(f"Proposal review record not found: {review_path}")
    return OptimizationProposalReviewRecord.from_dict(_load_json(review_path))




def apply_reviewed_optimization_proposals(
    base_dir: Path,
    review_path: Path,
) -> tuple[OptimizationProposalApplicationRecord, Path]:
    from swallow.application.commands.proposals import apply_reviewed_proposals_command

    result = apply_reviewed_proposals_command(base_dir, review_path)
    return result.application_record, result.record_path
