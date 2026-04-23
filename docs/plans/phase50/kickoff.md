---
author: claude
phase: 50
slice: kickoff
status: draft
depends_on: ["docs/roadmap.md", "docs/plans/phase50/context_brief.md"]
---

TL;DR: Phase 50 目标是把现有的孤立审计/遥测能力连接成闭环——Meta-Optimizer 产出结构化提案、一致性审计可自动触发、路由器可消费质量信号调整权重。非目标：不做真正的自动路由切换，不做 UI，不改 SQLite schema 主结构。

# Phase 50 Kickoff: 路由策略闭环与专项审计

## Track & Phase

- **Primary Track**: Evaluation / Policy
- **Secondary Track**: Provider Routing
- **Phase**: 50
- **前置 Phase**: 49 (v0.7.0, Knowledge SSOT & Vector RAG)

## 目标

将现有的孤立审计与遥测能力连接成可感知的策略闭环：

1. Meta-Optimizer 从"文本建议"升级为"结构化提案 + workflow 提案"
2. 一致性审计从"手动调用"升级为"可配置自动触发"
3. 路由器从"静态权重"升级为"可消费质量信号的动态权重"

## 非目标（本 phase 刻意不做）

- **不做自动路由切换**：权重调整建议由 operator 审批后手动应用，不自动变更生产路由
- **不做 Web UI**：所有入口通过 CLI，不扩展 `swl serve` 仪表盘
- **不改 SQLite 主 schema**：route weight 持久化使用独立轻量存储，不修改 `swallow.db` 的核心表结构
- **不做跨任务并发审计**：自动触发策略为单任务粒度，不做批量并发审计
- **不做 LLM-based 路由决策**：权重调整基于规则/阈值，不引入新的 LLM 调用

## Slice 拆解

### S1: Meta-Optimizer 结构化提案

**目标**：将 `build_optimization_proposals()` 的输出从纯文本升级为结构化 dataclass，并补充 `workflow_optimization_proposal`。

**影响范围**：`meta_optimizer.py`, `models.py`, `tests/test_meta_optimizer.py`

**验收条件**：
- `OptimizationProposal` dataclass 包含 `proposal_type`（route/workflow）、`severity`（info/warn/critical）、`route_name`（可选）、`description`、`suggested_action`
- `build_optimization_proposals()` 返回 `list[OptimizationProposal]`
- 新增 workflow 类提案：debate retry 率过高、task family 成本离群
- `build_meta_optimizer_report()` 从结构化提案渲染，输出格式不变
- 原有 eval 测试通过

### S2: 一致性审计自动触发策略

**目标**：在 harness 执行完成后，根据可配置策略决定是否自动触发一致性审计。

**影响范围**：`consistency_audit.py`, `harness.py`（或 orchestrator），`models.py`（AuditTriggerPolicy），`cli.py`

**验收条件**：
- `AuditTriggerPolicy` dataclass：`enabled`、`trigger_on_degraded`、`trigger_on_cost_above`、`auditor_route`
- harness/orchestrator 在任务完成后检查 policy，满足条件则 fire-and-forget 触发审计（不阻塞主路径）
- `ConsistencyAuditResult` 新增 `verdict` 字段（`pass` / `fail` / `inconclusive`），从 LLM 输出中解析
- `swl audit policy show/set` CLI 入口
- 测试覆盖：触发条件满足/不满足、verdict 解析、policy 持久化

### S3: 路由质量权重

**目标**：RouteRegistry 支持 per-route 质量权重，Meta-Optimizer 提案可建议权重调整，operator 通过 CLI 应用。

**影响范围**：`router.py`（RouteRegistry, RouteSpec），`meta_optimizer.py`（新增权重建议提案），`cli.py`

**验收条件**：
- `RouteSpec` 新增可选 `quality_weight: float = 1.0`（1.0 = 正常，< 1.0 = 降权，0.0 = 禁用）
- `candidate_routes()` 在多候选时按 quality_weight 排序（高权重优先）
- Meta-Optimizer 可产出 `proposal_type=route_weight` 提案，包含建议权重值
- `swl route weights show/apply <proposal-file>` CLI：show 显示当前权重，apply 从提案文件应用
- 权重持久化到 `.swl/route_weights.json`（独立于 swallow.db）
- 测试覆盖：权重排序、apply/show CLI、权重持久化与加载

## 依赖顺序

```
S1 (结构化提案) → S3 (权重提案需要 OptimizationProposal 结构)
S2 (审计触发) → S3 (audit verdict 可作为权重调整信号，但 S3 不强依赖 S2)
```

S1 必须先于 S3。S2 可与 S3 并行，但建议 S2 先完成以便 S3 可引用 verdict。

## 完成条件

- [ ] S1: `OptimizationProposal` 结构化，workflow 提案覆盖，原有 eval 通过
- [ ] S2: `AuditTriggerPolicy` 可配置，harness 集成，verdict 解析，CLI 入口
- [ ] S3: `quality_weight` 字段，候选排序，CLI apply/show，持久化
- [ ] 所有新增功能有对应测试，`pytest` 全量通过
- [ ] `docs/active_context.md` 更新到 phase50 实现态

## 设计边界

- route weight 是 operator 工具，不是自动决策器——所有权重变更需人工 `apply` 确认
- 审计触发是 fire-and-forget，不影响任务结果，不写入任务 state
- Meta-Optimizer 仍然只读，不直接修改任何路由状态
