---
author: gemini
status: living-document
---

# 蓝图差距与演进路线图 (Gap Analysis & Roadmap)

## 一、当前实现与蓝图设计的核心差距 (Gap Analysis)

根据最新修订的 `ARCHITECTURE.md` 与最近完成的 Phase 45 (Eval基线)，Swallow 系统内核已趋于稳定，但与真正的“本地优先统一调度系统”蓝图相比，暴露出一个最严重的基础设施断层，以及若干演进差距：

### 1. [最紧急] 单点 CLI 代理与原生 Gateway 的断层 (CLI Proxy vs Native Gateway)
*   **蓝图要求**：第 6 层（Gateway Core）应将上层语义路由精准翻译为对不同物理端点（new-api, TensorZero 等）的原生 HTTP 调用，并配合不同模型的方言适配器。
*   **当前现状**：`executor.py` 内部硬编码了 `subprocess.run(["codex"])`，导致编排层辛辛苦苦算出的多模型路由策略全部失效，流量全部流向单一 CLI 代理。
*   **核心差距**：系统没有真正的网络分发权，“多模型生态”和“交叉审查”地基不存。

### 2. 本地栈集成与真实成本感知 (Local Stack & Real Cost)
*(已于 Phase 42 建立基线，并在 Phase 45 接入 Eval，该项差距已基本弥合)*

### 3. 从单体审查向多机/多 Agent 共识演进 (Consensus Topology)
*   **蓝图要求**：支持多 Reviewer 对话拓扑，通过多模型共识（Majority Pass）确保输出质量。
*   **当前现状**：目前的 `ReviewGate` 仅支持单 Reviewer 模式；且受限于单一 CLI 代理，无法同时呼叫多种模型互查。
*   **核心差距**：系统缺乏冗余校验，极易被单一模型的幻觉带偏。

### 4. 存储层与执行引擎的并发瓶颈 (Storage & Async Bottlenecks)
*   **蓝图要求**：支持长周期、高并发的多路子任务与知识对比。
*   **当前现状**：调度与执行重度依赖同步阻塞（Synchronous IO）及文件系统（JSON/Markdown）进行状态流转。
*   **核心差距**：无法支撑未来规模化的并发拓扑，且文件系统缺乏事务保证与复杂查询追踪能力。

---

## 二、架构演进 Roadmap (Phases 46-48)

基于前序 Phase (41-45) 已将内核与监控基线打通，接下来系统必须停止往上层堆叠策略，转而“向底层深挖”，填补基础设施空白。

### Phase 46: 模型网关物理层实装 (Gateway Core Materialization) 🚀 [Next]
*   **Primary Track**: Execution Topology
*   **Secondary Track**: Capabilities
*   **目标**：彻底废除单点 CLI 依赖，实现原生的多模型 HTTP 网络接入与真实的方言闭环。
*   **核心任务**：
    - **网络执行器 (HTTP Executor)**：在 Python 层引入 `httpx` 直连本地 `new-api`（暂时移除较重的 TensorZero 依赖，将其降级为未来可选插件），替代 `subprocess.run`。
    - **方言与端点对齐 (Dialect Alignment)**：补齐 Gemini 等适配器，确保 `route_model_hint` 严格决定物理路由，让 Claude 收到 `<thinking>`、让代码模型收到 FIM。
    - **降级矩阵 (Fallback Matrix)**：落地真正的异常捕获与“跨模型族”的平滑降级（如断网、限流时自动切换）。
*   **产出价值**：系统真正拥有了网络分发权，名副其实地成为一个“多模型”编排引擎。

### Phase 47: 多模型共识与策略护栏 (Consensus & Policy Guardrails)
*   **Primary Track**: Evaluation / Policy
*   **Secondary Track**: Core Loop
*   **目标**：在具备真实多模型调度能力（Phase 46）的基础上，引入冗余审查机制，自动管控风险。
*   **核心任务**：
    - **N-Reviewer 共识拓扑**：支持 TaskCard 配置多个审查模型，实现”多数票通过”或”首席模型否决”。
    - **智能预算策略**：基于历史成本数据实现自动熔断与财务自律。
    - **跨模型抽检**：由强模型定期审计低成本模型的海量中间产物。
*   **产出价值**：系统具备极强的自我纠偏能力，适应高风险、高强度的无人值守运行。

### Phase 48: 存储引擎升级与全异步改造 (Storage & Async Engine)
*   **Primary Track**: Core Loop
*   **Secondary Track**: State / Truth
*   **目标**：重构系统的 IO 模型与状态存储，支撑下一代高并发任务树。
*   **核心任务**：
    - **调度全异步化**：将 Orchestrator 和 Executor 的核心链路迁移至 `asyncio`。
    - **轻量化本地数据库化 (SQLite)**：**放弃 PostgreSQL，引入 SQLite (WAL 模式) + `sqlite-vec` 向量扩展。**将 `TaskState`、`EventLog` 和 RAG 知识索引全部迁移至本地 `.swl/swallow.db`，实现系统的零依赖跨平台部署。
*   **产出价值**：彻底消除并行子任务的 IO 阻塞瓶颈，大幅降低系统部署门槛（回归真正的纯本地 CLI 体验）。

---

## 三、推荐 Phase 队列与风险批注 (Claude 维护)

> 最近更新：2026-04-20 (Phase 46 完成，更新队列状态与 Phase 47 前置验证要求)

### 队列总览

| 优先级 | Phase | 名称 | Primary Track | Secondary Track | 风险等级 |
|--------|-------|------|---------------|-----------------|----------|
| ~~1~~ | ~~41-45~~| ~~Librarian 收口 / 工作台 / 外部摄入 / Eval 基线~~ | ~~...~~ | ~~...~~ | ~~已完成~~ |
| ~~2~~ | ~~46~~ | ~~模型网关物理层实装 (Gateway Core Materialization)~~ | ~~Execution Topology~~ | ~~Capabilities~~ | ~~已完成，tag v0.4.0~~ |
| **3** | **47** | **多模型共识与策略护栏** | **Evaluation / Policy** | **Core Loop** | **中** |
| 4 | 48 | 存储引擎升级与全异步改造 | Core Loop | State / Truth | 高 |

### 依赖关系

```
Phase 45 (Eval 基线) ✅
  └──→ Phase 46 (Gateway 网关) ✅ tag v0.4.0
         └──→ Phase 47 (多模型共识：依赖真实的底层多模型分发能力)
                └──→ Phase 48 (全异步：提升并发调度的性能)
```

### ~~Phase 46 — 模型网关物理层实装~~（已完成）

已完成，tag `v0.4.0`。`HTTPExecutor` 落地，`CLIAgentExecutor` 去品牌化，5 条 HTTP 路由 + `local-cline` 注册，降级链 `http-claude → http-qwen → http-glm → local-cline → local-summary` 有循环检测保护，429 rate-limit 走重试路径。342 passed，4 eval passed。

### Phase 47 — 多模型共识与策略护栏（当前最优先级）

**风险批注**：中。Phase 46 已提供真实多模型分发能力，Phase 47 的前置依赖已满足。

**Phase 47 kickoff 前置验证要求**：
1. 确认 Phase 46 的降级路径在多模型并发场景下稳定（可通过 eval 场景覆盖）
2. 明确 N-Reviewer 共识拓扑的触发条件：是 TaskCard 级配置还是全局策略
3. 智能预算策略的成本数据来源：Phase 46 的 `token_cost` event log 已可消费，确认 Meta-Optimizer 是否需要扩展

### Phase 48 — 存储引擎升级与全异步改造

**风险批注**：高。SQLite (WAL 模式) + `sqlite-vec` 已在 roadmap 中确认为目标方案（替代 PostgreSQL），与项目零外部依赖原则一致。主要风险是 `TaskState`、`EventLog`、RAG 知识索引的迁移范围，建议 kickoff 时明确迁移边界和回滚策略。

### Tag 建议

Phase 46 完成后已打 `v0.4.0`（多模型网络引擎纪元）。Phase 47 完成后建议打 `v0.5.0`（多模型共识纪元）。
