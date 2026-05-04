from __future__ import annotations

import json
from pathlib import Path

import pytest

from swallow.application.commands.knowledge import (
    StagePromotePreflightError,
    promote_stage_candidate_command,
    summarize_text_preview,
)
from swallow.knowledge_retrieval.knowledge_plane import (
    StagedCandidate,
    list_staged_knowledge as load_staged_candidates,
    submit_staged_knowledge as submit_staged_candidate,
)
from swallow.application.infrastructure.paths import canonical_registry_path
from tests.helpers.cli_runner import run_cli


def test_knowledge_stage_promote_characterization_stdout_stderr_exit_code(tmp_path: Path) -> None:
    candidate = submit_staged_candidate(
        tmp_path,
        StagedCandidate(
            candidate_id="",
            text="Promote this focused integration note.",
            source_task_id="task-stage-promote",
            source_object_id="knowledge-0001",
            submitted_by="integration-test",
            taxonomy_role="specialist",
            taxonomy_memory_authority="staged-knowledge",
        ),
    )

    result = run_cli(
        tmp_path,
        "knowledge",
        "stage-promote",
        candidate.candidate_id,
        "--note",
        "Approved by focused CLI test.",
    )

    result.assert_success()
    assert result.stderr == ""
    assert f"{candidate.candidate_id} staged_promoted canonical_id=canonical-{candidate.candidate_id}" in result.stdout
    staged = load_staged_candidates(tmp_path)
    assert staged[0].status == "promoted"
    assert staged[0].decision_note == "Approved by focused CLI test."
    canonical_records = [
        json.loads(line)
        for line in canonical_registry_path(tmp_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert canonical_records[0]["canonical_id"] == f"canonical-{candidate.candidate_id}"


def test_knowledge_stage_promote_target_id_supersede_requires_force_and_marks_old_record(tmp_path: Path) -> None:
    old = submit_staged_candidate(
        tmp_path,
        StagedCandidate(
            candidate_id="",
            text="Old wiki entry that should be superseded by explicit target id.",
            source_task_id="task-stage-target-old",
            source_object_id="knowledge-old",
            submitted_by="integration-test",
        ),
    )
    old_result = run_cli(
        tmp_path,
        "knowledge",
        "stage-promote",
        old.candidate_id,
        "--note",
        "Approve old target.",
    )
    old_result.assert_success()

    replacement = submit_staged_candidate(
        tmp_path,
        StagedCandidate(
            candidate_id="",
            text="Replacement wiki entry with a different canonical key.",
            source_task_id="task-stage-target-new",
            source_object_id="knowledge-new",
            submitted_by="integration-test",
            relation_metadata=[
                {
                    "relation_type": "supersedes",
                    "target_object_id": f"canonical-{old.candidate_id}",
                }
            ],
        ),
    )

    with pytest.raises(StagePromotePreflightError) as raised:
        promote_stage_candidate_command(
            tmp_path,
            replacement.candidate_id,
            note="Approve replacement.",
        )

    assert raised.value.notices == [
        {
            "notice_type": "supersede",
            "canonical_id": f"canonical-{old.candidate_id}",
            "target_object_id": f"canonical-{old.candidate_id}",
            "text_preview": summarize_text_preview(old.text, 60),
        }
    ]
    assert load_staged_candidates(tmp_path)[1].status == "pending"

    force_result = run_cli(
        tmp_path,
        "knowledge",
        "stage-promote",
        replacement.candidate_id,
        "--note",
        "Approve replacement.",
        "--force",
    )
    force_result.assert_success()
    assert force_result.stderr == ""
    assert f"[SUPERSEDE] canonical_id=canonical-{old.candidate_id}" in force_result.stdout

    canonical_records = [
        json.loads(line)
        for line in canonical_registry_path(tmp_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert canonical_records[0]["canonical_status"] == "superseded"
    assert canonical_records[0]["superseded_by"] == f"canonical-{replacement.candidate_id}"
    assert canonical_records[0]["superseded_at"] == canonical_records[1]["promoted_at"]
    assert canonical_records[1]["canonical_status"] == "active"


def test_knowledge_stage_reject_characterization_stdout_stderr_exit_code(tmp_path: Path) -> None:
    candidate = submit_staged_candidate(
        tmp_path,
        StagedCandidate(
            candidate_id="",
            text="Reject this focused integration note.",
            source_task_id="task-stage-reject",
            submitted_by="integration-test",
        ),
    )

    result = run_cli(
        tmp_path,
        "knowledge",
        "stage-reject",
        candidate.candidate_id,
        "--note",
        "Needs better evidence.",
    )

    result.assert_success()
    assert result.stderr == ""
    assert f"{candidate.candidate_id} staged_rejected status=rejected" in result.stdout
    staged = load_staged_candidates(tmp_path)
    assert staged[0].status == "rejected"
    assert staged[0].decision_note == "Needs better evidence."


def test_knowledge_ingest_file_characterization_stdout_stderr_exit_code(tmp_path: Path) -> None:
    source = tmp_path / "operator-note.md"
    source.write_text("# Operator Note\n\nUse focused CLI tests for migration baselines.\n", encoding="utf-8")

    result = run_cli(tmp_path, "knowledge", "ingest-file", str(source), "--summary")

    result.assert_success()
    assert result.stderr == ""
    assert "# Ingestion Report" in result.stdout
    assert "staged_candidates:" in result.stdout


# --- Moved mechanically from tests/test_cli.py during LTO-4. ---
import json
import shutil
import tempfile
import unittest
from pathlib import Path
import subprocess
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest.mock import patch

from swallow.adapters.cli import build_stage_promote_preflight_notices, main
from swallow.orchestration.compatibility import build_compatibility_report, evaluate_route_compatibility
from swallow.application.services.capabilities import (
    DEFAULT_CAPABILITY_MANIFEST,
    build_capability_assembly,
    parse_capability_refs,
    validate_capability_manifest,
)
from swallow.orchestration.execution_fit import build_execution_fit_report, evaluate_execution_fit
from swallow.orchestration.executor import (
    AIDER_CONFIG,
    build_formatted_executor_prompt,
    build_fallback_output,
    classify_failure_kind,
    normalize_executor_name,
    resolve_dialect_name,
    resolve_executor_name,
    run_cli_agent_executor,
)
from swallow.orchestration.harness import (
    build_remote_handoff_contract_record,
    build_resume_note,
    build_retrieval_report,
    build_source_grounding,
)
from swallow.knowledge_retrieval.knowledge_plane import (
    ARTIFACTS_SOURCE_TYPE,
    KNOWLEDGE_SOURCE_TYPE,
    OPERATOR_CANONICAL_WRITE_AUTHORITY,
    StagedCandidate,
    evaluate_knowledge_policy,
    list_staged_knowledge as load_staged_candidates,
    retrieve_knowledge_context as retrieve_context,
    submit_staged_knowledge as submit_staged_candidate,
)
from swallow.application.services.meta_optimizer import load_optimization_proposal_bundle
from swallow.orchestration.models import (
    DispatchVerdict,
    Event,
    EVENT_EXECUTOR_FAILED,
    ExecutorResult,
    HandoffContractSchema,
    RouteCapabilities,
    RouteSelection,
    RouteSpec,
    RetrievalItem,
    RetrievalRequest,
    TaskCard,
    TaxonomyProfile,
    TaskState,
    ValidationResult,
    evaluate_dispatch_verdict,
    validate_remote_handoff_contract_payload,
)
from swallow.orchestration.orchestrator import (
    acknowledge_task,
    build_task_retrieval_request,
    create_task,
    decide_task_knowledge,
    run_task,
    update_task_planning_handoff,
)
from swallow.application.infrastructure.paths import (
    artifacts_dir,
    canonical_registry_path,
    canonical_reuse_policy_path,
    canonical_reuse_regression_path,
    knowledge_wiki_entry_path,
    latest_optimization_proposal_bundle_path,
    remote_handoff_contract_path,
    route_capabilities_path,
    route_policy_path,
    route_registry_path,
    route_weights_path,
    swallow_db_path,
)
from swallow.knowledge_retrieval.retrieval_adapters import select_retrieval_adapter
from swallow.provider_router.router import (
    apply_route_policy,
    apply_route_registry,
    load_route_capability_profiles,
    load_route_policy,
    load_route_registry,
    load_route_weights,
    route_by_name,
    select_route,
)
from swallow.truth_governance.store import (
    append_event,
    append_canonical_record,
    load_knowledge_objects,
    load_state,
    save_knowledge_objects,
    save_remote_handoff_contract,
    save_retrieval,
    save_state,
)
from swallow.orchestration.planner import plan
from swallow.orchestration.validator import build_validation_report, validate_run_outputs


class LegacyCliKnowledgeCommandTest(unittest.TestCase):
    def test_cli_create_persists_staged_knowledge_objects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Knowledge capture",
                        "--goal",
                        "Persist staged knowledge objects",
                        "--workspace-root",
                        str(tmp_path),
                        "--knowledge-stage",
                        "candidate",
                        "--knowledge-source",
                        "chat://knowledge-session-1",
                        "--knowledge-item",
                        "Route selection should stay explicit.",
                        "--knowledge-item",
                        "Imported notes should remain task-linked before promotion.",
                    ]
                ),
                0,
            )
            task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
            task_dir = tmp_path / ".swl" / "tasks" / task_id
            state = json.loads((task_dir / "state.json").read_text(encoding="utf-8"))
            knowledge_objects = json.loads((task_dir / "knowledge_objects.json").read_text(encoding="utf-8"))
            knowledge_report = (task_dir / "artifacts" / "knowledge_objects_report.md").read_text(encoding="utf-8")
            events = [
                json.loads(line)
                for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(len(knowledge_objects), 2)
        self.assertEqual(knowledge_objects[0]["stage"], "candidate")
        self.assertEqual(knowledge_objects[0]["source_kind"], "external_knowledge_capture")
        self.assertEqual(knowledge_objects[0]["source_ref"], "chat://knowledge-session-1")
        self.assertEqual(knowledge_objects[1]["stage"], "candidate")
        self.assertEqual(state["knowledge_objects"][0]["stage"], "candidate")
        self.assertTrue(state["artifact_paths"]["knowledge_objects_json"].endswith("knowledge_objects.json"))
        self.assertTrue(state["artifact_paths"]["knowledge_objects_report"].endswith("knowledge_objects_report.md"))
        self.assertEqual(events[0]["payload"]["knowledge_objects_count"], 2)
        self.assertEqual(events[0]["payload"]["knowledge_stage_counts"]["candidate"], 2)
        self.assertIn("Knowledge Objects Report", knowledge_report)
        self.assertIn("candidate: 2", knowledge_report)

    def test_append_canonical_record_replaces_existing_canonical_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            append_canonical_record(
                tmp_path,
                {
                    "canonical_id": "canonical-task-1-object-1",
                    "canonical_key": "artifact:.swl/tasks/demo/artifacts/evidence.md",
                    "source_task_id": "task-1",
                    "source_object_id": "object-1",
                    "promoted_at": "2026-04-09T00:00:00Z",
                    "decision_note": "initial",
                    "canonical_status": "active",
                    "superseded_by": "",
                    "superseded_at": "",
                },
            )
            append_canonical_record(
                tmp_path,
                {
                    "canonical_id": "canonical-task-1-object-1",
                    "canonical_key": "artifact:.swl/tasks/demo/artifacts/evidence.md",
                    "source_task_id": "task-1",
                    "source_object_id": "object-1",
                    "promoted_at": "2026-04-09T01:00:00Z",
                    "decision_note": "updated",
                    "canonical_status": "active",
                    "superseded_by": "",
                    "superseded_at": "",
                },
            )

            records = [
                json.loads(line)
                for line in canonical_registry_path(tmp_path).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["canonical_id"], "canonical-task-1-object-1")
        self.assertEqual(records[0]["decision_note"], "updated")
        self.assertEqual(records[0]["promoted_at"], "2026-04-09T01:00:00Z")
        self.assertEqual(records[0]["canonical_status"], "active")

    def test_append_canonical_record_supersedes_previous_trace_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            append_canonical_record(
                tmp_path,
                {
                    "canonical_id": "canonical-task-1-object-1",
                    "canonical_key": "artifact:.swl/tasks/demo/artifacts/evidence.md",
                    "source_task_id": "task-1",
                    "source_object_id": "object-1",
                    "promoted_at": "2026-04-09T00:00:00Z",
                    "decision_note": "initial",
                    "canonical_status": "active",
                    "superseded_by": "",
                    "superseded_at": "",
                },
            )
            append_canonical_record(
                tmp_path,
                {
                    "canonical_id": "canonical-task-2-object-9",
                    "canonical_key": "artifact:.swl/tasks/demo/artifacts/evidence.md",
                    "source_task_id": "task-2",
                    "source_object_id": "object-9",
                    "promoted_at": "2026-04-09T02:00:00Z",
                    "decision_note": "replacement",
                    "canonical_status": "active",
                    "superseded_by": "",
                    "superseded_at": "",
                },
            )

            records = [
                json.loads(line)
                for line in canonical_registry_path(tmp_path).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["canonical_status"], "superseded")
        self.assertEqual(records[0]["superseded_by"], "canonical-task-2-object-9")
        self.assertEqual(records[0]["superseded_at"], "2026-04-09T02:00:00Z")
        self.assertEqual(records[1]["canonical_status"], "active")
        self.assertEqual(records[1]["canonical_id"], "canonical-task-2-object-9")

    def test_cli_knowledge_capture_appends_staged_knowledge_objects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Knowledge append",
                        "--goal",
                        "Attach staged knowledge after task creation",
                        "--workspace-root",
                        str(tmp_path),
                    ]
                ),
                0,
            )
            task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "knowledge-capture",
                        task_id,
                        "--knowledge-stage",
                        "verified",
                        "--knowledge-source",
                        "chat://phase11-knowledge",
                        "--knowledge-item",
                        "Imported planning notes can become staged knowledge.",
                        "--knowledge-retrieval-eligible",
                        "--knowledge-canonicalization-intent",
                        "review",
                    ]
                ),
                0,
            )

            task_dir = tmp_path / ".swl" / "tasks" / task_id
            knowledge_objects = json.loads((task_dir / "knowledge_objects.json").read_text(encoding="utf-8"))
            events = [
                json.loads(line)
                for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(len(knowledge_objects), 1)
        self.assertEqual(knowledge_objects[0]["stage"], "verified")
        self.assertEqual(knowledge_objects[0]["source_ref"], "chat://phase11-knowledge")
        self.assertEqual(knowledge_objects[0]["retrieval_eligible"], True)
        self.assertEqual(knowledge_objects[0]["knowledge_reuse_scope"], "retrieval_candidate")
        self.assertEqual(knowledge_objects[0]["canonicalization_intent"], "review")
        self.assertEqual(events[-1]["event_type"], "task.knowledge_capture_added")
        self.assertEqual(events[-1]["payload"]["added_count"], 1)

    def test_cli_create_marks_artifact_backed_knowledge_objects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Artifact-backed knowledge",
                        "--goal",
                        "Preserve artifact-backed evidence references",
                        "--workspace-root",
                        str(tmp_path),
                        "--knowledge-stage",
                        "candidate",
                        "--knowledge-source",
                        "chat://knowledge-session-2",
                        "--knowledge-item",
                        "The route report should remain inspectable.",
                        "--knowledge-item",
                        "The summary should remain the run record.",
                        "--knowledge-artifact-ref",
                        ".swl/tasks/demo/artifacts/route_report.md",
                    ]
                ),
                0,
            )
            task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
            task_dir = tmp_path / ".swl" / "tasks" / task_id
            knowledge_objects = json.loads((task_dir / "knowledge_objects.json").read_text(encoding="utf-8"))
            knowledge_report = (task_dir / "artifacts" / "knowledge_objects_report.md").read_text(encoding="utf-8")
            knowledge_partition = json.loads((task_dir / "knowledge_partition.json").read_text(encoding="utf-8"))
            partition_report = (task_dir / "artifacts" / "knowledge_partition_report.md").read_text(encoding="utf-8")
            events = [
                json.loads(line)
                for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(knowledge_objects[0]["evidence_status"], "artifact_backed")
        self.assertEqual(knowledge_objects[0]["artifact_ref"], ".swl/tasks/demo/artifacts/route_report.md")
        self.assertEqual(knowledge_objects[1]["evidence_status"], "source_only")
        self.assertEqual(events[0]["payload"]["knowledge_evidence_counts"]["artifact_backed"], 1)
        self.assertEqual(events[0]["payload"]["knowledge_evidence_counts"]["source_only"], 1)
        self.assertIn("artifact_backed: 1", knowledge_report)
        self.assertIn("source_only: 1", knowledge_report)
        self.assertIn(".swl/tasks/demo/artifacts/route_report.md", knowledge_report)

    def test_cli_knowledge_review_queue_classifies_ready_and_blocked_objects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Knowledge queue",
                        "--goal",
                        "Classify staged knowledge review states",
                        "--workspace-root",
                        str(tmp_path),
                        "--knowledge-stage",
                        "verified",
                        "--knowledge-source",
                        "chat://knowledge-queue",
                        "--knowledge-item",
                        "Artifact-backed verified knowledge should be reuse ready.",
                        "--knowledge-item",
                        "Source-only verified knowledge should stay blocked.",
                        "--knowledge-artifact-ref",
                        ".swl/tasks/demo/artifacts/evidence.md",
                        "--knowledge-retrieval-eligible",
                        "--knowledge-canonicalization-intent",
                        "review",
                    ]
                ),
                0,
            )
            task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "knowledge-review-queue", task_id]), 0)

        output = stdout.getvalue()
        self.assertIn("Knowledge Review Queue", output)
        self.assertIn("promote_ready: 1", output)
        self.assertIn("blocked: 1", output)
        self.assertIn("recommended_action: promote-canonical", output)
        self.assertIn("blocked_reason: evidence_not_artifact_backed", output)

    def test_cli_knowledge_promote_reuse_persists_decision_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Knowledge promote",
                        "--goal",
                        "Promote one knowledge object for retrieval reuse",
                        "--workspace-root",
                        str(tmp_path),
                        "--knowledge-stage",
                        "verified",
                        "--knowledge-source",
                        "chat://knowledge-promote",
                        "--knowledge-item",
                        "Verified artifact-backed knowledge should be promoted by operator review.",
                        "--knowledge-artifact-ref",
                        ".swl/tasks/demo/artifacts/evidence.md",
                    ]
                ),
                0,
            )
            task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "knowledge-promote",
                        task_id,
                        "knowledge-0001",
                        "--target",
                        "reuse",
                        "--note",
                        "Promote for cross-task retrieval review.",
                    ]
                ),
                0,
            )

            task_dir = tmp_path / ".swl" / "tasks" / task_id
            knowledge_objects = json.loads((task_dir / "knowledge_objects.json").read_text(encoding="utf-8"))
            knowledge_index = json.loads((task_dir / "knowledge_index.json").read_text(encoding="utf-8"))
            decision_records = [
                json.loads(line)
                for line in (task_dir / "knowledge_decisions.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            inspect_stdout = StringIO()
            with redirect_stdout(inspect_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "inspect", task_id]), 0)
            events = [
                json.loads(line)
                for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(knowledge_objects[0]["knowledge_reuse_scope"], "retrieval_candidate")
        self.assertEqual(knowledge_objects[0]["retrieval_eligible"], True)
        self.assertEqual(knowledge_index["active_reusable_count"], 1)
        self.assertEqual(decision_records[0]["decision_type"], "promote")
        self.assertEqual(decision_records[0]["decision_target"], "reuse")
        self.assertEqual(decision_records[0]["note"], "Promote for cross-task retrieval review.")
        self.assertIn("knowledge_review_reuse_ready: 1", inspect_stdout.getvalue())
        self.assertIn("knowledge_review_decisions_recorded: 1", inspect_stdout.getvalue())
        self.assertEqual(events[-1]["event_type"], "knowledge.promoted")

    def test_cli_knowledge_reject_canonical_clears_intent_and_reports_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Knowledge reject",
                        "--goal",
                        "Reject canonical promotion for one object",
                        "--workspace-root",
                        str(tmp_path),
                        "--knowledge-stage",
                        "verified",
                        "--knowledge-source",
                        "chat://knowledge-reject",
                        "--knowledge-item",
                        "Verified artifact-backed knowledge may still be rejected by operator review.",
                        "--knowledge-artifact-ref",
                        ".swl/tasks/demo/artifacts/evidence.md",
                        "--knowledge-canonicalization-intent",
                        "review",
                    ]
                ),
                0,
            )
            task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "knowledge-reject",
                        task_id,
                        "knowledge-0001",
                        "--target",
                        "canonical",
                        "--note",
                        "Keep task-linked only for now.",
                    ]
                ),
                0,
            )

            task_dir = tmp_path / ".swl" / "tasks" / task_id
            knowledge_objects = json.loads((task_dir / "knowledge_objects.json").read_text(encoding="utf-8"))
            decisions_stdout = StringIO()
            queue_stdout = StringIO()
            review_stdout = StringIO()
            with redirect_stdout(decisions_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "knowledge-decisions", task_id]), 0)
            with redirect_stdout(queue_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "knowledge-review-queue", task_id]), 0)
            with redirect_stdout(review_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "review", task_id]), 0)

        self.assertEqual(knowledge_objects[0]["canonicalization_intent"], "none")
        self.assertIn("Knowledge Decision Record", decisions_stdout.getvalue())
        self.assertIn("knowledge-0001 reject canonical", decisions_stdout.getvalue())
        self.assertIn("queue_state: rejected", queue_stdout.getvalue())
        self.assertIn("knowledge_review_rejected: 1", review_stdout.getvalue())
        self.assertIn("knowledge_review_decisions_recorded: 1", review_stdout.getvalue())

    def test_cli_knowledge_promote_canonical_persists_registry_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Canonical promote",
                        "--goal",
                        "Persist canonical registry records",
                        "--workspace-root",
                        str(tmp_path),
                        "--knowledge-stage",
                        "verified",
                        "--knowledge-source",
                        "chat://canonical-promote",
                        "--knowledge-item",
                        "Verified artifact-backed knowledge should enter canonical registry.",
                        "--knowledge-artifact-ref",
                        ".swl/tasks/demo/artifacts/evidence.md",
                        "--knowledge-canonicalization-intent",
                        "promote",
                    ]
                ),
                0,
            )
            task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "knowledge-promote",
                        task_id,
                        "knowledge-0001",
                        "--target",
                        "canonical",
                        "--note",
                        "Promote into canonical registry baseline.",
                    ]
                ),
                0,
            )

            task_dir = tmp_path / ".swl" / "tasks" / task_id
            knowledge_objects = json.loads((task_dir / "knowledge_objects.json").read_text(encoding="utf-8"))
            canonical_records = [
                json.loads(line)
                for line in (tmp_path / ".swl" / "canonical_knowledge" / "registry.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            decision_records = [
                json.loads(line)
                for line in (task_dir / "knowledge_decisions.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            inspect_stdout = StringIO()
            review_stdout = StringIO()
            registry_stdout = StringIO()
            registry_json_stdout = StringIO()
            registry_index_stdout = StringIO()
            reuse_stdout = StringIO()
            registry_index_json_stdout = StringIO()
            reuse_json_stdout = StringIO()
            with redirect_stdout(inspect_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "inspect", task_id]), 0)
            with redirect_stdout(review_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "review", task_id]), 0)
            with redirect_stdout(registry_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "canonical-registry", task_id]), 0)
            with redirect_stdout(registry_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "canonical-registry-json", task_id]), 0)
            with redirect_stdout(registry_index_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "canonical-registry-index", task_id]), 0)
            with redirect_stdout(reuse_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "canonical-reuse", task_id]), 0)
            with redirect_stdout(registry_index_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "canonical-registry-index-json", task_id]), 0)
            with redirect_stdout(reuse_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "canonical-reuse-json", task_id]), 0)

        self.assertEqual(knowledge_objects[0]["stage"], "canonical")
        self.assertEqual(canonical_records[0]["source_task_id"], task_id)
        self.assertEqual(canonical_records[0]["source_object_id"], "knowledge-0001")
        self.assertEqual(canonical_records[0]["artifact_ref"], ".swl/tasks/demo/artifacts/evidence.md")
        self.assertEqual(decision_records[0]["caller_authority"], "operator-gated")
        self.assertIn("Canonical Registry", inspect_stdout.getvalue())
        self.assertIn("canonical_registry_count: 1", inspect_stdout.getvalue())
        self.assertIn("canonical_registry_active_count: 1", inspect_stdout.getvalue())
        self.assertIn("canonical_registry_superseded_count: 0", inspect_stdout.getvalue())
        self.assertIn("canonical_registry_source_task_count: 1", inspect_stdout.getvalue())
        self.assertIn("canonical_registry_latest_source_task: " + task_id, inspect_stdout.getvalue())
        self.assertIn("Canonical Reuse", inspect_stdout.getvalue())
        self.assertIn("canonical_reuse_visible_count: 1", inspect_stdout.getvalue())
        self.assertIn("Canonical Registry", review_stdout.getvalue())
        self.assertIn("canonical_registry_count: 1", review_stdout.getvalue())
        self.assertIn("canonical_reuse_visible_count: 1", review_stdout.getvalue())
        self.assertIn("Canonical Knowledge Registry", registry_stdout.getvalue())
        self.assertIn("Canonical Knowledge Registry Index", registry_index_stdout.getvalue())
        self.assertIn("Canonical Reuse Policy", reuse_stdout.getvalue())
        self.assertIn("dedupe_key: canonical_id", registry_index_stdout.getvalue())
        self.assertIn("replace_strategy: latest_record_wins", registry_index_stdout.getvalue())
        self.assertIn("supersede_key: canonical_key", registry_index_stdout.getvalue())
        self.assertIn("supersede_strategy: latest_active_by_trace", registry_index_stdout.getvalue())

    def test_decide_task_knowledge_blocks_unauthorized_canonical_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Unauthorized canonical promote",
                        "--goal",
                        "Block automatic canonical promotion without librarian authority",
                        "--workspace-root",
                        str(tmp_path),
                        "--knowledge-stage",
                        "verified",
                        "--knowledge-source",
                        "chat://canonical-promote-blocked",
                        "--knowledge-item",
                        "Verified artifact-backed knowledge should still require librarian authority.",
                        "--knowledge-artifact-ref",
                        ".swl/tasks/demo/artifacts/evidence.md",
                        "--knowledge-canonicalization-intent",
                        "promote",
                    ]
                ),
                0,
            )
            task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())

            with self.assertRaises(PermissionError) as raised:
                decide_task_knowledge(
                    tmp_path,
                    task_id,
                    object_id="knowledge-0001",
                    decision_type="promote",
                    decision_target="canonical",
                    caller_authority="task-state",
                    note="Attempt automatic promote without librarian.",
                    decided_by="mock-remote",
                )

            task_dir = tmp_path / ".swl" / "tasks" / task_id
            knowledge_objects = json.loads((task_dir / "knowledge_objects.json").read_text(encoding="utf-8"))
            events = [
                json.loads(line)
                for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertIn("caller_authority=canonical-promotion", str(raised.exception))
        self.assertEqual(knowledge_objects[0]["stage"], "verified")
        self.assertEqual(events[-1]["event_type"], "knowledge.promotion.unauthorized")
        self.assertEqual(events[-1]["payload"]["caller_authority"], "task-state")
        self.assertEqual(events[-1]["payload"]["decision_target"], "canonical")

    def test_cli_stage_list_reports_no_pending_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "stage-list"]), 0)

        output = stdout.getvalue()
        self.assertIn("Staged Knowledge Review Queue", output)
        self.assertIn("pending_count: 0", output)
        self.assertIn("no pending candidates", output)

    def test_cli_stage_inspect_prints_full_candidate_details(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            candidate = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Candidate knowledge should be visible to operators.",
                    source_task_id="task-stage-inspect",
                    topic="visibility",
                    source_object_id="knowledge-0001",
                    submitted_by="mock-remote",
                    taxonomy_role="specialist",
                    taxonomy_memory_authority="staged-knowledge",
                ),
            )
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "stage-inspect", candidate.candidate_id]), 0)

        output = stdout.getvalue()
        self.assertIn(f"Staged Candidate: {candidate.candidate_id}", output)
        self.assertIn("status: pending", output)
        self.assertIn("source_task_id: task-stage-inspect", output)
        self.assertIn("topic: visibility", output)
        self.assertIn("taxonomy_role: specialist", output)
        self.assertIn("taxonomy_memory_authority: staged-knowledge", output)
        self.assertIn("Candidate knowledge should be visible to operators.", output)

    def test_cli_stage_list_includes_topic_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="List view should show the topic field.",
                    source_task_id="task-stage-list",
                    topic="knowledge-capture",
                    source_kind="operator_note",
                    source_ref="note://operator",
                ),
            )
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "stage-list"]), 0)

        output = stdout.getvalue()
        self.assertIn("topic: knowledge-capture", output)
        self.assertIn("source_kind: operator_note", output)
        self.assertIn("source_ref: note://operator", output)

    def test_cli_note_persists_operator_note_with_topic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "note",
                            "Use explicit route guards for fallback behavior.",
                            "--tag",
                            "routing",
                        ]
                    ),
                    0,
                )

            staged_records = load_staged_candidates(tmp_path)

        note_id = stdout.getvalue().strip()
        self.assertTrue(note_id.startswith("staged-"))
        self.assertEqual(len(staged_records), 1)
        self.assertEqual(staged_records[0].candidate_id, note_id)
        self.assertEqual(staged_records[0].source_kind, "operator_note")
        self.assertEqual(staged_records[0].topic, "routing")
        self.assertEqual(staged_records[0].submitted_by, "swl_note")

    def test_cli_stage_promote_updates_candidate_and_canonical_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            candidate = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Promote this staged note into canonical guidance.",
                    source_task_id="task-stage-promote",
                    source_object_id="knowledge-0002",
                    submitted_by="mock-remote",
                    taxonomy_role="specialist",
                    taxonomy_memory_authority="staged-knowledge",
                ),
            )
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "knowledge",
                            "stage-promote",
                            candidate.candidate_id,
                            "--note",
                            "Approved from staged queue.",
                        ]
                    ),
                    0,
                )

            staged_records = [
                json.loads(line)
                for line in (tmp_path / ".swl" / "staged_knowledge" / "registry.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            canonical_records = [
                json.loads(line)
                for line in canonical_registry_path(tmp_path).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            wiki_entry = json.loads(
                knowledge_wiki_entry_path(tmp_path, "task-stage-promote", "knowledge-0002").read_text(encoding="utf-8")
            )
            reuse_policy = json.loads(canonical_reuse_policy_path(tmp_path).read_text(encoding="utf-8"))

        self.assertIn(f"{candidate.candidate_id} staged_promoted", stdout.getvalue())
        self.assertEqual(staged_records[0]["status"], "promoted")
        self.assertEqual(staged_records[0]["decision_note"], "Approved from staged queue.")
        self.assertEqual(canonical_records[0]["canonical_id"], f"canonical-{candidate.candidate_id}")
        self.assertEqual(canonical_records[0]["source_task_id"], "task-stage-promote")
        self.assertEqual(canonical_records[0]["source_object_id"], "knowledge-0002")
        self.assertEqual(wiki_entry["stage"], "canonical")
        self.assertEqual(wiki_entry["store_type"], "wiki")
        self.assertEqual(wiki_entry["promoted_by"], "swl_cli")
        self.assertEqual(reuse_policy["reuse_visible_count"], 1)

    def test_create_task_preserves_existing_canonical_reuse_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            candidate = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Promote this staged note into canonical guidance.",
                    source_task_id="task-stage-promote",
                    source_object_id="knowledge-0002",
                ),
            )
            self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "stage-promote", candidate.candidate_id]), 0)

            before_reuse = json.loads(canonical_reuse_policy_path(tmp_path).read_text(encoding="utf-8"))
            created = create_task(
                base_dir=tmp_path,
                title="Preserve canonical reuse",
                goal="Do not reset global canonical reuse state when creating a task",
                workspace_root=tmp_path,
                executor_name="local",
            )
            after_reuse = json.loads(canonical_reuse_policy_path(tmp_path).read_text(encoding="utf-8"))
            task_report = (
                tmp_path / ".swl" / "tasks" / created.task_id / "artifacts" / "canonical_reuse_policy_report.md"
            ).read_text(encoding="utf-8")

        self.assertEqual(before_reuse["reuse_visible_count"], 1)
        self.assertEqual(after_reuse["reuse_visible_count"], 1)
        self.assertIn("reuse_visible_count: 1", task_report)

    def test_cli_knowledge_apply_suggestions_creates_relations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            save_knowledge_objects(tmp_path, "task-a", [{"object_id": "knowledge-a", "text": "A", "stage": "verified"}])
            save_knowledge_objects(tmp_path, "task-b", [{"object_id": "knowledge-b", "text": "B", "stage": "verified"}])
            created = create_task(
                base_dir=tmp_path,
                title="Apply relation suggestions",
                goal="Persist literature relation suggestions",
                workspace_root=tmp_path,
                executor_name="local",
            )
            (artifacts_dir(tmp_path, created.task_id) / "executor_side_effects.json").write_text(
                json.dumps(
                    {
                        "relation_suggestions": [
                            {
                                "source_object_id": "knowledge-a",
                                "target_object_id": "knowledge-b",
                                "relation_type": "extends",
                                "confidence": 0.9,
                                "context": "A extends B",
                            }
                        ]
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "knowledge",
                            "apply-suggestions",
                            "--task-id",
                            created.task_id,
                        ]
                    ),
                    0,
                )
            relations_output = StringIO()
            with redirect_stdout(relations_output):
                self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "links", "knowledge-a"]), 0)

        self.assertIn("applied_count: 1", stdout.getvalue())
        self.assertIn("extends", relations_output.getvalue())
        self.assertIn("knowledge-b", relations_output.getvalue())

    def test_cli_knowledge_apply_suggestions_skips_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            save_knowledge_objects(tmp_path, "task-a", [{"object_id": "knowledge-a", "text": "A", "stage": "verified"}])
            save_knowledge_objects(tmp_path, "task-b", [{"object_id": "knowledge-b", "text": "B", "stage": "verified"}])
            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "knowledge",
                        "link",
                        "knowledge-a",
                        "knowledge-b",
                        "--type",
                        "extends",
                    ]
                ),
                0,
            )
            created = create_task(
                base_dir=tmp_path,
                title="Apply duplicate suggestions",
                goal="Skip duplicate literature relation suggestions",
                workspace_root=tmp_path,
                executor_name="local",
            )
            (artifacts_dir(tmp_path, created.task_id) / "executor_side_effects.json").write_text(
                json.dumps(
                    {
                        "relation_suggestions": [
                            {
                                "source_object_id": "knowledge-a",
                                "target_object_id": "knowledge-b",
                                "relation_type": "extends",
                                "confidence": 0.9,
                                "context": "A extends B",
                            }
                        ]
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "knowledge",
                            "apply-suggestions",
                            "--task-id",
                            created.task_id,
                        ]
                    ),
                    0,
                )
            relations_output = StringIO()
            with redirect_stdout(relations_output):
                self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "links", "knowledge-a"]), 0)

        self.assertIn("applied_count: 0", stdout.getvalue())
        self.assertIn("duplicate_count: 1", stdout.getvalue())
        self.assertEqual(relations_output.getvalue().count("relation_type: extends"), 1)

    def test_cli_knowledge_apply_suggestions_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            save_knowledge_objects(tmp_path, "task-a", [{"object_id": "knowledge-a", "text": "A", "stage": "verified"}])
            save_knowledge_objects(tmp_path, "task-b", [{"object_id": "knowledge-b", "text": "B", "stage": "verified"}])
            created = create_task(
                base_dir=tmp_path,
                title="Dry run suggestions",
                goal="Preview literature relation suggestions",
                workspace_root=tmp_path,
                executor_name="local",
            )
            (artifacts_dir(tmp_path, created.task_id) / "executor_side_effects.json").write_text(
                json.dumps(
                    {
                        "relation_suggestions": [
                            {
                                "source_object_id": "knowledge-a",
                                "target_object_id": "knowledge-b",
                                "relation_type": "extends",
                                "confidence": 0.9,
                                "context": "A extends B",
                            }
                        ]
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "knowledge",
                            "apply-suggestions",
                            "--task-id",
                            created.task_id,
                            "--dry-run",
                        ]
                    ),
                    0,
                )
            relations_output = StringIO()
            with redirect_stdout(relations_output):
                self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "links", "knowledge-a"]), 0)

        self.assertIn("dry_run: True", stdout.getvalue())
        self.assertIn("applied_count: 1", stdout.getvalue())
        self.assertIn("count: 0", relations_output.getvalue())

    def test_cli_stage_promote_accepts_refined_text_without_mutating_staged_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            candidate = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Original staged wording should remain in staged storage.",
                    source_task_id="task-stage-refine",
                    source_object_id="knowledge-0015",
                ),
            )

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "knowledge",
                        "stage-promote",
                        candidate.candidate_id,
                        "--text",
                        "Refined canonical wording for downstream reuse.",
                        "--note",
                        "Operator tightened wording.",
                    ]
                ),
                0,
            )

            staged_records = [
                json.loads(line)
                for line in (tmp_path / ".swl" / "staged_knowledge" / "registry.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            canonical_records = [
                json.loads(line)
                for line in canonical_registry_path(tmp_path).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(staged_records[0]["text"], "Original staged wording should remain in staged storage.")
        self.assertEqual(staged_records[0]["decision_note"], "Operator tightened wording. [refined]")
        self.assertEqual(canonical_records[0]["text"], "Refined canonical wording for downstream reuse.")
        self.assertEqual(canonical_records[0]["decision_note"], "Operator tightened wording. [refined]")

    def test_cli_stage_promote_supersedes_previous_record_from_same_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            first = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Initial canonical fact from the same task object.",
                    source_task_id="task-stage-dedupe",
                    source_object_id="knowledge-0009",
                    submitted_by="mock-remote",
                ),
            )
            second = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Updated canonical fact from the same task object.",
                    source_task_id="task-stage-dedupe",
                    source_object_id="knowledge-0009",
                    submitted_by="mock-remote",
                ),
            )

            self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "stage-promote", first.candidate_id]), 0)
            self.assertEqual(
                main(["--base-dir", str(tmp_path), "knowledge", "stage-promote", second.candidate_id, "--force"]),
                0,
            )

            canonical_records = [
                json.loads(line)
                for line in canonical_registry_path(tmp_path).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(len(canonical_records), 2)
        self.assertEqual(canonical_records[0]["canonical_key"], "task-object:task-stage-dedupe:knowledge-0009")
        self.assertEqual(canonical_records[0]["canonical_status"], "superseded")
        self.assertEqual(canonical_records[0]["superseded_by"], f"canonical-{second.candidate_id}")
        self.assertEqual(canonical_records[1]["canonical_key"], "task-object:task-stage-dedupe:knowledge-0009")
        self.assertEqual(canonical_records[1]["canonical_status"], "active")

    def test_cli_stage_promote_keeps_records_from_different_sources_active(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            first = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Canonical fact from task object A.",
                    source_task_id="task-stage-dedupe",
                    source_object_id="knowledge-0010",
                ),
            )
            second = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Canonical fact from task object B.",
                    source_task_id="task-stage-dedupe",
                    source_object_id="knowledge-0011",
                ),
            )

            self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "stage-promote", first.candidate_id]), 0)
            self.assertEqual(
                main(["--base-dir", str(tmp_path), "knowledge", "stage-promote", second.candidate_id, "--force"]),
                0,
            )

            canonical_records = [
                json.loads(line)
                for line in canonical_registry_path(tmp_path).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(len(canonical_records), 2)
        self.assertEqual(canonical_records[0]["canonical_status"], "active")
        self.assertEqual(canonical_records[1]["canonical_status"], "active")
        self.assertEqual(canonical_records[0]["canonical_key"], "task-object:task-stage-dedupe:knowledge-0010")
        self.assertEqual(canonical_records[1]["canonical_key"], "task-object:task-stage-dedupe:knowledge-0011")

    def test_cli_stage_promote_falls_back_to_candidate_key_without_source_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            candidate = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Canonical fact without a source object id.",
                    source_task_id="task-stage-fallback",
                    source_object_id="",
                ),
            )

            self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "stage-promote", candidate.candidate_id]), 0)

            canonical_records = [
                json.loads(line)
                for line in canonical_registry_path(tmp_path).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(len(canonical_records), 1)
        self.assertEqual(canonical_records[0]["canonical_key"], f"staged-candidate:{candidate.candidate_id}")

    def test_cli_stage_promote_prints_idempotent_notice_for_existing_canonical_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            candidate = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="staged-fixedid",
                    text="Re-promote an already seeded canonical record.",
                    source_task_id="task-stage-idempotent",
                    source_object_id="knowledge-0012",
                ),
            )
            append_canonical_record(
                tmp_path,
                {
                    "canonical_id": f"canonical-{candidate.candidate_id}",
                    "canonical_key": "task-object:task-stage-idempotent:knowledge-0012",
                    "source_task_id": "task-stage-idempotent",
                    "source_object_id": "knowledge-0012",
                    "promoted_at": "2026-04-13T00:00:00+00:00",
                    "decision_note": "seeded",
                    "canonical_status": "active",
                    "superseded_by": "",
                    "superseded_at": "",
                },
            )
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "stage-promote", candidate.candidate_id]), 0)

        output = stdout.getvalue()
        self.assertIn("[IDEMPOTENT] canonical_id=canonical-staged-fixedid", output)
        self.assertIn("staged-fixedid staged_promoted canonical_id=canonical-staged-fixedid", output)

    def test_cli_stage_promote_requires_force_for_active_key_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            first = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Original staged fact.",
                    source_task_id="task-stage-notice",
                    source_object_id="knowledge-0013",
                ),
            )
            second = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Replacement staged fact.",
                    source_task_id="task-stage-notice",
                    source_object_id="knowledge-0013",
                ),
            )
            self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "stage-promote", first.candidate_id]), 0)
            stdout = StringIO()

            with redirect_stdout(stdout):
                with self.assertRaises(ValueError) as raised:
                    main(["--base-dir", str(tmp_path), "knowledge", "stage-promote", second.candidate_id])

        output = stdout.getvalue()
        self.assertIn(f"[SUPERSEDE] canonical_id=canonical-{first.candidate_id}", output)
        self.assertIn("Supersede notice detected; rerun with --force to confirm promotion.", str(raised.exception))

    def test_cli_stage_promote_with_force_prints_supersede_notice_and_promotes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            first = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Original staged fact.",
                    source_task_id="task-stage-notice",
                    source_object_id="knowledge-0013",
                ),
            )
            second = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Replacement staged fact.",
                    source_task_id="task-stage-notice",
                    source_object_id="knowledge-0013",
                ),
            )
            self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "stage-promote", first.candidate_id]), 0)
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(
                    main(["--base-dir", str(tmp_path), "knowledge", "stage-promote", second.candidate_id, "--force"]),
                    0,
                )

        output = stdout.getvalue()
        self.assertIn(f"[SUPERSEDE] canonical_id=canonical-{first.candidate_id}", output)
        self.assertIn(f"{second.candidate_id} staged_promoted canonical_id=canonical-{second.candidate_id}", output)

    def test_stage_promote_preflight_notices_return_structured_notice_records(self) -> None:
        candidate = StagedCandidate(
            candidate_id="staged-fixedid",
            text="Re-promote an already seeded canonical record.",
            source_task_id="task-stage-idempotent",
            source_object_id="knowledge-0012",
        )

        notices = build_stage_promote_preflight_notices(
            [
                {
                    "canonical_id": "canonical-staged-fixedid",
                    "canonical_key": "task-object:task-stage-idempotent:knowledge-0012",
                    "text": "Re-promote an already seeded canonical record.",
                    "canonical_status": "active",
                }
            ],
            candidate,
        )

        self.assertEqual(
            notices,
            [
                {
                    "notice_type": "idempotent",
                    "canonical_id": "canonical-staged-fixedid",
                    "text_preview": "Re-promote an already seeded canonical record.",
                }
            ],
        )
        self.assertTrue(all(isinstance(value, str) for value in notices[0].values()))

    def test_cli_stage_promote_does_not_print_preflight_notice_for_fresh_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            candidate = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Fresh staged fact without conflicts.",
                    source_task_id="task-stage-fresh",
                    source_object_id="knowledge-0014",
                ),
            )
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "stage-promote", candidate.candidate_id]), 0)

        output = stdout.getvalue()
        self.assertNotIn("(idempotent)", output)
        self.assertNotIn("(supersede)", output)
        self.assertIn(f"{candidate.candidate_id} staged_promoted canonical_id=canonical-{candidate.candidate_id}", output)

    def test_cli_stage_reject_updates_candidate_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            candidate = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Reject this staged note for now.",
                    source_task_id="task-stage-reject",
                    submitted_by="local",
                ),
            )
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "knowledge",
                            "stage-reject",
                            candidate.candidate_id,
                            "--note",
                            "Needs more evidence.",
                        ]
                    ),
                    0,
                )

            staged_records = [
                json.loads(line)
                for line in (tmp_path / ".swl" / "staged_knowledge" / "registry.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertIn(f"{candidate.candidate_id} staged_rejected status=rejected", stdout.getvalue())
        self.assertEqual(staged_records[0]["status"], "rejected")
        self.assertEqual(staged_records[0]["decision_note"], "Needs more evidence.")

    def test_cli_stage_promote_reject_block_decided_candidate_reentry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            candidate = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Once decided, candidate cannot be promoted twice.",
                    source_task_id="task-stage-block",
                ),
            )
            self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "stage-reject", candidate.candidate_id]), 0)

            with self.assertRaises(ValueError) as promote_error:
                main(["--base-dir", str(tmp_path), "knowledge", "stage-promote", candidate.candidate_id])
            with self.assertRaises(ValueError) as reject_error:
                main(["--base-dir", str(tmp_path), "knowledge", "stage-reject", candidate.candidate_id])

        self.assertIn("already decided", str(promote_error.exception))
        self.assertIn("already decided", str(reject_error.exception))

    def test_cli_canonical_reuse_evaluate_records_judgment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Canonical reuse evaluation",
                        "--goal",
                        "Record explicit evaluation for canonical reuse hits",
                        "--workspace-root",
                        str(tmp_path),
                        "--knowledge-stage",
                        "verified",
                        "--knowledge-source",
                        "chat://canonical-eval",
                        "--knowledge-item",
                        "Canonical reuse evaluation should remain explicit.",
                        "--knowledge-artifact-ref",
                        ".swl/tasks/demo/artifacts/evidence.md",
                        "--knowledge-canonicalization-intent",
                        "promote",
                    ]
                ),
                0,
            )
            task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "knowledge-promote",
                        task_id,
                        "knowledge-0001",
                        "--target",
                        "canonical",
                        "--note",
                        "Promote into canonical registry for evaluation baseline.",
                    ]
                ),
                0,
            )

            evaluation_stdout = StringIO()
            evaluation_report_stdout = StringIO()
            evaluation_json_stdout = StringIO()
            regression_report_stdout = StringIO()
            regression_json_stdout = StringIO()
            inspect_stdout = StringIO()
            review_stdout = StringIO()
            citation = ".swl/canonical_knowledge/reuse_policy.json#canonical-" + task_id + "-knowledge-0001"
            save_retrieval(
                tmp_path,
                task_id,
                [
                    RetrievalItem(
                        path=".swl/canonical_knowledge/reuse_policy.json",
                        source_type="knowledge",
                        score=11,
                        preview="Canonical reuse evaluation should remain explicit.",
                        chunk_id="canonical-" + task_id + "-knowledge-0001",
                        title="Canonical reuse evaluation",
                        citation=citation,
                        matched_terms=["canonical", "evaluation"],
                        score_breakdown={"coverage_hits": 2},
                        metadata={
                            "storage_scope": "canonical_registry",
                            "canonical_id": "canonical-" + task_id + "-knowledge-0001",
                            "canonical_policy": "reuse_visible",
                            "source_ref": "chat://canonical-eval",
                            "artifact_ref": ".swl/tasks/demo/artifacts/evidence.md",
                            "knowledge_task_relation": "current_task",
                        },
                    )
                ],
            )
            with redirect_stdout(evaluation_stdout):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "task",
                            "canonical-reuse-evaluate",
                            task_id,
                            "--citation",
                            citation,
                            "--judgment",
                            "useful",
                            "--note",
                            "Useful canonical reuse hit.",
                        ]
                    ),
                    0,
                )
            with redirect_stdout(evaluation_report_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "canonical-reuse-eval", task_id]), 0)
            with redirect_stdout(evaluation_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "canonical-reuse-eval-json", task_id]), 0)
            with redirect_stdout(regression_report_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "canonical-reuse-regression", task_id]), 0)
            with redirect_stdout(regression_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "canonical-reuse-regression-json", task_id]), 0)
            with redirect_stdout(inspect_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "inspect", task_id]), 0)
            with redirect_stdout(review_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "review", task_id]), 0)

            regression_baseline = json.loads(canonical_reuse_regression_path(tmp_path, task_id).read_text(encoding="utf-8"))

        self.assertIn("canonical_reuse_evaluated judgment=useful citations=1", evaluation_stdout.getvalue())
        self.assertIn("Canonical Reuse Evaluation", evaluation_report_stdout.getvalue())
        self.assertIn("useful_count: 1", evaluation_report_stdout.getvalue())
        self.assertIn("resolved_citation_count: 1", evaluation_report_stdout.getvalue())
        self.assertIn("retrieval_match_count: 1", evaluation_report_stdout.getvalue())
        self.assertIn(".swl/tasks/" + task_id + "/retrieval.json", evaluation_report_stdout.getvalue())
        self.assertIn(citation, evaluation_report_stdout.getvalue())
        self.assertIn('"judgment": "useful"', evaluation_json_stdout.getvalue())
        self.assertIn('"resolved_citation_count": 1', evaluation_json_stdout.getvalue())
        self.assertIn('"retrieval_match_count": 1', evaluation_json_stdout.getvalue())
        self.assertIn('"canonical_id": "canonical-' + task_id + '-knowledge-0001"', evaluation_json_stdout.getvalue())
        self.assertIn("Canonical Reuse Regression", regression_report_stdout.getvalue())
        self.assertIn("- status: match", regression_report_stdout.getvalue())
        self.assertIn("- mismatch_count: 0", regression_report_stdout.getvalue())
        self.assertIn("- evaluation_count_delta: 0", regression_report_stdout.getvalue())
        self.assertIn('"evaluation_count": 1', regression_json_stdout.getvalue())
        self.assertIn('"latest_judgment": "useful"', regression_json_stdout.getvalue())
        self.assertIn("canonical_reuse_eval_count: 1", inspect_stdout.getvalue())
        self.assertIn("canonical_reuse_eval_resolved: 1", inspect_stdout.getvalue())
        self.assertIn("canonical_reuse_eval_retrieval_matches: 1", inspect_stdout.getvalue())
        self.assertIn("canonical_reuse_eval_latest_judgment: useful", inspect_stdout.getvalue())
        self.assertIn("canonical_reuse_regression_eval_count: 1", inspect_stdout.getvalue())
        self.assertIn("canonical_reuse_regression_latest_judgment: useful", inspect_stdout.getvalue())
        self.assertIn("canonical_reuse_eval_count: 1", review_stdout.getvalue())
        self.assertIn("canonical_reuse_regression_eval_count: 1", review_stdout.getvalue())
        self.assertEqual(regression_baseline["task_id"], task_id)
        self.assertEqual(regression_baseline["evaluation_count"], 1)
        self.assertEqual(regression_baseline["judgment_counts"]["useful"], 1)
        self.assertEqual(regression_baseline["resolved_citation_count"], 1)
        self.assertEqual(regression_baseline["retrieval_match_count"], 1)
        self.assertEqual(regression_baseline["latest_judgment"], "useful")
        self.assertEqual(regression_baseline["latest_citations"], [citation])
        self.assertEqual(regression_baseline["latest_retrieval_context_ref"], f".swl/tasks/{task_id}/retrieval.json")

    def test_cli_canonical_reuse_regression_reports_mismatch_when_baseline_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Regression compare",
                        "--goal",
                        "Detect stale canonical reuse regression baseline",
                        "--workspace-root",
                        str(tmp_path),
                        "--knowledge-stage",
                        "verified",
                        "--knowledge-source",
                        "chat://canonical-regression",
                        "--knowledge-item",
                        "Canonical reuse regression should detect stale baseline files.",
                        "--knowledge-artifact-ref",
                        ".swl/tasks/demo/artifacts/evidence.md",
                        "--knowledge-canonicalization-intent",
                        "promote",
                    ]
                ),
                0,
            )
            task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "knowledge-promote",
                        task_id,
                        "knowledge-0001",
                        "--target",
                        "canonical",
                    ]
                ),
                0,
            )

            citation = ".swl/canonical_knowledge/reuse_policy.json#canonical-" + task_id + "-knowledge-0001"
            save_retrieval(
                tmp_path,
                task_id,
                [
                    RetrievalItem(
                        path=".swl/canonical_knowledge/reuse_policy.json",
                        source_type="knowledge",
                        score=7,
                        preview="Canonical reuse regression should detect stale baseline files.",
                        chunk_id="canonical-" + task_id + "-knowledge-0001",
                        title="Canonical reuse regression",
                        citation=citation,
                        matched_terms=["canonical", "regression"],
                        score_breakdown={"coverage_hits": 2},
                        metadata={
                            "storage_scope": "canonical_registry",
                            "canonical_id": "canonical-" + task_id + "-knowledge-0001",
                            "canonical_policy": "reuse_visible",
                            "source_ref": "chat://canonical-regression",
                            "artifact_ref": ".swl/tasks/demo/artifacts/evidence.md",
                            "knowledge_task_relation": "current_task",
                        },
                    )
                ],
            )
            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "canonical-reuse-evaluate",
                        task_id,
                        "--citation",
                        citation,
                        "--judgment",
                        "useful",
                    ]
                ),
                0,
            )

            stale_baseline = json.loads(canonical_reuse_regression_path(tmp_path, task_id).read_text(encoding="utf-8"))
            stale_baseline["evaluation_count"] = 0
            stale_baseline["judgment_counts"]["useful"] = 0
            stale_baseline["latest_judgment"] = ""
            canonical_reuse_regression_path(tmp_path, task_id).write_text(
                json.dumps(stale_baseline, indent=2) + "\n",
                encoding="utf-8",
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "canonical-reuse-regression", task_id]), 0)

        output = stdout.getvalue()
        self.assertIn("Canonical Reuse Regression", output)
        self.assertIn("- status: mismatch", output)
        self.assertIn("evaluation_count", output)
        self.assertIn("judgment_useful", output)
        self.assertIn("latest_judgment", output)
        self.assertIn("- evaluation_count_delta: 1", output)
        self.assertIn("- useful_delta: 1", output)

    def test_create_task_initializes_empty_canonical_reuse_regression_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Regression baseline init",
                        "--goal",
                        "Create an empty canonical reuse regression baseline artifact",
                        "--workspace-root",
                        str(tmp_path),
                    ]
                ),
                0,
            )
            task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
            regression_baseline = json.loads(canonical_reuse_regression_path(tmp_path, task_id).read_text(encoding="utf-8"))
            state = load_state(tmp_path, task_id)

        self.assertEqual(regression_baseline["task_id"], task_id)
        self.assertEqual(regression_baseline["evaluation_count"], 0)
        self.assertEqual(regression_baseline["judgment_counts"], {"useful": 0, "noisy": 0, "needs_review": 0})
        self.assertEqual(regression_baseline["resolved_citation_count"], 0)
        self.assertEqual(regression_baseline["unresolved_citation_count"], 0)
        self.assertEqual(regression_baseline["retrieval_match_count"], 0)
        self.assertEqual(regression_baseline["latest_judgment"], "")
        self.assertEqual(state.artifact_paths["canonical_reuse_regression_json"], str(canonical_reuse_regression_path(tmp_path, task_id).resolve()))

    def test_cli_create_persists_canonicalization_intent_without_promoting_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Canonicalization intent",
                        "--goal",
                        "Persist canonicalization boundary semantics",
                        "--workspace-root",
                        str(tmp_path),
                        "--knowledge-stage",
                        "verified",
                        "--knowledge-source",
                        "chat://canonicalization-intent",
                        "--knowledge-artifact-ref",
                        ".swl/tasks/demo/artifacts/summary.md",
                        "--knowledge-canonicalization-intent",
                        "promote",
                        "--knowledge-item",
                        "Verified artifact-backed knowledge may be ready for canonical review without already being canonical.",
                    ]
                ),
                0,
            )
            task_dir = next(entry for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
            knowledge_objects = json.loads((task_dir / "knowledge_objects.json").read_text(encoding="utf-8"))
            knowledge_report = (task_dir / "artifacts" / "knowledge_objects_report.md").read_text(encoding="utf-8")
            events = [
                json.loads(line)
                for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(knowledge_objects[0]["stage"], "verified")
        self.assertEqual(knowledge_objects[0]["canonicalization_intent"], "promote")
        self.assertEqual(events[0]["payload"]["knowledge_canonicalization_counts"]["promotion_ready"], 1)
        self.assertIn("canonicalization_intent: promote", knowledge_report)
        self.assertIn("canonicalization_status: promotion_ready", knowledge_report)
        self.assertIn("canonicalization_promotion_ready: 1", knowledge_report)

    def test_cli_create_builds_reusable_knowledge_index_for_artifact_backed_verified_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Knowledge index",
                        "--goal",
                        "Persist reusable knowledge index",
                        "--workspace-root",
                        str(tmp_path),
                        "--knowledge-stage",
                        "verified",
                        "--knowledge-source",
                        "chat://knowledge-index",
                        "--knowledge-retrieval-eligible",
                        "--knowledge-item",
                        "Artifact-backed verified reusable knowledge should enter the index.",
                        "--knowledge-artifact-ref",
                        ".swl/tasks/demo/artifacts/summary.md",
                    ]
                ),
                0,
            )
            task_dir = next(entry for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
            state = json.loads((task_dir / "state.json").read_text(encoding="utf-8"))
            events = [
                json.loads(line)
                for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            knowledge_index = json.loads((task_dir / "knowledge_index.json").read_text(encoding="utf-8"))
            knowledge_index_report = (task_dir / "artifacts" / "knowledge_index_report.md").read_text(encoding="utf-8")

        self.assertTrue(state["artifact_paths"]["knowledge_index_json"].endswith("knowledge_index.json"))
        self.assertTrue(state["artifact_paths"]["knowledge_index_report"].endswith("knowledge_index_report.md"))
        self.assertEqual(knowledge_index["active_reusable_count"], 1)
        self.assertEqual(knowledge_index["inactive_reusable_count"], 0)
        self.assertTrue(bool(knowledge_index["refreshed_at"]))
        self.assertEqual(knowledge_index["reusable_records"][0]["object_id"], "knowledge-0001")
        self.assertEqual(events[0]["payload"]["knowledge_index"]["active_reusable_count"], 1)
        self.assertEqual(events[0]["payload"]["knowledge_index"]["inactive_reusable_count"], 0)
        self.assertIn("Knowledge Index Report", knowledge_index_report)
        self.assertIn("active_reusable_count: 1", knowledge_index_report)
        self.assertIn("inactive_reusable_count: 0", knowledge_index_report)

    def test_cli_create_builds_inactive_knowledge_index_for_source_only_verified_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Knowledge index inactive",
                        "--goal",
                        "Persist inactive reusable knowledge records",
                        "--workspace-root",
                        str(tmp_path),
                        "--knowledge-stage",
                        "verified",
                        "--knowledge-source",
                        "chat://knowledge-index-inactive",
                        "--knowledge-retrieval-eligible",
                        "--knowledge-item",
                        "Source-only verified knowledge should remain indexed but inactive.",
                    ]
                ),
                0,
            )
            task_dir = next(entry for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
            knowledge_index = json.loads((task_dir / "knowledge_index.json").read_text(encoding="utf-8"))
            knowledge_index_report = (task_dir / "artifacts" / "knowledge_index_report.md").read_text(encoding="utf-8")

        self.assertEqual(knowledge_index["active_reusable_count"], 0)
        self.assertEqual(knowledge_index["inactive_reusable_count"], 1)
        self.assertEqual(knowledge_index["inactive_records"][0]["invalidation_reason"], "evidence_not_artifact_backed")
        self.assertIn("inactive_reusable_count: 1", knowledge_index_report)
        self.assertIn("invalidation_reason: evidence_not_artifact_backed", knowledge_index_report)

    def test_task_queue_includes_knowledge_review_attention_when_no_run_action_is_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_id = "task-knowledge-review"
            task_root = tmp_path / ".swl" / "tasks" / task_id
            task_root.mkdir(parents=True, exist_ok=True)
            state = TaskState(
                task_id=task_id,
                title="Knowledge attention",
                goal="Surface knowledge review in the operator queue",
                workspace_root=str(tmp_path),
                status="completed",
                phase="done",
                updated_at="2026-04-09T12:30:00+00:00",
                current_attempt_id="attempt-0001",
                executor_status="completed",
            )
            (task_root / "state.json").write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")
            (task_root / "knowledge_objects.json").write_text(
                json.dumps(
                    [
                        {
                            "object_id": "knowledge-0001",
                            "text": "Verified source-only knowledge still needs explicit review.",
                            "stage": "verified",
                            "source_kind": "external_knowledge_capture",
                            "source_ref": "chat://knowledge-queue",
                            "task_linked": True,
                            "captured_at": "2026-04-09T12:00:00+00:00",
                            "evidence_status": "source_only",
                            "artifact_ref": "",
                            "retrieval_eligible": True,
                            "knowledge_reuse_scope": "retrieval_candidate",
                            "canonicalization_intent": "none",
                        }
                    ],
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "queue"]), 0)

        output = stdout.getvalue()
        self.assertIn("task-knowledge-review\tknowledge-review\tcompleted\tattempt-0001", output)
        self.assertIn("knowledge_blocked_review\tmatch\tblocked=1", output)
        self.assertIn("swl task knowledge-review-queue task-knowledge-review", output)

    def test_task_acknowledge_moves_dispatch_blocked_task_back_to_local_execution_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Dispatch blocked task",
                goal="Allow operator acknowledgement",
                workspace_root=tmp_path,
            )
            persisted = load_state(tmp_path, state.task_id)
            persisted.artifact_paths["task_semantics_json"] = "missing-artifact.md"
            save_state(tmp_path, persisted)
            blocked = run_task(tmp_path, state.task_id, executor_name="mock-remote")

            acknowledged = acknowledge_task(tmp_path, blocked.task_id)
            events = [
                json.loads(line)
                for line in (tmp_path / ".swl" / "tasks" / state.task_id / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(blocked.status, "dispatch_blocked")
        self.assertEqual(acknowledged.status, "running")
        self.assertEqual(acknowledged.phase, "retrieval")
        self.assertEqual(acknowledged.topology_dispatch_status, "acknowledged")
        self.assertEqual(acknowledged.executor_name, "local")
        self.assertEqual(acknowledged.route_name, "local-summary")
        self.assertEqual(events[-1]["event_type"], "task.dispatch_acknowledged")

    def test_task_acknowledge_accepts_route_mode_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Dispatch blocked task",
                goal="Allow operator acknowledgement with an alternate local mode",
                workspace_root=tmp_path,
            )
            persisted = load_state(tmp_path, state.task_id)
            persisted.artifact_paths["task_semantics_json"] = "missing-artifact.md"
            save_state(tmp_path, persisted)
            blocked = run_task(tmp_path, state.task_id, executor_name="mock-remote")

            acknowledged = acknowledge_task(tmp_path, blocked.task_id, route_mode="offline")

        self.assertEqual(blocked.status, "dispatch_blocked")
        self.assertEqual(acknowledged.status, "running")
        self.assertEqual(acknowledged.route_mode, "offline")
        self.assertEqual(acknowledged.executor_name, "note-only")
        self.assertEqual(acknowledged.route_name, "local-note")

    def test_task_acknowledge_applies_capability_enforcement_to_reselected_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            blocked_state = TaskState(
                task_id="task-ack-enforce",
                title="Acknowledge enforce",
                goal="Apply capability enforcement on acknowledge",
                workspace_root=str(tmp_path),
                status="dispatch_blocked",
                phase="dispatch",
                route_taxonomy_role="validator",
                route_taxonomy_memory_authority="stateless",
            )
            save_state(tmp_path, blocked_state)
            enforced_route = RouteSelection(
                route=RouteSpec(
                    name="validator-local",
                    executor_name="local",
                    backend_kind="validator_test",
                    model_hint="local",
                    executor_family="cli",
                    execution_site="local",
                    remote_capable=False,
                    transport_kind="local_process",
                    capabilities=RouteCapabilities(
                        execution_kind="code_execution",
                        supports_tool_loop=True,
                        filesystem_access="workspace_write",
                        network_access="optional",
                        deterministic=False,
                        resumable=True,
                    ),
                    taxonomy=TaxonomyProfile(
                        system_role="validator",
                        memory_authority="stateless",
                    ),
                ),
                reason="Test-only validator route for acknowledge enforcement.",
                policy_inputs={},
            )

            with patch("swallow.orchestration.orchestrator.select_route", return_value=enforced_route):
                acknowledged = acknowledge_task(tmp_path, blocked_state.task_id)

        self.assertEqual(acknowledged.route_capabilities["filesystem_access"], "none")
        self.assertEqual(acknowledged.route_capabilities["network_access"], "none")
        self.assertEqual(acknowledged.route_capabilities["supports_tool_loop"], False)

    def test_task_acknowledge_rejects_non_dispatch_blocked_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Fresh task",
                goal="Do not acknowledge normal task",
                workspace_root=tmp_path,
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "acknowledge", state.task_id]), 1)

        self.assertIn("acknowledge_blocked", stdout.getvalue())
        self.assertIn("status=created", stdout.getvalue())

    def test_task_resume_runs_after_dispatch_acknowledge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Resume acknowledged task",
                goal="Resume from acknowledged dispatch block",
                workspace_root=tmp_path,
            )
            persisted = load_state(tmp_path, state.task_id)
            persisted.artifact_paths["task_semantics_json"] = "missing-artifact.md"
            save_state(tmp_path, persisted)
            blocked = run_task(tmp_path, state.task_id, executor_name="mock-remote")
            self.assertEqual(blocked.status, "dispatch_blocked")

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "acknowledge", state.task_id]), 0)
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "resume", state.task_id]), 0)

            final_state = load_state(tmp_path, state.task_id)

        self.assertEqual(final_state.status, "completed")
        self.assertEqual(final_state.executor_name, "local")
        self.assertEqual(final_state.route_name, "local-summary")
        self.assertEqual(final_state.topology_dispatch_status, "local_dispatched")
        self.assertIn("dispatch_acknowledged", stdout.getvalue())
        self.assertIn(f"{state.task_id} completed retrieval=", stdout.getvalue())

    def test_task_inspect_shows_specialist_taxonomy_for_local_note_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Specialist inspect",
                goal="Show specialist taxonomy in inspect",
                workspace_root=tmp_path,
                executor_name="note-only",
            )
            final_state = run_task(tmp_path, state.task_id, executor_name="note-only")

            self.assertEqual(final_state.route_name, "local-note")
            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "inspect", state.task_id]), 0)

        output = stdout.getvalue()
        self.assertIn("taxonomy: specialist / task-memory", output)

    def test_task_intake_prints_planning_and_knowledge_boundary_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Intake snapshot",
                        "--goal",
                        "Inspect imported planning and knowledge from a compact view",
                        "--workspace-root",
                        str(tmp_path),
                    ]
                ),
                0,
            )
            task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "planning-handoff",
                        task_id,
                        "--planning-source",
                        "chat://intake-planning",
                        "--constraint",
                        "Keep imported planning explicit",
                    ]
                ),
                0,
            )
            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "knowledge-capture",
                        task_id,
                        "--knowledge-stage",
                        "candidate",
                        "--knowledge-source",
                        "chat://intake-knowledge",
                        "--knowledge-item",
                        "Imported knowledge should remain staged.",
                    ]
                ),
                0,
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "intake", task_id]), 0)

        output = stdout.getvalue()
        self.assertIn(f"Task Intake: {task_id}", output)
        self.assertIn("Planning Handoff", output)
        self.assertIn("task_semantics_source_kind: external_planning_handoff", output)
        self.assertIn("task_semantics_source_ref: chat://intake-planning", output)
        self.assertIn("constraints_count: 1", output)
        self.assertIn("Staged Knowledge Capture", output)
        self.assertIn("knowledge_objects_count: 1", output)
        self.assertIn("knowledge_stage_counts: raw=0 candidate=1 verified=0 canonical=0", output)
        self.assertIn("Boundary", output)
        self.assertIn("task_semantics_role: execution_intent", output)
        self.assertIn("knowledge_objects_role: staged_evidence", output)
        self.assertIn("task_semantics_report:", output)
        self.assertIn("knowledge_objects_report:", output)

    def test_intake_commands_help_describes_planning_and_knowledge_paths(self) -> None:
        command_expectations = [
            (["task", "planning-handoff", "--help"], "Attach or tighten imported planning semantics"),
            (["task", "knowledge-capture", "--help"], "Attach staged knowledge objects to an existing task."),
            (["task", "intake", "--help"], "Print a compact planning-handoff and staged-knowledge intake snapshot."),
            (["task", "staged", "--help"], "Print a compact staged knowledge queue with optional task and status filters."),
            (["task", "knowledge-review-queue", "--help"], "Print a compact review queue for staged knowledge objects."),
            (["task", "knowledge-promote", "--help"], "Explicitly promote one knowledge object"),
            (["task", "knowledge-reject", "--help"], "Explicitly reject one knowledge object"),
            (["task", "canonical-registry", "--help"], "Print the canonical knowledge registry report."),
            (["task", "canonical-registry-index", "--help"], "Print the canonical knowledge registry index report."),
            (["task", "canonical-reuse", "--help"], "Print the canonical reuse policy report."),
            (["task", "canonical-reuse-regression", "--help"], "Print the canonical reuse regression compare report."),
            (["task", "canonical-reuse-eval", "--help"], "Print the canonical reuse evaluation report."),
            (["task", "canonical-reuse-evaluate", "--help"], "Record an explicit canonical reuse evaluation judgment"),
            (["task", "canonical-reuse-regression-json", "--help"], "Print the canonical reuse regression baseline record."),
        ]

        for argv, expected in command_expectations:
            stdout = StringIO()
            with redirect_stdout(stdout):
                with self.assertRaises(SystemExit) as raised:
                    main(argv)
            self.assertEqual(raised.exception.code, 0)
            self.assertIn(expected, stdout.getvalue())

    def test_global_knowledge_help_describes_stage_commands(self) -> None:
        command_expectations = [
            (["knowledge", "--help"], "stage-list"),
            (["knowledge", "stage-list", "--help"], "List pending staged knowledge candidates."),
            (["knowledge", "stage-inspect", "--help"], "Inspect one staged knowledge candidate."),
            (["knowledge", "stage-promote", "--help"], "Promote one pending staged candidate into the canonical registry."),
            (["knowledge", "stage-reject", "--help"], "Reject one pending staged candidate."),
            (["knowledge", "canonical-audit", "--help"], "Audit canonical registry health."),
            (["knowledge", "ingest-file", "--help"], "Ingest one local markdown/text file into staged knowledge."),
            (["knowledge", "link", "--help"], "Create one explicit relation between two knowledge objects."),
            (["knowledge", "unlink", "--help"], "Delete one explicit relation between two knowledge objects."),
            (["knowledge", "links", "--help"], "List explicit relations for one knowledge object."),
        ]

        for argv, expected in command_expectations:
            stdout = StringIO()
            with redirect_stdout(stdout):
                with self.assertRaises(SystemExit) as raised:
                    main(argv)
            self.assertEqual(raised.exception.code, 0)
            self.assertIn(expected, stdout.getvalue())

    def test_ingest_help_describes_external_session_ingestion(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as raised:
                main(["ingest", "--help"])

        self.assertEqual(raised.exception.code, 0)
        output = stdout.getvalue()
        self.assertIn("Parse an external session export, filter it into staged candidates", output)
        self.assertIn("--dry-run", output)
        self.assertIn("--format", output)
        self.assertIn("--from-clipboard", output)
        self.assertIn("--summary", output)

    def test_cli_ingest_dry_run_prints_report_without_persisting_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "session.md"
            source.write_text("# Constraints\nNo realtime sync.\n\n# Thanks\n谢谢", encoding="utf-8")
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "ingest", str(source), "--dry-run"]), 0)

            staged_records = load_staged_candidates(tmp_path)

        output = stdout.getvalue()
        self.assertIn("# Ingestion Report", output)
        self.assertIn("dry_run: yes", output)
        self.assertIn("source_kind: external_session_ingestion", output)
        self.assertEqual(staged_records, [])

    def test_cli_ingest_persists_staged_candidates_with_external_session_source_kind(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "session.md"
            source.write_text("# Decisions\nDecision: keep staged review manual.", encoding="utf-8")
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "ingest", str(source)]), 0)

            staged_records = load_staged_candidates(tmp_path)

        output = stdout.getvalue()
        self.assertIn("dry_run: no", output)
        self.assertEqual(len(staged_records), 1)
        self.assertEqual(staged_records[0].source_kind, "external_session_ingestion")
        self.assertEqual(staged_records[0].source_ref, "file://workspace/session.md")

    def test_cli_ingest_summary_appends_structured_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "session.md"
            source.write_text(
                "# Decisions\nDecision: keep staged review manual.\n\n# Constraints\nConstraint: no realtime sync.",
                encoding="utf-8",
            )
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "ingest", str(source), "--dry-run", "--summary"]), 0)

        output = stdout.getvalue()
        self.assertIn("# Ingestion Report", output)
        self.assertIn("# Ingestion Summary", output)
        self.assertIn("## Decisions (1)", output)
        self.assertIn("## Constraints (1)", output)
        self.assertIn("## Rejected Alternatives (0)", output)

    def test_cli_ingest_from_clipboard_supports_generic_chat_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            stdout = StringIO()

            with patch(
                "swallow.adapters.cli._read_clipboard_bytes",
                return_value=json.dumps([{"role": "user", "content": "Decision: keep it simple."}]).encode("utf-8"),
            ):
                with redirect_stdout(stdout):
                    self.assertEqual(
                        main(
                            [
                                "--base-dir",
                                str(tmp_path),
                                "ingest",
                                "--from-clipboard",
                                "--format",
                                "generic_chat_json",
                            ]
                        ),
                        0,
                    )

            staged_records = load_staged_candidates(tmp_path)

        output = stdout.getvalue()
        self.assertIn("source_path: clipboard://generic_chat_json", output)
        self.assertEqual(len(staged_records), 1)
        self.assertEqual(staged_records[0].source_ref, "clipboard://generic_chat_json")
        self.assertTrue(staged_records[0].source_task_id.startswith("ingest-clipboard-"))

    def test_cli_ingest_from_clipboard_uses_auto_source_ref_when_format_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            stdout = StringIO()

            with patch(
                "swallow.adapters.cli._read_clipboard_bytes",
                return_value=b"# Constraints\nConstraint: clipboard path is supplemental.",
            ):
                with redirect_stdout(stdout):
                    self.assertEqual(main(["--base-dir", str(tmp_path), "ingest", "--from-clipboard", "--dry-run"]), 0)

        output = stdout.getvalue()
        self.assertIn("source_path: clipboard://auto", output)
        self.assertIn("detected_format: markdown", output)

    def test_cli_ingest_rejects_both_file_and_clipboard_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "session.md"
            source.write_text("# Decisions\nDecision: keep one input path.", encoding="utf-8")
            stderr = StringIO()

            with redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as raised:
                    main(["--base-dir", str(tmp_path), "ingest", str(source), "--from-clipboard"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("requires exactly one input source", stderr.getvalue())

    def test_cli_ingest_rejects_missing_input_source(self) -> None:
        stderr = StringIO()

        with redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as raised:
                main(["ingest"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("requires exactly one input source", stderr.getvalue())

    def test_cli_knowledge_ingest_file_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "notes.md"
            source.write_text("# Decisions\nKeep staged review manual.", encoding="utf-8")
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "ingest-file", str(source)]), 0)

            staged_records = load_staged_candidates(tmp_path)

        output = stdout.getvalue()
        self.assertIn("# Ingestion Report", output)
        self.assertIn("dry_run: no", output)
        self.assertEqual(len(staged_records), 1)
        self.assertEqual(staged_records[0].source_kind, "local_file_capture")
        self.assertEqual(staged_records[0].source_ref, "file://workspace/notes.md")

    def test_cli_knowledge_link_command(self) -> None:
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
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "knowledge",
                            "link",
                            "knowledge-a",
                            "knowledge-b",
                            "--type",
                            "cites",
                            "--confidence",
                            "0.8",
                            "--context",
                            "A cites B",
                        ]
                    ),
                    0,
                )

        output = stdout.getvalue()
        self.assertIn("relation_id: relation-", output)
        self.assertIn("relation_type: cites", output)
        self.assertIn("source_object_id: knowledge-a", output)
        self.assertIn("target_object_id: knowledge-b", output)

    def test_cli_knowledge_links_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            save_knowledge_objects(tmp_path, "task-a", [{"object_id": "knowledge-a", "text": "A", "stage": "verified"}])
            save_knowledge_objects(tmp_path, "task-b", [{"object_id": "knowledge-b", "text": "B", "stage": "verified"}])
            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "knowledge",
                        "link",
                        "knowledge-a",
                        "knowledge-b",
                        "--type",
                        "related_to",
                    ]
                ),
                0,
            )
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "links", "knowledge-a"]), 0)

        output = stdout.getvalue()
        self.assertIn("# Knowledge Relations", output)
        self.assertIn("object_id: knowledge-a", output)
        self.assertIn("relation_type: related_to", output)
        self.assertIn("counterparty_object_id: knowledge-b", output)

    def test_cli_knowledge_unlink_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            save_knowledge_objects(tmp_path, "task-a", [{"object_id": "knowledge-a", "text": "A", "stage": "verified"}])
            save_knowledge_objects(tmp_path, "task-b", [{"object_id": "knowledge-b", "text": "B", "stage": "verified"}])
            create_stdout = StringIO()

            with redirect_stdout(create_stdout):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "knowledge",
                            "link",
                            "knowledge-a",
                            "knowledge-b",
                            "--type",
                            "extends",
                        ]
                    ),
                    0,
                )

            relation_line = next(
                line for line in create_stdout.getvalue().splitlines() if line.startswith("relation_id: ")
            )
            relation_id = relation_line.split(": ", 1)[1]
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "unlink", relation_id]), 0)

        output = stdout.getvalue()
        self.assertIn(f"deleted_relation_id: {relation_id}", output)

    def test_cli_canonical_audit_reports_empty_registry_as_no_issues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "canonical-audit"]), 0)

        output = stdout.getvalue()
        self.assertIn("Canonical Registry Audit", output)
        self.assertIn("total: 0", output)
        self.assertIn("duplicate_active_keys: 0", output)
        self.assertIn("orphan_records: 0", output)
        self.assertIn("no issues", output)

    def test_cli_canonical_audit_reports_duplicate_active_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            registry_file = canonical_registry_path(tmp_path)
            registry_file.parent.mkdir(parents=True, exist_ok=True)
            registry_file.write_text(
                "".join(
                    [
                        json.dumps(
                            {
                                "canonical_id": "canonical-a",
                                "canonical_key": "task-object:task-a:object-1",
                                "source_task_id": "task-a",
                                "source_object_id": "object-1",
                                "canonical_status": "active",
                            }
                        )
                        + "\n",
                        json.dumps(
                            {
                                "canonical_id": "canonical-b",
                                "canonical_key": "task-object:task-a:object-1",
                                "source_task_id": "task-a",
                                "source_object_id": "object-1",
                                "canonical_status": "active",
                            }
                        )
                        + "\n",
                    ]
                ),
                encoding="utf-8",
            )
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "canonical-audit"]), 0)

        output = stdout.getvalue()
        self.assertIn("duplicate_active_keys: 1", output)
        self.assertIn("Duplicate Active Keys", output)
        self.assertIn("- task-object:task-a:object-1: canonical-a, canonical-b", output)

    def test_cli_canonical_audit_reports_orphan_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            append_canonical_record(
                tmp_path,
                {
                    "canonical_id": "canonical-orphan",
                    "canonical_key": "task-object:missing-task:object-9",
                    "source_task_id": "missing-task",
                    "source_object_id": "object-9",
                    "promoted_at": "2026-04-13T00:00:00+00:00",
                    "decision_note": "orphan",
                    "canonical_status": "active",
                    "superseded_by": "",
                    "superseded_at": "",
                },
            )
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "canonical-audit"]), 0)

        output = stdout.getvalue()
        self.assertIn("orphan_records: 1", output)
        self.assertIn("Orphan Records", output)
        self.assertIn("- canonical-orphan", output)

    def test_cli_canonical_audit_reports_no_issues_for_healthy_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Canonical audit healthy",
                        "--goal",
                        "Seed a canonical record with a valid source object",
                        "--workspace-root",
                        str(tmp_path),
                    ]
                ),
                0,
            )
            save_knowledge_objects(
                tmp_path,
                "task-0001",
                [
                    {
                        "object_id": "knowledge-healthy",
                        "text": "Healthy canonical fact.",
                        "stage": "canonical",
                    }
                ],
                write_authority=OPERATOR_CANONICAL_WRITE_AUTHORITY,
            )
            append_canonical_record(
                tmp_path,
                {
                    "canonical_id": "canonical-healthy",
                    "canonical_key": "task-object:task-0001:knowledge-healthy",
                    "source_task_id": "task-0001",
                    "source_object_id": "knowledge-healthy",
                    "promoted_at": "2026-04-13T00:00:00+00:00",
                    "decision_note": "healthy",
                    "canonical_status": "active",
                    "superseded_by": "",
                    "superseded_at": "",
                },
            )
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "canonical-audit"]), 0)

        output = stdout.getvalue()
        self.assertIn("total: 1", output)
        self.assertIn("duplicate_active_keys: 0", output)
        self.assertIn("orphan_records: 0", output)
        self.assertIn("no issues", output)

    def test_note_only_mode_skips_subprocess(self) -> None:
        state = TaskState(
            task_id="note123",
            title="Note only",
            goal="Skip live execution",
            workspace_root="/tmp",
        )
        with patch.dict("os.environ", {"AIWF_EXECUTOR_MODE": "note-only"}, clear=False):
            with patch("swallow.orchestration.executor.subprocess.run") as mocked_run:
                from swallow.orchestration.executor import run_executor

                result = run_executor(state, [])

        mocked_run.assert_not_called()
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.failure_kind, "unreachable_backend")
        self.assertIn("non-live mode", result.message)
        self.assertIn("# Executor Fallback Note", result.output)

    def test_knowledge_migrate_dry_run_reports_candidates_without_writing_db(self) -> None:
        stdout = StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            with patch.dict("os.environ", {"SWALLOW_STORE_BACKEND": "file"}, clear=False):
                save_knowledge_objects(
                    base_dir,
                    "legacy-knowledge",
                    [
                        {
                            "object_id": "knowledge-0001",
                            "text": "Dry-run knowledge candidate",
                            "stage": "verified",
                            "evidence_status": "artifact_backed",
                            "artifact_ref": ".swl/tasks/legacy-knowledge/artifacts/evidence.md",
                        }
                    ],
                )
            with redirect_stdout(stdout):
                exit_code = main(["--base-dir", str(base_dir), "knowledge", "migrate", "--dry-run"])
            db_exists = swallow_db_path(base_dir).exists()

        self.assertEqual(exit_code, 0)
        self.assertFalse(db_exists)
        output = stdout.getvalue()
        self.assertIn("dry_run=yes", output)
        self.assertIn("task_count_migrated=1", output)
        self.assertIn("knowledge_object_count_migrated=1", output)

    def test_knowledge_migrate_imports_file_knowledge_into_sqlite(self) -> None:
        stdout = StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            with patch.dict("os.environ", {"SWALLOW_STORE_BACKEND": "file"}, clear=False):
                save_knowledge_objects(
                    base_dir,
                    "legacy-knowledge",
                    [
                        {
                            "object_id": "knowledge-0001",
                            "text": "Migrate sqlite knowledge",
                            "stage": "verified",
                            "evidence_status": "artifact_backed",
                            "artifact_ref": ".swl/tasks/legacy-knowledge/artifacts/evidence.md",
                        }
                    ],
                )
            with redirect_stdout(stdout):
                exit_code = main(["--base-dir", str(base_dir), "knowledge", "migrate"])
            db_exists = swallow_db_path(base_dir).exists()
            migrated_knowledge = load_knowledge_objects(base_dir, "legacy-knowledge")

        self.assertEqual(exit_code, 0)
        self.assertTrue(db_exists)
        self.assertEqual(migrated_knowledge[0]["text"], "Migrate sqlite knowledge")
        output = stdout.getvalue()
        self.assertIn("dry_run=no", output)
        self.assertIn("task_count_migrated=1", output)
        self.assertIn("knowledge_object_count_migrated=1", output)

    def test_run_task_canonical_forbidden_route_does_not_stage_knowledge_in_orchestrator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            created = create_task(
                base_dir=tmp_path,
                title="Stage restricted knowledge",
                goal="Route verified knowledge into staged storage for operator review",
                workspace_root=tmp_path,
                executor_name="local",
            )
            restricted_route = RouteSelection(
                route=RouteSpec(
                    name="restricted-specialist",
                    executor_name="note-only",
                    backend_kind="local_fallback",
                    model_hint="note-only",
                    executor_family="cli",
                    execution_site="local",
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
                    taxonomy=TaxonomyProfile(
                        system_role="specialist",
                        memory_authority="canonical-write-forbidden",
                    ),
                ),
                reason="Test-only canonical forbidden route.",
                policy_inputs={},
            )

            def write_artifacts_side_effect(
                _base_dir: Path,
                state: TaskState,
                _retrieval_items: list[RetrievalItem],
                _executor_result: ExecutorResult,
                grounding_evidence_override: dict[str, object] | None = None,
            ) -> tuple[ValidationResult, ValidationResult, ValidationResult, ValidationResult, ValidationResult, ValidationResult, ValidationResult]:
                save_knowledge_objects(
                    _base_dir,
                    state.task_id,
                    [
                        {
                            "object_id": "knowledge-0001",
                            "text": "Verified guidance should enter staged review first.",
                            "stage": "verified",
                            "source_kind": "external_knowledge_capture",
                            "source_ref": "chat://stage-route",
                            "task_linked": True,
                            "captured_at": "2026-04-12T00:00:00+00:00",
                            "evidence_status": "artifact_backed",
                            "artifact_ref": ".swl/tasks/demo/artifacts/evidence.md",
                            "retrieval_eligible": False,
                            "knowledge_reuse_scope": "task_only",
                            "canonicalization_intent": "promote",
                        }
                    ],
                )
                return (
                    ValidationResult(status="passed", message="Compatibility passed."),
                    ValidationResult(status="passed", message="Execution fit passed."),
                    ValidationResult(status="passed", message="Knowledge policy passed."),
                    ValidationResult(status="passed", message="Validation passed."),
                    ValidationResult(status="passed", message="Retry policy passed."),
                    ValidationResult(status="passed", message="Execution budget policy passed."),
                    ValidationResult(status="warning", message="Stop policy warning."),
                )

            with patch("swallow.orchestration.orchestrator.select_route", return_value=restricted_route):
                with patch("swallow.orchestration.orchestrator.run_retrieval", return_value=[]):
                    with patch(
                        "swallow.orchestration.orchestrator._execute_task_card",
                        return_value=ExecutorResult(
                            executor_name="note-only",
                            status="completed",
                            message="Execution finished.",
                            output="done",
                        ),
                    ):
                        with patch("swallow.orchestration.orchestrator.write_task_artifacts", side_effect=write_artifacts_side_effect):
                            final_state = run_task(tmp_path, created.task_id, executor_name="local")

            staged_records = load_staged_candidates(tmp_path)
            events = [
                json.loads(line)
                for line in (tmp_path / ".swl" / "tasks" / created.task_id / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(final_state.status, "completed")
        self.assertEqual(final_state.route_taxonomy_memory_authority, "canonical-write-forbidden")
        self.assertEqual(staged_records, [])
        guard_warning = next(event for event in events if event["event_type"] == "task.canonical_write_guard_warning")
        self.assertEqual(guard_warning["payload"]["canonical_write_guard"], True)
        self.assertEqual(guard_warning["payload"]["executor_name"], "note-only")
        self.assertEqual(guard_warning["payload"]["route_taxonomy_memory_authority"], "canonical-write-forbidden")
        self.assertFalse(any(event["event_type"] == "task.knowledge_staged" for event in events))
        self.assertEqual(events[-1]["payload"]["staged_candidate_count"], 0)

    def test_failure_resume_note_keeps_failure_guidance(self) -> None:
        state = TaskState(
            task_id="resumefail",
            title="Failure resume note",
            goal="Keep failure guidance",
            workspace_root="/tmp",
            status="failed",
            phase="summarize",
        )
        retrieval_items = [
            RetrievalItem(path="notes.md", source_type="notes", score=2, preview="failure resume"),
        ]
        executor_result = ExecutorResult(
            executor_name="aider",
            status="failed",
            message="Aider binary not found.",
            output="fallback",
            failure_kind="launch_error",
        )

        note = build_resume_note(state, retrieval_items, executor_result, None, None, None, None, None, None, None)

        self.assertIn("treat this run as incomplete", note)
        self.assertIn("Treat this run as a failed live execution attempt", note)
        self.assertIn("Verify that the configured live executor binary is installed", note)

    def test_rerun_from_analysis_reuses_previous_execution_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "notes.md").write_text("# Notes\n\nselective rerun analysis\n", encoding="utf-8")

            with patch.dict("os.environ", {"AIWF_EXECUTOR_MODE": "mock"}, clear=False):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "task",
                            "create",
                            "--title",
                            "Selective analysis rerun",
                            "--goal",
                            "Reuse executor artifacts",
                            "--workspace-root",
                            str(tmp_path),
                        ]
                    ),
                    0,
                )
                task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)

            with patch("swallow.orchestration.harness.retrieve_context", side_effect=AssertionError("retrieval should be skipped")):
                with patch("swallow.orchestration.harness.run_executor", side_effect=AssertionError("execution should be skipped")):
                    self.assertEqual(
                        main(
                            [
                                "--base-dir",
                                str(tmp_path),
                                "task",
                                "rerun",
                                task_id,
                                "--from-phase",
                                "analysis",
                            ]
                        ),
                        0,
                    )

            task_dir = tmp_path / ".swl" / "tasks" / task_id
            events = [
                json.loads(line)
                for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            inspect_stdout = StringIO()
            review_stdout = StringIO()
            with redirect_stdout(inspect_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "inspect", task_id]), 0)
            with redirect_stdout(review_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "review", task_id]), 0)

        second_attempt_phase_events = [
            event
            for event in events
            if event["event_type"] == "task.phase_checkpoint" and event["payload"].get("source") in {"previous_retrieval", "previous_execution", "live_analysis"}
        ][-3:]
        self.assertEqual(
            [(event["payload"]["execution_phase"], event["payload"]["skipped"]) for event in second_attempt_phase_events],
            [("retrieval_done", True), ("execution_done", True), ("analysis_done", False)],
        )
        self.assertIn("execution_phase: analysis_done", inspect_stdout.getvalue())
        self.assertIn("last_phase_checkpoint_at:", inspect_stdout.getvalue())
        self.assertIn("execution_phase: analysis_done", review_stdout.getvalue())
        self.assertIn("last_phase_checkpoint_at:", review_stdout.getvalue())
