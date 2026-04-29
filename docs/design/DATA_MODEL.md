# Swallow Data Model

> **Design Statement**
> 本文档是 Swallow 实现层的不变量。它定义 SQLite 命名空间、表 schema 边界、Repository 写权限白名单、文件系统布局和跨真值面的引用规则。
>
> 任何新表、新字段、新文件路径在写代码之前必须先改本文档。Code review 第一条问"你改了 DATA_MODEL.md 吗"。

> 概念层不变量见 → `INVARIANTS.md`(权威)。本文档只承载实现细节,不重复声明权限矩阵或 truth 面的语义边界。

---

## 1. 物理存储布局

```
<workspace_root>/.swl/
├── swallow.db                 SQLite 主库 (P2: SQLite-primary truth)
├── swallow.db-wal             WAL 文件(SQLite 自动管理)
├── swallow.db-shm             共享内存文件(SQLite 自动管理)
├── artifacts/
│   ├── <task_id>/             单个任务的 artifact 目录
│   │   ├── <artifact_id>.<ext>
│   │   └── ...
│   └── proposals/             Meta-Optimizer / Librarian 产出的 proposal
│       └── <proposal_id>.json
├── config/
│   ├── routes.toml            Route 配置(可选,首选库内表)
│   └── policy.toml            Policy 配置(可选,首选库内表)
└── logs/
    └── <date>.jsonl           运行日志(非 truth,可清理)
```

`.swl/` 整体可加入 git。`logs/` 应在 `.gitignore` 中标记为不追踪;`swallow.db-wal` 与 `swallow.db-shm` 同样不追踪。

---

## 2. SQLite 命名空间划分

单文件 `swallow.db` 内通过**表名前缀**实现逻辑隔离。同一连接可读跨命名空间(为 retrieval 与 observability 服务),但写操作必须经过对应命名空间的 Repository 类(见 §4)。

| 命名空间 | 前缀 | 承载内容 | 对应 Truth 面 |
|---|---|---|---|
| Task | `task_*` | 任务推进现场、subtask 拓扑、handoff、resume note | Task Truth |
| Event | `event_*` | 过程事件、executor 遥测、降级痕迹、审计线索 | Event Truth |
| Knowledge | `know_*` | Evidence、WikiEntry、staged candidates、canonical registry | Knowledge Truth |
| Route | `route_*` | route metadata、health、telemetry 聚合 | Route Truth |
| Policy | `policy_*` | review threshold、capability floor、retry 上限、subtask 拓扑模板 | Policy Truth |

**禁止**跨命名空间使用外键约束(`FOREIGN KEY`)。跨命名空间引用一律通过 ID 字段进行,不依赖数据库层的引用完整性。理由:

- 各命名空间生命周期不同(task 可归档,knowledge 长期存活)
- 未来可能拆分到独立 DB / 独立进程
- 外键级联会让权限矩阵失效(例如删 task 自动删 knowledge 的引用)

---

## 3. 核心表 Schema

### 3.1 Task 命名空间

```sql
-- 任务主表
CREATE TABLE task_records (
    task_id          TEXT PRIMARY KEY,           -- ULID
    parent_task_id   TEXT,                       -- 子任务的父引用,无外键
    title            TEXT NOT NULL,
    goal             TEXT NOT NULL,
    constraints      JSON,
    workspace_root   TEXT NOT NULL,              -- 相对 git root 的路径(见 §6)
    state            TEXT NOT NULL,              -- pending|running|waiting_human|suspended|completed|failed|cancelled
    attempt          INTEGER NOT NULL DEFAULT 1, -- rerun 计数,每次 rerun +1
    created_at       TEXT NOT NULL,              -- ISO 8601
    updated_at       TEXT NOT NULL,
    archived_at      TEXT,                       -- 软删除/归档时间;NULL 表示活跃
    route_override_hint  JSON,                       -- 任务级 route override(见 INVARIANTS §7.1)
    created_by       TEXT NOT NULL DEFAULT 'local'  -- actor 字段(见 INVARIANTS §7)
);

CREATE INDEX idx_task_active ON task_records(state) WHERE archived_at IS NULL;

-- subtask 拓扑(DAG / tree)
CREATE TABLE task_topology (
    task_id          TEXT NOT NULL,
    depends_on       TEXT NOT NULL,
    relation_kind    TEXT NOT NULL,              -- sequential|parallel|review_gate
    PRIMARY KEY (task_id, depends_on)
);

-- handoff object(结构化任务延续)
CREATE TABLE task_handoffs (
    handoff_id       TEXT PRIMARY KEY,           -- ULID
    task_id          TEXT NOT NULL,
    goal             TEXT NOT NULL,
    done             JSON,                       -- list[str]
    next_steps       JSON,                       -- list[str]
    context_pointers JSON,                       -- list[ContextPointer]
    constraints      JSON,
    created_at       TEXT NOT NULL,
    created_by       TEXT NOT NULL DEFAULT 'local'
);

-- resume note(任务恢复辅助,不是 task state 的替代品)
CREATE TABLE task_resume_notes (
    note_id          TEXT PRIMARY KEY,
    task_id          TEXT NOT NULL,
    content          TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    created_by       TEXT NOT NULL DEFAULT 'local'
);
```
**归档语义**:
- `archived_at` 为软删除/归档标记,不改变任务的 truth 内容,只影响默认查询过滤。Repository 默认查询自动排除 `archived_at IS NOT NULL` 的记录,显式 `include_archived=True` 才返回。归档不是状态迁移,不进入 `state` 字段;状态终态(completed / failed / cancelled)与归档是正交的。
- **Rerun 与 attempt**:Rerun 操作不创建新 `task_id`,而是把现有 task 切回 `running`,同时把 `attempt` 字段 +1。审计时 `(task_id, attempt)` 是定位某次执行的唯一二元组。Event_log 中所有事件都带隐式的 attempt 上下文(可通过 `event_log.timestamp` 与 task state 转换历史交叉确定)。新 task 创建时 `attempt = 1`。


### 3.2 Event 命名空间(append-only)

```sql
-- 事件流(全局 append-only,不允许 UPDATE / DELETE)
CREATE TABLE event_log (
    event_id         TEXT PRIMARY KEY,           -- ULID
    task_id          TEXT,                       -- 可空(系统级事件无 task)
    timestamp        TEXT NOT NULL,
    actor            TEXT NOT NULL DEFAULT 'local',  -- INVARIANTS §7
    kind             TEXT NOT NULL,              -- task_created | step_started | review_failed | ...
    payload          JSON NOT NULL
);

-- 索引:按 task 聚合,按时间排序
CREATE INDEX idx_event_task_time ON event_log(task_id, timestamp);
CREATE INDEX idx_event_kind_time ON event_log(kind, timestamp);

-- executor 遥测(细粒度,Meta-Optimizer 主要消费)
CREATE TABLE event_telemetry (
    telemetry_id     TEXT PRIMARY KEY,
    task_id          TEXT NOT NULL,
    step_id          TEXT,
    executor_id      TEXT NOT NULL,              -- 见 EXECUTOR_REGISTRY
    logical_path     TEXT NOT NULL,              -- A | B | C
    physical_route   TEXT,                       -- 经过的 route id(Path A/C)
    latency_ms       INTEGER,
    token_input      INTEGER,
    token_output     INTEGER,
    cost_usd         REAL,
    degraded         INTEGER NOT NULL DEFAULT 0, -- bool
    error_code       TEXT,
    timestamp        TEXT NOT NULL,
    actor            TEXT NOT NULL DEFAULT 'local'
);
```

### 3.3 Knowledge 命名空间

```sql
-- Evidence:带来源的原始证据
CREATE TABLE know_evidence (
    evidence_id      TEXT PRIMARY KEY,           -- ULID
    content          TEXT NOT NULL,
    source_pointer   JSON,                       -- {kind, ref, locator}
    created_at       TEXT NOT NULL,
    created_by       TEXT NOT NULL DEFAULT 'local'
);

-- WikiEntry:项目级知识编译对象
CREATE TABLE know_wiki (
    wiki_id          TEXT PRIMARY KEY,
    slug             TEXT NOT NULL UNIQUE,
    title            TEXT NOT NULL,
    body             TEXT NOT NULL,
    state            TEXT NOT NULL,              -- draft | active | superseded
    superseded_by    TEXT,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

-- Staged candidates:待审查的知识候选对象
CREATE TABLE know_staged (
    staged_id        TEXT PRIMARY KEY,
    kind             TEXT NOT NULL,              -- evidence | wiki_entry | canonical_record
    payload          JSON NOT NULL,
    source_event     TEXT,                       -- 关联到 event_log.event_id(无外键)
    review_state     TEXT NOT NULL,              -- pending | approved | rejected | superseded
    created_at       TEXT NOT NULL,
    created_by       TEXT NOT NULL DEFAULT 'local'
);

-- Canonical registry:经 review/promotion 的长期规范知识
-- 写入仅通过 apply_proposal,见 §4
CREATE TABLE know_canonical (
    canonical_id     TEXT PRIMARY KEY,
    slug             TEXT NOT NULL UNIQUE,
    body             TEXT NOT NULL,
    promoted_from    TEXT,                       -- staged_id
    promoted_at      TEXT NOT NULL,
    promoted_by      TEXT NOT NULL,              -- operator actor
    superseded_by    TEXT,
    state            TEXT NOT NULL DEFAULT 'active'
);

-- knowledge change log:所有 promotion / rejection / supersede 痕迹
CREATE TABLE know_change_log (
    change_id        TEXT PRIMARY KEY,
    target_kind      TEXT NOT NULL,              -- staged | canonical | wiki
    target_id        TEXT NOT NULL,
    action           TEXT NOT NULL,              -- promote | reject | supersede | dedupe
    rationale        TEXT,
    timestamp        TEXT NOT NULL,
    actor            TEXT NOT NULL
);
```

### 3.4 Route 命名空间

```sql
-- Route 元数据(写入仅通过 apply_proposal)
CREATE TABLE route_registry (
    route_id              TEXT PRIMARY KEY,
    model_family          TEXT NOT NULL,
    model_hint            TEXT NOT NULL,
    dialect_hint          TEXT,
    backend_kind          TEXT NOT NULL,         -- http | cli | local
    transport_kind        TEXT,
    fallback_route_id     TEXT,
    quality_weight        REAL NOT NULL DEFAULT 1.0,
    unsupported_task_types TEXT NOT NULL DEFAULT '[]',   -- JSON list[str]
    cost_profile          TEXT NOT NULL DEFAULT 'null',  -- JSON object or null
    updated_at            TEXT NOT NULL,
    updated_by            TEXT NOT NULL,         -- operator,通过 apply_proposal
    capabilities_json     TEXT NOT NULL DEFAULT '{}',
    taxonomy_json         TEXT NOT NULL DEFAULT '{}',
    execution_site        TEXT NOT NULL,
    executor_family       TEXT NOT NULL,
    executor_name         TEXT NOT NULL,
    remote_capable        INTEGER NOT NULL DEFAULT 0
);

-- Route 健康观测(append-only,Provider Router 写入)
CREATE TABLE route_health (
    health_id        TEXT PRIMARY KEY,
    route_id         TEXT NOT NULL,
    timestamp        TEXT NOT NULL,
    status           TEXT NOT NULL,              -- healthy | degraded | down
    error_code       TEXT,
    sample_size      INTEGER
);

-- Route metadata change log(append-only,Repository 事务内写入)
CREATE TABLE route_change_log (
    change_id        TEXT PRIMARY KEY,
    proposal_id      TEXT,
    target_kind      TEXT NOT NULL,              -- route_registry | route_policy | route_weights | route_capability_profiles
    target_id        TEXT,
    action           TEXT NOT NULL,              -- upsert | delete
    before_payload   TEXT,                       -- JSON snapshot
    after_payload    TEXT,                       -- JSON snapshot
    timestamp        TEXT NOT NULL,
    actor            TEXT NOT NULL DEFAULT 'local'
);
```

Phase 65 实装说明:
- `route_id = RouteSpec.name`,是 human-readable stable key,不是独立 ULID。
- SQLite 无原生 JSON 类型,实现层统一用 `TEXT NOT NULL` 保存 JSON 字符串;空 list 用 `'[]'`,缺失 optional object 用 `'null'`。
- `capabilities_json` 保存 RouteCapabilities 字段,并承载 route capability profile 的 `task_family_scores` 扩展;`unsupported_task_types` 独立列承载 capability profile 的 unsupported list。
- `taxonomy_json` 保存 `{system_role, memory_authority}`。
- `remote_capable` 用 SQLite `INTEGER` 表示 bool。
- 本表通过 `apply_proposal(..., ROUTE_METADATA)` 间接写入;`route_change_log` 记录同事务审计。

### 3.5 Policy 命名空间

```sql
-- Policy 配置(写入仅通过 apply_proposal)
CREATE TABLE policy_records (
    policy_id        TEXT PRIMARY KEY,
    kind             TEXT NOT NULL,              -- review_threshold | retry_limit | capability_floor | ...
    scope            TEXT NOT NULL,              -- global | task_family | executor
    scope_value      TEXT,
    payload          JSON NOT NULL,
    updated_at       TEXT NOT NULL,
    updated_by       TEXT NOT NULL               -- operator,通过 apply_proposal
);

-- Policy change log(append-only,Repository 事务内写入)
CREATE TABLE policy_change_log (
    change_id        TEXT PRIMARY KEY,
    proposal_id      TEXT,
    target_kind      TEXT NOT NULL,              -- audit_trigger_policy | mps_policy
    target_id        TEXT,
    action           TEXT NOT NULL,              -- upsert | delete
    before_payload   TEXT,
    after_payload    TEXT,
    timestamp        TEXT NOT NULL,
    actor            TEXT NOT NULL DEFAULT 'local'
);
```

Phase 65 实装说明:

| 逻辑对象 | `kind` | `scope` | `scope_value` | `policy_id` | `payload` |
|---|---|---|---|---|---|
| route selection policy | `route_selection` | `global` | `NULL` | `route_selection:global` | normalized route policy JSON |
| audit trigger policy | `audit_trigger` | `global` | `NULL` | `audit_trigger:global` | `AuditTriggerPolicy.to_dict()` |
| MPS policy | `mps` | `mps_kind` | `<mps_kind>` | `mps:<mps_kind>` | `{"value": <int>}` |

本表通过 `apply_proposal(..., ROUTE_METADATA)` 或 `apply_proposal(..., POLICY)` 间接写入;`policy_change_log` 记录 policy 写入审计。

---

## 4. Repository 类与写权限白名单

每个命名空间对应一个 Repository 类。**所有写入必须通过 Repository 接口**,禁止裸 SQL 直接 INSERT / UPDATE / DELETE。

| Repository | 模块路径 | 公开写方法 | 允许的调用方 |
|---|---|---|---|
| `TaskRepo` | `swallow.truth.task` | `create_task` / `transition_state` / `record_handoff` / `add_resume_note` | Orchestrator;Operator(via CLI) |
| `EventRepo` | `swallow.truth.event` | `append_event` / `append_telemetry` | 任意执行实体(append-only) |
| `KnowledgeRepo` | `swallow.truth.knowledge` | `add_evidence` / `add_wiki_draft` / `add_staged` / `mark_review_state` | General Executor / Specialist;Operator |
| `RouteRepo` | `swallow.truth.route` | `record_health`(public) / `_apply_metadata_change`(private) | Provider Router(health 写入);`apply_proposal`(metadata 写入) |
| `PolicyRepo` | `swallow.truth.policy` | `_apply_policy_change`(private) | `apply_proposal` |

### 4.1 单一写入入口:`apply_proposal`

```python
# swallow.governance
def apply_proposal(proposal_id: str, operator_token: OperatorToken, target: ProposalTarget) -> ApplyResult:
    """
    canonical knowledge / route metadata / policy 的唯一写入函数。
    其他模块禁止调用 RouteRepo._apply_metadata_change / PolicyRepo._apply_policy_change /
    KnowledgeRepo._promote_canonical(私有方法仅供 apply_proposal 调用)。
    """
```

CI 守卫:`grep '\\b_apply_metadata_change\\b\\|\\b_apply_policy_change\\b\\|\\b_promote_canonical\\b'` 在代码库的命中数应严格等于私有定义本身 + `apply_proposal` 的调用 + 测试。

### 4.2 Append-only 表的写约束

`event_log` / `event_telemetry` / `route_health` / `know_change_log` / `route_change_log` / `policy_change_log` 六张表标记为 append-only:

- Repository 层不暴露 update / delete 方法
- 数据库层加触发器拒绝 UPDATE / DELETE(开发期可选,生产期必须)

```sql
CREATE TRIGGER event_log_no_update BEFORE UPDATE ON event_log
BEGIN SELECT RAISE(FAIL, 'event_log is append-only'); END;

CREATE TRIGGER event_log_no_delete BEFORE DELETE ON event_log
BEGIN SELECT RAISE(FAIL, 'event_log is append-only'); END;
```

---

## 5. 跨命名空间引用规则

- **跨命名空间不使用 `FOREIGN KEY`**(见 §2 末尾)
- **跨命名空间引用必须通过 ID 字段**,字段类型为 `TEXT`,语义由命名清晰表达(`task_id` / `staged_id` / `evidence_id`)
- **不允许嵌入 JSON snapshot 替代引用**:例如 `know_staged.payload` 不应内嵌 task 主表的完整字段,只引用 `task_id`
- **artifact 引用使用 `(task_id, artifact_id)` 二元组**,不存绝对路径

`ContextPointer` 标准结构:

```python
class ContextPointer(TypedDict):
    kind: Literal["artifact", "git_ref", "knowledge", "task", "event"]
    id: str                     # 对应命名空间的主键
    locator: dict | None        # 可选:子定位(行号 / 段落 / commit)
```

---

## 6. 文件系统约束

- `workspace_root` 在 truth 中**存相对 git 仓库根的路径**,绝对路径只在运行时由 `swallow.workspace.resolve_path()` 一处解析(见 INVARIANTS §7)
- Artifact 文件路径**永远是 `<workspace_root>/.swl/artifacts/<task_id>/<artifact_id>.<ext>` 形式**,truth 中只存 `(task_id, artifact_id, ext)`,不存路径字符串
- 守卫测试 `test_no_absolute_path_in_truth_writes` 验证所有 truth 写入字段不出现以 `/` 或盘符开头的字符串

---

## 7. ID 与 Actor 约束

- 所有主键使用 ULID(26 字符,时间可排序,无 hostname / username)
- ID 生成函数集中在 `swallow.identity.new_id(kind: str) -> str`,不允许在多处自行 `uuid.uuid4()` 或 `ulid_new()`
- `actor` 字段默认值 `"local"`,该字面量只允许在 `swallow.identity.local_actor()` 内出现
- 守卫测试见 INVARIANTS §9

---

## 8. Migration 与版本

```sql
CREATE TABLE schema_version (
    version          INTEGER NOT NULL,
    applied_at       TEXT NOT NULL,
    slug             TEXT NOT NULL
);
```

- 每次 schema 变更必须 +1 version 并提交 migration 脚本到 `swallow/migrations/<version>_<slug>.sql`
- 不向后兼容的 migration 必须在 PR 中显式标记 `BREAKING-MIGRATION` 标签,并附带:数据保全策略、回滚步骤、对 INVARIANTS §5 矩阵的影响评估
- Migration 不允许在运行时静默执行;`swl` 启动时检测 schema 落后会进入 `waiting_human`,提示运行 `swl migrate`
- `首次建表(table creation on fresh DB)` 不属于本节 migration 范围,由 `sqlite_store.py:_connect` 内 `CREATE TABLE IF NOT EXISTS` 一次性维护;`schema_version` 在首次建表后直接 INSERT `version=1, slug='phase65_initial'`。

---

## 9. 与其他文档的接口

| 对接文档 | 接口关系 |
|---|---|
| `INVARIANTS.md` | §5 权限矩阵 → §4 Repository 白名单;§7 埋点 → §6 / §7 |
| `STATE_AND_TRUTH.md` | 描述真值面的语义边界与状态迁移;本文档承载其物理 schema |
| `KNOWLEDGE.md` | 描述知识对象的治理工作流;本文档承载其表结构 |
| `PROVIDER_ROUTER.md` | 描述 route 选择逻辑;本文档承载 `route_registry` / `route_health` 表 |
| `SELF_EVOLUTION.md` | 描述 `apply_proposal` 的调用语义;本文档定义其私有方法约束 |
