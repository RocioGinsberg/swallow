from __future__ import annotations

import sys
from pathlib import Path

from swallow.application.commands.policies import set_mps_policy_command
from swallow.application.commands.synthesis import run_synthesis_command, stage_synthesis_command
from swallow.surface_tools.workspace import resolve_path


def handle_synthesis_command(base_dir: Path, args: object) -> int | None:
    if getattr(args, "command", None) != "synthesis":
        return None

    synthesis_command = getattr(args, "synthesis_command", None)
    if synthesis_command == "policy" and getattr(args, "synthesis_policy_command", None) == "set":
        result = set_mps_policy_command(
            base_dir,
            kind=getattr(args, "kind"),
            value=int(getattr(args, "value")),
        )
        print(f"{result.kind}: {result.value}")
        print(f"applied: {'yes' if result.applied else 'no'}")
        return 0

    if synthesis_command == "run":
        result = run_synthesis_command(
            base_dir,
            task_id=getattr(args, "task_id"),
            config_path=resolve_path(getattr(args, "config_path")),
        )
        print(f"{result.task_id} synthesis_completed config_id={result.config_id} artifact={result.artifact_path}")
        if result.summary:
            print(result.summary)
        return 0

    if synthesis_command == "stage":
        result = stage_synthesis_command(base_dir, task_id=getattr(args, "task_id"))
        if result.duplicate is not None:
            print(
                f"Synthesis arbitration is already staged: "
                f"{result.duplicate.candidate_id} submitted_at={result.duplicate.submitted_at}",
                file=sys.stderr,
            )
            return 1
        if result.candidate is None:
            raise RuntimeError("Synthesis staging did not return a candidate.")
        print(f"{result.candidate.candidate_id} synthesis_staged config_id={result.config_id}")
        return 0

    return None
