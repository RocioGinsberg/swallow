---
author: claude
phase: orchestration-lifecycle-decomposition-step2
slice: lto8-step2-plan-audit
status: review
depends_on:
  - docs/plans/orchestration-lifecycle-decomposition-step2/plan.md
  - docs/plans/orchestration-lifecycle-decomposition-step2/context_brief.md
  - docs/design/INVARIANTS.md
  - docs/design/ORCHESTRATION.md
  - docs/design/HARNESS.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/TEST_ARCHITECTURE.md
---

TL;DR: has-concerns — 5 milestones audited, 0 blockers, 5 concerns found.
The plan is structurally sound and the allowlist design is correctly specified.
The primary concerns are: (1) the allowlist has no enforcement mechanism defined (source-text test missing),
(2) M5 acceptance criteria are hand-wavy for the hardest slice, (3) `test_cli.py` imports four builder
symbols that are not in the patch-target preservation list, and (4) two integration test files patching
at `orchestrator.*` scope are not named in the plan despite being at risk.

---

## Audit Verdict

Overall: has-concerns

---

## Blockers

None.

---

## Concerns

### CONCERN-1: `append_event` allowlist has no enforcement mechanism

Location: `plan.md §M4 Acceptance` — "Any helper that appends events only emits from the explicit allowlist above."

Issue: The allowlist itself is correctly specified (12 event kinds listed, disallowed list includes
`state_transitioned` and `entered_waiting_human`). However, the plan does not specify the test
mechanism that enforces it. The M4 acceptance criterion is a prose statement, not a test name.
In contrast, the analogous guard for `save_state` is backed by a source-text AST test
(`test_state_transitions_only_via_orchestrator` scans every non-allowlisted file). There is no
analogous scan for `append_event` emitting disallowed event kinds in helper modules.

The existing `test_artifact_writer_module.py` pattern (line 117: `assert "append_event" not in source`)
is the Step 1 pattern for modules that should have zero `append_event` calls. For Step 2 helper modules
that ARE allowed to call `append_event`, that same blanket assertion cannot be used. The plan creates a
new class of module — "allowed to call `append_event` but only for allowlisted kinds" — without specifying
the test that enforces the "only allowlisted kinds" half.

Why it matters: A future Codex could add a new event kind (e.g. `state.advanced`) to a helper module
without any guard firing. The allowlist would then be commentary rather than enforced invariant.

Suggested resolution: M4 should require a named source-text test, e.g.
`test_harness_helper_modules_only_emit_allowlisted_event_kinds`, that parses `execution_attempts.py`,
`retrieval_flow.py`, `artifact_writer.py`, and `task_report.py` for any string literal passed as
`event_type` and asserts each is in the explicit allowlist. The disallowed strings (`state_transitioned`,
`entered_waiting_human`) should appear as explicit patterns in the test, analogous to the `save_state`
scan in `test_state_transitions_only_via_orchestrator`.

---

### CONCERN-2: M5 acceptance criteria do not name the helpers to be extracted from `write_task_artifacts`

Location: `plan.md §M5 Acceptance` — "Decompose `write_task_artifacts` so the harness wrapper only
sequences helper calls and does not own the report/record payload construction."

Issue: The plan reads the source correctly: `write_task_artifacts` is a ~430-line sequential pipeline
with 9 policy evaluation blocks, each calling `append_event`, plus ~80 lines of setup and ~40 lines
of finalization. M5's scope says to "decompose" it, but neither the scope nor the acceptance criteria
name which sub-units become which helper functions, nor which new module they land in. The acceptance
criterion "harness.py is reduced to a thin compatibility facade with no heavy builder ownership" does
not indicate how much of the pipeline structure becomes a helper call vs stays inline sequencing.

Additionally, the plan defers `write_task_artifacts` to M5 because M2/M3 extract the record/report
builders first — this is correct. But after M2/M3, `write_task_artifacts` still holds the 9 sequential
`evaluate_*` + `save_*` + `append_event` blocks (lines 312-603). M5 needs to decide: does each policy
evaluation block become a helper in its respective module, or does a new coordinator live in `artifact_writer.py`
or `execution_attempts.py`? The plan does not answer this.

The test that validates the sequential `append_event` order (so reordering is caught) is also absent
from M5 acceptance. The `waiting_human` check at `harness.py` lines 480-493, tested by
`tests/test_grounding.py:205`, is not named as a binding gate in M5 acceptance even though it is the
hardest-to-preserve rollback semantic.

Why it matters: Codex will need to make a substantial design decision mid-implementation without a plan
anchor. If the extraction changes the sequential evaluation order or misplaces the `waiting_human` branch,
tests will catch it, but only if the right characterization tests exist — and M1 acceptance does not
specify a test for `append_event` ordering inside `write_task_artifacts`.

Suggested resolution: M5 acceptance should add three items:
(a) Name at minimum the 7 policy evaluation blocks and their target modules (e.g., "each `evaluate_*`
call and its `append_event` pair moves to the module owning that policy type").
(b) Require a pre-extraction characterization test in M1 or M5 that asserts the sequential
`append_event` event kind order inside `write_task_artifacts` (so any permutation is caught).
(c) Name `tests/test_grounding.py:205` as an explicit gate: "Must remain green after M5 decomposition
without modification to the test."

---

### CONCERN-3: `test_cli.py` imports four builder symbols not in the patch-target preservation list

Location: `plan.md §Goals #5` and `§Scope Decisions #6` vs `tests/test_cli.py` lines 35-40.

Issue: The plan names `run_execution`, `run_retrieval`, `run_retrieval_async`, `write_task_artifacts`,
and `write_task_artifacts_async` as the symbols to preserve in `harness.py`. However, `tests/test_cli.py`
directly imports four additional symbols from `swallow.orchestration.harness`:
`build_remote_handoff_contract_record`, `build_resume_note`, `build_retrieval_report`,
`build_source_grounding` (lines 35-40).

Per the plan's module mapping, all four of these will move: `build_remote_handoff_contract_record`
to `artifact_writer.py`, `build_retrieval_report` and `build_source_grounding` to `task_report.py`,
and `build_resume_note` to `task_report.py`. If `harness.py` does not re-export these four symbols as
compatibility wrappers, `test_cli.py` breaks on import. The plan states "keep wrappers stable" but
only names the execution entry points explicitly; it does not name these builder symbols as requiring
re-export preservation.

Additionally, `orchestrator.py` imports `build_remote_handoff_contract_record` and
`build_remote_handoff_contract_report` directly from `harness.py` (line 43). If these move without
re-export wrappers in `harness.py`, `orchestrator.py` needs an import update — which is a
behavior-neutral change but should be named as an explicit step rather than an implicit consequence.

Why it matters: Codex could complete M3 (moving record builders to `artifact_writer.py`) without
realizing that `test_cli.py` imports them directly from `harness`. The tests would break with an
`ImportError` rather than a semantic failure.

Suggested resolution: M1 acceptance should assert that `harness.py` re-exports all symbols currently
imported by external callers, and §Scope Decisions #6 should enumerate all six symbols requiring
compatibility re-export: `run_execution`, `run_retrieval`, `run_retrieval_async`, `write_task_artifacts`,
`write_task_artifacts_async`, `build_remote_handoff_contract_record`, `build_resume_note`,
`build_retrieval_report`, `build_source_grounding`.

---

### CONCERN-4: `test_debate_loop.py` and `test_librarian_executor.py` patch at `orchestrator.*` scope but are not named in plan.md

Location: `plan.md §Scope Decisions #6` names `test_executor_protocol.py`, `test_executor_async.py`,
`test_grounding.py`, and `test_cost_estimation.py` as the stability gate tests.

Issue: `tests/test_debate_loop.py` (5 tests) and `tests/test_librarian_executor.py` (1+ test) both
patch `swallow.orchestration.orchestrator.run_retrieval` and
`swallow.orchestration.orchestrator.write_task_artifacts`. These patch at the `orchestrator` import
level, not at `harness` directly. Per `context_brief.md §5`, patches at this level are unaffected
by harness function moves as long as the functions remain re-exported by `orchestrator.py`. However,
the plan does not verify this re-export chain is preserved.

`orchestrator.py` imports `run_retrieval` and `write_task_artifacts` from `harness.py` at line 43.
After M2 and M5 moves these into `retrieval_flow.py` and the harness facade, `orchestrator.py` would
need to keep those imports live for the `orchestrator.*` patch paths to work. The plan's "keep harness.py
wrappers stable" rule addresses the `harness.*` paths but does not explicitly address whether
`orchestrator.py`'s re-import of `run_retrieval` / `write_task_artifacts` stays in place.

Why it matters: If Codex updates `orchestrator.py` to import directly from `retrieval_flow.py` instead
of from `harness.py`, the `swallow.orchestration.orchestrator.run_retrieval` patch path still works.
But if the symbol is removed from `orchestrator.py`'s namespace (e.g., inlined), those 6+ tests break.

Suggested resolution: M2 and M5 acceptance should include an explicit line: "The `run_retrieval` and
`write_task_artifacts` names must remain importable from `swallow.orchestration.orchestrator` without
import errors." And `test_debate_loop.py` / `test_librarian_executor.py` should be named in §Scope
Decisions #6 alongside the other integration tests.

---

### CONCERN-5: M1 does not name the new test files it will create in `tests/unit/orchestration/`

Location: `plan.md §M1 Acceptance` — "Add or expand unit tests for the new or expanded helper modules
so boundary assertions fail loudly if they ever pick up control-plane authority."

Issue: M1 acceptance describes what the tests will cover but does not name the files. The Step 1
precedent in `tests/unit/orchestration/` is six files named `test_<module>_module.py`. For Step 2,
M1 is the baseline characterization milestone and would logically add `test_harness_facade.py` or
`test_task_report_module.py`. But the plan says "Add or expand unit tests" without specifying which
files.

Per the LTO-9 Step 2 precedent (CONCERN-2 in that audit: "preferably under tests/unit/orchestration/"
is too weak), the plan should commit to specific file names before implementation begins. Without named
files, there is no way to verify at M1 gate that the baseline characterization was done.

Why it matters: If M1 creates tests in `tests/test_harness.py` instead of `tests/unit/orchestration/`,
or spreads assertions across multiple existing test files, the M2-M5 moves lack a coherent baseline anchor.

Suggested resolution: M1 acceptance should name at minimum: `tests/unit/orchestration/test_harness_facade.py`
(facade import compatibility, `save_state`-absence guard for new helpers) and note that builder-specific
files (e.g., `test_task_report_module.py`) will be created alongside the relevant extraction milestone
(M2, M3) following the `test_<module>_module.py` naming convention.

---

## Validation

Cross-checks performed:

1. `append_event` callsite count: grep confirms 11 callsites at lines 87, 146, 320, 341, 362, 378,
   406, 437, 463, 531, 599 (matching context_brief §2). The brief said "11 call sites" with a note
   that it counted 12 in the TL;DR — the actual code shows 11. The plan's allowlist lists 12 event
   kinds but that is the correct number of distinct kind strings (11 callsites, but line 150 emits
   either `executor.completed` OR `executor.failed` conditionally, so both must be in the allowlist).
   All 11 actual event kinds from the code are present in the plan's allowlist. No event kind emitted
   in `harness.py` is missing from the allowlist.

2. `wait_human` check at `harness.py` lines 480-493 confirmed. `tests/test_grounding.py:205`
   (`test_write_task_artifacts_preserves_waiting_human_checkpoint_state`) confirmed as the binding
   coverage for that branch.

3. `tests/unit/orchestration/` exists with 6 test files from Step 1. The directory is ready for new
   files; no bootstrap needed.

4. `test_state_transitions_only_via_orchestrator` allowlist (lines 419-423 of `test_invariant_guards.py`)
   contains exactly 3 files. No harness helper module is in it. The plan's "without broadening the
   Control Plane allowlist" criterion is correct — no new helper module needs to be added there since
   none of them call `save_state`.

5. `apply_proposal` boundary: confirmed `harness.py` has no `apply_proposal` calls and no imports
   from `truth_governance.governance`. Step 2 does not introduce them. Non-goal is binding.

6. Debate-loop non-goal: M4 moves debate-loop helpers into `execution_attempts.py` as a helper move,
   not a semantic redesign. The non-goal ("do not redesign debate-loop closure semantics as a new
   policy system") is not violated — M4 documents callback semantics as "telemetry-only" but does
   not change them.

7. `build_route_report`, `build_topology_report`, `build_execution_site_report`, `build_dispatch_report`,
   `build_handoff_report` also exist in `harness.py` (confirmed by grep). These are candidates for
   `artifact_writer.py` or `task_report.py` in M3 but are not imported by any external caller
   (no import-from-harness reference found in tests or src beyond harness itself). They do not
   require re-export wrappers.

8. `harness.py` end-state size: plan does not give a line target. The "thin facade" criterion is soft.
   Given that the clearly extractable helpers account for ~800 lines and the execution entry points
   for ~165 lines, a post-M5 harness of ~200-350 lines is plausible. Not flagging as a concern because
   the completion conditions (condition #2) define shape clearly enough and line count is not a
   behavioral gate.

9. `subtask_flow.py` / `knowledge_flow.py` no-touch: module table says "only touched if needed for
   compatibility cleanup." No milestone acceptance criterion adds them to scope. Consistent with the
   plan's non-goals.

---

## Confirmed Ready

- M1 scope and acceptance: ready, subject to CONCERN-5 (no named test files). Codex can start
  characterization; the file naming concern is a clarification before first commit, not a blocker.
- M2 scope and acceptance: ready. retrieval + grounding split is unambiguous. Wrapper preservation
  rule is explicit. Import from `orchestrator.py` path not explicitly named but patch paths are stable
  as long as `orchestrator.py` keeps its current import line.
- M3 scope and acceptance: ready, subject to CONCERN-3 (need explicit re-export list for
  `test_cli.py` builder symbols).
- M4 scope and acceptance: has CONCERN-1 (allowlist enforcement test). The allowlist content itself
  is correct; only the enforcement mechanism is missing.
- M5 scope and acceptance: has CONCERN-2 (hand-wavy decomposition target). The milestone is
  implementable but Codex will need to make design decisions that should be pre-decided.

---

## Questions for Codex / Human

1. **M4 allowlist enforcement**: Should the source-text test for helper-module `append_event` emission
   be added to `tests/unit/orchestration/` (e.g., `test_harness_helpers_event_allowlist.py`) or to
   `tests/test_invariant_guards.py` as a new guard? Given that it enforces an invariant boundary
   introduced in this phase, `test_invariant_guards.py` is the more appropriate home.

2. **M5 extraction target**: Before M5 begins, should Codex produce a brief decomposition note
   (inline in the commit message or as a slash-comment in `write_task_artifacts`) naming which 7
   policy evaluation blocks go to which helper? This can be decided at M4 closeout rather than
   at Plan Gate, but the plan should acknowledge the decision point.

3. **`test_cli.py` re-exports**: The plan should confirm that `harness.py` will re-export
   `build_remote_handoff_contract_record`, `build_resume_note`, `build_retrieval_report`, and
   `build_source_grounding` as compatibility names after M2/M3. If Codex prefers to update
   `test_cli.py`'s import instead, that should be an explicit plan decision with a noted test
   stability impact.

4. **`test_debate_loop.py` / `test_librarian_executor.py` coverage**: These tests are not in the
   M5 final validation gate command list. Should they be added to the final `.venv/bin/python -m pytest -q`
   run? (They are covered by the full default pytest, but naming them in M2/M5 acceptance would
   prevent a false sense of safety if someone runs only the named subset.)
