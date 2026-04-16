---
author: gemini
status: living-document
---

# 蓝图差距与演进路线图 (Gap Analysis & Roadmap)

## 一、当前实现与蓝图设计的核心差距 (Gap Analysis)

根据最新修订的 `ARCHITECTURE.md` 与 `docs/design/*.md`，项目定位已从“多模型文件协同”正式升级为**“本地优先的统一调度系统 (Local-first Unified Scheduling System)”**。

当前代码实现与新架构蓝图之间存在以下重大差距：

### 1. 编排层 (Orchestrator Layer) 缺失核心组件
*   **蓝图要求**：系统需自建轻量的 Runtime v0，包含 `Router`（统一路由）、`Planner`（任务拆解）、`Subtask Orchestrator`（平台级子代理编排）和 `Review Gate`（审查门禁）。厂商 Agent（如 Codex CLI / Gemini CLI）只作为底层 Executor 接入。
*   **当前现状**：目前高度依赖基于 Markdown 文件（如 `.agents/shared/read_order.md`, `AGENTS.md`）的协同，调度逻辑隐式地散落在人工触发的命令行指令和工作流文档中。
*   **核心差距**：缺乏统一的、代码化的调度中枢（Dispatcher/Runtime v0），平台级的 Subagent 并发能力尚未建立。

### 2. 知识层：未实现 LLM Wiki 与 RAG 的分离
*   **蓝图要求**：建立“知识双层架构”。底层为 `Enhanced RAG`（原始证据层，包含 Graph RAG），上层为 `LLM Wiki`（高层认知层）。必须严格通过 `Librarian Agent` 进行提纯、冲突仲裁和衰减管理，禁止普通 Agent 随意写回全局知识。
*   **当前现状**：目前知识沉淀主要通过 Obsidian 笔记和基础的 `Staged -> Canonical` 命令实现。
*   **核心差距**：缺乏结构化的 `LLM Wiki` 概念，没有专门守护认知层质量的 `Librarian Agent` 工作流，缺乏 `Ingestion Specialist` 来处理外部会话的结构化摄入。

### 3. Agent 认知分层与兜底策略 (Fallback Matrix) 缺失
*   **蓝图要求**：通用 Agent 应按照高阶认知能力分为三层（Codex: 施工, Claude: 规划/审查, Gemini: 知识整合）。且必须具备严密的“通用认知替补与降级矩阵”，当任一环节故障时能够降级调度（如：强模型挂了，降级由小模型逐行施工；丢失 Gemini 长上下文缓存，强制启动 Librarian 压缩摘要）。
*   **当前现状**：目前主要通过人工指定使用哪个 CLI 工具，或简单的 `router.py` 进行静态转发。
*   **核心差距**：缺少基于认知角色的智能调度器和动态平滑降级（Graceful Degradation）处理机制。

### 4. 专项代理生态 (Specialist Agents) 与无状态审查者空缺
*   **蓝图要求**：明确引入 `Librarian Agent`, `Ingestion Specialist`, `Literature Specialist` 以及只读的 `Meta-Optimizer`，并强制引入 Stateless 的 `Quality Reviewer` 守住质量底线。
*   **当前现状**：系统仍在使用“全能型”思维调用大模型，专项边界划分不明显，且没有独立的 Review Gate 防线。

---

## 二、架构演进 Roadmap (5 Phases)

为弥补上述差距，推荐按以下 5 个 Phase 稳步重构与演进：

### Phase 31: Runtime v0 与统一执行器抽象 (Foundation)
*   **目标**：将“基于文档约定”的隐式调度，转化为由代码驱动的显式 Runtime 中枢。
*   **核心任务**：
    *   构建基础的 `Planner` 与 `Router` 模块，将宏观目标转化为标准化的 `Task Cards`。
    *   定义统一的 Executor Interface（执行器接口），将直连 API 的 `ModelExecutor` 和封装外部工具的 `AgentExecutor`（如 Codex CLI Wrapper）纳入同一抽象。
    *   引入无状态的 `Review Gate`（质量审查门禁）：所有 Executor 产出写入状态前，强制进行 Schema 校验与基本通过性检查。
*   **产出价值**：确立 Swallow 作为“统一调度系统”的绝对主权，厂商 Agent 正式退为底层工具。

### Phase 32: 知识双层架构与 Librarian Agent 落地 (Memory & Quality)
*   **目标**：拆分 RAG 证据层与 LLM Wiki 认知层，实施严格的知识晋升防线。
*   **核心任务**：
    *   在知识库设计上正式区分 `Raw Evidence Store` 与 `LLM Wiki Store`。
    *   实现 **Librarian Agent (图书管理员)**：开发专用的知识沉淀工作流，由该 Agent 接管 `Staged-Knowledge` 的合并仲裁、降噪提炼，并产出 Change Log。
    *   实现 **Ingestion Specialist (外部会话摄入者)**：建立从 ChatGPT/Claude Web 导出文件到系统 `HandoffContractSchema` 的结构化转换链路。
*   **产出价值**：彻底解决多 Agent 协作带来的隐式记忆污染问题，确保系统上下文越用越精炼。

### Phase 33: 编排策略升级与 Subtask Orchestrator (Parallelism)
*   **目标**：解锁宏大任务的“包工头”模式与并发执行能力。
*   **核心任务**：
    *   开发 `Subtask Orchestrator` 组件，支持 `Planner` 生成的多子任务（Subtasks）并发下发给多个专项 Agent。
    *   实现“对抗与审查拓扑 (Debate / Review Topology)”：在 `Coding Agent` 与 `Review Agent` 之间建立 State Store 驱动的自动打回与重试机制（Review Feedback Loop）。
    *   开发 `Literature Specialist` 等基于便宜/本地模型的降级专项工种。
*   **产出价值**：突破单线程任务链瓶颈，实现真正的平台级多智能体协同网络。

### Phase 34: 认知模型路由与全局降级兜底网格 (Resilience)
*   **目标**：实现能力协商、方言翻译以及防止单点故障的降级矩阵。
*   **核心任务**：
    *   完善 `Dialect Translators`：全面落实 Claude XML、Codex FIM 与 Gemini Context Caching 的底层 Prompt 装配逻辑。
    *   实现 **认知角色替补与降级矩阵 (Cognitive Role Fallback Matrix)**：由 Strategy Router（编排层）与 Model Gateway（第 6 层）协作完成。Strategy Router 负责策略判断（能力下限断言、降级粒度决策、`waiting_human` 挂起），Gateway 负责执行层面的通道切换和 ReAct 格式降级。当主力执行器（如 Codex/Claude/Gemini）不可用时，Strategy Router 决定降级策略，Gateway 执行通道替补。
    *   支持**同角色多执行器并存**：在 `resolve_executor()` 中注册多个实现（如 Codex + Cursor），Strategy Router 根据任务类型、可用性或用户偏好选择具体执行器。
*   **产出价值**：构建极高可用性的本地调度系统，无惧外部 API 波动。

### Phase 35: 自我进化与 Meta-Optimizer 顾问 (Self-Evolution)
*   **目标**：闭环系统的长期成长能力。
*   **核心任务**：
    *   完善底层的错误日志采集与指纹聚类 (Telemetry)。
    *   引入纯只读的 **Meta-Optimizer Agent (编排策略顾问)**：定期被定时任务唤醒，扫描最近 100 个任务的 Event Logs，输出包含”新 Workflow 建议”、”Skill 调整”和”路由优化”的系统提案 (Proposals) 供人类审查。
    *   探索向混合云 / Remote Worker 形态的演进验证。
*   **产出价值**：系统具备了基于真实历史数据”自我反思”和提请架构进化的能力。

---

## 三、推荐 Phase 队列：优先级排序与风险批注 (Claude 维护)

> 本节由 Claude 维护，基于差距分析和依赖关系进行优先级排序与风险评估。
> 最近更新：2026-04-15

### 队列总览

| 优先级 | Phase | 名称 | Primary Track | Secondary Track | 风险等级 |
|--------|-------|------|---------------|-----------------|----------|
| 1 | 31 | Runtime v0 — Planner + Executor Interface + Review Gate | Core Loop | Execution Topology | 中 |
| 2 | 32 | 知识双层架构 + Librarian Agent | Retrieval / Memory | — | 中 |
| 3 | 33 | Subtask Orchestrator + 并发编排 | Execution Topology | Core Loop | 中高 |
| 4 | 34 | Dialect Translators + 降级矩阵 | Execution Topology | Evaluation / Policy | 高 |
| 5 | 35 | Meta-Optimizer + 自我进化 | Evaluation / Policy | — | 低 |

### 依赖关系

```
Phase 31 (Runtime v0)
  ├──→ Phase 32 (知识双层 + Librarian)
  ├──→ Phase 33 (Subtask Orchestrator)  [依赖 31 Executor Interface]
  └──→ Phase 34 (Dialect + 降级)        [依赖 31 Router + 33 Executor 稳定]
          └──→ Phase 35 (Meta-Optimizer) [依赖 31-33 Event Log schema freeze]
```

Phase 32 与 33 无硬依赖，理论可并行，建议串行以控制带宽。

### 各 Phase 风险批注

**Phase 31 — Runtime v0**
- ⚠️ Scope 膨胀风险：Planner 和 Router 应严格限制在”静态路由 + Task Card 标准化”级别，v0 不引入动态能力协商。
- Review Gate 只做 Schema 校验 + 基本通过性检查，不做语义级审查。

**Phase 32 — 知识双层 + Librarian**
- ⚠️ 建议拆分：Ingestion Specialist 应延后至 Phase 32 stretch slice 或 Phase 33 附加。Librarian Agent 的写回防线是核心，需独立验证后再引入外部会话摄入链路。
- 依赖 Phase 31 的 Executor Interface 已稳定。

**Phase 33 — Subtask Orchestrator**
- ⚠️ 收窄 Review Feedback Loop：Phase 33 只建立”Review Gate 触发 retry”的单向链路。完整的 Debate/Review Topology（双向自动协商）延后，因其跨模块复杂度 ≥7。
- Literature Specialist 可作为验证并发编排的 PoC 专项工种同步实现。

**Phase 34 — Dialect + 降级矩阵**
- ⚠️ 本路线风险最高的 Phase。建议分期：Phase 34 仅实现 Dialect Translator 框架 + 1-2 个 concrete dialect（Claude XML + Codex FIM），降级矩阵只做”主力不可用时 fallback 到通用 API”的最简二元降级。全量降级策略追加到 Phase 35。
- 降级矩阵的职责已拆分：Strategy Router（编排层 §2.1）做策略判断，Model Gateway（第 6 层 §4.1）做通道切换。Phase 34 需同步实现两侧。
- 可同步验证多执行器并存：注册 Cursor executor 作为 Codex 的备选执行器 PoC。

**Phase 35 — Meta-Optimizer**
- 探索性 Phase，风险低。准入条件：Phase 31-33 的 Event Log schema 已 freeze。Telemetry 数据采集依赖前序 Phase 的事件格式稳定。