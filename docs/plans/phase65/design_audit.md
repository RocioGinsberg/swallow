---
author: claude/design-auditor
phase: phase65
slice: design-audit
status: final
depends_on:
  - docs/plans/phase65/kickoff.md
  - docs/plans/phase65/design_decision.md
  - docs/plans/phase65/risk_assessment.md
  - docs/plans/phase65/context_brief.md
  - docs/design/INVARIANTS.md
  - docs/design/DATA_MODEL.md
  - src/swallow/sqlite_store.py
  - src/swallow/router.py
  - src/swallow/truth/route.py
  - src/swallow/truth/policy.py
  - src/swallow/governance.py
  - tests/test_invariant_guards.py
---

TL;DR: NEEDS_REVISION_BEFORE_GATE — 3 slices audited, 9 issues found (2 BLOCKER, 4 CONCERN, 3 OK).

## Audit Verdict

Overall: NEEDS_REVISION_BEFORE_GATE

The two blockers are both in S2 and concern the Python `sqlite3` transaction API and the missing connection-access mechanism for `router.py` / `truth/` modules. Neither requires redesign — they need a one-paragraph design clarification that tells Codex exactly which API to use. The concerns are implementable with stated assumptions but will produce PR-time surprises if not addressed upfront.

---

## Issues by Slice

### Slice S1: Schema兑现 + Reader 切 SQLite + 一次性 Migration

**Focus 1 — DATA_MODEL §3.4 schema vs RouteSpec actual fields**

- [BLOCKER] The `route_registry` DDL in DATA_MODEL §3.4 covers `route_id`, `model_family`, `model_hint`, `dialect_hint`, `backend_kind`, `transport_kind`, `fallback_route_id`, `quality_weight`, `unsupported_task_types`, `cost_profile`, `updated_at`, `updated_by`. The actual routes.default.json entries (confirmed in code) carry: `name`, `capabilities` (nested dict with 6 sub-keys), `taxonomy` (nested dict with 2 sub-keys), `execution_site`, `executor_family`, `executor_name`, `remote_capable`, plus `task_family_scores` (stored in capability profiles, not registry). None of the nested dicts (`capabilities`, `taxonomy`) appear in §3.4 at all; `execution_site`, `executor_family`, `executor_name`, `remote_capable` are also absent. The design_decision §S1 says "若发现需调整先改 DATA_MODEL.md 再改代码" but does not resolve this gap — it defers to Codex's "sanity check PR body." This creates a loop: Codex cannot build the DDL without knowing whether these fields go into the main table (as individual columns), into a catch-all JSON blob, or into a new `capabilities`/`taxonomy` column. The design must answer this definitively before Codex starts, or at minimum must say "add a `raw_json TEXT NOT NULL` catch-all blob and store the whole route dict serialized, with the listed columns as materialized extracts." Without this, Codex either invents the schema or pauses to ask. Location: design_decision.md §S1 "关键设计决策" bullet 1; DATA_MODEL.md §3.4.

- [CONCERN] The `route_registry` table uses `route_id TEXT PRIMARY KEY` in DATA_MODEL §3.4, but the actual RouteSpec uses `name` as its identifier (`route.name`, e.g. "http-claude"). The `save_route_registry` function already uses the name as key in the JSON dict. Codex will need to decide: is `route_id == name`, or does `route_id` get a new ULID per phase 65 schema rule? If it is the name, the field should be documented as `route_id = route.name` (a human-readable stable key, not a ULID). If it is a ULID, a mapping table or column is needed. The design docs are silent. Location: DATA_MODEL.md §3.4; design_decision.md §S1.

- [CONCERN] The migration algorithm pseudocode (design_decision §S1) calls `_get_connection(base_dir)`. This function does not exist anywhere in the codebase. `sqlite_store.py` exposes `SqliteTaskStore()._connect(base_dir)` as an instance method. The pseudocode treats this as a module-level function. Codex needs to know whether (a) `router.py` should call `SqliteTaskStore()._connect(base_dir)` directly — which violates the intent of not having free modules call `_connect` — or (b) a new module-level helper should be introduced in `sqlite_store.py`, or (c) `router.py` should accept a connection argument injected from outside. Location: design_decision.md §S1 migration pseudocode.

**Focus 4 — JSON 字段空值表达**

- [CONCERN] The design_decision §S1 specifies `unsupported_task_types` and `cost_profile` stored as `TEXT NOT NULL` JSON strings in SQLite, but does not define the empty-value contract. `save_route_capability_profiles` in router.py normalizes `unsupported_task_types` to a sorted list and could legitimately produce `[]`; `cost_profile` is not present in the current RouteSpec dataclass at all (it appears only in DATA_MODEL §3.4 DDL). The design must specify: empty list stored as `'[]'`, not `''` or `NULL`, and missing optional fields stored as `'null'` or `'{}'`. Codex will need to make an assumption here. Location: design_decision.md §S1 DDL section.

**Focus 8 — test_only_apply_proposal_calls_private_writers guard**

- [OK] `test_only_apply_proposal_calls_private_writers` (test_invariant_guards.py:263) currently lists `save_route_registry`, `save_route_policy`, `save_route_weights`, `save_route_capability_profiles`, `save_audit_trigger_policy`, `save_mps_policy` as protected names; `allowed_files` includes `src/swallow/router.py` and `src/swallow/truth/route.py`. After S2, the `save_*` functions still live in `router.py` and are still called only from `truth/route.py`. The guard does not need changes as long as the function names are preserved. This is consistent with design intent and the "接口签名不变" constraint. No action needed.

---

### Slice S2: Writer 切 SQLite + 事务包裹 + 审计写入

**Focus 2 — 事务边界精确位置 + Python sqlite3 API**

- [BLOCKER] The design_decision pseudocode for `_apply_metadata_change` uses `conn.execute("BEGIN IMMEDIATE")` on a connection returned by `_get_connection(base_dir)`. Python's `sqlite3` module by default operates in implicit-transaction mode (`isolation_level=''`): when a DML statement (INSERT/UPDATE/DELETE) is issued, Python automatically opens a transaction. Issuing a raw `"BEGIN IMMEDIATE"` on a connection that already has an implicit transaction open raises `OperationalError: cannot start a transaction within a transaction`. This is confirmed by runtime testing against the Python version in this repo's environment. The current `_connect` does not set `isolation_level=None`. The design pseudocode will fail as written unless either (a) connections used for `_apply_metadata_change` are opened with `isolation_level=None` (autocommit mode, where you manage all transactions explicitly), or (b) the code calls `conn.commit()` or `conn.rollback()` first to close any pending implicit transaction before issuing `BEGIN IMMEDIATE`. The design document must specify which approach Codex should use, because the choice also affects every other write path on that connection object. Location: design_decision.md §S2 事务边界 pseudocode.

- [CONCERN] The design pseudocode for the ROLLBACK redo path calls `apply_route_registry(base_dir)`, `apply_route_policy(base_dir)`, `apply_route_weights(base_dir)`, `apply_route_capability_profiles(base_dir)` in sequence after `conn.execute("ROLLBACK")`. Each of these calls `load_route_*` internally, which in S2 reads from SQLite (S1 already landed by this point). However, `apply_route_weights` and `apply_route_capability_profiles` take an optional `registry` argument and default to the module-level `ROUTE_REGISTRY`. The full 4-call redo sequence correctly restores all in-memory state only if `apply_route_registry` is called first (it replaces `ROUTE_REGISTRY` content via `.replace()`), which is the existing 5-entry load ordering. The design does not explicitly state that the redo calls must follow this same ordering — it lists them in any order. Codex should be told: redo ordering must match the established `apply_route_registry → apply_route_policy → apply_route_weights → apply_route_capability_profiles` sequence (skipping `apply_route_fallbacks`, which is operator-local and not written by the transaction). Location: design_decision.md §S2 ROLLBACK redo pseudocode.

- [CONCERN] The design says `_apply_policy_change` gets the same `BEGIN IMMEDIATE` event transaction treatment as `_apply_metadata_change`. However, the current `PolicyRepo._apply_policy_change` (truth/policy.py:18-23) delegates immediately to either `save_audit_trigger_policy` or `save_mps_policy` — both of which are defined in `consistency_audit.py` and `mps_policy_store.py` respectively, not in `router.py`. These two functions are not listed in the design's S2 scope for "改为 SQL UPSERT". The design makes no mention of where the SQLite-backed versions of `save_audit_trigger_policy` / `save_mps_policy` will live, what the `policy_records` table row schema looks like for audit_trigger vs mps kinds, or how they map to the `policy_records.kind` / `payload` columns in DATA_MODEL §3.5. There is a parallel schema gap here to the one described for `route_registry`: DATA_MODEL §3.5 has `kind TEXT NOT NULL` and `scope TEXT NOT NULL`, but the actual policy data structures (`AuditTriggerPolicy` model and `mps_kind`/`mps_value`) need an explicit column-to-field mapping before Codex can write the UPSERT. Location: design_decision.md §S2 影响范围 / DATA_MODEL.md §3.5.

**Focus 5 — 审计 snapshot 完整性 + 大小**

- [CONCERN] The design recommends full-table snapshot for `before_payload` / `after_payload` and notes capability_profiles can be a large dict. It does not set any size constraint or truncation policy. More concretely: `_apply_route_review_metadata` can process dozens of approved entries across multiple routes, each with `task_family_scores` dicts. If the capability_profiles snapshot is stored twice (before + after) for every `apply_proposal` call that touches review metadata, the audit row could be hundreds of KB. The design should either (a) confirm this is accepted and no cap is needed in Phase 65, or (b) define a max-size threshold and a "oversized_snapshot_omitted" marker. Without this guidance, Codex will have to make an unconstrained choice. Location: design_decision.md §S2 before/after snapshot 实装 bullet.

- [CONCERN] The `action` column in `route_change_log` / `policy_change_log` is defined as `TEXT NOT NULL` with values `upsert | delete`. The migration path (from S1) also writes a row with `actor='migration'`. The design says "migration 也是一次变更" but the action enum is not extended to include `init` or `migrate`. If the test guard `test_append_only_tables_reject_update_and_delete` builds INSERT fixtures for these tables using only `upsert`/`delete` as valid action values, there will be no fixture validation that the migration path produces valid rows. This is an edge case but Codex would need to know whether `action='migration'` is a valid value or whether `action='upsert'` should be used for migration rows too. Location: design_decision.md §S1 migration pseudocode + §S2 审计表 DDL.

**Focus 6 — in-memory ROUTE_REGISTRY ROLLBACK redo 副作用**

- [OK] The design addresses the in-memory mutation problem via "ROLLBACK + full re-read from SQLite" redo. The `apply_route_*` helpers (confirmed in router.py) are idempotent: `apply_route_registry` calls `ROUTE_REGISTRY.replace()` which reinitializes `_routes` dict; `apply_route_weights` iterates and sets each route's `quality_weight`; `apply_route_capability_profiles` sets `task_family_scores` and `unsupported_task_types`. None of these helpers fire listener callbacks or mutate external state beyond the module-level registry. The redo path is thus side-effect free in the relevant sense. The design's risk_assessment R1 adequately covers this risk. No additional gap.

---

### Slice S3: §9 守卫扩展 + Migration 协议落地 + DATA_MODEL.md 同步

**Focus 7 — schema_version 协议落地最小可执行集**

- [CONCERN] The design_decision §S3 specifies that `EXPECTED_SCHEMA_VERSION` is a constant used at startup to detect schema drift but does not say where this constant lives. The existing codebase has no `schema_version` table and no migration infrastructure. Codex needs to know: (a) which module owns `EXPECTED_SCHEMA_VERSION` — `sqlite_store.py` seems natural but the design doesn't say; (b) whether the migration execution loop is in `sqlite_store.py:_connect`, in a new `migrations.py`, or elsewhere; (c) the `swl migrate` CLI exit codes — `0` for success, non-zero for failure, but what exit code for "already up to date" (0 or a distinct value)? The design says "失败提示" but gives no structured failure behavior. Additionally, DATA_MODEL §8 states "Migration 不允许在运行时静默执行; `swl` 启动时检测 schema 落后会进入 `waiting_human`" — but the design_decision §S3 says "开发模式默认自动 migrate". This is a direct conflict with DATA_MODEL §8's "不允许在运行时静默执行" rule. Codex cannot resolve this conflict without a design ruling. Location: design_decision.md §S3 启动时 schema 检测 bullet; DATA_MODEL.md §8.

**Focus 8 — 测试 fixture 迁移清单**

- [OK] The risk_assessment R6 and context_brief adequately identify the specific test lines (`test_router.py:242, 265`) and explain the required triage: path-name assertions (`.swl/routes.json`) need to become SQLite row-existence assertions; tests that call `save_*` via helper will follow automatically. The design correctly notes that `test_only_apply_proposal_calls_private_writers`'s protected function list does not need to change because the `save_*` function names are preserved. The fixture migration guidance is sufficient for Codex to proceed without further clarification.

**Focus 9 — scope necessity / non-goals**

- [OK] The `swl migrate` CLI and `schema_version` detection are correctly scoped into M3 (not M1/M2). The review record artifact write outside the transaction is correctly declared as "已知不完美 + 不修复" with a backlog note. The Phase 61 "事务回滚" Open closure evidence is adequately specified: the S2 regression test (monkeypatch to fail mid-transaction + verify SQLite ROLLBACK + in-memory redo) is the concrete closure artifact, and the backlog is to be marked Resolved in closeout.md. These decisions are defensible and the scope lines are clear.

---

## Questions for Claude

1. **S1 / DATA_MODEL §3.4 schema gap (BLOCKER)**: The actual RouteSpec serialization includes `capabilities` (nested dict), `taxonomy` (nested dict), `execution_site`, `executor_family`, `executor_name`, `remote_capable` — none of which appear in the DATA_MODEL §3.4 DDL. Before Codex can build the DDL and UPSERT, the design must answer: are these fields stored as individual columns (requiring DATA_MODEL §3.4 to be updated with new columns), or is there a catch-all `raw_json TEXT NOT NULL` blob column, or are `capabilities` and `taxonomy` stored as separate JSON TEXT columns named explicitly? The design's instruction to "先改 DATA_MODEL.md 再改代码" is correct but the design itself must provide the ruling on which approach is allowed, not leave it to the S1 PR body.

2. **S2 / Python sqlite3 transaction API (BLOCKER)**: The `BEGIN IMMEDIATE` pseudocode will fail unless connections are opened with `isolation_level=None` or the implicit transaction is committed before `BEGIN IMMEDIATE` is issued. The design must specify: (a) should `_connect` (or a new variant used by Repository write paths) set `isolation_level=None`? (b) if yes, does this affect existing write paths that use `with self._connect(base_dir) as connection:` (the context manager on a `isolation_level=None` connection does NOT auto-commit on exit — it becomes a no-op)? This requires an explicit ruling so Codex doesn't accidentally break existing write paths.

3. **S1 / `_get_connection` access pattern**: The pseudocode calls `_get_connection(base_dir)` which doesn't exist. Should Codex introduce a module-level `_get_route_connection(base_dir) -> sqlite3.Connection` function in `sqlite_store.py` (analogous to `SqliteTaskStore()._connect` but module-scoped), or should `router.py` and `truth/route.py` instantiate `SqliteTaskStore()` and call `._connect`? The choice has implications for the test guard `test_only_apply_proposal_calls_private_writers` (does accessing `_connect` from `router.py` count as a violation?) and for mocking in tests.

4. **S2 / PolicyRepo schema for `policy_records` (CONCERN, blocks S2)**: The `policy_records` table (DATA_MODEL §3.5) has `kind`, `scope`, `scope_value`, `payload`. The actual `_apply_policy_change` receives either an `AuditTriggerPolicy` object or `(mps_kind, mps_value)`. What is the `kind` column value for each? What is `scope`? What goes in `payload`? The design must provide the mapping table (even a 2-row table) before Codex can write the UPSERT.

5. **S3 / DATA_MODEL §8 conflict with auto-migrate in dev mode**: DATA_MODEL §8 says "Migration 不允许在运行时静默执行" (explicit mandate), but design_decision §S3 says "开发模式默认自动 migrate". This is a direct contradiction. The ruling should clarify whether Phase 65 is explicitly carving out an exception to DATA_MODEL §8's rule, or whether the "自动 migrate" only applies to first-time schema creation (which is arguably not a "migration" in the breaking-change sense but a fresh install). If it is an exception, it should be called out in the DATA_MODEL §8 update that S3 commits.

6. **S2 / `action` enum for migration rows in audit log**: The `route_change_log.action` column is defined with values `upsert | delete`. The S1 migration path writes rows with `actor='migration'`. Should those rows use `action='upsert'` (since migration is bulk-inserting rows), or should a new value `action='migrate'` be added? This affects (a) the DDL comment, (b) the S3 fixture for `test_append_only_tables_reject_update_and_delete`, and (c) any future consumer that enumerates action values.

---

## Confirmed Ready

- S3 is largely ready pending resolution of the DATA_MODEL §8 conflict (Q5 above, which is a one-sentence ruling). The append-only guard extension, migration SQL file, and DATA_MODEL.md edits are mechanically clear and unambiguous.
- S1's reader fallback chain (SQLite → .swl/*.json → *.default.json), idempotency semantics, and multi-process safety (BEGIN IMMEDIATE mutex) are well-specified.
- S2's in-memory ROUTE_REGISTRY redo logic, audit write location, and the "review record artifact outside transaction" known-gap declaration are all clear.
