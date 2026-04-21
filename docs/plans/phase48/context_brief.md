---
author: gemini
phase: 48
slice: kickoff
status: draft
depends_on:
  - docs/roadmap.md
  - docs/plans/phase47/closeout.md
---

## TL;DR
Phase 48 将系统从同步阻塞模型推向 **Async Era (v0.6.0)**。核心任务是实现 `Orchestrator` 与 `Executor` 的全异步化，并引入 `SQLite` 作为状态与事件的事务真值层，解决 N-Reviewer 与多路子任务的并发瓶颈。

# Context Brief: Phase 48 - Storage Engine Upgrade & Full Async Refactoring

## 变更范围

本 Phase 是跨模块的结构性重构，主要影响以下核心组件：

- **编排层 (`orchestrator.py`, `subtask_orchestrator.py`)**：`_debate_loop_core` 及任务调度循环需迁移至 `async/await`。
- **执行层 (`executor.py`, `librarian_executor.py`)**：`HTTPExecutor` 的 `httpx` 调用需切换至异步模式；`CLIAgentExecutor` 的子进程调用需改用 `asyncio.create_subprocess_exec`。
- **门禁层 (`review_gate.py`)**：共识审查逻辑由顺序执行改为 `asyncio.gather` 并发执行。
- **持久化层 (`store.py`, `knowledge_store.py`, `models.py`)**：引入 `sqlite3` 后端，将 `TaskState`、`EventLog` 与知识条目从散乱的 JSON/MD 文件迁移至数据库事务。
- **入口层 (`cli.py`, `paths.py`)**：适配异步入口点，并定义 `.swl/swallow.db` 路径。

## 近期变更摘要 (Git History)

- `docs(state): sync phase47 closeout after v0.5.0 tag` (Recent) - 系统进入 v0.5.0，共识门禁已稳固。
- `feat(cli): add manual consistency audit command` (Phase 47) - 引入了只读审计逻辑。
- `feat(policy): add task card token cost guardrails` (Phase 47) - 状态更新现已包含实时成本聚合。
- `feat(consensus): add multi-reviewer review gate` (Phase 47) - 为多模型并发审查提供了逻辑基础（目前为同步顺序执行）。

## 关键上下文

1. **同步阻塞瓶颈**：当前的 N-Reviewer 实现是顺序调用的，这意味着若配置 3 个 Reviewer，总耗时将是三者之和。这是下一阶段实现多路子任务并行的主要障碍。
2. **状态碎片化**：`.swl/` 下的文件系统虽然直观，但在并发写入（如子任务返回结果时）缺乏原子性。`LibrarianExecutor` 的“伪原子提交”通过 `os.replace` 实现，但在数据库事务面前仍显薄弱。
3. **Artifact 的双重性**：虽然真值将迁移至 SQLite，但为了保持 operator-facing 的可读性，系统仍需保留生成 Markdown Artifacts（如 `executor_output.md`, `evidence_*.md`）的能力，但这应被视为“导出的视图”而非“唯一的真值”。
4. **方言适配器**：`dialect_adapters/` 目前主要是字符串处理，异步化改造对其逻辑影响较小，但需确保调用链的连贯。

## 风险信号

1. **破坏性重构**：从 `def` 到 `async def` 的迁移是具有传染性的，几乎会触及 `src/swallow/` 的所有核心函数。必须分 slice 稳健推进，优先保证主循环不中断。
2. **测试覆盖**：现有的 359 个同步测试需要适配异步运行时。可能需要引入 `pytest-asyncio`。
3. **二进制依赖**：`sqlite-vec` 向量扩展在某些环境（如 ARM 或某些 Linux 发行版）下的安装可能存在挑战，需提供回退或明确的安装指引。
4. **向后兼容性**：需处理旧版 `.swl/` 目录结构向 SQLite 数据库的平滑迁移逻辑。

## 建议关注点

- **SQL 模式设计**：避免过度设计，优先将现有的 `models.py` 结构映射为表。
- **并发控制**：在 `asyncio` 环境下，文件系统操作仍可能存在竞态，SQLite 的 WAL 模式是关键。
- **Debug 复杂度**：异步代码的 Traceback 较难阅读，需在 Event Log 中保持高质量的异步上下文信息。
