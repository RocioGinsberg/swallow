from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.consistency_audit import ConsistencyAuditResult
from swallow.consistency_reviewer import (
    CONSISTENCY_REVIEWER_MEMORY_AUTHORITY,
    CONSISTENCY_REVIEWER_SYSTEM_ROLE,
    ConsistencyReviewerAgent,
)
from swallow.ingestion_specialist import (
    INGESTION_SPECIALIST_MEMORY_AUTHORITY,
    INGESTION_SPECIALIST_SYSTEM_ROLE,
    IngestionSpecialistAgent,
)
from swallow.models import ExecutorResult, RetrievalItem, TaskCard, TaskState
from swallow.validator_agent import VALIDATOR_MEMORY_AUTHORITY, VALIDATOR_SYSTEM_ROLE, ValidatorAgent


class SpecialistAgentTest(unittest.TestCase):
    def test_ingestion_specialist_agent_wraps_pipeline_and_returns_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "session.md"
            source.write_text("# Decisions\nDecision: keep staged review manual.", encoding="utf-8")
            state = TaskState(
                task_id="ingest-task",
                title="Ingest notes",
                goal="Wrap the ingestion pipeline as an agent",
                workspace_root=str(tmp_path),
            )
            card = TaskCard(
                goal="Ingest one exported conversation",
                parent_task_id=state.task_id,
                input_context={"source_path": str(source)},
            )

            result = IngestionSpecialistAgent().execute(tmp_path, state, card, [])

        self.assertEqual(IngestionSpecialistAgent.system_role, INGESTION_SPECIALIST_SYSTEM_ROLE)
        self.assertEqual(IngestionSpecialistAgent.memory_authority, INGESTION_SPECIALIST_MEMORY_AUTHORITY)
        self.assertEqual(result.executor_name, "ingestion-specialist")
        self.assertEqual(result.status, "completed")
        self.assertIn("# Ingestion Report", result.output)
        self.assertIn("# Ingestion Summary", result.output)
        self.assertEqual(result.side_effects["staged_candidate_count"], 1)

    def test_consistency_reviewer_agent_wraps_consistency_audit(self) -> None:
        state = TaskState(
            task_id="review-task",
            title="Audit task",
            goal="Wrap consistency audit as an agent",
            workspace_root="/tmp",
        )
        card = TaskCard(
            goal="Audit the current task artifact",
            parent_task_id=state.task_id,
            input_context={"auditor_route": "http-claude"},
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            expected = ConsistencyAuditResult(
                status="completed",
                verdict="pass",
                message="Consistency audit completed.",
                task_id=state.task_id,
                auditor_route="http-claude",
                sample_artifact_path="executor_output.md",
                audit_artifact=".swl/tasks/review-task/artifacts/consistency_audit_test.md",
                raw_output="# Consistency Audit\n- verdict: pass\n",
            )
            with patch("swallow.consistency_reviewer.run_consistency_audit", return_value=expected) as audit_mock:
                result = ConsistencyReviewerAgent().execute(tmp_path, state, card, [])

        self.assertEqual(ConsistencyReviewerAgent.system_role, CONSISTENCY_REVIEWER_SYSTEM_ROLE)
        self.assertEqual(ConsistencyReviewerAgent.memory_authority, CONSISTENCY_REVIEWER_MEMORY_AUTHORITY)
        audit_mock.assert_called_once_with(
            tmp_path,
            state.task_id,
            auditor_route="http-claude",
            sample_artifact_path="executor_output.md",
        )
        payload = json.loads(result.output)
        self.assertEqual(result.executor_name, "consistency-reviewer")
        self.assertEqual(result.status, "completed")
        self.assertEqual(payload["verdict"], "pass")
        self.assertEqual(result.side_effects["audit_artifact"], expected.audit_artifact)

    def test_validator_agent_validates_artifacts_using_reconstructed_executor_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output_path = tmp_path / "executor_output.md"
            output_path.write_text("done", encoding="utf-8")
            artifact_paths = {
                "executor_prompt": __file__,
                "executor_output": str(output_path),
                "executor_stdout": __file__,
                "executor_stderr": __file__,
                "summary": __file__,
                "resume_note": __file__,
                "compatibility_report": __file__,
                "source_grounding": __file__,
            }
            state = TaskState(
                task_id="validator-task",
                title="Validate artifacts",
                goal="Wrap validation as an agent",
                workspace_root=str(tmp_path),
                artifact_paths=artifact_paths,
            )
            card = TaskCard(
                goal="Validate existing task artifacts",
                parent_task_id=state.task_id,
            )
            retrieval_items = [RetrievalItem(path="notes.md", source_type="notes", score=1, preview="context")]

            result = ValidatorAgent().execute(tmp_path, state, card, retrieval_items)

        self.assertEqual(ValidatorAgent.system_role, VALIDATOR_SYSTEM_ROLE)
        self.assertEqual(ValidatorAgent.memory_authority, VALIDATOR_MEMORY_AUTHORITY)
        self.assertEqual(result.executor_name, "validator")
        self.assertEqual(result.status, "completed")
        self.assertIn("# Validation Report", result.output)
        self.assertIn("[pass] artifacts.complete", result.output)
        self.assertIn("[pass] executor.consistent", result.output)

    def test_validator_agent_returns_failed_status_when_validation_finds_blocking_issue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = TaskState(
                task_id="validator-fail",
                title="Validate missing output",
                goal="Expose blocking validation failures",
                workspace_root=str(tmp_path),
            )
            artifact_paths = {
                "executor_prompt": __file__,
                "executor_output": str(tmp_path / "missing-output.md"),
                "executor_stdout": __file__,
                "executor_stderr": __file__,
                "summary": __file__,
                "resume_note": __file__,
                "compatibility_report": __file__,
                "source_grounding": __file__,
            }
            card = TaskCard(
                goal="Validate task artifacts with missing output",
                parent_task_id=state.task_id,
                input_context={"artifact_paths": artifact_paths},
            )

            result = ValidatorAgent().execute(tmp_path, state, card, [])

        self.assertEqual(result.status, "failed")
        self.assertIn("[fail] executor.empty_output", result.output)
