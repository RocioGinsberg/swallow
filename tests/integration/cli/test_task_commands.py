from __future__ import annotations

from pathlib import Path

from swallow.orchestration.orchestrator import create_task, load_state, run_task
from swallow.truth_governance.store import save_state
from tests.helpers.assertions import assert_cli_success
from tests.helpers.builders import TaskBuilder
from tests.helpers.cli_runner import run_cli


def test_task_create_and_list_characterization_stdout_stderr_exit_code(tmp_path: Path) -> None:
    create_result = run_cli(
        tmp_path,
        "task",
        "create",
        "--title",
        "Focused CLI task",
        "--goal",
        "Freeze task create output before dispatch migration.",
        "--executor",
        "note-only",
        "--route-mode",
        "offline",
    )

    assert_cli_success(create_result)
    task_id = create_result.stdout.strip()
    assert task_id
    state = load_state(tmp_path, task_id)
    assert state.title == "Focused CLI task"
    assert state.goal == "Freeze task create output before dispatch migration."
    assert state.executor_name == "note-only"
    assert state.route_mode == "offline"

    list_result = run_cli(tmp_path, "task", "list")

    assert_cli_success(list_result)
    assert "task_id\tstatus\tphase\tattempt\tupdated_at\ttitle\tfocus=all" in list_result.stdout
    assert task_id in list_result.stdout
    assert "Focused CLI task" in list_result.stdout


def test_task_acknowledge_characterization_stdout_stderr_exit_code(tmp_path: Path, task_builder: TaskBuilder) -> None:
    created = task_builder.create(
        title="Dispatch blocked task",
        goal="Allow operator acknowledgement from CLI.",
    )
    persisted = load_state(tmp_path, created.task_id)
    persisted.artifact_paths["task_semantics_json"] = "missing-artifact.md"
    save_state(tmp_path, persisted)
    blocked = run_task(tmp_path, created.task_id, executor_name="mock-remote")
    assert blocked.status == "dispatch_blocked"

    result = run_cli(tmp_path, "task", "acknowledge", created.task_id)

    assert_cli_success(result)
    assert f"{created.task_id} dispatch_acknowledged" in result.stdout
    assert "status=running" in result.stdout
    assert "phase=retrieval" in result.stdout
    assert "dispatch_status=acknowledged" in result.stdout


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


class LegacyCliTaskCommandTest(unittest.TestCase):
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
            with patch("swallow.application.commands.tasks.run_task") as run_task_mock:
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
            with patch("swallow.application.commands.tasks.run_task") as run_task_mock:
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
            with patch("swallow.application.commands.tasks.run_task") as run_task_mock:
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
            with patch("swallow.application.commands.tasks.run_task") as run_task_mock:
                with redirect_stdout(stdout):
                    self.assertEqual(main(["--base-dir", str(tmp_path), "task", "resume", task_id]), 1)

        run_task_mock.assert_not_called()
        self.assertIn("resume_blocked", stdout.getvalue())
        self.assertIn("checkpoint_state=review_ready", stdout.getvalue())
        self.assertIn("suggested_reason=completed_run_review", stdout.getvalue())

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
            with patch("swallow.application.commands.tasks.run_task") as run_task_mock:
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

    def test_task_falls_back_to_local_summary_when_aider_binary_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\nexecutor failure coverage\n", encoding="utf-8")

            with patch.dict(
                "os.environ",
                {"AIWF_AIDER_BIN": "definitely-not-a-real-aider-binary", "AIWF_EXECUTOR_MODE": "aider"},
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
                        "Exercise aider adapter failure handling",
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

                self.assertIn('"status": "completed"', state)
                self.assertIn("route_reason: Executor-level route fallback selected 'local-summary'", summary)
                self.assertIn("# Local Executor Update", executor_output)
                self.assertEqual(executor_stdout.strip(), "")
                self.assertEqual(executor_stderr.strip(), "")
                self.assertIn('"route_name": "local-summary"', state)
                self.assertIn('"route_is_fallback": true', state)
                self.assertEqual(memory["status"], "completed")

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

            with patch("swallow.orchestration.orchestrator.load_state", return_value=created):
                with patch("swallow.orchestration.orchestrator.save_state", side_effect=save_state_spy):
                    with patch("swallow.orchestration.orchestrator.append_event", side_effect=append_event_spy):
                        with patch("swallow.orchestration.orchestrator.run_retrieval", return_value=retrieval_items):
                            with patch("swallow.orchestration.orchestrator._execute_task_card", return_value=executor_result):
                                with patch("swallow.orchestration.orchestrator.write_task_artifacts", side_effect=write_artifacts_spy):
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

            with patch("swallow.orchestration.orchestrator.load_state", return_value=created):
                with patch("swallow.orchestration.orchestrator.select_route", return_value=validator_route):
                    with patch("swallow.orchestration.orchestrator.save_state"):
                        with patch("swallow.orchestration.orchestrator.append_event"):
                            with patch("swallow.orchestration.orchestrator.run_retrieval", return_value=[]):
                                with patch("swallow.orchestration.orchestrator._execute_task_card", side_effect=execute_task_card_spy):
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
                                        final_state = run_task(base_dir, created.task_id, executor_name="local")

        self.assertEqual(final_state.route_capabilities["filesystem_access"], "workspace_read")
        self.assertEqual(final_state.route_capabilities["supports_tool_loop"], False)
        self.assertEqual(final_state.route_capabilities["network_access"], "optional")
        self.assertEqual(captured_states[0].route_capabilities["filesystem_access"], "workspace_read")
        self.assertEqual(captured_states[0].route_capabilities["supports_tool_loop"], False)

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

            with patch("swallow.orchestration.orchestrator.load_state", return_value=created):
                with patch("swallow.orchestration.orchestrator.save_state"):
                    with patch("swallow.orchestration.orchestrator.append_event"):
                        with patch("swallow.orchestration.orchestrator.run_retrieval", return_value=[]):
                            with patch("swallow.orchestration.orchestrator._execute_task_card", side_effect=execute_task_card_spy):
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
                                    final_state = run_task(base_dir, created.task_id, executor_name="codex")

        self.assertEqual(final_state.route_capabilities["filesystem_access"], "workspace_write")
        self.assertEqual(final_state.route_capabilities["supports_tool_loop"], True)
        self.assertEqual(final_state.route_capabilities["network_access"], "optional")
        self.assertEqual(captured_states[0].route_capabilities["filesystem_access"], "workspace_write")
        self.assertEqual(captured_states[0].route_capabilities["supports_tool_loop"], True)

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

            with patch("swallow.orchestration.orchestrator.load_state", return_value=created):
                with patch("swallow.orchestration.orchestrator.save_state", side_effect=save_state_spy):
                    with patch("swallow.orchestration.orchestrator.append_event", side_effect=append_event_spy):
                        with patch("swallow.orchestration.orchestrator.run_retrieval", return_value=retrieval_items):
                            with patch("swallow.orchestration.orchestrator._execute_task_card", return_value=executor_result):
                                with patch("swallow.orchestration.orchestrator.write_task_artifacts", side_effect=write_artifacts_spy):
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
        self.assertEqual(events[4]["payload"]["source_types_requested"], ["repo", "notes", "knowledge"])
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
        self.assertEqual(events[8]["payload"]["token_cost"], 0.0)
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
        self.assertEqual(events[1]["payload"]["route_name"], "local-aider")
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
        self.assertEqual(events[8]["event_type"], "executor.completed")
        self.assertEqual(events[8]["payload"]["status"], "completed")
        self.assertEqual(events[8]["payload"]["executor_name"], "local")
        self.assertEqual(events[8]["payload"]["route_name"], "local-summary")
        self.assertEqual(events[8]["payload"]["route_execution_site"], "local")
        self.assertEqual(events[8]["payload"]["attempt_id"], "attempt-0001")
        self.assertEqual(events[8]["payload"]["attempt_number"], 1)
        self.assertEqual(events[8]["payload"]["topology_dispatch_status"], "local_dispatched")
        self.assertTrue(bool(events[8]["payload"]["dispatch_started_at"]))
        self.assertEqual(events[8]["payload"]["execution_lifecycle"], "dispatched")
        self.assertEqual(events[8]["payload"]["task_family"], "execution")
        self.assertEqual(events[8]["payload"]["logical_model"], "local")
        self.assertEqual(events[8]["payload"]["physical_route"], "local-summary")
        self.assertGreaterEqual(events[8]["payload"]["latency_ms"], 0)
        self.assertTrue(events[8]["payload"]["degraded"])
        self.assertGreaterEqual(events[8]["payload"]["token_cost"], 0.0)
        self.assertEqual(events[8]["payload"]["error_code"], "")
        self.assertEqual(events[9]["event_type"], "task.review_gate")
        self.assertEqual(events[9]["payload"]["status"], "passed")
        self.assertEqual(events[10]["event_type"], "task.phase_checkpoint")
        self.assertEqual(events[10]["payload"]["execution_phase"], "execution_done")
        self.assertEqual(events[12]["event_type"], "compatibility.completed")
        self.assertEqual(events[12]["payload"]["status"], "passed")
        self.assertEqual(events[13]["event_type"], "execution_fit.completed")
        self.assertEqual(events[13]["payload"]["status"], "passed")
        self.assertEqual(events[14]["event_type"], "knowledge_policy.completed")
        self.assertEqual(events[14]["payload"]["status"], "passed")
        self.assertEqual(events[15]["event_type"], "validation.completed")
        self.assertEqual(events[15]["payload"]["status"], "warning")
        self.assertEqual(events[16]["event_type"], "retry_policy.completed")
        self.assertEqual(events[16]["payload"]["status"], "passed")
        self.assertEqual(events[17]["event_type"], "execution_budget_policy.completed")
        self.assertEqual(events[17]["payload"]["status"], "passed")
        self.assertEqual(events[18]["event_type"], "stop_policy.completed")
        self.assertEqual(events[18]["payload"]["status"], "warning")
        self.assertEqual(events[19]["event_type"], "checkpoint_snapshot.completed")
        self.assertEqual(events[19]["payload"]["status"], "passed")
        self.assertEqual(events[21]["event_type"], "task.phase_checkpoint")
        self.assertEqual(events[21]["payload"]["execution_phase"], "analysis_done")
        self.assertEqual(events[-1]["payload"]["status"], "completed")
        self.assertEqual(events[-1]["payload"]["phase"], "summarize")
        self.assertEqual(events[-1]["payload"]["executor_status"], "completed")
        self.assertEqual(events[-1]["payload"]["route_name"], "local-summary")
        self.assertEqual(events[-1]["payload"]["route_execution_site"], "local")
        self.assertEqual(events[-1]["payload"]["route_remote_capable"], False)
        self.assertEqual(events[-1]["payload"]["compatibility_status"], "passed")
        self.assertEqual(events[-1]["payload"]["execution_fit_status"], "passed")
        self.assertEqual(events[-1]["payload"]["knowledge_policy_status"], "passed")
        self.assertEqual(events[-1]["payload"]["validation_status"], "warning")
        self.assertEqual(events[-1]["payload"]["retrieval_count"], 0)

    def test_repeat_run_records_attempt_boundary_and_resets_phase_to_intake(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notes = tmp_path / "notes.md"
            notes.write_text("# Notes\n\nrepeat run lifecycle\n", encoding="utf-8")

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

    def test_task_create_passes_document_paths_to_literature_specialist_input_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            doc_a = base_dir / "docs" / "a.md"
            doc_b = base_dir / "docs" / "b.md"
            doc_a.parent.mkdir(parents=True, exist_ok=True)
            doc_a.write_text("# A\n", encoding="utf-8")
            doc_b.write_text("# B\n", encoding="utf-8")
            stdout = StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--base-dir",
                        str(base_dir),
                        "task",
                        "create",
                        "--title",
                        "Literature specialist task",
                        "--goal",
                        "Inspect local literature inputs",
                        "--workspace-root",
                        str(base_dir),
                        "--executor",
                        "literature-specialist",
                        "--document-paths",
                        str(doc_a),
                        "--document-paths",
                        str(doc_b),
                    ]
                )

            self.assertEqual(exit_code, 0)
            task_id = stdout.getvalue().strip()
            state = load_state(base_dir, task_id)
            cards = plan(state)

        self.assertEqual(
            state.input_context["document_paths"],
            [str(doc_a.resolve()), str(doc_b.resolve())],
        )
        self.assertEqual(state.executor_name, "literature-specialist")
        self.assertEqual(
            cards[0].input_context["document_paths"],
            [str(doc_a.resolve()), str(doc_b.resolve())],
        )

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

            with patch("swallow.orchestration.orchestrator.load_state", return_value=created):
                with patch("swallow.orchestration.orchestrator.save_state", side_effect=save_state_spy):
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
                                    final_state = run_task(base_dir, created.task_id, executor_name="local")

        self.assertEqual(observed_states[0], ("running", "intake", "local"))
        self.assertEqual(final_state.executor_name, "local")
        self.assertEqual(final_state.route_name, "local-summary")

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
