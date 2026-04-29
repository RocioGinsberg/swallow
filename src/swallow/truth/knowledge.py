from __future__ import annotations

import json
from pathlib import Path

from ..canonical_registry import build_canonical_registry_index
from ..canonical_reuse import build_canonical_reuse_summary
from ..knowledge_store import persist_wiki_entry_from_record
from ..paths import canonical_registry_path
from ..store import append_canonical_record, save_canonical_registry_index, save_canonical_reuse_policy


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
            persist_wiki_entry_from_record(
                base_dir,
                canonical_record,
                mirror_files=mirror_files,
                write_authority=write_authority,
            )
            applied_writes.append("wiki_entry")

        append_canonical_record(base_dir, canonical_record)
        applied_writes.append("canonical_registry")

        if persist_wiki and not persist_wiki_first:
            persist_wiki_entry_from_record(
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
        canonical_records = _load_json_lines(canonical_registry_path(base_dir))
        save_canonical_registry_index(base_dir, build_canonical_registry_index(canonical_records))
        save_canonical_reuse_policy(base_dir, build_canonical_reuse_summary(canonical_records))


def _load_json_lines(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    records: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            records.append(json.loads(stripped))
    return records
