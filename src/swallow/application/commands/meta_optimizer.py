from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from swallow.surface_tools.meta_optimizer import MetaOptimizerSnapshot, run_meta_optimizer
from swallow.surface_tools.paths import latest_optimization_proposal_bundle_path


@dataclass(frozen=True)
class MetaOptimizerCommandResult:
    snapshot: MetaOptimizerSnapshot
    artifact_path: Path
    report: str
    proposal_bundle_path: Path


def run_meta_optimizer_command(base_dir: Path, last_n: int = 100) -> MetaOptimizerCommandResult:
    snapshot, artifact_path, report = run_meta_optimizer(base_dir, last_n=last_n)
    return MetaOptimizerCommandResult(
        snapshot=snapshot,
        artifact_path=artifact_path,
        report=report,
        proposal_bundle_path=latest_optimization_proposal_bundle_path(base_dir),
    )
