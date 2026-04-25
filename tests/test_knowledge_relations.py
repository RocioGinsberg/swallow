from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.knowledge_relations import (
    KNOWLEDGE_RELATION_TYPES,
    create_knowledge_relation,
    delete_knowledge_relation,
    list_knowledge_relations,
)
from swallow.store import save_knowledge_objects


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


if __name__ == "__main__":
    unittest.main()
