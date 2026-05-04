from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from swallow._io_helpers import read_json_lines_strict_or_empty
from swallow.knowledge_retrieval.knowledge_plane import (
    build_canonical_registry_index,
    build_canonical_reuse_summary,
    materialize_source_evidence_from_canonical_record,
    persist_wiki_entry_from_canonical_record,
    upsert_knowledge_relation,
)
from swallow.application.infrastructure.paths import canonical_registry_path
from swallow.truth_governance.store import (
    append_canonical_record,
    mark_canonical_records_superseded_by_targets,
    save_canonical_registry_index,
    save_canonical_reuse_policy,
)


@dataclass(frozen=True)
class CanonicalPromotionResult:
    applied_writes: tuple[str, ...]
    superseded_canonical_ids: tuple[str, ...] = ()
    source_evidence_ids: tuple[str, ...] = ()
    derived_relation_ids: tuple[str, ...] = ()


class KnowledgeRepo:
    def _promote_canonical(
        self,
        *,
        base_dir: Path,
        canonical_record: dict[str, object],
        write_authority: str,
        mirror_files: bool,
        persist_wiki: bool,
        persist_wiki_first: bool,
        refresh_derived: bool,
        supersede_target_ids: tuple[str, ...] = (),
    ) -> CanonicalPromotionResult:
        canonical_record = dict(canonical_record)
        applied_writes: list[str] = []
        if supersede_target_ids:
            mark_canonical_records_superseded_by_targets(
                base_dir,
                supersede_target_ids,
                superseded_by=str(canonical_record.get("canonical_id", "")).strip(),
                superseded_at=str(canonical_record.get("promoted_at", "")).strip(),
                dry_run=True,
            )

        source_evidence_ids = tuple(
            materialize_source_evidence_from_canonical_record(
                base_dir,
                canonical_record,
                mirror_files=mirror_files,
                write_authority=write_authority,
            )
        )
        if source_evidence_ids:
            canonical_record["source_evidence_ids"] = list(source_evidence_ids)
            applied_writes.append("source_evidence_objects")

        if persist_wiki and persist_wiki_first:
            persist_wiki_entry_from_canonical_record(
                base_dir,
                canonical_record,
                mirror_files=mirror_files,
                write_authority=write_authority,
            )
            applied_writes.append("wiki_entry")

        append_canonical_record(base_dir, canonical_record)
        applied_writes.append("canonical_registry")

        superseded_records = mark_canonical_records_superseded_by_targets(
            base_dir,
            supersede_target_ids,
            superseded_by=str(canonical_record.get("canonical_id", "")).strip(),
            superseded_at=str(canonical_record.get("promoted_at", "")).strip(),
        )
        superseded_canonical_ids = tuple(
            str(record.get("canonical_id", "")).strip()
            for record in superseded_records
            if str(record.get("canonical_id", "")).strip()
        )
        if superseded_canonical_ids:
            applied_writes.append("canonical_supersede_targets")

        if persist_wiki and not persist_wiki_first:
            persist_wiki_entry_from_canonical_record(
                base_dir,
                canonical_record,
                mirror_files=mirror_files,
                write_authority=write_authority,
            )
            applied_writes.append("wiki_entry")

        derived_relation_ids: tuple[str, ...] = ()
        if persist_wiki and source_evidence_ids:
            derived_relation_ids = tuple(
                self._persist_source_evidence_relations(
                    base_dir,
                    canonical_record,
                    source_evidence_ids=source_evidence_ids,
                )
            )
            if derived_relation_ids:
                applied_writes.append("derived_from_relations")

        if refresh_derived:
            self._refresh_canonical_derivatives(base_dir)
            applied_writes.extend(["canonical_registry_index", "canonical_reuse_policy"])

        return CanonicalPromotionResult(
            applied_writes=tuple(applied_writes),
            superseded_canonical_ids=superseded_canonical_ids,
            source_evidence_ids=source_evidence_ids,
            derived_relation_ids=derived_relation_ids,
        )

    def _refresh_canonical_derivatives(self, base_dir: Path) -> None:
        canonical_records = read_json_lines_strict_or_empty(canonical_registry_path(base_dir))
        save_canonical_registry_index(base_dir, build_canonical_registry_index(canonical_records))
        save_canonical_reuse_policy(base_dir, build_canonical_reuse_summary(canonical_records))

    def _persist_source_evidence_relations(
        self,
        base_dir: Path,
        canonical_record: dict[str, object],
        *,
        source_evidence_ids: tuple[str, ...],
    ) -> list[str]:
        canonical_id = str(canonical_record.get("canonical_id", "")).strip()
        source_object_id = str(canonical_record.get("source_object_id", "")).strip()
        source_id = source_object_id or canonical_id
        if not source_id:
            return []

        candidate_id = _candidate_id_from_canonical_record(canonical_record)
        created_by = str(canonical_record.get("promoted_by", "")).strip() or "operator"
        relation_ids: list[str] = []
        for index, evidence_id in enumerate(source_evidence_ids, start=1):
            relation_id = _derived_from_relation_id(source_id, evidence_id)
            upsert_knowledge_relation(
                base_dir,
                relation_id=relation_id,
                source_object_id=source_id,
                target_object_id=evidence_id,
                relation_type="derived_from",
                confidence=1.0,
                context=f"Operator promoted staged candidate {candidate_id} source_pack[{index}].",
                created_by=created_by,
            )
            relation_ids.append(relation_id)
        return relation_ids


def _derived_from_relation_id(source_object_id: str, evidence_id: str) -> str:
    payload = [
        "derived-from-v1",
        str(source_object_id).strip(),
        str(evidence_id).strip(),
    ]
    token = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()[:16]
    return f"relation-derived-from-{token}"


def _candidate_id_from_canonical_record(record: dict[str, object]) -> str:
    decision_ref = str(record.get("decision_ref", "")).strip()
    if "#" in decision_ref:
        fragment = decision_ref.rsplit("#", 1)[1].strip()
        if fragment:
            return fragment
    canonical_id = str(record.get("canonical_id", "")).strip()
    if canonical_id.startswith("canonical-"):
        return canonical_id.removeprefix("canonical-")
    return canonical_id or "canonical-entry"
