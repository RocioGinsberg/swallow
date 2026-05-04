from __future__ import annotations

from pathlib import Path

from swallow.application.commands.policies import set_audit_trigger_policy_command
from swallow.application.services.consistency_audit import build_audit_trigger_policy_report, load_audit_trigger_policy


def handle_audit_command(base_dir: Path, args: object) -> int | None:
    if getattr(args, "command", None) != "audit":
        return None
    if getattr(args, "audit_command", None) != "policy":
        return None

    audit_policy_command = getattr(args, "audit_policy_command", None)
    if audit_policy_command == "show":
        print(build_audit_trigger_policy_report(load_audit_trigger_policy(base_dir)), end="")
        return 0
    if audit_policy_command == "set":
        result = set_audit_trigger_policy_command(
            base_dir,
            enabled=getattr(args, "enabled"),
            trigger_on_degraded=getattr(args, "trigger_on_degraded"),
            trigger_on_cost_above=getattr(args, "trigger_on_cost_above"),
            clear_trigger_on_cost_above=bool(getattr(args, "clear_trigger_on_cost_above")),
            auditor_route=getattr(args, "auditor_route"),
        )
        print(build_audit_trigger_policy_report(result.policy), end="")
        return 0
    return None
