# Active Context

## 当前轮次

- latest_completed_track: `Evaluation / Policy` (Primary) + `Core Loop` (Secondary)
- latest_completed_phase: `Phase 47`
- latest_completed_slice: `Consensus & Policy Guardrails (v0.5.0)`
- active_track: `Evaluation / Policy` (Primary) + `Core Loop` (Secondary)
- active_phase: `Phase 47`
- active_slice: `phase47_tag_alignment_ready_for_human_commit`
- active_branch: `main`
- status: `phase47_tag_sync_ready_for_human_commit`

---

## 当前状态说明

Phase 47 已完成 merge，`main` 现已吸收 `Consensus & Policy Guardrails` 的全部实现：N-Reviewer 共识 gate、TaskCard 级 `token_cost_limit` 成本护栏、`swl task consistency-audit` 只读一致性抽检入口，以及对应的回归与 eval 基线。当前稳定验证基线为默认 pytest `359 passed, 7 deselected`，eval pytest `7 passed, 359 deselected`。

`v0.5.0` tag 对齐文件修改已完成：`AGENTS.md`、`README.md` 与 `README.zh-CN.md` 的 tag 级描述现已同步到 Phase 47 merge 后的主线事实。`docs/active_context.md` 也已纠正到 merge 后的真实分支状态；`current_state.md` 与下一轮 phase 选择留待本轮 tag sync 提交和打 tag 完成后处理。

---

## 当前关键文档

当前进入 tag sync 前，优先读取：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/roadmap.md`
4. `README.md`
5. `README.zh-CN.md`

仅在需要时再读取：

- `docs/plans/phase47/closeout.md`
- `docs/plans/phase47/review_comments.md`
- `docs/plans/phase47/design_decision.md`
- `docs/plans/phase47/kickoff.md`
- `docs/plans/phase47/context_brief.md`
- `docs/plans/phase47/risk_assessment.md`
- `docs/concerns_backlog.md`

---

## 当前推进

已完成：

- **[Human/Codex]** 完成 Phase 46 并合并至 `main`，打 tag `v0.4.0`。
- **[Gemini]** 完成 Phase 47 `context_brief.md` 与 `roadmap.md` 增量更新。
- **[Claude]** 已产出 Phase 47 `kickoff.md`、`design_decision.md`、`risk_assessment.md`。
- **[Human]** 已授权 Phase 47 进入实现，并切换分支到 `feat/phase47_consensus-guardrails`。
- **[Codex]** 已完成 S1：`TaskCard.reviewer_routes` / `consensus_policy`、planner 透传、`ReviewGate` 共识聚合、orchestrator 接线、`task.planned` / `task.review_gate` 事件可见性均已落地。
- **[Codex]** 已补齐 S1 入口：`create_task(...)` 现在可直接注入 `reviewer_routes` / `consensus_policy`，无需手工修改 task JSON 即可执行真实双路由 gate。
- **[Codex]** 已完成 S1 定向回归：
  - `.venv/bin/python -m pytest tests/test_planner.py tests/test_review_gate.py tests/test_debate_loop.py --tb=short` → `22 passed`
  - `.venv/bin/python -m pytest tests/test_run_task_subtasks.py --tb=short` → `3 passed`
  - `.venv/bin/python -m pytest tests/test_executor_protocol.py --tb=short` → `17 passed`
- **[Codex]** 已完成 S2：`TaskCard.token_cost_limit`、planner / `create_task(...)` 透传、`execution_budget_policy.py` 真实 token cost 聚合、single-task / subtask 预算熔断、`waiting_human` 统一收口、`checkpoint_snapshot` 成本熔断语义修正。
- **[Codex]** 已完成 S2 定向回归：
  - `.venv/bin/python -m pytest tests/test_execution_budget_policy.py tests/test_planner.py tests/test_checkpoint_snapshot.py tests/test_debate_loop.py tests/test_run_task_subtasks.py --tb=short` → `18 passed`
  - `.venv/bin/python -m pytest tests/test_review_gate.py tests/test_grounding.py tests/test_executor_protocol.py --tb=short` → `35 passed`
- **[Codex]** 已完成 S3：新增 `src/swallow/consistency_audit.py`、接入 `swl task consistency-audit <task-id> --auditor-route <route>`，默认抽检 `executor_output.md`，结果写入 `consistency_audit_*.md` artifact。
- **[Codex]** 已完成 S2 + S3 叠加回归：
  - `.venv/bin/python -m pytest tests/test_consistency_audit.py tests/test_execution_budget_policy.py tests/test_planner.py tests/test_checkpoint_snapshot.py tests/test_debate_loop.py tests/test_run_task_subtasks.py tests/test_review_gate.py tests/test_grounding.py tests/test_executor_protocol.py --tb=short` → `56 passed`
- **[Codex]** 已完成 S4：新增 `tests/eval/test_consensus_eval.py`，覆盖 majority / veto / budget exhaustion 三类 Phase 47 核心场景。
- **[Codex]** 已完成 S4 回归护航：
  - `.venv/bin/python -m pytest -m eval --tb=short` → `7 passed, 359 deselected`
  - `.venv/bin/python -m pytest --tb=short` → `359 passed, 7 deselected`
- **[Human]** 已完成 Phase 47 merge，`feat/phase47_consensus-guardrails` 已并入 `main`。
- **[Codex]** 已完成 `v0.5.0` tag 对齐：`AGENTS.md`、`README.md`、`README.zh-CN.md` 与 `docs/active_context.md` 已同步到 merge 后状态。

## 当前产出物

- `docs/plans/phase47/context_brief.md` (gemini, 2026-04-20)
- `docs/plans/phase47/kickoff.md` (claude, 2026-04-20)
- `docs/plans/phase47/design_decision.md` (claude, 2026-04-20)
- `docs/plans/phase47/risk_assessment.md` (claude, 2026-04-20)
- `docs/plans/phase47/closeout.md` (codex, 2026-04-20)
- `docs/plans/phase47/review_comments.md` (claude, 2026-04-20)
- `AGENTS.md` (codex, 2026-04-20)
- `README.md` (codex, 2026-04-20)
- `README.zh-CN.md` (codex, 2026-04-20)

## 当前下一步

- **[Human]** 审查并提交 `AGENTS.md` / `README.md` / `README.zh-CN.md` / `docs/active_context.md` 的 tag sync diff。
- **[Human]** 在 `main` 上创建 tag `v0.5.0`。
- **[Codex]** tag 完成后再更新 `current_state.md` 与下一轮入口状态。

当前阻塞项：

- 无阻塞；等待 Human 审查并提交当前 tag sync diff。
