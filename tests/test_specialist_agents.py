from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.consistency_audit import ConsistencyAuditResult
from swallow.agent_llm import AgentLLMResponse, AgentLLMUnavailable
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
from swallow.literature_specialist import (
    LITERATURE_SPECIALIST_MEMORY_AUTHORITY,
    LITERATURE_SPECIALIST_SYSTEM_ROLE,
    LiteratureSpecialistAgent,
)
from swallow.models import (
    ExecutorResult,
    RetrievalItem,
    RouteCapabilities,
    RouteSelection,
    RouteSpec,
    TaskCard,
    TaskState,
    TaxonomyProfile,
    ValidationResult,
)
from swallow.orchestrator import create_task, run_task
from swallow.quality_reviewer import (
    QUALITY_REVIEWER_MEMORY_AUTHORITY,
    QUALITY_REVIEWER_SYSTEM_ROLE,
    QualityReviewerAgent,
)
from swallow.validator_agent import VALIDATOR_MEMORY_AUTHORITY, VALIDATOR_SYSTEM_ROLE, ValidatorAgent


def _passing_validation_tuple() -> tuple[ValidationResult, ...]:
    return (
        ValidationResult(status="passed", message="Compatibility passed."),
        ValidationResult(status="passed", message="Execution fit passed."),
        ValidationResult(status="passed", message="Knowledge policy passed."),
        ValidationResult(status="passed", message="Validation passed."),
        ValidationResult(status="passed", message="Retry policy passed."),
        ValidationResult(status="warning", message="Stop policy warning."),
        ValidationResult(status="passed", message="Execution budget policy passed."),
    )


def _load_events(base_dir: Path, task_id: str) -> list[dict[str, object]]:
    events_path = base_dir / ".swl" / "tasks" / task_id / "events.jsonl"
    return [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]


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

    def test_literature_specialist_agent_summarizes_documents_and_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            doc_a = tmp_path / "doc-a.md"
            doc_b = tmp_path / "doc-b.md"
            doc_a.write_text(
                "# Overview\nSwallow keeps task state explicit.\n\n## Routing\nParallel routing stays visible.",
                encoding="utf-8",
            )
            doc_b.write_text(
                "# Overview\nSwallow tracks artifacts and routing decisions.\n\n## Findings\nParallel review stays visible.",
                encoding="utf-8",
            )
            state = TaskState(
                task_id="literature-task",
                title="Compare reference docs",
                goal="Build a lightweight literature summary",
                workspace_root=str(tmp_path),
            )
            card = TaskCard(
                goal="Compare two design notes",
                parent_task_id=state.task_id,
                input_context={"document_paths": [str(doc_a), str(doc_b)]},
            )

            result = LiteratureSpecialistAgent().execute(tmp_path, state, card, [])

        self.assertEqual(LiteratureSpecialistAgent.system_role, LITERATURE_SPECIALIST_SYSTEM_ROLE)
        self.assertEqual(LiteratureSpecialistAgent.memory_authority, LITERATURE_SPECIALIST_MEMORY_AUTHORITY)
        self.assertEqual(result.executor_name, "literature-specialist")
        self.assertEqual(result.status, "completed")
        self.assertIn("# Literature Analysis", result.output)
        self.assertIn("shared_headings: Overview", result.output)
        self.assertIn("analysis_method: heuristic", result.output)

    def test_literature_specialist_uses_llm_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            doc_a = tmp_path / "doc-a.md"
            doc_b = tmp_path / "doc-b.md"
            doc_a.write_text("# Source\nArchitecture authority is explicit.\n", encoding="utf-8")
            doc_b.write_text("# Target\nExecution policy depends on authority.\n", encoding="utf-8")
            state = TaskState(
                task_id="literature-llm-task",
                title="Compare reference docs",
                goal="Build a semantic literature summary",
                workspace_root=str(tmp_path),
            )
            card = TaskCard(
                goal="Compare two design notes",
                parent_task_id=state.task_id,
                input_context={"document_paths": [str(doc_a), str(doc_b)]},
            )

            with patch(
                "swallow.literature_specialist.call_agent_llm",
                return_value=AgentLLMResponse(
                    content=json.dumps(
                        {
                            "summary": "The documents describe authority boundaries and execution policy coupling.",
                            "key_concepts": ["authority", "execution policy"],
                            "relation_suggestions": [
                                {
                                    "source_object_id": "knowledge-0001",
                                    "target_object_id": "knowledge-0002",
                                    "relation_type": "extends",
                                    "confidence": 0.88,
                                    "context": "The execution policy extends the authority contract.",
                                }
                            ],
                        }
                    ),
                    input_tokens=120,
                    output_tokens=48,
                    model="deepseek-chat",
                ),
            ):
                result = LiteratureSpecialistAgent().execute(tmp_path, state, card, [])

        self.assertEqual(result.status, "completed")
        self.assertIn("analysis_method: llm", result.output)
        self.assertIn("authority", result.output)
        self.assertEqual(result.side_effects["analysis_method"], "llm")
        self.assertEqual(result.side_effects["llm_usage"]["input_tokens"], 120)
        self.assertEqual(result.side_effects["llm_usage"]["output_tokens"], 48)
        self.assertEqual(result.side_effects["llm_usage"]["model"], "deepseek-chat")
        self.assertEqual(len(result.side_effects["relation_suggestions"]), 1)
        self.assertEqual(result.estimated_input_tokens, 120)
        self.assertEqual(result.estimated_output_tokens, 48)

    def test_literature_specialist_falls_back_to_heuristic_on_llm_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            doc_a = tmp_path / "doc-a.md"
            doc_b = tmp_path / "doc-b.md"
            doc_a.write_text("# Overview\nSwallow keeps task state explicit.\n", encoding="utf-8")
            doc_b.write_text("# Overview\nSwallow keeps route state explicit.\n", encoding="utf-8")
            state = TaskState(
                task_id="literature-fallback-task",
                title="Compare reference docs",
                goal="Build a resilient literature summary",
                workspace_root=str(tmp_path),
            )
            card = TaskCard(
                goal="Compare two design notes",
                parent_task_id=state.task_id,
                input_context={"document_paths": [str(doc_a), str(doc_b)]},
            )

            with patch(
                "swallow.literature_specialist.call_agent_llm",
                side_effect=AgentLLMUnavailable("timeout"),
            ):
                result = LiteratureSpecialistAgent().execute(tmp_path, state, card, [])

        self.assertEqual(result.status, "completed")
        self.assertIn("analysis_method: heuristic", result.output)
        self.assertEqual(result.side_effects["analysis_method"], "heuristic")
        self.assertEqual(result.side_effects["relation_suggestions"], [])
        self.assertEqual(result.side_effects["llm_usage"], {})

    def test_quality_reviewer_agent_reports_pass_for_structured_actionable_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            artifact = tmp_path / "artifact.md"
            artifact.write_text(
                "# Summary\n\n- Next step: implement the specialist agent.\n\n```text\nDone\n```\n",
                encoding="utf-8",
            )
            state = TaskState(
                task_id="quality-task",
                title="Review artifact quality",
                goal="Check a generated artifact",
                workspace_root=str(tmp_path),
            )
            card = TaskCard(
                goal="Review one artifact",
                parent_task_id=state.task_id,
                input_context={
                    "artifact_ref": str(artifact),
                    "quality_criteria": ["non_empty", "has_structure", "has_actionable_content", "min_length"],
                    "min_length": 20,
                },
            )

            result = QualityReviewerAgent().execute(tmp_path, state, card, [])

        self.assertEqual(QualityReviewerAgent.system_role, QUALITY_REVIEWER_SYSTEM_ROLE)
        self.assertEqual(QualityReviewerAgent.memory_authority, QUALITY_REVIEWER_MEMORY_AUTHORITY)
        self.assertEqual(result.executor_name, "quality-reviewer")
        self.assertEqual(result.status, "completed")
        self.assertIn("# Quality Review", result.output)
        self.assertIn("overall_verdict: pass", result.output)
        self.assertEqual(result.side_effects["overall_verdict"], "pass")

    def test_quality_reviewer_uses_llm_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            artifact = tmp_path / "artifact.md"
            artifact.write_text(
                "# Summary\n\n- Next step: implement the specialist agent.\n\n```text\nDone\n```\n",
                encoding="utf-8",
            )
            state = TaskState(
                task_id="quality-llm-task",
                title="Review artifact quality",
                goal="Check semantic quality",
                workspace_root=str(tmp_path),
            )
            card = TaskCard(
                goal="Review one artifact",
                parent_task_id=state.task_id,
                input_context={
                    "artifact_ref": str(artifact),
                    "quality_criteria": ["non_empty", "has_structure", "has_actionable_content", "min_length"],
                    "min_length": 20,
                },
            )

            with patch(
                "swallow.quality_reviewer.call_agent_llm",
                return_value=AgentLLMResponse(
                    content=json.dumps(
                        {
                            "verdicts": [
                                {"name": "coherence", "verdict": "pass", "detail": "Argument flow stays consistent."},
                                {
                                    "name": "completeness",
                                    "verdict": "warn",
                                    "detail": "Implementation detail is still abbreviated.",
                                },
                                {
                                    "name": "actionability",
                                    "verdict": "pass",
                                    "detail": "Next steps are concrete.",
                                },
                            ]
                        }
                    ),
                    input_tokens=90,
                    output_tokens=30,
                    model="deepseek-chat",
                ),
            ):
                result = QualityReviewerAgent().execute(tmp_path, state, card, [])

        self.assertIn("analysis_method: llm", result.output)
        self.assertIn("coherence: pass", result.output)
        self.assertIn("completeness: warn", result.output)
        self.assertEqual(result.side_effects["analysis_method"], "llm")
        self.assertEqual(result.side_effects["llm_usage"]["model"], "deepseek-chat")
        self.assertEqual(result.estimated_input_tokens, 90)
        self.assertEqual(result.estimated_output_tokens, 30)

    def test_quality_reviewer_falls_back_to_heuristic_on_llm_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            artifact = tmp_path / "artifact.md"
            artifact.write_text("# Summary\n\nText only.\n", encoding="utf-8")
            state = TaskState(
                task_id="quality-fallback-task",
                title="Review artifact quality",
                goal="Check semantic quality",
                workspace_root=str(tmp_path),
            )
            card = TaskCard(
                goal="Review one artifact",
                parent_task_id=state.task_id,
                input_context={"artifact_ref": str(artifact), "quality_criteria": ["non_empty", "has_structure"]},
            )

            with patch(
                "swallow.quality_reviewer.call_agent_llm",
                side_effect=AgentLLMUnavailable("timeout"),
            ):
                result = QualityReviewerAgent().execute(tmp_path, state, card, [])

        self.assertIn("analysis_method: heuristic", result.output)
        self.assertEqual(result.side_effects["analysis_method"], "heuristic")
        self.assertEqual(result.side_effects["llm_usage"], {})

    def test_quality_reviewer_agent_reports_failure_for_empty_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            artifact = tmp_path / "empty.md"
            artifact.write_text("", encoding="utf-8")
            state = TaskState(
                task_id="quality-fail",
                title="Review empty artifact quality",
                goal="Check a broken artifact",
                workspace_root=str(tmp_path),
            )
            card = TaskCard(
                goal="Review an empty artifact",
                parent_task_id=state.task_id,
                input_context={"artifact_ref": str(artifact), "quality_criteria": ["non_empty", "min_length"]},
            )

            result = QualityReviewerAgent().execute(tmp_path, state, card, [])

        self.assertEqual(result.status, "failed")
        self.assertIn("overall_verdict: fail", result.output)
        self.assertIn("non_empty: fail", result.output)

    def test_run_task_can_execute_literature_specialist_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            doc_a = tmp_path / "reference-a.md"
            doc_b = tmp_path / "reference-b.md"
            doc_a.write_text("# Shared\nAgent lifecycle stays explicit.\n", encoding="utf-8")
            doc_b.write_text("# Shared\nQuality review stays explicit.\n", encoding="utf-8")
            created = create_task(
                base_dir=tmp_path,
                title="Literature run",
                goal="Trigger literature specialist through orchestrator",
                workspace_root=tmp_path,
                executor_name="literature-specialist",
            )
            route_selection = RouteSelection(
                route=RouteSpec(
                    name="literature-specialist-local",
                    backend_kind="specialist_test",
                    executor_name="literature-specialist",
                    executor_family="cli",
                    execution_site="local",
                    model_hint="local",
                    dialect_hint="plain_text",
                    remote_capable=False,
                    transport_kind="local_process",
                    capabilities=RouteCapabilities(
                        execution_kind="artifact_generation",
                        supports_tool_loop=False,
                        filesystem_access="workspace_read",
                        network_access="none",
                        deterministic=True,
                        resumable=True,
                    ),
                    taxonomy=TaxonomyProfile(system_role="specialist", memory_authority="task-memory"),
                ),
                reason="Route literature specialist tasks to the local heuristic agent.",
                policy_inputs={},
            )
            validation_tuple = _passing_validation_tuple()
            literature_card = TaskCard(
                goal="Compare two reference docs",
                parent_task_id=created.task_id,
                executor_type="literature-specialist",
                input_context={"document_paths": [str(doc_a), str(doc_b)]},
            )

            with patch("swallow.orchestrator.run_retrieval", return_value=[]):
                with patch("swallow.orchestrator.select_route", return_value=route_selection):
                    with patch("swallow.orchestrator.plan", return_value=[literature_card]):
                        with patch("swallow.orchestrator.write_task_artifacts", return_value=validation_tuple):
                            final_state = run_task(tmp_path, created.task_id, executor_name="literature-specialist")

            events = _load_events(tmp_path, created.task_id)
            review_gate_event = next(event for event in events if event["event_type"] == "task.review_gate")
            self.assertEqual(final_state.status, "completed")
            self.assertEqual(final_state.executor_name, "literature-specialist")
            self.assertEqual(final_state.route_name, "literature-specialist-local")
            self.assertEqual(review_gate_event["payload"]["executor_name"], "literature-specialist")

    def test_run_task_can_execute_quality_reviewer_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            artifact = tmp_path / "review-target.md"
            artifact.write_text("# Review\n\n- Next step: apply the fix.\n", encoding="utf-8")
            created = create_task(
                base_dir=tmp_path,
                title="Quality review run",
                goal="Trigger quality reviewer through orchestrator",
                workspace_root=tmp_path,
                executor_name="quality-reviewer",
            )
            route_selection = RouteSelection(
                route=RouteSpec(
                    name="quality-reviewer-local",
                    backend_kind="validator_test",
                    executor_name="quality-reviewer",
                    executor_family="cli",
                    execution_site="local",
                    model_hint="local",
                    dialect_hint="plain_text",
                    remote_capable=False,
                    transport_kind="local_process",
                    capabilities=RouteCapabilities(
                        execution_kind="artifact_validation",
                        supports_tool_loop=False,
                        filesystem_access="workspace_read",
                        network_access="none",
                        deterministic=True,
                        resumable=True,
                    ),
                    taxonomy=TaxonomyProfile(system_role="validator", memory_authority="stateless"),
                ),
                reason="Route quality review tasks to the local heuristic validator.",
                policy_inputs={},
            )
            validation_tuple = _passing_validation_tuple()
            review_card = TaskCard(
                goal="Review one generated artifact",
                parent_task_id=created.task_id,
                executor_type="quality-reviewer",
                input_context={"artifact_ref": str(artifact), "quality_criteria": ["non_empty", "has_structure"]},
            )

            with patch("swallow.orchestrator.run_retrieval", return_value=[]):
                with patch("swallow.orchestrator.select_route", return_value=route_selection):
                    with patch("swallow.orchestrator.plan", return_value=[review_card]):
                        with patch("swallow.orchestrator.write_task_artifacts", return_value=validation_tuple):
                            final_state = run_task(tmp_path, created.task_id, executor_name="quality-reviewer")

            events = _load_events(tmp_path, created.task_id)
            review_gate_event = next(event for event in events if event["event_type"] == "task.review_gate")
            self.assertEqual(final_state.status, "completed")
            self.assertEqual(final_state.executor_name, "quality-reviewer")
            self.assertEqual(final_state.route_name, "quality-reviewer-local")
            self.assertEqual(review_gate_event["payload"]["executor_name"], "quality-reviewer")
