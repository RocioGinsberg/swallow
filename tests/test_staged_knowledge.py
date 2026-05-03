from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.surface_tools.paths import staged_knowledge_registry_path
from swallow.knowledge_retrieval.knowledge_plane import (
    StagedCandidate,
    decide_staged_knowledge as update_staged_candidate,
    list_staged_knowledge as load_staged_candidates,
    submit_staged_knowledge as submit_staged_candidate,
)


class StagedKnowledgeTest(unittest.TestCase):
    def test_submit_staged_candidate_persists_jsonl_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            candidate = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Promote the retry checklist once validated.",
                    source_task_id="task-123",
                    source_object_id="ko-1",
                    submitted_by="mock-remote",
                    taxonomy_role="specialist",
                    taxonomy_memory_authority="staged-knowledge",
                ),
            )

            registry_file = staged_knowledge_registry_path(tmp_path)
            registry_lines = registry_file.read_text(encoding="utf-8").splitlines()

            self.assertTrue(registry_file.exists())
            self.assertEqual(len(registry_lines), 1)

        self.assertTrue(candidate.candidate_id.startswith("staged-"))
        self.assertEqual(candidate.status, "pending")

    def test_load_staged_candidates_returns_full_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            first = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="First staged note",
                    source_task_id="task-a",
                    submitted_by="local",
                ),
            )
            second = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Second staged note",
                    source_task_id="task-b",
                    submitted_by="mock-remote",
                    taxonomy_role="specialist",
                    taxonomy_memory_authority="staged-knowledge",
                ),
            )

            candidates = load_staged_candidates(tmp_path)

        self.assertEqual([item.candidate_id for item in candidates], [first.candidate_id, second.candidate_id])
        self.assertEqual(candidates[0].text, "First staged note")
        self.assertEqual(candidates[1].taxonomy_memory_authority, "staged-knowledge")

    def test_update_staged_candidate_persists_promotion_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            candidate = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Review this as canonical guidance",
                    source_task_id="task-promote",
                    source_object_id="ko-9",
                    submitted_by="validator",
                ),
            )

            updated = update_staged_candidate(
                tmp_path,
                candidate.candidate_id,
                "promoted",
                "human-operator",
                "Approved after manual review.",
            )
            reloaded = load_staged_candidates(tmp_path)

        self.assertEqual(updated.status, "promoted")
        self.assertEqual(updated.decided_by, "human-operator")
        self.assertEqual(updated.decision_note, "Approved after manual review.")
        self.assertTrue(updated.decided_at)
        self.assertEqual(len(reloaded), 1)
        self.assertEqual(reloaded[0].status, "promoted")
        self.assertEqual(reloaded[0].decision_note, "Approved after manual review.")

    def test_topic_round_trips_through_registry_and_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            candidate = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Tag this staged note for retrieval follow-up.",
                    source_task_id="task-topic",
                    topic="retrieval",
                    submitted_by="validator",
                ),
            )

            updated = update_staged_candidate(
                tmp_path,
                candidate.candidate_id,
                "rejected",
                "human-operator",
                "Need stronger evidence.",
            )
            reloaded = load_staged_candidates(tmp_path)

        self.assertEqual(candidate.topic, "retrieval")
        self.assertEqual(updated.topic, "retrieval")
        self.assertEqual(reloaded[0].topic, "retrieval")

    def test_old_staged_candidate_record_loads_with_wiki_compiler_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            staged_knowledge_registry_path(tmp_path).parent.mkdir(parents=True)
            staged_knowledge_registry_path(tmp_path).write_text(
                json.dumps(
                    {
                        "candidate_id": "staged-oldrecord",
                        "text": "Legacy staged note.",
                        "source_task_id": "task-legacy",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            candidates = load_staged_candidates(tmp_path)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].wiki_mode, "")
        self.assertEqual(candidates[0].target_object_id, "")
        self.assertEqual(candidates[0].source_pack, [])
        self.assertEqual(candidates[0].rationale, "")
        self.assertEqual(candidates[0].relation_metadata, [])
        self.assertEqual(candidates[0].conflict_flag, "")

    def test_wiki_compiler_metadata_round_trips_through_registry_and_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            candidate = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Compiled wiki draft.",
                    source_task_id="task-wiki",
                    topic="compiler",
                    submitted_by="wiki-compiler",
                    wiki_mode="refines",
                    target_object_id="wiki-target",
                    source_pack=[
                        {
                            "source_ref": "file://workspace/notes.md",
                            "content_hash": "sha256:abc",
                            "parser_version": "wiki-compiler-v1",
                            "span": "L1-L2",
                        }
                    ],
                    rationale="Sources support the draft.",
                    relation_metadata=[{"relation_type": "refines", "target_object_id": "wiki-target"}],
                    conflict_flag="contradicts(wiki-old)",
                ),
            )

            updated = update_staged_candidate(
                tmp_path,
                candidate.candidate_id,
                "rejected",
                "human-operator",
                "Needs stronger evidence.",
            )
            reloaded = load_staged_candidates(tmp_path)

        self.assertEqual(updated.wiki_mode, "refines")
        self.assertEqual(updated.target_object_id, "wiki-target")
        self.assertEqual(updated.source_pack[0]["content_hash"], "sha256:abc")
        self.assertEqual(updated.rationale, "Sources support the draft.")
        self.assertEqual(updated.relation_metadata[0]["relation_type"], "refines")
        self.assertEqual(updated.conflict_flag, "contradicts(wiki-old)")
        self.assertEqual(reloaded[0].source_pack, updated.source_pack)
        self.assertEqual(reloaded[0].relation_metadata, updated.relation_metadata)

    def test_load_staged_candidates_returns_empty_list_when_registry_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            candidates = load_staged_candidates(tmp_path)

        self.assertEqual(candidates, [])


if __name__ == "__main__":
    unittest.main()
