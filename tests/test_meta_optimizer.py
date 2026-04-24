from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.cli import main
from swallow.meta_optimizer import (
    MetaOptimizerAgent,
    MetaOptimizerExecutor,
    apply_reviewed_optimization_proposals,
    build_meta_optimizer_snapshot,
    load_optimization_proposal_bundle,
    review_optimization_proposals,
    run_meta_optimizer,
)
from swallow.models import (
    EVENT_EXECUTOR_COMPLETED,
    EVENT_EXECUTOR_FAILED,
    EVENT_TASK_EXECUTION_FALLBACK,
    RouteCapabilities,
    RouteSelection,
    RouteSpec,
    TaskCard,
    TaxonomyProfile,
    ValidationResult,
)
from swallow.orchestrator import create_task, run_task
from swallow.paths import (
    latest_optimization_proposal_bundle_path,
    optimization_proposals_path,
    route_capabilities_path,
    route_weights_path,
)
from swallow.router import apply_route_capability_profiles, apply_route_weights, route_by_name
from swallow.store import load_state


def _write_events(task_dir: Path, records: list[dict[str, object]]) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "events.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


class MetaOptimizerTest(unittest.TestCase):
    def test_meta_optimizer_executor_is_agent_compatible_entity(self) -> None:
        self.assertIsInstance(MetaOptimizerExecutor(), MetaOptimizerAgent)

    def test_run_meta_optimizer_aggregates_route_health_and_failure_fingerprints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task_a = base_dir / ".swl" / "tasks" / "task-a"
            task_b = base_dir / ".swl" / "tasks" / "task-b"
            _write_events(
                task_a,
                [
                    {
                        "task_id": "task-a",
                        "event_type": EVENT_EXECUTOR_FAILED,
                        "message": "Codex launch failed.",
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
                        "task_id": "task-a",
                        "event_type": EVENT_TASK_EXECUTION_FALLBACK,
                        "message": "Fallback executed.",
                        "payload": {
                            "previous_route_name": "local-codex",
                            "fallback_route_name": "local-summary",
                            "latency_ms": 4,
                            "degraded": True,
                        },
                    },
                    {
                        "task_id": "task-a",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
                        "message": "Fallback completed.",
                        "payload": {
                            "physical_route": "local-summary",
                            "logical_model": "local",
                            "task_family": "execution",
                            "latency_ms": 4,
                            "token_cost": 0.0,
                            "degraded": True,
                            "error_code": "",
                        },
                    },
                ],
            )
            _write_events(
                task_b,
                [
                    {
                        "task_id": "task-b",
                        "event_type": EVENT_EXECUTOR_FAILED,
                        "message": "Codex launch failed again.",
                        "payload": {
                            "physical_route": "local-codex",
                            "logical_model": "codex",
                            "task_family": "execution",
                            "latency_ms": 8,
                            "token_cost": 0.0,
                            "degraded": False,
                            "failure_kind": "launch_error",
                            "error_code": "launch_error",
                        },
                    }
                ],
            )

            snapshot, artifact_path, report = run_meta_optimizer(base_dir, last_n=100)
            self.assertEqual(len(snapshot.scanned_task_ids), 2)
            self.assertEqual(snapshot.scanned_event_count, 4)
            self.assertTrue(snapshot.proposals)
            self.assertEqual(snapshot.proposals[0].proposal_type, "route")
            self.assertTrue(snapshot.route_task_family_stats)
            self.assertEqual(artifact_path, optimization_proposals_path(base_dir))
            self.assertTrue(artifact_path.exists())
            self.assertIn("## Route Health", report)
            self.assertIn("## Route Task Family Signals", report)
            self.assertIn("local-codex: success_rate=0% failure_rate=100% fallback_rate=50%", report)
            self.assertIn("local-summary: success_rate=100% failure_rate=0% fallback_rate=0%", report)
            self.assertIn("local-codex/execution: success_rate=0% degraded_rate=0% events=2", report)
            self.assertIn("failure_kind=launch_error error_code=launch_error count=2 routes=local-codex", report)
            self.assertIn("degraded_executor_events: 1/3", report)
            self.assertIn("## Cost Summary", report)
            self.assertIn("local-summary: total_cost=$0.000000 avg_cost=$0.000000 task_families=execution", report)
            self.assertIn("Review route `local-codex`", report)
            self.assertIn("Investigate repeated failure fingerprint `launch_error/launch_error`", report)
            self.assertEqual(artifact_path.read_text(encoding="utf-8"), report)

    def test_run_meta_optimizer_persists_latest_structured_proposal_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task_dir = base_dir / ".swl" / "tasks" / "bundle-task"
            _write_events(
                task_dir,
                [
                    {
                        "task_id": "bundle-task",
                        "event_type": EVENT_EXECUTOR_FAILED,
                        "message": "Local codex failed.",
                        "payload": {
                            "physical_route": "local-codex",
                            "logical_model": "codex",
                            "task_family": "execution",
                            "latency_ms": 15,
                            "token_cost": 0.0,
                            "degraded": False,
                            "failure_kind": "launch_error",
                            "error_code": "launch_error",
                        },
                    }
                ],
            )

            snapshot, artifact_path, _report = run_meta_optimizer(base_dir, last_n=100)

            bundle_path = latest_optimization_proposal_bundle_path(base_dir)
            self.assertTrue(bundle_path.exists())
            bundle = load_optimization_proposal_bundle(bundle_path)
            self.assertEqual(bundle.report_artifact, str(artifact_path))
            self.assertEqual(bundle.generated_at, snapshot.generated_at)
            self.assertTrue(bundle.proposals)
            self.assertTrue(bundle.proposals[0].proposal_id)
            self.assertTrue(bundle.proposals[0].priority)
            self.assertTrue(bundle.proposals[0].rationale)

    def test_review_and_apply_approved_route_weight_proposals(self) -> None:
        route = route_by_name("local-codex")
        self.assertIsNotNone(route)
        assert route is not None
        original_weight = route.quality_weight
        try:
            with tempfile.TemporaryDirectory() as tmp:
                base_dir = Path(tmp)
                task_dir = base_dir / ".swl" / "tasks" / "apply-task"
                _write_events(
                    task_dir,
                    [
                        {
                            "task_id": "apply-task",
                            "event_type": EVENT_EXECUTOR_FAILED,
                            "message": "Local codex failed.",
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
                            "task_id": "apply-task",
                            "event_type": EVENT_EXECUTOR_FAILED,
                            "message": "Local codex failed again.",
                            "payload": {
                                "physical_route": "local-codex",
                                "logical_model": "codex",
                                "task_family": "execution",
                                "latency_ms": 8,
                                "token_cost": 0.0,
                                "degraded": False,
                                "failure_kind": "launch_error",
                                "error_code": "launch_error",
                            },
                        },
                    ],
                )

                run_meta_optimizer(base_dir, last_n=100)
                bundle_path = latest_optimization_proposal_bundle_path(base_dir)
                bundle = load_optimization_proposal_bundle(bundle_path)
                route_weight_proposal = next(
                    proposal
                    for proposal in bundle.proposals
                    if proposal.proposal_type == "route_weight" and proposal.route_name == "local-codex"
                )

                review_record, review_path = review_optimization_proposals(
                    base_dir,
                    bundle_path,
                    decision="approved",
                    proposal_ids=[route_weight_proposal.proposal_id],
                    note="Demote unstable local codex route.",
                )
                self.assertTrue(review_path.exists())
                self.assertEqual(
                    next(
                        entry.decision
                        for entry in review_record.entries
                        if entry.proposal_id == route_weight_proposal.proposal_id
                    ),
                    "approved",
                )

                application_record, application_path = apply_reviewed_optimization_proposals(base_dir, review_path)
                self.assertTrue(application_path.exists())
                self.assertEqual(application_record.applied_count, 1)
                self.assertEqual(application_record.noop_count, 0)
                self.assertEqual(application_record.skipped_count, 0)
                self.assertEqual(application_record.rollback_weights, {"local-codex": 1.0})
                self.assertAlmostEqual(
                    route_by_name("local-codex").quality_weight,
                    route_weight_proposal.suggested_weight or 1.0,
                    places=2,
                )
                persisted_weights = json.loads(route_weights_path(base_dir).read_text(encoding="utf-8"))
                self.assertAlmostEqual(
                    persisted_weights["local-codex"],
                    route_weight_proposal.suggested_weight or 1.0,
                    places=2,
                )

                replay_record, _replay_path = apply_reviewed_optimization_proposals(base_dir, review_path)
                self.assertEqual(replay_record.applied_count, 0)
                self.assertEqual(replay_record.noop_count, 1)
        finally:
            route.quality_weight = original_weight

    def test_meta_optimizer_generates_route_capability_score_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task_dir = base_dir / ".swl" / "tasks" / "capability-score-task"
            _write_events(
                task_dir,
                [
                    {
                        "task_id": "capability-score-task",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
                        "message": "HTTP route completed review task.",
                        "payload": {
                            "physical_route": "local-http",
                            "logical_model": "http-default",
                            "task_family": "review",
                            "latency_ms": 10,
                            "token_cost": 0.0,
                            "degraded": False,
                        },
                    },
                    {
                        "task_id": "capability-score-task",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
                        "message": "HTTP route completed another review task.",
                        "payload": {
                            "physical_route": "local-http",
                            "logical_model": "http-default",
                            "task_family": "review",
                            "latency_ms": 12,
                            "token_cost": 0.0,
                            "degraded": True,
                        },
                    },
                ],
            )

            snapshot = build_meta_optimizer_snapshot(base_dir, last_n=100)

        proposal = next(
            proposal
            for proposal in snapshot.proposals
            if proposal.proposal_type == "route_capability"
            and proposal.route_name == "local-http"
            and proposal.task_family == "review"
            and not proposal.mark_task_family_unsupported
        )
        self.assertAlmostEqual(proposal.suggested_task_family_score or 0.0, 0.88, places=2)

    def test_review_and_apply_approved_route_capability_score_proposals(self) -> None:
        route = route_by_name("local-http")
        self.assertIsNotNone(route)
        assert route is not None
        original_scores = dict(route.task_family_scores)
        original_unsupported = list(route.unsupported_task_types)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                base_dir = Path(tmp)
                task_dir = base_dir / ".swl" / "tasks" / "capability-apply-task"
                _write_events(
                    task_dir,
                    [
                        {
                            "task_id": "capability-apply-task",
                            "event_type": EVENT_EXECUTOR_COMPLETED,
                            "message": "HTTP route completed review task.",
                            "payload": {
                                "physical_route": "local-http",
                                "logical_model": "http-default",
                                "task_family": "review",
                                "latency_ms": 10,
                                "token_cost": 0.0,
                                "degraded": False,
                            },
                        },
                        {
                            "task_id": "capability-apply-task",
                            "event_type": EVENT_EXECUTOR_COMPLETED,
                            "message": "HTTP route completed another review task.",
                            "payload": {
                                "physical_route": "local-http",
                                "logical_model": "http-default",
                                "task_family": "review",
                                "latency_ms": 12,
                                "token_cost": 0.0,
                                "degraded": False,
                            },
                        },
                    ],
                )

                snapshot, _artifact_path, _report = run_meta_optimizer(base_dir, last_n=100)
                proposal = next(
                    proposal
                    for proposal in snapshot.proposals
                    if proposal.proposal_type == "route_capability"
                    and proposal.route_name == "local-http"
                    and proposal.task_family == "review"
                    and not proposal.mark_task_family_unsupported
                )
                bundle_path = latest_optimization_proposal_bundle_path(base_dir)
                review_record, review_path = review_optimization_proposals(
                    base_dir,
                    bundle_path,
                    "approved",
                    proposal_ids=[proposal.proposal_id],
                    note="Apply route capability score.",
                )
                self.assertEqual(review_record.entries[0].task_family, "review")

                application_record, _application_path = apply_reviewed_optimization_proposals(base_dir, review_path)

                self.assertEqual(application_record.applied_count, 1)
                self.assertEqual(application_record.route_capabilities_path, str(route_capabilities_path(base_dir)))
                self.assertEqual(
                    application_record.rollback_capability_profiles["local-http"]["task_family_scores"],
                    {},
                )
                self.assertEqual(
                    application_record.rollback_capability_profiles["local-http"]["unsupported_task_types"],
                    [],
                )
                persisted_profiles = json.loads(route_capabilities_path(base_dir).read_text(encoding="utf-8"))
                self.assertAlmostEqual(
                    persisted_profiles["local-http"]["task_family_scores"]["review"],
                    proposal.suggested_task_family_score or 0.0,
                    places=2,
                )
                apply_route_capability_profiles(base_dir)
                self.assertAlmostEqual(route.task_family_scores["review"], proposal.suggested_task_family_score or 0.0, places=2)
        finally:
            route.task_family_scores = original_scores
            route.unsupported_task_types = original_unsupported

    def test_review_and_apply_approved_route_capability_boundary_proposals(self) -> None:
        route = route_by_name("local-codex")
        self.assertIsNotNone(route)
        assert route is not None
        original_scores = dict(route.task_family_scores)
        original_unsupported = list(route.unsupported_task_types)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                base_dir = Path(tmp)
                task_dir = base_dir / ".swl" / "tasks" / "capability-boundary-task"
                _write_events(
                    task_dir,
                    [
                        {
                            "task_id": "capability-boundary-task",
                            "event_type": EVENT_EXECUTOR_FAILED,
                            "message": "Codex failed review task.",
                            "payload": {
                                "physical_route": "local-codex",
                                "logical_model": "codex",
                                "task_family": "review",
                                "latency_ms": 11,
                                "token_cost": 0.0,
                                "degraded": False,
                                "failure_kind": "execution_error",
                                "error_code": "execution_error",
                            },
                        },
                        {
                            "task_id": "capability-boundary-task",
                            "event_type": EVENT_EXECUTOR_FAILED,
                            "message": "Codex failed review task again.",
                            "payload": {
                                "physical_route": "local-codex",
                                "logical_model": "codex",
                                "task_family": "review",
                                "latency_ms": 9,
                                "token_cost": 0.0,
                                "degraded": False,
                                "failure_kind": "execution_error",
                                "error_code": "execution_error",
                            },
                        },
                    ],
                )

                snapshot, _artifact_path, _report = run_meta_optimizer(base_dir, last_n=100)
                proposal = next(
                    proposal
                    for proposal in snapshot.proposals
                    if proposal.proposal_type == "route_capability"
                    and proposal.route_name == "local-codex"
                    and proposal.task_family == "review"
                    and proposal.mark_task_family_unsupported
                )
                bundle_path = latest_optimization_proposal_bundle_path(base_dir)
                _review_record, review_path = review_optimization_proposals(
                    base_dir,
                    bundle_path,
                    "approved",
                    proposal_ids=[proposal.proposal_id],
                    note="Apply route capability boundary.",
                )

                application_record, _application_path = apply_reviewed_optimization_proposals(base_dir, review_path)

                self.assertEqual(application_record.applied_count, 1)
                self.assertEqual(
                    application_record.rollback_capability_profiles["local-codex"]["unsupported_task_types"],
                    [],
                )
                persisted_profiles = json.loads(route_capabilities_path(base_dir).read_text(encoding="utf-8"))
                self.assertEqual(persisted_profiles["local-codex"]["unsupported_task_types"], ["review"])
                apply_route_capability_profiles(base_dir)
                self.assertEqual(route.unsupported_task_types, ["review"])
        finally:
            route.task_family_scores = original_scores
            route.unsupported_task_types = original_unsupported

    def test_meta_optimizer_agent_execute_returns_structured_snapshot_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task_dir = base_dir / ".swl" / "tasks" / "agent-task"
            _write_events(
                task_dir,
                [
                    {
                        "task_id": "agent-task",
                        "event_type": EVENT_EXECUTOR_FAILED,
                        "message": "HTTP route failed.",
                        "payload": {
                            "physical_route": "http-claude",
                            "logical_model": "claude",
                            "task_family": "review",
                            "latency_ms": 42,
                            "token_cost": 0.13,
                            "degraded": False,
                            "failure_kind": "timeout",
                            "error_code": "timeout",
                        },
                    }
                ],
            )

            state = load_state(
                base_dir,
                create_task(
                    base_dir=base_dir,
                    title="Analyze telemetry",
                    goal="Generate read-only optimization proposals",
                    workspace_root=base_dir,
                    executor_name="meta-optimizer",
                ).task_id,
            )
            state.executor_name = "meta-optimizer"
            state.route_name = "meta-optimizer-local"
            card = TaskCard(
                card_id="card-meta-optimizer",
                goal=state.goal,
                parent_task_id=state.task_id,
                input_context={"last_n": 25},
                output_schema={"const": {"kind": "meta_optimizer_snapshot_v0"}},
            )

            result = MetaOptimizerAgent().execute(base_dir, state, card, [])

            self.assertEqual(result.status, "completed")
            self.assertEqual(result.executor_name, "meta-optimizer")
            payload = json.loads(result.output)
            self.assertEqual(payload["kind"], "meta_optimizer_snapshot_v0")
            self.assertEqual(payload["agent_name"], "meta-optimizer")
            self.assertEqual(payload["memory_authority"], "canonical-write-forbidden")
            self.assertEqual(payload["snapshot"]["task_limit"], 25)
            self.assertTrue(payload["snapshot"]["proposals"])
            self.assertTrue(payload["snapshot"]["route_task_family_stats"])
            self.assertTrue(Path(result.side_effects["bundle_path"]).exists())
            self.assertTrue(Path(result.side_effects["report_artifact"]).exists())

    def test_meta_optimizer_agent_execute_async_uses_same_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task_dir = base_dir / ".swl" / "tasks" / "agent-async"
            _write_events(
                task_dir,
                [
                    {
                        "task_id": "agent-async",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
                        "message": "Local summary completed.",
                        "payload": {
                            "physical_route": "local-summary",
                            "logical_model": "local",
                            "task_family": "execution",
                            "latency_ms": 4,
                            "token_cost": 0.0,
                            "degraded": False,
                            "error_code": "",
                        },
                    }
                ],
            )
            state = load_state(
                base_dir,
                create_task(
                    base_dir=base_dir,
                    title="Analyze telemetry async",
                    goal="Generate read-only optimization proposals asynchronously",
                    workspace_root=base_dir,
                    executor_name="meta-optimizer",
                ).task_id,
            )
            state.executor_name = "meta-optimizer"
            card = TaskCard(card_id="card-meta-optimizer-async", goal=state.goal, parent_task_id=state.task_id)

            result = asyncio.run(MetaOptimizerAgent().execute_async(base_dir, state, card, []))

            self.assertEqual(result.status, "completed")
            payload = json.loads(result.output)
            self.assertEqual(payload["kind"], "meta_optimizer_snapshot_v0")
            self.assertIn("snapshot", payload)

    def test_run_task_executes_meta_optimizer_agent_via_executor_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task_dir = base_dir / ".swl" / "tasks" / "meta-runtime"
            _write_events(
                task_dir,
                [
                    {
                        "task_id": "meta-runtime",
                        "event_type": EVENT_EXECUTOR_FAILED,
                        "message": "Codex route failed.",
                        "payload": {
                            "physical_route": "local-codex",
                            "logical_model": "codex",
                            "task_family": "execution",
                            "latency_ms": 11,
                            "token_cost": 0.0,
                            "degraded": False,
                            "failure_kind": "launch_error",
                            "error_code": "launch_error",
                        },
                    }
                ],
            )
            created = create_task(
                base_dir=base_dir,
                title="Run meta optimizer agent",
                goal="Analyze recent telemetry via the specialist agent runtime",
                workspace_root=base_dir,
                executor_name="local",
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
            route_selection = RouteSelection(
                route=RouteSpec(
                    name="meta-optimizer-local",
                    executor_name="meta-optimizer",
                    backend_kind="specialist_meta_optimizer",
                    model_hint="local",
                    dialect_hint="plain_text",
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
                reason="Route meta-optimizer tasks to the specialist agent.",
                policy_inputs={},
            )

            with patch("swallow.orchestrator.run_retrieval", return_value=[]):
                with patch("swallow.orchestrator.select_route", return_value=route_selection):
                    with patch("swallow.orchestrator.write_task_artifacts", return_value=validation_tuple):
                        final_state = run_task(base_dir, created.task_id, executor_name="meta-optimizer")

            self.assertEqual(final_state.status, "completed")
            self.assertEqual(final_state.executor_name, "meta-optimizer")
            self.assertEqual(final_state.route_name, "meta-optimizer-local")
            self.assertTrue(latest_optimization_proposal_bundle_path(base_dir).exists())

    def test_run_meta_optimizer_generates_cost_proposals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task_a = base_dir / ".swl" / "tasks" / "cost-a"
            task_b = base_dir / ".swl" / "tasks" / "cost-b"
            task_c = base_dir / ".swl" / "tasks" / "cost-c"
            _write_events(
                task_a,
                [
                    {
                        "task_id": "cost-a",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
                        "message": "Claude review done.",
                        "payload": {
                            "physical_route": "api-claude-review",
                            "logical_model": "claude",
                            "task_family": "review",
                            "latency_ms": 30,
                            "token_cost": 0.12,
                            "degraded": False,
                            "error_code": "",
                        },
                    },
                    {
                        "task_id": "cost-a",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
                        "message": "Claude review done again.",
                        "payload": {
                            "physical_route": "api-claude-review",
                            "logical_model": "claude",
                            "task_family": "review",
                            "latency_ms": 35,
                            "token_cost": 0.18,
                            "degraded": False,
                            "error_code": "",
                        },
                    },
                ],
            )
            _write_events(
                task_b,
                [
                    {
                        "task_id": "cost-b",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
                        "message": "Claude review spiked.",
                        "payload": {
                            "physical_route": "api-claude-review",
                            "logical_model": "claude",
                            "task_family": "review",
                            "latency_ms": 36,
                            "token_cost": 0.42,
                            "degraded": False,
                            "error_code": "",
                        },
                    },
                    {
                        "task_id": "cost-b",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
                        "message": "Claude review spiked again.",
                        "payload": {
                            "physical_route": "api-claude-review",
                            "logical_model": "claude",
                            "task_family": "review",
                            "latency_ms": 39,
                            "token_cost": 0.48,
                            "degraded": False,
                            "error_code": "",
                        },
                    },
                ],
            )
            _write_events(
                task_c,
                [
                    {
                        "task_id": "cost-c",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
                        "message": "Local review summary done.",
                        "payload": {
                            "physical_route": "local-summary-review",
                            "logical_model": "local",
                            "task_family": "review",
                            "latency_ms": 5,
                            "token_cost": 0.0,
                            "degraded": False,
                            "error_code": "",
                        },
                    },
                ],
            )

            snapshot, _artifact_path, report = run_meta_optimizer(base_dir, last_n=100)
            expensive_route = next(stats for stats in snapshot.route_stats if stats.route_name == "api-claude-review")
            self.assertAlmostEqual(expensive_route.total_cost, 1.2)
            self.assertAlmostEqual(expensive_route.average_cost(), 0.3)
            self.assertTrue(any(proposal.severity == "warn" for proposal in snapshot.proposals))
            self.assertIn("api-claude-review: total_cost=$1.200000 avg_cost=$0.300000 task_families=review", report)
            self.assertIn(
                "Review route `api-claude-review`: average estimated cost is $0.30/task across 4 executor events.",
                report,
            )
            self.assertIn(
                "Compare cost for task_family `review`: route `api-claude-review` averages $0.30/task versus `local-summary-review` at $0.00/task.",
                report,
            )
            self.assertIn(
                "Watch cost trend on `api-claude-review`: recent estimated cost rose from $0.15 to $0.45 per executor event.",
                report,
            )

    def test_run_meta_optimizer_counts_fallback_token_cost_on_previous_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task_dir = base_dir / ".swl" / "tasks" / "fallback-cost"
            _write_events(
                task_dir,
                [
                    {
                        "task_id": "fallback-cost",
                        "event_type": EVENT_EXECUTOR_FAILED,
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
                        "task_id": "fallback-cost",
                        "event_type": EVENT_TASK_EXECUTION_FALLBACK,
                        "message": "Fallback executed.",
                        "payload": {
                            "previous_route_name": "local-codex",
                            "fallback_route_name": "local-summary",
                            "latency_ms": 4,
                            "degraded": True,
                            "token_cost": 0.25,
                        },
                    },
                    {
                        "task_id": "fallback-cost",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
                        "message": "Fallback completed.",
                        "payload": {
                            "physical_route": "local-summary",
                            "logical_model": "local",
                            "task_family": "execution",
                            "latency_ms": 4,
                            "token_cost": 0.0,
                            "degraded": True,
                            "error_code": "",
                        },
                    },
                ],
            )

            snapshot = build_meta_optimizer_snapshot(base_dir, last_n=100)
            previous_route = next(stats for stats in snapshot.route_stats if stats.route_name == "local-codex")

            self.assertEqual(previous_route.fallback_trigger_count, 1)
            self.assertAlmostEqual(previous_route.total_cost, 0.25)
            self.assertEqual(previous_route.cost_samples, [0.0, 0.25])
            self.assertAlmostEqual(previous_route.average_cost(), 0.25)

    def test_run_meta_optimizer_generates_workflow_proposals_from_task_family_signals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task_dir = base_dir / ".swl" / "tasks" / "workflow-audit"
            _write_events(
                task_dir,
                [
                    {
                        "task_id": "workflow-audit",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
                        "message": "Initial review finished.",
                        "payload": {
                            "physical_route": "http-claude",
                            "logical_model": "claude",
                            "task_family": "review",
                            "latency_ms": 24,
                            "token_cost": 0.12,
                            "degraded": False,
                            "error_code": "",
                        },
                    },
                    {
                        "task_id": "workflow-audit",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
                        "message": "Retry review finished.",
                        "payload": {
                            "physical_route": "http-claude",
                            "logical_model": "claude",
                            "task_family": "review",
                            "latency_ms": 26,
                            "token_cost": 0.18,
                            "degraded": False,
                            "error_code": "",
                            "review_feedback": "Needs another pass.",
                        },
                    },
                    {
                        "task_id": "workflow-audit",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
                        "message": "Retry review finished again.",
                        "payload": {
                            "physical_route": "http-qwen",
                            "logical_model": "qwen",
                            "task_family": "review",
                            "latency_ms": 18,
                            "token_cost": 0.2,
                            "degraded": False,
                            "error_code": "",
                            "review_feedback": "Still needs another pass.",
                        },
                    },
                    {
                        "task_id": "workflow-audit",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
                        "message": "Execution completed cheaply.",
                        "payload": {
                            "physical_route": "local-summary",
                            "logical_model": "local",
                            "task_family": "execution",
                            "latency_ms": 4,
                            "token_cost": 0.01,
                            "degraded": False,
                            "error_code": "",
                        },
                    },
                ],
            )

            snapshot = build_meta_optimizer_snapshot(base_dir, last_n=100)
            workflow_descriptions = [
                proposal.description for proposal in snapshot.proposals if proposal.proposal_type == "workflow"
            ]

            self.assertIn(
                "Review workflow for task_family `review`: debate retry rate is 67% over 3 attempts.",
                workflow_descriptions,
            )
            self.assertIn(
                "Review workflow cost for task_family `review`: average estimated cost is $0.17/attempt versus median $0.01.",
                workflow_descriptions,
            )

    def test_run_meta_optimizer_isolates_debate_retry_from_route_health(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task_dir = base_dir / ".swl" / "tasks" / "debate-retry"
            _write_events(
                task_dir,
                [
                    {
                        "task_id": "debate-retry",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
                        "message": "Primary execution completed.",
                        "payload": {
                            "physical_route": "api-claude-review",
                            "logical_model": "claude",
                            "task_family": "review",
                            "latency_ms": 20,
                            "token_cost": 0.10,
                            "degraded": False,
                            "error_code": "",
                            "review_feedback": "",
                        },
                    },
                    {
                        "task_id": "debate-retry",
                        "event_type": EVENT_EXECUTOR_FAILED,
                        "message": "Debate retry failed review again.",
                        "payload": {
                            "physical_route": "api-claude-review",
                            "logical_model": "claude",
                            "task_family": "review",
                            "latency_ms": 40,
                            "token_cost": 0.30,
                            "degraded": True,
                            "failure_kind": "output_schema",
                            "error_code": "output_schema",
                            "review_feedback": "artifacts/review_feedback_round_1.json",
                        },
                    },
                ],
            )

            snapshot, _artifact_path, report = run_meta_optimizer(base_dir, last_n=100)
            route = next(stats for stats in snapshot.route_stats if stats.route_name == "api-claude-review")

            self.assertEqual(route.event_count, 1)
            self.assertEqual(route.success_count, 1)
            self.assertEqual(route.failure_count, 0)
            self.assertEqual(route.debate_retry_count, 1)
            self.assertEqual(route.degraded_count, 0)
            self.assertAlmostEqual(route.total_cost, 0.40)
            self.assertEqual(route.total_latency_ms, 60)
            self.assertAlmostEqual(route.average_cost(), 0.20)
            self.assertEqual(route.average_latency_ms(), 30)
            self.assertEqual(snapshot.failure_fingerprints, [])
            self.assertIn(
                "api-claude-review: success_rate=100% failure_rate=0% fallback_rate=0% debate_retry=1",
                report,
            )

    def test_run_meta_optimizer_generates_route_weight_proposal_for_unhealthy_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task_dir = base_dir / ".swl" / "tasks" / "weight-proposal"
            _write_events(
                task_dir,
                [
                    {
                        "task_id": "weight-proposal",
                        "event_type": EVENT_EXECUTOR_FAILED,
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
                        "task_id": "weight-proposal",
                        "event_type": EVENT_EXECUTOR_FAILED,
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
                        "task_id": "weight-proposal",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
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

            snapshot, _artifact_path, report = run_meta_optimizer(base_dir, last_n=100)
            route_weight_proposals = [
                proposal for proposal in snapshot.proposals if proposal.proposal_type == "route_weight"
            ]

            self.assertEqual(len(route_weight_proposals), 1)
            self.assertEqual(route_weight_proposals[0].route_name, "local-codex")
            self.assertAlmostEqual(route_weight_proposals[0].suggested_weight or 0.0, 0.33, places=2)
            self.assertIn(
                "Route weight suggestion for `local-codex`: set quality weight to 0.33 based on failure rate 67%.",
                report,
            )

    def test_run_meta_optimizer_handles_empty_task_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)

            snapshot, artifact_path, report = run_meta_optimizer(base_dir, last_n=100)
            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--base-dir", str(base_dir), "meta-optimize"]), 0)
            self.assertEqual(snapshot.scanned_task_ids, [])
            self.assertTrue(artifact_path.exists())
            self.assertIn("- no data", report)
            self.assertIn("# Meta-Optimizer Proposals", stdout.getvalue())
            self.assertIn("artifact:", stdout.getvalue())

    def test_meta_optimizer_scan_is_read_only_for_task_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task_dir = base_dir / ".swl" / "tasks" / "readonly-task"
            task_dir.mkdir(parents=True, exist_ok=True)
            state_path = task_dir / "state.json"
            events_path = task_dir / "events.jsonl"
            state_path.write_text(json.dumps({"task_id": "readonly-task", "status": "completed"}) + "\n", encoding="utf-8")
            events_path.write_text(
                json.dumps(
                    {
                        "task_id": "readonly-task",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
                        "message": "Completed.",
                        "payload": {
                            "physical_route": "local-summary",
                            "logical_model": "local",
                            "task_family": "execution",
                            "latency_ms": 3,
                            "token_cost": 0.0,
                            "degraded": False,
                            "error_code": "",
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            original_state = state_path.read_text(encoding="utf-8")
            original_events = events_path.read_text(encoding="utf-8")

            snapshot = build_meta_optimizer_snapshot(base_dir, last_n=100)
            _, artifact_path, _report = run_meta_optimizer(base_dir, last_n=100)
            self.assertEqual(snapshot.scanned_task_ids, ["readonly-task"])
            self.assertEqual(state_path.read_text(encoding="utf-8"), original_state)
            self.assertEqual(events_path.read_text(encoding="utf-8"), original_events)
            self.assertTrue(artifact_path.exists())

    def test_cli_route_weights_apply_uses_meta_optimizer_proposal_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task_dir = base_dir / ".swl" / "tasks" / "apply-weight"
            _write_events(
                task_dir,
                [
                    {
                        "task_id": "apply-weight",
                        "event_type": EVENT_EXECUTOR_FAILED,
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
                        "task_id": "apply-weight",
                        "event_type": EVENT_EXECUTOR_FAILED,
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
                        "task_id": "apply-weight",
                        "event_type": EVENT_EXECUTOR_COMPLETED,
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

            _, artifact_path, _report = run_meta_optimizer(base_dir, last_n=100)
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--base-dir",
                        str(base_dir),
                        "route",
                        "weights",
                        "apply",
                        str(artifact_path),
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertTrue(route_weights_path(base_dir).exists())
            persisted = json.loads(route_weights_path(base_dir).read_text(encoding="utf-8"))
            self.assertEqual(persisted["local-codex"], 0.33)
            self.assertIn("local-codex: 0.330000", stdout.getvalue())

            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--base-dir",
                        str(base_dir),
                        "route",
                        "weights",
                        "show",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("local-codex: 0.330000", stdout.getvalue())
            self.assertAlmostEqual(route_by_name("local-codex").quality_weight, 0.33, places=2)

        with tempfile.TemporaryDirectory() as reset_tmp:
            apply_route_weights(Path(reset_tmp))


if __name__ == "__main__":
    unittest.main()
