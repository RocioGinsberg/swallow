---
author: claude
phase: 40
slice: debate-topology
status: draft
depends_on:
  - docs/plans/phase40/kickoff.md
---

> **TL;DR** Phase 40 整体风险 15/27（中）。S1 低风险纯数据模型，S2/S3 修改核心执行路径为主要关注点。死循环风险通过 max_rounds=3 硬上限 + 熔断机制物理消除。

# Phase 40 Risk Assessment

## 风险矩阵

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 风险等级 |
|-------|---------|--------|-----------|------|---------|
| S1: ReviewFeedback 模型 | 1 — 单文件 | 1 — 轻松回滚 | 1 — 无外部依赖 | **3** | 低 |
| S2: 单任务 Debate Loop | 2 — 跨模块 | 2 — 需额外工作 | 2 — 依赖多内部模块 | **6** | 中 |
| S3: 子任务路径统一 | 2 — 子任务路径 | 2 — 需额外工作 | 2 — 依赖 S2 | **6** | 中 |

**总分: 15/27** — 无高风险 slice（≥7），但 S2+S3 合计 12 分，属于需要重点关注的中风险区间。

## 各 Slice 风险详述

### S1: ReviewFeedback 模型

**风险极低**。纯数据结构 + 转换函数新增，不修改现有执行路径。

- `ReviewFeedback` dataclass 独立于 `ReviewGateResult`，不改变现有 API
- `build_review_feedback()` 为纯函数，无副作用

### S2: 单任务 Debate Loop

**中风险**。修改 `orchestrator.py` 的 `run_task` 主循环，是本 phase 的核心变更。

**关注点**：

1. **正常通过路径不受影响**：debate loop 仅在 review 失败时激活，review 通过时应零开销退出循环。需确保 `round_number == 0` 时行为与当前完全一致。
2. **feedback 注入不污染 prompt**：拼接到 prompt 尾部的 `## Review Feedback` section 不应干扰 dialect adapter 的格式解析。需验证 Claude XML / Codex FIM / Structured Markdown 三种 dialect 下 feedback 注入的兼容性。
3. **事件日志膨胀**：每轮 retry 产生额外事件（`task.debate_round_{n}`），需确保 Meta-Optimizer 的事件扫描不被重试事件干扰。建议 debate 事件使用独立 event_type 前缀。
4. **熔断状态与现有恢复路径兼容**：`waiting_human` 状态已存在于系统中，但需确认 `swl task run` 从 `waiting_human` 恢复时能正确重置 debate round 计数。

**缓解措施**：
- S2 实现时先写"review 通过直接返回"的快速路径测试，确保非 debate 场景零回归
- feedback 注入测试应覆盖三种 dialect
- 熔断后写入 `debate_exhausted.json` artifact，包含完整 round 历史

### S3: 子任务路径统一

**中风险**。替换 `orchestrator.py` 中硬编码的子任务单次 retry 逻辑。

**关注点**：

1. **并发安全**：子任务通过 `ThreadPoolExecutor` 并行执行，debate loop 内的状态（round 计数、feedback 积累）必须 per-card 隔离，不能共享。当前硬编码 retry 是 per-card 的，统一到 debate loop 时需保持此隔离。
2. **SubtaskOrchestrator 接口变更**：当前 `SubtaskOrchestrator.__init__` 接收 `ReviewCard` callback。debate loop 可能需要额外传入 `build_review_feedback` 和 `max_rounds` 参数，或在 callback 内部封装。需选择侵入性最小的集成方式。
3. **事件类型一致性**：子任务 debate 事件应与单任务 debate 事件使用相同的 schema（`subtask.{index}.debate_round_{n}`），便于 Meta-Optimizer 统一处理。

**缓解措施**：
- S3 开始前先确认 S2 的 debate loop 是否可提取为独立可复用函数（而非内联在 `run_task` 中）
- 子任务并发测试应验证多个子任务同时进入 debate loop 时互不干扰

## 与历史 Concern 的交互

- **Phase 36 C1 (save_state → index 一致性)**：debate loop 中每轮 retry 会触发 `save_state`，如果 Librarian 路径的任务进入 debate loop，save_state → index 一致性问题可能被放大。但当前 Librarian 任务不走标准 executor dispatch，不经过 ReviewGate，因此不受影响。
- **Phase 38 C1 (fallback 成本统计)**：debate loop 中每轮 retry 的 telemetry 事件需正确记录 `token_cost`，确保 Meta-Optimizer 不会将 retry 成本遗漏。S2 实现时需注意。

## 死循环风险专项评估

这是 roadmap 风险批注中明确标注的核心风险。

**物理防线**：
1. `max_rounds = 3` 硬编码上限，不可配置（首版）
2. 每轮 round 有独立的 artifact 持久化，operator 可审计
3. 熔断后状态为 `waiting_human`，不会静默重试
4. 熔断事件 `task.debate_circuit_breaker` 写入事件日志

**理论最坏情况**：3 轮 retry × 单次 executor latency。对于 30s 响应的 LLM 调用，最坏情况约 2 分钟。可接受。

## 整体判断

Phase 40 为中风险，核心变更集中在执行路径。建议 S2 完成后由 Human 审查 diff 再进入 S3，确保单任务路径稳定后再统一子任务路径。
