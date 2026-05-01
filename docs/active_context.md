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
- active_slice: `plan drafted; awaiting plan audit and Human Plan Gate`
- active_branch: `main`
- status: `lto8_plan_draft_pending_audit`

## 当前状态说明

当前 git 分支为 `main`。LTO-7 Provider Router Split 已合并到 `main`:

- `6033558 Provider Router Maintainability`

`docs/roadmap.md` 已由 post-merge factual update 切到下一阶段 ticket:

- 当前 ticket: `Orchestration lifecycle decomposition`
- 对应长期目标: `LTO-8`
- 默认边界: task lifecycle / execution attempts / subtask flow / retrieval flow / knowledge flow helpers
- 硬边界: Control 权限不可转出 Orchestrator

Codex 已按最新 roadmap 起草下一阶段计划:

- `docs/plans/orchestration-lifecycle-decomposition/plan.md`

本阶段尚未进入实现。按仓库 workflow,实现前仍需:

1. `plan_audit.md` 无未解决 `[BLOCKER]`
2. Human Plan Gate 通过
3. 切到实现分支,建议 `feat/orchestration-lifecycle-decomposition`

## 当前关键文档

1. `docs/active_context.md`(本文)
2. `current_state.md`
3. `docs/roadmap.md`
4. `docs/plans/orchestration-lifecycle-decomposition/plan.md`
5. `docs/design/INVARIANTS.md`
6. `docs/design/ORCHESTRATION.md`
7. `docs/design/HARNESS.md`
8. `docs/design/DATA_MODEL.md`
9. `docs/engineering/CODE_ORGANIZATION.md`
10. `docs/engineering/TEST_ARCHITECTURE.md`
11. `docs/plans/provider-router-split/closeout.md`
12. `docs/plans/provider-router-split/review_comments.md`
13. `docs/concerns_backlog.md`

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

进行中:

- **[Human / Claude]** Plan audit / Plan Gate for LTO-8.

待执行:

- **[Claude/design-auditor]** Produce `docs/plans/orchestration-lifecycle-decomposition/plan_audit.md`.
- **[Codex]** Absorb plan audit findings if needed.
- **[Human]** Approve Plan Gate and create/switch to `feat/orchestration-lifecycle-decomposition`.
- **[Codex]** Start LTO-8 implementation after gate and branch alignment.

当前阻塞项:

- Waiting for plan audit and Human Plan Gate before implementation.

## Tag 状态

- 最新已执行 tag: `v1.5.0`
- tag target: `bc8abb1 docs(release): sync v1.5.0 release docs`
- tag message: `v1.5.0: raw material store boundary`
- 当前结论: 不为 LTO-7 单独打 tag;等 Cluster-C subtracks 形成更完整能力边界后再评估。

## 当前下一步

1. **[Claude/design-auditor]** Review `docs/plans/orchestration-lifecycle-decomposition/plan.md`.
2. **[Codex]** Revise plan if audit finds blocker or concern that should be absorbed before implementation.
3. **[Human]** Approve plan and switch to `feat/orchestration-lifecycle-decomposition`.
4. **[Codex]** Implement M1 after gate.

```markdown
milestone_gate:
- current: lto8-plan-draft
- active_branch: main
- latest_main_checkpoint: 6033558 Provider Router Maintainability
- active_track: Architecture / Engineering
- active_phase: Orchestration Lifecycle Decomposition / LTO-8 Step 1
- active_slice: plan drafted; awaiting plan audit and Human Plan Gate
- plan: docs/plans/orchestration-lifecycle-decomposition/plan.md
- roadmap: docs/roadmap.md current ticket Orchestration lifecycle decomposition
- recommended_implementation_branch: feat/orchestration-lifecycle-decomposition
- implementation_status: not_started_waiting_plan_audit_and_human_gate
- next_gate: plan_audit + Human Plan Gate
```

## 当前产出物

- `docs/roadmap.md`(roadmap-updater, 2026-05-01, LTO-7 complete and LTO-8 current ticket)
- `docs/plans/orchestration-lifecycle-decomposition/plan.md`(codex, 2026-05-01, LTO-8 Step 1 plan draft)
- `current_state.md`(codex, 2026-05-01, post-merge recovery state for LTO-7 / LTO-8 planning gate)
- `docs/active_context.md`(codex, 2026-05-01, active phase switched to LTO-8 planning gate)
