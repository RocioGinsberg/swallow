---
author: claude
phase: 40
slice: debate-topology
status: final
depends_on:
  - docs/plans/phase40/kickoff.md
  - docs/plans/phase40/risk_assessment.md
---

> **TL;DR** Phase 40 review: 0 BLOCK / 2 CONCERN / 1 NOTE。Merge ready。Debate loop 完整覆盖单任务与子任务路径，max_rounds=3 熔断 + waiting_human 升级 + 每轮 feedback artifact 持久化。302 tests passed。

# Phase 40 Review Comments

## Review Scope

- 对照 `docs/plans/phase40/kickoff.md` 的方案拆解
- 对照 `docs/design/*.md` 架构原则一致性
- 测试覆盖充分性
- Phase scope 守界检查

## Checklist

### S1: ReviewFeedback 数据模型 + 生成逻辑

- [PASS] `ReviewFeedback` dataclass 结构清晰：`round_number` / `failed_checks` / `suggestions` / `original_output_snippet` / `max_rounds`
- [PASS] `build_review_feedback()` 为纯函数，review 通过时返回 `None`
- [PASS] `_suggestion_for_failed_check()` 为三种已知 check 类型（executor_status / output_non_empty / output_schema）生成具体建议，未知 check 提供通用 fallback
- [PASS] `_truncate_output_snippet()` 截断至 500 chars，尾部加 `...`
- [PASS] `render_review_feedback_markdown()` 输出结构化 markdown，包含 Failed Checks / Suggestions / Original Output Snippet 三节
- [PASS] suggestion 去重（`seen_suggestions` set）
- [PASS] 测试覆盖：通过时返回 None / 失败时收集 checks+suggestions / 截断验证（3 个新测试 + 5 个已有测试）

### S2: Debate Loop — 单任务路径

- [PASS] `_run_single_task_with_debate()` 封装完整 debate loop，与 `run_task` 主循环解耦良好
- [PASS] review 通过时快速路径退出（`_clear_review_feedback_state` + return），零额外开销
- [PASS] executor status="failed" 时不进入 debate loop（先走 binary fallback，fallback 后仍 failed 则直接返回）
- [PASS] `DEBATE_MAX_ROUNDS = 3` 模块级常量，物理防止死循环
- [PASS] 每轮 feedback 持久化为 `review_feedback_round_{n}.json` artifact
- [PASS] 熔断时写入 `debate_exhausted.json`（含 feedback_refs 列表 + last_feedback + review_gate_result）
- [PASS] 熔断事件 `task.debate_circuit_breaker` 写入事件日志，payload 包含完整审计信息
- [PASS] 熔断后 executor_result.failure_kind = `"debate_circuit_breaker"`，与现有 `"review_gate_retry_exhausted"` 语义区分
- [PASS] `state.review_feedback_markdown` / `state.review_feedback_ref` 在 feedback 注入和清除路径上正确管理
- [PASS] `harness.py` 中 `waiting_human` 状态保持不被覆盖为 "completed"/"failed"
- [PASS] feedback 注入三种 dialect 均验证：Claude XML（raw_prompt 内）/ Structured Markdown（尾部 section）/ Codex FIM（raw_prompt 内）
- [PASS] `checkpoint_snapshot.py` 新增 `waiting_human` 语义支持
- [PASS] 测试覆盖：成功重试（1 次 fail → 2nd pass）/ 熔断（3 轮全 fail → waiting_human）/ dialect 注入（3 种）/ checkpoint regression

### S3: Debate Loop — 子任务路径统一

- [PASS] `_run_subtask_attempt()` 提取为独立函数，替代原有的内联 lambda + SubtaskOrchestrator 组合
- [PASS] `_run_subtask_debate_retries()` 实现 per-card 独立 debate loop，每卡有独自的 feedback_refs 和 round 计数
- [PASS] 子任务 executor status="failed"（非 review 失败）时不进入 debate loop — 正确区分 executor failure vs review failure
- [PASS] 子任务 feedback artifact 使用 `subtask_{index}_review_feedback_round_{n}.json` 前缀，不与单任务 artifact 冲突
- [PASS] 子任务熔断事件 `subtask.{index}.debate_circuit_breaker`，payload 含 `attempt_count` 正确反映总尝试次数
- [PASS] 父任务在任一子任务熔断时升级为 `waiting_human`，写入 `task.waiting_human` 事件
- [PASS] 父任务 executor_result.failure_kind = `"debate_circuit_breaker"`（非旧的 `"review_gate_retry_exhausted"`，但旧 failure_kind 在纯 executor failure 时仍保留）
- [PASS] 测试覆盖：targeted retry 成功 / 熔断 waiting_human / executor failure 不进入 debate（3 个测试用例）

### 架构一致性

- [PASS] Reviewer 仍为规则式 ReviewGate，不引入 LLM-as-Reviewer — 符合 kickoff 非目标
- [PASS] 不修改 SubtaskOrchestrator 的 DAG 拓扑结构 — 符合 kickoff 非目标
- [PASS] 不引入置信度阈值 — 符合 kickoff 非目标
- [PASS] `waiting_human` 状态与现有系统语义一致（Phase 33 已有此状态路径）

### Scope 守界

- [PASS] 无越界实现：不做 LLM reviewer、不做跨任务对抗、不做 Consistency Review Agent

## CONCERN

### C1: 单任务与子任务 debate loop 代码结构重复

**位置**: `orchestrator.py` — `_run_single_task_with_debate()` (约 80 行) 与 `_run_subtask_debate_retries()` (约 90 行)

两个函数的核心循环结构几乎一致：check round limit → build feedback → persist artifact → append event → increment round。差异仅在于：(a) 单任务直接调用 `_execute_task_card`，子任务调用 `_run_subtask_attempt`；(b) artifact 命名前缀不同；(c) 事件 event_type 前缀不同。

当前重复可接受（两个路径确实有不同的前/后处理），但如果未来 debate 逻辑需要调整（如修改 max_rounds 策略、增加 feedback 格式），需要同步修改两处。

**建议**: 后续 phase 如需修改 debate 逻辑，考虑提取共享的 `_debate_loop_core()` 函数，通过 callback 参数化差异点。本次不建议修改。

**消化时机**: 下次触碰 debate/review 逻辑时评估是否提取。

### C2: `ExecutorResult.review_feedback` 字段的 telemetry 传播

**位置**: `executor.py:272`, `executor.py:343`, `harness.py:164`

`review_feedback` 字段从 `state.review_feedback_ref` 拷贝到 `ExecutorResult`，再由 `harness.py` 写入 executor event payload。但 `meta_optimizer.py` 的事件扫描（route health / failure fingerprint）目前不感知此字段。

如果同一任务的多轮 retry 事件都以 `executor.completed` 记录，Meta-Optimizer 会将 retry 事件与正常执行事件混在一起计算 route health 统计。debate 轮次的 retry 事件应能被区分，否则会膨胀某条 route 的请求计数和失败率。

**建议**: 后续触碰 Meta-Optimizer 逻辑时，考虑让 route health 聚合排除带 `review_feedback` 的 executor 事件，或用独立 event_type（如 `executor.debate_retry`）标记 debate 轮次的执行事件。

**消化时机**: 下次触碰 meta_optimizer route health 逻辑时。

## NOTE

### N1: 测试环境已就绪，自动测试已执行

全量 `pytest` 通过：302 passed, 5 subtests passed in 6.71s。无回归。

## 结论

**Merge ready**。实现完整覆盖 kickoff 定义的 ReviewFeedback 模型、单任务 Debate Loop、子任务路径统一。max_rounds=3 硬上限 + 熔断 waiting_human + 每轮 feedback artifact 持久化三层防线到位。2 个 CONCERN 均为后续优化建议，不影响当前正确性。
