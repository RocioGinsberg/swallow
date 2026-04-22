---
author: codex
phase: 40
slice: all
status: final
depends_on:
  - docs/plans/phase40/kickoff.md
  - docs/plans/phase40/risk_assessment.md
  - docs/plans/phase40/review_comments.md
  - docs/concerns_backlog.md
---

## TL;DR
Phase 40 已完成实现、review 与 PR 收口准备，当前状态为 **merge ready / PR sync ready**。本轮将规则式 ReviewGate 升级为多轮 Debate Topology：S1 引入结构化 `ReviewFeedback`，S2 为单任务路径增加 feedback-driven retry 与 `waiting_human` 熔断，S3 将相同机制统一到子任务路径。Claude review 结论为 `0 BLOCK / 2 CONCERN / 1 NOTE / Merge ready`，两个 concern 已登记回 backlog。当前全量回归基线为 `302 passed in 7.10s`。

# Phase 40 Closeout

## 结论

Phase 40 `Debate Topology` 已完成实现、review 与验证，当前分支状态为 **merge ready / PR sync ready**。

本轮围绕 kickoff 定义的 3 个 slice，交付了一个受控、可审计、带熔断的人机协作 review loop：

- S1：`ReviewFeedback` 数据模型、suggestion 生成与 markdown 渲染
- S2：单任务 debate loop，支持 review feedback 注入 prompt、三轮熔断与 `waiting_human` checkpoint 语义
- S3：子任务路径统一为 per-card debate loop，替换 Phase 33 的硬编码单次 retry

Claude review 已完成，结论为 `0 BLOCK / 2 CONCERN / 1 NOTE / Merge ready`。两个 concern 均为后续优化建议，不影响当前正确性，现已登记到 `docs/concerns_backlog.md`。

## 已完成范围

### Slice 1: ReviewFeedback 模型

- `src/swallow/review_gate.py` 新增 `ReviewFeedback` dataclass、`build_review_feedback()` 与 `render_review_feedback_markdown()`
- failed checks 现在会映射为结构化 `failed_checks`、去重 `suggestions` 与截断输出片段
- `tests/test_review_gate.py` 已覆盖 pass/null 路径、known check suggestion 映射与 snippet 截断

对应 commit：

- `2806a99` `feat(review-gate): add structured review feedback model`

### Slice 2: 单任务 Debate Loop

- `src/swallow/models.py` 为 `TaskState` / `ExecutorResult` 增加 review feedback prompt/ref 字段
- `src/swallow/executor.py` 在 raw prompt / structured markdown 中注入 `## Review Feedback (Round N)`，并把 feedback ref 带回执行结果
- `src/swallow/harness.py` executor 事件 payload 增加 `review_feedback`，并保留 `waiting_human` artifact 渲染状态
- `src/swallow/orchestrator.py` 新增单任务 debate loop：每轮 feedback artifact、`task.debate_round`、`task.debate_circuit_breaker` 与 `task.waiting_human`
- `src/swallow/checkpoint_snapshot.py` 增加 `waiting_human` / `human_gate_debate_exhausted` 恢复语义
- `tests/test_debate_loop.py`、`tests/test_dialect_adapters.py`、`tests/test_grounding.py` 已覆盖反馈注入、熔断与 checkpoint snapshot 回归

对应 commit：

- `d0831c1` `feat(review-gate): add single-task debate loop`

### Slice 3: 子任务路径统一

- `src/swallow/orchestrator.py` 将失败子任务从硬编码单次 retry 升级为 per-card debate loop，最多 3 轮 review feedback
- 子任务路径新增：
  - `subtask.{index}.debate_round`
  - `subtask.{index}.debate_circuit_breaker`
  - `subtask_{index}_review_feedback_round_{n}.json`
  - `subtask_{index}_debate_exhausted.json`
- 父任务在子任务 debate 熔断时统一收口为 `waiting_human`
- 同时保留 S2 的边界：基础 executor failure 不进入 debate
- `tests/test_run_task_subtasks.py` 已覆盖 targeted retry、子任务熔断等待人工、executor failure 非 debate 回归

对应 commit：

- `72882ba` `feat(review-gate): unify subtask debate loop retries`

## Review Follow-up

- C1 单任务与子任务 debate loop 代码结构重复：当前不在本轮继续提取共享 `_debate_loop_core()`，已登记到 `docs/concerns_backlog.md`，待下次触碰 debate/review 逻辑时统一评估。
- C2 debate retry telemetry 会进入 Meta-Optimizer route health 聚合：当前不改 event_type 与聚合规则，已登记到 `docs/concerns_backlog.md`，待下次触碰 meta_optimizer route health 逻辑时处理。
- N1 自动测试环境已就绪且全量回归通过，无额外 follow-up。

## 与 kickoff 完成条件对照

### 已完成的目标

- `ReviewFeedback` 已能从 `ReviewGateResult` 生成结构化反馈
- 单任务路径已支持 feedback-driven debate loop，最多 3 轮 retry
- `review_feedback_round_{n}.json` 与 `subtask_{index}_review_feedback_round_{n}.json` artifact 已可追溯每轮反馈
- 单任务与子任务路径均可在 debate 穷尽后进入 `waiting_human`
- `task.debate_circuit_breaker` 与 `subtask.{index}.debate_circuit_breaker` 事件已落地
- 子任务路径已统一使用 debate loop，替代原硬编码单次 retry
- 全量测试通过

### 未继续扩张的内容

以下方向仍明确不在本 phase 范围内：

- LLM-as-Reviewer / 独立 Reviewer Agent
- consistency review agent
- 跨任务 debate / 交叉审查
- Subtask DAG 拓扑改造
- review 置信度评分或动态轮次策略
- Debate artifact 的 Web surface 扩张

## Stop / Go 判断

### Stop 判断

当前 phase 应停止继续扩张，理由如下：

- kickoff 定义的 S1 / S2 / S3 已全部完成，并已按 slice 独立提交
- `max_rounds = 3`、artifact 持久化、`waiting_human` 熔断三条核心边界均已满足
- 单任务与子任务 debate 语义已经统一，再继续扩张会自然滑向更重的 reviewer agent 或动态策略系统
- 当前实现已形成一个清晰的 review loop baseline，review 也已完成且无 BLOCK，适合直接进入 PR sync / merge 决策

### Go 判断

下一步应按如下顺序推进：

1. Human 用当前根目录 `pr.md` 同步 PR 描述
2. Human 根据 `docs/plans/phase40/review_comments.md` 与 `docs/concerns_backlog.md` 确认 review disposition
3. Human push 当前分支
4. Human 决定 merge

## 当前稳定边界

Phase 40 closeout 后，以下边界应视为当前实现候选的稳定 checkpoint：

- debate 仅在 `executor_status == completed` 但 review 失败时激活
- 基础 executor failure、launch error、binary fallback failure 不进入 debate
- `max_rounds` 当前固定为 `3`，不开放运行时配置
- feedback 注入保持为 prompt 尾部 markdown section，不改 dialect adapter 接口契约
- 子任务 debate 是 per-card 隔离的，不共享 round 计数或 feedback 状态
- `waiting_human` 仍是 operator rerun gate，不自动恢复执行

## 当前已知问题

- 当前 `suggestions` 仍是基于已知规则检查的启发式映射，不包含更细粒度的 domain-specific repair advice
- debate artifact 目前只写入任务目录，尚未扩展到 Web Control Center 的专门可视化 surface
- `waiting_human` 之后仍需 operator 手动 rerun，不提供自动接续策略
- debate loop 的单任务 / 子任务核心循环仍有一定重复；已记入 backlog
- debate retry executor 事件会混入 Meta-Optimizer route health 聚合；已记入 backlog

以上问题均不阻塞当前进入 merge 阶段。

## 测试结果

最终验证结果：

```text
302 passed in 7.10s
```

补充说明：

- `tests/test_review_gate.py` 覆盖 feedback 生成与 suggestion 映射
- `tests/test_debate_loop.py` 覆盖单任务 retry / 熔断
- `tests/test_dialect_adapters.py` 覆盖 feedback 注入到 Claude XML / Structured Markdown / Codex FIM
- `tests/test_grounding.py` 覆盖 `waiting_human` checkpoint snapshot
- `tests/test_run_task_subtasks.py` 覆盖子任务 debate retry / 熔断 / 非 debate executor failure

## 规则文件同步检查

### 必查

- [x] `docs/plans/phase40/closeout.md`
- [x] `docs/plans/phase40/kickoff.md`
- [x] `docs/plans/phase40/risk_assessment.md`
- [x] `docs/plans/phase40/review_comments.md`
- [x] `docs/active_context.md`
- [x] `docs/concerns_backlog.md`
- [x] `./pr.md`

### 条件更新

- [ ] `AGENTS.md`
- [ ] `README.md`
- [ ] `README.zh-CN.md`

说明：

- 本轮未改变长期协作规则与 README 级对外叙述，暂不更新 `AGENTS.md` / README

## Git / PR 建议

1. 使用当前根目录 `pr.md` 作为 PR 描述草案
2. PR 描述同步当前 review disposition：`0 BLOCK / 2 CONCERN / 1 NOTE / Merge ready`
3. Human push 当前分支并创建 / 更新 PR
4. Human 再决定是否 merge

## 下一轮建议

如果 Phase 40 merge 完成，下一轮应优先考虑 roadmap 中与 Debate Topology 邻接的恢复与协商能力，但不应默认继续扩张到 LLM reviewer 或跨任务对抗。
