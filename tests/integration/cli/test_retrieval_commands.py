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


class LegacyCliRetrievalCommandTest(unittest.TestCase):
    def test_create_task_persists_explicit_retrieval_source_override_in_task_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Explicit retrieval sources",
                goal="Persist override in task semantics",
                workspace_root=tmp_path,
                retrieval_source_types=["repo", "knowledge", "repo", ARTIFACTS_SOURCE_TYPE],
            )
            task_dir = tmp_path / ".swl" / "tasks" / state.task_id
            persisted_state = json.loads((task_dir / "state.json").read_text(encoding="utf-8"))
            task_semantics = json.loads((task_dir / "task_semantics.json").read_text(encoding="utf-8"))
            semantics_report = (task_dir / "artifacts" / "task_semantics_report.md").read_text(encoding="utf-8")

        self.assertEqual(task_semantics["retrieval_source_types"], ["repo", "knowledge", ARTIFACTS_SOURCE_TYPE])
        self.assertEqual(
            persisted_state["task_semantics"]["retrieval_source_types"],
            ["repo", "knowledge", ARTIFACTS_SOURCE_TYPE],
        )
        self.assertIn("- retrieval_source_types: repo, knowledge, artifacts", semantics_report)

    def test_planning_handoff_preserves_existing_retrieval_source_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = create_task(
                base_dir=tmp_path,
                title="Preserve retrieval sources",
                goal="Keep explicit override during planning handoff",
                workspace_root=tmp_path,
                retrieval_source_types=["notes", KNOWLEDGE_SOURCE_TYPE],
            )

            update_task_planning_handoff(
                tmp_path,
                state.task_id,
                constraints=["Do not drop retrieval override"],
                planning_source="chat://phase60-handoff",
            )

            task_dir = tmp_path / ".swl" / "tasks" / state.task_id
            task_semantics = json.loads((task_dir / "task_semantics.json").read_text(encoding="utf-8"))
            semantics_report = (task_dir / "artifacts" / "task_semantics_report.md").read_text(encoding="utf-8")

        self.assertEqual(task_semantics["retrieval_source_types"], ["notes", KNOWLEDGE_SOURCE_TYPE])
        self.assertEqual(task_semantics["source_ref"], "chat://phase60-handoff")
        self.assertIn("- retrieval_source_types: notes, knowledge", semantics_report)

    def test_create_task_rejects_invalid_explicit_retrieval_source_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            with self.assertRaisesRegex(ValueError, "Invalid retrieval source type"):
                create_task(
                    base_dir=tmp_path,
                    title="Invalid retrieval override",
                    goal="Reject unsupported retrieval source types",
                    workspace_root=tmp_path,
                    retrieval_source_types=["repo", "unsupported-source"],
                )

    def test_cli_end_to_end_local_file_promotion_link_and_relation_retrieval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            alpha_doc = tmp_path / "alpha.md"
            beta_doc = tmp_path / "beta.md"
            alpha_doc.write_text(
                "# Alpha Anchor\n\nzephyranchor prismseed establishes the source concept.\n",
                encoding="utf-8",
            )
            beta_doc.write_text(
                "# Beta Expansion\n\nlatchboundary governs downstream policy edges.\n",
                encoding="utf-8",
            )

            self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "ingest-file", str(alpha_doc)]), 0)
            self.assertEqual(main(["--base-dir", str(tmp_path), "knowledge", "ingest-file", str(beta_doc)]), 0)

            candidates = load_staged_candidates(tmp_path)
            alpha_candidate = next(
                candidate
                for candidate in candidates
                if candidate.source_task_id == "ingest-alpha" and candidate.text.startswith("Alpha Anchor")
            )
            beta_candidate = next(
                candidate
                for candidate in candidates
                if candidate.source_task_id == "ingest-beta" and candidate.text.startswith("Beta Expansion")
            )

            self.assertEqual(
                main(["--base-dir", str(tmp_path), "knowledge", "stage-promote", alpha_candidate.candidate_id]),
                0,
            )
            self.assertEqual(
                main(["--base-dir", str(tmp_path), "knowledge", "stage-promote", beta_candidate.candidate_id]),
                0,
            )

            alpha_canonical_id = f"canonical-{alpha_candidate.candidate_id}"
            beta_canonical_id = f"canonical-{beta_candidate.candidate_id}"
            self.assertEqual(
                main(
                    [
                        "--base-dir",
                        str(tmp_path),
                        "knowledge",
                        "link",
                        alpha_canonical_id,
                        beta_canonical_id,
                        "--type",
                        "related_to",
                        "--context",
                        "alpha anchor expands to beta boundary",
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
                        "create",
                        "--title",
                        "CLI Relation E2E",
                        "--goal",
                        "Explain zephyranchor prismseed",
                        "--workspace-root",
                        str(tmp_path),
                        "--executor",
                        "local",
                    ]
                ),
                0,
            )

            task_id = next(
                entry.name
                for entry in (tmp_path / ".swl" / "tasks").iterdir()
                if entry.is_dir() and (entry / "state.json").exists()
            )
            self.assertEqual(main(["--base-dir", str(tmp_path), "task", "run", task_id]), 0)

            retrieval = json.loads((tmp_path / ".swl" / "tasks" / task_id / "retrieval.json").read_text(encoding="utf-8"))
            summary = (tmp_path / ".swl" / "tasks" / task_id / "artifacts" / "summary.md").read_text(encoding="utf-8")

        direct_hit = next(
            item
            for item in retrieval
            if item.get("source_type") == "knowledge"
            and item.get("metadata", {}).get("canonical_id") == alpha_canonical_id
            and item.get("metadata", {}).get("expansion_source") != "relation"
        )
        expanded_hit = next(
            item
            for item in retrieval
            if item.get("source_type") == "knowledge"
            and item.get("metadata", {}).get("canonical_id") == beta_canonical_id
            and item.get("metadata", {}).get("expansion_source") == "relation"
        )

        self.assertEqual(direct_hit["metadata"]["storage_scope"], "canonical_registry")
        self.assertEqual(expanded_hit["metadata"]["storage_scope"], "canonical_registry")
        self.assertEqual(expanded_hit["metadata"]["expansion_parent_object_id"], alpha_candidate.source_object_id)
        self.assertEqual(expanded_hit["metadata"]["expansion_relation_type"], "related_to")
        self.assertIn("retrieval_reused_knowledge_count: 2", summary)
        self.assertIn("retrieval_reused_canonical_registry_count: 2", summary)

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
                    "knowledge_retrieval_mode": "vector",
                    "knowledge_retrieval_adapter": "sqlite_vec",
                    "embedding_backend": "api_embedding",
                    "retrieval_fallback_reason": "",
                    "final_rank": 1,
                    "raw_score": 8,
                    "final_order_basis": "raw_score",
                    "rerank_backend": "none",
                    "rerank_model": "",
                    "rerank_enabled": True,
                    "rerank_configured": False,
                    "rerank_attempted": False,
                    "rerank_applied": False,
                    "rerank_failure_reason": "not_configured",
                },
            )
        ]

        retrieval_report = build_retrieval_report(state, retrieval_items)
        source_grounding = build_source_grounding(retrieval_items)

        self.assertIn("reused_canonical_registry_count: 1", retrieval_report)
        self.assertIn("retrieval_mode: vector", retrieval_report)
        self.assertIn("retrieval_adapter: sqlite_vec", retrieval_report)
        self.assertIn("embedding_backend: api_embedding", retrieval_report)
        self.assertIn("rerank_backend: none", retrieval_report)
        self.assertIn("rerank_configured: False", retrieval_report)
        self.assertIn("final_order_basis: raw_score", retrieval_report)
        self.assertIn("source_policy_warning_count: 0", retrieval_report)
        self.assertIn("evidence_pack_primary_object_count: 1", retrieval_report)
        self.assertIn("evidence_pack_canonical_object_count: 1", retrieval_report)
        self.assertIn("evidence_pack_fallback_hit_count: 0", retrieval_report)
        self.assertIn("## EvidencePack Summary", retrieval_report)
        self.assertIn("source_policy_label: canonical_truth", retrieval_report)
        self.assertIn("source_policy_flags: primary_truth_candidate", retrieval_report)
        self.assertIn("storage_scope: canonical_registry", retrieval_report)
        self.assertIn("canonical_id: canonical-trace123-knowledge-0001", retrieval_report)
        self.assertIn("canonical_policy: reuse_visible", retrieval_report)
        self.assertIn("source_ref: chat://canonical-reuse", retrieval_report)
        self.assertIn("artifact_ref: .swl/tasks/demo/artifacts/evidence.md", retrieval_report)
        self.assertIn("storage_scope: canonical_registry", source_grounding)
        self.assertIn("source_policy_label: canonical_truth", source_grounding)
        self.assertIn("canonical_policy: reuse_visible", source_grounding)

    def test_retrieval_report_warns_when_operational_notes_outrank_canonical_truth(self) -> None:
        state = TaskState(
            task_id="trace123",
            title="Trace retrieval",
            goal="Surface retrieval noise",
            workspace_root="/tmp/trace",
            artifact_paths={
                "retrieval_json": "/tmp/trace/.swl/tasks/trace123/retrieval.json",
                "source_grounding": "/tmp/trace/.swl/tasks/trace123/artifacts/source_grounding.md",
                "task_memory": "/tmp/trace/.swl/tasks/trace123/memory.json",
            },
        )
        retrieval_items = [
            RetrievalItem(
                path="docs/archive_phases/phase64/design_decision.md",
                source_type="notes",
                score=130,
                preview="Historical route decision.",
                citation="docs/archive_phases/phase64/design_decision.md#L105-L138",
                metadata={
                    "final_rank": 1,
                    "adapter_name": "markdown_notes",
                    "chunk_kind": "markdown_section",
                    "source_policy_label": "archive_note",
                    "source_policy_flags": ["operator_context_noise", "fallback_text_hit"],
                },
            ),
            RetrievalItem(
                path=".swl/canonical_knowledge/reuse_policy.json",
                source_type=KNOWLEDGE_SOURCE_TYPE,
                score=99,
                preview="Canonical LLM path boundary.",
                citation=".swl/canonical_knowledge/reuse_policy.json#canonical-staged-090c3193",
                metadata={
                    "final_rank": 2,
                    "storage_scope": "canonical_registry",
                    "canonical_id": "canonical-staged-090c3193",
                    "canonical_policy": "reuse_visible",
                    "adapter_name": "canonical_registry_records",
                    "chunk_kind": "canonical_record",
                    "source_policy_label": "canonical_truth",
                    "source_policy_flags": ["primary_truth_candidate"],
                },
            ),
        ]

        retrieval_report = build_retrieval_report(state, retrieval_items)

        self.assertIn("source_policy_warning_count: 1", retrieval_report)
        self.assertIn("evidence_pack_primary_object_count: 1", retrieval_report)
        self.assertIn("evidence_pack_fallback_hit_count: 1", retrieval_report)
        self.assertIn("## Source Policy Warnings", retrieval_report)
        self.assertIn("operational_doc_outranks_canonical_truth", retrieval_report)
        self.assertIn("source_policy_label: archive_note", retrieval_report)
        self.assertIn("source_policy_flags: operator_context_noise, fallback_text_hit", retrieval_report)

    def test_retrieval_reports_surface_resolved_source_pointers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_path = tmp_path / "docs" / "design" / "KNOWLEDGE.md"
            source_path.parent.mkdir(parents=True)
            source_path.write_text("# Knowledge\n\nEvidence body.\n", encoding="utf-8")
            state = TaskState(
                task_id="trace123",
                title="Trace retrieval",
                goal="Surface source pointers",
                workspace_root=str(tmp_path),
                artifact_paths={
                    "retrieval_json": str(tmp_path / ".swl" / "tasks" / "trace123" / "retrieval.json"),
                    "source_grounding": str(
                        tmp_path / ".swl" / "tasks" / "trace123" / "artifacts" / "source_grounding.md"
                    ),
                    "task_memory": str(tmp_path / ".swl" / "tasks" / "trace123" / "memory.json"),
                },
            )
            retrieval_items = [
                RetrievalItem(
                    path="docs/design/KNOWLEDGE.md",
                    source_type="notes",
                    score=12,
                    preview="Evidence body.",
                    citation="docs/design/KNOWLEDGE.md#L1-L3",
                    title="Knowledge",
                    metadata={
                        "final_rank": 1,
                        "line_start": 1,
                        "line_end": 3,
                        "title_source": "heading",
                        "heading_level": 1,
                    },
                )
            ]

            retrieval_report = build_retrieval_report(state, retrieval_items, base_dir=tmp_path)
            source_grounding = build_source_grounding(retrieval_items, workspace_root=tmp_path, base_dir=tmp_path)

        self.assertIn("## EvidencePack Source Pointers", retrieval_report)
        self.assertIn("status: resolved", retrieval_report)
        self.assertIn("resolved_ref: file://workspace/docs/design/KNOWLEDGE.md", retrieval_report)
        self.assertIn("resolved_path: docs/design/KNOWLEDGE.md", retrieval_report)
        self.assertIn("line_span: L1-L3", retrieval_report)
        self.assertIn("heading_path: Knowledge", retrieval_report)
        self.assertIn("source_pointer_status: resolved", source_grounding)
        self.assertIn("source_pointer_path: docs/design/KNOWLEDGE.md", source_grounding)
        self.assertIn("line_span: L1-L3", source_grounding)

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

            with patch("swallow.orchestration.orchestrator.run_retrieval", return_value=retrieval_items):
                with patch("swallow.orchestration.orchestrator._execute_task_card", return_value=executor_result):
                    with patch("swallow.orchestration.orchestrator.write_task_artifacts", side_effect=write_artifacts_side_effect):
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

            with patch("swallow.orchestration.orchestrator.run_retrieval", return_value=first_retrieval):
                with patch("swallow.orchestration.orchestrator._execute_task_card", return_value=executor_result):
                    with patch("swallow.orchestration.orchestrator.write_task_artifacts", side_effect=write_artifacts_side_effect):
                        first_state = run_task(tmp_path, state.task_id, executor_name="mock")

            with patch("swallow.orchestration.orchestrator.run_retrieval", return_value=second_retrieval):
                with patch("swallow.orchestration.orchestrator._execute_task_card", return_value=executor_result):
                    with patch("swallow.orchestration.orchestrator.write_task_artifacts", side_effect=write_artifacts_side_effect):
                        resumed_state = run_task(tmp_path, state.task_id, executor_name="mock")

            with patch("swallow.orchestration.orchestrator.run_retrieval", return_value=second_retrieval):
                with patch("swallow.orchestration.orchestrator._execute_task_card", return_value=executor_result):
                    with patch("swallow.orchestration.orchestrator.write_task_artifacts", side_effect=write_artifacts_side_effect):
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

    def test_retrieval_evaluation_fixtures_cover_notes_repo_and_artifacts(self) -> None:
        fixture_root = Path(__file__).resolve().parents[2] / "fixtures" / "retrieval_eval"
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
        fixture_root = Path(__file__).resolve().parents[2] / "fixtures" / "retrieval_eval"
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

    def test_retrieve_context_includes_relation_expansion_metadata_for_linked_knowledge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            save_knowledge_objects(
                tmp_path,
                "task123",
                [
                    {
                        "object_id": "knowledge-0001",
                        "text": "Current task graphseed retrieval anchor.",
                        "stage": "verified",
                        "source_kind": "external_knowledge_capture",
                        "source_ref": "chat://task123",
                        "task_linked": True,
                        "captured_at": "2026-04-25T00:00:00+00:00",
                        "evidence_status": "artifact_backed",
                        "artifact_ref": ".swl/tasks/task123/artifacts/summary.md",
                        "retrieval_eligible": True,
                        "knowledge_reuse_scope": "retrieval_candidate",
                    }
                ],
            )
            save_knowledge_objects(
                tmp_path,
                "task999",
                [
                    {
                        "object_id": "knowledge-0002",
                        "text": "Operator note about taxonomy closure and archived evidence bundle.",
                        "stage": "verified",
                        "source_kind": "external_knowledge_capture",
                        "source_ref": "chat://task999",
                        "task_linked": True,
                        "captured_at": "2026-04-25T00:00:00+00:00",
                        "evidence_status": "artifact_backed",
                        "artifact_ref": ".swl/tasks/task999/artifacts/summary.md",
                        "retrieval_eligible": True,
                        "knowledge_reuse_scope": "retrieval_candidate",
                    }
                ],
            )
            stdout = StringIO()
            with redirect_stdout(stdout):
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

            items = retrieve_context(
                tmp_path,
                request=RetrievalRequest(
                    query="graphseed retrieval anchor",
                    source_types=[KNOWLEDGE_SOURCE_TYPE],
                    context_layers=["task", "history"],
                    current_task_id="task123",
                    limit=8,
                    strategy="system_baseline",
                ),
            )

        expanded = next(item for item in items if item.chunk_id == "knowledge-0002")
        self.assertEqual(expanded.metadata["expansion_source"], "relation")
        self.assertEqual(expanded.metadata["expansion_relation_type"], "cites")
        self.assertEqual(expanded.metadata["knowledge_task_relation"], "cross_task")

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

    def test_build_task_retrieval_request_uses_conservative_default_when_route_capabilities_are_missing(self) -> None:
        state = TaskState(
            task_id="request123",
            title="Improve retrieval",
            goal="Refine harness boundary",
            workspace_root="/tmp",
        )

        request = build_task_retrieval_request(state)

        self.assertEqual(request.query, "Improve retrieval Refine harness boundary")
        self.assertEqual(request.source_types, ["knowledge", "notes"])
        self.assertEqual(request.context_layers, ["workspace", "task"])
        self.assertEqual(request.current_task_id, "request123")
        self.assertEqual(request.limit, 8)
        self.assertEqual(request.strategy, "system_baseline")

    def test_build_task_retrieval_request_uses_knowledge_only_for_autonomous_cli_coding_routes(self) -> None:
        route = route_by_name("local-codex")
        self.assertIsNotNone(route)
        assert route is not None
        state = TaskState(
            task_id="request-cli",
            title="Improve retrieval",
            goal="Refine harness boundary",
            workspace_root="/tmp",
            executor_name=route.executor_name,
            route_name=route.name,
            route_executor_family=route.executor_family,
            route_taxonomy_role=route.taxonomy.system_role,
            route_capabilities=route.capabilities.to_dict(),
        )

        request = build_task_retrieval_request(state)

        self.assertEqual(request.source_types, ["knowledge"])

    def test_build_task_retrieval_request_preserves_legacy_sources_for_non_autonomous_cli_fallback_routes(self) -> None:
        route = route_by_name("local-summary")
        self.assertIsNotNone(route)
        assert route is not None
        state = TaskState(
            task_id="request-legacy-cli",
            title="Summarize retrieval",
            goal="Preserve fallback compatibility",
            workspace_root="/tmp",
            executor_name=route.executor_name,
            route_name=route.name,
            route_executor_family=route.executor_family,
            route_taxonomy_role=route.taxonomy.system_role,
            route_capabilities=route.capabilities.to_dict(),
        )

        request = build_task_retrieval_request(state)

        self.assertEqual(request.source_types, ["repo", "notes", "knowledge"])

    def test_build_task_retrieval_request_keeps_http_routes_off_repo_by_default(self) -> None:
        route = route_by_name("http-claude")
        self.assertIsNotNone(route)
        assert route is not None
        state = TaskState(
            task_id="request-http",
            title="Review retrieval",
            goal="Keep HTTP defaults conservative",
            workspace_root="/tmp",
            executor_name=route.executor_name,
            route_name=route.name,
            route_executor_family=route.executor_family,
            route_taxonomy_role=route.taxonomy.system_role,
            route_capabilities=route.capabilities.to_dict(),
        )

        request = build_task_retrieval_request(state)

        self.assertEqual(request.source_types, ["knowledge", "notes"])

    def test_build_task_retrieval_request_keeps_http_routes_off_repo_across_task_families(self) -> None:
        route = route_by_name("http-claude")
        self.assertIsNotNone(route)
        assert route is not None

        for source_kind in (
            "planning_session",
            "review_feedback",
            "operator_entry",
            "knowledge_capture",
            "retrieval_probe",
        ):
            with self.subTest(source_kind=source_kind):
                state = TaskState(
                    task_id=f"request-http-{source_kind}",
                    title="HTTP retrieval family",
                    goal="Keep HTTP defaults conservative",
                    workspace_root="/tmp",
                    executor_name=route.executor_name,
                    route_name=route.name,
                    route_executor_family=route.executor_family,
                    route_taxonomy_role=route.taxonomy.system_role,
                    route_capabilities=route.capabilities.to_dict(),
                    task_semantics={"source_kind": source_kind},
                )

                request = build_task_retrieval_request(state)

                self.assertEqual(request.source_types, ["knowledge", "notes"])

    def test_build_task_retrieval_request_prefers_explicit_retrieval_source_override(self) -> None:
        route = route_by_name("local-codex")
        self.assertIsNotNone(route)
        assert route is not None
        state = TaskState(
            task_id="request-override",
            title="Override retrieval sources",
            goal="Bypass default policy when explicitly configured",
            workspace_root="/tmp",
            executor_name=route.executor_name,
            route_name=route.name,
            route_executor_family=route.executor_family,
            route_taxonomy_role=route.taxonomy.system_role,
            route_capabilities=route.capabilities.to_dict(),
            task_semantics={"retrieval_source_types": ["repo", "knowledge", "repo", ARTIFACTS_SOURCE_TYPE]},
        )

        request = build_task_retrieval_request(state)

        self.assertEqual(request.source_types, ["repo", "knowledge", ARTIFACTS_SOURCE_TYPE])

    def test_build_task_retrieval_request_rejects_invalid_explicit_retrieval_source_override(self) -> None:
        state = TaskState(
            task_id="request-invalid-override",
            title="Invalid retrieval override",
            goal="Reject unsupported retrieval sources",
            workspace_root="/tmp",
            task_semantics={"retrieval_source_types": ["repo", "unsupported-source"]},
        )

        with self.assertRaisesRegex(ValueError, "Invalid retrieval source type"):
            build_task_retrieval_request(state)

    def test_build_task_retrieval_request_does_not_treat_specialist_cli_routes_as_autonomous_coding(self) -> None:
        state = TaskState(
            task_id="request-specialist-cli",
            title="Specialist retrieval",
            goal="Protect explicit input paths",
            workspace_root="/tmp",
            executor_name="librarian",
            route_name="specialist-simulated",
            route_executor_family="cli",
            route_taxonomy_role="specialist",
            route_capabilities={
                "execution_kind": "code_execution",
                "supports_tool_loop": True,
                "filesystem_access": "workspace_write",
                "network_access": "optional",
                "deterministic": False,
                "resumable": True,
            },
        )

        request = build_task_retrieval_request(state)

        self.assertEqual(request.source_types, ["knowledge", "notes"])

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

            with patch("swallow.orchestration.orchestrator.load_state", return_value=created):
                with patch("swallow.orchestration.orchestrator.save_state"):
                    with patch("swallow.orchestration.orchestrator.append_event"):
                        with patch("swallow.orchestration.orchestrator.run_retrieval", side_effect=run_retrieval_spy):
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
                                    run_task(base_dir, created.task_id)

        request = captured_request["request"]
        self.assertEqual(request.query, "Request boundary Pass retrieval request explicitly")
        self.assertEqual(request.source_types, ["knowledge"])
        self.assertEqual(request.context_layers, ["workspace", "task"])
        self.assertEqual(request.current_task_id, "taskrequest")
        self.assertEqual(request.strategy, "system_baseline")

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
            with patch("swallow.orchestration.harness.retrieve_context", side_effect=AssertionError("retrieval should be skipped")):
                with patch("swallow.orchestration.harness.run_executor", return_value=executor_result) as run_executor_mock:
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

            with patch("swallow.orchestration.harness.retrieve_context", return_value=knowledge_retrieval_items):
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
