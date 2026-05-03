---
author: claude
status: living-document
---

> **Document discipline**
> Owner: Human
> Updater: Codex 主线(长期目标、近期 ticket、优先级、风险批注)+ `roadmap-updater` subagent(phase 完成后的事实状态同步)+ Claude 主线(review / tag 相关轻量风险批注)
> Trigger: phase 收口 OR 会话讨论中浮现新方向 OR phase 拆分 OR Human 请求方向建议
> Anti-scope: 不维护已完成 phase 历史(→ git log + `docs/plans/<phase>/closeout.md`);不维护 tag / release docs 状态(→ `docs/concerns_backlog.md`);不存储设计原则(→ `INVARIANTS.md`);不维护 phase 高频状态(→ `docs/active_context.md`)
> 长度上限:300 行;超过说明放进了不该放的东西

# 演进路线图 (Roadmap)

> 最近更新:见 git log。本文件维护**长期优化目标**和**近期可执行 phase ticket**。
> 规则:长期目标可以跨多轮增量推进;phase ticket 是一次可提交切片,完成后从近期队列移走,但它对应的长期目标继续保留状态。

---

## 一、当前实现基线

| 维度 | 当前状态 |
|------|----------|
| **稳定 checkpoint** | `v1.5.0` 已发布;Phase 67 module / hygiene cleanup + Phase 68 `RawMaterialStore` boundary 构成当前 knowledge plane baseline |
| **知识治理** | Raw Material / Knowledge Truth / Retrieval & Serving 三层已成型;Wiki / Canonical 是默认语义入口;`RawMaterialStore` filesystem backend 已落地 |
| **知识捕获** | `swl note` / clipboard / `generic_chat_json` / local file ingestion 已可进入 staged review 管线 |
| **检索基础设施** | Retrieval U-T-Y 已落地:dedicated rerank boundary、retrieval trace、source policy warnings、EvidencePack compatibility view、RawMaterialStore-backed source pointer resolution、summary route boundary |
| **治理边界** | `apply_proposal`、SQLite-primary truth、Path A/B/C、§9 guard suite 均已实现到稳定基线 |
| **Agent 体系** | 4 Specialist + 2 Validator 独立生命周期已落地;具体品牌绑定见 `docs/design/EXECUTOR_REGISTRY.md` |
| **当前重构状态** | **簇 C 完全终结 + LTO-13 接口边界首次落地**:LTO-7/8/9/10 全部完成 + LTO-13 FastAPI Local Web UI Write Surface 实现 milestone 已提交,Claude PR review = recommend-merge。LTO-7 Provider Router facade 化、LTO-8 Step 1+Step 2 orchestrator.py + harness.py 聚焦模块化、LTO-9 Step 1+Step 2 CLI / Meta-Optimizer 拆分 + 广泛命令族迁移 + application/commands 写命令完整化、LTO-10 governance apply handler 模块化、LTO-13 FastAPI 写表面(task lifecycle / staged knowledge / proposal review-apply 路由 + Pydantic request/response envelope + `Depends` + 集中 `@app.exception_handler` + loopback-only serve guard)。LTO-5 重定义为 Repository / Persistence Ports 并默认 defer。v1.6.0 已发布标记 cluster C 完整闭合。下一启动:Adapter Discipline Codification → Adapter Boundary Cleanup Phase A → Knowledge Plane Facade Solidification(=LTO-6 主动化)。 |
| **架构身份** | 项目事实上的架构 = **Hexagonal (Ports & Adapters)**;driving adapters = `surface_tools/{cli,web}/`(LTO-13 后即将重命名为 `adapters/{cli,http}/`);application layer = `application/{commands,queries}/`;domain / control plane = `orchestration/` + `knowledge_retrieval/` + `truth_governance/` + `provider_router/`;driven adapters / infrastructure = `truth_governance/sqlite_store.py` + `provider_router/completion_gateway.py` + `_io_helpers.py` 等。已识别 6 项偏离(D1–D6),修复路径见 §五。 |
| **工程纪律** | 长期编码 / 重构遵循 `docs/engineering/CODE_ORGANIZATION.md`(分层 / facade-first / migration discipline)+ `docs/engineering/GOF_PATTERN_ALIGNMENT.md`(facade / strategy / repository / adapter / value object / state / pipeline 等 pattern 仅作为 responsibility language)+ `docs/engineering/TEST_ARCHITECTURE.md`(分层测试 / TDD harness)+ 即将提交的 `docs/engineering/ARCHITECTURE_DECISIONS.md`(架构身份 = Hexagonal、当前已用模式清单 + 已识别 6 项偏离 D1-D6 的修复路径)。LTO-13 R3 audit 暴露的 framework-rejection 系统性问题将由 D5 Adapter Discipline Codification phase 编纂为独立工程纪律文档(见 §三 / §五)。 |

---

## 二、长期优化目标

这些是跨 phase 的长期目标。一次 phase 只推进其中一个可审查增量,不会让目标本身消失。

12 条 LTO 不是平等并列(编号 LTO-3 已归档不复用),按推进性质分 **4 簇**:

- **簇 A 产品 / 知识能力**(LTO-1, LTO-2):沿现有架构垂直推进的产品级能力。LTO-2 第一阶段已闭环,LTO-1 等地基。
- **簇 B 架构重构已开头 seed + 接口边界**(LTO-4, LTO-5, LTO-6, LTO-13):已被 first branch 开了 seed,后续靠簇 C 各 subtrack phase 自然带动。LTO-13 FastAPI Local Web UI Write Surface 已完成接口边界首次落地。LTO-5 已重定义为 **Driven Ports Rollout**(N phases,首推 `TaskStorePort`),从被动 defer 改为按需主动推进。LTO-6 已重定义为 **Knowledge Plane Facade Solidification**(主动收口,而非 touched-surface 慢推),修复 `knowledge_plane.py` 当前 50 名透传 barrel-file 形态 + 上层(application/commands、truth_governance)8 处直接 reach `knowledge_retrieval.*` 子模块的边界绕过。(LTO-3 已归档,见 §四。)
- **簇 C 子系统解耦四金刚**(LTO-7, LTO-8, LTO-9, LTO-10):**已完全终结**;四条均已完成,各自独立 phase / 分支。每条独立一个 phase / 一条分支,不允许合并到一个 PR。
- **簇 D 远端 / 休眠**(LTO-11, LTO-12):默认不投入,仅由真实需求触发。

下面分簇展开。

### 簇 A:产品 / 知识能力(沿现有架构垂直推进)

| ID | 长期目标 | 当前状态 | 下一类增量 | 工程锚点 |
|----|----------|----------|------------|----------------|
| **LTO-1** | Knowledge Authoring / LLM Wiki Compiler | `note` / ingest / promote 管线可用;还没有 raw material → staged wiki/canonical draft 的 LLM 编译层 | 显式 `draft-wiki` / `refine-wiki`;source pack、rationale、conflict flags、review-promote gate | `KNOWLEDGE.md`, `SELF_EVOLUTION.md` |
| **LTO-2** | Retrieval Quality / Evidence Serving | Retrieval U-T-Y 第一阶段完成:trace、dedicated rerank、source policy、EvidencePack view、source pointers、summary boundary | bounded excerpt、conflict flags、eval hardening、wiki compiler integration、report UX polish | `KNOWLEDGE.md`, `HARNESS.md` |

### 簇 B:架构重构已开头 seed

| ID | 长期目标 | 当前状态 | 下一类增量 | 工程锚点 |
|----|----------|----------|------------|----------------|
| **LTO-4** | Test Architecture / TDD Harness | 已有 `tests/helpers` seed 与首批 layered tests;root tests 与 `test_cli.py` 仍偏聚合 | touched-surface test split、builders/assertions、guard helper 收敛、collect-only + full pytest gate | `docs/engineering/TEST_ARCHITECTURE.md` |
| **LTO-5** | Driven Ports Rollout(formerly Repository / Persistence Ports) | 当前 `truth_governance/{store.py, sqlite_store.py, truth/}` 已是 repository facade 风格,有 `TaskStoreProtocol` 定义但 application 层不通过它访问;application 直接 import 具体实现(orchestrator/knowledge_retrieval/truth_governance/provider_router)。Application/commands 与 application/queries 已由 LTO-9 Step 1 / Step 2 完成。 | 重定义为 N-phase rollout:`application/ports/` 显式定义 `OrchestratorPort` / `KnowledgePort` / `ProposalPort` / `ProviderRouterPort` / `TaskStorePort` / `HttpClientPort` 等;每个 phase 落一个 port,application 函数接受 port 参数。HTTP client port(D6)依赖第一个 port 落定后再做。**触发条件**:测试需要 mock application boundary、添加 second adapter 实现、或 LTO-13 后续 phase 需要更细的注入。 | `CODE_ORGANIZATION.md`, `INVARIANTS.md` |
| **LTO-6** | Knowledge Plane Facade Solidification(主动收口) | `knowledge_plane.py` 当前是 98 行 50 名透传 barrel file,无自有领域语言,被绕过:`application/commands/{knowledge,synthesis}.py` 直接 import `canonical_registry / staged_knowledge / knowledge_store / knowledge_relations / ingestion.pipeline / knowledge_suggestions` 6 个子模块;LTO-13 又新增 1 处 `surface_tools/web/schemas.py` import `staged_knowledge.StagedCandidate`(C1 已修),共 ~10 处绕过。 | **从 touched-surface 慢推改为主动 phase**:替换 50 个 re-export → 6-10 个领域方法(`submit_staged` / `promote` / `reject` / `load_task_view` / `persist_task_view` / `search` 等);把 `knowledge_retrieval` 子模块加 `_internal_*` 前缀或 `internals/` 子包;一次性迁移所有上层导入。一个独立 phase。 | `KNOWLEDGE.md`, `CODE_ORGANIZATION.md` |
| **LTO-13** | FastAPI Local Web UI Write Surface | **已完成实现 milestone**(branch `feat/lto-13-fastapi-local-web-ui-write-surface`,implementation commit `d4c25ac`)。task lifecycle / staged knowledge promote-reject / proposal review-apply 路由全部走 `application/commands/*`;Pydantic request + response Pydantic envelopes(`{"ok": true, "data": ...}`);`Depends` 注入 base_dir;5 处集中 `@app.exception_handler` 替代 try/except ladder;`UnknownStagedCandidateError` 替代 message-string status;`server.py` loopback-only host guard;UI 通过 backend `action_eligibility` 决定按钮可见性,长跑路由用 `pendingTaskAction` 防重复提交;`UI_FORBIDDEN_WRITE_CALLS` 加入 `apply_proposal` / `create_task` / `run_task`。Claude PR review = recommend-merge。 | 无 — LTO-13 已闭合。后续相关工作分裂为:Adapter Discipline Codification(D5,§三)、Adapter Boundary Cleanup Phase A(D4,§三)、fire-and-poll background runner(R2-1 deferred)、Web UX for staged-knowledge force(R2-4 deferred)、文件上传 / route policy admin write controls(deferred)。 | `INTERACTION.md §4.2.3`, `CODE_ORGANIZATION.md §3` |

### 簇 C:子系统解耦四金刚(已完全终结)

每条独立一个 phase / 一条分支,顺序见 §五。

每个 subtrack 实际推进时使用的 pattern vocabulary(facade / strategy / repository / adapter / value object / state / pipeline 等)见 `docs/engineering/GOF_PATTERN_ALIGNMENT.md §3`;不允许"为模式而模式"。

| ID | 长期目标 | 当前状态 | 下一类增量 | 工程锚点 |
|----|----------|----------|------------|----------------|
| **LTO-7** | Provider Router Maintainability | `router.py` 现为 6 个聚焦模块上的 facade:registry / policy / metadata-store / selection / completion-gateway / reports;Path A/C 边界清晰,不依赖 orchestration.executor。**LTO-9 Step 1 消化 CONCERN-1**:route metadata guard allowlist 现明确指定 `provider_router/route_metadata_store.py` 为物理写入者,`router.py` 仅作为 legacy compatibility facade,加入正向断言保证导入路径一致性。| 可选 touched-surface caller 直接导入聚焦模块代替 `router.py`;CONCERN-2 / CONCERN-3(私有名字泄露、fallback 所有权)记录在 `docs/concerns_backlog.md` 并保持开放,仅在相关表面被修改时合并 | `PROVIDER_ROUTER.md` |
| **LTO-8** | Orchestration Lifecycle Decomposition | **已完成**(Step 1 + Step 2)。Step 1:`orchestrator.py` 抽出 6 个聚焦模块(`task_lifecycle / retrieval_flow / artifact_writer / subtask_flow / execution_attempts / knowledge_flow`),Control Plane authority 保留在 `orchestrator.py`;facade 减重 ~14%(3853 → 3331)。Step 2:`harness.py` 2077 → 1028 行 (-50%);9 个 policy/artifact/checkpoint 辅助函数提取到 `artifact_writer.py`;新 helper-side `append_event` 允名单不变量(12 个 telemetry kind + 2 个禁用 kind),由 `test_harness_helper_modules_only_emit_allowlisted_event_kinds` 强制。 | 无 — LTO-8 已完成。`harness.py` 1028 行包含 `build_summary` / `build_resume_note` / `build_task_memory` / `write_task_artifacts` body,作为 deferred 项已记录在 closeout;若未来真实需求触发可单独开 phase。 | `ORCHESTRATION.md`, `HARNESS.md` |
| **LTO-9** | Surface / Meta Optimizer Modularity | **已完成**(Step 1 + Step 2)。Step 1:Meta-Optimizer 只读路径拆分为聚焦模块、CLI 命令族适配器提取、application/commands 种子建立。Step 2:CLI 广泛命令族迁移完成(`cli.py` 3653 → 2672 行,-27%;6 个 application command 模块;6 个 CLI adapter 模块;5 个新 integration test 文件;所有 `apply_proposal` 直接调用移出 `cli.py`)。| 无 — LTO-9 已完成。Reviewed Meta-Optimizer 路径在 `apply_route_metadata.py` 内的内部拆分作为 LTO-10 deferred 项已记录,不在 LTO-9 范围。 | `INTERACTION.md`, `SELF_EVOLUTION.md` |
| **LTO-10** | Governance Apply Handler Maintainability | **已完成**:`apply_proposal` 唯一入口稳定;`governance.py` 642 → 45 行 facade;proposal_registry、apply_canonical、apply_policy、apply_route_metadata、apply_outbox 模块化完成;guard allowlist 明确指定。 | 可选:reviewed route metadata 支持内部拆分(若有可读性收益);durable governance outbox persistence(待事件 schema 与消费者落地) | `INVARIANTS.md`, `DATA_MODEL.md` |

### 簇 D:远端 / 休眠

| ID | 长期目标 | 当前状态 | 下一类增量 | 工程锚点 |
|----|----------|----------|------------|----------------|
| **LTO-11** | Planner / DAG / Strategy Router | 当前编排可用;Planner / DAG / Strategy Router 未一等化 | 等 Orchestration lifecycle 或真实编排瓶颈后再推进 Planner interface / DAG dependency / Strategy Router observability | `ORCHESTRATION.md` |
| **LTO-12** | Long-horizon Runtime / Sync | 当前不投入:local-first single-user 为实现选择,远期保留 multi-actor / sync / object storage 扩展空间 | 仅由真实跨设备/团队/remote worker 需求触发;不在当前 architecture branch 中顺手做 | future; `INVARIANTS.md §7` |

---

## 三、近期 Phase Tickets

近期队列只放下一两个可执行 ticket。Ticket 完成后移出本节,它的后续增量回到上面的长期目标。

当前阶段 **簇 C 完全终结 + LTO-13 实现 milestone 已提交**。Claude PR review = recommend-merge,等待 Human merge gate。Merge 后近期工作转向**架构纪律收口**:把 LTO-13 R3 audit 暴露的 framework-rejection 教训编纂成独立工程纪律,把 `surface_tools/{cli,web}` 重命名为标准 `adapters/{cli,http}`,然后激活 LTO-6 主动 facade 化。

| 优先级 | Ticket | 对应长期目标 | 状态 / Gate | 默认下一步 |
|--------|--------|--------------|-------------|------------|
| 收口中 | **LTO-13 — FastAPI Local Web UI Write Surface** | LTO-13 | 实现 milestone 已提交;Claude PR review = recommend-merge;C1 / N1 follow-up Codex 已处理,等待 Human merge gate | Human merge → 评估 `v1.7.0` tag(WebUI write surface 是首次 LLM-外可观察能力增量) |
| 下一启动 | **Adapter Discipline Codification**(D5;non-LTO independent phase) | 工程纪律 / LTO-4 邻接 | LTO-13 merge 后立即;single-commit phase | 起草 `docs/engineering/ADAPTER_DISCIPLINE.md`(~150 行):Framework-Default Principle(框架原语优先于自写 helper)+ Adapter forbidden zone(adapter 不许编 state machine、不许动 module global、不许在 schema 默认值编码"我是哪个 surface")+ Adapter 模块布局(`api.py` / `schemas.py` / `dependencies.py` / `errors.py`)+ Surface-identity 通过 `OperatorToken` 而非 schema 默认值传递。以 LTO-13 plan_audit Round 1-3 的 14 concerns 为 worked examples |
| 紧随 | **Adapter Boundary Cleanup Phase A**(D4 Phase A;non-LTO independent phase) | 工程纪律 / LTO-13 后续 | D5 落定后;纯 import-path 重命名,无逻辑变化,blast radius 小 | `surface_tools/cli/` → `adapters/cli/`;`surface_tools/web/` → `adapters/http/`;后两波 Phase B(`surface_tools/{consistency_audit,meta_optimizer}.py` → `application/services/`)和 Phase C(`surface_tools/{paths,workspace}.py` → `application/infrastructure/`)按需触发 |
| 然后 | **Knowledge Plane Facade Solidification**(D1;= LTO-6 主动化) | LTO-6 | D4 Phase A 落定后,或 Wiki Compiler 启动前必须先做(因为 Wiki Compiler 会扩大 knowledge_retrieval 调用面) | 替换 `knowledge_plane.py` 50 个 re-export → 6-10 个领域方法;`knowledge_retrieval` 子模块加 `_internal` 前缀;一次性迁移所有 application/truth_governance imports;~10 import 调整 + 6 模块 relabel |
| 候选 | Wiki Compiler draft workflow(LTO-1)/ LTO-4 Test Architecture / 真实需求触发的其他 LTO | LTO-1 / LTO-4 / LTO-2 等 | 上述四个动作完成后视真实需求选择 | Wiki Compiler 需要 LTO-6 facade 完成做 prerequisite;LTO-4 / LTO-5 / LTO-2 仅由真实测试隔离、多 storage、retrieval quality 痛点触发 |

**未列入近期队列(deferred)**:
- **D2 Driven Ports Rollout** = LTO-5 主动启动 —— 等真实 port 需求触发(测试隔离 / second adapter / LTO-13 后续 phase 需要更细注入)。
- **D6 HTTP Client Port** —— D2 第一个 port 落定后做,作为 D2 子项;不预先立 phase。
- **D3 Orchestrator God Object 拆 domain / service / IO 三层** —— 等 D2 部分落定后做,巨大 phase。

---

## 四、命名规则与归档

旧编号不再作为 roadmap 导航语义使用。

- 已经完成或归档的旧编号不再在近期队列里反复出现。
- 如果旧编号覆盖的方向还有长期增量,状态归入 `LTO-*`。
- 新 phase 应写成”推进哪个 LTO 的哪个增量”,例如:
  - `feat/provider-router-split` → 推进 `LTO-7`
  - `feat/wiki-compiler-draft` → 推进 `LTO-1`
  - `feat/test-architecture-cli-split` → 推进 `LTO-4`
- 不再用”某个旧编号没完成所以继续叫同一个编号”来表示长期未完成;这会让 roadmap 读起来像永远半完成。

**LTO-3 已归档**:Architecture Recomposition Program 的执行清单已由簇 C 各 subtrack phase(LTO-7/8/9/10)及 Architecture First Branch helper seed 完全兑现;LTO-3 编号不复用,其历史 plan 保留在 git。

**v1.6.0 Tag 决策**:**已执行 v1.6.0**(2026-05-03,标记 cluster C closure;tag target = `0e6215a docs(release): sync v1.6.0 release docs`)。

**v1.7.0 Tag 决策**:**待 LTO-13 merge 后评估**。LTO-13 FastAPI Local Web UI Write Surface 是首次 LLM-外可观察能力增量,值得单独 cut;也可累积 D5 Adapter Discipline + D4 Phase A rename + D1/LTO-6 Knowledge Plane Facade Solidification 一起作为"接口边界 + 工程纪律"小簇收口后再 cut。Human 决定。

---

## 五、推荐顺序

**Retrieval 第一阶段(done) → Architecture first branch(done) → 簇 C 四金刚(done) → LTO-13 FastAPI Local Web UI(merge 中) → D5 Adapter Discipline → D4 Phase A 重命名 adapters → D1 / LTO-6 Knowledge Plane Facade Solidification → 后续视真实需求(Wiki Compiler / LTO-4 / D2 LTO-5 driven ports)**

### 簇 C 内部顺序与理由

每个 subtrack 在 plan / audit / review 阶段都对照 `docs/engineering/GOF_PATTERN_ALIGNMENT.md` 选择 responsibility language(facade / strategy / repository / adapter / value object / state / pipeline 等);facade-first 与 invariant-preserving 是默认纪律,不是可选项。

| 顺位 | Subtrack | 选这个位置的理由 |
|------|----------|----------|
| 第 1 | **LTO-7 Provider Router**(已完成) | 1422 行单文件,target shape 已在 `CODE_ORGANIZATION §5.2` 画好;Path A/C invariant 边界清晰,blast radius 最小;作为 facade-first 纪律的 warm-up phase 风险最低 |
| 第 2 | **LTO-8 Orchestration lifecycle**(Step 1 + Step 2 已完成) | 痛点最大(orchestrator+harness ~6k 行),但 invariant 敏感度也最高(Control only in Orchestrator / Operator);先靠 LTO-7 把执行肌肉建立起来,再动这块;helper 不可拿到状态推进权。Step 1 完成 6 个编排聚焦模块提取,Step 2 完成 harness.py 2077 → 1028 行 (-50%),政策/工件 pipeline 提取与 event-kind allowlist 新设计点。 |
| 第 3 | **LTO-9 Surface / CLI / Meta Optimizer**(已完成) | cli.py 3790 + meta_optimizer 1320,以 behavior-preserving 拆分为主;借此同时把 LTO-5(application/commands)从 read-only query pilot 推进到写命令完整化;invariant 敏感度最低。Step 1 + Step 2 完成 Meta-Optimizer 聚焦模块、CLI 命令适配器、application/commands 写命令完整化、Control Center 查询迁移。LTO-9 现已完全终结。 |
| 第 4 | **LTO-10 Governance apply handler**(已完成) | Truth write path 最敏感,放最后;`apply_proposal` 仍是唯一公共 mutation entry;前面三轮巩固 facade-first 纪律后再做手术刀级拆分。完成了私有 handler 模块化与 governance.py facade 化。 |

### LTO-13 后续工程纪律 phase 顺序

LTO-13 audit Round 1-3 共 14 项 concerns(R1 5+1 nit + Pydantic + R2 4+2 + R3 5+1)暴露了一个系统性问题:**没有显式架构身份与 adapter 纪律**,导致 Codex 在实现时反复绕开 framework 原语自写 helper(R3 6 项),且 web adapter 直接 reach `knowledge_retrieval.*`(C1)。后续三个独立 phase 把这些教训编纂、消化、放大消除:

| 顺位 | Phase | 选这个位置的理由 |
|------|-------|------------------|
| 第 5 | **D5 Adapter Discipline Codification** | 单文档 phase,~150 行,无代码改动。把 LTO-13 R1-R3 的 14 个真实 concern 作为 worked examples 写进 `docs/engineering/ADAPTER_DISCIPLINE.md` —— 后续每个 adapter phase(LTO-13 已落、D4 Phase A 待做、未来 MCP / desktop / CLI 改造)都受同一份纪律约束。成本极低,价值是"未来不再撞 R3 那种 framework-rejection 雷"。 |
| 第 6 | **D4 Phase A Adapter Boundary Cleanup** | `surface_tools/{cli,web}` → `adapters/{cli,http}` 纯 import-path rename,~50-150 行 diff,无逻辑改动。LTO-13 刚把 web 写表面安顿好,趁热改名;再过几个 phase 就有更多文件堆在 `surface_tools/`(已经混了 driving adapter / application service / application infrastructure 三种东西),改名成本翻倍。Phase B (`surface_tools/{consistency_audit,meta_optimizer}.py` → `application/services/`) 与 Phase C (`surface_tools/{paths,workspace}.py` → `application/infrastructure/`) 按需触发。 |
| 第 7 | **D1 Knowledge Plane Facade Solidification(= LTO-6 主动化)** | LTO-6 不再 passive 慢推。`knowledge_plane.py` 当前是 50 名透传 barrel file,被 application/commands(8 处)+ truth_governance(3 处)+ LTO-13 schemas.py(1 处)绕过;Wiki Compiler / Retrieval 后续增量都会扩大 knowledge_retrieval 调用面。**主动收口的最佳窗口在 Wiki Compiler 启动前**;否则 Wiki Compiler 等于又往 barrel file 上加堆叠。一个独立 phase,~10 import 调整 + 6 模块 relabel + facade 替换 50 re-export → 6-10 领域方法。 |

### 跨阶段排序依据

1. **Retrieval 第一阶段已闭环**:trace、EvidencePack/source pointer、summary boundary 已进入 baseline;后续增量归入 LTO-2,真实使用触发再推进。
2. **Architecture first branch 已 merge**:helper seed、Knowledge Plane facade、Control Center query pilot 提供了 facade-first migration 的样本;后续 subtrack 不能借 program plan 隐式进入实现。
3. **簇 C 四金刚已完全终结**:LTO-7/8/9/10 各自独立 phase 完成;每条都涉及不同 invariant 边界(Provider Router → Path A/C;Orchestration → Control;Governance → Truth write;CLI → application/commands boundary)。v1.6.0 标签已发布标记闭合。
4. **LTO-13 FastAPI Local Web UI 已落地**:Cluster C 已终结后,application/commands 写命令完整化的价值通过 Web UI 表面落地;LTO-13 不依赖簇 B 剩余项重构,作为接口边界首次落地。等待 Human merge gate;merge 后评估 v1.7.0 tag。
5. **D5 / D4 Phase A / D1 紧随 LTO-13**:这是 LTO-13 暴露的系统性教训的工程纪律收口;先文档(D5),再低风险 rename(D4 Phase A),再有真实工程价值的 facade 主动化(D1/LTO-6)。三者按风险升序、按阻断关系排列(Wiki Compiler 真要做就必须先有 D1)。
6. **Wiki Compiler 后置**:LLM Wiki Compiler 依赖 D1 facade 完成、LTO-2 retrieval quality 完成后再启动。
7. **D2 / LTO-5 driven ports + D6 HTTP client port + D3 orchestrator decomposition**:都属于"等真实需求触发"区。D2 触发条件 = 测试隔离 / 第二个 adapter 实现 / 注入复杂度提升;D6 必须在 D2 第一个 port 落定后做;D3 必须在 D2 部分落定后做。三者均为大 phase,不预先排日程。
8. **后续视真实需求**:LTO-4 由测试隔离痛点触发;LTO-1 / LTO-2 由产品需求触发。

---

## 六、维护规则

- Phase closeout 时,只更新对应 `LTO-*` 的当前状态和“下一类增量”。
- 近期队列最多保留 3-4 个 ticket;不要把所有想做的事都放进 queue。
- 已完成 ticket 的细节不复制到 roadmap;查 `git log` 和 `docs/plans/<phase>/closeout.md`。
- 如果某个长期目标连续多轮没有现实触发,保留在 LTO 表,但不放入近期 queue。
- `docs/active_context.md` 仍是当前分支 / 当前 slice / 当前阻塞项的唯一高频状态入口。

---

## 七、本文件的职责边界

`docs/roadmap.md` 是:

- 长期优化目标索引
- 近期可执行 phase ticket 队列
- 跨 phase 优先级和排序理由
- 战略锚点状态

`docs/roadmap.md` 不是:

- 当前 phase 状态板(→ `docs/active_context.md`)
- 完整 phase 历史编年(→ git log + `docs/plans/<phase>/closeout.md`)
- 设计文档(→ `docs/design/`)
- 设计原则副本(→ `docs/design/INVARIANTS.md`)
- closeout 索引(→ `docs/plans/<phase>/closeout.md`)
- Tag / Release docs 同步状态(→ `docs/concerns_backlog.md`)
