from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from swallow.orchestration.models import RouteSelection
from swallow.provider_router.router import load_route_policy_from_path, select_route
from swallow.truth_governance.governance import (
    OperatorToken,
    ProposalTarget,
    apply_proposal,
    register_route_metadata_proposal,
)
from swallow.truth_governance.store import load_state


@dataclass(frozen=True)
class RouteMetadataApplyCommandResult:
    proposal_id: str


@dataclass(frozen=True)
class RouteSelectionCommandResult:
    task_id: str
    selection: RouteSelection
    executor_override: str
    route_mode_override: str


def apply_route_registry_command(base_dir: Path, registry_path: Path) -> RouteMetadataApplyCommandResult:
    route_registry = json.loads(registry_path.read_text(encoding="utf-8"))
    proposal_id = register_route_metadata_proposal(
        base_dir=base_dir,
        proposal_id=f"route-registry:{registry_path.name}",
        route_registry=route_registry,
    )
    apply_proposal(proposal_id, OperatorToken(source="cli"), ProposalTarget.ROUTE_METADATA)
    return RouteMetadataApplyCommandResult(proposal_id=proposal_id)


def apply_route_policy_command(base_dir: Path, policy_path: Path) -> RouteMetadataApplyCommandResult:
    route_policy = load_route_policy_from_path(policy_path)
    proposal_id = register_route_metadata_proposal(
        base_dir=base_dir,
        proposal_id=f"route-policy:{policy_path.name}",
        route_policy=route_policy,
    )
    apply_proposal(proposal_id, OperatorToken(source="cli"), ProposalTarget.ROUTE_METADATA)
    return RouteMetadataApplyCommandResult(proposal_id=proposal_id)


def select_route_command(
    base_dir: Path,
    task_id: str,
    *,
    executor: str | None,
    route_mode: str | None,
) -> RouteSelectionCommandResult:
    state = load_state(base_dir, task_id)
    selection = select_route(state, executor, route_mode)
    return RouteSelectionCommandResult(
        task_id=state.task_id,
        selection=selection,
        executor_override=str(executor or "").strip(),
        route_mode_override=str(route_mode or "").strip(),
    )
