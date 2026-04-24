from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.dispatch_policy import validate_handoff_semantics, validate_taxonomy_dispatch
from swallow.models import RouteCapabilities, RouteSelection, RouteSpec, TaxonomyProfile
from swallow.orchestrator import create_task, run_task
from swallow.store import load_state, save_state


class DispatchPolicyTest(unittest.TestCase):
    def test_validate_handoff_semantics_accepts_existing_relative_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_dir = tmp_path / ".swl" / "tasks" / "task-relative-pointer"
            artifacts_dir = task_dir / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            (artifacts_dir / "dispatch_report.md").write_text("dispatch ok\n", encoding="utf-8")

            result = validate_handoff_semantics(
                {"context_pointers": ["dispatch_report.md"]},
                task_dir,
            )

        self.assertTrue(result.valid)
        self.assertEqual(result.errors, [])

    def test_validate_handoff_semantics_rejects_missing_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_dir = tmp_path / ".swl" / "tasks" / "task-missing-pointer"
            task_dir.mkdir(parents=True, exist_ok=True)

            result = validate_handoff_semantics(
                {"context_pointers": ["missing-artifact.md"]},
                task_dir,
            )

        self.assertFalse(result.valid)
        self.assertEqual(result.errors, ["context pointer not found: missing-artifact.md"])

    def test_validate_handoff_semantics_allows_empty_context_pointers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_dir = tmp_path / ".swl" / "tasks" / "task-empty-pointers"
            task_dir.mkdir(parents=True, exist_ok=True)

            result = validate_handoff_semantics(
                {"context_pointers": []},
                task_dir,
            )

        self.assertTrue(result.valid)
        self.assertEqual(result.errors, [])

    def test_run_task_blocks_remote_dispatch_when_context_pointer_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Semantic validation block",
                goal="Block mock remote dispatch when context pointers are dead links",
                workspace_root=tmp_path,
            )
            task_dir = tmp_path / ".swl" / "tasks" / state.task_id
            persisted = load_state(tmp_path, state.task_id)
            persisted.artifact_paths["task_semantics_json"] = "missing-artifact.md"
            save_state(tmp_path, persisted)

            final_state = run_task(tmp_path, state.task_id, executor_name="mock-remote")
            events = [
                json.loads(line)
                for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(final_state.status, "dispatch_blocked")
        self.assertEqual(final_state.phase, "dispatch")
        self.assertEqual(events[-1]["event_type"], "task.dispatch_blocked")
        self.assertEqual(events[-1]["payload"]["dispatch_verdict"]["action"], "blocked")
        self.assertEqual(
            events[-1]["payload"]["dispatch_verdict"]["reason"],
            "remote handoff contract failed semantic validation",
        )
        self.assertIn("context pointer not found: missing-artifact.md", events[-1]["payload"]["dispatch_verdict"]["blocking_detail"])

    def test_validate_taxonomy_dispatch_blocks_validator_write_intent(self) -> None:
        task_state = type("TaskStateStub", (), {"route_taxonomy_role": "validator", "route_taxonomy_memory_authority": "task-state"})()

        result = validate_taxonomy_dispatch(
            task_state,
            {
                "goal": "Review task outcome",
                "next_steps": ["Write the updated file and save it."],
                "context_pointers": [],
            },
        )

        self.assertFalse(result.valid)
        self.assertEqual(result.errors, ["validator routes cannot accept write-intent dispatch contracts"])

    def test_validate_taxonomy_dispatch_blocks_canonical_forbidden_promotion_goal(self) -> None:
        task_state = type(
            "TaskStateStub",
            (),
            {"route_taxonomy_role": "specialist", "route_taxonomy_memory_authority": "canonical-write-forbidden"},
        )()

        result = validate_taxonomy_dispatch(
            task_state,
            {
                "goal": "Promote reusable knowledge into canonical memory",
                "next_steps": ["Review the evidence."],
                "context_pointers": [],
            },
        )

        self.assertFalse(result.valid)
        self.assertEqual(
            result.errors,
            ["canonical-write-forbidden routes cannot accept promotion-oriented dispatch goals"],
        )

    def test_validate_taxonomy_dispatch_allows_default_general_executor_route(self) -> None:
        task_state = type(
            "TaskStateStub",
            (),
            {"route_taxonomy_role": "general-executor", "route_taxonomy_memory_authority": "task-state"},
        )()

        result = validate_taxonomy_dispatch(
            task_state,
            {
                "goal": "Implement the requested change",
                "next_steps": ["Edit the target file."],
                "context_pointers": ["artifacts/summary.md"],
            },
        )

        self.assertTrue(result.valid)
        self.assertEqual(result.errors, [])

    def test_validate_taxonomy_dispatch_allows_stateless_route_for_local_baseline_contract(self) -> None:
        task_state = type(
            "TaskStateStub",
            (),
            {"route_taxonomy_role": "validator", "route_taxonomy_memory_authority": "stateless"},
        )()

        result = validate_taxonomy_dispatch(
            task_state,
            {
                "contract_kind": "not_applicable",
                "handoff_boundary": "local_baseline",
                "goal": "Review the generated artifact",
                "next_steps": ["Continue through the existing local execution path."],
                "context_pointers": ["artifacts/summary.md"],
            },
        )

        self.assertTrue(result.valid)
        self.assertEqual(result.errors, [])

    def test_run_task_blocks_dispatch_when_validator_route_receives_write_intent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Validator mismatch",
                goal="Edit the target file and save the result",
                workspace_root=tmp_path,
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
                        execution_kind="artifact_generation",
                        supports_tool_loop=False,
                        filesystem_access="workspace_read",
                        network_access="none",
                        deterministic=True,
                        resumable=True,
                    ),
                    taxonomy=TaxonomyProfile(
                        system_role="validator",
                        memory_authority="task-state",
                    ),
                ),
                reason="Selected a validator route for taxonomy guard verification.",
                policy_inputs={},
            )

            with patch("swallow.orchestrator.select_route", return_value=validator_route):
                final_state = run_task(tmp_path, state.task_id, executor_name="local")

            task_dir = tmp_path / ".swl" / "tasks" / state.task_id
            events = [
                json.loads(line)
                for line in (task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(final_state.status, "dispatch_blocked")
        self.assertEqual(events[-1]["payload"]["dispatch_verdict"]["action"], "blocked")
        self.assertEqual(events[-1]["payload"]["dispatch_verdict"]["reason"], "route taxonomy rejected dispatch contract")
        self.assertIn(
            "validator routes cannot accept write-intent dispatch contracts",
            events[-1]["payload"]["dispatch_verdict"]["blocking_detail"],
        )
