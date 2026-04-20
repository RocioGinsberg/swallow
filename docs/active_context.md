# Active Context

## 当前轮次

- latest_completed_track: `Execution Topology` (Primary) + `Capabilities` (Secondary)
- latest_completed_phase: `Phase 46`
- latest_completed_slice: `Gateway Core Materialization (v0.4.0)`
- active_track: `Evaluation / Policy` (Primary) + `Core Loop` (Secondary)
- active_phase: `Phase 47`
- active_slice: `phase47_review_followups_absorbed`
- active_branch: `feat/phase47_consensus-guardrails`
- status: `phase47_review_followups_ready_for_human_commit`

---

## 当前状态说明

Phase 46 已于 2026-04-20 顺利收口并合并至 `main` 分支，正式发布 `v0.4.0` 版本。主要成果包括：`HTTPExecutor` 落地（直连 `new-api`）、CLI 执行器去品牌化、支持多模型路由（Claude/Qwen/GLM/Gemini/DeepSeek）以及分层降级矩阵。系统已具备真实的多模型网络分发能力。

Phase 47 kickoff 文档已产出并获 Human 授权进入实现，方向为多模型共识与策略护栏：扩展 `ReviewGate` 支持 N-Reviewer 共识拓扑，引入 TaskCard 级成本护栏，新增跨模型一致性抽检入口。整体风险 22/36（中）。S1（N-Reviewer 共识拓扑）已完成：`TaskCard` 支持 `reviewer_routes` / `consensus_policy`，planner 可透传共识配置，`ReviewGate` 已支持多数票 / veto 聚合，single-task 与 subtask 两条 debate 路径都已接入新 gate。S2（TaskCard 级成本护栏）已完成：`TaskCard.token_cost_limit` 已落地，planner / `create_task(...)` 可透传成本上限，`execution_budget_policy.py` 可按 event log 聚合真实 `token_cost`，single-task 与 subtask 两条路径都会在执行前触发预算熔断并统一进入 `waiting_human`，`checkpoint_snapshot` 现可区分 `human_gate_budget_exhausted` 语义。S3（跨模型一致性抽检）已完成：新增 `consistency_audit.py` 只读抽检模块与 `swl task consistency-audit` CLI 手动入口，可指定 auditor route 对既有 artifact 做抽检并产出 `consistency_audit_*.md` 审计 artifact，审计失败时也会优雅降级写入失败报告，不修改 task state。S4（eval 护航与全量回归）已完成：新增 `tests/eval/test_consensus_eval.py` 覆盖多数票通过、veto 否决、预算熔断进入 `waiting_human` 三个场景；同时修复 executor-level route fallback 与既有 binary fallback 测试桩的签名兼容问题，并完成 `pytest` 全量回归与 `pytest -m eval` 验证。Claude review 已产出，结论为可 merge、无 block。当前分支已吸收 C2（veto 路由顺序文档化）与 C4（`load_state` 异常保护），并对 C3（token cost 按 task 生命周期聚合）补充文档说明；默认 pytest 与 eval pytest 已完成 review follow-up 复验。

---

## 当前关键文档

当前进入收口 final sync 前，优先读取：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/roadmap.md`
4. `docs/plans/phase47/closeout.md`
5. `docs/plans/phase47/review_comments.md`

仅在需要时再读取：

- `docs/plans/phase47/design_decision.md`
- `docs/plans/phase47/kickoff.md`
- `docs/plans/phase47/context_brief.md`
- `docs/plans/phase47/risk_assessment.md`
- `docs/plans/phase46/closeout.md`
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
- **[Human]** 已完成 Phase 47 slice 提交：
  - `5a37454 feat(consensus): add multi-reviewer review gate`
  - `370a220 feat(policy): add task card token cost guardrails`
  - `db2929b feat(cli): add manual consistency audit command`
  - `8564cd2 fix(executor): restore cli wrapper fallback dispatch`
- **[Claude]** 已产出 `docs/plans/phase47/review_comments.md`，结论：可 merge，无 block 项；当前分支已吸收其中的 C2/C4。
- **[Codex]** 已吸收 C2/C4，并对 C3 增加代码注释说明：
  - `src/swallow/models.py`：补充 `veto` 策略下 reviewer 顺序约定
  - `src/swallow/consistency_audit.py`：`load_state` 缺失 / 异常时返回 `failed`，CLI 不崩溃
  - `src/swallow/execution_budget_policy.py`：标注 token cost 为 task 生命周期聚合
- **[Codex]** 已完成 review follow-up 复验：
  - `.venv/bin/python -m pytest tests/test_consistency_audit.py --tb=short` → `5 passed`
  - `.venv/bin/python -m pytest tests/test_execution_budget_policy.py --tb=short` → `2 passed`
  - `.venv/bin/python -m pytest -m eval --tb=short` → `7 passed, 359 deselected`
  - `.venv/bin/python -m pytest --tb=short` → `359 passed, 7 deselected`
- **[Codex]** 已完成 `docs/plans/phase47/closeout.md` final sync，并更新 `pr.md` 供 Human 同步 PR。

## 当前产出物

- `docs/plans/phase47/context_brief.md` (gemini, 2026-04-20)
- `docs/plans/phase47/kickoff.md` (claude, 2026-04-20)
- `docs/plans/phase47/design_decision.md` (claude, 2026-04-20)
- `docs/plans/phase47/risk_assessment.md` (claude, 2026-04-20)
- `docs/plans/phase47/closeout.md` (codex, 2026-04-20)
- `src/swallow/models.py` (codex, 2026-04-20)
- `src/swallow/planner.py` (codex, 2026-04-20)
- `src/swallow/executor.py` (codex, 2026-04-20)
- `src/swallow/execution_budget_policy.py` (codex, 2026-04-20)
- `src/swallow/harness.py` (codex, 2026-04-20)
- `src/swallow/review_gate.py` (codex, 2026-04-20)
- `src/swallow/orchestrator.py` (codex, 2026-04-20)
- `src/swallow/consistency_audit.py` (codex, 2026-04-20)
- `src/swallow/cli.py` (codex, 2026-04-20)
- `src/swallow/checkpoint_snapshot.py` (codex, 2026-04-20)
- `tests/eval/test_consensus_eval.py` (codex, 2026-04-20)
- `tests/test_planner.py` (codex, 2026-04-20)
- `tests/test_review_gate.py` (codex, 2026-04-20)
- `tests/test_debate_loop.py` (codex, 2026-04-20)
- `tests/test_run_task_subtasks.py` (codex, 2026-04-20)
- `tests/test_execution_budget_policy.py` (codex, 2026-04-20)
- `tests/test_checkpoint_snapshot.py` (codex, 2026-04-20)
- `tests/test_consistency_audit.py` (codex, 2026-04-20)
- `docs/plans/phase47/review_comments.md` (claude, 2026-04-20)
- `pr.md` (codex, 2026-04-20)

## 当前下一步

- **[Human]** 审查并提交当前 review-closeout diff：
  - `fix(audit): handle missing consistency audit task state`
  - `docs(phase47): sync closeout and pr after review`
- **[Human]** push `feat/phase47_consensus-guardrails`，并按 `./pr.md` 更新 PR 描述。
- **[Human]** merge `feat/phase47_consensus-guardrails` → `main`，如无额外 concern，再打 tag `v0.5.0`。

当前阻塞项：

- 无阻塞；等待 Human 审查并提交当前 review-closeout diff。
