---
author: gemini
status: living-document
---

# 蓝图差距与演进路线图 (Gap Analysis & Roadmap)

## 一、当前实现与蓝图设计的核心差距 (Gap Analysis)

根据最新收口的 Phase 47 (v0.5.0) 成果，系统已具备了多模型共识审查与初步的财务熔断护栏。当前的差距已从“质量护栏”转向“执行效率与存储架构”：

### 1. [最紧急] 存储层与执行引擎的并发瓶颈 (Storage & Async Bottlenecks)
*   **蓝图要求**：支持长周期、高并发的多路子任务与知识对比，具备事务保证。
*   **当前现状**：调度与执行重度依赖同步阻塞（Synchronous IO）及文件系统（JSON/Markdown）。
*   **核心差距**：无法支撑真正的高并发拓扑（如 N-Reviewer 的并行执行或多路 Subtask 并行），且文件系统在大负载下缺乏可靠的查询追踪与事务保证。

### 2. 知识库与 RAG 的碎片化 (Fragmented Knowledge Layer)
*   **蓝图要求**：具备统一的知识索引与检索接口，支持本地向量化。
*   **当前现状**：知识存储分布在 `Evidence Store` 和 `Wiki Store`，索引机制（JSON/Markdown）查询效率低且难以维护语义关联。
*   **核心差距**：检索质量受限于低效的文本匹配，缺乏原生向量能力。

### 3. 动态路由与多维评估的协同 (Dynamic Routing & Eval Synergy)
*   **蓝图要求**：Strategy Router 应基于实时质量反馈（Eval）和历史性能进行动态决策。
*   **当前现状**：共识与审计已落地，但审计结果（Consistency Audit）尚未闭环反馈给路由决策逻辑。
*   **核心差距**：审计目前是只读的，缺乏自动纠偏路由权重的机制。

---

## 二、已消化差距 (Digested Gaps)

### [Phase 47] 多模型共识与策略护栏
*   **解决方式**：实装 `ReviewGate` N-Reviewer 逻辑与 `TaskCard.token_cost_limit` 熔断机制。
*   **成果**：系统进入 Consensus Era (v0.5.0)，具备了多数票、一票否决以及基于真实 Token 成本的财务护栏。

### [Phase 46] 单点 CLI 代理与原生 Gateway 的断层
*   **解决方式**：实装 `HTTPExecutor` 并引入方言适配器，废除品牌硬编码。
*   **成果**：系统获得网络分发权与分层降级矩阵。

---

## 三、架构演进 Roadmap (Phases 48-50)

### Phase 48: 存储引擎升级与全异步改造 (Storage & Async Engine) 🚀 [Next]
*   **Primary Track**: Core Loop
*   **Secondary Track**: State / Truth
*   **目标**：重构系统的 IO 模型与状态存储，支撑高并发任务树。
*   **核心任务**：
    - **调度全异步化**：将 Orchestrator、Executor、ReviewGate 的核心链路迁移至 `asyncio`。
    - **轻量化本地数据库 (SQLite)**：引入 SQLite (WAL 模式) + `sqlite-vec` 向量扩展。
    - **状态与事件迁移**：将 `TaskState`、`EventLog` 和 RAG 索引迁移至 `.swl/swallow.db`。
*   **产出价值**：彻底消除并行子任务的 IO 阻塞瓶颈，具备原生语义搜索能力。

### Phase 49: 检索增强与知识层闭环 (RAG & Knowledge Closure)
*   **Primary Track**: Knowledge / RAG
*   **Secondary Track**: Capabilities
*   **目标**：利用 Phase 48 的向量能力，彻底升级知识检索质量。
*   **核心任务**：
    - **向量化 RAG 实装**：基于 `sqlite-vec` 实现本地向量索引。
    - **知识关联审计**：利用审计机制自动发现并修复过时或冲突的知识点。
*   **产出价值**：显著提升 Grounding 的准确度，降低长上下文下的幻觉率。

---

## 四、推荐 Phase 队列与风险批注 (Claude 维护)

> 最近更新：2026-04-20 (Phase 47 收口，Phase 48 启动准备中)

### 队列总览

| 优先级 | Phase | 名称 | Primary Track | Secondary Track | 风险等级 | 备注 |
|--------|-------|------|---------------|-----------------|----------|------|
| ~~1~~ | ~~47~~ | ~~多模型共识与策略护栏~~ | ~~Evaluation / Policy~~ | ~~Core Loop~~ | ~~已完成~~ | tag v0.5.0 |
| **2** | **48** | **存储引擎升级与全异步改造** | **Core Loop** | **State / Truth** | **高** | 当前重点，破坏性重构 |
| 3 | 49 | 检索增强与知识层闭环 | Knowledge / RAG | Capabilities | 中 | 依赖 Phase 48 向量能力 |

### Phase 48 多维度锚点分析 (Gemini)

| 维度 | 参考源 | 蓝图愿景 | 核心差距 | 局部最优风险预警 |
| :--- | :--- | :--- | :--- | :--- |
| **系统级锚点** | `ARCHITECTURE.md` | 基于状态的异步协同，事务性状态流转 | 目前全部是同步阻塞 IO，无事务保证 | 纯 asyncio 改造若不配合数据库事务，可能导致文件状态损坏或竞争 |
| **领域级卫星** | `STATE_AND_TRUTH` | 集中式真值存储，可查询事件流 | .swl/ 下 JSON 文件散乱，难以回溯 | 若过度依赖数据库，可能丧失 Markdown Artifact 的可读性优势 |
| **跨界嗅探** | `HARNESS / CLI` | CLI 启动快速，环境无依赖 | `sqlite-vec` 引入了新的二进制依赖 | 若依赖管理不当，将破坏“纯 Python 环境”的易用性 |

### Tag 建议

Phase 47 已达成 `v0.5.0`。Phase 48 完成后建议打 `v0.6.0` (Async Era)。
