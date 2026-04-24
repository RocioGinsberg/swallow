---
author: claude
phase: 47
slice: all
status: draft
depends_on:
  - docs/plans/phase47/kickoff.md
  - docs/roadmap.md
  - src/swallow/review_gate.py
  - src/swallow/orchestrator.py
  - src/swallow/execution_budget_policy.py
  - src/swallow/models.py
---

> **TL;DR**: Phase 47 在不改变 `_debate_loop_core` 外部接口的前提下，将共识逻辑封装进 `ReviewGate`，通过 `TaskCard.reviewer_routes` 配置多审查员，顺序调用 HTTP 路由并按策略判定。成本护栏扩展 `execution_budget_policy.py`，消费 event log 累计 `token_cost`。一致性抽检作为独立 slice，不阻塞主路径。

---

# Phase 47: 多模型共识与策略护栏 — 方案拆解

## 方案总述

Phase 46 打通了物理层多模型分发，但编排层的 `ReviewGate` 仍是单审查员模式——每轮 debate 只调用一个模型，无法对冲单模型幻觉。Phase 47 的核心是：

1. **共识拓扑**：让 `ReviewGate` 能顺序调用多个 HTTP 路由，按"多数票"或"强模型否决"策略汇聚结果，`_debate_loop_core` 不感知内部变化
2. **成本护栏**：`execution_budget_policy.py` 扩展为消费 event log 中的真实 `token_cost` 累计值，超限时触发熔断
3. **一致性抽检**：独立的抽检入口，由强模型路由对低成本路由的输出进行抽样审计，结果写入 artifact

**关键设计约束**：Phase 47 的多审查员调用采用**顺序执行**，不引入 `asyncio`。这是有意为之——Phase 48 的全异步改造会自然升级这条路径，Phase 47 不应为了并发而提前引入复杂度。

---

## Slice 拆解

### S1: N-Reviewer 共识拓扑（ReviewGate 扩展）

**目标**：扩展 `ReviewGate` 支持多审查员，`_debate_loop_core` 接口不变。

**具体任务**：

**模型层扩展**（`models.py`）：
- `TaskCard` 新增 `reviewer_routes: list[str] = field(default_factory=list)`——路由名列表，空列表时退化为单审查员行为（向后兼容）
- `TaskCard` 新增 `consensus_policy: str = "majority"`——支持 `"majority"`（多数票）和`"veto"`（强模型一票否决）两种策略
- 不修改 `TaskState`——多审查员的中间结果通过 artifact 持久化，不写入 state 字段

**ReviewGate 扩展**（`review_gate.py`）：
- 新增 `run_consensus_review(executor_result, card, reviewer_routes, consensus_policy)` 函数
- 内部顺序调用每个路由的 HTTP 审查请求，收集各审查员的 `ReviewGateResult`
- 按 `consensus_policy` 判定最终结果：
  - `"majority"`：超过半数通过则整体通过
  - `"veto"`：第一个路由（强模型）失败则整体失败，其余路由只作参考
- 返回汇聚后的单个 `ReviewGateResult`，`checks` 字段包含各审查员的子结果
- `reviewer_routes` 为空时，退化为现有的单审查员逻辑（不改变现有路径）

**Orchestrator 适配**（`orchestrator.py`）：
- 在调用 `run_review_gate` 的位置，检查 `card.reviewer_routes`，非空时改为调用 `run_consensus_review`
- `_debate_loop_core` 接口**不变**——它只感知最终的 `ReviewGateResult.status`

**影响范围**：`models.py`、`review_gate.py`、`orchestrator.py`、`tests/test_review_gate.py`
**风险评级**：影响范围 3 + 可逆性 2 + 依赖复杂度 3 = **8（高）**
**验收条件**：
- `reviewer_routes=[]` 时行为与现有单审查员完全一致（无回归）
- `reviewer_routes=["http-claude", "http-qwen"]` + `consensus_policy="majority"` 时，2/2 通过 → passed，1/2 通过 → failed
- `consensus_policy="veto"` 时，第一个路由失败 → 整体 failed，无论其他路由结果
- 使用 mock HTTP server 的单元测试通过

**Human gate**：S1 完成后，通过两个真实 HTTP 路由验证共识判定逻辑。

---

### S2: TaskCard 级成本护栏（Budget Policy 扩展）

**目标**：基于真实 `token_cost` 事件流，实现 TaskCard 级成本熔断。

**具体任务**：

**模型层扩展**（`models.py`）：
- `TaskCard` 新增 `token_cost_limit: float = 0.0`——0.0 表示不限制（向后兼容）

**Budget Policy 扩展**（`execution_budget_policy.py`）：
- 新增 `evaluate_token_cost_budget(base_dir, task_id, cost_limit)` 函数
- 从 event log 中聚合当前 task 的累计 `token_cost`（复用 Meta-Optimizer 的事件扫描逻辑）
- 超限时返回 `budget_state="cost_exhausted"`，触发熔断
- 在 `evaluate_execution_budget_policy` 中集成此检查（`cost_limit > 0` 时启用）

**Orchestrator 集成**（`orchestrator.py`）：
- 在每轮 debate attempt 前调用 budget policy 检查
- `budget_state == "cost_exhausted"` 时，跳过执行，直接进入 `waiting_human` 状态并记录 `budget_exhausted` 事件

**影响范围**：`models.py`、`execution_budget_policy.py`、`orchestrator.py`
**风险评级**：影响范围 2 + 可逆性 1 + 依赖复杂度 2 = **5（中）**
**验收条件**：
- `token_cost_limit=0.0` 时行为与现有完全一致
- 累计成本超限时，`budget_exhausted` 事件存在于 event log
- 超限后任务进入 `waiting_human` 而非继续执行

---

### S3: 跨模型一致性抽检（Consistency Audit）

**目标**：由强模型路由对低成本路由的输出进行抽样审计，结果写入 artifact。

**具体任务**：

**新增 `consistency_audit.py`**：
- `run_consistency_audit(base_dir, task_id, auditor_route, sample_artifact_path)` 函数
- 读取指定 artifact（如 `executor_output.md`），构造审计 prompt，通过 `auditor_route`（如 `http-claude`）发起 HTTP 审查请求
- 将审计结果写入 `consistency_audit_<timestamp>.md` artifact
- 不修改 task state，不触发 debate retry——纯只读审计

**CLI 入口**（`cli.py`）：
- 新增 `swl task consistency-audit <task-id> --auditor-route http-claude` 命令
- operator 手动触发，不自动执行

**影响范围**：新增 `consistency_audit.py`、`cli.py`
**风险评级**：影响范围 2 + 可逆性 1 + 依赖复杂度 3 = **6（中）**
**验收条件**：
- `swl task consistency-audit <task-id>` 能调用 `http-claude` 路由并写入审计 artifact
- 审计失败（HTTP 不可达）时优雅降级，不影响 task state

---

### S4: Eval 护航与全量回归

**目标**：补齐 Phase 47 新增能力的 eval 覆盖，确认无回归。

**具体任务**：
- 在 `tests/eval/` 新增 `test_consensus_eval.py`：覆盖多数票通过、强模型否决、成本熔断三个场景
- 运行全量 `pytest`，确认 342+ tests passed
- 运行 `pytest -m eval`，确认所有 eval 场景通过

**影响范围**：`tests/eval/`
**风险评级**：影响范围 1 + 可逆性 1 + 依赖复杂度 1 = **3（低）**

---

## 依赖说明

```
S1 (N-Reviewer 共识拓扑)
  └──→ S2 (成本护栏) ← 依赖 S1 的 TaskCard 扩展已落地
  └──→ S3 (一致性抽检) ← 依赖 S1 的 HTTP 路由调用模式
         └──→ S4 (Eval 护航) ← 依赖 S1/S2/S3 全部完成
```

S2 和 S3 之间无强依赖，可并行实现。

## 明确的非目标

- **不实现异步并发审查**：多审查员顺序执行，Phase 48 升级
- **不修改 `_debate_loop_core` 接口**：共识逻辑封装在 `ReviewGate` 内部
- **不自动触发一致性抽检**：S3 是 operator 手动入口，不进入自动化流程
- **不修改 `TaskState` 核心字段**：审查历史通过 artifact 持久化

## 整体风险评估

| Slice | 风险分 | 等级 |
|-------|--------|------|
| S1 N-Reviewer 共识拓扑 | 8 | 高 |
| S2 成本护栏 | 5 | 中 |
| S3 一致性抽检 | 6 | 中 |
| S4 Eval 护航 | 3 | 低 |
| **总计** | **22/36** | **中** |
