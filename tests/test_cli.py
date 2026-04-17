from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys
import subprocess
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.cli import main
from swallow.compatibility import build_compatibility_report, evaluate_route_compatibility
from swallow.capabilities import (
    DEFAULT_CAPABILITY_MANIFEST,
    build_capability_assembly,
    parse_capability_refs,
    validate_capability_manifest,
)
from swallow.execution_fit import build_execution_fit_report, evaluate_execution_fit
from swallow.executor import (
    build_formatted_executor_prompt,
    build_fallback_output,
    classify_failure_kind,
    normalize_executor_name,
    resolve_dialect_name,
    resolve_executor_name,
    run_codex_executor,
)
from swallow.harness import (
    build_remote_handoff_contract_record,
    build_resume_note,
    build_retrieval_report,
    build_source_grounding,
)
from swallow.knowledge_policy import evaluate_knowledge_policy
from swallow.models import (
    DispatchVerdict,
    Event,
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
from swallow.orchestrator import acknowledge_task, build_task_retrieval_request, create_task, decide_task_knowledge, run_task
from swallow.paths import (
    canonical_registry_path,
    canonical_reuse_policy_path,
    canonical_reuse_regression_path,
    knowledge_wiki_entry_path,
    remote_handoff_contract_path,
)
from swallow.retrieval import ARTIFACTS_SOURCE_TYPE, KNOWLEDGE_SOURCE_TYPE, retrieve_context
from swallow.retrieval_adapters import select_retrieval_adapter
from swallow.router import select_route
from swallow.staged_knowledge import StagedCandidate, submit_staged_candidate
from swallow.store import (
    append_canonical_record,
    load_state,
    save_knowledge_objects,
    save_remote_handoff_contract,
    save_retrieval,
    save_state,
)
from swallow.validator import build_validation_report, validate_run_outputs


class CliLifecycleTest(unittest.TestCase):
    def test_parse_capability_refs_returns_default_manifest_when_not_provided(self) -> None:
        manifest = parse_capability_refs(None)

        self.assertEqual(manifest.to_dict(), DEFAULT_CAPABILITY_MANIFEST.to_dict())

    def test_parse_capability_refs_builds_manifest_from_explicit_refs(self) -> None:
        manifest = parse_capability_refs(
            [
                "profile:baseline_local",
                "workflow:task_loop",
                "validator:run_output_validation",
                "skill:plan-task",
                "tool:doctor.codex",
            ]
        )

        self.assertEqual(manifest.profile_refs, ["baseline_local"])
        self.assertEqual(manifest.workflow_refs, ["task_loop"])
        self.assertEqual(manifest.validator_refs, ["run_output_validation"])
        self.assertEqual(manifest.skill_refs, ["plan-task"])
        self.assertEqual(manifest.tool_refs, ["doctor.codex"])

    def test_validate_capability_manifest_reports_unknown_refs(self) -> None:
        manifest = parse_capability_refs(
            [
                "profile:missing_profile",
                "validator:missing_validator",
            ]
        )

        errors = validate_capability_manifest(manifest)

        self.assertIn("Unknown profile capability: missing_profile", errors)
        self.assertIn("Unknown validator capability: missing_validator", errors)

    def test_create_task_persists_default_capability_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Default capability manifest",
                goal="Persist baseline capability selection",
                workspace_root=tmp_path,
            )
            persisted = json.loads((tmp_path / ".swl" / "tasks" / state.task_id / "state.json").read_text(encoding="utf-8"))
            capability_assembly = json.loads(
                (tmp_path / ".swl" / "tasks" / state.task_id / "capability_assembly.json").read_text(encoding="utf-8")
            )

        self.assertEqual(state.capability_manifest, DEFAULT_CAPABILITY_MANIFEST.to_dict())
        self.assertEqual(state.capability_assembly, build_capability_assembly(DEFAULT_CAPABILITY_MANIFEST).to_dict())
        self.assertEqual(persisted["capability_manifest"], DEFAULT_CAPABILITY_MANIFEST.to_dict())
        self.assertEqual(capability_assembly["effective"], DEFAULT_CAPABILITY_MANIFEST.to_dict())

    def test_create_task_initializes_remote_handoff_contract_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Remote handoff baseline",
                goal="Persist baseline remote handoff contract truth",
                workspace_root=tmp_path,
            )
            contract = json.loads(remote_handoff_contract_path(tmp_path, state.task_id).read_text(encoding="utf-8"))
            report = (
                tmp_path / ".swl" / "tasks" / state.task_id / "artifacts" / "remote_handoff_contract_report.md"
            ).read_text(encoding="utf-8")

        self.assertEqual(contract["contract_kind"], "not_applicable")
        self.assertEqual(contract["contract_status"], "not_needed")
        self.assertEqual(contract["handoff_boundary"], "local_baseline")
        self.assertEqual(contract["transport_truth"], "local_only")
        self.assertEqual(contract["ownership_required"], "no")
        self.assertEqual(contract["dispatch_readiness"], "not_applicable")
        self.assertEqual(contract["goal"], "Persist baseline remote handoff contract truth")
        self.assertEqual(contract["constraints"], [])
        self.assertEqual(contract["done"], ["Current route remains inside the local execution baseline."])
        self.assertEqual(contract["next_steps"], ["Continue through the existing local execution path."])
        self.assertTrue(contract["context_pointers"])
        self.assertFalse(contract["remote_candidate"])
        self.assertFalse(contract["operator_ack_required"])
        self.assertEqual(contract["next_owner_kind"], "local_orchestrator")
        self.assertTrue(state.artifact_paths["remote_handoff_contract_json"].endswith("remote_handoff_contract.json"))
        self.assertTrue(
            state.artifact_paths["remote_handoff_contract_report"].endswith("remote_handoff_contract_report.md")
        )
        self.assertIn("Remote Handoff Contract Report", report)
        self.assertIn("contract_kind: not_applicable", report)
        self.assertIn("handoff_boundary: local_baseline", report)
        self.assertIn("## Unified Handoff Schema", report)
        self.assertIn("goal: Persist baseline remote handoff contract truth", report)

    def test_handoff_contract_schema_serializes_unified_fields(self) -> None:
        schema = HandoffContractSchema(
            goal="Unify the handoff vocabulary",
            constraints=["Do not expand remote execution"],
            done=["Phase 18 baseline already landed"],
            next_steps=["Validate remote_handoff_contract.json on write"],
            context_pointers=["docs/plans/phase19/design_decision.md"],
        )

        self.assertEqual(
            schema.to_dict(),
            {
                "goal": "Unify the handoff vocabulary",
                "constraints": ["Do not expand remote execution"],
                "done": ["Phase 18 baseline already landed"],
                "next_steps": ["Validate remote_handoff_contract.json on write"],
                "context_pointers": ["docs/plans/phase19/design_decision.md"],
            },
        )

    def test_evaluate_dispatch_verdict_routes_local_contracts_to_local_execution(self) -> None:
        verdict = evaluate_dispatch_verdict(
            {
                "remote_candidate": False,
                "operator_ack_required": False,
            }
        )

        self.assertEqual(
            verdict,
            DispatchVerdict(
                action="local",
                reason="handoff contract stays within the local execution baseline",
                blocking_detail="",
            ),
        )

    def test_evaluate_dispatch_verdict_blocks_remote_contracts_awaiting_operator_ack(self) -> None:
        verdict = evaluate_dispatch_verdict(
            {
                "contract_kind": "remote_handoff_candidate",
                "contract_status": "planned",
                "handoff_boundary": "cross_site_candidate",
                "contract_reason": "remote handoff required",
                "remote_candidate": True,
                "remote_capable_intent": True,
                "execution_site": "remote",
                "execution_site_contract_kind": "remote_candidate",
                "execution_site_contract_status": "planned",
                "transport_kind": "mock_remote_transport",
                "transport_truth": "explicit_remote_transport_required",
                "ownership_required": "yes",
                "ownership_truth": "transfer_required_before_remote_dispatch",
                "dispatch_readiness": "contract_required",
                "dispatch_truth": "planned",
                "operator_ack_required": True,
                "next_owner_kind": "remote_executor",
                "next_owner_ref": "unassigned",
                "blocking_reason": "awaiting review",
                "recommended_next_action": "Review the remote handoff contract before dispatch.",
                "goal": "Dispatch to mock remote executor",
                "constraints": ["Do not introduce real network transport"],
                "done": ["Schema was validated"],
                "next_steps": ["Approve remote handoff contract"],
                "context_pointers": ["remote_handoff_contract.json"],
            }
        )

        self.assertEqual(verdict.action, "blocked")
        self.assertEqual(verdict.reason, "remote handoff contract still requires operator acknowledgment")
        self.assertEqual(verdict.blocking_detail, "Review the remote handoff contract before dispatch.")

    def test_evaluate_dispatch_verdict_routes_ack_free_remote_contracts_to_mock_remote(self) -> None:
        verdict = evaluate_dispatch_verdict(
            {
                "contract_kind": "remote_handoff_candidate",
                "contract_status": "ready",
                "handoff_boundary": "cross_site_candidate",
                "contract_reason": "mock dispatch allowed",
                "remote_candidate": True,
                "remote_capable_intent": True,
                "execution_site": "remote",
                "execution_site_contract_kind": "remote_candidate",
                "execution_site_contract_status": "ready",
                "transport_kind": "mock_remote_transport",
                "transport_truth": "explicit_remote_transport_required",
                "ownership_required": "yes",
                "ownership_truth": "transfer_required_before_remote_dispatch",
                "dispatch_readiness": "ready",
                "dispatch_truth": "planned",
                "operator_ack_required": False,
                "next_owner_kind": "remote_executor",
                "next_owner_ref": "mock-remote-node",
                "blocking_reason": "",
                "recommended_next_action": "Dispatch to the mock remote executor.",
                "goal": "Dispatch to mock remote executor",
                "constraints": ["Do not introduce real network transport"],
                "done": ["Contract approved"],
                "next_steps": ["Run mock remote executor"],
                "context_pointers": ["remote_handoff_contract.json"],
            }
        )

        self.assertEqual(
            verdict,
            DispatchVerdict(
                action="mock_remote",
                reason="remote handoff contract is valid and no operator acknowledgment is pending",
                blocking_detail="",
            ),
        )

    def test_remote_handoff_contract_record_marks_cross_site_candidate_truth(self) -> None:
        state = TaskState(
            task_id="task-remote",
            title="Remote candidate",
            goal="Describe remote handoff contract",
            workspace_root="/tmp/workspace",
            route_name="remote-prototype",
            route_execution_site="remote",
            route_remote_capable=True,
            route_transport_kind="remote_transport_candidate",
            topology_route_name="remote-prototype",
            topology_execution_site="remote",
            topology_transport_kind="remote_transport_candidate",
            topology_remote_capable_intent=True,
            topology_dispatch_status="planned",
            execution_site_contract_kind="remote_candidate",
            execution_site_boundary="cross_site_candidate",
            execution_site_contract_status="planned",
            execution_site_handoff_required=True,
        )

        contract = build_remote_handoff_contract_record(state)

        self.assertEqual(contract["contract_kind"], "remote_handoff_candidate")
        self.assertEqual(contract["contract_status"], "planned")
        self.assertEqual(contract["handoff_boundary"], "cross_site_candidate")
        self.assertEqual(contract["transport_truth"], "explicit_remote_transport_required")
        self.assertEqual(contract["ownership_required"], "yes")
        self.assertEqual(contract["ownership_truth"], "transfer_required_before_remote_dispatch")
        self.assertEqual(contract["dispatch_readiness"], "contract_required")
        self.assertEqual(contract["dispatch_truth"], "planned")
        self.assertEqual(contract["goal"], "Describe remote handoff contract")
        self.assertEqual(contract["constraints"], [])
        self.assertEqual(
            contract["done"],
            ["Remote candidate contract detected; dispatch remains blocked until contract review is complete."],
        )
        self.assertEqual(
            contract["next_steps"],
            ["Review the remote handoff contract before treating this task as ready for remote dispatch."],
        )
        self.assertEqual(contract["context_pointers"], [])
        self.assertTrue(contract["remote_candidate"])
        self.assertTrue(contract["remote_capable_intent"])
        self.assertTrue(contract["operator_ack_required"])
        self.assertEqual(contract["next_owner_kind"], "remote_executor")
        self.assertEqual(contract["next_owner_ref"], "unassigned")

    def test_validate_remote_handoff_contract_payload_reports_schema_errors(self) -> None:
        errors = validate_remote_handoff_contract_payload(
            {
                "contract_kind": "remote_handoff_candidate",
                "contract_status": "planned",
                "handoff_boundary": "cross_site_candidate",
                "contract_reason": "missing schema fields",
                "remote_candidate": True,
                "remote_capable_intent": True,
                "execution_site": "remote",
                "execution_site_contract_kind": "remote_candidate",
                "execution_site_contract_status": "planned",
                "transport_kind": "remote_transport_candidate",
                "transport_truth": "explicit_remote_transport_required",
                "ownership_required": "yes",
                "ownership_truth": "transfer_required_before_remote_dispatch",
                "dispatch_readiness": "contract_required",
                "dispatch_truth": "planned",
                "operator_ack_required": True,
                "next_owner_kind": "remote_executor",
                "next_owner_ref": "unassigned",
                "blocking_reason": "blocked",
                "recommended_next_action": "review",
                "goal": "Describe remote handoff contract",
                "constraints": [],
                "done": ["ready"],
                "next_steps": "review next",
                "context_pointers": [],
            }
        )

        self.assertIn("next_steps must be a list of non-empty strings", errors)

    def test_save_remote_handoff_contract_rejects_invalid_schema_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            with self.assertRaisesRegex(ValueError, "next_steps must be a list of non-empty strings"):
                save_remote_handoff_contract(
                    tmp_path,
                    "task-invalid-handoff",
                    {
                        "contract_kind": "remote_handoff_candidate",
                        "contract_status": "planned",
                        "handoff_boundary": "cross_site_candidate",
                        "contract_reason": "missing schema typing",
                        "remote_candidate": True,
                        "remote_capable_intent": True,
                        "execution_site": "remote",
                        "execution_site_contract_kind": "remote_candidate",
                        "execution_site_contract_status": "planned",
                        "transport_kind": "remote_transport_candidate",
                        "transport_truth": "explicit_remote_transport_required",
                        "ownership_required": "yes",
                        "ownership_truth": "transfer_required_before_remote_dispatch",
                        "dispatch_readiness": "contract_required",
                        "dispatch_truth": "planned",
                        "operator_ack_required": True,
                        "next_owner_kind": "remote_executor",
                        "next_owner_ref": "unassigned",
                        "blocking_reason": "blocked",
                        "recommended_next_action": "review",
                        "goal": "Describe remote handoff contract",
                        "constraints": [],
                        "done": ["ready"],
                        "next_steps": "review next",
                        "context_pointers": [],
                    },
                )

    def test_cli_create_persists_explicit_capability_manifest(self) -> None:
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
                        "Capability manifest",
                        "--goal",
                        "Persist explicit capability refs",
                        "--workspace-root",
                        str(tmp_path),
                        "--capability",
                        "profile:baseline_local",
                        "--capability",
                        "workflow:task_loop",
                        "--capability",
                        "validator:run_output_validation",
                    ]
                ),
                0,
            )
            task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
            state = json.loads((tmp_path / ".swl" / "tasks" / task_id / "state.json").read_text(encoding="utf-8"))
            capability_assembly = json.loads(
                (tmp_path / ".swl" / "tasks" / task_id / "capability_assembly.json").read_text(encoding="utf-8")
            )
            events = [
                json.loads(line)
                for line in (tmp_path / ".swl" / "tasks" / task_id / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(state["capability_manifest"]["profile_refs"], ["baseline_local"])
        self.assertEqual(state["capability_manifest"]["workflow_refs"], ["task_loop"])
        self.assertEqual(state["capability_manifest"]["validator_refs"], ["run_output_validation"])
        self.assertEqual(capability_assembly["requested"]["profile_refs"], ["baseline_local"])
        self.assertEqual(capability_assembly["effective"]["workflow_refs"], ["task_loop"])
        self.assertEqual(capability_assembly["assembly_status"], "assembled")
        self.assertEqual(events[0]["payload"]["capability_manifest"]["profile_refs"], ["baseline_local"])
        self.assertEqual(events[0]["payload"]["capability_assembly"]["resolver"], "local_baseline")

    def test_cli_create_persists_task_semantics_handoff_record(self) -> None:
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
                        "Imported planning",
                        "--goal",
                        "Turn external planning into task semantics",
                        "--workspace-root",
                        str(tmp_path),
                        "--planning-source",
                        "chat://planning-session-1",
                        "--constraint",
                        "Preserve current artifact semantics",
                        "--acceptance-criterion",
                        "Persist a task-linked semantics record",
                        "--priority-hint",
                        "Do the smallest first cut",
                        "--next-action-proposal",
                        "Define the imported planning boundary",
                    ]
                ),
                0,
            )
            task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
            task_dir = tmp_path / ".swl" / "tasks" / task_id
            state = json.loads((task_dir / "state.json").read_text(encoding="utf-8"))
            task_semantics = json.loads((task_dir / "task_semantics.json").read_text(encoding="utf-8"))
            semantics_report = (task_dir / "artifacts" / "task_semantics_report.md").read_text(encoding="utf-8")
            events = [
                json.loads(line)
                for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(task_semantics["source_kind"], "external_planning_handoff")
        self.assertEqual(task_semantics["source_ref"], "chat://planning-session-1")
        self.assertEqual(task_semantics["constraints"], ["Preserve current artifact semantics"])
        self.assertEqual(task_semantics["acceptance_criteria"], ["Persist a task-linked semantics record"])
        self.assertEqual(task_semantics["priority_hints"], ["Do the smallest first cut"])
        self.assertEqual(task_semantics["next_action_proposals"], ["Define the imported planning boundary"])
        self.assertEqual(state["task_semantics"]["source_kind"], "external_planning_handoff")
        self.assertTrue(state["artifact_paths"]["task_semantics_json"].endswith("task_semantics.json"))
        self.assertTrue(state["artifact_paths"]["task_semantics_report"].endswith("task_semantics_report.md"))
        self.assertEqual(events[0]["payload"]["task_semantics"]["source_kind"], "external_planning_handoff")
        self.assertIn("Task Semantics Report", semantics_report)
        self.assertIn("chat://planning-session-1", semantics_report)

    def test_cli_planning_handoff_updates_existing_task_semantics(self) -> None:
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
                        "Planning handoff update",
                        "--goal",
                        "Attach imported planning after task creation",
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
                        "chat://phase11-planning",
                        "--constraint",
                        "Keep imported planning explicit",
                        "--next-action-proposal",
                        "Promote the handoff into task semantics",
                    ]
                ),
                0,
            )

            task_dir = tmp_path / ".swl" / "tasks" / task_id
            task_semantics = json.loads((task_dir / "task_semantics.json").read_text(encoding="utf-8"))
            events = [
                json.loads(line)
                for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(task_semantics["source_kind"], "external_planning_handoff")
        self.assertEqual(task_semantics["source_ref"], "chat://phase11-planning")
        self.assertEqual(task_semantics["constraints"], ["Keep imported planning explicit"])
        self.assertEqual(task_semantics["next_action_proposals"], ["Promote the handoff into task semantics"])
        self.assertEqual(events[-1]["event_type"], "task.planning_handoff_added")
        self.assertEqual(events[-1]["payload"]["task_semantics"]["source_ref"], "chat://phase11-planning")

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
        self.assertEqual(decision_records[0]["caller_authority"], "canonical-promotion")
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

    def test_cli_task_staged_defaults_to_pending_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pending = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Pending staged note should appear in the task queue output.",
                    source_task_id="task-stage-queue",
                ),
            )
            promoted = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Promoted staged note should stay hidden by default.",
                    source_task_id="task-stage-queue",
                    status="promoted",
                    decided_at="2026-04-14T00:00:00+00:00",
                    decided_by="swl_cli",
                ),
            )
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "staged"]), 0)

        output = stdout.getvalue()
        self.assertIn("Task Staged Knowledge", output)
        self.assertIn("status_filter: pending", output)
        self.assertIn(pending.candidate_id, output)
        self.assertNotIn(promoted.candidate_id, output)

    def test_cli_task_staged_filters_by_status_and_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            promoted = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Promoted staged note should be shown when explicitly requested.",
                    source_task_id="task-stage-queue-a",
                    status="promoted",
                    decided_at="2026-04-14T00:00:00+00:00",
                    decided_by="swl_cli",
                ),
            )
            submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Different task should be filtered out.",
                    source_task_id="task-stage-queue-b",
                    status="promoted",
                    decided_at="2026-04-14T00:00:00+00:00",
                    decided_by="swl_cli",
                ),
            )
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "task",
                            "staged",
                            "--status",
                            "promoted",
                            "--task",
                            "task-stage-queue-a",
                        ]
                    ),
                    0,
                )

        output = stdout.getvalue()
        self.assertIn("status_filter: promoted", output)
        self.assertIn("task_filter: task-stage-queue-a", output)
        self.assertIn(promoted.candidate_id, output)
        self.assertIn("text: Promoted staged note should be shown when explicitly requested.", output)
        self.assertNotIn("Different task should be filtered out.", output)

    def test_cli_stage_inspect_prints_full_candidate_details(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            candidate = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Candidate knowledge should be visible to operators.",
                    source_task_id="task-stage-inspect",
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
        self.assertIn("taxonomy_role: specialist", output)
        self.assertIn("taxonomy_memory_authority: staged-knowledge", output)
        self.assertIn("Candidate knowledge should be visible to operators.", output)

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

    def test_retrieve_context_includes_canonical_reuse_visible_records(self) -> None:
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
                        "Canonical retrieval",
                        "--goal",
                        "Reuse canonical registry records in retrieval",
                        "--workspace-root",
                        str(tmp_path),
                        "--knowledge-stage",
                        "verified",
                        "--knowledge-source",
                        "chat://canonical-reuse",
                        "--knowledge-item",
                        "Canonical reuse policy should keep source traceability visible.",
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
                        "Promote into canonical registry for reuse policy baseline.",
                    ]
                ),
                0,
            )

            records = retrieve_context(
                workspace_root=tmp_path,
                source_types=["knowledge"],
                request=build_task_retrieval_request(load_state(tmp_path, task_id)),
            )
            reuse_policy = json.loads(canonical_reuse_policy_path(tmp_path).read_text(encoding="utf-8"))

        self.assertEqual(reuse_policy["reuse_visible_count"], 1)
        self.assertTrue(any(item.metadata.get("storage_scope") == "canonical_registry" for item in records))
        self.assertTrue(any(item.metadata.get("canonical_policy") == "reuse_visible" for item in records))

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

    def test_retrieval_reports_surface_canonical_reuse_traceability(self) -> None:
        state = TaskState(
            task_id="trace123",
            title="Trace retrieval",
            goal="Surface canonical reuse traceability",
            workspace_root="/tmp/trace",
            artifact_paths={
                "retrieval_json": "/tmp/trace/.swl/tasks/trace123/retrieval.json",
                "source_grounding": "/tmp/trace/.swl/tasks/trace123/artifacts/source_grounding.md",
                "task_memory": "/tmp/trace/.swl/tasks/trace123/memory.json",
            },
        )
        retrieval_items = [
            RetrievalItem(
                path=".swl/canonical_knowledge/reuse_policy.json",
                source_type=KNOWLEDGE_SOURCE_TYPE,
                score=8,
                preview="Canonical reuse policy should keep source traceability visible.",
                chunk_id="canonical-trace123-knowledge-0001",
                title="Canonical canonical-trace123-knowledge-0001",
                citation=".swl/canonical_knowledge/reuse_policy.json#canonical-trace123-knowledge-0001",
                matched_terms=["canonical", "traceability"],
                score_breakdown={"content_hits": 2},
                metadata={
                    "storage_scope": "canonical_registry",
                    "knowledge_task_relation": "cross_task",
                    "canonical_id": "canonical-trace123-knowledge-0001",
                    "canonical_policy": "reuse_visible",
                    "source_ref": "chat://canonical-reuse",
                    "artifact_ref": ".swl/tasks/demo/artifacts/evidence.md",
                    "adapter_name": "canonical_registry_records",
                    "chunk_kind": "canonical_record",
                },
            )
        ]

        retrieval_report = build_retrieval_report(state, retrieval_items)
        source_grounding = build_source_grounding(retrieval_items)

        self.assertIn("reused_canonical_registry_count: 1", retrieval_report)
        self.assertIn("storage_scope: canonical_registry", retrieval_report)
        self.assertIn("canonical_id: canonical-trace123-knowledge-0001", retrieval_report)
        self.assertIn("canonical_policy: reuse_visible", retrieval_report)
        self.assertIn("source_ref: chat://canonical-reuse", retrieval_report)
        self.assertIn("artifact_ref: .swl/tasks/demo/artifacts/evidence.md", retrieval_report)
        self.assertIn("storage_scope: canonical_registry", source_grounding)
        self.assertIn("canonical_policy: reuse_visible", source_grounding)

    def test_cli_create_marks_retrieval_eligible_knowledge_objects(self) -> None:
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
                        "Reusable knowledge",
                        "--goal",
                        "Declare retrieval-eligible imported knowledge",
                        "--workspace-root",
                        str(tmp_path),
                        "--knowledge-stage",
                        "verified",
                        "--knowledge-source",
                        "chat://reuse-session-1",
                        "--knowledge-retrieval-eligible",
                        "--knowledge-item",
                        "The retrieval layer should keep verified reusable knowledge explicit.",
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

        self.assertEqual(knowledge_objects[0]["retrieval_eligible"], True)
        self.assertEqual(knowledge_objects[0]["knowledge_reuse_scope"], "retrieval_candidate")
        self.assertEqual(knowledge_partition["task_linked_count"], 1)
        self.assertEqual(knowledge_partition["reusable_candidate_count"], 1)
        self.assertEqual(events[0]["payload"]["knowledge_reuse_counts"]["retrieval_candidate"], 1)
        self.assertEqual(events[0]["payload"]["knowledge_partition"]["reusable_candidate_count"], 1)
        self.assertIn("retrieval_candidate: 1", knowledge_report)
        self.assertIn("retrieval_eligible: yes", knowledge_report)
        self.assertIn("knowledge_reuse_scope: retrieval_candidate", knowledge_report)

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

    def test_run_task_capability_override_updates_manifest_and_assembly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Capability override",
                goal="Override capability manifest at run time",
                workspace_root=tmp_path,
            )

            retrieval_items = [RetrievalItem(path="notes.md", source_type="notes", score=1, preview="context")]
            executor_result = ExecutorResult(
                executor_name="mock",
                status="completed",
                message="Execution finished.",
                output="done",
            )

            with patch("swallow.orchestrator.run_retrieval", return_value=retrieval_items):
                with patch("swallow.orchestrator._execute_task_card", return_value=executor_result):
                    with patch(
                        "swallow.orchestrator.write_task_artifacts",
                        return_value=(
                            ValidationResult(status="passed", message="Compatibility passed."),
                            ValidationResult(status="passed", message="Execution fit passed."),
                            ValidationResult(status="passed", message="Knowledge policy passed."),
                            ValidationResult(status="passed", message="Validation passed."),
                            ValidationResult(status="passed", message="Retry policy passed."),
                            ValidationResult(status="passed", message="Execution budget policy passed."),
                            ValidationResult(status="warning", message="Stop policy warning."),
                        ),
                    ):
                        final_state = run_task(
                            tmp_path,
                            state.task_id,
                            capability_refs=["profile:research_local", "validator:strict_validation"],
                        )

            persisted = json.loads((tmp_path / ".swl" / "tasks" / state.task_id / "state.json").read_text(encoding="utf-8"))
            capability_assembly = json.loads(
                (tmp_path / ".swl" / "tasks" / state.task_id / "capability_assembly.json").read_text(encoding="utf-8")
            )
            events = [
                json.loads(line)
                for line in (tmp_path / ".swl" / "tasks" / state.task_id / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(final_state.capability_manifest["profile_refs"], ["research_local"])
        self.assertEqual(final_state.capability_manifest["validator_refs"], ["strict_validation"])
        self.assertEqual(persisted["capability_manifest"]["profile_refs"], ["research_local"])
        self.assertEqual(capability_assembly["effective"]["validator_refs"], ["strict_validation"])
        self.assertEqual(events[1]["event_type"], "task.run_started")
        self.assertEqual(events[1]["payload"]["capability_manifest"]["profile_refs"], ["research_local"])
        self.assertEqual(events[1]["payload"]["capability_assembly"]["assembly_status"], "assembled")

    def test_run_task_locks_grounding_refs_from_canonical_retrieval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Grounding lock",
                goal="Lock canonical retrieval grounding",
                workspace_root=tmp_path,
            )
            retrieval_items = [
                RetrievalItem(
                    path=".swl/canonical_knowledge/reuse_policy.json",
                    source_type=KNOWLEDGE_SOURCE_TYPE,
                    score=8,
                    preview="Canonical grounding entry.",
                    citation=".swl/canonical_knowledge/reuse_policy.json#canonical-grounding-1",
                    metadata={
                        "storage_scope": "canonical_registry",
                        "canonical_id": "canonical-grounding-1",
                        "canonical_key": "task-object:grounding-source:knowledge-1",
                        "knowledge_task_id": "grounding-source",
                        "evidence_status": "source_only",
                    },
                )
            ]
            executor_result = ExecutorResult(
                executor_name="mock",
                status="completed",
                message="Execution finished.",
                output="done",
            )

            def write_artifacts_side_effect(
                base_dir: Path,
                current_state: TaskState,
                current_retrieval_items: list[RetrievalItem],
                current_executor_result: ExecutorResult,
                grounding_evidence_override: dict[str, object] | None = None,
            ) -> tuple[ValidationResult, ...]:
                artifacts_root = base_dir / ".swl" / "tasks" / current_state.task_id / "artifacts"
                artifacts_root.mkdir(parents=True, exist_ok=True)
                (artifacts_root / "grounding_evidence.json").write_text(
                    json.dumps(grounding_evidence_override or {}, indent=2) + "\n",
                    encoding="utf-8",
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

            with patch("swallow.orchestrator.run_retrieval", return_value=retrieval_items):
                with patch("swallow.orchestrator._execute_task_card", return_value=executor_result):
                    with patch("swallow.orchestrator.write_task_artifacts", side_effect=write_artifacts_side_effect):
                        final_state = run_task(tmp_path, state.task_id, executor_name="mock")

            events = [
                json.loads(line)
                for line in (tmp_path / ".swl" / "tasks" / state.task_id / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(final_state.grounding_refs, ["canonical:canonical-grounding-1"])
        self.assertTrue(final_state.grounding_locked)
        grounding_event = next(event for event in events if event["event_type"] == "grounding.locked")
        self.assertEqual(grounding_event["payload"]["grounding_refs"], ["canonical:canonical-grounding-1"])
        self.assertFalse(grounding_event["payload"]["reused_locked_artifact"])

    def test_run_task_reuses_locked_grounding_on_resume_and_resets_on_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Grounding reuse",
                goal="Keep resume stable and rerun fresh",
                workspace_root=tmp_path,
            )
            first_retrieval = [
                RetrievalItem(
                    path=".swl/canonical_knowledge/reuse_policy.json",
                    source_type=KNOWLEDGE_SOURCE_TYPE,
                    score=8,
                    preview="Original grounding entry.",
                    citation=".swl/canonical_knowledge/reuse_policy.json#canonical-grounding-old",
                    metadata={
                        "storage_scope": "canonical_registry",
                        "canonical_id": "canonical-grounding-old",
                        "canonical_key": "task-object:grounding-source:knowledge-old",
                        "knowledge_task_id": "grounding-source",
                        "evidence_status": "source_only",
                    },
                )
            ]
            second_retrieval = [
                RetrievalItem(
                    path=".swl/canonical_knowledge/reuse_policy.json",
                    source_type=KNOWLEDGE_SOURCE_TYPE,
                    score=9,
                    preview="New grounding entry after rerun.",
                    citation=".swl/canonical_knowledge/reuse_policy.json#canonical-grounding-new",
                    metadata={
                        "storage_scope": "canonical_registry",
                        "canonical_id": "canonical-grounding-new",
                        "canonical_key": "task-object:grounding-source:knowledge-new",
                        "knowledge_task_id": "grounding-source",
                        "evidence_status": "source_only",
                    },
                )
            ]
            executor_result = ExecutorResult(
                executor_name="mock",
                status="failed",
                message="Execution failed.",
                output="failed",
                failure_kind="mock_failure",
            )

            def write_artifacts_side_effect(
                base_dir: Path,
                current_state: TaskState,
                current_retrieval_items: list[RetrievalItem],
                current_executor_result: ExecutorResult,
                grounding_evidence_override: dict[str, object] | None = None,
            ) -> tuple[ValidationResult, ...]:
                artifacts_root = base_dir / ".swl" / "tasks" / current_state.task_id / "artifacts"
                artifacts_root.mkdir(parents=True, exist_ok=True)
                (artifacts_root / "grounding_evidence.json").write_text(
                    json.dumps(grounding_evidence_override or {}, indent=2) + "\n",
                    encoding="utf-8",
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

            with patch("swallow.orchestrator.run_retrieval", return_value=first_retrieval):
                with patch("swallow.orchestrator._execute_task_card", return_value=executor_result):
                    with patch("swallow.orchestrator.write_task_artifacts", side_effect=write_artifacts_side_effect):
                        first_state = run_task(tmp_path, state.task_id, executor_name="mock")

            with patch("swallow.orchestrator.run_retrieval", return_value=second_retrieval):
                with patch("swallow.orchestrator._execute_task_card", return_value=executor_result):
                    with patch("swallow.orchestrator.write_task_artifacts", side_effect=write_artifacts_side_effect):
                        resumed_state = run_task(tmp_path, state.task_id, executor_name="mock")

            with patch("swallow.orchestrator.run_retrieval", return_value=second_retrieval):
                with patch("swallow.orchestrator._execute_task_card", return_value=executor_result):
                    with patch("swallow.orchestrator.write_task_artifacts", side_effect=write_artifacts_side_effect):
                        rerun_state = run_task(tmp_path, state.task_id, executor_name="mock", reset_grounding=True)

            events = [
                json.loads(line)
                for line in (tmp_path / ".swl" / "tasks" / state.task_id / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            grounding_events = [event for event in events if event["event_type"] == "grounding.locked"]

        self.assertEqual(first_state.grounding_refs, ["canonical:canonical-grounding-old"])
        self.assertEqual(resumed_state.grounding_refs, ["canonical:canonical-grounding-old"])
        self.assertEqual(rerun_state.grounding_refs, ["canonical:canonical-grounding-new"])
        self.assertTrue(first_state.grounding_locked)
        self.assertTrue(resumed_state.grounding_locked)
        self.assertTrue(rerun_state.grounding_locked)
        self.assertEqual(
            [event["payload"]["reused_locked_artifact"] for event in grounding_events],
            [False, True, False],
        )

    def test_knowledge_policy_fails_for_unbacked_canonical_knowledge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\ncanonical policy\n", encoding="utf-8")

            with patch.dict("os.environ", {"AIWF_EXECUTOR_MODE": "mock"}, clear=False):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "task",
                            "create",
                            "--title",
                            "Canonical knowledge policy",
                            "--goal",
                            "Block unbacked canonical promotion",
                            "--workspace-root",
                            str(tmp_path),
                            "--knowledge-stage",
                            "canonical",
                            "--knowledge-source",
                            "chat://canonical-source",
                            "--knowledge-item",
                            "The route report is the canonical execution record.",
                        ]
                    ),
                    0,
                )
                task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)

                task_dir = tmp_path / ".swl" / "tasks" / task_id
                state = json.loads((task_dir / "state.json").read_text(encoding="utf-8"))
                knowledge_policy = json.loads((task_dir / "knowledge_policy.json").read_text(encoding="utf-8"))
                summary = (task_dir / "artifacts" / "summary.md").read_text(encoding="utf-8")
                resume_note = (task_dir / "artifacts" / "resume_note.md").read_text(encoding="utf-8")
                inspect_stdout = StringIO()
                with redirect_stdout(inspect_stdout):
                    self.assertEqual(main(["--base-dir", str(tmp_path), "task", "inspect", task_id]), 0)

        self.assertEqual(state["status"], "failed")
        self.assertEqual(knowledge_policy["status"], "failed")
        self.assertEqual(knowledge_policy["findings"][0]["code"], "knowledge.canonical.evidence_missing")
        self.assertIn("knowledge_policy_status: failed", summary)
        self.assertIn("knowledge policy status: failed", resume_note)
        self.assertIn("Treat the knowledge policy report as blocking", resume_note)
        self.assertIn("knowledge_policy_status: failed", inspect_stdout.getvalue())

    def test_cli_capabilities_commands_show_requested_and_effective_capability_state(self) -> None:
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
                        "Capability inspect",
                        "--goal",
                        "Inspect capability assembly",
                        "--workspace-root",
                        str(tmp_path),
                        "--capability",
                        "profile:baseline_local",
                        "--capability",
                        "validator:run_output_validation",
                    ]
                ),
                0,
            )
            task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())

            summary_stdout = StringIO()
            json_stdout = StringIO()
            with redirect_stdout(summary_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "capabilities", task_id]), 0)
            with redirect_stdout(json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "capabilities-json", task_id]), 0)

        summary_output = summary_stdout.getvalue()
        self.assertIn(f"Task Capabilities: {task_id}", summary_output)
        self.assertIn("Requested Manifest", summary_output)
        self.assertIn("profile_refs: baseline_local", summary_output)
        self.assertIn("validator_refs: run_output_validation", summary_output)
        self.assertIn("Effective Assembly", summary_output)
        self.assertIn("assembly_status: assembled", summary_output)
        self.assertIn("resolver: local_baseline", summary_output)
        self.assertIn("effective_profiles: baseline_local", summary_output)

        json_output = json_stdout.getvalue()
        self.assertIn('"requested"', json_output)
        self.assertIn('"effective"', json_output)
        self.assertIn('"assembly_status"', json_output)

    def test_create_task_rejects_unknown_capability_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            with self.assertRaises(ValueError) as raised:
                create_task(
                    base_dir=tmp_path,
                    title="Invalid capability",
                    goal="Reject unknown capability refs",
                    workspace_root=tmp_path,
                    capability_refs=["profile:missing_profile"],
                )

        self.assertIn("Unknown profile capability: missing_profile", str(raised.exception))

    def test_run_task_rejects_unknown_capability_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Capability validation",
                goal="Reject invalid run-time capability override",
                workspace_root=tmp_path,
            )

            with self.assertRaises(ValueError) as raised:
                run_task(
                    tmp_path,
                    state.task_id,
                    capability_refs=["validator:missing_validator"],
                )

        self.assertIn("Unknown validator capability: missing_validator", str(raised.exception))

    def test_run_task_blocks_remote_dispatch_when_operator_ack_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Blocked mock dispatch",
                goal="Block remote dispatch until operator review",
                workspace_root=tmp_path,
            )
            remote_route = RouteSelection(
                route=RouteSpec(
                    name="mock-remote",
                    executor_name="mock",
                    backend_kind="mock_remote_test",
                    model_hint="mock-remote",
                    executor_family="cli",
                    execution_site="remote",
                    remote_capable=True,
                    transport_kind="remote_transport_candidate",
                    capabilities=RouteCapabilities(
                        execution_kind="artifact_generation",
                        supports_tool_loop=False,
                        filesystem_access="workspace_read",
                        network_access="none",
                        deterministic=True,
                        resumable=True,
                    ),
                ),
                reason="Selected a mock remote route for dispatch blocking verification.",
                policy_inputs={},
            )

            with patch(
                "swallow.orchestrator.select_route",
                return_value=remote_route,
            ):
                with patch("swallow.orchestrator.run_retrieval") as retrieval_mock:
                    with patch("swallow.orchestrator._execute_task_card") as execution_mock:
                        final_state = run_task(tmp_path, state.task_id, executor_name="mock")

            task_dir = tmp_path / ".swl" / "tasks" / state.task_id
            events = [
                json.loads(line)
                for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            contract = json.loads((task_dir / "remote_handoff_contract.json").read_text(encoding="utf-8"))

        self.assertEqual(final_state.status, "dispatch_blocked")
        self.assertEqual(final_state.phase, "dispatch")
        self.assertEqual(final_state.topology_dispatch_status, "blocked")
        self.assertEqual(final_state.execution_lifecycle, "blocked")
        self.assertEqual(final_state.executor_status, "blocked")
        self.assertEqual(contract["contract_kind"], "remote_handoff_candidate")
        self.assertEqual(events[-1]["event_type"], "task.dispatch_blocked")
        self.assertEqual(events[-1]["payload"]["dispatch_verdict"]["action"], "blocked")
        retrieval_mock.assert_not_called()
        execution_mock.assert_not_called()

    def test_run_task_dispatches_to_mock_remote_executor_and_completes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Mock remote success",
                goal="Validate mock remote dispatch success",
                workspace_root=tmp_path,
            )

            with patch.dict("os.environ", {"AIWF_MOCK_REMOTE_OUTCOME": "completed"}, clear=False):
                final_state = run_task(tmp_path, state.task_id, executor_name="mock-remote")

            task_dir = tmp_path / ".swl" / "tasks" / state.task_id
            contract = json.loads((task_dir / "remote_handoff_contract.json").read_text(encoding="utf-8"))
            dispatch = json.loads((task_dir / "dispatch.json").read_text(encoding="utf-8"))
            events = [
                json.loads(line)
                for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            executor_output = (task_dir / "artifacts" / "executor_output.md").read_text(encoding="utf-8")

        self.assertEqual(final_state.status, "completed")
        self.assertEqual(final_state.executor_name, "mock-remote")
        self.assertEqual(final_state.topology_dispatch_status, "mock_remote_dispatched")
        self.assertEqual(contract["contract_status"], "ready")
        self.assertFalse(contract["operator_ack_required"])
        self.assertEqual(contract["next_owner_ref"], "mock-remote-node")
        self.assertEqual(dispatch["remote_handoff_contract_status"], "ready")
        self.assertEqual(events[-1]["event_type"], "task.completed")
        self.assertIn("Mock Remote Executor Update", executor_output)

    def test_run_task_dispatches_to_mock_remote_executor_and_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Mock remote failure",
                goal="Validate mock remote dispatch failure",
                workspace_root=tmp_path,
            )

            with patch.dict("os.environ", {"AIWF_MOCK_REMOTE_OUTCOME": "failed"}, clear=False):
                final_state = run_task(tmp_path, state.task_id, executor_name="mock-remote")

            task_dir = tmp_path / ".swl" / "tasks" / state.task_id
            events = [
                json.loads(line)
                for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            stderr_output = (task_dir / "artifacts" / "executor_stderr.txt").read_text(encoding="utf-8")

        self.assertEqual(final_state.status, "failed")
        self.assertEqual(final_state.executor_name, "mock-remote")
        self.assertEqual(final_state.topology_dispatch_status, "mock_remote_dispatched")
        self.assertEqual(final_state.executor_status, "failed")
        self.assertEqual(events[-1]["event_type"], "task.failed")
        self.assertIn("Simulated mock remote failure.", stderr_output)

    def test_task_list_prints_header_when_no_tasks_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "list"]), 0)

        self.assertEqual(stdout.getvalue(), "task_id\tstatus\tphase\tattempt\tupdated_at\ttitle\tfocus=all\n")

    def test_task_list_shows_stable_recent_first_summaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            alpha_root = tmp_path / ".swl" / "tasks" / "task-alpha"
            beta_root = tmp_path / ".swl" / "tasks" / "task-beta"
            alpha_root.mkdir(parents=True, exist_ok=True)
            beta_root.mkdir(parents=True, exist_ok=True)

            alpha_state = TaskState(
                task_id="task-alpha",
                title="Alpha task",
                goal="Older task",
                workspace_root=str(tmp_path),
                status="completed",
                phase="summarize",
                updated_at="2026-04-08T09:00:00+00:00",
                current_attempt_id="attempt-0001",
            )
            beta_state = TaskState(
                task_id="task-beta",
                title="Beta task",
                goal="Newer task",
                workspace_root=str(tmp_path),
                status="failed",
                phase="execute",
                updated_at="2026-04-08T10:00:00+00:00",
                current_attempt_id="attempt-0002",
            )
            (alpha_root / "state.json").write_text(json.dumps(alpha_state.to_dict(), indent=2) + "\n", encoding="utf-8")
            (beta_root / "state.json").write_text(json.dumps(beta_state.to_dict(), indent=2) + "\n", encoding="utf-8")

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "list"]), 0)

        lines = stdout.getvalue().splitlines()
        self.assertEqual(lines[0], "task_id\tstatus\tphase\tattempt\tupdated_at\ttitle\tfocus=all")
        self.assertEqual(
            lines[1],
            "task-beta\tfailed\texecute\tattempt-0002\t2026-04-08T10:00:00+00:00\tBeta task",
        )
        self.assertEqual(
            lines[2],
            "task-alpha\tcompleted\tsummarize\tattempt-0001\t2026-04-08T09:00:00+00:00\tAlpha task",
        )

    def test_task_list_failed_focus_only_shows_failed_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            failed_root = tmp_path / ".swl" / "tasks" / "task-failed"
            completed_root = tmp_path / ".swl" / "tasks" / "task-done"
            failed_root.mkdir(parents=True, exist_ok=True)
            completed_root.mkdir(parents=True, exist_ok=True)

            failed_state = TaskState(
                task_id="task-failed",
                title="Failed task",
                goal="Needs attention",
                workspace_root=str(tmp_path),
                status="failed",
                phase="summarize",
                updated_at="2026-04-08T10:00:00+00:00",
                current_attempt_id="attempt-0001",
            )
            completed_state = TaskState(
                task_id="task-done",
                title="Done task",
                goal="No attention needed",
                workspace_root=str(tmp_path),
                status="completed",
                phase="summarize",
                updated_at="2026-04-08T09:00:00+00:00",
                current_attempt_id="attempt-0001",
            )
            (failed_root / "state.json").write_text(json.dumps(failed_state.to_dict(), indent=2) + "\n", encoding="utf-8")
            (completed_root / "state.json").write_text(
                json.dumps(completed_state.to_dict(), indent=2) + "\n", encoding="utf-8"
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "list", "--focus", "failed"]), 0)

        lines = stdout.getvalue().splitlines()
        self.assertEqual(lines[0], "task_id\tstatus\tphase\tattempt\tupdated_at\ttitle\tfocus=failed")
        self.assertEqual(len(lines), 2)
        self.assertIn("task-failed\tfailed", lines[1])

    def test_task_list_needs_review_focus_and_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            entries = [
                (
                    "task-review-1",
                    TaskState(
                        task_id="task-review-1",
                        title="Review one",
                        goal="Summarize pending review",
                        workspace_root=str(tmp_path),
                        status="completed",
                        phase="summarize",
                        updated_at="2026-04-08T11:00:00+00:00",
                        current_attempt_id="attempt-0001",
                    ),
                ),
                (
                    "task-review-2",
                    TaskState(
                        task_id="task-review-2",
                        title="Review two",
                        goal="Executor still running",
                        workspace_root=str(tmp_path),
                        status="running",
                        phase="executing",
                        updated_at="2026-04-08T10:00:00+00:00",
                        current_attempt_id="attempt-0002",
                        executor_status="running",
                    ),
                ),
                (
                    "task-ignore",
                    TaskState(
                        task_id="task-ignore",
                        title="Ignore me",
                        goal="Already done",
                        workspace_root=str(tmp_path),
                        status="completed",
                        phase="done",
                        updated_at="2026-04-08T09:00:00+00:00",
                        current_attempt_id="attempt-0001",
                        executor_status="completed",
                    ),
                ),
            ]
            for task_id, state in entries:
                task_root = tmp_path / ".swl" / "tasks" / task_id
                task_root.mkdir(parents=True, exist_ok=True)
                (task_root / "state.json").write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "task",
                            "list",
                            "--focus",
                            "needs-review",
                            "--limit",
                            "1",
                        ]
                    ),
                    0,
                )

        lines = stdout.getvalue().splitlines()
        self.assertEqual(lines[0], "task_id\tstatus\tphase\tattempt\tupdated_at\ttitle\tfocus=needs-review")
        self.assertEqual(len(lines), 2)
        self.assertIn("task-review-1\tcompleted\tsummarize", lines[1])

    def test_task_queue_surfaces_action_needed_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            entries = [
                (
                    "task-created",
                    TaskState(
                        task_id="task-created",
                        title="Created task",
                        goal="Needs first run",
                        workspace_root=str(tmp_path),
                        status="created",
                        phase="intake",
                        updated_at="2026-04-09T12:00:00+00:00",
                    ),
                    {},
                    {},
                    {},
                ),
                (
                    "task-retry",
                    TaskState(
                        task_id="task-retry",
                        title="Retry task",
                        goal="Can retry",
                        workspace_root=str(tmp_path),
                        status="failed",
                        phase="summarize",
                        updated_at="2026-04-09T11:00:00+00:00",
                        current_attempt_id="attempt-0002",
                    ),
                    {
                        "status": "resume_from_failure",
                        "next_operator_action": "Retry the task with the latest recovery guidance.",
                    },
                    {"retryable": True, "retry_decision": "operator_retry_available"},
                    {
                        "continue_allowed": True,
                        "stop_required": False,
                        "checkpoint_kind": "retry_review",
                    },
                ),
                (
                    "task-review",
                    TaskState(
                        task_id="task-review",
                        title="Review task",
                        goal="Needs review",
                        workspace_root=str(tmp_path),
                        status="completed",
                        phase="summarize",
                        updated_at="2026-04-09T10:00:00+00:00",
                        current_attempt_id="attempt-0001",
                    ),
                    {
                        "status": "review_completed_run",
                        "next_operator_action": "Review summary.md before starting the next task iteration.",
                    },
                    {"retryable": False, "retry_decision": "not_applicable"},
                    {
                        "continue_allowed": False,
                        "stop_required": False,
                        "checkpoint_kind": "completed_run_review",
                    },
                ),
                (
                    "task-running",
                    TaskState(
                        task_id="task-running",
                        title="Running task",
                        goal="Still in progress",
                        workspace_root=str(tmp_path),
                        status="running",
                        phase="executing",
                        updated_at="2026-04-09T09:00:00+00:00",
                        current_attempt_id="attempt-0003",
                        executor_status="running",
                        execution_lifecycle="executing",
                    ),
                    {},
                    {},
                    {},
                ),
                (
                    "task-done",
                    TaskState(
                        task_id="task-done",
                        title="Done task",
                        goal="No current action",
                        workspace_root=str(tmp_path),
                        status="completed",
                        phase="done",
                        updated_at="2026-04-09T08:00:00+00:00",
                        current_attempt_id="attempt-0001",
                        executor_status="completed",
                    ),
                    {},
                    {},
                    {},
                ),
            ]
            for task_id, state, handoff, retry_policy, stop_policy in entries:
                task_root = tmp_path / ".swl" / "tasks" / task_id
                task_root.mkdir(parents=True, exist_ok=True)
                (task_root / "state.json").write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")
                if handoff:
                    (task_root / "handoff.json").write_text(json.dumps(handoff, indent=2) + "\n", encoding="utf-8")
                if retry_policy:
                    (task_root / "retry_policy.json").write_text(
                        json.dumps(retry_policy, indent=2) + "\n", encoding="utf-8"
                    )
                if stop_policy:
                    (task_root / "stop_policy.json").write_text(
                        json.dumps(stop_policy, indent=2) + "\n", encoding="utf-8"
                    )

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "queue", "--limit", "4"]), 0)

        lines = stdout.getvalue().splitlines()
        self.assertEqual(lines[0], "task_id\taction\tstatus\tattempt\tupdated_at\treason\tregression\tknowledge\tnext\ttitle")
        self.assertEqual(len(lines), 5)
        self.assertIn("task-created\trun\tcreated\t-\t2026-04-09T12:00:00+00:00\ttask_created\tmatch\t-", lines[1])
        self.assertIn("task-retry\tretry\tfailed\tattempt-0002\t2026-04-09T11:00:00+00:00\tretry_review\tmatch\t-", lines[2])
        self.assertIn(
            "task-review\treview\tcompleted\tattempt-0001\t2026-04-09T10:00:00+00:00\tcompleted_run_review\tmatch\t-",
            lines[3],
        )
        self.assertIn("task-running\tmonitor\trunning\tattempt-0003\t2026-04-09T09:00:00+00:00\texecuting\tmatch\t-", lines[4])
        self.assertNotIn("task-done", stdout.getvalue())

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

    def test_task_control_prints_compact_control_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_id = "task-control"
            state = TaskState(
                task_id=task_id,
                title="Control task",
                goal="Summarize control readiness",
                workspace_root=str(tmp_path),
                status="failed",
                phase="summarize",
                updated_at="2026-04-09T12:00:00+00:00",
                current_attempt_id="attempt-0002",
                artifact_paths={
                    "resume_note": ".swl/tasks/task-control/artifacts/resume_note.md",
                    "handoff_report": ".swl/tasks/task-control/artifacts/handoff_report.md",
                    "retry_policy_report": ".swl/tasks/task-control/artifacts/retry_policy_report.md",
                    "execution_budget_policy_report": ".swl/tasks/task-control/artifacts/execution_budget_policy_report.md",
                    "stop_policy_report": ".swl/tasks/task-control/artifacts/stop_policy_report.md",
                    "checkpoint_snapshot_report": ".swl/tasks/task-control/artifacts/checkpoint_snapshot_report.md",
                },
            )
            task_root = tmp_path / ".swl" / "tasks" / task_id
            task_root.mkdir(parents=True, exist_ok=True)
            (task_root / "state.json").write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")
            (task_root / "handoff.json").write_text(
                json.dumps(
                    {
                        "status": "resume_from_failure",
                        "next_operator_action": "Retry the task with the latest recovery guidance.",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (task_root / "retry_policy.json").write_text(
                json.dumps(
                    {
                        "status": "warning",
                        "retryable": True,
                        "retry_decision": "operator_retry_available",
                        "remaining_attempts": 1,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (task_root / "execution_budget_policy.json").write_text(
                json.dumps(
                    {
                        "status": "passed",
                        "timeout_seconds": 20,
                        "budget_state": "available",
                        "timeout_state": "default",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (task_root / "stop_policy.json").write_text(
                json.dumps(
                    {
                        "status": "warning",
                        "stop_required": False,
                        "continue_allowed": True,
                        "stop_decision": "checkpoint_before_retry",
                        "checkpoint_kind": "retry_review",
                        "escalation_level": "operator_retry_review",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (task_root / "checkpoint_snapshot.json").write_text(
                json.dumps(
                    {
                        "status": "warning",
                        "checkpoint_state": "retry_ready",
                        "recommended_path": "retry",
                        "recommended_reason": "retry_review",
                        "resume_ready": False,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "control", task_id]), 0)

        output = stdout.getvalue()
        self.assertIn(f"Task Control: {task_id}", output)
        self.assertIn("recommended_action: retry", output)
        self.assertIn("recommended_reason: retry_review", output)
        self.assertIn("checkpoint_state: retry_ready", output)
        self.assertIn("resume_ready: no", output)
        self.assertIn("next_operator_action: Retry the task with the latest recovery guidance.", output)
        self.assertIn("retry_ready: yes", output)
        self.assertIn("review_ready: no", output)
        self.assertIn("rerun_ready: yes", output)
        self.assertIn("monitor_needed: no", output)
        self.assertIn("Knowledge Control", output)
        self.assertIn("knowledge_review_needed: no", output)
        self.assertIn("knowledge_review_summary: -", output)
        self.assertIn("knowledge_review_command: swl task knowledge-review-queue task-control", output)
        self.assertIn("Regression Control", output)
        self.assertIn("canonical_reuse_regression_status: match", output)
        self.assertIn("canonical_reuse_regression_mismatch_count: 0", output)
        self.assertIn("canonical_reuse_regression_command: swl task canonical-reuse-regression task-control", output)
        self.assertIn("Control Boundaries", output)
        self.assertIn("resume_path: blocked reason=retry_ready suggested_path=retry", output)
        self.assertIn("retry_path: allowed reason=operator_retry_available", output)
        self.assertIn("rerun_path: allowed reason=explicit_operator_override suggested_path=retry", output)
        self.assertIn("Policy Controls", output)
        self.assertIn("retry_policy_status: warning", output)
        self.assertIn("execution_budget_policy_status: passed", output)
        self.assertIn("stop_policy_status: warning", output)
        self.assertIn(f"review: swl task review {task_id}", output)
        self.assertIn(f"knowledge_review: swl task knowledge-review-queue {task_id}", output)
        self.assertIn(f"policy: swl task policy {task_id}", output)
        self.assertIn(f"checkpoint: swl task checkpoint {task_id}", output)
        self.assertIn(f"inspect: swl task inspect {task_id}", output)
        self.assertIn(f"run: swl task run {task_id}", output)
        self.assertIn("resume_note: .swl/tasks/task-control/artifacts/resume_note.md", output)
        self.assertIn("checkpoint_snapshot_report: .swl/tasks/task-control/artifacts/checkpoint_snapshot_report.md", output)

    def test_task_queue_surfaces_regression_mismatch_attention(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_id = "task-regression-queue"
            task_root = tmp_path / ".swl" / "tasks" / task_id
            task_root.mkdir(parents=True, exist_ok=True)
            state = TaskState(
                task_id=task_id,
                title="Regression queue",
                goal="Surface regression mismatch in the queue",
                workspace_root=str(tmp_path),
                status="completed",
                phase="done",
                updated_at="2026-04-09T12:30:00+00:00",
                current_attempt_id="attempt-0001",
                executor_status="completed",
            )
            (task_root / "state.json").write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")
            (task_root / "canonical_reuse_regression.json").write_text(
                json.dumps(
                    {
                        "baseline_generated_at": "2026-04-09T12:00:00+00:00",
                        "task_id": task_id,
                        "evaluation_count": 0,
                        "judgment_counts": {"useful": 0, "noisy": 0, "needs_review": 0},
                        "resolved_citation_count": 0,
                        "unresolved_citation_count": 0,
                        "retrieval_match_count": 0,
                        "latest_judgment": "",
                        "latest_task_id": task_id,
                        "latest_citations": [],
                        "latest_retrieval_context_ref": "",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (task_root / "canonical_reuse_eval.jsonl").write_text(
                json.dumps(
                    {
                        "task_id": task_id,
                        "evaluated_at": "2026-04-09T12:10:00+00:00",
                        "evaluated_by": "swl_cli",
                        "judgment": "useful",
                        "citations": [".swl/canonical_knowledge/reuse_policy.json#canonical-demo"],
                        "citation_count": 1,
                        "resolved_citations": [],
                        "resolved_citation_count": 0,
                        "unresolved_citations": [],
                        "unresolved_citation_count": 0,
                        "retrieval_context_ref": "",
                        "retrieval_context_available": False,
                        "retrieval_context_count": 0,
                        "retrieval_matches": [],
                        "retrieval_match_count": 0,
                        "note": "",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "queue"]), 0)

        output = stdout.getvalue()
        self.assertIn("task-regression-queue\tinspect\tcompleted\tattempt-0001", output)
        self.assertIn("canonical_reuse_regression_mismatch\tmismatch:4", output)
        self.assertIn("swl task canonical-reuse-regression task-regression-queue", output)

    def test_task_control_surfaces_regression_mismatch_attention(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_id = "task-regression-control"
            task_root = tmp_path / ".swl" / "tasks" / task_id
            task_root.mkdir(parents=True, exist_ok=True)
            state = TaskState(
                task_id=task_id,
                title="Regression control",
                goal="Surface regression mismatch in control",
                workspace_root=str(tmp_path),
                status="completed",
                phase="summarize",
                updated_at="2026-04-09T12:10:00+00:00",
                current_attempt_id="attempt-0001",
            )
            (task_root / "state.json").write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")
            (task_root / "handoff.json").write_text(
                json.dumps({"status": "review_completed_run", "next_operator_action": "Review run output."}, indent=2) + "\n",
                encoding="utf-8",
            )
            (task_root / "retry_policy.json").write_text(
                json.dumps({"status": "passed", "retryable": False, "retry_decision": "no_retry"}, indent=2) + "\n",
                encoding="utf-8",
            )
            (task_root / "execution_budget_policy.json").write_text(
                json.dumps({"status": "passed", "timeout_seconds": 20, "budget_state": "available", "timeout_state": "default"}, indent=2) + "\n",
                encoding="utf-8",
            )
            (task_root / "stop_policy.json").write_text(
                json.dumps({"status": "passed", "stop_required": False, "continue_allowed": False, "stop_decision": "review", "checkpoint_kind": "review_completed_run", "escalation_level": "operator_review"}, indent=2) + "\n",
                encoding="utf-8",
            )
            (task_root / "checkpoint_snapshot.json").write_text(
                json.dumps({"status": "passed", "checkpoint_state": "review_ready", "recommended_path": "review", "recommended_reason": "completed_run_review", "resume_ready": False}, indent=2) + "\n",
                encoding="utf-8",
            )
            (task_root / "canonical_reuse_regression.json").write_text(
                json.dumps(
                    {
                        "baseline_generated_at": "2026-04-09T12:00:00+00:00",
                        "task_id": task_id,
                        "evaluation_count": 0,
                        "judgment_counts": {"useful": 0, "noisy": 0, "needs_review": 0},
                        "resolved_citation_count": 0,
                        "unresolved_citation_count": 0,
                        "retrieval_match_count": 0,
                        "latest_judgment": "",
                        "latest_task_id": task_id,
                        "latest_citations": [],
                        "latest_retrieval_context_ref": "",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (task_root / "canonical_reuse_eval.jsonl").write_text(
                json.dumps(
                    {
                        "task_id": task_id,
                        "evaluated_at": "2026-04-09T12:10:00+00:00",
                        "evaluated_by": "swl_cli",
                        "judgment": "useful",
                        "citations": [".swl/canonical_knowledge/reuse_policy.json#canonical-demo"],
                        "citation_count": 1,
                        "resolved_citations": [],
                        "resolved_citation_count": 0,
                        "unresolved_citations": [],
                        "unresolved_citation_count": 0,
                        "retrieval_context_ref": "",
                        "retrieval_context_available": False,
                        "retrieval_context_count": 0,
                        "retrieval_matches": [],
                        "retrieval_match_count": 0,
                        "note": "",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "control", task_id]), 0)

        output = stdout.getvalue()
        self.assertIn("recommended_action: review", output)
        self.assertIn("recommended_reason: completed_run_review", output)
        self.assertIn("Regression Control", output)
        self.assertIn("canonical_reuse_regression_status: mismatch", output)
        self.assertIn("canonical_reuse_regression_mismatch_count: 4", output)
        self.assertIn("canonical_reuse_regression_reason: canonical_reuse_regression_mismatch", output)
        self.assertIn("canonical_reuse_regression_command: swl task canonical-reuse-regression task-regression-control", output)

    def test_task_control_surfaces_remote_handoff_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_id = "task-remote-control"
            task_root = tmp_path / ".swl" / "tasks" / task_id
            task_root.mkdir(parents=True, exist_ok=True)
            state = TaskState(
                task_id=task_id,
                title="Remote control",
                goal="Surface remote handoff readiness in control",
                workspace_root=str(tmp_path),
                status="created",
                phase="intake",
                updated_at="2026-04-10T10:00:00+00:00",
                current_attempt_id="attempt-0001",
                artifact_paths={
                    "remote_handoff_contract_report": ".swl/tasks/task-remote-control/artifacts/remote_handoff_contract_report.md",
                },
            )
            (task_root / "state.json").write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")
            (task_root / "handoff.json").write_text(
                json.dumps({"status": "pending", "next_operator_action": "Inspect task artifacts."}, indent=2) + "\n",
                encoding="utf-8",
            )
            (task_root / "retry_policy.json").write_text(
                json.dumps({"status": "passed", "retryable": False, "retry_decision": "no_retry"}, indent=2) + "\n",
                encoding="utf-8",
            )
            (task_root / "execution_budget_policy.json").write_text(
                json.dumps({"status": "passed", "timeout_seconds": 20, "budget_state": "available", "timeout_state": "default"}, indent=2) + "\n",
                encoding="utf-8",
            )
            (task_root / "stop_policy.json").write_text(
                json.dumps({"status": "passed", "stop_required": False, "continue_allowed": False, "stop_decision": "wait", "checkpoint_kind": "none", "escalation_level": "none"}, indent=2) + "\n",
                encoding="utf-8",
            )
            (task_root / "checkpoint_snapshot.json").write_text(
                json.dumps({"status": "passed", "checkpoint_state": "planned", "recommended_path": "review", "recommended_reason": "remote_handoff_contract_required", "resume_ready": False}, indent=2) + "\n",
                encoding="utf-8",
            )
            (task_root / "remote_handoff_contract.json").write_text(
                json.dumps(
                    {
                        "contract_kind": "remote_handoff_candidate",
                        "contract_status": "planned",
                        "handoff_boundary": "cross_site_candidate",
                        "dispatch_readiness": "contract_required",
                        "operator_ack_required": True,
                        "recommended_next_action": "Review the remote handoff contract before treating this task as ready for remote dispatch.",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "control", task_id]), 0)

        output = stdout.getvalue()
        self.assertIn("Remote Handoff Control", output)
        self.assertIn("remote_handoff_needed: yes", output)
        self.assertIn("remote_handoff_summary: planned:cross_site_candidate:contract_required", output)
        self.assertIn("remote_handoff_contract_kind: remote_handoff_candidate", output)
        self.assertIn("remote_handoff_dispatch_readiness: contract_required", output)
        self.assertIn("remote_handoff_operator_ack_required: yes", output)
        self.assertIn("remote_handoff_command: swl task remote-handoff task-remote-control", output)
        self.assertIn("remote_handoff: swl task remote-handoff task-remote-control", output)

    def test_task_inspect_surfaces_regression_mismatch_attention(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_id = "task-regression-inspect"
            task_root = tmp_path / ".swl" / "tasks" / task_id
            artifacts_root = task_root / "artifacts"
            artifacts_root.mkdir(parents=True, exist_ok=True)
            state = TaskState(
                task_id=task_id,
                title="Regression inspect",
                goal="Surface regression mismatch in inspect",
                workspace_root=str(tmp_path),
                status="completed",
                phase="summarize",
                updated_at="2026-04-09T12:10:00+00:00",
                current_attempt_id="attempt-0001",
            )
            (task_root / "state.json").write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")
            (task_root / "handoff.json").write_text(
                json.dumps({"status": "review_completed_run", "next_operator_action": "Inspect task artifacts."}, indent=2) + "\n",
                encoding="utf-8",
            )
            (task_root / "canonical_reuse_regression.json").write_text(
                json.dumps(
                    {
                        "baseline_generated_at": "2026-04-09T12:00:00+00:00",
                        "task_id": task_id,
                        "evaluation_count": 0,
                        "judgment_counts": {"useful": 0, "noisy": 0, "needs_review": 0},
                        "resolved_citation_count": 0,
                        "unresolved_citation_count": 0,
                        "retrieval_match_count": 0,
                        "latest_judgment": "",
                        "latest_task_id": task_id,
                        "latest_citations": [],
                        "latest_retrieval_context_ref": "",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (task_root / "canonical_reuse_eval.jsonl").write_text(
                json.dumps(
                    {
                        "task_id": task_id,
                        "evaluated_at": "2026-04-09T12:10:00+00:00",
                        "evaluated_by": "swl_cli",
                        "judgment": "useful",
                        "citations": [".swl/canonical_knowledge/reuse_policy.json#canonical-demo"],
                        "citation_count": 1,
                        "resolved_citations": [],
                        "resolved_citation_count": 0,
                        "unresolved_citations": [],
                        "unresolved_citation_count": 0,
                        "retrieval_context_ref": "",
                        "retrieval_context_available": False,
                        "retrieval_context_count": 0,
                        "retrieval_matches": [],
                        "retrieval_match_count": 0,
                        "note": "",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "inspect", task_id]), 0)

        output = stdout.getvalue()
        self.assertIn("canonical_reuse_regression_status: mismatch", output)
        self.assertIn("canonical_reuse_regression_mismatch_count: 4", output)
        self.assertIn("canonical_reuse_regression_command: swl task canonical-reuse-regression task-regression-inspect", output)

    def test_task_inspect_surfaces_remote_handoff_attention(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_id = "task-remote-inspect"
            task_root = tmp_path / ".swl" / "tasks" / task_id
            artifacts_root = task_root / "artifacts"
            artifacts_root.mkdir(parents=True, exist_ok=True)
            state = TaskState(
                task_id=task_id,
                title="Remote inspect",
                goal="Surface remote handoff attention in inspect",
                workspace_root=str(tmp_path),
                status="created",
                phase="intake",
                updated_at="2026-04-10T10:05:00+00:00",
                current_attempt_id="attempt-0001",
                artifact_paths={
                    "remote_handoff_contract_report": ".swl/tasks/task-remote-inspect/artifacts/remote_handoff_contract_report.md",
                },
            )
            (task_root / "state.json").write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")
            (task_root / "handoff.json").write_text(
                json.dumps({"status": "pending", "next_operator_action": "Inspect task artifacts."}, indent=2) + "\n",
                encoding="utf-8",
            )
            (task_root / "remote_handoff_contract.json").write_text(
                json.dumps(
                    {
                        "contract_kind": "remote_handoff_candidate",
                        "contract_status": "planned",
                        "handoff_boundary": "cross_site_candidate",
                        "dispatch_readiness": "contract_required",
                        "operator_ack_required": True,
                        "recommended_next_action": "Review the remote handoff contract before treating this task as ready for remote dispatch.",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "inspect", task_id]), 0)

        output = stdout.getvalue()
        self.assertIn("remote_handoff_needed: yes", output)
        self.assertIn("remote_handoff_summary: planned:cross_site_candidate:contract_required", output)
        self.assertIn("remote_handoff_contract_kind: remote_handoff_candidate", output)
        self.assertIn("remote_handoff_contract_status: planned", output)
        self.assertIn("remote_handoff_boundary: cross_site_candidate", output)
        self.assertIn("remote_handoff_dispatch_readiness: contract_required", output)
        self.assertIn("remote_handoff_operator_ack_required: yes", output)
        self.assertIn("remote_handoff_command: swl task remote-handoff task-remote-inspect", output)
        self.assertIn("remote_handoff_contract_report: .swl/tasks/task-remote-inspect/artifacts/remote_handoff_contract_report.md", output)

    def test_task_review_surfaces_regression_mismatch_attention(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_id = "task-regression-review"
            task_root = tmp_path / ".swl" / "tasks" / task_id
            task_root.mkdir(parents=True, exist_ok=True)
            state = TaskState(
                task_id=task_id,
                title="Regression review",
                goal="Surface regression mismatch in review",
                workspace_root=str(tmp_path),
                status="completed",
                phase="summarize",
                updated_at="2026-04-09T12:10:00+00:00",
                current_attempt_id="attempt-0001",
            )
            (task_root / "state.json").write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")
            (task_root / "handoff.json").write_text(
                json.dumps({"status": "review_completed_run", "next_operator_action": "Review run output."}, indent=2) + "\n",
                encoding="utf-8",
            )
            (task_root / "checkpoint_snapshot.json").write_text(
                json.dumps({"checkpoint_state": "review_ready", "recommended_path": "review", "recommended_reason": "completed_run_review", "resume_ready": False}, indent=2) + "\n",
                encoding="utf-8",
            )
            (task_root / "canonical_reuse_regression.json").write_text(
                json.dumps(
                    {
                        "baseline_generated_at": "2026-04-09T12:00:00+00:00",
                        "task_id": task_id,
                        "evaluation_count": 0,
                        "judgment_counts": {"useful": 0, "noisy": 0, "needs_review": 0},
                        "resolved_citation_count": 0,
                        "unresolved_citation_count": 0,
                        "retrieval_match_count": 0,
                        "latest_judgment": "",
                        "latest_task_id": task_id,
                        "latest_citations": [],
                        "latest_retrieval_context_ref": "",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (task_root / "canonical_reuse_eval.jsonl").write_text(
                json.dumps(
                    {
                        "task_id": task_id,
                        "evaluated_at": "2026-04-09T12:10:00+00:00",
                        "evaluated_by": "swl_cli",
                        "judgment": "useful",
                        "citations": [".swl/canonical_knowledge/reuse_policy.json#canonical-demo"],
                        "citation_count": 1,
                        "resolved_citations": [],
                        "resolved_citation_count": 0,
                        "unresolved_citations": [],
                        "unresolved_citation_count": 0,
                        "retrieval_context_ref": "",
                        "retrieval_context_available": False,
                        "retrieval_context_count": 0,
                        "retrieval_matches": [],
                        "retrieval_match_count": 0,
                        "note": "",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "review", task_id]), 0)

        output = stdout.getvalue()
        self.assertIn("canonical_reuse_regression_status: mismatch", output)
        self.assertIn("canonical_reuse_regression_mismatch_count: 4", output)
        self.assertIn("canonical_reuse_regression_command: swl task canonical-reuse-regression task-regression-review", output)

    def test_task_review_surfaces_remote_handoff_attention(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_id = "task-remote-review"
            task_root = tmp_path / ".swl" / "tasks" / task_id
            task_root.mkdir(parents=True, exist_ok=True)
            state = TaskState(
                task_id=task_id,
                title="Remote review",
                goal="Surface remote handoff attention in review",
                workspace_root=str(tmp_path),
                status="created",
                phase="intake",
                updated_at="2026-04-10T10:10:00+00:00",
                current_attempt_id="attempt-0001",
                artifact_paths={
                    "remote_handoff_contract_report": ".swl/tasks/task-remote-review/artifacts/remote_handoff_contract_report.md",
                },
            )
            (task_root / "state.json").write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")
            (task_root / "handoff.json").write_text(
                json.dumps({"status": "pending", "next_operator_action": "Review resume_note.md and summary.md."}, indent=2) + "\n",
                encoding="utf-8",
            )
            (task_root / "checkpoint_snapshot.json").write_text(
                json.dumps({"checkpoint_state": "planned", "recommended_path": "review", "recommended_reason": "remote_handoff_contract_required", "resume_ready": False}, indent=2) + "\n",
                encoding="utf-8",
            )
            (task_root / "remote_handoff_contract.json").write_text(
                json.dumps(
                    {
                        "contract_kind": "remote_handoff_candidate",
                        "contract_status": "planned",
                        "handoff_boundary": "cross_site_candidate",
                        "dispatch_readiness": "contract_required",
                        "operator_ack_required": True,
                        "recommended_next_action": "Review the remote handoff contract before treating this task as ready for remote dispatch.",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "review", task_id]), 0)

        output = stdout.getvalue()
        self.assertIn("remote_handoff_needed: yes", output)
        self.assertIn("remote_handoff_summary: planned:cross_site_candidate:contract_required", output)
        self.assertIn("remote_handoff_contract_kind: remote_handoff_candidate", output)
        self.assertIn("remote_handoff_contract_status: planned", output)
        self.assertIn("remote_handoff_boundary: cross_site_candidate", output)
        self.assertIn("remote_handoff_dispatch_readiness: contract_required", output)
        self.assertIn("remote_handoff_operator_ack_required: yes", output)
        self.assertIn("remote_handoff_command: swl task remote-handoff task-remote-review", output)
        self.assertIn("remote_handoff_contract_report: .swl/tasks/task-remote-review/artifacts/remote_handoff_contract_report.md", output)

    def test_task_checkpoint_prints_checkpoint_snapshot_report_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\ncheckpoint snapshot\n", encoding="utf-8")

            with patch.dict("os.environ", {"AIWF_EXECUTOR_MODE": "mock"}, clear=False):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "task",
                            "create",
                            "--title",
                            "Checkpoint task",
                            "--goal",
                            "Persist a checkpoint snapshot",
                            "--workspace-root",
                            str(tmp_path),
                        ]
                    ),
                    0,
                )
                task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)

                checkpoint_stdout = StringIO()
                checkpoint_json_stdout = StringIO()
                with redirect_stdout(checkpoint_stdout):
                    self.assertEqual(main(["--base-dir", str(tmp_path), "task", "checkpoint", task_id]), 0)
                with redirect_stdout(checkpoint_json_stdout):
                    self.assertEqual(main(["--base-dir", str(tmp_path), "task", "checkpoint-json", task_id]), 0)

        self.assertIn("Checkpoint Snapshot Report", checkpoint_stdout.getvalue())
        self.assertIn("recovery_semantics: completed_run_review", checkpoint_stdout.getvalue())
        self.assertIn("interruption_kind: none", checkpoint_stdout.getvalue())
        self.assertIn("recommended_path: review", checkpoint_stdout.getvalue())
        self.assertIn('"checkpoint_state": "review_ready"', checkpoint_json_stdout.getvalue())
        self.assertIn('"recovery_semantics": "completed_run_review"', checkpoint_json_stdout.getvalue())

    def test_task_attempts_prints_compact_attempt_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_id = "task-attempts"
            task_root = tmp_path / ".swl" / "tasks" / task_id
            task_root.mkdir(parents=True, exist_ok=True)
            state = TaskState(
                task_id=task_id,
                title="Attempt history",
                goal="Inspect repeated attempts",
                workspace_root=str(tmp_path),
                status="completed",
                phase="summarize",
                updated_at="2026-04-09T12:10:00+00:00",
                current_attempt_id="attempt-0002",
                current_attempt_number=2,
            )
            (task_root / "state.json").write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")
            events = [
                {
                    "task_id": task_id,
                    "event_type": "task.run_started",
                    "created_at": "2026-04-09T12:00:00+00:00",
                    "payload": {
                        "attempt_id": "attempt-0001",
                        "attempt_number": 1,
                        "executor_status": "running",
                        "execution_lifecycle": "prepared",
                    },
                },
                {
                    "task_id": task_id,
                    "event_type": "task.failed",
                    "created_at": "2026-04-09T12:01:00+00:00",
                    "payload": {
                        "attempt_id": "attempt-0001",
                        "attempt_number": 1,
                        "status": "failed",
                        "executor_status": "failed",
                        "execution_lifecycle": "failed",
                        "retrieval_count": 1,
                        "compatibility_status": "passed",
                        "execution_fit_status": "passed",
                        "retry_policy_status": "warning",
                        "stop_policy_status": "warning",
                    },
                },
                {
                    "task_id": task_id,
                    "event_type": "task.run_started",
                    "created_at": "2026-04-09T12:05:00+00:00",
                    "payload": {
                        "attempt_id": "attempt-0002",
                        "attempt_number": 2,
                        "executor_status": "running",
                        "execution_lifecycle": "prepared",
                    },
                },
                {
                    "task_id": task_id,
                    "event_type": "task.completed",
                    "created_at": "2026-04-09T12:06:00+00:00",
                    "payload": {
                        "attempt_id": "attempt-0002",
                        "attempt_number": 2,
                        "status": "completed",
                        "executor_status": "completed",
                        "execution_lifecycle": "completed",
                        "retrieval_count": 2,
                        "compatibility_status": "passed",
                        "execution_fit_status": "passed",
                        "retry_policy_status": "passed",
                        "stop_policy_status": "warning",
                    },
                },
            ]
            (task_root / "events.jsonl").write_text(
                "\n".join(json.dumps(item) for item in events) + "\n",
                encoding="utf-8",
            )
            (task_root / "handoff.json").write_text(
                json.dumps({"attempt_id": "attempt-0002", "status": "review_completed_run"}, indent=2) + "\n",
                encoding="utf-8",
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "attempts", task_id]), 0)

        lines = stdout.getvalue().splitlines()
        self.assertEqual(
            lines[0],
            "attempt_id\tattempt_number\tstatus\texecutor_status\texecution_lifecycle\tretrieval_count\thandoff_status\tstarted_at\tfinished_at",
        )
        self.assertIn(
            "attempt-0002\t2\tcompleted\tcompleted\tcompleted\t2\treview_completed_run\t2026-04-09T12:05:00+00:00\t2026-04-09T12:06:00+00:00",
            lines[1],
        )
        self.assertIn(
            "attempt-0001\t1\tfailed\tfailed\tfailed\t1\tpending\t2026-04-09T12:00:00+00:00\t2026-04-09T12:01:00+00:00",
            lines[2],
        )

    def test_task_compare_attempts_prints_compact_diff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_id = "task-compare"
            task_root = tmp_path / ".swl" / "tasks" / task_id
            task_root.mkdir(parents=True, exist_ok=True)
            state = TaskState(
                task_id=task_id,
                title="Attempt compare",
                goal="Compare two attempts",
                workspace_root=str(tmp_path),
                status="completed",
                phase="summarize",
                updated_at="2026-04-09T12:10:00+00:00",
                current_attempt_id="attempt-0002",
                current_attempt_number=2,
            )
            (task_root / "state.json").write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")
            events = [
                {
                    "task_id": task_id,
                    "event_type": "task.run_started",
                    "created_at": "2026-04-09T12:00:00+00:00",
                    "payload": {"attempt_id": "attempt-0001", "attempt_number": 1},
                },
                {
                    "task_id": task_id,
                    "event_type": "task.failed",
                    "created_at": "2026-04-09T12:01:00+00:00",
                    "payload": {
                        "attempt_id": "attempt-0001",
                        "attempt_number": 1,
                        "status": "failed",
                        "executor_status": "failed",
                        "execution_lifecycle": "failed",
                        "retrieval_count": 1,
                        "compatibility_status": "passed",
                        "execution_fit_status": "passed",
                        "retry_policy_status": "warning",
                        "stop_policy_status": "warning",
                    },
                },
                {
                    "task_id": task_id,
                    "event_type": "task.run_started",
                    "created_at": "2026-04-09T12:05:00+00:00",
                    "payload": {"attempt_id": "attempt-0002", "attempt_number": 2},
                },
                {
                    "task_id": task_id,
                    "event_type": "task.completed",
                    "created_at": "2026-04-09T12:06:00+00:00",
                    "payload": {
                        "attempt_id": "attempt-0002",
                        "attempt_number": 2,
                        "status": "completed",
                        "executor_status": "completed",
                        "execution_lifecycle": "completed",
                        "retrieval_count": 2,
                        "compatibility_status": "passed",
                        "execution_fit_status": "passed",
                        "retry_policy_status": "passed",
                        "stop_policy_status": "warning",
                    },
                },
            ]
            (task_root / "events.jsonl").write_text(
                "\n".join(json.dumps(item) for item in events) + "\n",
                encoding="utf-8",
            )
            (task_root / "handoff.json").write_text(
                json.dumps({"attempt_id": "attempt-0002", "status": "review_completed_run"}, indent=2) + "\n",
                encoding="utf-8",
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "compare-attempts", task_id]), 0)

        output = stdout.getvalue()
        self.assertIn(f"Task Attempt Compare: {task_id}", output)
        self.assertIn("left_attempt: attempt-0001", output)
        self.assertIn("right_attempt: attempt-0002", output)
        self.assertIn("status: failed -> completed", output)
        self.assertIn("executor_status: failed -> completed", output)
        self.assertIn("retrieval_count: 1 -> 2", output)
        self.assertIn("handoff_status: pending -> review_completed_run", output)
        self.assertIn("retry_policy_status: warning -> passed", output)

    def test_task_retry_runs_when_retry_policy_allows_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_id = "task-retry-run"
            task_root = tmp_path / ".swl" / "tasks" / task_id
            task_root.mkdir(parents=True, exist_ok=True)
            state = TaskState(
                task_id=task_id,
                title="Retry allowed",
                goal="Retry through the run path",
                workspace_root=str(tmp_path),
                status="failed",
                phase="summarize",
                updated_at="2026-04-09T12:10:00+00:00",
            )
            (task_root / "state.json").write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")
            (task_root / "retry_policy.json").write_text(
                json.dumps({"retryable": True, "retry_decision": "operator_retry_available"}, indent=2) + "\n",
                encoding="utf-8",
            )
            (task_root / "stop_policy.json").write_text(
                json.dumps({"checkpoint_kind": "retry_review"}, indent=2) + "\n",
                encoding="utf-8",
            )

            stdout = StringIO()
            with patch("swallow.cli.run_task") as run_task_mock:
                run_task_mock.return_value = TaskState(
                    task_id=task_id,
                    title="Retry allowed",
                    goal="Retry through the run path",
                    workspace_root=str(tmp_path),
                    status="completed",
                    phase="summarize",
                    retrieval_count=1,
                )
                with redirect_stdout(stdout):
                    self.assertEqual(main(["--base-dir", str(tmp_path), "task", "retry", task_id]), 0)

        run_task_mock.assert_called_once()
        self.assertIn(f"{task_id} completed retrieval=1", stdout.getvalue())

    def test_task_retry_blocks_when_retry_policy_disallows_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_id = "task-retry-blocked"
            task_root = tmp_path / ".swl" / "tasks" / task_id
            task_root.mkdir(parents=True, exist_ok=True)
            state = TaskState(
                task_id=task_id,
                title="Retry blocked",
                goal="Do not retry",
                workspace_root=str(tmp_path),
                status="failed",
                phase="summarize",
                updated_at="2026-04-09T12:10:00+00:00",
            )
            (task_root / "state.json").write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")
            (task_root / "retry_policy.json").write_text(
                json.dumps({"retryable": False, "retry_decision": "non_retryable_failure"}, indent=2) + "\n",
                encoding="utf-8",
            )
            (task_root / "stop_policy.json").write_text(
                json.dumps({"checkpoint_kind": "blocking_failure_review"}, indent=2) + "\n",
                encoding="utf-8",
            )

            stdout = StringIO()
            with patch("swallow.cli.run_task") as run_task_mock:
                with redirect_stdout(stdout):
                    self.assertEqual(main(["--base-dir", str(tmp_path), "task", "retry", task_id]), 1)

        run_task_mock.assert_not_called()
        self.assertIn("retry_blocked", stdout.getvalue())
        self.assertIn("retry_decision=non_retryable_failure", stdout.getvalue())
        self.assertIn("suggested_path=rerun", stdout.getvalue())

    def test_task_resume_runs_when_checkpoint_allows_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_id = "task-resume-run"
            task_root = tmp_path / ".swl" / "tasks" / task_id
            task_root.mkdir(parents=True, exist_ok=True)
            state = TaskState(
                task_id=task_id,
                title="Resume allowed",
                goal="Resume through the run path",
                workspace_root=str(tmp_path),
                status="failed",
                phase="summarize",
                updated_at="2026-04-09T12:10:00+00:00",
            )
            (task_root / "state.json").write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")
            (task_root / "checkpoint_snapshot.json").write_text(
                json.dumps(
                    {
                        "resume_ready": True,
                        "checkpoint_state": "resume_ready",
                        "recommended_path": "resume",
                        "recommended_reason": "failure_resume",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            stdout = StringIO()
            with patch("swallow.cli.run_task") as run_task_mock:
                run_task_mock.return_value = TaskState(
                    task_id=task_id,
                    title="Resume allowed",
                    goal="Resume through the run path",
                    workspace_root=str(tmp_path),
                    status="completed",
                    phase="summarize",
                    retrieval_count=1,
                )
                with redirect_stdout(stdout):
                    self.assertEqual(main(["--base-dir", str(tmp_path), "task", "resume", task_id]), 0)

        run_task_mock.assert_called_once()
        self.assertIn(f"{task_id} completed retrieval=1", stdout.getvalue())

    def test_task_resume_blocks_when_checkpoint_disallows_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_id = "task-resume-blocked"
            task_root = tmp_path / ".swl" / "tasks" / task_id
            task_root.mkdir(parents=True, exist_ok=True)
            state = TaskState(
                task_id=task_id,
                title="Resume blocked",
                goal="Do not resume",
                workspace_root=str(tmp_path),
                status="completed",
                phase="summarize",
                updated_at="2026-04-09T12:10:00+00:00",
            )
            (task_root / "state.json").write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")
            (task_root / "checkpoint_snapshot.json").write_text(
                json.dumps(
                    {
                        "resume_ready": False,
                        "checkpoint_state": "review_ready",
                        "recommended_path": "review",
                        "recommended_reason": "completed_run_review",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            stdout = StringIO()
            with patch("swallow.cli.run_task") as run_task_mock:
                with redirect_stdout(stdout):
                    self.assertEqual(main(["--base-dir", str(tmp_path), "task", "resume", task_id]), 1)

        run_task_mock.assert_not_called()
        self.assertIn("resume_blocked", stdout.getvalue())
        self.assertIn("checkpoint_state=review_ready", stdout.getvalue())
        self.assertIn("suggested_reason=completed_run_review", stdout.getvalue())

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

            with patch("swallow.orchestrator.select_route", return_value=enforced_route):
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

    def test_task_rerun_always_uses_run_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_id = "task-rerun"
            task_root = tmp_path / ".swl" / "tasks" / task_id
            task_root.mkdir(parents=True, exist_ok=True)
            state = TaskState(
                task_id=task_id,
                title="Rerun task",
                goal="Allow explicit rerun",
                workspace_root=str(tmp_path),
                status="completed",
                phase="done",
                updated_at="2026-04-09T12:10:00+00:00",
            )
            (task_root / "state.json").write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")

            stdout = StringIO()
            with patch("swallow.cli.run_task") as run_task_mock:
                run_task_mock.return_value = TaskState(
                    task_id=task_id,
                    title="Rerun task",
                    goal="Allow explicit rerun",
                    workspace_root=str(tmp_path),
                    status="completed",
                    phase="summarize",
                    retrieval_count=2,
                )
                with redirect_stdout(stdout):
                    self.assertEqual(main(["--base-dir", str(tmp_path), "task", "rerun", task_id]), 0)

        run_task_mock.assert_called_once()
        self.assertIn(f"{task_id} completed retrieval=2", stdout.getvalue())

    def test_task_inspect_shows_compact_overview_for_latest_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\ninspect overview baseline\n", encoding="utf-8")

            with patch.dict("os.environ", {"AIWF_EXECUTOR_MODE": "mock"}, clear=False):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "task",
                            "create",
                            "--title",
                            "Inspect task",
                            "--goal",
                            "Surface compact overview",
                            "--workspace-root",
                            str(tmp_path),
                        "--planning-source",
                        "chat://inspect-baseline",
                        "--constraint",
                        "Keep inspect concise",
                        "--acceptance-criterion",
                        "Show imported semantics availability",
                        "--knowledge-retrieval-eligible",
                        "--knowledge-item",
                        "A verified retrieval candidate should remain inspectable.",
                        "--knowledge-stage",
                        "verified",
                        "--knowledge-source",
                        "chat://inspect-knowledge",
                    ]
                ),
                    0,
                )
                task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)

                stdout = StringIO()
                with redirect_stdout(stdout):
                    self.assertEqual(main(["--base-dir", str(tmp_path), "task", "inspect", task_id]), 0)

        output = stdout.getvalue()
        self.assertIn(f"Task Overview: {task_id}", output)
        self.assertIn("title: Inspect task", output)
        self.assertIn("status: completed", output)
        self.assertIn("attempt_id: attempt-0002", output)
        self.assertIn("attempt_number: 2", output)
        self.assertIn("attempt_owner_kind: local_orchestrator", output)
        self.assertIn("attempt_owner_ref: swl_cli", output)
        self.assertIn("attempt_ownership_status: owned", output)
        self.assertIn("task_semantics_source_kind: external_planning_handoff", output)
        self.assertIn("task_semantics_source_ref: chat://inspect-baseline", output)
        self.assertIn("task_semantics_constraints: 1", output)
        self.assertIn("task_semantics_acceptance_criteria: 1", output)
        self.assertIn("knowledge_objects_count: 1", output)
        self.assertIn("knowledge_object_evidence: artifact_backed=0 source_only=1 unbacked=0", output)
        self.assertIn("knowledge_object_reuse: retrieval_candidate=1 task_only=0", output)
        self.assertIn("knowledge_partition: task_linked=1 reusable_candidate=1", output)
        self.assertIn("knowledge_index: active_reusable=0 inactive_reusable=1", output)
        self.assertIn("knowledge_index_refreshed_at:", output)
        self.assertIn("Knowledge Review", output)
        self.assertIn("knowledge_review_blocked: 1", output)
        self.assertIn("knowledge_review_blocked_reasons: evidence_not_artifact_backed", output)
        self.assertIn("knowledge_review_decisions_recorded: 0", output)
        self.assertIn("route_name: local-mock", output)
        self.assertIn("taxonomy: general-executor / task-state", output)
        self.assertIn("execution_site_contract_kind: local_inline", output)
        self.assertIn("execution_site_boundary: same_process", output)
        self.assertIn("execution_site_contract_status: active", output)
        self.assertIn("execution_site_handoff_required: no", output)
        self.assertIn("topology_execution_site: local", output)
        self.assertIn("topology_dispatch_status: local_dispatched", output)
        self.assertIn("grounding_locked: yes", output)
        self.assertIn("grounding_refs_count: 0", output)
        self.assertIn("grounding_refs: -", output)
        self.assertIn("compatibility_status: passed", output)
        self.assertIn("execution_fit_status: passed", output)
        self.assertIn("retry_policy_status: passed", output)
        self.assertIn("execution_budget_policy_status: passed", output)
        self.assertIn("stop_policy_status: warning", output)
        self.assertIn("knowledge_policy_status: warning", output)
        self.assertIn("validation_status: passed", output)
        self.assertIn("retrieval_record_available: yes", output)
        self.assertIn("reused_knowledge_in_retrieval: 0", output)
        self.assertIn("reused_knowledge_references: -", output)
        self.assertIn("grounding_available: yes", output)
        self.assertIn("memory_available: yes", output)
        self.assertIn("handoff_status: review_completed_run", output)
        self.assertIn("handoff_contract_status: ready", output)
        self.assertIn("handoff_contract_kind: operator_review", output)
        self.assertIn("checkpoint_state: review_ready", output)
        self.assertIn("recovery_semantics: completed_run_review", output)
        self.assertIn("interruption_kind: none", output)
        self.assertIn("retryable: no", output)
        self.assertIn("retry_decision: completed_no_retry", output)
        self.assertIn("remaining_attempts: 0", output)
        self.assertIn("timeout_seconds: 20", output)
        self.assertIn("budget_state: exhausted", output)
        self.assertIn("timeout_state: default", output)
        self.assertIn("stop_required: yes", output)
        self.assertIn("stop_decision: checkpoint_review", output)
        self.assertIn("escalation_level: operator_review", output)
        self.assertIn("handoff_next_owner_kind: operator", output)
        self.assertIn("handoff_next_owner_ref: swl_cli", output)
        self.assertIn("next_operator_action: Review summary.md", output)
        self.assertIn("task_semantics_report:", output)
        self.assertIn("knowledge_objects_report:", output)
        self.assertIn("knowledge_partition_report:", output)
        self.assertIn("knowledge_index_report:", output)
        self.assertIn("knowledge_decisions_report:", output)
        self.assertIn("summary:", output)
        self.assertIn("execution_site_report:", output)
        self.assertIn("retrieval_report:", output)
        self.assertIn("retry_policy_report:", output)
        self.assertIn("execution_budget_policy_report:", output)
        self.assertIn("stop_policy_report:", output)

    def test_task_inspect_marks_mock_remote_routes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Mock remote inspect",
                goal="Mark mock remote topology",
                workspace_root=tmp_path,
            )

            with patch.dict("os.environ", {"AIWF_MOCK_REMOTE_OUTCOME": "completed"}, clear=False):
                final_state = run_task(tmp_path, state.task_id, executor_name="mock-remote")

            self.assertEqual(final_state.topology_dispatch_status, "mock_remote_dispatched")
            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "inspect", state.task_id]), 0)

        output = stdout.getvalue()
        self.assertIn("route_label: [MOCK-REMOTE]", output)
        self.assertIn("topology_dispatch_status: mock_remote_dispatched", output)

    def test_task_inspect_does_not_mark_local_routes_as_mock_remote(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Local inspect",
                goal="Keep local route unmarked",
                workspace_root=tmp_path,
                executor_name="local",
            )
            final_state = run_task(tmp_path, state.task_id, executor_name="local")

            self.assertEqual(final_state.topology_dispatch_status, "local_dispatched")
            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "inspect", state.task_id]), 0)

        output = stdout.getvalue()
        self.assertIn("route_label: -", output)
        self.assertNotIn("[MOCK-REMOTE]", output)

    def test_task_inspect_keeps_blocked_dispatch_unmarked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Blocked inspect",
                goal="Do not mark blocked route as mock remote",
                workspace_root=tmp_path,
            )
            persisted = load_state(tmp_path, state.task_id)
            persisted.artifact_paths["task_semantics_json"] = "missing-artifact.md"
            save_state(tmp_path, persisted)
            blocked = run_task(tmp_path, state.task_id, executor_name="mock-remote")

            self.assertEqual(blocked.topology_dispatch_status, "blocked")
            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "inspect", state.task_id]), 0)

        output = stdout.getvalue()
        self.assertIn("route_label: -", output)
        self.assertIn("topology_dispatch_status: blocked", output)
        self.assertNotIn("[MOCK-REMOTE]", output)

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

    def test_task_inspect_shows_capability_enforcement_for_validator_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            created = create_task(
                base_dir=base_dir,
                title="Inspect enforcement",
                goal="Show capability enforcement in inspect",
                workspace_root=base_dir,
            )
            validator_route = RouteSelection(
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
                        memory_authority="task-state",
                    ),
                ),
                reason="Test-only validator route for inspect enforcement.",
                policy_inputs={},
            )

            with patch("swallow.orchestrator.select_route", return_value=validator_route):
                with patch("swallow.orchestrator.run_retrieval", return_value=[]):
                    with patch(
                        "swallow.orchestrator._execute_task_card",
                        return_value=ExecutorResult(
                            executor_name="local",
                            status="completed",
                            message="Execution finished.",
                            output="done",
                        ),
                    ):
                        run_task(base_dir, created.task_id, executor_name="local")

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(base_dir), "task", "inspect", created.task_id]), 0)

        output = stdout.getvalue()
        self.assertIn("capability_enforced: yes", output)
        self.assertIn("capability_enforced_fields: filesystem_access->workspace_read, supports_tool_loop->false", output)

    def test_task_inspect_shows_no_capability_enforcement_for_general_executor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Inspect no enforcement",
                goal="Keep general executor inspect clean",
                workspace_root=tmp_path,
                executor_name="codex",
            )
            with patch("swallow.orchestrator.run_retrieval", return_value=[]):
                with patch(
                    "swallow.orchestrator._execute_task_card",
                    return_value=ExecutorResult(
                        executor_name="codex",
                        status="completed",
                        message="Execution finished.",
                        output="done",
                    ),
                ):
                    run_task(tmp_path, state.task_id, executor_name="codex")

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "inspect", state.task_id]), 0)

        output = stdout.getvalue()
        self.assertIn("capability_enforced: -", output)
        self.assertIn("capability_enforced_fields: -", output)

    def test_task_dispatch_prints_mock_remote_label_for_mock_remote_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Mock remote dispatch report",
                goal="Label dispatch report output",
                workspace_root=tmp_path,
            )

            with patch.dict("os.environ", {"AIWF_MOCK_REMOTE_OUTCOME": "completed"}, clear=False):
                run_task(tmp_path, state.task_id, executor_name="mock-remote")

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "dispatch", state.task_id]), 0)

        output = stdout.getvalue()
        self.assertIn("[MOCK-REMOTE]", output)

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

    def test_task_artifacts_groups_paths_by_operator_concern(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\nartifact index grouping\n", encoding="utf-8")

            with patch.dict("os.environ", {"AIWF_EXECUTOR_MODE": "mock"}, clear=False):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "task",
                            "create",
                            "--title",
                            "Artifact index",
                            "--goal",
                            "Group artifact paths for review",
                            "--workspace-root",
                            str(tmp_path),
                        ]
                    ),
                    0,
                )
                task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)

                stdout = StringIO()
                with redirect_stdout(stdout):
                    self.assertEqual(main(["--base-dir", str(tmp_path), "task", "artifacts", task_id]), 0)

        output = stdout.getvalue()
        self.assertIn("Task Artifact Index", output)
        self.assertIn("Core Run Record", output)
        self.assertIn("Routing And Topology", output)
        self.assertIn("Retrieval And Grounding", output)
        self.assertIn("Validation", output)
        self.assertIn("Execution Control Policy", output)
        self.assertIn("Memory And Reuse", output)
        self.assertIn("summary:", output)
        self.assertIn("resume_note:", output)
        self.assertIn("route_report:", output)
        self.assertIn("execution_site_report:", output)
        self.assertIn("handoff_report:", output)
        self.assertIn("remote_handoff_contract_report:", output)
        self.assertIn("retrieval_report:", output)
        self.assertIn("validation_report:", output)
        self.assertIn("compatibility_report:", output)
        self.assertIn("execution_fit_report:", output)
        self.assertIn("retry_policy_report:", output)
        self.assertIn("execution_budget_policy_report:", output)
        self.assertIn("stop_policy_report:", output)
        self.assertIn("knowledge_policy_report:", output)
        self.assertIn("task_memory:", output)

    def test_task_policy_prints_compact_execution_control_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\npolicy summary\n", encoding="utf-8")

            with patch.dict("os.environ", {"AIWF_EXECUTOR_MODE": "mock"}, clear=False):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "task",
                            "create",
                            "--title",
                            "Policy summary",
                            "--goal",
                            "Show execution control state compactly",
                            "--workspace-root",
                            str(tmp_path),
                        ]
                    ),
                    0,
                )
                task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)

                stdout = StringIO()
                with redirect_stdout(stdout):
                    self.assertEqual(main(["--base-dir", str(tmp_path), "task", "policy", task_id]), 0)

        output = stdout.getvalue()
        self.assertIn(f"Task Policy: {task_id}", output)
        self.assertIn("Policy Controls", output)
        self.assertIn("retry_policy_status: passed", output)
        self.assertIn("execution_budget_policy_status: passed", output)
        self.assertIn("stop_policy_status: warning", output)
        self.assertIn("timeout_seconds: 20", output)
        self.assertIn("checkpoint_kind: completed_run_review", output)
        self.assertIn("Policy Artifacts", output)
        self.assertIn("retry_policy_report:", output)
        self.assertIn("execution_budget_policy_report:", output)
        self.assertIn("stop_policy_report:", output)

    def test_task_review_surfaces_handoff_and_resume_guidance_after_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\nreview handoff guidance\n", encoding="utf-8")

            with patch.dict(
                "os.environ",
                {"AIWF_CODEX_BIN": "definitely-not-a-real-codex-binary", "AIWF_EXECUTOR_MODE": "codex"},
                clear=False,
            ):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "task",
                            "create",
                            "--title",
                            "Review failure",
                            "--goal",
                            "Surface handoff review guidance",
                            "--workspace-root",
                            str(tmp_path),
                        ]
                    ),
                    0,
                )
                task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)

                stdout = StringIO()
                with redirect_stdout(stdout):
                    self.assertEqual(main(["--base-dir", str(tmp_path), "task", "review", task_id]), 0)

        output = stdout.getvalue()
        self.assertIn(f"Task Review: {task_id}", output)
        self.assertIn("status: completed", output)
        self.assertIn("handoff_status: review_completed_run", output)
        self.assertIn("handoff_contract_status: ready", output)
        self.assertIn("handoff_contract_kind: operator_review", output)
        self.assertIn("checkpoint_state: review_ready", output)
        self.assertIn("recovery_semantics: completed_run_review", output)
        self.assertIn("interruption_kind: none", output)
        self.assertIn("recommended_path: review", output)
        self.assertIn("handoff_next_owner_kind: operator", output)
        self.assertIn("handoff_next_owner_ref: swl_cli", output)
        self.assertIn("retry_policy_status: passed", output)
        self.assertIn("execution_budget_policy_status: passed", output)
        self.assertIn("retryable: no", output)
        self.assertIn("retry_decision: completed_no_retry", output)
        self.assertIn("stop_policy_status: warning", output)
        self.assertIn("stop_required: yes", output)
        self.assertIn("stop_decision: checkpoint_review", output)
        self.assertIn("blocking_reason: -", output)
        self.assertIn("knowledge_policy_status: passed", output)
        self.assertIn("knowledge_index_active_reusable: 0", output)
        self.assertIn("knowledge_index_inactive_reusable: 0", output)
        self.assertIn("knowledge_index_refreshed_at:", output)
        self.assertIn("reused_knowledge_in_retrieval: 0", output)
        self.assertIn("taxonomy: general-executor / task-state", output)
        self.assertIn("Knowledge Review", output)
        self.assertIn("knowledge_review_decisions_recorded: 0", output)
        self.assertIn("reused_knowledge_references: -", output)
        self.assertIn("next_operator_action:", output)
        self.assertIn("task_semantics_report:", output)
        self.assertIn("knowledge_objects_report:", output)
        self.assertIn("knowledge_partition_report:", output)
        self.assertIn("knowledge_index_report:", output)
        self.assertIn("knowledge_decisions_report:", output)
        self.assertIn("retrieval_report:", output)
        self.assertIn("source_grounding:", output)
        self.assertIn("grounding_locked: yes", output)
        self.assertIn("grounding_refs_count: 0", output)
        self.assertIn("grounding_evidence_report:", output)
        self.assertIn("resume_note:", output)
        self.assertIn("handoff_report:", output)
        self.assertIn("knowledge_policy_report:", output)
        self.assertIn("validation_report:", output)
        self.assertIn("retry_policy_report:", output)
        self.assertIn("execution_budget_policy_report:", output)
        self.assertIn("stop_policy_report:", output)
        self.assertIn("checkpoint_snapshot_report:", output)

    def test_task_help_includes_workbench_commands(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as raised:
                main(["task", "--help"])

        self.assertEqual(raised.exception.code, 0)
        output = stdout.getvalue()
        self.assertIn("list                List tasks with compact status summaries.", output)
        self.assertIn("planning-handoff    Attach or tighten imported planning semantics", output)
        self.assertIn("knowledge-capture   Attach staged knowledge objects to an existing", output)
        self.assertIn("knowledge-review-queue", output)
        self.assertIn("knowledge-promote", output)
        self.assertIn("knowledge-reject", output)
        self.assertIn("canonical-registry", output)
        self.assertIn("canonical-registry-index", output)
        self.assertIn("canonical-reuse", output)
        self.assertIn("inspect             Print a compact per-task overview.", output)
        self.assertIn("intake              Print a compact planning-handoff and staged-", output)
        self.assertIn("review              Print a review-focused task handoff summary.", output)
        self.assertIn("resume              Resume a task on the accepted run path", output)
        self.assertIn("artifacts           Print grouped task artifact paths.", output)
        self.assertIn("execution-site      Print the task execution-site report artifact.", output)
        self.assertIn("remote-handoff", output)
        self.assertIn("Print the task remote handoff contract report", output)

    def test_task_list_help_includes_focus_and_limit(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as raised:
                main(["task", "list", "--help"])

        self.assertEqual(raised.exception.code, 0)
        output = stdout.getvalue()
        self.assertIn("--focus {all,active,failed,needs-review,recent}", output)
        self.assertIn("--limit LIMIT", output)

    def test_top_level_help_includes_task_workbench_wording(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as raised:
                main(["--help"])

        self.assertEqual(raised.exception.code, 0)
        self.assertIn("task                Task workbench and lifecycle commands.", stdout.getvalue())
        self.assertIn("knowledge           Global staged knowledge review commands.", stdout.getvalue())

    def test_task_help_includes_capability_commands(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as raised:
                main(["task", "--help"])

        self.assertEqual(raised.exception.code, 0)
        output = stdout.getvalue()
        self.assertIn("capabilities        Print the task capability assembly summary.", output)
        self.assertIn("capabilities-json   Print the task capability assembly record.", output)
        self.assertIn("semantics           Print the task semantics report artifact.", output)
        self.assertIn("semantics-json      Print the task semantics record.", output)
        self.assertIn("knowledge-objects   Print the task knowledge-objects report artifact.", output)
        self.assertIn("knowledge-policy    Print the task knowledge-policy report artifact.", output)
        self.assertIn("knowledge-decisions", output)
        self.assertIn("canonical-registry", output)
        self.assertIn("canonical-registry-index", output)
        self.assertIn("canonical-reuse", output)

    def test_task_help_includes_phase9_workbench_commands(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as raised:
                main(["task", "--help"])

        self.assertEqual(raised.exception.code, 0)
        output = stdout.getvalue()
        self.assertIn("queue               List tasks that currently need operator action,", output)
        self.assertIn("including resume/retry/review.", output)
        self.assertIn("control             Print a compact per-task recovery and", output)
        self.assertIn("snapshot.", output)
        self.assertIn("attempts            Print compact attempt history for a task.", output)
        self.assertIn("compare-attempts", output)
        self.assertIn("Compare two task attempts using compact control-", output)
        self.assertIn("retry               Retry a task on the accepted run path when", output)
        self.assertIn("stop policy allow it.", output)
        self.assertIn("rerun               Start a new explicit operator-triggered run even", output)
        self.assertIn("retry or resume stay", output)

    def test_recovery_command_help_describes_checkpoint_boundaries(self) -> None:
        command_expectations = [
            (["task", "resume", "--help"], "checkpoint recovery truth allows"),
            (["task", "retry", "--help"], "retry and stop policy allow"),
            (["task", "rerun", "--help"], "retry or resume stay"),
            (["task", "checkpoint", "--help"], "used for resume, retry, review, and"),
        ]

        for argv, expected in command_expectations:
            stdout = StringIO()
            with redirect_stdout(stdout):
                with self.assertRaises(SystemExit) as raised:
                    main(argv)
            self.assertEqual(raised.exception.code, 0)
            self.assertIn(expected, stdout.getvalue())

    def test_task_create_help_includes_capability_flag(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as raised:
                main(["task", "create", "--help"])

        self.assertEqual(raised.exception.code, 0)
        self.assertIn("--capability CAPABILITY", stdout.getvalue())

    def test_task_run_help_includes_capability_flag(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as raised:
                main(["task", "run", "--help"])

        self.assertEqual(raised.exception.code, 0)
        self.assertIn("--capability CAPABILITY", stdout.getvalue())

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
        ]

        for argv, expected in command_expectations:
            stdout = StringIO()
            with redirect_stdout(stdout):
                with self.assertRaises(SystemExit) as raised:
                    main(argv)
            self.assertEqual(raised.exception.code, 0)
            self.assertIn(expected, stdout.getvalue())

    def test_task_grounding_prints_grounding_evidence_report(self) -> None:
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
                        "Grounding command",
                        "--goal",
                        "Read grounding evidence report",
                        "--workspace-root",
                        str(tmp_path),
                    ]
                ),
                0,
            )
            task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
            grounding_report = tmp_path / ".swl" / "tasks" / task_id / "artifacts" / "grounding_evidence_report.md"
            grounding_report.write_text("# Grounding Evidence\n\n- entry_count: 1\n", encoding="utf-8")
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "grounding", task_id]), 0)

        self.assertIn("Grounding Evidence", stdout.getvalue())
        self.assertIn("entry_count: 1", stdout.getvalue())

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

    def test_retrieval_evaluation_fixtures_cover_notes_repo_and_artifacts(self) -> None:
        fixture_root = Path(__file__).resolve().parent / "fixtures" / "retrieval_eval"
        cases = [
            {
                "query": "retrieval memory reuse grounding",
                "source_types": ["notes"],
                "expected_path": "notes_plan.md",
                "expected_title": "Retrieval Memory Reuse",
                "expected_source_type": "notes",
            },
            {
                "query": "route provenance compatibility",
                "source_types": ["repo"],
                "expected_path": "router.py",
                "expected_title": "select_route_policy",
                "expected_source_type": "repo",
            },
            {
                "query": "grounding artifact compatibility report",
                "source_types": [ARTIFACTS_SOURCE_TYPE],
                "expected_path": ".swl/tasks/demo/artifacts/summary.md",
                "expected_title": "Summary",
                "expected_source_type": ARTIFACTS_SOURCE_TYPE,
            },
        ]

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            shutil.copytree(fixture_root, tmp_path, dirs_exist_ok=True)

            for case in cases:
                with self.subTest(query=case["query"], source_types=case["source_types"]):
                    items = retrieve_context(
                        tmp_path,
                        query=case["query"],
                        source_types=case["source_types"],
                        limit=5,
                    )
                    self.assertGreaterEqual(len(items), 1)
                    top_item = items[0]
                    self.assertEqual(top_item.path, case["expected_path"])
                    self.assertEqual(top_item.title, case["expected_title"])
                    self.assertEqual(top_item.source_type, case["expected_source_type"])

    def test_retrieval_evaluation_fixtures_cover_current_and_cross_task_knowledge_boundaries(self) -> None:
        fixture_root = Path(__file__).resolve().parent / "fixtures" / "retrieval_eval"
        cases = [
            {
                "query": "current task topology review retrieval reuse boundary",
                "request": RetrievalRequest(
                    query="current task topology review retrieval reuse boundary",
                    source_types=[KNOWLEDGE_SOURCE_TYPE],
                    context_layers=["task"],
                    current_task_id="demo",
                    limit=5,
                    strategy="fixture_eval",
                ),
                "expected_path": ".swl/tasks/demo/knowledge_objects.json",
                "expected_citation": ".swl/tasks/demo/knowledge_objects.json#knowledge-0001",
                "expected_relation": "current_task",
            },
            {
                "query": "historical cross task retrieval history boundary grounding reuse",
                "request": RetrievalRequest(
                    query="historical cross task retrieval history boundary grounding reuse",
                    source_types=[KNOWLEDGE_SOURCE_TYPE],
                    context_layers=["history"],
                    current_task_id="demo",
                    limit=5,
                    strategy="fixture_eval",
                ),
                "expected_path": ".swl/tasks/prior/knowledge_objects.json",
                "expected_citation": ".swl/tasks/prior/knowledge_objects.json#knowledge-0001",
                "expected_relation": "cross_task",
            },
        ]

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            shutil.copytree(fixture_root, tmp_path, dirs_exist_ok=True)

            for case in cases:
                with self.subTest(query=case["query"]):
                    items = retrieve_context(tmp_path, request=case["request"])
                    self.assertEqual(len(items), 1)
                    top_item = items[0]
                    self.assertEqual(top_item.path, case["expected_path"])
                    self.assertEqual(top_item.citation, case["expected_citation"])
                    self.assertEqual(top_item.metadata["knowledge_task_relation"], case["expected_relation"])

    def test_task_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\norchestrator harness task memory\n", encoding="utf-8")

            with patch.dict("os.environ", {"AIWF_EXECUTOR_MODE": "mock"}, clear=False):
                exit_code = main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Design orchestrator",
                        "--goal",
                        "Create a phase 0 harness",
                        "--workspace-root",
                        str(tmp_path),
                    ]
                )
                self.assertEqual(exit_code, 0)

                tasks_dir = tmp_path / ".swl" / "tasks"
                created = [entry.name for entry in tasks_dir.iterdir() if entry.is_dir()]
                self.assertEqual(len(created), 1)
                task_id = created[0]

                exit_code = main(["--base-dir", str(tmp_path), "task", "run", task_id])
                self.assertEqual(exit_code, 0)

                summary = (tasks_dir / task_id / "artifacts" / "summary.md").read_text(encoding="utf-8")
                resume_note = (tasks_dir / task_id / "artifacts" / "resume_note.md").read_text(encoding="utf-8")
                validation_report = (tasks_dir / task_id / "artifacts" / "validation_report.md").read_text(
                    encoding="utf-8"
                )
                compatibility_report = (tasks_dir / task_id / "artifacts" / "compatibility_report.md").read_text(
                    encoding="utf-8"
                )
                execution_fit_report = (tasks_dir / task_id / "artifacts" / "execution_fit_report.md").read_text(
                    encoding="utf-8"
                )
                retry_policy_report = (tasks_dir / task_id / "artifacts" / "retry_policy_report.md").read_text(
                    encoding="utf-8"
                )
                execution_budget_policy_report = (
                    tasks_dir / task_id / "artifacts" / "execution_budget_policy_report.md"
                ).read_text(encoding="utf-8")
                stop_policy_report = (tasks_dir / task_id / "artifacts" / "stop_policy_report.md").read_text(
                    encoding="utf-8"
                )
                checkpoint_snapshot_report = (
                    tasks_dir / task_id / "artifacts" / "checkpoint_snapshot_report.md"
                ).read_text(encoding="utf-8")
                execution_site_report = (tasks_dir / task_id / "artifacts" / "execution_site_report.md").read_text(
                    encoding="utf-8"
                )
                knowledge_policy_report = (tasks_dir / task_id / "artifacts" / "knowledge_policy_report.md").read_text(
                    encoding="utf-8"
                )
                route_report = (tasks_dir / task_id / "artifacts" / "route_report.md").read_text(
                    encoding="utf-8"
                )
                topology_report = (tasks_dir / task_id / "artifacts" / "topology_report.md").read_text(
                    encoding="utf-8"
                )
                dispatch_report = (tasks_dir / task_id / "artifacts" / "dispatch_report.md").read_text(
                    encoding="utf-8"
                )
                handoff_report = (tasks_dir / task_id / "artifacts" / "handoff_report.md").read_text(
                    encoding="utf-8"
                )
                remote_handoff_report = (
                    tasks_dir / task_id / "artifacts" / "remote_handoff_contract_report.md"
                ).read_text(encoding="utf-8")
                retrieval_report = (tasks_dir / task_id / "artifacts" / "retrieval_report.md").read_text(
                    encoding="utf-8"
                )
                source_grounding = (tasks_dir / task_id / "artifacts" / "source_grounding.md").read_text(
                    encoding="utf-8"
                )
                executor_output = (tasks_dir / task_id / "artifacts" / "executor_output.md").read_text(
                    encoding="utf-8"
                )
                retrieval = json.loads((tasks_dir / task_id / "retrieval.json").read_text(encoding="utf-8"))
                compatibility = json.loads((tasks_dir / task_id / "compatibility.json").read_text(encoding="utf-8"))
                execution_fit = json.loads((tasks_dir / task_id / "execution_fit.json").read_text(encoding="utf-8"))
                retry_policy = json.loads((tasks_dir / task_id / "retry_policy.json").read_text(encoding="utf-8"))
                execution_budget_policy = json.loads(
                    (tasks_dir / task_id / "execution_budget_policy.json").read_text(encoding="utf-8")
                )
                stop_policy = json.loads((tasks_dir / task_id / "stop_policy.json").read_text(encoding="utf-8"))
                checkpoint_snapshot = json.loads(
                    (tasks_dir / task_id / "checkpoint_snapshot.json").read_text(encoding="utf-8")
                )
                knowledge_policy = json.loads((tasks_dir / task_id / "knowledge_policy.json").read_text(encoding="utf-8"))
                validation = json.loads((tasks_dir / task_id / "validation.json").read_text(encoding="utf-8"))
                memory = json.loads((tasks_dir / task_id / "memory.json").read_text(encoding="utf-8"))
                route = json.loads((tasks_dir / task_id / "route.json").read_text(encoding="utf-8"))
                execution_site = json.loads((tasks_dir / task_id / "execution_site.json").read_text(encoding="utf-8"))
                topology = json.loads((tasks_dir / task_id / "topology.json").read_text(encoding="utf-8"))
                dispatch = json.loads((tasks_dir / task_id / "dispatch.json").read_text(encoding="utf-8"))
                handoff = json.loads((tasks_dir / task_id / "handoff.json").read_text(encoding="utf-8"))
                remote_handoff = json.loads(
                    (tasks_dir / task_id / "remote_handoff_contract.json").read_text(encoding="utf-8")
                )

                self.assertIn("Summary for", summary)
                self.assertIn("notes.md", summary)
                self.assertIn("notes.md#L1-L3", summary)
                self.assertIn("mock", summary)
                self.assertIn("score_breakdown:", summary)
                self.assertIn("## Validation", summary)
                self.assertIn("- status: passed", summary)
                self.assertIn("route_mode:", summary)
                self.assertIn("route_name:", summary)
                self.assertIn("route_backend:", summary)
                self.assertIn("route_executor_family:", summary)
                self.assertIn("route_execution_site:", summary)
                self.assertIn("route_remote_capable:", summary)
                self.assertIn("route_transport_kind:", summary)
                self.assertIn("execution_lifecycle:", summary)
                self.assertIn("attempt_id:", summary)
                self.assertIn("attempt_number:", summary)
                self.assertIn("attempt_owner_kind:", summary)
                self.assertIn("attempt_owner_ref:", summary)
                self.assertIn("attempt_ownership_status:", summary)
                self.assertIn("attempt_owner_assigned_at:", summary)
                self.assertIn("attempt_transfer_reason:", summary)
                self.assertIn("route_capabilities:", summary)
                self.assertIn("execution_kind=", summary)
                self.assertIn("route_report_artifact:", summary)
                self.assertIn("topology_execution_site:", summary)
                self.assertIn("topology_executor_family:", summary)
                self.assertIn("topology_transport_kind:", summary)
                self.assertIn("topology_dispatch_status:", summary)
                self.assertIn("topology_report_artifact:", summary)
                self.assertIn("execution_site_contract_kind:", summary)
                self.assertIn("execution_site_boundary:", summary)
                self.assertIn("execution_site_contract_status:", summary)
                self.assertIn("execution_site_handoff_required:", summary)
                self.assertIn("execution_site_report_artifact:", summary)
                self.assertIn("dispatch_requested_at:", summary)
                self.assertIn("dispatch_started_at:", summary)
                self.assertIn("dispatch_report_artifact:", summary)
                self.assertIn("handoff_report_artifact:", summary)
                self.assertIn("compatibility_status:", summary)
                self.assertIn("execution_fit_status:", summary)
                self.assertIn("retry_policy_status:", summary)
                self.assertIn("execution_budget_policy_status:", summary)
                self.assertIn("stop_policy_status:", summary)
                self.assertIn("checkpoint_snapshot_report_artifact:", summary)
                self.assertIn("knowledge_policy_status:", summary)
                self.assertIn("execution_fit_report_artifact:", summary)
                self.assertIn("retry_policy_report_artifact:", summary)
                self.assertIn("execution_budget_policy_report_artifact:", summary)
                self.assertIn("stop_policy_report_artifact:", summary)
                self.assertIn("compatibility_report_artifact:", summary)
                self.assertIn("knowledge_policy_report_artifact:", summary)
                self.assertIn("source_grounding_artifact:", summary)
                self.assertIn("retrieval_report_artifact:", summary)
                self.assertIn("retrieval_record_path:", summary)
                self.assertIn("task_memory_path:", summary)
                self.assertIn("task_semantics_source_kind:", summary)
                self.assertIn("task_semantics_source_ref:", summary)
                self.assertIn("task_semantics_report_artifact:", summary)
                self.assertIn("knowledge_objects_count:", summary)
                self.assertIn("knowledge_evidence_artifact_backed:", summary)
                self.assertIn("knowledge_retrieval_candidate_count:", summary)
                self.assertIn("knowledge_objects_report_artifact:", summary)
                self.assertIn("knowledge_partition_report_artifact:", summary)
                self.assertIn("knowledge_index_report_artifact:", summary)
                self.assertIn("knowledge_index_active_reusable_count: 0", summary)
                self.assertIn("knowledge_index_inactive_reusable_count: 0", summary)
                self.assertIn("knowledge_index_refreshed_at:", summary)
                self.assertIn("retrieval_reused_knowledge_count: 0", summary)
                self.assertIn("## Task Semantics", summary)
                self.assertIn("## Knowledge Objects", summary)
                self.assertIn("## Compatibility", summary)
                self.assertIn("## Retry Policy", summary)
                self.assertIn("## Execution Budget Policy", summary)
                self.assertIn("## Stop Policy", summary)
                self.assertIn("## Knowledge Policy", summary)
                self.assertIn("## Executor Output", summary)
                self.assertNotIn("## Next Suggested Step", summary)
                self.assertIn("Resume Note for", resume_note)
                self.assertIn("## Hand-off", resume_note)
                self.assertIn("## Next Suggested Step", resume_note)
                self.assertNotIn("## Executor Output", resume_note)
                self.assertNotIn("failed live execution attempt", resume_note)
                self.assertIn("Review summary.md to confirm the run outcome", resume_note)
                self.assertIn("validation status: passed", resume_note)
                self.assertIn("route mode:", resume_note)
                self.assertIn("route name:", resume_note)
                self.assertIn("route backend:", resume_note)
                self.assertIn("route executor family:", resume_note)
                self.assertIn("route execution site:", resume_note)
                self.assertIn("task semantics source kind:", resume_note)
                self.assertIn("task semantics source ref:", resume_note)
                self.assertIn("task semantics report artifact:", resume_note)
                self.assertIn("knowledge objects count:", resume_note)
                self.assertIn("artifact-backed knowledge objects:", resume_note)
                self.assertIn("retrieval-eligible knowledge objects:", resume_note)
                self.assertIn("reused verified knowledge records: 0", resume_note)
                self.assertIn("knowledge objects report artifact:", resume_note)
                self.assertIn("knowledge partition report artifact:", resume_note)
                self.assertIn("knowledge index report artifact:", resume_note)
                self.assertIn("knowledge index active reusable count: 0", resume_note)
                self.assertIn("knowledge index inactive reusable count: 0", resume_note)
                self.assertIn("knowledge index refreshed at:", resume_note)
                self.assertIn("knowledge index json path:", resume_note)
                self.assertIn("reused knowledge references: none", resume_note)
                self.assertIn("route remote capable:", resume_note)
                self.assertIn("route transport kind:", resume_note)
                self.assertIn("execution lifecycle:", resume_note)
                self.assertIn("attempt id:", resume_note)
                self.assertIn("attempt number:", resume_note)
                self.assertIn("attempt owner kind:", resume_note)
                self.assertIn("attempt owner ref:", resume_note)
                self.assertIn("attempt ownership status:", resume_note)
                self.assertIn("attempt owner assigned at:", resume_note)
                self.assertIn("attempt transfer reason:", resume_note)
                self.assertIn("route reason:", resume_note)
                self.assertIn("route report artifact:", resume_note)
                self.assertIn("topology execution site:", resume_note)
                self.assertIn("topology executor family:", resume_note)
                self.assertIn("topology transport kind:", resume_note)
                self.assertIn("topology dispatch status:", resume_note)
                self.assertIn("topology report artifact:", resume_note)
                self.assertIn("execution-site contract kind:", resume_note)
                self.assertIn("execution-site boundary:", resume_note)
                self.assertIn("execution-site contract status:", resume_note)
                self.assertIn("execution-site handoff required:", resume_note)
                self.assertIn("execution-site report artifact:", resume_note)
                self.assertIn("dispatch requested at:", resume_note)
                self.assertIn("dispatch started at:", resume_note)
                self.assertIn("dispatch report artifact:", resume_note)
                self.assertIn("handoff report artifact:", resume_note)
                self.assertIn("compatibility status: passed", resume_note)
                self.assertIn("execution fit status: passed", resume_note)
                self.assertIn("retry policy status: passed", resume_note)
                self.assertIn("execution budget policy status: passed", resume_note)
                self.assertIn("stop policy status: warning", resume_note)
                self.assertIn("checkpoint snapshot report artifact:", resume_note)
                self.assertIn("knowledge policy status: passed", resume_note)
                self.assertIn("execution fit report artifact:", resume_note)
                self.assertIn("retry policy report artifact:", resume_note)
                self.assertIn("execution budget policy report artifact:", resume_note)
                self.assertIn("stop policy report artifact:", resume_note)
                self.assertIn("compatibility report artifact:", resume_note)
                self.assertIn("knowledge policy report artifact:", resume_note)
                self.assertIn("source grounding artifact:", resume_note)
                self.assertIn("task memory path:", resume_note)
                self.assertIn("task semantics json path:", resume_note)
                self.assertIn("knowledge objects json path:", resume_note)
                self.assertIn("top retrieved references: notes.md#L1-L3", resume_note)
                self.assertIn("Validation Report", validation_report)
                self.assertIn("Compatibility Report", compatibility_report)
                self.assertIn("Execution Fit Report", execution_fit_report)
                self.assertIn("Retry Policy Report", retry_policy_report)
                self.assertIn("Execution Budget Policy Report", execution_budget_policy_report)
                self.assertIn("Stop Policy Report", stop_policy_report)
                self.assertIn("Checkpoint Snapshot Report", checkpoint_snapshot_report)
                self.assertIn("Execution Site Report", execution_site_report)
                self.assertIn("Knowledge Policy Report", knowledge_policy_report)
                self.assertIn("Route Report", route_report)
                self.assertIn("Topology Report", topology_report)
                self.assertIn("Dispatch Report", dispatch_report)
                self.assertIn("Handoff Report", handoff_report)
                self.assertIn("Remote Handoff Contract Report", remote_handoff_report)
                self.assertIn("## Remote Handoff Contract", execution_site_report)
                self.assertIn("## Remote Handoff Contract", dispatch_report)
                self.assertIn("remote_handoff_contract_kind: not_applicable", handoff_report)
                self.assertIn("contract_status: ready", handoff_report)
                self.assertIn("contract_kind: operator_review", handoff_report)
                self.assertIn("next_owner_kind: operator", handoff_report)
                self.assertIn("next_owner_ref: swl_cli", handoff_report)
                self.assertIn("## Required Inputs", handoff_report)
                self.assertIn("## Expected Outputs", handoff_report)
                self.assertIn("contract_kind: not_applicable", remote_handoff_report)
                self.assertIn("handoff_boundary: local_baseline", remote_handoff_report)
                self.assertIn("Retrieval Report", retrieval_report)
                self.assertIn("reused_knowledge_count: 0", retrieval_report)
                self.assertIn("Source Grounding", source_grounding)
                self.assertIn("notes.md#L1-L3", source_grounding)
                self.assertEqual(compatibility["status"], "passed")
                self.assertEqual(execution_fit["status"], "passed")
                self.assertEqual(retry_policy["status"], "passed")
                self.assertEqual(retry_policy["retryable"], False)
                self.assertEqual(execution_budget_policy["status"], "passed")
                self.assertEqual(execution_budget_policy["timeout_seconds"], 20)
                self.assertEqual(stop_policy["status"], "warning")
                self.assertEqual(stop_policy["stop_decision"], "checkpoint_review")
                self.assertEqual(checkpoint_snapshot["status"], "passed")
                self.assertEqual(checkpoint_snapshot["checkpoint_state"], "review_ready")
                self.assertEqual(checkpoint_snapshot["recommended_path"], "review")
                self.assertTrue(checkpoint_snapshot["review_ready"])
                self.assertFalse(checkpoint_snapshot["resume_ready"])
                self.assertEqual(knowledge_policy["status"], "passed")
                self.assertEqual(validation["status"], "passed")
                self.assertEqual(route["name"], "local-mock")
                self.assertEqual(route["executor_family"], "cli")
                self.assertEqual(execution_site["contract_kind"], "local_inline")
                self.assertEqual(execution_site["boundary"], "same_process")
                self.assertEqual(execution_site["contract_status"], "active")
                self.assertEqual(execution_site["handoff_required"], False)
                self.assertEqual(execution_site["execution_site"], "local")
                self.assertEqual(topology["route_name"], "local-mock")
                self.assertEqual(topology["executor_family"], "cli")
                self.assertEqual(topology["execution_site"], "local")
                self.assertEqual(topology["transport_kind"], "local_process")
                self.assertEqual(topology["remote_capable_intent"], False)
                self.assertEqual(topology["dispatch_status"], "local_dispatched")
                self.assertEqual(topology["execution_lifecycle"], "dispatched")
                self.assertEqual(dispatch["attempt_id"], "attempt-0001")
                self.assertEqual(dispatch["attempt_number"], 1)
                self.assertEqual(dispatch["attempt_owner_kind"], "local_orchestrator")
                self.assertEqual(dispatch["attempt_owner_ref"], "swl_cli")
                self.assertEqual(dispatch["attempt_ownership_status"], "owned")
                self.assertTrue(bool(dispatch["attempt_owner_assigned_at"]))
                self.assertEqual(dispatch["attempt_transfer_reason"], "")
                self.assertEqual(dispatch["route_name"], "local-mock")
                self.assertEqual(dispatch["execution_site_contract_kind"], "local_inline")
                self.assertEqual(dispatch["execution_site_boundary"], "same_process")
                self.assertEqual(dispatch["executor_family"], "cli")
                self.assertEqual(dispatch["execution_site"], "local")
                self.assertEqual(dispatch["transport_kind"], "local_process")
                self.assertEqual(dispatch["dispatch_status"], "local_dispatched")
                self.assertEqual(dispatch["execution_lifecycle"], "dispatched")
                self.assertEqual(dispatch["remote_handoff_contract_kind"], "not_applicable")
                self.assertEqual(dispatch["remote_handoff_dispatch_readiness"], "not_applicable")
                self.assertTrue(bool(dispatch["dispatch_requested_at"]))
                self.assertTrue(bool(dispatch["dispatch_started_at"]))
                self.assertEqual(handoff["status"], "review_completed_run")
                self.assertEqual(handoff["contract_status"], "ready")
                self.assertEqual(handoff["contract_kind"], "operator_review")
                self.assertEqual(handoff["next_owner_kind"], "operator")
                self.assertEqual(handoff["next_owner_ref"], "swl_cli")
                self.assertGreaterEqual(len(handoff["required_inputs"]), 3)
                self.assertGreaterEqual(len(handoff["expected_outputs"]), 2)
                self.assertEqual(handoff["task_status"], "completed")
                self.assertEqual(handoff["attempt_id"], "attempt-0001")
                self.assertEqual(handoff["attempt_number"], 1)
                self.assertEqual(handoff["attempt_owner_kind"], "local_orchestrator")
                self.assertEqual(handoff["attempt_owner_ref"], "swl_cli")
                self.assertEqual(handoff["attempt_ownership_status"], "owned")
                self.assertTrue(bool(handoff["attempt_owner_assigned_at"]))
                self.assertEqual(handoff["attempt_transfer_reason"], "")
                self.assertEqual(handoff["execution_site_contract_kind"], "local_inline")
                self.assertEqual(handoff["execution_site_boundary"], "same_process")
                self.assertEqual(handoff["execution_site_contract_status"], "active")
                self.assertEqual(handoff["execution_site_handoff_required"], False)
                self.assertEqual(handoff["execution_site"], "local")
                self.assertEqual(handoff["executor_family"], "cli")
                self.assertEqual(handoff["dispatch_status"], "local_dispatched")
                self.assertEqual(handoff["remote_handoff_contract_kind"], "not_applicable")
                self.assertEqual(handoff["remote_handoff_contract_status"], "not_needed")
                self.assertEqual(handoff["remote_handoff_boundary"], "local_baseline")
                self.assertEqual(handoff["blocking_reason"], "")
                self.assertIn("Review summary.md", handoff["next_operator_action"])
                self.assertEqual(remote_handoff["contract_kind"], "not_applicable")
                self.assertEqual(remote_handoff["contract_status"], "not_needed")
                self.assertEqual(remote_handoff["handoff_boundary"], "local_baseline")
                self.assertEqual(remote_handoff["transport_truth"], "local_only")
                self.assertIn("task_semantics", memory)
                self.assertIn("knowledge_objects", memory)
                self.assertEqual(memory["executor"]["name"], "mock")
                self.assertEqual(memory["execution_attempt"]["attempt_id"], "attempt-0001")
                self.assertEqual(memory["execution_attempt"]["attempt_number"], 1)
                self.assertEqual(memory["execution_attempt"]["owner_kind"], "local_orchestrator")
                self.assertEqual(memory["execution_attempt"]["owner_ref"], "swl_cli")
                self.assertEqual(memory["execution_attempt"]["ownership_status"], "owned")
                self.assertTrue(bool(memory["execution_attempt"]["owner_assigned_at"]))
                self.assertEqual(memory["execution_attempt"]["transfer_reason"], "")
                self.assertTrue(bool(memory["execution_attempt"]["dispatch_requested_at"]))
                self.assertTrue(bool(memory["execution_attempt"]["dispatch_started_at"]))
                self.assertEqual(memory["execution_attempt"]["execution_lifecycle"], "completed")
                self.assertEqual(memory["route"]["mode"], "auto")
                self.assertEqual(memory["route"]["name"], "local-mock")
                self.assertEqual(memory["route"]["executor_family"], "cli")
                self.assertEqual(memory["route"]["execution_site"], "local")
                self.assertEqual(memory["route"]["remote_capable"], False)
                self.assertEqual(memory["route"]["transport_kind"], "local_process")
                self.assertEqual(memory["route"]["capabilities"]["deterministic"], True)
                self.assertEqual(memory["execution_site"]["contract_kind"], "local_inline")
                self.assertEqual(memory["topology"]["route_name"], "local-mock")
                self.assertEqual(memory["topology"]["executor_family"], "cli")
                self.assertEqual(memory["topology"]["execution_site"], "local")
                self.assertEqual(memory["topology"]["transport_kind"], "local_process")
                self.assertEqual(memory["topology"]["remote_capable_intent"], False)
                self.assertEqual(memory["topology"]["dispatch_status"], "local_dispatched")
                self.assertEqual(memory["topology"]["execution_lifecycle"], "completed")
                self.assertEqual(memory["dispatch"]["attempt_id"], "attempt-0001")
                self.assertEqual(memory["dispatch"]["executor_family"], "cli")
                self.assertEqual(memory["dispatch"]["attempt_number"], 1)
                self.assertEqual(memory["dispatch"]["dispatch_status"], "local_dispatched")
                self.assertEqual(memory["dispatch"]["execution_lifecycle"], "completed")
                self.assertEqual(memory["handoff"]["status"], "review_completed_run")
                self.assertEqual(memory["handoff"]["task_status"], "completed")
                self.assertEqual(memory["handoff"]["executor_family"], "cli")
                self.assertEqual(memory["handoff"]["execution_lifecycle"], "completed")
                self.assertIn("evidence_counts", memory["knowledge_objects"])
                self.assertIn("reuse_counts", memory["knowledge_objects"])
                self.assertEqual(memory["knowledge_partition"]["reusable_candidate_count"], 0)
                self.assertEqual(memory["knowledge_index"]["active_reusable_count"], 0)
                self.assertEqual(memory["knowledge_index"]["inactive_reusable_count"], 0)
                self.assertTrue(bool(memory["knowledge_index"]["refreshed_at"]))
                self.assertEqual(memory["compatibility"]["status"], "passed")
                self.assertEqual(memory["execution_fit"]["status"], "passed")
                self.assertEqual(memory["retry_policy"]["status"], "passed")
                self.assertEqual(memory["execution_budget_policy"]["status"], "passed")
                self.assertEqual(memory["stop_policy"]["status"], "warning")
                self.assertEqual(memory["checkpoint_snapshot"]["checkpoint_state"], "review_ready")
                self.assertEqual(memory["knowledge_policy"]["status"], "passed")
                self.assertTrue(
                    memory["artifact_paths"]["compatibility_report"].endswith("compatibility_report.md")
                )
                self.assertTrue(memory["artifact_paths"]["compatibility_json"].endswith("compatibility.json"))
                self.assertTrue(memory["artifact_paths"]["knowledge_policy_report"].endswith("knowledge_policy_report.md"))
                self.assertTrue(memory["artifact_paths"]["knowledge_policy_json"].endswith("knowledge_policy.json"))
                self.assertTrue(memory["artifact_paths"]["task_semantics_json"].endswith("task_semantics.json"))
                self.assertTrue(memory["artifact_paths"]["task_semantics_report"].endswith("task_semantics_report.md"))
                self.assertTrue(memory["artifact_paths"]["knowledge_objects_json"].endswith("knowledge_objects.json"))
                self.assertTrue(memory["artifact_paths"]["knowledge_objects_report"].endswith("knowledge_objects_report.md"))
                self.assertTrue(memory["artifact_paths"]["knowledge_partition_json"].endswith("knowledge_partition.json"))
                self.assertTrue(memory["artifact_paths"]["knowledge_partition_report"].endswith("knowledge_partition_report.md"))
                self.assertTrue(memory["artifact_paths"]["knowledge_index_json"].endswith("knowledge_index.json"))
                self.assertTrue(memory["artifact_paths"]["knowledge_index_report"].endswith("knowledge_index_report.md"))
                self.assertTrue(memory["artifact_paths"]["route_report"].endswith("route_report.md"))
                self.assertTrue(memory["artifact_paths"]["route_json"].endswith("route.json"))
                self.assertTrue(memory["artifact_paths"]["topology_report"].endswith("topology_report.md"))
                self.assertTrue(memory["artifact_paths"]["topology_json"].endswith("topology.json"))
                self.assertTrue(memory["artifact_paths"]["dispatch_report"].endswith("dispatch_report.md"))
                self.assertTrue(memory["artifact_paths"]["dispatch_json"].endswith("dispatch.json"))
                self.assertTrue(memory["artifact_paths"]["handoff_report"].endswith("handoff_report.md"))
                self.assertTrue(memory["artifact_paths"]["handoff_json"].endswith("handoff.json"))
                self.assertTrue(memory["artifact_paths"]["execution_fit_report"].endswith("execution_fit_report.md"))
                self.assertTrue(memory["artifact_paths"]["execution_fit_json"].endswith("execution_fit.json"))
                self.assertTrue(memory["artifact_paths"]["retry_policy_report"].endswith("retry_policy_report.md"))
                self.assertTrue(memory["artifact_paths"]["retry_policy_json"].endswith("retry_policy.json"))
                self.assertTrue(
                    memory["artifact_paths"]["execution_budget_policy_report"].endswith(
                        "execution_budget_policy_report.md"
                    )
                )
                self.assertTrue(
                    memory["artifact_paths"]["execution_budget_policy_json"].endswith(
                        "execution_budget_policy.json"
                    )
                )
                self.assertTrue(memory["artifact_paths"]["stop_policy_report"].endswith("stop_policy_report.md"))
                self.assertTrue(memory["artifact_paths"]["stop_policy_json"].endswith("stop_policy.json"))
                self.assertTrue(
                    memory["artifact_paths"]["checkpoint_snapshot_report"].endswith("checkpoint_snapshot_report.md")
                )
                self.assertTrue(
                    memory["artifact_paths"]["checkpoint_snapshot_json"].endswith("checkpoint_snapshot.json")
                )
                self.assertTrue(memory["artifact_paths"]["retrieval_json"].endswith("retrieval.json"))
                self.assertTrue(memory["artifact_paths"]["retrieval_report"].endswith("retrieval_report.md"))
                self.assertEqual(memory["artifact_paths"]["source_grounding"].endswith("source_grounding.md"), True)
                self.assertEqual(memory["retrieval"]["top_references"], ["notes.md#L1-L3"])
                self.assertEqual(memory["retrieval"]["reused_knowledge_count"], 0)
                self.assertEqual(memory["retrieval"]["reused_knowledge_references"], [])
                self.assertEqual(memory["retrieval"]["grounding_artifact"].endswith("source_grounding.md"), True)
                self.assertEqual(memory["retrieval"]["retrieval_record_path"].endswith("retrieval.json"), True)
                self.assertEqual(memory["retrieval"]["retrieval_report_artifact"].endswith("retrieval_report.md"), True)
                self.assertEqual(memory["retrieval"]["reuse_ready"], True)
                self.assertEqual(memory["validation"]["status"], "passed")
                self.assertEqual(memory["status"], "completed")
                self.assertIn("Mock executor output", executor_output)
                self.assertEqual(retrieval[0]["chunk_id"], "section-1")
                self.assertEqual(retrieval[0]["title"], "Notes")
                self.assertEqual(retrieval[0]["citation"], "notes.md#L1-L3")
                self.assertIn("score_breakdown", retrieval[0])
                self.assertEqual(retrieval[0]["metadata"]["chunk_kind"], "markdown_section")
                self.assertEqual(retrieval[0]["metadata"]["title_source"], "heading")

    def test_task_failure_when_codex_binary_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\nexecutor failure coverage\n", encoding="utf-8")

            with patch.dict(
                "os.environ",
                {"AIWF_CODEX_BIN": "definitely-not-a-real-codex-binary", "AIWF_EXECUTOR_MODE": "codex"},
                clear=False,
            ):
                exit_code = main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Failing executor",
                        "--goal",
                        "Exercise codex adapter failure handling",
                        "--workspace-root",
                        str(tmp_path),
                    ]
                )
                self.assertEqual(exit_code, 0)

                tasks_dir = tmp_path / ".swl" / "tasks"
                task_id = next(entry.name for entry in tasks_dir.iterdir() if entry.is_dir())

                exit_code = main(["--base-dir", str(tmp_path), "task", "run", task_id])
                self.assertEqual(exit_code, 0)

                state = (tasks_dir / task_id / "state.json").read_text(encoding="utf-8")
                summary = (tasks_dir / task_id / "artifacts" / "summary.md").read_text(encoding="utf-8")
                executor_output = (tasks_dir / task_id / "artifacts" / "executor_output.md").read_text(
                    encoding="utf-8"
                )
                executor_stdout = (tasks_dir / task_id / "artifacts" / "executor_stdout.txt").read_text(
                    encoding="utf-8"
                )
                executor_stderr = (tasks_dir / task_id / "artifacts" / "executor_stderr.txt").read_text(
                    encoding="utf-8"
                )
                memory = json.loads((tasks_dir / task_id / "memory.json").read_text(encoding="utf-8"))

                fallback_primary_output = (
                    tasks_dir / task_id / "artifacts" / "fallback_primary_executor_output.md"
                ).read_text(encoding="utf-8")
                fallback_primary_stderr = (
                    tasks_dir / task_id / "artifacts" / "fallback_primary_executor_stderr.txt"
                ).read_text(encoding="utf-8")

                self.assertIn('"status": "completed"', state)
                self.assertIn("Selected fallback route 'local-summary'", summary)
                self.assertIn("# Local Executor Update", executor_output)
                self.assertEqual(executor_stdout.strip(), "")
                self.assertEqual(executor_stderr.strip(), "")
                self.assertIn("Codex binary not found", fallback_primary_output)
                self.assertIn("definitely-not-a-real-codex-binary", fallback_primary_stderr)
                self.assertEqual(memory["status"], "completed")

    def test_codex_timeout_preserves_partial_output(self) -> None:
        state = TaskState(
            task_id="timeout123",
            title="Timeout executor",
            goal="Keep partial output on timeout",
            workspace_root="/tmp",
        )
        timeout_exc = subprocess.TimeoutExpired(
            cmd=["codex", "exec"],
            timeout=5,
            output="partial stdout",
            stderr="partial stderr",
        )

        with patch("swallow.executor.shutil.which", return_value="/usr/bin/codex"):
            with patch("swallow.executor.subprocess.run", side_effect=timeout_exc):
                result = run_codex_executor(state, [])

        self.assertEqual(result.status, "failed")
        self.assertIn("timed out", result.message)
        self.assertIn("Structured fallback note generated", result.message)
        self.assertEqual(result.failure_kind, "timeout")
        self.assertIn("# Executor Fallback Note", result.output)
        self.assertIn("partial stdout", result.output)
        self.assertEqual(result.stdout, "partial stdout")
        self.assertEqual(result.stderr, "partial stderr")

    def test_failure_classifier_marks_unreachable_backend(self) -> None:
        failure_kind = classify_failure_kind(
            1,
            "failed to connect to websocket: Operation not permitted",
            "ERROR: Reconnecting... 2/5",
        )
        self.assertEqual(failure_kind, "unreachable_backend")

    def test_failure_classifier_expanded_unreachable_markers(self) -> None:
        failure_kind = classify_failure_kind(
            1,
            "Request failed while connecting to wss://chatgpt.com/backend-api/codex/responses",
            "连接失败；请求失败；https://chatgpt.com/backend-api/wham/apps",
        )
        self.assertEqual(failure_kind, "unreachable_backend")

    def test_note_only_mode_skips_subprocess(self) -> None:
        state = TaskState(
            task_id="note123",
            title="Note only",
            goal="Skip live execution",
            workspace_root="/tmp",
        )
        with patch.dict("os.environ", {"AIWF_EXECUTOR_MODE": "note-only"}, clear=False):
            with patch("swallow.executor.subprocess.run") as mocked_run:
                from swallow.executor import run_executor

                result = run_executor(state, [])

        mocked_run.assert_not_called()
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.failure_kind, "unreachable_backend")
        self.assertIn("non-live mode", result.message)
        self.assertIn("# Executor Fallback Note", result.output)

    def test_unreachable_backend_fallback_includes_connectivity_guidance(self) -> None:
        state = TaskState(
            task_id="net123",
            title="Connectivity failure",
            goal="Classify unreachable backend correctly",
            workspace_root="/tmp",
        )
        unreachable_result = ExecutorResult(
            executor_name="codex",
            status="failed",
            message="Backend connection failed.",
            output="failed to connect to websocket",
            prompt="prompt",
            failure_kind="unreachable_backend",
        )
        note = build_fallback_output(state, [], unreachable_result)
        self.assertIn("outbound network and websocket access", note)
        self.assertIn("backend connectivity", note)

    def test_doctor_codex_missing_binary_returns_nonzero(self) -> None:
        stdout = StringIO()
        with patch("swallow.doctor.shutil.which", return_value=None):
            with redirect_stdout(stdout):
                exit_code = main(["doctor", "codex"])
        self.assertNotEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("binary_found=no", output)
        self.assertIn("launch_ok=no", output)
        self.assertIn("note_only_recommended=yes", output)

    def test_doctor_codex_success_returns_zero(self) -> None:
        stdout = StringIO()
        completed = subprocess.CompletedProcess(
            args=["codex", "--version"],
            returncode=0,
            stdout="codex 1.2.3",
            stderr="",
        )
        with patch("swallow.doctor.shutil.which", return_value="/usr/bin/codex"):
            with patch("swallow.doctor.subprocess.run", return_value=completed):
                with redirect_stdout(stdout):
                    exit_code = main(["doctor", "codex"])
        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("binary_found=yes", output)
        self.assertIn("launch_ok=yes", output)
        self.assertIn("note_only_recommended=no", output)

    def test_task_run_artifact_paths_include_executor_streams(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\nartifact path coverage\n", encoding="utf-8")

            with patch.dict("os.environ", {"AIWF_EXECUTOR_MODE": "mock"}, clear=False):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "task",
                            "create",
                            "--title",
                            "Artifact paths",
                            "--goal",
                            "Ensure artifact_paths include executor streams",
                            "--workspace-root",
                            str(tmp_path),
                        ]
                    ),
                    0,
                )
                task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)
                state = (tmp_path / ".swl" / "tasks" / task_id / "state.json").read_text(encoding="utf-8")

        self.assertIn('"executor_prompt"', state)
        self.assertIn('"executor_output"', state)
        self.assertIn('"executor_stdout"', state)
        self.assertIn('"executor_stderr"', state)
        self.assertIn('"summary"', state)
        self.assertIn('"resume_note"', state)
        self.assertIn('"route_report"', state)
        self.assertIn('"compatibility_report"', state)
        self.assertIn('"source_grounding"', state)
        self.assertIn('"retrieval_report"', state)
        self.assertIn('"compatibility_json"', state)
        self.assertIn('"validation_report"', state)
        self.assertIn('"validation_json"', state)
        self.assertIn('"task_memory"', state)
        self.assertIn('"retrieval_json"', state)
        self.assertIn('"route_json"', state)
        self.assertIn('"topology_report"', state)
        self.assertIn('"topology_json"', state)
        self.assertIn('"dispatch_report"', state)
        self.assertIn('"dispatch_json"', state)
        self.assertIn('"execution_fit_report"', state)
        self.assertIn('"execution_fit_json"', state)
        self.assertIn('"handoff_report"', state)
        self.assertIn('"handoff_json"', state)

    def test_retrieve_context_returns_traceable_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text(
                "# Retrieval Title\n\nretrieval metadata baseline for context records\n",
                encoding="utf-8",
            )
            script = tmp_path / "task.py"
            script.write_text("print('retrieval metadata baseline')\n", encoding="utf-8")

            items = retrieve_context(tmp_path, query="retrieval metadata baseline", limit=4)

        self.assertGreaterEqual(len(items), 2)
        note_item = next(item for item in items if item.path == "notes.md")
        repo_item = next(item for item in items if item.path == "task.py")
        self.assertEqual(note_item.chunk_id, "section-1")
        self.assertEqual(note_item.title, "Retrieval Title")
        self.assertEqual(note_item.citation, "notes.md#L1-L3")
        self.assertIn("retrieval", note_item.matched_terms)
        self.assertIn("content_hits", note_item.score_breakdown)
        self.assertIn("rerank_bonus", note_item.score_breakdown)
        self.assertIn("coverage_hits", note_item.score_breakdown)
        self.assertEqual(note_item.metadata["adapter_name"], "markdown_notes")
        self.assertEqual(note_item.metadata["query_token_count"], 3)
        self.assertEqual(note_item.metadata["title_source"], "heading")
        self.assertEqual(note_item.metadata["chunk_kind"], "markdown_section")
        self.assertEqual(note_item.metadata["line_start"], 1)
        self.assertEqual(note_item.metadata["line_end"], 3)
        self.assertEqual(repo_item.title, "task.py")
        self.assertEqual(repo_item.metadata["adapter_name"], "repo_text")
        self.assertEqual(repo_item.metadata["title_source"], "filename")

    def test_select_retrieval_adapter_uses_source_specific_seam(self) -> None:
        markdown_adapter = select_retrieval_adapter(Path("notes.md"))
        repo_adapter = select_retrieval_adapter(Path("task.py"))
        unsupported_adapter = select_retrieval_adapter(Path("archive.bin"))

        self.assertIsNotNone(markdown_adapter)
        self.assertEqual(markdown_adapter.name, "markdown_notes")
        self.assertEqual(markdown_adapter.source_type, "notes")
        self.assertIsNotNone(repo_adapter)
        self.assertEqual(repo_adapter.name, "repo_text")
        self.assertEqual(repo_adapter.source_type, "repo")
        self.assertIsNone(unsupported_adapter)

    def test_retrieve_context_uses_markdown_sections_for_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text(
                "# Notes\n\n## Build Harness\nretrieval baseline and harness planning\n\n## Grocery\nharness milk eggs\n",
                encoding="utf-8",
            )

            items = retrieve_context(tmp_path, query="retrieval baseline harness", limit=8)

        matching_section = next(item for item in items if item.title == "Build Harness")
        grocery_section = next(item for item in items if item.title == "Grocery")
        self.assertEqual(matching_section.chunk_id, "section-2")
        self.assertEqual(matching_section.citation, "notes.md#L3-L5")
        self.assertEqual(matching_section.metadata["chunk_kind"], "markdown_section")
        self.assertGreater(matching_section.score, grocery_section.score)

    def test_retrieve_context_uses_repo_line_chunks_and_symbol_titles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo_file = tmp_path / "analyze.py"
            filler = "\n".join(f"line_{index} = {index}" for index in range(1, 41))
            repo_file.write_text(
                f"{filler}\n\ndef analyze_context():\n    return 'retrieval baseline context'\n",
                encoding="utf-8",
            )

            items = retrieve_context(tmp_path, query="analyze context retrieval", limit=8)

        target_chunk = next(item for item in items if item.path == "analyze.py" and item.title == "analyze_context")
        self.assertEqual(target_chunk.chunk_id, "lines-41-43")
        self.assertEqual(target_chunk.citation, "analyze.py#L41-L43")
        self.assertEqual(target_chunk.metadata["chunk_kind"], "repo_lines")
        self.assertEqual(target_chunk.metadata["title_source"], "symbol")

    def test_retrieve_context_query_shaping_prefers_phrase_and_coverage_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text(
                "# Retrieval Memory Reuse\n\nretrieval memory reuse baseline for grounding\n\n"
                "# Retrieval\n\nretrieval baseline only\n",
                encoding="utf-8",
            )
            script = tmp_path / "memory_helper.py"
            script.write_text(
                "def retrieval_helper():\n    return 'retrieval memory baseline'\n",
                encoding="utf-8",
            )

            items = retrieve_context(tmp_path, query="the retrieval memory reuse for task", limit=4)

        self.assertGreaterEqual(len(items), 2)
        self.assertEqual(items[0].title, "Retrieval Memory Reuse")
        self.assertEqual(items[0].path, "notes.md")
        self.assertGreater(items[0].score_breakdown["rerank_bonus"], 0)
        self.assertGreater(items[0].score, items[1].score)

    def test_retrieve_context_can_include_task_artifacts_when_explicitly_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_artifacts_dir = tmp_path / ".swl" / "tasks" / "task123" / "artifacts"
            task_artifacts_dir.mkdir(parents=True, exist_ok=True)
            summary = task_artifacts_dir / "summary.md"
            summary.write_text(
                "# Summary\n\nretrieval artifact baseline with route provenance and grounding\n",
                encoding="utf-8",
            )
            memory = tmp_path / ".swl" / "tasks" / "task123" / "memory.json"
            memory.write_text('{"note":"artifact memory baseline"}\n', encoding="utf-8")

            items = retrieve_context(
                tmp_path,
                query="route provenance grounding artifact",
                source_types=[ARTIFACTS_SOURCE_TYPE],
                limit=8,
            )

        self.assertGreaterEqual(len(items), 1)
        artifact_item = next(item for item in items if item.path.endswith("summary.md"))
        self.assertEqual(artifact_item.source_type, ARTIFACTS_SOURCE_TYPE)
        self.assertEqual(artifact_item.metadata["storage_scope"], "task_artifacts")
        self.assertEqual(artifact_item.metadata["artifact_name"], "summary.md")
        self.assertEqual(artifact_item.metadata["adapter_name"], "markdown_notes")

    def test_retrieve_context_excludes_task_artifacts_from_default_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_artifacts_dir = tmp_path / ".swl" / "tasks" / "task123" / "artifacts"
            task_artifacts_dir.mkdir(parents=True, exist_ok=True)
            (task_artifacts_dir / "summary.md").write_text(
                "# Summary\n\nartifact-only retrieval baseline\n",
                encoding="utf-8",
            )
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\nworkspace retrieval baseline\n", encoding="utf-8")

            items = retrieve_context(tmp_path, query="artifact retrieval baseline", limit=8)

        self.assertTrue(all(item.source_type != ARTIFACTS_SOURCE_TYPE for item in items))

    def test_retrieve_context_can_include_verified_knowledge_when_explicitly_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_dir = tmp_path / ".swl" / "tasks" / "task123"
            task_dir.mkdir(parents=True, exist_ok=True)
            (task_dir / "knowledge_objects.json").write_text(
                json.dumps(
                    [
                        {
                            "object_id": "knowledge-0001",
                            "text": "Verified retrieval knowledge should remain reusable and grounded.",
                            "stage": "verified",
                            "source_kind": "external_knowledge_capture",
                            "source_ref": "chat://knowledge-verified",
                            "task_linked": True,
                            "captured_at": "2026-04-08T00:00:00+00:00",
                            "evidence_status": "artifact_backed",
                            "artifact_ref": ".swl/tasks/task123/artifacts/summary.md",
                            "retrieval_eligible": True,
                            "knowledge_reuse_scope": "retrieval_candidate",
                        },
                        {
                            "object_id": "knowledge-0002",
                            "text": "Candidate knowledge should not enter retrieval yet.",
                            "stage": "candidate",
                            "source_kind": "external_knowledge_capture",
                            "source_ref": "chat://knowledge-candidate",
                            "task_linked": True,
                            "captured_at": "2026-04-08T00:00:00+00:00",
                            "evidence_status": "source_only",
                            "artifact_ref": "",
                            "retrieval_eligible": True,
                            "knowledge_reuse_scope": "retrieval_candidate",
                        },
                    ]
                ),
                encoding="utf-8",
            )

            items = retrieve_context(
                tmp_path,
                query="verified retrieval grounded knowledge",
                source_types=[KNOWLEDGE_SOURCE_TYPE],
                limit=8,
            )

        self.assertEqual(len(items), 1)
        knowledge_item = items[0]
        self.assertEqual(knowledge_item.source_type, KNOWLEDGE_SOURCE_TYPE)
        self.assertEqual(knowledge_item.path, ".swl/tasks/task123/knowledge_objects.json")
        self.assertEqual(knowledge_item.chunk_id, "knowledge-0001")
        self.assertEqual(knowledge_item.citation, ".swl/tasks/task123/knowledge_objects.json#knowledge-0001")
        self.assertEqual(knowledge_item.metadata["adapter_name"], "verified_knowledge_records")
        self.assertEqual(knowledge_item.metadata["storage_scope"], "task_knowledge")
        self.assertEqual(knowledge_item.metadata["knowledge_stage"], "verified")
        self.assertEqual(knowledge_item.metadata["knowledge_reuse_scope"], "retrieval_candidate")
        self.assertEqual(knowledge_item.metadata["artifact_ref"], ".swl/tasks/task123/artifacts/summary.md")

    def test_retrieve_context_excludes_verified_knowledge_from_default_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_dir = tmp_path / ".swl" / "tasks" / "task123"
            task_dir.mkdir(parents=True, exist_ok=True)
            (task_dir / "knowledge_objects.json").write_text(
                json.dumps(
                    [
                        {
                            "object_id": "knowledge-0001",
                            "text": "Verified retrieval knowledge should remain opt-in.",
                            "stage": "verified",
                            "source_kind": "external_knowledge_capture",
                            "source_ref": "chat://knowledge-verified",
                            "task_linked": True,
                            "captured_at": "2026-04-08T00:00:00+00:00",
                            "evidence_status": "artifact_backed",
                            "artifact_ref": ".swl/tasks/task123/artifacts/summary.md",
                            "retrieval_eligible": True,
                            "knowledge_reuse_scope": "retrieval_candidate",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            (tmp_path / "notes.md").write_text("# Notes\n\nworkspace retrieval baseline\n", encoding="utf-8")

            items = retrieve_context(tmp_path, query="verified retrieval knowledge", limit=8)

        self.assertTrue(all(item.source_type != KNOWLEDGE_SOURCE_TYPE for item in items))

    def test_retrieve_context_limits_knowledge_reuse_to_current_task_when_history_is_not_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            for task_id, text in [
                ("task123", "Current task verified reusable knowledge."),
                ("task999", "Cross task verified reusable knowledge."),
            ]:
                task_dir = tmp_path / ".swl" / "tasks" / task_id
                task_dir.mkdir(parents=True, exist_ok=True)
                (task_dir / "knowledge_objects.json").write_text(
                    json.dumps(
                        [
                            {
                                "object_id": "knowledge-0001",
                                "text": text,
                                "stage": "verified",
                                "source_kind": "external_knowledge_capture",
                                "source_ref": f"chat://{task_id}",
                                "task_linked": True,
                                "captured_at": "2026-04-09T00:00:00+00:00",
                                "evidence_status": "artifact_backed",
                                "artifact_ref": f".swl/tasks/{task_id}/artifacts/summary.md",
                                "retrieval_eligible": True,
                                "knowledge_reuse_scope": "retrieval_candidate",
                            }
                        ]
                    ),
                    encoding="utf-8",
                )

            items = retrieve_context(
                tmp_path,
                request=RetrievalRequest(
                    query="verified reusable knowledge",
                    source_types=[KNOWLEDGE_SOURCE_TYPE],
                    context_layers=["task"],
                    current_task_id="task123",
                    limit=8,
                    strategy="system_baseline",
                ),
            )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].metadata["knowledge_task_id"], "task123")
        self.assertEqual(items[0].metadata["knowledge_task_relation"], "current_task")

    def test_retrieve_context_can_include_cross_task_knowledge_when_history_is_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            for task_id, text in [
                ("task123", "Current task verified reusable knowledge."),
                ("task999", "Cross task verified reusable knowledge with history boundary."),
            ]:
                task_dir = tmp_path / ".swl" / "tasks" / task_id
                task_dir.mkdir(parents=True, exist_ok=True)
                (task_dir / "knowledge_objects.json").write_text(
                    json.dumps(
                        [
                            {
                                "object_id": "knowledge-0001",
                                "text": text,
                                "stage": "verified",
                                "source_kind": "external_knowledge_capture",
                                "source_ref": f"chat://{task_id}",
                                "task_linked": True,
                                "captured_at": "2026-04-09T00:00:00+00:00",
                                "evidence_status": "artifact_backed",
                                "artifact_ref": f".swl/tasks/{task_id}/artifacts/summary.md",
                                "retrieval_eligible": True,
                                "knowledge_reuse_scope": "retrieval_candidate",
                            }
                        ]
                    ),
                    encoding="utf-8",
                )

            items = retrieve_context(
                tmp_path,
                request=RetrievalRequest(
                    query="history boundary cross task knowledge",
                    source_types=[KNOWLEDGE_SOURCE_TYPE],
                    context_layers=["history"],
                    current_task_id="task123",
                    limit=8,
                    strategy="system_baseline",
                ),
            )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].metadata["knowledge_task_id"], "task999")
        self.assertEqual(items[0].metadata["knowledge_task_relation"], "cross_task")

    def test_retrieve_context_excludes_source_only_verified_knowledge_from_reusable_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_dir = tmp_path / ".swl" / "tasks" / "task123"
            task_dir.mkdir(parents=True, exist_ok=True)
            (task_dir / "knowledge_objects.json").write_text(
                json.dumps(
                    [
                        {
                            "object_id": "knowledge-0001",
                            "text": "Verified source-only knowledge should stay blocked from reusable retrieval.",
                            "stage": "verified",
                            "source_kind": "external_knowledge_capture",
                            "source_ref": "chat://knowledge-verified",
                            "task_linked": True,
                            "captured_at": "2026-04-08T00:00:00+00:00",
                            "evidence_status": "source_only",
                            "artifact_ref": "",
                            "retrieval_eligible": True,
                            "knowledge_reuse_scope": "retrieval_candidate",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            items = retrieve_context(
                tmp_path,
                query="verified source-only reusable knowledge",
                source_types=[KNOWLEDGE_SOURCE_TYPE],
                limit=8,
            )

        self.assertEqual(items, [])

    def test_knowledge_policy_warns_for_source_only_verified_reuse_candidate(self) -> None:
        state = TaskState(
            task_id="knowledgepolicy1",
            title="Knowledge policy",
            goal="Warn on source-only reusable knowledge",
            workspace_root="/tmp",
            knowledge_objects=[
                {
                    "object_id": "knowledge-0001",
                    "text": "Verified source-only knowledge",
                    "stage": "verified",
                    "source_kind": "external_knowledge_capture",
                    "source_ref": "chat://knowledge-verified",
                    "task_linked": True,
                    "captured_at": "2026-04-08T00:00:00+00:00",
                    "evidence_status": "source_only",
                    "artifact_ref": "",
                    "retrieval_eligible": True,
                    "knowledge_reuse_scope": "retrieval_candidate",
                }
            ],
        )

        result = evaluate_knowledge_policy(state)

        self.assertEqual(result.status, "warning")
        self.assertTrue(any(f.code == "knowledge.reuse.verified.blocked_source_only" for f in result.findings))

    def test_knowledge_policy_marks_verified_artifact_backed_canonicalization_intent_ready(self) -> None:
        state = TaskState(
            task_id="knowledgepolicy3",
            title="Canonicalization policy",
            goal="Allow explicit canonicalization review readiness",
            workspace_root="/tmp",
            knowledge_objects=[
                {
                    "object_id": "knowledge-0001",
                    "text": "Verified artifact-backed knowledge can be reviewed for canonical promotion.",
                    "stage": "verified",
                    "source_kind": "external_knowledge_capture",
                    "source_ref": "chat://knowledge-canonical-review",
                    "task_linked": True,
                    "captured_at": "2026-04-08T00:00:00+00:00",
                    "evidence_status": "artifact_backed",
                    "artifact_ref": ".swl/tasks/task123/artifacts/summary.md",
                    "retrieval_eligible": False,
                    "knowledge_reuse_scope": "task_only",
                    "canonicalization_intent": "promote",
                }
            ],
        )

        result = evaluate_knowledge_policy(state)

        self.assertEqual(result.status, "passed")
        self.assertTrue(any(f.code == "knowledge.canonicalization.ready_for_review" for f in result.findings))

    def test_knowledge_policy_warns_when_canonicalization_intent_is_declared_before_verified_stage(self) -> None:
        state = TaskState(
            task_id="knowledgepolicy4",
            title="Canonicalization policy",
            goal="Warn when canonicalization intent arrives too early",
            workspace_root="/tmp",
            knowledge_objects=[
                {
                    "object_id": "knowledge-0001",
                    "text": "Candidate knowledge should not be treated as canonical-ready.",
                    "stage": "candidate",
                    "source_kind": "external_knowledge_capture",
                    "source_ref": "chat://knowledge-canonical-blocked",
                    "task_linked": True,
                    "captured_at": "2026-04-08T00:00:00+00:00",
                    "evidence_status": "artifact_backed",
                    "artifact_ref": ".swl/tasks/task123/artifacts/summary.md",
                    "retrieval_eligible": False,
                    "knowledge_reuse_scope": "task_only",
                    "canonicalization_intent": "review",
                }
            ],
        )

        result = evaluate_knowledge_policy(state)

        self.assertEqual(result.status, "warning")
        self.assertTrue(any(f.code == "knowledge.canonicalization.stage_not_ready" for f in result.findings))

    def test_knowledge_policy_fails_for_non_verified_reuse_candidate(self) -> None:
        state = TaskState(
            task_id="knowledgepolicy2",
            title="Knowledge policy",
            goal="Block non-verified reusable knowledge",
            workspace_root="/tmp",
            knowledge_objects=[
                {
                    "object_id": "knowledge-0001",
                    "text": "Candidate knowledge should not enter reusable retrieval.",
                    "stage": "candidate",
                    "source_kind": "external_knowledge_capture",
                    "source_ref": "chat://knowledge-candidate",
                    "task_linked": True,
                    "captured_at": "2026-04-08T00:00:00+00:00",
                    "evidence_status": "artifact_backed",
                    "artifact_ref": ".swl/tasks/task123/artifacts/summary.md",
                    "retrieval_eligible": True,
                    "knowledge_reuse_scope": "retrieval_candidate",
                }
            ],
        )

        result = evaluate_knowledge_policy(state)

        self.assertEqual(result.status, "failed")
        self.assertTrue(any(f.code == "knowledge.reuse.stage_not_ready" for f in result.findings))

    def test_build_task_retrieval_request_uses_explicit_system_baseline(self) -> None:
        state = TaskState(
            task_id="request123",
            title="Improve retrieval",
            goal="Refine harness boundary",
            workspace_root="/tmp",
        )

        request = build_task_retrieval_request(state)

        self.assertEqual(request.query, "Improve retrieval Refine harness boundary")
        self.assertEqual(request.source_types, ["repo", "notes"])
        self.assertEqual(request.context_layers, ["workspace", "task"])
        self.assertEqual(request.current_task_id, "request123")
        self.assertEqual(request.limit, 8)
        self.assertEqual(request.strategy, "system_baseline")

    def test_run_task_passes_explicit_retrieval_request_to_harness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            created = TaskState(
                task_id="taskrequest",
                title="Request boundary",
                goal="Pass retrieval request explicitly",
                workspace_root=str(base_dir),
            )
            captured_request: dict[str, RetrievalRequest] = {}
            retrieval_items = [
                RetrievalItem(path="notes.md", source_type="notes", score=3, preview="request boundary"),
            ]
            executor_result = ExecutorResult(
                executor_name="mock",
                status="completed",
                message="Execution finished.",
                output="done",
            )

            def run_retrieval_spy(
                _base_dir: Path, _state: TaskState, request: RetrievalRequest
            ) -> list[RetrievalItem]:
                captured_request["request"] = request
                return retrieval_items

            with patch("swallow.orchestrator.load_state", return_value=created):
                with patch("swallow.orchestrator.save_state"):
                    with patch("swallow.orchestrator.append_event"):
                        with patch("swallow.orchestrator.run_retrieval", side_effect=run_retrieval_spy):
                            with patch("swallow.orchestrator._execute_task_card", return_value=executor_result):
                                with patch(
                                    "swallow.orchestrator.write_task_artifacts",
                                    return_value=(
                                        ValidationResult(status="passed", message="Compatibility passed."),
                                        ValidationResult(status="passed", message="Execution fit passed."),
                                        ValidationResult(status="passed", message="Knowledge policy passed."),
                                        ValidationResult(status="passed", message="Validation passed."),
                                        ValidationResult(status="passed", message="Retry policy passed."),
                                        ValidationResult(status="passed", message="Execution budget policy passed."),
                                        ValidationResult(status="warning", message="Stop policy warning."),
                                    ),
                                ):
                                    run_task(base_dir, created.task_id)

        request = captured_request["request"]
        self.assertEqual(request.query, "Request boundary Pass retrieval request explicitly")
        self.assertEqual(request.source_types, ["repo", "notes"])
        self.assertEqual(request.context_layers, ["workspace", "task"])
        self.assertEqual(request.current_task_id, "taskrequest")
        self.assertEqual(request.strategy, "system_baseline")

    def test_run_task_status_and_phase_timing_success_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            created = TaskState(
                task_id="tasksuccess",
                title="Lifecycle success",
                goal="Verify phase timing",
                workspace_root=str(base_dir),
            )

            observed_states: list[tuple[str, str]] = []
            observed_events: list[str] = []

            def save_state_spy(_base_dir: Path, state: TaskState) -> None:
                observed_states.append((state.status, state.phase))

            def append_event_spy(_base_dir: Path, event: Event) -> None:
                observed_events.append(event.event_type)

            retrieval_items = [
                RetrievalItem(path="notes.md", source_type="markdown", score=5, preview="phase timing"),
            ]
            executor_result = ExecutorResult(
                executor_name="mock",
                status="completed",
                message="Execution finished.",
                output="done",
            )
            artifact_states: list[tuple[str, str]] = []

            def write_artifacts_spy(
                _base_dir: Path,
                state: TaskState,
                _retrieval_items: list[RetrievalItem],
                _executor_result: ExecutorResult,
                grounding_evidence_override: dict[str, object] | None = None,
            ) -> tuple[ValidationResult, ValidationResult, ValidationResult, ValidationResult, ValidationResult, ValidationResult]:
                artifact_states.append((state.status, state.phase))
                return (
                    ValidationResult(status="passed", message="Compatibility passed."),
                    ValidationResult(status="passed", message="Execution fit passed."),
                    ValidationResult(status="passed", message="Knowledge policy passed."),
                    ValidationResult(status="passed", message="Validation passed."),
                    ValidationResult(status="passed", message="Retry policy passed."),
                    ValidationResult(status="passed", message="Execution budget policy passed."),
                    ValidationResult(status="warning", message="Stop policy warning."),
                )

            with patch("swallow.orchestrator.load_state", return_value=created):
                with patch("swallow.orchestrator.save_state", side_effect=save_state_spy):
                    with patch("swallow.orchestrator.append_event", side_effect=append_event_spy):
                        with patch("swallow.orchestrator.run_retrieval", return_value=retrieval_items):
                            with patch("swallow.orchestrator._execute_task_card", return_value=executor_result):
                                with patch("swallow.orchestrator.write_task_artifacts", side_effect=write_artifacts_spy):
                                    final_state = run_task(base_dir, created.task_id)

        self.assertEqual(
            observed_states,
            [
                ("running", "intake"),
                ("running", "retrieval"),
                ("running", "retrieval"),
                ("running", "retrieval"),
                ("running", "retrieval"),
                ("running", "executing"),
                ("running", "executing"),
                ("running", "executing"),
                ("running", "summarize"),
                ("running", "summarize"),
                ("completed", "summarize"),
                ("completed", "summarize"),
            ],
        )
        self.assertEqual(artifact_states, [("running", "summarize")])
        self.assertEqual(
            observed_events,
            [
                "task.run_started",
                "task.planned",
                "task.phase",
                "grounding.locked",
                "task.phase_checkpoint",
                "task.phase",
                "task.review_gate",
                "task.phase_checkpoint",
                "task.phase",
                "task.phase_checkpoint",
                "task.completed",
            ],
        )
        self.assertEqual(final_state.status, "completed")
        self.assertEqual(final_state.phase, "summarize")

    def test_run_task_enforces_validator_capabilities_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            created = TaskState(
                task_id="capenforce-validator",
                title="Validator enforce",
                goal="Downgrade route capabilities before execution",
                workspace_root=str(base_dir),
                executor_name="local",
            )
            validator_route = RouteSelection(
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
                        memory_authority="task-state",
                    ),
                ),
                reason="Test-only validator route for capability enforcement.",
                policy_inputs={},
            )
            captured_states: list[TaskState] = []

            def execute_task_card_spy(
                _base_dir: Path,
                state: TaskState,
                _card: TaskCard,
                _retrieval_items: list[RetrievalItem],
            ) -> ExecutorResult:
                captured_states.append(state)
                return ExecutorResult(
                    executor_name="local",
                    status="completed",
                    message="Execution finished.",
                    output="done",
                )

            with patch("swallow.orchestrator.load_state", return_value=created):
                with patch("swallow.orchestrator.select_route", return_value=validator_route):
                    with patch("swallow.orchestrator.save_state"):
                        with patch("swallow.orchestrator.append_event"):
                            with patch("swallow.orchestrator.run_retrieval", return_value=[]):
                                with patch("swallow.orchestrator._execute_task_card", side_effect=execute_task_card_spy):
                                    with patch(
                                        "swallow.orchestrator.write_task_artifacts",
                                        return_value=(
                                            ValidationResult(status="passed", message="Compatibility passed."),
                                            ValidationResult(status="passed", message="Execution fit passed."),
                                            ValidationResult(status="passed", message="Knowledge policy passed."),
                                            ValidationResult(status="passed", message="Validation passed."),
                                            ValidationResult(status="passed", message="Retry policy passed."),
                                            ValidationResult(status="passed", message="Execution budget policy passed."),
                                            ValidationResult(status="warning", message="Stop policy warning."),
                                        ),
                                    ):
                                        final_state = run_task(base_dir, created.task_id, executor_name="local")

        self.assertEqual(final_state.route_capabilities["filesystem_access"], "workspace_read")
        self.assertEqual(final_state.route_capabilities["supports_tool_loop"], False)
        self.assertEqual(final_state.route_capabilities["network_access"], "optional")
        self.assertEqual(captured_states[0].route_capabilities["filesystem_access"], "workspace_read")
        self.assertEqual(captured_states[0].route_capabilities["supports_tool_loop"], False)

    def test_run_task_records_capability_enforcement_event_for_validator_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            created = create_task(
                base_dir=base_dir,
                title="Capability event",
                goal="Record enforcement event for validator route",
                workspace_root=base_dir,
            )
            validator_route = RouteSelection(
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
                        memory_authority="task-state",
                    ),
                ),
                reason="Test-only validator route for enforcement event.",
                policy_inputs={},
            )

            with patch("swallow.orchestrator.select_route", return_value=validator_route):
                with patch("swallow.orchestrator.run_retrieval", return_value=[]):
                    with patch(
                        "swallow.orchestrator._execute_task_card",
                        return_value=ExecutorResult(
                            executor_name="local",
                            status="completed",
                            message="Execution finished.",
                            output="done",
                        ),
                    ):
                        with patch(
                            "swallow.orchestrator.write_task_artifacts",
                            return_value=(
                                ValidationResult(status="passed", message="Compatibility passed."),
                                ValidationResult(status="passed", message="Execution fit passed."),
                                ValidationResult(status="passed", message="Knowledge policy passed."),
                                ValidationResult(status="passed", message="Validation passed."),
                                ValidationResult(status="passed", message="Retry policy passed."),
                                ValidationResult(status="passed", message="Execution budget policy passed."),
                                ValidationResult(status="warning", message="Stop policy warning."),
                            ),
                        ):
                            self.assertEqual(run_task(base_dir, created.task_id, executor_name="local").status, "completed")

            events = [
                json.loads(line)
                for line in (base_dir / ".swl" / "tasks" / created.task_id / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        enforced_event = next(event for event in events if event["event_type"] == "task.capability_enforced")
        self.assertEqual(enforced_event["payload"]["taxonomy_role"], "validator")
        self.assertEqual(enforced_event["payload"]["taxonomy_memory_authority"], "task-state")
        self.assertEqual(enforced_event["payload"]["original_route_capabilities"]["filesystem_access"], "workspace_write")
        self.assertEqual(enforced_event["payload"]["enforced_route_capabilities"]["filesystem_access"], "workspace_read")

    def test_run_task_keeps_general_executor_capabilities_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            created = TaskState(
                task_id="capenforce-general",
                title="General executor preserve",
                goal="Do not downgrade default general executor capabilities",
                workspace_root=str(base_dir),
                executor_name="codex",
            )
            captured_states: list[TaskState] = []

            def execute_task_card_spy(
                _base_dir: Path,
                state: TaskState,
                _card: TaskCard,
                _retrieval_items: list[RetrievalItem],
            ) -> ExecutorResult:
                captured_states.append(state)
                return ExecutorResult(
                    executor_name="codex",
                    status="completed",
                    message="Execution finished.",
                    output="done",
                )

            with patch("swallow.orchestrator.load_state", return_value=created):
                with patch("swallow.orchestrator.save_state"):
                    with patch("swallow.orchestrator.append_event"):
                        with patch("swallow.orchestrator.run_retrieval", return_value=[]):
                            with patch("swallow.orchestrator._execute_task_card", side_effect=execute_task_card_spy):
                                with patch(
                                    "swallow.orchestrator.write_task_artifacts",
                                    return_value=(
                                        ValidationResult(status="passed", message="Compatibility passed."),
                                        ValidationResult(status="passed", message="Execution fit passed."),
                                        ValidationResult(status="passed", message="Knowledge policy passed."),
                                        ValidationResult(status="passed", message="Validation passed."),
                                        ValidationResult(status="passed", message="Retry policy passed."),
                                        ValidationResult(status="passed", message="Execution budget policy passed."),
                                        ValidationResult(status="warning", message="Stop policy warning."),
                                    ),
                                ):
                                    final_state = run_task(base_dir, created.task_id, executor_name="codex")

        self.assertEqual(final_state.route_capabilities["filesystem_access"], "workspace_write")
        self.assertEqual(final_state.route_capabilities["supports_tool_loop"], True)
        self.assertEqual(final_state.route_capabilities["network_access"], "optional")
        self.assertEqual(captured_states[0].route_capabilities["filesystem_access"], "workspace_write")
        self.assertEqual(captured_states[0].route_capabilities["supports_tool_loop"], True)

    def test_run_task_does_not_record_capability_enforcement_event_for_general_executor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            created = create_task(
                base_dir=base_dir,
                title="No capability event",
                goal="Do not record enforcement event for default route",
                workspace_root=base_dir,
                executor_name="codex",
            )

            with patch("swallow.orchestrator.run_retrieval", return_value=[]):
                with patch(
                    "swallow.orchestrator._execute_task_card",
                    return_value=ExecutorResult(
                        executor_name="codex",
                        status="completed",
                        message="Execution finished.",
                        output="done",
                    ),
                ):
                    with patch(
                        "swallow.orchestrator.write_task_artifacts",
                        return_value=(
                            ValidationResult(status="passed", message="Compatibility passed."),
                            ValidationResult(status="passed", message="Execution fit passed."),
                            ValidationResult(status="passed", message="Knowledge policy passed."),
                            ValidationResult(status="passed", message="Validation passed."),
                            ValidationResult(status="passed", message="Retry policy passed."),
                            ValidationResult(status="passed", message="Execution budget policy passed."),
                            ValidationResult(status="warning", message="Stop policy warning."),
                        ),
                    ):
                        self.assertEqual(run_task(base_dir, created.task_id, executor_name="codex").status, "completed")

            events = [
                json.loads(line)
                for line in (base_dir / ".swl" / "tasks" / created.task_id / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertFalse(any(event["event_type"] == "task.capability_enforced" for event in events))

    def test_run_task_status_and_phase_timing_failure_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            created = TaskState(
                task_id="taskfail",
                title="Lifecycle failure",
                goal="Verify failure timing",
                workspace_root=str(base_dir),
            )

            observed_states: list[tuple[str, str]] = []
            observed_events: list[str] = []

            def save_state_spy(_base_dir: Path, state: TaskState) -> None:
                observed_states.append((state.status, state.phase))

            def append_event_spy(_base_dir: Path, event: Event) -> None:
                observed_events.append(event.event_type)

            retrieval_items = [
                RetrievalItem(path="notes.md", source_type="markdown", score=3, preview="failure timing"),
            ]
            executor_result = ExecutorResult(
                executor_name="codex",
                status="failed",
                message="Execution failed.",
                output="failed",
                failure_kind="timeout",
            )
            artifact_states: list[tuple[str, str]] = []

            def write_artifacts_spy(
                _base_dir: Path,
                state: TaskState,
                _retrieval_items: list[RetrievalItem],
                _executor_result: ExecutorResult,
                grounding_evidence_override: dict[str, object] | None = None,
            ) -> tuple[ValidationResult, ValidationResult, ValidationResult, ValidationResult, ValidationResult, ValidationResult]:
                artifact_states.append((state.status, state.phase))
                return (
                    ValidationResult(status="passed", message="Compatibility passed."),
                    ValidationResult(status="passed", message="Execution fit passed."),
                    ValidationResult(status="passed", message="Knowledge policy passed."),
                    ValidationResult(status="passed", message="Validation passed."),
                    ValidationResult(status="warning", message="Retry policy warning."),
                    ValidationResult(status="warning", message="Execution budget policy warning."),
                    ValidationResult(status="warning", message="Stop policy warning."),
                )

            with patch("swallow.orchestrator.load_state", return_value=created):
                with patch("swallow.orchestrator.save_state", side_effect=save_state_spy):
                    with patch("swallow.orchestrator.append_event", side_effect=append_event_spy):
                        with patch("swallow.orchestrator.run_retrieval", return_value=retrieval_items):
                            with patch("swallow.orchestrator._execute_task_card", return_value=executor_result):
                                with patch("swallow.orchestrator.write_task_artifacts", side_effect=write_artifacts_spy):
                                    final_state = run_task(base_dir, created.task_id)

        self.assertEqual(
            observed_states,
            [
                ("running", "intake"),
                ("running", "retrieval"),
                ("running", "retrieval"),
                ("running", "retrieval"),
                ("running", "retrieval"),
                ("running", "executing"),
                ("running", "executing"),
                ("running", "executing"),
                ("running", "executing"),
                ("running", "summarize"),
                ("running", "summarize"),
                ("failed", "summarize"),
                ("failed", "summarize"),
            ],
        )
        self.assertEqual(artifact_states, [("running", "summarize")])
        self.assertEqual(
            observed_events,
            [
                "task.run_started",
                "task.planned",
                "task.phase",
                "grounding.locked",
                "task.phase_checkpoint",
                "task.phase",
                "task.execution_fallback",
                "task.review_gate",
                "task.phase_checkpoint",
                "task.phase",
                "task.phase_checkpoint",
                "task.failed",
            ],
        )
        self.assertEqual(final_state.status, "failed")
        self.assertEqual(final_state.route_name, "local-summary")
        self.assertEqual(final_state.phase, "summarize")

    def test_run_task_routes_promote_intent_knowledge_to_staged_for_canonical_forbidden_route(self) -> None:
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

            with patch("swallow.orchestrator.select_route", return_value=restricted_route):
                with patch("swallow.orchestrator.run_retrieval", return_value=[]):
                    with patch(
                        "swallow.orchestrator._execute_task_card",
                        return_value=ExecutorResult(
                            executor_name="note-only",
                            status="completed",
                            message="Execution finished.",
                            output="done",
                        ),
                    ):
                        with patch("swallow.orchestrator.write_task_artifacts", side_effect=write_artifacts_side_effect):
                            final_state = run_task(tmp_path, created.task_id, executor_name="local")

            staged_records = [
                json.loads(line)
                for line in (tmp_path / ".swl" / "staged_knowledge" / "registry.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            events = [
                json.loads(line)
                for line in (tmp_path / ".swl" / "tasks" / created.task_id / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(final_state.status, "completed")
        self.assertEqual(final_state.route_taxonomy_memory_authority, "canonical-write-forbidden")
        self.assertEqual(len(staged_records), 1)
        self.assertEqual(staged_records[0]["source_task_id"], created.task_id)
        self.assertEqual(staged_records[0]["source_object_id"], "knowledge-0001")
        self.assertEqual(staged_records[0]["taxonomy_role"], "specialist")
        self.assertEqual(staged_records[0]["taxonomy_memory_authority"], "canonical-write-forbidden")
        self.assertEqual(staged_records[0]["status"], "pending")
        self.assertTrue(any(event["event_type"] == "task.knowledge_staged" for event in events))
        self.assertEqual(events[-1]["payload"]["staged_candidate_count"], 1)

    def test_run_task_keeps_task_state_route_off_staged_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            created = create_task(
                base_dir=tmp_path,
                title="Default knowledge path",
                goal="Keep verified knowledge on the normal path",
                workspace_root=tmp_path,
                executor_name="local",
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
                            "text": "Default routes should not auto-stage this object.",
                            "stage": "verified",
                            "source_kind": "external_knowledge_capture",
                            "source_ref": "chat://default-route",
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

            with patch("swallow.orchestrator.run_retrieval", return_value=[]):
                with patch(
                    "swallow.orchestrator._execute_task_card",
                    return_value=ExecutorResult(
                        executor_name="local",
                        status="completed",
                        message="Execution finished.",
                        output="done",
                    ),
                ):
                    with patch("swallow.orchestrator.write_task_artifacts", side_effect=write_artifacts_side_effect):
                        final_state = run_task(tmp_path, created.task_id, executor_name="local")

            staged_registry = tmp_path / ".swl" / "staged_knowledge" / "registry.jsonl"
            events = [
                json.loads(line)
                for line in (tmp_path / ".swl" / "tasks" / created.task_id / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(final_state.status, "completed")
        self.assertEqual(final_state.route_taxonomy_memory_authority, "task-state")
        self.assertFalse(staged_registry.exists())
        self.assertFalse(any(event["event_type"] == "task.knowledge_staged" for event in events))
        self.assertEqual(events[-1]["payload"]["staged_candidate_count"], 0)

    def test_task_lifecycle_events_and_final_state_are_ordered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\nordered lifecycle\n", encoding="utf-8")

            with patch.dict("os.environ", {"AIWF_EXECUTOR_MODE": "mock"}, clear=False):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "task",
                            "create",
                            "--title",
                            "Ordered lifecycle",
                            "--goal",
                            "Check persisted phase ordering",
                            "--workspace-root",
                            str(tmp_path),
                        ]
                    ),
                    0,
                )
                task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)

                task_dir = tmp_path / ".swl" / "tasks" / task_id
                state = json.loads((task_dir / "state.json").read_text(encoding="utf-8"))
                events = [
                    json.loads(line)
                    for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]

        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["phase"], "summarize")
        self.assertEqual(
            [event["event_type"] for event in events],
            [
                "task.created",
                "task.run_started",
                "task.planned",
                "task.phase",
                "retrieval.completed",
                "grounding.locked",
                "task.phase_checkpoint",
                "task.phase",
                "executor.completed",
                "task.review_gate",
                "task.phase_checkpoint",
                "task.phase",
                "compatibility.completed",
                "execution_fit.completed",
                "knowledge_policy.completed",
                "validation.completed",
                "retry_policy.completed",
                "execution_budget_policy.completed",
                "stop_policy.completed",
                "checkpoint_snapshot.completed",
                "artifacts.written",
                "task.phase_checkpoint",
                "task.completed",
            ],
        )
        planned_event = next(event for event in events if event["event_type"] == "task.planned")
        review_gate_event = next(event for event in events if event["event_type"] == "task.review_gate")
        self.assertEqual(planned_event["payload"]["card_count"], 1)
        self.assertEqual(planned_event["payload"]["parent_task_id"], task_id)
        self.assertEqual(review_gate_event["payload"]["status"], "passed")
        self.assertFalse(review_gate_event["payload"]["skipped_execution"])
        self.assertEqual(events[0]["payload"]["status"], "created")
        self.assertEqual(events[0]["payload"]["phase"], "intake")
        self.assertEqual(events[0]["payload"]["route_name"], "local-mock")
        self.assertEqual(events[0]["payload"]["route_backend"], "deterministic_test")
        self.assertEqual(events[0]["payload"]["route_executor_family"], "cli")
        self.assertEqual(events[0]["payload"]["route_execution_site"], "local")
        self.assertEqual(events[0]["payload"]["route_remote_capable"], False)
        self.assertEqual(events[0]["payload"]["route_transport_kind"], "local_process")
        self.assertEqual(events[0]["payload"]["topology_route_name"], "local-mock")
        self.assertEqual(events[0]["payload"]["topology_executor_family"], "cli")
        self.assertEqual(events[0]["payload"]["topology_execution_site"], "local")
        self.assertEqual(events[0]["payload"]["topology_transport_kind"], "local_process")
        self.assertEqual(events[0]["payload"]["topology_remote_capable_intent"], False)
        self.assertEqual(events[0]["payload"]["topology_dispatch_status"], "not_requested")
        self.assertEqual(events[0]["payload"]["execution_site_contract_kind"], "local_inline")
        self.assertEqual(events[0]["payload"]["execution_site_boundary"], "same_process")
        self.assertEqual(events[0]["payload"]["execution_site_contract_status"], "active")
        self.assertEqual(events[0]["payload"]["execution_site_handoff_required"], False)
        self.assertEqual(events[0]["payload"]["execution_lifecycle"], "idle")
        self.assertNotIn("attempt_owner_kind", events[0]["payload"])
        self.assertEqual(events[1]["payload"]["previous_status"], "created")
        self.assertEqual(events[1]["payload"]["previous_phase"], "intake")
        self.assertEqual(events[1]["payload"]["status"], "running")
        self.assertEqual(events[1]["payload"]["phase"], "intake")
        self.assertEqual(events[1]["payload"]["route_name"], "local-mock")
        self.assertEqual(events[1]["payload"]["route_backend"], "deterministic_test")
        self.assertEqual(events[1]["payload"]["route_executor_family"], "cli")
        self.assertEqual(events[1]["payload"]["route_execution_site"], "local")
        self.assertEqual(events[1]["payload"]["route_remote_capable"], False)
        self.assertEqual(events[1]["payload"]["route_transport_kind"], "local_process")
        self.assertEqual(events[1]["payload"]["attempt_id"], "attempt-0001")
        self.assertEqual(events[1]["payload"]["attempt_number"], 1)
        self.assertEqual(events[1]["payload"]["attempt_owner_kind"], "local_orchestrator")
        self.assertEqual(events[1]["payload"]["attempt_owner_ref"], "swl_cli")
        self.assertEqual(events[1]["payload"]["attempt_ownership_status"], "owned")
        self.assertTrue(bool(events[1]["payload"]["attempt_owner_assigned_at"]))
        self.assertEqual(events[1]["payload"]["attempt_transfer_reason"], "")
        self.assertEqual(events[1]["payload"]["topology_route_name"], "local-mock")
        self.assertEqual(events[1]["payload"]["topology_executor_family"], "cli")
        self.assertEqual(events[1]["payload"]["topology_execution_site"], "local")
        self.assertEqual(events[1]["payload"]["topology_transport_kind"], "local_process")
        self.assertEqual(events[1]["payload"]["topology_remote_capable_intent"], False)
        self.assertEqual(events[1]["payload"]["topology_dispatch_status"], "planned")
        self.assertEqual(events[1]["payload"]["execution_site_contract_kind"], "local_inline")
        self.assertEqual(events[1]["payload"]["execution_site_boundary"], "same_process")
        self.assertEqual(events[1]["payload"]["execution_site_contract_status"], "active")
        self.assertEqual(events[1]["payload"]["execution_site_handoff_required"], False)
        self.assertTrue(bool(events[1]["payload"]["dispatch_requested_at"]))
        self.assertEqual(events[1]["payload"]["dispatch_started_at"], "")
        self.assertEqual(events[1]["payload"]["execution_lifecycle"], "prepared")
        self.assertIn("Selected the route from legacy executor mode", events[1]["payload"]["route_reason"])
        self.assertEqual(events[3]["payload"]["phase"], "retrieval")
        self.assertEqual(events[3]["payload"]["status"], "running")
        self.assertEqual(events[3]["payload"]["execution_lifecycle"], "prepared")
        self.assertEqual(events[4]["payload"]["count"], 1)
        self.assertEqual(events[4]["payload"]["query"], "Ordered lifecycle Check persisted phase ordering")
        self.assertEqual(events[4]["payload"]["source_types_requested"], ["repo", "notes"])
        self.assertEqual(events[4]["payload"]["context_layers"], ["workspace", "task"])
        self.assertEqual(events[4]["payload"]["limit"], 8)
        self.assertEqual(events[4]["payload"]["strategy"], "system_baseline")
        self.assertEqual(events[4]["payload"]["top_paths"], ["notes.md"])
        self.assertEqual(events[4]["payload"]["top_citations"], ["notes.md#L1-L3"])
        self.assertEqual(events[4]["payload"]["source_types"], ["notes"])
        self.assertEqual(events[5]["payload"]["grounding_locked"], True)
        self.assertEqual(events[5]["payload"]["grounding_refs"], [])
        self.assertEqual(events[6]["payload"]["execution_phase"], "retrieval_done")
        self.assertEqual(events[6]["payload"]["skipped"], False)
        self.assertEqual(events[7]["payload"]["phase"], "executing")
        self.assertEqual(events[7]["payload"]["execution_lifecycle"], "dispatched")
        self.assertEqual(events[8]["payload"]["status"], "completed")
        self.assertEqual(events[8]["payload"]["executor_name"], "mock")
        self.assertEqual(events[8]["payload"]["route_name"], "local-mock")
        self.assertEqual(events[8]["payload"]["route_backend"], "deterministic_test")
        self.assertEqual(events[8]["payload"]["route_executor_family"], "cli")
        self.assertEqual(events[8]["payload"]["route_execution_site"], "local")
        self.assertEqual(events[8]["payload"]["route_remote_capable"], False)
        self.assertEqual(events[8]["payload"]["route_transport_kind"], "local_process")
        self.assertEqual(events[8]["payload"]["route_capabilities"]["deterministic"], True)
        self.assertEqual(events[8]["payload"]["route_capabilities"]["filesystem_access"], "workspace_read")
        self.assertEqual(events[8]["payload"]["attempt_id"], "attempt-0001")
        self.assertEqual(events[8]["payload"]["attempt_number"], 1)
        self.assertEqual(events[8]["payload"]["attempt_owner_kind"], "local_orchestrator")
        self.assertEqual(events[8]["payload"]["attempt_owner_ref"], "swl_cli")
        self.assertEqual(events[8]["payload"]["attempt_ownership_status"], "owned")
        self.assertTrue(bool(events[8]["payload"]["attempt_owner_assigned_at"]))
        self.assertEqual(events[8]["payload"]["attempt_transfer_reason"], "")
        self.assertEqual(events[8]["payload"]["topology_route_name"], "local-mock")
        self.assertEqual(events[8]["payload"]["topology_executor_family"], "cli")
        self.assertEqual(events[8]["payload"]["topology_execution_site"], "local")
        self.assertEqual(events[8]["payload"]["topology_transport_kind"], "local_process")
        self.assertEqual(events[8]["payload"]["topology_remote_capable_intent"], False)
        self.assertEqual(events[8]["payload"]["topology_dispatch_status"], "local_dispatched")
        self.assertEqual(events[8]["payload"]["execution_site_contract_kind"], "local_inline")
        self.assertEqual(events[8]["payload"]["execution_site_boundary"], "same_process")
        self.assertEqual(events[8]["payload"]["execution_site_contract_status"], "active")
        self.assertEqual(events[8]["payload"]["execution_site_handoff_required"], False)
        self.assertTrue(bool(events[8]["payload"]["dispatch_requested_at"]))
        self.assertTrue(bool(events[8]["payload"]["dispatch_started_at"]))
        self.assertEqual(events[8]["payload"]["execution_lifecycle"], "dispatched")
        self.assertEqual(
            events[8]["payload"]["output_written"],
            [
                "executor_prompt.md",
                "executor_output.md",
                "executor_stdout.txt",
                "executor_stderr.txt",
            ],
        )
        self.assertEqual(events[8]["payload"]["task_family"], "execution")
        self.assertEqual(events[8]["payload"]["logical_model"], "mock")
        self.assertEqual(events[8]["payload"]["physical_route"], "local-mock")
        self.assertGreaterEqual(events[8]["payload"]["latency_ms"], 0)
        self.assertFalse(events[8]["payload"]["degraded"])
        self.assertEqual(events[8]["payload"]["error_code"], "")
        self.assertEqual(events[9]["payload"]["status"], "passed")
        self.assertEqual(events[10]["payload"]["execution_phase"], "execution_done")
        self.assertEqual(events[10]["payload"]["skipped"], False)
        self.assertEqual(events[11]["payload"]["phase"], "summarize")
        self.assertEqual(events[11]["payload"]["execution_lifecycle"], "dispatched")
        self.assertEqual(events[12]["payload"]["status"], "passed")
        self.assertEqual(events[12]["payload"]["finding_counts"], {"pass": 3, "warn": 0, "fail": 0})
        self.assertEqual(events[13]["payload"]["status"], "passed")
        self.assertEqual(events[13]["payload"]["finding_counts"], {"pass": 7, "warn": 0, "fail": 0})
        self.assertEqual(events[14]["payload"]["status"], "passed")
        self.assertEqual(events[14]["payload"]["finding_counts"], {"pass": 1, "warn": 0, "fail": 0})
        self.assertEqual(events[15]["payload"]["status"], "passed")
        self.assertEqual(events[15]["payload"]["finding_counts"], {"pass": 3, "warn": 0, "fail": 0})
        self.assertEqual(events[16]["payload"]["status"], "passed")
        self.assertEqual(events[17]["payload"]["status"], "passed")
        self.assertEqual(events[18]["payload"]["status"], "warning")
        self.assertEqual(events[19]["payload"]["status"], "passed")
        self.assertEqual(events[19]["payload"]["execution_phase"], "analysis_done")
        self.assertEqual(events[20]["payload"]["status"], "completed")
        self.assertTrue(events[20]["payload"]["artifact_paths"]["summary"].endswith("summary.md"))
        self.assertTrue(events[20]["payload"]["artifact_paths"]["resume_note"].endswith("resume_note.md"))
        self.assertTrue(events[20]["payload"]["artifact_paths"]["route_report"].endswith("route_report.md"))
        self.assertTrue(events[20]["payload"]["artifact_paths"]["topology_report"].endswith("topology_report.md"))
        self.assertTrue(events[20]["payload"]["artifact_paths"]["execution_site_report"].endswith("execution_site_report.md"))
        self.assertTrue(events[20]["payload"]["artifact_paths"]["dispatch_report"].endswith("dispatch_report.md"))
        self.assertTrue(events[20]["payload"]["artifact_paths"]["handoff_report"].endswith("handoff_report.md"))
        self.assertTrue(events[20]["payload"]["artifact_paths"]["execution_fit_report"].endswith("execution_fit_report.md"))
        self.assertTrue(
            events[20]["payload"]["artifact_paths"]["compatibility_report"].endswith("compatibility_report.md")
        )
        self.assertTrue(events[20]["payload"]["artifact_paths"]["source_grounding"].endswith("source_grounding.md"))
        self.assertTrue(events[20]["payload"]["artifact_paths"]["grounding_evidence_json"].endswith("grounding_evidence.json"))
        self.assertTrue(events[20]["payload"]["artifact_paths"]["grounding_evidence_report"].endswith("grounding_evidence_report.md"))
        self.assertTrue(events[20]["payload"]["artifact_paths"]["retrieval_report"].endswith("retrieval_report.md"))
        self.assertTrue(events[20]["payload"]["artifact_paths"]["validation_report"].endswith("validation_report.md"))
        self.assertTrue(events[20]["payload"]["artifact_paths"]["task_memory"].endswith("memory.json"))
        self.assertTrue(events[20]["payload"]["artifact_paths"]["knowledge_policy_report"].endswith("knowledge_policy_report.md"))
        self.assertEqual(events[21]["payload"]["execution_phase"], "analysis_done")
        self.assertEqual(events[21]["payload"]["skipped"], False)
        self.assertEqual(events[22]["payload"]["status"], "completed")
        self.assertEqual(events[22]["payload"]["phase"], "summarize")
        self.assertEqual(events[22]["payload"]["retrieval_count"], 1)
        self.assertEqual(events[22]["payload"]["executor_status"], "completed")
        self.assertEqual(events[22]["payload"]["route_name"], "local-mock")
        self.assertEqual(events[22]["payload"]["route_backend"], "deterministic_test")
        self.assertEqual(events[22]["payload"]["route_execution_site"], "local")
        self.assertEqual(events[22]["payload"]["route_remote_capable"], False)
        self.assertEqual(events[22]["payload"]["route_transport_kind"], "local_process")
        self.assertEqual(events[22]["payload"]["attempt_id"], "attempt-0001")
        self.assertEqual(events[22]["payload"]["attempt_number"], 1)
        self.assertEqual(events[22]["payload"]["attempt_owner_kind"], "local_orchestrator")
        self.assertEqual(events[22]["payload"]["attempt_owner_ref"], "swl_cli")
        self.assertEqual(events[22]["payload"]["attempt_ownership_status"], "owned")
        self.assertTrue(bool(events[22]["payload"]["attempt_owner_assigned_at"]))
        self.assertEqual(events[22]["payload"]["attempt_transfer_reason"], "")
        self.assertEqual(events[22]["payload"]["topology_route_name"], "local-mock")
        self.assertEqual(events[22]["payload"]["topology_execution_site"], "local")
        self.assertEqual(events[22]["payload"]["topology_transport_kind"], "local_process")
        self.assertEqual(events[22]["payload"]["topology_remote_capable_intent"], False)
        self.assertEqual(events[22]["payload"]["topology_dispatch_status"], "local_dispatched")
        self.assertEqual(events[22]["payload"]["execution_site_contract_kind"], "local_inline")
        self.assertEqual(events[22]["payload"]["execution_site_boundary"], "same_process")
        self.assertEqual(events[22]["payload"]["execution_site_contract_status"], "active")
        self.assertEqual(events[22]["payload"]["execution_site_handoff_required"], False)
        self.assertTrue(bool(events[22]["payload"]["dispatch_requested_at"]))
        self.assertTrue(bool(events[22]["payload"]["dispatch_started_at"]))
        self.assertEqual(events[22]["payload"]["execution_lifecycle"], "completed")
        self.assertEqual(events[22]["payload"]["compatibility_status"], "passed")
        self.assertEqual(events[22]["payload"]["execution_fit_status"], "passed")
        self.assertEqual(events[22]["payload"]["retry_policy_status"], "passed")
        self.assertEqual(events[22]["payload"]["execution_budget_policy_status"], "passed")
        self.assertEqual(events[22]["payload"]["stop_policy_status"], "warning")
        self.assertEqual(events[22]["payload"]["knowledge_policy_status"], "passed")
        self.assertEqual(events[22]["payload"]["validation_status"], "passed")
        self.assertEqual(events[22]["payload"]["grounding_locked"], True)
        self.assertEqual(events[22]["payload"]["grounding_refs"], [])
        self.assertEqual(events[22]["payload"]["execution_phase"], "analysis_done")
        self.assertTrue(events[22]["payload"]["artifact_paths"]["executor_output"].endswith("executor_output.md"))

    def test_failed_task_events_include_failure_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\nfailed lifecycle\n", encoding="utf-8")

            with patch.dict(
                "os.environ",
                {"AIWF_CODEX_BIN": "definitely-not-a-real-codex-binary", "AIWF_EXECUTOR_MODE": "codex"},
                clear=False,
            ):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "task",
                            "create",
                            "--title",
                            "Failed lifecycle",
                            "--goal",
                            "Check failure event payloads",
                            "--workspace-root",
                            str(tmp_path),
                        ]
                    ),
                    0,
                )
                task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)

                task_dir = tmp_path / ".swl" / "tasks" / task_id
                events = [
                    json.loads(line)
                    for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]

        self.assertEqual(events[-1]["event_type"], "task.completed")
        self.assertEqual(events[1]["event_type"], "task.run_started")
        self.assertEqual(events[1]["payload"]["previous_status"], "created")
        self.assertEqual(events[1]["payload"]["previous_phase"], "intake")
        self.assertEqual(events[1]["payload"]["route_name"], "local-codex")
        self.assertEqual(events[1]["payload"]["route_backend"], "local_cli")
        self.assertEqual(events[1]["payload"]["route_execution_site"], "local")
        self.assertEqual(events[1]["payload"]["route_remote_capable"], False)
        self.assertEqual(events[1]["payload"]["route_transport_kind"], "local_process")
        self.assertEqual(events[1]["payload"]["attempt_id"], "attempt-0001")
        self.assertEqual(events[1]["payload"]["attempt_number"], 1)
        self.assertEqual(events[1]["payload"]["topology_dispatch_status"], "planned")
        self.assertTrue(bool(events[1]["payload"]["dispatch_requested_at"]))
        self.assertEqual(events[1]["payload"]["dispatch_started_at"], "")
        self.assertEqual(events[1]["payload"]["execution_lifecycle"], "prepared")
        self.assertEqual(events[5]["event_type"], "grounding.locked")
        self.assertEqual(events[5]["payload"]["grounding_locked"], True)
        self.assertEqual(events[6]["event_type"], "task.phase_checkpoint")
        self.assertEqual(events[6]["payload"]["execution_phase"], "retrieval_done")
        self.assertEqual(events[7]["event_type"], "task.phase")
        self.assertEqual(events[8]["event_type"], "executor.failed")
        self.assertEqual(events[8]["payload"]["status"], "failed")
        self.assertEqual(events[8]["payload"]["executor_name"], "codex")
        self.assertEqual(events[8]["payload"]["route_name"], "local-codex")
        self.assertEqual(events[8]["payload"]["route_execution_site"], "local")
        self.assertEqual(events[8]["payload"]["attempt_id"], "attempt-0001")
        self.assertEqual(events[8]["payload"]["attempt_number"], 1)
        self.assertEqual(events[8]["payload"]["topology_dispatch_status"], "local_dispatched")
        self.assertTrue(bool(events[8]["payload"]["dispatch_started_at"]))
        self.assertEqual(events[8]["payload"]["execution_lifecycle"], "dispatched")
        self.assertEqual(events[8]["payload"]["failure_kind"], "launch_error")
        self.assertEqual(events[8]["payload"]["task_family"], "execution")
        self.assertEqual(events[8]["payload"]["logical_model"], "codex")
        self.assertEqual(events[8]["payload"]["physical_route"], "local-codex")
        self.assertGreaterEqual(events[8]["payload"]["latency_ms"], 0)
        self.assertFalse(events[8]["payload"]["degraded"])
        self.assertEqual(events[8]["payload"]["error_code"], "launch_error")
        self.assertEqual(events[9]["event_type"], "executor.completed")
        self.assertEqual(events[9]["payload"]["executor_name"], "local")
        self.assertEqual(events[9]["payload"]["route_name"], "local-summary")
        self.assertEqual(events[9]["payload"]["logical_model"], "local")
        self.assertEqual(events[9]["payload"]["physical_route"], "local-summary")
        self.assertGreaterEqual(events[9]["payload"]["latency_ms"], 0)
        self.assertTrue(events[9]["payload"]["degraded"])
        self.assertEqual(events[9]["payload"]["error_code"], "")
        self.assertEqual(events[10]["event_type"], "task.execution_fallback")
        self.assertEqual(events[10]["payload"]["previous_route_name"], "local-codex")
        self.assertEqual(events[10]["payload"]["fallback_route_name"], "local-summary")
        self.assertEqual(events[10]["payload"]["fallback_status"], "completed")
        self.assertGreaterEqual(events[10]["payload"]["latency_ms"], 0)
        self.assertIn("previous_latency_ms", events[10]["payload"])
        self.assertTrue(events[10]["payload"]["degraded"])
        self.assertEqual(events[11]["event_type"], "task.review_gate")
        self.assertEqual(events[11]["payload"]["status"], "passed")
        self.assertEqual(events[12]["event_type"], "task.phase_checkpoint")
        self.assertEqual(events[12]["payload"]["execution_phase"], "execution_done")
        self.assertEqual(events[14]["event_type"], "compatibility.completed")
        self.assertEqual(events[14]["payload"]["status"], "passed")
        self.assertEqual(events[15]["event_type"], "execution_fit.completed")
        self.assertEqual(events[15]["payload"]["status"], "passed")
        self.assertEqual(events[16]["event_type"], "knowledge_policy.completed")
        self.assertEqual(events[16]["payload"]["status"], "passed")
        self.assertEqual(events[17]["event_type"], "validation.completed")
        self.assertEqual(events[17]["payload"]["status"], "passed")
        self.assertEqual(events[18]["event_type"], "retry_policy.completed")
        self.assertEqual(events[18]["payload"]["status"], "passed")
        self.assertEqual(events[19]["event_type"], "execution_budget_policy.completed")
        self.assertEqual(events[19]["payload"]["status"], "passed")
        self.assertEqual(events[20]["event_type"], "stop_policy.completed")
        self.assertEqual(events[20]["payload"]["status"], "warning")
        self.assertEqual(events[21]["event_type"], "checkpoint_snapshot.completed")
        self.assertEqual(events[21]["payload"]["status"], "passed")
        self.assertEqual(events[23]["event_type"], "task.phase_checkpoint")
        self.assertEqual(events[23]["payload"]["execution_phase"], "analysis_done")
        self.assertEqual(events[-1]["payload"]["status"], "completed")
        self.assertEqual(events[-1]["payload"]["phase"], "summarize")
        self.assertEqual(events[-1]["payload"]["executor_status"], "completed")
        self.assertEqual(events[-1]["payload"]["route_name"], "local-summary")
        self.assertEqual(events[-1]["payload"]["route_execution_site"], "local")
        self.assertEqual(events[-1]["payload"]["route_remote_capable"], False)
        self.assertEqual(events[-1]["payload"]["compatibility_status"], "passed")
        self.assertEqual(events[-1]["payload"]["execution_fit_status"], "passed")
        self.assertEqual(events[-1]["payload"]["knowledge_policy_status"], "passed")
        self.assertEqual(events[-1]["payload"]["validation_status"], "passed")
        self.assertEqual(events[-1]["payload"]["retrieval_count"], 1)

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
            executor_name="codex",
            status="failed",
            message="Codex binary not found.",
            output="fallback",
            failure_kind="launch_error",
        )

        note = build_resume_note(state, retrieval_items, executor_result, None, None, None, None, None, None, None)

        self.assertIn("treat this run as incomplete", note)
        self.assertIn("Treat this run as a failed live execution attempt", note)
        self.assertIn("Verify that the Codex binary is installed", note)

    def test_repeat_run_records_attempt_boundary_and_resets_phase_to_intake(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\nrepeat run lifecycle\n", encoding="utf-8")

            with patch.dict(
                "os.environ",
                {"AIWF_CODEX_BIN": "definitely-not-a-real-codex-binary", "AIWF_EXECUTOR_MODE": "codex"},
                clear=False,
            ):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "task",
                            "create",
                            "--title",
                            "Repeat failure",
                            "--goal",
                            "Check rerun",
                            "--workspace-root",
                            str(tmp_path),
                        ]
                    ),
                    0,
                )
                task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)

                task_dir = tmp_path / ".swl" / "tasks" / task_id
                first_state = json.loads((task_dir / "state.json").read_text(encoding="utf-8"))
                first_events = [
                    json.loads(line)
                    for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]

                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)

                final_state = json.loads((task_dir / "state.json").read_text(encoding="utf-8"))
                final_events = [
                    json.loads(line)
                    for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]

        self.assertEqual(first_state["status"], "completed")
        self.assertEqual(first_state["phase"], "summarize")
        self.assertEqual(final_state["status"], "completed")
        self.assertEqual(final_state["phase"], "summarize")
        self.assertEqual(
            [event["event_type"] for event in first_events],
            [
                "task.created",
                "task.run_started",
                "task.planned",
                "task.phase",
                "retrieval.completed",
                "grounding.locked",
                "task.phase_checkpoint",
                "task.phase",
                "executor.failed",
                "executor.completed",
                "task.execution_fallback",
                "task.review_gate",
                "task.phase_checkpoint",
                "task.phase",
                "compatibility.completed",
                "execution_fit.completed",
                "knowledge_policy.completed",
                "validation.completed",
                "retry_policy.completed",
                "execution_budget_policy.completed",
                "stop_policy.completed",
                "checkpoint_snapshot.completed",
                "artifacts.written",
                "task.phase_checkpoint",
                "task.completed",
            ],
        )
        self.assertEqual(
            [event["event_type"] for event in final_events],
            [
                "task.created",
                "task.run_started",
                "task.planned",
                "task.phase",
                "retrieval.completed",
                "grounding.locked",
                "task.phase_checkpoint",
                "task.phase",
                "executor.failed",
                "executor.completed",
                "task.execution_fallback",
                "task.review_gate",
                "task.phase_checkpoint",
                "task.phase",
                "compatibility.completed",
                "execution_fit.completed",
                "knowledge_policy.completed",
                "validation.completed",
                "retry_policy.completed",
                "execution_budget_policy.completed",
                "stop_policy.completed",
                "checkpoint_snapshot.completed",
                "artifacts.written",
                "task.phase_checkpoint",
                "task.completed",
                "task.run_started",
                "task.planned",
                "task.phase",
                "retrieval.completed",
                "grounding.locked",
                "task.phase_checkpoint",
                "task.phase",
                "executor.completed",
                "task.review_gate",
                "task.phase_checkpoint",
                "task.phase",
                "compatibility.completed",
                "execution_fit.completed",
                "knowledge_policy.completed",
                "validation.completed",
                "retry_policy.completed",
                "execution_budget_policy.completed",
                "stop_policy.completed",
                "checkpoint_snapshot.completed",
                "artifacts.written",
                "task.phase_checkpoint",
                "task.completed",
            ],
        )
        second_run_started = final_events[len(first_events)]
        self.assertEqual(second_run_started["payload"]["previous_status"], "completed")
        self.assertEqual(second_run_started["payload"]["previous_phase"], "summarize")
        self.assertEqual(second_run_started["payload"]["status"], "running")
        self.assertEqual(second_run_started["payload"]["phase"], "intake")
        self.assertEqual(first_events[1]["payload"]["attempt_id"], "attempt-0001")
        self.assertEqual(first_events[1]["payload"]["attempt_number"], 1)
        self.assertEqual(first_events[1]["payload"]["execution_lifecycle"], "prepared")
        self.assertEqual(second_run_started["payload"]["attempt_id"], "attempt-0002")
        self.assertEqual(second_run_started["payload"]["attempt_number"], 2)
        self.assertEqual(second_run_started["payload"]["execution_lifecycle"], "prepared")
        self.assertEqual(final_state["run_attempt_count"], 2)
        self.assertEqual(final_state["current_attempt_id"], "attempt-0002")
        self.assertEqual(final_state["current_attempt_number"], 2)
        self.assertEqual(final_state["execution_lifecycle"], "completed")

    def test_run_persists_execution_phase_checkpoints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "notes.md").write_text("# Notes\n\nphase checkpoint\n", encoding="utf-8")

            with patch.dict("os.environ", {"AIWF_EXECUTOR_MODE": "mock"}, clear=False):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "task",
                            "create",
                            "--title",
                            "Phase checkpoints",
                            "--goal",
                            "Persist execution checkpoint truth",
                            "--workspace-root",
                            str(tmp_path),
                        ]
                    ),
                    0,
                )
                task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)

            task_dir = tmp_path / ".swl" / "tasks" / task_id
            state = json.loads((task_dir / "state.json").read_text(encoding="utf-8"))
            checkpoint_snapshot = json.loads((task_dir / "checkpoint_snapshot.json").read_text(encoding="utf-8"))
            events = [
                json.loads(line)
                for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        phase_events = [event for event in events if event["event_type"] == "task.phase_checkpoint"]
        self.assertEqual(state["execution_phase"], "analysis_done")
        self.assertTrue(bool(state["last_phase_checkpoint_at"]))
        self.assertEqual(checkpoint_snapshot["execution_phase"], "analysis_done")
        self.assertTrue(bool(checkpoint_snapshot["last_phase_checkpoint_at"]))
        self.assertEqual(
            [event["payload"]["execution_phase"] for event in phase_events],
            ["retrieval_done", "execution_done", "analysis_done"],
        )
        self.assertEqual([event["payload"]["skipped"] for event in phase_events], [False, False, False])

    def test_rerun_from_execution_reuses_previous_retrieval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "notes.md").write_text("# Notes\n\nselective rerun execution\n", encoding="utf-8")

            with patch.dict("os.environ", {"AIWF_EXECUTOR_MODE": "mock"}, clear=False):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "task",
                            "create",
                            "--title",
                            "Selective execution rerun",
                            "--goal",
                            "Reuse retrieval artifacts",
                            "--workspace-root",
                            str(tmp_path),
                        ]
                    ),
                    0,
                )
                task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)

            executor_result = ExecutorResult(
                executor_name="mock",
                status="completed",
                message="Mock executor rerun completed.",
                output="rerun output",
                prompt="rerun prompt",
                dialect="plain_text",
            )
            with patch("swallow.harness.retrieve_context", side_effect=AssertionError("retrieval should be skipped")):
                with patch("swallow.harness.run_executor", return_value=executor_result) as run_executor_mock:
                    self.assertEqual(
                        main(
                            [
                                "--base-dir",
                                str(tmp_path),
                                "task",
                                "rerun",
                                task_id,
                                "--from-phase",
                                "execution",
                            ]
                        ),
                        0,
                    )

            task_dir = tmp_path / ".swl" / "tasks" / task_id
            state = json.loads((task_dir / "state.json").read_text(encoding="utf-8"))
            events = [
                json.loads(line)
                for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        second_attempt_phase_events = [
            event
            for event in events
            if event["event_type"] == "task.phase_checkpoint" and event["payload"].get("source") in {"previous_retrieval", "live_execution", "live_analysis"}
        ][-3:]
        self.assertEqual(run_executor_mock.call_count, 1)
        self.assertEqual(state["run_attempt_count"], 2)
        self.assertEqual(
            [(event["payload"]["execution_phase"], event["payload"]["skipped"]) for event in second_attempt_phase_events],
            [("retrieval_done", True), ("execution_done", False), ("analysis_done", False)],
        )

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

            with patch("swallow.harness.retrieve_context", side_effect=AssertionError("retrieval should be skipped")):
                with patch("swallow.harness.run_executor", side_effect=AssertionError("execution should be skipped")):
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

    def test_normalize_executor_name_supports_aliases(self) -> None:
        self.assertEqual(normalize_executor_name("local-summary"), "local")
        self.assertEqual(normalize_executor_name("note_only"), "note-only")
        self.assertEqual(normalize_executor_name("unknown-executor"), "codex")

    def test_resolve_dialect_name_prefers_route_hint_and_falls_back_to_plain_text(self) -> None:
        self.assertEqual(resolve_dialect_name("structured_markdown", "codex"), "structured_markdown")
        self.assertEqual(resolve_dialect_name("", "codex"), "codex_fim")
        self.assertEqual(resolve_dialect_name("", "claude-3-5-sonnet"), "claude_xml")
        self.assertEqual(resolve_dialect_name("", "mock"), "plain_text")
        self.assertEqual(resolve_dialect_name("", "unknown-provider"), "plain_text")

    def test_build_formatted_executor_prompt_uses_codex_fim_for_codex_route(self) -> None:
        state = TaskState(
            task_id="dialect123",
            title="Dialect formatting",
            goal="Format executor prompt with provider dialect",
            workspace_root="/tmp",
            route_name="local-codex",
            route_backend="local_cli",
            route_model_hint="codex",
            route_dialect="codex_fim",
            route_capabilities={
                "execution_kind": "code_execution",
                "supports_tool_loop": True,
            },
        )
        retrieval_items = [
            RetrievalItem(
                path="notes.md",
                source_type="notes",
                score=3,
                preview="Dialect-sensitive context preview.",
                citation="notes.md#L1-L2",
                title="Notes",
            )
        ]

        prompt = build_formatted_executor_prompt(state, retrieval_items)

        self.assertTrue(prompt.startswith("<fim_prefix>\n"))
        self.assertIn("<fim_suffix>", prompt)
        self.assertIn("Route: local-codex", prompt)
        self.assertIn("notes.md#L1-L2", prompt)
        self.assertIn("Return a concise execution update", prompt)

    def test_resolve_executor_name_prefers_state_over_legacy_env(self) -> None:
        state = TaskState(
            task_id="executor123",
            title="Executor selection",
            goal="Use explicit task executor",
            workspace_root="/tmp",
            executor_name="local",
        )

        with patch.dict("os.environ", {"AIWF_EXECUTOR_MODE": "mock"}, clear=False):
            self.assertEqual(resolve_executor_name(state), "local")

    def test_create_task_persists_selected_executor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            state = create_task(
                base_dir=base_dir,
                title="Executor persistence",
                goal="Persist selected executor",
                workspace_root=base_dir,
                executor_name="local-summary",
            )

            persisted = json.loads(
                (base_dir / ".swl" / "tasks" / state.task_id / "state.json").read_text(encoding="utf-8")
            )

        self.assertEqual(state.executor_name, "local")
        self.assertEqual(state.route_mode, "auto")
        self.assertEqual(persisted["executor_name"], "local")
        self.assertEqual(persisted["route_mode"], "auto")
        self.assertEqual(persisted["route_name"], "local-summary")
        self.assertEqual(persisted["route_backend"], "local_summary")
        self.assertEqual(persisted["route_execution_site"], "local")
        self.assertEqual(persisted["route_remote_capable"], False)
        self.assertEqual(persisted["route_transport_kind"], "local_process")
        self.assertEqual(persisted["route_taxonomy_role"], "general-executor")
        self.assertEqual(persisted["route_taxonomy_memory_authority"], "task-state")
        self.assertEqual(persisted["route_capabilities"]["execution_kind"], "artifact_generation")

    def test_create_task_persists_route_dialect_for_default_codex_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            state = create_task(
                base_dir=base_dir,
                title="Route dialect",
                goal="Persist route dialect on create",
                workspace_root=base_dir,
            )

            persisted = json.loads(
                (base_dir / ".swl" / "tasks" / state.task_id / "state.json").read_text(encoding="utf-8")
            )

        self.assertEqual(state.route_name, "local-codex")
        self.assertEqual(state.route_dialect, "codex_fim")
        self.assertEqual(persisted["route_dialect"], "codex_fim")

    def test_select_route_uses_override_before_legacy_mode(self) -> None:
        state = TaskState(
            task_id="route123",
            title="Route selection",
            goal="Prefer explicit route selection",
            workspace_root="/tmp",
            executor_name="codex",
        )

        with patch.dict("os.environ", {"AIWF_EXECUTOR_MODE": "mock"}, clear=False):
            selection = select_route(state, executor_override="local")

        self.assertEqual(selection.route.name, "local-summary")
        self.assertEqual(selection.route.executor_name, "local")
        self.assertEqual(selection.route.execution_site, "local")
        self.assertEqual(selection.route.remote_capable, False)
        self.assertEqual(selection.route.transport_kind, "local_process")
        self.assertEqual(selection.route.taxonomy.system_role, "general-executor")
        self.assertEqual(selection.route.taxonomy.memory_authority, "task-state")
        self.assertEqual(selection.route.capabilities.filesystem_access, "workspace_read")
        self.assertIn("run-time executor override", selection.reason)

    def test_select_route_uses_legacy_mode_when_task_stays_default(self) -> None:
        state = TaskState(
            task_id="route124",
            title="Route selection",
            goal="Use legacy mode only for default tasks",
            workspace_root="/tmp",
            executor_name="codex",
        )

        with patch.dict("os.environ", {"AIWF_EXECUTOR_MODE": "mock"}, clear=False):
            selection = select_route(state)

        self.assertEqual(selection.route.name, "local-mock")
        self.assertEqual(selection.route.backend_kind, "deterministic_test")
        self.assertEqual(selection.route.execution_site, "local")
        self.assertEqual(selection.route.remote_capable, False)
        self.assertEqual(selection.route.taxonomy.system_role, "general-executor")
        self.assertEqual(selection.route.taxonomy.memory_authority, "task-state")
        self.assertEqual(selection.route.capabilities.deterministic, True)

    def test_select_route_uses_route_mode_when_no_executor_override_is_present(self) -> None:
        state = TaskState(
            task_id="route125",
            title="Route selection",
            goal="Use route mode policy inputs",
            workspace_root="/tmp",
            executor_name="codex",
            route_mode="deterministic",
        )

        selection = select_route(state)

        self.assertEqual(selection.route.name, "local-mock")
        self.assertEqual(selection.route.capabilities.execution_kind, "artifact_generation")
        self.assertIn("routing policy mode", selection.reason)

    def test_select_route_builds_detached_local_variant_from_route_mode(self) -> None:
        state = TaskState(
            task_id="route126",
            title="Detached route selection",
            goal="Use detached local transport",
            workspace_root="/tmp",
            executor_name="local",
            route_mode="detached",
        )

        selection = select_route(state)

        self.assertEqual(selection.route.name, "local-summary-detached")
        self.assertEqual(selection.route.executor_name, "local")
        self.assertEqual(selection.route.execution_site, "local")
        self.assertEqual(selection.route.transport_kind, "local_detached_process")
        self.assertEqual(selection.route.backend_kind, "local_summary_detached")
        self.assertEqual(selection.route.taxonomy.system_role, "general-executor")
        self.assertEqual(selection.route.taxonomy.memory_authority, "task-state")
        self.assertIn("detached local execution variant", selection.reason)

    def test_select_route_assigns_specialist_taxonomy_to_local_note(self) -> None:
        state = TaskState(
            task_id="route127",
            title="Specialist route selection",
            goal="Use offline specialist route",
            workspace_root="/tmp",
            executor_name="note-only",
            route_mode="offline",
        )

        selection = select_route(state)

        self.assertEqual(selection.route.name, "local-note")
        self.assertEqual(selection.route.taxonomy.system_role, "specialist")
        self.assertEqual(selection.route.taxonomy.memory_authority, "task-memory")

    def test_compatibility_reports_warning_for_live_route_without_network(self) -> None:
        state = TaskState(
            task_id="compatwarn",
            title="Compatibility warning",
            goal="Surface compatibility warnings",
            workspace_root="/tmp",
            executor_name="codex",
            route_mode="live",
            route_name="local-codex",
            route_backend="local_cli",
            route_capabilities={
                "execution_kind": "code_execution",
                "supports_tool_loop": True,
                "filesystem_access": "workspace_write",
                "network_access": "none",
                "deterministic": False,
                "resumable": True,
            },
        )
        executor_result = ExecutorResult(
            executor_name="codex",
            status="completed",
            message="Execution finished.",
            output="done",
        )

        result = evaluate_route_compatibility(state, executor_result)
        report = build_compatibility_report(result)

        self.assertEqual(result.status, "warning")
        self.assertIn("[warn] route_mode.live.network_limited", report)

    def test_compatibility_reports_failure_for_deterministic_mode_mismatch(self) -> None:
        state = TaskState(
            task_id="compatfail",
            title="Compatibility failure",
            goal="Block route-policy mismatches",
            workspace_root="/tmp",
            executor_name="codex",
            route_mode="deterministic",
            route_name="local-codex",
            route_backend="local_cli",
            route_capabilities={
                "execution_kind": "code_execution",
                "supports_tool_loop": True,
                "filesystem_access": "workspace_write",
                "network_access": "optional",
                "deterministic": False,
                "resumable": True,
            },
        )
        executor_result = ExecutorResult(
            executor_name="codex",
            status="completed",
            message="Execution finished.",
            output="done",
        )

        result = evaluate_route_compatibility(state, executor_result)

        self.assertEqual(result.status, "failed")
        self.assertTrue(any(finding.code == "route_mode.deterministic.missing" for finding in result.findings))

    def test_execution_fit_reports_pass_for_local_dispatched_baseline(self) -> None:
        state = TaskState(
            task_id="fitpass",
            title="Execution fit pass",
            goal="Check local execution-fit baseline",
            workspace_root="/tmp",
            executor_name="mock",
            route_name="local-mock",
            route_executor_family="cli",
            route_execution_site="local",
            route_transport_kind="local_process",
            topology_route_name="local-mock",
            topology_executor_family="cli",
            topology_execution_site="local",
            topology_transport_kind="local_process",
            topology_dispatch_status="local_dispatched",
            current_attempt_id="attempt-0001",
            current_attempt_number=1,
            dispatch_requested_at="2026-04-08T00:00:00+00:00",
            dispatch_started_at="2026-04-08T00:00:01+00:00",
            execution_lifecycle="dispatched",
        )
        executor_result = ExecutorResult(
            executor_name="mock",
            status="completed",
            message="Execution finished.",
            output="done",
        )

        result = evaluate_execution_fit(state, executor_result)
        report = build_execution_fit_report(result)

        self.assertEqual(result.status, "passed")
        self.assertTrue(any(finding.code == "executor_family.route_topology_aligned" for finding in result.findings))
        self.assertTrue(any(finding.code == "executor_family.cli_supported" for finding in result.findings))
        self.assertIn("Execution Fit Report", report)

    def test_execution_fit_reports_failure_for_inconsistent_local_dispatch(self) -> None:
        state = TaskState(
            task_id="fitfail",
            title="Execution fit fail",
            goal="Catch inconsistent dispatch state",
            workspace_root="/tmp",
            executor_name="mock",
            route_name="local-mock",
            route_executor_family="cli",
            route_execution_site="local",
            route_transport_kind="local_process",
            topology_route_name="local-mock",
            topology_executor_family="cli",
            topology_execution_site="local",
            topology_transport_kind="local_process",
            topology_dispatch_status="planned",
            current_attempt_id="attempt-0001",
            current_attempt_number=1,
            dispatch_requested_at="2026-04-08T00:00:00+00:00",
            dispatch_started_at="",
            execution_lifecycle="prepared",
        )
        executor_result = ExecutorResult(
            executor_name="mock",
            status="completed",
            message="Execution finished.",
            output="done",
        )

        result = evaluate_execution_fit(state, executor_result)

        self.assertEqual(result.status, "failed")

    def test_execution_fit_reports_failure_for_unsupported_api_executor_family(self) -> None:
        state = TaskState(
            task_id="fitfamilyfail",
            title="Execution fit family failure",
            goal="Reject unsupported executor family",
            workspace_root="/tmp",
            executor_name="mock",
            route_name="api-simulated",
            route_executor_family="api",
            route_execution_site="local",
            route_transport_kind="local_process",
            topology_route_name="api-simulated",
            topology_executor_family="api",
            topology_execution_site="local",
            topology_transport_kind="local_process",
            topology_dispatch_status="local_dispatched",
            current_attempt_id="attempt-0001",
            current_attempt_number=1,
            dispatch_requested_at="2026-04-08T00:00:00+00:00",
            dispatch_started_at="2026-04-08T00:00:01+00:00",
            execution_lifecycle="dispatched",
        )
        executor_result = ExecutorResult(
            executor_name="mock",
            status="completed",
            message="Execution finished.",
            output="done",
        )

        result = evaluate_execution_fit(state, executor_result)

        self.assertEqual(result.status, "failed")
        self.assertTrue(any(finding.code == "executor_family.unsupported" for finding in result.findings))

    def test_validator_reports_warning_when_retrieval_is_empty(self) -> None:
        state = TaskState(
            task_id="warn123",
            title="Validator warning",
            goal="Allow warning outcomes",
            workspace_root="/tmp",
            phase="summarize",
        )
        executor_result = ExecutorResult(
            executor_name="local",
            status="completed",
            message="Execution finished.",
            output="done",
        )
        artifact_paths = {
            "executor_prompt": __file__,
            "executor_output": __file__,
            "executor_stdout": __file__,
            "executor_stderr": __file__,
            "summary": __file__,
            "resume_note": __file__,
            "compatibility_report": __file__,
            "source_grounding": __file__,
        }

        result = validate_run_outputs(state, [], executor_result, artifact_paths)
        report = build_validation_report(result)

        self.assertEqual(result.status, "warning")
        self.assertIn("[warn] retrieval.empty", report)

    def test_validator_reports_failure_when_completed_executor_has_no_output(self) -> None:
        state = TaskState(
            task_id="fail123",
            title="Validator failure",
            goal="Block inconsistent runs",
            workspace_root="/tmp",
            phase="summarize",
        )
        retrieval_items = [RetrievalItem(path="notes.md", source_type="notes", score=1, preview="context")]
        executor_result = ExecutorResult(
            executor_name="local",
            status="completed",
            message="Execution finished.",
            output="",
        )
        artifact_paths = {
            "executor_prompt": __file__,
            "executor_output": __file__,
            "executor_stdout": __file__,
            "executor_stderr": __file__,
            "summary": __file__,
            "resume_note": __file__,
            "compatibility_report": __file__,
            "source_grounding": __file__,
        }

        result = validate_run_outputs(state, retrieval_items, executor_result, artifact_paths)

        self.assertEqual(result.status, "failed")
        self.assertTrue(any(finding.code == "executor.empty_output" for finding in result.findings))

    def test_cli_run_with_local_executor_completes_without_codex(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\nexecutor seam and retrieval reuse\n", encoding="utf-8")

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Local executor",
                        "--goal",
                        "Prove executor replaceability",
                        "--workspace-root",
                        str(tmp_path),
                        "--executor",
                        "local",
                    ]
                ),
                0,
            )
            task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
            self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)

            task_dir = tmp_path / ".swl" / "tasks" / task_id
            state = json.loads((task_dir / "state.json").read_text(encoding="utf-8"))
            summary = (task_dir / "artifacts" / "summary.md").read_text(encoding="utf-8")
            events = [
                json.loads(line)
                for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["executor_name"], "local")
        self.assertEqual(state["route_mode"], "auto")
        self.assertEqual(state["route_name"], "local-summary")
        self.assertEqual(state["route_backend"], "local_summary")
        self.assertEqual(state["route_execution_site"], "local")
        self.assertEqual(state["route_remote_capable"], False)
        self.assertEqual(state["route_transport_kind"], "local_process")
        self.assertEqual(state["executor_status"], "completed")
        self.assertIn("Local summary executor completed.", summary)
        self.assertEqual(events[0]["payload"]["executor_name"], "local")
        self.assertEqual(events[0]["payload"]["route_name"], "local-summary")
        run_started = next(event for event in events if event["event_type"] == "task.run_started")
        self.assertEqual(run_started["payload"]["executor_name"], "local")
        self.assertEqual(run_started["payload"]["route_name"], "local-summary")
        terminal_event = next(event for event in events if event["event_type"] == "task.completed")
        self.assertEqual(terminal_event["payload"]["executor_name"], "local")
        self.assertEqual(terminal_event["payload"]["route_name"], "local-summary")

    def test_cli_artifact_commands_print_phase1_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\nartifact commands\n", encoding="utf-8")

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Artifact commands",
                        "--goal",
                        "Expose phase1 artifacts in the CLI",
                        "--workspace-root",
                        str(tmp_path),
                        "--executor",
                        "local",
                    ]
                ),
                0,
            )
            task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
            self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)

            validation_stdout = StringIO()
            compatibility_stdout = StringIO()
            route_stdout = StringIO()
            retrieval_stdout = StringIO()
            topology_stdout = StringIO()
            execution_site_stdout = StringIO()
            dispatch_stdout = StringIO()
            handoff_stdout = StringIO()
            remote_handoff_stdout = StringIO()
            execution_fit_stdout = StringIO()
            semantics_stdout = StringIO()
            knowledge_objects_stdout = StringIO()
            knowledge_partition_stdout = StringIO()
            knowledge_index_stdout = StringIO()
            knowledge_policy_stdout = StringIO()
            knowledge_decisions_stdout = StringIO()
            canonical_registry_stdout = StringIO()
            canonical_registry_index_stdout = StringIO()
            canonical_reuse_eval_stdout = StringIO()
            canonical_reuse_regression_json_stdout = StringIO()
            compatibility_json_stdout = StringIO()
            route_json_stdout = StringIO()
            topology_json_stdout = StringIO()
            execution_site_json_stdout = StringIO()
            dispatch_json_stdout = StringIO()
            handoff_json_stdout = StringIO()
            remote_handoff_json_stdout = StringIO()
            execution_fit_json_stdout = StringIO()
            semantics_json_stdout = StringIO()
            knowledge_objects_json_stdout = StringIO()
            knowledge_partition_json_stdout = StringIO()
            knowledge_index_json_stdout = StringIO()
            knowledge_policy_json_stdout = StringIO()
            knowledge_decisions_json_stdout = StringIO()
            canonical_registry_json_stdout = StringIO()
            canonical_registry_index_json_stdout = StringIO()
            canonical_reuse_eval_json_stdout = StringIO()
            retrieval_json_stdout = StringIO()
            grounding_stdout = StringIO()
            memory_stdout = StringIO()

            with redirect_stdout(validation_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "validation", task_id]), 0)
            with redirect_stdout(compatibility_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "compatibility", task_id]), 0)
            with redirect_stdout(route_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "route", task_id]), 0)
            with redirect_stdout(retrieval_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "retrieval", task_id]), 0)
            with redirect_stdout(semantics_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "semantics", task_id]), 0)
            with redirect_stdout(knowledge_objects_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "knowledge-objects", task_id]), 0)
            with redirect_stdout(knowledge_partition_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "knowledge-partition", task_id]), 0)
            with redirect_stdout(knowledge_index_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "knowledge-index", task_id]), 0)
            with redirect_stdout(knowledge_policy_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "knowledge-policy", task_id]), 0)
            with redirect_stdout(knowledge_decisions_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "knowledge-decisions", task_id]), 0)
            with redirect_stdout(canonical_registry_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "canonical-registry", task_id]), 0)
            with redirect_stdout(canonical_registry_index_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "canonical-registry-index", task_id]), 0)
            with redirect_stdout(canonical_reuse_eval_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "canonical-reuse-eval", task_id]), 0)
            with redirect_stdout(topology_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "topology", task_id]), 0)
            with redirect_stdout(execution_site_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "execution-site", task_id]), 0)
            with redirect_stdout(dispatch_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "dispatch", task_id]), 0)
            with redirect_stdout(handoff_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "handoff", task_id]), 0)
            with redirect_stdout(remote_handoff_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "remote-handoff", task_id]), 0)
            with redirect_stdout(execution_fit_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "execution-fit", task_id]), 0)
            with redirect_stdout(compatibility_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "compatibility-json", task_id]), 0)
            with redirect_stdout(route_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "route-json", task_id]), 0)
            with redirect_stdout(topology_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "topology-json", task_id]), 0)
            with redirect_stdout(execution_site_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "execution-site-json", task_id]), 0)
            with redirect_stdout(dispatch_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "dispatch-json", task_id]), 0)
            with redirect_stdout(handoff_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "handoff-json", task_id]), 0)
            with redirect_stdout(remote_handoff_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "remote-handoff-json", task_id]), 0)
            with redirect_stdout(execution_fit_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "execution-fit-json", task_id]), 0)
            with redirect_stdout(semantics_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "semantics-json", task_id]), 0)
            with redirect_stdout(knowledge_objects_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "knowledge-objects-json", task_id]), 0)
            with redirect_stdout(knowledge_partition_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "knowledge-partition-json", task_id]), 0)
            with redirect_stdout(knowledge_index_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "knowledge-index-json", task_id]), 0)
            with redirect_stdout(knowledge_policy_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "knowledge-policy-json", task_id]), 0)
            with redirect_stdout(knowledge_decisions_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "knowledge-decisions-json", task_id]), 0)
            with redirect_stdout(canonical_registry_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "canonical-registry-json", task_id]), 0)
            with redirect_stdout(canonical_registry_index_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "canonical-registry-index-json", task_id]), 0)
            with redirect_stdout(canonical_reuse_eval_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "canonical-reuse-eval-json", task_id]), 0)
            with redirect_stdout(canonical_reuse_regression_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "canonical-reuse-regression-json", task_id]), 0)
            with redirect_stdout(retrieval_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "retrieval-json", task_id]), 0)
            with redirect_stdout(grounding_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "grounding", task_id]), 0)
            with redirect_stdout(memory_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "memory", task_id]), 0)

        self.assertIn("Validation Report", validation_stdout.getvalue())
        self.assertIn("Compatibility Report", compatibility_stdout.getvalue())
        self.assertIn("Route Report", route_stdout.getvalue())
        self.assertIn("Retrieval Report", retrieval_stdout.getvalue())
        self.assertIn("Task Semantics Report", semantics_stdout.getvalue())
        self.assertIn("Knowledge Objects Report", knowledge_objects_stdout.getvalue())
        self.assertIn("Knowledge Partition Report", knowledge_partition_stdout.getvalue())
        self.assertIn("Knowledge Index Report", knowledge_index_stdout.getvalue())
        self.assertIn("Knowledge Policy Report", knowledge_policy_stdout.getvalue())
        self.assertIn("Knowledge Decision Record", knowledge_decisions_stdout.getvalue())
        self.assertIn("Canonical Knowledge Registry", canonical_registry_stdout.getvalue())
        self.assertIn("Canonical Knowledge Registry Index", canonical_registry_index_stdout.getvalue())
        self.assertIn("Canonical Reuse Evaluation", canonical_reuse_eval_stdout.getvalue())
        self.assertIn("Topology Report", topology_stdout.getvalue())
        self.assertIn("Execution Site Report", execution_site_stdout.getvalue())
        self.assertIn("Dispatch Report", dispatch_stdout.getvalue())
        self.assertIn("Handoff Report", handoff_stdout.getvalue())
        self.assertIn("Remote Handoff Contract Report", remote_handoff_stdout.getvalue())
        self.assertIn("Execution Fit Report", execution_fit_stdout.getvalue())
        self.assertIn('"status"', compatibility_json_stdout.getvalue())
        self.assertIn('"name"', route_json_stdout.getvalue())
        self.assertIn('"execution_site"', route_json_stdout.getvalue())
        self.assertIn('"remote_capable"', route_json_stdout.getvalue())
        self.assertIn('"dispatch_status"', topology_json_stdout.getvalue())
        self.assertIn('"contract_kind"', execution_site_json_stdout.getvalue())
        self.assertIn('"attempt_id"', dispatch_json_stdout.getvalue())
        self.assertIn('"next_operator_action"', handoff_json_stdout.getvalue())
        self.assertIn('"required_inputs"', handoff_json_stdout.getvalue())
        self.assertIn('"expected_outputs"', handoff_json_stdout.getvalue())
        self.assertIn('"handoff_boundary"', remote_handoff_json_stdout.getvalue())
        self.assertIn('"transport_truth"', remote_handoff_json_stdout.getvalue())
        self.assertIn('"findings"', execution_fit_json_stdout.getvalue())
        self.assertIn('"source_kind"', semantics_json_stdout.getvalue())
        self.assertIn("[", knowledge_objects_json_stdout.getvalue())
        self.assertIn('"task_linked_count"', knowledge_partition_json_stdout.getvalue())
        self.assertIn('"active_reusable_count"', knowledge_index_json_stdout.getvalue())
        self.assertIn('"status"', knowledge_policy_json_stdout.getvalue())
        self.assertIn("[", knowledge_decisions_json_stdout.getvalue())
        self.assertIn("[", canonical_registry_json_stdout.getvalue())
        self.assertIn('"count"', canonical_registry_index_json_stdout.getvalue())
        self.assertIn("[", canonical_reuse_eval_json_stdout.getvalue())
        self.assertIn('"evaluation_count"', canonical_reuse_regression_json_stdout.getvalue())
        self.assertIn('"citation"', retrieval_json_stdout.getvalue())
        self.assertIn("Grounding Evidence", grounding_stdout.getvalue())
        self.assertIn('"task_id"', memory_stdout.getvalue())

    def test_run_task_executor_override_updates_selected_executor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            created = TaskState(
                task_id="override123",
                title="Executor override",
                goal="Override executor at run time",
                workspace_root=str(base_dir),
                executor_name="codex",
            )
            observed_states: list[tuple[str, str, str]] = []

            def save_state_spy(_base_dir: Path, state: TaskState) -> None:
                observed_states.append((state.status, state.phase, state.executor_name))

            retrieval_items = [
                RetrievalItem(path="notes.md", source_type="notes", score=3, preview="override"),
            ]
            executor_result = ExecutorResult(
                executor_name="local",
                status="completed",
                message="Execution finished.",
                output="done",
            )

            with patch("swallow.orchestrator.load_state", return_value=created):
                with patch("swallow.orchestrator.save_state", side_effect=save_state_spy):
                    with patch("swallow.orchestrator.append_event"):
                        with patch("swallow.orchestrator.run_retrieval", return_value=retrieval_items):
                            with patch("swallow.orchestrator._execute_task_card", return_value=executor_result):
                                with patch(
                                    "swallow.orchestrator.write_task_artifacts",
                                    return_value=(
                                        ValidationResult(status="passed", message="Compatibility passed."),
                                        ValidationResult(status="passed", message="Execution fit passed."),
                                        ValidationResult(status="passed", message="Knowledge policy passed."),
                                        ValidationResult(status="passed", message="Validation passed."),
                                        ValidationResult(status="passed", message="Retry policy passed."),
                                        ValidationResult(status="passed", message="Execution budget policy passed."),
                                        ValidationResult(status="warning", message="Stop policy warning."),
                                    ),
                                ):
                                    final_state = run_task(base_dir, created.task_id, executor_name="local")

        self.assertEqual(observed_states[0], ("running", "intake", "local"))
        self.assertEqual(final_state.executor_name, "local")
        self.assertEqual(final_state.route_name, "local-summary")

    def test_cli_route_mode_selects_route_without_executor_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\nroute mode policy\n", encoding="utf-8")

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Route mode",
                        "--goal",
                        "Pick a deterministic route policy",
                        "--workspace-root",
                        str(tmp_path),
                        "--route-mode",
                        "deterministic",
                    ]
                ),
                0,
            )
            task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
            self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)

            task_dir = tmp_path / ".swl" / "tasks" / task_id
            state = json.loads((task_dir / "state.json").read_text(encoding="utf-8"))
            events = [
                json.loads(line)
                for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(state["route_mode"], "deterministic")
        self.assertEqual(state["executor_name"], "mock")
        self.assertEqual(state["route_name"], "local-mock")
        self.assertEqual(state["route_execution_site"], "local")
        self.assertEqual(state["route_remote_capable"], False)
        self.assertEqual(events[1]["payload"]["route_mode"], "deterministic")
        self.assertEqual(events[1]["payload"]["route_name"], "local-mock")

    def test_cli_detached_route_mode_runs_through_detached_local_transport(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\ndetached route mode policy\n", encoding="utf-8")

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Detached route mode",
                        "--goal",
                        "Pick a detached deterministic route policy",
                        "--workspace-root",
                        str(tmp_path),
                        "--route-mode",
                        "detached",
                        "--executor",
                        "mock",
                    ]
                ),
                0,
            )
            task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
            self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)

            task_dir = tmp_path / ".swl" / "tasks" / task_id
            state = json.loads((task_dir / "state.json").read_text(encoding="utf-8"))
            execution_site = json.loads((task_dir / "execution_site.json").read_text(encoding="utf-8"))
            topology = json.loads((task_dir / "topology.json").read_text(encoding="utf-8"))
            dispatch = json.loads((task_dir / "dispatch.json").read_text(encoding="utf-8"))
            execution_fit = json.loads((task_dir / "execution_fit.json").read_text(encoding="utf-8"))
            stop_policy = json.loads((task_dir / "stop_policy.json").read_text(encoding="utf-8"))
            stop_policy_report = (task_dir / "artifacts" / "stop_policy_report.md").read_text(encoding="utf-8")
            events = [
                json.loads(line)
                for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(state["route_mode"], "detached")
        self.assertEqual(state["route_name"], "local-mock-detached")
        self.assertEqual(state["route_transport_kind"], "local_detached_process")
        self.assertEqual(state["execution_site_contract_kind"], "local_detached")
        self.assertEqual(state["execution_site_boundary"], "same_machine_detached")
        self.assertEqual(state["execution_site_contract_status"], "active")
        self.assertEqual(state["topology_dispatch_status"], "detached_dispatched")
        self.assertEqual(execution_site["contract_kind"], "local_detached")
        self.assertEqual(execution_site["boundary"], "same_machine_detached")
        self.assertEqual(execution_site["contract_status"], "active")
        self.assertEqual(topology["transport_kind"], "local_detached_process")
        self.assertEqual(dispatch["dispatch_status"], "detached_dispatched")
        self.assertEqual(dispatch["transport_kind"], "local_detached_process")
        self.assertEqual(execution_fit["status"], "passed")
        self.assertEqual(stop_policy["status"], "warning")
        self.assertEqual(stop_policy["stop_decision"], "detached_checkpoint_review")
        self.assertEqual(stop_policy["checkpoint_kind"], "detached_completed_run_review")
        self.assertEqual(stop_policy["escalation_level"], "operator_detached_review")
        self.assertIn("detached_completed_run_review", stop_policy_report)
        run_started = next(event for event in events if event["event_type"] == "task.run_started")
        self.assertEqual(run_started["payload"]["route_mode"], "detached")
        self.assertEqual(run_started["payload"]["route_name"], "local-mock-detached")
        self.assertEqual(run_started["payload"]["route_transport_kind"], "local_detached_process")
        terminal_event = next(event for event in events if event["event_type"] == "task.completed")
        self.assertEqual(terminal_event["payload"]["topology_dispatch_status"], "detached_dispatched")

    def test_run_task_route_mode_override_changes_selected_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            created = TaskState(
                task_id="routemodeoverride",
                title="Route mode override",
                goal="Override route mode at run time",
                workspace_root=str(base_dir),
                executor_name="codex",
                route_mode="auto",
            )
            retrieval_items = [
                RetrievalItem(path="notes.md", source_type="notes", score=3, preview="override"),
            ]
            executor_result = ExecutorResult(
                executor_name="note-only",
                status="failed",
                message="Execution skipped.",
                output="note",
                failure_kind="unreachable_backend",
            )

            with patch("swallow.orchestrator.load_state", return_value=created):
                with patch("swallow.orchestrator.save_state"):
                    with patch("swallow.orchestrator.append_event"):
                        with patch("swallow.orchestrator.run_retrieval", return_value=retrieval_items):
                            with patch("swallow.orchestrator._execute_task_card", return_value=executor_result):
                                with patch(
                                    "swallow.orchestrator.write_task_artifacts",
                                    return_value=(
                                        ValidationResult(status="passed", message="Compatibility passed."),
                                        ValidationResult(status="passed", message="Execution fit passed."),
                                        ValidationResult(status="passed", message="Knowledge policy passed."),
                                        ValidationResult(status="passed", message="Validation passed."),
                                        ValidationResult(status="passed", message="Retry policy passed."),
                                        ValidationResult(status="passed", message="Execution budget policy passed."),
                                        ValidationResult(status="warning", message="Stop policy warning."),
                                    ),
                                ):
                                    final_state = run_task(base_dir, created.task_id, route_mode="offline")

        self.assertEqual(final_state.route_mode, "offline")
        self.assertEqual(final_state.route_name, "local-note")
        self.assertEqual(final_state.executor_name, "note-only")

    def test_repeat_run_prompt_includes_prior_memory_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\nmemory reuse prompt\n", encoding="utf-8")

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Memory reuse",
                        "--goal",
                        "Preserve task memory across reruns",
                        "--workspace-root",
                        str(tmp_path),
                        "--executor",
                        "local",
                    ]
                ),
                0,
            )
            task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
            self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)

            task_dir = tmp_path / ".swl" / "tasks" / task_id
            first_prompt = (task_dir / "artifacts" / "executor_prompt.md").read_text(encoding="utf-8")
            self.assertNotIn("Prior persisted context:", first_prompt)

            self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)
            second_prompt = (task_dir / "artifacts" / "executor_prompt.md").read_text(encoding="utf-8")

        self.assertIn("Prior persisted context:", second_prompt)
        self.assertIn("Prior retrieval memory:", second_prompt)
        self.assertIn("previous_retrieval_count: 1", second_prompt)
        self.assertIn("previous_top_references: notes.md#L1-L3", second_prompt)
        self.assertIn("previous_reused_knowledge_count: 0", second_prompt)
        self.assertIn("previous_reused_knowledge_references: none", second_prompt)
        self.assertIn("previous_retrieval_record:", second_prompt)
        self.assertIn("Route Execution Site: local", second_prompt)
        self.assertIn("Route Remote Capable: no", second_prompt)
        self.assertIn("Route Transport Kind: local_process", second_prompt)
        self.assertIn("source_grounding.md", second_prompt)
        self.assertIn("memory.json", second_prompt)

    def test_provider_dialect_is_visible_in_prompt_artifact_events_inspect_and_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\nprovider dialect prompt\n", encoding="utf-8")

            with patch.dict(
                "os.environ",
                {"AIWF_CODEX_BIN": "definitely-not-a-real-codex-binary", "AIWF_EXECUTOR_MODE": "codex"},
                clear=False,
            ):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "task",
                            "create",
                            "--title",
                            "Provider dialect",
                            "--goal",
                            "Expose dialect metadata to operators",
                            "--workspace-root",
                            str(tmp_path),
                        ]
                    ),
                    0,
                )
                task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)

            task_dir = tmp_path / ".swl" / "tasks" / task_id
            prompt = (task_dir / "artifacts" / "executor_prompt.md").read_text(encoding="utf-8")
            primary_prompt = (task_dir / "artifacts" / "fallback_primary_executor_prompt.md").read_text(
                encoding="utf-8"
            )
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

        executor_event = next(event for event in events if event["event_type"] == "executor.failed")
        fallback_event = next(event for event in events if event["event_type"] == "task.execution_fallback")
        self.assertTrue(prompt.startswith("dialect: plain_text\n\n"))
        self.assertIn("Executor: local", prompt)
        self.assertIn("Route: local-summary", prompt)
        self.assertTrue(primary_prompt.startswith("dialect: codex_fim\n\n"))
        self.assertIn("<fim_prefix>", primary_prompt)
        self.assertIn("<fim_suffix>", primary_prompt)
        self.assertEqual(executor_event["payload"]["dialect"], "codex_fim")
        self.assertEqual(fallback_event["payload"]["fallback_route_name"], "local-summary")
        self.assertIn("dialect: plain_text", inspect_stdout.getvalue())
        self.assertIn("dialect: plain_text", review_stdout.getvalue())

    def test_reused_verified_knowledge_is_visible_in_retrieval_memory_and_rerun_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "notes.md").write_text("# Notes\n\nfallback note\n", encoding="utf-8")

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Knowledge reuse memory",
                        "--goal",
                        "Carry reused verified knowledge through retrieval memory",
                        "--workspace-root",
                        str(tmp_path),
                        "--executor",
                        "local",
                    ]
                ),
                0,
            )
            task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
            knowledge_retrieval_items = [
                RetrievalItem(
                    path=".swl/tasks/demo/knowledge_objects.json",
                    source_type=KNOWLEDGE_SOURCE_TYPE,
                    score=7,
                    preview="Verified reusable knowledge should remain visible in memory.",
                    chunk_id="knowledge-0001",
                    title="Knowledge knowledge-0001",
                    citation=".swl/tasks/demo/knowledge_objects.json#knowledge-0001",
                    matched_terms=["verified", "knowledge"],
                    score_breakdown={"content_hits": 2, "rerank_bonus": 3},
                metadata={
                    "adapter_name": "verified_knowledge_records",
                    "chunk_kind": "knowledge_object",
                    "knowledge_object_id": "knowledge-0001",
                    "knowledge_stage": "verified",
                    "knowledge_reuse_scope": "retrieval_candidate",
                    "evidence_status": "artifact_backed",
                    "artifact_ref": ".swl/tasks/demo/artifacts/summary.md",
                    "source_ref": "chat://knowledge-verified",
                    "knowledge_task_id": "demo",
                    "knowledge_task_relation": "cross_task",
                    "storage_scope": "canonical_registry",
                    "canonical_id": "canonical-demo-knowledge-0001",
                    "canonical_key": "task-object:demo:knowledge-0001",
                },
            )
        ]

            with patch("swallow.harness.retrieve_context", return_value=knowledge_retrieval_items):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)

            task_dir = tmp_path / ".swl" / "tasks" / task_id
            memory = json.loads((task_dir / "memory.json").read_text(encoding="utf-8"))
            summary = (task_dir / "artifacts" / "summary.md").read_text(encoding="utf-8")
            resume_note = (task_dir / "artifacts" / "resume_note.md").read_text(encoding="utf-8")
            retrieval_report = (task_dir / "artifacts" / "retrieval_report.md").read_text(encoding="utf-8")

            self.assertEqual(memory["retrieval"]["reused_knowledge_count"], 1)
            self.assertEqual(memory["retrieval"]["reused_knowledge_current_task_count"], 0)
            self.assertEqual(memory["retrieval"]["reused_knowledge_cross_task_count"], 1)
            self.assertEqual(
                memory["retrieval"]["reused_knowledge_references"],
                [".swl/tasks/demo/knowledge_objects.json#knowledge-0001"],
            )
            self.assertEqual(memory["retrieval"]["reused_knowledge_object_ids"], ["knowledge-0001"])
            self.assertEqual(memory["retrieval"]["reused_knowledge_evidence_counts"]["artifact_backed"], 1)
            self.assertIn("retrieval_reused_knowledge_count: 1", summary)
            self.assertIn("retrieval_reused_knowledge_cross_task_count: 1", summary)
            self.assertIn("reused_verified_knowledge: 1", summary)
            self.assertIn("reused_cross_task_knowledge: 1", summary)
            self.assertIn(".swl/tasks/demo/knowledge_objects.json#knowledge-0001", summary)
            self.assertIn("reused verified knowledge records: 1", resume_note)
            self.assertIn("reused cross-task knowledge records: 1", resume_note)
            self.assertIn("reused knowledge references: .swl/tasks/demo/knowledge_objects.json#knowledge-0001", resume_note)
            self.assertIn("reused_knowledge_count: 1", retrieval_report)
            self.assertIn("reused_knowledge_cross_task_count: 1", retrieval_report)
            self.assertIn("reused_knowledge_references: .swl/tasks/demo/knowledge_objects.json#knowledge-0001", retrieval_report)
            inspect_stdout = StringIO()
            review_stdout = StringIO()
            with redirect_stdout(inspect_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "inspect", task_id]), 0)
            with redirect_stdout(review_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "review", task_id]), 0)

            self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)
            second_prompt = (task_dir / "artifacts" / "executor_prompt.md").read_text(encoding="utf-8")

        self.assertIn("previous_reused_knowledge_count: 1", second_prompt)
        self.assertIn("previous_reused_cross_task_knowledge_count: 1", second_prompt)
        self.assertIn(
            "previous_reused_knowledge_references: .swl/tasks/demo/knowledge_objects.json#knowledge-0001",
            second_prompt,
        )
        self.assertIn("reused_knowledge_in_retrieval: 1", inspect_stdout.getvalue())
        self.assertIn("reused_cross_task_knowledge: 1", inspect_stdout.getvalue())
        self.assertIn(
            "reused_knowledge_references: .swl/tasks/demo/knowledge_objects.json#knowledge-0001",
            inspect_stdout.getvalue(),
        )
        self.assertIn("grounding_locked: yes", inspect_stdout.getvalue())
        self.assertIn("grounding_refs_count: 1", inspect_stdout.getvalue())
        self.assertIn("grounding_refs: canonical:canonical-demo-knowledge-0001", inspect_stdout.getvalue())
        self.assertIn("reused_knowledge_in_retrieval: 1", review_stdout.getvalue())
        self.assertIn("reused_cross_task_knowledge: 1", review_stdout.getvalue())
        self.assertIn(
            "reused_knowledge_references: .swl/tasks/demo/knowledge_objects.json#knowledge-0001",
            review_stdout.getvalue(),
        )
        self.assertIn("grounding_locked: yes", review_stdout.getvalue())
        self.assertIn("grounding_refs_count: 1", review_stdout.getvalue())
        self.assertIn("grounding_refs: canonical:canonical-demo-knowledge-0001", review_stdout.getvalue())
        self.assertIn("retrieval_report:", review_stdout.getvalue())
        self.assertIn("source_grounding:", review_stdout.getvalue())
        self.assertIn("grounding_evidence_report:", review_stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
