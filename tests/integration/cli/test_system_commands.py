from __future__ import annotations


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


class LegacyCliSystemCommandTest(unittest.TestCase):
    def test_cli_create_persists_complexity_hint_in_task_semantics(self) -> None:
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
                        "Complexity hint create",
                        "--goal",
                        "Persist complexity hint during task creation",
                        "--workspace-root",
                        str(tmp_path),
                        "--complexity-hint",
                        "high",
                    ]
                ),
                0,
            )
            task_id = next(entry.name for entry in (tmp_path / ".swl" / "tasks").iterdir() if entry.is_dir())
            task_dir = tmp_path / ".swl" / "tasks" / task_id
            state = json.loads((task_dir / "state.json").read_text(encoding="utf-8"))
            task_semantics = json.loads((task_dir / "task_semantics.json").read_text(encoding="utf-8"))
            semantics_report = (task_dir / "artifacts" / "task_semantics_report.md").read_text(encoding="utf-8")

        self.assertEqual(task_semantics["complexity_hint"], "high")
        self.assertEqual(state["task_semantics"]["complexity_hint"], "high")
        self.assertIn("- complexity_hint: high", semantics_report)

    def test_cli_task_staged_defaults_to_pending_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pending = submit_staged_candidate(
                tmp_path,
                StagedCandidate(
                    candidate_id="",
                    text="Pending staged note should appear in the task queue output.",
                    source_task_id="task-stage-queue",
                    topic="queueing",
                    source_kind="operator_note",
                    source_ref="note://operator",
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
        self.assertIn("topic: queueing", output)
        self.assertIn("source_kind: operator_note", output)
        self.assertIn("source_ref: note://operator", output)
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
                    topic="routing",
                    source_kind="external_session_ingestion",
                    source_ref="/tmp/export.json",
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
        self.assertIn("topic: routing", output)
        self.assertIn("source_kind: external_session_ingestion", output)
        self.assertIn("source_ref: /tmp/export.json", output)
        self.assertIn("text: Promoted staged note should be shown when explicitly requested.", output)
        self.assertNotIn("Different task should be filtered out.", output)

    def test_top_level_help_includes_task_workbench_wording(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as raised:
                main(["--help"])

        self.assertEqual(raised.exception.code, 0)
        self.assertIn("task                Task workbench and lifecycle commands.", stdout.getvalue())
        self.assertIn("knowledge           Global staged knowledge review commands.", stdout.getvalue())
        self.assertIn("ingest              Ingest an external session export into staged", stdout.getvalue())
        self.assertIn("meta-optimize       Scan recent task event logs and emit a read-only", stdout.getvalue())
        self.assertIn("proposal            Review or apply structured meta-optimizer proposals.", stdout.getvalue())

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

    def test_aider_timeout_preserves_partial_output(self) -> None:
        state = TaskState(
            task_id="timeout123",
            title="Timeout executor",
            goal="Keep partial output on timeout",
            workspace_root="/tmp",
            route_name="",
        )
        timeout_exc = subprocess.TimeoutExpired(
            cmd=["aider", "--yes-always"],
            timeout=5,
            output="partial stdout",
            stderr="partial stderr",
        )

        with patch("swallow.orchestration.executor.shutil.which", return_value="/usr/bin/aider"):
            with patch("swallow.orchestration.executor.subprocess.run", side_effect=timeout_exc):
                result = run_cli_agent_executor(AIDER_CONFIG, state, [])

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

    def test_unreachable_backend_fallback_includes_connectivity_guidance(self) -> None:
        state = TaskState(
            task_id="net123",
            title="Connectivity failure",
            goal="Classify unreachable backend correctly",
            workspace_root="/tmp",
        )
        unreachable_result = ExecutorResult(
            executor_name="aider",
            status="failed",
            message="Backend connection failed.",
            output="failed to connect to websocket",
            prompt="prompt",
            failure_kind="unreachable_backend",
        )
        note = build_fallback_output(state, [], unreachable_result)
        self.assertIn("outbound network and process execution access", note)
        self.assertIn("backend connectivity", note)

    def test_doctor_executor_missing_binary_returns_nonzero(self) -> None:
        stdout = StringIO()
        with patch("swallow.application.services.doctor.shutil.which", return_value=None):
            with patch("swallow.adapters.cli.diagnose_cli_agents", return_value=(1, [])):
                with redirect_stdout(stdout):
                    exit_code = main(["doctor", "executor"])
        self.assertNotEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("binary_found=no", output)
        self.assertIn("launch_ok=no", output)
        self.assertIn("note_only_recommended=yes", output)

    def test_doctor_executor_success_returns_zero(self) -> None:
        stdout = StringIO()
        completed = subprocess.CompletedProcess(
            args=["aider", "--version"],
            returncode=0,
            stdout="aider 1.2.3",
            stderr="",
        )
        with patch("swallow.application.services.doctor.shutil.which", return_value="/usr/bin/aider"):
            with patch("swallow.application.services.doctor.subprocess.run", return_value=completed):
                with patch("swallow.adapters.cli.diagnose_cli_agents", return_value=(0, [])):
                    with redirect_stdout(stdout):
                        exit_code = main(["doctor", "executor"])
        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("binary_found=yes", output)
        self.assertIn("launch_ok=yes", output)
        self.assertIn("note_only_recommended=no", output)

    def test_doctor_executor_includes_cli_agent_probe_results(self) -> None:
        stdout = StringIO()
        with patch("swallow.adapters.cli.diagnose_executor", return_value=(0, object())):
            with patch(
                "swallow.adapters.cli.diagnose_cli_agents",
                return_value=(
                    0,
                    [
                        type(
                            "C",
                            (),
                            {
                                "executor_name": "codex",
                                "display_name": "Codex",
                                "binary_found": True,
                                "launch_ok": True,
                                "executor_bin": "codex",
                                "resolved_path": "/usr/bin/codex",
                                "version": "codex-cli 0.125.0",
                                "details": "",
                            },
                        )()
                    ],
                ),
            ):
                with patch("swallow.adapters.cli.format_executor_doctor_result", return_value="executor-ok\ncli_agents:\n- codex: ok"):
                    with redirect_stdout(stdout):
                        exit_code = main(["doctor", "executor"])

        self.assertEqual(exit_code, 0)
        self.assertIn("cli_agents:", stdout.getvalue())

    def test_doctor_without_subcommand_runs_executor_and_stack_checks(self) -> None:
        stdout = StringIO()
        with patch("swallow.adapters.cli.diagnose_executor", return_value=(0, object())) as mocked_executor:
            with patch("swallow.adapters.cli.diagnose_cli_agents", return_value=(0, [])) as mocked_cli_agents:
                with patch("swallow.adapters.cli.format_executor_doctor_result", return_value="executor-ok"):
                    with patch("swallow.adapters.cli.diagnose_sqlite_store", return_value=(0, object())) as mocked_sqlite:
                        with patch("swallow.adapters.cli.format_sqlite_doctor_result", return_value="sqlite-ok"):
                            with patch("swallow.adapters.cli.diagnose_local_stack", return_value=(0, object())) as mocked_stack:
                                with patch("swallow.adapters.cli.format_local_stack_doctor_result", return_value="stack-ok"):
                                    with redirect_stdout(stdout):
                                        exit_code = main(["doctor"])
        self.assertEqual(exit_code, 0)
        mocked_executor.assert_called_once_with()
        mocked_cli_agents.assert_called_once_with()
        mocked_sqlite.assert_called_once()
        mocked_stack.assert_called_once_with()
        self.assertEqual(stdout.getvalue(), "executor-ok\n\nsqlite-ok\n\nstack-ok\n")

    def test_doctor_skip_stack_only_runs_executor_check(self) -> None:
        stdout = StringIO()
        with patch("swallow.adapters.cli.diagnose_executor", return_value=(0, object())) as mocked_executor:
            with patch("swallow.adapters.cli.diagnose_cli_agents", return_value=(0, [])) as mocked_cli_agents:
                with patch("swallow.adapters.cli.format_executor_doctor_result", return_value="executor-ok"):
                    with patch("swallow.adapters.cli.diagnose_sqlite_store", return_value=(0, object())) as mocked_sqlite:
                        with patch("swallow.adapters.cli.format_sqlite_doctor_result", return_value="sqlite-ok"):
                            with patch("swallow.adapters.cli.diagnose_local_stack") as mocked_stack:
                                with redirect_stdout(stdout):
                                    exit_code = main(["doctor", "--skip-stack"])
        self.assertEqual(exit_code, 0)
        mocked_executor.assert_called_once_with()
        mocked_cli_agents.assert_called_once_with()
        mocked_sqlite.assert_called_once()
        mocked_stack.assert_not_called()
        self.assertEqual(stdout.getvalue(), "executor-ok\n\nsqlite-ok\n")

    def test_doctor_sqlite_subcommand_runs_sqlite_check_only(self) -> None:
        stdout = StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            with patch("swallow.adapters.cli.diagnose_executor") as mocked_executor:
                with patch("swallow.adapters.cli.diagnose_local_stack") as mocked_stack:
                    with redirect_stdout(stdout):
                        exit_code = main(["--base-dir", tmp, "doctor", "sqlite"])
        self.assertEqual(exit_code, 0)
        mocked_executor.assert_not_called()
        mocked_stack.assert_not_called()
        output = stdout.getvalue()
        self.assertIn("db_path=", output)
        self.assertIn("migration_recommended=no", output)

    def test_doctor_stack_subcommand_runs_stack_check_only(self) -> None:
        stdout = StringIO()
        with patch("swallow.adapters.cli.diagnose_executor") as mocked_executor:
            with patch("swallow.adapters.cli.diagnose_local_stack", return_value=(0, object())) as mocked_stack:
                with patch("swallow.adapters.cli.format_local_stack_doctor_result", return_value="stack-ok"):
                    with redirect_stdout(stdout):
                        exit_code = main(["doctor", "stack"])
        self.assertEqual(exit_code, 0)
        mocked_executor.assert_not_called()
        mocked_stack.assert_called_once_with()
        self.assertEqual(stdout.getvalue(), "stack-ok\n")

    def test_migrate_dry_run_reports_candidates_without_writing_db(self) -> None:
        stdout = StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            with patch.dict("os.environ", {"SWALLOW_STORE_BACKEND": "file"}, clear=False):
                save_state(
                    base_dir,
                    TaskState(
                        task_id="legacy-task",
                        title="Legacy task",
                        goal="Dry-run sqlite migration",
                        workspace_root=str(base_dir),
                        executor_name="local",
                    ),
                )
                append_event(
                    base_dir,
                    Event(
                        task_id="legacy-task",
                        event_type="task.created",
                        message="legacy",
                        payload={"status": "created"},
                    ),
                )
            with redirect_stdout(stdout):
                exit_code = main(["--base-dir", str(base_dir), "migrate", "--dry-run"])
            db_exists = swallow_db_path(base_dir).exists()

        self.assertEqual(exit_code, 0)
        self.assertFalse(db_exists)
        output = stdout.getvalue()
        self.assertIn("dry_run=yes", output)
        self.assertIn("task_count_migrated=1", output)
        self.assertIn("event_count_migrated=1", output)

    def test_migrate_imports_file_task_into_sqlite(self) -> None:
        stdout = StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            with patch.dict("os.environ", {"SWALLOW_STORE_BACKEND": "file"}, clear=False):
                save_state(
                    base_dir,
                    TaskState(
                        task_id="legacy-task",
                        title="Legacy task",
                        goal="Migrate sqlite state",
                        workspace_root=str(base_dir),
                        executor_name="local",
                    ),
                )
                append_event(
                    base_dir,
                    Event(
                        task_id="legacy-task",
                        event_type="task.created",
                        message="legacy",
                        payload={"status": "created"},
                    ),
                )
            with redirect_stdout(stdout):
                exit_code = main(["--base-dir", str(base_dir), "migrate"])
            db_exists = swallow_db_path(base_dir).exists()
            migrated_state = load_state(base_dir, "legacy-task")

        self.assertEqual(exit_code, 0)
        self.assertTrue(db_exists)
        self.assertEqual(migrated_state.task_id, "legacy-task")
        output = stdout.getvalue()
        self.assertIn("dry_run=no", output)
        self.assertIn("task_count_migrated=1", output)

    def test_end_to_end_local_file_relation_expansion_reaches_task_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            seed_file = tmp_path / "seed.md"
            seed_file.write_text("# Seed\n\ngraphseed anchor relation closure", encoding="utf-8")
            linked_file = tmp_path / "linked.md"
            linked_file.write_text("# Linked\n\ntaxonomy archive bundle only", encoding="utf-8")

            self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "ingest-file", str(seed_file)]), 0)
            self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "ingest-file", str(linked_file)]), 0)
            staged = load_staged_candidates(tmp_path)
            self.assertEqual(len(staged), 2)

            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "task",
                        "create",
                        "--title",
                        "Graphseed task",
                        "--goal",
                        "Use graphseed anchor",
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
                        f"file://{seed_file.resolve()}",
                        "--knowledge-artifact-ref",
                        str(seed_file),
                        "--knowledge-artifact-ref",
                        str(linked_file),
                        "--knowledge-item",
                        staged[0].text,
                        "--knowledge-item",
                        staged[1].text,
                        "--knowledge-retrieval-eligible",
                    ]
                ),
                0,
            )
            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "knowledge",
                        "link",
                        "knowledge-0001",
                        "knowledge-0002",
                        "--type",
                        "cites",
                    ]
                ),
                0,
            )

            request = build_task_retrieval_request(load_state(tmp_path, task_id))
            retrieved = retrieve_context(tmp_path, request=request)
            expanded = next(item for item in retrieved if item.chunk_id == "knowledge-0002")
            self.assertEqual(expanded.metadata["expansion_source"], "relation")

            with patch.dict("os.environ", {"AIWF_EXECUTOR_MODE": "mock"}, clear=False):
                final_state = run_task(tmp_path, task_id, executor_name="mock")

            retrieval_payload = json.loads((tmp_path / ".swl" / "tasks" / task_id / "retrieval.json").read_text(encoding="utf-8"))
            expanded_payload = next(item for item in retrieval_payload if item["chunk_id"] == "knowledge-0002")

        self.assertEqual(final_state.status, "completed")
        self.assertEqual(expanded_payload["metadata"]["expansion_source"], "relation")
        self.assertEqual(expanded_payload["metadata"]["expansion_relation_type"], "cites")

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

    def test_normalize_executor_name_supports_aliases(self) -> None:
        self.assertEqual(normalize_executor_name("local-summary"), "local")
        self.assertEqual(normalize_executor_name("note_only"), "note-only")
        self.assertEqual(normalize_executor_name("codex"), "codex")
        self.assertEqual(normalize_executor_name("unknown-executor"), "unknown-executor")

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

    def test_cli_help_lists_serve_command(self) -> None:
        stdout = StringIO()

        with redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as raised:
                main(["--help"])

        self.assertEqual(raised.exception.code, 0)
        self.assertIn("serve", stdout.getvalue())

    def test_cli_serve_reports_missing_optional_dependencies_without_breaking_other_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            stdout = StringIO()

            with patch(
                "swallow.adapters.http.server.serve_control_center",
                side_effect=RuntimeError("FastAPI is required for `swl serve`."),
            ):
                with redirect_stdout(stdout):
                    self.assertEqual(main(["--base-dir", str(tmp_path), "serve"]), 1)

        self.assertIn("FastAPI is required for `swl serve`.", stdout.getvalue())

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
            executor_output = (task_dir / "artifacts" / "executor_output.md").read_text(encoding="utf-8")
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
        self.assertIn("summary_surface_kind: local_execution_summary", summary)
        self.assertIn("semantic_answer_produced: no", summary)
        self.assertIn("summary_route_boundary: run_record_not_semantic_qa", summary)
        self.assertIn("surface_kind: local_execution_summary", executor_output)
        self.assertIn("semantic_answer_produced: no", executor_output)
        self.assertIn("answer_contract: run_record_not_semantic_qa", executor_output)
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

