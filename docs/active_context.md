# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `Architecture / Engineering`
- latest_completed_phase: `Governance Apply Handler Split / LTO-10`
- latest_completed_slice: `governance.py 642 → 45 行 facade + handler 模块化`
- active_track: `Architecture / Engineering`
- active_phase: `LTO-9 Step 2 — broad CLI command-family migration`
- active_slice: `M3 knowledge family migration complete; awaiting Human review/commit`
- active_branch: `refactor/cli_command_family_migration`
- status: `lto9_step2_m3_complete_awaiting_commit`

## 当前状态说明

当前 git 分支为 `refactor/cli_command_family_migration`,工作树进入 LTO-9 Step 2 实现阶段。当前 HEAD 为:

- `b067f02 refactor(cli): migrate governance-adjacent command families`

LTO-10 已合并到主线:

- `b3f7f43 Governance Apply Handler Maintainability`

LTO-10 完整事实与 milestone 细节见 `docs/plans/governance-apply-handler-split/closeout.md`(本文不复制)。

**簇 C 四金刚 LTO-7 / 8 / 9 / 10 第一遍已完成**(LTO-7 Provider Router facade、LTO-8 Step 1 orchestrator 6 模块、LTO-9 Step 1 CLI / Meta-Optimizer 拆分、LTO-10 governance apply handler 模块化)。这是项目级别的一个里程碑,但 LTO-8 / LTO-9 各有 Step 2 待启动。

`docs/roadmap.md` 已由 `roadmap-updater` post-merge 增量更新,Human Direction Gate 后再做轻量校正:

- §一 baseline "当前重构状态" 反映簇 C 第一遍完成;下一阶段定为 **LTO-9 Step 2 → LTO-8 Step 2**(簇 C 终结)。
- §二 簇 C LTO-10 行标 "已完成"。
- §三 当前 ticket: **LTO-9 Step 2 — broad CLI command-family migration**(LTO-9/LTO-5 收口);下一选择: LTO-8 Step 2 — `harness.py` 拆分(含 event-kind allowlist 新设计点)。
- §五 LTO-10 顺位行标 "已完成"。

**Direction 决定理由**(Human + Claude 讨论后定):

- LTO-9 Step 2 没有新 invariant 设计点,纯机械应用 Step 1 已建立的 adapter / application command 模板;完成后 LTO-5(application/commands 写命令)实质收口。
- LTO-8 Step 2 的 `write_task_artifacts` 9 个 sequential `append_event` 拆分需要 event-kind allowlist 设计 — 是 Step 2 新 invariant 设计点,不只是机械拆分。把它留到最后,让它成为"重构封口 + 簇 C 完全终结"的高密度 phase。
- `v1.6.0` cut 时机:LTO-9 Step 2 merge 后 vs LTO-8 Step 2 merge 后,默认 defer 到簇 C 完全终结(LTO-8 Step 2 完成)。

候选下下阶段:

- **LTO-8 Step 2**:`harness.py` 拆分 + 进一步 `orchestrator.py` 减重 + event-kind allowlist 设计点。Brief 已就绪:`docs/plans/orchestration-lifecycle-decomposition-step2/context_brief.md`(335 行)。

LTO-10 Deferred(已记 closeout / roadmap §二):

- Reviewed route metadata 支持内部进一步拆分(若有可读性收益)。
- Durable governance outbox persistence(待事件 schema 与消费者落地;`apply_outbox.py` 当前为 7 行 no-op 占位)。

LTO-10 PR review concerns(均 non-blocking,合并后无 follow-up 负担):

- CONCERN-1:提交 `9018e25` 标题 "extract route metadata handler" 但 diff 是 M4 outbox 抽出 — commit 已合入 main,后续做 git bisect 时需注意此提交属于 M4。
- CONCERN-2:`apply_outbox.py` 7 行 no-op,与 plan_audit M4 narrowing 授权一致;若后续无事件 schema 落地,可在未来阶段折回 `governance.py`。

LTO-7 long-running follow-ups(仍开放):

- CONCERN-2 / CONCERN-3(`provider_router/router.py` 私有名字耦合、fallback 所有权)记录在 `docs/concerns_backlog.md`,触面 only。

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
12. `docs/plans/governance-apply-handler-split/closeout.md`
13. `docs/plans/governance-apply-handler-split/review_comments.md`
14. `docs/plans/surface-cli-meta-optimizer-split-step2/context_brief.md`
15. `docs/plans/surface-cli-meta-optimizer-split-step2/plan.md`
16. `docs/plans/surface-cli-meta-optimizer-split-step2/plan_audit.md`
17. `docs/plans/orchestration-lifecycle-decomposition-step2/context_brief.md`

## 当前推进

已完成:

- **[Human]** LTO-10 merged to `main` at `b3f7f43`。
- **[Claude / roadmap-updater]** `docs/roadmap.md` post-merge 增量更新:
  - §一 baseline "当前重构状态" 反映簇 C 第一遍完成。
  - §二 簇 C LTO-10 行标 "已完成"。
  - §三 当前 ticket 初版 "LTO-8 Step 2 / LTO-9 Step 2(待 Human 决策)"。
  - §五 LTO-10 顺位标 "已完成"。
- **[Claude]** Tag 评估:见下文 Tag 状态。
- **[Claude / context-analyst x2]** 并行产出两份事实型 brief 帮助 Direction Gate:
  - `docs/plans/orchestration-lifecycle-decomposition-step2/context_brief.md`(335 行;LTO-8 Step 2)
  - `docs/plans/surface-cli-meta-optimizer-split-step2/context_brief.md`(170 行;LTO-9 Step 2)
  - 关键事实:
    - `harness.py` 2077 行,12 个 `append_event` callsite,9 处集中在 `write_task_artifacts` pipeline,需要 event-kind allowlist 新设计点。
    - `cli.py` 3653 行;task 家族 ~800+800+650 ≈ 2250 行,**task 家族写命令不走 `apply_proposal` 路径**(直接调 orchestrator),application/commands 用更简单非 proposal 模式。
    - 两份估算均为 4–5 milestone 独立 phase,**无法合并为一个收尾 phase**(违反 §三 "不允许多条簇 C subtrack 合并到同一个 PR")。
- **[Human]** Direction Gate 决策:**先 LTO-9 Step 2,后 LTO-8 Step 2**(簇 C 终结)。
- **[Claude]** `docs/roadmap.md` Direction Gate 后轻量校正:
  - §一 baseline "下一阶段" 改为 "LTO-9 Step 2 → LTO-8 Step 2"。
  - §三 当前 ticket 改为 LTO-9 Step 2;下一选择 LTO-8 Step 2;候选 Wiki Compiler / 其他。
- **[Codex]** 起草 LTO-9 Step 2 `plan.md`(307 行,基于 brief §9 在 plan §"Scope Decisions From context_brief.md §9" 显式作答 6 条 open question;5 milestone:M1 baseline / M2 governance-adjacent / M3 knowledge / M4 task writes / M5 task reads + cleanup)。
- **[Claude / design-auditor]** Produced plan audit:
  - `docs/plans/surface-cli-meta-optimizer-split-step2/plan_audit.md`
  - verdict: `has-concerns`, 0 blockers / 5 concerns
  - 三条具体代码级 concern 经独立交叉验证:`canonical-reuse-evaluate` 实际是 task subparser(M4 仍合理);`stage-reject` 直调 `update_staged_candidate`(line 2566)非 `apply_proposal`;`apply-suggestions` 直调 `apply_relation_suggestions` → `create_knowledge_relation`(line 2618)非 `apply_proposal`。
- **[Claude]** Plan audit concerns 概览(均非 blocker):
  - CONCERN-1 (M4): `canonical-reuse-evaluate` 与 `consistency-audit` brief 分类为读、plan 放 M4 写 — 加一句 confirm M4 placement 防止 Codex 实施期重新分类。
  - CONCERN-2 (M3): `stage-reject` 调 `update_staged_candidate` 不走 `apply_proposal`;M3 boundary test prohibit 列表未明确该名字,需 explicit permit-or-prohibit 决策。
  - CONCERN-3 (M3): `apply-suggestions` 通过 `apply_relation_suggestions` 内部调 `create_knowledge_relation`;M3 prohibit 列表未涵盖,同 CONCERN-2 路径处理。
  - CONCERN-4 (M2): `apply_proposal` 从 `cli.py` 移到 `application/commands/*` 的 same-commit rule 未显式声明;两段提交会留 silent gap;同时 `test_invariant_guards.py` allowlist 须同 commit 更新。
  - CONCERN-5 (M2–M5 process): "baseline tests pass on pre-migration code" gate 只在 M1 acceptance 出现,M2–M5 应各自带一句话同纪律(对应自己 family 的 baseline);Step 1 同纪律。
- **[Codex]** 已吸收 5 条 plan audit concern 到 `plan.md`:
  - 新增 `Plan Audit Absorption` 节,逐条记录 C-1..C-5 resolution。
  - M2 acceptance 加入 `apply_proposal` callsite 迁移与 invariant guard allowlist / assertion 同 commit 规则。
  - M2–M5 acceptance 均加入对应 family 的 pre-migration characterization gate。
  - M3 scope / acceptance 显式说明 `stage-reject` 与 `apply-suggestions` 不是 `apply_proposal` flow,并定义允许的 high-level staged / relation helper 边界。
  - M4 scope 显式说明 `canonical-reuse-evaluate` / `consistency-audit` 放入 task write/control milestone 的理由。
- **[Human]** Plan Gate 已通过,并已提交最终 plan / audit / state 文档:
  - `b80d3b8 docs(plan): add LTO-9 Step 2 plan`
- **[Human]** M1 baseline characterization tests 已提交:
  - `5bb4660 test(cli): characterize broad command families`
- **[Human]** M2 governance-adjacent small families 已提交:
  - `b067f02 refactor(cli): migrate governance-adjacent command families`

进行中:

- 无。

待执行:

- **[Human]** 审查并提交 M3 knowledge family migration。
- **[Codex]** Human 提交 M3 后进入 M4 task write/control migration。

当前阻塞项:

- 无 blocker。

## Tag 状态

- 最新已执行 tag: `v1.5.0`
- tag target: `bc8abb1 docs(release): sync v1.5.0 release docs`
- 当前结论: defer `v1.6.0` 到簇 C 完全终结后再 cut。理由:LTO-9 Step 2 完成后 LTO-5 实质收口、LTO-8 Step 2 完成后簇 C 真正封口;两 phase 一起作为 `v1.6.0` 内容,信号比"四金刚第一遍"更聚焦。

## 当前下一步

1. **[Human]** 审查并提交 M3 knowledge family migration。
2. **[Codex]** Human 提交 M3 后进入 M4 task write/control migration。

```markdown
plan_gate:
- latest_completed_phase: Governance Apply Handler Split / LTO-10
- merge_commit: b3f7f43 Governance Apply Handler Maintainability
- active_branch: refactor/cli_command_family_migration
- active_phase: LTO-9 Step 2 — broad CLI command-family migration
- active_slice: M3 knowledge family migration complete; awaiting Human review/commit
- direction_decided: LTO-9 Step 2 first, then LTO-8 Step 2 (cluster C closure)
- roadmap: docs/roadmap.md current ticket = LTO-9 Step 2; next choice = LTO-8 Step 2
- context_brief: docs/plans/surface-cli-meta-optimizer-split-step2/context_brief.md (170 lines)
- plan: docs/plans/surface-cli-meta-optimizer-split-step2/plan.md (307 lines)
- plan_audit: docs/plans/surface-cli-meta-optimizer-split-step2/plan_audit.md
- audit_verdict: has-concerns, 0 blockers, 5 concerns absorbed in plan.md
- companion_brief: docs/plans/orchestration-lifecycle-decomposition-step2/context_brief.md (335 lines, ready for LTO-8 Step 2)
- closeout (prior phase): docs/plans/governance-apply-handler-split/closeout.md (status final)
- review (prior phase): recommend-merge; 0 blockers; 2 non-blocking concerns; 1 withdrawn
- tag_decision: defer v1.6.0 until LTO-9 Step 2 + LTO-8 Step 2 both land (cluster C closure)
- next_gate: Human review / commit → M4
```

## 当前产出物

- `docs/roadmap.md`(claude/roadmap-updater + claude 主线, 2026-05-02, post-merge LTO-10 完成 + Direction Gate 决定 LTO-9 Step 2 当前 ticket)
- `docs/plans/governance-apply-handler-split/closeout.md`(codex, 2026-05-02, LTO-10 closeout final)
- `docs/plans/governance-apply-handler-split/review_comments.md`(claude, 2026-05-02, recommend-merge;0 blockers / 2 non-blocking concerns;1 withdrawn)
- `docs/plans/surface-cli-meta-optimizer-split-step2/context_brief.md`(claude/context-analyst, 2026-05-02, LTO-9 Step 2 事实盘点)
- `docs/plans/surface-cli-meta-optimizer-split-step2/plan.md`(codex, 2026-05-02, LTO-9 Step 2 broad CLI command-family migration plan;已吸收 plan audit 5 条 concern)
- `docs/plans/surface-cli-meta-optimizer-split-step2/plan_audit.md`(claude/design-auditor, 2026-05-02, has-concerns, 0 blockers / 5 concerns)
- `docs/plans/orchestration-lifecycle-decomposition-step2/context_brief.md`(claude/context-analyst, 2026-05-02, LTO-8 Step 2 事实盘点;LTO-9 Step 2 完成后启用)
- `docs/active_context.md`(codex, 2026-05-02, LTO-9 Step 2 plan_audit concern 吸收后切到 Human Plan Gate)
- `tests/integration/cli/test_audit_commands.py`(codex, 2026-05-02, M1 audit policy CLI characterization)
- `tests/integration/cli/test_knowledge_commands.py`(codex, 2026-05-02, M1 knowledge stage/promote/reject/ingest characterization)
- `tests/integration/cli/test_route_family_commands.py`(codex, 2026-05-02, M1 route registry/policy/select characterization)
- `tests/integration/cli/test_task_commands.py`(codex, 2026-05-02, M1 task create/list/acknowledge characterization)
- `tests/integration/cli/test_synthesis_commands.py`(codex, 2026-05-02, M1 synthesis run/stage characterization expanded)
- `tests/unit/application/test_command_boundaries.py`(codex, 2026-05-02, M1 planned application command boundary scaffolding)
- `src/swallow/application/commands/route_metadata.py`(codex, 2026-05-03, M2 route registry/policy apply + route select application command boundary)
- `src/swallow/application/commands/policies.py`(codex, 2026-05-03, M2 audit/MPS policy application command boundary)
- `src/swallow/application/commands/synthesis.py`(codex, 2026-05-03, M2 synthesis run/stage application command boundary)
- `src/swallow/surface_tools/cli_commands/route.py`(codex, 2026-05-03, M2 route registry/policy/select CLI adapter)
- `src/swallow/surface_tools/cli_commands/audit.py`(codex, 2026-05-03, M2 audit policy CLI adapter)
- `src/swallow/surface_tools/cli_commands/synthesis.py`(codex, 2026-05-03, M2 synthesis CLI adapter)
- `src/swallow/application/commands/knowledge.py`(codex, 2026-05-03, M3 knowledge write application command boundary)
- `src/swallow/surface_tools/cli_commands/knowledge.py`(codex, 2026-05-03, M3 knowledge CLI adapter)

## 当前验证结果

```bash
.venv/bin/python -m pytest tests/unit/application/test_command_boundaries.py tests/integration/cli/test_audit_commands.py tests/integration/cli/test_knowledge_commands.py tests/integration/cli/test_route_family_commands.py tests/integration/cli/test_synthesis_commands.py tests/integration/cli/test_task_commands.py -q
# 15 passed

.venv/bin/python -m pytest tests/integration/cli tests/unit/application/test_command_boundaries.py -q
# 19 passed

git diff --check
# passed

.venv/bin/python -m pytest tests/integration/cli/test_route_family_commands.py tests/integration/cli/test_audit_commands.py tests/integration/cli/test_synthesis_commands.py tests/unit/application/test_command_boundaries.py tests/test_invariant_guards.py -q
# 39 passed

.venv/bin/python -m pytest tests/integration/cli tests/unit/application/test_command_boundaries.py -q
# 22 passed

git diff --check
# passed

.venv/bin/python -m pytest tests/test_governance.py tests/unit/application/test_command_boundaries.py tests/integration/cli/test_knowledge_commands.py -q
# 22 passed

.venv/bin/python -m pytest tests/integration/cli tests/unit/application/test_command_boundaries.py tests/test_invariant_guards.py -q
# 50 passed

git diff --check
# passed
```
