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
- active_slice: `implementation complete; awaiting human review / commit`
- active_branch: `feat/lto-13-fastapi-local-web-ui-write-surface`
- status: `lto13_implementation_complete`

## 当前状态说明

当前 git 分支为 `feat/lto-13-fastapi-local-web-ui-write-surface`。进入 LTO-13 实现前,HEAD 为:

- `5b18a7f docs(plan): local first write API`
- `3d280ca docs(state): update roadmap`
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
- **[Claude]** Plan-gate 后追加第 6 个 concern(post-impl 发现):§Design Decisions "不引入 Pydantic" 把 `api.py` 顶层 import 硬约束与 schema 工具选型捆绑;Pydantic 随 FastAPI dev extras 自动装,禁用它实际只换来每条路由手写 `from_json` / coercion / 400-mapping。建议拆成两条独立约束:`api.py` 顶层 import 不依赖 FastAPI/Pydantic + 请求体走 Pydantic 模型放在 lazy-imported `http_models.py`,从而拿回 422 字段级错误与 OpenAPI schema。详见 `plan_audit.md` Slice M1 末尾。
- **[Claude]** Round 2 post-impl deep re-read,plan_audit 追加 6 项发现(4 concerns + 2 nits):
  - R2-1 [critical concern] `run`/`retry`/`resume`/`rerun` 路由是分钟级阻塞,plan §Sync vs async 没分析后果(threadpool 占用 + 浏览器无进度反馈);需 plan 明示 fire-and-poll 或 accept-long-requests 二选一。
  - R2-2 [concern] 4 条 run-style 路由的语义差异未在 backend 暴露,UI 被迫在 JS 里编 state machine —— 违反 §Boundary Rules;建议 read model 增加 `retry_eligible` / `resume_eligible` / `rerun_eligible` 布尔字段。
  - R2-3 [concern] response shape 仅对 `POST /api/tasks` 一条路由 specced,其余 9 条路由契约空白;建议固定统一 envelope 或为每行加 response keys 列。
  - R2-4 [concern] `promote_stage_candidate_command` 的 `force=True` 绕过 preflight,plan 既没规定 wire format 也没规定 UX —— 建议本期不暴露(保留 CLI 逃生口)。
  - R2-5 [nit] `swl serve --host 0.0.0.0` 无 guard,LAN 暴露全部写面;建议加 loopback-only enforcement。
  - R2-6 [nit] `TaskAcknowledgeCommandResult` 没有 `blocked_kind` 字段,与 `TaskRecoveryCommandResult` 不对称,统一 error-mapping helper 会漏 acknowledge 的 409。
- **[Human]** Plan Gate 通过并切至 `feat/lto-13-fastapi-local-web-ui-write-surface`。
- **[Codex]** 完成 LTO-13 实现:
  - 新增 `surface_tools/web/schemas.py` 作为 FastAPI/Pydantic request schema,仅在 `create_fastapi_app()` 内部导入。
  - `surface_tools/web/http_models.py` 收敛为 response/path helper,不承担 body coercion。
  - `web/api.py` 新增 task lifecycle、staged knowledge promote/reject、proposal review/apply `POST` routes,全部通过 `application.commands.*`。
  - `index.html` 新增最小 operator action controls,写入后刷新后端 read model。
  - `tests/integration/http/test_web_write_routes.py` 覆盖 task write、knowledge write、proposal relative path bridge 和 path rejection。
  - `test_ui_backend_only_calls_governance_functions` 增加 `apply_proposal` / `create_task` / `run_task` 禁止项。
  - `pyproject.toml` dev optional dependency 增加 FastAPI。
- **[Codex]** 已处理 plan_audit 第 6 个 concern(Pydantic / DTO 决策拆分):修订 plan §Design Decisions 与实现,保留 `api.py` 顶层 import 不依赖 FastAPI/Pydantic 的硬约束;请求体验证改为 `surface_tools/web/schemas.py` 内的 scoped Pydantic models;沿用 FastAPI 默认 `422` + 字段级 detail,`api.py` 只映射 400/404/409 等 Swallow 语义错误。
- **[Codex]** 验证通过:`tests/integration/http/test_web_write_routes.py` 7 passed; Web/API/Invariant/Application boundary focused gates 48 passed; `compileall -q src/swallow`; `git diff --check`; full pytest `741 passed, 8 deselected`。

进行中:

- 无。

待执行:

- **[Codex]** 处理 plan_audit Round 2 的 6 项发现(plan 文本 + 实现两侧):
  - 必须先做的 plan 修订 5 项:R2-1 长请求决策、R2-2 eligibility flags 暴露、R2-3 response envelope、R2-4 `force` 立场、R2-5 host guard。
  - 实现 follow-up:对 `TaskAcknowledgeCommandResult` 加 `blocked_kind`(R2-6);`server.py` 加 loopback enforcement(R2-5);依据 R2-1 选择补对应测试形态。
- **[Human]** Review 当前实现 diff(含 Round 2 修订后的版本),决定是否提交实现 milestone。
- **[Claude]** 如需要,对实现进行 PR/review gate。

当前阻塞项:

- 无 blocker。实现与验证已完成,等待 human review / commit。

## Tag 状态

- 最新已执行 tag: **`v1.6.0`**(2026-05-03)
- tag target: `0e6215a docs(release): sync v1.6.0 release docs`
- 标记意义:**cluster C closure**(LTO-7 + LTO-8 Step 1+Step 2 + LTO-9 Step 1+Step 2 + LTO-10 全部完成)
- 下一 tag 评估:LTO-13 完成后视情况评估 `v1.7.0`(WebUI write surface 是首次 LLM-外可观察能力增量;但也可累积更多产品向 phase 后再 cut)。

## 当前下一步

1. **[Human]** Review LTO-13 implementation diff。
2. **[Human]** 若通过,提交实现 milestone。
3. **[Claude]** 进入 review gate。

```markdown
direction_gate:
- latest_completed_phase: LTO-8 Step 2 — harness decomposition
- merge_commit: ea4a886 Orchestration Lifecycle Decomposition
- release_tag: v1.6.0 at 0e6215a docs(release): sync v1.6.0 release docs
- active_branch: feat/lto-13-fastapi-local-web-ui-write-surface
- active_phase: LTO-13 — FastAPI Local Web UI Write Surface
- active_slice: implementation complete; awaiting human review / commit
- cluster_c_status: fully closed (LTO-7 + LTO-8 Step 1+Step 2 + LTO-9 Step 1+Step 2 + LTO-10)
- structural_changes_this_round: LTO-13 relocated 簇 C → 簇 B (interface boundary nature, not cluster C continuation); cluster C subheading dropped "+ 接续"; v1.6.0 tag decision marked executed
- direction_decided: do LTO-13 directly; LTO-5 / LTO-6 do not block LTO-13 (application/commands is the buffer layer)
- roadmap: docs/roadmap.md current ticket = LTO-13; next choice = Wiki Compiler / LTO-6 / LTO-4 / LTO-5 (per real demand)
- closeout (prior phase): docs/plans/orchestration-lifecycle-decomposition-step2/closeout.md (status final)
- review (prior phase): recommend-merge; 0 blockers; 2 non-blocking concerns (both absorbed)
- new_invariants_landed: helper-side append_event allowlist (12 telemetry kinds + 2 disallowed) registered in INVARIANTS.md §9
- validation: focused HTTP/Web/Application/Invariant gates passed; compileall passed; diff check passed; full pytest passed (741 passed, 8 deselected)
- next_gate: Human implementation review / milestone commit
```

## 当前产出物

- `docs/roadmap.md`(claude/roadmap-updater + claude 主线, 2026-05-03, post-merge LTO-8 Step 2 完成 + cluster C 完全终结 + LTO-13 移回簇 B + §三 切到 LTO-13 + §四 v1.6.0 已执行)
- `docs/plans/lto-13-fastapi-local-web-ui-write-surface/plan.md`(codex, 2026-05-03, LTO-13 phase plan; plan_audit concerns absorbed)
- `docs/plans/lto-13-fastapi-local-web-ui-write-surface/plan_audit.md`(claude/design-auditor + claude post-audit + Round 2, 2026-05-03, has-concerns; 0 blockers / 10 concerns / 3 nits;含 plan-gate 后追加的 Pydantic 决策拆分 + 6 项 Round 2 post-impl 发现)
- `src/swallow/surface_tools/web/api.py` / `http_models.py` / `static/index.html`(codex, 2026-05-03, LTO-13 write surface implementation)
- `tests/integration/http/test_web_write_routes.py` + Web/guard test updates(codex, 2026-05-03, LTO-13 HTTP write coverage)
- `docs/plans/orchestration-lifecycle-decomposition-step2/closeout.md`(codex, 2026-05-03, LTO-8 Step 2 closeout final)
- `docs/plans/orchestration-lifecycle-decomposition-step2/review_comments.md`(claude, 2026-05-03, recommend-merge;0 blockers / 2 non-blocking concerns)
- `docs/active_context.md`(claude, 2026-05-03, post-tag state synced;awaiting LTO-13 kickoff;Direction Gate 决定记录)
