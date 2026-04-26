from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import uuid4

from .models import utc_now
from .paths import staged_knowledge_registry_path, staged_knowledge_root


STAGED_CANDIDATE_STATUSES: tuple[str, ...] = ("pending", "promoted", "rejected")


@dataclass(slots=True)
class StagedCandidate:
    candidate_id: str
    text: str
    source_task_id: str
    topic: str = ""
    source_kind: str = ""
    source_ref: str = ""
    source_object_id: str = ""
    submitted_by: str = ""
    submitted_at: str = ""
    taxonomy_role: str = ""
    taxonomy_memory_authority: str = ""
    status: str = "pending"
    decided_at: str = ""
    decided_by: str = ""
    decision_note: str = ""

    def __post_init__(self) -> None:
        self.candidate_id = self.candidate_id.strip() or generate_candidate_id()
        self.text = self.text.strip()
        self.source_task_id = self.source_task_id.strip()
        self.topic = self.topic.strip()
        self.source_kind = self.source_kind.strip()
        self.source_ref = self.source_ref.strip()
        self.source_object_id = self.source_object_id.strip()
        self.submitted_by = self.submitted_by.strip()
        self.submitted_at = self.submitted_at.strip() or utc_now()
        self.taxonomy_role = self.taxonomy_role.strip()
        self.taxonomy_memory_authority = self.taxonomy_memory_authority.strip()
        self.status = self.status.strip() or "pending"
        self.decided_at = self.decided_at.strip()
        self.decided_by = self.decided_by.strip()
        self.decision_note = self.decision_note.strip()
        self.validate()

    def validate(self) -> None:
        if not self.candidate_id.startswith("staged-"):
            raise ValueError("candidate_id must start with 'staged-'")
        if not self.text:
            raise ValueError("text must be a non-empty string")
        if not self.source_task_id:
            raise ValueError("source_task_id must be a non-empty string")
        if self.status not in STAGED_CANDIDATE_STATUSES:
            raise ValueError(
                f"Invalid staged candidate status: {self.status}. "
                f"Expected one of: {', '.join(STAGED_CANDIDATE_STATUSES)}"
            )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> StagedCandidate:
        return cls(
            candidate_id=str(payload.get("candidate_id", "")).strip(),
            text=str(payload.get("text", "")),
            source_task_id=str(payload.get("source_task_id", "")).strip(),
            topic=str(payload.get("topic", "")).strip(),
            source_kind=str(payload.get("source_kind", "")).strip(),
            source_ref=str(payload.get("source_ref", "")).strip(),
            source_object_id=str(payload.get("source_object_id", "")).strip(),
            submitted_by=str(payload.get("submitted_by", "")).strip(),
            submitted_at=str(payload.get("submitted_at", "")).strip(),
            taxonomy_role=str(payload.get("taxonomy_role", "")).strip(),
            taxonomy_memory_authority=str(payload.get("taxonomy_memory_authority", "")).strip(),
            status=str(payload.get("status", "pending")).strip(),
            decided_at=str(payload.get("decided_at", "")).strip(),
            decided_by=str(payload.get("decided_by", "")).strip(),
            decision_note=str(payload.get("decision_note", "")).strip(),
        )


def generate_candidate_id() -> str:
    return f"staged-{uuid4().hex[:8]}"


def load_staged_candidates(base_dir: Path) -> list[StagedCandidate]:
    registry_file = staged_knowledge_registry_path(base_dir)
    if not registry_file.exists():
        return []

    candidates: list[StagedCandidate] = []
    for line in registry_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        candidates.append(StagedCandidate.from_dict(json.loads(stripped)))
    return candidates


def submit_staged_candidate(base_dir: Path, candidate: StagedCandidate) -> StagedCandidate:
    staged_knowledge_root(base_dir).mkdir(parents=True, exist_ok=True)
    persisted = StagedCandidate.from_dict(candidate.to_dict())
    registry_file = staged_knowledge_registry_path(base_dir)
    with registry_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(persisted.to_dict()) + "\n")
    return persisted


def update_staged_candidate(
    base_dir: Path,
    candidate_id: str,
    status: str,
    decided_by: str,
    note: str = "",
) -> StagedCandidate:
    updated_candidates: list[StagedCandidate] = []
    selected_candidate: StagedCandidate | None = None
    normalized_id = candidate_id.strip()
    normalized_status = status.strip()
    normalized_decided_by = decided_by.strip()
    normalized_note = note.strip()

    for candidate in load_staged_candidates(base_dir):
        if candidate.candidate_id != normalized_id:
            updated_candidates.append(candidate)
            continue

        selected_candidate = StagedCandidate(
            candidate_id=candidate.candidate_id,
            text=candidate.text,
            source_task_id=candidate.source_task_id,
            topic=candidate.topic,
            source_kind=candidate.source_kind,
            source_ref=candidate.source_ref,
            source_object_id=candidate.source_object_id,
            submitted_by=candidate.submitted_by,
            submitted_at=candidate.submitted_at,
            taxonomy_role=candidate.taxonomy_role,
            taxonomy_memory_authority=candidate.taxonomy_memory_authority,
            status=normalized_status,
            decided_at=utc_now(),
            decided_by=normalized_decided_by,
            decision_note=normalized_note,
        )
        updated_candidates.append(selected_candidate)

    if selected_candidate is None:
        raise ValueError(f"Unknown staged candidate: {normalized_id}")

    staged_knowledge_root(base_dir).mkdir(parents=True, exist_ok=True)
    staged_knowledge_registry_path(base_dir).write_text(
        "".join(json.dumps(item.to_dict()) + "\n" for item in updated_candidates),
        encoding="utf-8",
    )
    return selected_candidate
