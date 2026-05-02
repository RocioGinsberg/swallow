---
author: claude
phase: surface-cli-meta-optimizer-split
slice: pr-review
status: review
depends_on:
  - docs/plans/surface-cli-meta-optimizer-split/plan.md
  - docs/plans/surface-cli-meta-optimizer-split/plan_audit.md
  - docs/plans/surface-cli-meta-optimizer-split/closeout.md
  - docs/design/INVARIANTS.md
  - docs/design/INTERACTION.md
  - docs/design/SELF_EVOLUTION.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/TEST_ARCHITECTURE.md
  - pr.md
---

TL;DR:
Implementation matches the audit-revised plan and resolves all 5 CONCERNs from `plan_audit.md`. **LTO-7 carryover allowlist drift is fixed**—the guard now explicitly names `route_metadata_store.py` as physical writer owner with `router.py` only as a documented legacy facade exception, plus a positive `protected_writers <= route_metadata_store_imports` assertion that catches future drift. `cli.py` reduced 3790 → 3629 lines (~4%) and `meta_optimizer.py` 1320 → ~30 facade lines; 6 new focused modules + 3 CLI adapters + 2 application commands. Audit's source-text boundary checks (C-3, C-5) made persistent unit tests, exactly applying LTO-8 lesson. Full pytest passes locally (696 passed). Two CONCERN on follow-up scope, one PASS-with-note on a defect-catching M5 fix. Recommendation: **merge**.

# PR Review: Surface / CLI / Meta Optimizer Split (LTO-9 Step 1)

## Review Scope

- branch: `feat/surface-cli-meta-optimizer-split` @ `4b66ad2`
- merge-base on `main`: post-LTO-8 (`9ee9cc8 docs(state): update roadmap`)
- diff stat: 25 files, +2659 / −1764
- src changes: 6 new Meta-Optimizer modules (`meta_optimizer_{models,snapshot,proposals,reports,lifecycle,agent}.py`), 3 new CLI adapters (`cli_commands/{meta_optimizer,proposals,route_metadata}.py`), 2 new application commands (`application/commands/{proposals,meta_optimizer}.py`), expanded application/queries Control Center, `cli.py` 3790 → 3629 lines (-161 lines), `meta_optimizer.py` 1320 → ~30 lines (compatibility facade)
- test changes: 3 new files under `tests/integration/cli/` (proposal/route/meta-optimizer commands), 2 new boundary unit tests under `tests/unit/{application,surface_tools}/`, `test_invariant_guards.py` updated with positive assertions for LTO-7 carryover fix
- plan / audit / closeout / pr.md: present and consistent
- full pytest re-verified locally during review: `696 passed, 8 deselected, 10 subtests passed in 111.71s`

## 1. Plan Conformance — `[PASS]`

- [PASS] All target modules from plan `§Target Module Shape For This Phase` exist with the named ownership.
- [PASS] `swallow.surface_tools.cli.main` / `build_parser` and `swallow.surface_tools.meta_optimizer` retained as compatibility facades. The 6 milestones (M1–M5) match the revised plan with one separate fix commit `4b66ad2`.
- [PASS] No `docs/design/*.md` changes, no schema migrations, no proposal target kind changes, no Provider Router behavior changes, no Path A/B/C semantic changes.
- [PASS] Commit shape matches plan `§Branch And Commit Strategy`: 5 implementation commits + 1 follow-up fix.

## 2. Audit Resolution — `[PASS]`

The audit recorded 0 BLOCKERs and 5 CONCERNs. All five are absorbed:

- [PASS] **C-1 (M3 in-scope `swl` subcommand enumeration)**. Resolved in `plan.md §M3 Acceptance` with explicit list (`swl meta-optimize`, `swl proposal review/apply`, `swl route weights show/apply`, `swl route capabilities show/update`) AND explicit out-of-scope list (`swl route registry`, `swl route policy`, `swl route select` stay in `cli.py`). The CLI adapter implementation (`src/swallow/surface_tools/cli_commands/`) matches this enumeration exactly — no scope creep.
- [PASS] **C-2 (M3 pre-extraction characterization tests)**. Resolved in `plan.md §M3 Acceptance` and verified in implementation: `tests/integration/cli/test_proposal_commands.py`, `test_route_commands.py`, `test_meta_optimizer_commands.py` exist and assert stdout/stderr/exit-code patterns. The plan made this an **explicit precondition** ("Only after the pre-extraction characterization tests pass should parser or dispatch code move into `cli_commands/`"), which is the correct discipline structure.
- [PASS] **C-3 (M1 application/commands no-terminal-formatting test)**. Resolved with `tests/unit/application/test_command_boundaries.py` containing 11 forbidden-token assertions (`argparse`, `click`, `rich`, `\033[`, `\x1b[`, `print(`, `sys.stdout`, `sys.stderr`) plus a second test asserting proposal commands go through `register_route_metadata_proposal(...) + apply_proposal(...)` and forbid direct `route_metadata_store` / `save_route_*` references. **This is the strongest possible application of the LTO-8 lesson** — the test will fail in normal `pytest -q` if any future change breaches the boundary, regardless of import structure.
- [PASS] **C-4 (M4 conditional scope go/no-go)**. Resolved in `plan.md §M4 Acceptance` with explicit checkpoint language: "skip the query move and record `M4 query tightening skipped as not-safe` with rationale in closeout" if not safe. Implementation actually performed the optional move — `closeout.md §M4` records "Moved read-only Control Center artifact / subtask tree / execution timeline payload builders into `application/queries/control_center.py`". `tests/test_web_api.py` passes unchanged (HTTP response shape preserved per audit C-4 requirement).
- [PASS] **C-5 (M2 persistent boundary tests, not manual rg)**. Resolved with `tests/unit/surface_tools/test_meta_optimizer_boundary.py` containing 4 test functions covering 5 read-only modules with 7 prohibited mutation API tokens + a regex `\b(INSERT|UPDATE|DELETE)\b` SQL mutation check + a positive `MetaOptimizerAgent` no-`apply_proposal` assertion + a public-import-preservation check on the facade. Again, this is the LTO-8 source-text-grep pattern correctly applied.

## 3. LTO-7 Carryover Resolution (Critical) — `[PASS]` and **strengthened beyond audit ask**

This was the highest-priority secondary goal of LTO-9. The implementation is **better than what the audit asked for**:

- [PASS] **Allowlist correctly updated**. `tests/test_invariant_guards.py:228–232` — allowlist now contains `provider_router/route_metadata_store.py` (`# physical route metadata writer owner`), `provider_router/router.py` (`# legacy compatibility facade wrappers`), `truth_governance/truth/route.py` (`# governance repository caller`). Each entry has an explicit comment documenting *why* it's in the allowlist — exactly the documentation discipline the LTO-7 review concern asked for.
- [PASS] **Positive assertion added** (`tests/test_invariant_guards.py:217–227`). New code parses `truth/route.py` AST and asserts `protected_writers <= route_metadata_store_imports` — that is, **the route repository must import the 4 protected writer functions specifically from `swallow.provider_router.route_metadata_store`**. This catches a future drift the audit didn't anticipate: if anyone moves the writer implementations elsewhere (or renames them), this assertion fails immediately. **This is a stronger guarantee than the LTO-7 review CONCERN-1 even hoped for.**
- [PASS] **`provider_router/router.py` correctly retained as legacy facade**. The closeout note "wrapper functions remain only as legacy compatibility surface" is honest — the facade is not pretending to be the writer.
- [PASS] **`test_only_apply_proposal_calls_private_writers` allowlist also updated** (line 304–306) with the same physical-vs-facade distinction.
- [PASS] **`test_no_module_outside_governance_imports_store_writes` allowlist** (line 359) also adds `route_metadata_store.py` for the same reason.
- [PASS] **`meta_optimizer_agent.py` added to `EXECUTION_PLANE_FILES`** (line 66) — preempts agent code from accidentally triggering governance/private writer guards. Smart proactive measure.

## 4. Invariant Boundary — `[PASS]`

- [PASS] `apply_proposal` remains the unique public mutation entry. `application/commands/proposals.py:84-89` shows the canonical operator path: `register_route_metadata_proposal(...)` → `apply_proposal(proposal_id, OperatorToken(source="cli"), ProposalTarget.ROUTE_METADATA)`. No new public mutation entry.
- [PASS] Meta-Optimizer remains proposer-only. `meta_optimizer_agent.py` ripgrep clean of `apply_proposal` / `save_state` / `save_route_*` (verified during review). `MetaOptimizerAgent` / `MetaOptimizerExecutor` live in `meta_optimizer_agent.py` per closeout.
- [PASS] INTERACTION.md §4.2 preserved — `web/api.py` is now a thin FastAPI adapter, payload builders moved to `application/queries/`. No new write endpoint introduced.
- [PASS] INVARIANTS.md §0 "Control only in Orchestrator / Operator" — `application/commands` is the operator path, not a second control plane. Application command modules return structured data; CLI adapters format. Confirmed by source-text boundary tests.
- [PASS] INVARIANTS.md §5 Truth writes matrix: Meta-Optimizer's `truth_writes = {event_log, proposal_artifact}` boundary preserved. Confirmed by `test_meta_optimizer_boundary.py`.

## 5. CLI Behavior Preservation — `[PASS]`

- [PASS] `swl --help` listing not changed (verified by integration tests for in-scope commands).
- [PASS] stdout / stderr / exit codes preserved per `test_proposal_commands.py`, `test_route_commands.py`, `test_meta_optimizer_commands.py` integration coverage.
- [PASS] `swl serve` (FastAPI/Control Center) tested — `tests/test_cli.py -k serve` passes.
- [PASS] In-scope route commands handled by `cli_commands/route_metadata.py`; out-of-scope route commands (`registry`, `policy`, `select`) correctly remain in `cli.py` per plan.

## 6. Test Architecture Alignment — `[PASS]`

- [PASS] New CLI tests in `tests/integration/cli/` per `TEST_ARCHITECTURE.md §5`. Existing `tests/test_cli.py` not grown for touched behavior — only deselected by `-k` pattern at validation gates.
- [PASS] Boundary tests use the per-module source-text grep pattern established in LTO-8. The pattern is now applied **across three test files** (LTO-8's `tests/unit/orchestration/*` + LTO-9's `tests/unit/application/test_command_boundaries.py` + `tests/unit/surface_tools/test_meta_optimizer_boundary.py`), which means the project has converged on a real testing convention rather than a one-off.
- [PASS] `tests/integration/cli/test_synthesis_commands.py` from a previous phase preserved — no test relocation collision.

## 7. Code Hygiene — `[PASS]` with one PASS-with-note

- [PASS] `cli.py` reduced 3790 → 3629 lines (~4% net reduction). This is intentionally small — only in-scope commands extracted; rest deferred. Closeout records this. Lower than LTO-8's ~14% but **purposefully** — Step 1 is bounded.
- [PASS] `meta_optimizer.py` reduced 1320 → ~30 facade lines. The functional code moved to 6 focused modules (~1380 line increase across them, ~5% net growth from closure overhead — acceptable for a 6-way split).
- [PASS] No powerless wrapper modules. Each helper owns concrete responsibility (per `GOF_PATTERN_ALIGNMENT.md §1`).
- [PASS] `git diff --check` passes.
- [PASS-with-note] **M5 follow-up fix `4b66ad2` catches a real defect**. The `route weights apply` and `route capabilities update` adapter originally used proposal IDs derived only from `proposal_path.name` and `route_name` — meaning two CLI invocations in the same Python process (e.g., consecutive integration tests, or a `swl` script that runs both) would collide on `PendingProposalRepo`. The fix adds `time.time_ns()` suffix; proposal_id is not in stdout/stderr so behavior preservation holds. **This is exactly the kind of defect that gets caught by full pytest after extraction**, not by manually running CLI once. It's a positive sign that the test harness is doing its job. The fix commit is small and surgical.

## 8. Documentation — `[PASS]`

- [PASS] `closeout.md` records milestone results, implementation notes, boundary confirmation, deferred work, validation outputs. Status `final`.
- [PASS] `pr.md` is consistent with closeout. Plan-audit absorption summary in `pr.md` is accurate (5/5).
- [PASS] `docs/active_context.md` reflects current branch state.
- [PASS] No `docs/roadmap.md` change made on this branch — correct; LTO-9 → LTO-10 transition is post-merge `roadmap-updater` work.

## 9. Phase-Guard (Scope vs Plan) — `[PASS]`

- [PASS] No LTO-10 (Governance apply handler split) work performed. `apply_proposal` private handlers untouched.
- [PASS] No LTO-8 follow-up (`harness.py` decomposition, further `orchestrator.py` reduction) work.
- [PASS] No LTO-1 Wiki Compiler work.
- [PASS] No LTO-7 hygiene CONCERN-2/3 fixes (private name leak, `_BUILTIN_ROUTE_FALLBACKS` location) — correctly deferred to touched-surface basis as `concerns_backlog.md` recorded. Only CONCERN-1 (allowlist drift) was in scope.
- [PASS] No `[SCOPE WARNING]`. The plan honored its own ≤5 milestone discipline and bounded subcommand extraction.
- [PASS] LTO-5 advanced **incrementally**: `application/commands/` seeded with proposal + meta-optimizer commands only. **Did not** push to full LTO-5 (CLI/FastAPI/all write commands/repository ports) — exactly the right Step 1 posture, mirroring LTO-8's "Step 1 not Final" pattern.

## 10. CONCERN Summary

| # | Severity | Item | Disposition |
|---|----------|------|-------------|
| 1 | CONCERN | LTO-9 deferred broad task/knowledge/artifact CLI command-family migration; remains a multi-step LTO-9 program just like LTO-8 | Tracking note — closeout already records this; roadmap LTO-9 row should read "Step 1 done", not "fully done", same as LTO-8 |
| 2 | CONCERN | LTO-7 hygiene CONCERN-2 (private name leaks) and CONCERN-3 (`_BUILTIN_ROUTE_FALLBACKS` location) remain unaddressed | Deferred — touched-surface follow-up; will likely never need a dedicated phase, gets picked up when next change touches `provider_router/router.py` or `route_registry.py` |

Both CONCERNs are intentional deferrals already documented in `closeout.md §Deferred Work`. No new CONCERNs introduced by this PR.

## 11. PASS Summary

- All 5 audit CONCERNs (C-1 through C-5) resolved with verifiable artifacts.
- LTO-7 carryover CONCERN-1 fixed **with stronger guarantees than the original audit ask** (positive assertion linking repo to physical store).
- Source-text boundary test pattern (LTO-8 lesson) now established across 3 test files as a real project convention.
- Meta-Optimizer proposer-only boundary preserved with persistent test enforcement.
- `apply_proposal` invariant preserved.
- CLI behavior preservation verified by 3 new integration test files.
- 696-test full suite green locally.
- M4 query tightening proceeded safely with no test regression — `web/api.py` thinned to a real adapter.
- M5 follow-up fix catches a real same-process proposal_id collision defect.
- Behavior-preserving migration: zero design / schema / output / public-API change.
- LTO-5 application/commands seeded incrementally, not pushed to completion.

## 12. Recommendation

**Merge.**

This PR is the cleanest of the three Cluster-C subtracks so far. It carries forward and strengthens the LTO-8 source-text-boundary pattern, fixes the LTO-7 carryover CONCERN-1 with a stronger guard than the original concern asked for, and incrementally seeds the LTO-5 application/commands boundary without scope creep. The M5 follow-up fix catches a real concurrency-style defect that the new test harness exposed — precisely the kind of regression-catching the new layered tests are supposed to find.

Of particular note: the project now has **three concrete examples** (LTO-7 `tests/unit/provider_router/`, LTO-8 `tests/unit/orchestration/*`, LTO-9 `tests/unit/{application,surface_tools}/*`) of the source-text-grep boundary test pattern. This is no longer experimental — it should be documented as a recommended pattern in `docs/engineering/TEST_ARCHITECTURE.md` whenever LTO-4 (TDD harness) gets touched.

## 13. Post-Merge Actions (for tracking, not blocking)

- `roadmap-updater` subagent should mark LTO-9 row as **"Step 1 done"** (not "fully done"), same posture as LTO-8. The "下一类增量" cell should record:
  - broad task/knowledge/artifact CLI command-family migration (deferred)
  - the 5 deferred route commands (`registry show/apply`, `policy show/apply`, `select`)
  - LTO-7 hygiene CONCERN-2/3 (touched-surface only)
- §三 ticket queue advances to **LTO-10 Governance apply handler split** (the last Cluster-C subtrack).
- LTO-5 progress is real but partial — roadmap LTO-5 "当前状态" cell can mention proposal + meta-optimizer command seeds exist; full CLI/FastAPI/write/repository ports remain.
- `docs/concerns_backlog.md` LTO-7 follow-up group: CONCERN-1 is now **Resolved** (move from Active Open to Resolved). CONCERN-2 and CONCERN-3 remain Active Open.
- Tag evaluation: LTO-9 is the third of four Cluster-C subtracks. **Do not** tag yet. After LTO-10 completes, evaluate `v1.6.0` for the full Cluster-C structural baseline.
- Recommend documenting the source-text-grep boundary test pattern in `docs/engineering/TEST_ARCHITECTURE.md` next time it's touched (LTO-4 work).
