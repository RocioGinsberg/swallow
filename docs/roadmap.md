---
author: claude
status: living-document
---

> **Document discipline**
> Owner: Human
> Updater: Codex 主线(差距条目新增 / 推荐队列 / 优先级 / 风险批注 / 战略锚点)+ `roadmap-updater` subagent(phase 完成事实登记 / 已有差距条目状态同步)+ Claude 主线(review / tag 相关轻量风险批注)
> Trigger: phase 收口 OR 会话讨论中浮现新方向 OR phase 拆分 OR Human 请求方向建议
> Anti-scope: 不维护已完成 phase 历史(→ git log + `docs/plans/<phase>/closeout.md`);不维护 tag / release docs 状态(→ `docs/concerns_backlog.md`);不存储设计原则(→ `INVARIANTS.md`);不维护 phase 高频状态(→ `docs/active_context.md`)
> 长度上限:300 行;超过说明放进了不该放的东西

# 演进路线图 (Roadmap)

> 最近更新:见 git log。本文件只维护仍会影响未来决策的方向。已完成 phase 的细节请查 `git log` 与 `docs/plans/<phase>/closeout.md`。

---

## 一、当前实现基线

| 维度 | 当前状态 |
|------|----------|
| **稳定 checkpoint** | `v1.5.0` 已发布;Phase 67 module / hygiene cleanup + Phase 68 `RawMaterialStore` boundary 构成当前 knowledge plane baseline |
| **知识治理** | Raw Material / Knowledge Truth / Retrieval & Serving 三层已成型;Wiki / Canonical 是默认语义入口;`RawMaterialStore` filesystem backend 已落地 |
| **知识捕获** | `swl note` / clipboard / `generic_chat_json` / local file ingestion 已可进入 staged review 管线 |
| **检索基础设施** | `knowledge` / `notes` / `repo` / `artifacts` source policy 已按 route family 分流;embedding + sqlite-vec + LLM rerank 代码路径存在,但运行模式可见性不足 |
| **治理边界** | `apply_proposal`、SQLite-primary truth、Path A/B/C、§9 guard suite 均已实现到稳定基线 |
| **Agent 体系** | 4 Specialist + 2 Validator 独立生命周期已落地;具体品牌绑定见 `docs/design/EXECUTOR_REGISTRY.md` |
| **主要未完成面** | LLM Wiki Compiler、EvidencePack assembly / source resolution、RAG quality observability、TDD/test architecture、interface/application boundary、Planner / DAG / Strategy Router 一等化 |

---

## 二、开放差距表

| 差距 | 相关设计文档 | 当前状态 | 演进方向 |
|------|-------------|----------|----------|
| **LLM Wiki Compiler / Wiki Refinement** | KNOWLEDGE / SELF_EVOLUTION / AGENT_TAXONOMY | 当前 `note` / `ingest-file` / promote 路径不调用 LLM 编译 wiki;canonical→wiki 是确定性映射,不足以承担 Karpathy-style LLM-wiki 的解释层 | **候选 S**:显式 `draft-wiki` / `refine-wiki` workflow,从 raw material + existing truth + gap note 编译 staged draft / proposal,禁止静默写 Truth |
| **EvidencePack / Evidence Resolution** | KNOWLEDGE / DATA_MODEL | 设计定义了 EvidencePack,现有实现仍返回 flat `RetrievalItem[]`;knowledge item 仅携带 `source_ref` / `artifact_ref` pointer,不自动解析 supporting evidence | **候选 T**:结构化 EvidencePack assembly + RawMaterialStore-backed source pointer resolution,区分 primary/canonical/supporting/fallback |
| **RAG 可观测性 / 质量评估** | KNOWLEDGE / HARNESS | embedding、sqlite-vec、LLM rerank 已有代码路径,但 operator 侧不够直观看到当前是 `vector` 还是 `text_fallback`,也缺少真实 retrieval miss taxonomy / eval fixtures | **候选 U**:retrieval inspect / doctor / eval hardening;先观测真实 miss,再决定是否做持久化 vector index / query rewrite |
| **测试架构 / TDD Harness** | INVARIANTS / HARNESS / INTERACTION | `tests/test_cli.py` 已成为 1.1w 行聚合测试;root tests 混合 unit/integration/guard/eval;fixture/builder/CLI runner 缺少统一入口;标准见 `docs/engineering/TEST_ARCHITECTURE.md` | **候选 AA**:Test Architecture / TDD Harness;先建 tests helpers 与分层目录,再拆 CLI 巨型测试,为后续 TDD 降低摩擦 |
| **接口层 / 应用层边界不清** | INTERACTION / DATA_MODEL / ARCHITECTURE | CLI、FastAPI、application commands/queries、SQLite persistence 边界尚未显式化;FastAPI 当前偏 read-only adapter,SQLite 仍以大 store 文件为主;标准见 `docs/design/INTERACTION.md §4.2` 与 `docs/engineering/CODE_ORGANIZATION.md` | **候选 AB**:Interface / Application Boundary Clarification;CLI/FastAPI 成为共享 application command/query 的 adapters,SQLite 保持本地单文件但 persistence code 拆到 repository ports 后面 |
| **Knowledge Plane API 分裂** | KNOWLEDGE / ARCHITECTURE | `canonical_*` / `knowledge_*` / retrieval projections 共同描述 Knowledge Truth 生命周期,但 public import 面仍横向分散 | **候选 V**:facade-first Knowledge Plane API simplification;先收口上层依赖,再逐步整理内部命名 |
| **Provider Router 单文件过载** | PROVIDER_ROUTER | `router.py` 同时承载 registry / policy / SQLite metadata / selection / completion gateway / reports | **候选 W**:保留 `router.py` 兼容 facade,内部拆分 route registry / policy / metadata store / selection / completion gateway |
| **Orchestration God modules** | ORCHESTRATION / HARNESS | `orchestrator.py` / `harness.py` / `executor.py` 承载过多 workflow、artifact、executor、fallback 与 report 逻辑 | **候选 X**:facade-preserving decomposition;不移动 Control 权限,只抽 task / execution / subtask / retrieval / knowledge flow 服务 |
| **Surface / Optimizer 命令面聚合** | INTERACTION / SELF_EVOLUTION | `cli.py` 与 `meta_optimizer.py` 仍是表层命令、报告、proposal lifecycle 的大聚合文件 | **候选 Y**:CLI command family split + Meta Optimizer internal module split;以无行为变化的阅读性重组为主 |
| **Governance apply handler 集中度** | INVARIANTS / DATA_MODEL | `apply_proposal` 必须保持唯一入口,但 route / canonical / policy 私有 handler 可读性继续下降 | **候选 Z**:保留 `apply_proposal` invariant facade,只把私有 apply handlers 内聚到内部模块并强化 guard |
| **编排显式化(Planner / DAG)** | ORCHESTRATION | Planner 部分构造已抽出,DAG / Strategy Router 仍未一等化 | **候选 D**:Planner 独立组件、DAG subtask 依赖、Strategy Router 显式化;等待真实编排瓶颈推动 |
| **能力画像自动学习** | PROVIDER_ROUTER / SELF_EVOLUTION | 已被路由消费;自动学习质量与 guard 可观测性仍需提升 | 后续方向;优先级低于 RAG / wiki / evidence 缺口 |
| **Runtime v1** | HARNESS | harness bridge 为 v0 约束 | 低优先级;除非 R 阶段暴露 runtime 层真实瓶颈 |
| **远期方向** | 多处 | 当前不投入 | 跨设备同步(用户层 git / 同步盘优先)、团队协作扩展、IDE 集成、Remote Worker、Hosted Control Plane、object storage backend(MinIO / OSS / S3-compatible) |

---

## 三、推荐 Phase 队列

| 优先级 | Phase 候选 | 名称 | Primary Track | 状态 |
|--------|-----------|------|---------------|------|
| 当前 active | 候选 R | v1.5.0 Real-use Feedback & RAG Gap Triage | Operations / Knowledge | 从 `v1.5.0` 启动真实使用观察,重点记录 retrieval/wiki/evidence 缺口与运行模式 |
| 推荐次序 2 | 候选 AA | Test Architecture / TDD Harness | Engineering Quality | 后续 TDD 与 V/W/X 重构前置;先建立测试分层、helpers、CLI runner,再拆 `test_cli.py` |
| 推荐次序 3 | 候选 V | Knowledge Plane API Simplification | Knowledge / Architecture | S/T/U 前的低风险地基;先收口 public import 面,避免 wiki/evidence/RAG 继续放大命名分裂 |
| 推荐次序 4 | 候选 S | LLM Wiki Compiler / Wiki Refinement Workflow | Knowledge / LLM | 由 R 阶段样本触发;补齐 raw material → staged wiki/canonical draft 的自动编译层 |
| 推荐次序 5 | 候选 T | EvidencePack Assembly / Source Resolution | Knowledge / Retrieval | 由 R 阶段样本触发;把 flat retrieval items 提升为结构化 evidence-backed serving result |
| 推荐次序 6 | 候选 U | Neural Retrieval Observability / Eval / Index Hardening | Retrieval Quality | 先补运行模式可见性与 eval,再决定 persistent vector index / query rewrite |
| 推荐次序 7 | 候选 AB | Interface / Application Boundary Clarification | Architecture / Interaction | CLI/FastAPI 统一走 application commands/queries;SQLite 保持 local-first 单文件,但 persistence code 拆清 |
| 推荐次序 8 | 候选 W | Provider Router API Split | Provider Router / LLM Gateway | 与 S/U 可相邻推进;Path A/C 触发更多 LLM 调用前,拆清 routing 与 completion gateway |
| 推荐次序 9 | 候选 X | Orchestration Facade Decomposition | Orchestration | D 前置维护性重组;只抽服务,不移动 Orchestrator control authority |
| 推荐次序 10 | 候选 D | 编排增强(Planner / DAG / Strategy Router) | Orchestration | 后置;等待真实编排瓶颈推动 |
| 推荐次序 11 | 候选 Y | Surface Command / Meta Optimizer Module Split | Interaction / Self Evolution | 低风险阅读性重组;等核心 domain API 稳定后推进 |
| 推荐次序 12 | 候选 Z | Governance Apply Handler Split | Truth Governance | 最后推进;保持 `apply_proposal` 唯一入口,只整理私有 handler |

---

## 四、候选说明

### 候选 R:v1.5.0 Real-use Feedback & RAG Gap Triage

- **核心价值**:从 `v1.5.0` storage-abstracted knowledge plane 启动真实使用,把 retrieval / wiki / evidence 的真实缺口转成后续候选 phase。
- **R0 观察维度**:多 agent 协作、复杂任务编排、长期知识沉淀、Wiki / Canonical 检索质量、route 自动学习有效性、INVARIANTS P1 / P2 在生产负载下的稳定性。
- **R1 RAG 运行模式记录**:每次 retrieval miss 记录是否命中 `knowledge`、是否为 `vector` / `text_fallback`、LLM rerank 是否生效、是否因 source policy 未覆盖、wiki 太薄、无 canonical/wiki、或 evidence pointer 未解析而失败。
- **R2 后续分流规则**:wiki 缺解释 → 候选 S;命中 knowledge 但不能回溯 evidence → 候选 T;embedding/rerank 不可见或质量不可评估 → 候选 U;多任务依赖/Planner 真瓶颈 → 候选 D。
- **Concern watchlist**:conversation primary path tie-break、false fail verdict keyword scan、`generic_chat_json` auto-detect 只在 R 阶段真实样本复现时开 bugfix 或并入候选 U/Y。
- **使用边界**:默认使用 fresh v1.5 workspace 或现有 v1 backfill;不把 schema v2 migration runner、durable proposal artifact restore、真实 object-storage backend 当作 R 阶段入口条件。

### 候选 S:LLM Wiki Compiler / Wiki Refinement Workflow

- **核心价值**:补齐 raw material → wiki/canonical draft 的自动编译层,让原始材料可以被 LLM 编译为解释充分、证据可追溯的 staged knowledge。
- **可能 slice**:source_ref/artifact_ref prompt pack / `draft-wiki` 或 `refine-wiki` 显式入口 / staged draft or proposal artifact / evidence refs + rationale + conflict flags / review-promote gate。
- **边界**:LLM Compiler 是 Specialist / propose-only;不静默写 canonical/wiki Truth,不把 `swl note` 默认变成 LLM 调用。
- **风险**:中高;prompt schema、证据引用、diff/refinement、staleness(content_hash/parser_version)都需要设计清楚。

### 候选 T:EvidencePack Assembly / Source Resolution

- **核心价值**:把 Retrieval & Serving 从 flat `RetrievalItem[]` 提升为 design 中的 EvidencePack,让调用者区分 primary_objects / canonical_objects / supporting_evidence / fallback_hits / source_pointers。
- **可能 slice**:EvidencePack dataclass / current RetrievalItem compatibility adapter / RawMaterialStore-backed pointer resolution / artifact evidence span or heading support / retrieval report 可读化。
- **边界**:EvidencePack 不内嵌 raw bytes 为 Truth;只承载 reference 与必要 excerpt,不改变 source type 语义。
- **风险**:中;触及 harness / orchestrator / retrieval report surface,需要兼容既有 `retrieval.json`。

### 候选 U:Neural Retrieval Observability / Eval / Index Hardening

- **核心价值**:让 operator 能判断当前 RAG 是 vector、text fallback、relation expansion 还是 rerank 后结果,并用真实样本评估是否需要持久化 vector index / query rewrite / source policy refinement。
- **可能 slice**:retrieval inspect 字段强化 / doctor stack embedding+sqlite-vec+routing summary / retrieval miss taxonomy fixture / eval golden set / persistent embedding index 设计评估 / embedding dimension 延迟配置 / sqlite-vec warning guard / retrieval source policy ownership。
- **边界**:向量索引仍是辅助召回,不反向定义 Knowledge Truth;query rewrite 不得绕过 source policy 与治理过滤。
- **风险**:中;必须先用 R 阶段样本证明瓶颈,避免过早平台化。

### 候选 AA:Test Architecture / TDD Harness

- **核心价值**:把测试从历史堆叠状态整理为支持 TDD 的分层体系,让后续重构和功能开发能快速写红灯、定位失败、审查覆盖面。
- **可能 slice**:`tests/conftest.py` / `tests/helpers/{builders,workspace,cli_runner,assertions,ast_guards}.py` / `unit`、`integration`、`guards`、`eval` 分层 / 拆分 `test_cli.py` / phase 命名测试迁移到领域目录 / pytest markers / chat-completion guard def-use 能力评估。
- **边界**:先做无行为变化迁移;宪法 guard 独立显眼,不得弱化;eval 默认仍 deselect;不为“目录漂亮”搬动小而清晰的测试。
- **长期标准参考**:`docs/engineering/TEST_ARCHITECTURE.md` 固定测试分层、TDD workflow、fixture/helper、CLI 测试、guard/eval 规则。
- **风险**:中;主要风险是收集路径、共享 fixture 与 CLI snapshot 断言漂移,需要 collect-only + full pytest 验证。

### 候选 AB:Interface / Application Boundary Clarification

- **核心价值**:把 CLI、FastAPI、Web Control Center、application commands/queries、Truth persistence 的边界显式化,降低“后端一团”的理解成本。
- **可能 slice**:`application/queries/control_center.py` 抽出 read payload builders / `application/commands/{task,knowledge,proposal,route}.py` 统一 CLI 与 FastAPI 写入口 / `interfaces/http/{app,routes,schemas}` / `interfaces/cli/commands` / SQLite connection/schema/repository 拆包 / migration runner 与 event cutoff/backfill 策略。
- **边界**:保持 local-first monolith;SQLite 仍是 workspace-local 单文件 truth,不拆成外部 DB service;FastAPI 只是 interface adapter,不成为第二个 Orchestrator,所有写操作仍走 governance / Orchestrator / `apply_proposal`。
- **长期标准参考**:`docs/design/INTERACTION.md §4.2` 规定 Browser Web UI 与桌面应用走本地 FastAPI,CLI 普通命令不经 HTTP;`docs/engineering/CODE_ORGANIZATION.md` 固定 interface/application/persistence 收敛方向。
- **风险**:中高;触及 CLI、FastAPI、store facade 与测试组织,应依赖候选 AA 的 TDD harness 降低回归风险。

### 候选 V:Knowledge Plane API Simplification

- **核心价值**:把 `canonical_*` / `knowledge_*` / retrieval projections 收束为统一 Knowledge Plane public API,降低上层理解和修改成本。
- **可能 slice**:`knowledge_plane.py` facade / orchestrator、CLI、librarian executor 迁移到 facade import / canonical registry + reuse + audit 内部命名整理 / knowledge lifecycle 与 projection 边界明确化。
- **边界**:不改变 Knowledge Truth schema,不绕过 `apply_proposal`,不把 canonical 重新定义为独立 truth plane。
- **长期标准参考**:`docs/engineering/CODE_ORGANIZATION.md` Knowledge Plane / facade-first migration。
- **风险**:中低;主要风险是 import churn,应先 facade-first,后内部 rename / file move。

### 候选 W:Provider Router API Split

- **核心价值**:把 route registry、policy、metadata persistence、selection、completion invocation 从 `router.py` 内部拆清,为更多 Path A / Path C LLM 调用做准备。
- **可能 slice**:`route_registry.py` / `route_policy.py` / `route_metadata_store.py` / `route_selection.py` / `completion_gateway.py` / `route_reports.py` / runtime provider-executor defaults owner,并保留 `router.py` 作为兼容 facade。
- **边界**:不改变 Provider Router 治理职责;Path B agent black-box 仍不穿透 router;品牌绑定仍只在 registry 文档与默认配置中出现。
- **长期标准参考**:`docs/engineering/CODE_ORGANIZATION.md` Provider Router target boundary。
- **风险**:中;涉及 route metadata 与 SQLite bootstrap,需要守住现有 CLI/API 兼容。

### 候选 X:Orchestration Facade Decomposition

- **核心价值**:降低 `orchestrator.py` / `harness.py` / `executor.py` 的维护成本,让后续 Planner / DAG / Strategy Router 增强有清晰插入点。
- **可能 slice**:`task_lifecycle.py` / `execution_attempts.py` / `subtask_flow.py` / `knowledge_flow.py` / `retrieval_flow.py` / `artifact_writer.py` / executor registry、prompt builder、fallback 模块拆分 / event payload deprecated 字段 / artifact owner table / policy-result report-event helper / shared taxonomy-capability constants。
- **边界**:Orchestrator 仍是唯一 Control Plane 实体;抽出的服务不拥有静默推进 task state 的权力。
- **长期标准参考**:`docs/engineering/CODE_ORGANIZATION.md` Orchestration facade decomposition。
- **风险**:高;触及主执行链路,应在候选 D 前作为维护性前置,并要求完整 guard + focused regression。

### 候选 Y:Surface Command / Meta Optimizer Module Split

- **核心价值**:把 CLI 命令族与 Meta Optimizer proposal lifecycle 从大文件中拆出,提升日常回看和小改效率。
- **可能 slice**:`surface_tools/commands/{task,knowledge,route,proposal,reports,doctor}.py` / meta optimizer model、snapshot、proposal builder、review、apply、agent 模块化 / route weight proposal JSON artifact / durable proposal artifact lifecycle / parser-dispatch alignment。
- **边界**:以无行为变化重组为主;不扩大 CLI 公共语义,不改变 proposal governance。
- **长期标准参考**:`docs/engineering/CODE_ORGANIZATION.md` interface/application/surface_tools 收敛方向。
- **风险**:中低;主要是 parser / snapshot / report 兼容性测试成本。

### 候选 Z:Governance Apply Handler Split

- **核心价值**:在不动 `apply_proposal` 唯一入口的前提下,把 canonical / route metadata / policy 私有 apply 分支内聚到内部模块,降低 governance 文件局部复杂度。
- **可能 slice**:`proposal_registry.py` / `apply_canonical.py` / `apply_route_metadata.py` / `apply_policy.py` / route review metadata reconciliation extraction / `librarian_side_effect` vs §5 矩阵评估 / transaction envelope helper / review artifact outbox or stale marker / audit snapshot size policy。
- **边界**:`apply_proposal` 继续是 canonical knowledge / route metadata / policy 的唯一 public mutation entry;所有外部调用路径不变。
- **长期标准参考**:`docs/engineering/CODE_ORGANIZATION.md` Governance handler extraction boundary。
- **风险**:中高;这是宪法边界附近的重组,必须保持 `test_only_apply_proposal_calls_private_writers` 与 route/canonical guard 不弱化。

### 候选 D:编排增强(Planner / DAG / Strategy Router)

- **核心价值**:把已部分抽出的 planning 能力继续一等化,形成明确 Planner 接口、DAG dependency orchestration 与 Strategy Router 可观测边界。
- **可能 slice**:Planner 接口抽取 / DAG-based subtask 依赖 / Strategy Router 显式化。
- **风险**:高;涉及 orchestrator 主链路重构,回滚成本高。
- **优先级理由**:当前编排能力实际可用,等 R 阶段暴露真实瓶颈后再推进。

---

## 五、推荐顺序

**R → AA → V → S/T/U(按真实缺口排序) → AB/W/X(按触碰面触发) → D → Y/Z**

排序依据:

1. **R 先行**:当前最不确定的不是治理边界,而是 LLM-wiki 与 neural retrieval 在真实工作负载下是否足够可用。
2. **AA 前置**:后续 V/W/X/AB 都是 import 面、接口面或主链路重组,先建立 TDD harness 能显著降低改动成本。
3. **V 作为知识地基**:S/T/U 都会继续触碰 knowledge plane,先收口 public API 能避免命名分裂继续扩散。
4. **S/T/U 按样本排序**:wiki 缺解释优先 S;knowledge 命中但证据回溯不足优先 T;无法判断 vector/rerank 质量或反复 text fallback 优先 U。
5. **AB/W/X 按触碰面触发**:需要 Control Center/API 写入口时优先 AB;Path A/C 调用增长时优先 W;准备 D 或主链路维护摩擦升高时优先 X。
6. **D 后置**:Planner / DAG / Strategy Router 属于高回滚成本主链路重构,只有真实多任务依赖瓶颈出现时才值得启动。
7. **Y/Z 最后**:CLI / Meta Optimizer 与 governance handler 重组有维护收益,但不应阻塞知识能力与检索质量闭环。

---

## 六、战略锚点

| 维度 | 当前现状 | 下一步候选 |
|------|----------|------------|
| 知识治理 | RawMaterialStore 边界已落地;Wiki / Canonical 默认主入口稳定;EvidencePack 与 LLM Wiki Compiler 仍是实现缺口 | 候选 S / T |
| 检索质量 | source policy 已按 route family 分流;embedding/rerank 可选路径存在但可观测性不足 | 候选 U |
| Truth 物理存储 | task / event / knowledge / route / policy 以 SQLite 为主;raw material 后端当前为 filesystem | object-storage backend 后置,由真实跨设备需求触发 |
| 治理边界 | `apply_proposal`、Path A/B/C、§9 守卫已成稳定基线 | 保持,不在 R 阶段扩张治理规则 |
| 执行编排 | fan-out + timeout + subtask summary 已落地;DAG/Planner 未一等化 | 候选 D 后置 |
| 测试体系 | 默认测试 622 collected / 8 eval deselected;guard/eval 可用,但 `test_cli.py` 与 fixture 重复已阻碍 TDD | 候选 AA;参考 `docs/engineering/TEST_ARCHITECTURE.md` |
| 接口与应用边界 | CLI 是主入口;Browser/Desktop UI 通过本地 FastAPI;SQLite 为 local single-file truth;CLI/FastAPI 应共享 application commands/queries,但 application/query/command/persistence 边界仍不够显式 | 候选 AB;参考 `docs/design/INTERACTION.md §4.2` 与 `docs/engineering/CODE_ORGANIZATION.md` |
| 代码组织 | runtime code 已按 `truth_governance/`、`orchestration/`、`provider_router/`、`knowledge_retrieval/`、`surface_tools/` 分层,但 knowledge plane / router / orchestrator / CLI 仍有 API 面和职责边界重组空间 | 候选 V/W/X/Y/Z;参考 `docs/engineering/CODE_ORGANIZATION.md` |

---

## 七、本文件的职责边界

`docs/roadmap.md` 是:
- 跨 phase 蓝图对齐活文档
- 当前仍开放的差距表
- 推荐 phase 队列与优先级说明
- 战略锚点分析

`docs/roadmap.md` 不是:
- 当前 phase 状态板(→ `docs/active_context.md`)
- 完整 phase 历史编年(→ git log + `docs/plans/<phase>/closeout.md`)
- 设计文档(→ `docs/design/`)
- 设计原则副本(→ `docs/design/INVARIANTS.md`)
- closeout 索引(→ `docs/plans/<phase>/closeout.md`)
- Tag / Release docs 同步状态(→ `docs/concerns_backlog.md`)
