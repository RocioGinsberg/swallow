from __future__ import annotations

import json
from pathlib import Path

from swallow.provider_router.router import load_route_weights, route_by_name
from swallow.application.services.meta_optimizer import load_optimization_proposal_bundle
from swallow.application.infrastructure.paths import latest_optimization_proposal_bundle_path, route_weights_path
from tests.helpers.cli_runner import run_cli


def _write_events(task_dir: Path, records: list[dict[str, object]]) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "events.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


def test_proposal_review_apply_characterization_stdout_stderr_exit_code(tmp_path: Path) -> None:
    route = route_by_name("local-codex")
    assert route is not None
    original_weight = route.quality_weight
    try:
        _write_events(
            tmp_path / ".swl" / "tasks" / "cli-proposal-task",
            [
                {
                    "task_id": "cli-proposal-task",
                    "event_type": "executor.failed",
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
                    "task_id": "cli-proposal-task",
                    "event_type": "executor.failed",
                    "message": "Local codex failed again.",
                    "payload": {
                        "physical_route": "local-codex",
                        "logical_model": "codex",
                        "task_family": "execution",
                        "latency_ms": 9,
                        "token_cost": 0.0,
                        "degraded": False,
                        "failure_kind": "launch_error",
                        "error_code": "launch_error",
                    },
                },
            ],
        )
        optimize_result = run_cli(tmp_path, "meta-optimize", "--last-n", "100")
        optimize_result.assert_success()

        bundle_path = latest_optimization_proposal_bundle_path(tmp_path)
        bundle = load_optimization_proposal_bundle(bundle_path)
        route_weight = next(
            proposal
            for proposal in bundle.proposals
            if proposal.proposal_type == "route_weight" and proposal.route_name == "local-codex"
        )

        review_result = run_cli(
            tmp_path,
            "proposal",
            "review",
            str(bundle_path),
            "--decision",
            "approved",
            "--proposal-id",
            route_weight.proposal_id,
            "--note",
            "CLI review approval.",
        )

        review_result.assert_success()
        assert review_result.stderr == ""
        assert "# Proposal Review Record" in review_result.stdout
        assert "review_id:" in review_result.stdout
        assert f"{route_weight.proposal_id}: decision=approved type=route_weight" in review_result.stdout
        review_record_path = next(
            line.removeprefix("record: ").strip()
            for line in review_result.stdout.splitlines()
            if line.startswith("record: ")
        )

        apply_result = run_cli(tmp_path, "proposal", "apply", review_record_path)

        apply_result.assert_success()
        assert apply_result.stderr == ""
        assert "# Proposal Application Record" in apply_result.stdout
        assert "applied_count: 1" in apply_result.stdout
        assert "noop_count: 0" in apply_result.stdout
        assert "skipped_count: 0" in apply_result.stdout
        assert "record: " in apply_result.stdout
        persisted_weights = load_route_weights(tmp_path)
        assert round(persisted_weights["local-codex"], 2) == round(route_weight.suggested_weight or 1.0, 2)
        assert not route_weights_path(tmp_path).exists()
    finally:
        route.quality_weight = original_weight


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


class LegacyCliProposalCommandTest(unittest.TestCase):
    def test_proposal_review_and_apply_cli_flow(self) -> None:
        route = route_by_name("local-codex")
        self.assertIsNotNone(route)
        assert route is not None
        original_weight = route.quality_weight
        try:
            with tempfile.TemporaryDirectory() as tmp:
                base_dir = Path(tmp)
                task_dir = base_dir / ".swl" / "tasks" / "cli-proposal-task"
                task_dir.mkdir(parents=True, exist_ok=True)
                (task_dir / "events.jsonl").write_text(
                    "".join(
                        json.dumps(record) + "\n"
                        for record in [
                            {
                                "task_id": "cli-proposal-task",
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
                                "task_id": "cli-proposal-task",
                                "event_type": EVENT_EXECUTOR_FAILED,
                                "message": "Local codex failed again.",
                                "payload": {
                                    "physical_route": "local-codex",
                                    "logical_model": "codex",
                                    "task_family": "execution",
                                    "latency_ms": 9,
                                    "token_cost": 0.0,
                                    "degraded": False,
                                    "failure_kind": "launch_error",
                                    "error_code": "launch_error",
                                },
                            },
                        ]
                    ),
                    encoding="utf-8",
                )

                optimize_stdout = StringIO()
                with redirect_stdout(optimize_stdout):
                    exit_code = main(["--base-dir", str(base_dir), "meta-optimize", "--last-n", "100"])
                self.assertEqual(exit_code, 0)
                self.assertIn("proposal_bundle:", optimize_stdout.getvalue())

                bundle_path = latest_optimization_proposal_bundle_path(base_dir)
                bundle = load_optimization_proposal_bundle(bundle_path)
                route_weight = next(
                    proposal
                    for proposal in bundle.proposals
                    if proposal.proposal_type == "route_weight" and proposal.route_name == "local-codex"
                )

                review_stdout = StringIO()
                with redirect_stdout(review_stdout):
                    exit_code = main(
                        [
                            "--base-dir",
                            str(base_dir),
                            "proposal",
                            "review",
                            str(bundle_path),
                            "--decision",
                            "approved",
                            "--proposal-id",
                            route_weight.proposal_id,
                            "--note",
                            "CLI review approval.",
                        ]
                    )
                self.assertEqual(exit_code, 0)
                self.assertIn("review_id:", review_stdout.getvalue())
                review_record_path = next(
                    line.removeprefix("record: ").strip()
                    for line in review_stdout.getvalue().splitlines()
                    if line.startswith("record: ")
                )

                apply_stdout = StringIO()
                with redirect_stdout(apply_stdout):
                    exit_code = main(
                        [
                            "--base-dir",
                            str(base_dir),
                            "proposal",
                            "apply",
                            review_record_path,
                        ]
                    )
                self.assertEqual(exit_code, 0)
                self.assertIn("applied_count: 1", apply_stdout.getvalue())
                persisted_weights = load_route_weights(base_dir)
                self.assertAlmostEqual(
                    persisted_weights["local-codex"],
                    route_weight.suggested_weight or 1.0,
                    places=2,
                )
                self.assertFalse(route_weights_path(base_dir).exists())
        finally:
            route.quality_weight = original_weight

    def test_proposal_apply_cli_persists_route_capability_profile(self) -> None:
        route = route_by_name("local-http")
        self.assertIsNotNone(route)
        assert route is not None
        original_scores = dict(route.task_family_scores)
        original_unsupported = list(route.unsupported_task_types)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                base_dir = Path(tmp)
                task_dir = base_dir / ".swl" / "tasks" / "cli-capability-task"
                task_dir.mkdir(parents=True, exist_ok=True)
                (task_dir / "events.jsonl").write_text(
                    "".join(
                        json.dumps(record) + "\n"
                        for record in [
                            {
                                "task_id": "cli-capability-task",
                                "event_type": "executor.completed",
                                "message": "HTTP route completed review task.",
                                "payload": {
                                    "physical_route": "local-http",
                                    "logical_model": "http-default",
                                    "task_family": "review",
                                    "latency_ms": 12,
                                    "token_cost": 0.0,
                                    "degraded": False,
                                },
                            },
                            {
                                "task_id": "cli-capability-task",
                                "event_type": "executor.completed",
                                "message": "HTTP route completed another review task.",
                                "payload": {
                                "physical_route": "local-http",
                                "logical_model": "http-default",
                                "task_family": "review",
                                "latency_ms": 9,
                                "token_cost": 0.0,
                                "degraded": True,
                            },
                        },
                        ]
                    ),
                    encoding="utf-8",
                )

                optimize_stdout = StringIO()
                with redirect_stdout(optimize_stdout):
                    exit_code = main(["--base-dir", str(base_dir), "meta-optimize", "--last-n", "100"])
                self.assertEqual(exit_code, 0)

                bundle_path = latest_optimization_proposal_bundle_path(base_dir)
                bundle = load_optimization_proposal_bundle(bundle_path)
                capability_proposal = next(
                    proposal
                    for proposal in bundle.proposals
                    if proposal.proposal_type == "route_capability"
                    and proposal.route_name == "local-http"
                    and proposal.task_family == "review"
                    and not proposal.mark_task_family_unsupported
                )

                review_stdout = StringIO()
                with redirect_stdout(review_stdout):
                    exit_code = main(
                        [
                            "--base-dir",
                            str(base_dir),
                            "proposal",
                            "review",
                            str(bundle_path),
                            "--decision",
                            "approved",
                            "--proposal-id",
                            capability_proposal.proposal_id,
                            "--note",
                            "CLI review approval for route capability.",
                        ]
                    )
                self.assertEqual(exit_code, 0)
                review_record_path = next(
                    line.removeprefix("record: ").strip()
                    for line in review_stdout.getvalue().splitlines()
                    if line.startswith("record: ")
                )

                apply_stdout = StringIO()
                with redirect_stdout(apply_stdout):
                    exit_code = main(
                        [
                            "--base-dir",
                            str(base_dir),
                            "proposal",
                            "apply",
                            review_record_path,
                        ]
                    )
                self.assertEqual(exit_code, 0)
                self.assertIn("applied_count: 1", apply_stdout.getvalue())
                persisted_profiles = load_route_capability_profiles(base_dir)
                self.assertAlmostEqual(
                    persisted_profiles["local-http"]["task_family_scores"]["review"],
                    capability_proposal.suggested_task_family_score or 0.0,
                    places=2,
                )
                self.assertFalse(route_capabilities_path(base_dir).exists())
        finally:
            route.task_family_scores = original_scores
            route.unsupported_task_types = original_unsupported
