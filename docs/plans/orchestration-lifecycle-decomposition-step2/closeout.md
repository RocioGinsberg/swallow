---
author: codex
phase: orchestration-lifecycle-decomposition-step2
slice: closeout
status: final
depends_on:
  - docs/plans/orchestration-lifecycle-decomposition-step2/context_brief.md
  - docs/plans/orchestration-lifecycle-decomposition-step2/plan.md
  - docs/plans/orchestration-lifecycle-decomposition-step2/plan_audit.md
  - docs/design/INVARIANTS.md
  - docs/design/ORCHESTRATION.md
  - docs/design/HARNESS.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/TEST_ARCHITECTURE.md
---

TL;DR:
LTO-8 Step 2 is implementation-complete on `feat/orchestration-lifecycle-decomposition-step2`: `harness.py` was reduced from the 2077-line baseline to a 1028-line import-compatible orchestration facade with the policy/artifact pipeline extracted; summary, resume-note, and task-memory report builders remain pending a future report-rendering slice.
The phase is behavior-preserving: Orchestrator remains the only task-state control owner, helper-side event emission is constrained by an explicit allowlist guard, and existing `harness.*` / `orchestrator.*` patch targets remain compatible.
Claude review recommends merge with 0 blockers; final Codex and Claude validation both reproduced full default pytest: `734 passed, 8 deselected, 10 subtests passed`.

# LTO-8 Step 2 Closeout: Harness Decomposition and Facade Cleanup

## Scope

- track: `Architecture / Engineering`
- phase: `LTO-8 Step 2 — harness decomposition`
- branch: `feat/orchestration-lifecycle-decomposition-step2`
- mode: behavior-preserving orchestration helper extraction and facade reduction; not a full report-rendering extraction
- base context: LTO-8 Step 1 had already extracted focused helpers from `orchestrator.py`, while `harness.py` remained explicitly deferred at 2077 lines.
- public compatibility targets:
  - `swallow.orchestration.harness.run_execution`
  - `swallow.orchestration.harness.run_retrieval`
  - `swallow.orchestration.harness.run_retrieval_async`
  - `swallow.orchestration.harness.write_task_artifacts`
  - `swallow.orchestration.harness.write_task_artifacts_async`
  - `swallow.orchestration.harness.build_remote_handoff_contract_record`
  - `swallow.orchestration.harness.build_remote_handoff_contract_report`
  - `swallow.orchestration.harness.build_resume_note`
  - `swallow.orchestration.harness.build_retrieval_report`
  - `swallow.orchestration.harness.build_source_grounding`
  - `swallow.orchestration.orchestrator.run_retrieval`
  - `swallow.orchestration.orchestrator.write_task_artifacts`

## Completed Milestones

| Milestone | Result |
|---|---|
| M1 Baseline and facade characterization | Added `tests/unit/orchestration/test_harness_facade.py` to lock `harness.py` compatibility exports, wrapper behavior, and builder output shapes before moving implementation. |
| M2 Retrieval and retrieval-report split | Moved retrieval execution into `retrieval_flow.py`; moved source grounding and retrieval report rendering into `task_report.py`; kept `harness.retrieve_context` patch compatibility and `harness` report re-exports. |
| M3 Artifact layout and record helper split | Moved route/topology/execution-site/dispatch/remote-handoff/handoff/compatibility record and report builders into `artifact_writer.py`; kept `harness.py` re-export wrappers, including the failure-guidance handoff wrapper. |
| M4 Execution attempts and telemetry split | Moved `run_execution` into `execution_attempts.py`; kept `harness.run_executor` patch compatibility; added `test_harness_helper_modules_only_emit_allowlisted_event_kinds` to enforce helper-side telemetry event kinds. |
| M5 Write pipeline cleanup and facade reduction | Moved seven policy evaluation/save/report/event blocks plus checkpoint snapshot and closing `artifacts.written` event helpers into `artifact_writer.py`; kept `write_task_artifacts` as the sequencing compatibility facade and added event-order characterization. |

## Implementation Notes

- `src/swallow/orchestration/harness.py` remains the import-compatible orchestration facade. It now sequences top-level orchestration helper calls and keeps compatibility wrappers, but no longer owns the large retrieval/artifact/policy helper bodies moved in this phase. Summary, resume-note, task-memory, and final write sequencing remain in `harness.py` and are recorded as deferred report-rendering work.
- `src/swallow/orchestration/retrieval_flow.py` owns `run_retrieval` / `run_retrieval_async` implementation details, retrieval persistence, and `retrieval.completed` telemetry.
- `src/swallow/orchestration/execution_attempts.py` owns `run_execution`, executor artifact writes, executor side-effect persistence callback wiring, and `executor.completed` / `executor.failed` telemetry.
- `src/swallow/orchestration/task_report.py` owns source grounding and retrieval-report rendering extracted from `harness.py`.
- `src/swallow/orchestration/artifact_writer.py` now owns artifact path/record/report helpers plus the M5 policy write-pipeline helpers:
  - `write_compatibility_policy_artifacts`
  - `write_execution_fit_policy_artifacts`
  - `write_knowledge_policy_artifacts`
  - `write_validation_policy_artifacts`
  - `write_retry_policy_artifacts`
  - `write_execution_budget_policy_artifacts`
  - `write_stop_policy_artifacts`
  - `write_checkpoint_snapshot_artifacts`
  - `append_artifacts_written_event`
- The new helper-side event allowlist is enforced by `tests/test_invariant_guards.py::test_harness_helper_modules_only_emit_allowlisted_event_kinds` across `retrieval_flow.py`, `execution_attempts.py`, `artifact_writer.py`, and `task_report.py`.
- `tests/test_grounding.py::test_write_task_artifacts_emits_policy_and_artifact_events_in_order` locks the M5 policy/artifact event order:
  `compatibility.completed`, `execution_fit.completed`, `knowledge_policy.completed`, `validation.completed`, `retry_policy.completed`, `execution_budget_policy.completed`, `stop_policy.completed`, `checkpoint_snapshot.completed`, `artifacts.written`.

## Boundary Confirmation

- No `docs/design/*.md` semantic changes.
- No SQLite schema, event schema, repository port, migration, Provider Router behavior, or executor registry behavior changed.
- No FastAPI write route, Control Center write path, request schema, or HTTP error contract was added.
- No new public mutation function or proposal target kind was added.
- `apply_proposal(...)` remains the only canonical / route / policy mutation entry.
- No helper module imports or calls `save_state`.
- `retrieval_flow.py`, `execution_attempts.py`, `artifact_writer.py`, and `task_report.py` do not emit `state_transitioned` or `entered_waiting_human`.
- `orchestrator.py` remains the task-state control owner; this phase did not move task advancement authority out of Orchestrator / Operator.
- Existing `harness.*` and `orchestrator.*` patch surfaces used by CLI, debate-loop, librarian, executor, cost-estimation, and grounding tests remain stable.

## Plan Audit Absorption

`docs/plans/orchestration-lifecycle-decomposition-step2/plan_audit.md` reported `has-concerns` with 0 blockers and 5 concerns. All five were absorbed before or during implementation:

- CONCERN-1: added the named helper-side event allowlist guard.
- CONCERN-2: named and extracted the seven M5 policy blocks; added event-order characterization; preserved the existing `waiting_human` checkpoint state test.
- CONCERN-3: preserved `harness.py` builder re-exports needed by `tests/test_cli.py` and `orchestrator.py`.
- CONCERN-4: preserved `orchestrator.run_retrieval` and `orchestrator.write_task_artifacts` patch targets and kept `tests/test_debate_loop.py` / `tests/test_librarian_executor.py` in validation.
- CONCERN-5: added named unit anchors `tests/unit/orchestration/test_harness_facade.py`, `test_task_report_module.py`, and expanded `test_artifact_writer_module.py`.

## Validation

Codex final validation for M5 / phase closeout:

```bash
.venv/bin/python -m pytest tests/test_grounding.py tests/unit/orchestration/test_artifact_writer_module.py tests/test_invariant_guards.py -q
# 40 passed

.venv/bin/python -m pytest tests/unit/orchestration -q
# 46 passed

.venv/bin/python -m pytest tests/test_grounding.py tests/test_cost_estimation.py tests/test_executor_protocol.py tests/test_executor_async.py tests/test_debate_loop.py tests/test_librarian_executor.py tests/test_invariant_guards.py -q
# 79 passed

.venv/bin/python -m pytest tests/test_cli.py -q
# 242 passed, 10 subtests passed

.venv/bin/python -m compileall -q src/swallow
# passed

.venv/bin/python -m pytest -q
# 734 passed, 8 deselected, 10 subtests passed

git diff --check
# passed
```

Additional static compatibility check:

```bash
rg "append_event|Event\\(|compatibility_counts|execution_fit_counts|knowledge_policy_counts|validation_counts|evaluate_route_compatibility|evaluate_execution_fit|evaluate_knowledge_policy|evaluate_retry_policy|evaluate_stop_policy|evaluate_checkpoint_snapshot|save_compatibility|save_execution_fit|save_validation|save_retry_policy|save_stop_policy|save_checkpoint_snapshot" -n src/swallow/orchestration/harness.py
# no matches
```

## Deferred Work

- `harness.py` is now materially thinner but still over 1000 lines because task memory, summary, resume-note, and write sequencing remain in the facade layer. Optional further extraction should be a new explicit report-rendering slice; `task_report.py` could absorb `build_summary` / `build_resume_note` / `build_task_memory` if a real readability gain emerges, but the move would need careful handling of the many result-type imports they currently consume.
- `orchestrator.py` remains large after LTO-8 Step 1 and Step 2. Further extraction should stay facade-first and must not move `save_state` or task advancement authority out of Orchestrator.
- Debate-loop callback semantics were moved with `run_execution` but not redesigned. Any policy-system treatment remains out of scope.
- `_apply_librarian_side_effects` / proposal-boundary work remains out of scope because it touches `apply_proposal` semantics.
- LTO-13 FastAPI Local Web UI Write Surface remains the recommended next roadmap direction after this phase merges and cluster C closes.
- `v1.6.0` remains deferred until after LTO-8 Step 2 is merged to `main` and the post-merge tag decision is made.

## Review Absorption

Claude review is recorded in `docs/plans/orchestration-lifecycle-decomposition-step2/review_comments.md`.

- Verdict: `recommend-merge`.
- Blockers: none.
- CONCERN-1: closeout and `pr.md` no longer describe the result as a fully thin facade; they now describe the actual result as an import-compatible orchestration facade with policy/artifact pipeline extraction and deferred report-rendering work.
- CONCERN-2: `docs/design/INVARIANTS.md §9` now records `test_harness_helper_modules_only_emit_allowlisted_event_kinds` as the executable guard for helper-side `append_event` constraints.
- Claude independently re-ran `.venv/bin/python -m pytest -q` and reproduced `734 passed, 8 deselected, 10 subtests passed`.

## Completion Status

- Plan audit concerns C-1 through C-5 were absorbed.
- Implementation milestones M1 through M5 are complete and committed.
- Claude review completed with `recommend-merge`, 0 blockers, and 2 non-blocking documentation concerns absorbed.
- Full default pytest, compileall, and diff hygiene passed.
- `closeout.md` and root `pr.md` are prepared for Human PR creation / merge decision.
- Next workflow step: Human closeout / review state commit, PR creation or update from `pr.md`, merge decision, then post-merge roadmap / tag sync.
