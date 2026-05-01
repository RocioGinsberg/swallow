---
author: claude
phase: orchestration-lifecycle-decomposition
slice: pr-review
status: review
depends_on:
  - docs/plans/orchestration-lifecycle-decomposition/plan.md
  - docs/plans/orchestration-lifecycle-decomposition/plan_audit.md
  - docs/plans/orchestration-lifecycle-decomposition/closeout.md
  - docs/design/INVARIANTS.md
  - docs/design/ORCHESTRATION.md
  - docs/engineering/CODE_ORGANIZATION.md
  - pr.md
---

TL;DR:
Implementation matches the audit-revised plan and resolves all 1 BLOCKER + 7 CONCERNs from `plan_audit.md`. `orchestrator.py` reduced from 3853 to 3331 lines (about 14% facade-reduction; conservative on purpose), six new focused helpers added, all helpers verified clean of `save_state` / `append_event` / `apply_proposal` / `harness` / `executor` references both by ripgrep and by per-helper unit-test source-text assertions. Full pytest passes locally (686 passed). Two CONCERN on debate-loop closure pattern + LTO-7 followup carryover; one PASS-with-note on overall reduction depth being modest. Recommendation: **merge**.

# PR Review: Orchestration Lifecycle Decomposition (LTO-8 Step 1)

## Review Scope

- branch: `feat/orchestration-lifecycle-decomposition` @ `fe31d72`
- merge-base on `main`: post-LTO-7 (`9de4c66 docs(state):update roadmap`)
- diff stat: 18 files, +2830 / −788
- src changes: 6 new helper modules, `orchestrator.py` reduced 3853 → 3331 lines (~14%)
- test changes: 6 new files under `tests/unit/orchestration/` (35 focused tests)
- plan / audit / closeout / pr.md: present and consistent
- full pytest re-verified locally during review: `686 passed, 8 deselected, 10 subtests passed in 110.88s`

## 1. Plan Conformance — `[PASS]`

- [PASS] All six target modules from plan `§Target Module Shape For This Phase` exist with the named ownership (`task_lifecycle.py`, `retrieval_flow.py`, `artifact_writer.py`, `subtask_flow.py`, `execution_attempts.py`, `knowledge_flow.py`).
- [PASS] `orchestrator.py` retained as Control Plane facade. `run_task` / `run_task_async` / `create_task` are not exported from any helper.
- [PASS] Milestone shape matches plan: M1 lifecycle helpers, M2 retrieval flow, M3 artifact writer + subtask glue, M4 execution attempts, M5 knowledge flow + closeout. Each milestone is a separate commit (`0c6545d`, `e4d0539`, `246aac3`, `9fdf743`, `fe31d72`).
- [PASS] No `docs/design/*.md` changes, no schema migrations, no artifact filename changes, no Provider Router behavior changes, no Path A/B/C semantic changes.

## 2. Audit Resolution — `[PASS]`

The audit recorded 1 BLOCKER and 7 CONCERNs. All eight are absorbed:

- [PASS] **BLOCKER (M6 milestone count)**. Plan now defines 5 milestones (M1–M5); M6 closeout content folded into M5 as `m5-knowledge-flow-facade-closeout` slice and the Completion Conditions section.
- [PASS] **C-1 (M4 helper event-kind allowlist)**. Resolved by `closeout.md §Boundary Notes`: "M4 helper event append allowlist is `none`." No event append calls in any helper. Verified via ripgrep across all 6 helper files.
- [PASS] **C-2 (`save_state` closure injection prohibition)**. Multi-layer enforcement: (a) plan now contains explicit prohibition language ("No extracted helper module may import, call, receive, store, or invoke `save_state` by closure or any other callable indirection"); (b) every helper unit-test file contains a `assert "save_state" not in source` AST source-text grep — `tests/unit/orchestration/test_task_lifecycle_module.py:71`, `test_artifact_writer_module.py:116`, `test_subtask_flow_module.py:101`, `test_execution_attempts_module.py:356`, `test_knowledge_flow_module.py:162`, `test_retrieval_flow_module.py:216`. The source-text check covers the closure-injection blind spot that the existing AST guard does not; this is the right fix.
- [PASS] **C-3 (transitive import audit)**. All 6 helpers are clean of `from swallow.orchestration.harness` and `from swallow.orchestration.executor` imports. Verified by ripgrep across all helper files.
- [PASS] **C-4 (`harness.py` scope)**. Plan Non-Goals explicitly states: "Do not move `harness.py` functions into the new helper modules, and do not move new helper logic into `harness.py`; `harness.py` stays a separate future target for this phase." Verified: `harness.py` is unchanged on this branch.
- [PASS] **C-5 (target naming alignment with `CODE_ORGANIZATION.md §5`)**. Final module names align: `task_lifecycle.py`, `retrieval_flow.py`, `artifact_writer.py`, `subtask_flow.py`, `execution_attempts.py`, `knowledge_flow.py` — all six match `CODE_ORGANIZATION §5` target shape exactly. The earlier divergence (`execution_flow.py`, `artifact_index.py`) was eliminated.
- [PASS] **C-6 (`_apply_librarian_side_effects` import direction)**. `closeout.md §Boundary Notes`: "`_apply_librarian_side_effects(...)` remains in `orchestrator.py`. `decide_task_knowledge(...)` remains in `orchestrator.py`. `knowledge_flow.py` does not import or call `apply_proposal`." Verified by ripgrep — `knowledge_flow.py` does not import `apply_proposal` or `swallow.truth_governance.governance`.
- [PASS] **C-7 (`append_event` in helpers)**. No helper calls `append_event`. Verified by ripgrep across all 6 helper files. Closeout records this explicitly.

## 3. Control Plane Authority — `[PASS]` with one `[CONCERN]`

This is the LTO-8 critical boundary, so I verified each helper individually beyond the audit checklist.

- [PASS] **Direct `save_state` reference**: zero hits across all 6 helpers (ripgrep verified).
- [PASS] **Public state-advance entry exposure**: zero hits for `run_task`, `run_task_async`, `create_task`, `advance`, `transition`, `waiting_human`, `enter_waiting_human` as top-level `def` in any helper (ripgrep verified).
- [PASS] **`append_event` calls**: zero hits in helpers; all `append_event` calls remain in `orchestrator.py` (verified by grep — every callsite has `orchestrator.py` as the file).
- [PASS] **`apply_proposal` import / call**: zero hits in helpers.
- [PASS] **`save_state` closure-argument injection**: no helper function declares a parameter typed/named to receive a `save_state`-equivalent callable. The unit tests assert `"save_state" not in source` per file, which catches both direct references and closure-argument names.
- [CONCERN — Closure injection of mutating callables in `debate_loop_core` / `debate_loop_core_async`] `execution_attempts.debate_loop_core` (and its async sibling) accepts 9 callable parameters: `run_attempt`, `clear_feedback_state`, `build_feedback`, `build_last_feedback`, `store_feedback`, `apply_feedback`, `record_round`, `persist_exhausted`, `record_exhausted`. Some of these are pure (`build_feedback`, `build_last_feedback`); some have explicit mutation semantics (`store_feedback`, `apply_feedback`, `persist_exhausted`, `record_round`, `record_exhausted`). At the orchestrator call sites (`orchestrator.py:916, 942, 1025, 1051, 1330, 1361, 1445, 1476`), `record_round` and `record_exhausted` are lambdas wrapping `append_event` against `state`. This means `debate_loop_core` does not directly call `save_state` or `append_event` — but it **decides loop termination, decides when to call `record_exhausted`, and decides whether to capture round telemetry**. The helper holds the **temporal control of when a state-affecting side effect fires**, even though the side-effect implementation lives in the orchestrator's lambda. This is a softer form of the closure-injection concern: not the prohibited "save_state-callable in helper", but the structural twin "loop control owning the moment a state-affecting callable runs". Under `INVARIANTS.md "Control only in Orchestrator / Operator"`, this is borderline. Two reasons it's not a BLOCK: (a) the loop semantics are pure Template Method — `record_*` callables are append-only telemetry, not state advancement; (b) `DEBATE_MAX_ROUNDS = 3` and the termination condition are mechanical, not policy. But future readers of `debate_loop_core` may see the pattern as licensing helpers to hold control of when state-touching callbacks fire. Recommendation for follow-up: either (a) split the loop into a pure orchestrator-side controller plus a helper-side next-state computer, or (b) document explicitly in `execution_attempts.py` that `record_*` callables must be telemetry-only and that the loop's termination decision is mechanical. Filed as CONCERN, not blocking. **Not introduced by this PR** — the loop already lived in `orchestrator.py`; LTO-8 simply moved it. The concern surfaces because moving it makes the pattern more visible.
- [PASS] **Path B / Operator boundary**: `executor.py` and `review_gate.py` are not modified. `subtask_orchestrator.py` retains scheduler ownership; `subtask_flow.py` is glue only.
- [PASS] **Knowledge mutation boundary**: `_apply_librarian_side_effects` and `decide_task_knowledge` remain in `orchestrator.py`. `knowledge_flow.py` is pure plan/payload/report builders that return data structures; orchestrator does the I/O and event emission.

## 4. Invariant Boundary — `[PASS]`

- [PASS] `INVARIANTS.md "Control only in Orchestrator / Operator"`: preserved. All state-advancing operations (`save_state`, `append_event`, `apply_proposal`) remain in `orchestrator.py`.
- [PASS] `INVARIANTS.md "Execution never directly writes Truth"`: preserved. The 6 new helpers are pure builders / planners.
- [PASS] `apply_proposal` as the unique public mutation entry for canonical / route / policy: preserved. No new public mutation entry, no helper-side `apply_proposal` call.
- [PASS] `test_state_transitions_only_via_orchestrator` guard `(tests/test_invariant_guards.py:380)` allowlist remains `{orchestrator.py, sqlite_store.py, store.py}` — the 6 new helpers are **not** in the allowlist, which is the correct security default. The guard would catch any future helper-side `save_state` import or call. This is the **opposite** of the LTO-7 CONCERN-1 drift: here the allowlist correctly does not name the new files, because the new files must not have write authority.
- [PASS] No new cross-layer coupling: helpers use `swallow.orchestration.models`, `swallow.knowledge_retrieval.*`, `swallow.surface_tools.paths` — all permitted directions.

## 5. Test Coverage — `[PASS]`

- [PASS] Full pytest on this branch: `686 passed, 8 deselected, 10 subtests passed in 110.88s`. Re-verified locally during review.
- [PASS] Six new focused unit-test files under `tests/unit/orchestration/`:
  - `test_task_lifecycle_module.py` (84 lines)
  - `test_retrieval_flow_module.py` (229 lines, includes selective-retry regression case)
  - `test_artifact_writer_module.py` (129 lines)
  - `test_subtask_flow_module.py` (114 lines)
  - `test_execution_attempts_module.py` (370 lines, includes debate-loop core parity)
  - `test_knowledge_flow_module.py` (176 lines)
  - All 35 focused tests pass per closeout.
- [PASS] Each helper unit-test file contains a source-text source-grep assertion that the helper module does not contain `save_state`, `append_event`, `apply_proposal`, `swallow.orchestration.harness`, or `swallow.orchestration.executor` as substrings. This pattern is repeated consistently — the strongest part of the test design. `test_retrieval_flow_module.py:191` correctly uses `patch("swallow.orchestration.orchestrator.save_state")` for an integration-style test, confirming `save_state` lives only in orchestrator.
- [PASS] Existing integration tests preserved: `test_run_task_subtasks.py`, `test_subtask_orchestrator.py`, `test_review_gate.py`, `test_cli.py`, `test_web_api.py`, `test_consistency_audit.py` — all pass per closeout's milestone validation logs.
- [PASS] Invariant guards run inside full pytest. `test_state_transitions_only_via_orchestrator`, `test_validator_returns_verdict_only`, `test_route_metadata_writes_only_via_apply_proposal` all pass.
- [PASS] No live HTTP / API-key dependent test introduced.

## 6. Code Hygiene — `[PASS]` with two `[CONCERN]`

- [PASS] `orchestrator.py` reduced from 3853 → 3331 lines. The new helpers add ~824 lines of focused code — about 14% net facade-reduction with helper code added back.
- [PASS] No powerless wrapper modules. Each helper owns one concrete responsibility (per `GOF_PATTERN_ALIGNMENT.md §1`: "policy, command, trace, repository port, adapter, lifecycle step, or value object").
- [PASS] `git diff --check` passes (no whitespace damage).
- [PASS] Module names align with `CODE_ORGANIZATION.md §5` exactly (post-audit revision absorbed).
- [CONCERN — `orchestrator.py` reduction is conservative (14%)] Compared with LTO-7's 1422 → 267 line reduction (~81%), LTO-8's 3853 → 3331 (~14%) is much more conservative. This is **defensible** because: (a) Control Plane authority must stay in orchestrator, so a similar percentage reduction would have required moving authority-bearing code; (b) the audit explicitly authorized this conservative posture by gating M5 on "M1-M4 extraction leaves clear seams"; (c) follow-up LTO-8 slices are explicitly listed in `closeout.md §Deferred Follow-up`. No action required, but **future LTO-8 slices are expected** — this PR is "Step 1" not "Step Final", and the roadmap should reflect that the LTO-8 row should not be marked fully done after merge.
- [CONCERN — Carryover from LTO-7: `test_route_metadata_writes_only_via_apply_proposal` allowlist drift still unresolved] LTO-7 review CONCERN-1 (recorded in `docs/concerns_backlog.md` Active Open / LTO-7 follow-up group) noted that the route-metadata writer guard's allowlist names `provider_router/router.py` only, while the actual writers live in `route_metadata_store.py`. That CONCERN was deferred to "before LTO-10". **This LTO-8 PR does not introduce new drift**, but the existing drift is now one phase closer to LTO-10. Recommend Codex include the allowlist fix as a small commit in the next phase that touches `tests/test_invariant_guards.py`, ideally LTO-9 (Surface / CLI / Meta Optimizer) so it is resolved before LTO-10. Not blocking this PR.

## 7. Documentation — `[PASS]`

- [PASS] `closeout.md` records final module ownership, boundary notes, validation outputs, deferred follow-up. Status `review`.
- [PASS] `pr.md` is consistent with closeout and lists the relevant test commands. The plan-audit absorption summary in `pr.md §Plan Audit` is accurate.
- [PASS] `docs/active_context.md` records the M5 validation passing state.
- [PASS] No `docs/roadmap.md` change made on this branch — correct; the LTO-7 → LTO-8 transition's roadmap update is a post-merge `roadmap-updater` subagent task per `claude/rules.md §一`.

## 8. Phase-Guard (Scope vs Plan) — `[PASS]`

- [PASS] No LTO-9 (Surface / CLI / Meta Optimizer), LTO-10 (Governance apply), or LTO-11 (Planner / DAG / Strategy Router) work performed.
- [PASS] No design semantics change, schema migration, route metadata write boundary change, or default data change.
- [PASS] No new public mutation entry. `_apply_librarian_side_effects` correctly stayed in orchestrator.
- [PASS] No `[SCOPE WARNING]`. The plan honored its own ≤5 milestone discipline (resolved BLOCKER-1).

## 9. CONCERN Summary

| # | Severity | Item | Disposition |
|---|----------|------|-------------|
| 1 | CONCERN | `debate_loop_core` holds loop termination control over orchestrator-injected mutating callables (record_round / record_exhausted) | Backlog — design follow-up; not introduced by this PR but newly visible |
| 2 | CONCERN | `orchestrator.py` reduction is 14% (vs LTO-7's 81%); LTO-8 needs further slices | Tracking note — already reflected in `closeout.md §Deferred Follow-up`, ensure roadmap LTO-8 status reads "Step 1 done" not "fully done" |
| 3 | CONCERN | LTO-7 carryover: `test_route_metadata_writes_only_via_apply_proposal` allowlist drift still unresolved | Backlog — fix in LTO-9 phase before LTO-10 |

All three are recorded for `docs/concerns_backlog.md` per `claude/rules.md §八`. None block this PR.

## 10. PASS Summary

- All 1 BLOCKER + 7 CONCERNs from `plan_audit.md` resolved with verifiable artifacts.
- Control Plane authority preserved: every red line check passes.
- Module names align with `CODE_ORGANIZATION.md §5` exactly.
- Per-helper unit tests use source-text source-grep to enforce the closure-injection prohibition that AST guards cannot reach — strongest part of the test design.
- 686-test full suite green locally.
- Behavior-preserving migration: zero design / schema / artifact / public-API change.
- Helper modules clean of `save_state`, `append_event`, `apply_proposal`, `harness`, `executor` references (ripgrep + per-file unit-test source-grep).
- `INVARIANTS.md` "Control only in Orchestrator / Operator" preserved.
- `apply_proposal` write boundary preserved.
- `test_state_transitions_only_via_orchestrator` guard correctly does not name the new helpers in its allowlist (security default).

## 11. Recommendation

**Merge.**

This PR is a clean facade-first execution of LTO-8 Step 1 and respects the highest-risk invariant boundary in the project (Control Plane authority). The conservative 14% reduction of `orchestrator.py` is the **correct trade-off** — moving more would have required either (a) shifting state-advancement authority into helpers (forbidden) or (b) breaking the Template Method discipline that `debate_loop_core` already partially demonstrates.

The three CONCERNs are non-blocking:
- **CONCERN-1** (debate-loop closure pattern): a design observation that becomes visible by this PR, not introduced by it. Worth filing for design discussion at LTO-11 (Planner / DAG / Strategy Router).
- **CONCERN-2** (reduction depth): expected; LTO-8 is a multi-step long-term goal.
- **CONCERN-3** (LTO-7 carryover): not this PR's job, but inherits forward.

## 12. Post-Merge Actions (for tracking, not blocking)

- `roadmap-updater` subagent should mark LTO-8 row as "Step 1 done" — explicitly **not** as "LTO-8 fully done" — and advance the §三 ticket queue to LTO-9 (Surface / CLI / Meta Optimizer split). The "下一类增量" cell for LTO-8 should record the deferred items from `closeout.md §Deferred Follow-up`: further `orchestrator.py` reduction, eventual `harness.py` decomposition, and the closure-injection design follow-up from CONCERN-1.
- Tag evaluation: still **do not** recommend a new tag at this point. Cluster C (LTO-7/8/9/10) needs all four to land before `v1.6.0` is structurally coherent. We are 2/4 through.
- `docs/concerns_backlog.md` should record CONCERN-1 (debate-loop closure pattern) under LTO-8 follow-up, CONCERN-2 (reduction depth) under LTO-8 follow-up, and confirm CONCERN-3 (LTO-7 allowlist drift) is targeted for LTO-9 not LTO-10.
