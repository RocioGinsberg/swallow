---
author: claude
phase: 47
slice: all
status: review
depends_on:
  - docs/plans/phase47/closeout.md
  - docs/plans/phase47/design_decision.md
  - docs/plans/phase47/kickoff.md
  - src/swallow/review_gate.py
  - src/swallow/execution_budget_policy.py
  - src/swallow/consistency_audit.py
  - src/swallow/orchestrator.py
  - src/swallow/executor.py
  - tests/eval/test_consensus_eval.py
---

> **TL;DR**: Phase 47 实现与 kickoff 完成条件全部对齐，无 block 项。发现 3 个 concern（代码重复、veto 路由隐式约定、成本聚合粒度），均不阻塞 merge，建议在 Phase 48 或后续 slice 中跟进。tag v0.5.0 建议在 merge 后打。

---

# Phase 47 Review Comments

## 总体结论

**结论：可以 merge。**

Phase 47 的四个 slice 均已落地，kickoff 完成条件逐条对齐，全量回归与 eval 均通过。设计边界（`_debate_loop_core` 接口不变、`TaskState` 不膨胀、无 async 引入）得到严格遵守。以下 checklist 按 slice 展开。

---

## Checklist

### S1: N-Reviewer 共识拓扑

| 项目 | 状态 | 说明 |
|------|------|------|
| `reviewer_routes=[]` 退化为单审查员 | **pass** | `run_review_gate` → `review_executor_output`，路径不变 |
| majority 语义：超过半数才通过 | **pass** | `required_count = (total_count // 2) + 1`，1/2 不通过，平局保守失败 |
| veto 语义：第一个路由失败即整体失败 | **pass** | `veto_route = reviewer_results[0]`，逻辑正确 |
| `_debate_loop_core` 接口不变 | **pass** | 只感知 `ReviewGateResult.status`，内部变化完全封装 |
| baseline 结构检查先于 HTTP 审查员 | **pass** | 防止结构无效的输出浪费 HTTP 调用，是合理的防御层 |
| `_build_reviewer_state` 与 `_build_auditor_state` 代码重复 | **concern** | 见下方 C1 |
| veto 路由为"第一个路由"的约定未文档化 | **concern** | 见下方 C2 |

### S2: TaskCard 级成本护栏

| 项目 | 状态 | 说明 |
|------|------|------|
| `token_cost_limit=0.0` 向后兼容 | **pass** | `normalize_token_cost_limit` 将 0 和负值统一归零，不触发检查 |
| 超限后进入 `waiting_human` | **pass** | `_budget_guard_result` 在 attempt 前拦截，`_debate_loop_core` 收到 failed gate 后走 `waiting_human` |
| `budget_exhausted` 事件写入 event log | **pass** | `task.budget_exhausted` / `subtask.N.budget_exhausted` 均已落地 |
| single-task 与 subtask 两条路径均覆盖 | **pass** | `_run_single_task_with_debate` 与 `_run_subtask_attempt` 均接入 `_budget_guard_result` |
| 成本聚合粒度为 task 级而非 card 级 | **concern** | 见下方 C3 |

### S3: 一致性抽检

| 项目 | 状态 | 说明 |
|------|------|------|
| 审计失败时优雅降级写入失败报告 | **pass** | artifact missing、route unknown、execution failed 三种失败路径均写入报告 |
| 不修改 task state | **pass** | `run_consistency_audit` 只调用 `write_artifact`，不触碰 state |
| `load_state` 无 try/except 保护 | **concern** | 见下方 C4 |

### S4: Eval 护航与回归

| 项目 | 状态 | 说明 |
|------|------|------|
| majority / veto / budget exhaustion 三场景覆盖 | **pass** | `test_consensus_eval.py` 三个 eval 测试均通过 |
| budget exhaustion eval 使用 `AssertionError` 守卫 | **pass** | 确保 executor 在预算耗尽后不被调用，是好的测试模式 |
| 全量回归 357 passed | **pass** | 无回归 |
| executor fallback dispatch 修复 | **pass** | 旧路径 `http` fallback 传 `None` prompt 的 bug 已修复，`run_prompt_executor` 统一分发 |

---

## Concerns（不阻塞 merge，建议跟进）

### C1：`_build_reviewer_state` 与 `_build_auditor_state` 代码重复

**位置**：`src/swallow/review_gate.py:411` 与 `src/swallow/consistency_audit.py:51`

两个函数均执行"从 `base_state` 复制 `TaskState` 并覆写路由字段"，逻辑完全相同，约 20 行重复。当前不阻塞，但 Phase 48 引入更多路由调用场景时维护成本会上升。

**建议**：Phase 48 或下一个涉及路由调用的 slice 中，将此逻辑提取为 `_build_routed_state(base_state, route_name) -> tuple[TaskState | None, str]` 放入 `router.py` 或新的 `route_state.py`。

---

### C2：`veto` 策略的"第一个路由为否决路由"约定未文档化

**位置**：`src/swallow/review_gate.py:506`

```python
veto_route_name = reviewer_results[0][0]
veto_passed = reviewer_results[0][1].status == "passed"
```

`veto` 策略隐式依赖 `reviewer_routes` 列表的顺序——第一个路由是否决路由。这个约定在 `TaskCard` 的字段注释、CLI help、以及 `design_decision.md` 中均未明确说明。operator 如果不知道这个约定，可能会把弱模型放在第一位，导致否决权被错误分配。

**建议**：在 `models.py` 的 `TaskCard.reviewer_routes` 字段 docstring 或 `TaskCard.consensus_policy` 字段注释中补充一行说明：`veto` 策略下，列表第一个路由拥有否决权。不需要改逻辑，只需文档化约定。

---

### C3：成本聚合粒度为 task 级，与"TaskCard 级护栏"的命名存在语义差距

**位置**：`src/swallow/execution_budget_policy.py:29`

`calculate_task_token_cost` 扫描 task 的全部 `executor.completed` / `executor.failed` 事件，不区分是哪个 `card_id` 产生的成本。如果一个 task 在执行过程中切换了 card（例如 planner 重新规划），前一个 card 的成本会计入新 card 的限额。

当前场景下这不是 bug——task 级预算比 card 级预算更保守，符合"不超支"的目标。但命名（`token_cost_limit` 在 `TaskCard` 上）与实际行为（task 级聚合）存在语义差距，可能在未来引起混淆。

**建议**：在 `closeout.md` 的"当前已知问题"中补充此说明，或在 `execution_budget_policy.py` 的 `calculate_task_token_cost` 函数注释中说明"聚合范围为 task 全生命周期，不区分 card"。不需要改逻辑。

---

### C4：`run_consistency_audit` 中 `load_state` 无异常保护

**位置**：`src/swallow/consistency_audit.py:158`

```python
state = load_state(base_dir, task_id)
```

如果 `task_id` 不存在，`load_state` 会抛出异常，而不是返回 `ConsistencyAuditResult(status="failed", ...)`。CLI 调用者（`cli.py`）目前没有对此做 try/except，会导致未处理异常暴露给 operator。

**建议**：在 `run_consistency_audit` 入口处加 try/except，捕获 `load_state` 的异常并返回 `ConsistencyAuditResult(status="failed", message=str(exc), ...)`，与其他失败路径保持一致的优雅降级风格。这是一个小改动，可在当前分支修复，也可推迟到 Phase 48。

---

## Tag 建议

Phase 47 新增了三项有意义的能力增量：N-reviewer 共识门禁、TaskCard 级成本熔断、operator 手动一致性抽检。实现干净，向后兼容，无已知稳定性风险。

**建议**：merge 后打 `v0.5.0`，与 kickoff 预期一致。

---

## 收口动作清单

| 动作 | 负责方 | 状态 |
|------|--------|------|
| 产出 `review_comments.md` | Claude | ✅ 本文件 |
| 按 review 结论同步 `pr.md` | Codex | 待执行 |
| 更新 `docs/active_context.md` 标注 review 完成 | Claude | 待执行 |
| C4 修复（可选，当前分支或 Phase 48） | Codex | 待决策 |
| C2 文档补充（`models.py` 注释） | Codex | 待决策 |
| merge `feat/phase47_consensus-guardrails` → `main` | Human | 待执行 |
| 打 tag `v0.5.0` | Human | merge 后执行 |
| 更新 `current_state.md` | Codex | merge 后执行 |
