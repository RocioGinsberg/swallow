from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

WRITE_INTENT_KEYWORDS = ("write", "modify", "create", "edit", "delete")
PROMOTION_KEYWORDS = ("promot",)


@dataclass(slots=True)
class PolicyResult:
    valid: bool
    errors: list[str] = field(default_factory=list)


def _candidate_pointer_paths(pointer: str, task_dir: Path) -> list[Path]:
    candidate = Path(pointer)
    if candidate.is_absolute():
        return [candidate]

    return [
        task_dir / candidate,
        task_dir / "artifacts" / candidate,
    ]


def validate_handoff_semantics(contract: dict[str, Any], task_dir: Path) -> PolicyResult:
    errors: list[str] = []
    raw_pointers = contract.get("context_pointers", [])
    pointers = [str(pointer).strip() for pointer in raw_pointers if str(pointer).strip()]

    for pointer in pointers:
        if any(path.exists() for path in _candidate_pointer_paths(pointer, task_dir)):
            continue
        errors.append(f"context pointer not found: {pointer}")

    return PolicyResult(valid=not errors, errors=errors)


def validate_taxonomy_dispatch(task_state: Any, contract: dict[str, Any]) -> PolicyResult:
    errors: list[str] = []
    system_role = str(getattr(task_state, "route_taxonomy_role", "")).strip()
    memory_authority = str(getattr(task_state, "route_taxonomy_memory_authority", "")).strip()
    goal = str(contract.get("goal", "")).lower()
    next_steps = [str(step).strip().lower() for step in contract.get("next_steps", []) if str(step).strip()]
    done = [str(item).strip().lower() for item in contract.get("done", []) if str(item).strip()]
    context_pointers = [str(pointer).strip() for pointer in contract.get("context_pointers", []) if str(pointer).strip()]
    write_intent_text = " ".join([goal, *done, *next_steps])

    if system_role == "validator" and any(
        keyword in write_intent_text
        for keyword in WRITE_INTENT_KEYWORDS
    ):
        errors.append("validator routes cannot accept write-intent dispatch contracts")

    if memory_authority == "canonical-write-forbidden" and any(keyword in goal for keyword in PROMOTION_KEYWORDS):
        errors.append("canonical-write-forbidden routes cannot accept promotion-oriented dispatch goals")

    if memory_authority == "stateless" and context_pointers:
        errors.append("stateless routes cannot accept dispatch contracts that require task-state context pointers")

    return PolicyResult(valid=not errors, errors=errors)
