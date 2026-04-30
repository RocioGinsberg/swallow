from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.knowledge_retrieval.canonical_registry import build_canonical_record
from swallow.knowledge_retrieval.knowledge_relations import (
    KNOWLEDGE_RELATION_TYPES,
    create_knowledge_relation,
    delete_knowledge_relation,
    list_knowledge_relations,
)
from swallow.truth_governance.store import append_canonical_record, save_knowledge_objects


class KnowledgeRelationsTest(unittest.TestCase):
    def test_create_knowledge_relation_persists_to_sqlite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            save_knowledge_objects(
                tmp_path,
                "task-a",
                [
                    {
                        "object_id": "knowledge-a",
                        "text": "A",
                        "stage": "verified",
                    }
                ],
            )
            save_knowledge_objects(
                tmp_path,
                "task-b",
                [
                    {
                        "object_id": "knowledge-b",
                        "text": "B",
                        "stage": "verified",
                    }
                ],
            )

            relation = create_knowledge_relation(
                tmp_path,
                source_object_id="knowledge-a",
                target_object_id="knowledge-b",
                relation_type="cites",
                confidence=0.9,
                context="A cites B",
            )
            relations = list_knowledge_relations(tmp_path, "knowledge-a")

        self.assertTrue(relation["relation_id"].startswith("relation-"))
        self.assertEqual(relations[0]["relation_type"], "cites")
        self.assertEqual(relations[0]["source_object_id"], "knowledge-a")
        self.assertEqual(relations[0]["target_object_id"], "knowledge-b")
        self.assertEqual(relations[0]["direction"], "outgoing")

    def test_relation_bidirectional_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            save_knowledge_objects(tmp_path, "task-a", [{"object_id": "knowledge-a", "text": "A", "stage": "verified"}])
            save_knowledge_objects(tmp_path, "task-b", [{"object_id": "knowledge-b", "text": "B", "stage": "verified"}])

            create_knowledge_relation(
                tmp_path,
                source_object_id="knowledge-a",
                target_object_id="knowledge-b",
                relation_type="extends",
            )

            source_relations = list_knowledge_relations(tmp_path, "knowledge-a")
            target_relations = list_knowledge_relations(tmp_path, "knowledge-b")

        self.assertEqual(source_relations[0]["direction"], "outgoing")
        self.assertEqual(target_relations[0]["direction"], "incoming")
        self.assertEqual(target_relations[0]["counterparty_object_id"], "knowledge-a")

    def test_relation_type_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            save_knowledge_objects(tmp_path, "task-a", [{"object_id": "knowledge-a", "text": "A", "stage": "verified"}])
            save_knowledge_objects(tmp_path, "task-b", [{"object_id": "knowledge-b", "text": "B", "stage": "verified"}])

            with self.assertRaisesRegex(ValueError, "Unsupported knowledge relation type"):
                create_knowledge_relation(
                    tmp_path,
                    source_object_id="knowledge-a",
                    target_object_id="knowledge-b",
                    relation_type="invalid_type",
                )

        self.assertIn("related_to", KNOWLEDGE_RELATION_TYPES)

    def test_delete_relation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            save_knowledge_objects(tmp_path, "task-a", [{"object_id": "knowledge-a", "text": "A", "stage": "verified"}])
            save_knowledge_objects(tmp_path, "task-b", [{"object_id": "knowledge-b", "text": "B", "stage": "verified"}])

            relation = create_knowledge_relation(
                tmp_path,
                source_object_id="knowledge-a",
                target_object_id="knowledge-b",
                relation_type="related_to",
            )
            delete_knowledge_relation(tmp_path, relation["relation_id"])
            relations = list_knowledge_relations(tmp_path, "knowledge-a")

        self.assertEqual(relations, [])

    def test_list_relations_for_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            save_knowledge_objects(tmp_path, "task-a", [{"object_id": "knowledge-a", "text": "A", "stage": "verified"}])
            save_knowledge_objects(tmp_path, "task-b", [{"object_id": "knowledge-b", "text": "B", "stage": "verified"}])
            save_knowledge_objects(tmp_path, "task-c", [{"object_id": "knowledge-c", "text": "C", "stage": "verified"}])

            create_knowledge_relation(
                tmp_path,
                source_object_id="knowledge-a",
                target_object_id="knowledge-b",
                relation_type="cites",
            )
            create_knowledge_relation(
                tmp_path,
                source_object_id="knowledge-c",
                target_object_id="knowledge-a",
                relation_type="refines",
            )

            relations = list_knowledge_relations(tmp_path, "knowledge-a")

        self.assertEqual(len(relations), 2)
        self.assertEqual({item["direction"] for item in relations}, {"incoming", "outgoing"})

    def test_relation_commands_accept_canonical_id_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            save_knowledge_objects(
                tmp_path,
                "task-a",
                [{"object_id": "knowledge-a", "text": "A", "stage": "verified"}],
            )
            save_knowledge_objects(
                tmp_path,
                "task-b",
                [{"object_id": "knowledge-b", "text": "B", "stage": "verified"}],
            )
            append_canonical_record(
                tmp_path,
                build_canonical_record(
                    task_id="task-a",
                    object_id="knowledge-a",
                    knowledge_object={
                        "object_id": "knowledge-a",
                        "text": "A",
                        "stage": "verified",
                        "artifact_ref": ".swl/tasks/task-a/artifacts/summary.md",
                        "source_ref": "file://task-a",
                        "evidence_status": "artifact_backed",
                    },
                    decision_record={"decided_at": "2026-04-25T00:00:00+00:00", "decided_by": "test"},
                ),
            )
            append_canonical_record(
                tmp_path,
                build_canonical_record(
                    task_id="task-b",
                    object_id="knowledge-b",
                    knowledge_object={
                        "object_id": "knowledge-b",
                        "text": "B",
                        "stage": "verified",
                        "artifact_ref": ".swl/tasks/task-b/artifacts/summary.md",
                        "source_ref": "file://task-b",
                        "evidence_status": "artifact_backed",
                    },
                    decision_record={"decided_at": "2026-04-25T00:00:00+00:00", "decided_by": "test"},
                ),
            )

            relation = create_knowledge_relation(
                tmp_path,
                source_object_id="canonical-task-a-knowledge-a",
                target_object_id="canonical-task-b-knowledge-b",
                relation_type="extends",
            )
            relations = list_knowledge_relations(tmp_path, "canonical-task-a-knowledge-a")

        self.assertEqual(relation["source_object_id"], "knowledge-a")
        self.assertEqual(relation["target_object_id"], "knowledge-b")
        self.assertEqual(relations[0]["counterparty_object_id"], "knowledge-b")

    def test_relation_commands_accept_source_ref_filename_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            save_knowledge_objects(
                tmp_path,
                "ingest-knowledge",
                [{"object_id": "knowledge-doc", "text": "Knowledge", "stage": "verified"}],
            )
            save_knowledge_objects(
                tmp_path,
                "ingest-architecture",
                [{"object_id": "architecture-doc", "text": "Architecture", "stage": "verified"}],
            )
            append_canonical_record(
                tmp_path,
                build_canonical_record(
                    task_id="ingest-knowledge",
                    object_id="knowledge-doc",
                    knowledge_object={
                        "object_id": "knowledge-doc",
                        "text": "Knowledge",
                        "stage": "verified",
                        "source_ref": "file:///workspace/docs/design/KNOWLEDGE.md",
                        "evidence_status": "source_only",
                    },
                    decision_record={"decided_at": "2026-04-25T00:00:00+00:00", "decided_by": "test"},
                ),
            )
            append_canonical_record(
                tmp_path,
                build_canonical_record(
                    task_id="ingest-architecture",
                    object_id="architecture-doc",
                    knowledge_object={
                        "object_id": "architecture-doc",
                        "text": "Architecture",
                        "stage": "verified",
                        "source_ref": "file:///workspace/docs/design/ARCHITECTURE.md",
                        "evidence_status": "source_only",
                    },
                    decision_record={"decided_at": "2026-04-25T00:00:00+00:00", "decided_by": "test"},
                ),
            )

            relation = create_knowledge_relation(
                tmp_path,
                source_object_id="KNOWLEDGE.md",
                target_object_id="ARCHITECTURE.md",
                relation_type="related_to",
            )

        self.assertEqual(relation["source_object_id"], "knowledge-doc")
        self.assertEqual(relation["target_object_id"], "architecture-doc")


if __name__ == "__main__":
    unittest.main()
