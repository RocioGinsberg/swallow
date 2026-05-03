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
| **Agent 体系** | 4 Specialist + 2 Validator 独立生命周期已落地;具体品牌绑定见 `docs/design/EXECUTOR_REGISTRY.md` |
| **当前重构状态** | **簇 C 已归档 + LTO-13 接口边界首次落地**:LTO-7/8/9/10 全部完成(详情见 git log + closeouts);LTO-13 FastAPI Local Web UI Write Surface 已 merge(`4ea7a9d`)并打 tag **`v1.7.0`** at `2156d4a`,首次产出 LLM-外可观察的写表面(task lifecycle / staged knowledge / proposal review-apply)。下一启动:Adapter Discipline Codification → Adapter Boundary Cleanup Phase A → Knowledge Plane Facade Solidification(=LTO-6 主动化)。 |
| **架构身份** | 项目事实上的架构 = **Hexagonal (Ports & Adapters)**;driving adapters = `surface_tools/{cli,web}/`(D4 Phase A 后将重命名为 `adapters/{cli,http}/`);application layer = `application/{commands,queries}/`;domain / control plane = `orchestration/` + `knowledge_retrieval/` + `truth_governance/` + `provider_router/`;driven adapters / infrastructure = `truth_governance/sqlite_store.py` + `provider_router/completion_gateway.py` + `_io_helpers.py` 等。已识别 6 项偏离(D1–D6),修复路径见 §五。 |
| **工程纪律** | 长期编码 / 重构遵循 `docs/engineering/CODE_ORGANIZATION.md`(分层 / facade-first / migration discipline)+ `docs/engineering/GOF_PATTERN_ALIGNMENT.md`(facade / strategy / repository / adapter / value object / state / pipeline 等 pattern 仅作为 responsibility language)+ `docs/engineering/TEST_ARCHITECTURE.md`(分层测试 / TDD harness)+ 即将提交的 `docs/engineering/ARCHITECTURE_DECISIONS.md`(架构身份 = Hexagonal、当前已用模式清单 + 已识别 6 项偏离 D1-D6 的修复路径)+ `docs/engineering/ADAPTER_DISCIPLINE.md`(LTO-13 audit 教训编纂的 adapter 实施纪律,6 条规则 + 强制模块布局 + 16 项 worked examples)。LTO-13 R3 audit 暴露的 framework-rejection 系统性问题已由 D5 Adapter Discipline Codification phase 编纂为 `ADAPTER_DISCIPLINE.md`,后续每个 adapter phase(D4 Phase A 等)起草前必读。 |

---

## 二、长期优化目标

这些是跨 phase 的长期目标。一次 phase 只推进其中一个可审查增量,不会让目标本身消失。

12 条 LTO 不是平等并列(编号 LTO-3 已归档不复用),按推进性质分 **4 簇**:

- **簇 A 产品 / 知识能力**(LTO-1, LTO-2):沿现有架构垂直推进的产品级能力。LTO-2 第一阶段已闭环,LTO-1 等地基。
- **簇 B 架构重构 + 接口边界 + 工程纪律**(LTO-4, LTO-5, LTO-6, LTO-13):seed 来自 first branch,通过 LTO-13 接口边界落地后扩展为含工程纪律的活跃簇。LTO-13 已完成(v1.7.0 tagged)。LTO-5 已重定义为 **Driven Ports Rollout**(N phases,首推 `TaskStorePort`),按需主动推进。LTO-6 已重定义为 **Knowledge Plane Facade Solidification**(主动收口),修复 `knowledge_plane.py` 50 名透传 barrel-file 形态。新增的工程纪律收口动作(D5 Adapter Discipline、D4 Adapter Boundary Cleanup)以独立 phase 形式出现在 §三 队列,不取 LTO 编号。(LTO-3 已归档,见 §四。)
- **簇 C 子系统解耦四金刚**(LTO-7, LTO-8, LTO-9, LTO-10):**已归档**;详情见 git log 与各自 `docs/plans/<phase>/closeout.md`。
- **簇 D 远端 / 休眠**(LTO-11, LTO-12):默认不投入,仅由真实需求触发。

下面分簇展开。

### 簇 A:产品 / 知识能力(沿现有架构垂直推进)

| ID | 长期目标 | 当前状态 | 下一类增量 | 工程锚点 |
|----|----------|----------|------------|----------------|
| **LTO-1** | Knowledge Authoring / LLM Wiki Compiler | `note` / ingest / promote 管线可用;还没有 raw material → staged wiki/canonical draft 的 LLM 编译层 | 显式 `draft-wiki` / `refine-wiki`;source pack、rationale、conflict flags、review-promote gate | `KNOWLEDGE.md`, `SELF_EVOLUTION.md` |
| **LTO-2** | Retrieval Quality / Evidence Serving | Retrieval U-T-Y 第一阶段完成:trace、dedicated rerank、source policy、EvidencePack view、source pointers、summary boundary | bounded excerpt、conflict flags、eval hardening、wiki compiler integration、report UX polish | `KNOWLEDGE.md`, `HARNESS.md` |

### 簇 B:架构重构 + 接口边界 + 工程纪律(活跃推进)

| ID | 长期目标 | 当前状态 | 下一类增量 | 工程锚点 |
|----|----------|----------|------------|----------------|
| **LTO-4** | Test Architecture / TDD Harness | 已有 `tests/helpers` seed 与首批 layered tests;root tests 与 `test_cli.py` 仍偏聚合 | touched-surface test split、builders/assertions、guard helper 收敛、collect-only + full pytest gate | `docs/engineering/TEST_ARCHITECTURE.md` |
| **LTO-5** | Driven Ports Rollout(formerly Repository / Persistence Ports) | `truth_governance/{store.py, sqlite_store.py, truth/}` 已是 repository facade 风格,有 `TaskStoreProtocol` 但 application 层不通过它访问;application 直接 import 具体实现(orchestrator/knowledge_retrieval/truth_governance/provider_router) | N-phase rollout:`application/ports/` 显式定义 `OrchestratorPort` / `KnowledgePort` / `ProposalPort` / `ProviderRouterPort` / `TaskStorePort` / `HttpClientPort` 等;每个 phase 落一个 port。HTTP client port(D6)依赖第一个 port 落定后再做。**触发条件**:测试需要 mock application boundary、添加 second adapter 实现、或后续 phase 需要更细的注入 | `CODE_ORGANIZATION.md`, `INVARIANTS.md` |
| **LTO-6** | Knowledge Plane Facade Solidification(主动收口) | `knowledge_plane.py` 当前是 98 行 50 名透传 barrel file(0 个 `def` / `class`),无自有领域语言;**实测 24 个文件**直接绕过 facade reach `knowledge_retrieval.*` 子模块(application 5、orchestration 7、provider_router 2、surface_tools 4、adapters 2、truth_governance 3,加测试若干);仅 3 个 `truth_governance/` 文件用 facade | **从 touched-surface 慢推改为主动 phase + Functional facade 形态 + 一次清**(2026-05-03 Plan Gate 决议):重写 `knowledge_plane.py` 为 6-10 个领域函数(模块级,不引入 class + DI,留给未来 LTO-5 D2 升级);24 处直接绕过的 import 全部一次切换;`knowledge_retrieval/` 6 个子模块加 `_internal_` 前缀或迁入 `internals/` 子包;扩展 guard test 防止再绕开。Wiki Compiler(LTO-1)的硬 prerequisite | `KNOWLEDGE.md`, `CODE_ORGANIZATION.md` |
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

D4 Phase A + D5 Adapter Discipline 已落地(2026-05-03;commits `d67c2ad` `7450953`)。当前阶段 = **激活 LTO-6 主动 facade 化**,作为 Wiki Compiler(LTO-1)启动前的硬 prerequisite —— 否则 Wiki Compiler 会进一步扩大 `knowledge_retrieval.*` 直接调用面。

**v1.8.0 节点目标**:Wiki Compiler 第一阶段落地后 cut(用户可观察的 LLM-内编译能力增量)。LTO-6 + 任何 D4 Phase B/C 触面 follow-up 都是为 Wiki Compiler 铺路的 plumbing,不单独 cut tag。

| 优先级 | Ticket | 对应长期目标 | 状态 / Gate | 默认下一步 |
|--------|--------|--------------|-------------|------------|
| 当前 | **LTO-6 Knowledge Plane Facade Solidification**(D1 active 化) | LTO-6 | 下一启动;**Functional facade + 一次清**(Plan Gate 决议 2026-05-03) | (1) `knowledge_plane.py` 从 50 re-export barrel 升级为 6-10 个领域函数(`submit_staged` / `promote` / `reject` / `load_task_view` / `persist_task_view` / `search` / `record_decision` 等),保持 module-level `from ... import` 调用形态(不引入 class + DI,留给未来 LTO-5 D2 升级);(2) **24 个直接绕过 facade 的文件全部切换 import 路径**(application/{commands,queries,services} 5 个、orchestration 7 个、provider_router 2 个、surface_tools 4 个、adapters 2 个、truth_governance 3 个、tests 若干);(3) `knowledge_retrieval/` 内 6 个子模块(`canonical_registry / staged_knowledge / knowledge_store / knowledge_relations / ingestion.pipeline / knowledge_suggestions`)加 `_internal_` 前缀或迁入 `internals/` 子包;(4) 扩展 `tests/test_invariant_guards.py` 增加"非 knowledge_plane 模块不许 import knowledge_retrieval._internal_*"guard;(5) 新增/更新测试覆盖每个 facade 函数;(6) 跑 full pytest + compileall + diff hygiene |
| 紧随 | **Wiki Compiler 第一阶段**(LTO-1) | LTO-1 | LTO-6 落地后启动;独立 phase | 设计 prompt pack(raw material → wiki/canonical draft);staged review-promote gate;source pack + rationale + conflict flags;调用面**只走 LTO-6 facade**,无新增 `knowledge_retrieval._internal_*` 直接 import |
| 候选(touched-surface)| **D4 Phase B / Phase C** —— `surface_tools/` 残余文件搬迁 | 工程纪律 / 接口边界 | 不预先立 phase;在 LTO-6 / Wiki Compiler 触动相关文件时**顺手**做 | Phase B:`surface_tools/{consistency_audit,meta_optimizer,doctor,...}.py` 中明确属 application service 的 → `application/services/`;Phase C:`surface_tools/{paths,workspace}.py` → `application/infrastructure/` |

**未列入近期队列(deferred)**:
- **LTO-2 / LTO-4** —— 真实痛点(retrieval quality / 测试隔离)触发再启动。
- **D2 LTO-5 Driven Ports Rollout** —— 等真实 port 需求触发(测试隔离 / second adapter / 注入复杂度提升)。
- **D6 HTTP Client Port** —— D2 第一个 port 落定后做,作为 D2 子项。
- **D3 Orchestrator God Object 拆分** —— 等 D2 部分落定后做,巨大 phase。
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

**Retrieval 第一阶段(done) → Architecture first branch(done) → 簇 C 四金刚(done;v1.6.0) → LTO-13 FastAPI Local Web UI(done;v1.7.0) → D5 Adapter Discipline + D4 Phase A(done) → LTO-6 Knowledge Plane Facade Solidification → Wiki Compiler 第一阶段(LTO-1;v1.8.0) → 后续视真实需求(LTO-4 / LTO-2 / D2 LTO-5 driven ports)**

簇 C 四金刚的内部排序与每条 LTO 的逐步骤理由已归档,详情见 git log 与 `docs/plans/<phase>/closeout.md`。

### 近期 phase 顺序

| 顺位 | Phase | 选这个位置的理由 |
|------|-------|------------------|
| 当前 | **LTO-6 Knowledge Plane Facade Solidification** | 现存 24 个文件直接绕过 facade 直 reach `knowledge_retrieval.*`(remediation 量比 ADR 当初估算高 2x);Functional facade + 一次清形态由 Plan Gate 决议确定;**Wiki Compiler 的硬 prerequisite**(否则 Wiki Compiler 又往 barrel 上加堆叠)。本期不引入 class facade / DI 容器(留给未来 LTO-5 D2),保持 module-level `from ... import` 调用形态以最小化 phase 复杂度 |
| 紧随 | **Wiki Compiler 第一阶段(LTO-1)** | LTO-6 落地后启动;首次 LLM-内编译能力增量(raw material → staged wiki/canonical draft);用户可观察。此 phase 落地后 cut **v1.8.0** tag |
| 触面顺手 | **D4 Phase B / Phase C** | `surface_tools/` 残余文件搬到 `application/services/` + `application/infrastructure/`;LTO-6 / Wiki Compiler 触动相关文件时**顺手**做,不预先立 phase |

### 跨阶段排序依据

1. **D5 / D4 Phase A 已落地**(2026-05-03;commits `d67c2ad` `7450953`):工程纪律编纂 + adapter 命名标准化完成,LTO-13 audit Round 1-3 暴露的 14 项 concerns 全部归档为 `ADAPTER_DISCIPLINE.md` worked examples。
2. **LTO-6 紧随其后,且必须在 Wiki Compiler 之前**:`knowledge_plane.py` barrel-file 形态被 24 个文件绕过;Wiki Compiler 实施时会大量调用 knowledge layer,如不先收口,扩大调用面后再迁移成本翻倍。
3. **Wiki Compiler 是 v1.8.0 节点**:LTO-6 + 任何 D4 Phase B/C 触面 follow-up 都是 plumbing,用户不可见;Wiki Compiler 第一阶段落地是首个用户可观察的能力增量,值得 cut tag(类似 LTO-13 → v1.7.0 的关系)。
4. **D2 / LTO-5 driven ports + D6 HTTP client port + D3 orchestrator decomposition**:都属于"等真实需求触发"区。D2 触发条件 = 测试隔离 / 第二个 adapter 实现 / 注入复杂度提升;D6 必须在 D2 第一个 port 落定后做;D3 必须在 D2 部分落定后做。三者均为大 phase,不预先排日程。
5. **后续视真实需求**:LTO-4 由测试隔离痛点触发;LTO-2 由 retrieval quality 痛点触发。

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
