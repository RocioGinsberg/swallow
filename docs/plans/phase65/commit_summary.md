---
author: codex
phase: phase65
slice: implementation-summary
status: final
depends_on: ["docs/plans/phase65/kickoff.md", "docs/plans/phase65/design_decision.md", "docs/plans/phase65/risk_assessment.md", "docs/design/DATA_MODEL.md"]
---

TL;DR: Phase 65 implementation completed across M1/M2/M3. Route metadata and policy truth now persist in SQLite, route/policy governance writes run inside explicit `BEGIN IMMEDIATE` transactions with append-only audit logs, legacy JSON files are bootstrap-only backups, and tests/guards were updated for the new truth backend.

## Implementation Summary

- M1/S1: added SQLite schema for `route_registry`, `policy_records`, `route_change_log`, `policy_change_log`, `schema_version`; added `sqlite_store.get_connection(base_dir)` with `isolation_level=None`; moved route registry / route policy / weights / capability profile readers to SQLite with legacy JSON bootstrap and default seed fallback.
- M2/S2: moved route metadata writers and policy writers to SQLite while preserving public helper signatures; wrapped `RouteRepo._apply_metadata_change` and `PolicyRepo._apply_policy_change` in explicit transactions; added rollback redo for in-memory route registry state; wrote `route_change_log` / `policy_change_log` rows in the same transaction.
- M3/S3: extended append-only guard coverage from 4 to 6 tables; added `swl migrate --status`; synchronized `DATA_MODEL.md` §3.4 / §3.5 / §4.2 / §8; left `INVARIANTS.md` unchanged.

## Verification

- `.venv/bin/python -m pytest -q` -> `597 passed, 8 deselected, 10 subtests passed`
- `.venv/bin/python tests/audit_no_skip_drift.py` -> all 8 tracked guards green
- `git diff --check` -> passed
- `git diff -- docs/design/INVARIANTS.md` -> no output

## Suggested Commit Split

1. `feat(phase65): persist route and policy truth in sqlite`
   - Code: `src/swallow/sqlite_store.py`, `src/swallow/router.py`, `src/swallow/truth/route.py`, `src/swallow/truth/policy.py`, `src/swallow/consistency_audit.py`, `src/swallow/mps_policy_store.py`, `src/swallow/governance.py`, `src/swallow/cli.py`
   - Tests: `tests/test_phase65_sqlite_truth.py`, route/policy/CLI/meta-optimizer fixture migrations, append-only guard expansion

2. `docs(design): align data model with phase65 sqlite truth`
   - Docs: `docs/design/DATA_MODEL.md`

3. `docs(state): mark phase65 implementation ready for review`
   - Docs: `docs/active_context.md`, `docs/plans/phase65/commit_summary.md`
