from __future__ import annotations

from pathlib import Path

from swallow.application.commands.meta_optimizer import run_meta_optimizer_command


def handle_meta_optimize_command(base_dir: Path, args: object) -> int | None:
    if getattr(args, "command", None) != "meta-optimize":
        return None

    result = run_meta_optimizer_command(base_dir, last_n=getattr(args, "last_n"))
    print(result.report, end="")
    print(f"artifact: {result.artifact_path}")
    print(f"proposal_bundle: {result.proposal_bundle_path}")
    return 0
