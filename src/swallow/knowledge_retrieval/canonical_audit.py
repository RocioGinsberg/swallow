from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

from swallow.surface_tools.paths import task_root
from swallow.truth_governance.store import load_knowledge_objects


@dataclass(slots=True)
class CanonicalAuditResult:
    total: int
    active: int
    superseded: int
    duplicate_active_keys: dict[str, list[str]] = field(default_factory=dict)
    orphan_records: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _source_object_exists(base_dir: Path, source_task_id: str, source_object_id: str) -> bool:
    if not source_task_id or not source_object_id:
        return False
    if not task_root(base_dir, source_task_id).exists():
        return False
    payload = load_knowledge_objects(base_dir, source_task_id)
    return any(str(item.get("object_id", "")).strip() == source_object_id for item in payload if isinstance(item, dict))


def audit_canonical_registry(base_dir: Path, records: list[dict[str, object]]) -> CanonicalAuditResult:
    active_by_key: dict[str, list[str]] = defaultdict(list)
    orphan_records: list[str] = []
    active = 0
    superseded = 0

    for record in records:
        canonical_id = str(record.get("canonical_id", "")).strip() or "unknown"
        canonical_key = str(record.get("canonical_key", "")).strip()
        canonical_status = str(record.get("canonical_status", "active")).strip()
        source_task_id = str(record.get("source_task_id", "")).strip()
        source_object_id = str(record.get("source_object_id", "")).strip()

        if canonical_status == "superseded":
            superseded += 1
        else:
            active += 1
            if canonical_key:
                active_by_key[canonical_key].append(canonical_id)

        if not _source_object_exists(base_dir, source_task_id, source_object_id):
            orphan_records.append(canonical_id)

    duplicate_active_keys = {
        canonical_key: canonical_ids
        for canonical_key, canonical_ids in active_by_key.items()
        if len(canonical_ids) > 1
    }
    return CanonicalAuditResult(
        total=len(records),
        active=active,
        superseded=superseded,
        duplicate_active_keys=duplicate_active_keys,
        orphan_records=orphan_records,
    )


def build_canonical_audit_report(result: CanonicalAuditResult) -> str:
    lines = [
        "Canonical Registry Audit",
        f"total: {result.total}",
        f"active: {result.active}",
        f"superseded: {result.superseded}",
        f"duplicate_active_keys: {len(result.duplicate_active_keys)}",
        f"orphan_records: {len(result.orphan_records)}",
        "",
    ]

    if not result.duplicate_active_keys and not result.orphan_records:
        lines.append("no issues")
        return "\n".join(lines)

    if result.duplicate_active_keys:
        lines.append("Duplicate Active Keys")
        for canonical_key, canonical_ids in sorted(result.duplicate_active_keys.items()):
            lines.append(f"- {canonical_key}: {', '.join(canonical_ids)}")
        lines.append("")

    if result.orphan_records:
        lines.append("Orphan Records")
        for canonical_id in result.orphan_records:
            lines.append(f"- {canonical_id}")

    return "\n".join(lines)
