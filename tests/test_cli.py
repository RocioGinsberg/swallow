from __future__ import annotations

import json
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
from swallow.retrieval import retrieve_context
from swallow.validator import build_validation_report, validate_run_outputs


class CliLifecycleTest(unittest.TestCase):
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
                source_grounding = (tasks_dir / task_id / "artifacts" / "source_grounding.md").read_text(
                    encoding="utf-8"
                )
                executor_output = (tasks_dir / task_id / "artifacts" / "executor_output.md").read_text(
                    encoding="utf-8"
                )
                retrieval = json.loads((tasks_dir / task_id / "retrieval.json").read_text(encoding="utf-8"))
                validation = json.loads((tasks_dir / task_id / "validation.json").read_text(encoding="utf-8"))
                memory = json.loads((tasks_dir / task_id / "memory.json").read_text(encoding="utf-8"))

                self.assertIn("Summary for", summary)
                self.assertIn("notes.md", summary)
                self.assertIn("notes.md#L1-L3", summary)
                self.assertIn("mock", summary)
                self.assertIn("score_breakdown:", summary)
                self.assertIn("## Validation", summary)
                self.assertIn("- status: passed", summary)
                self.assertIn("source_grounding_artifact:", summary)
                self.assertIn("task_memory_path:", summary)
                self.assertIn("## Executor Output", summary)
                self.assertNotIn("## Next Suggested Step", summary)
                self.assertIn("Resume Note for", resume_note)
                self.assertIn("## Hand-off", resume_note)
                self.assertIn("## Next Suggested Step", resume_note)
                self.assertNotIn("## Executor Output", resume_note)
                self.assertNotIn("failed live execution attempt", resume_note)
                self.assertIn("Review summary.md to confirm the run outcome", resume_note)
                self.assertIn("validation status: passed", resume_note)
                self.assertIn("source grounding artifact:", resume_note)
                self.assertIn("task memory path:", resume_note)
                self.assertIn("top retrieved references: notes.md#L1-L3", resume_note)
                self.assertIn("Validation Report", validation_report)
                self.assertIn("Source Grounding", source_grounding)
                self.assertIn("notes.md#L1-L3", source_grounding)
                self.assertEqual(validation["status"], "passed")
                self.assertEqual(memory["retrieval"]["top_references"], ["notes.md#L1-L3"])
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
        self.assertIn('"source_grounding"', state)
        self.assertIn('"validation_report"', state)
        self.assertIn('"validation_json"', state)
        self.assertIn('"task_memory"', state)

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
        self.assertEqual(note_item.metadata["title_source"], "heading")
        self.assertEqual(note_item.metadata["chunk_kind"], "markdown_section")
        self.assertEqual(note_item.metadata["line_start"], 1)
        self.assertEqual(note_item.metadata["line_end"], 3)
        self.assertEqual(repo_item.title, "task.py")
        self.assertEqual(repo_item.metadata["title_source"], "filename")

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
                                    return_value=ValidationResult(status="passed", message="Validation passed."),
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
            ) -> ValidationResult:
                artifact_states.append((state.status, state.phase))
                return ValidationResult(status="passed", message="Validation passed.")

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
            ) -> ValidationResult:
                artifact_states.append((state.status, state.phase))
                return ValidationResult(status="passed", message="Validation passed.")

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
                "validation.completed",
                "artifacts.written",
                "task.completed",
            ],
        )
        self.assertEqual(events[0]["payload"]["status"], "created")
        self.assertEqual(events[0]["payload"]["phase"], "intake")
        self.assertEqual(events[1]["payload"]["previous_status"], "created")
        self.assertEqual(events[1]["payload"]["previous_phase"], "intake")
        self.assertEqual(events[1]["payload"]["status"], "running")
        self.assertEqual(events[1]["payload"]["phase"], "intake")
        self.assertEqual(events[2]["payload"]["phase"], "retrieval")
        self.assertEqual(events[2]["payload"]["status"], "running")
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
        self.assertEqual(events[5]["payload"]["status"], "completed")
        self.assertEqual(events[5]["payload"]["executor_name"], "mock")
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
        self.assertEqual(events[7]["payload"]["status"], "passed")
        self.assertEqual(events[7]["payload"]["finding_counts"], {"pass": 3, "warn": 0, "fail": 0})
        self.assertEqual(events[8]["payload"]["status"], "completed")
        self.assertTrue(events[8]["payload"]["artifact_paths"]["summary"].endswith("summary.md"))
        self.assertTrue(events[8]["payload"]["artifact_paths"]["resume_note"].endswith("resume_note.md"))
        self.assertTrue(events[8]["payload"]["artifact_paths"]["source_grounding"].endswith("source_grounding.md"))
        self.assertTrue(events[8]["payload"]["artifact_paths"]["validation_report"].endswith("validation_report.md"))
        self.assertTrue(events[8]["payload"]["artifact_paths"]["task_memory"].endswith("memory.json"))
        self.assertEqual(events[9]["payload"]["status"], "completed")
        self.assertEqual(events[9]["payload"]["phase"], "summarize")
        self.assertEqual(events[9]["payload"]["retrieval_count"], 1)
        self.assertEqual(events[9]["payload"]["executor_status"], "completed")
        self.assertEqual(events[9]["payload"]["validation_status"], "passed")
        self.assertTrue(events[9]["payload"]["artifact_paths"]["executor_output"].endswith("executor_output.md"))

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
        self.assertEqual(events[5]["event_type"], "executor.failed")
        self.assertEqual(events[5]["payload"]["status"], "failed")
        self.assertEqual(events[5]["payload"]["executor_name"], "codex")
        self.assertEqual(events[5]["payload"]["failure_kind"], "launch_error")
        self.assertEqual(events[7]["event_type"], "validation.completed")
        self.assertEqual(events[7]["payload"]["status"], "passed")
        self.assertEqual(events[8]["payload"]["status"], "failed")
        self.assertEqual(events[-1]["payload"]["status"], "failed")
        self.assertEqual(events[-1]["payload"]["phase"], "summarize")
        self.assertEqual(events[-1]["payload"]["executor_status"], "failed")
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

        note = build_resume_note(state, retrieval_items, executor_result, None)

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
                "validation.completed",
                "artifacts.written",
                "task.failed",
                "task.run_started",
                "task.phase",
                "retrieval.completed",
                "task.phase",
                "executor.failed",
                "task.phase",
                "validation.completed",
                "artifacts.written",
                "task.failed",
            ],
        )
        self.assertEqual(final_events[10]["payload"]["previous_status"], "failed")
        self.assertEqual(final_events[10]["payload"]["previous_phase"], "summarize")
        self.assertEqual(final_events[10]["payload"]["status"], "running")
        self.assertEqual(final_events[10]["payload"]["phase"], "intake")

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
        self.assertEqual(persisted["executor_name"], "local")

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
        self.assertEqual(state["executor_status"], "completed")
        self.assertIn("Local summary executor completed.", summary)
        self.assertEqual(events[0]["payload"]["executor_name"], "local")
        self.assertEqual(events[1]["payload"]["executor_name"], "local")
        self.assertEqual(events[5]["payload"]["executor_name"], "local")

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
            grounding_stdout = StringIO()
            memory_stdout = StringIO()

            with redirect_stdout(validation_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "validation", task_id]), 0)
            with redirect_stdout(grounding_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "grounding", task_id]), 0)
            with redirect_stdout(memory_stdout):
                self.assertEqual(main(["--base-dir", str(tmp_path), "task", "memory", task_id]), 0)

        self.assertIn("Validation Report", validation_stdout.getvalue())
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
                                    return_value=ValidationResult(status="passed", message="Validation passed."),
                                ):
                                    final_state = run_task(base_dir, created.task_id, executor_name="local")

        self.assertEqual(observed_states[0], ("running", "intake", "local"))
        self.assertEqual(final_state.executor_name, "local")

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
        self.assertIn("source_grounding.md", second_prompt)
        self.assertIn("memory.json", second_prompt)


if __name__ == "__main__":
    unittest.main()
