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
- active_slice: `M1 application command seed complete`
- active_branch: `feat/surface-cli-meta-optimizer-split`
- status: `lto9_m1_application_commands_complete_waiting_human_commit`

## 当前状态说明

当前 git 分支为 `feat/surface-cli-meta-optimizer-split`。LTO-8 Step 1 已合并到主线，当前 main checkpoint:

- `9ee9cc8 docs(state): update roadmap`

Human 已批准 Plan Gate，创建并切换到实现分支，且已提交修订后的 plan / audit / state docs:

- `e692408 docs(plan): revise surface split plan after audit`

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

- `src/swallow/surface_tools/cli.py` 仍承担 parser construction、command dispatch、task/knowledge/route/proposal/audit/synthesis/serve 等多组 surface 逻辑；M1 已让 `meta-optimize` / `proposal review` / `proposal apply` dispatch 调用 application commands，但尚未进入 M3 adapter split。
- `src/swallow/surface_tools/meta_optimizer.py` 仍承载 telemetry snapshot、proposal generation、proposal bundle IO、review、apply facade、report 与 executor adapter；M1 已让 `apply_reviewed_optimization_proposals(...)` 兼容函数委托到 application command。
- `src/swallow/surface_tools/web/api.py` 约 374 行，已有 `application/queries/control_center.py` 只读 query pilot，但写命令层尚未系统收口。
- `src/swallow/application/commands/` 已建立 M1 种子:
  - `meta_optimizer.py` 提供 structured run command result。
  - `proposals.py` 提供 proposal review/apply command result，并通过 `register_route_metadata_proposal` + `apply_proposal` 进入治理边界。

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
- **[Human]** Approved Plan Gate, created `feat/surface-cli-meta-optimizer-split`, and committed planning docs:
  - `e692408 docs(plan): revise surface split plan after audit`
- **[Codex]** Completed M1 application command seed:
  - added `src/swallow/application/commands/`
  - moved CLI `meta-optimize` / `proposal review` / `proposal apply` dispatch to application commands
  - kept terminal formatting in CLI and report builders
  - added source-text boundary tests for application command modules
- **[Codex]** M1 validation passed:
  - `.venv/bin/python -m pytest tests/unit/application/test_command_boundaries.py -q` -> `2 passed`
  - `.venv/bin/python -m pytest tests/unit/application -q` -> `3 passed`
  - `.venv/bin/python -m pytest tests/test_meta_optimizer.py -k "review_and_apply" -q` -> `3 passed, 16 deselected`
  - `.venv/bin/python -m pytest tests/test_cli.py -k "proposal_review_and_apply_cli_flow or proposal_apply_cli_persists_route_capability_profile" -q` -> `2 passed, 240 deselected`
  - `.venv/bin/python -m pytest tests/test_invariant_guards.py -q` -> `25 passed`
  - `.venv/bin/python -m pytest tests/test_meta_optimizer.py -q` -> `19 passed`
  - `.venv/bin/python -m pytest tests/test_cli.py -k "proposal or meta_optimizer or route_capabilities or route_weights or serve" -q` -> `11 passed, 231 deselected`
  - `.venv/bin/python -m compileall -q src/swallow` -> passed
  - `git diff --check` -> passed

进行中:

- None. M1 is ready for Human milestone review / commit.

待执行:

- **[Human]** Review and commit M1 implementation if accepted.
- **[Codex]** After Human confirms M1 commit, start M2 Meta-Optimizer read-only module split.

当前阻塞项:

- 无 blocker。

## Tag 状态

- 最新已执行 tag: `v1.5.0`
- tag target: `bc8abb1 docs(release): sync v1.5.0 release docs`
- 当前结论: 不为 LTO-8 Step 1 单独打 tag；Cluster C 需要 LTO-7/8/9/10 更完整收敛后再评估 `v1.6.0`。

## 当前下一步

1. **[Human]** Review and commit M1 implementation if accepted.
2. **[Codex]** After commit confirmation, start M2 Meta-Optimizer read-only module split.

```markdown
milestone_gate:
- current: lto9-m1-application-commands-complete-waiting-human-commit
- active_branch: feat/surface-cli-meta-optimizer-split
- latest_main_checkpoint: 9ee9cc8 docs(state): update roadmap
- planning_commit: e692408 docs(plan): revise surface split plan after audit
- active_track: Architecture / Engineering
- active_phase: Surface / CLI / Meta Optimizer Split / LTO-9 Step 1
- active_slice: M1 application command seed complete
- roadmap: docs/roadmap.md current ticket Surface / CLI / Meta Optimizer split
- plan: docs/plans/surface-cli-meta-optimizer-split/plan.md
- plan_audit: docs/plans/surface-cli-meta-optimizer-split/plan_audit.md
- audit_verdict: has-concerns, 0 blockers, 5 concerns absorbed
- m1_validation: unit application `3 passed`; meta optimizer focused `3 passed`; proposal CLI focused `2 passed`; invariant guards `25 passed`; full meta optimizer `19 passed`; focused CLI selector `11 passed`; compileall passed; git diff --check passed
- next_gate: Human M1 milestone review and commit
```

## 当前产出物

- `docs/roadmap.md`(roadmap-updater/Human, 2026-05-02, LTO-8 Step 1 done and LTO-9 current ticket)
- `docs/plans/surface-cli-meta-optimizer-split/plan.md`(codex, 2026-05-02, LTO-9 Step 1 plan revised after audit)
- `docs/plans/surface-cli-meta-optimizer-split/plan_audit.md`(claude/design-auditor, 2026-05-02, 0 blockers / 5 concerns)
- `src/swallow/application/commands/__init__.py`(codex, 2026-05-02, application command package seed)
- `src/swallow/application/commands/meta_optimizer.py`(codex, 2026-05-02, structured meta optimizer command result)
- `src/swallow/application/commands/proposals.py`(codex, 2026-05-02, proposal review/apply application commands)
- `tests/unit/application/test_command_boundaries.py`(codex, 2026-05-02, terminal formatting and proposal writer boundary checks)
- `src/swallow/surface_tools/cli.py`(codex, 2026-05-02, M1 dispatch delegation to application commands)
- `src/swallow/surface_tools/meta_optimizer.py`(codex, 2026-05-02, compatibility apply function delegates to application command)
- `docs/active_context.md`(codex, 2026-05-02, LTO-9 M1 complete and waiting Human milestone commit)
