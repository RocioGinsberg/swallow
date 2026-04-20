---
author: claude
phase: 48
slice: kickoff
status: draft
depends_on:
  - docs/plans/phase48/context_brief.md
  - docs/plans/phase48/kickoff.md
---

## TL;DR
Phase 48 分 5 个 slice 推进异步化与 SQLite 迁移：先建异步基础（S1），再并行化 ReviewGate（S2）与 SQLite 双存储（S3），最后完成 Orchestrator 全异步（S4）与存储切换（S5）。S4、S5 为高风险，需人工 gate。

---

# Phase 48 Design Decision: 存储引擎升级与全异步改造

## 方案总述

Phase 48 以两条并行主线推进：**异步化主线**（S1→S2→S4）消除 N-Reviewer 顺序执行瓶颈，**存储主线**（S3→S5）将 TaskState 与 EventLog 从散乱 JSON 文件迁移至 SQLite 事务层。两条主线在 S4+S5 合流，共同支撑高并发任务树。`sqlite-vec` 向量扩展不在本 Phase 范围，延至 Phase 49。Markdown Artifact 继续生成，定位为导出视图而非真值。

---

## Slice 拆解

### S1: `async-executor` — 异步基础设施

**目标**：将 `HTTPExecutor` 的 `httpx` 同步调用切换为异步模式；引入 `pytest-asyncio`，建立异步测试模式；为后续 slice 提供可用的异步执行器协议。

**影响范围**：
- `src/swallow/executor.py`：`HTTPExecutor.execute()` → `async def execute()`
- `pyproject.toml` / `requirements*.txt`：添加 `pytest-asyncio`
- `tests/`：添加 `asyncio_mode = "auto"` 配置，现有同步测试不受影响

**关键决策**：
- `CLIAgentExecutor` 保持同步，通过 `asyncio.to_thread()` 桥接，不在本 slice 改造
- `ExecutorProtocol` 新增 `async def execute_async()` 方法，与同步 `execute()` 并存，过渡期两者均有效
- `httpx.AsyncClient` 使用 context manager 管理生命周期，不做全局单例

**风险评级**：
- 影响范围：2（单模块）
- 可逆性：1（轻松回滚，接口并存）
- 依赖复杂度：1（无外部系统依赖）
- **总分：4（低风险）**

**验收条件**：
- `HTTPExecutor` 可通过 `await executor.execute_async(...)` 调用
- `pytest-asyncio` 配置就绪，`tests/test_executor_async.py` 通过
- 现有 359 个同步测试无回归

---

### S2: `async-review-gate` — ReviewGate 并行 N-Reviewer

**目标**：将 `review_gate.py` 中的顺序 Reviewer 调用改为 `asyncio.gather` 并发执行，N-Reviewer 场景下总耗时接近单路耗时而非 N 倍叠加。

**影响范围**：
- `src/swallow/review_gate.py`：核心审查循环异步化
- `src/swallow/orchestrator.py`：调用 ReviewGate 的位置适配 `await`
- `tests/test_review_gate*.py`：补充并发场景测试

**关键决策**：
- `asyncio.gather(*reviewer_tasks, return_exceptions=True)` 收集所有 Reviewer 结果，异常不中断其他 Reviewer
- 共识聚合逻辑（majority / veto）保持不变，只改执行并发度
- 超时控制：每个 Reviewer 调用加 `asyncio.wait_for(timeout=...)`，超时视为 `CONCERN`

**风险评级**：
- 影响范围：2（review_gate + orchestrator 调用点）
- 可逆性：2（需同步回滚 orchestrator 调用点）
- 依赖复杂度：2（依赖 S1 的异步 executor）
- **总分：6（中风险）**

**验收条件**：
- 3 路 Reviewer 并发耗时 ≤ 单路耗时 × 1.3（mock 计时测试）
- majority / veto 共识结果与顺序执行一致（回归测试）
- 单 Reviewer 超时不影响其他 Reviewer 完成

---

### S3: `sqlite-schema` — SQLite Schema + 双存储

**目标**：设计并实现 SQLite schema，将 `TaskState` 与 `EventLog` 映射为数据库表；实现 `SqliteTaskStore` 与现有 `FileTaskStore` 并存，通过配置切换。

**影响范围**：
- `src/swallow/sqlite_store.py`（新文件）：`SqliteTaskStore` 实现
- `src/swallow/store.py`：抽取 `TaskStoreProtocol`，现有实现重命名为 `FileTaskStore`
- `src/swallow/paths.py`：添加 `.swl/swallow.db` 路径常量
- `src/swallow/models.py`：确认 `TaskState` / `Event` 可序列化为 JSON 列

**Schema 设计**：
```sql
-- tasks 表：TaskState 快照
CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    state_json TEXT NOT NULL,       -- TaskState 完整 JSON
    status TEXT NOT NULL,           -- 冗余索引列，便于查询
    updated_at TEXT NOT NULL
);

-- events 表：EventLog 追加写
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    event_json TEXT NOT NULL,       -- Event 完整 JSON
    kind TEXT NOT NULL,             -- 冗余索引列
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
);

-- 索引
CREATE INDEX idx_events_task_id ON events(task_id);
CREATE INDEX idx_tasks_status ON tasks(status);
```

**关键决策**：
- 使用 `PRAGMA journal_mode=WAL` 支持并发读写
- TaskState 以 JSON 列整体存储（不拆列），避免 schema 与 models.py 强耦合
- 冗余 `status` / `kind` 列仅用于查询过滤，真值以 JSON 列为准
- 双存储通过 `SWALLOW_STORE_BACKEND=sqlite|file` 环境变量切换，默认仍为 `file`

**风险评级**：
- 影响范围：3（跨 store / models / paths 模块）
- 可逆性：2（新文件，回滚删除即可；store.py 重构需额外工作）
- 依赖复杂度：1（`sqlite3` 标准库，无外部依赖）
- **总分：6（中风险）**

**验收条件**：
- `SqliteTaskStore` 通过与 `FileTaskStore` 相同的接口测试套件
- WAL 模式下并发写入无数据损坏（并发测试）
- `SWALLOW_STORE_BACKEND=sqlite swl run ...` 可完整执行一次任务

---

### S4: `async-orchestrator` — Orchestrator 全异步 ⚠️ 高风险

**目标**：将 `orchestrator.py` 的 `_debate_loop_core` 与 `subtask_orchestrator.py` 的调度主循环迁移至 `async/await`；CLI 入口适配 `asyncio.run()`。

**影响范围**：
- `src/swallow/orchestrator.py`：`_debate_loop_core` 及所有调用链
- `src/swallow/subtask_orchestrator.py`：子任务调度循环
- `src/swallow/cli.py`：`run` / `rerun` / `resume` 命令入口包裹 `asyncio.run()`
- `src/swallow/harness.py`：`run_retrieval` 等被 orchestrator 调用的函数按需异步化

**关键决策**：
- 迁移策略：自底向上（executor → review_gate → orchestrator），确保每层异步化后测试通过再向上推进
- `harness.py` 中的文件 IO 操作（`write_task_artifacts` 等）通过 `asyncio.to_thread()` 桥接，不全量改写
- `threading.Lock` 替换为 `asyncio.Lock`，避免在 async 上下文中阻塞事件循环
- 保留同步 `execute()` 接口作为兼容层，供非 async 调用路径使用

**[SCOPE WARNING]**：此 slice 的传染性最强，几乎触及 `src/swallow/` 所有核心函数。必须严格控制改动范围，不得顺手重构无关逻辑。

**风险评级**：
- 影响范围：3（跨模块，orchestrator / subtask / cli / harness）
- 可逆性：3（async 传染性强，回滚需大量工作）
- 依赖复杂度：3（依赖 S1 + S2 完成，且与 S5 有合流点）
- **总分：9（高风险）— 需人工 gate，建议拆分验证**

**验收条件**：
- `swl run` / `swl rerun` / `swl resume` 在异步模式下可完整执行
- 子任务并行调度可验证（2 路子任务并发，耗时 ≤ 顺序耗时 × 1.3）
- 全量 pytest 无回归

---

### S5: `store-cutover` — SQLite 切为默认存储 + 迁移工具 ⚠️ 高风险

**目标**：将 SQLite 切换为默认存储后端；提供 `swl migrate` 命令，将现有 `.swl/<task-id>/` JSON 文件导入 SQLite；更新 `paths.py` 定义 `.swl/swallow.db`。

**影响范围**：
- `src/swallow/store.py`：默认后端切换为 `SqliteTaskStore`
- `src/swallow/cli.py`：添加 `swl migrate` 子命令
- `src/swallow/paths.py`：`swallow_db_path()` 常量
- `docs/`：更新 CLI 使用说明（如有）

**迁移策略**：
- `swl migrate --dry-run`：扫描 `.swl/` 目录，报告可迁移任务数，不写入
- `swl migrate`：逐任务读取 JSON → 写入 SQLite，成功后保留原 JSON 文件（不删除，作为备份）
- 迁移幂等：已存在于 SQLite 的 task_id 跳过，不覆盖

**关键决策**：
- 切换后文件存储作为只读回退（`SWALLOW_STORE_BACKEND=file` 可强制回退）
- 不自动删除旧 JSON 文件，由 operator 手动清理
- `swl doctor` 命令添加 SQLite 健康检查项

**风险评级**：
- 影响范围：3（store / cli / paths / harness 全链路）
- 可逆性：2（环境变量可回退到 file 模式，但默认行为已变）
- 依赖复杂度：2（依赖 S3 + S4 完成）
- **总分：7（高风险）— 需人工 gate**

**验收条件**：
- 新建任务默认写入 SQLite，`swl inspect` 可正常读取
- `swl migrate` 对现有测试 fixture 数据无损迁移
- `SWALLOW_STORE_BACKEND=file` 回退后系统行为与 Phase 47 一致
- `swl doctor` 输出 SQLite 状态检查结果

---

## 依赖说明

```
S1 (async-executor)
  └─→ S2 (async-review-gate)
        └─→ S4 (async-orchestrator)  ←─┐
                                        ├─ 合流验证
S3 (sqlite-schema)                      │
  └─→ S5 (store-cutover) ──────────────┘
```

- S2 必须在 S1 完成后启动（依赖异步 executor 协议）
- S4 必须在 S1 + S2 完成后启动（orchestrator 调用 review_gate）
- S5 必须在 S3 完成后启动（依赖 SqliteTaskStore 实现）
- S4 与 S3 可并行推进
- 最终集成验证在 S4 + S5 均完成后进行

---

## 明确的非目标

- `sqlite-vec` 向量扩展（Phase 49）
- `CLIAgentExecutor` 异步化（按需延后）
- 知识库（WikiStore / EvidenceStore）迁移至 SQLite（Phase 49）
- Web 控制中心读取 SQLite 的适配（Phase 49）
- ORM 引入（直接使用 `sqlite3` 标准库）
- 自动删除旧 JSON 文件

---

## 验收条件汇总

| Slice | 关键验收条件 |
|-------|-------------|
| S1 | HTTPExecutor 异步可调用；pytest-asyncio 就绪；无回归 |
| S2 | 3 路并发耗时 ≤ 单路 × 1.3；共识结果一致性回归通过 |
| S3 | SqliteTaskStore 接口测试通过；WAL 并发写入无损坏 |
| S4 | `swl run` 异步执行完整；子任务并发验证通过；全量无回归 |
| S5 | 默认 SQLite 存储；迁移无损；file 模式可回退 |
