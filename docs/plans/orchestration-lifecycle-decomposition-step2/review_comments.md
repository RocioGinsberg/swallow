---
author: claude
phase: orchestration-lifecycle-decomposition-step2
slice: lto8-step2-pr-review
status: review
depends_on:
  - docs/plans/orchestration-lifecycle-decomposition-step2/plan.md
  - docs/plans/orchestration-lifecycle-decomposition-step2/plan_audit.md
  - docs/plans/orchestration-lifecycle-decomposition-step2/closeout.md
  - docs/design/INVARIANTS.md
  - docs/design/ORCHESTRATION.md
  - docs/design/HARNESS.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/TEST_ARCHITECTURE.md
  - tests/test_invariant_guards.py
  - tests/test_grounding.py
  - tests/unit/orchestration/test_harness_facade.py
---

TL;DR:
LTO-8 Step 2 is the cluster C closure phase and it lands cleanly. `harness.py` reduced from 2077 → 1028 lines (-50%); `append_event` and `save_state` are both **zero** in `harness.py`; helper-side telemetry events are constrained by a new AST-walking guard test (`test_harness_helper_modules_only_emit_allowlisted_event_kinds`) that scans the four helper modules for both string-literal and `Event(...)` constructor references; all 5 plan_audit concerns are absorbed in code; the named gate tests (`test_write_task_artifacts_emits_policy_and_artifact_events_in_order`, `test_write_task_artifacts_preserves_waiting_human_checkpoint_state`) exist; full pytest reproduces 734 passed independently. Cluster C is functionally closed pending merge.

Recommendation: **`recommend-merge`** with 2 non-blocking concerns (one is a closeout-recorded deferral, one is a documentation polish for the new invariant). No blockers.

# LTO-8 Step 2 PR Review

## Scope

- track: `Architecture / Engineering`
- phase: `LTO-8 Step 2 — harness decomposition (cluster C closure phase)`
- branch: `feat/orchestration-lifecycle-decomposition-step2`
- base: `main` at `4229680` (post LTO-9 Step 2 merge)
- commits reviewed: `c8a94f3`, `3f0973c`, `eb4366f`, `5bf1c84`, `e65e606`
- mode: behavior-preserving harness decomposition + first-time helper-side `append_event` allowlist invariant
- inputs: `plan.md` (257 lines, audit-absorbed), `plan_audit.md`, `closeout.md`, `pr.md`, full diff `git diff main..HEAD`

## Verdict

`recommend-merge`. No blockers; 2 non-blocking concerns; the new helper-side event allowlist is a substantive new invariant that landed with proper test enforcement.

## Blockers

None.

## Concerns

### [CONCERN-1] `harness.py` is 1028 lines, not "thin facade" — `build_summary` / `build_resume_note` / `build_task_memory` and the `write_task_artifacts` body remain in the facade

**Location:** `src/swallow/orchestration/harness.py`

**What:** The closeout's TL;DR describes the result as a "1028-line import-compatible facade", and §Deferred Work acknowledges that `harness.py` is "still over 1000 lines because task memory, summary, resume-note, and write sequencing remain in the facade layer". For comparison:

- LTO-10 reduced `governance.py` 642 → 45 lines (-93%) and called it a facade
- LTO-9 Step 2 reduced `cli.py` 3653 → 2672 lines (-27%) but did not claim to be a facade
- LTO-8 Step 2 reduced `harness.py` 2077 → 1028 lines (-50%) and is described as a "thin facade"

The description "thin facade" doesn't match the contents. `harness.py` still owns `build_summary` (280 lines), `build_resume_note` (180 lines), `build_task_memory` (160 lines), and the `write_task_artifacts` body (220 lines of sequencing + summary/resume rendering). That's ~840 lines of business logic in the supposed facade.

**Why it matters:**
1. Future readers will look for "thin facade" semantics (re-exports + light wrappers like LTO-10's `governance.py`) and find substantial logic instead.
2. The discrepancy between description and reality is the kind of thing that lets future drift accumulate ("this file is already a facade so we don't need to extract more").
3. The plan §Goals #3 said "shrinking it to a thin compatibility facade" — implementation didn't fully meet that goal.

**Why non-blocking:** This is **explicitly recorded as deferred work** in `closeout.md §Deferred Work`. The deferral is honest and documented. The 50% reduction is meaningful (`append_event` count: 12 → 0; `save_state` count: 0; ~9 policy-block helpers extracted to `artifact_writer.py`). The remaining bulk is genuinely tightly coupled (summary/resume builders consume every result type from the policy pipeline) and a further extraction would be a sensible new phase rather than scope creep here.

**Suggested resolution:**
- Reword the closeout TL;DR and `pr.md` from "thin facade" to "import-compatible facade with the policy/artifact pipeline extracted; report builders remain in the facade pending a future report-rendering phase". This is what actually happened and prevents future-reader confusion.
- If future need triggers, file a deferred slice in roadmap §二 LTO-8 row: "Optional further extraction: `task_report.py` could absorb `build_summary` / `build_resume_note` / `build_task_memory` if a real readability gain emerges; would need careful handling of the many result-type imports they currently consume."
- No code changes required for this PR.

---

### [CONCERN-2] The new helper-side event allowlist invariant deserves a one-line entry in `INVARIANTS.md §9` or a comment block in `test_invariant_guards.py`

**Location:** `tests/test_invariant_guards.py` lines 113-141 (allowlist constants) + line 480 (`test_harness_helper_modules_only_emit_allowlisted_event_kinds`)

**What:** This phase introduced a meaningfully new invariant: "harness-sourced helper modules may emit only allowlisted telemetry events; state-transition events are forbidden". The test is well-written (AST walks both string-literal references and `Event(...)` constructor calls; covers `retrieval_flow.py` / `execution_attempts.py` / `artifact_writer.py` / `task_report.py`; 12 allowed kinds + 2 disallowed kinds + 3 allowed constants). But:

1. `docs/design/INVARIANTS.md §9` lists the project's guard suite (the section the audit referenced as "must not be deleted or weakened"). The new guard isn't there yet.
2. Future plan audits / design audits will need to reference this invariant by name. Right now the only authoritative mention is the test itself + closeout.

**Why it matters:** This is the cluster's first **new invariant** (LTO-7/8 Step 1/9 Step 1+2/10 were all behavior-preserving with existing invariants). Without it being recorded in INVARIANTS.md, a future agent reading the design docs alone would not know this constraint exists, and a future LTO-8 Step 3 (or LTO-13) phase audit might miss it.

**Why non-blocking:** The test enforces the rule; semantically the rule is real and active. INVARIANTS.md is a design document; updating it requires a design-doc commit and possibly a separate review thread. Not a blocker for this PR's behavior-preserving scope.

**Suggested resolution:** As a follow-up (not blocking this merge):
- Add one entry to `docs/design/INVARIANTS.md §9` along the lines of:
  ```
  - Helper-side `append_event` constraint: orchestration helpers (`retrieval_flow.py`, `execution_attempts.py`, `artifact_writer.py`, `task_report.py`) may emit only the 12 allowlisted telemetry / artifact-completion event kinds; state-transition events stay in Orchestrator. Enforced by `test_harness_helper_modules_only_emit_allowlisted_event_kinds`.
  ```
- This can be a one-file commit either before merge (preferred, since the design doc and the implementation should land together) or as an immediate post-merge follow-up commit on main. Either is acceptable.

---

## Validation

I independently re-ran the validation gates on the working tree (matching `e65e606`):

- `.venv/bin/python -m pytest -q` — **734 passed, 8 deselected, 10 subtests passed** (matches Codex's claim; +13 vs LTO-9 Step 2's 721 baseline = expected new test count: 1 invariant guard, 5 harness_facade, 1 task_report_module, ~6 expanded artifact_writer/grounding).

I cross-checked each plan_audit concern against the actual implementation:

| plan_audit concern | Where absorbed | Verified |
|---|---|---|
| C-1 `append_event` allowlist source-text test | `tests/test_invariant_guards.py:480 test_harness_helper_modules_only_emit_allowlisted_event_kinds`. AST walk over 4 helper modules; matches both string-literal references and `Event(...)` constructor. 12 allowed + 2 disallowed + 3 allowed constants. | ✓ |
| C-2 `write_task_artifacts` sub-helper list + named gate tests | M5 acceptance §Implementation Notes lists 9 named helpers (`write_compatibility_policy_artifacts` / `write_execution_fit_policy_artifacts` / `write_knowledge_policy_artifacts` / `write_validation_policy_artifacts` / `write_retry_policy_artifacts` / `write_execution_budget_policy_artifacts` / `write_stop_policy_artifacts` / `write_checkpoint_snapshot_artifacts` / `append_artifacts_written_event`). `test_grounding.py:236 test_write_task_artifacts_emits_policy_and_artifact_events_in_order` enforces sequencing. `test_grounding.py:205 test_write_task_artifacts_preserves_waiting_human_checkpoint_state` exists. | ✓ |
| C-3 `test_cli.py` patch target wrappers preserved | `harness.py` re-exports `build_remote_handoff_contract_record` / `build_resume_note` / `build_retrieval_report` / `build_source_grounding` (lines 33-61). Runtime import test confirmed. | ✓ |
| C-4 `orchestrator.*` patch target wrappers preserved | `orchestrator.py:46-47` re-exports `run_retrieval` / `write_task_artifacts`. `tests/test_debate_loop.py` (5 patches) + `tests/test_librarian_executor.py` still pass. Runtime import test confirmed. | ✓ |
| C-5 named M1 unit test files | `tests/unit/orchestration/test_harness_facade.py` (161 lines) + `tests/unit/orchestration/test_task_report_module.py` (66 lines) added in M1; existing `test_artifact_writer_module.py` expanded by 162 lines in M3. | ✓ |

I also verified the load-bearing invariants:

- **Control invariant**: `harness.py` calls `save_state` **0 times** post-merge; `retrieval_flow.py` / `execution_attempts.py` / `artifact_writer.py` / `task_report.py` all call `save_state` **0 times**. `test_state_transitions_only_via_orchestrator` allowlist still contains exactly `{orchestrator.py, sqlite_store.py, store.py}` — **not broadened**.
- **`append_event` discipline**: `harness.py` emits **0** `append_event` calls (down from 12 pre-LTO-8-Step-2). `artifact_writer.py` emits 9 (one per policy/artifact event), `retrieval_flow.py` emits 1 (`retrieval.completed`), `execution_attempts.py` emits 1 (`executor.completed`/`failed`). All within the allowlist.
- **`apply_proposal` boundary**: 0 `apply_proposal` calls in any of the 4 new helper modules (verified). Plan non-goal preserved.
- **No second control plane**: debate-loop helpers moved with `run_execution` into `execution_attempts.py` but no state authority transferred (no `save_state`, no state-transition events).
- **No FastAPI write route**: `web/api.py` unchanged.
- **No schema / event-log change**: confirmed by Boundary Confirmation in closeout + diff inspection.

I also verified the dependency-injection pattern `harness.py` uses to preserve test patches: `harness.run_retrieval(...)` calls `_run_retrieval(..., retrieve_context_fn=retrieve_context)`; `harness.run_execution(...)` calls `_run_execution(..., run_executor_fn=run_executor, persist_side_effects=persist_executor_side_effects)`. This is what allows tests like `test_executor_protocol.py` (3 patches at `harness.run_execution`) and `test_executor_async.py` to keep working without rewrites — the patches replace the wrapper, which is the correct surface to patch. Clean design.

## Recommendations

1. **Before merge — required:** None. PR is mergeable as-is.

2. **Optional polish (non-blocking, defer or fold into closeout commit):**
   - **(CONCERN-1)** Reword closeout TL;DR / `pr.md` from "thin facade" to "import-compatible facade with policy/artifact pipeline extracted; report builders remain pending a future phase".
   - **(CONCERN-2)** Add a one-entry follow-up to `docs/design/INVARIANTS.md §9` recording the new helper-side event allowlist invariant with the guard test name.

3. **Tag decision (this is the v1.6.0 trigger):** With LTO-8 Step 2 about to merge, **cluster C is fully closed**: LTO-7 / LTO-8 (Step 1+Step 2) / LTO-9 (Step 1+Step 2) / LTO-10 all done. This is the moment for `v1.6.0`. The roadmap §四 already records this trigger; the cluster C closure narrative is exactly what the version represents.

4. **Roadmap update after merge:** When `roadmap-updater` runs post-merge, it should:
   - Mark §二 簇 C LTO-8 row "已完成" (Step 1 + Step 2). Cluster C is now fully closed.
   - Update §一 baseline to remove "只剩 LTO-8 Step 2" and replace with "簇 C 已完全终结".
   - Promote §三 current ticket to **LTO-13 — FastAPI Local Web UI Write Surface** (cluster C closure trigger reached).
   - Mark §五 LTO-8 顺位 "Step 1 + Step 2 已完成".
   - Update v1.6.0 tag decision to "cut now (cluster C closure)".

5. **Post-merge follow-ups** (non-blocking, can be a single doc-only commit):
   - INVARIANTS.md §9 update for CONCERN-2.
   - Closeout TL;DR / `pr.md` description tweak for CONCERN-1.

## Acknowledgements

Five-milestone discipline held throughout: M1 characterization tests landed before any production move; each subsequent milestone preserved its own family's facade compatibility; all 5 plan_audit concerns absorbed in code (not just text). The new helper-side `append_event` allowlist is the **first new invariant** introduced in cluster C, and it landed with proper AST-walking guard test, explicit allowlist constants, and explicit prohibition list — exactly the kind of design discipline the audit asked for. The 50% `harness.py` reduction is genuinely meaningful: the file went from "load-bearing pipeline owner with 12 `append_event` callsites" to "import-compatible orchestration facade with 0 `append_event` callsites". With this merge, the four-subtrack cluster C decomposition program is complete; project moves into LTO-13 / Wiki Compiler territory.
