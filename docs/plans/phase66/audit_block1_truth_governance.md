---
author: codex
phase: phase66
slice: audit-block1-truth-governance
status: final
depends_on:
  - docs/plans/phase66/kickoff.md
  - docs/plans/phase66/design_decision.md
  - docs/plans/phase66/risk_assessment.md
  - docs/plans/phase66/context_brief.md
  - docs/concerns_backlog.md
---

TL;DR: Block 1 audited 9 files / 2671 LOC with 3 findings: 0 high / 1 med / 2 low. No code, tests, or design docs were changed; known backlog items were skipped.

## Coverage

Audited files:

- `src/swallow/governance.py` — 638 LOC
- `src/swallow/sqlite_store.py` — 953 LOC
- `src/swallow/store.py` — 723 LOC
- `src/swallow/__init__.py` — 5 LOC
- `src/swallow/truth/__init__.py` — 14 LOC
- `src/swallow/truth/knowledge.py` — 67 LOC
- `src/swallow/truth/policy.py` — 123 LOC
- `src/swallow/truth/proposals.py` — 33 LOC
- `src/swallow/truth/route.py` — 115 LOC

Block total: 2671 LOC.

## Skip List Applied

Loaded the Phase 66 skip list from `design_decision.md` and `docs/concerns_backlog.md`: 13 pre-Phase-65 Open items plus 3 Phase-65 known gaps, 16 total.

Block-specific skipped items:

- Phase 61 / 63 durable proposal artifact lifecycle: `_PENDING_PROPOSALS` / `PendingProposalRepo` remains in-memory in `governance.py` and `truth/proposals.py`; already tracked, not counted.
- Phase 61 / 63 canonical path `librarian_side_effect` matrix drift: `OperatorSource` still includes `librarian_side_effect`; already tracked, not counted.
- Phase 63 M2-5: `_apply_route_review_metadata` remains long reconciliation logic in `governance.py`; already tracked, not counted.
- Phase 63 M3-1: `events` / `event_log` historical backfill remains open; schema/table presence in `sqlite_store.py` not counted.
- Phase 65 known gaps: review application artifact outside SQLite transaction, audit snapshot size policy absent, and full migration runner deferred; related code was skipped as already tracked.

`tests/` was not audited as a subject. It was used only as a callsite oracle for dead-code checks, per Phase 66 design.

## Method

- File inventory: `wc -l` for the 9 block files.
- Symbol inventory: `rg -n 'def |class |^[A-Z][A-Z0-9_]+\\s*='`.
- Dead-code check: two-pass grep per design, with `src/swallow/` as production callsite source and `tests/` as oracle only.
- Literal / helper checks: targeted `rg` for `json.loads`, `read_text`, `FileNotFoundError`, `BEGIN IMMEDIATE`, `COMMIT`, `ROLLBACK`, `sqlite3.connect`, `timeout`, and block-specific repository helper names.

## Finding Summary

| Severity | dead-code | hardcoded-literal | duplicate-helper | abstraction-opportunity | Total |
|---|---:|---:|---:|---:|---:|
| high | 0 | 0 | 0 | 0 | 0 |
| med | 0 | 0 | 1 | 0 | 1 |
| low | 0 | 1 | 0 | 1 | 2 |
| **Total** | **0** | **1** | **1** | **1** | **3** |

The count is inside the design expectation for block 1(3-8 findings).

## Findings

### [med][duplicate-helper] JSONL reader helper is duplicated in block 1 and repeats across later blocks

- **位置**:
  - `src/swallow/store.py:136-148`
  - `src/swallow/truth/knowledge.py:59-67`
- **判定依据**:
  - `rg -n 'def _load_json_lines|_load_json_lines\\(' src/swallow/store.py src/swallow/truth/knowledge.py src/swallow/orchestrator.py src/swallow/librarian_executor.py tests`
  - Production definitions exist in `store.py`, `truth/knowledge.py`, `orchestrator.py`, and `librarian_executor.py`.
  - The two block-1 definitions both implement path-exists guard, `read_text(...).splitlines()`, blank-line skip, `json.loads`, and list append. The block-1 overlap is 9+ similar lines; broader production overlap crosses into later Phase 66 blocks.
  - Test helpers with the same name also exist, but tests are not audit subjects and are not counted as additional production duplication.
- **建议处理**:
  - In a later cleanup phase, centralize production JSONL reading into one small helper, likely near the existing store / path IO helpers.
  - Preserve the stricter `isinstance(payload, dict)` behavior from `store.py` or make the validation explicit at callsites.
- **影响范围**:cross-block / cross-module.
- **关联**:none; not a duplicate of any current backlog Open item.

### [low][hardcoded-literal] SQLite timeout and busy-timeout values are repeated as raw numbers

- **位置**:
  - `src/swallow/sqlite_store.py:281`
  - `src/swallow/sqlite_store.py:327`
  - `src/swallow/sqlite_store.py:358`
  - `src/swallow/sqlite_store.py:367`
  - `src/swallow/sqlite_store.py:370`
  - `src/swallow/sqlite_store.py:377`
  - `src/swallow/sqlite_store.py:885`
- **判定依据**:
  - `rg -n 'timeout=5\\.0|busy_timeout = 5000' src/swallow/sqlite_store.py`
  - `timeout=5.0` is repeated across cached connection, normal connection, read-only immutable connection, checkpoint, and health-check paths.
  - `PRAGMA busy_timeout = 5000` appears in schema initialization and read-only connection setup.
  - Phase 66 hardcoded-literal rules count timeout seconds / threshold values as magic numbers when not named.
- **建议处理**:
  - In a later cleanup phase, introduce named constants such as `SQLITE_CONNECT_TIMEOUT_SECONDS = 5.0` and `SQLITE_BUSY_TIMEOUT_MS = 5000`.
  - Keep behavior unchanged; this is readability and consistency cleanup only.
- **影响范围**:single-file.
- **关联**:`(Phase 65 new code)` for the cached route/policy connection path. This is not the Phase 65 migration-runner known gap; it is only literal naming hygiene.

### [low][abstraction-opportunity] Phase 65 route/policy repository transaction envelopes repeat the same shape

- **位置**:
  - `src/swallow/truth/route.py:34-75`
  - `src/swallow/truth/policy.py:25-47`
  - `src/swallow/truth/policy.py:53-70`
- **判定依据**:
  - `rg -n 'BEGIN IMMEDIATE|COMMIT|ROLLBACK|get_connection\\(|_write_.*change_log|_policy_record_payload|route_metadata_snapshot' src/swallow/truth src/swallow/router.py`
  - The three repository write paths share the envelope: `get_connection(base_dir)`, capture before state, `BEGIN IMMEDIATE`, perform namespace write, capture after state, append audit log, `COMMIT`, `ROLLBACK` on exception.
  - The shared structure appears 3 times and clears the abstraction-opportunity threshold, but the route path has additional in-memory route registry redo after rollback.
- **建议处理**:
  - Mark design-needed rather than quick-win. A later cleanup phase can evaluate a tiny transaction/audit helper or context manager only if it preserves namespace clarity and route-specific rollback redo.
  - Do not collapse these paths mechanically; Phase 65 intentionally kept route and policy namespaces explicit.
- **影响范围**:single block / cross namespace.
- **关联**:`(Phase 65 new code)`; not counted as the Phase 65 audit snapshot size-policy known gap.

## Checked But Not Counted

- `PendingProposalRepo` and `_PENDING_PROPOSALS` are known durable proposal lifecycle debt and were skipped.
- `_apply_route_review_metadata` remains long, but the exact readability concern is already tracked as Phase 63 M2-5.
- `events` / `event_log` schema coexistence was skipped because historical backfill is already tracked as Phase 63 M3-1.
- `__init__.py` and `truth/__init__.py` only expose metadata / public exports and produced no finding.
