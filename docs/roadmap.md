---
author: claude
status: living-document
---

# 演进路线图 (Roadmap)

## 一、能力现状与演进方向

> 最近更新：2026-04-26（Phase 57 已 merge，进入 Phase 58 Direction Gate；`v1.2.0` 需 tag 决策 / release docs 同步）

系统已完成 **Foundation Era**（Phase 47-54，v1.0.0 收官）：从 Consensus → Async → Knowledge → Policy → Parallel → Specialist 六个能力代际，把架构债务消化清零，7 个专项 Agent 全部具备独立生命周期，core loop / async runtime / SQLite truth / Librarian / Meta-Optimizer 主线完整。

进入 **Knowledge Loop Era**（Phase 55+）后，演进逻辑从"消化蓝图差距"转为"从可展示的知识闭环出发，逐步扩展系统能力"。每个 phase 是前一个的自然延伸，而不是从蓝图里挑 gap。

### 当前 v1.2.0 候选基线（Phase 57 已 merge）

| 维度 | 现状 |
|------|------|
| **知识治理** | truth-first 双层架构完整，Stage 1-5 全部实现，relation-aware retrieval 落地，LLM 增强 Literature/Quality |
| **检索基础设施** | 神经 API embedding（`text-embedding-3-small`）+ LLM rerank + canonical/verified 路径对齐 |
| **Agent 体系** | 7 个 Specialist Agent 全部独立生命周期，LLM 增强已接入 Literature/Quality |
| **执行编排** | fan-out + timeout + subtask summary 已落地；TaskCard 构造已部分抽到 `planner.py`，但独立 Planner / DAG / Strategy Router 仍未一等化 |
| **自我进化** | Librarian 知识沉淀 + Meta-Optimizer 提案应用闭环 |
| **CLI 路由** | 默认 CLI agent = aider + claude-code；`local-codex` 目前只是 `local-aider` legacy alias，尚无真实 Codex CLI route / config |

### 前瞻性差距表

| 差距 | 蓝图来源 | 当前状态 | 演进方向 |
|------|---------|---------|---------|
| **思考-讨论-沉淀一等流程** | `ORCHESTRATION.md` §2.5 (Brainstorm) + `KNOWLEDGE.md` §5 (外部会话摄入) + Phase 57 review 讨论 | ① Brainstorm topology 已设计但未实现；② Open WebUI 解析器已存在（`parse_open_webui_export`）但结论回流摩擦高（需导出文件 → 手动 ingest）；③ 灵感捕获只能走 `ingest-file`，对"突然冒出来的想法"太重；④ notes source type 作为长期检索源定位模糊（chunk-only、无治理），内容应优先流向 staged knowledge / artifact refs / explicit document refs | **候选方向 A**：先做 A-lite（`swl note` + `swl ingest --from-clipboard` + staged knowledge 出口统一），完整 Brainstorm topology / multi-route synthesis 后置 |
| **Codex CLI 接入（OpenAI 生态等价物）** | `ARCHITECTURE.md` §3 默认执行器分工 + 个人使用习惯 | 默认 CLI agent 只有 `local-aider` / `local-claude-code`；`local-codex` 现为 `local-aider` legacy alias，Codex CLI 尚未在默认 RouteRegistry 中作为真实 route 注册 | **候选方向 B**：在 `AsyncCLIAgentExecutor + CLIAgentConfig` 框架下新增真实 `local-codex` route，并处理 alias migration / 持久化兼容；包含 dialect 选择、binary 探测、能力画像默认值、降级矩阵位置 |
| **路径感知的 Retrieval Policy** | `ARCHITECTURE.md` §4 + Phase 57 review 讨论 | retrieval 默认 source 与执行路径无关；CLI agent（aider / claude-code / codex）有自主文件访问能力，repo retrieval 可能重复消耗；HTTP path 不等价于 agent 自主探索，brainstorm 可聚焦 knowledge + explicit materials，但 HTTP code-analysis 仍可能需要 repo | **候选方向 C**：按 `execution_family + task_intent` 分流 retrieval request；CLI coding path 收缩 repo chunk；HTTP brainstorm path 聚焦 knowledge / explicit refs；HTTP code-analysis 保留可控 repo 检索 |
| **编排显式化（Planner / DAG）** | `ORCHESTRATION.md`（Strategy Router、Planner、DAG 编排） | `planner.py` 已承接部分 TaskCard / input_context 构造，但 Planner 还不是独立接口，DAG dependency orchestration 与 Strategy Router 可观测性仍不足 | **后续方向**：Planner 抽取为独立组件、DAG-based subtask 依赖、Strategy Router 显式化 |
| **能力画像自动学习** | `PROVIDER_ROUTER.md` + `SELF_EVOLUTION.md` | `task_family_scores` / `unsupported_task_types` 已被路由消费，Meta-Optimizer 也能生成 `route_capability` 提案；剩余缺口是更高质量的自动学习、guard 可观测性、model-intel 摄入与 proposal 质量提升 | **后续方向**：从遥测数据与模型情报持续学习 route capability profiles，增强 capability boundary guard 的可解释性 |
| **Runtime v1（原生 async subprocess）** | `HARNESS.md` | harness bridge 为 v0 约束 | 低优先级，功能正常 |
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

---

## 三、推荐 Phase 队列 (Claude 维护)

> 最近更新：2026-04-26（Phase 57 已 merge，等待 Direction Gate 选择 Phase 58 方向）

### 队列总览

| 优先级 | Phase | 名称 | Primary Track | 状态 | 备注 |
|--------|-------|------|---------------|------|------|
| ~~1~~ | ~~55~~ | ~~知识图谱与本地 RAG~~ | ~~Knowledge / RAG~~ | ~~已完成~~ | tag `v1.1.0` |
| ~~2~~ | ~~56~~ | ~~知识质量与 LLM 增强检索~~ | ~~Knowledge / RAG~~ | ~~已完成~~ | merged |
| ~~3~~ | ~~57~~ | ~~检索质量增强~~ | ~~Knowledge / RAG~~ | ~~已完成~~ | merged，待重打 `v1.2.0` |
| **4** | **58** | **(待选)** | **(待选)** | **Direction Gate** | 4 个候选方向待评估 |
| 5 | 59+ | (待选) | — | 方向 | 取决于 Phase 58 选择 |

### Phase 58 候选方向评估

下一 phase 应在以下四个方向中选一个作为主线（其他可作为后续 phase 候选）：

#### 候选 A：思考-讨论-沉淀闭环（Brainstorm + 灵感捕获 + 知识落库）
*   **核心价值**：让"思考-讨论-沉淀"成为系统一等流程，而不是 task 执行的边角附属。短期先降低灵感捕获和外部讨论回收摩擦，统一进入 staged knowledge；完整 Brainstorm topology 后置，避免先上复杂编排但没有稳定输入/沉淀通道。
*   **设计要点**：
    - **A-lite 优先**：先落地 `swl note <text>` 与 `swl ingest --from-clipboard`，把低摩擦输入和 staged knowledge 出口打通；这比先做多模型编排更贴近当前真实使用瓶颈。
    - **外部 brainstorm 知识回收**：Open WebUI 等外部工具的讨论结论通过已有 ingestion pipeline（`parse_open_webui_export()` 等解析器已存在）回流到 staged knowledge。新增 `swl ingest --from-clipboard --format open_webui_json|markdown` 减少导出落盘摩擦。
    - **灵感捕获**：`swl note <text> [--tag <topic>]` 直接 wrap ingestion pipeline，写入 staged knowledge raw 阶段（`source_kind=operator_note`），几秒钟入库，进入现有 review/promote 流程。
    - **受控 Brainstorm 后置**：基于 `ORCHESTRATION.md §2.5` Brainstorm 设计，后续再落地 `DebateConfig` + `BrainstormOrchestrator`。它应是受控 topology / multi-route synthesis，产出结构化 artifact，不把 raw chat history 当作知识对象直接持久化。
    - **统一出口**：无论 Swallow 内部 brainstorm 的 synthesis artifact，还是 Open WebUI 外部讨论的导出，还是 `swl note` 灵感，全部走同一条 staged knowledge → review → promote/reject 管线。不引入新的知识存储通道。
*   **可能 slice**：
    - S1：`swl note <text> [--tag]` 灵感捕获 CLI，写入 staged knowledge
    - S2：`swl ingest --from-clipboard --format open_webui_json|markdown` 外部 brainstorm 低摩擦入口
    - S3：ingestion source metadata / summary 与 staged review visibility 收紧，确保 reviewer 能判断 source_ref、topic、候选质量
    - S4：brainstorm synthesis artifact → staged knowledge 自动候选通道（可作为 Phase 58 stretch 或 Phase 59 起点）
*   **风险**：低到中 — A-lite 主要复用 ingestion pipeline 与 staged knowledge，破坏性低；完整 BrainstormOrchestrator 涉及新编排组件，应在低摩擦捕获稳定后再做
*   **依赖**：Phase 56 `agent_llm.py` / HTTP executor 路由 + Phase 57 retrieval 基线 + 现有 ingestion pipeline（`parse_open_webui_export` 等）
*   **优先级理由**：贴合个人使用习惯、能立刻见效；打通"灵感 / 外部讨论 → staged → review → canonical"闭环后，系统从"任务执行工具"升级为"思考-执行一体工具"，这是使用体验层面的质变

#### 候选 B：CLI Agent 生态完善（Codex CLI 接入 + 默认配置整理）
*   **核心价值**：让 OpenAI / Anthropic / Aider 三大 CLI agent 在系统里同等地位，符合个人使用习惯
*   **可能 slice**：(1) 解除 `local-codex -> local-aider` legacy alias 冲突并保留旧 policy 兼容；(2) `local-codex` route 注册 + `CLIAgentConfig` 实例；(3) dialect / binary / 能力画像默认值；(4) 降级矩阵位置与 doctor 探针
*   **风险**：低 — 框架已就位，只是新增配置实例
*   **依赖**：Phase 52 `AsyncCLIAgentExecutor` + Phase 54 dialect 体系
*   **优先级理由**：单点缺口、范围明确、规模小（类似 Phase 54 的 cleanup phase）

#### 候选 C：路径感知的 Retrieval Policy（执行路径分流）
*   **核心价值**：retrieval 按 execution path 和 task intent 分流。CLI coding path 可减少 repo chunk，因为 CLI agent 能自主探索文件；HTTP brainstorm path 可聚焦 knowledge / explicit materials；HTTP code-analysis path 不能假设 agent 会自主读 repo，仍可能需要受控 repo 检索。
*   **可能 slice**：(1) execution family + task intent 判定接入 retrieval request 构造；(2) CLI coding path 默认 source 收紧为 knowledge / explicit refs，repo 交给 agent 自主探索；(3) HTTP brainstorm path 默认 source 调整为 knowledge / explicit materials；(4) HTTP code-analysis 保留可控 repo 检索；(5) notes 作为长期检索源收缩，内容优先流向 staged knowledge / artifact refs / explicit document refs
*   **风险**：中 — 涉及 retrieval 默认行为变化，需配套测试
*   **依赖**：Phase 57 retrieval 基线；候选 A 落地后对 notes 角色有更清晰判断
*   **优先级理由**：架构正确性提升，但当前 repo retrieval 不构成阻塞；建议在候选 A 的真实使用反馈后再决策

#### 候选 D：编排增强（Planner / DAG / Strategy Router 显式化）
*   **核心价值**：把已部分抽出的 planning 能力继续一等化，形成明确 Planner 接口、DAG dependency orchestration 与 Strategy Router 可观测边界
*   **可能 slice**：(1) Planner 接口抽取；(2) DAG-based subtask 依赖；(3) Strategy Router 显式化
*   **风险**：高 — 涉及 orchestrator 主链路重构，回滚成本高
*   **依赖**：Phase 52 fan-out 基线
*   **优先级理由**：架构债务清理，但当前编排能力实际可用，没有真实瓶颈推动

### Claude 推荐顺序

**A → B → C → D**

理由：
1. **A 优先**：贴合你的实际使用场景（讨论 / 灵感捕获 / 外部会话回收），低风险高反馈。建议 Phase 58 先做 A-lite：`swl note`、clipboard ingest、staged review visibility；完整 Brainstorm topology 不作为第一刀
2. **B 紧随**：单点缺口、规模小（类似 Phase 54 的 cleanup phase），能在 1-2 个 slice 内收口；但要先处理 `local-codex` legacy alias 与既有 route policy 兼容
3. **C 中期**：架构正确性提升，但需要 A/B 之后真实使用反馈才知道当前 repo retrieval 是否真的造成困扰
4. **D 后置**：当前编排能力够用，`planner.py` 已消化一部分局部结构；没有真实瓶颈前，过早重构 orchestrator 主链路风险高

### 战略锚点分析

| 维度 | 蓝图愿景 | v1.2.0 现状 | 下一步候选 |
|------|---------|------------|-----------|
| **知识治理** | truth-first 5 阶段检索 + neural retrieval | Stage 1-5 全部实现，神经 embedding + rerank 已接入 | 稳定期 |
| **思考-讨论-沉淀** | 受控 Brainstorm topology + 灵感低摩擦捕获 + 外部讨论回收 + staged → canonical 管线 | brainstorm 已设计未实现；Open WebUI 解析器存在但回流摩擦高；灵感捕获无低摩擦入口；notes source type 作为长期检索源定位模糊 | **候选 A** |
| **CLI 生态** | aider + claude-code + codex 三足鼎立 | aider + claude-code 已默认，`local-codex` 只是 `local-aider` legacy alias | **候选 B** |
| **检索分流** | retrieval policy 感知 execution family + task intent | retrieval 默认 source 不分流，CLI coding path 可能重复 repo chunk，HTTP brainstorm / code-analysis 尚未区分 | **候选 C** |
| **Agent 体系** | 7 个专项角色独立生命周期 | 全部落地，LLM 增强已接入 | 稳定期 |
| **执行编排** | 高并发多路 + DAG | fan-out 已落地，TaskCard 构造已部分抽到 `planner.py`，独立 Planner / DAG 仍未一等化 | **候选 D**（后置） |
| **自我进化** | Librarian + Meta-Optimizer 提案应用闭环 | route capability 已被路由消费并可由提案更新；自动学习质量与 guard 可观测性仍需提升 | 远期：能力画像自动学习 |

### Tag 评估

| Phase | Tag | Era |
|-------|-----|-----|
| Phase 55 | `v1.1.0` | Knowledge Graph Era |
| Phase 56 | — | Knowledge Graph Era (LLM 增强) |
| Phase 57 | `v1.2.0`（待重打） | Retrieval Quality Era |

**Phase 57 tag 处理建议**：当前 `v1.2.0` 指向 Phase 56 merge commit（commit `ef7d0b1`，message "LLM enhaced retrieval"），与 Phase 57 实际能力增量不对齐。建议：

1. Codex 同步 README / AGENTS.md 中的 v1.2.0 能力描述到 Phase 57（embedding + rerank）
2. Human 执行 `git tag -d v1.2.0` + `git push origin :refs/tags/v1.2.0` 删除旧 tag
3. Human 在 release docs 同步后的 main head 重新打 `git tag -a v1.2.0 -m "Retrieval Quality Era: neural embedding + LLM rerank"`；不要直接打在旧 Phase 57 merge commit 上，否则 tag-level docs 仍可能与 tag 不一致

也可以选择不重打，给 Phase 57 单独打 v1.3.0；但当前 v1.2.0 message 与实际不符的问题仍需修复。

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
