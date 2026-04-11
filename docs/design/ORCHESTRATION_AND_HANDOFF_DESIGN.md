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

---

## 3. 智能调度器 (The Dispatcher) 与模型选型

在多模型生态下，系统依赖一个常驻的轻量级“智能调度器（Dispatcher）”来决定“让哪个 Agent（挂载什么模型）接手当前任务”。

### 3.1 任务画像与能力匹配
当状态机中出现一个新的待执行 Task（状态为 `pending`），Dispatcher 会读取任务画像并与第 6 层的 **Model Capability Matrix（模型能力矩阵）** 进行匹配，实现最优化调度：

*   **匹配上下文窗口 (Context Size)**：如果任务是“跨全量代码库的重构”（预估 Token > 150K），Dispatcher 坚决不路由给普通模型，而是定向分发给 **Gemini 1.5 Pro Agent**，以利用其海量窗口与 Context Caching 机制。
*   **匹配特种权限 (Special Modalities)**：如果任务标签涉及“修复前端视觉错位”，Dispatcher 会选择激活配置了 `computer_use` 权限并挂载 **Claude 3.5 Sonnet** 的 Agent，允许其直接读取屏幕截图并操作虚拟浏览器。
*   **成本降维调度 (Cost-Driven Downgrading)**：对于任务流中的低频智力环节（如“将抓取的网页内容格式化为 JSON”或“补充函数的基础注释”），Dispatcher 会自动将其路由给 **Llama 3 / Claude Haiku / Gemini Flash** 等经济高速模型，极大节约系统运行成本。

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
