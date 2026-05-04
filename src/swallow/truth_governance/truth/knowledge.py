from __future__ import annotations

from pathlib import Path

from swallow._io_helpers import read_json_lines_strict_or_empty
from swallow.knowledge_retrieval.knowledge_plane import (
    build_canonical_registry_index,
    build_canonical_reuse_summary,
    persist_wiki_entry_from_canonical_record,
)
from swallow.application.infrastructure.paths import canonical_registry_path
from swallow.truth_governance.store import append_canonical_record, save_canonical_registry_index, save_canonical_reuse_policy


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
    ) -> tuple[str, ...]:
        applied_writes: list[str] = []
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

        if persist_wiki and not persist_wiki_first:
            persist_wiki_entry_from_canonical_record(
                base_dir,
                canonical_record,
                mirror_files=mirror_files,
                write_authority=write_authority,
            )
            applied_writes.append("wiki_entry")

        if refresh_derived:
            self._refresh_canonical_derivatives(base_dir)
            applied_writes.extend(["canonical_registry_index", "canonical_reuse_policy"])

        return tuple(applied_writes)

    def _refresh_canonical_derivatives(self, base_dir: Path) -> None:
        canonical_records = read_json_lines_strict_or_empty(canonical_registry_path(base_dir))
        save_canonical_registry_index(base_dir, build_canonical_registry_index(canonical_records))
        save_canonical_reuse_policy(base_dir, build_canonical_reuse_summary(canonical_records))
