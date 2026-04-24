---
author: codex
phase: 47
slice: all
status: final
depends_on:
  - docs/plans/phase47/kickoff.md
  - docs/plans/phase47/design_decision.md
  - docs/plans/phase47/risk_assessment.md
  - docs/plans/phase47/review_comments.md
  - docs/active_context.md
---

## TL;DR
Phase 47 已完成实现、review follow-up 吸收与回归复验，当前状态为 **closeout final / ready for human review-closeout commit**。本轮围绕多模型共识与策略护栏，落地了 N-Reviewer `ReviewGate`、TaskCard 级 `token_cost_limit` 熔断、`swl task consistency-audit` 手动抽检入口，以及对应的 eval / 全量回归护航。Claude review 无 block；当前分支已吸收 C2/C4，并文档化 C3。当前验证基线为默认 pytest `359 passed, 7 deselected`，eval pytest `7 passed, 359 deselected`。

# Phase 47 Closeout

## 结论

Phase 47 `Consensus & Policy Guardrails` 已完成实现、review 吸收与验证复验，当前状态为 **closeout final / ready for human review-closeout commit**。

本轮围绕 kickoff 定义的 4 个 slice，完成了四条明确增量：

- S1：N-Reviewer 共识拓扑，支持 `majority` / `veto`
- S2：TaskCard 级真实 `token_cost` 成本护栏
- S3：跨模型一致性抽检入口与审计 artifact
- S4：Phase 47 eval 护航与全量回归收口

当前所有实现 slice 已按提交节奏落账：

- `5a37454 feat(consensus): add multi-reviewer review gate`
- `370a220 feat(policy): add task card token cost guardrails`
- `db2929b feat(cli): add manual consistency audit command`
- `8564cd2 fix(executor): restore cli wrapper fallback dispatch`

另有 phase 文档初始化提交：

- `aab9b5d docs(phase47): initialize phase47`

当前 review-closeout follow-up diff 尚待 Human 审查并提交，内容包括：

- C2：`TaskCard.reviewer_routes` 的 veto 顺序约定文档化
- C4：`run_consistency_audit()` 的 `load_state` 异常保护与 CLI 友好输出
- C3：成本聚合粒度的代码注释与 closeout 说明
- `docs/active_context.md` / `pr.md` / 本 closeout 的收口同步

## Review 吸收情况

- Claude review 结论：**可 merge，无 block 项**
- C2 已吸收：`TaskCard.reviewer_routes` 增加注释，明确 `veto` 策略下列表第一个路由拥有否决权
- C4 已吸收：`run_consistency_audit()` 现在会对缺失或异常 task state 返回 `failed` 结果，CLI 不再因缺失 task 抛出未处理异常
- C3 已文档化：`calculate_task_token_cost()` 现明确说明其聚合范围为 task 全生命周期，而非单个 card
- C1 未在当前分支继续抽象：`_build_reviewer_state` / `_build_auditor_state` 去重留待 Phase 48 或后续路由 slice

## 已完成范围

### Slice 1: N-Reviewer 共识拓扑

- `TaskCard` 新增 `reviewer_routes` 与 `consensus_policy`
- `ReviewGate` 已支持多路 reviewer 顺序执行，并按 `majority` / `veto` 聚合
- planner、`create_task(...)`、single-task debate、subtask debate 均可透传新共识配置
- 保持 `_debate_loop_core()` 外部接口不变；多审查员细节封装在 gate 内部
- 未向 `TaskState` 引入审查历史膨胀字段，沿用 artifact / event 驱动收口

对应提交：

- `5a37454 feat(consensus): add multi-reviewer review gate`

### Slice 2: TaskCard 级成本护栏

- `TaskCard.token_cost_limit` 已落地，0.0 保持向后兼容
- `execution_budget_policy.py` 现可按 task event log 聚合真实 `token_cost`
- single-task 与 subtask 在执行前统一触发预算检查，超限即进入 `waiting_human`
- `checkpoint_snapshot` 已区分 `human_gate_budget_exhausted` 语义

对应提交：

- `370a220 feat(policy): add task card token cost guardrails`

### Slice 3: 一致性抽检入口

- 新增 `src/swallow/consistency_audit.py`
- 新增 `swl task consistency-audit <task-id> --auditor-route <route>` CLI
- 默认对 `executor_output.md` 发起只读审计，并写入 `consistency_audit_*.md`
- 审计失败时会写入失败报告，但不修改 task state，不触发 debate retry

对应提交：

- `db2929b feat(cli): add manual consistency audit command`

### Slice 4: Eval 护航与回归收口

- 新增 `tests/eval/test_consensus_eval.py`
- 覆盖多数票通过、veto 否决、预算熔断进入 `waiting_human` 三个核心场景
- 全量回归时发现 CLI wrapper fallback dispatch 与既有 binary fallback 测试桩签名不兼容，已在本 slice 吸收
- `run_prompt_executor()` 现通过 `run_codex_executor()` / `run_cline_executor()` 保留 executor-level route fallback 参数传播
- binary fallback 测试桩已适配新签名，默认 pytest 与 eval pytest 均恢复全绿

对应提交：

- `8564cd2 fix(executor): restore cli wrapper fallback dispatch`

## 与 kickoff 完成条件对照

### 已完成的目标

- `ReviewGate` 已支持 `reviewer_routes` 配置，并按 `majority` / `veto` 返回统一 gate 结果
- `TaskCard.token_cost_limit` 已接入真实 token cost 累计策略，超限时会记录 `budget_exhausted` 并进入 `waiting_human`
- 一致性抽检 CLI 已可通过 auditor route 对既有 artifact 发起只读审计
- 默认 pytest 与 `pytest -m eval` 均已通过
- eval 已覆盖 Phase 47 的三条关键路径：多数票、否决、成本熔断

### 当前未继续扩张的内容

以下方向仍明确不在本 phase 范围内：

- 不实现异步并发 reviewer 调度
- 不修改 `_debate_loop_core()` 的外部接口
- 不自动触发一致性抽检
- 不自动采纳策略提案或自动 knowledge promotion
- 不向 `TaskState` 继续塞入多 reviewer 历史状态

## 风险吸收情况

### 已吸收

- R1 debate loop 向后兼容性：
  - `reviewer_routes=[]` 仍保持单 reviewer 路径
  - 已通过 `tests/test_review_gate.py`、`tests/test_debate_loop.py`、`tests/test_run_task_subtasks.py`、`tests/test_planner.py` 回归覆盖
- R2 共识平局语义：
  - `majority` 采用“超过半数才通过”，因此 `1/2` 不通过，平局保守失败
- R4 event log 扫描开销：
  - 成本聚合限定在当前 task 事件，不做全局扫描
- SR1 成本翻倍：
  - S2 已在同一 phase 内紧跟落地，避免多 reviewer 路径裸奔
- SR2 Phase 48 并发改造前置：
  - reviewer 调用彼此独立，共识只在汇总后判定，没有引入顺序依赖

### 仍保留为当前边界

- R3 多 reviewer 顺序执行的延迟累积仍存在；本 phase 未引入 async
- R5 审计 prompt 的有效性当前由规则式模板保证，不是更强的结构化审计 DSL
- kickoff 中建议的 S1 “双真实 HTTP 路由 Human gate” 未在仓库中额外沉淀为独立 artifact；当前置信度主要来自单测、eval 与现有 HTTP executor 基线

## 当前稳定边界

Phase 47 实现完成后，当前候选稳定边界如下：

- `ReviewGate` 已从单 reviewer 演进为可配置的 N-reviewer 共识门禁
- 执行预算不再只看 attempt 数量，也可按真实 `token_cost` 熔断
- operator 可以对既有任务产物执行只读一致性审计，而不会污染任务主状态
- eval 继续维持 pytest 内部机制；Phase 47 的新增能力已有最小场景基线
- CLI executor wrapper 与 executor-level route fallback 现在保持一致的参数传播链

## 当前已知问题

- 多 reviewer 仍是顺序执行，真实延迟会随 reviewer 数量线性增长
- 一致性抽检目前仍是人工触发入口，不会自动纳入主任务闭环
- `TaskCard.token_cost_limit` 当前按 task 全生命周期聚合真实 `token_cost`，不区分 planner 是否切换了 card；语义上比“单 card 限额”更保守
- `route state` 构造逻辑在 `review_gate.py` 与 `consistency_audit.py` 之间仍有重复，后续涉及更多 routed state 构造时应统一抽取
- `current_state.md` 仍保持上一个稳定 checkpoint；应在 review / merge 路径明确后再更新

以上问题目前不阻塞 Human 执行 review-closeout commit、PR 同步与后续 merge。

## 测试结果

最终验证结果（含 review follow-up 复验）：

```text
.venv/bin/python -m pytest tests/test_consistency_audit.py --tb=short -> 5 passed
.venv/bin/python -m pytest tests/test_execution_budget_policy.py --tb=short -> 2 passed
.venv/bin/python -m pytest -m eval --tb=short -> 7 passed, 359 deselected
.venv/bin/python -m pytest --tb=short -> 359 passed, 7 deselected
```

补充说明：

- Phase 47 的三类核心语义已有 eval 基线：consensus majority、consensus veto、budget exhaustion
- S4 回归期间发现的 binary fallback 兼容性问题已在当前分支吸收并复验通过
- review follow-up 新增了缺失 task state 的一致性抽检回归，覆盖 CLI 不崩溃语义

## 规则文件同步检查

### 必查

- [x] `docs/plans/phase47/closeout.md`
- [x] `docs/plans/phase47/kickoff.md`
- [x] `docs/plans/phase47/design_decision.md`
- [x] `docs/plans/phase47/risk_assessment.md`
- [x] `docs/active_context.md`

### 条件更新

- [x] `docs/plans/phase47/review_comments.md`
- [x] `./pr.md`
- [ ] `current_state.md`
- [ ] `AGENTS.md`
- [ ] `README.md`
- [ ] `README.zh-CN.md`

说明：

- `review_comments.md` 已产出并已在本稿吸收
- `pr.md` 已按当前 review 结论同步
- 本轮尚未形成新的 merge 后稳定 checkpoint，因此暂不更新 `current_state.md`
- 本轮未改变 tag 级对外快照与长期规则，暂不更新 `AGENTS.md` / README

## Git / PR 建议

1. Human 审查当前 review-closeout diff，并按语义拆分提交
2. Human push `feat/phase47_consensus-guardrails` 并用 `./pr.md` 更新 PR 描述
3. Human 根据 review 结论做 merge 决策
4. merge 完成后由 Codex 更新 `current_state.md`

## 下一轮建议

如果 Phase 47 review 通过并 merge 完成，下一轮应回到 roadmap，优先评估 Phase 48 的异步执行 / 并发 reviewer 路径，或继续补强 operator-facing policy / audit surface，但不应在当前分支继续扩张自动化策略采纳。
