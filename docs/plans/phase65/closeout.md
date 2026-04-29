---
author: codex
phase: phase65
slice: closeout
status: review
created_at: 2026-04-30
depends_on:
  - docs/plans/phase65/kickoff.md
  - docs/plans/phase65/design_decision.md
  - docs/plans/phase65/risk_assessment.md
  - docs/plans/phase65/design_audit.md
  - docs/plans/phase65/model_review.md
  - docs/plans/phase65/context_brief.md
  - docs/plans/phase65/commit_summary.md
  - docs/plans/phase65/consistency_report.md
  - docs/plans/phase65/review_comments.md
  - docs/design/INVARIANTS.md
  - docs/design/DATA_MODEL.md
---

TL;DR: Phase 65 is ready for PR / Human Merge Gate. Route and policy truth now persist in SQLite, governance writes run under explicit `BEGIN IMMEDIATE` transactions with append-only audit rows, legacy JSON is bootstrap-only, the review follow-up is resolved, and final verification is green.

# Phase 65 Closeout

## Conclusion

Phase 65 `Truth Plane SQLite Consistency` completed roadmap candidate H, the final segment of the Governance sequence G + G.5 + H.

The phase moved route metadata and policy truth from `.swl/*.json` files into SQLite-backed truth tables:

- `route_registry`
- `policy_records`
- `route_change_log`
- `policy_change_log`
- `schema_version`

The public route/policy helper signatures remain stable, but their backing storage is now SQLite. Legacy JSON files remain as bootstrap sources only:

1. SQLite truth if populated.
2. Legacy `.swl/*.json` if SQLite is empty.
3. Immutable default seeds if both are absent.

`route_fallbacks.json` remains the operator-local config seam and was intentionally not migrated.

`docs/design/INVARIANTS.md` is unchanged.

## Milestone Review

### M1/S1: Schema + Readers + Bootstrap

Implemented:

- Added route/policy truth schema in `sqlite_store.py`.
- Added `schema_version` initialization with `version=1`, `slug='phase65_initial'`.
- Added `sqlite_store.get_connection(base_dir)` using `isolation_level=None` for explicit transaction control.
- Moved route registry / route policy / route weights / capability profiles readers to SQLite.
- Added idempotent legacy JSON bootstrap helpers:
  - `_bootstrap_route_metadata_from_legacy_json`
  - `_bootstrap_route_policy_from_legacy_json`
  - `_bootstrap_audit_trigger_policy_from_legacy_json`
  - `_bootstrap_mps_policy_from_legacy_json`
- Kept bootstrap out of `route_change_log` / `policy_change_log` by design.

Validation:

- `test_phase65_schema_tables_and_schema_version_exist`
- `test_route_registry_reader_priority_is_sqlite_then_legacy_json_then_default`
- route/policy fixture migrations in CLI / governance / meta-optimizer tests

### M2/S2: SQLite Writers + Transactions + Audit

Implemented:

- Route metadata writers now UPSERT SQLite rows while preserving public signatures.
- Policy writers now UPSERT into `policy_records`.
- `RouteRepo._apply_metadata_change` wraps all route metadata writes in one `BEGIN IMMEDIATE` transaction.
- `PolicyRepo._apply_policy_change` wraps policy writes in explicit transactions.
- Route rollback redoes in-memory route registry state from SQLite.
- `route_change_log` and `policy_change_log` are written in the same transaction as the truth changes.

Review follow-up completed:

- Review artifact writes in `_apply_route_review_metadata` now catch `OSError` after SQLite commit and log a warning instead of surfacing a false governance write failure.
- Failure injection coverage now includes the full route/policy matrix required by the revised design.
- Non-trivial round-trip coverage uses 3 routes with 5 task-family scores each and verifies audit JSON payloads.

Validation:

- `tests/test_phase65_sqlite_truth.py` -> 21 passed.
- The transaction tests assert SQLite rollback, audit-log absence on rollback, and in-memory route registry recovery.

### M3/S3: Guards + Migration Status + DATA_MODEL Sync

Implemented:

- `APPEND_ONLY_TABLES` now covers 6 tables:
  - `event_log`
  - `event_telemetry`
  - `route_health`
  - `know_change_log`
  - `route_change_log`
  - `policy_change_log`
- `test_append_only_tables_reject_update_and_delete` covers all 6 append-only tables.
- Added `swl migrate --status`, reporting `schema_version: 1, pending: 0`.
- `DATA_MODEL.md` synced within approved Phase 65 boundaries:
  - §3.4 route schema columns for full RouteSpec round-trip.
  - §3.5 policy mapping and `policy_change_log`.
  - §4.2 append-only table list 4 -> 6.
  - §8 `schema_version` reference and `slug TEXT NOT NULL`.

Validation:

- `tests/test_invariant_guards.py` -> 25 passed.
- `tests/audit_no_skip_drift.py` -> all 8 tracked guards green.

## Review Follow-Up

Claude review progressed from `APPROVE_WITH_CONDITIONS` to `APPROVE`.

Resolved items:

- **BLOCK-1**: review record artifact write failure now logs warning only after SQLite truth commit.
- **CONCERN-1**: transaction failure injection matrix is covered.
- **CONCERN-2**: non-trivial route round-trip fixture is covered.
- **NOTE-1**: `DATA_MODEL.md` §8 `schema_version.slug` DDL now matches implementation.

No merge-blocking items remain in `review_comments.md`.

## Backlog Updates

Updated `docs/concerns_backlog.md`:

- Moved Phase 61 `apply_proposal` route metadata transaction rollback concern to Resolved by Phase 65.
- Added Phase 65 known gaps:
  - Review record application artifact is still written outside the SQLite transaction; failure is warning-only.
  - Audit snapshots have no explicit size cap or truncation policy; oversized payload rollback is intentional.
  - Full schema migration runner remains deferred beyond Phase 65; Phase 65 only establishes initial `schema_version` status.

Existing deferred item unchanged:

- Phase 63 `events` / `event_log` double-write divergence remains open and is outside Phase 65 scope.

## Final Verification

Targeted verification:

```bash
.venv/bin/python -m pytest tests/test_phase65_sqlite_truth.py -q
# 21 passed

.venv/bin/python -m pytest tests/test_governance.py -q
# 10 passed

.venv/bin/python -m pytest tests/test_meta_optimizer.py -q
# 19 passed

.venv/bin/python -m pytest tests/test_cli.py -q
# 241 passed, 10 subtests passed

.venv/bin/python -m pytest tests/test_invariant_guards.py -q
# 25 passed
```

Full verification:

```bash
.venv/bin/python -m pytest -q
# 610 passed, 8 deselected, 10 subtests passed

.venv/bin/python tests/audit_no_skip_drift.py
# all 8 tracked guards green

git diff --check
# passed

git diff -- docs/design/INVARIANTS.md
# no output
```

Claude follow-up review verification:

```bash
.venv/bin/python -m pytest tests/test_phase65_sqlite_truth.py tests/test_invariant_guards.py -q
# 46 passed
```

## Stop / Go

### Stop

Phase 65 should stop here. Continuing into a real v1 -> v2 migration runner, outbox semantics for review artifacts, audit snapshot truncation, durable proposal artifacts, or event-log backfill would expand beyond the approved Phase 65 scope.

### Go

Go to PR creation and Human Merge Gate:

- `review_comments.md` verdict is APPROVE.
- The initial BLOCK / CONCERN items have been resolved.
- `commit_summary.md`, `closeout.md`, `docs/concerns_backlog.md`, `docs/active_context.md`, and `pr.md` reflect the current state.
- `current_state.md` and `docs/roadmap.md` should wait until after merge.
- Per Direction Gate, Phase 65 merge enables the later `v1.4.0` tag decision for Governance G + G.5 + H.
