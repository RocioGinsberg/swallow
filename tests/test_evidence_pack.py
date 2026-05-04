from __future__ import annotations

import sys
import tempfile
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.knowledge_retrieval.evidence_pack import build_evidence_pack
from swallow.orchestration.models import RetrievalItem
from swallow.application.infrastructure.paths import artifacts_dir


class EvidencePackTest(unittest.TestCase):
    def test_build_evidence_pack_groups_truth_supporting_and_fallback_hits(self) -> None:
        items = [
            RetrievalItem(
                path=".swl/canonical_knowledge/reuse_policy.json",
                source_type="knowledge",
                score=99,
                preview="Canonical truth.",
                citation=".swl/canonical_knowledge/reuse_policy.json#canonical-1",
                metadata={
                    "final_rank": 1,
                    "source_policy_label": "canonical_truth",
                    "source_policy_flags": ["primary_truth_candidate"],
                    "canonical_id": "canonical-1",
                    "knowledge_object_id": "knowledge-1",
                    "evidence_status": "source_only",
                    "source_ref": "file://workspace/docs/design/INVARIANTS.md",
                },
            ),
            RetrievalItem(
                path=".swl/tasks/task-1/artifacts/evidence.md",
                source_type="artifacts",
                score=20,
                preview="Supporting artifact.",
                citation=".swl/tasks/task-1/artifacts/evidence.md#L3-L5",
                metadata={
                    "final_rank": 2,
                    "source_policy_label": "artifact_source",
                    "source_policy_flags": ["fallback_text_hit"],
                    "artifact_ref": ".swl/tasks/task-1/artifacts/evidence.md",
                    "line_start": 3,
                    "line_end": 5,
                },
            ),
            RetrievalItem(
                path="docs/archive_phases/phase64/design_decision.md",
                source_type="notes",
                score=18,
                preview="Historical note.",
                citation="docs/archive_phases/phase64/design_decision.md#L1",
                metadata={
                    "final_rank": 3,
                    "source_policy_label": "archive_note",
                    "source_policy_flags": ["operator_context_noise", "fallback_text_hit"],
                },
            ),
        ]

        pack = build_evidence_pack(items)
        summary = pack.summary()

        self.assertEqual(summary["primary_object_count"], 1)
        self.assertEqual(summary["canonical_object_count"], 1)
        self.assertEqual(summary["supporting_evidence_count"], 1)
        self.assertEqual(summary["fallback_hit_count"], 2)
        self.assertEqual(summary["source_pointer_count"], 3)
        self.assertEqual(pack.canonical_objects[0]["canonical_id"], "canonical-1")
        self.assertEqual(pack.source_pointers[1].line_start, 3)
        self.assertEqual(pack.source_pointers[1].line_end, 5)

    def test_evidence_pack_to_dict_preserves_source_pointers(self) -> None:
        pack = build_evidence_pack(
            [
                RetrievalItem(
                    path="current_state.md",
                    source_type="notes",
                    score=4,
                    preview="State note.",
                    metadata={
                        "source_policy_label": "current_state",
                        "source_policy_flags": ["operator_context_noise", "fallback_text_hit"],
                    },
                )
            ]
        )

        payload = pack.to_dict()

        self.assertEqual(payload["fallback_hits"][0]["source_policy_label"], "current_state")
        self.assertEqual(payload["source_pointers"][0]["path"], "current_state.md")

    def test_build_evidence_pack_infers_policy_for_legacy_retrieval_items(self) -> None:
        pack = build_evidence_pack(
            [
                RetrievalItem(
                    path=".swl/canonical_knowledge/reuse_policy.json",
                    source_type="knowledge",
                    score=42,
                    preview="Canonical item without source policy metadata.",
                    citation=".swl/canonical_knowledge/reuse_policy.json#canonical-legacy",
                    metadata={
                        "storage_scope": "canonical_registry",
                        "canonical_id": "canonical-legacy",
                        "source_ref": "file://workspace/docs/design/INVARIANTS.md",
                    },
                ),
                RetrievalItem(
                    path="docs/archive_phases/phase64/design_decision.md",
                    source_type="notes",
                    score=12,
                    preview="Archive item without source policy metadata.",
                    citation="docs/archive_phases/phase64/design_decision.md#L1-L3",
                ),
            ]
        )

        summary = pack.summary()

        self.assertEqual(summary["primary_object_count"], 1)
        self.assertEqual(summary["canonical_object_count"], 1)
        self.assertEqual(summary["fallback_hit_count"], 1)
        self.assertEqual(pack.primary_objects[0]["source_policy_label"], "canonical_truth")
        self.assertEqual(pack.primary_objects[0]["source_policy_flags"], ["primary_truth_candidate"])
        self.assertEqual(pack.fallback_hits[0]["source_policy_label"], "archive_note")

    def test_source_pointers_resolve_workspace_files_and_legacy_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            note_path = base_dir / "docs" / "design" / "KNOWLEDGE.md"
            note_path.parent.mkdir(parents=True)
            note_path.write_text("# Knowledge\n\nEvidence body.\n", encoding="utf-8")
            artifact_path = artifacts_dir(base_dir, "task-1") / "evidence.md"
            artifact_path.parent.mkdir(parents=True)
            artifact_path.write_text("artifact body", encoding="utf-8")

            pack = build_evidence_pack(
                [
                    RetrievalItem(
                        path=".swl/canonical_knowledge/reuse_policy.json",
                        source_type="knowledge",
                        score=10,
                        preview="Canonical with source ref.",
                        citation=".swl/canonical_knowledge/reuse_policy.json#canonical-source",
                        title="Knowledge",
                        metadata={
                            "storage_scope": "canonical_registry",
                            "canonical_id": "canonical-source",
                            "source_ref": "file://workspace/docs/design/KNOWLEDGE.md",
                            "line_start": 1,
                            "line_end": 3,
                            "title_source": "heading",
                        },
                    ),
                    RetrievalItem(
                        path=".swl/tasks/task-1/artifacts/evidence.md",
                        source_type="artifacts",
                        score=8,
                        preview="Artifact evidence.",
                        citation=".swl/tasks/task-1/artifacts/evidence.md#L1",
                        metadata={
                            "artifact_ref": ".swl/tasks/task-1/artifacts/evidence.md",
                            "line_start": 1,
                            "line_end": 1,
                        },
                    ),
                ],
                workspace_root=base_dir,
                base_dir=base_dir,
            )

        self.assertEqual(pack.source_pointers[0].resolution_status, "resolved")
        self.assertEqual(pack.source_pointers[0].resolved_ref, "file://workspace/docs/design/KNOWLEDGE.md")
        self.assertEqual(pack.source_pointers[0].resolved_path, "docs/design/KNOWLEDGE.md")
        self.assertEqual(pack.source_pointers[0].heading_path, "Knowledge")
        self.assertEqual(pack.source_pointers[1].resolution_status, "resolved")
        self.assertEqual(pack.source_pointers[1].resolved_ref, "artifact://task-1/evidence.md")
        self.assertEqual(pack.source_pointers[1].resolved_path, ".swl/tasks/task-1/artifacts/evidence.md")


if __name__ == "__main__":
    unittest.main()
