---
author: codex
phase: phase65
slice: implementation-summary
status: final
depends_on: ["docs/plans/phase65/kickoff.md", "docs/plans/phase65/design_decision.md", "docs/plans/phase65/risk_assessment.md", "docs/plans/phase65/consistency_report.md", "docs/plans/phase65/review_comments.md", "docs/design/DATA_MODEL.md"]
---

TL;DR: Phase 65 implementation and review follow-up are complete. Route metadata and policy truth now persist in SQLite, route/policy governance writes run inside explicit `BEGIN IMMEDIATE` transactions with append-only audit logs, legacy JSON files are bootstrap-only backups, and review findings B-1/C-1/C-2/NOTE-1 have been addressed.

## Implementation Summary

- M1/S1: added SQLite schema for `route_registry`, `policy_records`, `route_change_log`, `policy_change_log`, `schema_version`; added `sqlite_store.get_connection(base_dir)` with `isolation_level=None`; moved route registry / route policy / weights / capability profile readers to SQLite with legacy JSON bootstrap and default seed fallback.
- M2/S2: moved route metadata writers and policy writers to SQLite while preserving public helper signatures; wrapped `RouteRepo._apply_metadata_change` and `PolicyRepo._apply_policy_change` in explicit transactions; added rollback redo for in-memory route registry state; wrote `route_change_log` / `policy_change_log` rows in the same transaction.
- M3/S3: extended append-only guard coverage from 4 to 6 tables; added `swl migrate --status`; synchronized `DATA_MODEL.md` §3.4 / §3.5 / §4.2 / §8; left `INVARIANTS.md` unchanged.

## Review Follow-up

- BLOCK-1: `_apply_route_review_metadata` now catches `OSError` from review record artifact writes after SQLite truth commit and logs a warning instead of surfacing a false governance-write failure.
- CONCERN-1: expanded `tests/test_phase65_sqlite_truth.py` from 8 to 21 tests, including route failure injection across registry / policy / weights / capability profile / audit / post-commit caller windows and policy failure injection across audit-trigger, MPS, after-payload, and audit-log windows.
- CONCERN-2: added a non-trivial route registry round-trip fixture with 3 routes and 5 task-family score entries per route; the test verifies SQLite round-trip and `route_change_log` JSON payload deserialization.
- NOTE-1: aligned `DATA_MODEL.md` §8 `schema_version.slug` DDL with implementation: `slug TEXT NOT NULL`.

Application artifact classification check:

- `rg "application_path|optimization_proposal_application_path" -n src tests docs/plans/phase65 docs/design/DATA_MODEL.md` shows the application artifact path is created/written in `governance.py`, returned by `meta_optimizer.apply_reviewed_optimization_proposals(...)` for audit/report callers, defined in `paths.py`, and asserted in tests. No runtime reader uses the application artifact as route/policy truth or as a decision input.

## Verification

- `.venv/bin/python -m pytest tests/test_phase65_sqlite_truth.py -q` -> `21 passed`
- `.venv/bin/python -m pytest tests/test_governance.py -q` -> `10 passed`
- `.venv/bin/python -m pytest tests/test_meta_optimizer.py -q` -> `19 passed`
- `.venv/bin/python -m pytest tests/test_cli.py -q` -> `241 passed, 10 subtests passed`
- `.venv/bin/python -m pytest tests/test_invariant_guards.py -q` -> `25 passed`
- `.venv/bin/python -m pytest -q` -> `610 passed, 8 deselected, 10 subtests passed`
- `.venv/bin/python tests/audit_no_skip_drift.py` -> all 8 tracked guards green
- `git diff --check` -> passed
- `git diff -- docs/design/INVARIANTS.md` -> no output

## Suggested Commit Split

1. `feat(phase65): persist route and policy truth in sqlite`
   - Code: `src/swallow/sqlite_store.py`, `src/swallow/router.py`, `src/swallow/truth/route.py`, `src/swallow/truth/policy.py`, `src/swallow/consistency_audit.py`, `src/swallow/mps_policy_store.py`, `src/swallow/governance.py`, `src/swallow/cli.py`
   - Tests: `tests/test_phase65_sqlite_truth.py`, route/policy/CLI/meta-optimizer fixture migrations, append-only guard expansion

2. `test(phase65): cover review follow-up transaction gaps`
   - Code/tests: `src/swallow/governance.py`, `tests/test_phase65_sqlite_truth.py`
   - Review follow-up: artifact write warning-only semantics, expanded failure injection coverage, non-trivial route round-trip fixture

3. `docs(design): align data model with phase65 sqlite truth`
   - Docs: `docs/design/DATA_MODEL.md`

4. `docs(state): mark phase65 review follow-up ready for review`
   - Docs: `docs/active_context.md`, `docs/plans/phase65/commit_summary.md`
