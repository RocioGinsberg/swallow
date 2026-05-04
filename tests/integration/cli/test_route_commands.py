from __future__ import annotations

import json
from pathlib import Path

from swallow.provider_router.router import load_route_capability_profiles, load_route_weights, route_by_name
from swallow.application.infrastructure.paths import route_capabilities_path, route_weights_path
from tests.helpers.cli_runner import run_cli


def _write_events(task_dir: Path, records: list[dict[str, object]]) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "events.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


def _write_route_weight_signal(base_dir: Path) -> None:
    _write_events(
        base_dir / ".swl" / "tasks" / "cli-route-weight-task",
        [
            {
                "task_id": "cli-route-weight-task",
                "event_type": "executor.failed",
                "message": "Primary route failed.",
                "payload": {
                    "physical_route": "local-codex",
                    "logical_model": "codex",
                    "task_family": "execution",
                    "latency_ms": 12,
                    "token_cost": 0.0,
                    "degraded": False,
                    "failure_kind": "launch_error",
                    "error_code": "launch_error",
                },
            },
            {
                "task_id": "cli-route-weight-task",
                "event_type": "executor.failed",
                "message": "Primary route failed again.",
                "payload": {
                    "physical_route": "local-codex",
                    "logical_model": "codex",
                    "task_family": "execution",
                    "latency_ms": 10,
                    "token_cost": 0.0,
                    "degraded": False,
                    "failure_kind": "launch_error",
                    "error_code": "launch_error",
                },
            },
            {
                "task_id": "cli-route-weight-task",
                "event_type": "executor.completed",
                "message": "Primary route recovered once.",
                "payload": {
                    "physical_route": "local-codex",
                    "logical_model": "codex",
                    "task_family": "execution",
                    "latency_ms": 8,
                    "token_cost": 0.0,
                    "degraded": False,
                    "error_code": "",
                },
            },
        ],
    )


def test_route_weights_show_apply_characterization_stdout_stderr_exit_code(tmp_path: Path) -> None:
    route = route_by_name("local-codex")
    assert route is not None
    original_weight = route.quality_weight
    try:
        show_before = run_cli(tmp_path, "route", "weights", "show")
        show_before.assert_success()
        assert show_before.stderr == ""
        assert "# Route Quality Weights" in show_before.stdout
        assert "local-codex:" in show_before.stdout

        _write_route_weight_signal(tmp_path)
        optimize_result = run_cli(tmp_path, "meta-optimize", "--last-n", "100")
        optimize_result.assert_success()
        artifact_path = next(
            line.removeprefix("artifact: ").strip()
            for line in optimize_result.stdout.splitlines()
            if line.startswith("artifact: ")
        )

        apply_result = run_cli(tmp_path, "route", "weights", "apply", artifact_path)

        apply_result.assert_success()
        assert apply_result.stderr == ""
        assert "# Route Quality Weights" in apply_result.stdout
        assert "local-codex: 0.330000" in apply_result.stdout
        assert load_route_weights(tmp_path)["local-codex"] == 0.33
        assert not route_weights_path(tmp_path).exists()

        show_after = run_cli(tmp_path, "route", "weights", "show")
        show_after.assert_success()
        assert show_after.stderr == ""
        assert "local-codex: 0.330000" in show_after.stdout
    finally:
        route.quality_weight = original_weight


def test_route_capabilities_show_update_characterization_stdout_stderr_exit_code(tmp_path: Path) -> None:
    route = route_by_name("local-http")
    assert route is not None
    original_scores = dict(route.task_family_scores)
    original_unsupported = list(route.unsupported_task_types)
    try:
        show_before = run_cli(tmp_path, "route", "capabilities", "show")
        show_before.assert_success()
        assert show_before.stderr == ""
        assert "# Route Capability Profiles" in show_before.stdout
        assert "local-http" in show_before.stdout

        update_result = run_cli(
            tmp_path,
            "route",
            "capabilities",
            "update",
            "local-http",
            "--task-type",
            "review",
            "--score",
            "0.75",
            "--mark-unsupported",
            "execution",
        )

        update_result.assert_success()
        assert update_result.stderr == ""
        assert "# Route Capability Profiles" in update_result.stdout
        assert "local-http" in update_result.stdout
        assert "task_family_scores: review=0.750000" in update_result.stdout
        assert "unsupported_task_types: execution" in update_result.stdout
        persisted = load_route_capability_profiles(tmp_path)
        assert persisted["local-http"]["task_family_scores"]["review"] == 0.75
        assert persisted["local-http"]["unsupported_task_types"] == ["execution"]
        assert not route_capabilities_path(tmp_path).exists()

        show_after = run_cli(tmp_path, "route", "capabilities", "show")
        show_after.assert_success()
        assert show_after.stderr == ""
        assert "task_family_scores: review=0.750000" in show_after.stdout
    finally:
        route.task_family_scores = original_scores
        route.unsupported_task_types = original_unsupported


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


class LegacyCliRouteCommandTest(unittest.TestCase):
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
                "tool:doctor.executor",
            ]
        )

        self.assertEqual(manifest.profile_refs, ["baseline_local"])
        self.assertEqual(manifest.workflow_refs, ["task_loop"])
        self.assertEqual(manifest.validator_refs, ["run_output_validation"])
        self.assertEqual(manifest.skill_refs, ["plan-task"])
        self.assertEqual(manifest.tool_refs, ["doctor.executor"])

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

    def test_cli_planning_handoff_updates_complexity_hint(self) -> None:
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
                        "Complexity hint handoff",
                        "--goal",
                        "Update complexity hint after task creation",
                        "--workspace-root",
                        str(tmp_path),
                    ]
                ),
                0,
            )
            task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
            task_dir = tmp_path / ".swl" / "tasks" / task_id
            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "planning-handoff",
                        task_id,
                        "--complexity-hint",
                        "parallel",
                    ]
                ),
                0,
            )
            task_semantics = json.loads((task_dir / "task_semantics.json").read_text(encoding="utf-8"))
            semantics_report = (task_dir / "artifacts" / "task_semantics_report.md").read_text(encoding="utf-8")
            events = [
                json.loads(line)
                for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(task_semantics["complexity_hint"], "parallel")
        self.assertIn("- complexity_hint: parallel", semantics_report)
        self.assertEqual(events[-1]["payload"]["task_semantics"]["complexity_hint"], "parallel")

    def test_cli_route_select_reports_policy_inputs_for_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Route selection report",
                goal="Show route selection dry-run output",
                workspace_root=tmp_path,
                complexity_hint="high",
            )
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "route",
                            "select",
                            "--task-id",
                            state.task_id,
                        ]
                    ),
                    0,
                )

        output = stdout.getvalue()
        self.assertIn("Route Selection", output)
        self.assertIn(f"- task_id: {state.task_id}", output)
        self.assertIn("- selected_route: local-claude-code", output)
        self.assertIn("- complexity_hint: high", output)
        self.assertIn("- parallel_intent: false", output)

    def test_cli_route_select_respects_executor_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Route selection override",
                goal="Prefer explicit override in route dry-run",
                workspace_root=tmp_path,
                complexity_hint="high",
            )
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(
                    main(
                        [
                            "--base-dir",
                            str(tmp_path),
                            "route",
                            "select",
                            "--task-id",
                            state.task_id,
                            "--executor",
                            "http",
                        ]
                    ),
                    0,
                )

        output = stdout.getvalue()
        self.assertIn("- override_executor: http", output)
        self.assertIn("- executor_name: http", output)
        self.assertIn("- executor_override: http", output)

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

            with patch("swallow.orchestration.orchestrator.run_retrieval", return_value=retrieval_items):
                with patch("swallow.orchestration.orchestrator._execute_task_card", return_value=executor_result):
                    with patch(
                        "swallow.orchestration.orchestrator.write_task_artifacts",
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
                "swallow.orchestration.orchestrator.select_route",
                return_value=remote_route,
            ):
                with patch("swallow.orchestration.orchestrator.run_retrieval") as retrieval_mock:
                    with patch("swallow.orchestration.orchestrator._execute_task_card") as execution_mock:
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

            with patch("swallow.orchestration.orchestrator.select_route", return_value=validator_route):
                with patch("swallow.orchestration.orchestrator.run_retrieval", return_value=[]):
                    with patch(
                        "swallow.orchestration.orchestrator._execute_task_card",
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
            with patch("swallow.orchestration.orchestrator.run_retrieval", return_value=[]):
                with patch(
                    "swallow.orchestration.orchestrator._execute_task_card",
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

    def test_task_review_surfaces_handoff_and_resume_guidance_after_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\nreview handoff guidance\n", encoding="utf-8")

            with patch.dict(
                "os.environ",
                {"AIWF_AIDER_BIN": "definitely-not-a-real-aider-binary", "AIWF_EXECUTOR_MODE": "aider"},
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

    def test_route_capabilities_update_and_show_cli_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)

            update_stdout = StringIO()
            with redirect_stdout(update_stdout):
                exit_code = main(
                    [
                        "--base-dir",
                        str(base_dir),
                        "route",
                        "capabilities",
                        "update",
                        "local-http",
                        "--task-type",
                        "review",
                        "--score",
                        "0.75",
                        "--mark-unsupported",
                        "execution",
                    ]
                )

            self.assertEqual(exit_code, 0)
            persisted = load_route_capability_profiles(base_dir)
            self.assertEqual(persisted["local-http"]["task_family_scores"]["review"], 0.75)
            self.assertEqual(persisted["local-http"]["unsupported_task_types"], ["execution"])
            self.assertFalse(route_capabilities_path(base_dir).exists())
            self.assertIn("local-http", update_stdout.getvalue())
            self.assertIn("task_family_scores: review=0.750000", update_stdout.getvalue())
            self.assertIn("unsupported_task_types: execution", update_stdout.getvalue())

            show_stdout = StringIO()
            with redirect_stdout(show_stdout):
                exit_code = main(["--base-dir", str(base_dir), "route", "capabilities", "show"])

            self.assertEqual(exit_code, 0)
            self.assertIn("# Route Capability Profiles", show_stdout.getvalue())
            self.assertIn("local-http", show_stdout.getvalue())
            self.assertIn("task_family_scores: review=0.750000", show_stdout.getvalue())

    def test_route_registry_apply_and_show_cli_flow(self) -> None:
        route = route_by_name("local-summary")
        self.assertIsNotNone(route)
        assert route is not None
        registry_payload = {
            "local-summary": {
                **route.to_dict(),
                "model_hint": "summary-cli-governed",
            }
        }
        try:
            with tempfile.TemporaryDirectory() as tmp:
                base_dir = Path(tmp)
                registry_file = base_dir / "routes.json"
                registry_file.write_text(json.dumps(registry_payload), encoding="utf-8")

                apply_stdout = StringIO()
                with redirect_stdout(apply_stdout):
                    exit_code = main(
                        [
                            "--base-dir",
                            str(base_dir),
                            "route",
                            "registry",
                            "apply",
                            str(registry_file),
                        ]
                    )

                self.assertEqual(exit_code, 0)
                self.assertEqual(load_route_registry(base_dir), registry_payload)
                self.assertFalse(route_registry_path(base_dir).exists())
                self.assertIn("# Route Registry", apply_stdout.getvalue())
                self.assertIn("summary-cli-governed", apply_stdout.getvalue())

                show_stdout = StringIO()
                with redirect_stdout(show_stdout):
                    exit_code = main(["--base-dir", str(base_dir), "route", "registry", "show"])

                self.assertEqual(exit_code, 0)
                self.assertIn("local-summary", show_stdout.getvalue())
                self.assertIn("summary-cli-governed", show_stdout.getvalue())
        finally:
            with tempfile.TemporaryDirectory() as reset_tmp:
                apply_route_registry(Path(reset_tmp))

    def test_route_policy_apply_and_show_cli_flow(self) -> None:
        policy_payload = {
            "route_mode_routes": {"offline": "local-summary"},
            "complexity_bias_routes": {"high": "local-summary"},
            "strategy_complexity_hints": ["high"],
            "parallel_intent_hints": ["fanout"],
            "summary_fallback_route_name": "local-summary",
        }
        try:
            with tempfile.TemporaryDirectory() as tmp:
                base_dir = Path(tmp)
                policy_file = base_dir / "route_policy.json"
                policy_file.write_text(json.dumps(policy_payload), encoding="utf-8")

                apply_stdout = StringIO()
                with redirect_stdout(apply_stdout):
                    exit_code = main(
                        [
                            "--base-dir",
                            str(base_dir),
                            "route",
                            "policy",
                            "apply",
                            str(policy_file),
                        ]
                    )

                self.assertEqual(exit_code, 0)
                self.assertEqual(load_route_policy(base_dir), policy_payload)
                self.assertFalse(route_policy_path(base_dir).exists())
                self.assertIn("# Route Policy", apply_stdout.getvalue())
                self.assertIn("- high: local-summary", apply_stdout.getvalue())
                self.assertIn("fanout", apply_stdout.getvalue())

                show_stdout = StringIO()
                with redirect_stdout(show_stdout):
                    exit_code = main(["--base-dir", str(base_dir), "route", "policy", "show"])

                self.assertEqual(exit_code, 0)
                self.assertIn("- offline: local-summary", show_stdout.getvalue())
                self.assertIn("- high: local-summary", show_stdout.getvalue())
        finally:
            with tempfile.TemporaryDirectory() as reset_tmp:
                apply_route_policy(Path(reset_tmp))

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

            with patch("swallow.orchestration.orchestrator.select_route", return_value=validator_route):
                with patch("swallow.orchestration.orchestrator.run_retrieval", return_value=[]):
                    with patch(
                        "swallow.orchestration.orchestrator._execute_task_card",
                        return_value=ExecutorResult(
                            executor_name="local",
                            status="completed",
                            message="Execution finished.",
                            output="done",
                        ),
                    ):
                        with patch(
                            "swallow.orchestration.orchestrator.write_task_artifacts",
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

            with patch("swallow.orchestration.orchestrator.run_retrieval", return_value=[]):
                with patch(
                    "swallow.orchestration.orchestrator._execute_task_card",
                    return_value=ExecutorResult(
                        executor_name="codex",
                        status="completed",
                        message="Execution finished.",
                        output="done",
                    ),
                ):
                    with patch(
                        "swallow.orchestration.orchestrator.write_task_artifacts",
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

            with patch("swallow.orchestration.orchestrator.run_retrieval", return_value=[]):
                with patch(
                    "swallow.orchestration.orchestrator._execute_task_card",
                    return_value=ExecutorResult(
                        executor_name="local",
                        status="completed",
                        message="Execution finished.",
                        output="done",
                    ),
                ):
                    with patch("swallow.orchestration.orchestrator.write_task_artifacts", side_effect=write_artifacts_side_effect):
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

    def test_resolve_dialect_name_prefers_route_hint_and_falls_back_to_plain_text(self) -> None:
        self.assertEqual(resolve_dialect_name("structured_markdown", "fim"), "structured_markdown")
        self.assertEqual(resolve_dialect_name("", "fim"), "fim")
        self.assertEqual(resolve_dialect_name("", "claude-3-5-sonnet"), "claude_xml")
        self.assertEqual(resolve_dialect_name("", "mock"), "plain_text")
        self.assertEqual(resolve_dialect_name("", "unknown-provider"), "plain_text")

    def test_build_formatted_executor_prompt_uses_fim_for_codex_route(self) -> None:
        state = TaskState(
            task_id="dialect123",
            title="Dialect formatting",
            goal="Format executor prompt with provider dialect",
            workspace_root="/tmp",
            route_name="local-codex",
            route_backend="local_cli",
            route_model_hint="fim",
            route_dialect="fim",
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

    def test_cli_serve_dispatches_to_control_center_server(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with patch("swallow.adapters.http.server.serve_control_center") as serve_mock:
                self.assertEqual(main(["--base-dir", str(tmp_path), "serve", "--host", "127.0.0.1", "--port", "8123"]), 0)

        serve_mock.assert_called_once_with(tmp_path.resolve(), host="127.0.0.1", port=8123)

    def test_create_task_persists_route_dialect_for_default_aider_route(self) -> None:
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

        self.assertEqual(state.route_name, "local-aider")
        self.assertEqual(state.route_dialect, "plain_text")
        self.assertEqual(persisted["route_dialect"], "plain_text")

    def test_select_route_uses_override_before_legacy_mode(self) -> None:
        state = TaskState(
            task_id="route123",
            title="Route selection",
            goal="Prefer explicit route selection",
            workspace_root="/tmp",
            executor_name="aider",
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
            executor_name="aider",
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
            executor_name="aider",
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
            executor_name="aider",
            route_mode="live",
            route_name="local-aider",
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
            executor_name="aider",
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
            executor_name="aider",
            route_mode="deterministic",
            route_name="local-aider",
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
            executor_name="aider",
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

            with patch("swallow.orchestration.orchestrator.load_state", return_value=created):
                with patch("swallow.orchestration.orchestrator.save_state"):
                    with patch("swallow.orchestration.orchestrator.append_event"):
                        with patch("swallow.orchestration.orchestrator.run_retrieval", return_value=retrieval_items):
                            with patch("swallow.orchestration.orchestrator._execute_task_card", return_value=executor_result):
                                with patch(
                                    "swallow.orchestration.orchestrator.write_task_artifacts",
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

    def test_provider_dialect_is_visible_in_prompt_artifact_events_inspect_and_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\nprovider dialect prompt\n", encoding="utf-8")

            with patch.dict(
                "os.environ",
                {"AIWF_AIDER_BIN": "definitely-not-a-real-aider-binary", "AIWF_EXECUTOR_MODE": "aider"},
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

        executor_event = next(event for event in events if event["event_type"] == "executor.completed")
        self.assertTrue(prompt.startswith("dialect: plain_text\n\n"))
        self.assertIn("Executor: local", prompt)
        self.assertIn("Route: local-summary", prompt)
        self.assertFalse((task_dir / "artifacts" / "fallback_primary_executor_prompt.md").exists())
        self.assertEqual(executor_event["payload"]["dialect"], "plain_text")
        self.assertIn("dialect: plain_text", inspect_stdout.getvalue())
        self.assertIn("dialect: plain_text", review_stdout.getvalue())
