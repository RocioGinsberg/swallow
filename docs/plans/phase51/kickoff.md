---
author: claude
phase: 51
slice: kickoff
status: draft
depends_on:
  - docs/plans/phase51/context_brief.md
  - docs/roadmap.md
  - docs/design/SELF_EVOLUTION.md
  - docs/design/AGENT_TAXONOMY.md
---

## TL;DR
Phase 51 是战略级关键，完成"自我观察 → 提案生成 → operator 审批 → 自动应用"的完整闭环。核心是落地 Meta-Optimizer 独立 Agent、实装提案应用流程与 operator gate、自动化一致性审计触发。系统从"有感遥测"进化到"主动优化"。

# Phase 51 Kickoff: 策略闭环与 Specialist Agent 落地

## 基本信息

| 字段 | 值 |
|------|-----|
| Phase | 51 |
| Primary Track | Evaluation / Policy + Agent Taxonomy |
| Secondary Track | Provider Routing |
| 目标 tag | v0.8.0 (Policy Era) |
| 前置 phase | Phase 50  |

## 战略定位

Phase 51 是系统从"被动记录"到"主动优化"的战略跃迁。

**蓝图要求**（`SELF_EVOLUTION.md`）：系统应能通过"自我观察 → 提案生成 → operator 审批 → 自动应用"的完整闭环实现自我进化。所有变更必须经过 operator gate，不允许静默突变。

**当前现状**：Meta-Optimizer 已能扫描遥测数据并生成结构化提案，但提案应用流程缺失——operator 无法审批、系统无法自动应用。这导致宝贵的反馈信号被浪费，路由和策略演进滞后于业务实际。

**Phase 51 的使命**：完成提案应用流程、落地 Meta-Optimizer 独立 Agent、实装一致性审计自动化触发。使系统具备"自我反思 → 自我改进"的能力。

## 目标 (Goals)

1. **Meta-Optimizer 提案应用流程**：设计与实装 operator review → apply 的完整工作流。包括提案持久化、operator gate、应用审计、回滚机制。
2. **Meta-Optimizer 独立 Agent 生命周期**：落地 Meta-Optimizer 作为独立 Specialist Agent（类似 Librarian）。定义其输入/输出边界、权限模型、与 Orchestrator 的协作接口。
3. **一致性审计自动化触发**：将只读的一致性抽检升级为可配置的自动化触发策略。支持基于 task 特征、route 质量、成本等维度的触发规则。
4. **Route 能力画像扩展**：实装能力画像评分机制与 `unsupported_task_types` 字段。支持路由决策时的能力边界守卫。

## 非目标 (Non-Goals)

- **不自动应用提案**：所有提案应用必须经过 operator 审批，不存在"自动突变"的路径。
- **不落地其他 Specialist Agent**：Ingestion / Literature / Quality Reviewer / Consistency Reviewer 等角色留待 Phase 52。
- **不修改 Librarian 流程**：Phase 51 不涉及知识沉淀工作流的改造。
- **不做 CLIAgentExecutor 全异步化**：执行器升级留待 Phase 51。
- **不做多租户或分布式部署**：系统仍为单机本地优先。

## 设计边界

- **Operator Gate 是必经之路**：提案应用前必须有 operator 审批，不存在绕过的机制。
- **Meta-Optimizer 为独立 Agent**：参照 `LibrarianAgent` 的实现模式，具备独立生命周期、受控输出边界、与 Orchestrator 的协作接口。
- **一致性审计异步触发**：基于可配置的 `AuditTriggerPolicy`，fire-and-forget 异步触发，不阻塞主执行路径。
- **Route 能力画像与路由决策解耦**：能力画像是 route 的元数据，路由决策时可选择是否启用能力边界守卫。
- **提案应用审计可追踪**：每次提案应用都应产出审计日志，支持回滚与重放。

## Slice 列表

| Slice | 名称 | 顺序依赖 | 目标 |
|-------|------|----------|------|
| S1 | Meta-Optimizer 结构化提案 | 无 | 将提案从文本升级为结构化 dataclass，支持 route/workflow 类型 |
| S2 | 一致性审计自动化触发 | S1 | 实装可配置的自动化审计触发策略，支持 verdict 解析 |
| S3 | Route 能力画像与质量权重 | S1 | 实装能力画像评分机制与 unsupported_task_types 字段 |
| S4 | Meta-Optimizer 独立 Agent 生命周期 | S1, S2, S3 | 落地 Meta-Optimizer 作为独立 Specialist Agent |

**依赖关系**：
- S1 是基础，S2、S3、S4 均依赖 S1 的提案结构化。
- S4 依赖 S1、S2、S3 完成，因为独立 Agent 需要整合所有提案类型。
- 建议顺序：S1 → S2 / S3（并行）→ S4。

## 每个 Slice 的详细目标与验收条件

### Slice 1: Meta-Optimizer 结构化提案

**目标**：将提案从文本升级为结构化 dataclass，支持 route/workflow 类型。

**验收条件**：
- [ ] `OptimizationProposal` dataclass 包含 `proposal_type`、`priority`、`rationale`、`suggested_action`
- [ ] `build_optimization_proposals()` 返回 `list[OptimizationProposal]`
- [ ] 支持 route 类型提案（路由失败率、降级率等）
- [ ] 支持 workflow 类型提案（debate retry 率、成本离群等）
- [ ] 提案持久化到 `.swl/optimization_proposals/` 目录
- [ ] 原有 eval 测试通过

### Slice 2: 一致性审计自动化触发

**目标**：实装可配置的自动化审计触发策略。

**验收条件**：
- [ ] `AuditTriggerPolicy` dataclass 支持基于 task 特征、route 质量、成本等维度的触发规则
- [ ] `schedule_consistency_audit()` 实现 fire-and-forget 异步触发
- [ ] `ConsistencyAuditResult` 新增 `verdict` 字段（`pass` / `fail` / `inconclusive`）
- [ ] `swl audit policy show/set` CLI 入口可用
- [ ] 审计触发不阻塞主执行路径
- [ ] 测试覆盖触发条件、verdict 解析、policy 持久化

### Slice 3: Route 能力画像与质量权重

**目标**：实装能力画像评分机制与 unsupported_task_types 字段。

**验收条件**：
- [ ] `RouteSpec` 新增 `quality_weight` 字段（默认 1.0）
- [ ] `candidate_routes()` 按 quality_weight 排序
- [ ] `swl route weights show/apply` CLI 可用
- [ ] 权重持久化到 `.swl/route_weights.json`
- [ ] Meta-Optimizer 可产出 route_weight 类提案
- [ ] 测试覆盖权重排序、持久化、CLI 操作

### Slice 4: Meta-Optimizer 独立 Agent 生命周期

**目标**：落地 Meta-Optimizer 作为独立 Specialist Agent。

**验收条件**：
- [ ] `MetaOptimizerAgent` 类实装，具备 `execute()` / `execute_async()` 接口
- [ ] 输入/输出边界清晰（输入：event log / route telemetry，输出：OptimizationProposal 列表）
- [ ] 与 Orchestrator 的协作接口定义清晰
- [ ] 权限模型：只读 Agent，不直接修改系统配置
- [ ] 每次执行产出 `MetaOptimizerSnapshot`（包含扫描时间、提案列表、诊断信息）
- [ ] 测试覆盖 Agent 生命周期、输出结构、与 Orchestrator 的集成

## 关键风险与缓解策略

| 风险 | 影响 | 缓解策略 |
|------|------|---------|
| Operator Gate 流程复杂度高 | 降低系统易用性 | 设计简洁的 CLI 接口，提供清晰的提案摘要与应用预览 |
| 提案应用失败导致系统不一致 | 数据污染 | 实装原子性应用与回滚机制，所有应用都产出审计日志 |
| 一致性审计异步触发的时序问题 | 审计结果过时 | 审计结果附带时间戳，operator 可判断是否需要重新审计 |
| Route 能力画像维护成本高 | 元数据过时 | 能力画像作为可选元数据，不强制维护；Meta-Optimizer 可定期扫描并建议更新 |
| Meta-Optimizer 与 Librarian 的职责边界模糊 | 设计混乱 | 明确定义：Librarian 负责知识沉淀，Meta-Optimizer 负责系统优化提案 |

## 完成条件

- [ ] S1 完成：提案结构化，支持 route/workflow 类型
- [ ] S2 完成：一致性审计可基于配置自动触发
- [ ] S3 完成：Route 能力画像与质量权重可配置与查询
- [ ] S4 完成：Meta-Optimizer 作为独立 Agent 可被 Orchestrator 触发
- [ ] 所有现有 pytest 通过（395+ tests）
- [ ] 新增 Phase 51 相关测试覆盖提案应用、Agent 生命周期、自动触发等场景
- [ ] 文档更新：`docs/design/SELF_EVOLUTION.md` 与 `docs/design/AGENT_TAXONOMY.md` 的实现部分已同步
- [ ] 无 `[BLOCK]` 级 review comment

## 与 Phase 51-52 的协作边界

**Phase 51 完成的是**：
- 提案结构化与持久化机制
- 一致性审计自动化触发
- Route 能力画像与质量权重
- Meta-Optimizer 独立 Agent 的生命周期模式

**Phase 51 将复用**：
- Phase 51 的 `schedule_consistency_audit()` 异步触发模式与 CLIAgentExecutor 的全异步改造共享执行上下文

**Phase 52 将复用**：
- Phase 51 的 Meta-Optimizer 独立 Agent 模式作为其他 5 个 Specialist Agent（Ingestion / Literature / Quality Reviewer / Consistency Reviewer / Validator）的参照实现

## 关键参考资源

- `docs/design/SELF_EVOLUTION.md` — 自我进化与记忆沉淀的蓝图要求
- `docs/design/AGENT_TAXONOMY.md` — Specialist Agent 的定义与职责边界
- `src/swallow/librarian_executor.py` — LibrarianAgent 的实现参照
- `docs/plans/phase49/closeout.md` — Phase 49 的完成状态与交接信息