# 自我进化与记忆沉淀设计 (Self-Evolution & Memory Consolidation)

## 1. 核心理念：拒绝隐式黑盒，拥抱显式工作流

在先进的开发工具（如 Claude Code）中，系统往往能够自动记忆用户的偏好、项目的上下文以及过去的错误。然而，在 Swallow 的多智能体（Multi-Agent）协作架构中，**隐式记忆（Implicit Memory）是系统稳定性的毒药**。如果记忆被隐藏在闭源模型的上下文缓存或不可读的向量库黑盒中，不同的 Agent 将无法实现状态同步，最终导致协作断裂。

Swallow 系统的自我改进与整合哲学是：**将记忆沉淀与自我进化显式化、实体化，变成标准的工作流。**

*   **调度器保持愚蠢 (Thin Orchestrator)**：系统的总控调度层不负责学习和认知。它只负责在合适的时机触发流程。
*   **执行器负责认知 (Smart Executors)**：系统分配专职的 Agent 或特殊的 Skill 包去执行记忆提取和经验总结。
*   **工件承载记忆 (Artifacts as Memory)**：所有的自我进化结果，最终必须固化为可见的、可版本控制的实体资产（如 `CONTEXT.md`, 更新后的架构图，或优化的 Prompt 模板）。

---

## 2. 项目级经验沉淀：强制复盘与归档阶段 (Consolidation Phase)

为了确保系统“越用越聪明”且上下文不流失，Swallow 在任务生命周期（Task Lifecycle）的标准结尾，强制植入了一个**自动归档期 (Consolidation Phase)**。

### 2.1 Librarian Agent (图书管理员/知识沉淀专家)
系统内置一个专职的 `Librarian Agent`（或者称为 `Archivist Agent`）。它的唯一职责不是编写业务代码，而是分析已经发生的工作流并提取知识。

### 2.2 自动整合工作流 (Workflow Integration)
1.  **触发条件**：当主要的业务 Agent（如 Coding Agent）完成了某个复杂需求或修复了顽固 Bug，并将任务标记为 `business_logic_completed` 后。
2.  **派发复盘任务**：调度层暂不将该任务彻底完结，而是自动唤醒 `Librarian Agent`，并将刚刚产生的 Event Logs（事件日志）、修改的 Code Diff 以及最终的 Handoff Note 喂给它。
3.  **认知与提取**：`Librarian Agent` 会深度分析这些材料，回答以下关键问题：
    *   *我们在这个任务中踩了什么坑？*
    *   *系统的依赖包或核心配置项是否发生了变化？*
    *   *有没有产生可复用的模式（Pattern）或组件？*
4.  **实体化存储 (Write-Back)**：`Librarian Agent` 将提取出的高价值知识，显式地追加修改到系统的权威文件中。例如：
    *   更新代码库根目录的 `CONTEXT.md` 或 `.swallow/project_memory.md`。
    *   向领域专属的 RAG 知识库提交新增的结构化条目。
5.  **彻底闭环**：当 `Librarian Agent` 提交完“记忆补丁”并触发 Git Checkpoint 后，调度层才将该任务正式置为 `completed`。

---

## 3. 系统级自我进化：工具与技能的 Meta-Optimization (元优化)

除了针对特定项目上下文的记忆沉淀，Swallow 还支持系统自身能力底座（Harness Tools & Skills）的演进。

### 3.1 失败驱动的遥测分析 (Failure-Driven Telemetry)
*   **日志采样**：系统在运行过程中，会持续监控并记录每个 Tool 或 Skill 的调用失败率（例如，因模型输出格式错误导致的 JSON 解析失败，或某段 Prompt 经常导致 Agent 陷入死循环）。
*   **错误指纹聚类**：底层的日志系统会自动对这些异常事件进行聚类，形成“错误指纹”。

### 3.2 Meta-Agent 的自我修正循环
*   当某类错误的置信度积累到阈值，调度层会自动生成一个内部的维护任务，并委派给高权限的 **`Meta-Agent`（系统工程师角色）**。
*   `Meta-Agent` 被赋予了修改 Swallow 框架内部配置甚至源码的沙盒权限。它会读取错误指纹，分析其背后的原因（例如：大模型对当前 Tool 的描述文本理解产生了歧义）。
*   随后，`Meta-Agent` 会生成改进建议，甚至自动提交包含优化后的 Prompt 模板（Prompts Tuning）或结构化定义（JSON Schema）的 Pull Request，从而在没有人类干预的情况下，实现系统组件级的自我修复与进化。
