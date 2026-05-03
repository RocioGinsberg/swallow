# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `Architecture / Engineering`
- latest_completed_phase: `LTO-8 Step 2 — harness decomposition (cluster C closure)`
- latest_completed_slice: `v1.6.0 tagged; cluster C fully closed`
- active_track: `Interface / Application Boundary`
- active_phase: `LTO-13 — FastAPI Local Web UI Write Surface`
- active_slice: `plan_audit absorbed; awaiting Human Plan Gate`
- active_branch: `main`
- status: `lto13_plan_audit_absorbed`

## 当前状态说明

当前 git 分支为 `main`。进入 LTO-13 plan / audit 文档更新前,HEAD 为:

- `0e6215a docs(release): sync v1.6.0 release docs`
- `ea4a886 Orchestration Lifecycle Decomposition`(LTO-8 Step 2 merge commit)

`v1.6.0` annotated tag 已 cut,标记 cluster C 完整闭合。

**簇 C 状态**:LTO-7 / LTO-8(Step 1+Step 2)/ LTO-9(Step 1+Step 2)/ LTO-10 全部完成。LTO-8 Step 2 完整事实见 `docs/plans/orchestration-lifecycle-decomposition-step2/closeout.md`。

`docs/roadmap.md` 已 post-merge + cluster C closure 同步,本轮一次性完成 7 项调整:

- §一 baseline "当前重构状态" 切到 "簇 C 完全终结";v1.6.0 已发布;下一启动 LTO-13。
- §二 簇 C LTO-8 行标 "已完成"(Step 1 + Step 2);列出 harness.py -50% 与 helper-side append_event allowlist 新 invariant。
- §二 LTO-13 **从簇 C 移回簇 B**(纠正之前 roadmap-updater 误分类:LTO-13 是接口边界 defer 项,性质同 LTO-5/LTO-6,不是簇 C 接续)。
- §二 簇 B 标题 "架构重构已开头 seed";cluster description 加 "+ 接口边界" 说明 LTO-13 性质。
- §二 簇 C 子标题去掉 "+ 接续";改为 "已完全终结"。
- §二 LTO-6 行加 "作为 touched-surface 慢推,不专门开 phase" 说明。
- §三 当前 ticket 切到 **LTO-13**;下一选择 = Wiki Compiler / LTO-6 / LTO-4 / LTO-5(视真实需求)。
- §四 v1.6.0 tag 决策 "已执行"(2026-05-03;tag target = `0e6215a`)。
- §五 推荐顺序更新:`簇 C(done)→ LTO-13 → 后续视真实需求`;LTO-8 顺位 "Step 1 + Step 2 已完成"。

**Direction 决定理由**(Human + Claude 讨论后定):

- LTO-13 不依赖 LTO-5(repository ports)/LTO-6(knowledge plane facade migration)— application/commands 已在 LTO-9 Step 2 完成,作为 LTO-13 与下层架构之间的缓冲层。
- LTO-5 / LTO-6 重构发生在 application 之下,不会让 LTO-13 已写代码改一行。
- LTO-6 当前状态:`application/commands/{synthesis,knowledge}.py` 还直接 import 6 个 `knowledge_retrieval.*` 子模块,绕开 `knowledge_plane` facade。LTO-13 plan 实施时显式约束新增 application 层调用走公共导出,避免直接 reach `knowledge_retrieval.*` 子模块。
- Human 真实需求 = WebUI 写支持,优先级高于簇 B 慢推项。

LTO-8 Step 2 deferred(已记 closeout):

- `harness.py` 1028 行包含 `build_summary` / `build_resume_note` / `build_task_memory` / `write_task_artifacts` body,真实需求触发可单独开 phase。

LTO-10 deferred(仍开放):

- Reviewed route metadata 内部拆分(若有可读性收益)。
- Durable governance outbox persistence(待事件 schema 与消费者落地)。

LTO-7 long-running follow-ups(仍开放):

- CONCERN-2 / CONCERN-3(`provider_router/router.py` 私有名字耦合、fallback 所有权)记录在 `docs/concerns_backlog.md`,触面 only。

## 当前关键文档

1. `docs/active_context.md`(本文)
2. `current_state.md`
3. `docs/roadmap.md`
4. `docs/design/INVARIANTS.md`
5. `docs/design/INTERACTION.md`
6. `docs/design/SELF_EVOLUTION.md`
7. `docs/design/HARNESS.md`
8. `docs/engineering/CODE_ORGANIZATION.md`
9. `docs/engineering/TEST_ARCHITECTURE.md`
10. `docs/concerns_backlog.md`
11. `docs/plans/orchestration-lifecycle-decomposition-step2/closeout.md`
12. `docs/plans/orchestration-lifecycle-decomposition-step2/review_comments.md`

## 当前推进

已完成:

- **[Human]** LTO-8 Step 2 merged to `main` at `ea4a886`(含 review-fix `dc62eba` + closeout `a25a554`)。
- **[Human]** v1.6.0 release docs commit + annotated tag `v1.6.0` 已 cut(target `0e6215a`)。
- **[Claude / roadmap-updater + 主线]** 一次性完成 7 项 roadmap 结构调整(post-merge LTO-8 Step 2 完成同步、簇 C 完全终结、LTO-13 从簇 C 移回簇 B、§三 当前 ticket = LTO-13、§四 v1.6.0 tag 决策标"已执行"、§五 顺序更新)+ 2 处轻量校正(§二 簇 C 子标题、§三 LTO-13 状态/Gate 列)。
- **[Claude]** Direction Gate 讨论后决定:**直接做 LTO-13**(不先做 LTO-5 / LTO-6);理由 = application/commands 是 LTO-13 与下层重构的缓冲层,LTO-5 / LTO-6 重构不会让 LTO-13 重写。
- **[Codex]** 产出 `docs/plans/lto-13-fastapi-local-web-ui-write-surface/plan.md`,明确 FastAPI 写路由范围、HTTP contract、guard 扩展和 milestone gate。
- **[Claude / design-auditor]** 产出 `plan_audit.md`:has-concerns;0 blockers / 5 concerns / 1 nit。
- **[Codex]** 已吸收 plan_audit 5 个 concern + 1 个 nit:workspace_root pre-existing gap、FastAPI dev dependency、proposal artifact relative path bridge、M2 `apply_proposal` UI guard、OperatorToken source 决策、static index test 归属。

进行中:

- 无。

待执行:

- **[Human]** Plan Gate;通过后切 `feat/lto-13-fastapi-local-web-ui-write-surface`(或类似名)。

当前阻塞项:

- 无 blocker。plan_audit concerns 已吸收,等待 Human Plan Gate。

## Tag 状态

- 最新已执行 tag: **`v1.6.0`**(2026-05-03)
- tag target: `0e6215a docs(release): sync v1.6.0 release docs`
- 标记意义:**cluster C closure**(LTO-7 + LTO-8 Step 1+Step 2 + LTO-9 Step 1+Step 2 + LTO-10 全部完成)
- 下一 tag 评估:LTO-13 完成后视情况评估 `v1.7.0`(WebUI write surface 是首次 LLM-外可观察能力增量;但也可累积更多产品向 phase 后再 cut)。

## 当前下一步

1. **[Human]** Plan Gate。
2. **[Human]** Plan Gate 通过后切 `feat/lto-13-fastapi-local-web-ui-write-surface`。

```markdown
direction_gate:
- latest_completed_phase: LTO-8 Step 2 — harness decomposition
- merge_commit: ea4a886 Orchestration Lifecycle Decomposition
- release_tag: v1.6.0 at 0e6215a docs(release): sync v1.6.0 release docs
- active_branch: main
- active_phase: LTO-13 — FastAPI Local Web UI Write Surface
- active_slice: plan_audit absorbed; awaiting Human Plan Gate
- cluster_c_status: fully closed (LTO-7 + LTO-8 Step 1+Step 2 + LTO-9 Step 1+Step 2 + LTO-10)
- structural_changes_this_round: LTO-13 relocated 簇 C → 簇 B (interface boundary nature, not cluster C continuation); cluster C subheading dropped "+ 接续"; v1.6.0 tag decision marked executed
- direction_decided: do LTO-13 directly; LTO-5 / LTO-6 do not block LTO-13 (application/commands is the buffer layer)
- roadmap: docs/roadmap.md current ticket = LTO-13; next choice = Wiki Compiler / LTO-6 / LTO-4 / LTO-5 (per real demand)
- closeout (prior phase): docs/plans/orchestration-lifecycle-decomposition-step2/closeout.md (status final)
- review (prior phase): recommend-merge; 0 blockers; 2 non-blocking concerns (both absorbed)
- new_invariants_landed: helper-side append_event allowlist (12 telemetry kinds + 2 disallowed) registered in INVARIANTS.md §9
- next_gate: Human Plan Gate (plan_audit complete; 5 concerns + 1 nit absorbed; 0 blockers)
```

## 当前产出物

- `docs/roadmap.md`(claude/roadmap-updater + claude 主线, 2026-05-03, post-merge LTO-8 Step 2 完成 + cluster C 完全终结 + LTO-13 移回簇 B + §三 切到 LTO-13 + §四 v1.6.0 已执行)
- `docs/plans/lto-13-fastapi-local-web-ui-write-surface/plan.md`(codex, 2026-05-03, LTO-13 phase plan; plan_audit concerns absorbed)
- `docs/plans/lto-13-fastapi-local-web-ui-write-surface/plan_audit.md`(claude/design-auditor, 2026-05-03, has-concerns; 0 blockers / 5 concerns / 1 nit)
- `docs/plans/orchestration-lifecycle-decomposition-step2/closeout.md`(codex, 2026-05-03, LTO-8 Step 2 closeout final)
- `docs/plans/orchestration-lifecycle-decomposition-step2/review_comments.md`(claude, 2026-05-03, recommend-merge;0 blockers / 2 non-blocking concerns)
- `docs/active_context.md`(claude, 2026-05-03, post-tag state synced;awaiting LTO-13 kickoff;Direction Gate 决定记录)
