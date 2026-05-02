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
- active_phase: `awaiting Human direction (next subtrack TBD)`
- active_slice: `direction gate; LTO-8 Step 2 vs LTO-9 Step 2 vs other`
- active_branch: `main`
- status: `cluster_c_first_pass_complete_awaiting_direction`

## 当前状态说明

当前 git 分支为 `main`,工作树干净。LTO-10 已合并到主线:

- `b3f7f43 Governance Apply Handler Maintainability` (HEAD)

LTO-10 完整事实与 milestone 细节见 `docs/plans/governance-apply-handler-split/closeout.md`(本文不复制)。

**簇 C 四金刚 LTO-7 / 8 / 9 / 10 第一遍已完成**(LTO-7 Provider Router facade、LTO-8 Step 1 orchestrator 6 模块、LTO-9 Step 1 CLI / Meta-Optimizer 拆分、LTO-10 governance apply handler 模块化)。这是项目级别的一个里程碑,但 LTO-8 / LTO-9 各有 Step 2 待启动。

`docs/roadmap.md` 已由 `roadmap-updater` post-merge 增量更新:

- §一 baseline "当前重构状态" 反映簇 C 第一遍完成,下一阶段 LTO-8 Step 2 / LTO-9 Step 2 候选,具体由 Human 决策。
- §二 簇 C LTO-10 行标 "已完成",列出 facade reduction 与 deferred 项(reviewed-route 内部拆分、durable outbox)。
- §三 当前 ticket 切换为 "LTO-8 Step 2 / LTO-9 Step 2(待 Human 决策)";Wiki Compiler 维持 "下一选择" 层级。
- §五 LTO-10 顺位行标 "已完成"。

候选下阶段(待 Human 决策,见 `docs/roadmap.md §三`):

- **LTO-8 Step 2**:`harness.py`(2077 行)拆分 + 进一步 `orchestrator.py` 减重。
- **LTO-9 Step 2**:广泛 task / knowledge / artifact CLI 命令族迁移 + `application/commands` 写命令完整迁移 + FastAPI 写路由模式。
- 其他可能性:Wiki Compiler 启动(LTO-1)、Test Architecture 收口(LTO-4)、Knowledge Plane 命名整理(LTO-6)、代码卫生独立 audit phase(memory 中已记的 Phase 65 后启动决策)。

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

## 当前推进

已完成:

- **[Human]** LTO-10 merged to `main` at `b3f7f43`。
- **[Claude / roadmap-updater]** `docs/roadmap.md` post-merge 增量更新:
  - §一 baseline "当前重构状态" 反映簇 C 第一遍完成。
  - §二 簇 C LTO-10 行标 "已完成"。
  - §三 当前 ticket 切换为 "LTO-8 Step 2 / LTO-9 Step 2(待 Human 决策)"。
  - §五 LTO-10 顺位标 "已完成"。
- **[Claude]** Tag 评估:见下文 Tag 状态。

进行中:

- 无。

待执行:

- **[Human]** Direction Gate:在 LTO-8 Step 2 / LTO-9 Step 2 / 其他 LTO 之间决策下阶段。
- 决策后:Codex 起草下阶段 plan.md(可选先 `context-analyst` subagent 产 context_brief);Claude/design-auditor plan audit;Human Plan Gate。

当前阻塞项:

- 无 blocker。等待 Human Direction Gate。

## Tag 状态

- 最新已执行 tag: `v1.5.0`
- tag target: `bc8abb1 docs(release): sync v1.5.0 release docs`
- 当前结论: **可以考虑评估 `v1.6.0` cut**。理由:簇 C 四金刚第一遍已完成,这是 architecture cluster 级别的里程碑;Provider Router / Orchestration Step 1 / CLI&Meta-Optimizer Step 1 / Governance handler 拆分构成可观察的内部能力增量(`apply_proposal` 仍是唯一 mutation entry,facade-first 纪律已固化)。
- 替代结论(默认): 继续 defer 到 LTO-8 Step 2 / LTO-9 Step 2 之一完成,合并打 `v1.6.0`,信号更聚焦。
- 决定权:Human;两种都合理。Claude 倾向轻微偏向 **defer 一轮**:LTO-8 Step 2 是 cluster C 真正的核心痛点(harness.py 2077 行未拆),把它纳入 v1.6.0 的"重构封口"叙事更完整;只是若 Human 想为四金刚第一遍单独打里程碑 tag 也合理。

## 当前下一步

1. **[Human]** Direction Gate: 选择下阶段(LTO-8 Step 2 / LTO-9 Step 2 / 其他 LTO / Wiki Compiler 启动)+ 决定 `v1.6.0` 现在 cut 还是再等一轮。
2. **[Codex]** 决策后起草下阶段 plan.md(可选先 context-analyst 产 context_brief)。
3. **[Claude / design-auditor]** plan.md 产出后 plan audit。
4. **[Human]** Plan Gate。

```markdown
direction_gate:
- latest_completed_phase: Governance Apply Handler Split / LTO-10
- merge_commit: b3f7f43 Governance Apply Handler Maintainability
- active_branch: main
- cluster_c_first_pass: complete (LTO-7, LTO-8 Step 1, LTO-9 Step 1, LTO-10)
- candidates_for_next_phase: LTO-8 Step 2 (harness.py decomposition) | LTO-9 Step 2 (broad CLI command-family migration) | other LTO
- roadmap: docs/roadmap.md current ticket = LTO-8 Step 2 / LTO-9 Step 2 (Human decision pending)
- closeout: docs/plans/governance-apply-handler-split/closeout.md (status final)
- review: recommend-merge; 0 blockers; 2 non-blocking concerns; 1 withdrawn
- tag_decision: v1.6.0 evaluation pending Human direction (cut now for cluster-C first-pass milestone, or defer until LTO-8/9 Step 2)
- next_gate: Human direction → Codex plan.md → Claude plan_audit → Human Plan Gate
```

## 当前产出物

- `docs/roadmap.md`(claude/roadmap-updater, 2026-05-02, post-merge LTO-10 完成 + cluster C 第一遍完成 + LTO-8/9 Step 2 候选)
- `docs/plans/governance-apply-handler-split/closeout.md`(codex, 2026-05-02, LTO-10 closeout final)
- `docs/plans/governance-apply-handler-split/review_comments.md`(claude, 2026-05-02, recommend-merge;0 blockers / 2 non-blocking concerns;1 withdrawn)
- `docs/active_context.md`(claude, 2026-05-02, post-merge state synced;awaiting Direction Gate;tag 评估记录)
