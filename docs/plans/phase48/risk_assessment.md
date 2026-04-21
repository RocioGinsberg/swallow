---
author: claude
phase: 48
slice: kickoff
status: draft
depends_on:
  - docs/plans/phase48/context_brief.md
  - docs/plans/phase48/design_decision.md
---

## TL;DR
Phase 48 整体风险等级为高。S4（Orchestrator 全异步）和 S5（存储切换）是最高风险点，需人工 gate。最大威胁是 async 传染性导致的测试覆盖断层，以及 SQLite 切换后的数据迁移完整性。

---

# Phase 48 Risk Assessment

## 一、风险矩阵

> 评分维度：影响范围（1=单文件 2=单模块 3=跨模块）× 可逆性（1=轻松回滚 2=需额外工作 3=难以回滚）× 依赖复杂度（1=无外部依赖 2=依赖内部模块 3=依赖外部系统）
> 总分 ≥7 标注为高风险。

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 风险等级 |
|-------|---------|--------|-----------|------|---------|
| S1: async-executor | 2 | 1 | 1 | **4** | 低 |
| S2: async-review-gate | 2 | 2 | 2 | **6** | 中 |
| S3: sqlite-schema | 3 | 2 | 1 | **6** | 中 |
| S4: async-orchestrator | 3 | 3 | 3 | **9** | **高 ⚠️** |
| S5: store-cutover | 3 | 2 | 2 | **7** | **高 ⚠️** |

---

## 二、高风险项详析

### R1: Async 传染性导致测试覆盖断层（S4，最高优先级）

**描述**：`async def` 的传染性会使 `orchestrator.py` 的改动扩散至 `harness.py`、`store.py`、`cli.py` 等多个模块。现有 359 个同步测试中，凡是直接调用 orchestrator 的测试均需适配 `pytest-asyncio`，存在大规模测试改写风险。

**影响**：若测试适配不完整，可能出现"代码改了但测试仍通过"的假阳性，掩盖真实回归。

**缓解措施**：
1. S1 完成后立即建立 `asyncio_mode = "auto"` 配置，确保现有同步测试不受影响
2. S4 开始前，Codex 需先列出所有直接调用 orchestrator 的测试文件，逐一确认适配计划
3. S4 分两步推进：先迁移 `_debate_loop_core`（单函数），验证通过后再迁移 `subtask_orchestrator`
4. 人工 gate：S4 完成后，全量 pytest 必须通过，方可进入 S5

---

### R2: SQLite 切换后数据迁移完整性（S5，次高优先级）

**描述**：`.swl/<task-id>/` 目录下的 JSON 文件结构复杂（TaskState、EventLog、Artifact 等多种文件），迁移脚本需正确处理所有边界情况（缺失字段、旧版 schema、损坏文件）。

**影响**：迁移失败或数据丢失将导致历史任务不可恢复，影响 operator 信任度。

**缓解措施**：
1. `swl migrate --dry-run` 必须先于实际迁移执行，输出详细的可迁移/不可迁移任务清单
2. 迁移过程中保留原 JSON 文件，不自动删除
3. 迁移后执行 `swl migrate --verify`，对比 SQLite 与 JSON 文件的 task_id 列表与关键字段
4. 测试 fixture 中包含"旧版 schema"场景，确保迁移脚本的向后兼容性

---

### R3: `asyncio.Lock` 替换 `threading.Lock` 的遗漏（S4）

**描述**：`orchestrator.py` 中存在 `threading.Lock` 用于并发保护。若在 async 上下文中遗漏替换，将导致事件循环阻塞，表现为随机性死锁或性能退化，难以复现。

**影响**：生产环境中的随机性阻塞，调试成本极高。

**缓解措施**：
1. S4 开始前，Codex 需 grep 所有 `threading.Lock` / `threading.RLock` 使用点，逐一评估是否需要替换
2. 文件 IO 操作（`write_task_artifacts` 等）通过 `asyncio.to_thread()` 桥接，不在事件循环中直接执行阻塞 IO
3. 添加 `asyncio.get_event_loop().is_running()` 断言，在关键路径上检测意外的同步阻塞

---

### R4: SQLite WAL 模式下的并发写入竞态（S3/S5）

**描述**：WAL 模式支持多读单写，但在高并发子任务场景下，多个 coroutine 同时写入 `events` 表可能触发 `SQLITE_BUSY` 错误。

**影响**：事件丢失或任务状态不一致。

**缓解措施**：
1. 设置 `PRAGMA busy_timeout = 5000`（5 秒等待），避免立即失败
2. `SqliteTaskStore` 的写入操作通过 `asyncio.to_thread()` 执行，避免在事件循环中直接调用 `sqlite3`（`sqlite3` 不是线程安全的异步库）
3. 长期方案：若并发压力持续增大，Phase 49 可评估引入 `aiosqlite`

---

## 三、中风险项

### R5: pytest-asyncio 版本兼容性（S1）

**描述**：`pytest-asyncio` 的 `asyncio_mode = "auto"` 在不同版本行为有差异（0.21+ 与旧版），可能导致现有同步测试被误标记为异步。

**缓解措施**：锁定 `pytest-asyncio>=0.23`，在 `pyproject.toml` 中明确配置 `asyncio_mode = "auto"`，并在 S1 完成后立即运行全量测试验证。

---

### R6: ReviewGate 超时策略的共识影响（S2）

**描述**：`asyncio.wait_for` 超时后将 Reviewer 结果视为 `CONCERN`，可能在网络抖动时意外触发 veto 策略，导致任务被错误阻断。

**缓解措施**：超时阈值通过 `TaskCard` 配置（默认 60s），不硬编码；超时事件写入 EventLog，便于 operator 审查。

---

## 四、依赖风险

| 依赖关系 | 风险 | 说明 |
|---------|------|------|
| S2 依赖 S1 | 低 | S1 接口稳定，S2 只需调用 `execute_async` |
| S4 依赖 S1+S2 | 中 | S4 开始前需确认 S1+S2 全量测试通过 |
| S5 依赖 S3+S4 | 高 | S5 是最终集成点，任何上游未解决的问题都会在此暴露 |

---

## 五、人工 Gate 建议

| Gate 点 | 触发条件 | 检查内容 |
|---------|---------|---------|
| Gate-1 | S1 完成后 | pytest 全量通过；asyncio_mode 配置正确 |
| Gate-2 | S4 完成后 | pytest 全量通过；`swl run` 异步执行验证；threading.Lock 替换清单确认 |
| Gate-3 | S5 完成后 | `swl migrate --verify` 无损确认；file 模式回退验证；`swl doctor` SQLite 健康检查通过 |

---

## 六、Phase 整体风险评估

**综合风险等级：高**

Phase 48 是 v0.5.0 以来最大规模的结构性重构，async 传染性与存储切换的叠加效应使整体风险显著高于前序 phase。建议：

1. **严格按 slice 顺序推进**，不跳跃、不并行启动高风险 slice
2. **每个 slice 完成后立即运行全量测试**，不积累技术债
3. **S4 是最高风险点**，建议 Codex 在实现前与 Claude 确认 `threading.Lock` 替换清单
4. **Phase 49 的 `sqlite-vec` 依赖**已从本 Phase 移除，降低了二进制依赖风险
