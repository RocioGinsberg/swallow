---
author: claude
phase: 31
slice: runtime-v0
status: draft
depends_on: [docs/roadmap.md, docs/plans/phase30/closeout.md]
---

> **TL;DR**: Phase 31 将当前隐式的文档驱动调度转化为代码驱动的 Runtime v0 中枢。核心产出：Planner（Task Card 标准化）、统一 Executor Interface、Review Gate（Schema 校验门禁）。

# Phase 31 Kickoff — Runtime v0 与统一执行器抽象

## 基本信息

- **Phase**: 31
- **Primary Track**: Core Loop
- **Secondary Track**: Execution Topology
- **Phase 名称**: Runtime v0 — Planner + Executor Interface + Review Gate

---

## 目标

1. **引入 Planner 模块**：将宏观目标转化为标准化的 Task Card（结构化的子任务描述），建立从"用户意图"到"可执行子任务"的代码化拆解路径。
2. **定义统一 Executor Interface**：将现有的直连执行（`run_execution`）和未来的 Agent Executor（如 Codex CLI Wrapper）纳入同一抽象接口，使 orchestrator 不再硬编码执行路径。
3. **引入 Review Gate**：所有 Executor 产出在写入 state/artifact 前，强制通过 Schema 校验与基本通过性检查。

---

## 非目标

- ❌ 动态能力协商（Router 根据 executor capabilities 自动选择最优路径）——留给 Phase 34
- ❌ 并发子任务编排（Subtask Orchestrator）——留给 Phase 33
- ❌ 语义级审查（Review Gate 做内容质量判断）——留给 Phase 33+
- ❌ Dialect 自动适配（Prompt 格式按 executor 自动装配）——留给 Phase 34
- ❌ 降级 fallback（executor 故障时自动切换）——留给 Phase 34
- ❌ Planner 使用 LLM 进行智能拆解——v0 只做静态/规则驱动拆解

---

## 设计边界

### Planner v0 边界
- 输入：用户意图（goal string + optional hints）
- 输出：一个或多个 Task Card（结构化 dataclass，包含 goal、input schema、expected output schema、assigned route hint）
- v0 的拆解策略是**规则驱动**（基于 task type / domain hint 做静态映射），不调用 LLM

### Executor Interface 边界
- 定义 `ExecutorProtocol`：统一 `execute(task_card) -> ExecutorResult` 签名
- 当前的 `run_execution()` 重构为 `LocalCLIExecutor` 实现该协议
- `MockExecutor` 同步适配
- 不引入新的外部 executor（如真实 API executor），只建立接口

### Review Gate 边界
- 位于 executor 产出与 state 写入之间
- v0 只做：output schema 校验、必填字段检查、artifact 格式验证
- 校验失败时：标记 `review_gate_status: failed`，触发 event 记录，不自动 retry（retry 由 orchestrator 现有 retry_policy 决定）
- 不做内容语义审查

### Router 调整
- 现有 `select_route()` 保持不变
- 新增：Route 选择结果附带 `executor_type` 标签，Planner 据此决定 Task Card 分发目标

---

## 完成条件

1. `TaskCard` dataclass 定义在 `models.py`，包含 goal / input_schema / output_schema / route_hint / constraints
2. `Planner` 模块能将单个 goal 拆解为 1+ 个 Task Card（规则驱动）
3. `ExecutorProtocol` 定义完成，`LocalCLIExecutor` 和 `MockExecutor` 实现该协议
4. `ReviewGate` 在 executor 产出后执行 schema 校验，结果写入 event log
5. `orchestrator.run_task()` 重构为 Planner → Executor → ReviewGate 流程
6. 所有现有测试通过（回归安全）
7. 新增测试覆盖 Planner 拆解、Executor Protocol、ReviewGate 校验

---

## Slice 拆解建议

| Slice | 目标 | 风险评级 |
|-------|------|----------|
| S1: TaskCard + Planner v0 | 定义 TaskCard 模型，实现规则驱动的 Planner | 低 (影响 1 / 可逆 1 / 依赖 1 = 3) |
| S2: ExecutorProtocol + 适配 | 定义统一接口，重构 LocalCLI 和 Mock executor | 中 (影响 2 / 可逆 2 / 依赖 2 = 6) |
| S3: ReviewGate + 流程串联 | 引入 ReviewGate，重构 run_task() 主流程 | 中 (影响 2 / 可逆 2 / 依赖 2 = 6) |

建议按 S1 → S2 → S3 顺序串行推进。S2 依赖 S1 的 TaskCard 定义，S3 依赖 S2 的 ExecutorProtocol。
