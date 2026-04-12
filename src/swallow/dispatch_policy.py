from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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
