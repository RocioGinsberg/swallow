# 多智能体协同与编排设计 (Orchestration & Handoff)

## 1. 核心理念：异步协同与基于状态的通信

在传统的多智能体（Multi-Agent）框架中，Agent 之间通常采用“群聊机制”（共享同一个包含所有对话历史的上下文）。这种模式在长周期、高复杂度的软件工程任务中会迅速崩溃，导致严重的上下文污染（Context Pollution）和模型幻觉（Lost in the Middle）。

Swallow 系统的第 2 层（编排层）彻底摒弃了这种直连通信机制，确立了**“基于状态的异步协同”**原则：
**Agent 之间绝对不直接对话。它们通过修改底层状态机（State Store）、生成标准化工件（Artifacts）和触发系统事件（Event Log）来完成协作与工作交接。**

---

## 2. 结构化交接单 (Structured Handoff Notes)

为了解决接手任务时上下文爆炸的问题，系统强制引入了“提纯交接”机制。

### 2.1 告别“堆叠聊天记录”
当 Agent A（如调研 Agent）完成阶段性工作，准备将任务流转给 Agent B（如代码 Agent）时，它不能将自己过去 50 轮的推理 Prompt 丢给 B。Agent A 必须在退出前调用专用的 Harness 工具（如 `submit_handoff_note`），将这 50 轮的冗余信息进行自我压缩与提纯，生成一份结构化的**任务交接单 (Handoff Note)**。

### 2.2 交接单的四大要素 (Goal / Done / Next / Pointers)
一份合格的 Handoff Note 必须作为不可变的 Artifact 持久化存储，其内容格式强制包含：
*   **Goal (总目标)**：这个 Task 最终要解决的核心问题是什么。
*   **Done (已完成与踩坑记录)**：我已经尝试了什么？修改了哪些逻辑？排除了哪些错误路线？
*   **Next_Steps (后续行动指南)**：接手者接下来应该优先处理哪几个 TODO。
*   **Context_Pointers (上下文指针)**：**核心精髓**。交接单绝不携带大段源码或原文档，只传递资源的**引用指针 (References)**（例如：`git_commit_hash: 8f7e2a`，`artifact_id: arch_doc_v1`，`obsidian_note: #1024`）。接手的 Agent 根据这些指针自行去 Git 层或数据库精准加载所需的最小上下文，保持 Prompt 绝对干净。

#### Schema Alignment Note

自 Phase 19 起，代码层对 handoff vocabulary 的 authoritative 定义统一收敛到 [src/swallow/models.py](/home/rocio/projects/swallow/src/swallow/models.py:87) 中的 `HandoffContractSchema`。

本节术语与统一 schema 的映射为：
- `Goal` -> `goal`
- `Done` -> `done`
- `Next_Steps` -> `next_steps`
- `Context_Pointers` -> `context_pointers`

本设计文档未单独列出的约束集合，在统一 schema 中使用 `constraints` 表达，以便与 interaction / knowledge ingestion 侧保持同一交接契约。

---

## 3. 智能调度器 (The Dispatcher) 与角色路由

在多模型生态下，系统依赖一个常驻的“智能调度器（Dispatcher）”来决定“让哪个角色的 Agent接手当前任务”。调度的核心依据是 **智能体分类学 (Agent Taxonomy)**，而非单纯的模型品牌。

### 3.1 基于分类学的任务分发
当状态机中出现一个新的待执行 Task，Dispatcher 会读取任务画像并进行最优化角色与模型绑定分发：

*   **通用主体任务 -> 通用执行者 (General Executor)**：如果任务是“跨全量代码库的重构”或“起草系统设计”，Dispatcher 会将其分配给具备 `Task-State` 修改权限的通用执行者。它会根据 Token 预估为其挂载合适的模型（如超大上下文需求挂载 Gemini 1.5 Pro）。
*   **高优单一能力 -> 专项 Agent (Specialist Agent)**：遇到如“记忆提纯”、“外部知识摄入”或“失败日志分析”时，Dispatcher 会唤醒专项 Agent。专项 Agent 严格遵循输入输出边界，且绝无路由权，防止其演变为“隐藏的 Orchestrator”。
*   **底线守卫 -> 审查者 (Validator/Reviewer)**：在代码提交或知识晋升前，Dispatcher 会强制插入一个 Stateless 的审查者进行质量与合规检查。
*   **特权匹配与成本降维**：针对需要视觉交互的环节激活 `computer_use` 特权；针对低频智力环节（如 JSON 格式化）自动降维至经济高速模型（如 Haiku / Flash）。

### 3.2 护栏：防止隐藏的编排器 (Hidden Orchestrator)
Dispatcher 垄断了系统的任务流转语义。任何 General Executor 或 Specialist Agent 可以“建议”下一步行动，但**绝对不能静默修改全局路由策略或跨越当前阶段边界**。所有的决策都必须通过标准化工件交回 Dispatcher 裁决。

---

## 4. 多智能体协同拓扑 (Collaboration Topologies)

Swallow 编排引擎支持三种核心的复杂任务流转图谱（Topologies）：

### 4.1 接力模式 (Sequential Handoff)
这是最线性的流水线工作流。
*   **流程**：`Research Agent` (检索分析) -> Handoff Note -> `Coding Agent` (实现代码) -> Handoff Note -> `Review Agent` (安全合规检查)。
*   **应用场景**：常规的需求开发、标准的 Bug 修复。上一环节的结果是下一环节的绝对输入。

### 4.2 包工头模式 (Hierarchical Delegation)
应对宏大需求（如“从零开发一个完整的子系统”）时的层级拆解工作流。
*   **流程**：
    1.  一个高认知能力的 `Manager Agent` (基于 GPT-4o 或 Claude 3.5) 接收到宏观目标。
    2.  Manager Agent **不写代码**，而是利用系统工具在 State Store 中创建多个并行的子任务 (Sub-tasks)。
    3.  Dispatcher 将这些子任务并发分发给多个低配版的执行 Agent（如专注于后端的 Agent 和专注于前端的 Agent）。
    4.  子任务全部完成后触发回调，Manager Agent 唤醒，综合所有子工件进行最终合并与审查。

### 4.3 对抗与审查模式 (Debate / Review)
保障系统产出质量下限的核心机制。
*   **流程**：
    1.  `Coding Agent` 编写代码并提交至工作流分支，触发检查状态。
    2.  `Review Agent` 接手任务执行 CI 脚本和代码审计。
    3.  如果发现缺陷或报错，`Review Agent` **绝对不自行修改代码**，而是生成一份 `Review_Feedback` Artifact，连同报错日志一起作为交接单打回给 `Coding Agent`。
    4.  两者通过 State Store 中的状态回退反复交锋，直到测试通过，状态方可流转为 `completed`。
*   **核心价值**：防止单一 Agent 陷入逻辑盲区，利用对抗机制打破幻觉死循环。
