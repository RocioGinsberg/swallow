---
author: claude
phase: 33
slice: subtask-orchestrator
status: draft
depends_on: [docs/roadmap.md, docs/plans/phase32/closeout.md, docs/plans/phase33/context_brief.md]
---

> **TL;DR**: Phase 33 将 Planner 从 1:1 静态映射升级为 1:N 拆解，引入 SubtaskOrchestrator 进行顺序/并发子任务编排，并建立 ReviewGate → retry 的单向反馈链路。Literature Specialist 和 Debate Topology 延后。

# Phase 33 Kickoff — Subtask Orchestrator 与并发编排

## 基本信息

- **Phase**: 33
- **Primary Track**: Execution Topology
- **Secondary Track**: Core Loop
- **Phase 名称**: Subtask Orchestrator + 并发编排 (1:N Planner + Review Feedback Loop)

---

## 前置依赖与现有基础

Phase 31 Runtime v0 checkpoint：
- `TaskCard` + `Planner v0`（1:1 静态映射）
- `ExecutorProtocol`（统一执行器接口）
- `ReviewGate`（无状态 Schema 校验，不参与 completion/retry 决策）
- `run_task()` 三段式：Planner → Executor → ReviewGate

Phase 32 知识层 checkpoint：
- Evidence/Wiki 双层存储（当前顺序读写，无并发保护）
- LibrarianExecutor（规则驱动，直接操作 state——已知技术债）
- `caller_authority` 权限校验

**关键约束**：
- `run_task()` 当前只取 `cards[0]`（`orchestrator.py:1156`），多卡产出被忽略
- `Planner.plan()` 已返回 `list[TaskCard]`，但只会产出 1 张卡
- ReviewGate 结果当前不影响 `state.status` 计算（`orchestrator.py:1357-1365`）
- knowledge_store 无并发写入保护

---

## 目标

1. **1:N Planner 升级**：`plan()` 可根据任务复杂度产出多张 TaskCard，支持声明子任务间的依赖关系（顺序/并行标注）。
2. **SubtaskOrchestrator**：新增编排组件，负责按依赖拓扑调度多张 TaskCard 的执行，支持顺序执行和基础并发（`concurrent.futures.ThreadPoolExecutor`）。
3. **Review Feedback Loop**：ReviewGate 结果参与 completion 决策——失败时触发单次 retry，retry 仍失败则标记 `failed` 并上报。

---

## 非目标

- ❌ Debate / Review Topology（双向自动协商）——路线图明确延后，跨模块复杂度 ≥7
- ❌ Literature Specialist——延后至 Phase 33 stretch 或 Phase 34，可作为并发编排验证的 PoC 但不是本轮核心
- ❌ LLM 驱动的智能 Planner——1:N 拆解仍为规则驱动（基于 task_semantics 中的 hints/constraints）
- ❌ 动态 executor negotiation / capability-based routing——留给 Phase 34
- ❌ knowledge_store 并发锁——本轮子任务共享父任务的 knowledge view，不独立写回（避免并发写冲突）
- ❌ 事件流分片/摘要——context_brief 提到的膨胀风险，本轮通过限制最大并发数（≤4）控制

---

## 设计边界

### 1:N Planner 边界

- `plan()` 新增规则：当 `task_semantics.constraints` 中包含 `parallel_subtasks` hint，或 `next_action_proposals` 包含多个可独立执行的动作时，产出多张 TaskCard
- 每张 TaskCard 新增字段：
  - `depends_on: list[str]`——依赖的其他 card_id（空列表 = 可并行）
  - `subtask_index: int`——在父任务中的顺序编号
- v0 拆解上限：最多 4 张子任务卡（硬限制，防止膨胀）
- Librarian TaskCard 逻辑保持不变（优先级高于 1:N 拆解——如果有 promotion_ready evidence，仍走 librarian 路径）

### SubtaskOrchestrator 边界

- **新模块**：`subtask_orchestrator.py`
- 输入：`list[TaskCard]` + `TaskState` + `base_dir`
- 行为：
  1. 按 `depends_on` 构建 DAG
  2. 无依赖的卡并行下发（`ThreadPoolExecutor(max_workers=4)`）
  3. 有依赖的卡等前置完成后串行下发
  4. 每张卡执行完毕后独立过 ReviewGate
  5. 收集所有 `ExecutorResult` + `ReviewGateResult`，聚合为父任务结果
- 输出：`SubtaskOrchestratorResult`（包含每张卡的执行结果 + review 结果 + 聚合状态）
- **不做**：跨子任务的知识写回、子任务级 state 持久化（子任务结果只存在于内存中，最终由父任务 run_task 汇总写入）

### Review Feedback Loop 边界

- ReviewGate 结果参与 `run_task()` 的 completion 判定：
  - 所有子任务 review 通过 → completed
  - 任一子任务 review 失败 → 触发**单次 retry**（重新执行该子任务的 TaskCard）
  - retry 后仍失败 → 标记 `failed`，记录 `review_gate_retry_exhausted` 事件
- retry 次数硬限制：1 次（v0 不做多次 retry 或 re-plan）
- **不做**：retry 后自动 re-plan（让 Planner 重新拆解）——那是 Debate Topology 的范畴

### run_task() 集成边界

- `run_task()` 中 `cards = plan(state)` 后：
  - 如果 `len(cards) == 1`：保持现有单卡路径不变
  - 如果 `len(cards) > 1`：调用 `SubtaskOrchestrator.run(cards, state, ...)`
- 子任务执行的 artifact 写入父任务的 artifacts 目录下（前缀 `subtask_{index}_`）
- 子任务不创建独立的 TaskState，不写入独立的 events.jsonl——所有事件记录在父任务的 event log 中（前缀 `subtask.{index}.`）

---

## 完成条件

1. `TaskCard` 新增 `depends_on` 和 `subtask_index` 字段
2. `plan()` 能在规则条件满足时产出 2-4 张有依赖关系的 TaskCard
3. `subtask_orchestrator.py` 实现 DAG 调度 + 并发执行 + 结果聚合
4. ReviewGate 结果参与 completion 判定，失败触发单次 retry
5. `run_task()` 在多卡场景下调用 SubtaskOrchestrator
6. 子任务 artifact 和 event 按约定写入父任务目录
7. 所有现有测试通过（回归安全）
8. 新增测试覆盖：1:N planner、SubtaskOrchestrator（顺序/并发/依赖/retry）、ReviewGate retry 集成

---

## Slice 拆解

| Slice | 目标 | 关键文件 | 风险评级 |
|-------|------|----------|----------|
| S1: TaskCard 扩展 + 1:N Planner | 新增 depends_on/subtask_index 字段，plan() 支持多卡产出 | 改 `models.py`，改 `planner.py` | 低 (影响 1 / 可逆 1 / 依赖 1 = 3) |
| S2: SubtaskOrchestrator 核心 | DAG 调度 + 并发执行 + 结果聚合 | 新建 `subtask_orchestrator.py` | 中 (影响 2 / 可逆 2 / 依赖 2 = 6) |
| S3: Review Feedback Loop + run_task 集成 | ReviewGate retry + run_task 多卡分支 + artifact/event 集成 | 改 `orchestrator.py`，改 `review_gate.py` | 中高 (影响 3 / 可逆 2 / 依赖 2 = 7) |

### 依赖关系

```
S1 (TaskCard + 1:N Planner)
  └──→ S2 (SubtaskOrchestrator)
         └──→ S3 (Review Loop + 集成)
```

串行推进。S2 需要 S1 的多卡 TaskCard 才能调度。S3 需要 S2 的 orchestrator 才能集成进 run_task。

---

## 风险评估

### R1: run_task() 改动范围（中高）
- **风险**：`run_task()` 当前有 400 行，是系统核心循环。在其中插入多卡分支可能影响单卡路径的回归安全
- **缓解**：多卡分支通过 `if len(cards) > 1` 显式分叉，单卡路径完全不变。SubtaskOrchestrator 作为独立模块，不修改 run_task 内部逻辑
- **检验**：现有全量测试必须在 S3 完成后全部通过

### R2: 并发写入安全（中）
- **风险**：并发子任务可能同时写 artifact 文件或 event log
- **缓解**：
  - artifact 写入使用 `subtask_{index}_` 前缀，物理隔离
  - event log 使用 `threading.Lock` 保护 append 操作
  - 子任务不写 state.json（只有父任务的 run_task 最终写入）
  - 子任务不写 knowledge_store（避免双层存储并发问题）
- **检验**：并发测试用例验证 artifact 不交叉

### R3: Scope 膨胀——Debate Topology 渗透（中）
- **风险**：Review Feedback Loop 容易滑入 re-plan / 双向协商
- **缓解**：硬限制 retry = 1 次，retry 只重新执行同一 TaskCard，不重新 plan。任何 re-plan 需求记录为 `review_gate_replan_needed` 事件但不执行
- **检验**：代码中无 `plan()` 的二次调用

### R4: 事件流膨胀（低）
- **风险**：4 个并发子任务各自产生多个事件，events.jsonl 迅速增长
- **缓解**：最大并发数硬限制 4，子任务事件使用精简 payload（不复制整个 state snapshot），后续 Phase 35 的 Meta-Optimizer 可消费这些事件
- **检验**：集成测试验证事件总数在可控范围

---

## 风险评分

| 维度 | 评分 (1-3) | 说明 |
|------|-----------|------|
| 影响范围 | 3 | 改动 run_task 核心循环 + 新增并发执行路径 |
| 可逆性 | 2 | 多卡分支可通过 feature flag 关闭，但并发代码回滚需要谨慎 |
| 外部依赖 | 1 | 纯内部重构，只用 stdlib concurrent.futures |
| 状态突变 | 2 | 子任务不独立持久化，但 artifact/event 写入模式变化 |
| 并发风险 | 3 | 首次引入真正的多线程并发执行 |
| **总分** | **11/15** | **中高风险**（与 roadmap 评估一致） |

---

## 与 concerns_backlog 的关系

Phase 32 记录的 LibrarianExecutor state mutation 技术债（concerns_backlog Open 项）：本轮**不消化**。LibrarianExecutor 仍走单卡路径，不进入 SubtaskOrchestrator 的并发分支，因此不会因并发而暴露该问题。消化时机推迟到 Phase 34（executor side effect 收敛）。
