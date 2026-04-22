---
author: gemini
status: living-document
---

# 蓝图差距与演进路线图 (Gap Analysis & Roadmap)

## 一、当前实现与蓝图设计的核心差距 (Gap Analysis)

根据最新收口的 Phase 49 (v0.7.0) 成果，系统已完成全异步化改造、SQLite 任务真值层与知识层 SQLite SSOT 落地。通过对全量设计蓝图（Track 1-7）的深度审计，当前系统正从“真值归一”转入**策略闭环与自我优化**阶段。

### 1. [已消化] 知识真值的“双重真相”风险 (SSOT Consistency)
*   **蓝图要求**：`STATE_AND_TRUTH_DESIGN` 要求单一事实源 (SSOT)，拒绝线性历史依赖。
*   **当前现状**：Phase 49 已将 Evidence / Wiki 知识读取切换为 SQLite primary，文件系统仅保留 mirror / export / fallback 视图。
*   **消化结果**：知识层事务性真值闭环已在 `v0.7.0` 落地，后续不应再回退为文件系统主读。

### 2. [战略级] 专项智能体 (Specialist Agent) 的缺位
*   **蓝图要求**：`AGENT_TAXONOMY_DESIGN` 定义了正交的 Agent 角色，强调 Librarian、Validator、Meta-Optimizer 等专项角色应具备边界清晰的职责。
*   **当前现状**：系统逻辑重度依赖通用执行者 (Codex/Claude)。虽然实现了共识审查和审计函数，但尚未落地具备独立生命周期和受控权限的“专项智能体”实体。
*   **核心差距**：知识沉淀和策略自省仍属于“函数的副作用”，而非“显式的工作流”，导致进化逻辑隐式化、黑盒化。

### 3. [最紧急] 闭环反馈数据的“沉寂” (Passive Telemetry)
*   **蓝图要求**：`SELF_EVOLUTION_AND_MEMORY` 要求系统能够通过复盘和遥测实现自我进化。
*   **当前现状**：系统已具备捕获真实 token 成本、一致性审计结果和降级事件的能力，但这些数据目前仅作为“离线记录”存在。
*   **核心差距**：缺乏将遥测数据转化为“动态路由建议”或“知识晋升提案”的自动化驱动路径。

---

## 二、已消化差距 (Digested Gaps)

### [Phase 49] 知识真值归一与向量 RAG (v0.7.0)
*   **解决方式**：落地知识层 SQLite SSOT、`swl knowledge migrate`、`LibrarianAgent` 与 `sqlite-vec` 可退级检索。
*   **成果**：系统进入 **Knowledge Era**，消除了知识层“双重真相”风险，并形成本地语义检索基线。

### [Phase 48] 存储引擎升级与全异步改造 (v0.6.0)
*   **解决方式**：落地 `SqliteTaskStore` 与全链路 `async/await`，实装 `swl migrate` 过渡入口。
*   **成果**：系统进入 **Async Era**，消除了高并发子任务的 IO 阻塞瓶颈。

### [Phase 47] 多模型共识与策略护栏 (v0.5.0)
*   **解决方式**：实装 N-Reviewer 共识门禁与 TaskCard 级成本护栏。
*   **成果**：系统进入 **Consensus Era**，具备了自我纠偏与财务自律能力。

---

## 三、架构演进 Roadmap (Phases 49-51)

### Phase 49: 知识真值归一与向量 RAG (Knowledge SSOT & Vector RAG) ✅ [Done]
*   **Primary Track**: Knowledge / RAG
*   **Secondary Track**: State / Truth
*   **目标**：彻底消除知识层的“双重真相”，实装本地向量检索。
*   **核心任务**：
    - **知识层 SSOT 归一**：将 `Evidence Store` / `Wiki Store` 全量迁移至 SQLite。废除文件系统作为真值的逻辑，仅将其保留为可导出的“视图”。
    - **图书管理员 (Librarian Agent) 实装**：落地首个专项智能体实体。由其接管知识的冲突检测、去重与 SQLite 写入边界。
    - **向量化 RAG 与平滑退级**：集成 `sqlite-vec` 提供本地向量能力。强制要求具备“向量 -> 文本模糊匹配”的自动降级机制，确保环境鲁棒性。
*   **产出价值**：终结碎片化存储，实现具备语义维度的高质量知识闭环。

### Phase 50: 路由策略闭环与专项审计 (Policy Closure & Specialist Audit) 🚀 [Next]
*   **Primary Track**: Evaluation / Policy
*   **Secondary Track**: Provider Routing
*   **目标**：将审计与遥测数据转化为可感知的策略行为，落地 Meta-Optimizer 建议链。
*   **核心任务**：
    - **Meta-Optimizer 提案实装**：落地编排策略顾问 Agent。扫描 SQLite 事件流，自动产出 `routing_optimization_proposal`（路由建议）和 `workflow_optimization_proposal`（工作流建议）。
    - **质量信号反哺路由**：实装基于审计质量和成本效益的“受控路由权重调整”机制。
    - **一致性审计自动化**：将只读的一致性抽检 (Consistency Audit) 升级为可配置的自动化触发策略。
*   **产出价值**：系统从“有感遥测”进化到“主动优化”，实现架构级的自我迭代闭环。

### Phase 51: 平台级多路并行与复杂拓扑 (Advanced Parallel Topologies)
*   **Primary Track**: Core Loop
*   **Secondary Track**: Execution Topology
*   **目标**：利用 Async & SQLite 底座，解锁蓝图中的高并发多路子任务编排。
*   **核心任务**：
    - **全异步执行器升级**：将 `CLIAgentExecutor` 等残留的同步桥接层彻底改为原生 async subprocess。
    - **多路 Subtask 并行压测**：实装跨任务/跨模型的并行提取与对比拓扑，处理资源争抢与死锁保护。
*   **产出价值**：实现蓝图定义的“长周期、高并发”任务树处理能力。

---

## 四、推荐 Phase 队列与风险批注 (Claude 维护)

> 最近更新：2026-04-22 (Phase 49 收口，Codex post-tag 状态同步)

### 队列总览

| 优先级 | Phase | 名称 | Primary Track | Secondary Track | 风险等级 | 备注 |
|--------|-------|------|---------------|-----------------|----------|------|
| ~~1~~ | ~~48~~ | ~~存储引擎升级与全异步改造~~ | ~~Core Loop~~ | ~~State / Truth~~ | ~~已完成~~ | tag `v0.6.0` |
| ~~2~~ | ~~49~~ | ~~知识真值归一与向量 RAG~~ | ~~Knowledge / RAG~~ | ~~State / Truth~~ | ~~已完成~~ | tag `v0.7.0` |
| **3** | **50** | **路由策略闭环与专项审计** | **Evaluation / Policy** | **Provider Routing** | **中** | 落地 Meta-Optimizer |

### 全局锚点分析 (Gemini)

| 维度 | 参考源 | 蓝图愿景 | 核心差距 | 局部最优风险预警 |
| :--- | :--- | :--- | :--- | :--- |
| **系统级锚点** | `ARCHITECTURE.md` | 基于状态的异步协同，SSOT 事实层 | 遥测与审计结果尚未进入可执行策略闭环 | **[中高]** 若不完成策略闭环，系统会停留在“记录很多但不主动优化”的阶段 |
| **领域级卫星** | `AGENT_TAXONOMY` | 显式的角色认知分工 | `LibrarianAgent` 已落地，但 Meta-Optimizer / Validator 等专项角色仍偏函数化 | 通用 Agent 上下文压力降低有限，策略建议仍缺少明确 agent 边界 |
| **跨界嗅探** | `SELF_EVOLUTION` | 记忆沉淀作为显式工作流 | 遥测数据目前处于“已捕获但未消费”状态 | 浪费了宝贵的反馈信号，导致路由和策略演进滞后于业务实际 |

### Tag 记录

Phase 49 已打标 `v0.7.0` (Knowledge Era)，标志着知识真值归一与向量检索能力的正式闭环。Phase 50 是否形成新 tag，待其 closeout 后再评估。
