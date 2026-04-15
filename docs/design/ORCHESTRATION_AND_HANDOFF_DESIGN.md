# 多智能体协同与编排设计 (Orchestration & Handoff)

## 1. 核心理念：自建调度引擎与基于状态的异步通信

在传统的多智能体（Multi-Agent）框架中，Agent 之间通常采用“群聊机制”，或者系统彻底依附于某一家厂商的“原生 Agent”来实现调度。这在长周期软件工程任务中会导致上下文污染或系统被厂商绑定。

Swallow 系统的第 2 层（编排层）确立了**统一调度中枢**与**“基于状态的异步协同”**原则：
**系统自建轻量级的 Runtime (Router / Planner / Subtask Orchestrator / Review Gate)，厂商原生 Agent 仅作为外部执行器 (Executor) 接入。Agent 之间绝对不直接对话。它们通过修改底层状态机、生成标准化工件（Artifacts）和结构化交接单来完成协作。**

---

## 2. 调度引擎核心组件

Swallow 的调度引擎 (Runtime) 由以下关键节点构成：

### 2.1 Router (统一路由)
*   判断当前任务域（工程 / 研究 / 日常 / 批处理）。
*   评估复杂度，决定应该分配给具体的**模型 API**，还是分配给**厂商原生 Agent (如 Codex / Gemini CLI)**，或是唤醒某个低成本的**专项 Agent**。

### 2.2 Planner (任务分解)
*   负责将宏大的用户意图拆解为可操作的任务卡 (Task Cards)。
*   定义每个子任务的输入、输出 Schema、权限约束与置信度阈值。

### 2.3 Subtask Orchestrator (平台级子代理编排)
*   **平台级 Subagents (Platform-level Subagents)**：这是 Swallow 系统的核心。它在外部控制多个任务的并行下发、执行与最终的汇聚复核（例如：并发抓取多篇论文并提取摘要）。
*   *对比：执行器原生 Subagents (Executor-native Subagents)*：某些外部执行器（如厂商 CLI）自带的内部拆解能力。系统仅将其视为局部的“黑盒增强”，系统级协同不依赖于此。

### 2.4 Review Gate (审查门禁)
*   所有执行器的产出在合并或写入知识库前，必须通过审查门禁。
*   负责 Schema 校验、置信度判断、知识库冲突检测。如果失败，触发重试或升级（向强模型或人类抛出）。

---

## 3. 结构化交接单 (Structured Handoff Notes)

为了解决接手任务时上下文爆炸的问题，系统强制引入了“提纯交接”机制。

### 3.1 告别“堆叠聊天记录”
当 Agent A 完成阶段性工作，准备将任务流转给 Agent B 时，必须在退出前调用专用的 Harness 工具，将冗余信息进行自我压缩与提纯，生成一份结构化的**任务交接单 (Handoff Note)**。

### 3.2 交接单的四大要素 (Goal / Done / Next / Pointers)
一份合格的 Handoff Note 必须作为不可变的 Artifact 持久化存储，其内容格式强制包含：
*   **Goal (总目标)**：这个 Task 最终要解决的核心问题是什么。
*   **Done (已完成与踩坑记录)**：我已经尝试了什么？排除了哪些错误路线？
*   **Next_Steps (后续行动指南)**：接手者接下来应该优先处理哪几个 TODO。
*   **Context_Pointers (上下文指针)**：**核心精髓**。交接单绝不携带大段源码或原文档，只传递资源的**引用指针 (References)**（例如：`git_commit_hash: 8f7e2a`，`obsidian_note: #1024`）。接手的 Agent 根据指针自行去加载所需的最小上下文，保持 Prompt 绝对干净。

#### Schema Alignment Note
自 Phase 19 起，代码层对 handoff vocabulary 的 authoritative 定义统一收敛到 [src/swallow/models.py](/home/rocio/projects/swallow/src/swallow/models.py:87) 中的 `HandoffContractSchema`。
映射：`Goal` -> `goal`，`Done` -> `done`，`Next_Steps` -> `next_steps`，`Context_Pointers` -> `context_pointers`。
（本设计文档未单独列出的约束集合，在统一 schema 中使用 `constraints` 表达，以便与 interaction / knowledge ingestion 侧保持同一交接契约。）

---

## 4. 多智能体协同拓扑 (Collaboration Topologies)

在多模型生态下，协同不仅是“多个 Agent”，而是“**不同认知能力**的接力”。

### 4.1 通用认知代理的默认范式
*   **Gemini (知识整合者)** 读全局：生成知识底稿、Wiki 草稿，梳理长历史上下文。
*   **Claude (规划与审查者)** 做判断：任务拆解、风险建模、利弊分析。
*   **Codex (施工执行者)** 干脏活：写代码、修 bug、补测试、生成执行脚本。

### 4.2 典型工作流拓扑

#### 4.2.1 工程链路接力
Gemini 读全局并校验文档一致性 -> Claude (Planner) 拆解子任务并生成 Handoff Note -> Codex (Executor) 稳健施工生成 Diff -> Claude / Gemini (Reviewer) 复核代码逻辑 -> 交由 Human (人类) 决定 PR 合并。

#### 4.2.2 研究/日常链路 (包工头与平台级并行)
Claude (Planner) 接到宏大目标（如跨领域调研） -> Subtask Orchestrator 拆出 5 个并行检索子任务 -> 分发给多个**低成本的专项 Agent (Literature Specialist)** 并行抓取并提取结构化表格 -> Gemini 汇总 5 份表格生成关联图谱草稿 -> 写入 LLM Wiki。

#### 4.2.3 对抗与审查模式 (Debate / Review Gate)
保障系统产出质量下限的核心机制。
1.  Codex 提交代码，触发 Review Gate。
2.  审查者 (Validator/Reviewer，如 Claude) 运行 CI 或做静态分析。
3.  如果失败，Reviewer **绝对不自行修改代码**，而是生成一份 `Review_Feedback` Artifact 打回。
4.  两者在 State Store 中反复交锋，直到通过门禁。
