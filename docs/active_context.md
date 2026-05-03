# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `Adapter / Service Boundary Cleanup`
- latest_completed_phase: `D4 Phase A — Adapter Boundary Cleanup (rename surface_tools → adapters)`
- latest_completed_slice: `D4 Phase A merged; LTO-6 direction confirmed (Functional facade + 一次清)`
- active_track: `Architecture / Knowledge Plane`
- active_phase: `LTO-6 — Knowledge Plane Facade Solidification`
- active_slice: `M4 complete; awaiting commit gate`
- active_branch: `feat/lto-6-knowledge-plane-facade-solidification`
- status: `lto6_m4_commit_gate`

## 当前状态说明

当前 git 分支为 `feat/lto-6-knowledge-plane-facade-solidification`。当前 HEAD 为:

- `47e69af docs(state): mark lto-6 m2 m3 commit gate`
- `04102c4 refactor(knowledge): internalize modules and migrate callers`
- `c9697f2 refactor(knowledge): add functional knowledge plane facade`

进入 LTO-13 实现前,HEAD 为:

- `5b18a7f docs(plan): local first write API`
- `3d280ca docs(state): update roadmap`
- `ea4a886 Orchestration Lifecycle Decomposition`(LTO-8 Step 2 merge commit)

`v1.6.0` annotated tag 已 cut(2026-05-03,标记 cluster C closure;target `0e6215a`)。**`v1.7.0` annotated tag 已 cut**(标记 LTO-13 接口边界首次落地;tag target `2156d4a docs(release): sync v1.7.0 release docs`;merge commit `4ea7a9d FastAPI Local Web UI Write Surface`)。

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
- **[Claude]** Round 3 framework-rejection pattern audit(human 提出战略担忧后做的代码层验证):确认 Pydantic-at-adapter 是 hexagonal 标准做法,但 Codex 的实现把 framework 原语**对称地拒绝了**—— 请求侧用 Pydantic,响应/错误/注入侧全部手写。新增 5 concerns + 1 nit:
  - R3-1 [concern] `http_models.py` 8 个手写 response 转换器 + `api.py` 0 个 `response_model=` —— `TaskState` 加字段会被静默漏掉;OpenAPI 响应契约空白;R2-3 的根因。
  - R3-2 [concern] 每条路由复制 `try/except` 4 行错误 ladder × 11 处,`@app.exception_handler` 完全没用;R2-6 的根因。
  - R3-3 [concern] `WebRequestError` 完全是 `HTTPException` 的复刻,只为绕开自己定的 lazy-import 规则。
  - R3-4 [concern] `_status_for_value_error` 用 `message.startswith(...)` 字符串匹配决定 HTTP status —— upstream 改文案就静默 404→400。
  - R3-5 [nit] `globals().update({CreateTaskRequest: ..., ...})` 给测试桥接 lazy-imported 模型 —— 测试有顺序依赖,IDE 无法静态解析,信号是"在和自己定的规则打架"。
  - R3-6 [concern] `base_dir` 走闭包捕获,`Depends` 完全没用;后续 phase 要加 audit actor / request ID / artifact-ID 解析时,闭包模式扩不开,部分迁移到 `Depends` 几乎是必然的;现在做更便宜。
  - 元规则建议:plan §Design Decisions 新增 **Framework-Default Principle** —— FastAPI/Pydantic/uvicorn 提供的任何能力默认使用框架原语,自写需书面理由。这条规则若早立,R3 的 6 项发现都不会出现。
- **[Human]** Plan Gate 通过并切至 `feat/lto-13-fastapi-local-web-ui-write-surface`。
- **[Codex]** 完成 LTO-13 实现:
  - 新增 `adapters/http/schemas.py` 作为 FastAPI/Pydantic request schema,仅在 `create_fastapi_app()` 内部导入。
  - `adapters/http/http_models.py` 收敛为 response/path helper,不承担 body coercion。
  - `web/api.py` 新增 task lifecycle、staged knowledge promote/reject、proposal review/apply `POST` routes,全部通过 `application.commands.*`。
  - `index.html` 新增最小 operator action controls,写入后刷新后端 read model。
  - `tests/integration/http/test_web_write_routes.py` 覆盖 task write、knowledge write、proposal relative path bridge 和 path rejection。
  - `test_ui_backend_only_calls_governance_functions` 增加 `apply_proposal` / `create_task` / `run_task` 禁止项。
  - `pyproject.toml` dev optional dependency 增加 FastAPI。
- **[Codex]** 已处理 plan_audit 第 6 个 concern(Pydantic / DTO 决策拆分):修订 plan §Design Decisions 与实现,保留 `api.py` 顶层 import 不依赖 FastAPI/Pydantic 的硬约束;请求体验证改为 `adapters/http/schemas.py` 内的 scoped Pydantic models;沿用 FastAPI 默认 `422` + 字段级 detail,`api.py` 只映射 400/404/409 等 Swallow 语义错误。
- **[Codex]** 验证通过:`tests/integration/http/test_web_write_routes.py` 7 passed; Web/API/Invariant/Application boundary focused gates 48 passed; `compileall -q src/swallow`; `git diff --check`; full pytest `741 passed, 8 deselected`。
- **[Codex]** 已吸收 plan_audit Round 2 + Round 3 新增问题到 `plan.md`:新增 Framework-Default Principle;明确 long-running routes 采用 accept-long-request contract;要求 backend action eligibility;固定统一 success envelope + Pydantic response models;禁止 Web promote `force`;要求 loopback-only serve guard;要求 `Depends` / centralized exception handlers / typed error mapping,并把自写 response converter、`WebRequestError` mirror、message-string status classifier、`globals().update` bridge 列为需清理项。
- **[Codex]** 已完成 Round 2 / Round 3 实现 follow-up:
  - `adapters/http/schemas.py` 同时持有 request + response Pydantic models;所有新写路由声明 `response_model=` 并返回统一 `{"ok": true, "data": ...}` envelope。
  - `adapters/http/api.py` 使用 FastAPI `Depends` 读取 `base_dir`,用集中 `@app.exception_handler` 映射 `FileNotFoundError` / `UnknownStagedCandidateError` / `StagePromotePreflightError` / `TaskActionBlockedError` / `ValueError`;删除 `globals().update`,删除 `_status_for_value_error` message-prefix mapping。
  - 删除 `adapters/http/http_models.py`;新增 `dependencies.py` / `exceptions.py` 承接 adapter dependency 与 typed blocked action。
  - `application/queries/control_center.py` 为 task read payload 增加 backend-derived `action_eligibility`。
  - Web staged promote schema 移除 `force`;server 增加 loopback-only host guard;static UI 使用 eligibility 控制 task action buttons 并为 long-running action 显示 pending state。
  - 新增/更新 HTTP、Web API、server safety tests。
- **[Codex]** Round 2 / Round 3 follow-up 验证通过:HTTP write tests 9 passed; Web/server tests 12 passed; invariant/application boundary 38 passed; control_center query unit 1 passed; CLI tests 242 passed; `compileall -q src/swallow`; `git diff --check`; full pytest `745 passed, 8 deselected`。
- **[Human]** 已提交实现 milestone:`d4c25ac feat(web): harden local write API surface`。
- **[Codex]** 补齐 PR / closeout 材料:
  - `docs/plans/lto-13-fastapi-local-web-ui-write-surface/closeout.md`(implementation closeout draft;Claude review 后再 final)
  - `./pr.md`(PR body draft;Review section 等待 `review_comments.md`)
- **[Claude]** 完成 PR review,产出 `docs/plans/lto-13-fastapi-local-web-ui-write-surface/review_comments.md`:**recommend-merge**;0 blockers / 1 concern / 2 nits。逐项核验 14 项 plan_audit findings(R1 5+1 nit + Pydantic + R2 4+2 + R3 5+1)全部吸收,无静默回归。
  - C1 [concern] `adapters/http/schemas.py:12` 直接 import `swallow.knowledge_retrieval.staged_knowledge.StagedCandidate`,违反 Direction 决定中"避免直接 reach `knowledge_retrieval.*`"约束;放大 `ARCHITECTURE_DECISIONS.md §3.1 D1` 偏离;建议 application 层增加 `StagedCandidate` 公共导出,3 行修复。
  - N1 [nit] `api.py:35-36` `_static_dir()` 用 `Path.cwd()` 作为 `resolve_path` 的 base,实际是 dead-arg 因为 `__file__` 已是 absolute;建议简化为 `Path(__file__).resolve().parent / "static"`。
  - N2 [nit] `tests/integration/http/test_web_write_routes.py:53-56` 通过 `executor_name="local"` 跑真实任务到完成,对 local executor success 契约敏感;留待 D2 driven port 落地后切换到 stub。
- **[Codex]** 已处理 review:
  - C1 fixed: `StagedCandidate` 从 `application.commands.knowledge` 公共导出,`adapters/http/schemas.py` 不再直接 import `knowledge_retrieval.*`。
  - N1 fixed: `_static_dir()` 改为 `Path(__file__).parent / "static"`,避免 `Path.cwd()` dead base 且不触发 `Path.resolve()` invariant guard。
  - N2 acknowledged/deferred:保留真实 local executor HTTP integration 覆盖,等 D2 driven ports 后再切到 command-boundary stub。
  - Post-review validation:focused Web/Application/Invariant gate `59 passed`;`compileall -q src/swallow`;`git diff --check`;full pytest `745 passed, 8 deselected`。
  - `closeout.md` 更新为 `status: final`;`./pr.md` Review 段已同步 review 结论与 post-review validation。
- **[Claude]** Roadmap 增量更新(post-LTO-13 + ADR D1-D6 框架):
  - §一 baseline `当前重构状态` 升级到 "簇 C 完全终结 + LTO-13 接口边界首次落地";新增 `架构身份` 行(Hexagonal + 6 项偏离 D1-D6)。
  - §二 簇 B 描述更新:LTO-5 重定义为 **Driven Ports Rollout**(N phases,首推 `TaskStorePort`);LTO-6 重定义为 **Knowledge Plane Facade Solidification**(主动收口,而非 touched-surface 慢推);LTO-13 行标已完成,列出全部 R1-R3 吸收点。
  - §三 近期队列重写:LTO-13(收口中)→ **D5 Adapter Discipline Codification** → **D4 Phase A 重命名 surface_tools/{cli,web} → adapters/{cli,http}** → **D1 Knowledge Plane Facade Solidification(=LTO-6)**。明确 D2/D6/D3 默认 deferred。
  - §四 加 **v1.7.0 Tag 决策**;当前已由 Human 决定打 tag,release docs 已同步。
  - §五 推荐顺序更新到 "...→ LTO-13 → D5 → D4 Phase A → D1/LTO-6 → 后续";新增"LTO-13 后续工程纪律 phase 顺序"小节,把 D5 → D4 Phase A → D1 三步的理由写清。跨阶段排序依据从 6 条扩到 8 条,加了 LTO-13 已落地 / D5/D4/D1 紧随 / D2/D6/D3 deferred 三条。
  - §一 工程纪律行加一句 ARCHITECTURE_DECISIONS.md 待提交、D5 文档化的指引。
  - 已通过 phase-guard scope check 与 format-validator(193 行,远在 300 行上限内)。
- **[Human]** 已将 LTO-13 branch 合并回 `main`;当前 main HEAD = `52fd14c docs(state): update roadmap`。
- **[Human]** 决定基于 LTO-13 能力增量打 `v1.7.0` tag。
- **[Codex]** 已同步 tag-level release docs:
  - `README.md` Release Snapshot 更新为 `v1.7.0 local Web Control Center write surface`。
  - `current_state.md` 更新为 `v1_7_0_release_docs_ready_for_tag`。
  - `docs/active_context.md` 更新为 release docs / tag preparation 状态。
- **[Claude]** D5 Adapter Discipline Codification 已落地(2026-05-03):
  - 产出 `docs/engineering/ADAPTER_DISCIPLINE.md`(~178 行 → revision 后),六条规则(§1 Framework-Default Principle / §2 Adapter Forbidden Zone / §3 模块布局 / §4 Surface-identity / §5 错误映射)+ §6 worked examples 把 LTO-13 audit Round 1-3 + post-merge follow-up 共 16 项 concerns 逐项映射到规则。
  - design-auditor subagent 完成轻量交叉审,verdict = approve-with-fixes;两个 must-fix(TL;DR 14→16 计数、`errors.py` vs `exceptions.py` 命名冲突)+ 两个建议性改进(R2-6 多标签、§4 dated callout)全部已吸收。
  - User 决定 D5 不走完整 plan / plan_audit / review / closeout 流程,直接产出文档(纯文档 phase 风险低,以省流程换实际收益)。
- **[Codex / 主线]** 完成 **D4 Phase A** —— 纯 import-path rename:`surface_tools/cli.py` + `surface_tools/cli_commands/` → `adapters/cli.py` + `adapters/cli_commands/`、`surface_tools/web/` → `adapters/http/`。无逻辑改动。
  - `pyproject.toml` `swl` entry point 改为 `swallow.adapters.cli:main`。
  - Runtime/test callers 已切到 `swallow.adapters.cli` / `swallow.adapters.http`。
  - `tests/test_invariant_guards.py` 和 `tests/unit/application/test_command_boundaries.py` 路径引用已同步到 `src/swallow/adapters/...`。
  - `docs/engineering/ADAPTER_DISCIPLINE.md` worked examples 与 `docs/engineering/ARCHITECTURE_DECISIONS.md` D4 描述已同步新路径。
  - 验证通过:`compileall -q src/swallow`;`git diff --check`;runtime old-path scan clean;focused CLI/Web/Invariant/Application gate `316 passed`;full pytest `745 passed, 8 deselected`。
  - Merged to `main` at `7450953 refactor(adapters): move cli and http driving adapters`(前序 `d67c2ad docs(engineering): adapter discipline + architecture decisions`)。
- **[Claude]** LTO-6 方向决议(2026-05-03,Human + Claude 讨论后定):
  - **facade 形态 = Functional facade**(模块级 6-10 个领域函数,不引入 class + DI);理由 = class 形态会迫使 24 个调用方改函数签名,与 LTO-5 driven port rollout 耦合,过度提前。
  - **执行节奏 = 一次清**;理由 = 24 个 import 都是机械替换,grep+sed 即可;guard test 在 PR 时强制完整性;三轮分批反而引入"双形态共存"混淆期。
  - **24 个绕过点核实**(2026-05-03 grep):application 5、orchestration 7、provider_router 2、surface_tools 4、adapters 2、truth_governance 3,加测试若干。比 ADR §3.1 当时估算的"~10 处"高 2x。
  - **Wiki Compiler 是硬 prerequisite**:LTO-6 必须在 Wiki Compiler(LTO-1)前落地,否则 Wiki Compiler 实施时会大量调用 knowledge layer,扩大 barrel 调用面后再迁移成本翻倍。
  - **v1.8.0 节点 = Wiki Compiler 第一阶段落地后**(类似 LTO-13 → v1.7.0 关系;LTO-6 + 任何 D4 Phase B/C 都是 plumbing,本身用户不可见,不单独 cut)。
- **[Claude]** Roadmap 第三轮更新(post-D4-Phase-A + LTO-6 方向决议)已落地(roadmap.md 172 行):
  - §三 §五 §二 LTO-6 行同步全部新规格(Functional facade + 一次清 + 24 个文件实测数);
  - 移除 §三 D5 / D4 Phase A 的 "已完成 ticket" 留底(按 §六 维护规则归档到 git log);
  - §三 加 v1.8.0 节点说明(Wiki Compiler 第一阶段后 cut);
  - §五 推荐顺序更新到 "...→ D5 + D4 Phase A(done)→ LTO-6 → Wiki Compiler(v1.8.0)→ 后续"。
- **[Codex]** 已吸收 LTO-6 `plan_audit.md` 7 个 concerns + 2 个 nits 到 `plan.md`:
  - 拆掉 `build_knowledge_projection` / `serve_knowledge_context` / `load_task_knowledge` 类 omnibus 方案,改为显式领域函数;不再硬卡 raw export count,但禁止 selector/mode flag。
  - 将 M2 internal rename 与 M3 caller migration 明确为同一原子实现 gate,避免中间 commit/compileall 断裂。
  - 明确 `ingestion/__init__.py` 不再 re-export pipeline,`run_knowledge_ingestion_pipeline` 进入 facade。
  - 补齐未分类 imports 的迁移矩阵,包括 `artifact_writer.py`、`harness.py`、`adapters/cli.py`、`truth_governance/sqlite_store.py`、`surface_tools/librarian_executor.py` 等。
  - M4 guard scope 扩为 production source 默认只能经 `knowledge_plane`,并要求同步 `_internal_knowledge_store.py` invariant allowlist。
- **[Codex]** 完成 M1 facade contract and characterization:
  - `knowledge_plane.py` 从 import-only barrel 改为显式 functional facade wrapper,删除 broad legacy `__all__`。
  - 新增 `tests/test_knowledge_plane_facade.py`,覆盖 staged lifecycle、task knowledge view、ingestion、relations/suggestions、projection/review/policy/retrieval/prompt 等 facade 入口。
  - 修正 canonical audit facade 为 lazy import,避免 `truth_governance.store` ↔ `knowledge_plane` 初始化循环。
  - M1 验证通过:`tests/test_knowledge_plane_facade.py` 6 passed;M1 focused gate 31 passed;`compileall -q src/swallow`;`git diff --check`。
- **[Codex]** 完成 M2+M3 atomic internalization and caller migration:
  - 六个 lifecycle modules 已 rename 为 `_internal_*`,旧 public module files 不保留 compatibility stubs。
  - application / adapters / orchestration / provider_router / residual `surface_tools` / truth_governance runtime callers 已迁移到 `knowledge_plane` facade;`raw_material.py` 作为 explicit storage-boundary exception 保留。
  - `knowledge_retrieval/ingestion/__init__.py` 不再 re-export pipeline behavior,只保留 parser/filter public exports。
  - 行为测试改走 facade imports;`tests/test_invariant_guards.py` 同步 `_internal_knowledge_store.py` 与 `_internal_ingestion_pipeline.py` allowlist。
  - M2+M3 验证通过:`compileall -q src/swallow`;计划 focused gate `303 passed`;facade/knowledge/invariant gate `58 passed`;application boundary `11 passed`;provider_router focused gate `40 passed`;full pytest `751 passed, 8 deselected`;旧六模块 import scan clean;外层 `_internal_*` import scan clean;`git diff --check`。
- **[Codex]** 完成 M4 guard and documentation sync:
  - `tests/test_invariant_guards.py` 新增 Knowledge Plane public-boundary import guard,扫描 production source 并阻止外层代码直接 import `_internal_*`、旧六 public module、facade-covered behavior modules 或任意非 `knowledge_plane` Knowledge Retrieval 子模块。
  - 守卫保留唯一 production exception:`surface_tools/librarian_executor.py` 可直接 import `raw_material.py` 作为 storage-boundary dependency。
  - 新增 synthetic fixture tests,证明守卫会拒绝 `_internal_knowledge_store` 与 `retrieval` 直接 import,并允许 `knowledge_plane` 与 raw-material exception。
  - M4 验证通过:`tests/test_invariant_guards.py` 31 passed;`git diff --check`。

进行中:

- 无。

待执行:

- **[Human]** 审阅并提交 M4 milestone。
- **[Codex]** Human 提交 M4 后继续 M5 full validation and closeout prep。
- **[Claude]** PR review;**[Human]** merge gate。

当前阻塞项:

- 无 blocker。M4 已完成并停在 commit gate;等待 Human 审阅/提交。

## Tag 状态

- 最新已执行 tag: **`v1.7.0`**(2026-05-03 同期 cut)
- tag target: `2156d4a docs(release): sync v1.7.0 release docs`
- 标记意义:**LTO-13 FastAPI Local Web UI Write Surface 首次落地**(本地 Web Control Center write surface;LLM-外可观察能力增量)
- 上一 tag: `v1.6.0` at `0e6215a`(标记 cluster C closure)
- 下一 tag 评估:无明确预期;留给后续 phase(D5 / D4 Phase A / D1 是工程纪律收口型,未必单独 cut tag;Wiki Compiler 等产品向 phase 触发再评估)

## 当前下一步

1. **[Human]** 审阅并提交 M4 milestone。
2. **[Codex]** Human 提交 M4 后继续 M5 full validation and closeout prep。

```markdown
direction_gate:
- latest_completed_phase: D4 Phase A — Adapter Boundary Cleanup
- merge_commit: 4ea7a9d FastAPI Local Web UI Write Surface
- latest_release_tag: v1.7.0 at 2156d4a docs(release): sync v1.7.0 release docs
- active_branch: feat/lto-6-knowledge-plane-facade-solidification
- active_phase: LTO-6 — Knowledge Plane Facade Solidification
- active_slice: M4 complete; awaiting commit gate
- cluster_c_status: fully closed (LTO-7 + LTO-8 Step 1+Step 2 + LTO-9 Step 1+Step 2 + LTO-10)
- structural_changes_this_round: LTO-13 relocated 簇 C → 簇 B (interface boundary nature, not cluster C continuation); cluster C subheading dropped "+ 接续"; v1.6.0 tag decision marked executed
- direction_decided: do LTO-13 directly; LTO-5 / LTO-6 do not block LTO-13 (application/commands is the buffer layer)
- roadmap: docs/roadmap.md current ticket = LTO-6 Knowledge Plane Facade Solidification; next startup = Wiki Compiler 第一阶段
- closeout (prior phase): docs/plans/orchestration-lifecycle-decomposition-step2/closeout.md (status final)
- review (prior phase): recommend-merge; 0 blockers; 2 non-blocking concerns (both absorbed)
- new_invariants_landed: helper-side append_event allowlist (12 telemetry kinds + 2 disallowed) registered in INVARIANTS.md §9
- validation: focused HTTP/Web/Application/Invariant/CLI gates passed; post-review focused Web/Application/Invariant gate passed (59 passed); compileall passed; diff check passed; full pytest passed (745 passed, 8 deselected)
- implementation_commit: d4c25ac feat(web): harden local write API surface
- pr_materials: docs/plans/lto-13-fastapi-local-web-ui-write-surface/closeout.md + ./pr.md + review_comments.md
- review_outcome: recommend-merge; 14/14 audit findings absorbed; C1 and N1 fixed; N2 deferred to D2 driven ports
- d4_validation: compileall passed; diff check passed; runtime old-path scan clean; focused CLI/Web/Invariant/Application gate 316 passed; full pytest 745 passed, 8 deselected
- lto6_plan: docs/plans/lto-6-knowledge-plane-facade-solidification/plan.md (status review; plan_audit concerns absorbed)
- lto6_plan_audit: docs/plans/lto-6-knowledge-plane-facade-solidification/plan_audit.md (has-concerns; 0 blockers / 7 concerns / 2 nits)
- lto6_m1_validation: knowledge_plane_facade 6 passed; M1 focused gate 31 passed; compileall passed; diff check passed
- lto6_m2_m3_validation: compileall passed; focused gate 303 passed; facade/knowledge/invariant gate 58 passed; application boundary 11 passed; provider_router focused 40 passed; full pytest 751 passed, 8 deselected; old-module/import-boundary scans clean; diff check passed
- lto6_m4_validation: invariant guard 31 passed; diff check passed
- next_gate: M4 commit gate (Human review/commit)
```

## 当前产出物

- `docs/plans/lto-6-knowledge-plane-facade-solidification/plan_audit.md`(claude/design-auditor, 2026-05-03, has-concerns;0 blockers / 7 concerns / 2 nits;重点:`build_knowledge_projection` god-function risk、`serve_knowledge_context` Callable injection、M2+M3 compileall gap、unclassified imports 26 处、M4 guard insufficiency、invariant guard allowlist staleness)
- `docs/plans/lto-6-knowledge-plane-facade-solidification/plan.md`(codex, 2026-05-03, LTO-6 phase plan;Functional facade + one-shot migration + `_internal_*` module internalization + guard/test strategy;plan_audit 7 concerns + 2 nits absorbed)
- `src/swallow/knowledge_retrieval/knowledge_plane.py`(codex, 2026-05-03, M1 functional facade wrapper implementation)
- `tests/test_knowledge_plane_facade.py`(codex, 2026-05-03, M1 facade characterization coverage)
- `src/swallow/knowledge_retrieval/_internal_canonical_registry.py` / `_internal_staged_knowledge.py` / `_internal_knowledge_store.py` / `_internal_knowledge_relations.py` / `_internal_knowledge_suggestions.py` / `_internal_ingestion_pipeline.py`(codex, 2026-05-03, M2 internal lifecycle modules)
- `src/swallow/application/` / `adapters/` / `orchestration/` / `provider_router/` / `surface_tools/` / `truth_governance/` touched imports(codex, 2026-05-03, M3 caller migration to `knowledge_plane`)
- `tests/test_*` + `tests/integration/*` + `tests/unit/*` touched imports/guards(codex, 2026-05-03, M3 facade behavior tests and moved-module guard sync)
- `tests/test_invariant_guards.py`(codex, 2026-05-03, M4 Knowledge Plane public-boundary import guard)
- `docs/roadmap.md`(claude, 2026-05-03, post-LTO-13 增量更新:LTO-13 标完成、LTO-5 重定义为 Driven Ports Rollout、LTO-6 重定义为 Knowledge Plane Facade Solidification 主动化、新增 D5/D4 Phase A independent phase tickets、§五 顺序更新)
- `docs/engineering/ARCHITECTURE_DECISIONS.md`(claude, 2026-05-03, 草稿;架构身份 = Hexagonal + 当前模式清单 + 6 项已识别偏离 D1-D6;待与 LTO-13 closeout 一起提交)
- `docs/plans/lto-13-fastapi-local-web-ui-write-surface/plan.md`(codex, 2026-05-03, LTO-13 phase plan; Round 1 / Pydantic follow-up / Round 2 / Round 3 audit concerns absorbed)
- `docs/plans/lto-13-fastapi-local-web-ui-write-surface/plan_audit.md`(claude/design-auditor + claude post-audit + Round 2 + Round 3, 2026-05-03, has-concerns; 0 blockers / 14 concerns / 4 nits;含 plan-gate 后追加的 Pydantic 决策拆分 + 6 项 Round 2 post-impl 发现 + 6 项 Round 3 framework-rejection 发现 + Framework-Default Principle 元规则)
- `docs/plans/lto-13-fastapi-local-web-ui-write-surface/closeout.md`(codex, 2026-05-03, final closeout;review concern addressed)
- `docs/plans/lto-13-fastapi-local-web-ui-write-surface/review_comments.md`(claude, 2026-05-03, **recommend-merge**;14/14 plan_audit findings absorbed;0 blockers / 1 concern (C1 schemas.py knowledge_retrieval 越界) / 2 nits)
- `./pr.md`(codex, 2026-05-03, PR body;review outcome synced)
- `src/swallow/adapters/http/api.py` / `schemas.py` / `dependencies.py` / `exceptions.py` / `server.py` / `static/index.html`(codex, 2026-05-03, LTO-13 write surface implementation;milestone commit `d4c25ac`)
- `tests/integration/http/test_web_write_routes.py` + Web/guard test updates(codex, 2026-05-03, LTO-13 HTTP write coverage)
- `docs/plans/orchestration-lifecycle-decomposition-step2/closeout.md`(codex, 2026-05-03, LTO-8 Step 2 closeout final)
- `docs/plans/orchestration-lifecycle-decomposition-step2/review_comments.md`(claude, 2026-05-03, recommend-merge;0 blockers / 2 non-blocking concerns)
- `src/swallow/adapters/cli.py` / `adapters/cli_commands/` / `adapters/http/`(codex, 2026-05-03, D4 Phase A adapter path rename)
- `pyproject.toml` + tests(codex, 2026-05-03, D4 Phase A caller / guard path sync)
