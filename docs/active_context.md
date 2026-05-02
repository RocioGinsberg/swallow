# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `Architecture / Engineering`
- latest_completed_phase: `Orchestration Lifecycle Decomposition / LTO-8 Step 1`
- latest_completed_slice: `Facade-first orchestrator helper extraction`
- active_track: `Architecture / Engineering`
- active_phase: `Surface / CLI / Meta Optimizer Split / LTO-9 Step 1`
- active_slice: `plan revised after audit`
- active_branch: `main`
- status: `lto9_plan_revised_after_audit_waiting_human_gate`

## 当前状态说明

当前 git 分支为 `main`。LTO-8 Step 1 已合并到主线，当前主线 checkpoint:

- `9ee9cc8 docs(state): update roadmap`

`docs/roadmap.md` 已由 Human / roadmap update 切到下一阶段 ticket:

- 当前 ticket: `Surface / CLI / Meta Optimizer split`
- 对应长期目标: `LTO-9 Surface / CLI / Meta Optimizer Modularity` + `LTO-5 Interface / Application Boundary`
- 默认边界: CLI command family split、Meta Optimizer proposal lifecycle modules、application commands / queries seed
- 继承 follow-up: LTO-7 `test_route_metadata_writes_only_via_apply_proposal` allowlist drift fix should be absorbed in this phase

`docs/plans/surface-cli-meta-optimizer-split/plan_audit.md` 已产出，结论为 `has-concerns`，0 blockers / 5 concerns。Codex 已将 5 条 concern 吸收到 `plan.md`:

- M1 增加 `application/commands` no-terminal-formatting source-text boundary tests。
- M2 增加 Meta-Optimizer read-only module persistent source-text boundary tests。
- M3 明确 in-scope `swl` subcommand list，并要求先建立 stdout/stderr/exit-code characterization baseline。
- M4 明确 query tightening 为 optional-if-safe，并加入 go/no-go / skip rationale 规则；route metadata guard fix 仍是 required deliverable。

当前代码事实:

- `src/swallow/surface_tools/cli.py` 约 3790 行，仍承担 parser construction、command dispatch、task/knowledge/route/proposal/audit/synthesis/serve 等多组 surface 逻辑。
- `src/swallow/surface_tools/meta_optimizer.py` 约 1320 行，仍同时承载 telemetry snapshot、proposal generation、proposal bundle IO、review、apply、report 与 executor adapter。
- `src/swallow/surface_tools/web/api.py` 约 374 行，已有 `application/queries/control_center.py` 只读 query pilot，但写命令层尚未系统收口。
- `src/swallow/application/` 当前只有 query pilot；`application/commands/` 尚未建立。

## 当前关键文档

1. `docs/active_context.md`(本文)
2. `current_state.md`
3. `docs/roadmap.md`
4. `docs/design/INVARIANTS.md`
5. `docs/design/INTERACTION.md`
6. `docs/design/SELF_EVOLUTION.md`
7. `docs/design/ORCHESTRATION.md`
8. `docs/design/HARNESS.md`
9. `docs/engineering/CODE_ORGANIZATION.md`
10. `docs/engineering/TEST_ARCHITECTURE.md`
11. `docs/concerns_backlog.md`
12. `docs/plans/orchestration-lifecycle-decomposition/closeout.md`
13. `docs/plans/orchestration-lifecycle-decomposition/review_comments.md`
14. `docs/plans/surface-cli-meta-optimizer-split/plan.md`
15. `docs/plans/surface-cli-meta-optimizer-split/plan_audit.md`

## 当前推进

已完成:

- **[Human]** LTO-8 Step 1 merged to `main`.
- **[roadmap-updater / Human]** Updated `docs/roadmap.md` to mark LTO-8 Step 1 done and advance the current ticket to LTO-9.
- **[Codex]** Confirmed branch/state mismatch and switched active context from LTO-8 merge gate to LTO-9 planning.
- **[Codex]** Produced LTO-9 Step 1 plan:
  - `docs/plans/surface-cli-meta-optimizer-split/plan.md`
- **[Claude/design-auditor]** Produced plan audit:
  - `docs/plans/surface-cli-meta-optimizer-split/plan_audit.md`
  - verdict: `has-concerns`, 0 blockers / 5 concerns
- **[Codex]** Revised `plan.md` to absorb all 5 concerns before Human Plan Gate.

进行中:

- None. Revised LTO-9 plan is waiting for Human Plan Gate.

待执行:

- **[Human]** Review revised plan + audit and decide Plan Gate.
- **[Human]** After Plan Gate, create implementation branch `feat/surface-cli-meta-optimizer-split`.

当前阻塞项:

- 无实现 blocker。实现尚未开始；等待 Human Plan Gate。

## Tag 状态

- 最新已执行 tag: `v1.5.0`
- tag target: `bc8abb1 docs(release): sync v1.5.0 release docs`
- 当前结论: 不为 LTO-8 Step 1 单独打 tag；Cluster C 需要 LTO-7/8/9/10 更完整收敛后再评估 `v1.6.0`。

## 当前下一步

1. **[Human]** Review revised `plan.md` + `plan_audit.md` and decide Plan Gate.
2. **[Human]** If approved, create `feat/surface-cli-meta-optimizer-split` from `main`.
3. **[Codex]** After branch switch and gate approval, start M1 implementation.

```markdown
planning_gate:
- current: lto9-plan-revised-after-audit-waiting-human-gate
- active_branch: main
- latest_main_checkpoint: 9ee9cc8 docs(state): update roadmap
- active_track: Architecture / Engineering
- active_phase: Surface / CLI / Meta Optimizer Split / LTO-9 Step 1
- active_slice: plan revised after audit
- roadmap: docs/roadmap.md current ticket Surface / CLI / Meta Optimizer split
- recommended_implementation_branch: feat/surface-cli-meta-optimizer-split
- plan: docs/plans/surface-cli-meta-optimizer-split/plan.md
- plan_audit: docs/plans/surface-cli-meta-optimizer-split/plan_audit.md
- audit_verdict: has-concerns, 0 blockers, 5 concerns absorbed
- next_gate: Human Plan Gate
```

## 当前产出物

- `docs/roadmap.md`(roadmap-updater/Human, 2026-05-02, LTO-8 Step 1 done and LTO-9 current ticket)
- `docs/plans/surface-cli-meta-optimizer-split/plan.md`(codex, 2026-05-02, LTO-9 Step 1 plan revised after audit)
- `docs/plans/surface-cli-meta-optimizer-split/plan_audit.md`(claude/design-auditor, 2026-05-02, 0 blockers / 5 concerns)
- `docs/active_context.md`(codex, 2026-05-02, LTO-9 plan revised after audit and waiting Human Plan Gate)
