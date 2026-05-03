# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `Architecture / Knowledge Plane`
- latest_completed_phase: `LTO-6 — Knowledge Plane Facade Solidification`
- latest_completed_slice: `LTO-6 merged at 883e2a9; Wiki Compiler design positioning decided`
- active_track: `Knowledge Authoring`
- active_phase: `LTO-1 — Wiki Compiler 第一阶段`
- active_slice: `M4 — Web UI Knowledge panel complete; ready for Human milestone review`
- active_branch: `feat/lto-1-wiki-compiler-first-stage`
- status: `lto1_m4_ready_for_human_commit`

## 当前状态说明

当前 git 分支为 `feat/lto-1-wiki-compiler-first-stage`。当前 HEAD 为:

- `8c7faba docs(state): update active_context for M2/M3 complete`
- `8e03ddd feat(web): add knowledge browse read routes`
- `178f9ee feat(wiki): add compiler draft and refine commands`
- `7eb2ef8 docs(plan): add lto-1 wiki compiler plan`
- `b73ebf8 docs(state): update roadmap`
- `1a3d61b docs(design): add wiki compiler specialist`
- `883e2a9 Knowledge Plane Facade Solidification`

`v1.6.0` annotated tag 已 cut(2026-05-03,标记 cluster C closure;target `0e6215a`)。`v1.7.0` annotated tag 已 cut(标记 LTO-13 接口边界首次落地;tag target `2156d4a docs(release): sync v1.7.0 release docs`;merge commit `4ea7a9d FastAPI Local Web UI Write Surface`)。

**当前真实入口**:LTO-6 已 merge 到 `main`;Wiki Compiler 设计定位、4 模式语义与 Web 知识呈现视图分级已通过设计文档先行落到 `main`;`docs/roadmap.md` 已更新为 LTO-1 当前 ticket。`docs/plans/lto-1-wiki-compiler-first-stage/plan_audit.md` 已产出(0 blockers / 5 concerns / 2 nits),Codex 已吸收到 `plan.md`;Human 已完成 Plan Gate、planning docs commit 与 feature branch switch。M1 — Wiki Compiler 起草核心已提交为 `178f9ee feat(wiki): add compiler draft and refine commands`;M2/M3 — read-only Knowledge browse routes + detail/relations 已提交为 `8e03ddd feat(web): add knowledge browse read routes` + `8c7faba docs(state): update active_context for M2/M3 complete`;M4 — Web UI Knowledge panel 已实现并通过 full validation,等待 Human milestone review / commit。

**簇 C 状态**:LTO-7 / LTO-8(Step 1+Step 2)/ LTO-9(Step 1+Step 2)/ LTO-10 全部完成。LTO-8 Step 2 完整事实见 `docs/plans/orchestration-lifecycle-decomposition-step2/closeout.md`。

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
5. `docs/design/EXECUTOR_REGISTRY.md`
6. `docs/design/SELF_EVOLUTION.md`
7. `docs/design/KNOWLEDGE.md`
8. `docs/engineering/ADAPTER_DISCIPLINE.md`
9. `docs/engineering/CODE_ORGANIZATION.md`
10. `docs/engineering/TEST_ARCHITECTURE.md`
11. `docs/engineering/ARCHITECTURE_DECISIONS.md`
12. `docs/plans/lto-1-wiki-compiler-first-stage/plan.md`
13. `docs/plans/lto-1-wiki-compiler-first-stage/plan_audit.md`
14. `docs/plans/lto-6-knowledge-plane-facade-solidification/closeout.md`
15. `docs/plans/lto-6-knowledge-plane-facade-solidification/review_comments.md`

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
- **[Codex]** 完成 M5 full validation and closeout prep:
  - M5 验证通过:`compileall -q src/swallow`;full pytest `755 passed, 8 deselected`;`git diff --check`。
  - 新增并最终同步 `docs/plans/lto-6-knowledge-plane-facade-solidification/closeout.md`,记录 outcome、plan audit absorption、validation、review disposition 和 deferred follow-ups。
  - 更新 ignored `./pr.md` 为 LTO-6 PR body,供 Human 同步 PR 描述时使用。
- **[Claude]** 完成 PR review,产出 `docs/plans/lto-6-knowledge-plane-facade-solidification/review_comments.md`:**recommend-merge**;0 blockers / 1 concern / 2 nits。逐项核验 7 项 plan_audit concerns + 2 项 nits 全部吸收,无静默回归。INVARIANTS §0 canonical write authority 经核实保留(`apply_proposal` 不在 facade 暴露,`application/commands/knowledge.py` 仍直接 import `truth_governance.governance`)。
  - C1 [concern] facade `render_*` / `build_*` 配对别名 ~14 处,M3 caller 迁移 commit 已更动每个 import line,正是删除冗余别名的最便宜窗口;建议 option (a) 单 follow-up commit 删冗余别名,~50 行 diff。
  - N1 [nit] `audit_canonical_registry` / `render_canonical_audit_report` 是 facade 中唯一两个用 lazy import 的函数(`knowledge_plane.py:510-519`),likely 因 `canonical_audit.py` 反向 import facade 形成循环;建议加 1 行注释或验证可消除。
  - N2 [nit] `knowledge_plane.py` 缺 `__all__`,wildcard import 隐含面比显式 surface 大;建议加 `__all__` 列 ~70 个 public functions / value classes(可后续 polish)。
- **[Human]** LTO-6 已 merge to `main` at `883e2a9 Knowledge Plane Facade Solidification`(含 closeout final `41f1ac9`)。
- **[Claude]** Wiki Compiler 定位决议(2026-05-04,Human + Claude 讨论后定):
  - **选项 A 独立 specialist**(不是 Librarian / Ingestion 子能力,也不是 application command 形态)。
  - 五元组 = `(specialist / propose_only / {task_artifacts, event_log, staged_knowledge} / specialist_internal / hybrid)`;`default_retrieval_sources = ["knowledge", "artifacts", "raw_material"]`。
  - 与 Librarian 是**上下游关系**(Wiki Compiler 起草 → Librarian 守门 → Operator review → `apply_proposal`),不是合并关系。让一个 agent 同时做创作 + 守门会失去独立 verdict。
  - 与 Ingestion 是**平行不重叠**:Ingestion 把单源外部会话结构化;Wiki Compiler 从多源 raw_material 综合产出 wiki/canonical 草稿,需要 retrieval 召回查重。
- **[Claude]** LTO-1 phase plan 启动前的设计文档先行已完成:
  - `docs/design/EXECUTOR_REGISTRY.md` §1.2 加 Wiki Compiler 第 5 个 specialist 条目(完整五元组 + 与 Librarian / Ingestion 关系说明 + retrieval sources 理由)。
  - `docs/design/EXECUTOR_REGISTRY.md` §2 默认绑定表加"知识起草主线 / Wiki Compiler"行。
  - `docs/design/SELF_EVOLUTION.md` §2 mermaid 图加 Wiki Compiler 上游环节(`raw_material → Wiki Compiler → staged`),与 Librarian 在同一 subgraph 内并列;主线表拆为"起草侧 / 守门侧"两行。
  - `docs/design/SELF_EVOLUTION.md` §4.2 沉淀工作流文字拆为 [A] 起草侧 / [B] 守门侧 / [共同收口] 三段,显式说明 Wiki Compiler 与 Librarian 的上下游关系。
  - 没改 INVARIANTS / KNOWLEDGE / ARCHITECTURE_DECISIONS / ADAPTER_DISCIPLINE —— 这些文档对 Wiki Compiler 没有需要修订的约束;新 specialist 完美套入既有 propose_only / 写 staged 边界。

- **[Claude]** Wiki Compiler 4 模式语义决议(2026-05-04):
  - **Mode 1 — `draft`**:从 raw_material 起草新 wiki entry,无对应旧对象;`relation_metadata = (无 / derived_from)`。
  - **Mode 2 — `refine --mode supersede`**:旧 wiki 整体被取代;`relation_metadata = supersedes(<wiki_id>)`;旧 wiki 状态置 superseded(append-only,不删除)。
  - **Mode 3 — `refine --mode refines`**:旧 wiki 仍 active,新 wiki 独立入库;`relation_metadata = refines(<wiki_id>)`;retrieval 通过 relation expansion 一并返回。
  - **Mode 4 — `refresh-evidence`**:**不走 LLM**,仅刷 evidence 锚点(`content_hash` + `span` + `parser_version`);**不**经 `apply_proposal`(非 canonical mutation),但必须更新 `parser_version`(parser 升级时)以防 `KNOWLEDGE.md §A "Unversioned Evidence Rebuild"` 反模式。
  - **Conflict 决策点**:Wiki Compiler 起草若召回到矛盾旧 wiki,标 `conflict_flag = contradicts(<wiki_id>)`;Librarian 守门时验证;Operator review 时人工二选一(supersede 旧 wiki / reject 新草稿 / 触发 audit);**系统永远不自动 supersede**(P7 / P8)。
  - 设计文档已同步:`EXECUTOR_REGISTRY.md` Wiki Compiler 条目加 4 模式表 + Conflict 决策段;`SELF_EVOLUTION.md §4.2` 工作流文字按 4 模式 + Operator 决策点重写。
- **[Claude]** Web Control Center 知识呈现决议(2026-05-04):
  - **视图 1**(task-knowledge)+ **视图 2**(knowledge detail + adjacent relations 邻接表)并入 LTO-1 phase 作为 M2-M4 子目标。
  - **视图 3**(项目级全图谱可视化)deferred —— 当前 wiki 节点量(~10s)在全图谱不友好区间;违反 LTO-13 §M3 "no new frontend package, build step, or asset pipeline";Wiki Compiler 落地前价值未显;留给真实需求触发或 Graph RAG 远期方向(`KNOWLEDGE.md §9`)。
- **[Human]** LTO-1 Plan Gate 通过,planning docs 已提交为 `7eb2ef8 docs(plan): add lto-1 wiki compiler plan`,并切至 `feat/lto-1-wiki-compiler-first-stage`。
- **[Codex]** 完成 **M1 — Wiki Compiler 起草核心**:
  - `StagedCandidate` 增加 `wiki_mode` / `target_object_id` / `source_pack` / `rationale` / `relation_metadata` / `conflict_flag`,旧记录可加载,promote/reject 保留 metadata。
  - 新增 Wiki Compiler specialist + executor registry 绑定 + `application.commands.wiki` + CLI `swl wiki draft/refine/refresh-evidence`。
  - `draft/refine` 走 Provider Router `call_agent_llm`,只写 task artifacts + staged candidate;`refresh-evidence` 不走 LLM,只刷新 evidence anchor。
  - Operator promote 后 application command 消费 `refines` metadata 创建 relation row;raw `derived_from` / `supersedes` staged signal 不写 relation row。
  - 验证通过:focused M1 gates, invariant guards, CLI integration, `compileall`, `git diff --check`,full pytest `762 passed, 8 deselected`。
- **[Human]** 已提交 M1 milestone:`178f9ee feat(wiki): add compiler draft and refine commands`。
- **[Codex]** 完成 **M2/M3 — Knowledge browse routes + detail/relations**:
  - 新增 `application/queries/knowledge.py` read model,支持 wiki/canonical/staged lists、knowledge detail、relations adjacency 分组。
  - HTTP 新增 `GET /api/knowledge/wiki`、`/api/knowledge/canonical`、`/api/knowledge/staged`、`/api/knowledge/{object_id}`、`/api/knowledge/{object_id}/relations`,均走 Pydantic success envelope + `Depends(get_base_dir)` + centralized exception handler。
  - Knowledge Plane facade 补只读 `load_canonical_registry_records` / `iter_knowledge_task_ids`,HTTP adapter 不直接读 SQLite / 文件路径 / knowledge internals。
  - relations view 合并 persisted relations 与 staged/canonical `relation_metadata`,分组覆盖 `supersedes` / `refines` / `contradicts` / `refers_to` / `derived_from` + `legacy`。
  - 验证通过:M2/M3 focused tests `7 passed`;Web/API/Invariant focused gate `50 passed`;facade/relations gate `13 passed`;`compileall`;`git diff --check`;full pytest `769 passed, 8 deselected`。
- **[Human]** 已提交 M2/M3 milestone:`8e03ddd feat(web): add knowledge browse read routes` + `8c7faba docs(state): update active_context for M2/M3 complete`。
- **[Codex]** 完成 **M4 — Web UI Knowledge panel**:
  - `index.html` 新增 Tasks / Knowledge surface segmented control,Knowledge surface 只读展示 wiki/canonical/staged 列表、详情、source pack 与 relations adjacency。
  - JS 只调用 M2/M3 GET routes,通过 backend read model 切换 knowledge kind/status,不引入 Wiki Compiler draft/refine/refresh 触发按钮。
  - `tests/test_web_api.py` 增加 knowledge surface / route string smoke,验证 UI 文本与 route exposure。
  - 验证通过:Web/API focused gate `22 passed`;`compileall`;`git diff --check`;full pytest `769 passed, 8 deselected`。

进行中:

- 无。

待执行:

- **[Human]** 审阅 M4 diff 与验证结果后执行 milestone commit。
- **[Codex]** 处理 LTO-6 review C1 follow-up(可选,~50 行 cleanup):删除 `knowledge_plane.py` 中 ~14 处 `render_*` / `build_*` 配对别名,每对保留一个(`render_*` 用于报告渲染,`build_*` 用于对象构造)。默认不阻塞 LTO-1 plan。
- **[Codex / 主线]** 继续按 **LTO-1 Wiki Compiler 第一阶段** `plan.md` 实现。设计文档(EXECUTOR_REGISTRY 5 specialist + 4 mode + SELF_EVOLUTION §2/§4.2)已先行更新到 main,实现时继续遵循如下锚点:
  - **M4 — Web UI Knowledge panel**:静态 `index.html` 加"Knowledge"标签页,展示 wiki/canonical/staged 列表 + 详情 + 邻接 relations;遵循 `ADAPTER_DISCIPLINE.md` 6 条规则(Pydantic response_model / Depends / 集中 exception handler / 无 state machine in JS / loopback only);本期 Web 只读,不加入 Wiki Compiler draft/refine/refresh 触发按钮。
  - **M5 — Guard / closeout**:`tests/test_invariant_guards.py` 加 Wiki Compiler agent boundary guard(`truth_writes` 不含 canonical,只走 facade)+ Evidence rebuild parser_version guard(`refresh-evidence` 必须更新 parser_version 字段)。
  - 此 phase 落地后 cut **v1.8.0**。

当前阻塞项:

- 无 blocker。M4 已实现,等待 Human milestone review / commit。

## Tag 状态

- 最新已执行 tag: **`v1.7.0`**(2026-05-03 同期 cut)
- tag target: `2156d4a docs(release): sync v1.7.0 release docs`
- 标记意义:**LTO-13 FastAPI Local Web UI Write Surface 首次落地**(本地 Web Control Center write surface;LLM-外可观察能力增量)
- 上一 tag: `v1.6.0` at `0e6215a`(标记 cluster C closure)
- 下一 tag 评估:roadmap 当前预期为 LTO-1 Wiki Compiler 第一阶段落地后评估 / cut **v1.8.0**。

## 当前下一步

1. **[Human]** 审阅 M4 diff 与验证结果后执行 milestone commit。
2. **[Codex]** Human 确认 M4 commit 后进入 M5 guards / closeout。

```markdown
direction_gate:
- latest_completed_phase: LTO-6 — Knowledge Plane Facade Solidification
- latest_release_tag: v1.7.0 at 2156d4a docs(release): sync v1.7.0 release docs
- active_branch: feat/lto-1-wiki-compiler-first-stage
- active_phase: LTO-1 — Wiki Compiler 第一阶段
- active_slice: M4 — Web UI Knowledge panel complete; ready for Human milestone review
- roadmap: docs/roadmap.md current ticket = LTO-1 Wiki Compiler 第一阶段; v1.8.0 after first-stage landing
- lto1_design_docs: docs/design/EXECUTOR_REGISTRY.md + docs/design/SELF_EVOLUTION.md updated with Wiki Compiler specialist + 4 modes
- lto1_plan: docs/plans/lto-1-wiki-compiler-first-stage/plan.md (review; Codex; plan_audit concerns absorbed)
- lto1_plan_audit: docs/plans/lto-1-wiki-compiler-first-stage/plan_audit.md (Claude/design-auditor; has-concerns; 0 blockers / 5 concerns / 2 nits)
- next_gate: Human M4 milestone review / commit -> M5 guards / closeout
```

## 当前产出物

- `src/swallow/adapters/http/static/index.html`(codex, 2026-05-04, M4 Knowledge surface;wiki/canonical/staged lists + detail + source pack + relations adjacency;read-only)
- `tests/test_web_api.py`(codex, 2026-05-04, M4 static smoke for Knowledge panel IDs and GET route strings)
- `src/swallow/application/queries/knowledge.py`(codex, 2026-05-04, M2/M3 read model;wiki/canonical/staged list + detail + persisted/metadata relations adjacency)
- `src/swallow/adapters/http/api.py` + `src/swallow/adapters/http/schemas.py`(codex, 2026-05-04, M2/M3 read-only Knowledge Browse HTTP routes + Pydantic response envelopes)
- `src/swallow/knowledge_retrieval/knowledge_plane.py` + `_internal_canonical_registry.py` + `_internal_knowledge_store.py`(codex, 2026-05-04, M2/M3 read-only facade helpers for canonical registry records and knowledge task ids)
- `tests/integration/http/test_knowledge_browse_routes.py` + `tests/unit/application/test_knowledge_queries.py` + `tests/test_web_api.py`(codex, 2026-05-04, M2/M3 HTTP/application coverage and route response_model exposure checks)
- `src/swallow/surface_tools/wiki_compiler.py`(codex, 2026-05-04, M1 Wiki Compiler specialist;Path C via Provider Router;source pack anchors;staged candidate write)
- `src/swallow/application/commands/wiki.py`(codex, 2026-05-04, M1 adapter-facing wiki commands;draft/refine/refresh-evidence)
- `src/swallow/adapters/cli_commands/wiki.py` + `src/swallow/adapters/cli.py`(codex, 2026-05-04, M1 `swl wiki draft/refine/refresh-evidence` CLI)
- `src/swallow/knowledge_retrieval/_internal_staged_knowledge.py` + `knowledge_plane.py`(codex, 2026-05-04, M1 staged metadata extension + raw-material facade exports)
- `src/swallow/application/commands/knowledge.py`(codex, 2026-05-04, M1 promote/refines relation side effect + conflict preflight)
- `tests/integration/cli/test_wiki_commands.py` + `tests/test_staged_knowledge.py` + `tests/test_specialist_agents.py` + `tests/test_executor_protocol.py`(codex, 2026-05-04, M1 focused coverage)
- `docs/plans/lto-1-wiki-compiler-first-stage/plan_audit.md`(claude/design-auditor, 2026-05-04, has-concerns;0 blockers / 5 concerns / 2 nits;重点:M1 StagedCandidate slots 约束、promotion 路径 relation 创建层、derived_from target type、relation enum 跨 milestone 依赖、source_pack schema 未锚定;M2/M3/M4/M5 confirmed ready)
- `docs/plans/lto-1-wiki-compiler-first-stage/plan.md`(codex, 2026-05-04, review LTO-1 Wiki Compiler 第一阶段 plan;已吸收 plan_audit 5 concerns + 2 nits;M1-M5 覆盖 Wiki Compiler CLI/specialist、Knowledge Browse routes、detail+relations、Web panel、boundary/evidence guards)
- `docs/plans/lto-6-knowledge-plane-facade-solidification/plan_audit.md`(claude/design-auditor, 2026-05-03, has-concerns;0 blockers / 7 concerns / 2 nits;重点:`build_knowledge_projection` god-function risk、`serve_knowledge_context` Callable injection、M2+M3 compileall gap、unclassified imports 26 处、M4 guard insufficiency、invariant guard allowlist staleness)
- `docs/plans/lto-6-knowledge-plane-facade-solidification/plan.md`(codex, 2026-05-03, final LTO-6 phase plan;Functional facade + one-shot migration + `_internal_*` module internalization + guard/test strategy;plan_audit 7 concerns + 2 nits absorbed)
- `src/swallow/knowledge_retrieval/knowledge_plane.py`(codex, 2026-05-03, M1 functional facade wrapper implementation)
- `tests/test_knowledge_plane_facade.py`(codex, 2026-05-03, M1 facade characterization coverage)
- `src/swallow/knowledge_retrieval/_internal_canonical_registry.py` / `_internal_staged_knowledge.py` / `_internal_knowledge_store.py` / `_internal_knowledge_relations.py` / `_internal_knowledge_suggestions.py` / `_internal_ingestion_pipeline.py`(codex, 2026-05-03, M2 internal lifecycle modules)
- `src/swallow/application/` / `adapters/` / `orchestration/` / `provider_router/` / `surface_tools/` / `truth_governance/` touched imports(codex, 2026-05-03, M3 caller migration to `knowledge_plane`)
- `tests/test_*` + `tests/integration/*` + `tests/unit/*` touched imports/guards(codex, 2026-05-03, M3 facade behavior tests and moved-module guard sync)
- `tests/test_invariant_guards.py`(codex, 2026-05-03, M4 Knowledge Plane public-boundary import guard)
- `docs/plans/lto-6-knowledge-plane-facade-solidification/closeout.md`(codex, 2026-05-04, final closeout;review recommend-merge, C1/N1/N2 dispositions recorded)
- `docs/plans/lto-6-knowledge-plane-facade-solidification/review_comments.md`(claude, 2026-05-04, **recommend-merge**;7/7 plan_audit concerns + 2/2 nits absorbed;0 blockers / 1 concern(C1 `render_*` / `build_*` 配对别名 ~14 处)/ 2 nits)
- `docs/concerns_backlog.md`(codex, 2026-05-04, LTO-6 C1 facade naming cleanup logged as non-blocking follow-up before Wiki Compiler)
- `./pr.md`(codex, 2026-05-04, ignored PR body draft for LTO-6;review outcome synced)
- `docs/roadmap.md`(claude, 2026-05-03, post-LTO-13 增量更新:LTO-13 标完成、LTO-5 重定义为 Driven Ports Rollout、LTO-6 重定义为 Knowledge Plane Facade Solidification 主动化、新增 D5/D4 Phase A independent phase tickets、§五 顺序更新)
- `docs/engineering/ARCHITECTURE_DECISIONS.md`(claude, 2026-05-03, 草稿;架构身份 = Hexagonal + 当前模式清单 + 6 项已识别偏离 D1-D6;待与 LTO-13 closeout 一起提交)
- `docs/plans/lto-13-fastapi-local-web-ui-write-surface/plan.md`(codex, 2026-05-03, LTO-13 phase plan; Round 1 / Pydantic follow-up / Round 2 / Round 3 audit concerns absorbed)
- `docs/plans/lto-13-fastapi-local-web-ui-write-surface/plan_audit.md`(claude/design-auditor + claude post-audit + Round 2 + Round 3, 2026-05-03, has-concerns; 0 blockers / 14 concerns / 4 nits;含 plan-gate 后追加的 Pydantic 决策拆分 + 6 项 Round 2 post-impl 发现 + 6 项 Round 3 framework-rejection 发现 + Framework-Default Principle 元规则)
- `docs/plans/lto-13-fastapi-local-web-ui-write-surface/closeout.md`(codex, 2026-05-03, final closeout;review concern addressed)
- `docs/plans/lto-13-fastapi-local-web-ui-write-surface/review_comments.md`(claude, 2026-05-03, **recommend-merge**;14/14 plan_audit findings absorbed;0 blockers / 1 concern (C1 schemas.py knowledge_retrieval 越界) / 2 nits)
- `src/swallow/adapters/http/api.py` / `schemas.py` / `dependencies.py` / `exceptions.py` / `server.py` / `static/index.html`(codex, 2026-05-03, LTO-13 write surface implementation;milestone commit `d4c25ac`)
- `tests/integration/http/test_web_write_routes.py` + Web/guard test updates(codex, 2026-05-03, LTO-13 HTTP write coverage)
- `docs/plans/orchestration-lifecycle-decomposition-step2/closeout.md`(codex, 2026-05-03, LTO-8 Step 2 closeout final)
- `docs/plans/orchestration-lifecycle-decomposition-step2/review_comments.md`(claude, 2026-05-03, recommend-merge;0 blockers / 2 non-blocking concerns)
- `src/swallow/adapters/cli.py` / `adapters/cli_commands/` / `adapters/http/`(codex, 2026-05-03, D4 Phase A adapter path rename)
- `pyproject.toml` + tests(codex, 2026-05-03, D4 Phase A caller / guard path sync)
