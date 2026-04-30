from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


FILESYSTEM_ACCESS_ORDER = {"none": 0, "workspace_read": 1, "workspace_write": 2}
NETWORK_ACCESS_ORDER = {"none": 0, "optional": 1, "required": 2}


@dataclass(slots=True)
class CapabilityConstraint:
    field: str
    max_value: str | bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


TAXONOMY_CAPABILITY_CONSTRAINTS: dict[str, list[CapabilityConstraint]] = {
    "validator/*": [
        CapabilityConstraint(
            field="filesystem_access",
            max_value="workspace_read",
            reason="validator routes stay read-only at execution time",
        ),
        CapabilityConstraint(
            field="supports_tool_loop",
            max_value=False,
            reason="validator routes cannot keep an unrestricted tool loop",
        ),
    ],
    "*/stateless": [
        CapabilityConstraint(
            field="filesystem_access",
            max_value="none",
            reason="stateless routes cannot rely on local task-state files",
        ),
        CapabilityConstraint(
            field="network_access",
            max_value="none",
            reason="stateless routes cannot rely on live network access",
        ),
        CapabilityConstraint(
            field="supports_tool_loop",
            max_value=False,
            reason="stateless routes cannot keep an unrestricted tool loop",
        ),
    ],
    "*/canonical-write-forbidden": [
        CapabilityConstraint(
            field="canonical_write_guard",
            max_value=True,
            reason="canonical-write-forbidden routes must stay behind manual promotion gates",
        )
    ],
}


def _matching_constraints(system_role: str, memory_authority: str) -> list[CapabilityConstraint]:
    matches: list[CapabilityConstraint] = []
    keys = (
        f"{system_role}/{memory_authority}",
        f"{system_role}/*",
        f"*/{memory_authority}",
    )
    for key in keys:
        matches.extend(TAXONOMY_CAPABILITY_CONSTRAINTS.get(key, []))
    return matches


def _is_stricter(field: str, current_value: Any, max_value: str | bool) -> bool:
    if isinstance(max_value, bool):
        return bool(current_value) and not max_value

    if field == "filesystem_access":
        return FILESYSTEM_ACCESS_ORDER.get(str(current_value), -1) > FILESYSTEM_ACCESS_ORDER.get(max_value, -1)
    if field == "network_access":
        return NETWORK_ACCESS_ORDER.get(str(current_value), -1) > NETWORK_ACCESS_ORDER.get(max_value, -1)

    return False


def enforce_capability_constraints(
    taxonomy_role: str,
    taxonomy_memory_authority: str,
    capabilities: dict[str, Any],
) -> tuple[dict[str, Any], list[CapabilityConstraint]]:
    enforced = dict(capabilities)
    applied: list[CapabilityConstraint] = []

    for constraint in _matching_constraints(taxonomy_role.strip(), taxonomy_memory_authority.strip()):
        current_value = enforced.get(constraint.field)
        if constraint.field not in enforced:
            enforced[constraint.field] = constraint.max_value
            applied.append(constraint)
            continue
        if _is_stricter(constraint.field, current_value, constraint.max_value):
            enforced[constraint.field] = constraint.max_value
            applied.append(constraint)
            continue
        if current_value == constraint.max_value:
            applied.append(constraint)

    return enforced, applied
