---
author: claude
phase: 51
slice: design
status: draft
depends_on: ["docs/plans/phase51/kickoff.md", "docs/plans/phase51/context_brief.md", "docs/design/SELF_EVOLUTION.md", "docs/design/AGENT_TAXONOMY.md", "docs/design/ORCHESTRATION.md"]
---

TL;DR: Phase 51 完成"自我观察 → 提案生成 → operator 审批 → 自动应用"的完整闭环。核心设计：(1) Operator Gate 强制审批，不自动应用；(2) Meta-Optimizer 升级为独立 Agent 实体；(3) 一致性审计 fire-and-forget 异步触发；(4) Route 能力画像基于隐式信号自动聚合。

---

## 方案总述

Phase 51 的核心是将系统从"有感遥测"进化到"主动优化"。系统已在 Phase 49 完成知识真值归一，具备完整的遥测数据捕获能力（token 成本、一致性审计结果、降级事件）。Phase 51 的使命是将这些数据转化为**可感知的策略行为**，实现系统的自我观察与自我优化。

实现路径分四步：

1. **S1 - 提案应用流程**：设计 operator gate 机制，确保所有提案应用都经过显式审批，不自动突变生产策略
2. **S2 - Meta-Optimizer 独立 Agent**：参照 LibrarianAgent 模式，将 Meta-Optimizer 升级为类实体，具备独立生命周期与受控权限
3. **S3 - 审计自动化触发**：实装 AuditTriggerPolicy 自动触发工作流，fire-and-forget 异步执行，不阻塞主路径
4. **S4 - Route 能力画像**：基于隐式信号（历史执行结果、成本效益、降级频率）自动聚合能力评分，支持多候选时的评分匹配

---

## 核心设计决策

### 决策 1: Operator Gate 强制审批，不自动应用

**问题**：系统生成的优化提案应该如何应用？是自动应用还是需要人工审批？

**候选方案**：
- A. 自动应用：系统自动执行提案，提高效率但风险高
- B. 强制审批：所有提案需 operator 手动审批与应用，风险低但效率低
- C. 混合模式：低风险提案自动应用，高风险提案需审批

**选择方案**：B（强制审批）

**理由**：
- 蓝图原则 P7："Proposal over Mutation"——系统自我改进以提案为主，不自动突变
- 系统仍处于演进阶段，自动应用可能引入不可预见的副作用
- operator 审批提供了显式的人工控制点，便于审计与追溯
- 后续可基于提案质量与历史成功率逐步放宽审批条件

**实现**：
- 提案持久化到 `.swl/proposals/` 目录
- operator 通过 `swl proposal review <proposal-file>` 审批
- 审批记录（approved / rejected / deferred）持久化
- 通过 `swl proposal apply <review-record>` 应用已审批的提案
- 应用为幂等操作，重复应用不产生副作用

---

### 决策 2: Meta-Optimizer 升级为独立 Agent 实体

**问题**：Meta-Optimizer 应该如何组织？是保持函数化还是升级为独立 Agent？

**候选方案**：
- A. 保持函数化：`run_meta_optimizer()` 函数，简单但不符合 Specialist Agent 体系
- B. 升级为独立 Agent：`MetaOptimizerAgent` 类，复杂但符合蓝图与后续 Phase 52 的需求
- C. 混合模式：保留函数化接口，内部调用 Agent 实体

**选择方案**：B（升级为独立 Agent）

**理由**：
- `AGENT_TAXONOMY.md` 定义 Meta-Optimizer 为 `specialist / cloud-backed / read-only / workflow-optimization`
- Phase 52 的其他 5 个 Specialist Agent 落地将复用此模式，需要建立统一的 Agent 生命周期
- LibrarianAgent 已落地为参照模式，复用度高
- 独立 Agent 实体便于权限管理、输入/输出边界定义、与 Orchestrator 的协作

**实现**：
- 创建 `MetaOptimizerAgent` 类，继承或参照 `LibrarianAgent` 的结构
- 实现 `execute(base_dir, state, card, retrieval_items) -> ExecutorResult` 方法
- 实现 `execute_async()` 异步包装
- 定义权限模型：`system_role = "specialist"`、`memory_authority = "read-only"`
- 在 `MetaOptimizerAgent` 中集成 `build_meta_optimizer_snapshot()` 与 `build_optimization_proposals()` 逻辑
- 提案输出为 `OptimizationProposal` 列表，进入 S1 的审批流程

---

### 决策 3: 一致性审计 fire-and-forget 异步触发

**问题**：一致性审计应该如何触发？是同步等待还是异步触发？

**候选方案**：
- A. 同步等待：task 完成后同步执行审计，等待审计结果，简单但可能阻塞主路径
- B. 异步触发（fire-and-forget）：task 完成后异步触发审计，不等待结果，复杂但不阻塞主路径
- C. 后台队列：审计任务进入队列，由独立 worker 处理

**选择方案**：B（异步触发 fire-and-forget）

**理由**：
- 审计是可选的质量检查，不影响主任务的成功/失败判定
- 同步等待可能导致任务完成延迟，影响用户体验
- fire-and-forget 模式简单可靠，不需要额外的队列管理
- 审计失败不影响主路径，降级处理即可

**实现**：
- 在 `AsyncSubtaskOrchestrator.run_task_async()` 完成后，检查 `AuditTriggerPolicy`
- 如果满足触发条件，调用 `asyncio.create_task(schedule_consistency_audit_async(...))`
- 不 await 审计结果，立即返回
- 审计结果异步写入 `.swl/tasks/{task_id}/artifacts/consistency_audit_*.md`
- 审计失败记录日志，不影响主任务状态

---

### 决策 4: Route 能力画像基于隐式信号自动聚合

**问题**：Route 的能力应该如何评估？是手动配置还是自动聚合？

**候选方案**：
- A. 手动配置：operator 手动为每条 route 配置能力评分，精确但维护成本高
- B. 自动聚合：从历史执行结果自动聚合能力评分，低维护但可能不准确
- C. 混合模式：自动聚合为基础，operator 可手动调整

**选择方案**：C（混合模式，优先自动聚合）

**理由**：
- 自动聚合基于真实数据（成功率、review 通过率、retry 次数、成本），更准确
- operator 可手动调整，保留人工控制点
- 能力画像与 quality_weight 正交：权重是 operator 配置，能力画像是系统观测
- 后续可基于能力画像产出优化提案（Meta-Optimizer 可产出能力画像更新提案）

**实现**：
- 从 event truth 扫描历史执行结果，计算成功率、review 通过率、retry 次数、成本等
- 基于隐式信号推断能力评分（例如：成功率高 → 推理能力强、review 通过率高 → 代码编辑能力强）
- 能力画像持久化到 `.swl/route_capabilities.json`
- 多候选时按能力评分排序，单候选时不变
- operator 可通过 `swl route capabilities update` 手动调整

---

## 与蓝图的对齐

| 蓝图原则 | Phase 51 实现 | 对齐度 |
|---------|-------------|--------|
| **P7: Proposal over Mutation** | Operator Gate 强制审批，不自动应用 | ✅ 完全对齐 |
| **SELF_EVOLUTION.md** | 完整的"观察 → 提案 → 审批 → 应用"闭环 | ✅ 完全对齐 |
| **AGENT_TAXONOMY.md** | Meta-Optimizer 升级为独立 Specialist Agent | ✅ 完全对齐 |
| **ORCHESTRATION.md** | operator gate 作为显式的人工控制点 | ✅ 完全对齐 |

---

## 与现有系统的集成点

### 1. 与 Orchestrator 的集成

- **触发点**：`AsyncSubtaskOrchestrator.run_task_async()` 完成后
- **集成方式**：插入审计触发检查点（≤10 行代码）
- **影响**：无，仅添加 fire-and-forget 异步任务

### 2. 与 EventLog 的集成

- **读取**：Meta-Optimizer 扫描 EventLog 生成提案
- **写入**：审计结果、提案应用记录写入 EventLog
- **影响**：无，仅追加新的事件类型

### 3. 与 SQLite 的集成

- **新增表**：`optimization_proposals`（提案）、`proposal_review_records`（审批记录）
- **修改表**：无（保持现有 schema 稳定）
- **影响**：低，仅新增表，不修改现有 schema

### 4. 与 CLI 的集成

- **新增命令**：`swl proposal review`、`swl proposal apply`、`swl audit policy show/set`、`swl route capabilities show/update`
- **修改命令**：无
- **影响**：低，仅新增命令

---

## 明确的非目标

- **不自动应用提案**：所有提案需 operator 手动审批
- **不落地其他 Specialist Agent**：仅落地 Meta-Optimizer，其他 5 个留待 Phase 52
- **不修改 SQLite 主 schema**：权重、能力画像、审计策略等配置存储在独立文件
- **不实现 Web UI 扩展**：所有操作通过 CLI 完成
- **不做跨任务并发审计**：审计为 fire-and-forget，不管理并发队列
- **不引入新的 LLM 调用**：verdict 解析用正则，提案生成基于启发式规则
- **不做自动权重衰减或学习**：权重调整需 operator 手动执行

---

## 验收条件

| Slice | 验收条件 |
|-------|---------|
| **S1** | ✓ 提案可持久化到 SQLite ✓ operator 可审批与应用提案 ✓ 提案应用前后状态可审计 ✓ 应用失败时可回滚 ✓ 集成测试覆盖完整工作流 |
| **S2** | ✓ `MetaOptimizerAgent` 类实装完成 ✓ 权限模型清晰定义 ✓ 与 Orchestrator 协作接口设计完成 ✓ 单元测试覆盖 Agent 生命周期 ✓ 集成测试验证与 Orchestrator 协作 |
| **S3** | ✓ AuditTriggerPolicy 支持多维度触发条件 ✓ 触发评估逻辑完整 ✓ 异步调度机制稳定 ✓ CLI 入口可用 ✓ 集成测试覆盖完整工作流 |
| **S4** | ✓ RouteCapabilityProfile 数据结构完成 ✓ 能力画像评分逻辑实装 ✓ Strategy Router 集成完成 ✓ CLI 入口可用 ✓ 单元测试覆盖评分逻辑 |

---

## 关键风险与缓解

| 风险 | 影响 | 缓解策略 |
|------|------|---------|
| Operator gate 机制复杂度高 | 可能引入新 bug | 充分的单元测试 + 集成测试 + 手动验证 |
| Meta-Optimizer 独立 Agent 与现有函数化实现冲突 | 可能破坏现有逻辑 | 保持向后兼容性，逐步迁移 |
| 一致性审计自动化可能导致过度审计 | 系统负载增加 | 可配置的触发规则，支持关闭 |
| Route 能力画像评分不准确 | 路由决策偏差 | 基于历史数据，operator 可手动调整 |
| Phase 51 改造可能破坏 fire-and-forget 语义 | 审计触发失败 | 在 Phase 51 kickoff 时明确协作边界 |

---

## 实现时间估算

| 任务 | 估算工时 |
|------|---------|
| S1 - 提案应用流程 | 16h |
| S2 - Meta-Optimizer Agent | 12h |
| S3 - 审计自动化工作流 | 10h |
| S4 - 能力画像评分 | 12h |
| 测试与集成 | 16h |
| 文档 | 8h |
| **总计** | **74h**（不含 S4）/ **86h**（含 S4） |
