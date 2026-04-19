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

> 最近更新：2026-04-19 (Claude 审阅 Gemini roadmap 产出，更新风险批注与补充上下文)

### 队列总览

| 优先级 | Phase | 名称 | Primary Track | Secondary Track | 风险等级 |
|--------|-------|------|---------------|-----------------|----------|
| ~~1~~ | ~~41-45~~| ~~Librarian 收口 / 工作台 / 外部摄入 / Eval 基线~~ | ~~...~~ | ~~...~~ | ~~已完成~~ |
| **2** | **46** | **模型网关物理层实装 (Gateway Core Materialization)** | **Execution Topology** | **Capabilities** | **高** |
| 3 | 47 | 多模型共识与策略护栏 | Evaluation / Policy | Core Loop | 中 |
| 4 | 48 | 存储引擎升级与全异步改造 | Core Loop | State / Truth | 高 |

### 依赖关系

```
Phase 45 (Eval 基线) ✅
  └──→ Phase 46 (Gateway 网关：通过 Eval 保证底座替换不降级)
         └──→ Phase 47 (多模型共识：依赖真实的底层多模型分发能力)
                └──→ Phase 48 (全异步：提升并发调度的性能)
```

排序确认：46 → 47 → 48 的依赖链成立。没有真实 HTTP 执行器，多模型共识无从谈起；没有多模型分发，异步改造的收益不大。Phase 46 作为最高优先级，完全同意。

### Phase 46 — 模型网关物理层实装（当前最优先级）

**优先级理由**：系统现在存在”大脑（Orchestrator）与四肢（Executor）断开”的致命问题。编排层已有完整的路由策略、方言适配、能力协商设计（`PROVIDER_ROUTER_AND_NEGOTIATION.md`），但执行层唯一能真正调用 LLM 的活路径仍然是 `run_codex_executor` 通过 `subprocess.run` 调 Codex CLI。其他路径（`run_local_executor`、`run_mock_executor` 等）要么是 mock 要么是 note-only，不具备真实 LLM 调用能力。必须开发 HTTP Client 替换这条路径，否则后续所有多模型策略编排都是纸上谈兵。

**风险**: 高。具体风险点如下：

1. **Eval 覆盖缺口**：当前 `tests/eval/` 的基线覆盖的是 ingestion 降噪和 meta-optimizer 提案质量，并不直接覆盖”执行器替换后模型输出质量不降级”这个场景。Phase 46 kickoff 时必须明确：新增哪些 eval 场景来覆盖 HTTP executor 的方言正确性和输出质量（如 JSON Schema 遵循率、代码格式、`<thinking>` 标签闭合等）。

2. **基础设施就绪假设**：Phase 46 假设 `localhost:3000` (new-api) 已经可用。Roadmap 未说明当前 Docker Compose 栈的部署状态。如果 new-api 还没跑起来，Phase 46 的第一个 slice 需要包含基础设施就绪验证，否则后续 slice 全部阻塞。

3. **单 Phase scope 过大**：三个核心任务（HTTP Executor + 方言对齐 + 降级矩阵）放在一个 phase 里。HTTP Executor 本身按风险评级标准已是跨模块(3) + 依赖外部系统(3) + 需要额外工作回滚(2) = 8 分高风险。建议 kickoff 时拆为 3-4 个有明确 stop/go gate 的 slice，避免大爆炸式替换。

### Phase 47 — 多模型共识与策略护栏

**风险批注**：中。前置依赖（Phase 46 HTTP 执行器）是主要风险来源——如果 Phase 46 的降级矩阵不够健壮，多 Reviewer 共识拓扑会放大单点故障。建议 Phase 47 kickoff 时先验证 Phase 46 的降级路径在多模型并发场景下是否稳定。

### Phase 48 — 存储引擎升级与全异步改造

**风险批注**：高。需要特别讨论一个 trade-off：当前系统的核心卖点之一是”本地优先、零外部依赖”，引入 PostgreSQL 会改变部署模型（用户需要额外运行 PG 实例）。建议 Gemini 在 context_brief 中评估 SQLite（或 SQLite + WAL）作为中间方案的可行性——它保持零服务依赖，同时提供事务保证和 SQL 查询能力，可能足以覆盖 Phase 48 的并发需求而不破坏部署简洁性。如果最终确认需要 PG，应在 kickoff 中显式标注这是一个部署模型变更决策，需要 Human gate。

### 差距描述精确性备注（供 Gemini 参考）

差距 #1 的描述”`executor.py` 内部硬编码了 `subprocess.run([“codex”])`”需要微调。当前 `executor.py` 已有 `run_local_executor`、`run_mock_executor`、`run_mock_remote_executor`、`run_note_only_executor`、`run_codex_executor` 五条路径，`run_codex_executor` 是默认 fallback 而非唯一路径。问题的本质是：**唯一能真正调用 LLM 的活路径仍然是 subprocess 调 Codex CLI**，其他路径不具备真实推理能力。建议将措辞从”硬编码”调整为”唯一活 LLM 路径”。

### Tag 建议

v0.3.2 已打。待 Phase 46 网关彻底打通后，系统将迎来历史性的架构闭环（大脑与手脚连接），届时建议升级大版本号为 `v0.4.0` (多模型网络引擎纪元)。
