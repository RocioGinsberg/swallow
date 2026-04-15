# 智能体分类学设计 (Agent Taxonomy)

## 1. 文档目的与设计理念 (Purpose & Design Principles)

本设计文档定义了 Swallow 系统的**智能体分类学 (Agent Taxonomy)**。由于 Swallow 系统不仅仅是一个单次对话的套壳工具，而是围绕任务编排、上下文检索、执行器集成以及状态持久化构建的复杂工程，因此仅仅称呼某个组件为“Claude Agent”或“记忆 Agent”是远远不够的。

本分类学旨在回答以下核心问题：
*   系统中应该存在哪些类型的 Agent？
*   通用执行者（General Executor）与专项智能体（Specialist Agent）的区别何在？
*   如何超越模型品牌（如 Gemini、Claude）来描述 Agent 的系统角色？
*   如何定义不同 Agent 的执行权限、记忆权限及部署形态？
*   如何防止新增的 Agent 意外演变成隐藏的全局编排器（Hidden Orchestrator）或隐式的全局记忆写入者。

**核心设计原则**：
*   编排器（Orchestrator）与 Harness 运行时边界必须保持清晰。
*   能力（Capabilities）应始终作为一等公民对象。
*   状态（State）、事件（Events）与工件（Artifacts）必须保持分层并具备可观测性。
*   检索是系统的通用能力，而不是某一个执行者的副作用。
*   供应商（Provider）、底层后端、执行器族（Executor family）与 Agent 角色绝对不能混为一谈。
*   知识的晋升（Knowledge Promotion）必须保持显式且受到策略守卫（Policy-gated）。
*   隐式的全局记忆写入绝不能成为默认行为。

因此，本分类学从**三个正交的显式维度**对 Agent 进行划分：
1.  **系统角色 (System Role)**：该 Agent 在系统中承担什么职责。
2.  **运行站点 (Execution Site)**：该 Agent 的运行环境或后台支持在哪里。
3.  **记忆权限 (Memory Authority)**：该 Agent 可以读取或写入哪些范围的记忆与事实源。

---

## 2. 系统角色 (System Role)

### 2.1 编排器 (Orchestrator)
*   **定义**：决定系统“下一步该做什么”。它负责调度能力、拼装上下文、记录执行结果以及处理重试/中断/恢复逻辑。
*   **核心职责**：垄断**任务进展语义 (Task Progression Semantics)**。
*   **设计底线**：编排器是唯一的协调层。绝对不能让新增的执行者或专项 Agent 意外获取全局路由的决策权，否则系统将失去可观测性。

### 2.2 通用执行者 (General Executor)
*   **定义**：在任务流中能够独立完成相对完整或大体量工作切片的 Agent。
*   **典型职责**：执行代码仓库级工作、文件编辑、命令行操作、拟定结构化计划草案、大跨度任务总结等。
*   **典型家族**：API Executor、CLI Executor。
*   **能力边界**：通用执行者可以产出大量核心任务工件（Artifacts），但**无权**重新定义全局路由策略、规范化记忆策略或跨越当前阶段边界。

### 2.3 专项智能体 (Specialist Agent)
*   **定义**：拥有**单一且高价值边界职责**的 Agent。
*   **典型特征**：不试图接管整个任务生命周期。具有极强的输入输出边界、较窄的写权限、明确的成功标准及较低的治理风险。
*   **典型例子**：记忆提纯者 (Memory Curator)、检索评估者 (Retrieval Evaluation Agent)、失败日志分析者 (Failure Analysis Agent)、移动端交互者等。

### 2.4 验证者/审查者 (Validator / Reviewer)
*   **定义**：不生成核心工作产物，主要用于评估、审计和检查其他组件产出质量的 Agent。
*   **核心职责**：回答“代码偏离设计了吗？”、“知识符合晋升标准吗？”、“请求违规了吗？”等守门问题。
*   **典型例子**：一致性审查者 (Consistency Review Agent)、安全风险审计者、引用溯源检查者。

### 2.5 人类操作员 (Human Operator)
*   **定义**：人类不是 Agent，但在此分类学中是一等公民角色。
*   **核心职责**：审批设计方向、进行高风险变更的合并及决定知识的最终晋升，解决系统不应自动裁决的歧义。

---

## 3. 核心对比：通用执行者 vs 专项智能体 (General Executor vs Specialist Agent)

如果把每个好用的模型或能力辅助都统称为“Agent”并赋予相同的权限，将导致系统职责的混乱。我们必须明确区分通用执行与专项辅助的界限。

*   **通用执行者 (General Executor)**：当系统需要一个代理来承担一大块实际工作（如编写代码、执行 CLI 命令、撰写完整设计稿）时使用。它们在**工作广度**上较高，但风险也更高（易出现范围蔓延与过度重构）。
*   **专项智能体 (Specialist Agent)**：当系统需要对某一局部功能（如压缩上下文、分析检索结果质量）进行深度打磨时使用。它们在**职责范围**上极窄，边界清晰，利于策略拦截。

**判断法则**：
*   如果可以合理地要求该角色“接管这步任务并产出主要输出”，它是**通用执行者**。
*   如果任务更偏向于“在一个受限区域内分析、压缩、审计、验证、提纯或提出建议”，它是**专项智能体**。

---

## 4. 运行站点 (Execution Site)

系统角色（Role）不应与部署形态（Site）混淆。同一个角色可以有不同的运行站点。

*   **本地 (Local)**：运行在与主任务环境相同的机器或工作区内。拥有对本地状态的直接访问权和较低延迟。风险与本地执行权限和宿主环境深度耦合。
*   **云端支持 (Cloud-backed)**：即便调用发生在本地，其能力由远程 API 或服务提供支撑（如强逻辑模型进行的长上下文反思）。优势在于模型能力强，但运行时内部逻辑不透明，更需严格的策略拦截。
*   **远程计算节点 (Remote Worker)**：在独立的机器或远端站点上执行实际任务（偏向于未来的扩展拓扑），存在较高的网络传输、交接和安全复杂性。
*   **混合部署 (Hybrid)**：以受治的方式跨越多个站点。例如本地网关接收移动端输入，委派给云端模型解析意图，再返回本地执行指令。

---

## 5. 记忆权限 (Memory Authority)

由于 Swallow 严格区分任务状态（Task State）、暂存知识（Staged Knowledge）与规范事实（Canonical Truth），并非所有 Agent 都有权跨越这些记忆边界。

1.  **无状态 (Stateless)**：除明确的入参外，不跨调用保留记忆。最安全的默认选项，适合审查者和单次摘要器。
2.  **任务状态读写 (Task-State Access)**：允许读取或修改任务执行所依赖的本地状态、事件或运行时产出。通用执行者通常拥有此权限。
3.  **任务记忆读写 (Task-Memory)**：可以在当前任务或会话周期内写入与读取记忆伪像。适合记忆提纯者、失败分析者等。产出物通常为恢复记录（Resume Note）或局部记忆压缩摘要。
4.  **暂存知识库读写 (Staged-Knowledge)**：有权生成或修改待审查的“知识候选对象”（Knowledge Candidates）。通常适用于知识摄入 Agent 或研发提议整理助手。
5.  **规范写入禁止 (Canonical-Write-Forbidden)**：**核心安全标签**。系统内大多数 Agent 默认**被严格限制直接突变核心规范知识真相**。它们只能提建议、打草稿或准备晋升候选对象。
6.  **规范晋升权限 (Canonical Promotion Authority)**：权限域最窄、最敏感的分类。通常只属于极少数经过严格 Workflow 约束或通过操作员确认的人机协作节点。

---

## 6. 标准命名格式与反模式 (Naming Format & Anti-Patterns)

### 6.1 推荐命名规范 (Naming Format)
在系统架构讨论中，每一个 Agent 都必须严格遵循四个字段的显式命名法：
`[系统角色] / [运行站点] / [记忆权限] / [功能领域]`
`( [System Role] / [Execution Site] / [Memory Authority] / [Domain] )`

**示例**：
*   `general-executor / local / task-state / codex-cli` (本地终端代码执行者)
*   `general-executor / cloud-backed / task-state / planning-api` (云端支持的规划与摘要执行者)
*   `specialist / cloud-backed / task-memory / memory-curator` (云端支持的任务记忆提纯专家)
*   `validator / cloud-backed / stateless / consistency-review` (无状态的云端架构一致性审查者)
*   `specialist / hybrid / stateless / mobile-operator-interaction` (跨混合架构的移动端交互解析专家)

### 6.2 常见反模式 (Anti-Patterns)
1.  **唯品牌论智能体 (The Brand-Only Agent)**：仅仅将其称呼为“Gemini Agent”或“Claude Agent”，这完全掩盖了其在系统中的权限、角色与记忆范围。
2.  **隐藏的编排器 (The Hidden Orchestrator)**：一个计划生成、路由辅助或反思类的 Agent，在未被授权的情况下，静默地接管了系统下一步执行走向的决策。这极大地破坏了可观测性。
3.  **隐式的全局写入者 (The Implicit Global Memory Writer)**：未经严格的验证防线，局部的研究或反思智能体就能直接将其生成的见解写入长期的规范化知识库中，造成事实源污染。
4.  **全能智能体 (The Everything Agent)**：号称能同时承担计划、执行、审查、路由及提纯记忆的功能。这通常意味着功能定义不足和巨大的治理风险。

### 6.3 默认的安全预设 (Recommended Defaults)
当为系统引入新的 Agent 实体时，推荐的基准假定应当是：
*   **系统角色**：默认为 `specialist`。
*   **运行站点**：选择运维最简单的方式，但绝不以站点指代角色。
*   **记忆权限**：默认为 `stateless` 或仅限 `task-memory`。
*   **规范事实权限**：默认 `Canonical-Write-Forbidden`。
只有在具备充足的工程需求设计时，才可显式地放宽上述限制。

---

## 7. Swallow 典型角色模式 (Canonical Role Patterns)

结合系统长期的通用代理协作（Claude、Gemini、Codex 作为不同认知层级的通用代理）与不断扩展的专项代理生态，以下是系统中的核心典型角色指派模板：

### 7.1 通用代理的认知领域分野 (Cognitive Domains of General Agents)
这三者在系统中不是互相替代的竞品，而是代表不同的高阶认知模式：
1.  **施工与执行者 (Implementation Executor / e.g., Codex)**
    *   `general-executor / local / task-state / implementation`
    *   **核心认知**：稳健施工。
    *   **职责**：明确的实现任务、修 bug、补测试、代码修改、终端命令执行。擅长将抽象要求转化为可落地的代码和 Diff。
2.  **规划与审查者 (Planner & Reviewer / e.g., Claude)**
    *   `general-executor / cloud-backed / task-state / planning-and-review`
    *   **核心认知**：方案判断、任务拆解与风险识别。
    *   **职责**：方案比较、大改动前的约束建模、过程纠偏、复杂的逻辑反思与审查。
3.  **知识与上下文整合者 (Knowledge & Consistency Agent / e.g., Gemini)**
    *   `general-executor / cloud-backed / task-state / knowledge-integration`
    *   **核心认知**：长上下文吸收与一致性维护。
    *   **职责**：大仓库理解、长历史记录或多文档汇总、Wiki 草稿生成、文档与实现的一致性检查。

### 7.2 核心专项智能体 (Core Specialist Agents)
专项 Agent 应当优先使用低成本 API 或本地模型，处理高度标准化的输入输出。
1.  **图书管理员 Agent (Librarian Agent)**
    *   `specialist / cloud-backed / staged-knowledge / memory-curation`
    *   **职责**：系统记忆质量的守门人。负责任务结束后的降噪摘要提炼、知识库冲突检测与合并仲裁、周期性记忆衰减（归档过时信息）。**权限例外**：允许写入 Staged-Knowledge，但必须生成详细变更日志供审计。
2.  **外部会话摄入 Agent (Ingestion Specialist)**
    *   `specialist / cloud-backed / staged-knowledge / conversation-ingestion`
    *   **职责**：将外部（ChatGPT/Claude Web 等）非结构化脑暴聊天记录转化为结构化的知识资产。负责识别有效结论、提取被否决的路径，并带上来源标注进入知识库暂存区。
3.  **文献解析 Agent (Literature Specialist)**
    *   `specialist / cloud-backed / task-memory / domain-rag-parsing`
    *   **职责**：服务于学术等领域的高级解析器。不是简单总结，而是从批量 PDF 中提取结构化对比表（数据集、模型、指标）、识别引用关系与冲突。需要挂载专门的 Domain RAG Package。
4.  **编排策略顾问 Agent (Meta-Optimizer)**
    *   `specialist / cloud-backed / read-only / workflow-optimization`
    *   **职责**：定期扫描 Event Log 和已归档任务轨迹。识别反复出现的模式以提议新 Workflow、发现脆弱环节提议 Skill 优化、分析模型路由表现以建议策略调整。**输出仅为供人类决定的提案**。

### 7.3 核心验证者 (Core Validators)
1.  **质量审查 Agent (Quality Reviewer / Validator)**
    *   `validator / cloud-backed / stateless / artifact-validation`
    *   **职责**：在关键节点对其他 Agent 产出进行**独立校验**（如：代码脚本是否能跑通、提取表格是否与原文一致）。**绝对无状态**且**无修复能力**（发现问题只返回错误列表打回重做），确保防线干净。
2.  **一致性审查者 (Consistency Review Agent)**
    *   `validator / cloud-backed / stateless / consistency-check`
    *   职责：评估候选知识对象的质量、识别冗余与架构偏离。