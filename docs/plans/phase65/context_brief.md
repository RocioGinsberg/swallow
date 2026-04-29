---
author: claude/context-analyst
phase: phase65
slice: context-brief
status: draft
depends_on:
  - docs/roadmap.md
  - docs/design/INVARIANTS.md
  - docs/design/DATA_MODEL.md
  - docs/plans/phase63/closeout.md
  - docs/plans/phase64/closeout.md
  - docs/concerns_backlog.md
  - src/swallow/sqlite_store.py
  - src/swallow/governance.py
  - src/swallow/truth/route.py
  - src/swallow/router.py
  - src/swallow/paths.py
  - src/swallow/store.py
  - tests/test_invariant_guards.py
---

TL;DR: Phase 64 (G.5) is merged; route metadata / policy are externalized as JSON files under `.swl/` but still violate INVARIANTS P2 ("SQLite-primary truth"). Phase 65 scope = migrate `route_registry` / `route_policy` / `route_weights` / `route_capability_profiles` from JSON files to SQLite, wrap `_apply_metadata_change` in `BEGIN IMMEDIATE`, introduce `route_change_log` / `policy_change_log` append-only audit tables, and extend `test_append_only_tables_reject_update_and_delete` to cover the new tables. The transaction gap in `RouteRepo._apply_metadata_change` (up to 4 sequential save+apply pairs with no atomicity guarantee) is the primary correctness risk; `_BUILTIN_ROUTE_FALLBACKS` baseline and test fixture compat are secondary design questions.

---

## 目标摘要

route metadata(registry / policy / weights / capability profiles)和 policy 从 `.swl/*.json` 迁入 SQLite。`apply_proposal` 对应 dispatch 路径用 `BEGIN IMMEDIATE` 包裹整组写操作。引入 `route_change_log` / `policy_change_log` append-only 审计表。`test_append_only_tables_reject_update_and_delete` 扩展含新两张表。履行 INVARIANTS P2 在 route / policy 层的代码承诺。

---

## 变更范围

### 直接影响模块

| 文件 | 函数 / Symbol | 角色 |
|------|--------------|------|
| `src/swallow/sqlite_store.py:148` | `APPEND_ONLY_TABLES` | 新增 `route_change_log` / `policy_change_log`;对应 `APPEND_ONLY_TRIGGER_SQLS` 自动生成 |
| `src/swallow/sqlite_store.py:191-218` | `SqliteTaskStore._connect` | 新增两张 route/policy metadata 表的 DDL 调用 + 新审计表触发器 |
| `src/swallow/truth/route.py:17-48` | `RouteRepo._apply_metadata_change` | 4 对 save+apply 改为单 SQLite `BEGIN IMMEDIATE` 事务;save 路径由 JSON 写改为 SQL INSERT/UPSERT |
| `src/swallow/router.py:559-598` | `load_route_registry` / `save_route_registry` / `apply_route_registry` | reader 改从 SQLite 加载;writer 改为 SQL UPSERT;apply 仍刷新进程内 `ROUTE_REGISTRY` 和 `_BUILTIN_ROUTE_FALLBACKS` |
| `src/swallow/router.py:566-603` | `load_route_policy` / `save_route_policy` / `apply_route_policy` | 同上 |
| `src/swallow/router.py:653-690` | `load_route_weights` / `save_route_weights` / `apply_route_weights` | 同上 |
| `src/swallow/router.py:713-749` | `load_route_capability_profiles` / `save_route_capability_profiles` / `apply_route_capability_profiles` | 同上 |
| `src/swallow/truth/policy.py` | `PolicyRepo._apply_policy_change` | audit_trigger_policy / mps_policy 迁入 SQLite;`policy_change_log` 审计写入 |
| `src/swallow/governance.py:303-323` | `_apply_route_metadata` | 通过 `RouteRepo._apply_metadata_change` 间接受益于事务包装;无公开接口变更 |
| `src/swallow/governance.py:587-617` | `_apply_policy` | 同上通过 `PolicyRepo._apply_policy_change` |
| `tests/test_invariant_guards.py` | `test_append_only_tables_reject_update_and_delete` | 扩展 `insert_sql` dict 含 `route_change_log` / `policy_change_log` 两张新表 |

### 间接影响模块

| 文件 | 关联方式 |
|------|---------|
| `src/swallow/orchestrator.py:2477-2481, 2617-2621` | 两处 5-函数加载顺序调用序列不变;底层 reader 改从 SQLite 读 |
| `src/swallow/cli.py:2347-2351, 2776-2780` | 同上两处加载序列 |
| `src/swallow/cli.py:2643-2668` | `swl route registry apply` / `route policy apply` 仍走 `register_route_metadata_proposal + apply_proposal`;接口不变 |
| `src/swallow/meta_optimizer.py:820` | `load_route_capability_profiles(base_dir)` 读路径改从 SQLite |
| `src/swallow/governance.py:345-346` | `_apply_route_review_metadata` 内 `load_route_weights` + `load_route_capability_profiles` 读路径改从 SQLite |
| `src/swallow/paths.py:209-227` | `route_weights_path` / `route_registry_path` / `route_policy_path` / `route_capabilities_path` / `route_fallbacks_path` — Phase 65 后这些 helper 仅在迁移逻辑和 report builder 中使用;不再是 truth write 路径 |
| `tests/test_router.py` | 大量测试通过 `save_route_registry(tmp_path, ...)` / `save_route_policy(tmp_path, ...)` 写 JSON,Phase 65 后需改为写 SQLite — 见"测试 fixture 兼容"节 |

---

## 近期相关变更 (git history)

| Commit | 描述 | 相关模块 |
|--------|------|---------|
| `7b38aeb` | Merge Phase 64 (G.5) | 全部 Phase 64 改动 |
| `ba2f518` | docs(phase64): close out review follow-up | `router.resolve_fallback_chain` public |
| `625948d` | refactor(phase64): expose fallback chain resolver | `router.py` |
| `c404f3e` | feat(phase64): externalize route selection policy | `router.py` / `cli.py` / `truth/route.py` |
| `900c38b` | feat(phase64): externalize route registry metadata | `router.py` / `cli.py` / `truth/route.py` |
| `6ad909e` | feat(phase64): allow route fallback overrides | `router.py` / `paths.py` |
| `1df5992` | feat(phase63): add truth repository write boundary | `truth/route.py` / `truth/policy.py` / `governance.py` |
| `5116b62` | test(phase63): add invariant guard batch | `test_invariant_guards.py` / `sqlite_store.py` |

---

## 关键上下文

### SQLite 现有表清单

`sqlite_store.py:_connect` 在 `_connect` 调用时按顺序建表:

```
tasks / events / knowledge_evidence / knowledge_wiki
knowledge_migrations / knowledge_relations
event_log / event_telemetry / route_health / know_change_log
```

append-only 表(`sqlite_store.py:148`): `("event_log", "event_telemetry", "route_health", "know_change_log")`

DATA_MODEL §3.4 中 `route_registry` 表 DDL 已写入设计文档但**尚未在 `sqlite_store.py` 中建表**。DATA_MODEL §3.5 中 `policy_records` 表同理。Phase 65 需要在 `_connect` 中新增对应 DDL,并同步 `DATA_MODEL.md §3.4 / §3.5` 的实现标注。

### `RouteRepo._apply_metadata_change` 事务空隙(精确定位)

`src/swallow/truth/route.py:28-47`:

```python
if route_registry is not None:
    save_route_registry(base_dir, route_registry)   # JSON 写磁盘 (原子 rename)
    apply_route_registry(base_dir)                  # 刷新进程内 ROUTE_REGISTRY
    ...
if route_policy is not None:
    save_route_policy(base_dir, route_policy)        # JSON 写磁盘
    apply_route_policy(base_dir)                     # 刷新进程内 policy globals
    ...
if route_weights is not None:
    save_route_weights(base_dir, route_weights)      # JSON 写磁盘
    apply_route_weights(base_dir)                    # 刷新 ROUTE_REGISTRY 权重
    ...
if route_capability_profiles is not None:
    save_route_capability_profiles(base_dir, ...)    # JSON 写磁盘
    apply_route_capability_profiles(base_dir)        # 刷新 ROUTE_REGISTRY 能力
    ...
```

失败场景:第 N 对 save+apply 成功,第 N+1 对 save 失败 → 磁盘 JSON 与进程内 `ROUTE_REGISTRY` 已局部更新但不一致。进程重启后从 JSON 加载会恢复部分更新状态。`BEGIN IMMEDIATE` + SQLite 事务包裹全部 SQL UPSERT 是唯一可靠修复路径。

此即 `docs/concerns_backlog.md` Phase 61 Open 条目: `save_route_weights → apply_route_weights → save_route_capability_profiles → apply_route_capability_profiles` 四步如中途失败进入不一致状态。

### `_apply_route_review_metadata` 的 double-read 问题

`governance.py:345-346` 在进入 `_apply_route_review_metadata` 时先读取:
```python
updated_weights = load_route_weights(proposal.base_dir)
existing_profiles = load_route_capability_profiles(proposal.base_dir)
```

Phase 65 切到 SQLite 后,这两处 read 改从同一 SQLite 连接读,逻辑不变但要确保 read 发生在事务开始前(快照一致),再 upsert 结果。

### `_emit_event` 桩函数

`governance.py:620-621`:
```python
def _emit_event(_operator_token: OperatorToken, _target: ProposalTarget, _result: ApplyResult) -> None:
    """Reserved for durable governance audit events once the event repository exists."""
```

Phase 65 引入 `route_change_log` / `policy_change_log` 后,`_emit_event` 可成为真实写入点。设计决策需要明确:写入 `route_change_log` 是在 `RouteRepo._apply_metadata_change` 内部的事务里,还是由 `governance._emit_event` 在事务外追加 — 两种方式对"审计原子性"有不同含义。

### 加载顺序(5 入口已对齐)

Phase 64 后以下 5 处均按相同顺序调用 5 个 apply helper:

```
apply_route_registry → apply_route_policy → apply_route_weights
→ apply_route_fallbacks → apply_route_capability_profiles
```

- `src/swallow/orchestrator.py:2477-2481`(run_task 初始化)
- `src/swallow/orchestrator.py:2617-2621`(resume 路径)
- `src/swallow/cli.py:2347-2351`(run 命令)
- `src/swallow/cli.py:2776-2780`(task resume)
- `src/swallow/cli.py:3311-3315`(第三处,行号来自 grep)

Phase 65 不改变调用顺序,只改 reader 实现。

### `_BUILTIN_ROUTE_FALLBACKS` 基线快照

`router.py:530`:
```python
_BUILTIN_ROUTE_FALLBACKS = {route.name: route.fallback_route_name for route in ROUTE_REGISTRY.values()}
```

此快照在模块 import 时从默认 JSON 构建。`apply_route_fallbacks` 以此为 baseline 再叠加 `.swl/route_fallbacks.json` override。Phase 65 后:

- `ROUTE_REGISTRY` 初始仍从 `routes.default.json` 构建(import-time 无 `base_dir` 可用)
- 首次 `apply_route_registry(base_dir)` 从 SQLite 加载 → 刷新 `ROUTE_REGISTRY` + `_BUILTIN_ROUTE_FALLBACKS`
- `route_fallbacks.json` 仍保留为 operator-local override seam,不迁入 SQLite(Phase 64 closeout 明确此 seam 不走 governance)

### DATA_MODEL 与代码层表名差异

DATA_MODEL §3.4 用 `route_registry`(主表)+ `route_health`;`sqlite_store.py:125-133` 已建 `route_health`,但 `route_registry` 表未建。DATA_MODEL §3.5 用 `policy_records`,`sqlite_store.py` 中同样未建。Phase 65 需要新建两张主表 + 两张变更日志表。

DATA_MODEL §4.2 明确声明 append-only 表为 4 张(`event_log / event_telemetry / route_health / know_change_log`)。Phase 65 新增 2 张(`route_change_log / policy_change_log`),需同步更新 DATA_MODEL §4.2 清单。

### events / event_log 双写现状

`sqlite_store.py:292-322`: `append_event` 同时写 `events`(旧表)和 `event_log`(新表)。`concerns_backlog.md` Phase 63 review M3-1 记录"历史 `events` 行不会 backfill 到 `event_log`"。Phase 65 范围仅引入 route/policy 审计表,不处理此双写问题(继续 deferred)。

### Migration 路径

`DATA_MODEL.md §8` 规定:schema 变更必须在 `swallow/migrations/<version>_<slug>.sql` 提交 migration 脚本;启动时检测 schema 落后进入 `waiting_human`,提示运行 `swl migrate`。Phase 65 实装时需同步实现 `schema_version` 检测逻辑(若当前尚未实现)或记录 deferred。

---

## 测试 Fixture 兼容

当前 `tests/test_router.py` 与 `tests/test_governance.py` 中大量测试通过 `save_route_registry(tmp_path, ...)` / `save_route_policy(tmp_path, ...)` 写 JSON 再调用 `apply_route_registry` / `apply_route_policy` 验证加载行为。具体:

- `tests/test_router.py:237` — `save_route_registry(tmp_path, route_registry)` + `apply_route_registry(tmp_path, registry)` 
- `tests/test_router.py:260` — `save_route_policy(tmp_path, route_policy)` + `apply_route_policy(tmp_path)`
- `tests/test_router.py:685` — `save_route_capability_profiles(...)`
- `tests/test_router.py:722` — `save_route_weights(...)`
- `tests/test_governance.py:191` — `apply_route_registry(tmp_path.parent)`
- `tests/test_governance.py:224` — `apply_route_policy(tmp_path.parent)`

Phase 65 后 `save_*` 函数改为 SQL UPSERT。测试 fixture 如果直接用 `save_*` 调用则自动跟随,无需额外改动。如果测试用 `tmp_path.write_text(...)` 绕过 helper 直接写 JSON 文件,则需要改写;`tests/test_router.py:242` 和 `tests/test_router.py:265` 有路径名断言(`routes.json` / `route_policy.json`),Phase 65 后这些路径 helper 不再是 truth 写路径,对应断言需更新或删除。

`tests/test_invariant_guards.py:206-215` 中 `test_only_apply_proposal_calls_private_writers` 验证只有 `apply_proposal` 调用 `save_route_registry / save_route_policy / save_route_weights / save_route_capability_profiles`。Phase 65 后如果 `save_*` 改名或语义变化,该守卫检测列表需同步更新。

---

## 风险信号

- **DATA_MODEL §3.4 / §3.5 与 sqlite_store.py 存在"文档已定义但代码未建表"的漂移**。Phase 65 建表需以 DATA_MODEL 为权威,补充 `route_registry` / `policy_records` 两张表及对应 index;如发现 DATA_MODEL schema 需调整,必须先改 DATA_MODEL 再改代码。

- **`_apply_route_review_metadata` 约 250 行,涉及 route_weight + capability 双路复杂写逻辑**(`concerns_backlog.md` Phase 63 review M2-5)。Phase 65 把这段逻辑的最终 write 路径切到 SQLite 事务,但不重构业务逻辑 — 需谨慎确认事务包裹的起止边界是在 `RouteRepo._apply_metadata_change` 内部,而非在 `_apply_route_review_metadata` 外层。

- **进程内 `ROUTE_REGISTRY` 是 module-level 全局 mutable 对象**。SQLite 是 source of truth,但进程内缓存在 apply_route_* 调用之间不会自动刷新。多进程 / 多线程场景下 in-memory 与 SQLite 仍可能短暂不一致 — 此为 Phase 65 范围内已知限制,不引入 authn/locking。

- **`route_fallbacks.json` 不走 governance,不迁入 SQLite**。这是 Phase 64 closeout 明确的设计意图。但 `_BUILTIN_ROUTE_FALLBACKS` 快照从 import-time `ROUTE_REGISTRY` 构建,Phase 65 后首次加载依然来自 `routes.default.json`。如果 SQLite 中 registry 与 default JSON 有差异,则 `_BUILTIN_ROUTE_FALLBACKS` 在首次 `apply_route_registry` 前后会更新 — 需确认 `apply_route_fallbacks` 调用顺序在 `apply_route_registry` 之后(当前 5 处加载顺序均满足)。

- **`governance.py:_emit_event` 桩函数**尚未写入任何审计表。Phase 65 引入 `route_change_log` / `policy_change_log` 后需要明确是由 Repository 层在事务内写审计记录,还是由 `_emit_event` 在事务外写 — 设计决策影响审计原子性保证。

---

## 对象存储后端兼容说明(范围边界)

roadmap §四候选 H 提到"为对象存储后端兼容清除技术债"。Phase 65 **不引入**对象存储后端,只把 SQLite 作为 route/policy 的唯一 truth backend。SQLite `BEGIN IMMEDIATE` 事务取代文件系统原子 rename,从根本上消除了"filesystem atomic rename 依赖"这一障碍;对象存储后端适配是更后续 phase 的 scope。

---

## Branch 建议

`feat/phase65-truth-plane-sqlite`
