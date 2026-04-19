---
author: gemini
phase: 47
slice: phase47_context_brief
status: final
depends_on:
  - docs/roadmap.md
  - docs/plans/phase46/closeout.md
---

## TL;DR
Phase 47 启动：在 Phase 46 提供的 HTTP 多模型分发能力基础上，进入“多模型共识与策略护栏”阶段。变更核心涉及 `ReviewGate` 的多审查员扩展、`Orchestrator` 的共识逻辑实装以及基于真实成本的智能预算策略。

# Context Brief - Phase 47

## 变更范围

### 1. 模型层 (`src/swallow/models.py`)
- **TaskCard**: 需扩展以支持 `reviewers: list[str]` (逻辑路由名列表) 或类似的审查员配置。
- **TaskState**: 需记录多个审查员的结果，可能涉及 `review_results: list[dict]` 字段。

### 2. 审查门禁 (`src/swallow/review_gate.py`)
- **ReviewGateResult**: 需支持从“1:1 审查”向“N 汇聚审查”演进。
- **Consensus Logic**: 需实装“多数票通过”、“强模型一票否决”等共识判定算法。

### 3. 编排内核 (`src/swallow/orchestrator.py`)
- **Debate Loop**: `_debate_loop_core` 需适配多审查员反馈的汇聚逻辑。
- **Dispatching**: 实装并行或顺序呼叫多个审查模型的能力。

### 4. 成本与策略 (`src/swallow/cost_estimation.py` & `dispatch_policy.py`)
- **Budgeting**: 利用 Phase 46 捕获的 `token_cost` 真实数据，实装 TaskCard 级的成本护栏。

## 近期变更摘要 (Last 10 Commits)

1. `31363b0` close phase46 and sync v0.4.0 (HEAD)
2. `a486068` merge: Gateway Core Materialization
3. `0f040e4` docs(phase46):review-closeout
4. `14a4629` feat(gateway): add fallback matrix for http routes
5. `b5ccf5e` feat(gateway): align http dialect routing matrix
6. `8e030a7` feat(gateway): add http executor and debrand cli agents
7. `0455e93` docs(infra): deploy pre phase46 infra
8. `d002e18` change suggested branch name
9. `84585a2` feat:interrupted by env
10. `4da4130` docs(phase46):initialize geteway core build

## 关键上下文

- **HTTP 基础设施已就绪**: Phase 46 实装的 `HTTPExecutor` 已支持 Claude/Qwen/GLM/Gemini/DeepSeek 路由，这为 Phase 47 的多模型共识提供了真实的物理通道。
- **Debate Loop 耦合**: 目前 `orchestrator.py` 中的 debate loop (重试循环) 与单审查员反馈紧密耦合。引入 N-Reviewer 时，需小心处理反馈的合并，避免 Prompt 爆炸或逻辑混乱。
- **同步 IO 限制**: 当前系统仍为同步阻塞 IO。在 Phase 47 中若并行呼叫多个模型进行审查，可能会暴露 `httpx` 在同步模式下的延迟瓶颈（Phase 48 将解决此问题，但 47 需考虑初步应对）。

## 风险信号

- **成本翻倍风险**: N-Reviewer 会显著增加 Token 消耗。若不先实装预算护栏，可能会在自动化测试中产生非预期的高额账单。
- **共识冲突**: 当强模型（如 Claude 3.5 Sonnet）与弱模型（如本地 7B）意见不一致时，简单的 Majority Pass 可能会降低系统质量。需设计有权重的共识机制。
- **状态膨胀**: 在 `TaskState` 中记录多轮、多人的审查历史可能会导致 JSON 文件迅速膨胀，影响序列化性能。
