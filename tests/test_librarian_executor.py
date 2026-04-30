from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.knowledge_retrieval.canonical_registry import build_canonical_registry_index
from swallow.knowledge_retrieval.canonical_reuse import build_canonical_reuse_summary
from swallow.knowledge_retrieval.knowledge_index import build_knowledge_index
from swallow.knowledge_retrieval.knowledge_partition import build_knowledge_partition
from swallow.surface_tools.librarian_executor import LIBRARIAN_CHANGE_LOG_KIND, LibrarianAgent, LibrarianExecutor
from swallow.orchestration.models import TaskCard, TaskState, ValidationResult
from swallow.orchestration.orchestrator import _apply_librarian_side_effects, create_task, run_task
from swallow.surface_tools.paths import canonical_registry_index_path, canonical_reuse_policy_path, knowledge_index_path, knowledge_partition_path
from swallow.truth_governance.store import (
    append_canonical_record,
    load_state,
    save_canonical_registry_index,
    save_canonical_reuse_policy,
    save_knowledge_index,
    save_knowledge_objects,
    save_knowledge_partition,
    save_state,
)


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
    def test_librarian_agent_is_executor_compatible_entity(self) -> None:
        self.assertIsInstance(LibrarianExecutor(), LibrarianAgent)

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
            payload = json.loads(result.output)
            self.assertEqual(payload["agent_name"], "librarian")
            self.assertEqual(payload["write_authority"], "canonical-promotion")
            self.assertEqual(payload["entries"][0]["source"], "librarian")
            self.assertTrue(payload["entries"][0]["timestamp"])
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

            with patch("swallow.orchestration.orchestrator.run_retrieval", return_value=[]):
                with patch("swallow.orchestration.orchestrator.write_task_artifacts", return_value=validation_tuple):
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

    def test_run_task_rolls_back_librarian_atomic_files_when_replace_fails(self) -> None:
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
                    "object_id": "knowledge-rollback",
                    "text": "Promote   this   fact",
                    "stage": "verified",
                    "source_kind": "external_knowledge_capture",
                    "source_ref": "chat://rollback",
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
            save_knowledge_partition(tmp_path, state.task_id, build_knowledge_partition(state.knowledge_objects))
            save_knowledge_index(tmp_path, state.task_id, build_knowledge_index(state.knowledge_objects))
            save_canonical_registry_index(tmp_path, build_canonical_registry_index([]))
            save_canonical_reuse_policy(tmp_path, build_canonical_reuse_summary([]))
            (tmp_path / ".swl" / "tasks" / created.task_id / "artifacts" / "evidence.md").write_text(
                "artifact-backed evidence\n",
                encoding="utf-8",
            )

            before_state = (tmp_path / ".swl" / "tasks" / created.task_id / "state.json").read_text(encoding="utf-8")
            before_knowledge = (tmp_path / ".swl" / "tasks" / created.task_id / "knowledge_objects.json").read_text(
                encoding="utf-8"
            )
            before_partition = knowledge_partition_path(tmp_path, created.task_id).read_text(encoding="utf-8")
            before_index = knowledge_index_path(tmp_path, created.task_id).read_text(encoding="utf-8")
            before_registry_index = canonical_registry_index_path(tmp_path).read_text(encoding="utf-8")
            before_reuse = canonical_reuse_policy_path(tmp_path).read_text(encoding="utf-8")

            card = TaskCard(
                card_id="card-librarian-rollback",
                goal="Promote canonical-ready evidence with the librarian executor",
                executor_type="librarian",
                route_hint="librarian-local",
                input_context={"promotion_ready_object_ids": ["knowledge-rollback"]},
                output_schema={"type": "object", "const": {"kind": LIBRARIAN_CHANGE_LOG_KIND}},
            )
            executor_result = LibrarianExecutor().execute(tmp_path, state, card, [])

            real_replace = os.replace
            failed_once = False

            def flaky_replace(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
                nonlocal failed_once
                target = Path(dst)
                if target.name == "knowledge_index.json" and not failed_once:
                    failed_once = True
                    raise OSError("simulated replace failure")
                real_replace(src, dst)

            with patch("swallow.truth_governance.store.os.replace", side_effect=flaky_replace):
                with self.assertRaises(OSError):
                    _apply_librarian_side_effects(tmp_path, state, executor_result)

            self.assertEqual(
                (tmp_path / ".swl" / "tasks" / created.task_id / "state.json").read_text(encoding="utf-8"),
                before_state,
            )
            self.assertEqual(
                (tmp_path / ".swl" / "tasks" / created.task_id / "knowledge_objects.json").read_text(encoding="utf-8"),
                before_knowledge,
            )
            self.assertEqual(knowledge_partition_path(tmp_path, created.task_id).read_text(encoding="utf-8"), before_partition)
            self.assertEqual(knowledge_index_path(tmp_path, created.task_id).read_text(encoding="utf-8"), before_index)
            self.assertEqual(canonical_registry_index_path(tmp_path).read_text(encoding="utf-8"), before_registry_index)
            self.assertEqual(canonical_reuse_policy_path(tmp_path).read_text(encoding="utf-8"), before_reuse)
            self.assertFalse(list(tmp_path.rglob("*.tmp")))
            self.assertFalse(list(tmp_path.rglob("*.restore")))

    def test_librarian_agent_skips_existing_conflict_and_emits_structured_change_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_id = "task-librarian-conflict"
            state = TaskState(
                task_id=task_id,
                title="Skip explicit canonical conflicts",
                goal="Detect duplicate canonical keys before promotion",
                workspace_root=str(tmp_path),
                executor_name="librarian",
            )
            state.knowledge_objects = [
                {
                    "object_id": "knowledge-0002",
                    "text": "Existing canonical wording",
                    "stage": "verified",
                    "source_kind": "external_knowledge_capture",
                    "source_ref": "chat://conflict",
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
            append_canonical_record(
                tmp_path,
                {
                    "canonical_id": "canonical-existing",
                    "canonical_key": f"artifact:.swl/tasks/{task_id}/artifacts/evidence.md",
                    "source_task_id": "existing-task",
                    "source_object_id": "knowledge-existing",
                    "promoted_at": "2026-04-16T00:00:00+00:00",
                    "decision_note": "existing",
                    "canonical_status": "active",
                    "superseded_by": "",
                    "superseded_at": "",
                    "text": "Existing canonical wording",
                },
            )
            (tmp_path / ".swl" / "tasks" / task_id / "artifacts" / "evidence.md").write_text(
                "artifact-backed evidence\n",
                encoding="utf-8",
            )
            card = TaskCard(
                card_id="card-librarian-conflict",
                goal="Skip conflicting canonical evidence",
                executor_type="librarian",
                route_hint="librarian-local",
                input_context={"promotion_ready_object_ids": ["knowledge-0002"]},
                output_schema={"type": "object", "const": {"kind": LIBRARIAN_CHANGE_LOG_KIND}},
            )

            result = LibrarianAgent().execute(tmp_path, state, card, [])
            payload = json.loads(result.output)

        self.assertEqual(result.status, "completed")
        self.assertEqual(payload["promoted_count"], 0)
        self.assertEqual(payload["skipped_count"], 1)
        self.assertEqual(payload["entries"][0]["reason"], "conflict_existing_canonical_key")
        self.assertEqual(result.side_effects["knowledge_decision_records"], [])
        self.assertEqual(result.side_effects["canonical_records"], [])


if __name__ == "__main__":
    unittest.main()
