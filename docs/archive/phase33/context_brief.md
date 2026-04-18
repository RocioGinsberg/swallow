---
author: gemini
phase: 33
slice: none_selected
status: draft
depends_on: [docs/roadmap.md, docs/active_context.md]
---

# Context Brief: Phase 33 — Subtask Orchestrator & 并发编排

## TL;DR
本阶段旨在将系统从“单任务静态执行”升级为“多子任务并发编排”模式。引入 `Subtask Orchestrator` 处理任务拆解与并发下发，建立 `Review Feedback Loop` 实现自动打回重试。

## 变更范围

### 核心模块
- `src/swallow/planner.py`: 重构 `plan()` 函数，使其支持根据任务复杂度和 `TaskState` 产出多个 `TaskCard`。
- `src/swallow/orchestrator.py`: 引入 `SubtaskOrchestrator` 组件，负责协调多个子任务的生命周期、并发控制与结果聚合。
- `src/swallow/models.py`: 扩展 `TaskCard` 或新增 `SubtaskState` 以支持父子任务关系跟踪及并发执行状态标识。
- `src/swallow/executor.py`: 优化执行引擎以支持异步/并发调用底层 Executor。
- `src/swallow/review_gate.py`: 扩展反馈机制，支持产出能被 Orchestrator 识别的 `retry` 或 `re-plan` 信号。

### 新增模块 (预期)
- `src/swallow/subtask_orchestrator.py`: 专门的并发子任务调度中枢。
- `src/swallow/literature_specialist.py`: 作为并发编排验证的轻量级本地/便宜模型执行器示例。

## 近期变更摘要 (Git History)
- `b01ba97`: 同步 Phase 32 收口状态至 `active_context.md`。
- `abbc363`: 合并 Phase 32：知识双层架构与 Librarian Agent，确立了知识晋升防线。
- `8a29471`: 实现 `LibrarianExecutor`，支持规则驱动的知识提纯与 Change Log 产出。
- `5824659`: 强化 `canonical-promotion` 权限校验，引入 Librarian 身份标识。
- `11aba11`: 引入 `knowledge_store.py`，实现 Evidence Store 与 Wiki Store 的物理分离。
- `c6804c7`: 将 Gateway 融合设计内化至 `ARCHITECTURE.md` 和设计蓝图。

## 关键上下文
- **知识层并发风险**: Phase 32 引入的双层存储（Evidence/Wiki）目前主要为顺序读写设计。并发子任务若同时尝试写回知识，需在 `store.py` 或 `knowledge_store.py` 层面增加锁定或合并机制。
- **Librarian 角色定位**: 所有的子任务知识产出应先进入 `Staged Candidate`，最终通过父任务或独立的 `Librarian` 任务进行统一晋升，避免并发写入 Canonical Memory 导致冲突。
- **Review 信号增强**: 当前 `ReviewGate` 仅做 Schema 校验和通过性检查。本阶段需定义明确的“打回”协议，使 `Orchestrator` 能根据 Review 结果决定是结束任务、重试当前 Card 还是请求 `Planner` 重新规划。

## 风险信号
- **局部最优陷阱**: 仅实现简单的 `concurrent.futures` 调度可能无法处理复杂的子任务依赖。需确保 `SubtaskOrchestrator` 的设计预留了拓扑依赖处理的空间。
- **上下文膨胀**: 并发执行多个子任务可能导致 `TaskState` 中的 `events` 迅速膨胀，影响长上下文模型的性能。建议同步考虑事件摘要或分片存储策略。
