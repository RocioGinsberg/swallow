---
author: claude/consistency-checker
phase: phase65
slice: implementation-vs-design
status: review
depends_on:
  - docs/plans/phase65/design_decision.md
  - docs/plans/phase65/kickoff.md
  - docs/plans/phase65/risk_assessment.md
  - docs/plans/phase65/design_audit.md
  - docs/plans/phase65/model_review.md
  - docs/plans/phase65/commit_summary.md
  - docs/design/DATA_MODEL.md
  - docs/design/INVARIANTS.md
verdict: concerns
---

TL;DR: 12 consistent, 3 concerns, 1 not-covered — implementation is structurally sound; two CONCERN items have known gaps (CONCERN-2 partial injection matrix, CONCERN-7 non-trivial fixture shortfall), one slug discrepancy in design_decision pre-revision vs post-revision text is resolved by revised acceptance criteria.

## Consistency Report

### 检查范围
- 对比对象: `git diff main...feat/phase65-truth-plane-sqlite` (commits 1b934c4, 77991d3, 1f258a7, 6cc16ee)
- 设计文档: `docs/plans/phase65/design_decision.md` (revised-after-model-review) §S1/§S2/§S3 + BLOCK-1 through BLOCK-5 + 9 CONCERN 决议; `docs/design/DATA_MODEL.md`; `docs/design/INVARIANTS.md`

---

### 一致项

- [CONSISTENT] **BLOCK-1**: `sqlite_store.get_connection` 设置 `isolation_level=None` (sqlite_store.py:328); `RouteRepo._apply_metadata_change` 和 `PolicyRepo._apply_policy_change` 均以 `BEGIN IMMEDIATE` 开始事务、`COMMIT`/`ROLLBACK` 收尾 (truth/route.py:37,67,70; truth/policy.py:31,43,46,54,66,69); `SqliteTaskStore._connect` 不传 `isolation_level` 参数(sqlite_store.py:356—363),既有 task/event/knowledge 写路径不受影响。

- [CONSISTENT] **BLOCK-2**: `get_connection(base_dir: Path)` 在 `sqlite_store.py:312` 作为 module-level public helper 实装; router.py / truth/route.py / truth/policy.py / consistency_audit.py / mps_policy_store.py 均通过 `sqlite_store.get_connection(base_dir)` 取连接,无新增 `SqliteTaskStore()._connect` 直连。

- [CONSISTENT] **BLOCK-3**: `route_registry` DDL 含全 6 列 (sqlite_store.py:157-163): `capabilities_json TEXT NOT NULL DEFAULT '{}'`, `taxonomy_json TEXT NOT NULL DEFAULT '{}'`, `execution_site TEXT NOT NULL`, `executor_family TEXT NOT NULL`, `executor_name TEXT NOT NULL`, `remote_capable INTEGER NOT NULL DEFAULT 0`; `test_phase65_schema_tables_and_schema_version_exist` 验证 6 列均存在 (test_phase65_sqlite_truth.py:85-92); round-trip 测试覆盖 capabilities/taxonomy 字段 (test_phase65_sqlite_truth.py:96-107)。

- [CONSISTENT] **BLOCK-4**: `policy_records` 映射表实装如下 — `audit_trigger` policy: `kind='audit_trigger', scope='global', scope_value=NULL, policy_id='audit_trigger:global'` (consistency_audit.py:239-258); `mps` policy: `kind='mps', scope='mps_kind', scope_value=<mps_kind>, policy_id='mps:<mps_kind>'` (mps_policy_store.py:112-133); 反序列化失败均回退 default 不抛异常 (consistency_audit.py:192-198; mps_policy_store.py:63-75)。

- [CONSISTENT] **BLOCK-5**: migrations 目录不存在 (选项 A); `_connect` 路径通过 `_initialize_schema` → `_ensure_schema_version` 在首次建表后直接 `INSERT OR IGNORE INTO schema_version VALUES (1, ..., 'phase65_initial')` (sqlite_store.py:266-276); 无 migration runner; `test_migrate_status_reports_phase65_initial_schema` 验证输出 `schema_version: 1, pending: 0` (test_phase65_sqlite_truth.py:212-216)。

- [CONSISTENT] **CONCERN-4 命名分离**: router.py 中只存在 `_bootstrap_route_metadata_from_legacy_json` (line 820) 和 `_bootstrap_route_policy_from_legacy_json` (line 860),以及 consistency_audit.py 中的 `_bootstrap_audit_trigger_policy_from_legacy_json` 和 mps_policy_store.py 中的 `_bootstrap_mps_policy_from_legacy_json`; 无任何 `_migrate_route_metadata` / `_migrate_policy` 命名存在; `swl migrate` CLI 与 bootstrap 概念隔离。

- [CONSISTENT] **CONCERN-5 M1 不可单独 release**: 实装在单个 feature commit (`77991d3`) 中同时包含 M1+M2+M3 全部内容,未分拆独立 PR。

- [CONSISTENT] **CONCERN-6 bootstrap 不写 audit log**: `_bootstrap_route_metadata_from_legacy_json` (router.py:820-857)、`_bootstrap_route_policy_from_legacy_json` (router.py:860-879)、`_bootstrap_audit_trigger_policy_from_legacy_json` (consistency_audit.py)、`_bootstrap_mps_policy_from_legacy_json` (mps_policy_store.py) 均无 `route_change_log` / `policy_change_log` INSERT 调用。

- [CONSISTENT] **DATA_MODEL.md §3.4 修改边界**: 仅追加 6 列 + 空值约定说明(DATA_MODEL.md:221-237); 既有列 DDL 字段语义不动; 追加 route_change_log 表定义; 加 Phase 65 实装说明注。

- [CONSISTENT] **DATA_MODEL.md §3.5 修改边界**: 追加 policy_change_log 表定义; 加 Phase 65 round-trip 映射表(DATA_MODEL.md:295-306); route_selection policy 条目正确列入映射表。

- [CONSISTENT] **DATA_MODEL.md §4.2 表清单 4→6**: `event_log / event_telemetry / route_health / know_change_log / route_change_log / policy_change_log` 六张表(DATA_MODEL.md:336)。

- [CONSISTENT] **DATA_MODEL.md §8 既有文字不变 + 末尾 reference**: git diff 显示 §8 段唯一实质性文字改动为将 `description TEXT` 改为 `slug TEXT`(见"额外发现"第14项)加一行 reference; §8 既有三条规则文字保持不变; INVARIANTS.md 无任何改动(diff 行数为 0)。

- [CONSISTENT] **`test_append_only_tables_reject_update_and_delete` 扩展到 6 张表**: test_invariant_guards.py 新增 `route_change_log` 和 `policy_change_log` fixture + UPDATE/DELETE 拒绝反例,并断言 `set(APPEND_ONLY_TABLES) == set(insert_sql)`。

---

### 不一致项

- [INCONSISTENT] **CONCERN-2 失败注入测试矩阵不完整**
  - 来源: `docs/plans/phase65/design_decision.md:382-395` — "S2 PR 必须包含以下 monkeypatch 注入点的 regression test(每个独立 test case)": route 8 注入点 (1: UPSERT前抛错 / 2: route_registry UPSERT后 / 3: route_policy UPSERT后 / 4: route_weights UPSERT后 / 5: route_capability_profiles UPSERT后 / 6: apply_route_* in-memory mutation后 / 7: audit INSERT后commit前 / 8: commit成功后caller异常); policy 4 注入点 (audit_trigger UPSERT / mps_policy UPSERT / in-memory / audit)。
  - 当前状态: `test_phase65_sqlite_truth.py` 有 2 个注入测试: `test_route_metadata_transaction_rolls_back_sqlite_audit_and_in_memory` (注入点 5: save_route_capability_profiles) 和 `test_policy_transaction_rolls_back_policy_record_and_audit` (注入点: _write_policy_change_log)。共 2 个 case,覆盖 12 个要求中的 2 个。注入点 1/2/3/4/6/7/8 及 policy 注入点 1/2/4 未实现。
  - 期望状态: 设计要求 12 个独立 test case(route 8 + policy 4),文件名建议 `test_governance_phase65_transaction.py` 或 `test_truth_route_transaction.py`。
  - 建议: PR closeout 前补充缺失的 10 个注入 case,或在 closeout 文档中登记为 known gap,说明已有 2 个关键路径覆盖(commit成功 + ROLLBACK触发)。

- [INCONSISTENT] **CONCERN-3 review record artifact 显式归类 — 声明缺失**
  - 来源: `docs/plans/phase65/design_decision.md:399-403` — "任何 reader 不得把它当作 truth(Codex 在 PR body 中验证: grep `application_path` 的所有 read 调用,确认仅用于 audit/debug/报告生成); artifact 写失败仅 log warning,不影响 SQL truth"。
  - 当前状态: governance.py:577-578 中 `_write_json(application_path, ...)` 在 `RouteRepo()._apply_metadata_change(...)` 返回(即 SQL COMMIT 完成)之后执行,时序正确。但 `_write_json` 调用处无 try/except 包裹,若 filesystem 写失败会向上传播异常,不符合"仅 log warning 不影响 SQL truth"的 at-least-once 语义设计。PR body / commit_summary 中未见对 `application_path` 所有 read 调用的验证记录。
  - 期望状态: artifact 写失败应 log warning 并静默继续;PR body 含 `grep application_path` 验证说明。
  - 建议: governance.py:577-578 处加 try/except + logging.warning;closeout 文档中补充验证说明或登记 backlog Open。

- [INCONSISTENT] **CONCERN-7 audit snapshot 非 trivial 测试规格不达标**
  - 来源: `docs/plans/phase65/design_decision.md:408` — "S2 PR 必须含 non-trivial round-trip 测试: fixture 包含 ≥3 routes × 5+ task_family_scores entries 的 capability_profiles,验证 audit 行 JSON 完整可反序列化"。
  - 当前状态: `test_route_registry_round_trips_full_route_spec_through_sqlite` (test_phase65_sqlite_truth.py:96) 使用单个 route + 2个 task_family_scores (`review: 0.91, execution: 0.44`); 无 ≥3 routes × 5+ scores 的 fixture。
  - 期望状态: ≥3 routes 每条含 5+ task_family_scores 的 capability_profiles fixture,验证 audit 行 `before_payload` / `after_payload` 可反序列化为完整 dict。
  - 建议: 补充一个 non-trivial fixture test,或在 closeout 中登记为 known gap(风险: 超大 payload ROLLBACK 行为未验证)。

---

### 未覆盖项

- [NOT_COVERED] **schema_version DDL `slug TEXT NOT NULL` vs DATA_MODEL §8 `slug TEXT`**
  - 说明: design_decision.md:447-450 定义 `slug TEXT NOT NULL` (带 NOT NULL 约束); 实装 sqlite_store.py:206-210 定义 `slug TEXT NOT NULL`; DATA_MODEL §8 DDL 仍写 `slug TEXT`(无 NOT NULL)(DATA_MODEL.md:392)。DATA_MODEL §8 的 schema_version DDL 是 git diff 中从 `description TEXT` 改为 `slug TEXT` 时保留的旧约束形式。实装与 design_decision 一致,但 DATA_MODEL.md 的 DDL 定义与实装有细微差异(NOT NULL 缺失)。design_decision 已是 revised 权威文档,DATA_MODEL 文字仅为 reference,不影响实装正确性;但属于文档与代码未完全同步的状态。

---

## 额外发现

**14. scope 漂移检查**: 无超出设计范围的 scope 漂移。router.py 新增了 `_run_sqlite_write` helper 和多个 `_save_route_*_to_sqlite` / `_load_route_*_from_sqlite` 私有函数,均属于 BLOCK-2/BLOCK-3 的合理实装。`route_registry` DDL 6列与设计完全对齐,无超出。INVARIANTS.md 零修改。`route_fallbacks.json` 路径(`apply_route_fallbacks`)未触动,与 Phase 64 决议一致。`_apply_route_review_metadata` 业务逻辑仅新增 `proposal_id=proposal_id` 透传(governance.py:560),未重构业务逻辑。

**15. consistency_audit.py / mps_policy_store.py 改动**: 两文件的改动是 BLOCK-4 policy 映射的合理实装。consistency_audit.py 新增 `_bootstrap_audit_trigger_policy_from_legacy_json`、`_upsert_audit_trigger_policy`、`_run_policy_write` 等私有函数,实现 audit_trigger policy 的 SQLite 读写; mps_policy_store.py 同款实现 mps policy。两者均属于 Phase 65 design_decision §S1/§S2 预期改动范围内。`apply_atomic_text_updates` 调用已移除(consistency_audit.py diff:line -9),被 SQLite UPSERT 替代,符合 P2 truth 迁移目标。

**16. cli.py 改动**: 25行改动分两部分 — (a) `migrate --status` 子命令(cli.py:1451-1454, 3786-3790),调用 `get_schema_status` 输出 `schema_version: N, pending: N`,完全在 Phase 65 §S3 scope 内; (b) `route_bootstrap_writes_allowed` guard(cli.py:2353-2361),在 `migrate --dry-run` 和 `knowledge migrate --dry-run` 场景跳过 bootstrap,防止 dry-run 模式触发 SQLite 写入,属于合理防护,未引入 scope 外改动。

---

## 总体结论

实装在 BLOCK-1 至 BLOCK-5 全部核心约束上与设计一致。三个不一致项均为测试覆盖深度问题(CONCERN-2、CONCERN-7)和 artifact 写失败处理缺失(CONCERN-3),不影响 SQLite truth 路径的正确性。

**是否需要回到 design / Codex**: CONCERN-3 中 `_write_json` 异常传播问题需要 Codex 修补(governance.py:577-578 加 try/except);CONCERN-2 和 CONCERN-7 测试缺口可在 closeout 中登记 known gap,或补充后合并。BLOCK 项全部 consistent,PR 可进入 review 流程。
