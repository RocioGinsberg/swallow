---
author: claude
phase: orchestration-lifecycle-decomposition-step2
slice: context-brief
status: draft
depends_on:
  - docs/roadmap.md
  - docs/plans/orchestration-lifecycle-decomposition/closeout.md
  - docs/plans/orchestration-lifecycle-decomposition/plan.md
  - docs/plans/orchestration-lifecycle-decomposition/plan_audit.md
  - docs/plans/orchestration-lifecycle-decomposition/review_comments.md
  - docs/design/INVARIANTS.md
  - docs/design/ORCHESTRATION.md
  - docs/design/HARNESS.md
  - docs/engineering/CODE_ORGANIZATION.md
  - src/swallow/orchestration/harness.py
  - src/swallow/orchestration/orchestrator.py
  - tests/test_invariant_guards.py
---

TL;DR: `harness.py` is 2077 lines and was explicitly out of scope for Step 1; it holds the
execution loop, artifact evaluation pipeline, and all report/summary builders — most of which
call `append_event` and persistence functions directly, not `save_state`. `orchestrator.py`
is still 3331 lines post-Step-1; further facade reduction is constrained by the Control
invariant. The primary risk signal: `harness.py` already calls `append_event` and all
persistence helpers pervasively — extracted helpers from it cannot have the same no-`append_event`
rule that applied to Step 1 orchestrator helpers without a plan revision establishing an allowlist.

---

## 1. Step 1 Recap

LTO-8 Step 1 extracted six focused helper modules from `orchestrator.py`:
`task_lifecycle.py`, `retrieval_flow.py`, `artifact_writer.py`, `subtask_flow.py`,
`execution_attempts.py`, `knowledge_flow.py`. These hold lifecycle payload builders,
retrieval request construction, artifact-path helpers, subtask glue, attempt metadata, and
knowledge write-plan helpers respectively. `orchestrator.py` reduced from 3853 to 3331 lines
(~14%). All extracted helpers were verified clean of `save_state`, `append_event`,
`apply_proposal`, `harness`, and `executor` references by ripgrep and per-helper source-text
assertions in `tests/unit/orchestration/`.

Explicitly deferred to a later step (per `closeout.md §Deferred Follow-up`):
- `harness.py` decomposition — "remains a separate future target"
- Further reduction of `orchestrator.py` — "can continue in later LTO-8 slices, but should
  remain facade-first"
- `execution_attempts.debate_loop_core` / `debate_loop_core_async` callback shape revisit
  (CONCERN-1 from `review_comments.md` — currently filed as LTO-11 design follow-up)
- `_apply_librarian_side_effects` move — requires explicit plan for `apply_proposal` boundary

---

## 2. `harness.py` Current Shape

**Line count:** 2077. **Top-level functions:** 30 (`def` or `async def`; no classes).

### Major responsibility groupings (as code shows)

| Group | Functions | Approx lines |
|-------|-----------|--------------|
| **Execution entry / retrieval execution** | `run_retrieval`, `run_retrieval_async`, `run_execution` | ~130 |
| **Write-task-artifacts pipeline** | `write_task_artifacts`, `write_task_artifacts_async` | ~440 (sync version; this is the central pipeline function) |
| **Policy evaluation count helpers** | `validation_counts`, `compatibility_counts`, `execution_fit_counts`, `knowledge_policy_counts` | ~30 |
| **Retrieval / grounding report builders** | `build_source_grounding`, `build_retrieval_report`, `_format_line_span` | ~165 |
| **Task memory builder** | `build_task_memory` | ~165 |
| **Infrastructure record builders** | `build_route_record`, `build_route_report`, `build_topology_record`, `build_topology_report`, `build_execution_site_record`, `build_execution_site_report`, `build_dispatch_record`, `build_dispatch_report` | ~185 |
| **Remote handoff contract builders** | `build_remote_handoff_contract_record`, `build_remote_handoff_contract_report` | ~160 |
| **Handoff record and report builders** | `build_handoff_record`, `build_handoff_report` | ~190 |
| **Compatibility record builder** | `build_compatibility_record` | ~20 |
| **Summary / resume builders** | `build_summary`, `_summary_surface_fields`, `build_resume_note` | ~480 |
| **Route capability formatter** | `format_route_capabilities` | ~12 |

### Public API surface (imported by other modules)

Search across `src/` and `tests/` for `from swallow.orchestration.harness import`:

- `src/swallow/orchestration/orchestrator.py` (line 43): imports
  `build_remote_handoff_contract_record`, `build_remote_handoff_contract_report`,
  `run_retrieval`, `write_task_artifacts`
- `tests/test_cli.py` (line 35): imports `build_remote_handoff_contract_record`,
  `build_resume_note`, `build_retrieval_report`, `build_source_grounding`
- `tests/test_grounding.py` (line 12): imports `write_task_artifacts`
- `tests/test_cost_estimation.py` (line 13): imports `run_execution`

No other production `src/` modules import directly from `harness.py`. The `orchestrator.py`
import of `run_retrieval` and `write_task_artifacts` are the primary integration seams.

### Direct dependencies on Truth-write and Control-adjacent patterns

`harness.py` imports `append_event` from `swallow.truth_governance.store` (line 60) and calls
it at 11 call sites (lines 87, 146, 320, 341, 362, 378, 406, 437, 463, 531, 599) — these are in
`run_retrieval` (1 call), `run_execution` (1 call), and `write_task_artifacts` (9 calls, one per
policy evaluation step plus the closing `artifacts.written` event).

`harness.py` does NOT call `save_state` or `apply_proposal`. It does call all persistence
helpers for non-task-state records: `save_route`, `save_topology`, `save_execution_site`,
`save_dispatch`, `save_remote_handoff_contract`, `save_knowledge_index`, `save_compatibility`,
`save_checkpoint_snapshot`, `save_execution_fit`, `save_knowledge_policy`, `save_validation`,
`save_retry_policy`, `save_stop_policy`, `save_execution_budget_policy`, `save_memory`,
`save_handoff`, `write_artifact`, `save_retrieval` (60 total truth-write call sites counted by
grep). These are artifact / policy-record writes, not task-state advancement writes.

`harness.py` imports `run_executor` from `swallow.orchestration.executor` (line 18). This is the
only executor dependency; `run_execution` calls it.

`harness.py` imports `persist_executor_side_effects` from
`swallow.knowledge_retrieval.knowledge_suggestions` (line 29) — this is called in
`run_execution` to persist knowledge side-effects.

`harness.py` does NOT import from `swallow.truth_governance.governance` (`apply_proposal`). It
does not call `_apply_*` pattern functions.

### Test coverage

No dedicated `test_harness.py` file exists. Test coverage of harness paths comes from:
- `tests/test_grounding.py`: directly calls `write_task_artifacts` (2 tests, covering
  grounding evidence persistence and `waiting_human` checkpoint state)
- `tests/test_cost_estimation.py`: directly calls `run_execution` (1 test, cost estimator
  injection)
- `tests/test_executor_protocol.py`: patches `swallow.orchestration.harness.run_execution`
  in 3 tests (local CLI, HTTP, CLI agent executor delegation)
- `tests/test_executor_async.py`: patches `swallow.orchestration.harness.run_execution`
  (1 async test)
- Integration tests (`test_cli.py`, `test_binary_fallback.py`, `test_specialist_agents.py`,
  `test_consistency_audit.py`, eval tests): patch `swallow.orchestration.orchestrator.run_retrieval`
  and `swallow.orchestration.orchestrator.write_task_artifacts` — these patch at the
  `orchestrator` import level, not at the `harness` import level. Moving the functions would
  require updating these patch paths.
- Failure-mode / rollback semantics are covered through `write_task_artifacts_async` inside
  `orchestrator.py`'s `run_task`/`run_task_async`, not through direct harness tests.
  The `waiting_human` state check inside `write_task_artifacts` (line 480–493) is specifically
  tested in `test_grounding.py:205`.

---

## 3. `orchestrator.py` Current Shape

**Current line count:** 3331 (post-Step-1). **Total top-level functions:** ~52 (public and
private). No classes.

Functions remaining include: `acknowledge_task`, `create_task`, `update_task_planning_handoff`,
`append_task_knowledge_capture`, `decide_task_knowledge`, `evaluate_task_canonical_reuse`,
`run_task`, `run_task_async`, `build_task_semantics_report`, `build_knowledge_objects_report`,
`_set_phase`, `_record_phase_checkpoint`, `_append_phase_recovery_fallback`,
`_apply_capability_enforcement`, `_apply_route_spec_to_state`, `_dispatch_status_for_transport`,
`_apply_execution_topology`, `_apply_execution_site_contract`, `_begin_execution_attempt`,
`_evaluate_dispatch_for_run`, `_apply_blocked_dispatch_verdict`, `_apply_librarian_side_effects`,
`_persist_librarian_atomic_updates`, `_append_canonical_write_guard_warning`,
`_clear_review_feedback_state`, `_persist_review_feedback`, `_persist_debate_exhausted_artifact`,
`_append_parent_executor_event`, `_run_binary_fallback`, `_run_binary_fallback_async`,
`_build_debate_last_feedback`, `_task_card_token_cost_limit`, `_append_budget_exhausted_event`,
`_budget_guard_result`, `_run_single_task_with_debate`, `_run_single_task_with_debate_async`,
`_run_subtask_attempt`, `_run_subtask_attempt_async`, `_run_subtask_debate_retries`,
`_run_subtask_debate_retries_async`, `_append_subtask_events`, `_build_subtask_review_gate_result`,
`_build_subtask_executor_result`, `_build_subtask_summary_report`, `_run_subtask_orchestration`,
`_run_subtask_orchestration_async`, and helper wrappers around them.

### Areas of further facade reduction potential

- `build_task_semantics_report` (line 3286) and `build_knowledge_objects_report` (line 3330) are
  pure string builders. Step 1 already moved `build_knowledge_objects_report` (the
  knowledge-objects-from-objects version) to `knowledge_flow.py`; these two in `orchestrator.py`
  operate on `TaskState` not raw objects. They could be extracted but the gain is small.
- `_build_subtask_summary_report` (line 1663) is a ~60-line markdown builder that builds only
  from result data; it appears extractable.
- `_build_subtask_review_gate_result` (line 1552), `_build_subtask_executor_result` (line 1581)
  are pure builders and look extractable to `subtask_flow.py`.
- The ~150-line subtask infrastructure (`_append_subtask_events`, `_persist_subtask_review_feedback`,
  `_persist_subtask_debate_exhausted_artifact`) contains `append_event` calls — these would need
  an allowlist revision analogous to what a Step 2 plan would specify.
- Functions interleaved with `save_state` and the task advancement sequencer
  (`_run_single_task_with_debate`, `_run_subtask_orchestration`, `_evaluate_dispatch_for_run`,
  `_apply_librarian_side_effects`) must remain in `orchestrator.py` under the current invariant
  unless an explicit plan revision authorizes a narrower delegation.

---

## 4. Invariant Boundaries That Constrain Extraction

### INVARIANTS §0, Rule 1 (Control only in Orchestrator / Operator)

"任何执行实体不得静默推进 task state." This forbids any helper extracted from `harness.py` from
holding `save_state` calls. `harness.py` does NOT call `save_state`, so the §0 red line is not
crossed by harness's current code. However, `harness.py` does call `append_event` at 11 sites
(in `run_retrieval`, `run_execution`, and `write_task_artifacts`). These are `W*` (append-only,
non-state-transition) calls per the Truth write matrix (§5). The Step 1 plan ruled out
`append_event` in helpers by default, but that was applied to orchestrator-extracted helpers.
For harness-sourced helpers, `append_event` is already the resident pattern.

### ORCHESTRATION.md / HARNESS.md anchor

`HARNESS.md §1`: "Harness provides controlled execution environment and artifact recovery, but
does not decide task advancement." Consistent with harness not calling `save_state`.
`ORCHESTRATION.md §7`: "Orchestration layer decides 'what to do'; Harness provides 'in what
controlled environment'." This creates a soft boundary: functions that decide execution flow (e.g.
`run_execution`) should stay anchored to harness as the execution-environment layer;
record/report builders that merely format state do not carry control authority.

### Step 1 control boundary rules (from `plan.md §Control Boundary Rules`)

The rules as written apply to orchestrator-extracted helpers and include:
- No `save_state` import, call, receive, store, or invoke — applicable to harness-sourced helpers
- No `append_event` calls by default — this rule would need an explicit allowlist for
  harness-sourced helpers, because `run_retrieval`, `run_execution`, and `write_task_artifacts`
  all use `append_event` internally
- Extracted helpers must not import from `swallow.orchestration.harness` or
  `swallow.orchestration.executor` — if functions from `harness.py` are moved to new modules,
  those new modules may retain the `executor` import if needed (e.g. `run_execution` calls
  `run_executor`)
- `append_event` calls whose `event_type` values are not state-transition events (e.g.
  `retrieval.completed`, `compatibility.completed`, `artifacts.written`) can be allowed in helpers
  subject to an explicit event-kind allowlist, as established in Step 1 C-1 resolution

### CODE_ORGANIZATION.md §5 target shape for orchestration

The doc (lines 157-167) notes that Step 1 already extracted the six modules, and that
"harness.py (2077 lines) remains in subsequent step". No additional target names for harness
sub-modules are specified in `CODE_ORGANIZATION.md`; the target shape there ends at the six
Step 1 modules. Any Step 2 module naming is a Codex plan-time decision.

---

## 5. Test Architecture Context

### Test files covering the touched surface

- `tests/test_grounding.py` — directly exercises `write_task_artifacts` (baseline, must stay green)
- `tests/test_cost_estimation.py` — directly exercises `run_execution` (baseline)
- `tests/test_executor_protocol.py` — patches `swallow.orchestration.harness.run_execution` in 3
  tests; any extracted location must keep this patch path working or tests must be updated
- `tests/test_executor_async.py` — patches `swallow.orchestration.harness.run_execution`
- `tests/test_binary_fallback.py`, `tests/test_specialist_agents.py`,
  `tests/test_consistency_audit.py`, `tests/eval/test_consensus_eval.py` — patch at
  `swallow.orchestration.orchestrator.run_retrieval` and
  `swallow.orchestration.orchestrator.write_task_artifacts`; if these functions are moved out of
  harness but remain re-exported by `orchestrator.py`, the patch paths are unaffected

### Baseline characterization anchors

- `tests/test_grounding.py:165` — `write_task_artifacts` grounding evidence persistence
- `tests/test_grounding.py:205` — `write_task_artifacts` waiting_human checkpoint state
  preservation (failure-mode / rollback test — must preserve patch-target compatibility)
- `tests/test_invariant_guards.py` — all 17 guards in `INVARIANTS §9` must remain green
- `tests/unit/orchestration/` — the 6 Step 1 unit test files (35 tests) cover extracted helpers;
  new helpers would need analogous coverage

### No `test_harness.py` exists

`harness.py` has no dedicated unit test file. Test coverage of its internal functions
(`build_summary`, `build_resume_note`, `build_handoff_record`, `build_task_memory`,
`build_route_record`, `build_retrieval_report`, etc.) is purely through integration tests that
exercise the full `run_task` path or through the two direct-call tests in `test_grounding.py`
and `test_cost_estimation.py`. Step 2 should add characterization tests before extraction,
consistent with Step 1's M1 pattern.

---

## 6. Deferred Items Inherited

From `closeout.md §Deferred Follow-up` and `review_comments.md §CONCERN Summary`:

- **Debate-loop closure pattern design follow-up** (`review_comments.md` CONCERN-1): the
  `debate_loop_core` / `debate_loop_core_async` callback shape where the helper holds temporal
  control of when orchestrator-injected mutating callables fire. Explicitly deferred to LTO-11
  per review; Step 2 should not pull this in.
- **`_apply_librarian_side_effects` move** (`closeout.md`): any move requires explicit plan for
  the `apply_proposal` boundary; Step 1 explicitly kept it in `orchestrator.py`. Step 2 can
  choose to address it but it requires an `apply_proposal`-boundary plan note.
- **LTO-7 CONCERN-3 / `test_route_metadata_writes_only_via_apply_proposal` allowlist drift**
  (`review_comments.md` CONCERN-3): was targeted for LTO-9, not Step 2. Step 2 should not touch
  `test_invariant_guards.py` guard allowlists except those directly relevant to harness extraction.
- **Further orchestrator.py reduction** (`closeout.md`): "can continue in later LTO-8 slices,
  but should remain facade-first" — this is in scope for Step 2 but is secondary to harness work.
- **`apply_outbox.py` no-op persistence** (LTO-10 deferred, `active_context.md`): entirely
  separate from Step 2 scope; should not be absorbed.

---

## 7. Estimated Scope Size

**Rough partition of harness.py's 2077 lines:**

| Category | Estimated lines | Notes |
|----------|-----------------|-------|
| **Clearly extractable behavior-preserving helpers** (pure record/report builders, count helpers, surface-field helpers) | ~800 (38%) | `build_route_record/report`, `build_topology_record/report`, `build_execution_site_record/report`, `build_dispatch_record/report`, `build_remote_handoff_contract_record/report`, `build_handoff_record/report`, `build_compatibility_record`, `build_task_memory`, `build_retrieval_report`, `build_source_grounding`, `_format_line_span`, `_summary_surface_fields`, `format_route_capabilities`, count helpers. None call `save_state`; most could be extracted with minimal `append_event` concern. |
| **Interleaved with Control authority / persistence pipeline** | ~710 (34%) | `write_task_artifacts` (the central pipeline: evaluates 7 policies, calls 11 `append_event` sites and ~20 persistence helpers in sequence). The function is a single coordinated pipeline and decomposing it requires deciding which sub-units are extractable without breaking the sequential evaluation contract. `run_execution` is also in this group (calls `run_executor` from `executor.py` + 1 `append_event`). |
| **Execution entry points** (`run_retrieval`, `run_retrieval_async`) | ~35 (2%) | These call `save_retrieval` and `append_event`. They are currently imported directly by `orchestrator.py`. The question of whether they merge into `retrieval_flow.py` or stay in harness is a key Step 2 decision. |
| **Summary / resume note builders** | ~530 (26%) | `build_summary`, `build_resume_note` — large but pure text builders. No `append_event` or `save_state`. Extractable in principle, but they consume many result types that `write_task_artifacts` also uses, so extraction creates a dependency on the same import surface. Could merge into a `task_report_builder.py` or stay in harness. |

**Assessment for Human direction decision:** Step 2 is likely a 4–5 milestone phase comparable
in effort to LTO-9 Step 1. The "clearly extractable" ~38% can be done in 2 milestones.
`write_task_artifacts` decomposition (34%) is the hardest slice — the pipeline calls `append_event`
at 9 internal steps and any sub-unit extraction requires explicit event-kind allowlisting. A
conservative approach would extract the pure record/report builders first, characterize
`write_task_artifacts`, and leave the execution entry points for last. An aggressive approach
would merge `run_retrieval` / `run_retrieval_async` into `retrieval_flow.py` in milestone 1
and tackle the artifact pipeline in later milestones.

---

## 8. Open Questions for Codex

1. **Should `run_retrieval` / `run_retrieval_async` move into `retrieval_flow.py` as execution
   siblings, or remain in `harness.py` as the execution-environment entry points?** Step 1 kept
   these in harness explicitly (plan.md M2: "do not move `run_retrieval(...)` or
   `run_retrieval_async(...)` execution from `harness.py` into `retrieval_flow.py`"). That
   constraint applied during Step 1; Step 2 can revisit, but the allowlist for `append_event`
   and `save_retrieval` in `retrieval_flow.py` would need to be explicitly authorized.

2. **Should `write_task_artifacts` be decomposed into sub-functions, or only have its
   surrounding record/report builders extracted while the pipeline orchestration stays intact?**
   The function is ~430 lines with 9 sequential policy evaluation + event append blocks; it is a
   coordinated pipeline with a 7-tuple return. Decomposing the internal blocks into sub-helpers
   changes the call structure and requires an `append_event` allowlist for each sub-helper.

3. **Should the record/report builders for route/topology/execution-site/dispatch/remote-handoff
   be grouped into a single new module (e.g. `execution_record_builder.py`) or spread across
   existing modules (`artifact_writer.py`, `task_lifecycle.py`)?** `CODE_ORGANIZATION.md §5`
   does not name a target module for these.

4. **Should `build_summary` and `build_resume_note` be extracted together into a new
   `task_report_builder.py`, or is the size reduction from `harness.py` insufficient to justify
   a new module?** These two functions alone account for ~530 lines (25%).

5. **What `append_event` allowlist applies to Step 2 extracted modules?** Step 1 ruled
   `append_event = none` for all helpers. Any Step 2 module that is a sub-unit of
   `write_task_artifacts` must carry event kinds such as `compatibility.completed`,
   `execution_fit.completed`, `knowledge_policy.completed`, `validation.completed`,
   `retry_policy.completed`, `execution_budget_policy.completed`, `stop_policy.completed`,
   `checkpoint_snapshot.completed`, `artifacts.written`. The plan must specify the allowlist
   before implementation.

6. **How should the `test_executor_protocol.py` / `test_executor_async.py` patch paths be
   handled?** These patch `swallow.orchestration.harness.run_execution`. If `run_execution` is
   moved, these patch paths break. Codex should decide whether to re-export from harness as a
   compatibility facade or update the patch sites.
