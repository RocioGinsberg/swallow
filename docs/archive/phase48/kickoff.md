---
author: claude
phase: 48
slice: kickoff
status: draft
depends_on:
  - docs/plans/phase48/context_brief.md
  - docs/roadmap.md
---

## TL;DR
Phase 48 将系统从同步阻塞模型迁移至全异步架构，并引入 SQLite（WAL 模式）作为 TaskState 与 EventLog 的事务真值层，彻底消除 N-Reviewer 顺序执行瓶颈。`sqlite-vec` 向量扩展延至 Phase 49。

---

# Phase 48 Kickoff: 存储引擎升级与全异步改造

## 基本信息

| 字段 | 值 |
|------|----|
| Phase | 48 |
| Primary Track | Core Loop |
| Secondary Track | State / Truth |
| 目标版本 | v0.6.0 (Async Era) |
| 前置 Phase | Phase 47 (v0.5.0, 已收口) |
| 预期分支 | `feat/phase48_async-storage` |

---

## Goals（本 Phase 要做的）

1. **ReviewGate 并行化**：将 N-Reviewer 的顺序调用改为 `asyncio.gather` 并发执行，消除多 Reviewer 场景下的线性耗时叠加。
2. **HTTPExecutor 异步化**：将 `httpx` 同步调用切换为异步模式，作为全链路异步化的基础。
3. **Orchestrator 全异步**：将 `_debate_loop_core`、`subtask_orchestrator` 的核心调度链路迁移至 `async/await`，CLI 入口适配 `asyncio.run()`。
4. **SQLite 状态真值层**：引入 SQLite（WAL 模式）作为 `TaskState` 与 `EventLog` 的持久化后端，替代散乱的 JSON 文件，提供事务保证。
5. **双存储过渡**：实现 `SqliteTaskStore` 与现有文件存储并存，提供从 `.swl/` JSON 文件到 `.swl/swallow.db` 的迁移路径。

---

## Non-Goals（本 Phase 刻意不做的）

- **`sqlite-vec` 向量扩展**：引入二进制依赖风险高，延至 Phase 49（RAG 闭环阶段）。
- **向量化 RAG**：Phase 49 的核心任务，不在本 Phase 范围内。
- **CLIAgentExecutor 异步化**：子进程调用的异步改造（`asyncio.create_subprocess_exec`）复杂度高，且 CLI executor 使用频率低于 HTTP executor，延至后续 phase 按需处理。
- **Web 控制中心异步适配**：`swl serve` 的 FastAPI 层已是异步，无需改动；但 Web 层读取 SQLite 的适配留至 Phase 49。
- **知识库（WikiStore / EvidenceStore）迁移至 SQLite**：知识层迁移依赖 RAG 设计，与 Phase 49 协同，本 Phase 只迁移 TaskState + EventLog。
- **多租户 / 分布式 worker**：超出当前系统边界。

---

## 设计边界

- Markdown Artifact（`executor_output.md`、`evidence_*.md` 等）继续生成，定位为"导出视图"而非真值。
- SQLite 使用 WAL 模式，支持并发读写；不引入 ORM，直接使用 `sqlite3` 标准库。
- 异步化范围：`executor.py`（HTTPExecutor）、`review_gate.py`、`orchestrator.py`、`subtask_orchestrator.py`、`cli.py` 入口。
- 同步兼容层：`CLIAgentExecutor` 保持同步，通过 `asyncio.to_thread` 或 `loop.run_in_executor` 桥接。
- 测试框架：引入 `pytest-asyncio`，现有同步测试不受影响。

---

## Slice 列表

| Slice | 名称 | 核心目标 | 风险 |
|-------|------|----------|------|
| S1 | `async-executor` | HTTPExecutor 异步化 + pytest-asyncio 基础设施 | 低 |
| S2 | `async-review-gate` | ReviewGate 并行 N-Reviewer | 中 |
| S3 | `sqlite-schema` | SQLite schema + SqliteTaskStore 双存储 | 中 |
| S4 | `async-orchestrator` | Orchestrator + SubtaskOrchestrator 全异步 | 高 |
| S5 | `store-cutover` | SQLite 切为默认存储 + 迁移工具 | 高 |

依赖顺序：S1 → S2 → S4；S3 → S5；S4 + S5 可并行后合流。

---

## 完成条件（Phase Gate）

Phase 48 视为完成，当且仅当：

- [ ] 所有 5 个 slice 的验收条件均已满足
- [ ] `pytest`（非 eval）全部通过，无回归
- [ ] `swl run` 在 SQLite 模式下可完整执行一次任务（含 N-Reviewer 并行）
- [ ] N-Reviewer 3 路并行耗时 ≤ 单路耗时 × 1.3（验证并行效果）
- [ ] 旧 `.swl/` JSON 数据可通过迁移命令导入 SQLite，无数据丢失
- [ ] `docs/plans/phase48/closeout.md` 已写完
- [ ] `current_state.md` 已更新 checkpoint
