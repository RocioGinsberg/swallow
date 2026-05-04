from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.knowledge_retrieval.knowledge_plane import (
    build_source_anchor_identity,
    load_task_knowledge_view,
    materialize_source_evidence_from_canonical_record,
    persist_wiki_entry_from_canonical_record as persist_wiki_entry_from_record,
)
from swallow.application.infrastructure.paths import knowledge_evidence_entry_path, knowledge_objects_path
from swallow.truth_governance.store import save_knowledge_objects


class KnowledgeStoreTest(unittest.TestCase):
    def test_source_anchor_identity_normalizes_heading_path_and_hashes_all_fields(self) -> None:
        anchor = {
            "source_ref": "file://workspace/source.md",
            "content_hash": "sha256:source",
            "parser_version": "wiki-compiler-v1",
            "span": "L1-L3",
            "heading_path": ["Design", "Evidence"],
        }
        identity = build_source_anchor_identity(anchor)
        string_heading_identity = build_source_anchor_identity(
            {
                **anchor,
                "heading_path": "Design > Evidence",
            }
        )

        self.assertEqual(identity["source_anchor_version"], "source-anchor-v1")
        self.assertEqual(identity["heading_path"], "Design > Evidence")
        self.assertEqual(identity["source_anchor_key"], string_heading_identity["source_anchor_key"])
        self.assertEqual(identity["evidence_id"], f"evidence-src-{identity['source_anchor_key']}")

        changed_fields = {
            "source_ref": "file://workspace/other.md",
            "content_hash": "sha256:other",
            "parser_version": "wiki-compiler-v2",
            "span": "L4-L7",
            "heading_path": ["Design", "Other"],
        }
        for field_name, changed_value in changed_fields.items():
            changed_anchor = {**anchor, field_name: changed_value}
            changed_identity = build_source_anchor_identity(changed_anchor)
            self.assertNotEqual(
                identity["source_anchor_key"],
                changed_identity["source_anchor_key"],
                field_name,
            )

    def test_materialize_source_pack_evidence_writes_source_anchor_metadata_and_stable_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            anchor = {
                "reference": "source-1",
                "path": "source.md",
                "source_type": "raw_material",
                "source_ref": "file://workspace/source.md",
                "resolved_ref": "file://workspace/source.md",
                "resolved_path": "source.md",
                "resolution_status": "resolved",
                "line_start": 10,
                "line_end": 12,
                "content_hash": "sha256:source",
                "parser_version": "wiki-compiler-v1",
                "heading_path": ["Design", "Evidence"],
                "preview": "Source preview for stable identity.",
            }
            expected_identity = build_source_anchor_identity(anchor)

            evidence_ids = materialize_source_evidence_from_canonical_record(
                tmp_path,
                {
                    "canonical_id": "canonical-staged-source",
                    "source_task_id": "task-source",
                    "promoted_at": "2026-05-04T00:00:00+00:00",
                    "decision_ref": ".swl/staged_knowledge/registry.jsonl#staged-source",
                    "source_pack": [anchor],
                },
            )
            view = load_task_knowledge_view(tmp_path, "task-source")

        self.assertEqual(evidence_ids, [expected_identity["evidence_id"]])
        self.assertEqual(len(view), 1)
        entry = view[0]
        self.assertEqual(entry["object_id"], expected_identity["evidence_id"])
        self.assertEqual(entry["source_anchor_version"], "source-anchor-v1")
        self.assertEqual(entry["source_anchor_key"], expected_identity["source_anchor_key"])
        self.assertEqual(entry["span"], "line:10-12")
        self.assertEqual(entry["heading_path"], "Design > Evidence")
        self.assertEqual(entry["text"], "Source preview for stable identity.")

    def test_materialize_source_pack_evidence_reuses_existing_anchor_across_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            anchor = {
                "reference": "source-1",
                "source_ref": "file://workspace/shared.md",
                "resolved_ref": "file://workspace/shared.md",
                "resolution_status": "resolved",
                "content_hash": "sha256:shared",
                "parser_version": "wiki-compiler-v1",
                "span": "L1-L3",
                "preview": "Shared source preview.",
            }
            expected_identity = build_source_anchor_identity(anchor)

            first_ids = materialize_source_evidence_from_canonical_record(
                tmp_path,
                {
                    "canonical_id": "canonical-a",
                    "source_task_id": "task-a",
                    "promoted_at": "2026-05-04T00:00:00+00:00",
                    "decision_ref": ".swl/staged_knowledge/registry.jsonl#staged-a",
                    "source_pack": [anchor],
                },
            )
            second_ids = materialize_source_evidence_from_canonical_record(
                tmp_path,
                {
                    "canonical_id": "canonical-b",
                    "source_task_id": "task-b",
                    "promoted_at": "2026-05-04T00:00:00+00:00",
                    "decision_ref": ".swl/staged_knowledge/registry.jsonl#staged-b",
                    "source_pack": [anchor],
                },
            )
            first_view = load_task_knowledge_view(tmp_path, "task-a")
            second_view = load_task_knowledge_view(tmp_path, "task-b")

        self.assertEqual(first_ids, [expected_identity["evidence_id"]])
        self.assertEqual(second_ids, [expected_identity["evidence_id"]])
        self.assertEqual([item["object_id"] for item in first_view], [expected_identity["evidence_id"]])
        self.assertEqual(second_view, [])

    def test_persist_wiki_entry_from_record_overlays_legacy_view(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            save_knowledge_objects(
                tmp_path,
                "task-promote",
                [
                    {
                        "object_id": "knowledge-0007",
                        "text": "Verified evidence before promotion.",
                        "stage": "verified",
                        "source_kind": "external_knowledge_capture",
                        "source_ref": "chat://phase32",
                        "task_linked": True,
                        "captured_at": "2026-04-16T11:00:00+00:00",
                        "evidence_status": "artifact_backed",
                        "artifact_ref": ".swl/tasks/task-promote/artifacts/evidence.md",
                        "canonicalization_intent": "promote",
                    }
                ],
            )

            wiki_entry = persist_wiki_entry_from_record(
                tmp_path,
                {
                    "canonical_id": "canonical-task-promote-knowledge-0007",
                    "source_task_id": "task-promote",
                    "source_object_id": "knowledge-0007",
                    "promoted_at": "2026-04-16T12:00:00+00:00",
                    "promoted_by": "swl_cli",
                    "decision_ref": ".swl/staged_knowledge/registry.jsonl#staged-0007",
                    "artifact_ref": ".swl/tasks/task-promote/artifacts/evidence.md",
                    "source_ref": "chat://phase32",
                    "text": "Canonical wording after promotion.",
                    "evidence_status": "artifact_backed",
                },
            )
            merged_view = load_task_knowledge_view(tmp_path, "task-promote")

        self.assertEqual(wiki_entry["store_type"], "wiki")
        self.assertFalse(knowledge_evidence_entry_path(tmp_path, "task-promote", "knowledge-0007").exists())
        self.assertEqual(len(merged_view), 1)
        self.assertEqual(merged_view[0]["object_id"], "knowledge-0007")
        self.assertEqual(merged_view[0]["stage"], "canonical")
        self.assertEqual(merged_view[0]["promoted_by"], "swl_cli")
        self.assertEqual(merged_view[0]["change_log_ref"], ".swl/staged_knowledge/registry.jsonl#staged-0007")

    def test_load_task_knowledge_view_prefers_sqlite_when_file_view_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            with patch.dict("os.environ", {"SWALLOW_STORE_BACKEND": "sqlite"}, clear=False):
                save_knowledge_objects(
                    tmp_path,
                    "task-sqlite-truth",
                    [
                        {
                            "object_id": "knowledge-0010",
                            "text": "SQLite-backed knowledge.",
                            "stage": "verified",
                            "evidence_status": "artifact_backed",
                            "artifact_ref": ".swl/tasks/task-sqlite-truth/artifacts/evidence.md",
                        }
                    ],
                )

            knowledge_objects_path(tmp_path, "task-sqlite-truth").write_text(
                json.dumps(
                    [
                        {
                            "object_id": "knowledge-0010",
                            "text": "Stale file mirror.",
                            "stage": "verified",
                            "store_type": "evidence",
                        }
                    ],
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            merged_view = load_task_knowledge_view(tmp_path, "task-sqlite-truth")

        self.assertEqual(len(merged_view), 1)
        self.assertEqual(merged_view[0]["text"], "SQLite-backed knowledge.")


if __name__ == "__main__":
    unittest.main()
