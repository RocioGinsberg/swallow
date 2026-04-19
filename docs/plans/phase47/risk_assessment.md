---
author: claude
phase: 47
slice: all
status: draft
depends_on:
  - docs/plans/phase47/design_decision.md
  - docs/plans/phase47/kickoff.md
---

> **TL;DR**: Phase 47 整体风险 22/36（中）。S1（N-Reviewer 共识拓扑）是最高风险点，核心风险是 debate loop 的向后兼容性和多审查员反馈汇聚的语义正确性。成本翻倍是系统性风险，必须在 S1 完成后立即推进 S2。

---

# Phase 47 Risk Assessment: 多模型共识与策略护栏

## 风险矩阵

### 维度说明

- **影响范围**：1=单文件 2=单模块 3=跨模块
- **可逆性**：1=轻松回滚 2=需要额外工作 3=难以回滚
- **依赖复杂度**：1=无外部依赖 2=依赖内部模块 3=依赖外部系统

总分 ≥7 标注为高风险。

---

### S1: N-Reviewer 共识拓扑

| 维度 | 分数 | 说明 |
|------|------|------|
| 影响范围 | 3 | 跨 `models.py`、`review_gate.py`、`orchestrator.py`、测试文件 |
| 可逆性 | 2 | `TaskCard` 新增字段可回滚，但 `orchestrator.py` 的分支逻辑需额外清理 |
| 依赖复杂度 | 3 | 依赖 Phase 46 的 HTTP 路由可用 + 现有 debate loop 的兼容性 |
| **总分** | **8** | **高风险** |

**风险 R1：debate loop 向后兼容性破坏**
- 描述：`orchestrator.py` 中调用 `run_review_gate` 的位置需要条件分支，若判断逻辑有误，可能导致 `reviewer_routes=[]` 时走入新路径，破坏现有单审查员行为
- 影响：现有 342 个测试中涉及 debate loop 的部分可能失败
- 概率：中
- 缓解：`reviewer_routes=[]` 时严格退化为现有路径，不进入 `run_consensus_review`；S1 完成后必须全量回归

**风险 R2：共识判定语义不一致**
- 描述：`"majority"` 策略在审查员数量为偶数时（如 2 个）存在平局情况，需明确平局处理规则
- 影响：平局时系统行为不确定
- 概率：低
- 缓解：平局时默认为 `"failed"`（保守策略），在 `run_consensus_review` 中显式文档化

**风险 R3：多审查员顺序调用延迟累积**
- 描述：N 个审查员顺序调用，延迟为 N × 单次延迟。若每次调用 20s，3 个审查员则 60s，可能触发外层超时
- 影响：debate loop 超时，任务进入 `waiting_human`
- 概率：中
- 缓解：`AIWF_EXECUTOR_TIMEOUT_SECONDS` 应在使用多审查员时相应调整；在 `swl doctor` 中新增多审查员超时预警

---

### S2: TaskCard 级成本护栏

| 维度 | 分数 | 说明 |
|------|------|------|
| 影响范围 | 2 | `models.py`、`execution_budget_policy.py`、`orchestrator.py` |
| 可逆性 | 1 | `token_cost_limit=0.0` 时完全向后兼容，轻松回滚 |
| 依赖复杂度 | 2 | 依赖 event log 中的 `token_cost` 字段（Phase 46 已落地） |
| **总分** | **5** | **中风险** |

**风险 R4：event log 扫描性能**
- 描述：每轮 debate attempt 前扫描 event log 累计成本，若 event log 很大，扫描可能引入明显延迟
- 影响：debate loop 变慢
- 概率：低（当前 event log 规模有限）
- 缓解：只扫描当前 task_id 的事件，不全量扫描；Phase 48 的 SQLite 迁移后此问题自然消解

---

### S3: 跨模型一致性抽检

| 维度 | 分数 | 说明 |
|------|------|------|
| 影响范围 | 2 | 新增 `consistency_audit.py`、`cli.py` |
| 可逆性 | 1 | 新增模块，不修改现有路径，轻松回滚 |
| 依赖复杂度 | 3 | 依赖 `http-claude` 等强模型路由可用 |
| **总分** | **6** | **中风险** |

**风险 R5：审计 prompt 质量**
- 描述：一致性审计的 prompt 设计直接影响审计结果的有效性，过于宽泛的 prompt 会导致审计结论无意义
- 影响：审计 artifact 质量低，operator 无法据此判断
- 概率：中
- 缓解：S3 kickoff 时明确审计 prompt 模板，聚焦"输出是否符合 task goal"和"是否存在明显幻觉"两个维度

---

## 系统性风险

### SR1：成本翻倍风险（最重要）

N-Reviewer 会使每轮 debate 的 token 消耗乘以审查员数量。若 S1 完成但 S2 未完成，在自动化测试或真实任务中使用多审查员配置，可能产生非预期的高额账单。

**缓解**：S2 必须紧跟 S1 完成，不允许在 S2 完成前将多审查员配置用于真实任务。

### SR2：Phase 48 依赖前置

Phase 47 的多审查员顺序调用在 Phase 48 异步改造后可自然升级为并发。但如果 Phase 47 的实现过于依赖顺序语义（如依赖前一个审查员的结果来决定是否调用下一个），Phase 48 的并发改造会更复杂。

**缓解**：S1 的设计应保持各审查员调用相互独立，共识判定只在所有调用完成后进行，不引入顺序依赖。

---

## 风险总览

| ID | 风险 | Slice | 概率 | 影响 | 缓解策略 |
|----|------|-------|------|------|----------|
| R1 | debate loop 向后兼容性破坏 | S1 | 中 | 高 | `reviewer_routes=[]` 严格退化 |
| R2 | 共识平局语义不确定 | S1 | 低 | 中 | 平局默认 failed |
| R3 | 多审查员延迟累积超时 | S1 | 中 | 中 | 文档化超时调整建议 |
| R4 | event log 扫描性能 | S2 | 低 | 低 | 只扫描当前 task_id |
| R5 | 审计 prompt 质量 | S3 | 中 | 中 | 明确审计 prompt 模板 |
| SR1 | 成本翻倍 | 全局 | 确定 | 高 | S2 紧跟 S1，不提前使用多审查员 |
| SR2 | Phase 48 并发改造复杂度 | 全局 | 低 | 中 | 各审查员调用相互独立 |

## 建议的 Human Gate 时机

1. **S1 完成后**：通过两个真实 HTTP 路由验证共识判定逻辑，确认向后兼容性
2. **S4 完成后**：全量测试 + eval 通过，准备 PR
