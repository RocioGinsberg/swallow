from __future__ import annotations

from enum import Enum


class DuplicateProposalError(ValueError):
    pass


class PendingProposalRepo:
    def __init__(self) -> None:
        self._pending: dict[tuple[Enum, str], object] = {}

    def register(self, target: Enum, proposal_id: str, proposal: object) -> str:
        normalized_id = proposal_id.strip()
        if not normalized_id:
            raise ValueError("proposal_id must be a non-empty string.")
        key = (target, normalized_id)
        if key in self._pending:
            target_value = str(getattr(target, "value", target))
            raise DuplicateProposalError(f"Duplicate proposal artifact: {normalized_id} ({target_value})")
        self._pending[key] = proposal
        return normalized_id

    def load(self, target: Enum, proposal_id: str) -> object:
        normalized_id = proposal_id.strip()
        if not normalized_id:
            raise ValueError("proposal_id must be a non-empty string.")
        key = (target, normalized_id)
        if key not in self._pending:
            target_value = str(getattr(target, "value", target))
            raise ValueError(f"Unknown proposal artifact: {normalized_id} ({target_value})")
        return self._pending[key]
