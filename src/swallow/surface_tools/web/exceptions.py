from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TaskActionBlockedError(Exception):
    blocked_kind: str
    blocked_reason: str
    detail: dict[str, Any]

    def __str__(self) -> str:
        return self.blocked_reason
