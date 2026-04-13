from __future__ import annotations

from dataclasses import asdict, dataclass

from .models import RetrievalItem, utc_now


@dataclass(slots=True)
class GroundingEntry:
    canonical_id: str
    canonical_key: str
    text: str
    citation: str
    source_task_id: str
    evidence_status: str
    score: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def extract_grounding_entries(retrieval_items: list[RetrievalItem]) -> list[GroundingEntry]:
    entries: list[GroundingEntry] = []
    for item in retrieval_items:
        if str(item.metadata.get("storage_scope", "")).strip() != "canonical_registry":
            continue
        canonical_id = str(item.metadata.get("canonical_id", "")).strip()
        if not canonical_id:
            continue
        entries.append(
            GroundingEntry(
                canonical_id=canonical_id,
                canonical_key=str(item.metadata.get("canonical_key", "")).strip(),
                text=item.preview.strip(),
                citation=f"canonical:{canonical_id}",
                source_task_id=str(item.metadata.get("knowledge_task_id", "")).strip(),
                evidence_status=str(item.metadata.get("evidence_status", "")).strip(),
                score=item.score,
            )
        )
    return entries


def build_grounding_evidence(entries: list[GroundingEntry]) -> dict[str, object]:
    return {
        "generated_at": utc_now(),
        "entry_count": len(entries),
        "citations": [entry.citation for entry in entries],
        "entries": [entry.to_dict() for entry in entries],
    }


def build_grounding_evidence_report(evidence: dict[str, object]) -> str:
    entries = evidence.get("entries", [])
    if not isinstance(entries, list):
        entries = []
    lines = [
        "# Grounding Evidence",
        "",
        f"- generated_at: {evidence.get('generated_at', 'unknown')}",
        f"- entry_count: {evidence.get('entry_count', 0)}",
        f"- citations: {', '.join(evidence.get('citations', [])) if isinstance(evidence.get('citations', []), list) else '-'}",
        "",
        "## Entries",
    ]
    if not entries:
        lines.append("- none")
        return "\n".join(lines)

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        lines.extend(
            [
                f"- {entry.get('citation', 'unknown')}",
                f"  canonical_id: {entry.get('canonical_id', 'unknown')}",
                f"  canonical_key: {entry.get('canonical_key', '') or 'none'}",
                f"  source_task_id: {entry.get('source_task_id', '') or 'none'}",
                f"  evidence_status: {entry.get('evidence_status', '') or 'none'}",
                f"  score: {entry.get('score', 0)}",
                f"  text: {entry.get('text', '') or '(empty)'}",
            ]
        )
    return "\n".join(lines)
