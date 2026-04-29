---
author: claude
phase: phase65
slice: design-decomposition
status: revised-after-model-review
depends_on: ["docs/plans/phase65/kickoff.md", "docs/plans/phase65/context_brief.md", "docs/plans/phase65/design_audit.md", "docs/plans/phase65/model_review.md", "docs/plans/phase64/closeout.md", "docs/plans/phase63/closeout.md", "docs/design/INVARIANTS.md", "docs/design/DATA_MODEL.md", "docs/roadmap.md", "src/swallow/sqlite_store.py", "src/swallow/router.py", "src/swallow/governance.py", "src/swallow/truth/route.py", "src/swallow/truth/policy.py"]
---

TL;DR(revised-after-model-review,2026-04-29): **3 milestone / 3 slice**(M1 schema + reader + **legacy bootstrap import** / M2 writer + 事务 + 审计 / M3 守卫扩展 + DATA_MODEL 同步)。**S1**:`route_registry` / `policy_records` / `route_change_log` / `policy_change_log` 4 张新表(DATA_MODEL §3.4 加列以承载完整 RouteSpec,见下方 §S1 schema 决议);reader 改从 SQLite 加载,SQLite 表空 + 既有 JSON 存在时一次性 **bootstrap import**(明确区别于 §8 schema migration);writer 仍 JSON(基线安全)。**S2**:writer 切 SQLite UPSERT + `RouteRepo._apply_metadata_change` / `PolicyRepo._apply_policy_change` 整体 `BEGIN IMMEDIATE` 事务包裹(connection 通过 `sqlite_store.get_connection(base_dir)` 新 module-level accessor 取得;`isolation_level=None` 显式管理事务);Repository 层事务内写 `route_change_log` / `policy_change_log` 审计行。**S3**:`test_append_only_tables_reject_update_and_delete` 6 张表;`swallow/migrations/<version>.sql` 协议 + `schema_version` 检测(**首次建表不算 §8 migration**,符合 DATA_MODEL §8 文字);DATA_MODEL.md §3.4 加 6 列(capabilities_json / taxonomy_json / execution_site / executor_family / executor_name / remote_capable)+ §3.5 实装标注 + §4.2 表清单 4→6 + §8 protocol-landing 标注。INVARIANTS.md 文字不动。

## Revision Index(2026-04-29 model_review 后修订)

本文件在原 draft 基础上吸收 `design_audit.md`(2 BLOCKER + 4 CONCERN)与 `model_review.md`(5 BLOCK + 9 CONCERN)结论,Human 已确认两条关键路径决议:

- **BLOCK-5 §8 矛盾**:采纳路径 (i) — Phase 65 收紧:首次建表不算 §8 migration;dev-mode auto-apply 仅限 fresh empty DB;§8 文字不动
- **BLOCK-3 §3.4 字段缺口**:采纳路径 (a) — DATA_MODEL §3.4 加 6 个独立列承载完整 RouteSpec(`capabilities_json` / `taxonomy_json` / `execution_site` / `executor_family` / `executor_name` / `remote_capable`)

修订点定位:
- §S1 关键设计决策:补 `route_registry` 列扩展决议(BLOCK-3);补 connection accessor 决议(BLOCK-2);命名分离 `_bootstrap_route_metadata` 而非 `_migrate_*`(CONCERN-4);bootstrap 不写 audit log(CONCERN-6)
- §S2 关键设计决策:补 SQLite isolation_level + connection 共享决议(BLOCK-1);补 `policy_records` round-trip 映射表(BLOCK-4);补 ROLLBACK 后 redo 时序约束(CONCERN-1);补失败注入测试矩阵(CONCERN-2);补 review record artifact 显式归类(CONCERN-3)
- §S3 关键设计决策:补"首次建表不算 §8 migration"narrowing(BLOCK-5);DATA_MODEL §3.4 修改边界放宽至加列(BLOCK-3);保持 §8 文字不动
- §验收条件 / 全文件:吸收 GPT-5 missing acceptance criteria 清单,一并并入各 slice 验收

## 方案总述

Phase 65 是治理三段(G + G.5 + H)的最后一段,实质内容是把 truth plane 中 route metadata / policy 从 JSON 文件 + 进程内 dict 迁入 SQLite,履行 INVARIANTS P2(SQLite-primary truth)。Phase 63 引入的 Repository 抽象层骨架是本 phase 的天然实装载体:每个 Repository 私有 write method 内部从 JSON 写改为 SQL UPSERT,事务包裹在 method 最外层,接口契约不变。

**为什么拆 3 个 slice 而非合并**:
- S1(reader 切 SQLite,writer 仍 JSON):**双写一段时间** = 安全过渡。Reader 优先 SQLite,SQLite 为空 fallback 到 JSON;writer 仍 JSON 维持基线行为。这让"一次性 migration"在 M1 内可独立验证,不与 writer 切换混合
- S2(writer 切 SQLite + 事务):**唯一高风险 slice**。事务边界设计 + 审计写入位置 = Phase 65 的核心正确性保证;独立 review
- S3(守卫 + migration 工具 + DATA_MODEL.md):**收尾 slice**。守卫扩展是机械补充;migration 协议是 §8 兑现;DATA_MODEL.md 同步是文档对齐

**等价性保证**:
- M1 后 reader 行为对 caller 不可观察(无论 SQLite 还是 JSON 加载,返回的 dict / RouteSpec 一样)
- M2 后 writer 行为对外可观察的语义零变化(`apply_proposal(..., ROUTE_METADATA)` 接口不变,`save_route_*` 函数签名不变),只是底层 storage 与原子保证升级
- M3 是文档 / 守卫 / 工具,无运行时行为变化

## Slice 拆解

### S1 — Schema 兑现 + Reader 切 SQLite + 一次性 Migration(M1 单独 review)

**目标**:
- 在 SQLite 中建立 4 张新表(route_registry / policy_records / route_change_log / policy_change_log)
- Reader 改从 SQLite 加载;SQLite 表空 + 既有 `.swl/*.json` 存在时一次性 migrate
- Writer 保持 JSON(下一 milestone 切)
- 守卫不动(M3 内补)

**影响范围**:
- 改动:`src/swallow/sqlite_store.py:_connect`(line 191-218 周围)— 新增 4 表 DDL + 对应 trigger SQL;`APPEND_ONLY_TABLES` tuple 从 4 → 6
- 新增:`src/swallow/sqlite_store.py` — `route_registry` / `policy_records` 主表 DDL(对齐 DATA_MODEL §3.4 / §3.5);`route_change_log` / `policy_change_log` append-only 审计表 DDL
- 改动:`src/swallow/router.py` — `load_route_registry` / `load_route_policy` / `load_route_weights` / `load_route_capability_profiles` 4 个 reader 改实装层:**先查 SQLite,SQLite 空则 fallback 加载 .swl/*.json,继续空则 fallback default seed**(routes.default.json / route_policy.default.json)
- 新增:`src/swallow/router.py` — `_migrate_route_metadata_to_sqlite(base_dir)` / `_migrate_policy_to_sqlite(base_dir)` 一次性 migration helper(idempotent:若 SQLite 已有数据,跳过)
- 改动:`src/swallow/router.py:apply_route_*` helper — 在 reader 路径前调用 `_migrate_*` helper(idempotent,migration 完成后 reader 直接读 SQLite)
- **不动**:`save_route_*` writer(继续写 JSON,M2 内切)
- **不动**:`apply_route_fallbacks` / `route_fallbacks_path`(operator-local config seam,Phase 64 决议;不迁 SQLite)

**关键设计决策**:

- **Schema 严格对齐 DATA_MODEL §3.4 / §3.5**:Codex 实装前 sanity check 字段名 / 类型;若发现需调整(如 Phase 64 引入的字段在 §3.4 中未列),**先改 DATA_MODEL.md 再改代码**(per DATA_MODEL.md 顶部"先改文档"原则)。本 phase scope 内允许的 DATA_MODEL 修改:补字段 + §4.2 表清单 + §8 migration 协议;**不重写既有 DDL 语义**

- **`route_registry` 表的 `unsupported_task_types` / `cost_profile` 字段**:DATA_MODEL §3.4 用 `JSON` 类型(SQLite 原生不支持,实装层用 `TEXT NOT NULL` 存 JSON 字符串)。Codex 实装时按 SQLite 习惯用 TEXT + 应用层序列化

- **`route_change_log` / `policy_change_log` schema(authoritative,Codex 严格对齐)**:
  ```sql
  CREATE TABLE route_change_log (
      change_id      TEXT PRIMARY KEY,
      proposal_id    TEXT,                     -- 可空,backfill / migration 时为 null
      target_kind    TEXT NOT NULL,            -- registry | policy | weights | capability_profiles
      target_id      TEXT,                     -- 主表 PK 引用(如 route_id)
      action         TEXT NOT NULL,            -- upsert | delete
      before_payload TEXT,                     -- JSON,变更前快照
      after_payload  TEXT,                     -- JSON,变更后快照
      timestamp      TEXT NOT NULL,
      actor          TEXT NOT NULL DEFAULT 'local'
  );

  CREATE TABLE policy_change_log (
      change_id      TEXT PRIMARY KEY,
      proposal_id    TEXT,
      target_kind    TEXT NOT NULL,            -- audit_trigger_policy | mps_policy
      target_id      TEXT,
      action         TEXT NOT NULL,
      before_payload TEXT,
      after_payload  TEXT,
      timestamp      TEXT NOT NULL,
      actor          TEXT NOT NULL DEFAULT 'local'
  );
  ```

- **一次性 migration 算法**(authoritative):
  ```python
  def _migrate_route_metadata_to_sqlite(base_dir: Path) -> None:
      conn = _get_connection(base_dir)
      # idempotent: 若 SQLite 已有数据,跳过
      if conn.execute("SELECT COUNT(*) FROM route_registry").fetchone()[0] > 0:
          return
      # 从 .swl/routes.json 加载,无则从 routes.default.json
      registry_path = route_registry_path(base_dir)  # .swl/routes.json
      if registry_path.exists():
          payload = json.loads(registry_path.read_text(...))
      else:
          default_path = Path(__file__).parent / "routes.default.json"
          payload = json.loads(default_path.read_text(...))
      # SQL UPSERT
      for route_dict in payload:
          conn.execute("INSERT OR REPLACE INTO route_registry (...) VALUES (...)", (...))
      conn.commit()
      # 审计:本次 migration 也是一次"变更",写 route_change_log
      # 但 migration 不走 apply_proposal,审计行用 actor='migration', proposal_id=null
  ```

- **Reader fallback 优先级**(authoritative):
  1. SQLite `route_registry` / `policy_records` / etc(P2 truth)
  2. `.swl/*.json`(Phase 64 三层外部化 working copy,migrate 后保留作 backup)
  3. `*.default.json`(Phase 64 immutable seed)

- **Migration 时序**:`apply_route_*` helper 第一行调 `_migrate_*` helper(idempotent);后续 read 直接走 SQLite。这保证 reader 第一次访问时 migration 已完成

- **Writer 暂不动**:`save_route_*` 仍写 `.swl/*.json`(M2 内切)。M1 期间 SQLite 与 JSON **双写**:`apply_proposal` 触发 `save_*` → 写 JSON → `apply_*` 刷新 in-memory ROUTE_REGISTRY;但下次 reader 触发时 migration 已完成,SQLite 已有数据,**reader 不会重新跑 migration**(idempotent),所以 reader 读到的是 **migration 时刻的快照**,而非最新 JSON 写入。**这是 M1 的已知限制**:M1 期间 writer 写入只对当前进程 in-memory ROUTE_REGISTRY 有效,新进程启动会读 SQLite 旧快照。M2 切 writer 后此限制消除

- **守卫不动**:M1 不扩展 §9 守卫(M3 内做);`test_append_only_tables_reject_update_and_delete` 暂时仍只测 4 张表,新建的 `route_change_log` / `policy_change_log` 在 M3 加入

### S1 修订决议(2026-04-29 model_review 后)

**[BLOCK-3 解决] `route_registry` 表 schema 列扩展(authoritative)**

DATA_MODEL §3.4 在 Phase 65 内**允许加 6 个独立列**(范围限定:加列 + index,不动既有 DDL 字段语义):

```sql
CREATE TABLE route_registry (
    -- 原 §3.4 字段(不动)
    route_id              TEXT PRIMARY KEY,
    model_family          TEXT NOT NULL,
    model_hint            TEXT NOT NULL,
    dialect_hint          TEXT,
    backend_kind          TEXT NOT NULL,
    transport_kind        TEXT,
    fallback_route_id     TEXT,
    quality_weight        REAL NOT NULL DEFAULT 1.0,
    unsupported_task_types TEXT NOT NULL DEFAULT '[]',  -- JSON 字符串(SQLite 无原生 JSON,统一 TEXT NOT NULL)
    cost_profile          TEXT NOT NULL DEFAULT 'null', -- JSON 字符串
    updated_at            TEXT NOT NULL,
    updated_by            TEXT NOT NULL,
    -- Phase 65 加列(承载完整 RouteSpec round-trip)
    capabilities_json     TEXT NOT NULL DEFAULT '{}',   -- nested dict(6 子字段),JSON 序列化
    taxonomy_json         TEXT NOT NULL DEFAULT '{}',   -- nested dict(2 子字段:role / memory_authority)
    execution_site        TEXT NOT NULL,                -- local | remote(枚举)
    executor_family       TEXT NOT NULL,
    executor_name         TEXT NOT NULL,
    remote_capable        INTEGER NOT NULL DEFAULT 0    -- BOOL(SQLite 习惯用 INTEGER)
);
```

- `route_id` = `RouteSpec.name`(human-readable stable key,Phase 65 不引入独立 ULID;Phase 64 之前 JSON 已用 name 作 key,保持兼容)
- 既有 `unsupported_task_types` / `cost_profile` 字段类型在 §3.4 标 `JSON`(SQLite 无原生支持)→ 实装层用 `TEXT NOT NULL DEFAULT '[]'` / `TEXT NOT NULL DEFAULT 'null'`(空值约定:空 list 用 `'[]'`,缺失用 `'null'`,不允许 SQL NULL 或空字符串)
- DATA_MODEL §3.4 修改边界(M3 同步):**追加 6 列说明 + 空值约定**;不重写既有字段语义

**[BLOCK-2 解决] Connection access pattern(authoritative)**

在 `sqlite_store.py` 引入 module-level helper:

```python
# src/swallow/sqlite_store.py
def get_connection(base_dir: Path) -> sqlite3.Connection:
    """
    Return a SQLite connection for the given base_dir.
    Used by RouteRepo / PolicyRepo / migration / bootstrap helpers.
    Caller is responsible for transaction lifecycle (BEGIN / COMMIT / ROLLBACK).

    Implementation note: returns the same connection per (base_dir) within
    a process for transaction continuity (4 save+apply pairs + audit insert
    must share connection). Internal cache keyed by canonicalized base_dir.
    """
    ...
```

- 选项排除:不让 `router.py` 直连 `SqliteTaskStore()._connect`(违反 Repository 层封装);不通过依赖注入(scope creep,改动调用方过多)
- 守卫影响:`test_only_apply_proposal_calls_private_writers` **不变**(被守护的是 `save_route_*` / `save_*_policy` 函数名,不是 connection accessor);`get_connection` 是 module-level public helper,被允许在 `router.py` / `truth/*.py` 调用
- mock 模式:测试可继续 `monkeypatch.setattr("swallow.sqlite_store.get_connection", lambda base_dir: fake_conn)`,与现有 mock 模式同款

**[CONCERN-4 解决] 命名分离 — M1 是 bootstrap,不是 migration**

为避免与 §8 schema migration 概念耦合,M1 的"一次性 JSON 导入"helper 命名:

| 旧命名(draft) | 修订命名 | 语义 |
|---|---|---|
| `_migrate_route_metadata_to_sqlite` | `_bootstrap_route_metadata_from_legacy_json` | M1 一次性 legacy data import / 首次建表数据填充 |
| `_migrate_policy_to_sqlite` | `_bootstrap_policy_from_legacy_json` | 同款 |

`swl migrate` CLI(M3)仅指 schema_version 升级。Phase 65 内 M1 的"bootstrap"与 M3 的"migrate"是两个独立概念,不混用。

**[CONCERN-6 解决] M1 bootstrap 不写 audit log**

bootstrap 路径**不**向 `route_change_log` / `policy_change_log` 写入。理由:

- audit history 应从真正的 governance 写入(M2 起)开始记录;bootstrap 是 legacy data 转储,不属于 operator action
- `action` enum 保持 `upsert | delete` 两值,不需扩展 `bootstrap` / `migrate`(避免守卫 fixture 复杂化)
- closeout 文档显式记录:`route_change_log` 第一行的 `timestamp` 即 M2 commit 后第一次 governance 写入的时刻

**bootstrap 完成的 idempotency 标识** = `SELECT COUNT(*) FROM route_registry > 0`(M2 后第一次 apply_proposal 写入也会让计数 > 0;但 bootstrap 在 M1 期间走的路径不重复触发,即使 reader 在 M2 后第一次启动只看到非空表也直接走 SQLite read,不再 bootstrap)

**修订后的 bootstrap 算法**(authoritative):

```python
def _bootstrap_route_metadata_from_legacy_json(base_dir: Path) -> None:
    """
    One-shot legacy JSON → SQLite import. Idempotent.
    Phase 65 only; not a §8 schema migration.
    Audit log is NOT written.
    """
    conn = get_connection(base_dir)
    # idempotent guard
    if conn.execute("SELECT COUNT(*) FROM route_registry").fetchone()[0] > 0:
        return
    # BEGIN IMMEDIATE wraps entire bootstrap (multi-process mutex)
    conn.execute("BEGIN IMMEDIATE")
    try:
        # 优先 .swl/routes.json(operator working copy);否则 routes.default.json
        registry_path = route_registry_path(base_dir)
        payload = (
            json.loads(registry_path.read_text(...))
            if registry_path.exists()
            else json.loads((Path(__file__).parent / "routes.default.json").read_text(...))
        )
        for name, route_dict in payload.items():
            conn.execute(
                "INSERT OR REPLACE INTO route_registry (route_id, ..., capabilities_json, taxonomy_json, ...) VALUES (...)",
                (name, ..., json.dumps(route_dict.get("capabilities", {}), ...))
            )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    # 不写 audit log
```

policy bootstrap 同款。

**验收条件**:
- `sqlite_store.py:_connect` 在初始化路径上建 `route_registry` / `policy_records` / `route_change_log` / `policy_change_log` 4 张表
- `APPEND_ONLY_TABLES` 含 6 张表
- `load_route_*` reader 优先从 SQLite 读;SQLite 空 fallback JSON
- 一次性 migration 跑成功后 SQLite 表非空,reader 后续直读 SQLite
- 既有 `.swl/*.json` 在 migration 后保留(不删)
- 全量 pytest 通过(M1 不应破坏既有测试,即使 writer 仍 JSON)

**风险评级**:影响范围 2 / 可逆性 1 / 依赖 2 = 5(中)。schema 引入 + reader 切换;reader fallback 链长但每层独立可测

---

### S2 — Writer 切 SQLite + 事务包裹 + 审计写入(M2 单独 review,**高风险**)

**目标**:消化"`apply_proposal` 事务回滚缺失"Open(Phase 61 留下);writer 切 SQLite UPSERT;Repository 层最外层 `BEGIN IMMEDIATE` 事务;审计写入在事务内

**影响范围**:
- 改动:`src/swallow/router.py` — `save_route_registry` / `save_route_policy` / `save_route_weights` / `save_route_capability_profiles` 实装层从 JSON 写改为 SQL UPSERT(签名不变)
- 改动:`src/swallow/truth/route.py:RouteRepo._apply_metadata_change` — 整体 `BEGIN IMMEDIATE` ... `COMMIT` 包裹;事务内顺序调 4 对 save+apply(无变化);失败自动 ROLLBACK
- 改动:`src/swallow/truth/policy.py:PolicyRepo._apply_policy_change` — 同款事务包裹
- 新增:`src/swallow/truth/route.py` / `truth/policy.py` — 在事务内写 `route_change_log` / `policy_change_log` 审计行
- 改动:`src/swallow/governance.py:_apply_route_metadata` 与 `_apply_policy` — 把 `proposal.proposal_id` 透传给 Repository,作为审计行 `proposal_id` 字段(governance.py 现已传 `proposal_id` 参数,只需透传)
- **不动**:`apply_proposal` 公开签名;`OperatorToken` schema;`ProposalTarget` enum;`_PENDING_PROPOSALS` 行为
- **不动**:Repository 接口契约(Phase 63 立的私有 write method 名 + 签名)

**关键设计决策**:

- **事务边界(authoritative)**:`BEGIN IMMEDIATE` 在 `_apply_metadata_change` / `_apply_policy_change` 函数体最外层;函数内部所有 save + apply + 审计写都在事务内;`COMMIT` / `ROLLBACK` 由函数 try/except 控制
  ```python
  def _apply_metadata_change(self, *, base_dir, route_registry=None, ...):
      conn = _get_connection(base_dir)
      conn.execute("BEGIN IMMEDIATE")
      try:
          applied_writes = []
          before_snapshot = self._capture_snapshot(conn)  # 用于 audit
          if route_registry is not None:
              save_route_registry_via_sql(conn, route_registry)
              apply_route_registry(base_dir)  # in-memory mutation
              applied_writes.append("route_registry")
          # ... 同样模式处理 route_policy / route_weights / route_capability_profiles
          # 审计行:在事务内写 route_change_log
          self._write_audit_log(conn, before_snapshot=..., after_snapshot=..., proposal_id=...)
          conn.execute("COMMIT")
          return tuple(applied_writes)
      except Exception:
          conn.execute("ROLLBACK")
          raise
  ```

- **`apply_route_*` 在事务内调用 in-memory mutation**:`apply_route_registry(base_dir)` 等 helper 在事务内调用,刷新进程内 `ROUTE_REGISTRY`。**关键正确性**:若事务后续步骤失败 ROLLBACK,SQLite 数据回滚,但 in-memory `ROUTE_REGISTRY` **已经 mutation**(`apply_route_registry` mutate ROUTE_REGISTRY 实例属性,Python 层无 rollback 能力)
  
  **缓解**:在事务开始时 snapshot 当前 in-memory ROUTE_REGISTRY 状态;失败 ROLLBACK 后从 SQLite 重新加载并刷新 in-memory(等价于 redo)。具体实装:
  ```python
  except Exception:
      conn.execute("ROLLBACK")
      # 从 SQLite 重新加载,把 in-memory ROUTE_REGISTRY 恢复到事务前状态
      apply_route_registry(base_dir)
      apply_route_policy(base_dir)
      apply_route_weights(base_dir)
      apply_route_capability_profiles(base_dir)
      raise
  ```
  这是 in-memory 不一致的唯一可靠修复路径(SQLite ROLLBACK + 重新加载 = 等价于事务前快照)

- **审计写入位置(kickoff G4 已锁定)**:Repository 层事务内写 `route_change_log` / `policy_change_log`。`governance._emit_event` 桩函数继续保留,但**不**在 Phase 65 内写审计 log(留给后续 phase 作 telemetry / observer 钩子)

- **before / after snapshot 实装**:在事务开始时从 SQLite SELECT 出当前 route_registry / policy_records 全量 → JSON 序列化作为 `before_payload`;事务结束前再 SELECT → `after_payload`。**仅记录"本次 proposal 实际改动的字段"** 还是"全量 snapshot",由 Codex 在 PR body 中给出 rationale + 示例数据(推荐:全量 snapshot,因为 audit 用途是回溯 + 调试,全量字段更有价值;成本 = 每次 audit 行存一份 JSON dict,可接受)

- **`_apply_route_review_metadata` 跨多 save 调用的事务边界**:governance.py 中 `_apply_route_review_metadata`(line 325-577)在多处调 save_route_weights / save_route_capability_profiles / write_json (review record artifact)。**事务包裹的边界**:`_apply_metadata_change` 内部的事务**只覆盖** SQL writes(route_weights / capability_profiles 的 SQL UPSERT);review record artifact 文件写入(`_write_json(application_path, ...)`)**不在事务内**(filesystem write)
  
  这是已知不完美:若 SQL commit 成功但 review record write 失败,会出现"SQLite 已写但 review record 缺失"。**Phase 65 不修复此问题**(超出 scope,review record 是 audit artifact 而非 truth);closeout 登记 backlog Open

- **接口签名不变**:`save_route_registry(base_dir, payload)` / `save_route_policy(base_dir, payload)` / `save_route_weights(base_dir, payload)` / `save_route_capability_profiles(base_dir, payload)` 签名不变;**内部实装**从 JSON 写改为 SQL UPSERT(走 _http_helpers 同款 helper 模式或新加 `_get_connection(base_dir)` 内部辅助函数)。这保证测试 mock 透明:`patch("swallow.router.save_route_registry", ...)` 等用例不需调整

- **migration 与 writer 切换的协调**:M2 切 writer 时,SQLite 已经在 M1 跑过 migration(idempotent);M2 后所有 writer 写入直接 SQLite,JSON 文件**不再被 writer 触动**(deprecated 状态,JSON 文件保留作为 backup,但内容不再更新)。**Phase 65 不删 JSON 文件**(YAGNI;后续 phase 可清理)

- **`apply_route_*` 在 ROLLBACK 后重新加载 vs 暂存 in-memory snapshot**:Codex 实装时选其一。Claude 推荐前者(从 SQLite 重新加载),理由:简单 + SQLite 是 source of truth + 等价于"事务前 snapshot"

### S2 修订决议(2026-04-29 model_review 后)

**[BLOCK-1 解决] SQLite isolation_level + 显式事务管理(authoritative)**

`sqlite_store.get_connection(base_dir)` 内部建立的 connection **必须设置 `isolation_level=None`**(autocommit mode + 显式事务管理),避免 Python `sqlite3` 默认隐式事务与 `BEGIN IMMEDIATE` 冲突。

```python
# src/swallow/sqlite_store.py
def get_connection(base_dir: Path) -> sqlite3.Connection:
    conn = ...  # process-cached or freshly opened
    conn.isolation_level = None  # explicit transaction management
    return conn
```

**对既有 write path 的影响**:`SqliteTaskStore._connect` 当前仍走默认 `isolation_level=''`(隐式事务 + `with conn:` 自动 commit/rollback)。Phase 65 引入 `get_connection` **新通道**,只用于 `RouteRepo / PolicyRepo / bootstrap`;`SqliteTaskStore` 内部既有 task / event / knowledge 的写路径不动(避免 Phase 65 scope 外漂移)。

**事务模式**(`isolation_level=None` 下,`_apply_metadata_change` 完整模板):

```python
def _apply_metadata_change(self, *, base_dir, route_registry=None, ...):
    conn = sqlite_store.get_connection(base_dir)
    # autocommit mode → 显式 BEGIN
    conn.execute("BEGIN IMMEDIATE")
    try:
        if route_registry is not None:
            _save_route_registry_via_sql(conn, route_registry)  # 不在 _save 内部 commit
            apply_route_registry(base_dir)  # in-memory mutation
        # ... policy / weights / capability_profiles 同款
        # 同事务内写 audit log
        _write_route_audit_log(conn, before=..., after=..., proposal_id=...)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        # connection 此时回到 idle 状态,redo 路径下面 [CONCERN-1 解决]
        try:
            apply_route_registry(base_dir)
            apply_route_policy(base_dir)
            apply_route_weights(base_dir)
            apply_route_capability_profiles(base_dir)
        except Exception:
            # SQLite 损坏属于 catastrophic;Phase 65 假设健康
            raise
        raise  # 抛出原异常给 caller
```

**[BLOCK-4 解决] `policy_records` round-trip 映射表(authoritative)**

| Repo 入参 | `policy_records.kind` | `policy_records.scope` | `policy_records.scope_value` | `policy_records.payload` |
|---|---|---|---|---|
| `AuditTriggerPolicy` 实例 | `'audit_trigger'` | `'global'` | `NULL` | `AuditTriggerPolicy.to_dict()` JSON 序列化 |
| `(mps_kind, mps_value)` 二元组 | `'mps'` | `'mps_kind'` | `mps_kind`(str) | `{"value": mps_value}` JSON 序列化 |

- `policy_id` 主键 = `f"{kind}:{scope_value or 'global'}"`(human-readable stable key,与 route_id 同模式;Phase 65 不引入独立 ULID)
- 反序列化失败回退路径:`load_*` helper 检测 `payload` JSON parse 失败 → log warning + fallback 到 default seed(`route_policy.default.json` 中对应 entry 或 hardcoded fallback);**不**抛异常给 caller(避免启动期级联失败)
- DATA_MODEL §3.5 修改边界(M3 同步):标"已实装(Phase 65)" + 加映射表说明;不动既有列定义

**[CONCERN-1 解决] ROLLBACK 后 redo 时序约束**

- ROLLBACK 后 connection 自动回到 idle 状态(SQLite 标准行为)
- redo 路径在 `except` 块中执行;此时 4 个 `apply_route_*` helper 各自走 `load_*` → SQLite SELECT(纯读,不开新事务)
- **关键**:redo 必须按 INVARIANTS Phase 64 立的加载顺序 `apply_route_registry → apply_route_policy → apply_route_weights → apply_route_capability_profiles`(不调 `apply_route_fallbacks`,因 fallback 是 operator-local seam,不在事务内)
- redo 自身失败(罕见)→ 抛新异常并保留原异常 chain(`raise OriginalException from RedoException`),由 caller 决定是否 fail-fast 进入 waiting_human

**[CONCERN-2 解决] 失败注入测试矩阵(必入 closeout 验收)**

S2 PR 必须包含以下 monkeypatch 注入点的 regression test(每个独立 test case;test 文件 `tests/test_governance_phase65_transaction.py` 或 `tests/test_truth_route_transaction.py`):

| 注入点 | 测试断言 |
|---|---|
| 1. 第一次 SQL UPSERT 前抛错 | SQLite 行未变 / audit 未写 / in-memory == 事务前 |
| 2. route_registry UPSERT 后抛错 | 同上(SQLite ROLLBACK 验证) |
| 3. route_policy UPSERT 后抛错 | 同上 |
| 4. route_weights UPSERT 后抛错 | 同上 |
| 5. route_capability_profiles UPSERT 后抛错 | 同上 |
| 6. `apply_route_*` in-memory mutation 后抛错 | redo 路径触发,in-memory 恢复 |
| 7. audit INSERT 后 commit 前抛错 | SQLite 全 ROLLBACK,audit 行不存在 |
| 8. commit 成功后 caller 异常 | 仅验 transaction 已 commit + audit 已写(非 ROLLBACK 场景) |

policy 路径同款简化版:注入点 1-2(`audit_trigger_policy` UPSERT / `mps_policy` UPSERT)+ 6-7(in-memory + audit)。

**[CONCERN-3 解决] review record artifact 显式归类**

`_apply_route_review_metadata` 内部的 `_write_json(application_path, ...)` 调用属于 **audit-adjacent 派生物**,**不是 canonical governance state**:

- 任何 reader 不得把它当作 truth(Codex 在 PR body 中验证:grep `application_path` 的所有 read 调用,确认仅用于 audit / debug / 报告生成,不作为决策输入)
- 它的失败语义是 at-least-once:SQL commit 成功后才写 artifact;artifact 写失败仅 log warning,不影响 SQL truth(Phase 65 已知限制,不修复;closeout 登记 backlog Open)
- DATA_MODEL §6 文件系统约束已规定 artifact 路径形态;Phase 65 不动 artifact 路径与命名

**[CONCERN-7 部分解决] audit snapshot 大小**

- before/after 仍用全量 snapshot(Phase 65 决议)
- S2 PR 必须含 non-trivial round-trip 测试:fixture 包含 ≥3 routes × 5+ task_family_scores entries 的 capability_profiles,验证 audit 行 JSON 完整可反序列化
- 若超大 payload(>1MB)导致 SQLite 写失败,该次 proposal apply 应整体 ROLLBACK(audit 在事务内,大 payload 失败即 governance 失败,符合原子性)— 这是 intentional behavior,closeout 文字声明

**验收条件**:
- `swl route registry apply <file>` 写入 SQLite;`swl route policy apply <file>` 同款
- 模拟事务中途失败:`apply_proposal(..., ROUTE_METADATA)` 在 capability_profiles save 阶段抛错,SQLite 中 route_registry 也 ROLLBACK 不留部分写;in-memory `ROUTE_REGISTRY` 恢复到事务前状态(回归测试覆盖)
- `route_change_log` 在每次成功 `apply_proposal(..., ROUTE_METADATA)` 后新增一行,含 `before_payload` / `after_payload` / `proposal_id`
- `policy_change_log` 同款
- `save_route_*` 接口签名不变
- 现有测试 mock(`patch("swallow.router.save_route_registry", ...)`)零迁移 — 全量 pytest 通过

**风险评级**:影响范围 3 / 可逆性 2 / 依赖 2 = **7(高)**。事务边界设计是 Phase 65 核心正确性保证;in-memory + SQLite 一致性 + 审计原子性三方耦合;`_apply_route_review_metadata` 跨多 save 调用的事务边界设计需谨慎

**SCOPE WARNING**:
- 不要顺手重构 `_apply_route_review_metadata` 业务逻辑(non-goal)
- 不要把 review record artifact write 也塞进事务(超 scope,登记 backlog)
- 不要扩展 `_emit_event` 写 audit log(本 phase 决议:Repository 内写,_emit_event 留给后续)
- 不要引入 multi-actor / locking(永久非目标)

---

### S3 — §9 守卫扩展 + Migration 协议落地 + DATA_MODEL.md 同步(M3 单独 review)

**目标**:扩展 §9 append-only 守卫;落地 §8 migration 协议;同步 DATA_MODEL.md 文字

**影响范围**:
- 改动:`tests/test_invariant_guards.py:test_append_only_tables_reject_update_and_delete` — `insert_sql` dict 扩展含 `route_change_log` / `policy_change_log` 两表的 INSERT fixture + UPDATE / DELETE 反例(实装与现 4 张表同款,机械补充)
- 新增:`src/swallow/migrations/001_phase65_route_policy_sqlite.sql`(或同款命名)— SQL DDL 文件,包含 4 张新表 schema + trigger
- 改动:`src/swallow/sqlite_store.py` — 加 `schema_version` 表(若不存在)+ 启动时检测 version + 自动 apply migration(开发期 default true);设计层让 production 部署可禁用自动 migrate(进入 `waiting_human` 提示运行 `swl migrate`)
- 新增:`swl migrate` CLI 子命令(若不存在)— 手动运行 migration
- 改动:`docs/design/DATA_MODEL.md`:
  - §3.4 / §3.5 加"已实装(Phase 65)"标注;不动既有 DDL 字段
  - §4.2 append-only 表清单从 4 张扩展到 6 张
  - §8 migration 协议补充实际落地状态(若现为 placeholder)

**关键设计决策**:

- **`schema_version` 表 schema**(authoritative):
  ```sql
  CREATE TABLE IF NOT EXISTS schema_version (
      version    INTEGER PRIMARY KEY,
      applied_at TEXT NOT NULL,
      slug       TEXT NOT NULL
  );
  ```
  Phase 65 后 `version=1, slug='phase65_route_policy_sqlite'`;后续 phase 引入新 migration 时 `INSERT INTO schema_version`

- **启动时 schema 检测**:`SqliteTaskStore._connect` 检测 `schema_version` 表是否存在 + 最高 version 是否落后于代码层 `EXPECTED_SCHEMA_VERSION` 常量;落后则:
  - 开发模式(默认):自动 apply pending migrations
  - 生产模式(可选 env var `SWL_MIGRATION_MODE=manual`):进入 `waiting_human` 提示运行 `swl migrate`
  - 本 phase scope 内只实装开发模式,生产模式 placeholder

- **`swl migrate` CLI**:简单实装 — 列出 pending migrations + apply 全部;输出 schema_version 行;失败提示
  ```bash
  swl migrate              # apply all pending
  swl migrate --status     # show current version + pending migrations
  ```

- **DATA_MODEL.md 修改边界**(authoritative,Codex 严格对齐):
  - §3.4 末尾加注:"**Phase 65 实装**:`route_registry` 表已建,通过 `apply_proposal(..., ROUTE_METADATA)` 写入。`route_change_log` 审计表 append-only。"
  - §3.5 同款加注
  - §4.2 表清单 4 → 6:增加 `route_change_log` / `policy_change_log` 两行,与现 4 张表同款描述
  - §8 migration 段补充实际工具:`swl migrate` CLI + `swallow/migrations/<version>_<slug>.sql` 协议
  - **不重写既有 DDL / 不修改既有字段语义 / 不动 §1 / §2 / §5 / §6 / §7 / §9**

- **`test_append_only_tables_reject_update_and_delete` fixture 数据**:对每张新表准备 schema-aligned INSERT + UPDATE/DELETE 反例。`route_change_log` / `policy_change_log` schema 见 S2 关键设计决策段

### S3 修订决议(2026-04-29 model_review 后)

**[BLOCK-5 解决] §8 矛盾 — 收紧 Phase 65 scope(authoritative,Human 已确认路径 i)**

DATA_MODEL §8 文字 **不动**(永远不允许运行时静默执行 schema migration,仍要求 schema 落后 → `waiting_human` + `swl migrate`)。

Phase 65 的 schema 兑现行为重新归类为 **"首次建表(table creation on fresh DB)"**,不属于 §8 范围内的 migration:

| 行为 | 是否属于 §8 migration | Phase 65 内的处理 |
|---|---|---|
| Fresh empty DB 首次启动 → 建 4 张新表 | **否**(不存在旧 schema 升级到新 schema) | `_connect` 自动 `CREATE TABLE IF NOT EXISTS`(开发 + 生产模式都允许;`schema_version` 同步插入 `version=1`) |
| 既有 DB 缺 Phase 65 表 → 建表 | **否**(同上,只是逻辑上的"首次") | 同上 |
| 既有 DB 有 schema_version<1 但有 Phase 65 表(状态错位) | 是(数据已存但 version 落后) | 进入 §8 标准路径:`waiting_human` + `swl migrate` |
| Phase 66+ 真正 schema 升级(改字段类型 / drop 列等) | **是** | 走 §8 标准路径 |

**design_decision §S3 修订要点**:

- 删除"开发模式默认自动 migrate"提法
- 改为:**首次建表是 `_connect` 的初始化职责,不算 migration;`schema_version` 仅在真正的 schema 升级时增长**
- `swl migrate` CLI(M3 内引入)的语义仅指真正的 schema_version 升级 — Phase 65 内不会触发该路径(因为 version=1 是 fresh install,无 pending migration)
- `swl migrate --status` 在 Phase 65 fresh DB 上输出 `schema_version: 1, pending: 0`(无 pending,因为没有 v0 → v1 的 migration script;v1 是首次 schema)

**migration 文件命名修订**:`swallow/migrations/001_phase65_route_policy_sqlite.sql` **不再作为 Phase 65 内"必须 apply 的 migration"** — 它的存在仅作 **schema 版本快照参考**(documentation-as-DDL 形式)。Codex 实装时可:

- 选项 A(推荐):**不创建 `001_*.sql` 文件**,Phase 65 内 schema 完全由 `sqlite_store.py:_connect` 中的 `CREATE TABLE IF NOT EXISTS` 维护;migrations/ 目录在 Phase 66+ 真正 schema 升级时启用
- 选项 B:创建 `001_*.sql` 但仅作 reference,`schema_version=1` 在 `_connect` 内直接 INSERT(不走 migration runner)

Claude 推荐选项 A,理由:Phase 65 内"首次建表"已经不是 migration,引入 migration file 是过度设计;Phase 66+ 第一次真正 schema 升级时再启用 migration runner 与 v1→v2 SQL 文件。

**[BLOCK-3 衔接] DATA_MODEL §3.4 修改边界放宽(M3 同步)**

§3.4 修改范围:

- 加 6 列(`capabilities_json` / `taxonomy_json` / `execution_site` / `executor_family` / `executor_name` / `remote_capable`),含空值约定说明
- 标"已实装(Phase 65)"
- 既有列(`route_id` / `model_family` / ...)的 DDL 字段语义不动
- 同步保持:`unsupported_task_types` / `cost_profile` 类型从文档标 `JSON` 到实装 `TEXT NOT NULL DEFAULT '[]'` / `'null'` 的差异说明(SQLite 习惯)

§3.5 修改范围:

- 标"已实装(Phase 65)"
- 加 round-trip 映射表(audit_trigger_policy → kind='audit_trigger' / mps_policy → kind='mps' / scope_value 用法)
- 既有列的 DDL 字段语义不动

§4.2 修改范围:

- append-only 表清单从 4 张扩展到 6 张(加 `route_change_log` / `policy_change_log`)

§8 修改范围:

- **不动文字**(per BLOCK-5 路径 i)
- 仅在 §8 末尾加一行 reference:"`首次建表(table creation on fresh DB)`不属于本节 migration 范围,由 `sqlite_store.py:_connect` 内 `CREATE TABLE IF NOT EXISTS` 一次性维护;`schema_version` 在首次建表后直接 INSERT v=1"

**[CONCERN-5 衔接] M1 不允许独立 release(closeout 验收)**

kickoff §完成条件 已增加约束(本 phase 同款):**M1 commit 不可单独 PR 上 main**;Phase 65 整体 release 必须包含 M1 + M2 + M3。Codex M1 commit 后必须直接接 M2 实装,Human Gate 时不会被允许 review M1 单独提交分支为 ready-to-merge。

**验收条件**(修订后):
- `tests/test_invariant_guards.py:test_append_only_tables_reject_update_and_delete` 测 6 张表,每张表 INSERT + UPDATE 拒 + DELETE 拒
- `_connect` 在 fresh DB 上正确建 4 张新表 + INSERT `schema_version(version=1, slug='phase65_initial', applied_at=...)` 1 行
- `swl migrate --status` 在 Phase 65 fresh DB 上输出 `schema_version: 1, pending: 0`(无 pending)
- `swl migrate` 在 Phase 65 内**不会被触发**(无 pending migration);仅作 Phase 66+ 入口
- `git diff docs/design/DATA_MODEL.md` 仅含 §3.4 加 6 列 + §3.5 映射表 + §4.2 表清单 4→6 + §8 末尾 reference 一行;**§8 既有文字不变**
- `git diff docs/design/INVARIANTS.md` 无任何改动

**风险评级**:影响范围 2 / 可逆性 1 / 依赖 2 = 5(中)。守卫扩展 + 工具新增 + 文档同步;每项独立可逆

---

## 依赖与顺序

```
S1 (M1, schema + reader + migration) ──> S2 (M2, writer + transaction + audit) ──> S3 (M3, guard + migration tool + docs)
                                       (M2 切 writer 必须先有 SQLite schema 与 reader)
                                                                              (M3 守卫扩展依赖 M1 表已存在)
```

**Codex 推荐实装顺序**:**S1 → S2 → S3**(无并行,无倒序)

## Milestone 与 review checkpoint

| Milestone | 包含 slice | review 重点 | 提交节奏 |
|-----------|-----------|------------|---------|
| **M1** | S1 | 4 张新表 DDL 对齐 DATA_MODEL §3.4/§3.5 / reader fallback 链(SQLite → JSON → seed)/ 一次性 migration idempotency | 单独 milestone commit |
| **M2** | S2 | 事务边界设计 / in-memory ROUTE_REGISTRY 在 ROLLBACK 后重新加载 / 审计 before/after snapshot 完整性 / save_* 接口签名不变 | 单独 milestone commit;**高风险,review 重点关注事务正确性** |
| **M3** | S3 | 守卫扩展 6 张表 / migration 协议 + `swl migrate` CLI / DATA_MODEL.md §3.4/§3.5/§4.2/§8 同步对齐 | 单独 milestone commit |

## 守卫与测试映射

| Slice | 启用 / 新增守卫 / 测试 | §9 表内 | §9 表外 |
|-------|----------------------|---------|---------|
| S1 | 一次性 migration 的 idempotency 测试(新增,test_router.py 或 test_sqlite_store.py)| 0 | 1(idempotency)|
| S2 | 事务回滚回归测试(新增,test_governance.py)+ 审计行写入测试(新增) | 0 | 2(transaction + audit) |
| S3 | `test_append_only_tables_reject_update_and_delete` 扩展含 6 张表(既有守卫扩范围,不计新增) | 0 (扩展不计) | 0 |
| **合计** | **3 条新测试** | **0** | **3** |

完结后:INVARIANTS §9 标准表 17 条全 active 不变(本 phase 不新增 §9 表内守卫,只扩展既有 `test_append_only_tables_reject_update_and_delete` 守卫的被测表清单)

## phase-guard 检查

- ✅ 当前方案不越出 kickoff goals(G1-G7 与 S1-S3 一一对应)
- ✅ kickoff non-goals 严守:**不修改 INVARIANTS.md 任何文字**;不引入对象存储后端;不动 Phase 63/64 已落地内容;不重构 `_apply_route_review_metadata` 业务逻辑;不动 `route_fallbacks.json` operator-local seam
- ✅ DATA_MODEL.md 修改限定在 §3.4 / §3.5 / §4.2 / §8 的"已定义未实装"补丁
- ✅ slice 数量 3 个,符合"≤5 slice"指引
- ✅ 1 个高风险 slice(S2,7 分),其他 2 个中风险
- ✅ Provider Router / Repository 抽象层契约保持(Phase 63 立的接口不动)
- ✅ Phase 64 已落地的 `lookup_route_by_name` / `invoke_completion` / `_http_helpers` / route metadata 三层外部化保持

## Branch Advice

- 当前分支:`main`(Phase 64 已 merge)
- 建议 branch 名:`feat/phase65-truth-plane-sqlite`
- 建议操作:Human Design Gate 通过后 Human 切出该 branch,Codex 在该分支上实装 S1 → S2 → S3

## Model Review Gate

**推荐触发**(Claude 推荐;Human 在 Design Gate 决定):理由见 kickoff §Model Review Gate。事务边界 + DATA_MODEL §3.4/§3.5 实装兑现 + S2 高风险都是值得外部 reviewer(GPT-5 via `mcp__gpt5__chat-with-gpt5_5`)核验的点

## 不做的事(详见 kickoff non-goals)

- 不修改 INVARIANTS.md
- 不引入对象存储后端
- 不重构 `_apply_route_review_metadata` 业务逻辑
- 不动 `route_fallbacks.json`
- 不动 Phase 63/64 已落地内容
- 不动 `events`/`event_log` 双写问题
- 不引入 metrics / multi-actor / authn

## 验收条件(全 phase)

详见 `kickoff.md §完成条件`。本 design_decision 与 kickoff 一致,无补充。
