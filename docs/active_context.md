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
- active_slice: `context_brief produced; awaiting Codex plan.md`
- active_branch: `main`
- status: `lto9_step2_context_brief_ready`

## 当前状态说明

当前 git 分支为 `main`,工作树干净。LTO-10 已合并到主线:

- `b3f7f43 Governance Apply Handler Maintainability` (HEAD)

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
15. `docs/plans/orchestration-lifecycle-decomposition-step2/context_brief.md`

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

进行中:

- 无。

待执行:

- **[Codex]** 起草 LTO-9 Step 2 `plan.md`(基于 `docs/plans/surface-cli-meta-optimizer-split-step2/context_brief.md`,目标路径 `docs/plans/surface-cli-meta-optimizer-split-step2/plan.md`)。
- **[Claude / design-auditor]** plan.md 产出后 plan audit。
- **[Human]** Plan Gate。

当前阻塞项:

- 无 blocker。等待 Codex plan.md 起草。

## Tag 状态

- 最新已执行 tag: `v1.5.0`
- tag target: `bc8abb1 docs(release): sync v1.5.0 release docs`
- 当前结论: defer `v1.6.0` 到簇 C 完全终结后再 cut。理由:LTO-9 Step 2 完成后 LTO-5 实质收口、LTO-8 Step 2 完成后簇 C 真正封口;两 phase 一起作为 `v1.6.0` 内容,信号比"四金刚第一遍"更聚焦。

## 当前下一步

1. **[Codex]** 起草 `docs/plans/surface-cli-meta-optimizer-split-step2/plan.md`(LTO-9 Step 2 — broad CLI command-family migration);可参考 `context_brief.md §9` 列的 6 条 open question 在 plan 内显式作答。
2. **[Claude / design-auditor]** plan.md 产出后 plan audit。
3. **[Human]** Plan Gate;通过后切 `feat/surface-cli-meta-optimizer-split-step2`(或 Codex 推荐其他名)。

```markdown
plan_gate:
- latest_completed_phase: Governance Apply Handler Split / LTO-10
- merge_commit: b3f7f43 Governance Apply Handler Maintainability
- active_branch: main
- active_phase: LTO-9 Step 2 — broad CLI command-family migration
- active_slice: context_brief produced; awaiting Codex plan.md
- direction_decided: LTO-9 Step 2 first, then LTO-8 Step 2 (cluster C closure)
- roadmap: docs/roadmap.md current ticket = LTO-9 Step 2; next choice = LTO-8 Step 2
- context_brief: docs/plans/surface-cli-meta-optimizer-split-step2/context_brief.md (170 lines)
- companion_brief: docs/plans/orchestration-lifecycle-decomposition-step2/context_brief.md (335 lines, ready for LTO-8 Step 2)
- closeout (prior phase): docs/plans/governance-apply-handler-split/closeout.md (status final)
- review (prior phase): recommend-merge; 0 blockers; 2 non-blocking concerns; 1 withdrawn
- tag_decision: defer v1.6.0 until LTO-9 Step 2 + LTO-8 Step 2 both land (cluster C closure)
- next_gate: Codex plan.md → Claude plan_audit → Human Plan Gate
```

## 当前产出物

- `docs/roadmap.md`(claude/roadmap-updater + claude 主线, 2026-05-02, post-merge LTO-10 完成 + Direction Gate 决定 LTO-9 Step 2 当前 ticket)
- `docs/plans/governance-apply-handler-split/closeout.md`(codex, 2026-05-02, LTO-10 closeout final)
- `docs/plans/governance-apply-handler-split/review_comments.md`(claude, 2026-05-02, recommend-merge;0 blockers / 2 non-blocking concerns;1 withdrawn)
- `docs/plans/surface-cli-meta-optimizer-split-step2/context_brief.md`(claude/context-analyst, 2026-05-02, LTO-9 Step 2 事实盘点)
- `docs/plans/orchestration-lifecycle-decomposition-step2/context_brief.md`(claude/context-analyst, 2026-05-02, LTO-8 Step 2 事实盘点;LTO-9 Step 2 完成后启用)
- `docs/active_context.md`(claude, 2026-05-02, Direction Gate 后切到 LTO-9 Step 2;等待 Codex plan.md)
