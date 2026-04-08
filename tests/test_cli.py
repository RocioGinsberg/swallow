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
    build_fallback_output,
    classify_failure_kind,
    normalize_executor_name,
    resolve_executor_name,
    run_codex_executor,
)
from swallow.harness import build_resume_note
from swallow.models import Event, ExecutorResult, RetrievalItem, RetrievalRequest, TaskState, ValidationResult
from swallow.orchestrator import build_task_retrieval_request, create_task, run_task
from swallow.retrieval import ARTIFACTS_SOURCE_TYPE, retrieve_context
from swallow.retrieval_adapters import select_retrieval_adapter
from swallow.router import select_route
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
                with patch("swallow.orchestrator.run_execution", return_value=executor_result):
                    with patch(
                        "swallow.orchestrator.write_task_artifacts",
                        return_value=(
                            ValidationResult(status="passed", message="Compatibility passed."),
                            ValidationResult(status="passed", message="Execution fit passed."),
                            ValidationResult(status="passed", message="Validation passed."),
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
        self.assertIn("route_name: local-mock", output)
        self.assertIn("topology_execution_site: local", output)
        self.assertIn("topology_dispatch_status: local_dispatched", output)
        self.assertIn("compatibility_status: passed", output)
        self.assertIn("execution_fit_status: passed", output)
        self.assertIn("validation_status: passed", output)
        self.assertIn("retrieval_record_available: yes", output)
        self.assertIn("grounding_available: yes", output)
        self.assertIn("memory_available: yes", output)
        self.assertIn("handoff_status: review_completed_run", output)
        self.assertIn("next_operator_action: Review summary.md", output)
        self.assertIn("summary:", output)
        self.assertIn("retrieval_report:", output)

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
        self.assertIn("Validation And Policy", output)
        self.assertIn("Memory And Reuse", output)
        self.assertIn("summary:", output)
        self.assertIn("resume_note:", output)
        self.assertIn("route_report:", output)
        self.assertIn("handoff_report:", output)
        self.assertIn("retrieval_report:", output)
        self.assertIn("validation_report:", output)
        self.assertIn("compatibility_report:", output)
        self.assertIn("execution_fit_report:", output)
        self.assertIn("task_memory:", output)

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
        self.assertIn("status: failed", output)
        self.assertIn("handoff_status: resume_from_failure", output)
        self.assertIn("blocking_reason: launch_error", output)
        self.assertIn("next_operator_action:", output)
        self.assertIn("resume_note:", output)
        self.assertIn("handoff_report:", output)
        self.assertIn("validation_report:", output)

    def test_task_help_includes_workbench_commands(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as raised:
                main(["task", "--help"])

        self.assertEqual(raised.exception.code, 0)
        output = stdout.getvalue()
        self.assertIn("list                List tasks with compact status summaries.", output)
        self.assertIn("inspect             Print a compact per-task overview.", output)
        self.assertIn("review              Print a review-focused task handoff summary.", output)
        self.assertIn("artifacts           Print grouped task artifact paths.", output)

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
        self.assertIn("task               Task workbench and lifecycle commands.", stdout.getvalue())

    def test_task_help_includes_capability_commands(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as raised:
                main(["task", "--help"])

        self.assertEqual(raised.exception.code, 0)
        output = stdout.getvalue()
        self.assertIn("capabilities        Print the task capability assembly summary.", output)
        self.assertIn("capabilities-json   Print the task capability assembly record.", output)

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
                validation = json.loads((tasks_dir / task_id / "validation.json").read_text(encoding="utf-8"))
                memory = json.loads((tasks_dir / task_id / "memory.json").read_text(encoding="utf-8"))
                route = json.loads((tasks_dir / task_id / "route.json").read_text(encoding="utf-8"))
                topology = json.loads((tasks_dir / task_id / "topology.json").read_text(encoding="utf-8"))
                dispatch = json.loads((tasks_dir / task_id / "dispatch.json").read_text(encoding="utf-8"))
                handoff = json.loads((tasks_dir / task_id / "handoff.json").read_text(encoding="utf-8"))

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
                self.assertIn("route_execution_site:", summary)
                self.assertIn("route_remote_capable:", summary)
                self.assertIn("route_transport_kind:", summary)
                self.assertIn("execution_lifecycle:", summary)
                self.assertIn("attempt_id:", summary)
                self.assertIn("attempt_number:", summary)
                self.assertIn("route_capabilities:", summary)
                self.assertIn("execution_kind=", summary)
                self.assertIn("route_report_artifact:", summary)
                self.assertIn("topology_execution_site:", summary)
                self.assertIn("topology_transport_kind:", summary)
                self.assertIn("topology_dispatch_status:", summary)
                self.assertIn("topology_report_artifact:", summary)
                self.assertIn("dispatch_requested_at:", summary)
                self.assertIn("dispatch_started_at:", summary)
                self.assertIn("dispatch_report_artifact:", summary)
                self.assertIn("handoff_report_artifact:", summary)
                self.assertIn("compatibility_status:", summary)
                self.assertIn("execution_fit_status:", summary)
                self.assertIn("execution_fit_report_artifact:", summary)
                self.assertIn("compatibility_report_artifact:", summary)
                self.assertIn("source_grounding_artifact:", summary)
                self.assertIn("retrieval_report_artifact:", summary)
                self.assertIn("retrieval_record_path:", summary)
                self.assertIn("task_memory_path:", summary)
                self.assertIn("## Compatibility", summary)
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
                self.assertIn("route execution site:", resume_note)
                self.assertIn("route remote capable:", resume_note)
                self.assertIn("route transport kind:", resume_note)
                self.assertIn("execution lifecycle:", resume_note)
                self.assertIn("attempt id:", resume_note)
                self.assertIn("attempt number:", resume_note)
                self.assertIn("route reason:", resume_note)
                self.assertIn("route report artifact:", resume_note)
                self.assertIn("topology execution site:", resume_note)
                self.assertIn("topology transport kind:", resume_note)
                self.assertIn("topology dispatch status:", resume_note)
                self.assertIn("topology report artifact:", resume_note)
                self.assertIn("dispatch requested at:", resume_note)
                self.assertIn("dispatch started at:", resume_note)
                self.assertIn("dispatch report artifact:", resume_note)
                self.assertIn("handoff report artifact:", resume_note)
                self.assertIn("compatibility status: passed", resume_note)
                self.assertIn("execution fit status: passed", resume_note)
                self.assertIn("execution fit report artifact:", resume_note)
                self.assertIn("compatibility report artifact:", resume_note)
                self.assertIn("source grounding artifact:", resume_note)
                self.assertIn("task memory path:", resume_note)
                self.assertIn("top retrieved references: notes.md#L1-L3", resume_note)
                self.assertIn("Validation Report", validation_report)
                self.assertIn("Compatibility Report", compatibility_report)
                self.assertIn("Execution Fit Report", execution_fit_report)
                self.assertIn("Route Report", route_report)
                self.assertIn("Topology Report", topology_report)
                self.assertIn("Dispatch Report", dispatch_report)
                self.assertIn("Handoff Report", handoff_report)
                self.assertIn("Retrieval Report", retrieval_report)
                self.assertIn("Source Grounding", source_grounding)
                self.assertIn("notes.md#L1-L3", source_grounding)
                self.assertEqual(compatibility["status"], "passed")
                self.assertEqual(execution_fit["status"], "passed")
                self.assertEqual(validation["status"], "passed")
                self.assertEqual(route["name"], "local-mock")
                self.assertEqual(topology["route_name"], "local-mock")
                self.assertEqual(topology["execution_site"], "local")
                self.assertEqual(topology["transport_kind"], "local_process")
                self.assertEqual(topology["remote_capable_intent"], False)
                self.assertEqual(topology["dispatch_status"], "local_dispatched")
                self.assertEqual(topology["execution_lifecycle"], "dispatched")
                self.assertEqual(dispatch["attempt_id"], "attempt-0001")
                self.assertEqual(dispatch["attempt_number"], 1)
                self.assertEqual(dispatch["route_name"], "local-mock")
                self.assertEqual(dispatch["execution_site"], "local")
                self.assertEqual(dispatch["transport_kind"], "local_process")
                self.assertEqual(dispatch["dispatch_status"], "local_dispatched")
                self.assertEqual(dispatch["execution_lifecycle"], "dispatched")
                self.assertTrue(bool(dispatch["dispatch_requested_at"]))
                self.assertTrue(bool(dispatch["dispatch_started_at"]))
                self.assertEqual(handoff["status"], "review_completed_run")
                self.assertEqual(handoff["task_status"], "completed")
                self.assertEqual(handoff["attempt_id"], "attempt-0001")
                self.assertEqual(handoff["attempt_number"], 1)
                self.assertEqual(handoff["execution_site"], "local")
                self.assertEqual(handoff["dispatch_status"], "local_dispatched")
                self.assertEqual(handoff["blocking_reason"], "")
                self.assertIn("Review summary.md", handoff["next_operator_action"])
                self.assertEqual(memory["executor"]["name"], "mock")
                self.assertEqual(memory["execution_attempt"]["attempt_id"], "attempt-0001")
                self.assertEqual(memory["execution_attempt"]["attempt_number"], 1)
                self.assertTrue(bool(memory["execution_attempt"]["dispatch_requested_at"]))
                self.assertTrue(bool(memory["execution_attempt"]["dispatch_started_at"]))
                self.assertEqual(memory["execution_attempt"]["execution_lifecycle"], "completed")
                self.assertEqual(memory["route"]["mode"], "auto")
                self.assertEqual(memory["route"]["name"], "local-mock")
                self.assertEqual(memory["route"]["execution_site"], "local")
                self.assertEqual(memory["route"]["remote_capable"], False)
                self.assertEqual(memory["route"]["transport_kind"], "local_process")
                self.assertEqual(memory["route"]["capabilities"]["deterministic"], True)
                self.assertEqual(memory["topology"]["route_name"], "local-mock")
                self.assertEqual(memory["topology"]["execution_site"], "local")
                self.assertEqual(memory["topology"]["transport_kind"], "local_process")
                self.assertEqual(memory["topology"]["remote_capable_intent"], False)
                self.assertEqual(memory["topology"]["dispatch_status"], "local_dispatched")
                self.assertEqual(memory["topology"]["execution_lifecycle"], "completed")
                self.assertEqual(memory["dispatch"]["attempt_id"], "attempt-0001")
                self.assertEqual(memory["dispatch"]["attempt_number"], 1)
                self.assertEqual(memory["dispatch"]["dispatch_status"], "local_dispatched")
                self.assertEqual(memory["dispatch"]["execution_lifecycle"], "completed")
                self.assertEqual(memory["handoff"]["status"], "review_completed_run")
                self.assertEqual(memory["handoff"]["task_status"], "completed")
                self.assertEqual(memory["handoff"]["execution_lifecycle"], "completed")
                self.assertEqual(memory["compatibility"]["status"], "passed")
                self.assertEqual(memory["execution_fit"]["status"], "passed")
                self.assertTrue(
                    memory["artifact_paths"]["compatibility_report"].endswith("compatibility_report.md")
                )
                self.assertTrue(memory["artifact_paths"]["compatibility_json"].endswith("compatibility.json"))
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
                self.assertTrue(memory["artifact_paths"]["retrieval_json"].endswith("retrieval.json"))
                self.assertTrue(memory["artifact_paths"]["retrieval_report"].endswith("retrieval_report.md"))
                self.assertEqual(memory["artifact_paths"]["source_grounding"].endswith("source_grounding.md"), True)
                self.assertEqual(memory["retrieval"]["top_references"], ["notes.md#L1-L3"])
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

                self.assertIn('"status": "failed"', state)
                self.assertIn("Codex binary not found", summary)
                self.assertIn("Codex binary not found", executor_output)
                self.assertEqual(executor_stdout.strip(), "")
                self.assertIn("definitely-not-a-real-codex-binary", executor_stderr)
                self.assertEqual(memory["status"], "failed")

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
                            with patch("swallow.orchestrator.run_execution", return_value=executor_result):
                                with patch(
                                    "swallow.orchestrator.write_task_artifacts",
                                    return_value=(
                                        ValidationResult(status="passed", message="Compatibility passed."),
                                        ValidationResult(status="passed", message="Execution fit passed."),
                                        ValidationResult(status="passed", message="Validation passed."),
                                    ),
                                ):
                                    run_task(base_dir, created.task_id)

        request = captured_request["request"]
        self.assertEqual(request.query, "Request boundary Pass retrieval request explicitly")
        self.assertEqual(request.source_types, ["repo", "notes"])
        self.assertEqual(request.context_layers, ["workspace", "task"])
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
            ) -> tuple[ValidationResult, ValidationResult, ValidationResult]:
                artifact_states.append((state.status, state.phase))
                return (
                    ValidationResult(status="passed", message="Compatibility passed."),
                    ValidationResult(status="passed", message="Execution fit passed."),
                    ValidationResult(status="passed", message="Validation passed."),
                )

            with patch("swallow.orchestrator.load_state", return_value=created):
                with patch("swallow.orchestrator.save_state", side_effect=save_state_spy):
                    with patch("swallow.orchestrator.append_event", side_effect=append_event_spy):
                        with patch("swallow.orchestrator.run_retrieval", return_value=retrieval_items):
                            with patch("swallow.orchestrator.run_execution", return_value=executor_result):
                                with patch("swallow.orchestrator.write_task_artifacts", side_effect=write_artifacts_spy):
                                    final_state = run_task(base_dir, created.task_id)

        self.assertEqual(
            observed_states,
            [
                ("running", "intake"),
                ("running", "retrieval"),
                ("running", "executing"),
                ("running", "executing"),
                ("running", "summarize"),
                ("completed", "summarize"),
            ],
        )
        self.assertEqual(artifact_states, [("running", "summarize")])
        self.assertEqual(
            observed_events,
            [
                "task.run_started",
                "task.phase",
                "task.phase",
                "task.phase",
                "task.completed",
            ],
        )
        self.assertEqual(final_state.status, "completed")
        self.assertEqual(final_state.phase, "summarize")

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
            ) -> tuple[ValidationResult, ValidationResult, ValidationResult]:
                artifact_states.append((state.status, state.phase))
                return (
                    ValidationResult(status="passed", message="Compatibility passed."),
                    ValidationResult(status="passed", message="Execution fit passed."),
                    ValidationResult(status="passed", message="Validation passed."),
                )

            with patch("swallow.orchestrator.load_state", return_value=created):
                with patch("swallow.orchestrator.save_state", side_effect=save_state_spy):
                    with patch("swallow.orchestrator.append_event", side_effect=append_event_spy):
                        with patch("swallow.orchestrator.run_retrieval", return_value=retrieval_items):
                            with patch("swallow.orchestrator.run_execution", return_value=executor_result):
                                with patch("swallow.orchestrator.write_task_artifacts", side_effect=write_artifacts_spy):
                                    final_state = run_task(base_dir, created.task_id)

        self.assertEqual(
            observed_states,
            [
                ("running", "intake"),
                ("running", "retrieval"),
                ("running", "executing"),
                ("running", "executing"),
                ("running", "summarize"),
                ("failed", "summarize"),
            ],
        )
        self.assertEqual(artifact_states, [("running", "summarize")])
        self.assertEqual(
            observed_events,
            [
                "task.run_started",
                "task.phase",
                "task.phase",
                "task.phase",
                "task.failed",
            ],
        )
        self.assertEqual(final_state.status, "failed")
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
                "task.phase",
                "retrieval.completed",
                "task.phase",
                "executor.completed",
                "task.phase",
                "compatibility.completed",
                "execution_fit.completed",
                "validation.completed",
                "artifacts.written",
                "task.completed",
            ],
        )
        self.assertEqual(events[0]["payload"]["status"], "created")
        self.assertEqual(events[0]["payload"]["phase"], "intake")
        self.assertEqual(events[0]["payload"]["route_name"], "local-mock")
        self.assertEqual(events[0]["payload"]["route_backend"], "deterministic_test")
        self.assertEqual(events[0]["payload"]["route_execution_site"], "local")
        self.assertEqual(events[0]["payload"]["route_remote_capable"], False)
        self.assertEqual(events[0]["payload"]["route_transport_kind"], "local_process")
        self.assertEqual(events[0]["payload"]["topology_route_name"], "local-mock")
        self.assertEqual(events[0]["payload"]["topology_execution_site"], "local")
        self.assertEqual(events[0]["payload"]["topology_transport_kind"], "local_process")
        self.assertEqual(events[0]["payload"]["topology_remote_capable_intent"], False)
        self.assertEqual(events[0]["payload"]["topology_dispatch_status"], "not_requested")
        self.assertEqual(events[0]["payload"]["execution_lifecycle"], "idle")
        self.assertEqual(events[1]["payload"]["previous_status"], "created")
        self.assertEqual(events[1]["payload"]["previous_phase"], "intake")
        self.assertEqual(events[1]["payload"]["status"], "running")
        self.assertEqual(events[1]["payload"]["phase"], "intake")
        self.assertEqual(events[1]["payload"]["route_name"], "local-mock")
        self.assertEqual(events[1]["payload"]["route_backend"], "deterministic_test")
        self.assertEqual(events[1]["payload"]["route_execution_site"], "local")
        self.assertEqual(events[1]["payload"]["route_remote_capable"], False)
        self.assertEqual(events[1]["payload"]["route_transport_kind"], "local_process")
        self.assertEqual(events[1]["payload"]["attempt_id"], "attempt-0001")
        self.assertEqual(events[1]["payload"]["attempt_number"], 1)
        self.assertEqual(events[1]["payload"]["topology_route_name"], "local-mock")
        self.assertEqual(events[1]["payload"]["topology_execution_site"], "local")
        self.assertEqual(events[1]["payload"]["topology_transport_kind"], "local_process")
        self.assertEqual(events[1]["payload"]["topology_remote_capable_intent"], False)
        self.assertEqual(events[1]["payload"]["topology_dispatch_status"], "planned")
        self.assertTrue(bool(events[1]["payload"]["dispatch_requested_at"]))
        self.assertEqual(events[1]["payload"]["dispatch_started_at"], "")
        self.assertEqual(events[1]["payload"]["execution_lifecycle"], "prepared")
        self.assertIn("Selected the route from legacy executor mode", events[1]["payload"]["route_reason"])
        self.assertEqual(events[2]["payload"]["phase"], "retrieval")
        self.assertEqual(events[2]["payload"]["status"], "running")
        self.assertEqual(events[2]["payload"]["execution_lifecycle"], "prepared")
        self.assertEqual(events[3]["payload"]["count"], 1)
        self.assertEqual(events[3]["payload"]["query"], "Ordered lifecycle Check persisted phase ordering")
        self.assertEqual(events[3]["payload"]["source_types_requested"], ["repo", "notes"])
        self.assertEqual(events[3]["payload"]["context_layers"], ["workspace", "task"])
        self.assertEqual(events[3]["payload"]["limit"], 8)
        self.assertEqual(events[3]["payload"]["strategy"], "system_baseline")
        self.assertEqual(events[3]["payload"]["top_paths"], ["notes.md"])
        self.assertEqual(events[3]["payload"]["top_citations"], ["notes.md#L1-L3"])
        self.assertEqual(events[3]["payload"]["source_types"], ["notes"])
        self.assertEqual(events[4]["payload"]["phase"], "executing")
        self.assertEqual(events[4]["payload"]["execution_lifecycle"], "dispatched")
        self.assertEqual(events[5]["payload"]["status"], "completed")
        self.assertEqual(events[5]["payload"]["executor_name"], "mock")
        self.assertEqual(events[5]["payload"]["route_name"], "local-mock")
        self.assertEqual(events[5]["payload"]["route_backend"], "deterministic_test")
        self.assertEqual(events[5]["payload"]["route_execution_site"], "local")
        self.assertEqual(events[5]["payload"]["route_remote_capable"], False)
        self.assertEqual(events[5]["payload"]["route_transport_kind"], "local_process")
        self.assertEqual(events[5]["payload"]["route_capabilities"]["deterministic"], True)
        self.assertEqual(events[5]["payload"]["route_capabilities"]["filesystem_access"], "workspace_read")
        self.assertEqual(events[5]["payload"]["attempt_id"], "attempt-0001")
        self.assertEqual(events[5]["payload"]["attempt_number"], 1)
        self.assertEqual(events[5]["payload"]["topology_route_name"], "local-mock")
        self.assertEqual(events[5]["payload"]["topology_execution_site"], "local")
        self.assertEqual(events[5]["payload"]["topology_transport_kind"], "local_process")
        self.assertEqual(events[5]["payload"]["topology_remote_capable_intent"], False)
        self.assertEqual(events[5]["payload"]["topology_dispatch_status"], "local_dispatched")
        self.assertTrue(bool(events[5]["payload"]["dispatch_requested_at"]))
        self.assertTrue(bool(events[5]["payload"]["dispatch_started_at"]))
        self.assertEqual(events[5]["payload"]["execution_lifecycle"], "dispatched")
        self.assertEqual(
            events[5]["payload"]["output_written"],
            [
                "executor_prompt.md",
                "executor_output.md",
                "executor_stdout.txt",
                "executor_stderr.txt",
            ],
        )
        self.assertEqual(events[6]["payload"]["phase"], "summarize")
        self.assertEqual(events[6]["payload"]["execution_lifecycle"], "dispatched")
        self.assertEqual(events[7]["payload"]["status"], "passed")
        self.assertEqual(events[7]["payload"]["finding_counts"], {"pass": 3, "warn": 0, "fail": 0})
        self.assertEqual(events[8]["payload"]["status"], "passed")
        self.assertEqual(events[8]["payload"]["finding_counts"], {"pass": 5, "warn": 0, "fail": 0})
        self.assertEqual(events[9]["payload"]["status"], "passed")
        self.assertEqual(events[9]["payload"]["finding_counts"], {"pass": 3, "warn": 0, "fail": 0})
        self.assertEqual(events[10]["payload"]["status"], "completed")
        self.assertTrue(events[10]["payload"]["artifact_paths"]["summary"].endswith("summary.md"))
        self.assertTrue(events[10]["payload"]["artifact_paths"]["resume_note"].endswith("resume_note.md"))
        self.assertTrue(events[10]["payload"]["artifact_paths"]["route_report"].endswith("route_report.md"))
        self.assertTrue(events[10]["payload"]["artifact_paths"]["topology_report"].endswith("topology_report.md"))
        self.assertTrue(events[10]["payload"]["artifact_paths"]["dispatch_report"].endswith("dispatch_report.md"))
        self.assertTrue(events[10]["payload"]["artifact_paths"]["handoff_report"].endswith("handoff_report.md"))
        self.assertTrue(events[10]["payload"]["artifact_paths"]["execution_fit_report"].endswith("execution_fit_report.md"))
        self.assertTrue(
            events[10]["payload"]["artifact_paths"]["compatibility_report"].endswith("compatibility_report.md")
        )
        self.assertTrue(events[10]["payload"]["artifact_paths"]["source_grounding"].endswith("source_grounding.md"))
        self.assertTrue(events[10]["payload"]["artifact_paths"]["retrieval_report"].endswith("retrieval_report.md"))
        self.assertTrue(events[10]["payload"]["artifact_paths"]["validation_report"].endswith("validation_report.md"))
        self.assertTrue(events[10]["payload"]["artifact_paths"]["task_memory"].endswith("memory.json"))
        self.assertEqual(events[11]["payload"]["status"], "completed")
        self.assertEqual(events[11]["payload"]["phase"], "summarize")
        self.assertEqual(events[11]["payload"]["retrieval_count"], 1)
        self.assertEqual(events[11]["payload"]["executor_status"], "completed")
        self.assertEqual(events[11]["payload"]["route_name"], "local-mock")
        self.assertEqual(events[11]["payload"]["route_backend"], "deterministic_test")
        self.assertEqual(events[11]["payload"]["route_execution_site"], "local")
        self.assertEqual(events[11]["payload"]["route_remote_capable"], False)
        self.assertEqual(events[11]["payload"]["route_transport_kind"], "local_process")
        self.assertEqual(events[11]["payload"]["attempt_id"], "attempt-0001")
        self.assertEqual(events[11]["payload"]["attempt_number"], 1)
        self.assertEqual(events[11]["payload"]["topology_route_name"], "local-mock")
        self.assertEqual(events[11]["payload"]["topology_execution_site"], "local")
        self.assertEqual(events[11]["payload"]["topology_transport_kind"], "local_process")
        self.assertEqual(events[11]["payload"]["topology_remote_capable_intent"], False)
        self.assertEqual(events[11]["payload"]["topology_dispatch_status"], "local_dispatched")
        self.assertTrue(bool(events[11]["payload"]["dispatch_requested_at"]))
        self.assertTrue(bool(events[11]["payload"]["dispatch_started_at"]))
        self.assertEqual(events[11]["payload"]["execution_lifecycle"], "completed")
        self.assertEqual(events[11]["payload"]["compatibility_status"], "passed")
        self.assertEqual(events[11]["payload"]["execution_fit_status"], "passed")
        self.assertEqual(events[11]["payload"]["validation_status"], "passed")
        self.assertTrue(events[11]["payload"]["artifact_paths"]["executor_output"].endswith("executor_output.md"))

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

        self.assertEqual(events[-1]["event_type"], "task.failed")
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
        self.assertEqual(events[5]["event_type"], "executor.failed")
        self.assertEqual(events[5]["payload"]["status"], "failed")
        self.assertEqual(events[5]["payload"]["executor_name"], "codex")
        self.assertEqual(events[5]["payload"]["route_name"], "local-codex")
        self.assertEqual(events[5]["payload"]["route_execution_site"], "local")
        self.assertEqual(events[5]["payload"]["attempt_id"], "attempt-0001")
        self.assertEqual(events[5]["payload"]["attempt_number"], 1)
        self.assertEqual(events[5]["payload"]["topology_dispatch_status"], "local_dispatched")
        self.assertTrue(bool(events[5]["payload"]["dispatch_started_at"]))
        self.assertEqual(events[5]["payload"]["execution_lifecycle"], "dispatched")
        self.assertEqual(events[5]["payload"]["failure_kind"], "launch_error")
        self.assertEqual(events[7]["event_type"], "compatibility.completed")
        self.assertEqual(events[7]["payload"]["status"], "passed")
        self.assertEqual(events[8]["event_type"], "execution_fit.completed")
        self.assertEqual(events[8]["payload"]["status"], "passed")
        self.assertEqual(events[9]["event_type"], "validation.completed")
        self.assertEqual(events[9]["payload"]["status"], "passed")
        self.assertEqual(events[10]["payload"]["status"], "failed")
        self.assertEqual(events[-1]["payload"]["status"], "failed")
        self.assertEqual(events[-1]["payload"]["phase"], "summarize")
        self.assertEqual(events[-1]["payload"]["executor_status"], "failed")
        self.assertEqual(events[-1]["payload"]["route_name"], "local-codex")
        self.assertEqual(events[-1]["payload"]["route_execution_site"], "local")
        self.assertEqual(events[-1]["payload"]["route_remote_capable"], False)
        self.assertEqual(events[-1]["payload"]["compatibility_status"], "passed")
        self.assertEqual(events[-1]["payload"]["execution_fit_status"], "passed")
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

        note = build_resume_note(state, retrieval_items, executor_result, None, None, None)

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

        self.assertEqual(first_state["status"], "failed")
        self.assertEqual(first_state["phase"], "summarize")
        self.assertEqual(final_state["status"], "failed")
        self.assertEqual(final_state["phase"], "summarize")
        self.assertEqual(
            [event["event_type"] for event in first_events],
            [
                "task.created",
                "task.run_started",
                "task.phase",
                "retrieval.completed",
                "task.phase",
                "executor.failed",
                "task.phase",
                "compatibility.completed",
                "execution_fit.completed",
                "validation.completed",
                "artifacts.written",
                "task.failed",
            ],
        )
        self.assertEqual(
            [event["event_type"] for event in final_events],
            [
                "task.created",
                "task.run_started",
                "task.phase",
                "retrieval.completed",
                "task.phase",
                "executor.failed",
                "task.phase",
                "compatibility.completed",
                "execution_fit.completed",
                "validation.completed",
                "artifacts.written",
                "task.failed",
                "task.run_started",
                "task.phase",
                "retrieval.completed",
                "task.phase",
                "executor.failed",
                "task.phase",
                "compatibility.completed",
                "execution_fit.completed",
                "validation.completed",
                "artifacts.written",
                "task.failed",
            ],
        )
        self.assertEqual(final_events[12]["payload"]["previous_status"], "failed")
        self.assertEqual(final_events[12]["payload"]["previous_phase"], "summarize")
        self.assertEqual(final_events[12]["payload"]["status"], "running")
        self.assertEqual(final_events[12]["payload"]["phase"], "intake")
        self.assertEqual(first_events[1]["payload"]["attempt_id"], "attempt-0001")
        self.assertEqual(first_events[1]["payload"]["attempt_number"], 1)
        self.assertEqual(first_events[1]["payload"]["execution_lifecycle"], "prepared")
        self.assertEqual(final_events[12]["payload"]["attempt_id"], "attempt-0002")
        self.assertEqual(final_events[12]["payload"]["attempt_number"], 2)
        self.assertEqual(final_events[12]["payload"]["execution_lifecycle"], "prepared")
        self.assertEqual(final_state["run_attempt_count"], 2)
        self.assertEqual(final_state["current_attempt_id"], "attempt-0002")
        self.assertEqual(final_state["current_attempt_number"], 2)
        self.assertEqual(final_state["execution_lifecycle"], "failed")

    def test_normalize_executor_name_supports_aliases(self) -> None:
        self.assertEqual(normalize_executor_name("local-summary"), "local")
        self.assertEqual(normalize_executor_name("note_only"), "note-only")
        self.assertEqual(normalize_executor_name("unknown-executor"), "codex")

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
        self.assertEqual(persisted["route_capabilities"]["execution_kind"], "artifact_generation")

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
            route_execution_site="local",
            route_transport_kind="local_process",
            topology_route_name="local-mock",
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
        self.assertIn("Execution Fit Report", report)

    def test_execution_fit_reports_failure_for_inconsistent_local_dispatch(self) -> None:
        state = TaskState(
            task_id="fitfail",
            title="Execution fit fail",
            goal="Catch inconsistent dispatch state",
            workspace_root="/tmp",
            executor_name="mock",
            route_name="local-mock",
            route_execution_site="local",
            route_transport_kind="local_process",
            topology_route_name="local-mock",
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
        self.assertEqual(events[1]["payload"]["executor_name"], "local")
        self.assertEqual(events[1]["payload"]["route_name"], "local-summary")
        self.assertEqual(events[5]["payload"]["executor_name"], "local")
        self.assertEqual(events[5]["payload"]["route_name"], "local-summary")

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
            dispatch_stdout = StringIO()
            handoff_stdout = StringIO()
            execution_fit_stdout = StringIO()
            compatibility_json_stdout = StringIO()
            route_json_stdout = StringIO()
            topology_json_stdout = StringIO()
            dispatch_json_stdout = StringIO()
            handoff_json_stdout = StringIO()
            execution_fit_json_stdout = StringIO()
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
            with redirect_stdout(topology_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "topology", task_id]), 0)
            with redirect_stdout(dispatch_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "dispatch", task_id]), 0)
            with redirect_stdout(handoff_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "handoff", task_id]), 0)
            with redirect_stdout(execution_fit_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "execution-fit", task_id]), 0)
            with redirect_stdout(compatibility_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "compatibility-json", task_id]), 0)
            with redirect_stdout(route_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "route-json", task_id]), 0)
            with redirect_stdout(topology_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "topology-json", task_id]), 0)
            with redirect_stdout(dispatch_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "dispatch-json", task_id]), 0)
            with redirect_stdout(handoff_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "handoff-json", task_id]), 0)
            with redirect_stdout(execution_fit_json_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "execution-fit-json", task_id]), 0)
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
        self.assertIn("Topology Report", topology_stdout.getvalue())
        self.assertIn("Dispatch Report", dispatch_stdout.getvalue())
        self.assertIn("Handoff Report", handoff_stdout.getvalue())
        self.assertIn("Execution Fit Report", execution_fit_stdout.getvalue())
        self.assertIn('"status"', compatibility_json_stdout.getvalue())
        self.assertIn('"name"', route_json_stdout.getvalue())
        self.assertIn('"execution_site"', route_json_stdout.getvalue())
        self.assertIn('"remote_capable"', route_json_stdout.getvalue())
        self.assertIn('"dispatch_status"', topology_json_stdout.getvalue())
        self.assertIn('"attempt_id"', dispatch_json_stdout.getvalue())
        self.assertIn('"next_operator_action"', handoff_json_stdout.getvalue())
        self.assertIn('"findings"', execution_fit_json_stdout.getvalue())
        self.assertIn('"citation"', retrieval_json_stdout.getvalue())
        self.assertIn("Source Grounding", grounding_stdout.getvalue())
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
                            with patch("swallow.orchestrator.run_execution", return_value=executor_result):
                                with patch(
                                    "swallow.orchestrator.write_task_artifacts",
                                    return_value=(
                                        ValidationResult(status="passed", message="Compatibility passed."),
                                        ValidationResult(status="passed", message="Execution fit passed."),
                                        ValidationResult(status="passed", message="Validation passed."),
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
                            with patch("swallow.orchestrator.run_execution", return_value=executor_result):
                                with patch(
                                    "swallow.orchestrator.write_task_artifacts",
                                    return_value=(
                                        ValidationResult(status="passed", message="Compatibility passed."),
                                        ValidationResult(status="passed", message="Execution fit passed."),
                                        ValidationResult(status="passed", message="Validation passed."),
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
        self.assertIn("previous_retrieval_record:", second_prompt)
        self.assertIn("Route Execution Site: local", second_prompt)
        self.assertIn("Route Remote Capable: no", second_prompt)
        self.assertIn("Route Transport Kind: local_process", second_prompt)
        self.assertIn("source_grounding.md", second_prompt)
        self.assertIn("memory.json", second_prompt)


if __name__ == "__main__":
    unittest.main()
