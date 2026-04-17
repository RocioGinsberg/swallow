from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.librarian_executor import LIBRARIAN_CHANGE_LOG_KIND, LibrarianExecutor
from swallow.models import TaskCard, TaskState, ValidationResult
from swallow.orchestrator import create_task, run_task
from swallow.store import load_state, save_knowledge_objects, save_state


def _load_json_lines(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []

    records: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            records.append(payload)
    return records


class LibrarianExecutorIntegrationTest(unittest.TestCase):
    def test_librarian_executor_returns_side_effect_plan_without_persisting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_id = "task-librarian-side-effect"
            state = TaskState(
                task_id=task_id,
                title="Promote verified evidence",
                goal="Return a side-effect plan instead of mutating state directly",
                workspace_root=str(tmp_path),
                executor_name="librarian",
            )
            state.knowledge_objects = [
                {
                    "object_id": "knowledge-0001",
                    "text": "Promote   this   fact",
                    "stage": "verified",
                    "source_kind": "external_knowledge_capture",
                    "source_ref": "chat://librarian",
                    "task_linked": True,
                    "captured_at": "2026-04-16T00:00:00+00:00",
                    "evidence_status": "artifact_backed",
                    "artifact_ref": f".swl/tasks/{task_id}/artifacts/evidence.md",
                    "retrieval_eligible": False,
                    "knowledge_reuse_scope": "task_only",
                    "canonicalization_intent": "promote",
                }
            ]
            save_state(tmp_path, state)
            save_knowledge_objects(tmp_path, task_id, state.knowledge_objects)
            original_state = (tmp_path / ".swl" / "tasks" / task_id / "state.json").read_text(encoding="utf-8")
            original_knowledge = (tmp_path / ".swl" / "tasks" / task_id / "knowledge_objects.json").read_text(
                encoding="utf-8"
            )
            (tmp_path / ".swl" / "tasks" / task_id / "artifacts" / "evidence.md").write_text(
                "artifact-backed evidence\n",
                encoding="utf-8",
            )
            card = TaskCard(
                card_id="card-librarian",
                goal="Promote canonical-ready evidence with the librarian executor",
                executor_type="librarian",
                route_hint="librarian-local",
                input_context={"promotion_ready_object_ids": ["knowledge-0001"]},
                output_schema={"type": "object", "const": {"kind": LIBRARIAN_CHANGE_LOG_KIND}},
            )

            result = LibrarianExecutor().execute(tmp_path, state, card, [])

            self.assertEqual(result.status, "completed")
            self.assertEqual(result.executor_name, "librarian")
            self.assertEqual(result.side_effects["kind"], LIBRARIAN_CHANGE_LOG_KIND)
            self.assertEqual(len(result.side_effects["knowledge_decision_records"]), 1)
            self.assertEqual(len(result.side_effects["canonical_records"]), 1)
            self.assertEqual(result.side_effects["updated_knowledge_objects"][0]["stage"], "canonical")
            self.assertFalse((tmp_path / ".swl" / "canonical_knowledge" / "registry.jsonl").exists())
            self.assertFalse((tmp_path / ".swl" / "tasks" / task_id / "knowledge_decisions.jsonl").exists())
            self.assertFalse((tmp_path / ".swl" / "tasks" / task_id / "artifacts" / "librarian_change_log.json").exists())
            self.assertEqual((tmp_path / ".swl" / "tasks" / task_id / "state.json").read_text(encoding="utf-8"), original_state)
            self.assertEqual(
                (tmp_path / ".swl" / "tasks" / task_id / "knowledge_objects.json").read_text(encoding="utf-8"),
                original_knowledge,
            )

    def test_run_task_promotes_local_promotion_ready_evidence_with_librarian_executor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            created = create_task(
                base_dir=tmp_path,
                title="Promote verified evidence",
                goal="Promote canonical-ready evidence with the librarian executor",
                workspace_root=tmp_path,
                executor_name="local",
            )
            state = load_state(tmp_path, created.task_id)
            state.knowledge_objects = [
                {
                    "object_id": "knowledge-0001",
                    "text": "Promote   this   fact",
                    "stage": "verified",
                    "source_kind": "external_knowledge_capture",
                    "source_ref": "chat://librarian",
                    "task_linked": True,
                    "captured_at": "2026-04-16T00:00:00+00:00",
                    "evidence_status": "artifact_backed",
                    "artifact_ref": f".swl/tasks/{created.task_id}/artifacts/evidence.md",
                    "retrieval_eligible": False,
                    "knowledge_reuse_scope": "task_only",
                    "canonicalization_intent": "promote",
                }
            ]
            save_state(tmp_path, state)
            save_knowledge_objects(tmp_path, state.task_id, state.knowledge_objects)
            (tmp_path / ".swl" / "tasks" / created.task_id / "artifacts" / "evidence.md").write_text(
                "artifact-backed evidence\n",
                encoding="utf-8",
            )

            validation_tuple = (
                ValidationResult(status="passed", message="Compatibility passed."),
                ValidationResult(status="passed", message="Execution fit passed."),
                ValidationResult(status="passed", message="Knowledge policy passed."),
                ValidationResult(status="passed", message="Validation passed."),
                ValidationResult(status="passed", message="Retry policy passed."),
                ValidationResult(status="passed", message="Execution budget policy passed."),
                ValidationResult(status="warning", message="Stop policy warning."),
            )

            with patch("swallow.orchestrator.run_retrieval", return_value=[]):
                with patch("swallow.orchestrator.write_task_artifacts", return_value=validation_tuple):
                    final_state = run_task(tmp_path, created.task_id, executor_name="local")

            change_log_path = tmp_path / ".swl" / "tasks" / created.task_id / "artifacts" / "librarian_change_log.json"
            change_log = json.loads(change_log_path.read_text(encoding="utf-8"))
            canonical_records = _load_json_lines(tmp_path / ".swl" / "canonical_knowledge" / "registry.jsonl")
            events = _load_json_lines(tmp_path / ".swl" / "tasks" / created.task_id / "events.jsonl")
            decisions = _load_json_lines(tmp_path / ".swl" / "tasks" / created.task_id / "knowledge_decisions.jsonl")
            self.assertEqual(final_state.status, "completed")
            self.assertEqual(final_state.executor_name, "librarian")
            self.assertEqual(final_state.knowledge_objects[0]["stage"], "canonical")
            self.assertEqual(final_state.knowledge_objects[0]["text"], "Promote this fact")
            self.assertEqual(
                final_state.artifact_paths["librarian_change_log"],
                str(change_log_path.resolve()),
            )
            self.assertTrue(change_log_path.exists())
            self.assertEqual(change_log["kind"], "librarian_change_log_v0")
            self.assertEqual(change_log["candidate_count"], 1)
            self.assertEqual(change_log["promoted_count"], 1)
            self.assertEqual(change_log["skipped_count"], 0)
            self.assertEqual(canonical_records[-1]["source_object_id"], "knowledge-0001")
            self.assertEqual(
                canonical_records[-1]["decision_ref"],
                f".swl/tasks/{created.task_id}/artifacts/librarian_change_log.json#knowledge-0001",
            )
            self.assertEqual(decisions[-1]["caller_authority"], "canonical-promotion")
            planned_event = next(event for event in events if event["event_type"] == "task.planned")
            self.assertEqual(planned_event["payload"]["executor_type"], "librarian")
            review_gate_event = next(event for event in events if event["event_type"] == "task.review_gate")
            self.assertEqual(review_gate_event["payload"]["status"], "passed")
            self.assertTrue(
                any(
                    check["name"] == "output_schema" and check["passed"]
                    for check in review_gate_event["payload"]["checks"]
                )
            )


if __name__ == "__main__":
    unittest.main()
