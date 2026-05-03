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
| **知识治理** | Raw Material / Knowledge Truth / Retrieval & Serving 三层已成型;Wiki / Canonical 是默认语义入口;`RawMaterialStore` filesystem backend 已落地 |
| **知识捕获** | `swl note` / clipboard / `generic_chat_json` / local file ingestion 已可进入 staged review 管线 |
| **检索基础设施** | Retrieval U-T-Y 已落地:dedicated rerank boundary、retrieval trace、source policy warnings、EvidencePack compatibility view、RawMaterialStore-backed source pointer resolution、summary route boundary |
| **治理边界** | `apply_proposal`、SQLite-primary truth、Path A/B/C、§9 guard suite 均已实现到稳定基线 |
| **Agent 体系** | 4 Specialist + 1 Authoring Specialist(Wiki Compiler,LTO-1 待落地)+ 2 Validator 独立生命周期已落地;具体品牌绑定见 `docs/design/EXECUTOR_REGISTRY.md` |
| **当前重构状态** | **簇 C 已归档 + LTO-13 接口边界落地 + LTO-6 Knowledge Plane facade 收口完成**:LTO-7/8/9/10 全部完成(详情见 git log + closeouts);LTO-13 已 merge(`4ea7a9d`)tag `v1.7.0` at `2156d4a`;LTO-6 已 merge(`883e2a9`)`knowledge_plane.py` 升级为 functional facade,24 处绕过全部清零,`knowledge_retrieval/` 6 个子模块 `_internal_*` 化。下一启动:**LTO-1 Wiki Compiler 第一阶段**(authoring specialist + 4 模式 + Web 知识呈现视图 1+2),落地后 cut `v1.8.0`。 |
| **架构身份** | 项目事实上的架构 = **Hexagonal (Ports & Adapters)**;driving adapters = `adapters/{cli,http}/`(D4 Phase A 已落地,从 `surface_tools/` 重命名);application layer = `application/{commands,queries}/`;domain / control plane = `orchestration/` + `knowledge_retrieval/`(D1/LTO-6 已收口为 functional facade)+ `truth_governance/` + `provider_router/`;driven adapters / infrastructure = `truth_governance/sqlite_store.py` + `provider_router/completion_gateway.py` + `_io_helpers.py` 等。已识别 6 项偏离 D1-D6,D1/D4 Phase A/D5 已落地;D2/D3/D6 deferred;修复路径见 §五。 |
| **工程纪律** | 长期编码 / 重构遵循 `docs/engineering/CODE_ORGANIZATION.md`(分层 / facade-first / migration discipline)+ `docs/engineering/GOF_PATTERN_ALIGNMENT.md`(facade / strategy / repository / adapter / value object / state / pipeline 等 pattern 仅作为 responsibility language)+ `docs/engineering/TEST_ARCHITECTURE.md`(分层测试 / TDD harness)+ `docs/engineering/ARCHITECTURE_DECISIONS.md`(已 merge:架构身份 = Hexagonal、当前已用模式清单 + 已识别 6 项偏离 D1-D6 的修复路径)+ `docs/engineering/ADAPTER_DISCIPLINE.md`(已 merge:LTO-13 audit 教训编纂的 adapter 实施纪律,6 条规则 + 强制模块布局 + 16 项 worked examples)。LTO-13 R3 audit 暴露的 framework-rejection 系统性问题已由 D5 Adapter Discipline Codification 编纂,后续每个 adapter / specialist phase(LTO-1 等)起草前必读。 |

---

## 二、长期优化目标

这些是跨 phase 的长期目标。一次 phase 只推进其中一个可审查增量,不会让目标本身消失。

12 条 LTO 不是平等并列(编号 LTO-3 已归档不复用),按推进性质分 **4 簇**:

- **簇 A 产品 / 知识能力**(LTO-1, LTO-2):沿现有架构垂直推进的产品级能力。LTO-2 第一阶段已闭环,LTO-1 等地基。
- **簇 B 架构重构 + 接口边界 + 工程纪律**(LTO-4, LTO-5, LTO-6, LTO-13):seed 来自 first branch,通过 LTO-13 接口边界落地后扩展为含工程纪律的活跃簇。**LTO-13 已完成(v1.7.0 tagged),LTO-6 已完成(`883e2a9`)**。LTO-5 已重定义为 **Driven Ports Rollout**(N phases,首推 `TaskStorePort`),按需主动推进。新增的工程纪律收口动作 D5 Adapter Discipline + D4 Adapter Boundary Cleanup Phase A 已落地;后续 D2 / D3 / D6 deferred。(LTO-3 已归档,见 §四。)
- **簇 C 子系统解耦四金刚**(LTO-7, LTO-8, LTO-9, LTO-10):**已归档**;详情见 git log 与各自 `docs/plans/<phase>/closeout.md`。
- **簇 D 远端 / 休眠**(LTO-11, LTO-12):默认不投入,仅由真实需求触发。

下面分簇展开。

### 簇 A:产品 / 知识能力(沿现有架构垂直推进)

| ID | 长期目标 | 当前状态 | 下一类增量 | 工程锚点 |
|----|----------|----------|------------|----------------|
| **LTO-1** | Knowledge Authoring / LLM Wiki Compiler(authoring specialist) | `note` / ingest / promote 管线可用;LTO-6 Knowledge Plane facade 已收口(已 merge `883e2a9`),Wiki Compiler 硬 prerequisite 已就绪。设计文档已先行:`EXECUTOR_REGISTRY.md` 加 Wiki Compiler 第 5 个 specialist 条目 + 4 模式表(draft / refine-supersede / refine-refines / refresh-evidence);`SELF_EVOLUTION.md §2 + §4.2` 工作流加上游环节 + 4 模式 + Operator 决策点。Web Control Center 知识呈现 3 视图分级:视图 1(task-knowledge)+ 视图 2(detail + adjacent relations)并入本 phase;视图 3(全图谱)deferred | **下一启动 phase**(v1.8.0 节点)。M1:Wiki Compiler 起草核心(`swl wiki draft` / `swl wiki refine --mode supersede\|refines` / `swl wiki refresh-evidence` 三命令 + application/commands + prompt pack + source pack + rationale + conflict_flag);M2:Knowledge browse 路由(`GET /api/knowledge/{wiki,canonical,staged}`);M3:Knowledge detail + relations(`GET /api/knowledge/{id}` + `GET /api/knowledge/{id}/relations`);M4:Web UI Knowledge panel(标签页 + 列表 + 详情 + 邻接 relations,遵循 `ADAPTER_DISCIPLINE.md`);M5:Guard(Wiki Compiler agent boundary + Evidence rebuild parser_version guard) | `KNOWLEDGE.md`, `SELF_EVOLUTION.md`, `EXECUTOR_REGISTRY.md`, `ADAPTER_DISCIPLINE.md` |
| **LTO-2** | Retrieval Quality / Evidence Serving | Retrieval U-T-Y 第一阶段完成:trace、dedicated rerank、source policy、EvidencePack view、source pointers、summary boundary | bounded excerpt、conflict flags、eval hardening、wiki compiler integration、report UX polish | `KNOWLEDGE.md`, `HARNESS.md` |

### 簇 B:架构重构 + 接口边界 + 工程纪律(活跃推进)

| ID | 长期目标 | 当前状态 | 下一类增量 | 工程锚点 |
|----|----------|----------|------------|----------------|
| **LTO-4** | Test Architecture / TDD Harness | 已有 `tests/helpers` seed 与首批 layered tests;root tests 与 `test_cli.py` 仍偏聚合 | touched-surface test split、builders/assertions、guard helper 收敛、collect-only + full pytest gate | `docs/engineering/TEST_ARCHITECTURE.md` |
| **LTO-5** | Driven Ports Rollout(formerly Repository / Persistence Ports) | `truth_governance/{store.py, sqlite_store.py, truth/}` 已是 repository facade 风格,有 `TaskStoreProtocol` 但 application 层不通过它访问;application 直接 import 具体实现(orchestrator/knowledge_retrieval/truth_governance/provider_router) | N-phase rollout:`application/ports/` 显式定义 `OrchestratorPort` / `KnowledgePort` / `ProposalPort` / `ProviderRouterPort` / `TaskStorePort` / `HttpClientPort` 等;每个 phase 落一个 port。HTTP client port(D6)依赖第一个 port 落定后再做。**触发条件**:测试需要 mock application boundary、添加 second adapter 实现、或后续 phase 需要更细的注入 | `CODE_ORGANIZATION.md`, `INVARIANTS.md` |
| **LTO-6** | Knowledge Plane Facade Solidification(已闭合) | **已完成,merge `883e2a9 Knowledge Plane Facade Solidification`**(2026-05-04)。`knowledge_plane.py` 从 50 名透传 barrel file 升级为 ~70 个 functional facade wrapper(domain 命名 + 包装 body,非 re-export);6 个 `_internal_*` 模块在同一 package 内 rename(`_internal_canonical_registry` / `_internal_staged_knowledge` / `_internal_knowledge_store` / `_internal_knowledge_relations` / `_internal_knowledge_suggestions` / `_internal_ingestion_pipeline`);24 处 application / orchestration / adapters / truth_governance / surface_tools 残余 / tests 直接 reach `knowledge_retrieval.*` 已全部清零;`tests/test_invariant_guards.py` 加 Knowledge Plane public-boundary import guard(rejects `_internal_*` + facade-covered modules + 任意非 facade `knowledge_retrieval.*`);唯一 production 例外 = `surface_tools/librarian_executor.py` import `raw_material.py`(显式 allowlist) | 无 — 已闭合。Review concern C1(`render_*` / `build_*` 配对别名 ~14 处)记为非阻塞 follow-up,可选清理 | `KNOWLEDGE.md`, `CODE_ORGANIZATION.md` |
| **LTO-13** | FastAPI Local Web UI Write Surface | **已完成,v1.7.0 tagged**(merge `4ea7a9d`,tag `2156d4a`)。task lifecycle / staged knowledge promote-reject / proposal review-apply 路由全部走 `application/commands/*`;Pydantic request + response envelope;`Depends` + 集中 `@app.exception_handler`;loopback-only serve guard;UI 通过 backend `action_eligibility` 决定按钮可见性 | 无 — 已闭合。后续相关工作分裂为 §三 中的 D5 / D4 Phase A 独立 phase,以及 deferred 项(fire-and-poll background runner、Web UX for staged-knowledge force、文件上传、route policy admin write controls) | `INTERACTION.md §4.2.3`, `CODE_ORGANIZATION.md §3` |

### 簇 C:子系统解耦四金刚(已归档)

LTO-7 / LTO-8(Step 1+Step 2)/ LTO-9(Step 1+Step 2)/ LTO-10 全部完成,v1.6.0 tagged 标记 cluster closure(`0e6215a`)。每条 LTO 各自独立 phase / closeout / merge 已落定,**详情见 git log 与 `docs/plans/<phase>/closeout.md`**;本 roadmap 不再维护 step 级历史。

四条 LTO 触及的 invariant 边界(Provider Router → Path A/C;Orchestration → Control;CLI → application/commands;Governance → Truth write)已在簇 C phase 期间稳定;后续动作仅在真实痛点触发时通过新 phase / 偏离修复(D1-D6)进入,而非作为簇 C 接续。

### 簇 D:远端 / 休眠

| ID | 长期目标 | 当前状态 | 下一类增量 | 工程锚点 |
|----|----------|----------|------------|----------------|
| **LTO-11** | Planner / DAG / Strategy Router | 当前编排可用;Planner / DAG / Strategy Router 未一等化 | 等 Orchestration lifecycle 或真实编排瓶颈后再推进 Planner interface / DAG dependency / Strategy Router observability | `ORCHESTRATION.md` |
| **LTO-12** | Long-horizon Runtime / Sync | 当前不投入:local-first single-user 为实现选择,远期保留 multi-actor / sync / object storage 扩展空间 | 仅由真实跨设备/团队/remote worker 需求触发;不在当前 architecture branch 中顺手做 | future; `INVARIANTS.md §7` |

---

## 三、近期 Phase Tickets

近期队列只放下一两个可执行 ticket。Ticket 完成后移出本节,它的后续增量回到上面的长期目标(已完成 ticket 不在此重复留底,见 git log)。

D5 Adapter Discipline + D4 Phase A + LTO-6 Knowledge Plane Facade Solidification 已落地(2026-05-03 → 2026-05-04;commits `d67c2ad` `7450953` `883e2a9`)。当前阶段 = **激活 LTO-1 Wiki Compiler 第一阶段**,首次落地 LLM-内编译能力(raw_material → staged wiki/canonical 草稿)+ Web Control Center 知识浏览视图。

**v1.8.0 节点目标**:LTO-1 Wiki Compiler 第一阶段落地后 cut(用户可观察的 LLM-内编译能力增量,类似 LTO-13 → v1.7.0)。

**LTO-1 phase 起草前必读**(已 merge,可直接引用):
- `docs/design/EXECUTOR_REGISTRY.md §1.2 Wiki Compiler` 五元组 + 4 模式表(draft / refine-supersede / refine-refines / refresh-evidence)+ Conflict 决策段
- `docs/design/SELF_EVOLUTION.md §2 mermaid + §4.2` 起草侧 / 守门侧 / 共同收口 + Operator 决策点
- `docs/engineering/ADAPTER_DISCIPLINE.md` 6 条规则 + 强制模块布局(M2-M4 Web 实现锚点)
- `docs/engineering/ARCHITECTURE_DECISIONS.md` Hexagonal 身份 + D1-D6 偏离地图
- `docs/design/KNOWLEDGE.md §A` 反模式清单(`Unversioned Evidence Rebuild` 是 M5 guard 的 worked example)

| 优先级 | Ticket | 对应长期目标 | 状态 / Gate | 默认下一步 |
|--------|--------|--------------|-------------|------------|
| 当前 | **LTO-1 Wiki Compiler 第一阶段**(authoring specialist + Knowledge Browse) | LTO-1 | 设计文档先行已 merge;LTO-6 prerequisite 就绪;待 Codex 启动 phase plan | M1:Wiki Compiler 起草核心(3 命令 + prompt pack + source pack + rationale + conflict_flag,4 模式语义 authoritative);M2:Knowledge browse 路由(`GET /api/knowledge/{wiki,canonical,staged}`);M3:Knowledge detail + relations(`GET /api/knowledge/{id}` + `GET /api/knowledge/{id}/relations`,Pydantic envelope 含 supersedes/refines/contradicts/refers_to/derived_from);M4:Web UI Knowledge panel(标签页 + 列表 + 详情 + 邻接 relations,遵循 ADAPTER_DISCIPLINE 6 条);M5:Guard(Wiki Compiler `truth_writes` 不含 canonical;`refresh-evidence` 必须更新 `parser_version`)。落地后 cut **v1.8.0** |
| 触面顺手 | **D4 Phase B / Phase C** —— `surface_tools/` 残余文件搬迁 | 工程纪律 / 接口边界 | 不预先立 phase;在 LTO-1 / Wiki Compiler 触动相关文件时**顺手**做 | Phase B:`surface_tools/{consistency_audit,meta_optimizer,doctor,librarian_executor,...}.py` 中明确属 application service 的 → `application/services/`;Phase C:`surface_tools/{paths,workspace}.py` → `application/infrastructure/` |
| 触面顺手 | **LTO-6 review C1 follow-up** | LTO-6 | 非阻塞 cleanup,~50 行 diff | 删除 `knowledge_plane.py` 中 ~14 处 `render_*` / `build_*` 配对别名,每对保留一个(`render_*` 用于报告渲染,`build_*` 用于对象构造);可在 LTO-1 phase 内顺手做或单独小 commit |

**未列入近期队列(deferred)**:
- **LTO-2** —— retrieval quality 痛点触发(eval hardening / bounded excerpt / wiki compiler integration);LTO-1 落地后会触发部分(wiki compiler integration)。
- **LTO-4** —— 测试隔离痛点触发(touched-surface test split / builders / collect-only gate)。
- **D2 LTO-5 Driven Ports Rollout** —— 等真实 port 需求触发(测试隔离 / second adapter / 注入复杂度提升)。
- **D6 HTTP Client Port** —— D2 第一个 port 落定后做,作为 D2 子项。
- **D3 Orchestrator God Object 拆分** —— 等 D2 部分落定后做,巨大 phase。
- **Wiki Compiler 视图 3(项目级全图谱可视化)**—— 当前 wiki 节点量(~10s)在全图谱不友好区间;违反 LTO-13 §M3 "no new frontend package, build step, or asset pipeline";Wiki Compiler 第一阶段落地后视真实需求或 Graph RAG 远期方向(`KNOWLEDGE.md §9`)再评估。
- LTO-13 的 fire-and-poll background runner、staged-knowledge force Web UX、文件上传、route policy admin write —— 真实需求触发再开 phase。

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

---

## 五、推荐顺序

**Retrieval 第一阶段(done) → Architecture first branch(done) → 簇 C 四金刚(done;v1.6.0) → LTO-13 FastAPI Local Web UI(done;v1.7.0) → D5 Adapter Discipline + D4 Phase A(done) → LTO-6 Knowledge Plane Facade Solidification(done) → LTO-1 Wiki Compiler 第一阶段(下一启动;v1.8.0) → 后续视真实需求(LTO-2 / LTO-4 / D2 LTO-5 driven ports)**

簇 C 四金刚的内部排序与每条 LTO 的逐步骤理由已归档,详情见 git log 与 `docs/plans/<phase>/closeout.md`。

### 近期 phase 顺序

| 顺位 | Phase | 选这个位置的理由 |
|------|-------|------------------|
| 当前 | **LTO-1 Wiki Compiler 第一阶段** | LTO-6 facade 已收口(`883e2a9`),Wiki Compiler 硬 prerequisite 已就绪。Wiki Compiler 是 5th specialist(authoring 角色,与 Librarian governance 角色形成上下游关系),4 模式语义(draft / refine-supersede / refine-refines / refresh-evidence)已在 EXECUTOR_REGISTRY + SELF_EVOLUTION 落定。Web Control Center 加 Knowledge Browse 视图(视图 1+2)与 Wiki Compiler 是孪生设计(产出有地方看,Operator review 不盲决策),并入同一 phase 的 M2-M4。落地后 cut **v1.8.0** tag(类似 LTO-13 → v1.7.0 关系) |
| 触面顺手 | **D4 Phase B / Phase C** | `surface_tools/` 残余文件搬到 `application/services/` + `application/infrastructure/`;LTO-1 触动相关 application service 文件时**顺手**做,不预先立 phase |
| 触面顺手 | **LTO-6 review C1 follow-up** | `knowledge_plane.py` ~14 处 `render_*` / `build_*` 配对别名清理,~50 行 cleanup;LTO-1 Wiki Compiler M1 起草命令时如触动 facade 顺手做,或单独小 commit |

### 跨阶段排序依据

1. **D5 / D4 Phase A / LTO-6 已落地**(2026-05-03 → 2026-05-04;commits `d67c2ad` `7450953` `883e2a9`):工程纪律编纂 + adapter 命名标准化 + Knowledge Plane facade 收口三件事顺序完成,LTO-13 audit Round 1-3 暴露的 14 项 concerns 全部归档为 `ADAPTER_DISCIPLINE.md` worked examples;`knowledge_plane.py` 从 50 名 barrel 升级为 ~70 个 functional facade。
2. **LTO-1 Wiki Compiler 是 v1.8.0 节点**:首次 LLM-内编译能力增量(raw material → wiki/canonical 草稿),用户可观察。设计文档(EXECUTOR_REGISTRY 5 specialist + 4 mode + SELF_EVOLUTION §2/§4.2)已先行 merge 到 main,phase plan 起草时直接引用。Web Control Center 视图 1+2 并入,让 Wiki Compiler 产出的 `relation_metadata`(supersedes / refines / contradicts / refers_to / derived_from)有 Operator 审核界面,避免盲决策。
3. **D2 / LTO-5 driven ports + D6 HTTP client port + D3 orchestrator decomposition**:都属于"等真实需求触发"区。D2 触发条件 = 测试隔离 / 第二个 adapter 实现 / 注入复杂度提升;D6 必须在 D2 第一个 port 落定后做;D3 必须在 D2 部分落定后做。三者均为大 phase,不预先排日程。
4. **LTO-2 retrieval quality 部分由 LTO-1 触发**:`wiki compiler integration` 增量本身归 LTO-2,但落地于 LTO-1 phase 内(M3 relations + retrieval 召回返回带 supersedes / refines 的 wiki entry,通过 relation expansion 一并返回)。bounded excerpt / eval hardening / report UX polish 仍 deferred。
5. **后续视真实需求**:LTO-4 由测试隔离痛点触发;LTO-2 剩余项由 retrieval quality 痛点触发;Wiki Compiler 视图 3(全图谱)与 Graph RAG 远期方向同步,真实需求触发再做。

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
