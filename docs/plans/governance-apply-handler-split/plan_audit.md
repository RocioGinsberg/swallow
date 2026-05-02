---
author: claude
phase: governance-apply-handler-split
slice: lto10-plan-audit
status: review
depends_on:
  - docs/plans/governance-apply-handler-split/plan.md
  - docs/design/INVARIANTS.md
  - docs/design/DATA_MODEL.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/TEST_ARCHITECTURE.md
---

TL;DR:
Plan is structurally sound and well-constrained. 0 blockers, 5 concerns. The headline risk is M3: `_apply_route_review_metadata` currently imports private underscore helpers from `swallow.surface_tools.meta_optimizer` by name — those helpers now live in LTO-9 split submodules and are only re-exported through the compatibility facade. M3 must resolve whether to import from the facade, from the owning submodule directly, or to inline-copy the helpers into `apply_route_metadata.py`. The plan does not name this decision. The remaining four concerns are implementation-discipline gaps: no named test for pre-M1 baseline characterization, guard allowlist migration order unspecified, `governance_models.py` growth constraint not asserted, and `tests/unit/truth_governance/` directory creation is a structural addition the plan quietly assumes.

## Audit Verdict

Overall: has-concerns

## Blockers

None.

## Concerns

### [CONCERN-1] M3 — Private helper import origin after LTO-9 split

**Location:** M3 Scope / `_apply_route_review_metadata` extraction

**Issue:** `_apply_route_review_metadata(...)` (governance.py lines 331–343) imports six names from `swallow.surface_tools.meta_optimizer` at call time: `OptimizationProposalApplicationRecord`, `ProposalApplicationEntry`, `_normalize_task_family_name`, `_timestamp_token`, `_write_json`, and `load_optimization_proposal_review`. After LTO-9's split, four of these are private helpers that now live in focused submodules (`meta_optimizer_models.py`, `meta_optimizer_proposals.py`, `meta_optimizer_lifecycle.py`) and are only re-exported through the `meta_optimizer.py` compatibility facade. The plan says "prefer direct imports from focused LTO-9 Meta-Optimizer modules where behavior-compatible" (M3 Scope) but does not resolve which of three approaches to take:

1. Keep importing through the `meta_optimizer.py` facade (safe, but couples `truth_governance` to a `surface_tools` compatibility shim permanently).
2. Import directly from the owning LTO-9 submodules (reduces coupling, but `_normalize_task_family_name`, `_timestamp_token`, `_write_json` are private by name and must be treated as owned by those submodules — a cross-package private import).
3. Inline-copy the three small utility helpers into `apply_route_metadata.py` or a shared `truth_governance` utility, breaking the dependency entirely.

**Why it matters:** Without a resolved decision, the implementer will make an ad-hoc choice during M3. Option 2 would introduce a new cross-package private import that could later be flagged by a future import guard. Option 3 requires a judgment call on what counts as behavior-preserving. The plan's "prefer direct imports" guidance is insufficient to start coding without a second pass.

**Suggested resolution:** Add to M3 Scope a one-sentence decision: either "import from the `swallow.surface_tools.meta_optimizer` facade until a dedicated cross-module utility path is established" or "inline the three filesystem helpers (`_write_json`, `_timestamp_token`, `_normalize_task_family_name`) into `apply_route_metadata.py` as private implementation". Either is acceptable as long as it is explicit. The acceptance criterion should add a `rg "from swallow.surface_tools.meta_optimizer import.*_" src/swallow/truth_governance/` check that is either zero-hit (if inlined) or explicitly bounded (if facade import is retained), so future guard drift does not occur silently.

---

### [CONCERN-2] M1 — `tests/unit/truth_governance/` is a new directory the plan does not call out

**Location:** M1 Scope ("Add focused boundary tests before broad movement, preferably under `tests/unit/truth_governance/`")

**Issue:** `tests/unit/truth_governance/` does not currently exist (verified: only `tests/unit/application/`, `tests/unit/knowledge/`, `tests/unit/orchestration/`, `tests/unit/provider_router/`, `tests/unit/surface_tools/` exist). Creating it is a structural addition that `TEST_ARCHITECTURE.md §1` anticipates but does not mandate. The plan uses "preferably" which makes this optional. If Codex skips the directory creation and places boundary tests in `tests/test_governance.py` instead (the existing root-level file), the `TEST_ARCHITECTURE.md §5` anti-growth rule is not technically violated (that rule targets `test_cli.py`), but the test placement will diverge from the target shape.

**Why it matters:** If M1 boundary tests land in the root-level test file, subsequent milestones will either continue adding there (defeating the architectural intent) or require a later file relocation, which risks obscuring regressions. The "preferably" hedge is too weak for a phase that explicitly tightens test discipline.

**Suggested resolution:** Change "preferably under `tests/unit/truth_governance/`" to "under `tests/unit/truth_governance/` (create directory; this is a structural addition and should be the first file created in M1 before any production code moves)." This makes the directory creation an explicit M1 step, not an afterthought.

---

### [CONCERN-3] M1/M2 — Guard allowlist migration order not sequenced

**Location:** M2 Acceptance ("Update guard tests so repository private writer calls are allowlisted only in the extracted handler modules")

**Issue:** `test_only_governance_calls_repository_write_methods` in `tests/test_invariant_guards.py` currently has a single-entry allowlist: `{"src/swallow/truth_governance/governance.py"}`. After M2 extracts `apply_canonical.py` and `apply_policy.py`, the private writer calls (`_promote_canonical`, `_apply_policy_change`) will move to those modules, and the guard will fail until the allowlist is updated. The plan says to update the allowlist narrowly to handler modules, but does not specify whether the allowlist update happens before, after, or simultaneously with the handler extraction.

If the handler code is moved before the allowlist is updated, the guard fails mid-M2. If the allowlist is updated before the handler moves, the guard passes too generously for the transition window. The plan does not address this sequencing.

**Why it matters:** Mid-milestone guard failures are noisy and can mask real regressions. LTO-9 Step 1 CONCERN-1 (allowlist drift in LTO-7) was caused precisely by an allowlist that drifted without a sequencing rule. The same failure mode applies here in the opposite direction.

**Suggested resolution:** Add a sentence to M2 Scope: "Update `test_only_governance_calls_repository_write_methods` allowlist in the same commit as — or immediately before — the private writer call moves to the extracted module. Never leave the guard failing between commits in a milestone." Mirror this rule for M3 when `_apply_metadata_change` moves. This is the same pattern `TEST_ARCHITECTURE.md §6` calls out: "update guard allowlists narrowly" — the plan should make "same-commit" the explicit migration order.

---

### [CONCERN-4] M3 — Named transaction rollback test required as explicit M3 gate

**Location:** M3 Acceptance ("Transaction and audit tests in `tests/test_phase65_sqlite_truth.py -q` pass")

**Issue:** The M3 acceptance criterion specifies running `tests/test_phase65_sqlite_truth.py -q` as a whole, but does not name the specific tests most likely to catch a silent transaction-semantic regression in `_apply_route_review_metadata`. The eight route metadata transaction rollback tests in that file (`test_route_metadata_transaction_rolls_back_sqlite_audit_and_in_memory`, `test_route_metadata_transaction_rolls_back_when_registry_save_fails_before_upsert`, etc.) and `test_route_review_artifact_write_failure_logs_warning_after_sqlite_commit` are the binding regression gates for M3. Running the full file passes them, but an implementer under time pressure who runs only focused tests could skip them.

**Why it matters:** M3 is rated high-risk. The route review apply path is the longest and most stateful function in governance.py (300 lines). Post-commit artifact failure semantics and the multi-step rollback ladder both need explicit gates. The LTO-9 audit (CONCERN-2) flagged the same pattern for CLI: pre-extraction baseline assertions must be named, not implied by "the file passes."

**Suggested resolution:** Add to M3 Acceptance: "The following tests in `tests/test_phase65_sqlite_truth.py` must pass individually before any M3 commit is pushed: `test_route_metadata_transaction_rolls_back_sqlite_audit_and_in_memory`, `test_route_metadata_transaction_rolls_back_when_audit_insert_fails_after_insert`, `test_route_metadata_commit_survives_caller_exception_after_commit`, and `test_route_review_artifact_write_failure_logs_warning_after_sqlite_commit`. These four tests are the minimal rollback-semantics and post-commit artifact gate for M3." Running the full file is still required at milestone close; these four are an explicit pre-commit check.

---

### [CONCERN-5] M4 — `governance_models.py` growth must be guarded, not just described

**Location:** Target Module Shape table / M4 Scope

**Issue:** `governance_models.py` is described as "optional shared public/private records if needed to avoid import cycles; public names remain re-exported from `governance.py`." The plan correctly limits it to a cycle-breaker. However, there is no automated check that prevents it from growing into a general shared models file over time. LTO-8/LTO-9 experience shows that files described as "optional cycle-breakers" can attract unrelated records if there is no enforcement.

**Why it matters:** If `governance_models.py` grows to hold non-cycle-breaking records during M1–M3, it becomes a second public API surface for `truth_governance`, blurring the facade boundary. The INVARIANTS §0 rule ("apply_proposal is the only public canonical / route / policy mutation entry") does not cover record leakage, but CODE_ORGANIZATION.md §5 Governance section makes `governance.py` the stable public facade — growing `governance_models.py` undermines that.

**Suggested resolution:** Add to M5 Acceptance (or M1 Acceptance if the file is created there): "If `governance_models.py` exists, a source-text boundary assertion must confirm it contains only record types that are also re-exported from `governance.py` and no handler logic, no repository calls, and no direct imports from handler modules." This can be a simple `assert "KnowledgeRepo" not in source` style check in a `tests/unit/truth_governance/test_governance_boundary.py` file (which M1 should create per CONCERN-2). The check takes one minute to write and permanently enforces the cycle-breaker-only scope.

---

## Validation

The following were cross-checked:

- `src/swallow/truth_governance/governance.py` (643 lines) read in full. Current Code Context claims in plan.md are accurate. `_emit_event(...)` is confirmed as a no-op placeholder (line 641–642). `_apply_route_review_metadata(...)` confirmed as the largest branch (~270 lines). Private proposal records (`_CanonicalProposal`, `_RouteMetadataProposal`, `_PolicyProposal`, `_MpsPolicyProposal`) and `_PENDING_PROPOSALS` confirmed to live in `governance.py`. Repository private writers are accessed exactly as described.
- `tests/test_invariant_guards.py`: `test_only_governance_calls_repository_write_methods` confirmed with `allowed_files={"src/swallow/truth_governance/governance.py"}` (single-entry allowlist). No pre-existing `apply_canonical.py`, `apply_policy.py`, or `apply_route_metadata.py` in the allowlist. Migration order gap confirmed (CONCERN-3).
- `tests/test_phase65_sqlite_truth.py`: 8 route metadata transaction rollback tests confirmed present and named. `test_route_review_artifact_write_failure_logs_warning_after_sqlite_commit` confirmed present. `test_route_metadata_commit_survives_caller_exception_after_commit` confirmed present. These are the correct M3 gate tests.
- `tests/unit/` directory: `truth_governance/` subdirectory confirmed absent. CONCERN-2 verified.
- `src/swallow/surface_tools/meta_optimizer*.py`: LTO-9 split confirmed. `_normalize_task_family_name` now in `meta_optimizer_proposals.py`, `_timestamp_token` in `meta_optimizer_models.py`, `_write_json` in `meta_optimizer_lifecycle.py`. All re-exported through `meta_optimizer.py` facade. CONCERN-1 confirmed.
- `docs/active_context.md`: Branch/PR recommendation is consistent. `active_branch: main`, implementation branch `feat/governance-apply-handler-split` after Human Plan Gate. Matches plan §Branch And PR Recommendation.
- `docs/design/INVARIANTS.md` §9 guard table: `test_only_apply_proposal_calls_private_writers` and `test_route_metadata_writes_only_via_apply_proposal` both listed. Plan explicitly requires these to remain at least as strict. Verified consistent.
- Non-Goals: All listed non-goals are load-bearing. "Do not change operator surface CLI/HTTP" is covered by "Do not expand CLI, FastAPI, Control Center..." and the public compatibility targets list. The non-goals are adequate.
- Completion Conditions: All are concretely checkable. No aspirational statements found.
- M4 `apply_outbox.py` scope: Plan explicitly states "no durable schema or event-log write is added in this phase" in the Target Module Shape table and repeats it in M4 Acceptance ("No durable outbox or event-log schema is introduced"). This is well-guarded. The "narrow if no real duplication" escape hatch in M4 Scope is acceptable and M4 Acceptance's "if not, closeout records why" language is an explicit condition, not a silent skip.

## Recommendations

1. **Before M1 starts:** Resolve CONCERN-1 (private helper import origin for M3) in `plan.md`. A one-sentence addition to M3 Scope is sufficient.
2. **Before M1 starts:** Harden M1 Scope to make `tests/unit/truth_governance/` directory creation an explicit first step (CONCERN-2).
3. **Before M1 starts:** Add same-commit sequencing rule for guard allowlist updates to M2 and M3 Scope (CONCERN-3). This is the single most common guard drift failure mode in this project.
4. **Before M3 starts:** Add four named test-level pre-commit checks to M3 Acceptance (CONCERN-4). These tests already exist; they just need to be named as explicit gates.
5. **Before M5 closes:** Add a source-text boundary assertion for `governance_models.py` to M5 Acceptance (or M1 if the file is created there) (CONCERN-5).

None of the concerns require a plan rewrite. CONCERN-1 and CONCERN-3 are the highest priority and should be absorbed before Codex starts coding. CONCERN-2, CONCERN-4, and CONCERN-5 can be absorbed in the first commit of the relevant milestone.

## Confirmed Ready

- M5 (Facade cleanup / closeout): Scope and acceptance are well-defined. Completion conditions are concrete. No issues.
- M4 (Apply envelope / outbox helper): Outbox scope creep is correctly guarded by three explicit "no durable schema / no event-log write" constraints. "Narrow if no duplication" escape hatch has a required closeout note. Ready pending CONCERN-1 resolution (which affects M3, not M4 directly).
- M2 (Canonical and policy handlers): Scope is clear and the affected modules are named. Ready pending CONCERN-3 (allowlist migration order).
- M1 (Baseline and proposal registry): Scope is clear. Ready pending CONCERN-2 (test directory creation) and CONCERN-3 (allowlist migration order for the guard update step).
- M3 (Route metadata handler): Ready pending CONCERN-1 (import origin decision), CONCERN-3 (allowlist migration order for `_apply_metadata_change` move), and CONCERN-4 (named rollback test gates).
