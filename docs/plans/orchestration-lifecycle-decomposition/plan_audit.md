---
author: claude
phase: orchestration-lifecycle-decomposition
slice: plan-audit
status: draft
depends_on:
  - docs/plans/orchestration-lifecycle-decomposition/plan.md
  - docs/design/INVARIANTS.md
  - docs/design/ORCHESTRATION.md
  - docs/design/HARNESS.md
  - docs/design/STATE_AND_TRUTH.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/GOF_PATTERN_ALIGNMENT.md
  - docs/engineering/TEST_ARCHITECTURE.md
  - docs/roadmap.md
  - docs/plans/architecture-recomposition/plan.md
  - docs/plans/provider-router-split/review_comments.md
---

TL;DR:
The plan maintains the Control Plane authority boundary clearly: `run_task` / `run_task_async` remain in `orchestrator.py` and helpers are explicitly barred from calling `save_state` independently.
One BLOCKER: the plan names 6 milestones (M1-M6), exceeding the claude/rules.md §五 limit of 5 slices per phase — must be resolved before the Plan Gate.
Three CONCERNs: target module shape diverges from `CODE_ORGANIZATION.md §5`, guard allowlist drift is a live risk for `test_state_transitions_only_via_orchestrator`, and `harness.py` extraction scope is under-specified in the non-goals.

# Plan Audit: Orchestration Lifecycle Decomposition (LTO-8)

---

## 1. Control Plane Authority (LTO-8 critical)

### 1.1 Helper independence from state advancement

[PASS] The plan explicitly states at TL;DR level and in every milestone acceptance section that extracted helpers must not independently advance task state. "Do not let helper modules call `save_state(...)` or mutate task status as autonomous decisions unless the call remains clearly orchestrator-delegated and reviewed in plan audit" (Non-Goals). This wording is precise.

[PASS] The plan identifies `_set_phase(...)` and `save_state(...)` calls as explicitly remaining in `orchestrator.py` through M1 unless plan audit grants approval. This is the correct conservative default. The audit does not grant any delegated `save_state` authority beyond what the plan already holds back.

[PASS] `run_task` / `run_task_async` / `create_task` are all named as non-movable in Non-Goals. Caller direction is one-way: Orchestrator calls helpers, helpers do not call back into Orchestrator to advance state.

[PASS] M4 acceptance includes an explicit conditional: "If a helper writes events, the plan audit must have approved its ownership and tests must prove it does not decide advancement independently." This is the right gate structure for the highest-risk milestone.

[CONCERN] M4 allows `execution_attempts.py` helpers to write `append_event` calls if auditor-approved, but the plan does not pre-specify which event kinds from `execution_attempts.py` would be auditor-approved. This creates an implicit scope that must be resolved during M4 implementation. Codex should document, at M4 commit time, a specific list of event `kind` values that the extracted helpers may append (e.g. `execution_attempt_initialized`, `attempt_telemetry`) versus those that must remain Orchestrator-owned (e.g. `state_transitioned`, `entered_waiting_human`). This is implementable but requires an explicit assumption at that milestone.

[PASS] Path B boundary is not touched. The plan does not move anything related to `executor.py` Path B plumbing into new modules that could confuse the `test_path_b_does_not_call_provider_router` guard. `executor.py` is listed in the current code context table but not in the target module shape for extraction.

### 1.2 Guard coverage for Control authority

[PASS] The validation plan names `tests/test_invariant_guards.py -q` as a gate at every milestone. This is the correct approach.

[CONCERN] The existing `test_state_transitions_only_via_orchestrator` guard has an allowlist of exactly three files: `orchestrator.py`, `sqlite_store.py`, `store.py`. When any new helper module (e.g. `task_lifecycle.py`, `retrieval_flow.py`) is extracted, the guard will pass automatically only as long as `save_state` is not imported or called in those new files. However, the plan does not explicitly commit to a policy: if an extracted module legitimately receives a `save_state`-calling closure from Orchestrator (e.g. via lambda injection, as already seen for `append_event` at lines 1199 / 1300 in `orchestrator.py`), it may call `save_state` indirectly through the closure without triggering the AST guard. The guard checks import and direct call nodes, not closure calls. Codex must not route `save_state` calls into extracted helpers via closure injection — this is technically guard-invisible but architecturally equivalent to giving helpers state-write authority. The plan should explicitly prohibit `save_state` closure injection into helper modules.

---

## 2. Scope Discipline

### 2.1 LTO boundary compliance

[PASS] No Planner / DAG / Strategy Router implementation is attempted. Non-Goals explicitly exclude these.

[PASS] No route selection, Provider Router behavior, or executor registry behavior is changed.

[PASS] `apply_proposal` private handlers are explicitly deferred to LTO-10.

[PASS] CLI / FastAPI / Meta Optimizer split is explicitly deferred to LTO-9.

[PASS] No task state schema change or SQLite migration is in scope.

### 2.2 harness.py scope gap

[CONCERN] `harness.py` is listed in the current code context table (2077 lines) but is NOT listed in the target module shape for this phase. The target module shape names `task_lifecycle.py`, `execution_attempts.py`, `retrieval_flow.py`, `execution_flow.py`, `knowledge_flow.py`, `artifact_index.py` — all of which are sourced from `orchestrator.py` functions. The plan says harness "does not decide task advancement" (Design and Engineering Anchors), but nowhere states whether any `harness.py` functions will be migrated to or referenced by new extracted helpers. Given that `harness.py` currently owns "retrieval execution, artifact writing, summary/resume/report builders, policy artifact generation" and the new modules will own adjacent concepts (`retrieval_flow.py`, `artifact_index.py`), there is a risk of unintended coupling in M2 and M3 if an extractor decides to consolidate `harness.py` retrieval execution into `retrieval_flow.py`. The plan should explicitly state whether `harness.py` is in scope for migration in this phase or is left as a separate future target.

### 2.3 Target shape diverges from CODE_ORGANIZATION.md §5

[CONCERN] `CODE_ORGANIZATION.md §5` names the orchestration target direction as:
`task_lifecycle.py`, `execution_attempts.py`, `subtask_flow.py`, `knowledge_flow.py`, `retrieval_flow.py`, `artifact_writer.py`.

The plan's target module shape table names:
`task_lifecycle.py`, `execution_attempts.py`, `retrieval_flow.py`, `execution_flow.py`, `knowledge_flow.py`, `artifact_index.py`.

Two discrepancies exist:
1. `subtask_flow.py` (from `CODE_ORGANIZATION.md`) is absent from the plan. Instead `execution_flow.py` is introduced. The plan lists `execution_flow.py` as owning "previous executor artifact loading, parent executor artifact write helpers, fallback artifact prefix helpers, budget guard result builders" — this is a subset of what would normally belong in an `execution_attempts.py` or `artifact_writer.py` under the CODE_ORGANIZATION naming. Not a blocker since CODE_ORGANIZATION §5 explicitly says "the exact package names may evolve during implementation", but the absence of `subtask_flow.py` combined with the introduction of `execution_flow.py` should be acknowledged.
2. `artifact_writer.py` (from `CODE_ORGANIZATION.md`) is replaced by `artifact_index.py` in the plan. The plan's `artifact_index.py` scope ("artifact path map construction for task run outputs") is narrower than `artifact_writer.py` would imply. This is implementable but means this phase only covers a subset of what CODE_ORGANIZATION calls `artifact_writer.py`. Codex should either rename `artifact_index.py` to match or add a note that `artifact_writer.py` is deferred.

These are CONCERNs and not BLOCKERs because CODE_ORGANIZATION explicitly calls itself a convergence standard rather than a frozen directory tree. However, if the module names diverge from the design document, future phases will need to reconcile, and it is cleaner to resolve the naming before the branch is opened.

---

## 3. Milestone / Slice Executability

### 3.1 Slice count

[BLOCKER] The plan defines 6 milestones (M1 through M6). `docs/.agents/claude/rules.md §五` sets a limit of ≤5 slices per phase. M6 is "Facade cleanup, closeout, PR body, full validation" — this is standard housekeeping that does not require a separate numbered milestone and can be folded into M5 or described as the PR gate condition rather than a named milestone. The plan must reduce milestone count to 5 before the Plan Gate can be approved.

Recommended resolution: collapse M6 into the completion conditions section (which already exists and covers the same acceptance criteria). This is a documentation fix only; it does not change the implementation scope.

### 3.2 Per-milestone testability

[PASS] M1 acceptance: "No behavior change in `run_task`", "No import churn outside orchestration tests and `orchestrator.py`", "`tests/unit/orchestration -q` passes", "`tests/test_invariant_guards.py -q` passes" — all concrete and testable.

[PASS] M2 acceptance: specific retrieval source policy defaults are enumerated. The regression commands are named.

[PASS] M3 acceptance: "No `.swl/tasks/<task_id>/artifacts/*` filename changes" is a precise, verifiable criterion.

[PASS] M4 acceptance: "Debate loop retry behavior remains unchanged", "Budget-exhausted behavior still transitions to `waiting_human`" — verifiable against existing tests.

[PASS] M5 acceptance: "Governance and canonical-write guard tests pass" is concrete.

[PASS] Each milestone maps to a suggested commit message in the Branch and Commit Strategy section. This matches LTO-7's successful pattern.

### 3.3 Human commit gate

[PASS] "High-risk slices M4 and M5 should stay separate commits" is stated explicitly. Plan Gate requirements include Human branch creation. The pattern matches LTO-7.

### 3.4 M1 characterization test scope

[CONCERN] M1 says "Add characterization tests around lifecycle descriptors that do not require running a full task." However, `orchestrator.py` has ~49 `append_event` / `save_state` call sites and many tightly interlocked private functions. Writing characterization tests at the helper extraction level, before any extraction, requires identifying stable interfaces in a 3853-line file with dense internal coupling. The plan does not name which specific functions or descriptors will be characterized in M1. This is implementable (Codex can choose), but the risk of characterization tests being overly broad or tautological is high for M1. At minimum, the M1 guard assertion — "extracted lifecycle helper module does not expose `run_task`, `run_task_async`, `create_task`, or a public state-advance entry" — is concrete and should be the primary M1 test anchor. The plan should note that characterization scope will be determined by Codex at M1 implementation and limited to the functions being moved in M1.

---

## 4. Invariant Boundary

### 4.1 INVARIANTS §0 rules

[PASS] "Control only in Orchestrator / Operator" is preserved by design: helpers receive inputs, return outputs, and do not decide state transitions. The plan's repeated explicit prohibition on helper-owned `save_state` calls enforces this.

[PASS] "Execution never directly writes Truth" is preserved: none of the extracted modules are executors or validators. They are orchestration-internal helpers.

[PASS] "Path A / B / C boundaries remain explicit" — the plan does not touch path selection or provider routing. No new path routing logic is introduced.

[PASS] "`apply_proposal` remains the only canonical / route / policy mutation entry" — the plan explicitly lists this as a Design and Engineering Anchor and M5 acceptance requires governance guard tests to pass.

### 4.2 Truth write paths

[PASS] task state / event log persistence remains behind `save_state` / `append_event` imported from `truth_governance.store`, which only `orchestrator.py` is allowed to import per the `test_state_transitions_only_via_orchestrator` guard.

[PASS] `_apply_librarian_side_effects` (which calls `apply_proposal`) stays in `orchestrator.py` for M5 "only if the M1-M4 extraction leaves clear seams". The plan correctly treats this as the highest-risk extraction and gates it on prior milestone stability.

[PASS] Knowledge writes (canonical) continue through `apply_proposal` path. M5 explicitly prohibits widening Specialist or Meta-Optimizer authority.

### 4.3 Cross-layer import risks

[CONCERN] LTO-7's BLOCKER was that `DEFAULT_EXECUTOR` appeared to live in `orchestration/executor.py` but was actually exported from `knowledge_retrieval/dialect_data.py`. LTO-8 has an analogous latent risk: `orchestrator.py` imports from `harness.py` (line 43), `executor.py` (line 40), `subtask_orchestrator.py` (line 146), and many knowledge retrieval modules. When a new helper module (e.g. `retrieval_flow.py`) is created and the `_retrieval_policy_family` / `_select_source_types` functions are moved there, if those functions transitively import from `orchestration.harness` or `orchestration.executor`, the new module will create a circular or unexpected import chain that the plan has not enumerated. The plan does not conduct a pre-audit of transitive imports for any of the six target modules. Codex should verify import dependencies for each candidate function before moving it, particularly for M2 (retrieval_flow) and M4 (execution_attempts / budget guard).

Specifically: `build_task_retrieval_request` (M2 candidate) currently calls `_retrieval_policy_family` and `normalize_retrieval_source_types` (from `task_semantics.py`). If `retrieval_flow.py` imports from `orchestration.harness` or `orchestration.executor`, the `test_path_b_does_not_call_provider_router` guard might be unaffected (it only scans `executor.py`), but new unintended coupling paths would form.

### 4.4 Path B / Operator guard

[PASS] Validator / Review Gate separation is preserved. `review_gate.py` is not in scope for migration. `subtask_orchestrator.py` remains as owner.

---

## 5. Test Coverage

### 5.1 tests/unit/orchestration/ creation

[PASS] M1 explicitly creates `tests/unit/orchestration/` if absent. This aligns with `TEST_ARCHITECTURE.md §1` target shape.

### 5.2 Integration test preservation

[PASS] The validation plan names all major existing integration test files:
- `tests/test_run_task_subtasks.py`
- `tests/test_subtask_orchestrator.py`
- `tests/test_review_gate.py`
- `tests/test_cli.py`
- `tests/test_web_api.py`
- `tests/test_consistency_audit.py`

All of these are specified as must-pass at appropriate milestones.

[PASS] The plan requires `tests/test_invariant_guards.py` at every milestone gate.

### 5.3 Guard test preservation

[PASS] No guard tests are proposed for removal or weakening.

[CONCERN] As noted in §1.2, the `test_state_transitions_only_via_orchestrator` guard allowlist currently names only `orchestrator.py` as the allowed orchestration source. After M1-M5, new helper modules in `src/swallow/orchestration/` will exist. If any of them legitimately needs to call `append_event` (not `save_state`) for telemetry, the guard does not cover `append_event` — only `save_state`. This is technically correct per the Truth write matrix (append_event is `W*` for General Executor and others, not restricted to Orchestrator), but the plan should acknowledge that extracted orchestration helpers which call `append_event` are permitted by the existing guard semantics. This means the plan's requirement that "helpers must not advance task state" is enforced by design intent but not by the existing `test_state_transitions_only_via_orchestrator` guard for `append_event` calls. If Codex needs to prevent `append_event` calls in helpers, a new focused guard or assertion in the helper module's own test would be needed.

### 5.4 Eval coverage

[PASS] The plan correctly excludes eval. "Not required for this phase. This is behavior-preserving orchestration decomposition, not quality-gradient retrieval / LLM output work." This matches the shared rules §十 eval criteria.

---

## 6. LTO-7 Lessons Applied

### 6.1 Guard allowlist drift

[CONCERN] LTO-7 CONCERN-1 (still open in `docs/concerns_backlog.md`) warned that `test_route_metadata_writes_only_via_apply_proposal` allowlist does not yet name `route_metadata_store.py`. The LTO-8 plan does not address this pre-existing open concern before starting implementation. While it is not LTO-8's job to fix LTO-7's concerns, Codex should confirm that the existing guard suite baseline is clean before branching, since any new guard drift introduced by LTO-8 module moves may compound the existing drift from LTO-7 CONCERN-1 and make the final LTO-10 tightening harder.

Specifically for LTO-8: the `test_state_transitions_only_via_orchestrator` guard's allowlist only names `orchestrator.py`. If extracted helper modules are moved to `src/swallow/orchestration/task_lifecycle.py`, `retrieval_flow.py`, etc., the guard will correctly reject any attempt to import or call `save_state` in those new files. This is good. But if the plan later in M4/M5 decides that a helper should receive a `save_state`-wrapping function reference, the guard's AST scan of `ImportFrom` / `Call` nodes may not catch that pattern. This is the same guard topology issue LTO-7 hit — the guard is AST-name based, not call-graph based. Recommendation: add a focused comment in M4/M5 acceptance saying "no `save_state` reference of any kind may appear in extracted modules — neither import, call, closure argument, nor dataclass field".

### 6.2 Cross-layer import chain (LTO-7 BLOCKER analog)

[PASS] LTO-7's BLOCKER was `DEFAULT_EXECUTOR` defined in `knowledge_retrieval.dialect_data` but imported via `orchestration.executor`. The LTO-8 plan avoids this by explicitly keeping `executor.py` imports within `orchestrator.py` and not extracting `executor.py`-touching logic into helpers. The plan correctly keeps executor invocation, review gate decision consumption, and status transition sequencing visibly orchestrator-owned (M4 acceptance).

[CONCERN] There is one latent analog: `_apply_librarian_side_effects` (M5 candidate) calls `apply_proposal` imported from `swallow.truth_governance.governance`. If this function is moved to `knowledge_flow.py`, the new module will become the only orchestration module that directly imports from `truth_governance.governance`. This creates an asymmetry where `orchestrator.py` delegates to `knowledge_flow.py` which independently holds a reference to the governance boundary. The plan acknowledges this risk implicitly by making M5 conditional ("only if the M1-M4 extraction leaves clear seams") but does not state what "clear seams" means for the `apply_proposal` import path. Codex should clarify at M5 whether `knowledge_flow.py` will import `apply_proposal` directly or receive it as a callable argument from Orchestrator — the latter is safer for invariant enforcement.

---

## 7. Phase-Guard (Scope vs Program Plan)

[PASS] The program plan (`docs/plans/architecture-recomposition/plan.md`) explicitly authorizes LTO-8 for "Orchestration lifecycle" with the rule "helpers cannot own Control Plane advancement". The LTO-8 plan is within this authorization.

[PASS] Non-Goal "Do not implement Planner / DAG / Strategy Router as part of AD0" is matched by LTO-8's Non-Goal "Do not introduce Planner / DAG / Strategy Router as first-class runtime components."

[PASS] No work outside the orchestration package boundary is attempted.

[BLOCKER - SCOPE WARNING] The plan has 6 milestones (M1 through M6). `claude/rules.md §五` states "单 phase 建议 ≤5 个 slice". M6 is documentably foldable into existing completion conditions without implementation scope loss. This exceeds the slice limit and must be resolved before the Plan Gate.

[PASS] No second control plane is introduced. No second business implementation is created.

---

## 8. BLOCKER Items (Must Fix Before Plan Gate)

### BLOCKER-1: Milestone count exceeds the 5-slice limit

**Location**: Milestones table (M1–M6).
**Rule violated**: `docs/.agents/claude/rules.md §五` — single-phase slice count must be ≤5.
**Description**: The plan defines 6 milestones. M6 ("Facade cleanup, closeout, PR body, full validation") is administrative housekeeping equivalent to what other phases handle as completion conditions. The Completion Conditions section already covers the same requirements. Collapsing M6 into M5 or describing it as a PR gate condition (not a separate numbered milestone) resolves this without any scope change.
**Required fix**: Reduce milestone count to ≤5. The simplest resolution: rename M5 as the final implementation milestone (knowledge flow) and move M6 content into the Completion Conditions and Branch and Commit Strategy sections where it logically belongs.

---

## 9. CONCERN Items (Implementable with Explicit Assumptions)

| # | Milestone | Item |
|---|-----------|------|
| C-1 | M4 | Extracted helper event-kind allowlist not pre-specified. Codex must document at M4 commit time which `event.kind` values extracted helpers may `append_event` vs. which must stay Orchestrator-owned. |
| C-2 | M1-M5 | `save_state` closure injection must be explicitly prohibited. Plan guards against direct import/call but not closure delivery. Add a line to each relevant milestone acceptance: "no `save_state` reference may appear in the helper module by any means — import, call, or closure argument." |
| C-3 | M2, M4 | Transitive import audit not specified. Before moving each candidate function group, Codex should verify that the function group does not transitively import from `orchestration.harness` or `orchestration.executor` in a way that creates unintended coupling. This should be a pre-move checklist item per milestone. |
| C-4 | General | `harness.py` scope is not addressed. The plan should explicitly state: "harness.py is not in scope for migration in this phase; functions from orchestrator.py may not be moved to harness.py nor pulled from harness.py into new helper modules." |
| C-5 | General | Target module name discrepancies vs. `CODE_ORGANIZATION.md §5`: `subtask_flow.py` absent, `execution_flow.py` introduced, `artifact_writer.py` replaced by `artifact_index.py`. Codex should either align names with CODE_ORGANIZATION.md or add a note acknowledging the deliberate divergence and deferred items. |
| C-6 | M5 | `_apply_librarian_side_effects` migration to `knowledge_flow.py` would make that module the sole orchestration-internal importer of `apply_proposal`. Codex should clarify before M5: does `knowledge_flow.py` import `apply_proposal` directly (acceptable but requires explicit audit note) or receive it as a callable argument from Orchestrator? |
| C-7 | M1-M5 | `append_event` calls in extracted helpers are not covered by `test_state_transitions_only_via_orchestrator`. If any helper appends events, a focused assertion or module-level test should verify the helper does not use event appends to advance task state (i.e. no `kind = "state_transitioned"` or `kind = "entered_waiting_human"` emitted from helper code). |

---

## 10. PASS Items

- [PASS] Control Plane authority: `run_task` / `run_task_async` ownership explicitly preserved.
- [PASS] `save_state` gating: M1 acceptance explicitly holds `_set_phase` and `save_state` in `orchestrator.py`.
- [PASS] Non-goal boundary: LTO-9 / LTO-10 / LTO-11 work explicitly excluded.
- [PASS] Facade-first discipline: `orchestrator.py` remains the public compatibility facade throughout.
- [PASS] `apply_proposal` boundary: explicitly listed as a Design and Engineering Anchor; M5 acceptance gates on governance guard pass.
- [PASS] Path A / B / C boundaries: no route selection, provider routing, or executor registry change.
- [PASS] Invariant guard tests: listed as a required gate at every milestone.
- [PASS] Human commit gate: M4 and M5 specified as separate commits, branch created by Human after Plan Gate.
- [PASS] Eval exclusion: correctly excluded per shared rules §十.
- [PASS] No big-bang rewrite: phased extraction with facade retained as compatibility surface.
- [PASS] No new design documents: plan does not introduce unnecessary auxiliary files (`kickoff.md`, `breakdown.md`, `risk_assessment.md`).
- [PASS] Retrieval source policy defaults explicitly enumerated in M2 acceptance — this is a precise, auditable behavioral contract.
- [PASS] LTO-7 BLOCKER analog (cross-layer import chain): mitigated by keeping `executor.py` imports in `orchestrator.py` and not extracting executor-touching logic.
- [PASS] Risks and Controls table is present and covers the primary risks (second Control Plane, hidden behavior changes, sync/async divergence, subtask regression, knowledge write drift, over-broad branch).

---

## 11. Overall Conclusion

**Verdict: has-blockers — 1 BLOCKER, 7 CONCERNs**

**Recommended path: modify plan, then proceed to Plan Gate**

The plan is structurally sound and correctly identifies the Control Plane authority red line. The non-goals are tight, the milestone acceptance criteria are concrete, and the facade-first discipline is consistently applied. The plan is significantly better than a naive "split the big file" approach.

The single BLOCKER is a documentation issue (6 milestones vs. the 5-slice limit), not a design flaw. It can be resolved in a single plan edit. None of the CONCERNs are design blockers; each is implementable with an explicit assumption flagged at the relevant milestone.

**Required before Plan Gate:**
1. Reduce milestone count from 6 to 5 (BLOCKER-1). Recommended: fold M6 content into Completion Conditions.

**Recommended before implementation starts (CONCERNs C-1 through C-7):**
- Codex should absorb C-1 through C-4 as explicit acceptance criteria additions to the relevant milestones.
- C-5 (module naming) and C-6 (knowledge_flow import path) can be decided at implementation time with a note.
- C-7 (append_event in helpers) should be added as a focused assertion in `tests/unit/orchestration/` at each milestone that introduces a helper with event-writing capability.

After BLOCKER-1 is resolved, this plan is ready for the Human Plan Gate.
