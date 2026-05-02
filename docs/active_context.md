# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `Architecture / Engineering`
- latest_completed_phase: `Surface / CLI / Meta Optimizer Split / LTO-9 Step 1`
- latest_completed_slice: `CLI command-family adapters + Meta-Optimizer read-only split + application command/query seed`
- active_track: `Architecture / Engineering`
- active_phase: `Governance Apply Handler Split / LTO-10`
- active_slice: `M2 canonical + policy handler extraction complete`
- active_branch: `feat/governance-apply-handler-split`
- status: `lto10_m2_complete_waiting_human_commit`

## 当前状态说明

当前 git 分支为 `feat/governance-apply-handler-split`。LTO-9 Step 1 已合并到主线,当前 feature branch 从 LTO-10 planning commit 开始:

- `2183137 docs(plan): governance-apply-handler-split` (planning docs committed; feature branch base commit)
- `f22d5d6 docs(state): update roadmap`
- `21c1884 Surface / Meta Optimizer Modularity`
- `824551a docs(state): mark surface split ready to merge`
- `4b66ad2 fix(cli): make route metadata proposal ids unique`

LTO-9 Step 1 完整事实与 milestone 细节见 `docs/plans/surface-cli-meta-optimizer-split/closeout.md`(本文不复制)。

Human 已提交 planning docs、通过 Plan Gate 并切换到 `feat/governance-apply-handler-split`。M1 已由 Human 提交:

- `34c2c42 refactor(governance): extract proposal registry`

Codex 已完成 M1:

- create `tests/unit/truth_governance/test_governance_boundary.py`
- extract proposal registry / payload ownership behind `governance.py`
- preserve public imports from `swallow.truth_governance.governance`

`docs/roadmap.md` 已由 `roadmap-updater` subagent + Claude 主线 post-merge 增量更新:

- 当前 ticket: `Governance apply handler split`
- 对应长期目标: `LTO-10 Governance Apply Handler Maintainability`
- 默认边界: 私有 canonical / route / policy handler 模块化、transaction envelope、audit/outbox helpers
- 硬边界: `apply_proposal` 仍是唯一公共 mutation entry,不暴露新 mutation 入口
- §一 baseline 已反映 LTO-9 Step 1 完成;§二 LTO-9 行标 "Step 1 已完成" 并列出 deliverables;§五 LTO-9 顺位标 "Step 1 已完成,后续 step 待启动";§二 LTO-5 行反映 application/commands seed 与 application/queries 扩展。

簇 C 内部后续候选(进入近期队列前需 Human 决策):

- LTO-9 Step 2:广泛 task / knowledge / artifact CLI 命令族迁移。
- LTO-8 Step 2:`harness.py`(2077 行)拆分 + 进一步 `orchestrator.py` 减重。

LTO-7 follow-up 状态:

- CONCERN-1(`test_route_metadata_writes_only_via_apply_proposal` allowlist drift)已在 LTO-9 Step 1 M4 消化(guard 现明确指定 `provider_router/route_metadata_store.py` 为物理写入者,`router.py` 仅作为 legacy compatibility facade)。
- CONCERN-2 / CONCERN-3(`provider_router/router.py` 私有名字耦合、fallback 所有权)仍记录在 `docs/concerns_backlog.md` 并保持开放,仅在相关表面被修改时一并合并。

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
12. `docs/plans/surface-cli-meta-optimizer-split/closeout.md`
13. `docs/plans/surface-cli-meta-optimizer-split/review_comments.md`
14. `docs/plans/governance-apply-handler-split/plan.md`
15. `docs/plans/governance-apply-handler-split/plan_audit.md`

## 当前推进

已完成:

- **[Human]** LTO-9 Step 1 merged to `main` at `21c1884`。
- **[Claude / roadmap-updater]** `docs/roadmap.md` post-merge 增量更新:
  - §一 baseline 反映 LTO-9 Step 1 完成,下一阶段指向 LTO-10。
  - §二 簇 B LTO-5 行扩展为 application command seed + application/queries 扩展。
  - §二 簇 C LTO-7 行注明 CONCERN-1 在 LTO-9 Step 1 消化;CONCERN-2/3 仍开放。
  - §二 簇 C LTO-9 行标 "Step 1 已完成",列出 Step 1 deliverables 与延迟事项。
  - §三 当前 ticket 从 "Surface / CLI / Meta Optimizer split" 切换至 "Governance apply handler split (LTO-10)";LTO-9 Step 2 / LTO-8 Step 2 列为后续候选。
  - §五 LTO-9 顺位行标 "Step 1 已完成,后续 step 待启动"。
- **[Claude]** Roadmap 数字校正:`cli.py` 行数 3790 → 3653(实测);`meta_optimizer.py` facade ~50 行(对齐 closeout / active_context 记录)。
- **[Claude]** Tag 评估:见下文 Tag 状态。
- **[Codex]** 起草 LTO-10 Governance apply handler split `plan.md`:
  - `docs/plans/governance-apply-handler-split/plan.md`
  - scope: 私有 proposal registry / canonical / route metadata / policy handler split, apply envelope, post-commit outbox helper tightening
  - hard boundary: `apply_proposal` 仍是唯一 public canonical / route / policy mutation entry
- **[Codex]** 同步恢复入口:
  - `current_state.md`
  - checkpoint_type: `lto10_plan_drafted_pending_audit`
- **[Claude / design-auditor]** Produced plan audit:
  - `docs/plans/governance-apply-handler-split/plan_audit.md`
  - verdict: `has-concerns`, 0 blockers / 5 concerns
  - cross-checked: `governance.py` 642 行;guard allowlist 当前为单条目 `{governance.py}`;LTO-9 Meta-Optimizer 私有 helper 实际归属(`_normalize_task_family_name` / `_timestamp_token` / `_write_json`);`tests/unit/truth_governance/` 不存在
- **[Claude]** Plan audit concerns 概览(均非 blocker,可在对应 milestone 起步前/中吸收):
  - CONCERN-1 (M3): `_apply_route_review_metadata` 仍从 `surface_tools.meta_optimizer` facade 名字导入 6 个符号(其中 4 个在 LTO-9 后是子模块的私有 helper);plan 需在 M3 scope 一句话明确选择哪种迁移路径(facade 导入 / 子模块直接私有导入 / inline 复制 3 个 filesystem helper)。
  - CONCERN-2 (M1): `tests/unit/truth_governance/` 不存在;plan "preferably" 措辞过弱,应明确为 M1 第一步结构性新增,先于任何生产代码移动。
  - CONCERN-3 (M1/M2/M3): guard allowlist(`test_only_governance_calls_repository_write_methods`)与 handler 抽出的迁移顺序未规定。须强制 same-commit 更新规则,避免 mid-milestone guard 假失败 / 假通过。
  - CONCERN-4 (M3): M3 acceptance 应显式命名 4 条具体回归 gate 测试(三条 transaction rollback + 一条 post-commit artifact failure),不能只 "整文件通过"。
  - CONCERN-5 (M4/M5): `governance_models.py` 的 cycle-breaker 限定缺自动化校验;应加 source-text boundary 断言禁止其增长为通用 shared-models 出口。
- **[Codex]** 已将 5 条 plan_audit concern 吸收到 `docs/plans/governance-apply-handler-split/plan.md`:
  - CONCERN-1: M3 明确采用直接 owning-submodule import,不再通过 `surface_tools.meta_optimizer` compatibility facade 导入 route-review helper set。
  - CONCERN-2: M1 明确先创建 `tests/unit/truth_governance/` 与 `test_governance_boundary.py`。
  - CONCERN-3: Boundary Rules / M2 / M3 明确 private writer guard allowlist 与 handler move 同 commit 更新。
  - CONCERN-4: M3 acceptance 明确 4 条 route rollback / post-commit artifact gate tests。
  - CONCERN-5: M1 / M5 明确 `governance_models.py` record-only cycle-breaker source-text boundary。
- **[Human]** Committed LTO-10 planning docs and switched to `feat/governance-apply-handler-split`:
  - `2183137 docs(plan): governance-apply-handler-split`
- **[Codex]** Completed M1 baseline + proposal registry extraction:
  - added `src/swallow/truth_governance/governance_models.py` for public cycle-breaking record types.
  - added `src/swallow/truth_governance/proposal_registry.py` for proposal payload records, pending repo ownership, registration, lookup, validation, and typed proposal accessors.
  - kept `src/swallow/truth_governance/governance.py` as the public facade for existing imports.
  - added `tests/unit/truth_governance/test_governance_boundary.py`.
- **[Codex]** M1 validation passed:
  - `.venv/bin/python -m pytest tests/unit/truth_governance/test_governance_boundary.py -q` -> `3 passed`
  - `.venv/bin/python -m pytest tests/test_governance.py -q` -> `10 passed`
  - `.venv/bin/python -m pytest tests/test_invariant_guards.py -q` -> `25 passed`
  - `.venv/bin/python -m pytest tests/test_phase65_sqlite_truth.py -q` -> `21 passed`
  - `.venv/bin/python -m compileall -q src/swallow` -> passed
  - `git diff --check` -> passed
- **[Codex]** Completed M2 canonical + policy handler extraction:
  - added `src/swallow/truth_governance/apply_canonical.py` as the only current canonical repository private-writer caller.
  - added `src/swallow/truth_governance/apply_policy.py` as the only current policy repository private-writer caller.
  - kept route metadata repository private-writer ownership in `governance.py` until M3.
  - split `tests/test_invariant_guards.py` writer ownership guards so canonical/policy and route metadata have separate allowlists.
- **[Codex]** M2 validation passed:
  - `.venv/bin/python -m pytest tests/unit/truth_governance/test_governance_boundary.py -q` -> `4 passed`
  - `.venv/bin/python -m pytest tests/test_governance.py -q` -> `10 passed`
  - `.venv/bin/python -m pytest tests/test_invariant_guards.py -q` -> `26 passed`
  - `.venv/bin/python -m pytest tests/test_phase65_sqlite_truth.py -q` -> `21 passed`
  - `.venv/bin/python -m compileall -q src/swallow` -> passed
  - `git diff --check` -> passed

进行中:

- 无。

待执行:

- **[Human]** 审查 M2 后执行 milestone commit。

当前阻塞项:

- 无。

## Tag 状态

- 最新已执行 tag: `v1.5.0`
- tag target: `bc8abb1 docs(release): sync v1.5.0 release docs`
- 当前结论: 不为 LTO-9 Step 1 单独打 tag。延续既有 Cluster C 收敛策略 — 待 LTO-10 完成、LTO-8 Step 2 / `harness.py` 拆分推进后,再评估 `v1.6.0`。理由:LTO-9 Step 1 是 behavior-preserving 重构,无外部能力增量;Cluster C 仍有两条 subtrack 未收敛,合并打 tag 更合理。

## 当前下一步

1. **[Human]** 审查 M2 后执行 milestone commit。
2. **[Codex]** 在 Human commit 后进入 M3 route metadata handler extraction。

```markdown
plan_gate:
- latest_completed_phase: Surface / CLI / Meta Optimizer Split / LTO-9 Step 1
- merge_commit: 21c1884 Surface / Meta Optimizer Modularity
- active_branch: feat/governance-apply-handler-split
- active_phase: Governance Apply Handler Split / LTO-10
- active_slice: M2 canonical + policy handler extraction complete
- roadmap: docs/roadmap.md current ticket = Governance apply handler split (LTO-10)
- plan: docs/plans/governance-apply-handler-split/plan.md
- plan_audit: docs/plans/governance-apply-handler-split/plan_audit.md
- audit_verdict: has-concerns, 0 blockers, 5 concerns absorbed
- closeout (prior phase): docs/plans/surface-cli-meta-optimizer-split/closeout.md (status final)
- review (prior phase): recommendation merge; 0 blockers; 2 non-blocking deferred concerns
- lto7_followup: CONCERN-1 resolved in LTO-9 Step 1 M4; CONCERN-2/3 still open in concerns_backlog
- tag_decision: defer v1.6.0 until LTO-10 + LTO-8 Step 2 land
- latest_milestone_commit: 34c2c42 refactor(governance): extract proposal registry
- next_gate: Human M2 milestone commit
```

## 当前产出物

- `docs/roadmap.md`(claude/roadmap-updater + claude 主线, 2026-05-02, post-merge LTO-9 Step 1 完成 + LTO-10 当前 ticket)
- `docs/plans/surface-cli-meta-optimizer-split/closeout.md`(codex, 2026-05-02, LTO-9 Step 1 closeout final)
- `docs/plans/surface-cli-meta-optimizer-split/review_comments.md`(claude, 2026-05-02, recommendation merge; 0 blockers; 2 non-blocking concerns)
- `docs/plans/governance-apply-handler-split/plan.md`(codex, 2026-05-02, LTO-10 plan revised after audit)
- `docs/plans/governance-apply-handler-split/plan_audit.md`(claude/design-auditor, 2026-05-02, has-concerns, 0 blockers / 5 concerns)
- `current_state.md`(codex, 2026-05-02, LTO-10 plan audit concerns absorbed recovery checkpoint)
- `src/swallow/truth_governance/governance_models.py`(codex, 2026-05-02, M1 public governance record types)
- `src/swallow/truth_governance/proposal_registry.py`(codex, 2026-05-02, M1 proposal payload registry ownership)
- `src/swallow/truth_governance/apply_canonical.py`(codex, 2026-05-02, M2 canonical apply handler)
- `src/swallow/truth_governance/apply_policy.py`(codex, 2026-05-02, M2 policy apply handler)
- `src/swallow/truth_governance/governance.py`(codex, 2026-05-02, M2 public facade delegates canonical / policy handlers; route handler remains for M3)
- `tests/unit/truth_governance/test_governance_boundary.py`(codex, 2026-05-02, M2 boundary tests)
- `tests/test_invariant_guards.py`(codex, 2026-05-02, M2 private writer ownership guard split)
- `docs/active_context.md`(codex, 2026-05-02, LTO-10 M2 complete;waiting Human milestone commit)
