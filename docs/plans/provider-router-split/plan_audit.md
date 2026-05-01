---
author: claude
phase: provider-router-split
slice: plan-audit
status: draft
depends_on:
  - docs/plans/provider-router-split/plan.md
  - docs/design/INVARIANTS.md
  - docs/design/PROVIDER_ROUTER.md
  - docs/design/DATA_MODEL.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/GOF_PATTERN_ALIGNMENT.md
  - docs/engineering/TEST_ARCHITECTURE.md
  - docs/roadmap.md
  - docs/plans/architecture-recomposition/plan.md
---

TL;DR:
Plan is largely sound and scope-disciplined. One BLOCKER: router.py imports from orchestration.executor and surface_tools, and those modules import back from provider_router — the extraction dependency graph is not mapped, so split modules may inherit this circular coupling silently.
Two CONCERNs: (1) M0 characterization test target location is unspecified relative to TEST_ARCHITECTURE.md's target layout; (2) M4 states "update agent_llm.py only if compatibility stays clean" but agent_llm.py already uses a lazy `from .router import invoke_completion` — the conditionality is ambiguous and risks a silent skip.
No SCOPE WARNING. Slice count is 6 (M0–M5), which exceeds the ≤5 recommendation.

# Plan Audit: Provider Router Split

## 1. Scope Discipline

- [PASS] Goals are bounded to facade-first extraction only. No new providers, no protocol changes, no schema migration. — `plan.md §Goals`
- [PASS] Non-goals explicitly exclude LTO-8/LTO-9/LTO-10 work, new public mutation entries, and moving Control Plane authority. — `plan.md §Non-Goals`
- [PASS] Target module list maps exactly to `CODE_ORGANIZATION.md §5.2`. No extra modules are proposed. — `plan.md §Target Module Shape`
- [PASS] "The exact split may be adjusted during implementation if tests show a cleaner dependency direction" is appropriately hedged and bounded by "must not collapse multiple unrelated architecture subtracks." — `plan.md §Target Module Shape` last paragraph
- [CONCERN] Slice count is 6 (M0 through M5). `rules.md §五` recommends ≤5 slices per phase. M0 (characterization) and M5 (cleanup/closeout) are both lightweight bookend milestones. Codex should assess whether M0 can be merged into M1 or M5 folded into the PR gate without loss of reviewability. — `claude/rules.md §五`

## 2. Invariant Boundary

- [PASS] `apply_proposal` as the sole public mutation entry for route metadata and policy is explicitly listed in Anchors and Non-Goals. — `plan.md §Anchors`, `plan.md §Non-Goals`
- [PASS] Path A/C governance and the prohibition on Path B calling Provider Router are listed as Material Risks with mitigation. — `plan.md §Material Risks`
- [PASS] `apply_route_registry`, `apply_route_policy`, `apply_route_weights`, `apply_route_capability_profiles` are public facade functions in `router.py` that do NOT bypass `apply_proposal` — they are separate `apply_*` helpers that load/save route metadata for bootstrap/configuration use, distinct from the governance `apply_proposal` path. The plan's language "keep `apply_*` facade functions stable" in M2 is correct but could cause confusion with `governance.apply_proposal`. — No change needed, but implementer should be aware of the naming collision.
- [PASS] Route metadata write drift is called out specifically in Material Risks with a concrete mitigation. — `plan.md §Material Risks`
- [PASS] Provider Router must not gain Control Plane authority is named in Anchors. — `plan.md §Anchors`
- [BLOCKER] `router.py` imports `from swallow.orchestration.executor import DEFAULT_EXECUTOR, normalize_executor_name` at module level (line 23). `executor.py` in turn imports `from swallow.provider_router._http_helpers import ...` and `from swallow.provider_router.cost_estimation import ...` at module level, and uses a deferred `from swallow.provider_router.router import lookup_route_by_name` inside a function. When `route_selection.py` is extracted and needs `DEFAULT_EXECUTOR` / `normalize_executor_name`, it must decide: import from `orchestration.executor` (inheriting the cross-layer coupling), import from `knowledge_retrieval.dialect_data` where `DEFAULT_EXECUTOR` is actually defined, or relocate the constant. The plan does not map this dependency and names no resolution strategy. If the wrong choice is made, the extracted module either introduces a new cross-module import cycle or an implicit assumption about where the constant lives. — `router.py` lines 23–25 vs. `executor.py` line 27 (actual source is `dialect_data.py`)

## 3. Milestone / Slice Executability

- [PASS] Each milestone has a named scope, risk level, validation command set, and a Human review + commit gate. — `plan.md §Plan` table
- [PASS] M2 (high-risk SQLite persistence extraction) and M3 (high-risk selection extraction) are separated into their own milestones with dedicated Human commit gates, satisfying the high-risk isolation requirement. — `plan.md §Plan`, `plan.md §Branch And PR Recommendation`
- [PASS] No single milestone moves more than one conceptual module boundary simultaneously (M1 moves registry+policy together, which are tightly coupled by their shared global state and short combined surface, an acceptable grouping). — `plan.md §Plan`
- [CONCERN] M0 (Baseline and import contract) does not specify where new characterization tests should land. The current `test_router.py` lives at the flat `tests/` root, but `TEST_ARCHITECTURE.md §1` targets `tests/unit/provider_router/` for focused router unit tests. If M0 adds characterization tests to the flat root, the subsequent extraction milestones will not have the target test location ready. The plan should either state "add to `tests/unit/provider_router/`" explicitly or acknowledge the test location as a M0 decision. — `TEST_ARCHITECTURE.md §1`, `plan.md §Plan M0`
- [PASS] M5 (cleanup and closeout) is lightweight and gates on the full pytest + compileall run, not on code movement. — `plan.md §Plan M5`
- [PASS] Validation command set is concrete and milestone-specific. Minimum validation is named for all milestones; additional focused checks are specified by name for M2 and M3. — `plan.md §Validation`

## 4. Test Coverage

- [PASS] Invariant guards `test_path_b_does_not_call_provider_router` and `test_route_metadata_writes_only_via_apply_proposal` are explicitly required in high-risk gates. — `plan.md §Material Risks`, `plan.md §Plan M2/M3`
- [PASS] `tests/test_phase65_sqlite_truth.py` is correctly identified as the M2 SQLite regression gate. — `plan.md §Validation`
- [PASS] `invoke_completion` coverage is required to remain mocked; no live HTTP or API key dependency is introduced. — `plan.md §Validation` last line
- [CONCERN] M4 moves `invoke_completion` to `completion_gateway.py` and states "update `agent_llm.py` to call the new module only if compatibility stays clean." The current `agent_llm.py` already uses a lazy import `from .router import invoke_completion` inside the function body (line 21). The conditionality ("only if compatibility stays clean") is ambiguous: if the implementer decides compatibility is not clean and skips the update, `agent_llm.py` will continue importing `invoke_completion` from `router.py`, which then re-exports from `completion_gateway.py`. This creates an indirect import chain but leaves `agent_llm.py` uncoupled from the new module's public API. The plan should clarify whether the M4 `agent_llm.py` update is required or explicitly deferred with a note in closeout. — `plan.md §Plan M4`, `agent_llm.py` line 21
- [PASS] Guard tests are listed in the Validation section and are required for every high-risk milestone gate. — `plan.md §Validation`
- [PASS] The plan correctly notes that `tests/unit/provider_router/` is the target for new focused tests. — `plan.md §Existing Surface` (implicitly, via TEST_ARCHITECTURE.md reference in Anchors)

## 5. Risk & Rollback

- [PASS] All six named Material Risks have explicit mitigations. — `plan.md §Material Risks`
- [PASS] Global policy state drift (`ROUTE_MODE_TO_ROUTE_NAME`, `ROUTE_COMPLEXITY_BIAS_ROUTES`, `ROUTE_STRATEGY_COMPLEXITY_HINTS`) is specifically called out with a concrete mitigation strategy ("move state in one milestone, preserve facade-visible getters"). — `plan.md §Material Risks`
- [PASS] Transaction nesting regression risk for `_run_sqlite_write` / `sqlite_store.get_connection` is explicitly named. — `plan.md §Material Risks`
- [PASS] Over-extraction risk is named and guarded: modules that have no real responsibility must stay in the facade. — `plan.md §Material Risks`
- [PASS] Import churn risk is named; the mitigation (keep existing imports valid, caller migration is optional touched-surface only) is consistent with facade-first discipline. — `plan.md §Material Risks`
- [PASS] Rollback is implicitly defined: removing the new modules restores all imports to `router.py` facade without data/schema loss, matching the program plan's subtrack entry criteria. — `docs/plans/architecture-recomposition/plan.md §Subtrack Entry Criteria`
- [CONCERN] The plan does not name a concrete rollback procedure for M2 (SQLite metadata store extraction). If `route_metadata_store.py` is partially written and the transaction envelope behavior changes, the rollback is not as simple as deleting the new module — the `_run_sqlite_write` closure pattern and `sqlite_store.get_connection` call sites need to be preserved verbatim. The plan should note that M2 must preserve the exact `_run_sqlite_write` wrapper contract or explicitly say "do not change transaction semantics; keep the wrapper function unchanged." This is not a blocker because the risk is named, but the mitigation should be tightened.

## 6. Phase-Guard (Scope vs Program Plan)

- [PASS] The plan's authorized scope matches the program plan's LTO-7 subtrack entry: "keep `router.py` compatibility facade, split registry / policy / metadata store / selection / completion gateway / reports." — `docs/plans/architecture-recomposition/plan.md §Program Topology`
- [PASS] The plan does not implement LTO-8 (Orchestration lifecycle), LTO-9 (Surface/CLI/Meta Optimizer), or LTO-10 (Governance apply handlers). These are explicitly in Non-Goals. — `plan.md §Non-Goals`
- [PASS] The plan does not touch program plan non-goals: does not change design semantics, does not make FastAPI a second business implementation, does not bypass `apply_proposal`. — `docs/plans/architecture-recomposition/plan.md §Non-Goals`
- [PASS] The plan stays within the subtrack entry criteria: compatibility facade identified (`router.py`), callers that must remain unchanged are listed, focused tests precede or accompany movement, no INVARIANTS boundary is weakened. — `docs/plans/architecture-recomposition/plan.md §Subtrack Entry Criteria`
- [PASS] No `[SCOPE WARNING]` required. The plan does not exceed LTO-7 authorization and does not touch non-goals of the program plan.

## 7. Required Items (BLOCKER)

1. **[BLOCKER — Dependency graph for cross-module imports not mapped (Section 2)]**
   `router.py` imports `DEFAULT_EXECUTOR` and `normalize_executor_name` from `swallow.orchestration.executor`, but `executor.py` re-exports these from `swallow.knowledge_retrieval.dialect_data`. When `route_selection.py` is extracted, this import must be resolved: the correct upstream source is `dialect_data.py`, not `executor.py`. The plan must add a note identifying this import chain and naming the intended import source for extracted modules that need `DEFAULT_EXECUTOR`. If the M3 implementer inherits the `from swallow.orchestration.executor import DEFAULT_EXECUTOR` line without checking, the extracted `route_selection.py` will gain a cross-layer dependency on orchestration that did not exist before.

   **Required resolution:** Add a note under M3 scope specifying that `DEFAULT_EXECUTOR` / `normalize_executor_name` should be imported from `swallow.knowledge_retrieval.dialect_data` (where they are defined) rather than through `swallow.orchestration.executor`, or alternatively identify an appropriate constants module if that import direction is also considered wrong.

## 8. Improvement Suggestions (CONCERN)

1. **[CONCERN — Slice count exceeds ≤5 guideline]** 6 milestones (M0–M5). Consider merging M0 characterization into M1 (write characterization tests, then immediately begin extraction in the same milestone), or folding M5 cleanup into the PR gate. If M0 is kept separate, it must have a Human commit gate or it cannot serve as an extraction baseline.

2. **[CONCERN — M0 test location unspecified]** Characterization tests added in M0 should land in `tests/unit/provider_router/` per `TEST_ARCHITECTURE.md §1` target shape, not the flat `tests/` root. Plan should name the target path explicitly to avoid creating technical debt in M0 that the subsequent slices inherit.

3. **[CONCERN — M4 agent_llm.py update conditionality is ambiguous]** The phrase "only if compatibility stays clean" needs a concrete definition of "not clean" or should be replaced with an explicit deferral policy: either (a) always update `agent_llm.py` in M4 to import from `completion_gateway.py` directly, or (b) always defer to M5 cleanup with a specific TODO note, or (c) leave `agent_llm.py` using `router.py` as the re-export path (which is valid if `router.py` re-exports `invoke_completion`). The current wording risks this update being silently skipped.

4. **[CONCERN — M2 rollback for transaction envelope not tightened]** The `_run_sqlite_write` transaction wrapper and `sqlite_store.get_connection` call pattern must be reproduced verbatim in `route_metadata_store.py`. The plan's mitigation says "keep focused SQLite truth tests in M2 and avoid changing transaction envelope semantics" but does not say "copy `_run_sqlite_write` into the new module" or "import it from a shared location." This is the highest-risk behavioral regression surface in the phase and deserves a more explicit instruction.

## 9. Items Confirmed Ready (PASS)

- Goals and non-goals are precise enough to prevent scope creep into LTO-8/9/10.
- Target module shape matches `CODE_ORGANIZATION.md §5.2` exactly.
- Facade-first discipline is correctly described: `router.py` stays as compatibility facade throughout.
- Existing caller list is specific and complete (orchestration, governance, surfaces, tests all named).
- Material Risks section names all high-probability failure modes with concrete mitigations.
- M2 and M3 are correctly separated into independent Human-gated milestones.
- Validation command set is concrete, milestone-specific, and reproducible.
- Invariant guard retention is required at every high-risk gate.
- `apply_proposal` as the sole public mutation entry is maintained: the router-internal `apply_route_*` functions are distinct from governance `apply_proposal` and the plan preserves their facade semantics.
- No live HTTP or API key dependency is introduced; `invoke_completion` stays mocked.
- No schema change, no migration, no `routes.default.json` content change.
- Branch strategy is correct: plan on `main`, implementation on `feat/provider-router-split` after Plan Gate.
- Phase-guard passes: no scope beyond LTO-7 first step authorization.

## 10. Overall Conclusion

**Recommended path: Modify plan.md to resolve the BLOCKER and three CONCERNs, then proceed to Plan Gate. No full rewrite required.**

**Reason:** The plan is well-structured, scope-disciplined, and respects all invariant boundaries. The single BLOCKER (unresolved cross-module import dependency for `DEFAULT_EXECUTOR`) is a concrete, narrow fix that does not require restructuring milestones. The three CONCERNs are all resolvable with 1–3 sentences of additional specification in the plan. The slice count concern (6 vs ≤5) is the least urgent: if Human decides M0 and M5 as bookend gates provide sufficient reviewability justification, the guideline can be acknowledged as a documented exception.

Model review (`model_review.md`) is recommended before Plan Gate because this phase touches Provider Router route metadata boundaries and the `apply_proposal` write path, satisfying the `[BLOCKER]-present` trigger condition in `claude/rules.md §六`.
