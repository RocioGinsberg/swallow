---
author: claude
phase: provider-router-split
slice: pr-review
status: review
depends_on:
  - docs/plans/provider-router-split/plan.md
  - docs/plans/provider-router-split/plan_audit.md
  - docs/plans/provider-router-split/closeout.md
  - docs/design/INVARIANTS.md
  - docs/design/PROVIDER_ROUTER.md
  - docs/engineering/CODE_ORGANIZATION.md
  - pr.md
---

TL;DR:
Implementation matches the revised plan and resolves all four audit findings (BLOCKER + 3 CONCERN). `router.py` reduced from 1422 lines to a thin compatibility facade over six focused modules. Full pytest passes locally (651 passed, 8 deselected, 10 subtests). One CONCERN on guard allowlist drift, two CONCERN on minor follow-ups. No BLOCK. Recommendation: merge.

# PR Review: Provider Router Split (LTO-7 Step 1)

## Review Scope

- branch: `feat/provider-router-split` @ `cbc72ce`
- merge-base with main: `a1b8d9e1` (plan commit)
- diff stat: 20 files, +2230 / −1338
- src changes: 6 new modules, `router.py` reduced from 1422 → 267 lines, `agent_llm.py` lazy-import retargeted
- test changes: 6 new files under `tests/unit/provider_router/`, 1 invariant guard relocated, 1 router test patch path updated
- plan / closeout / pr.md: present and consistent

## 1. Plan Conformance — `[PASS]`

- [PASS] All six target modules from `plan.md §Target Module Shape` exist with the named ownership (`route_registry.py`, `route_policy.py`, `route_metadata_store.py`, `route_selection.py`, `completion_gateway.py`, `route_reports.py`).
- [PASS] `router.py` retained as compatibility facade with public re-exports for constants, aliases, `RouteRegistry`, `ROUTE_REGISTRY`, normalizers, and wrapper functions. Existing imports from `swallow.provider_router.router` remain valid.
- [PASS] Milestone shape matches plan: M1 registry+policy, M2 metadata store, M3 selection, M4 completion gateway + reports, M5 cleanup. Each milestone is a separate commit with its own validation gate (commits `088e80a`, `2ff2941`, `eb7c54e`, `380d202`, `64995d6`).
- [PASS] No `docs/design/*.md` changes, no schema migrations, no `routes.default.json` / `route_policy.default.json` content changes.

## 2. Audit Resolution — `[PASS]`

- [PASS] **BLOCKER (DEFAULT_EXECUTOR import direction)** resolved. `route_selection.py:5` imports `DEFAULT_EXECUTOR` and `normalize_executor_name` from `swallow.knowledge_retrieval.dialect_data`, not `swallow.orchestration.executor`. Verified with `rg -n "from swallow.orchestration.executor" src/swallow/provider_router` → no matches.
- [PASS] **CONCERN-1 (slice count)** resolved. M0 characterization tests folded into M1; final milestone count is 5 (M1–M5).
- [PASS] **CONCERN-2 (test target path)** resolved. All new focused tests landed under `tests/unit/provider_router/` per `TEST_ARCHITECTURE.md §1`.
- [PASS] **CONCERN-3 (`agent_llm.py` ambiguity)** resolved with option (a). `agent_llm.py:21` now lazy-imports `from .completion_gateway import invoke_completion` directly. `router.py` still re-exports `invoke_completion` for any legacy callers.
- [PASS] **CONCERN-4 (M2 transaction wrapper)** resolved. `_run_sqlite_write` and `sqlite_store.get_connection` patterns moved into `route_metadata_store.py` verbatim; transaction semantics preserved (verified at lines 331–474 of `route_metadata_store.py`).

## 3. Invariant Boundary — `[PASS]` with one `[CONCERN]`

- [PASS] `apply_proposal` remains the unique public mutation entry. The router-internal `apply_route_*` family is preserved as compatibility facade functions; no new public mutation entry was added.
- [PASS] Path A / Path C governance preserved. `select_route` and the fallback chain logic moved into `route_selection.py` without semantic change.
- [PASS] Path B isolation is **strengthened** by the guard relocation: `test_specialist_internal_llm_calls_go_through_router` now tightens the chat-completion HTTP allowlist from `router.py` to `completion_gateway.py` only (single-file allowlist, narrower than before).
- [PASS] `test_path_b_does_not_call_provider_router` continues to scan `orchestration/executor.py` for selection-function imports/calls. Provider Router selection remains outside Path B.
- [PASS] No new cross-layer dependency from Provider Router into orchestration implementation. Remaining `from swallow.orchestration.*` imports are limited to value/config types (`models`, `runtime_config`), which the plan explicitly permits and the program plan's dependency direction allows.
- [CONCERN — Guard allowlist semantic drift] `test_route_metadata_writes_only_via_apply_proposal` allowlist still names `src/swallow/provider_router/router.py` as the only Provider Router file allowed to reference `save_route_registry / save_route_policy / save_route_weights / save_route_capability_profiles`. After this PR, **the actual function bodies live in `route_metadata_store.py`**, while `router.py` is a thin wrapper that forwards via `route_metadata_store_module.save_*`. The guard happens to pass because it inspects `ImportFrom` and `Call` nodes by name, and `route_metadata_store.py`'s own definitions are neither imports nor outbound calls of those names. But the **intent** of the guard ("only these files may write route metadata") is now misaligned with the new module topology: the writers live in a file the allowlist does not name. Recommendation: add `src/swallow/provider_router/route_metadata_store.py` to the allowlist in a follow-up commit so the guard's allowlist matches the actual implementation surface. Not a BLOCK because the guard does not currently produce false negatives or false positives, but it should be tightened before LTO-10 (governance apply split) lands, otherwise the same drift will compound.

## 4. Test Coverage — `[PASS]`

- [PASS] Full pytest run on this branch: `651 passed, 8 deselected, 10 subtests passed in 104.82s`. Re-verified locally during review.
- [PASS] Six new focused unit tests under `tests/unit/provider_router/`:
  - `test_registry_policy_modules.py` — module/facade parity for registry + policy (M1)
  - `test_metadata_store_module.py` — round-trip + snapshot for metadata store (M2)
  - `test_route_selection_module.py` — module/facade parity, detached route, fallback chain, **import-boundary coverage** (M3)
  - `test_completion_gateway_module.py` — gateway invocation through new module (M4)
  - `test_reports_module.py` — report rendering parity (M4)
  - `test_router_facade_module.py` — facade re-export contract (M5)
- [PASS] `tests/test_router.py:147` patch target updated from `swallow.provider_router.router.httpx.post` to `swallow.provider_router.completion_gateway.httpx.post`. The test name was also renamed from `test_call_agent_llm_invokes_router_completion_gateway` to `test_call_agent_llm_invokes_completion_gateway`, matching the new module ownership. Other router tests still patch `swallow.provider_router.router.ROUTE_REGISTRY` per closeout note (compatibility patch point preserved).
- [PASS] Invariant guards run inside the full pytest. `test_specialist_internal_llm_calls_go_through_router`, `test_path_b_does_not_call_provider_router`, and `test_route_metadata_writes_only_via_apply_proposal` all pass.
- [PASS] No live HTTP / API-key dependent test introduced; `invoke_completion` coverage stays mocked per plan §Validation last line.

## 5. Code Hygiene — `[PASS]` with two `[CONCERN]`

- [PASS] `router.py` reduced from 1422 lines (pre-merge-base) to 267 lines. `rg -n "sqlite_store|sqlite3|httpx\.post|class RouteRegistry|def invoke_completion|def build_route_registry_report|_replace_route_registry_in_sqlite" src/swallow/provider_router/router.py` → no matches (verified in closeout). Internals fully moved out.
- [PASS] No powerless wrapper modules. Each new file owns one concrete responsibility from the target shape.
- [PASS] `git diff --check` passes; no whitespace / mixed-indent damage.
- [CONCERN — `_apply_route_policy_payload` private name leak across module boundary] `router.py:53` calls `route_policy_module._apply_route_policy_payload(route_policy)`. Reaching into another module's underscore-prefixed symbol works but signals the function is not really private to `route_policy.py`. Either rename to `apply_route_policy_payload` (public) and have `router.py` call the public form, or expose a public re-application wrapper from `route_policy.py` and keep the underscore form truly module-internal. Same observation for the helpers reached via `route_registry_module._normalize_task_family_scores` / `_normalize_unsupported_task_types` / `_routes_from_registry_payload` (router.py:103, 153, 156, 167). This is purely a hygiene point; not blocking.
- [CONCERN — `_BUILTIN_ROUTE_FALLBACKS` lives in `router.py` but registry data is owned by `route_registry.py`] `router.py:58, 99, 105, 197–203` maintain a module-global `_BUILTIN_ROUTE_FALLBACKS` derived from the registry. The fallback baseline conceptually belongs with `RouteRegistry`. Not a blocker because the fallback semantics are unchanged and `apply_route_fallbacks` is still on the facade for caller compatibility, but a future touched-surface pass may want to relocate this state into `route_registry.py` so the registry owns its own builtin-fallback baseline.

## 6. Documentation — `[PASS]`

- [PASS] `closeout.md` records final module ownership table, compatibility notes, boundary notes, and validation outputs. Status `final`.
- [PASS] `pr.md` matches closeout content and lists the relevant test commands. Status: pending Human review / commit / PR creation.
- [PASS] `docs/active_context.md` records the M5 validation passing state and waiting-for-Human-commit gate.
- [PASS] No update to `docs/roadmap.md` was made on this branch — correct per `claude/rules.md §一` (LTO-7 progress factual update is `roadmap-updater` subagent's job after merge, not a same-branch concern).

## 7. Phase-Guard (Scope vs Plan) — `[PASS]`

- [PASS] No LTO-8 (orchestration), LTO-9 (surface / CLI / meta optimizer), or LTO-10 (governance apply) work performed. All six new modules are within Provider Router boundary.
- [PASS] No new public mutation entry, no schema migration, no design doc change, no default route data change.
- [PASS] No `[SCOPE WARNING]` required.

## 8. CONCERN Summary

| # | Severity | Item | Disposition |
|---|----------|------|-------------|
| 1 | CONCERN | Guard allowlist `test_route_metadata_writes_only_via_apply_proposal` does not yet name `route_metadata_store.py` as the actual write-implementation file | Backlog — fix before LTO-10 |
| 2 | CONCERN | `router.py` reaches into `_`-prefixed names in `route_policy.py` / `route_registry.py` | Backlog — hygiene |
| 3 | CONCERN | `_BUILTIN_ROUTE_FALLBACKS` lives in `router.py` but conceptually belongs with `route_registry.py` | Backlog — touched-surface follow-up |

All three are recorded for `docs/concerns_backlog.md` per `claude/rules.md §八`. None block this PR.

## 9. PASS Summary

- Plan structure, milestone gating, and commit shape match the revised plan exactly.
- BLOCKER from `plan_audit.md` resolved with verifiable code change.
- All four CONCERNs from `plan_audit.md` resolved.
- Invariant guard for chat-completion HTTP narrowed (single-file allowlist) — strengthened, not weakened.
- `apply_proposal`, Path A/B/C, and Provider Router → orchestration implementation isolation preserved.
- 651-test full suite green locally on the review machine.
- Compatibility facade contract honored: existing imports keep working.
- M2 transaction wrapper preserved verbatim per audit demand.
- Behavior-preserving migration: no design doc, schema, default data, or routing semantics change.

## 10. Recommendation

**Merge.**

This PR is a clean facade-first execution of LTO-7 Step 1 and is exactly the warm-up phase the program plan called for. It establishes the working pattern (plan → audit → revise → implement per milestone with separate Human commit gates) that LTO-8 / LTO-9 / LTO-10 will inherit.

The three CONCERNs are non-blocking hygiene items appropriate for `docs/concerns_backlog.md`. Specifically:

- CONCERN-1 should be fixed **before LTO-10** (Governance apply handler split), because LTO-10 will compound the same allowlist-vs-implementation drift if not addressed first.
- CONCERN-2 / 3 are touched-surface follow-ups, no specific deadline.

## 11. Post-Merge Actions (for tracking, not blocking)

- `roadmap-updater` subagent should mark LTO-7 Step 1 as completed, advance the §三 ticket queue to LTO-8 (Orchestration lifecycle) per the simplified path the user already approved.
- Tag evaluation: I would **not** recommend a new tag for LTO-7 alone. The four Cluster-C subtracks together form a coherent capability boundary for `v1.6.0`; tagging mid-cluster would advertise a structural baseline that is still in motion.
- `docs/concerns_backlog.md` should record the three CONCERNs above, mapped to LTO-10 (CONCERN-1) and LTO-7-followup (CONCERN-2 / 3).
