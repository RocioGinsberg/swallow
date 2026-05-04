from __future__ import annotations

import json
from pathlib import Path

from swallow.knowledge_retrieval.knowledge_plane import list_staged_knowledge as load_staged_candidates
from swallow.orchestration.orchestrator import create_task
from swallow.orchestration.models import ExecutorResult
from swallow.application.services.mps_policy_store import read_mps_policy
from swallow.application.infrastructure.paths import artifacts_dir, mps_policy_path
from tests.helpers.cli_runner import run_cli


def test_synthesis_policy_set_writes_mps_policy(tmp_path: Path) -> None:
    result = run_cli(
        tmp_path,
        "synthesis",
        "policy",
        "set",
        "--kind",
        "mps_round_limit",
        "--value",
        "3",
    )

    result.assert_success()
    assert "mps_round_limit: 3" in result.stdout
    assert read_mps_policy(tmp_path, "mps_round_limit") == 3
    assert not mps_policy_path(tmp_path).exists()


def test_synthesis_run_and_stage_characterization_stdout_stderr_exit_code(tmp_path: Path, monkeypatch) -> None:
    state = create_task(
        base_dir=tmp_path,
        title="MPS baseline",
        goal="Freeze synthesis run and stage behavior before CLI migration.",
        workspace_root=tmp_path,
    )
    config_path = tmp_path / "synthesis-config.json"
    config_path.write_text(
        json.dumps(
            {
                "config_id": "config-mps",
                "rounds": 1,
                "participants": [
                    {
                        "participant_id": "participant-1",
                        "role_prompt": "Consider the baseline route.",
                    }
                ],
                "arbiter": {
                    "participant_id": "arbiter",
                    "role_prompt": "Resolve the synthesis result.",
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    def _mock_http_executor(state, retrieval_items, prompt=None, **kwargs):
        del state, retrieval_items, kwargs
        return ExecutorResult(
            executor_name="http",
            status="completed",
            message="HTTP executor completed.",
            output=f"synthesized: {str(prompt or '').splitlines()[0]}",
        )

    monkeypatch.setattr("swallow.orchestration.synthesis.run_http_executor", _mock_http_executor)

    run_result = run_cli(tmp_path, "synthesis", "run", "--task", state.task_id, "--config", str(config_path))

    run_result.assert_success()
    assert run_result.stderr == ""
    assert f"{state.task_id} synthesis_completed config_id=config-mps" in run_result.stdout
    assert "artifact=" in run_result.stdout
    arbitration_path = artifacts_dir(tmp_path, state.task_id) / "synthesis_arbitration.json"
    assert arbitration_path.exists()

    stage_result = run_cli(tmp_path, "synthesis", "stage", "--task", state.task_id)

    stage_result.assert_success()
    assert stage_result.stderr == ""
    assert "synthesis_staged config_id=config-mps" in stage_result.stdout
    staged = load_staged_candidates(tmp_path)
    assert len(staged) == 1
    assert staged[0].source_kind == "synthesis"
    assert staged[0].source_object_id == "config-mps"


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


class LegacyCliSynthesisCommandTest(unittest.TestCase):
    def test_synthesis_stage_rejects_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            state = TaskState(
                task_id="task-mps",
                title="MPS",
                goal="Stage synthesis.",
                workspace_root=".",
            )
            save_state(base_dir, state)
            arbitration_path = artifacts_dir(base_dir, state.task_id) / "synthesis_arbitration.json"
            arbitration_path.write_text(
                json.dumps(
                    {
                        "schema": "synthesis_arbitration_v1",
                        "config_id": "config-mps",
                        "task_id": state.task_id,
                        "arbiter_decision": {
                            "synthesis_summary": "Keep the operator-visible candidate.",
                            "rationale": "The arbiter selected the stable path.",
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            stdout = StringIO()

            with redirect_stdout(stdout):
                self.assertEqual(
                    main(["--base-dir", str(base_dir), "synthesis", "stage", "--task", state.task_id]),
                    0,
                )
            self.assertIn("synthesis_staged", stdout.getvalue())
            candidates = load_staged_candidates(base_dir)
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0].source_kind, "synthesis")
            self.assertEqual(candidates[0].source_object_id, "config-mps")

            stderr = StringIO()
            with redirect_stderr(stderr):
                exit_code = main(["--base-dir", str(base_dir), "synthesis", "stage", "--task", state.task_id])

            self.assertEqual(exit_code, 1)
            self.assertIn("already staged", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())
