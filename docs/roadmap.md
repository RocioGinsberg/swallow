---
author: gemini
status: living-document
---

# 蓝图差距与演进路线图 (Gap Analysis & Roadmap)

## 一、当前实现与蓝图设计的核心差距 (Gap Analysis)

根据最新收口的 Phase 46 (v0.4.0) 成果，系统已打通了物理层的多模型分发权，解决了单点 CLI 硬编码的断层。当前的差距已从“基础设施有无”转向“协作深度与系统健壮性”：

### 1. [最紧急] 从单体审查向多机/多 Agent 共识演进 (Consensus Topology)
*   **蓝图要求**：第 2 层（编排层）应支持多 Reviewer 对话拓扑，通过多模型共识（Majority Pass）或异构审查确保输出质量，避免单一模型幻觉。
*   **当前现状**：`ReviewGate` 仅支持单 Reviewer 模式。虽然 Phase 46 提供了调用多模型的能力，但编排层尚未利用此能力进行并发/冗余审计。
*   **核心差距**：系统缺乏冗余校验机制，无法自动对冲单一强模型的思维定式或瞬时幻觉。

### 2. 策略护栏与财务自律的缺失 (Guardrails & Budgeting)
*   **蓝图要求**：Strategy Router 应基于成本、风险和能力下限进行智能决策，并具备自动熔断与预算控制能力。
*   **当前现状**：虽然已捕获真实 token 成本，但系统仍缺乏主动的预算策略。路由降级主要依赖硬编码的 fallback 链，而非基于实时质量/成本反馈的动态调整。
*   **核心差距**：在高强度自动化场景下，系统存在“无感烧钱”或“盲目降级”的财务与质量风险。

### 3. 存储层与执行引擎的并发瓶颈 (Storage & Async Bottlenecks)
*   **蓝图要求**：支持长周期、高并发的多路子任务与知识对比，具备事务保证。
*   **当前现状**：调度与执行重度依赖同步阻塞（Synchronous IO）及文件系统（JSON/Markdown）。
*   **核心差距**：无法支撑未来规模化的并发拓扑（如 N-Reviewer 的并行执行），且文件系统在大负载下缺乏可靠的查询追踪能力。

---

## 二、已消化差距 (Digested Gaps)

### [Phase 46] 单点 CLI 代理与原生 Gateway 的断层
*   **解决方式**：实装 `HTTPExecutor` 并引入方言适配器（Claude XML, DeepSeek FIM 等），废除品牌硬编码。
*   **成果**：系统获得网络分发权，实现 `http-claude → http-qwen → http-glm → local-cline` 的降级矩阵。

---

## 三、架构演进 Roadmap (Phases 47-49)

### Phase 47: 多模型共识与策略护栏 (Consensus & Policy Guardrails) 🚀 [Next]
*   **Primary Track**: Evaluation / Policy
*   **Secondary Track**: Core Loop
*   **目标**：在具备真实多模型调度能力的基础上，引入冗余审查机制和智能预算策略，提升系统的自我纠偏能力。
*   **核心任务**：
    - **N-Reviewer 共识拓扑**：扩展 `ReviewGate` 支持多模型并发审查，实现“多数票通过”或“强模型一票否决”机制。
    - **智能预算策略**：基于 Phase 46 捕获的真实 `token_cost` 事件流，实现 TaskCard 级的成本熔断与财务预警。
    - **一致性审计插件**：引入跨模型抽检逻辑，由强模型定期审计低成本模型的中间产物。
*   **产出价值**：系统具备极强的自我纠偏能力，适应高风险、高强度的无人值守运行。

### Phase 48: 存储引擎升级与全异步改造 (Storage & Async Engine)
*   **Primary Track**: Core Loop
*   **Secondary Track**: State / Truth
*   **目标**：重构系统的 IO 模型与状态存储，支撑下一代高并发任务树。
*   **核心任务**：
    - **调度全异步化**：将 Orchestrator 和 Executor 的核心链路迁移至 `asyncio`。
    - **轻量化本地数据库 (SQLite)**：引入 SQLite (WAL 模式) + `sqlite-vec` 向量扩展。将 `TaskState`、`EventLog` 和 RAG 索引迁移至 `.swl/swallow.db`。
*   **产出价值**：彻底消除并行子任务的 IO 阻塞瓶颈，大幅降低系统部署门槛（回归真正的纯本地 CLI 体验）。

---

## 四、推荐 Phase 队列与风险批注 (Claude 维护)

> 最近更新：2026-04-20 (Phase 46 收口，Phase 47 启动准备中)

### 队列总览

| 优先级 | Phase | 名称 | Primary Track | Secondary Track | 风险等级 | 备注 |
|--------|-------|------|---------------|-----------------|----------|------|
| ~~1~~ | ~~46~~ | ~~模型网关物理层实装~~ | ~~Execution Topology~~ | ~~Capabilities~~ | ~~已完成~~ | tag v0.4.0 |
| **2** | **47** | **多模型共识与策略护栏** | **Evaluation / Policy** | **Core Loop** | **中** | 当前重点 |
| 3 | 48 | 存储引擎升级与全异步改造 | Core Loop | State / Truth | 高 | 涉及存储重构 |

### Phase 47 多维度锚点分析 (Gemini)

| 维度 | 参考源 | 蓝图愿景 | 核心差距 | 局部最优风险预警 |
| :--- | :--- | :--- | :--- | :--- |
| **系统级锚点** | `ARCHITECTURE.md` | 基于状态的异步协同，Agent 不直接对话 | `ReviewGate` 当前为单点阻塞逻辑，且反馈协议简单 | 简单引入 N-Reviewer 可能会导致父任务状态机膨胀或并发死锁 |
| **领域级卫星** | `ORCHESTRATION_AND_HANDOFF` | 多角色认知分工（Planner/Reviewer） | 当前 Reviewer 角色单一，未利用多模型异构性 | 仅追求“多数票”可能导致平庸化，需保留强模型的“架构否决权” |
| **跨界嗅探** | `COST / TELEMETRY` | 财务自律与成本感知决策 | 路由降级尚未联动真实成本反馈 | 冗余审查会使成本翻倍，若无智能预算策略，系统 ROI 将显著下降 |

### Tag 建议

Phase 46 完成后已打 `v0.4.0`。Phase 47 完成后建议打 `v0.5.0` (Consensus Era)。
