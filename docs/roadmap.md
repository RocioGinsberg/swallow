---
author: claude
status: living-document
---

# 演进路线图 (Roadmap)

## 一、能力现状与演进方向

> 最近更新：2026-04-26（Phase 59 已 merge；候选 A/B 已完成；`v1.2.0` 仍需 tag 决策）

系统已完成 **Foundation Era**（Phase 47-54，v1.0.0 收官）：从 Consensus → Async → Knowledge → Policy → Parallel → Specialist 六个能力代际，把架构债务消化清零，7 个专项 Agent 全部具备独立生命周期，core loop / async runtime / SQLite truth / Librarian / Meta-Optimizer 主线完整。

进入 **Knowledge Loop Era**（Phase 55+）后，演进逻辑从"消化蓝图差距"转为"从可展示的知识闭环出发，逐步扩展系统能力"。每个 phase 是前一个的自然延伸，而不是从蓝图里挑 gap。

### 当前 v1.2.0 候选基线（Phase 59 已 merge）

| 维度 | 现状 |
|------|------|
| **知识治理** | truth-first 双层架构完整，Stage 1-5 全部实现，relation-aware retrieval 落地，LLM 增强 Literature/Quality |
| **知识捕获** | `swl note` 灵感捕获 + `swl ingest --from-clipboard` + `generic_chat_json` 受限 parser + staged review visibility 收紧 |
| **检索基础设施** | 神经 API embedding（`text-embedding-3-small`）+ LLM rerank + canonical/verified 路径对齐 |
| **Agent 体系** | 7 个 Specialist Agent 全部独立生命周期，LLM 增强已接入 Literature/Quality |
| **CLI 生态** | aider + claude-code + codex 三足鼎立，各有独立 route / config / dispatch / doctor probe |
| **执行编排** | fan-out + timeout + subtask summary 已落地；TaskCard 构造已部分抽到 `planner.py`，但独立 Planner / DAG / Strategy Router 仍未一等化 |
| **自我进化** | Librarian 知识沉淀 + Meta-Optimizer 提案应用闭环 |

### 前瞻性差距表

| 差距 | 蓝图来源 | 当前状态 | 演进方向 |
|------|---------|---------|---------| 
| ~~**思考-讨论-沉淀一等流程**~~ | `ORCHESTRATION.md` §2.5 + `KNOWLEDGE.md` §5 | ~~Phase 58 已完成 A-lite：`swl note` + clipboard + `generic_chat_json` + review visibility~~ | ~~**候选 A 已完成**~~。完整 Brainstorm topology 后置为候选 E |
| ~~**Codex CLI 接入**~~ | `ARCHITECTURE.md` §3 | ~~Phase 59 已完成：真实 `local-codex` route + `CODEX_CONFIG` + dispatch + doctor probe~~ | ~~**候选 B 已完成**~~ |
| **路径感知的 Retrieval Policy** | `ARCHITECTURE.md` §4 | retrieval 默认 source 与执行路径无关；CLI agent 有自主文件访问能力，repo retrieval 可能重复消耗 | **候选 C**：按 `execution_family + task_intent` 分流 retrieval request |
| **编排显式化（Planner / DAG）** | `ORCHESTRATION.md` | `planner.py` 已承接部分构造，Planner / DAG / Strategy Router 仍未一等化 | **候选 D**：Planner 独立组件、DAG subtask 依赖、Strategy Router 显式化 |
| **完整 Brainstorm topology** | `ORCHESTRATION.md` §2.5 | A-lite 已落地低摩擦捕获；`DebateConfig` + `BrainstormOrchestrator` + 多模型群聊仍未实现 | **候选 E**：受控 Brainstorm topology，依赖 A-lite 真实使用反馈 |
| **能力画像自动学习** | `PROVIDER_ROUTER.md` + `SELF_EVOLUTION.md` | 已被路由消费；自动学习质量与 guard 可观测性仍需提升 | **后续方向** |
| **Runtime v1** | `HARNESS.md` | harness bridge 为 v0 约束 | 低优先级 |
| **远期方向** | 多处 | — | IDE 集成、Remote Worker、Hosted Control Plane |

---

## 二、已完成 Phase 记录

### Foundation Era (Phase 47-54) — v1.0.0 收官

**一句话摘要**：6 个能力代际依次落地（Consensus → Async → Knowledge → Policy → Parallel → Specialist），架构债务清零，7 个 Specialist Agent 独立生命周期成型，452 tests passed。详细 phase 历史通过 git log 与 `docs/archive/` 追溯。

### Knowledge Loop Era (Phase 55+)

#### [Phase 55] 知识图谱与本地 RAG (v1.1.0)
*   **Primary Track**: Knowledge / RAG · **Secondary**: Agent Taxonomy
*   **成果**：双链知识图谱（`knowledge_relations` SQLite 表）+ 本地文件摄入（`swl knowledge ingest-file`）+ relation-aware retrieval（BFS 遍历 + 置信度衰减）+ 端到端知识闭环。系统进入 **Knowledge Graph Era**。

#### [Phase 56] 知识质量与 LLM 增强检索
*   **Primary Track**: Knowledge / RAG · **Secondary**: Agent Taxonomy
*   **成果**：LiteratureSpecialist / QualityReviewer 接入 LLM 语义分析，relation suggestions gated workflow 落地，HTTP executor token 统计统一为 API usage 优先。approved，无 CONCERN。

#### [Phase 57] 检索质量增强 (Retrieval Quality Enhancement) ✅ Done (待重打 v1.2.0)
*   **Primary Track**: Knowledge / RAG · **Secondary**: Workbench / UX
*   **成果**：
    - S1：神经 API embedding 替换 blake2b hash，canonical reuse 路径与 verified knowledge 路径对齐
    - S2：`retrieve_context()` 出口新增可关闭、可退化的 LLM rerank
    - S3：markdown / repo 检索分段加入 max_chunk_size，默认 overlap 已关闭（review 后收紧）
    - S4：`swl task create --executor literature-specialist --document-paths` CLI 透传
*   **Review**：approved_with_concerns（1 BLOCK 已修复，1 CONCERN 已登记）。`tests/test_cli.py` 220 passed。
*   **Tag**：v1.2.0（候选，待 release docs 同步后重打）

#### [Phase 58] 知识捕获闭环 (Knowledge Capture Loop Tightening) ✅ Done
*   **Primary Track**: Knowledge / RAG · **Secondary**: Workbench / UX
*   **成果**：
    - S1：`swl note <text> [--tag <topic>]` 灵感捕获直接写入 staged knowledge
    - S2：`swl ingest --from-clipboard` + 受限 `generic_chat_json` parser
    - S3：staged review visibility 收紧（`topic` / `source_kind` / `source_ref` 三视图对齐）
*   **Review**：approved_with_concerns（0 BLOCK，2 CONCERN 已登记 / 修复）。

#### [Phase 59] Codex CLI Route 接入 ✅ Done
*   **Primary Track**: CLI / Routing
*   **成果**：
    - S1：`local-codex` 真实 route 注册 + `ROUTE_NAME_ALIASES` 清空
    - S2：`CODEX_CONFIG`（`codex exec`）+ `run_prompt_executor` 同步/异步 dispatch
    - S3：`diagnose_cli_agents()` — aider / claude-code / codex 三合一 binary probe
*   **Review**：approved_with_concerns（1 BLOCK 已修复，1 CONCERN 已登记）。

---

## 三、推荐 Phase 队列 (Claude 维护)

> 最近更新：2026-04-26（Phase 59 已 merge，进入 Phase 60 Direction Gate）

### 队列总览

| 优先级 | Phase | 名称 | Primary Track | 状态 | 备注 |
|--------|-------|------|---------------|------|------|
| ~~1~~ | ~~55~~ | ~~知识图谱与本地 RAG~~ | ~~Knowledge / RAG~~ | ~~已完成~~ | tag `v1.1.0` |
| ~~2~~ | ~~56~~ | ~~知识质量与 LLM 增强检索~~ | ~~Knowledge / RAG~~ | ~~已完成~~ | merged |
| ~~3~~ | ~~57~~ | ~~检索质量增强~~ | ~~Knowledge / RAG~~ | ~~已完成~~ | merged，已重打 `v1.2.0` |
| ~~4~~ | ~~58~~ | ~~知识捕获闭环~~ | ~~Knowledge / RAG~~ | ~~已完成~~ | merged |
| ~~5~~ | ~~59~~ | ~~Codex CLI Route 接入~~ | ~~CLI / Routing~~ | ~~已完成~~ | merged 已打v1.3.0|
| **6** | **60** | **(待选)** | **(待选)** | **Direction Gate** | 3 个候选方向待评估 |

### Phase 60 候选方向评估

候选 A/B 已完成。剩余方向重新编号为 C/D/E：

#### 候选 C：路径感知的 Retrieval Policy（执行路径分流）
*   **核心价值**：retrieval 按 execution path 和 task intent 分流。CLI coding path 可减少 repo chunk（CLI agent 能自主探索文件）；HTTP brainstorm path 可聚焦 knowledge / explicit materials；HTTP code-analysis path 保留受控 repo 检索。
*   **可能 slice**：(1) execution family + task intent 判定接入 retrieval request 构造；(2) CLI coding path 默认 source 收紧为 knowledge / explicit refs；(3) HTTP brainstorm path 聚焦 knowledge / explicit materials；(4) HTTP code-analysis 保留可控 repo 检索
*   **风险**：中 — 涉及 retrieval 默认行为变化，需配套测试
*   **依赖**：Phase 57 retrieval 基线 + Phase 58 知识捕获入口（notes 角色更清晰）
*   **优先级理由**：架构正确性提升。Phase 58/59 落地后，retrieval 是下一个最有价值的分流点

#### 候选 D：编排增强（Planner / DAG / Strategy Router 显式化）
*   **核心价值**：把已部分抽出的 planning 能力继续一等化，形成明确 Planner 接口、DAG dependency orchestration 与 Strategy Router 可观测边界
*   **可能 slice**：(1) Planner 接口抽取；(2) DAG-based subtask 依赖；(3) Strategy Router 显式化
*   **风险**：高 — 涉及 orchestrator 主链路重构，回滚成本高
*   **依赖**：Phase 52 fan-out 基线
*   **优先级理由**：架构债务清理，但当前编排能力实际可用，没有真实瓶颈推动

#### 候选 E：完整 Brainstorm topology（受控多模型群聊）
*   **核心价值**：基于 `ORCHESTRATION.md §2.5` Brainstorm 设计，落地 `DebateConfig` + `BrainstormOrchestrator` + 多模型 synthesis，产出结构化 artifact 进入 staged knowledge
*   **可能 slice**：(1) `BrainstormConfig` + topology 定义；(2) multi-route synthesis orchestration；(3) synthesis artifact → staged knowledge 自动候选通道
*   **风险**：中到高 — 涉及新编排组件，需在低摩擦捕获（Phase 58）的真实使用反馈基础上再做
*   **依赖**：Phase 58 A-lite 稳定 + Phase 52 fan-out 基线
*   **优先级理由**：使用价值高但复杂度也高；建议在 Phase 58 入口被证明有效后再做

### Claude 推荐顺序

**C → E → D**

理由：
1. **C 优先**：Phase 58/59 完成后，retrieval 分流是下一个最直接有价值的优化——CLI agent 有自主文件访问能力，让 retrieval 不再盲目给 CLI path 灌 repo chunk 可以降噪提效。风险可控
2. **E 中期**：Brainstorm topology 是使用体验层面的下一个大跃升。但复杂度高，且需要 Phase 58 入口的真实使用反馈来校准 topology 设计
3. **D 后置**：编排能力实际可用，没有真实瓶颈。Planner / DAG 重构回滚成本高，应在真实需求明确后再做

### 战略锚点分析

| 维度 | 蓝图愿景 | 当前现状 | 下一步候选 |
|------|---------|----------|-----------|
| **知识治理** | truth-first 5 阶段检索 + neural retrieval | Stage 1-5 全部实现，神经 embedding + rerank 已接入 | 稳定期 |
| **知识捕获** | 低摩擦入口 + 外部讨论回收 + staged review | Phase 58 已完成 A-lite | 稳定期（完整 Brainstorm 后置为候选 E） |
| **CLI 生态** | aider + claude-code + codex 三足鼎立 | Phase 59 已完成，三者均为独立 route | 稳定期 |
| **检索分流** | retrieval policy 感知 execution family + task intent | 默认 source 不分流，CLI path 可能重复 repo chunk | **候选 C** |
| **Agent 体系** | 7 个专项角色独立生命周期 | 全部落地，LLM 增强已接入 | 稳定期 |
| **执行编排** | 高并发多路 + DAG | fan-out 已落地，Planner / DAG 仍未一等化 | **候选 D**（后置） |
| **思考-讨论-沉淀（完整）** | 受控 Brainstorm topology + multi-route synthesis | A-lite 已落地低摩擦捕获 | **候选 E**（中期） |
| **自我进化** | Librarian + Meta-Optimizer 提案应用闭环 | 已基本完成；自动学习质量仍需提升 | 远期 |

### Tag 评估

| Phase | Tag | Era |
|-------|-----|-----|
| Phase 55 | `v1.1.0` | Knowledge Graph Era |
| Phase 56 | — | Knowledge Graph Era (LLM 增强) |
| Phase 57 | `v1.2.0`（待重打） | Retrieval Quality Era |
| Phase 58-59 | — | Knowledge Capture + CLI Era |

**Phase 59 tag 评估**：

Phase 58-59 一起构成了一个有意义的能力增量：知识捕获入口打通 + CLI 三足鼎立。建议：

- **选项 1（推荐）**：先处理 `v1.2.0` retag（对齐到 Phase 57 embedding + rerank），然后给 Phase 59 merge 后的 main head 打 `v1.3.0`（Knowledge Capture + CLI Era）
- **选项 2**：跳过 v1.2.0 retag，直接在 Phase 59 后打 `v1.3.0`，覆盖 Phase 57-59 全部增量
- **选项 3**：不打 tag，等候选 C 完成后再打一个更大的里程碑 tag

当前 main 稳定（Phase 59 测试全量通过），无进行中的重构或已知破坏性问题，无即将消化的 concern 会改变公共 API。从稳定性角度适合打 tag。

---

## 四、本文件的职责边界

`docs/roadmap.md` 是：
- 跨 phase 蓝图对齐活文档
- 推荐 phase 队列（Claude 维护优先级与风险批注）
- 战略锚点分析（能力维度 × 现状 × 下一步）

`docs/roadmap.md` 不是：
- 当前 phase 状态板（→ `docs/active_context.md`）
- 完整 phase 历史编年（→ git log + `docs/archive/`）
- 设计文档（→ `docs/design/`）
- closeout 索引（→ `docs/plans/<phase>/closeout.md`）
