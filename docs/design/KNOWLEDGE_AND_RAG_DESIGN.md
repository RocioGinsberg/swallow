# 知识双层架构：LLM Wiki 与 RAG 摄入设计 (Knowledge Architecture: LLM Wiki & RAG)

## 1. 核心定位：LLM Wiki 认知层与 RAG 证据层的分离
在处理复杂的软件工程和系统架构任务时，标准的“切块与嵌入”（Chunk & Embed）RAG 模式往往会面临极限。单纯的 RAG 只能解决“找得到资料”的问题，但很难稳定解决：历史决策之间的关系、模块职责边界、某条规则为什么存在、文档代码是否一致，以及长期项目认知的沉淀与复用。

因此，Swallow 构建了**知识双层架构**：

*   **RAG 检索层 (原始证据层)**：建立在代码、README、PR、Issue、外部文档之上的原始资料检索层。负责切块、向量化、混合索引、召回与回源。
*   **LLM Wiki (结构化认知层)**：建立在 RAG 之上的高层知识组织层。负责沉淀高价值的系统目标、调度器职责、术语、架构边界、决策记录（ADR）、工作流规则与阶段总结。

**核心协同关系**：
RAG 提供底层的事实依据，LLM Wiki 提供高层的认知摘要。调度系统（及通用编排 Agent）通过动态决策来判断何时查 Wiki 了解全局规范，何时回源到 RAG 寻找具体实现细节。

## 2. LLM Wiki 的写入与管理原则
LLM Wiki 绝不能成为任由底层大模型自由发散、堆砌形成的“第二知识幻觉层”。它必须遵循极其严苛的守卫规则：

*   **高门槛准入**：只有高价值、可复用、相对稳定的信息才能进入 Wiki。
*   **证据追溯**：Wiki 中的每条结论尽量带来源指针（如关联的 PR、文档片段、代码或决策记录）。
*   **复核机制**：所有对 Wiki 的修改必须经过严格复核。不允许执行级的专项 Agent 或常规任务 Agent 随意直接改写 Wiki。
*   **图书管理员介入 (Librarian Agent)**：系统知识的沉淀、冲突合并、去重及衰减，由高权限的图书管理员 Agent 结合人类审核来统一收口管理。

## 3. RAG 层的演进：Graph RAG 与全局理解

> **当前状态（v0.3.0）**：当前 RAG 实现基于 vector retrieval + keyword 检索，Graph RAG 与社区发现为远期演进方向，尚未进入实现 roadmap。以下描述为长期设计目标。

在底层 RAG 证据层，长期设计引入 **Graph RAG (图检索增强生成)** 与混合图谱：
*   **混合图谱结构**：将图结构的确定性关系（引用、继承、属于）与向量检索的模糊语义匹配相结合，提供具有深度上下文和逻辑链条的检索。
*   **全局问题回答 (Graph RAG)**：通过社区检测（Community Detection）算法将知识图谱聚类并生成层次化摘要。解决诸如“整个分布式系统的容灾策略是如何演进的？”这类传统向量检索束手无策的跨文档“纵览全局”问题。

## 4. 领域专属的数据摄入与切块策略 (Domain-Specific RAG Packages)
底层证据的数据类型多样，必须采用特定的提取与扩展策略：

*   **代码仓库 (Code & AST)**：
    *   基于抽象语法树 (AST) 进行解析。按类、函数、接口级别进行切块；提取函数签名、Docstring、输入输出依赖；保留跨文件的导入和调用链。
*   **长篇文档与学术PDF (Legal/Academic PDFs)**：
    *   层级化切块 (Hierarchical Chunking)。利用版面分析还原文档树结构（标题 -> 章节 -> 段落）；保留跨页的引用和脚注；生成章节级别的摘要（建立“父块”），保留具体细节作为“子块”。
*   **事件日志与追踪 (Event Logs)**：
    *   基于时间线 (Timeline-based) 与因果链切分。提取时间戳、Trace ID 和状态变更；将连续事件流聚合为单个“会话”切块。

## 5. 外部AI会话摄入 (External AI Handoff & Ingestion)
用户常常已经在 ChatGPT 或 Claude Web 界面中进行了初步探索。系统需要无缝继承这些外部上下文。这属于高复杂度的知识摄入，由专门的 **外部会话摄入 Agent (Ingestion Specialist)** 处理。

*   **工作流摄入**：支持导入 ChatGPT/Claude 的对话记录。
*   **深度提纯**：摄入 Agent 不是简单格式转换，它需要识别有效结论与无效发散，提取隐含决策点和被否决方案（路没走通的记录同样高价值）。
*   **结构化重组**：提取出上下文 (Context)、约束 (Constraints) 与目标 (Goals)。
*   **生成权威资产**：提纯后的信息转化为标准化的**“任务交接单” (Task Handoff Note)**，进入知识库暂存区，作为后续编排的指导。

### 5.1 Schema Alignment Note
自 Phase 19 起，外部 AI 会话摄入提纯后的 handoff vocabulary 在代码层统一落到 [src/swallow/models.py](/home/rocio/projects/swallow/src/swallow/models.py:87) 的 `HandoffContractSchema`。
本节术语映射：`Context` -> `context_pointers`，`Constraints` -> `constraints`，`Goals` -> `goal`。统一 schema 显式补充了 `done` 与 `next_steps`，用于和 orchestration handoff 保持一致。

## 6. Agentic RAG：从静态流水线到自主决策
对于复杂的系统问题，系统使用 **Agentic RAG** 将检索行为升级为智能体的“决策问题”：

1.  **动态路由与工具选择 (Routing & Tool Use)**：
    评估问题后自主选择工具：需要局部细节调用 Vector DB；需要解答宏观全局问题调用 Graph RAG/Wiki；需要精确统计调用执行器。
2.  **多跳推理与迭代检索 (Multi-hop Reasoning)**：
    打破“一次提问、一次检索”限制，执行 `检索 -> 阅读 -> 意识到信息缺失 -> 构建新查询 -> 再次检索` 的循环。
3.  **文档相关性自我反思 (Self-Reflection & Correction)**：
    判断当前召回质量不足时，主动触发反思机制调整搜索策略，防止强行幻觉。
