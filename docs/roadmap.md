---
author: claude
status: living-document
---

# 演进路线图 (Roadmap)

## 一、能力现状与演进方向

> 最近更新：2026-04-26（Phase 57 已 merge，准备重打 `v1.2.0`）

系统已完成 **Foundation Era**（Phase 47-54，v1.0.0 收官）：从 Consensus → Async → Knowledge → Policy → Parallel → Specialist 六个能力代际，把架构债务消化清零，7 个专项 Agent 全部具备独立生命周期，core loop / async runtime / SQLite truth / Librarian / Meta-Optimizer 主线完整。

进入 **Knowledge Loop Era**（Phase 55+）后，演进逻辑从"消化蓝图差距"转为"从可展示的知识闭环出发，逐步扩展系统能力"。每个 phase 是前一个的自然延伸，而不是从蓝图里挑 gap。

### 当前 v1.2.0 候选基线（Phase 57 已 merge）

| 维度 | 现状 |
|------|------|
| **知识治理** | truth-first 双层架构完整，Stage 1-5 全部实现，relation-aware retrieval 落地，LLM 增强 Literature/Quality |
| **检索基础设施** | 神经 API embedding（`text-embedding-3-small`）+ LLM rerank + canonical/verified 路径对齐 |
| **Agent 体系** | 7 个 Specialist Agent 全部独立生命周期，LLM 增强已接入 Literature/Quality |
| **执行编排** | fan-out + timeout + subtask summary 已落地；planner 逻辑仍嵌入 orchestrator |
| **自我进化** | Librarian 知识沉淀 + Meta-Optimizer 提案应用闭环 |
| **CLI 路由** | 默认 CLI agent = aider + claude-code；codex CLI 未接入 |

### 前瞻性差距表

| 差距 | 蓝图来源 | 当前状态 | 演进方向 |
|------|---------|---------|---------|
| **思考-讨论-沉淀一等流程** | `ORCHESTRATION.md` §2.5 (Brainstorm) + `KNOWLEDGE.md` §5 (外部会话摄入) + Phase 57 review 讨论 | ① Brainstorm topology 已设计（`DebateConfig`）但未实现；② Open WebUI 解析器已存在（`parse_open_webui_export`）但结论回流摩擦高（需导出文件 → 手动 ingest）；③ 灵感捕获只能走 `ingest-file`，对"突然冒出来的想法"太重；④ notes source type 定位模糊（chunk-only、无治理），应流向 staged knowledge | **候选方向 A**：`DebateConfig` + `BrainstormOrchestrator` 多模型群聊落地；brainstorm synthesis → staged knowledge 自动候选；`swl ingest --from-clipboard` 外部讨论低摩擦回收；`swl note` 灵感捕获；统一出口走 staged → review → promote |
| **Codex CLI 接入（OpenAI 生态等价物）** | `ARCHITECTURE.md` §3 默认执行器分工 + 个人使用习惯 | 默认 CLI agent 只有 `local-aider` / `local-claude-code`；Codex CLI 作为 OpenAI 生态等价物未在默认 RouteRegistry 中注册 | **候选方向 B**：在 `AsyncCLIAgentExecutor + CLIAgentConfig` 框架下新增 `local-codex` route，与 aider / claude-code 同等地位；包含 dialect 选择、binary 探测、能力画像默认值、降级矩阵位置 |
| **路径感知的 Retrieval Policy** | `ARCHITECTURE.md` §4 + Phase 57 review 讨论 | retrieval 默认 source 与执行路径无关；CLI agent（aider / claude-code / codex）有自主文件访问能力，repo retrieval 重复消耗；HTTP path 是讨论 / brainstorm 主路径，不必纠结 repo 读取 | **候选方向 C**：CLI agent path 默认只带 knowledge/notes 摘要，repo 交给 agent 自主探索；HTTP path 面向讨论场景，默认带 knowledge（repo 留给 agent） |
| **编排显式化（Planner / DAG）** | `ORCHESTRATION.md`（Strategy Router、Planner、DAG 编排） | planner 逻辑嵌入 orchestrator | **候选方向 E**：Planner 抽取为独立组件、DAG-based subtask 依赖、Strategy Router 显式化 |
| **能力画像自动学习** | `PROVIDER_ROUTER.md` + `SELF_EVOLUTION.md` | `unsupported_task_types` 字段存在但未消费 | **候选方向 F**：从遥测数据自动学习 route capability profiles、capability boundary guard 激活 |
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
*   **Tag**：v1.2.0（候选，待重打指向 Phase 57 merge commit）

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
*   **核心价值**：让"思考-讨论-沉淀"成为系统一等流程，而不是 task 执行的边角附属。把 HTTP path 重新定位为"讨论 / brainstorm 主路径"，同时打通两条讨论入口（Open WebUI 外部 brainstorm + Swallow 内部多模型 brainstorm）到 staged knowledge 的落库通道。
*   **设计要点**：
    - **Swallow 内部 brainstorm**：基于 `ORCHESTRATION.md §2.5` Brainstorm 设计，落地 `DebateConfig` + `BrainstormOrchestrator`。每轮参与者顺序发言并累积上下文，最终由仲裁者收口为结构化 synthesis artifact。参与者绑定不同 HTTP route（`http-claude` / `http-qwen` / `http-glm` / `http-gemini`），形成多模型群聊。角色定义通过 prompt prefix 注入，不引入新 agent 类型。
    - **外部 brainstorm 知识回收**：Open WebUI 等外部工具的讨论结论通过已有 ingestion pipeline（`parse_open_webui_export()` 等解析器已存在）回流到 staged knowledge。新增 `swl ingest --from-clipboard --format open-webui` 减少导出落盘摩擦。
    - **灵感捕获**：`swl note <text> [--tag <topic>]` 直接 wrap ingestion pipeline，写入 staged knowledge raw 阶段（`source_kind=operator_note`），几秒钟入库，进入现有 review/promote 流程。
    - **两条入口统一出口**：无论 Swallow 内部 brainstorm 的 synthesis artifact，还是 Open WebUI 外部讨论的导出，还是 `swl note` 灵感，全部走同一条 staged knowledge → review → promote/reject 管线。不引入新的知识存储通道。
*   **可能 slice**：
    - S1：`DebateConfig` 数据结构 + `BrainstormOrchestrator` 落地（多模型顺序发言 + 仲裁收口）
    - S2：brainstorm synthesis artifact → staged knowledge 自动候选通道
    - S3：`swl ingest --from-clipboard` 外部 brainstorm 低摩擦入口
    - S4：`swl note <text>` 灵感捕获 CLI
*   **风险**：中 — S1 涉及新编排组件但复用 HTTPExecutor 基础设施；S2/S3/S4 均为 additive 无破坏性
*   **依赖**：Phase 56 `agent_llm.py` / HTTP executor 路由 + Phase 57 retrieval 基线 + 现有 ingestion pipeline（`parse_open_webui_export` 等）
*   **优先级理由**：贴合个人使用习惯、能立刻见效；打通"灵感 → staged → review → canonical"闭环后，系统从"任务执行工具"升级为"思考-执行一体工具"，这是使用体验层面的质变

#### 候选 B：CLI Agent 生态完善（Codex CLI 接入 + 默认配置整理）
*   **核心价值**：让 OpenAI / Anthropic / Aider 三大 CLI agent 在系统里同等地位，符合个人使用习惯
*   **可能 slice**：(1) `local-codex` route 注册 + CLIAgentConfig 实例；(2) dialect / binary / 能力画像默认值；(3) 降级矩阵位置；(4) doctor 探针
*   **风险**：低 — 框架已就位，只是新增配置实例
*   **依赖**：Phase 52 `AsyncCLIAgentExecutor` + Phase 54 dialect 体系
*   **优先级理由**：单点缺口、范围明确、规模小（类似 Phase 54 的 cleanup phase）

#### 候选 C：路径感知的 Retrieval Policy（执行路径分流）
*   **核心价值**：retrieval 按 execution path 分流 — CLI agent 路径不再消耗 repo chunk（agent 自主探索更有效），HTTP path 面向讨论场景聚焦 knowledge（不必纠结 repo 读取）
*   **可能 slice**：(1) execution path 判定接入 retrieval request 构造；(2) CLI agent path 默认 source 收紧为 knowledge/notes 摘要；(3) HTTP path 默认 source 面向讨论场景调整；(4) 评估 notes source type 退场可行性
*   **风险**：中 — 涉及 retrieval 默认行为变化，需配套测试
*   **依赖**：Phase 57 retrieval 基线；候选 A 落地后对 notes 角色有更清晰判断
*   **优先级理由**：架构正确性提升，但当前 repo retrieval 不构成阻塞；建议在候选 A 的真实使用反馈后再决策

#### 候选 D：编排增强（Planner / DAG / Strategy Router 显式化）
*   **核心价值**：把嵌入 orchestrator 的 planner 逻辑抽出为独立组件，支持 DAG 依赖
*   **可能 slice**：(1) Planner 接口抽取；(2) DAG-based subtask 依赖；(3) Strategy Router 显式化
*   **风险**：高 — 涉及 orchestrator 主链路重构，回滚成本高
*   **依赖**：Phase 52 fan-out 基线
*   **优先级理由**：架构债务清理，但当前编排能力实际可用，没有真实瓶颈推动

### Claude 推荐顺序

**A → B → C → D**

理由：
1. **A 优先**：贴合你的实际使用场景（讨论 / 灵感捕获 / 多模型 brainstorm），低风险高反馈，系统从"任务执行工具"升级为"思考-执行一体工具"。且基础设施已大量就绪（ingestion pipeline、HTTP executor routing、agent_llm）
2. **B 紧随**：单点缺口、规模小（类似 Phase 54 的 cleanup phase），能在 1-2 个 slice 内收口
3. **C 中期**：架构正确性提升，但需要 A/B 之后真实使用反馈才知道当前 repo retrieval 是否真的造成困扰
4. **D 后置**：当前编排能力够用，没有真实瓶颈；过早重构 orchestrator 主链路风险高

### 战略锚点分析

| 维度 | 蓝图愿景 | v1.2.0 现状 | 下一步候选 |
|------|---------|------------|-----------|
| **知识治理** | truth-first 5 阶段检索 + neural retrieval | Stage 1-5 全部实现，神经 embedding + rerank 已接入 | 稳定期 |
| **思考-讨论-沉淀** | brainstorm 多模型群聊 + 灵感低摩擦捕获 + 外部讨论回收 + staged → canonical 管线 | brainstorm 已设计未实现；Open WebUI 解析器存在但回流摩擦高；灵感捕获无低摩擦入口；notes source type 定位模糊 | **候选 A** |
| **CLI 生态** | aider + claude-code + codex 三足鼎立 | aider + claude-code 已默认，codex 缺失 | **候选 B** |
| **检索分流** | retrieval policy 感知 execution path | retrieval 默认 source 不分流，CLI agent 路径仍消耗 repo chunk | **候选 C** |
| **Agent 体系** | 7 个专项角色独立生命周期 | 全部落地，LLM 增强已接入 | 稳定期 |
| **执行编排** | 高并发多路 + DAG | fan-out 已落地，planner 仍嵌入 orchestrator | **候选 D**（后置） |
| **自我进化** | Librarian + Meta-Optimizer 提案应用闭环 | 主线完整 | 远期：能力画像自动学习 |

### Tag 评估

| Phase | Tag | Era |
|-------|-----|-----|
| Phase 55 | `v1.1.0` | Knowledge Graph Era |
| Phase 56 | — | Knowledge Graph Era (LLM 增强) |
| Phase 57 | `v1.2.0`（待重打） | Retrieval Quality Era |

**Phase 57 tag 处理建议**：当前 `v1.2.0` 指向 Phase 56 merge commit（commit `ef7d0b1`，message "LLM enhaced retrieval"），与 Phase 57 实际能力增量不对齐。建议：

1. Codex 同步 README / AGENTS.md 中的 v1.2.0 能力描述到 Phase 57（embedding + rerank）
2. Human 执行 `git tag -d v1.2.0` + `git push origin :refs/tags/v1.2.0` 删除旧 tag
3. Human 在 main 当前 head（Phase 57 merge commit `aa35ac9`）重新打 `git tag -a v1.2.0 -m "Retrieval Quality Era: neural embedding + LLM rerank"`

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
