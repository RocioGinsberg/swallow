---
author: claude
phase: 30
slice: Operator Checkpoint & Selective Retry
status: draft
depends_on: [docs/roadmap.md]
---

## TL;DR
Phase 30 在现有全任务级 checkpoint 基础上引入 phase-level checkpoint：(1) 将 run_task 的 retrieval→execution→analysis 三阶段显式化为可检查点，(2) 允许 selective retry 从指定 phase 重跑而非整任务重跑，(3) 在 inspect/review 中暴露 phase checkpoint 状态。不改动 stop_policy 的决策逻辑，不引入 step-level 中断。

---

## 方案总述

源码分析发现当前 checkpoint 粒度为**全任务级**：

```
run_task() → retrieval → execution → analysis → terminal state → checkpoint
```

resume/retry/rerun 三个路径都是从头重跑整个 `run_task()` 流程。区别仅在于 grounding 是否保留（resume 保留，retry/rerun 重置）。这意味着：

1. **retry 浪费**：如果 execution 成功但 analysis 中发现问题（如 validation failure），retry 会重跑 retrieval + execution，即使 retrieval 完全没问题
2. **resume 不够灵活**：resume 只能从失败点"重跑一切"，不能选择"只重跑 execution"
3. **operator 无法观察中间状态**：retrieval 完成后、execution 开始前，operator 看不到中间快照

Phase 30 的目标是将 `run_task()` 内部的三个阶段（retrieval → execution → analysis）显式化为可检查的 phase checkpoint，使 selective retry 成为可能。

**关键约束**：不拆分 `run_task()` 为独立的子命令，不引入 step-level 中断/恢复，不改变 stop_policy 的宏观决策逻辑。

---

## Slice 拆解

### Slice 1: Execution Phase 显式化

**目标**：在 TaskState 中记录当前执行走到了哪个阶段。

**具体内容**：
- `TaskState` 新增 `execution_phase: str` 字段，值域：`"pending"` | `"retrieval_done"` | `"execution_done"` | `"analysis_done"`
- `orchestrator.py` 的 `run_task()` 在每个阶段完成后更新 `execution_phase` 并 `save_state()`：
  - retrieval 完成后 → `execution_phase = "retrieval_done"`
  - execution 完成后 → `execution_phase = "execution_done"`
  - analysis 完成后 → `execution_phase = "analysis_done"`
- 每次 `_begin_execution_attempt()` 时重置 `execution_phase = "pending"`
- 记录 `task.phase_checkpoint` 事件，payload 含 `execution_phase` 和时间戳

**影响范围**：`models.py`（新增字段）、`orchestrator.py`（save_state 调用点）

**风险评级**：
- 影响范围：2（models + orchestrator）
- 可逆性：1（轻松回滚）
- 依赖复杂度：1（无外部依赖）
- **总分：4（低风险）**

**验收条件**：
- 正常 run 结束后 `execution_phase == "analysis_done"`
- 中间失败时 `execution_phase` 停在对应阶段
- state.json 中持久化了 `execution_phase`
- events.jsonl 中有 `task.phase_checkpoint` 事件

---

### Slice 2: Selective Retry 支持

**目标**：允许 retry/rerun 从指定 phase 重跑。

**具体内容**：
- `swl task retry` 和 `swl task rerun` 新增 `--from-phase` 参数：
  - `--from-phase retrieval`（默认，等价于当前行为）
  - `--from-phase execution`（跳过 retrieval，复用上次 retrieval 结果）
  - `--from-phase analysis`（跳过 retrieval + execution，仅重跑 analysis）
- `orchestrator.py` 的 `run_task()` 接受新参数 `skip_to_phase: str = ""`：
  - `""` 或 `"retrieval"` → 正常流程
  - `"execution"` → 跳过 retrieval，加载上次 retrieval items from disk，直接进入 execution
  - `"analysis"` → 跳过 retrieval + execution，加载上次 executor result from disk，直接进入 analysis
- 跳过的阶段仍记录 `task.phase_checkpoint` 事件，标记 `skipped: true`
- `resume` 不支持 `--from-phase`（resume 语义是"从失败点继续"，自动根据 `execution_phase` 决定）

**影响范围**：`cli.py`（parser 扩展）、`orchestrator.py`（run_task 逻辑分支）、`harness.py`（加载历史 retrieval/executor 结果的工具函数）

**风险评级**：
- 影响范围：3（跨模块：cli + orchestrator + harness）
- 可逆性：2（需要额外工作回滚，因为修改了 run_task 核心流程）
- 依赖复杂度：2（依赖 Slice 1 的 execution_phase + 历史 artifact 加载）
- **总分：7（高风险）**

**缓解措施**：
1. `skip_to_phase` 默认为空，不传时行为完全不变
2. 加载历史 retrieval items 时做严格校验（文件存在性、格式合法性），失败则 fallback 到完整 retrieval
3. Slice 2 完成后做全量测试确认零回归

**验收条件**：
- `swl task retry <id> --from-phase execution` 跳过 retrieval，复用上次结果
- `swl task rerun <id> --from-phase analysis` 仅重跑 analysis
- 不传 `--from-phase` 时行为不变
- 跳过的阶段有 skipped 事件记录
- 历史 artifact 不存在时 graceful fallback 到完整流程

---

### Slice 3: Checkpoint 可观测性 (Secondary Track 5)

**目标**：在 operator 视图中暴露 phase checkpoint 状态。

**具体内容**：
- `task inspect` 输出新增：
  - `execution_phase` 当前值
  - `last_phase_checkpoint_at` 最近 checkpoint 时间
- `task review` 同步显示 execution_phase
- checkpoint snapshot 新增 `execution_phase` 字段，供 retry/resume 决策参考
- summary report 新增 execution_phase 信息

**影响范围**：`cli.py`（inspect/review）、`harness.py`（checkpoint snapshot 构建）

**风险评级**：
- 影响范围：2（cli + harness）
- 可逆性：1（轻松回滚）
- 依赖复杂度：2（依赖 Slice 1-2）
- **总分：5（中低风险）**

**验收条件**：
- `task inspect` 显示 execution_phase
- checkpoint snapshot 含 execution_phase
- summary 中有 execution_phase 信息

---

## 依赖说明

```
Slice 1 (execution phase 显式化) ← 无依赖
        ↓
Slice 2 (selective retry)         ← 依赖 Slice 1
        ↓
Slice 3 (checkpoint 可观测性)     ← 依赖 Slice 1-2
```

严格顺序依赖。**Slice 2 是高风险项（总分 7），建议增加人工 gate**：Slice 1 完成后先全量测试确认，Slice 2 实现后再做一次全量测试，确认无回归后再进入 Slice 3。

---

## 明确的非目标

- **不做 step-level 中断/恢复**：phase checkpoint 是"事后记录 + 选择性重跑"，不是"执行中暂停 + 继续"
- **不拆分 `run_task()` 为独立子命令**：retrieval/execution/analysis 仍在一次 run_task 调用中完成
- **不改动 stop_policy 决策逻辑**：stop_policy 继续基于 terminal state 做判断
- **不改动 retry_policy 的 max_attempts 或 retryable 判定**：保持 BASELINE_MAX_ATTEMPTS = 2
- **不做跨任务 checkpoint 或任务链恢复**

---

## Branch Advice

- 当前分支: `main`
- 建议操作: Human 审批后新建分支
- 建议分支名: `feat/phase30-checkpoint-selective-retry`
- 建议 PR 范围: Slice 1-3 统一入一个 PR
- 建议在 Slice 2 完成后增加一次人工确认（因为高风险）

---

## Phase Guard

- [x] 方案不越出 Operator Checkpoint & Selective Retry 的 goals
- [x] 方案不触及非目标（无 step-level 中断、无 run_task 拆分、无 stop_policy 变更）
- [x] Slice 数量 = 3（≤5，合理）
- [x] Primary Track: Core Loop，Secondary Track: Workbench/UX — 符合 roadmap 队列定义
- [x] 高风险 Slice 2（总分 7）已标注，建议增加人工 gate
