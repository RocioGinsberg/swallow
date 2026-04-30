---
author: claude
status: living-document
---

> **Document discipline**
> Owner: Claude
> Updater: Claude 主线(差距条目新增 / 推荐队列 / 优先级 / 风险批注 / 战略锚点)+ `roadmap-updater` subagent(phase 完成事实登记 / 已有差距条目状态同步)
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
| **主要未完成面** | LLM Wiki Compiler、EvidencePack assembly / source resolution、RAG quality observability、Planner / DAG / Strategy Router 一等化 |

---

## 二、开放差距表

| 差距 | 相关设计文档 | 当前状态 | 演进方向 |
|------|-------------|----------|----------|
| **LLM Wiki Compiler / Wiki Refinement** | KNOWLEDGE / SELF_EVOLUTION / AGENT_TAXONOMY | 当前 `note` / `ingest-file` / promote 路径不调用 LLM 编译 wiki;canonical→wiki 是确定性映射,不足以承担 Karpathy-style LLM-wiki 的解释层 | **候选 S**:显式 `draft-wiki` / `refine-wiki` workflow,从 raw material + existing truth + gap note 编译 staged draft / proposal,禁止静默写 Truth |
| **EvidencePack / Evidence Resolution** | KNOWLEDGE / DATA_MODEL | 设计定义了 EvidencePack,现有实现仍返回 flat `RetrievalItem[]`;knowledge item 仅携带 `source_ref` / `artifact_ref` pointer,不自动解析 supporting evidence | **候选 T**:结构化 EvidencePack assembly + RawMaterialStore-backed source pointer resolution,区分 primary/canonical/supporting/fallback |
| **RAG 可观测性 / 质量评估** | KNOWLEDGE / HARNESS | embedding、sqlite-vec、LLM rerank 已有代码路径,但 operator 侧不够直观看到当前是 `vector` 还是 `text_fallback`,也缺少真实 retrieval miss taxonomy / eval fixtures | **候选 U**:retrieval inspect / doctor / eval hardening;先观测真实 miss,再决定是否做持久化 vector index / query rewrite |
| **编排显式化(Planner / DAG)** | ORCHESTRATION | Planner 部分构造已抽出,DAG / Strategy Router 仍未一等化 | **候选 D**:Planner 独立组件、DAG subtask 依赖、Strategy Router 显式化;等待真实编排瓶颈推动 |
| **能力画像自动学习** | PROVIDER_ROUTER / SELF_EVOLUTION | 已被路由消费;自动学习质量与 guard 可观测性仍需提升 | 后续方向;优先级低于 RAG / wiki / evidence 缺口 |
| **Runtime v1** | HARNESS | harness bridge 为 v0 约束 | 低优先级;除非 R 阶段暴露 runtime 层真实瓶颈 |
| **远期方向** | 多处 | 当前不投入 | 跨设备同步(用户层 git / 同步盘优先)、团队协作扩展、IDE 集成、Remote Worker、Hosted Control Plane、object storage backend(MinIO / OSS / S3-compatible) |

---

## 三、推荐 Phase 队列

| 优先级 | Phase 候选 | 名称 | Primary Track | 状态 |
|--------|-----------|------|---------------|------|
| 当前 active | 候选 R | v1.5.0 Real-use Feedback & RAG Gap Triage | Operations / Knowledge | 从 `v1.5.0` 启动真实使用观察,重点记录 retrieval/wiki/evidence 缺口与运行模式 |
| 推荐次序 2 | 候选 S | LLM Wiki Compiler / Wiki Refinement Workflow | Knowledge / LLM | 由 R 阶段样本触发;补齐 raw material → staged wiki/canonical draft 的自动编译层 |
| 推荐次序 3 | 候选 T | EvidencePack Assembly / Source Resolution | Knowledge / Retrieval | 由 R 阶段样本触发;把 flat retrieval items 提升为结构化 evidence-backed serving result |
| 推荐次序 4 | 候选 U | Neural Retrieval Observability / Eval / Index Hardening | Retrieval Quality | 先补运行模式可见性与 eval,再决定 persistent vector index / query rewrite |
| 推荐次序 5 | 候选 D | 编排增强(Planner / DAG / Strategy Router) | Orchestration | 后置;等待真实编排瓶颈推动 |

---

## 四、候选说明

### 候选 R:v1.5.0 Real-use Feedback & RAG Gap Triage

- **核心价值**:从 `v1.5.0` storage-abstracted knowledge plane 启动真实使用,把 retrieval / wiki / evidence 的真实缺口转成后续候选 phase。
- **R0 观察维度**:多 agent 协作、复杂任务编排、长期知识沉淀、Wiki / Canonical 检索质量、route 自动学习有效性、INVARIANTS P1 / P2 在生产负载下的稳定性。
- **R1 RAG 运行模式记录**:每次 retrieval miss 记录是否命中 `knowledge`、是否为 `vector` / `text_fallback`、LLM rerank 是否生效、是否因 source policy 未覆盖、wiki 太薄、无 canonical/wiki、或 evidence pointer 未解析而失败。
- **R2 后续分流规则**:wiki 缺解释 → 候选 S;命中 knowledge 但不能回溯 evidence → 候选 T;embedding/rerank 不可见或质量不可评估 → 候选 U;多任务依赖/Planner 真瓶颈 → 候选 D。
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
- **可能 slice**:retrieval inspect 字段强化 / doctor stack embedding+sqlite-vec+routing summary / retrieval miss taxonomy fixture / eval golden set / persistent embedding index 设计评估。
- **边界**:向量索引仍是辅助召回,不反向定义 Knowledge Truth;query rewrite 不得绕过 source policy 与治理过滤。
- **风险**:中;必须先用 R 阶段样本证明瓶颈,避免过早平台化。

### 候选 D:编排增强(Planner / DAG / Strategy Router)

- **核心价值**:把已部分抽出的 planning 能力继续一等化,形成明确 Planner 接口、DAG dependency orchestration 与 Strategy Router 可观测边界。
- **可能 slice**:Planner 接口抽取 / DAG-based subtask 依赖 / Strategy Router 显式化。
- **风险**:高;涉及 orchestrator 主链路重构,回滚成本高。
- **优先级理由**:当前编排能力实际可用,等 R 阶段暴露真实瓶颈后再推进。

---

## 五、推荐顺序

**R → S/T/U(按真实缺口排序) → D**

排序依据:

1. **R 先行**:当前最不确定的不是治理边界,而是 LLM-wiki 与 neural retrieval 在真实工作负载下是否足够可用。
2. **S/T/U 按样本排序**:wiki 缺解释优先 S;knowledge 命中但证据回溯不足优先 T;无法判断 vector/rerank 质量或反复 text fallback 优先 U。
3. **D 后置**:Planner / DAG / Strategy Router 属于高回滚成本主链路重构,只有真实多任务依赖瓶颈出现时才值得启动。

---

## 六、战略锚点

| 维度 | 当前现状 | 下一步候选 |
|------|----------|------------|
| 知识治理 | RawMaterialStore 边界已落地;Wiki / Canonical 默认主入口稳定;EvidencePack 与 LLM Wiki Compiler 仍是实现缺口 | 候选 S / T |
| 检索质量 | source policy 已按 route family 分流;embedding/rerank 可选路径存在但可观测性不足 | 候选 U |
| Truth 物理存储 | task / event / knowledge / route / policy 以 SQLite 为主;raw material 后端当前为 filesystem | object-storage backend 后置,由真实跨设备需求触发 |
| 治理边界 | `apply_proposal`、Path A/B/C、§9 守卫已成稳定基线 | 保持,不在 R 阶段扩张治理规则 |
| 执行编排 | fan-out + timeout + subtask summary 已落地;DAG/Planner 未一等化 | 候选 D 后置 |
| 代码组织 | runtime code 已按 `truth_governance/`、`orchestration/`、`provider_router/`、`knowledge_retrieval/`、`surface_tools/` 分层 | R 阶段观察维护摩擦 |

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
