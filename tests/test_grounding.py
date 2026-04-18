from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.grounding import build_grounding_evidence, build_grounding_evidence_report, extract_grounding_entries
from swallow.harness import write_task_artifacts
from swallow.models import ExecutorResult, RetrievalItem, TaskState


def _build_task_state(
    tmp_path: Path,
    task_id: str,
    *,
    status: str = "created",
    phase: str = "intake",
    execution_lifecycle: str = "idle",
) -> TaskState:
    artifacts_path = tmp_path / ".swl" / "tasks" / task_id / "artifacts"
    artifacts_path.mkdir(parents=True, exist_ok=True)
    return TaskState(
        task_id=task_id,
        title="Grounding artifact",
        goal="Persist grounding evidence artifacts",
        workspace_root=str(tmp_path),
        status=status,
        phase=phase,
        execution_lifecycle=execution_lifecycle,
        knowledge_objects=[],
        artifact_paths={
            "source_grounding": str((artifacts_path / "source_grounding.md").resolve()),
            "grounding_evidence_json": str((artifacts_path / "grounding_evidence.json").resolve()),
            "grounding_evidence_report": str((artifacts_path / "grounding_evidence_report.md").resolve()),
            "retrieval_report": str((artifacts_path / "retrieval_report.md").resolve()),
            "retrieval_json": str((tmp_path / ".swl" / "tasks" / task_id / "retrieval.json").resolve()),
            "summary": str((artifacts_path / "summary.md").resolve()),
            "resume_note": str((artifacts_path / "resume_note.md").resolve()),
            "route_report": str((artifacts_path / "route_report.md").resolve()),
            "topology_report": str((artifacts_path / "topology_report.md").resolve()),
            "execution_site_report": str((artifacts_path / "execution_site_report.md").resolve()),
            "dispatch_report": str((artifacts_path / "dispatch_report.md").resolve()),
            "remote_handoff_contract_report": str((artifacts_path / "remote_handoff_contract_report.md").resolve()),
            "knowledge_index_report": str((artifacts_path / "knowledge_index_report.md").resolve()),
            "compatibility_report": str((artifacts_path / "compatibility_report.md").resolve()),
            "validation_report": str((artifacts_path / "validation_report.md").resolve()),
            "task_memory": str((tmp_path / ".swl" / "tasks" / task_id / "memory.json").resolve()),
            "knowledge_index_json": str((tmp_path / ".swl" / "tasks" / task_id / "knowledge_index.json").resolve()),
            "route_json": str((tmp_path / ".swl" / "tasks" / task_id / "route.json").resolve()),
            "topology_json": str((tmp_path / ".swl" / "tasks" / task_id / "topology.json").resolve()),
            "execution_site_json": str((tmp_path / ".swl" / "tasks" / task_id / "execution_site.json").resolve()),
            "dispatch_json": str((tmp_path / ".swl" / "tasks" / task_id / "dispatch.json").resolve()),
            "handoff_json": str((tmp_path / ".swl" / "tasks" / task_id / "handoff.json").resolve()),
            "remote_handoff_contract_json": str(
                (tmp_path / ".swl" / "tasks" / task_id / "remote_handoff_contract.json").resolve()
            ),
            "compatibility_json": str((tmp_path / ".swl" / "tasks" / task_id / "compatibility.json").resolve()),
            "validation_json": str((tmp_path / ".swl" / "tasks" / task_id / "validation.json").resolve()),
            "knowledge_policy_json": str((tmp_path / ".swl" / "tasks" / task_id / "knowledge_policy.json").resolve()),
            "knowledge_policy_report": str((artifacts_path / "knowledge_policy_report.md").resolve()),
            "canonical_reuse_policy_report": str((artifacts_path / "canonical_reuse_policy_report.md").resolve()),
            "canonical_reuse_policy_json": str((tmp_path / ".swl" / "canonical_knowledge" / "reuse_policy.json").resolve()),
            "execution_fit_report": str((artifacts_path / "execution_fit_report.md").resolve()),
            "execution_fit_json": str((tmp_path / ".swl" / "tasks" / task_id / "execution_fit.json").resolve()),
            "retry_policy_report": str((artifacts_path / "retry_policy_report.md").resolve()),
            "retry_policy_json": str((tmp_path / ".swl" / "tasks" / task_id / "retry_policy.json").resolve()),
            "execution_budget_policy_report": str((artifacts_path / "execution_budget_policy_report.md").resolve()),
            "execution_budget_policy_json": str(
                (tmp_path / ".swl" / "tasks" / task_id / "execution_budget_policy.json").resolve()
            ),
            "stop_policy_report": str((artifacts_path / "stop_policy_report.md").resolve()),
            "stop_policy_json": str((tmp_path / ".swl" / "tasks" / task_id / "stop_policy.json").resolve()),
            "checkpoint_snapshot_report": str((artifacts_path / "checkpoint_snapshot_report.md").resolve()),
            "checkpoint_snapshot_json": str((tmp_path / ".swl" / "tasks" / task_id / "checkpoint_snapshot.json").resolve()),
            "handoff_report": str((artifacts_path / "handoff_report.md").resolve()),
        },
    )


class GroundingTest(unittest.TestCase):
    def test_extract_grounding_entries_returns_only_canonical_registry_items(self) -> None:
        retrieval_items = [
            RetrievalItem(
                path=".swl/canonical_knowledge/reuse_policy.json",
                source_type="knowledge",
                score=9,
                preview="Canonical fact for retrieval grounding.",
                citation=".swl/canonical_knowledge/reuse_policy.json#canonical-a",
                metadata={
                    "storage_scope": "canonical_registry",
                    "canonical_id": "canonical-a",
                    "canonical_key": "task-object:task-a:object-1",
                    "knowledge_task_id": "task-a",
                    "evidence_status": "source_only",
                },
            ),
            RetrievalItem(
                path="README.md",
                source_type="docs",
                score=3,
                preview="Non-canonical retrieval result.",
                citation="README.md#L1-L3",
                metadata={"storage_scope": "task_artifacts"},
            ),
        ]

        entries = extract_grounding_entries(retrieval_items)

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].canonical_id, "canonical-a")
        self.assertEqual(entries[0].canonical_key, "task-object:task-a:object-1")
        self.assertEqual(entries[0].citation, "canonical:canonical-a")
        self.assertEqual(entries[0].source_task_id, "task-a")
        self.assertEqual(entries[0].evidence_status, "source_only")
        self.assertEqual(entries[0].score, 9)

    def test_extract_grounding_entries_returns_empty_for_non_canonical_results(self) -> None:
        retrieval_items = [
            RetrievalItem(
                path="README.md",
                source_type="docs",
                score=1,
                preview="General repo result.",
                citation="README.md#L1",
                metadata={"storage_scope": "task_artifacts"},
            )
        ]

        self.assertEqual(extract_grounding_entries(retrieval_items), [])

    def test_build_grounding_evidence_report_formats_entries(self) -> None:
        evidence = build_grounding_evidence(
            extract_grounding_entries(
                [
                    RetrievalItem(
                        path=".swl/canonical_knowledge/reuse_policy.json",
                        source_type="knowledge",
                        score=8,
                        preview="Grounded canonical note.",
                        citation=".swl/canonical_knowledge/reuse_policy.json#canonical-b",
                        metadata={
                            "storage_scope": "canonical_registry",
                            "canonical_id": "canonical-b",
                            "canonical_key": "task-object:task-b:object-2",
                            "knowledge_task_id": "task-b",
                            "evidence_status": "artifact_backed",
                        },
                    )
                ]
            )
        )

        report = build_grounding_evidence_report(evidence)

        self.assertIn("Grounding Evidence", report)
        self.assertIn("entry_count: 1", report)
        self.assertIn("canonical:canonical-b", report)
        self.assertIn("canonical_key: task-object:task-b:object-2", report)
        self.assertIn("score: 8", report)

    def test_write_task_artifacts_persists_grounding_evidence_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_id = "task-grounding"
            artifacts_path = tmp_path / ".swl" / "tasks" / task_id / "artifacts"
            state = _build_task_state(tmp_path, task_id)
            retrieval_items = [
                RetrievalItem(
                    path=".swl/canonical_knowledge/reuse_policy.json",
                    source_type="knowledge",
                    score=7,
                    preview="Canonical grounding entry.",
                    citation=".swl/canonical_knowledge/reuse_policy.json#canonical-c",
                    metadata={
                        "storage_scope": "canonical_registry",
                        "canonical_id": "canonical-c",
                        "canonical_key": "task-object:task-c:object-3",
                        "knowledge_task_id": "task-c",
                        "evidence_status": "source_only",
                    },
                )
            ]
            executor_result = ExecutorResult(
                executor_name="codex",
                status="completed",
                message="done",
                output="Grounding artifact execution output.",
            )

            write_task_artifacts(tmp_path, state, retrieval_items, executor_result)

            grounding_json = json.loads((artifacts_path / "grounding_evidence.json").read_text(encoding="utf-8"))
            grounding_report = (artifacts_path / "grounding_evidence_report.md").read_text(encoding="utf-8")

        self.assertEqual(grounding_json["entry_count"], 1)
        self.assertEqual(grounding_json["entries"][0]["canonical_id"], "canonical-c")
        self.assertEqual(grounding_json["entries"][0]["citation"], "canonical:canonical-c")
        self.assertIn("Grounding Evidence", grounding_report)
        self.assertIn("canonical:canonical-c", grounding_report)

    def test_write_task_artifacts_preserves_waiting_human_checkpoint_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_id = "task-debate-waiting"
            state = _build_task_state(
                tmp_path,
                task_id,
                status="waiting_human",
                phase="waiting_human",
                execution_lifecycle="waiting_human",
            )
            executor_result = ExecutorResult(
                executor_name="local",
                status="failed",
                message="Debate loop exhausted the maximum review rounds; waiting for human intervention.",
                output="",
                failure_kind="debate_circuit_breaker",
            )

            write_task_artifacts(tmp_path, state, [], executor_result)

            checkpoint_snapshot = json.loads(
                (tmp_path / ".swl" / "tasks" / task_id / "checkpoint_snapshot.json").read_text(encoding="utf-8")
            )
            task_memory = json.loads((tmp_path / ".swl" / "tasks" / task_id / "memory.json").read_text(encoding="utf-8"))

        self.assertEqual(checkpoint_snapshot["checkpoint_state"], "waiting_human")
        self.assertEqual(checkpoint_snapshot["recovery_semantics"], "human_gate_debate_exhausted")
        self.assertEqual(checkpoint_snapshot["recommended_path"], "run")
        self.assertEqual(task_memory["status"], "waiting_human")


if __name__ == "__main__":
    unittest.main()
