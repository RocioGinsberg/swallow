---
author: gemini
status: living-document
---

# 蓝图差距与演进路线图 (Gap Analysis & Roadmap)

## 一、当前实现与蓝图设计的核心差距 (Gap Analysis)

根据最新收口并打标的 Phase 48 (`v0.6.0`) 成果，系统已经补齐了 async orchestration 与 SQLite 任务真值层的基础设施。当前最主要的差距，已从“执行效率与存储架构”转向“知识闭环与检索质量”：

### 1. [最紧急] 知识层与 RAG 仍然碎片化 (Knowledge / RAG Fragmentation)
*   **蓝图要求**：具备统一的知识索引、可追踪引用与本地向量化检索能力。
*   **当前现状**：`Evidence Store` 与 `Wiki Store` 仍主要依赖 JSON / Markdown 索引与文本匹配；Phase 48 仅迁移了 `TaskState` / `EventLog`，尚未迁移知识层。
*   **核心差距**：Grounding 与 retrieval 仍缺少原生向量能力，知识对象之间的语义关联与召回质量仍受限。

### 2. 动态路由与多维评估尚未形成闭环 (Dynamic Routing & Eval Synergy)
*   **蓝图要求**：Strategy Router 应基于实时质量反馈（Eval / Audit）和历史性能进行动态决策。
*   **当前现状**：共识审查、一致性抽检和 Meta-Optimizer 已具备只读分析能力，但质量信号尚未反哺 route policy。
*   **核心差距**：审计与遥测仍主要停留在 operator-facing 只读层，缺乏受控、可审计的策略闭环。

### 3. SQLite 过渡层仍有收口空间 (SQLite Transition Tightening)
*   **蓝图要求**：真值层集中、查询高效、operator 语义清晰。
*   **当前现状**：默认 backend 已切到 SQLite，但仍保留 file mirror/fallback 作为过渡层；大体量历史 `.swl/` 目录仍可能触发迁移建议与兼容读取路径。
*   **核心差距**：过渡层虽然保证了稳定切换，但还未完全收束到知识层与检索层统一消费 SQLite 真值的终局形态。

---

## 二、已消化差距 (Digested Gaps)

### [Phase 48] 存储层与执行引擎的并发瓶颈
*   **解决方式**：实装 `execute_async()`、`run_review_gate_async()`、`run_task_async()`、`AsyncSubtaskOrchestrator`，并引入 SQLite (`.swl/swallow.db`) 作为 `TaskState` / `EventLog` 的默认真值层。
*   **成果**：系统进入 Async Era (`v0.6.0`)，具备全异步执行基础、并发 reviewer 调度、SQLite 默认存储、`swl migrate` 与 `swl doctor sqlite` operator 入口。

### [Phase 47] 多模型共识与策略护栏
*   **解决方式**：实装 `ReviewGate` N-Reviewer 逻辑与 `TaskCard.token_cost_limit` 熔断机制。
*   **成果**：系统进入 Consensus Era (`v0.5.0`)，具备多数票、一票否决以及基于真实 Token 成本的财务护栏。

### [Phase 46] 单点 CLI 代理与原生 Gateway 的断层
*   **解决方式**：实装 `HTTPExecutor` 并引入方言适配器，废除品牌硬编码。
*   **成果**：系统获得网络分发权与分层降级矩阵。

---

## 三、架构演进 Roadmap (Phases 49-50)

### Phase 49: 检索增强与知识层闭环 (RAG & Knowledge Closure) 🚀 [Next]
*   **Primary Track**: Knowledge / RAG
*   **Secondary Track**: Capabilities
*   **目标**：利用 Phase 48 的 SQLite 基础，实装本地向量检索并把知识层拉回统一真值闭环。
*   **核心任务**：
    - **向量化 RAG 实装**：基于 `sqlite-vec` 或等效能力建立本地向量索引。
    - **知识层迁移**：评估 `Evidence Store` / `Wiki Store` 的 SQLite 化与统一检索入口。
    - **知识关联审计**：利用审计机制发现过时、冲突或可合并的知识对象。
*   **产出价值**：显著提升 grounding 准确度、召回质量与知识复用效率。

### Phase 50: 路由质量闭环与策略收束 (Routing & Eval Closure)
*   **Primary Track**: Evaluation / Policy
*   **Secondary Track**: Provider Routing
*   **目标**：将 audit / eval / telemetry 的质量信号，以可审计、可回滚的方式反馈到 routing 与 policy 层。
*   **核心任务**：
    - **审计信号回流**：让 consistency audit / review / optimizer proposal 能进入受控的 route policy 建议流程。
    - **策略闭环护栏**：为 route policy 提案、试运行与回滚建立 operator-facing gate。
    - **多维质量聚合**：将成本、失败率、审计质量与 retrieval 成效纳入统一评估视图。
*   **产出价值**：让系统从“可观测”进化到“可控优化”，减少长期人工调参成本。

---

## 四、推荐 Phase 队列与风险批注 (Claude 维护)

> 最近更新：2026-04-22 (Phase 48 收口并打标 `v0.6.0`，Phase 49 启动准备中)

### 队列总览

| 优先级 | Phase | 名称 | Primary Track | Secondary Track | 风险等级 | 备注 |
|--------|-------|------|---------------|-----------------|----------|------|
| ~~1~~ | ~~48~~ | ~~存储引擎升级与全异步改造~~ | ~~Core Loop~~ | ~~State / Truth~~ | ~~已完成~~ | tag `v0.6.0` |
| **2** | **49** | **检索增强与知识层闭环** | **Knowledge / RAG** | **Capabilities** | **中高** | 当前重点 |
| 3 | 50 | 路由质量闭环与策略收束 | Evaluation / Policy | Provider Routing | 中 | 依赖 Phase 49 的质量信号沉淀 |

### Phase 49 多维度锚点分析 (Gemini)

| 维度 | 参考源 | 蓝图愿景 | 核心差距 | 局部最优风险预警 |
| :--- | :--- | :--- | :--- | :--- |
| **系统级锚点** | `ARCHITECTURE.md` | 统一知识真值、可检索、可审计 | 任务真值已 SQLite 化，但知识真值仍分散 | 只做向量索引而不统一知识入口，会形成“双真值层” |
| **领域级卫星** | `STATE_AND_TRUTH` | grounding / retrieval / promotion 闭环 | `Evidence` / `Wiki` 仍以文本匹配和分散索引为主 | 过快迁移知识层若不保留 Markdown 可读性，operator 可审查性会下降 |
| **跨界嗅探** | `HARNESS / CLI / doctor` | 本地可恢复、零复杂部署 | `sqlite-vec` 或等效依赖会引入新的环境约束 | 若依赖管理失控，可能破坏“纯 Python + 本地栈”易用性 |

### Tag 建议

Phase 48 已达成 `v0.6.0`（Async Era）。Phase 49 是否形成下一次 tag，需待知识层闭环与向量检索能力稳定后再评估。
