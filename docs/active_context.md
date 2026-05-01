# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `Architecture / Engineering`
- latest_completed_phase: `Provider Router Split / LTO-7 Step 1`
- latest_completed_slice: `Provider Router Maintainability`
- active_track: `Architecture / Engineering`
- active_phase: `Orchestration Lifecycle Decomposition / LTO-8 Step 1`
- active_slice: `plan audit absorbed; awaiting Human Plan Gate`
- active_branch: `feat/orchestration-lifecycle-decomposition`
- status: `lto8_plan_revised_pending_human_gate`

## 当前状态说明

当前 git 分支为 `feat/orchestration-lifecycle-decomposition`。LTO-7 Provider Router Split 已合并到 `main`:

- `6033558 Provider Router Maintainability`

`docs/roadmap.md` 已由 post-merge factual update 切到下一阶段 ticket:

- 当前 ticket: `Orchestration lifecycle decomposition`
- 对应长期目标: `LTO-8`
- 默认边界: task lifecycle / execution attempts / subtask flow / retrieval flow / knowledge flow helpers
- 硬边界: Control 权限不可转出 Orchestrator

Codex 已按最新 roadmap 起草并根据 plan audit 修订下一阶段计划:

- `docs/plans/orchestration-lifecycle-decomposition/plan.md`
- `docs/plans/orchestration-lifecycle-decomposition/plan_audit.md`

Plan audit 结论为 `has-blockers`，包含 1 个 BLOCKER 与 7 个 CONCERN。Codex 已吸收:

- 将 milestone 数量从 6 降到 5，把原 M6 closeout / PR gate 折进 M5 与 Completion Conditions。
- 明确禁止 helper module 以 import / call / closure / field 等任何形式接收或调用 `save_state`。
- 明确 `harness.py` 不在本 phase 迁移范围内。
- 将 target module 命名对齐 `CODE_ORGANIZATION.md §5`:`subtask_flow.py` / `artifact_writer.py`。
- 明确 helper 默认不得调用 `append_event`，如确需 helper-owned event append 必须先修订计划。
- 明确 M5 不移动 `_apply_librarian_side_effects(...)` 或任何直接 `apply_proposal` caller。

本阶段尚未进入实现。按仓库 workflow,实现前仍需:

1. Human 确认修订后的 `plan.md` 已解决 audit BLOCKER。
2. Human Plan Gate 通过。
3. 当前分支继续保持 `feat/orchestration-lifecycle-decomposition`。

## 当前关键文档

1. `docs/active_context.md`(本文)
2. `current_state.md`
3. `docs/roadmap.md`
4. `docs/plans/orchestration-lifecycle-decomposition/plan.md`
5. `docs/plans/orchestration-lifecycle-decomposition/plan_audit.md`
6. `docs/design/INVARIANTS.md`
7. `docs/design/ORCHESTRATION.md`
8. `docs/design/HARNESS.md`
9. `docs/design/DATA_MODEL.md`
10. `docs/engineering/CODE_ORGANIZATION.md`
11. `docs/engineering/TEST_ARCHITECTURE.md`
12. `docs/plans/provider-router-split/closeout.md`
13. `docs/plans/provider-router-split/review_comments.md`
14. `docs/concerns_backlog.md`

## 当前推进

已完成:

- **[Human]** Merged Provider Router Split into `main`:
  - `6033558 Provider Router Maintainability`
- **[roadmap-updater]** Updated `docs/roadmap.md` to mark LTO-7 done and advance the near-term queue to LTO-8.
- **[Codex]** Drafted LTO-8 plan:
  - `docs/plans/orchestration-lifecycle-decomposition/plan.md`
- **[Codex]** Synced post-merge recovery state:
  - `current_state.md`
  - `docs/active_context.md`
- **[Claude/design-auditor]** Produced LTO-8 plan audit:
  - `docs/plans/orchestration-lifecycle-decomposition/plan_audit.md`
  - result: 1 BLOCKER + 7 CONCERNs
- **[Codex]** Revised LTO-8 plan to absorb audit findings:
  - folded M6 into M5 / Completion Conditions
  - added no-`save_state` closure-injection rule
  - excluded `harness.py` migration from this phase
  - aligned target module names with `CODE_ORGANIZATION.md §5`
  - clarified `append_event` and `apply_proposal` boundaries

进行中:

- **[Human]** Plan Gate for revised LTO-8 plan.

待执行:

- **[Human]** Review revised `docs/plans/orchestration-lifecycle-decomposition/plan.md`.
- **[Human]** Approve Plan Gate if the audit blocker is considered resolved.
- **[Codex]** Start LTO-8 implementation after gate and branch alignment.

当前阻塞项:

- Waiting for Human Plan Gate before implementation.

## Tag 状态

- 最新已执行 tag: `v1.5.0`
- tag target: `bc8abb1 docs(release): sync v1.5.0 release docs`
- tag message: `v1.5.0: raw material store boundary`
- 当前结论: 不为 LTO-7 单独打 tag;等 Cluster-C subtracks 形成更完整能力边界后再评估。

## 当前下一步

1. **[Human]** Review revised `docs/plans/orchestration-lifecycle-decomposition/plan.md`.
2. **[Human]** Approve Plan Gate if accepted.
3. **[Codex]** Implement M1 after gate.

```markdown
milestone_gate:
- current: lto8-plan-revised-after-audit
- active_branch: feat/orchestration-lifecycle-decomposition
- latest_main_checkpoint: 6033558 Provider Router Maintainability
- active_track: Architecture / Engineering
- active_phase: Orchestration Lifecycle Decomposition / LTO-8 Step 1
- active_slice: plan audit absorbed; awaiting Human Plan Gate
- plan: docs/plans/orchestration-lifecycle-decomposition/plan.md (revised after audit)
- plan_audit: docs/plans/orchestration-lifecycle-decomposition/plan_audit.md (1 BLOCKER + 7 CONCERNs)
- audit_absorbed: milestone count, save_state closure ban, harness scope, module naming, append_event boundary, apply_proposal movement boundary
- roadmap: docs/roadmap.md current ticket Orchestration lifecycle decomposition
- recommended_implementation_branch: feat/orchestration-lifecycle-decomposition
- implementation_status: not_started_waiting_human_gate
- next_gate: Human Plan Gate
```

## 当前产出物

- `docs/roadmap.md`(roadmap-updater, 2026-05-01, LTO-7 complete and LTO-8 current ticket)
- `docs/plans/orchestration-lifecycle-decomposition/plan.md`(codex, 2026-05-01, LTO-8 Step 1 plan revised after audit)
- `docs/plans/orchestration-lifecycle-decomposition/plan_audit.md`(claude, 2026-05-01, 1 BLOCKER + 7 CONCERNs)
- `current_state.md`(codex, 2026-05-01, post-merge recovery state for LTO-7 / LTO-8 planning gate)
- `docs/active_context.md`(codex, 2026-05-01, active phase switched to LTO-8 Human Plan Gate)
