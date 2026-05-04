from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.knowledge_retrieval.knowledge_plane import (
    load_task_knowledge_view,
    persist_wiki_entry_from_canonical_record as persist_wiki_entry_from_record,
)
from swallow.application.infrastructure.paths import knowledge_evidence_entry_path, knowledge_objects_path
from swallow.truth_governance.store import save_knowledge_objects


class KnowledgeStoreTest(unittest.TestCase):
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
