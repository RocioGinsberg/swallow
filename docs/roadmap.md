---
author: claude
status: living-document
---

# 演进路线图 (Roadmap)

## 一、能力现状与演进方向 (Post-v1.0.0)

> 最近更新：2026-04-24

系统已完成 **Foundation Era**（Phase 47-54），核心架构差距全部消化：异步底座（v0.6.0）、知识 SSOT（v0.7.0）、策略闭环（v0.8.0）、并行编排（v0.9.0）、Specialist Agent 体系（v1.0.0）、命名清理（v1.0.0）。452 tests passed，7 个 specialist/validator Agent 全部具备独立生命周期。

### 已消化的蓝图差距（Foundation Era 回顾）

| 差距 | 消化 Phase | 状态 |
|------|-----------|------|
| 知识真值”双重真相”风险（SSOT） | Phase 49 (v0.7.0) | ✅ SQLite-primary，文件系统仅保留 mirror |
| Specialist Agent 缺位与提案应用流程 | Phase 50-51-53 (v0.7.0+ → v1.0.0) | ✅ 7 个 Agent 全部落地，提案应用闭环完整 |
| 执行能力不完整（同步桥接、并发控制） | Phase 52 (v0.9.0) | ✅ AsyncCLIAgentExecutor + fan-out + timeout |
| Taxonomy 命名品牌残留 | Phase 54 (v1.0.0) | ✅ codex_fim → fim，shim 保留 |

### 前瞻性能力差距（Knowledge Loop Era 方向）

Foundation Era 以”消化蓝图差距”为驱动。v1.0.0 后，主要架构债务已清零，演进逻辑转为**从知识闭环出发，逐步扩展系统能力**。

| 差距 | 蓝图来源 | 当前状态 | 演进方向 |
|------|---------|---------|---------|
| **知识图谱与关系检索** | `KNOWLEDGE.md` Stage 3 (Relation Expansion) | ✅ Phase 55 完成：双链图谱 + BFS relation expansion | 稳定期 |
| **本地文件摄入** | `KNOWLEDGE.md` + `INTERACTION.md` | ✅ Phase 55 完成：`swl knowledge ingest-file` | 稳定期 |
| **LLM 增强检索与知识质量** | `KNOWLEDGE.md` 远期方向 | ✅ Phase 56 完成：LLM 增强 Literature/Quality + gated suggestions | 稳定期 |
| **检索基础设施（Embedding / Rerank）** | `KNOWLEDGE.md` §2.2 + §8 | blake2b hash 64 维（非神经网络），无 rerank | **Phase 57**：neural embedding + LLM rerank |
| **路径感知的 Retrieval Policy（HTTP path 优先）** | `ARCHITECTURE.md` §4（HTTP path vs Agent black-box path）+ Phase 57 review 讨论 | retrieval 默认 source 与执行路径无关。HTTP path 是讨论 / brainstorm / 受控模型调用的主路径，最依赖 retrieval；CLI agent path（aider / claude-code / codex）有自主文件访问能力，repo retrieval 价值低 | **候选方向**：retrieval policy 感知 execution path — HTTP path 默认带 knowledge/notes（讨论场景），CLI agent path 默认只带 knowledge/notes 摘要，repo 不再由 swallow 切 chunk，统一交给 agent 自主探索 |
| **灵感捕获低摩擦入口（`swl note`）** | Phase 57 review 讨论 + `KNOWLEDGE.md` staged knowledge raw 阶段 | operator 灵感目前只能走 `ingest-file` → 需建文件 / 选路径 / 切终端，对"突然冒出来的想法"摩擦太大；同时 notes source type 当前定位模糊（chunk-only，无治理） | **候选方向**：新增 `swl note <text>` CLI，wrap 现有 ingestion pipeline，自动写入 staged knowledge 的 raw 阶段（`source_kind=operator_note`、`source_task_id=note-<timestamp>`），灵感进入既有 review/promote 流程；同步评估让 notes source type 退场，内容流向 staged knowledge / artifacts / repo 三个治理清晰的层 |
| **CLI Agent 生态完善（Codex CLI 接入）** | `ARCHITECTURE.md` §3 默认执行器分工 + 个人使用习惯 | 当前默认 CLI agent 只有 `local-aider` / `local-claude-code`；Codex CLI 作为 OpenAI 生态等价物未在默认 RouteRegistry 中注册 | **候选方向**：在 `AsyncCLIAgentExecutor + CLIAgentConfig` 框架下新增 `local-codex` route，与 aider / claude-code 同等地位；可能涉及 dialect adapter、binary 探测、能力画像默认值 |
| **编排显式化（Planner / DAG）** | `ORCHESTRATION.md` | planner 逻辑嵌入 orchestrator | **Phase 58 方向**：独立组件 |
| **能力画像自动学习** | `PROVIDER_ROUTER.md` + `SELF_EVOLUTION.md` | unsupported_task_types 字段存在但未消费 | **Phase 59 方向**：遥测驱动 |
| **Runtime v1（原生 async subprocess）** | `HARNESS.md` | harness bridge 为 v0 约束 | 低优先级，功能正常 |
| **远期方向** | 多处 | — | IDE 集成、Remote Worker、Hosted Control Plane |

---

## 二、已完成 Phase 记录 (Completed Phases)

### [Phase 47] 多模型共识与策略护栏 (v0.5.0)
*   **成果**：系统进入 **Consensus Era**，实装 N-Reviewer 共识门禁与 TaskCard 级成本护栏。

### [Phase 48] 存储引擎升级与全异步改造 (v0.6.0)
*   **成果**：系统进入 **Async Era**，落地 `SqliteTaskStore` 与全链路 `async/await`。

### [Phase 49] 知识真值归一与向量 RAG (v0.7.0)
*   **成果**：系统进入 **Knowledge Era**，落地知识层 SQLite SSOT、`LibrarianAgent` 与 `sqlite-vec` 可退级检索。

### [Phase 50] 路由策略闭环与专项审计 (v0.7.0+)
*   **成果**：系统从”孤立的遥测记录”进化到”可感知的策略行为”，实现审计、提案、权重调整的单向数据流闭环。406 tests passed。

### [Phase 51] 策略闭环与 Specialist Agent 落地 (v0.8.0)
*   **成果**：系统进入 **Policy Era**，实现”自我观察 → 提案生成 → operator 审批 → 自动应用”的完整闭环。Specialist Agent 体系初步成型（MetaOptimizerAgent / LibrarianAgent）。approved_with_concerns，2 CONCERN 登记。

### [Phase 52] 平台级多路并行与复杂拓扑 (v0.9.0)
*   **成果**：系统进入 **Parallel Era**，落地 `AsyncCLIAgentExecutor`、`complexity_hint` 路由偏置、`AsyncSubtaskOrchestrator` fan-out + timeout 守卫。437 tests passed，approved_with_concerns，2 CONCERN 登记。

### [Phase 53] Specialist Agent 生态落地 (v1.0.0)
*   **成果**：系统进入 **Specialist Era**，5 个专项 Agent 独立生命周期全部落地（IngestionSpecialist、ConsistencyReviewer、Validator、LiteratureSpecialist、QualityReviewer），`EXECUTOR_REGISTRY` 替换 if-chain，`MEMORY_AUTHORITY_SEMANTICS` 落地，`AGENT_TAXONOMY.md §5` 补充 side effect 列。452 tests passed，approved_with_concerns（唯一 CONCERN 已在合并前消化）。

### [Phase 54] Taxonomy 命名与品牌残留清理 (v1.0.0)
*   **成果**：`codex_fim` 降级为 legacy shim，`fim` 成为主键，文件重命名 `codex_fim.py → fim_dialect.py`，Phase 52 CONCERN 消化完毕。452 tests passed，approved，无新 CONCERN。

### [Phase 55] 知识图谱与本地 RAG (v1.1.0)
*   **成果**：系统进入 **Knowledge Graph Era**，落地双链知识图谱（`knowledge_relations` SQLite 表）、本地文件摄入（`swl knowledge ingest-file`）、relation-aware retrieval（BFS 遍历 + 置信度衰减）与端到端知识闭环。

### [Phase 56] 知识质量与 LLM 增强检索
*   **成果**：LiteratureSpecialist / QualityReviewer 从启发式升级为 LLM 增强（`agent_llm.py` 共享 helper），HTTP executor token 统计切换为 API usage 优先，relation suggestions 进入 operator-gated CLI 工作流。approved，无 CONCERN。

---

## 三、Phase 定义

### Foundation Era (Phase 47-54) — 已完成

| Phase | 名称 | Tag | Primary Track | 状态 |
|-------|------|-----|---------------|------|
| 47 | 多模型共识与策略护栏 | v0.5.0 | Consensus | ✅ Done |
| 48 | 存储引擎升级与全异步改造 | v0.6.0 | Core Loop | ✅ Done |
| 49 | 知识真值归一与向量 RAG | v0.7.0 | Knowledge / RAG | ✅ Done |
| 50 | 路由策略闭环与专项审计 | v0.7.0+ | Evaluation / Policy | ✅ Done |
| 51 | 策略闭环与 Specialist Agent 落地 | v0.8.0 | Agent Taxonomy | ✅ Done |
| 52 | 平台级多路并行与复杂拓扑 | v0.9.0 | Core Loop | ✅ Done |
| 53 | Specialist Agent 生态落地 | v1.0.0 | Agent Taxonomy | ✅ Done |
| 54 | Taxonomy 命名与品牌残留清理 | v1.0.0 | Agent Taxonomy | ✅ Done |

### Knowledge Loop Era (Phase 55+) — 从知识闭环出发的能力扩展

v1.0.0 后，演进逻辑从”消化蓝图差距”转为”从可展示的知识闭环出发，逐步扩展系统能力”。每个 phase 的输出是前一个 phase 的自然延伸，而非从蓝图中挑选 gap 填补。

#### Phase 55: 知识图谱与本地 RAG (Knowledge Graph & Local RAG) ✅ Done
*   **Primary Track**: Knowledge / RAG
*   **Secondary Track**: Agent Taxonomy
*   **成果**：系统进入 **Knowledge Graph Era**，双链知识图谱 + 本地文件摄入 + relation-aware retrieval + 端到端闭环全部落地。tag `v1.1.0`。

#### Phase 56: 知识质量与 LLM 增强检索 ✅ Done
*   **Primary Track**: Knowledge / RAG
*   **Secondary Track**: Agent Taxonomy
*   **成果**：LiteratureSpecialist / QualityReviewer 接入 LLM 语义分析，relation suggestions gated workflow 落地，HTTP executor token 统计统一为 API usage 优先。

#### Phase 57: 检索质量增强 (Retrieval Quality Enhancement) 🚀 [Active]
*   **Primary Track**: Knowledge / RAG
*   **Secondary Track**: Workbench / UX
*   **目标**：将检索管线从”本地 hash embedding + 单阶段评分”升级为”神经 API embedding + LLM rerank + chunking 优化”。
*   **核心任务**：
    - **S1: Neural Embedding**：API embedding 替换 blake2b hash，保留 local fallback。
    - **S2: LLM Rerank**：`retrieve_context()` 出口插入 LLM rerank，复用 `call_agent_llm()`。
    - **S3: Chunking 优化**：markdown/repo chunking 增加 overlap 和 max_chunk_size。
    - **S4: Specialist CLI 补齐**：`swl task create --executor literature-specialist --document-paths` 透传。
*   **风险等级**：中（S1 引入 API 依赖，但 graceful degradation 充分缓解）
*   **依赖**：Phase 56 `runtime_config.py` + `call_agent_llm()` 基础设施
*   **方向调整说明**：roadmap 原定 Phase 57 为”编排增强”，Phase 56 前置真实数据验证暴露检索质量为更紧迫瓶颈，编排增强后移至 Phase 58。

#### Phase 58 方向: 编排增强
*   **驱动**：检索质量稳定后，任务拆解和执行编排成为瓶颈。
*   **方向**：Planner 显式化为独立组件、DAG-based subtask 依赖、Strategy Router 抽取。
*   **蓝图对齐**：`ORCHESTRATION.md`（Strategy Router、Planner、DAG 编排）。

#### Phase 59 方向: 能力画像自动学习
*   **驱动**：编排能力上来后，路由决策的精度成为瓶颈。
*   **方向**：从遥测数据自动学习 route capability profiles、capability boundary guard 激活。
*   **蓝图对齐**：`PROVIDER_ROUTER.md`（能力画像评分）、`SELF_EVOLUTION.md`（隐式信号聚合）。

---

## 四、队列与战略分析 (Claude 维护)

> 最近更新：2026-04-26 (Phase 56 已完成，Phase 57 检索质量增强方向已确立)

### 队列总览

| 优先级 | Phase | 名称 | Primary Track | 状态 | 备注 |
|--------|-------|------|---------------|------|------|
| ~~1~~ | ~~47~~ | ~~多模型共识与策略护栏~~ | ~~Consensus~~ | ~~已完成~~ | tag `v0.5.0` |
| ~~2~~ | ~~48~~ | ~~存储引擎升级与全异步改造~~ | ~~Core Loop~~ | ~~已完成~~ | tag `v0.6.0` |
| ~~3~~ | ~~49~~ | ~~知识真值归一与向量 RAG~~ | ~~Knowledge / RAG~~ | ~~已完成~~ | tag `v0.7.0` |
| ~~4~~ | ~~50~~ | ~~路由策略闭环与专项审计~~ | ~~Evaluation / Policy~~ | ~~已完成~~ | tag `v0.7.0+` |
| ~~5~~ | ~~51~~ | ~~策略闭环与 Specialist Agent 落地~~ | ~~Agent Taxonomy~~ | ~~已完成~~ | tag `v0.8.0` |
| ~~6~~ | ~~52~~ | ~~平台级多路并行与复杂拓扑~~ | ~~Core Loop~~ | ~~已完成~~ | tag `v0.9.0` |
| ~~7~~ | ~~53~~ | ~~Specialist Agent 生态落地~~ | ~~Agent Taxonomy~~ | ~~已完成~~ | tag `v1.0.0` |
| ~~8~~ | ~~54~~ | ~~Taxonomy 命名与品牌残留清理~~ | ~~Agent Taxonomy~~ | ~~已完成~~ | tag `v1.0.0` |
| ~~9~~ | ~~55~~ | ~~知识图谱与本地 RAG~~ | ~~Knowledge / RAG~~ | ~~已完成~~ | tag `v1.1.0` |
| ~~10~~ | ~~56~~ | ~~知识质量与 LLM 增强检索~~ | ~~Knowledge / RAG~~ | ~~已完成~~ | merged |
| **11** | **57** | **检索质量增强** | **Knowledge / RAG** | **Active** | Neural Embedding + LLM Rerank + Chunking |
| 12 | 58 | 编排增强 | Core Loop | 方向 | Planner / DAG / Strategy Router |
| 13 | 59 | 能力画像自动学习 | Evaluation / Policy | 方向 | 遥测驱动 capability profiles |

### 战略锚点分析

| 维度 | 蓝图愿景 | v1.1.0 现状 | 下一步 |
|------|---------|------------|--------|
| **知识治理** | truth-first 知识系统，5 阶段检索（含 Relation Expansion） | 双层架构完整，Stage 1-5 全部实现，relation-aware retrieval 落地 | **Phase 57**：检索质量增强（neural embedding + rerank） |
| **Agent 体系** | 6 个专项角色独立生命周期 | 7 个 Agent 全部落地，LLM 增强已接入 Literature/Quality | 稳定期 |
| **自我进化** | Librarian 知识沉淀 + Meta-Optimizer 优化提案 | 两条主线完整，提案应用闭环已落地 | Phase 59：能力画像自动学习 |
| **执行编排** | 高并发多路编排 + 复杂拓扑 | fan-out + timeout + subtask summary 已落地 | Phase 58：Planner 显式化 + DAG |
| **命名体系** | taxonomy before brand | codex 品牌清理完成，http-claude 保留（描述性名称） | 无近期计划 |

### 知识闭环驱动的能力扩展路线

```
Phase 55: 知识图谱 + 本地 RAG（核心闭环）✅
    ↓ 闭环跑通后，启发式分析质量成为瓶颈
Phase 56: LLM 增强检索 + 知识质量 ✅
    ↓ LLM 增强后，检索基础设施（embedding/rerank）成为瓶颈
Phase 57: 检索质量增强（Neural Embedding + Rerank）🚀
    ↓ 检索质量稳定后，任务编排成为瓶颈
Phase 58: 编排增强（Planner / DAG）
    ↓ 编排能力上来后，路由精度成为瓶颈
Phase 59: 能力画像自动学习
```

每个 phase 的详细 slice 拆解在前一个 phase 完成后再细化，避免过早规划。

### Tag 评估

| Phase | Tag | Era |
|-------|-----|-----|
| Phase 47 | `v0.5.0` | Consensus Era |
| Phase 48 | `v0.6.0` | Async Era |
| Phase 49 | `v0.7.0` | Knowledge Era |
| Phase 50 | `v0.7.0+` | Policy Closure |
| Phase 51 | `v0.8.0` | Policy Era |
| Phase 52 | `v0.9.0` | Parallel Era |
| Phase 53 | `v1.0.0` | Specialist Era |
| Phase 54 | `v1.0.0` | Specialist Era (cleanup) |
| Phase 55 | `v1.1.0` | Knowledge Graph Era |
| Phase 56 | — | Knowledge Graph Era (LLM 增强) |
| Phase 57 | `v1.2.0` (预估) | Retrieval Quality Era |
