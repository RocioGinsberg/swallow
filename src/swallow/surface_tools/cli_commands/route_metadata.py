from __future__ import annotations

import time
from pathlib import Path

from swallow.provider_router.router import (
    build_route_capability_profiles_report,
    build_route_weights_report,
    current_route_weights,
    load_route_capability_profiles,
    route_by_name,
)
from swallow.surface_tools.meta_optimizer import extract_route_weight_proposals_from_report
from swallow.surface_tools.workspace import resolve_path
from swallow.truth_governance.governance import (
    OperatorToken,
    ProposalTarget,
    apply_proposal,
    register_route_metadata_proposal,
)


def _unique_cli_proposal_id(prefix: str, identity: str) -> str:
    normalized_identity = identity.strip() or "unknown"
    return f"{prefix}:{normalized_identity}:{time.time_ns():x}"


def handle_route_metadata_command(base_dir: Path, args: object) -> int | None:
    if getattr(args, "command", None) != "route":
        return None

    route_command = getattr(args, "route_command", None)
    if route_command == "weights":
        return _handle_route_weights_command(base_dir, args)
    if route_command == "capabilities":
        return _handle_route_capabilities_command(base_dir, args)
    return None


def _handle_route_weights_command(base_dir: Path, args: object) -> int | None:
    route_weights_command = getattr(args, "route_weights_command", None)
    if route_weights_command == "show":
        print(build_route_weights_report(base_dir), end="")
        return 0

    if route_weights_command != "apply":
        return None

    proposal_path = resolve_path(getattr(args, "proposal_file"))
    proposals = extract_route_weight_proposals_from_report(proposal_path.read_text(encoding="utf-8"))
    if not proposals:
        raise ValueError(f"No route_weight proposals found in {proposal_path}")

    updated_weights = current_route_weights()
    for proposal in proposals:
        route_name = str(proposal.route_name or "").strip()
        if not route_name:
            continue
        if route_by_name(route_name) is None:
            raise ValueError(f"Unknown route in proposal file: {route_name}")
        updated_weights[route_name] = float(proposal.suggested_weight or 1.0)

    persisted_weights = {
        route_name: weight
        for route_name, weight in updated_weights.items()
        if abs(weight - 1.0) > 1e-9
    }
    proposal_id = register_route_metadata_proposal(
        base_dir=base_dir,
        proposal_id=_unique_cli_proposal_id("route-weights", proposal_path.name),
        route_weights=persisted_weights,
    )
    apply_proposal(proposal_id, OperatorToken(source="cli"), ProposalTarget.ROUTE_METADATA)
    print(build_route_weights_report(base_dir), end="")
    return 0


def _handle_route_capabilities_command(base_dir: Path, args: object) -> int | None:
    route_capabilities_command = getattr(args, "route_capabilities_command", None)
    if route_capabilities_command == "show":
        print(build_route_capability_profiles_report(base_dir), end="")
        return 0

    if route_capabilities_command != "update":
        return None

    route_name = getattr(args, "route_name").strip()
    if not route_name:
        raise ValueError("route_name must be a non-empty route name.")
    if route_by_name(route_name) is None:
        raise ValueError(f"Unknown route: {route_name}")

    profiles = load_route_capability_profiles(base_dir)
    profile = dict(profiles.get(route_name, {}))
    task_family_scores = dict(profile.get("task_family_scores", {}))
    unsupported_task_types = {
        str(item).strip().lower()
        for item in profile.get("unsupported_task_types", [])
        if str(item).strip()
    }

    updated = False
    if getattr(args, "task_type") is not None or getattr(args, "score") is not None:
        if getattr(args, "task_type") is None or getattr(args, "score") is None:
            raise ValueError("--task-type and --score must be provided together.")
        task_type = getattr(args, "task_type").strip().lower()
        if not task_type:
            raise ValueError("--task-type must be a non-empty task family.")
        if getattr(args, "score") < 0:
            raise ValueError("--score must be non-negative.")
        task_family_scores[task_type] = float(getattr(args, "score"))
        unsupported_task_types.discard(task_type)
        updated = True

    if getattr(args, "clear_task_type") is not None:
        task_type = getattr(args, "clear_task_type").strip().lower()
        if not task_type:
            raise ValueError("--clear-task-type must be a non-empty task family.")
        task_family_scores.pop(task_type, None)
        updated = True

    for task_type in getattr(args, "mark_unsupported"):
        normalized_task_type = task_type.strip().lower()
        if not normalized_task_type:
            raise ValueError("--mark-unsupported must contain non-empty task families.")
        unsupported_task_types.add(normalized_task_type)
        task_family_scores.pop(normalized_task_type, None)
        updated = True

    for task_type in getattr(args, "clear_unsupported"):
        normalized_task_type = task_type.strip().lower()
        if not normalized_task_type:
            raise ValueError("--clear-unsupported must contain non-empty task families.")
        unsupported_task_types.discard(normalized_task_type)
        updated = True

    if not updated:
        raise ValueError("No route capability profile changes requested.")

    profiles[route_name] = {
        "task_family_scores": task_family_scores,
        "unsupported_task_types": sorted(unsupported_task_types),
    }
    proposal_id = register_route_metadata_proposal(
        base_dir=base_dir,
        proposal_id=_unique_cli_proposal_id("route-capabilities", route_name),
        route_capability_profiles=profiles,
    )
    apply_proposal(proposal_id, OperatorToken(source="cli"), ProposalTarget.ROUTE_METADATA)
    print(build_route_capability_profiles_report(base_dir), end="")
    return 0
