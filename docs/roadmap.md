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
| **当前重构状态** | **簇 C 四金刚 LTO-7/8/9/10 第一遍已完成;LTO-9 Step 2 已完全终结;簇 C 只剩 LTO-8 Step 2 作为终结 phase**。LTO-7 Provider Router facade 化、LTO-8 Step 1 orchestrator.py 6 个聚焦模块化、LTO-9 Step 1 CLI / Meta-Optimizer 拆分、LTO-9 Step 2 广泛 CLI 命令族迁移 + LTO-5 应用边界完成、LTO-10 governance apply handler 模块化。LTO-9 Step 2 顺带完成 application/commands 写命令完整化(原 LTO-5 应用边界部分)。LTO-5 重定义为 Repository / Persistence Ports 并默认 defer。FastAPI 写路由从 LTO-5 拆出为新 LTO-13,簇 C 终结后启动。下一阶段:LTO-8 Step 2(`harness.py` 拆分,含 event-kind allowlist 新设计点)。 |
| **工程纪律** | 长期编码 / 重构遵循 `docs/engineering/CODE_ORGANIZATION.md`(分层 / facade-first / migration discipline)+ `docs/engineering/GOF_PATTERN_ALIGNMENT.md`(facade / strategy / repository / adapter / value object / state / pipeline 等 pattern 仅作为 responsibility language)+ `docs/engineering/TEST_ARCHITECTURE.md`(分层测试 / TDD harness) |

---

## 二、长期优化目标

这些是跨 phase 的长期目标。一次 phase 只推进其中一个可审查增量,不会让目标本身消失。

12 条 LTO 不是平等并列(编号 LTO-3 已归档不复用),按推进性质分 **4 簇**:

- **簇 A 产品 / 知识能力**(LTO-1, LTO-2):沿现有架构垂直推进的产品级能力。LTO-2 第一阶段已闭环,LTO-1 等地基。
- **簇 B 架构重构已开头 seed**(LTO-4, LTO-5, LTO-6):已被 first branch 开了 seed,后续靠簇 C 各 subtrack phase 自然带动。LTO-5 已重定义为 Repository / Persistence Ports 并默认 defer。(LTO-3 已归档,见 §四。)
- **簇 C 子系统解耦四金刚 + 接续**(LTO-7, LTO-8, LTO-9, LTO-10 + 接续 LTO-13):**当前阶段主战场**;LTO-7/9/10 已完成,LTO-8 Step 2 是最后一个金刚 phase,LTO-13 FastAPI 写路由作为簇 C 终结后的接续。每条独立一个 phase / 一条分支,不允许合并到一个 PR。
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
| **LTO-5** | Repository / Persistence Ports | 当前 `truth_governance/{store.py, sqlite_store.py, truth/}` 已是 repository facade 风格,但缺 `ports.py` interface 抽象;application 层直接依赖具体实现。Application/commands 与 application/queries 已由 LTO-9 Step 1 / Step 2 完成。 | 仅由真实需求触发(多 storage backend / test isolation 复杂化 / 远程 sync 评估)。目标形状见 `CODE_ORGANIZATION.md §4` 的 `truth_governance/repositories/{ports,default_store,file_store}.py` + `truth_governance/sqlite/*.py`。 | `CODE_ORGANIZATION.md`, `INVARIANTS.md` |
| **LTO-6** | Knowledge Plane API Simplification | `knowledge_plane.py` facade 已添加并迁移少量上层 imports;内部命名和更广调用面仍未完成 | touched-callsite facade migration、内部 lifecycle/projection 命名整理 | `KNOWLEDGE.md`, `CODE_ORGANIZATION.md` |

### 簇 C:子系统解耦四金刚 + 接续(下一阶段主战场)

每条独立一个 phase / 一条分支,顺序见 §五。

每个 subtrack 实际推进时使用的 pattern vocabulary(facade / strategy / repository / adapter / value object / state / pipeline 等)见 `docs/engineering/GOF_PATTERN_ALIGNMENT.md §3`;不允许"为模式而模式"。

| ID | 长期目标 | 当前状态 | 下一类增量 | 工程锚点 |
|----|----------|----------|------------|----------------|
| **LTO-7** | Provider Router Maintainability | `router.py` 现为 6 个聚焦模块上的 facade:registry / policy / metadata-store / selection / completion-gateway / reports;Path A/C 边界清晰,不依赖 orchestration.executor。**LTO-9 Step 1 消化 CONCERN-1**:route metadata guard allowlist 现明确指定 `provider_router/route_metadata_store.py` 为物理写入者,`router.py` 仅作为 legacy compatibility facade,加入正向断言保证导入路径一致性。| 可选 touched-surface caller 直接导入聚焦模块代替 `router.py`;CONCERN-2 / CONCERN-3(私有名字泄露、fallback 所有权)记录在 `docs/concerns_backlog.md` 并保持开放,仅在相关表面被修改时合并 | `PROVIDER_ROUTER.md` |
| **LTO-8** | Orchestration Lifecycle Decomposition | **Step 1 已完成,Step 2 待启动**。Step 1:`orchestrator.py` 抽出 6 个聚焦模块(`task_lifecycle / retrieval_flow / artifact_writer / subtask_flow / execution_attempts / knowledge_flow`),Control Plane authority 保留在 `orchestrator.py`;facade 减重 ~14%(3853 → 3331)。`harness.py`(2077 行)含 9 个 sequential `append_event` callsite 集中在 `write_task_artifacts`,留作 Step 2。 | Step 2:`harness.py` 分解;further `orchestrator.py` reduction;event-kind allowlist 新设计点(9 个 sequential `append_event` 需 allowlist 决策);debate-loop closure pattern design follow-up(defer to LTO-11) | `ORCHESTRATION.md`, `HARNESS.md` |
| **LTO-9** | Surface / Meta Optimizer Modularity | **已完成**(Step 1 + Step 2)。Step 1:Meta-Optimizer 只读路径拆分为聚焦模块、CLI 命令族适配器提取、application/commands 种子建立。Step 2:CLI 广泛命令族迁移完成(`cli.py` 3653 → 2672 行,-27%;6 个 application command 模块;6 个 CLI adapter 模块;5 个新 integration test 文件;所有 `apply_proposal` 直接调用移出 `cli.py`)。| 无 — LTO-9 已完成。Reviewed Meta-Optimizer 路径在 `apply_route_metadata.py` 内的内部拆分作为 LTO-10 deferred 项已记录,不在 LTO-9 范围。 | `INTERACTION.md`, `SELF_EVOLUTION.md` |
| **LTO-10** | Governance Apply Handler Maintainability | **已完成**:`apply_proposal` 唯一入口稳定;`governance.py` 642 → 45 行 facade;proposal_registry、apply_canonical、apply_policy、apply_route_metadata、apply_outbox 模块化完成;guard allowlist 明确指定。 | 可选:reviewed route metadata 支持内部拆分(若有可读性收益);durable governance outbox persistence(待事件 schema 与消费者落地) | `INVARIANTS.md`, `DATA_MODEL.md` |
| **LTO-13** | FastAPI Local Web UI Write Surface | 当前 `web/api.py` 仅有 read-only `@app.get(...)` 路由(LTO-9 Step 1 M4 收口);写路由模式未引入 | 簇 C 完全终结(LTO-8 Step 2 merge 后)启动;首次引入 write 路由需设计 request body schema、HTTP verb 选择、error mapping、`test_ui_backend_only_calls_governance_functions` guard 扩展;调用同一份 `application/commands/*` 函数,不允许第二条 business 路径 | `INTERACTION.md §4.2.3`, `CODE_ORGANIZATION.md §3` |

### 簇 D:远端 / 休眠

| ID | 长期目标 | 当前状态 | 下一类增量 | 工程锚点 |
|----|----------|----------|------------|----------------|
| **LTO-11** | Planner / DAG / Strategy Router | 当前编排可用;Planner / DAG / Strategy Router 未一等化 | 等 Orchestration lifecycle 或真实编排瓶颈后再推进 Planner interface / DAG dependency / Strategy Router observability | `ORCHESTRATION.md` |
| **LTO-12** | Long-horizon Runtime / Sync | 当前不投入:local-first single-user 为实现选择,远期保留 multi-actor / sync / object storage 扩展空间 | 仅由真实跨设备/团队/remote worker 需求触发;不在当前 architecture branch 中顺手做 | future; `INVARIANTS.md §7` |

---

## 三、近期 Phase Tickets

近期队列只放下一两个可执行 ticket。Ticket 完成后移出本节,它的后续增量回到上面的长期目标。

当前阶段主战场是 **簇 C 终结**:LTO-7/9/10 已完成;LTO-8 Step 2 是最后一个金刚 phase;LTO-13 FastAPI 写路由作为簇 C 终结后的接续。顺序由 §五 给出。不允许将多条簇 C subtrack 合并到同一个 PR。

| 优先级 | Ticket | 对应长期目标 | 状态 / Gate | 默认下一步 |
|--------|--------|--------------|-------------|------------|
| 当前 | **LTO-8 Step 2 — `harness.py` 拆分** | LTO-8 | LTO-9 Step 2 merge 后 | `harness.py` 2077 行 + 进一步 `orchestrator.py` 减重;`write_task_artifacts` 内 9 个 sequential `append_event` 拆分需要 event-kind allowlist 设计(新 invariant 设计点) |
| 下一选择 | **LTO-13 — FastAPI Local Web UI Write Surface** | LTO-13 | 簇 C 完全终结(LTO-8 Step 2 merge)后 | 首次引入 write 路由、request body schema、HTTP verb 选择、error mapping、guard 扩展;调用同一份 `application/commands/*` 函数,不允许第二条 business 路径 |
| 候选 | Wiki Compiler draft workflow / 其他 LTO | LTO-1 / LTO-2 / 其他 | LTO-13 完成后 | 先设计 prompt pack / staged draft / review gate |

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

**v1.6.0 Tag 决策**:待 LTO-8 Step 2 merge 后评估;届时簇 C 真正终结,版本号代表”cluster C closure”的完整信号。

---

## 五、推荐顺序

**Retrieval 第一阶段(done) → Architecture first branch(done) → 簇 C 四金刚(LTO-7 → 8 → 9 → 10)→ LTO-13 FastAPI Local Web UI → Wiki Compiler → Planner/DAG**

### 簇 C 内部顺序与理由

每个 subtrack 在 plan / audit / review 阶段都对照 `docs/engineering/GOF_PATTERN_ALIGNMENT.md` 选择 responsibility language(facade / strategy / repository / adapter / value object / state / pipeline 等);facade-first 与 invariant-preserving 是默认纪律,不是可选项。

| 顺位 | Subtrack | 选这个位置的理由 |
|------|----------|----------|
| 第 1 | **LTO-7 Provider Router**(已完成) | 1422 行单文件,target shape 已在 `CODE_ORGANIZATION §5.2` 画好;Path A/C invariant 边界清晰,blast radius 最小;作为 facade-first 纪律的 warm-up phase 风险最低 |
| 第 2 | **LTO-8 Orchestration lifecycle**(Step 1 已完成,Step 2 待启动) | 痛点最大(orchestrator+harness ~6k 行),但 invariant 敏感度也最高(Control only in Orchestrator / Operator);先靠 LTO-7 把执行肌肉建立起来,再动这块;helper 不可拿到状态推进权。Step 1 完成 6 个编排聚焦模块提取,Step 2 分解 harness.py(含 event-kind allowlist 新设计点) |
| 第 3 | **LTO-9 Surface / CLI / Meta Optimizer**(已完成) | cli.py 3790 + meta_optimizer 1320,以 behavior-preserving 拆分为主;借此同时把 LTO-5(application/commands)从 read-only query pilot 推进到写命令完整化;invariant 敏感度最低。Step 1 + Step 2 完成 Meta-Optimizer 聚焦模块、CLI 命令适配器、application/commands 写命令完整化、Control Center 查询迁移。LTO-9 现已完全终结。 |
| 第 4 | **LTO-10 Governance apply handler**(已完成) | Truth write path 最敏感,放最后;`apply_proposal` 仍是唯一公共 mutation entry;前面三轮巩固 facade-first 纪律后再做手术刀级拆分。完成了私有 handler 模块化与 governance.py facade 化。 |

### 跨阶段排序依据

1. **Retrieval 第一阶段已闭环**:trace、EvidencePack/source pointer、summary boundary 已进入 baseline;后续增量归入 LTO-2,真实使用触发再推进。
2. **Architecture first branch 已 merge**:helper seed、Knowledge Plane facade、Control Center query pilot 提供了 facade-first migration 的样本;后续 subtrack 不能借 program plan 隐式进入实现。
3. **簇 C 四金刚必须独立 phase**:每条都涉及不同 invariant 边界(Provider Router → Path A/C;Orchestration → Control;Governance → Truth write);合并到一个 PR 会让 review gate 同时失效。
4. **LTO-13 FastAPI Local Web UI 后接**:FastAPI 写路由引入在簇 C 完全终结(LTO-8 Step 2)后启动,调用同一份 application/commands 函数,确保 business 路径唯一。
5. **Wiki Compiler 后置**:LLM Wiki Compiler 依赖 LTO-4 / LTO-6 地基稳定后再启动。
6. **Planner / DAG 最后**:依赖 LTO-8 完成,回滚成本高。

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
