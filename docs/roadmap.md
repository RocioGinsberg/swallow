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
| **当前重构状态** | Architecture Recomposition first branch 已进入 closeout gate:helper seed、Knowledge Plane facade、narrow Control Center query pilot 已完成到 branch;当前应 closeout / PR / 选择下一个 subtrack,不要继续隐式扩张 |

---

## 二、长期优化目标

这些是跨 phase 的长期目标。一次 phase 只推进其中一个可审查增量,不会让目标本身消失。

| ID | 长期目标 | 当前状态 | 下一类增量 | 工程锚点 |
|----|----------|----------|------------|----------------|
| **LTO-1** | Knowledge Authoring / LLM Wiki Compiler | `note` / ingest / promote 管线可用;还没有 raw material → staged wiki/canonical draft 的 LLM 编译层 | 显式 `draft-wiki` / `refine-wiki`;source pack、rationale、conflict flags、review-promote gate | `KNOWLEDGE.md`, `SELF_EVOLUTION.md` |
| **LTO-2** | Retrieval Quality / Evidence Serving | Retrieval U-T-Y 第一阶段完成:trace、dedicated rerank、source policy、EvidencePack view、source pointers、summary boundary | bounded excerpt、conflict flags、eval hardening、wiki compiler integration、report UX polish | `KNOWLEDGE.md`, `HARNESS.md` |
| **LTO-3** | Architecture Recomposition Program | Program plan 存在;first branch 完成 helper seed、Knowledge Plane facade、narrow Control Center query pilot;后续 subtrack 需单独 gate | closeout / PR;再选择 Provider Router、Orchestration、Surface、Governance 或 broad test/application/knowledge follow-up | `docs/plans/architecture-recomposition/plan.md` |
| **LTO-4** | Test Architecture / TDD Harness | 已有 `tests/helpers` seed 与首批 layered tests;root tests 与 `test_cli.py` 仍偏聚合 | touched-surface test split、builders/assertions、guard helper 收敛、collect-only + full pytest gate | `docs/engineering/TEST_ARCHITECTURE.md` |
| **LTO-5** | Interface / Application Boundary | Control Center read-only query pilot 已完成;CLI/FastAPI/write commands/repository ports 尚未系统收口 | application commands、CLI/FastAPI adapters、HTTP route schemas、local SQLite repository ports | `INTERACTION.md`, `CODE_ORGANIZATION.md` |
| **LTO-6** | Knowledge Plane API Simplification | `knowledge_plane.py` facade 已添加并迁移少量上层 imports;内部命名和更广调用面仍未完成 | touched-callsite facade migration、内部 lifecycle/projection 命名整理 | `KNOWLEDGE.md`, `CODE_ORGANIZATION.md` |
| **LTO-7** | Provider Router Maintainability | `router.py` 仍承载 registry / policy / metadata / selection / completion / reports | 保留 `router.py` facade,拆 registry / policy / metadata store / selection / completion gateway | `PROVIDER_ROUTER.md` |
| **LTO-8** | Orchestration Lifecycle Decomposition | `orchestrator.py` / `harness.py` / `executor.py` 仍是主复杂面;Control boundary 稳定 | task lifecycle、execution attempts、subtask flow、retrieval/knowledge flow helpers;不得转移 Control 权限 | `ORCHESTRATION.md`, `HARNESS.md` |
| **LTO-9** | Surface / Meta Optimizer Modularity | Summary route boundary 已澄清;CLI / meta optimizer 文件仍偏聚合 | CLI command family split、proposal lifecycle modules、report/parser alignment | `INTERACTION.md`, `SELF_EVOLUTION.md` |
| **LTO-10** | Governance Apply Handler Maintainability | `apply_proposal` 唯一入口稳定;私有 canonical / route / policy apply 分支可读性继续下降 | 私有 handler 模块化、transaction envelope、audit/outbox helpers;不暴露新 public mutation entry | `INVARIANTS.md`, `DATA_MODEL.md` |
| **LTO-11** | Planner / DAG / Strategy Router | 当前编排可用;Planner / DAG / Strategy Router 未一等化 | 等 Orchestration lifecycle 或真实编排瓶颈后再推进 Planner interface / DAG dependency / Strategy Router observability | `ORCHESTRATION.md` |
| **LTO-12** | Long-horizon Runtime / Sync | 当前不投入:local-first single-user 为实现选择,远期保留 multi-actor / sync / object storage 扩展空间 | 仅由真实跨设备/团队/remote worker 需求触发;不在当前 architecture branch 中顺手做 | future; `INVARIANTS.md §7` |

---

## 三、近期 Phase Tickets

近期队列只放下一两个可执行 ticket。Ticket 完成后移出本节,它的后续增量回到上面的长期目标。

| 优先级 | Ticket | 对应长期目标 | 状态 / Gate | 默认下一步 |
|--------|--------|--------------|-------------|------------|
| 当前 | **Architecture Recomposition first-branch closeout / PR** | LTO-3 / LTO-4 / LTO-5 / LTO-6 | `feat/architecture-recomposition-ad1-v`;代码已完成,文档已补 scope/gate | 写 closeout / PR material;Human review / PR / merge |
| 下一选择 | **Provider Router split or Orchestration lifecycle split** | LTO-7 或 LTO-8 | 当前 branch merge 后再选;不在当前 branch 继续实现 | 以真实维护痛点决定下一轮 phase |
| 后续选择 | **Broad test / application / knowledge follow-up** | LTO-4 / LTO-5 / LTO-6 | first branch 只完成 seed/pilot;不视为 broad completion | 按 touched surface 继续迁移,避免一次性大搬迁 |
| 后续选择 | **Wiki Compiler draft workflow** | LTO-1 / LTO-2 | Architecture 地基稳定后再启动 | 先设计 prompt pack / staged draft / review gate |

---

## 四、命名规则

旧编号不再作为 roadmap 导航语义使用。

- 已经完成或归档的旧编号不再在近期队列里反复出现。
- 如果旧编号覆盖的方向还有长期增量,状态归入 `LTO-*`。
- 新 phase 应写成“推进哪个 LTO 的哪个增量”,例如:
  - `feat/provider-router-split` → 推进 `LTO-7`
  - `feat/wiki-compiler-draft` → 推进 `LTO-1`
  - `feat/test-architecture-cli-split` → 推进 `LTO-4`
- 不再用“某个旧编号没完成所以继续叫同一个编号”来表示长期未完成;这会让 roadmap 读起来像永远半完成。

---

## 五、推荐顺序

**Retrieval quality baseline(done) → Architecture first branch(done) → closeout/PR → selected architecture subtrack → Wiki Compiler → Planner/DAG**

排序依据:

1. **Retrieval 第一阶段已闭环**:trace、EvidencePack/source pointer、summary boundary 已进入 baseline;后续增量归入 LTO-2。
2. **Architecture first branch 应先收口**:helper seed、Knowledge Plane facade、Control Center query pilot 已足够构成一轮 reviewable PR。
3. **下一个重构 subtrack 需要重新 gate**:Provider Router、Orchestration、Surface、Governance 都不应靠 program plan 隐式进入实现。
4. **Wiki Compiler 后置**:LLM Wiki Compiler 依赖 architecture/test/knowledge facade 地基更稳定。
5. **Planner / DAG 最后**:Planner / DAG / Strategy Router 依赖 orchestration 主链路整理,回滚成本高。

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
