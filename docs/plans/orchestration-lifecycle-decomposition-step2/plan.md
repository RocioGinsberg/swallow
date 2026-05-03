---
author: codex
phase: orchestration-lifecycle-decomposition-step2
slice: phase-plan
status: review
depends_on:
  - docs/active_context.md
  - docs/roadmap.md
  - docs/plans/orchestration-lifecycle-decomposition-step2/context_brief.md
  - docs/design/INVARIANTS.md
  - docs/design/ORCHESTRATION.md
  - docs/design/HARNESS.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/TEST_ARCHITECTURE.md
  - src/swallow/orchestration/harness.py
  - src/swallow/orchestration/orchestrator.py
  - src/swallow/orchestration/retrieval_flow.py
  - src/swallow/orchestration/artifact_writer.py
  - src/swallow/orchestration/execution_attempts.py
  - src/swallow/orchestration/task_lifecycle.py
  - src/swallow/orchestration/subtask_flow.py
  - src/swallow/orchestration/knowledge_flow.py
  - tests/test_invariant_guards.py
  - tests/test_cli.py
  - tests/test_grounding.py
  - tests/test_cost_estimation.py
  - tests/test_executor_protocol.py
  - tests/test_executor_async.py
---

TL;DR:
LTO-8 Step 2 decomposes `src/swallow/orchestration/harness.py` into focused orchestration helpers while keeping `harness.py` import-compatible as a thin facade for existing callers and tests.
The phase is behavior-preserving: no task-state authority moves out of `orchestrator.py`, no schema or Provider Router change is introduced, and no new control plane appears.
The hardest part is `write_task_artifacts`: the plan makes its `append_event` allowlist explicit and splits pure report / record builders out before touching sequencing.

# LTO-8 Step 2 Plan: Harness Decomposition and Facade Cleanup

## Frame

- track: `Architecture / Engineering`
- phase: `Orchestration Lifecycle Decomposition / LTO-8 Step 2`
- roadmap ticket: `LTO-8 Step 2 — harness.py 拆分`
- long-term goal: `LTO-8 Orchestration Lifecycle Decomposition`
- recommended_branch: `feat/orchestration-lifecycle-decomposition-step2`
- implementation mode: behavior-preserving / facade-first / milestone-gated
- planning branch: `main`

## Goals

1. Reduce `src/swallow/orchestration/harness.py` by moving pure builders, report renderers, and artifact-layout helpers into focused modules.
2. Keep `orchestrator.py` as the only Control Plane owner for task advancement, state persistence, and review-gate decisions.
3. Keep `harness.py` import-compatible for existing callers and patch targets while shrinking it to a thin compatibility facade.
4. Make the `append_event` boundary explicit for harness-sourced helpers that emit telemetry or artifact-complete events.
5. Preserve the current CLI / test patch surface where possible, especially `swallow.orchestration.harness.run_execution`, `run_retrieval`, and `write_task_artifacts`.

## Non-Goals

- Do not move task state advancement authority out of `orchestrator.py`.
- Do not introduce a second control plane, a second truth store, or a parallel task lifecycle implementation.
- Do not change task state schema, truth schema, Provider Router behavior, or executor registry behavior.
- Do not add FastAPI write routes or any new HTTP write surface.
- Do not redesign debate-loop closure semantics as a new policy system; that follow-up stays parked for a later phase.
- Do not widen `apply_proposal` authority or move governance mutation semantics into this phase.
- Do not start a `harness.py` to `web/api.py` API redesign; this phase stays on orchestration internals.

## Scope Decisions From `context_brief.md`

1. `run_retrieval` and `run_retrieval_async` will move their implementation into `retrieval_flow.py`, but `harness.py` will keep wrapper exports for patch compatibility.
2. `run_execution` will move its implementation into `execution_attempts.py`, again with `harness.py` preserved as a compatibility facade.
3. `write_task_artifacts` will be decomposed into focused helpers rather than left monolithic; the harness wrapper will remain as the public call site.
4. A new `task_report.py` module will own pure text-report builders and summary/resume builders so `harness.py` no longer carries the largest markdown payloads.
5. `harness.py` itself remains in scope only as a thin facade and orchestration entrypoint shell, not as a place to introduce new behavior.
6. Existing patch targets in `tests/test_executor_protocol.py`, `tests/test_executor_async.py`, `tests/test_grounding.py`, `tests/test_cost_estimation.py`, `tests/test_debate_loop.py`, and `tests/test_librarian_executor.py` should stay stable unless a specific wrapper cannot be preserved safely.
7. `harness.py` must preserve compatibility exports for all currently imported non-entry builder symbols:
   - `build_remote_handoff_contract_record`
   - `build_remote_handoff_contract_report`
   - `build_resume_note`
   - `build_retrieval_report`
   - `build_source_grounding`

## Plan Audit Absorption

`docs/plans/orchestration-lifecycle-decomposition-step2/plan_audit.md` returned `has-concerns` with 0 blockers and 5 concerns. This revision absorbs all five:

- C-1: M4 now names `tests/test_invariant_guards.py::test_harness_helper_modules_only_emit_allowlisted_event_kinds` as the enforcement mechanism for the helper-side `append_event` allowlist.
- C-2: M5 now names the seven policy evaluation blocks inside `write_task_artifacts`, their helper target, an event-order characterization test, and the `waiting_human` checkpoint preservation gate.
- C-3: Scope decisions and M1/M2/M3 acceptance now explicitly preserve the `harness.py` compatibility exports imported by `tests/test_cli.py` and `orchestrator.py`.
- C-4: Scope decisions and M2/M5 validation now name `tests/test_debate_loop.py` and `tests/test_librarian_executor.py` because they patch `orchestrator.run_retrieval` / `orchestrator.write_task_artifacts`.
- C-5: M1 now names `tests/unit/orchestration/test_harness_facade.py`; M2/M3 name `test_task_report_module.py` and expanded `test_artifact_writer_module.py` as the helper characterization anchors.

## Target Module Shape

| Area | Target files | Ownership |
|---|---|---|
| Harness facade | `src/swallow/orchestration/harness.py` | Import-compatible wrappers only; no heavy builder ownership after the phase completes |
| Retrieval execution | `src/swallow/orchestration/retrieval_flow.py` | `run_retrieval`, `run_retrieval_async`, retrieval request construction, previous retrieval loading, retrieval telemetry boundary |
| Execution attempts | `src/swallow/orchestration/execution_attempts.py` | `run_execution`, attempt metadata, debate-loop core, budget-exhaustion builders, execution telemetry helpers |
| Artifact layout and record helpers | `src/swallow/orchestration/artifact_writer.py` | Task artifact path maps, route/topology/execution-site/dispatch/remote-handoff/handoff/compatibility record builders, low-level artifact writes |
| Task reports | `src/swallow/orchestration/task_report.py` | `build_source_grounding`, `build_retrieval_report`, `build_task_memory`, `build_summary`, `build_resume_note`, count helpers, formatter helpers |
| Lifecycle payload helpers | `src/swallow/orchestration/task_lifecycle.py` | Phase event/checkpoint/recovery payloads; stay as the existing pure lifecycle owner |
| Subtask artifact helpers | `src/swallow/orchestration/subtask_flow.py` | Subtask extra-artifact collection and subtask artifact refs; only touched if needed for compatibility cleanup |
| Knowledge / existing report helpers | `src/swallow/orchestration/knowledge_flow.py` | Remains the owner of knowledge-plane builders already extracted in Step 1; no new authority expansion |

## Milestones

| Milestone | Slice | Scope | Risk | Validation | Gate |
|---|---|---|---|---|---|
| M1 | Baseline and facade characterization | Characterize current harness entry points and report outputs before moving logic; add or expand unit tests for `harness.py` facade compatibility and new helper-module boundary assertions | high | focused `tests/unit/orchestration/` + invariant guards | Human review + commit |
| M2 | Retrieval and retrieval-report split | Move retrieval implementation into `retrieval_flow.py`; move source-grounding / retrieval-report text helpers into `task_report.py`; keep `harness.py` wrappers stable | high | retrieval-focused tests + `tests/test_grounding.py` + `tests/test_cli.py` affected paths | Human review + commit |
| M3 | Artifact layout and record helper split | Move route/topology/execution-site/dispatch/remote-handoff/handoff/compatibility record and path helpers out of `harness.py` into `artifact_writer.py`; keep low-level artifact I/O centralized | high | artifact writer tests + targeted CLI/task lifecycle coverage | Human review + commit |
| M4 | Execution attempts and telemetry split | Move `run_execution` and execution-attempt metadata / budget-exhaustion helpers into `execution_attempts.py`; define the explicit `append_event` allowlist for harness-sourced helper telemetry | high | execution protocol / async / cost-estimation tests + invariant guards | Human review + commit |
| M5 | Write pipeline cleanup and facade reduction | Decompose `write_task_artifacts` across the new helper modules; keep `harness.py` as a thin facade; verify patch compatibility, async wrappers, full validation, and closeout | medium-high | full default pytest + compileall + diff hygiene + review gate | Human review + commit, then Claude PR review |

## M1 Acceptance: Baseline and Facade Characterization

Scope:

- Add narrow characterization coverage for the current `harness.py` exports:
  - `run_retrieval`
  - `run_retrieval_async`
  - `run_execution`
  - `write_task_artifacts`
  - `write_task_artifacts_async`
- Add `tests/unit/orchestration/test_harness_facade.py` for facade import compatibility and wrapper behavior.
- Assert `harness.py` exports all external compatibility names currently imported by `orchestrator.py` and `tests/test_cli.py`:
  - `run_execution`
  - `run_retrieval`
  - `run_retrieval_async`
  - `write_task_artifacts`
  - `write_task_artifacts_async`
  - `build_remote_handoff_contract_record`
  - `build_remote_handoff_contract_report`
  - `build_resume_note`
  - `build_retrieval_report`
  - `build_source_grounding`
- Add or expand unit tests for the new or expanded helper modules so boundary assertions fail loudly if they ever pick up control-plane authority.
- Capture the current report-builder contracts that are about to move: source grounding, retrieval report, task memory, summary, resume note, artifact path maps, and artifact record builders.

Acceptance:

- Current behavior remains unchanged on pre-migration code.
- A failing test exists for any future helper module that imports or calls `save_state`.
- Facade import compatibility is asserted for `harness.py` exports before any implementation move.
- `tests/unit/orchestration/test_harness_facade.py` follows the existing `test_<module>_module.py` convention and becomes the stable M1 anchor.
- `tests/test_invariant_guards.py -q` still passes at the baseline.

## M2 Acceptance: Retrieval and Retrieval-Report Split

Scope:

- Move `run_retrieval` and `run_retrieval_async` implementation into `retrieval_flow.py`.
- Keep `harness.py` wrapper exports so current patch targets continue to work.
- Move `build_source_grounding` and `build_retrieval_report` into `task_report.py`.
- Add `tests/unit/orchestration/test_task_report_module.py` for source-grounding and retrieval-report contracts.
- Keep retrieval-source policy behavior, previous retrieval loading, and retrieval request construction intact.

Acceptance:

- `retrieval_flow.py` owns retrieval request construction and retrieval execution support.
- `task_report.py` owns source-grounding and retrieval-report text rendering.
- No helper in this slice imports `save_state`.
- `run_retrieval` compatibility through `harness.py` remains intact for `orchestrator.py` and test patching.
- `run_retrieval` remains importable from `swallow.orchestration.orchestrator` so `tests/test_debate_loop.py` and `tests/test_librarian_executor.py` patch paths keep working.
- `build_retrieval_report` and `build_source_grounding` remain importable from `swallow.orchestration.harness` for `tests/test_cli.py`.
- Focused retrieval and grounding tests pass on the pre-migration and post-migration shape.

## M3 Acceptance: Artifact Layout and Record Helper Split

Scope:

- Move artifact path-map logic into `artifact_writer.py`.
- Move route / topology / execution-site / dispatch / remote-handoff / handoff / compatibility record builders and corresponding text report builders into the new helper split.
- Keep low-level artifact file writes in a single owning module rather than scattering `write_artifact(...)` calls across many helpers.
- Keep the synchronous artifact pipeline shape stable for the harness wrapper.
- Expand `tests/unit/orchestration/test_artifact_writer_module.py` for remote-handoff, handoff, route, topology, execution-site, dispatch, and compatibility record/report contracts.

Acceptance:

- `artifact_writer.py` is the owner for artifact-layout helpers and low-level artifact write helpers.
- `task_report.py` owns the pure report text builders that do not need artifact I/O.
- The new helper modules remain free of `save_state` and free of `orchestrator` / `harness` imports.
- `build_remote_handoff_contract_record` and `build_remote_handoff_contract_report` remain importable from `swallow.orchestration.harness` unless `orchestrator.py` and all direct test imports are intentionally updated in the same milestone.
- Existing artifact-related tests remain green.

## M4 Acceptance: Execution Attempts and Telemetry Split

Scope:

- Move `run_execution` into `execution_attempts.py`.
- Move execution-attempt metadata and budget-exhaustion builders into the same module so the attempt lifecycle stays together.
- Keep debate-loop helpers in the same module, but document that their callback semantics are telemetry-only and do not grant state authority.
- Make the event allowlist explicit for any helper that appends telemetry events.

Allowed helper-side event kinds:

- `retrieval.completed`
- `executor.completed`
- `executor.failed`
- `compatibility.completed`
- `execution_fit.completed`
- `knowledge_policy.completed`
- `validation.completed`
- `retry_policy.completed`
- `execution_budget_policy.completed`
- `stop_policy.completed`
- `checkpoint_snapshot.completed`
- `artifacts.written`

Disallowed helper-side event kinds:

- `state_transitioned`
- `entered_waiting_human`
- any new state-advance event kind not explicitly listed above

Allowlist enforcement:

- Add `tests/test_invariant_guards.py::test_harness_helper_modules_only_emit_allowlisted_event_kinds`.
- The guard must scan helper modules that are allowed to append events:
  - `src/swallow/orchestration/retrieval_flow.py`
  - `src/swallow/orchestration/execution_attempts.py`
  - `src/swallow/orchestration/artifact_writer.py`
  - `src/swallow/orchestration/task_report.py`
- The guard must fail on any `event_type` string literal outside the allowed list above.
- The guard must explicitly fail on disallowed state-advance strings such as `state_transitioned` and `entered_waiting_human` in those helper modules.

Acceptance:

- `execution_attempts.py` remains free of `save_state`.
- Any helper that appends events only emits from the explicit allowlist above.
- The named allowlist guard exists and passes.
- `tests/test_cost_estimation.py`, `tests/test_executor_protocol.py`, and `tests/test_executor_async.py` still pass.
- `tests/test_invariant_guards.py -q` still passes without broadening the Control Plane allowlist.

## M5 Acceptance: Write Pipeline Cleanup and Facade Reduction

Scope:

- Decompose `write_task_artifacts` so the harness wrapper only sequences helper calls and does not own the report/record payload construction.
- The seven policy evaluation blocks must be extracted as named helper functions while preserving order:
  - compatibility evaluation / save / report / `compatibility.completed`
  - execution fit evaluation / save / report / `execution_fit.completed`
  - knowledge policy evaluation / save / report / `knowledge_policy.completed`
  - validation evaluation / save / report / `validation.completed`
  - retry policy evaluation / save / report / `retry_policy.completed`
  - execution budget policy evaluation / save / report / `execution_budget_policy.completed`
  - stop policy evaluation / save / report / `stop_policy.completed`
- These helpers should live in `artifact_writer.py` unless implementation reveals a narrower existing owner; any divergence must be recorded in closeout.
- Checkpoint snapshot finalization and the closing `artifacts.written` event remain in the artifact pipeline helper layer, not in `orchestrator.py`.
- Keep `harness.py` import-compatible for the current top-level call sites.
- Validate that synchronous and async wrappers still behave the same from the caller’s perspective.
- Run the final validation gate and prepare closeout / PR materials.

Acceptance:

- `harness.py` is reduced to a thin compatibility facade with no heavy builder ownership.
- `write_task_artifacts` behavior is unchanged from a caller’s perspective.
- Add or update a characterization test that asserts `write_task_artifacts` emits the policy/artifact event kinds in the current sequential order:
  - `compatibility.completed`
  - `execution_fit.completed`
  - `knowledge_policy.completed`
  - `validation.completed`
  - `retry_policy.completed`
  - `execution_budget_policy.completed`
  - `stop_policy.completed`
  - `checkpoint_snapshot.completed`
  - `artifacts.written`
- `tests/test_grounding.py::test_write_task_artifacts_preserves_waiting_human_checkpoint_state` remains green without modification.
- `write_task_artifacts` remains importable from `swallow.orchestration.orchestrator` so `tests/test_debate_loop.py` and `tests/test_librarian_executor.py` patch paths keep working.
- `tests/test_grounding.py`, `tests/test_cli.py`, and the orchestration unit suite remain green.
- Final gates pass:
  - `.venv/bin/python -m pytest tests/unit/orchestration -q`
  - `.venv/bin/python -m pytest tests/test_grounding.py tests/test_cost_estimation.py tests/test_executor_protocol.py tests/test_executor_async.py tests/test_debate_loop.py tests/test_librarian_executor.py tests/test_invariant_guards.py -q`
  - `.venv/bin/python -m pytest tests/test_cli.py -q`
  - `.venv/bin/python -m pytest -q`
  - `.venv/bin/python -m compileall -q src/swallow`
  - `git diff --check`

## Material Risks

- **Sequential pipeline drift**: `write_task_artifacts` is a long, ordered pipeline. Mitigation: move pure builders first, then split orchestration sequencing only after behavior is characterized.
- **Hidden state authority via closures**: the existing AST guard does not catch callable injection. Mitigation: every new helper test must assert `save_state` does not appear in the helper source at all, not merely that it is not called directly.
- **Append-only telemetry confusion**: some helpers may append telemetry events, which is legal, but they must not emit state-transition events. Mitigation: explicit event-kind allowlist in M4 and source-text assertions in the helper tests.
- **Patch-target compatibility**: current tests patch `swallow.orchestration.harness.run_execution` and related facade names. Mitigation: preserve wrappers in `harness.py` rather than forcing test rewrites.
- **Import-cycle risk**: new helper modules must not pull in `harness.py` or `executor.py` casually. Mitigation: verify transitive imports before each move and keep the ownership of `run_execution`/retrieval logic narrow.
- **Over-splitting the phase**: too many tiny modules can make review harder. Mitigation: keep the split at the module boundaries above and do not chase further micro-refactors once the facade is thin and the tests are stable.

## Validation Plan

Focused commands will be refined per milestone, but the minimum gates are:

```bash
.venv/bin/python -m pytest tests/unit/orchestration -q
.venv/bin/python -m pytest tests/test_grounding.py tests/test_cost_estimation.py tests/test_executor_protocol.py tests/test_executor_async.py tests/test_debate_loop.py tests/test_librarian_executor.py tests/test_invariant_guards.py -q
.venv/bin/python -m pytest tests/test_cli.py -q
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src/swallow
git diff --check
```

No eval coverage is required. This phase is behavior-preserving orchestration decomposition, not quality-gradient retrieval or LLM-output tuning.

## Branch, Review, and Commit Gates

- Recommended implementation branch after Human Plan Gate: `feat/orchestration-lifecycle-decomposition-step2`.
- Milestones are commit gates. Human should review and commit after each milestone before Codex proceeds.
- Suggested milestone commit scopes:
  - `test(orchestration): characterize harness facade`
  - `refactor(orchestration): split retrieval and report helpers`
  - `refactor(orchestration): split artifact layout and record helpers`
  - `refactor(orchestration): split execution attempts and telemetry`
  - `refactor(orchestration): thin harness facade and close out`
- Claude `plan_audit.md` is required before Human Plan Gate.
- Claude PR review is required after implementation before merge.

## Completion Conditions

1. `plan_audit.md` has no unresolved `[BLOCKER]`, and Human Plan Gate passes before implementation begins.
2. `harness.py` is reduced to a thin compatibility facade for the moved retrieval / execution / artifact-report logic.
3. The new helper modules own their respective pure builders, record builders, and execution-entry helpers.
4. No helper module owns task-state advancement authority or `save_state`.
5. Any helper that appends events does so only from the explicit telemetry allowlist in M4.
6. `tests/unit/orchestration/` contains focused coverage for each new helper module, including `test_harness_facade.py` and `test_task_report_module.py`, and the existing compatibility tests still pass.
7. No FastAPI write endpoint is added.
8. Full default pytest, compileall, invariant guards, and diff hygiene pass.
9. Closeout records the actual module split, compatibility decisions, deferred work, and the next step toward LTO-13.
