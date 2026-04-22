---
author: claude
phase: 40
slice: debate-topology
status: draft
depends_on:
  - docs/roadmap.md
  - docs/plans/phase39/closeout.md
---

> **TL;DR** Phase 40 升级 ReviewGate 为多轮对抗审查拓扑：Reviewer 可生成结构化 `ReviewFeedback` artifact 持续打回 Executor，直到通过或触发熔断升级 human。3 个 slice，中风险。最大轮次 = 3，防死循环。

# Phase 40 Kickoff: Debate Topology — 对抗审查拓扑增强

## Track

- **Primary Track**: Core Loop
- **Secondary Track**: Execution Topology

## 目标

将当前 ReviewGate 从"单次通过/失败"升级为真正的多轮 Debate Topology，让系统具备结构化的 Executor-Reviewer 对抗循环能力。

具体目标：

1. 引入 **`ReviewFeedback` artifact**：当 ReviewGate 判定 failed 时，生成结构化的反馈（具体失败项 + 改进建议），而非仅返回 pass/fail 布尔结果
2. 实现 **Debate Loop**：Executor 收到 ReviewFeedback 后可在受控循环内重试，重试时将 feedback 注入 prompt 上下文
3. 实现 **熔断机制**：max rounds = 3，循环超限后升级为 `waiting_human` 状态，防止死循环
4. 保持对现有单任务和子任务两条执行路径的向后兼容

## 非目标

- **不做 LLM-as-Reviewer**：本阶段 Reviewer 仍为规则式 ReviewGate（schema 校验 + 输出检查），不引入独立的 Reviewer Agent / LLM 二次评审
- **不做 Consistency Review Agent**：蓝图中提到的"设计文档与代码实现一致性校验"延后，本阶段只增强已有 ReviewGate 的反馈循环能力
- **不做跨任务对抗**：Debate 限于单任务的 Executor-Reviewer 循环，不涉及多任务间的交叉审查
- **不修改 SubtaskOrchestrator 的 DAG 拓扑**：子任务编排结构不变，仅升级单个子任务内部的 review 循环
- **不引入置信度阈值**：不做 review 通过的概率/置信度评分，保持确定性 pass/fail

## 设计边界

### 当前 ReviewGate 现状

- `review_gate.py`: `review_executor_output()` 返回 `ReviewGateResult(status, message, checks)`
- `checks` 包含 `executor_status`、`output_non_empty`、可选 `output_schema` 三类检查
- 单次调用，无反馈生成能力
- `orchestrator.py` 中单任务路径：执行 → review → 事件记录 → 完成/失败
- `subtask_orchestrator.py` 中子任务路径：已有**单次 retry**（Phase 33），失败后重跑一次，之后标记 `review_gate_retry_exhausted`

### 升级后的 Debate 循环

```
Executor 首次执行
    ↓
ReviewGate 评审 → PASS → 正常完成
    ↓ FAIL
生成 ReviewFeedback artifact
    ↓
Executor 重试（feedback 注入 prompt）
    ↓
ReviewGate 再次评审 → PASS → 正常完成
    ↓ FAIL (round < max_rounds)
再次生成 ReviewFeedback → 循环
    ↓ FAIL (round >= max_rounds)
熔断：状态升级为 waiting_human
```

### `ReviewFeedback` 数据结构

```python
@dataclass(slots=True)
class ReviewFeedback:
    round_number: int
    failed_checks: list[dict[str, Any]]   # 失败的 check 项
    suggestions: list[str]                  # 基于失败项生成的改进建议
    original_output_snippet: str            # 触发失败的输出片段（截断）
    max_rounds: int
```

### 关键设计决策

1. **max_rounds = 3**：roadmap 风险批注中明确要求，防死循环。首次执行不算 round，三次 retry 后熔断。
2. **feedback 注入方式**：将 ReviewFeedback 序列化为 markdown，拼接到 executor prompt 的尾部作为 `## Review Feedback (Round N)` section。不修改 dialect adapter 接口。
3. **熔断后行为**：设置 `state.phase = "waiting_human"`，写入 `debate_exhausted` artifact，事件标记 `task.debate_circuit_breaker`。operator 可通过 `swl task run` 手动重跑。
4. **向后兼容**：单任务路径默认启用 debate loop（max_rounds=3）；子任务路径复用同一机制替代现有的硬编码单次 retry。
5. **每轮 feedback 持久化**：每轮 ReviewFeedback 写入 `review_feedback_round_{n}.json` artifact，确保审计可追溯。

### 与现有模块的接口

- **`review_gate.py`**：新增 `ReviewFeedback` dataclass + `build_review_feedback()` 函数
- **`orchestrator.py`**：`run_task` 中的单任务路径引入 debate loop wrapper
- **`subtask_orchestrator.py`**：将硬编码的单次 retry 替换为统一的 debate loop
- **`models.py`**：`ExecutorResult` 新增可选 `review_feedback` 字段（前轮 feedback 的序列化引用）
- **`harness.py`**：executor 调用时，如有前轮 feedback，拼接到 prompt

## Slice 拆解

### S1: ReviewFeedback 数据模型 + 生成逻辑

**目标**：在 `review_gate.py` 中新增 `ReviewFeedback` dataclass 和 `build_review_feedback()` 函数，将 `ReviewGateResult` 中的失败 checks 转化为结构化反馈。

**影响范围**：修改 `review_gate.py`

**风险评级**：
- 影响范围: 1 (单文件修改)
- 可逆性: 1 (轻松回滚)
- 依赖复杂度: 1 (无外部依赖)
- **总分: 3** — 低风险

**验收条件**：
- `build_review_feedback()` 从 `ReviewGateResult` 生成 `ReviewFeedback`
- 失败的 checks 正确映射到 `failed_checks` + `suggestions`
- `original_output_snippet` 截断至合理长度（≤500 chars）
- 全部 checks 通过时返回 `None`（无需 feedback）

### S2: Debate Loop — 单任务路径集成

**目标**：在 `orchestrator.py` 的 `run_task` 中引入 debate loop：review 失败时生成 feedback → 重新调用 executor → 再次 review，直到通过或 max_rounds 耗尽触发熔断。

**影响范围**：修改 `orchestrator.py`、`harness.py`、`review_gate.py`

**风险评级**：
- 影响范围: 2 (跨模块：orchestrator + harness + review_gate)
- 可逆性: 2 (需要额外工作回滚，涉及执行路径变更)
- 依赖复杂度: 2 (依赖 executor dispatch + review gate + event log)
- **总分: 6** — 中风险

**验收条件**：
- review 失败触发 debate loop，feedback 注入 prompt 后重试
- max_rounds=3 后熔断，状态设为 `waiting_human`
- 每轮 feedback 写入 `review_feedback_round_{n}.json` artifact
- 熔断事件 `task.debate_circuit_breaker` 写入事件日志
- review 通过时正常完成，不进入循环
- 全量 pytest 通过

### S3: Debate Loop — 子任务路径统一

**目标**：将 `orchestrator.py` 中子任务的硬编码单次 retry 替换为 S2 实现的统一 debate loop 机制，消除重复代码。

**影响范围**：修改 `orchestrator.py`（子任务 retry 段落）

**风险评级**：
- 影响范围: 2 (子任务执行路径)
- 可逆性: 2 (需要额外工作回滚)
- 依赖复杂度: 2 (依赖 S2 的 debate loop + SubtaskOrchestrator)
- **总分: 6** — 中风险

**验收条件**：
- 子任务 review 失败时进入 debate loop 而非硬编码 retry
- 子任务 max_rounds 与单任务一致（=3）
- 子任务熔断事件标记为 `subtask.{index}.debate_circuit_breaker`
- 现有子任务测试通过，无回归
- 全量 pytest 通过

## Slice 依赖

```
S1 (ReviewFeedback 模型) → S2 (单任务 Debate Loop) → S3 (子任务路径统一)
```

严格顺序依赖。

## 风险总评

| Slice | 影响 | 可逆 | 依赖 | 总分 | 评级 |
|-------|------|------|------|------|------|
| S1 | 1 | 1 | 1 | 3 | 低 |
| S2 | 2 | 2 | 2 | 6 | 中 |
| S3 | 2 | 2 | 2 | 6 | 中 |
| **合计** | | | | **15/27** | **中** |

主要风险在 S2/S3 对核心执行路径的修改。S2 修改 `run_task` 主循环，需确保 debate loop 不影响正常通过路径。S3 替换子任务 retry，需确保 DAG 编排不受影响。

**关键缓解措施**：
- max_rounds 硬上限 = 3，物理防止无限循环
- 每轮 feedback 持久化为 artifact，确保可审计
- 熔断后升级 `waiting_human`，不静默失败

## 完成条件

1. ReviewGate 失败时生成结构化 `ReviewFeedback`
2. 单任务路径支持 debate loop（最多 3 轮 retry + feedback）
3. 子任务路径统一使用 debate loop 替代硬编码 retry
4. 熔断后状态为 `waiting_human`，事件日志记录 `debate_circuit_breaker`
5. 每轮 feedback 持久化为 artifact
6. 全量 pytest 通过，无回归

## Branch Advice

- 当前分支: `main`
- 建议操作: 人工审批 kickoff 后，从 `main` 切出 `feat/phase40-debate-topology`
- 理由: Phase 40 修改核心执行路径，应在 feature branch 上进行
- 建议 PR 范围: S1 + S2 + S3 合并为单 PR（三个 slice 紧密耦合）
