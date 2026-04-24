---
author: claude
phase: 47
slice: all
status: draft
depends_on:
  - docs/roadmap.md
  - docs/plans/phase47/context_brief.md
  - docs/plans/phase46/closeout.md
---

> **TL;DR**: Phase 47 目标是在 Phase 46 提供的真实多模型分发能力基础上，引入 N-Reviewer 共识拓扑和 TaskCard 级成本护栏。完成后系统具备冗余审查能力和财务自律机制，适应高强度无人值守运行。

---

# Phase 47 Kickoff: 多模型共识与策略护栏 (Consensus & Policy Guardrails)

## Phase 信息

- **Phase**: 47
- **Primary Track**: Evaluation / Policy
- **Secondary Track**: Core Loop
- **前置 Phase**: Phase 46 (Gateway Core) ✅ 已完成，tag v0.4.0
- **预期 tag**: v0.5.0（多模型共识纪元）

## 目标

1. 扩展 `ReviewGate` 支持多审查员并发调用，实现"多数票通过"或"强模型一票否决"共识判定
2. 在 `TaskCard` 层引入成本护栏：基于 Phase 46 捕获的真实 `token_cost` 事件流，实现 TaskCard 级的成本熔断与预警
3. 引入跨模型一致性抽检：由强模型定期审计低成本模型的中间产物，提升系统自我纠偏能力

## 非目标

- 不实现全异步并发调度（留给 Phase 48）——Phase 47 的多审查员调用采用顺序执行，避免在同步 IO 下引入并发复杂度
- 不修改 `_debate_loop_core` 的外部接口语义——共识逻辑封装在 `ReviewGate` 内部，debate loop 只感知最终的 `ReviewGateResult`
- 不实现自动 knowledge promotion 或自动策略采纳
- 不引入新的外部依赖（复用 Phase 46 的 `HTTPExecutor` 调用多模型）
- 不修改 `TaskState` 的核心字段结构（避免状态膨胀，审查历史通过 artifact 持久化而非 state 字段）

## 设计边界

- N-Reviewer 配置通过 `TaskCard.reviewer_routes: list[str]` 注入（路由名列表），不修改 `TaskState`
- 共识判定在 `ReviewGateResult` 内部完成，`_debate_loop_core` 只看 `status == "passed"` / `"failed"`
- 成本护栏通过扩展 `execution_budget_policy.py` 实现，消费 event log 中的 `token_cost` 累计值
- 多审查员调用顺序执行（`httpx` 同步），Phase 48 异步改造后可自然升级为并发

## Slice 列表

| # | Slice | 风险 | 依赖 |
|---|-------|------|------|
| S1 | N-Reviewer 共识拓扑（ReviewGate 扩展） | 高 (8) | 无 |
| S2 | TaskCard 级成本护栏（Budget Policy 扩展） | 中 (5) | S1 |
| S3 | 跨模型一致性抽检（Consistency Audit） | 中 (6) | S1 |
| S4 | Eval 护航与全量回归 | 低 (3) | S1, S2, S3 |

## 完成条件

1. `ReviewGate` 支持 `reviewer_routes` 配置，能顺序调用多个 HTTP 路由并按共识策略判定通过/失败
2. `TaskCard` 可配置 `token_cost_limit`，超限时 `execution_budget_policy` 触发熔断并记录 `budget_exhausted` 事件
3. 一致性抽检可由强模型路由（如 `http-claude`）对低成本路由的输出进行抽样审计
4. 全量 pytest 无回归（342+ tests passed）
5. `pytest -m eval` 新增共识拓扑 eval 场景通过

## Stop/Go Gates

- **S1 完成后**：Human gate。必须验证通过两个不同 HTTP 路由的真实审查调用，确认共识判定逻辑正确。
- **S4 完成后**：全量测试 + eval 通过后，准备 PR。

## Eval 验收条件

| 场景 | 指标 | 基线 |
|------|------|------|
| 多数票通过：2/3 审查员通过 | `ReviewGateResult.status == "passed"` | 100% |
| 强模型否决：1 个强模型失败即整体失败 | `ReviewGateResult.status == "failed"` | 100% |
| 成本熔断触发准确性 | 超限后 `budget_exhausted` 事件存在 | 100% |
| 一致性抽检覆盖率 | 抽检结果写入 artifact | ≥ 1 场景 |

## 分支建议

- 建议分支名：`feat/phase47_consensus-guardrails`
- PR 范围：S1-S4 全部完成后一次性 PR
- 如果 S1 scope 过大，可考虑 S1 先开一个 PR，S2+S3+S4 第二个 PR
