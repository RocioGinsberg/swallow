---
author: claude
status: living-document
---

> **Document discipline**
> Owner: Human
> Updater: Codex 主线(长期目标、近期 ticket、优先级、风险批注)+ `roadmap-updater` subagent(phase 完成后的事实状态同步)+ Claude 主线(review / tag 相关轻量风险批注)
> Trigger: phase 收口 OR 会话讨论中浮现新方向 OR phase 拆分 OR Human 请求方向建议
> Anti-scope: 不维护已完成 phase 历史(→ git log + active `docs/plans/<phase>/closeout.md` 或 archived `docs/archive_phases/<phase>/closeout.md`);不维护 tag / release docs 状态(→ `docs/concerns_backlog.md`);不存储设计原则(→ `INVARIANTS.md`);不维护 phase 高频状态(→ `docs/active_context.md`)
> 长度上限:300 行;超过说明放进了不该放的东西

# 演进路线图 (Roadmap)

> 最近更新:见 git log。本文件维护**长期优化目标**和**近期可执行 phase ticket**。
> 规则:长期目标可以跨多轮增量推进;phase ticket 是一次可提交切片,完成后从近期队列移走,但它对应的长期目标继续保留状态。

---

## 一、当前实现基线

| 维度 | 当前状态 |
|------|----------|
| **知识治理** | Raw Material / Knowledge Truth / Retrieval & Serving 三层已成型;Wiki / Canonical 是默认语义入口;`RawMaterialStore` filesystem backend 已落地 |
| **知识捕获** | `swl note` / clipboard / `generic_chat_json` / local file ingestion 已可进入 staged review 管线 |
| **检索基础设施** | Retrieval U-T-Y 已落地:dedicated rerank boundary、retrieval trace、source policy warnings、EvidencePack compatibility view、RawMaterialStore-backed source pointer resolution、summary route boundary |
| **治理边界** | `apply_proposal`、SQLite-primary truth、Path A/B/C、§9 guard suite 均已实现到稳定基线 |
| **Agent 体系** | 4 Specialist + 1 Authoring Specialist(Wiki Compiler 第一 + 第二阶段已落地)+ 2 Validator 独立生命周期已落地;具体品牌绑定见 `docs/design/EXECUTOR_REGISTRY.md` |
| **当前重构状态** | **簇 C 已归档 + LTO-13 / LTO-6 / LTO-1(stage 1 + stage 2) / LTO-2 retrieval quality / LTO-4 Test Architecture / LTO-2 source scoping 全部落地 + Hygiene Bundle 已完成**:LTO-7/8/9/10 全部完成(详情见 git log + closeouts);LTO-13 已 merge(`4ea7a9d`)tag `v1.7.0` at `2156d4a`;LTO-6 已 merge(`883e2a9`)`knowledge_plane.py` 升级为 functional facade;LTO-1 第一阶段已 merge(`349efa9`)tag `v1.8.0` at `d6f2442` 首次 LLM-内编译能力进入本地 operator workflow;**LTO-1 第二阶段已 merge(`21f8dc8`)** governed supersede apply + derived_from evidence objectization + Web fire-and-poll authoring + 结构化 confirmation UX,**不单独 cut tag**;**LTO-2 Retrieval Quality / Evidence Serving 已 merge(`03744f0`)** source-anchor evidence identity + cross-candidate evidence dedup + EvidencePack/source pointer dedup + operator report quality + deterministic eval/guard coverage,**review 建议不单独 cut tag**;**LTO-4 Test Architecture 已在 `main` 完成到 `ac2d3ff`**(压缩流程):`test_cli.py` 拆入 `tests/integration/cli/` command-family modules;新增 `tests/helpers/{builders,assertions,ast_guards}.py`;`tests/conftest.py` 暴露 builder fixtures;最终 `806/825` collected、`806 passed,19 deselected`;**LTO-2 Retrieval Source Scoping And Truth Reuse Visibility 已 merge(`d4288a1`)**:task-declared `document_paths` 进入 retrieval request,declared docs 优先,generated/archive/build-cache 噪声降权,report / memory 暴露 truth reuse visibility。Hygiene Bundle 已收口 D4 Phase B/C + LTO-6 C1 alias + LTO-7 follow-up 私名耦合。当前处于 post-merge checkpoint,等待 tag evaluation / 下一方向选择。 |
| **架构身份** | 项目事实上的架构 = **Hexagonal (Ports & Adapters)**;driving adapters = `adapters/{cli,http}/`;application layer = `application/{commands,queries,services,infrastructure}/`(D4 Phase A/B/C 全部已落地);domain / control plane = `orchestration/` + `knowledge_retrieval/`(D1/LTO-6 已收口为 functional facade)+ `truth_governance/` + `provider_router/`(LTO-7 follow-up 已收口);driven adapters / infrastructure = `truth_governance/sqlite_store.py` + `provider_router/completion_gateway.py` + `_io_helpers.py` 等。**`surface_tools/` 包已整体删除**(原 application service 类文件搬到 `application/services/`,原路径/工作区类搬到 `application/infrastructure/`)。已识别 6 项偏离 D1-D6,**D1 / D4(全部 Phase A+B+C)/ D5 已落地**;D2 / D3 / D6 deferred;修复路径见 §五。 |
| **工程纪律** | 长期编码 / 重构遵循 `docs/engineering/CODE_ORGANIZATION.md`(分层 / facade-first / migration discipline)+ `docs/engineering/GOF_PATTERN_ALIGNMENT.md`(facade / strategy / repository / adapter / value object / state / pipeline 等 pattern 仅作为 responsibility language)+ `docs/engineering/TEST_ARCHITECTURE.md`(分层测试 / TDD harness)+ `docs/engineering/ARCHITECTURE_DECISIONS.md`(已 merge:架构身份 = Hexagonal、当前已用模式清单 + 已识别 6 项偏离 D1-D6 的修复路径)+ `docs/engineering/ADAPTER_DISCIPLINE.md`(已 merge:LTO-13 audit 教训编纂的 adapter 实施纪律,6 条规则 + 强制模块布局 + 16 项 worked examples)。LTO-13 R3 audit 暴露的 framework-rejection 系统性问题已由 D5 Adapter Discipline Codification 编纂,后续每个 adapter / specialist phase 起草前必读。 |

---

## 二、长期优化目标

这些是跨 phase 的长期目标。一次 phase 只推进其中一个可审查增量,不会让目标本身消失。

12 条 LTO 不是平等并列(编号 LTO-3 已归档不复用),按推进性质分 **4 簇**:

- **簇 A 产品 / 知识能力**(LTO-1, LTO-2):沿现有架构垂直推进的产品级能力。LTO-2 第一阶段已闭环,LTO-1 Wiki Compiler 第一阶段已落地;后续增量按真实知识质量 / authoring workflow 痛点触发。
- **簇 B 架构重构 + 接口边界 + 工程纪律**(LTO-4, LTO-5, LTO-6, LTO-13):seed 来自 first branch,通过 LTO-13 接口边界落地后扩展为含工程纪律的活跃簇。**LTO-13 已完成(v1.7.0 tagged),LTO-6 已完成(`883e2a9`)**。LTO-5 已重定义为 **Driven Ports Rollout**(N phases,首推 `TaskStorePort`),按需主动推进。新增的工程纪律收口动作 D5 Adapter Discipline + D4 Adapter Boundary Cleanup Phase A 已落地;后续 D2 / D3 / D6 deferred。(LTO-3 已归档,见 §四。)
- **簇 C 子系统解耦四金刚**(LTO-7, LTO-8, LTO-9, LTO-10):**已归档**;详情见 git log 与各自 archived closeout。
- **簇 D 远端 / 休眠**(LTO-11, LTO-12):默认不投入,仅由真实需求触发。

下面分簇展开。

### 簇 A:产品 / 知识能力(沿现有架构垂直推进)

| ID | 长期目标 | 当前状态 | 下一类增量 | 工程锚点 |
|----|----------|----------|------------|----------------|
| **LTO-1** | Knowledge Authoring / LLM Wiki Compiler(authoring specialist) | **第一阶段已完成,merge `349efa9`**(2026-05-04;v1.8.0 tagged at `d6f2442`):`swl wiki draft` / `swl wiki refine --mode supersede\|refines` / `swl wiki refresh-evidence` 三命令;Wiki Compiler specialist 注册为 `WikiCompilerAgent`;LLM Path C 经 Provider Router;只写 task artifacts + staged knowledge;staged candidate 保留 source pack / rationale / relation metadata / conflict_flag;Knowledge Browse read routes + Web Knowledge panel(read-only);M5 guard/eval。**第二阶段已完成,merge `21f8dc8`**(2026-05-04,不 cut tag):`_CanonicalProposal.supersede_target_ids` + `_promote_canonical` target-id flip(governed supersede 走 `apply_proposal`);`materialize_source_evidence_from_canonical_record` 把 source_pack 锚点物化为 evidence object 并通过 `derived_from` relation 持久(类型守卫 source=wiki / target=evidence);Web fire-and-poll API(FastAPI `BackgroundTasks` 原语);静态 Web authoring 面板 + 结构化 `confirmed_notice_types` 替代 raw `force`;5 个 M5 guard 强制 propose-only / adapter boundary / supersede apply ownership / derived_from target / evidence anchor versioning。`KNOWLEDGE_RELATION_TYPES` 加入 `derived_from`(双枚举分层延续:metadata 5 类型 vs persisted 6 类型,`supersedes` 仍只翻 status field 不持 row)。 | 后续触发模式。下一类增量(stage 3 候选,真实需求触发):cross-candidate evidence dedup(已在 backlog Roadmap-Bound 由 LTO-2 消化)、`know_evidence` schema migration(已在 backlog Active Open)、Wiki Compiler 视图 3 全图谱可视化(deferred to Graph RAG)、relation creation site decision matrix(LTO-1 stage 2 review C1 已 fold 进 closeout,但未来若引入新 relation 类型需要重新审视) | `KNOWLEDGE.md`, `SELF_EVOLUTION.md`, `EXECUTOR_REGISTRY.md`, `ADAPTER_DISCIPLINE.md` |
| **LTO-2** | Retrieval Quality / Evidence Serving | Retrieval U-T-Y 第一阶段完成:trace、dedicated rerank、source policy、EvidencePack view、source pointers、summary boundary。**LTO-2 Retrieval Quality / Evidence Serving 已完成,merge `03744f0`**(2026-05-04,不 cut tag):`source-anchor-v1` five-field canonical JSON identity;stable `evidence-src-<source_anchor_key>` evidence ids;cross-candidate evidence object reuse through `knowledge_object_exists(base_dir, evidence_id)`;`derived-from-v1` deterministic relation id by source object + evidence id;retrieval metadata path A enrichment;EvidencePack supporting evidence / fallback hits / source pointers dedup by metadata;operator report source-anchor key / dedup counts / pointer status / stored preview excerpt;M5 deterministic eval + invariant guard。**Retrieval Source Scoping And Truth Reuse Visibility 已完成,merge `d4288a1`**(2026-05-04):task-declared `document_paths` 通过 `RetrievalRequest.declared_document_paths` 进入 retrieval,declared docs 在 rerank 前获得 priority,generated/archive/build-cache noise source policy 会降权;`score_breakdown` 暴露 `declared_document_priority` / `source_noise_penalty`;`retrieval_report.md`、task memory、summary 暴露 truth reuse visibility。Review 3 concerns 已登记到 `docs/concerns_backlog.md`:score magnitude tuning、task-knowledge reason count 语义、canonical reason coverage。 | 后续触发模式。下一类增量:retrieval policy tuning(score magnitude / reason count semantics / canonical filtered reason visibility)或 `know_evidence` schema migration / evidence lookup index;均等真实使用反馈或 schema 需求触发。Chunk 调整仍保持次级,不在无实证时预先大改。 | `KNOWLEDGE.md`, `HARNESS.md`, `docs/plans/r-entry-real-usage/findings.md` |

### 簇 B:架构重构 + 接口边界 + 工程纪律(活跃推进)

| ID | 长期目标 | 当前状态 | 下一类增量 | 工程锚点 |
|----|----------|----------|------------|----------------|
| **LTO-4** | Test Architecture / TDD Harness | **已完成,main at `ac2d3ff`**(2026-05-04,压缩流程,不 cut tag):`tests/test_cli.py` 从 11156 行历史聚合拆为 `tests/integration/cli/test_<family>_commands.py`;新增 `tests/helpers/builders.py` / `assertions.py` / `ast_guards.py`;`tests/test_invariant_guards.py` AST/import-walking helper 收敛;`tests/conftest.py` 统一 builder fixture 入口;最终 collect-only `806/825 tests collected (19 deselected)`,比起始 baseline `802/821` 仅新增 4 个 helper self-tests;全量 `806 passed,19 deselected in 131.76s`。 | 后续仅按 touched surface 增量维护;真实使用期发现的测试摩擦再作为小 hygiene / D2 port 触发信号处理。 | `docs/engineering/TEST_ARCHITECTURE.md` |
| **LTO-5** | Driven Ports Rollout(formerly Repository / Persistence Ports) | `truth_governance/{store.py, sqlite_store.py, truth/}` 已是 repository facade 风格,有 `TaskStoreProtocol` 但 application 层不通过它访问;application 直接 import 具体实现(orchestrator/knowledge_retrieval/truth_governance/provider_router) | N-phase rollout:`application/ports/` 显式定义 `OrchestratorPort` / `KnowledgePort` / `ProposalPort` / `ProviderRouterPort` / `TaskStorePort` / `HttpClientPort` 等;每个 phase 落一个 port。HTTP client port(D6)依赖第一个 port 落定后再做。**触发条件**:测试需要 mock application boundary、添加 second adapter 实现、或后续 phase 需要更细的注入 | `CODE_ORGANIZATION.md`, `INVARIANTS.md` |
| **LTO-6** | Knowledge Plane Facade Solidification(已闭合) | **已完成,merge `883e2a9 Knowledge Plane Facade Solidification`**(2026-05-04)。`knowledge_plane.py` 从 50 名透传 barrel file 升级为 functional facade wrapper(domain 命名 + 包装 body,非 re-export);6 个 `_internal_*` 模块在同一 package 内 rename(`_internal_canonical_registry` / `_internal_staged_knowledge` / `_internal_knowledge_store` / `_internal_knowledge_relations` / `_internal_knowledge_suggestions` / `_internal_ingestion_pipeline`);24 处 application / orchestration / adapters / truth_governance / tests 直接 reach `knowledge_retrieval.*` 已全部清零;`tests/test_invariant_guards.py` 加 Knowledge Plane public-boundary import guard(rejects `_internal_*` + facade-covered modules + 任意非 facade `knowledge_retrieval.*`);唯一 production 例外 = `application/services/librarian_executor.py` import `raw_material.py`(显式 storage-boundary allowlist)。Hygiene Bundle 已删除 report `render_*` / `build_*` 配对别名,报告渲染公共名统一为 `render_*`。 | 无 — 已闭合。 | `KNOWLEDGE.md`, `CODE_ORGANIZATION.md` |
| **LTO-13** | FastAPI Local Web UI Write Surface | **已完成,v1.7.0 tagged**(merge `4ea7a9d`,tag `2156d4a`)。task lifecycle / staged knowledge promote-reject / proposal review-apply 路由全部走 `application/commands/*`;Pydantic request + response envelope;`Depends` + 集中 `@app.exception_handler`;loopback-only serve guard;UI 通过 backend `action_eligibility` 决定按钮可见性 | 无 — 已闭合。后续相关工作分裂为 §三 中的 D5 / D4 Phase A 独立 phase,以及 deferred 项(fire-and-poll background runner、Web UX for staged-knowledge force、文件上传、route policy admin write controls) | `INTERACTION.md §4.2.3`, `CODE_ORGANIZATION.md §3` |

### 簇 C:子系统解耦四金刚(已归档)

LTO-7 / LTO-8(Step 1+Step 2)/ LTO-9(Step 1+Step 2)/ LTO-10 全部完成,v1.6.0 tagged 标记 cluster closure(`0e6215a`)。每条 LTO 各自独立 phase / closeout / merge 已落定,**详情见 git log 与 `docs/archive_phases/` 下的 archived closeout**;本 roadmap 不再维护 step 级历史。

四条 LTO 触及的 invariant 边界(Provider Router → Path A/C;Orchestration → Control;CLI → application/commands;Governance → Truth write)已在簇 C phase 期间稳定;后续动作仅在真实痛点触发时通过新 phase / 偏离修复(D1-D6)进入,而非作为簇 C 接续。

### 簇 D:远端 / 休眠

| ID | 长期目标 | 当前状态 | 下一类增量 | 工程锚点 |
|----|----------|----------|------------|----------------|
| **LTO-11** | Planner / DAG / Strategy Router | 当前编排可用;Planner / DAG / Strategy Router 未一等化 | 等 Orchestration lifecycle 或真实编排瓶颈后再推进 Planner interface / DAG dependency / Strategy Router observability | `ORCHESTRATION.md` |
| **LTO-12** | Long-horizon Runtime / Sync | 当前不投入:local-first single-user 为实现选择,远期保留 multi-actor / sync / object storage 扩展空间 | 仅由真实跨设备/团队/remote worker 需求触发;不在当前 architecture branch 中顺手做 | future; `INVARIANTS.md §7` |

---

## 三、近期 Phase Tickets

近期队列只放下一两个可执行 ticket。Ticket 完成后移出本节,它的后续增量回到上面的长期目标(已完成 ticket 不在此重复留底,见 git log)。

D5 Adapter Discipline + D4 Phase A + LTO-6 Knowledge Plane Facade Solidification + LTO-1 Wiki Compiler 第一阶段 + Hygiene Bundle + LTO-1 Wiki Compiler 第二阶段 + LTO-2 Retrieval Quality / Evidence Serving + LTO-4 Test Architecture + LTO-2 Retrieval Source Scoping And Truth Reuse Visibility 全部已落地(2026-05-03 → 2026-05-04;commits `d67c2ad` `7450953` `883e2a9` `349efa9` `e656bd3` `21f8dc8` `03744f0` `ac2d3ff` `d4288a1`,tag `v1.8.0` at `d6f2442`;Hygiene Bundle / LTO-1 stage 2 / LTO-2 retrieval quality / LTO-4 不 cut tag;LTO-2 source scoping 等待 post-merge tag evaluation)。

**当前近期队列 = none;post-merge checkpoint**。

R-entry Real Usage runbook 与 findings 已完成本机可验证部分,并触发/支撑 LTO-2 source scoping phase。保留 `docs/plans/r-entry-real-usage/plan.md` / `findings.md` 作为后续真实使用输入,但不再作为当前近期队列项。

**下一 Direction Gate 候选(由 Human 选定)**:

| 候选方向 | 触发条件 / 信号 | 性质 |
|---|---|---|
| **Wiki Compiler 第三阶段** | R-entry 真实 Operator 使用反馈:cross-task evidence schema migration / 视图 3 全图谱 / 多 worker durable job runner / 文件上传 source ingestion 等 | 产品向 / LTO-1 增量 |
| **LTO-2 retrieval policy tuning** | LTO-2 source scoping review follow-ups 在真实使用中复现:declared-doc priority 过强、task knowledge reason counts 被误读、canonical filtered reason 不透明。 | 产品质量 / LTO-2 增量 |
| **D2 LTO-5 Driven Ports Rollout 第一个 port** | 测试需要 mock application boundary / 引入 second adapter / 注入复杂度提升(LTO-4 完成后 builders 形态会让这个边界更清晰) | 架构重构 |

**未列入近期队列(deferred)**:

- **D6 HTTP Client Port** —— D2 第一个 port 落定后做,作为 D2 子项;不预先立 phase。
- **D3 Orchestrator God Object 拆分** —— 等 D2 部分落定后做,巨大 phase。
- **LTO-8 follow-up:`debate_loop_core` 9 callable 注入** —— `execution_attempts.py:254` 持有 loop termination 控制,与 helper 不持 state-touching 控制权的纪律边缘相似;callables 是 telemetry-only(技术上守住 INVARIANTS)。**Revisit at LTO-11**(Planner / DAG / Strategy Router)首次设计 loop control pattern 时一并处理。
- **Wiki Compiler 视图 3(项目级全图谱可视化)**—— 当前 wiki 节点量在全图谱不友好区间;违反 LTO-13 §M3 "no new frontend package, build step, or asset pipeline";视真实需求或 Graph RAG 远期方向(`KNOWLEDGE.md §9`)再评估。
- **`know_evidence` schema migration** —— LTO-1 stage 2 backlog Active Open 项(DATA_MODEL §3.3 设计草案 vs `knowledge_evidence` 实际 schema 长期不一致);跨任务 evidence lookup / 全局 evidence id 唯一性需求触发时开独立 schema migration phase。
- LTO-13 deferred 项(fire-and-poll background runner、staged-knowledge force Web UX、文件上传、route policy admin write controls)—— 真实需求触发再开 phase。

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

**v1.7.0 Tag 决策**:**已执行 v1.7.0**(标记 LTO-13 FastAPI Local Web UI Write Surface 落地;tag target = `2156d4a docs(release): sync v1.7.0 release docs`;merge commit = `4ea7a9d FastAPI Local Web UI Write Surface`)。这是首次 LLM-外可观察的写表面增量。

**v1.8.0 Tag 决策**:**已执行 v1.8.0**(标记 LTO-1 Wiki Compiler 第一阶段落地;tag target = `d6f2442 docs(release): sync v1.8.0 release docs`;merge commit = `349efa9 Knowledge Authoring / LLM Wiki Compiler(authoring specialist)`)。这是首次 LLM-内知识编译能力增量进入本地 operator workflow,与 v1.7.0(首次 LLM-外可观察写表面)形成姐妹节点。

---

## 五、推荐顺序

**Retrieval 第一阶段(done) → Architecture first branch(done) → 簇 C 四金刚(done;v1.6.0) → LTO-13 FastAPI Local Web UI(done;v1.7.0) → D5 Adapter Discipline + D4 Phase A(done) → LTO-6 Knowledge Plane Facade Solidification(done) → LTO-1 Wiki Compiler 第一阶段(done;v1.8.0) → Hygiene Bundle(done;不 cut tag) → LTO-1 Wiki Compiler 第二阶段(done;不 cut tag) → LTO-2 Retrieval Quality / Evidence Serving(done;不 cut tag) → LTO-4 Test Architecture(done;压缩流程,不 cut tag) → R-entry Real Usage(done;findings captured) → LTO-2 Retrieval Source Scoping And Truth Reuse Visibility(done;merge `d4288a1`) → tag evaluation / next Direction Gate**

簇 C 四金刚的内部排序与每条 LTO 的逐步骤理由已归档,详情见 git log 与 `docs/archive_phases/` 下的 archived closeout。

### 近期 phase 顺序

当前无开发 phase 排队。LTO-2 Retrieval Source Scoping And Truth Reuse Visibility 已完成并 merge 到 `main@d4288a1`;下一步先做 tag evaluation,再由 Human 选择下一轮 phase。R-entry runbook/findings 与 source scoping closeout 保留为后续真实使用输入。

### 跨阶段排序依据

1. **D5 / D4 Phase A / LTO-6 / LTO-1 stage 1 / Hygiene Bundle / LTO-1 stage 2 / LTO-2 / LTO-4 顺序完成**(2026-05-03 → 2026-05-04;commits `d67c2ad` `7450953` `883e2a9` `349efa9` `e656bd3` `21f8dc8` `03744f0` `ac2d3ff`,tags `v1.7.0` / `v1.8.0`):八个 phase 形成"adapter 工程纪律编纂 → adapter 命名标准化 → Knowledge Plane facade 收口 → 首次 LLM-内编译能力 → 工程纪律 hygiene 收口 → Wiki Compiler 闭环到 Web governed authoring → retrieval quality / evidence dedup baseline → test architecture 收口"的连续闭环;LTO-13 audit Round 1-3 暴露的 14 项 concerns 全部归档为 `ADAPTER_DISCIPLINE.md` worked examples;`surface_tools/` 包整体消失,Hexagonal 三层 driving adapter / application / domain+driven 边界稳定。
2. **Hygiene Bundle / LTO-1 stage 2 / LTO-2 / LTO-4 都不 cut tag**:Hygiene Bundle 是工程纪律收口;LTO-1 stage 2 是 v1.8.0 能力的质量提升;LTO-2 是 retrieval quality 增量;LTO-4 是测试架构纪律 —— 四者都是质量 / 工程纪律提升而非新能力跃迁。累积到"知识 authoring 闭环 + retrieval quality 增量 + 工程纪律稳定"后 cut **v1.9.0**(典型时机:R-entry 真实反馈触发的下一个产品 phase 完成后)。
3. **LTO-4 Test Architecture 已完成,作为 R-entry 前最后工程纪律 phase**:`test_cli.py` 11156 行单文件与 `test_invariant_guards.py` 1435 行的维护成本已被拆分/helper 化消化;R-entry 期任何 bugfix / touched-surface phase 都会受益。压缩流程判据 = 风险极低 + 无新功能 / LLM / invariant + 每项有 file:line 锚点。
4. **R-entry 不是 LTO-* phase 节点,是当前项目阶段**:它检验 phase 链路最终成果,真实使用产生的反馈是 Wiki Compiler 第三阶段 / LTO-2 进一步增量 / D2 LTO-5 driven ports 优先级判断的最强信号源 —— 比凭直觉做 D2 / 第三阶段更扎实。当前 runbook 已在 `docs/plans/r-entry-real-usage/plan.md`。
5. **D2 / LTO-5 driven ports + D6 HTTP client port + D3 orchestrator decomposition**:都属于"等真实需求触发"区。D2 触发条件 = 测试隔离 / 第二个 adapter 实现 / 注入复杂度提升;D6 必须在 D2 第一个 port 落定后做;D3 必须在 D2 部分落定后做。三者均为大 phase,不预先排日程。**LTO-4 完成后 builders 形态会让 D2 注入边界更清晰**,但仍需要真实需求作为最终触发。
6. **Wiki Compiler 第三阶段候选**:cross-task evidence schema migration / 视图 3 全图谱 / 多 worker durable job runner / 文件上传 source ingestion 等;每一项都需要真实 Operator 使用反馈作为锚点 —— LTO-2 刚 merge,加上 LTO-4 一并落地后,反馈环境才完整。
7. **LTO-8 `debate_loop_core` deferred 到 LTO-11**:9 callable 注入纪律边缘问题,callables 是 telemetry-only,技术上守住 INVARIANTS;待 LTO-11 Planner / DAG / Strategy Router 首次设计 loop control pattern 时一并处理。
8. **R-entry 后的首选 Direction Gate 已完成 = LTO-2 Retrieval Source Scoping And Truth Reuse Visibility**:该 phase 只处理候选池 source scoping / generated-archive 噪声策略 / report truth reuse visibility / 相关 eval fixture,没有顺手推进 Graph RAG、schema migration、vector index overhaul 或 chunk 策略大改。
9. **后续视真实使用反馈**:Wiki Compiler 视图 3(全图谱)与 Graph RAG 远期方向同步,真实需求触发再做;`know_evidence` schema migration 等跨任务 evidence lookup / 全局 evidence id 唯一性需求触发;LTO-2 source scoping 的 3 个 review concerns 进入 retrieval policy tuning 候选。

---

## 六、维护规则

- Phase closeout 时,只更新对应 `LTO-*` 的当前状态和“下一类增量”。
- 近期队列最多保留 3-4 个 ticket;不要把所有想做的事都放进 queue。
- 已完成 ticket 的细节不复制到 roadmap;查 `git log` 和 active / archived phase closeout。
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
- 完整 phase 历史编年(→ git log + active / archived phase closeout)
- 设计文档(→ `docs/design/`)
- 设计原则副本(→ `docs/design/INVARIANTS.md`)
- closeout 索引(→ active / archived phase closeout)
- Tag / Release docs 同步状态(→ `docs/concerns_backlog.md`)
