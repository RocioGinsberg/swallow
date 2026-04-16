# 自我进化与记忆沉淀设计 (Self-Evolution & Memory Consolidation)

## 1. 核心理念：拒绝隐式黑盒，拥抱显式工作流

在先进的开发工具（如 Claude Code）中，系统往往能够自动记忆用户的偏好、项目的上下文以及过去的错误。然而，在 Swallow 的多智能体（Multi-Agent）协作架构中，**隐式记忆（Implicit Memory）是系统稳定性的毒药**。如果记忆被隐藏在闭源模型的上下文缓存或不可读的向量库黑盒中，不同的 Agent 将无法实现状态同步，最终导致协作断裂。

Swallow 系统的自我改进与整合哲学是：**将记忆沉淀与自我进化显式化、实体化，变成标准的工作流。**

*   **调度器保持愚蠢 (Thin Orchestrator)**：系统的总控调度层不负责学习和认知。它只负责在合适的时机触发流程。
*   **执行器负责认知 (Smart Executors)**：系统分配专职的 Agent 或特殊的 Skill 包去执行记忆提取和经验总结。
*   **工件承载记忆 (Artifacts as Memory)**：所有的自我进化结果，最终必须固化为可见的、可版本控制的实体资产（如 `LLM Wiki`, 更新后的架构图，或优化的 Prompt 模板）。

---

## 2. 项目级经验沉淀：强制复盘与归档阶段 (Consolidation Phase)

为了确保系统“越用越聪明”且上下文不流失，Swallow 在任务生命周期（Task Lifecycle）的标准结尾，强制植入了一个**自动归档期 (Consolidation Phase)**。

### 2.1 Librarian Agent (图书管理员/知识沉淀专家)
系统内置一个专职的 `Librarian Agent`。它的唯一职责不是编写业务代码，而是作为整个系统记忆质量的守门人。它的三大核心职责是：
1.  **降噪摘要提炼**：任务结束后，将冗长的 Event Logs 转化为精炼的结论。
2.  **冲突检测与合并仲裁**：当两次任务产出了对同一问题的矛盾结论时，它要标记冲突而不是默默覆盖旧知识。
3.  **周期性记忆衰减**：对长期未被引用的知识条目降权或归档，防止 LLM Wiki 认知层或底层 RAG 被过时信息污染。

**权限特例**：作为守门人，它是系统中少数拥有 **Staged-Knowledge 写入权限** 的 Agent，但其每次写入必须生成详细的变更日志（Change Log），供人类审计或 Review Gate 校验。

### 2.2 自动整合工作流 (Workflow Integration)
1.  **触发条件**：当主要的业务 Agent（如 Coding Agent）完成了某个复杂需求或修复了顽固 Bug，并将任务标记为完成。
2.  **派发复盘任务**：调度层暂不将该任务彻底完结，而是自动唤醒 `Librarian Agent`，并将刚刚产生的 Event Logs、修改的 Code Diff 以及最终的 Handoff Note 喂给它。
3.  **认知与提取**：`Librarian Agent` 分析材料，提取坑位、依赖变化、可复用的组件或模式。
4.  **实体化存储 (Write-Back)**：将高价值知识，显式地推入暂存区，经过复核后写入 LLM Wiki 认知层。
5.  **彻底闭环**：当 `Librarian Agent` 提交完“记忆补丁”后，调度层才将该任务正式置为 `completed`。

---

## 3. 系统级自我进化：编排策略顾问 (Meta-Optimizer)

除了针对特定项目上下文的记忆沉淀，Swallow 还支持系统自身能力底座（Harness Tools & Skills）和编排策略的演进。

### 3.1 失败驱动的遥测分析 (Failure-Driven Telemetry)
*   **日志采样**：系统在运行过程中，会持续监控并记录每个 Tool 或 Skill 的调用失败率、模型路由表现。
*   **错误指纹聚类**：底层的日志系统会自动对这些异常事件进行聚类，形成“错误指纹”。

### 3.2 Meta-Optimizer Agent (编排策略顾问)
这是一个专门用于系统自省的专项 Agent。它定期（如每周）被唤醒执行扫描：

*   **只读权限 (Read-Only)**：与之前的构想不同，Meta-Optimizer 必须是**完全只读**的。它可以读取 Event Log 和 Artifact Store，但**不能**直接写入或修改任何系统配置或代码。它是一个纯粹的建议者。
*   **四大扫描职责**：
    1.  识别反复出现的任务模式，提议新的 **Workflow 模板**。
    2.  发现频繁失败或需要人工干预的环节，提议 **Skill 优化**。
    3.  分析模型路由的实际表现（如路由给某个小模型的成功率过低），建议 **路由策略调整**。
    4.  **消费网关层路由遥测 (Gateway Telemetry Consumption)**：读取 Event Log 中带有任务族标签的路由遥测数据（延迟、成本、错误率、降级频次），识别以下模式：
        *   哪些任务族在哪条物理通道上表现持续恶化
        *   哪些降级路径被频繁触发，暗示需要引入新的备选通道
        *   成本/延迟的趋势性漂移是否需要调整 Strategy Router 的默认路由偏好
*   **输出形态**：它的输出是一份**”系统优化提案 (Proposal)”**（含路由优化时的 `routing_optimization_proposal` Artifact）。这份提案会交由人类开发者（架构师）决定是否采纳。这种机制在保证系统能基于数据自我反思的同时，杜绝了黑盒式的自我变异风险。

#### 路由遥测 → Meta-Optimizer 的数据接口

网关层写入 Event Log 的路由遥测条目应包含以下最小字段集：

| 字段 | 类型 | 说明 |
|---|---|---|
| `task_family` | string | 任务族标签（planning / review / extraction / retrieval / execution） |
| `logical_model` | string | 编排层选定的逻辑模型标识 |
| `physical_route` | string | 实际使用的物理通道标识 |
| `latency_ms` | int | 端到端延迟 |
| `token_cost` | float | 本次调用的 token 成本估算 |
| `degraded` | bool | 是否经历了执行级降级 |
| `error_code` | string? | 如有错误，错误码 |

Meta-Optimizer 以只读方式扫描这些条目，不直接修改 Event Log 或网关配置。
