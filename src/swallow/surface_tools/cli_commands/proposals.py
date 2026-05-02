from __future__ import annotations

from pathlib import Path

from swallow.application.commands.proposals import apply_reviewed_proposals_command, review_proposals_command
from swallow.surface_tools.meta_optimizer import (
    build_optimization_proposal_application_report,
    build_optimization_proposal_review_report,
)
from swallow.surface_tools.workspace import resolve_path


def handle_proposal_command(base_dir: Path, args: object) -> int | None:
    if getattr(args, "command", None) != "proposal":
        return None

    proposal_command = getattr(args, "proposal_command", None)
    if proposal_command == "review":
        result = review_proposals_command(
            base_dir,
            resolve_path(getattr(args, "proposal_file")),
            decision=getattr(args, "decision"),
            proposal_ids=list(getattr(args, "proposal_ids") or []),
            note=getattr(args, "note"),
        )
        print(build_optimization_proposal_review_report(result.review_record), end="")
        print(f"record: {result.record_path}")
        return 0

    if proposal_command == "apply":
        result = apply_reviewed_proposals_command(
            base_dir,
            resolve_path(getattr(args, "review_file")),
            proposal_id_strategy="review_id",
        )
        print(build_optimization_proposal_application_report(result.application_record), end="")
        print(f"record: {result.record_path}")
        return 0

    return None
