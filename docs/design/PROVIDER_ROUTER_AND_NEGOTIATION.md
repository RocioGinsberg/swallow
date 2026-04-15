# 模型路由与能力协商设计 (Provider Router & Capability Negotiation)

## 1. 核心定位：智能网关与方言翻译器

在多模型生态并存的时代，Swallow 系统的架构不能被单一的大模型供应商（Vendor Lock-in）所绑架。在第 6 层（模型接入与路由层），我们引入了区别于普通 API 转发网关的核心组件——**能力协商 器 (Capability Negotiator)** 与 **方言适配器 (Dialect Translators)**。

它的根本职责是：**承接上层统一的语义意图，将其智能分配至最具性价比的模型基座，并翻译为该模型能达到最高性能表现的“专属原生方言”。**

---

## 2. 统一语义描述 (Universal Semantic Description)

系统在编排层 (Orchestrator)、状态存储 (State Store) 和执行框架 (Harness) 中流转的所有数据结构，必须保持纯净和抽象。

*   **抵制硬编码**：坚决禁止在应用层代码中出现 `if openai:` 或写死特定模型的 API 结构。
*   **标准化契约**：工具 (Tools) 必须使用与平台无关的规范（例如标准的 JSON Schema 或 OpenAPI 规范）进行声明；系统 Prompt 与逻辑约束也必须采用纯粹的语义表达，而不是针对某个模型特调的模版。
*   **推迟绑定**：直到实际发包请求网络的最后一刻，统一语义才会流转到 Provider Router 进行具象化转换。

---

## 3. 下推差异化执行 (Push-Down Differentiated Execution)

当通用请求抵达路由层时，能力协商器会根据模型能力矩阵触发下推逻辑，通过专属适配器将请求“降维打击”为特定模型的原生形态：

### 3.1 Claude XML 适配器
*   **挑战**：Anthropic 的 Claude 模型对 JSON 和松散的文本指令敏感度较低，但在结构化 XML 标签体系下展现出极强的逻辑控制力。
*   **适配逻辑**：适配器会自动扫描上层传递的 System Prompt 和规则约束，将其转换包裹进对应的 `<thinking>`, `<scratchpad>`, `<instructions>` 等特定 XML 标签中。这能将 Claude 的长文 本遵循能力和减少幻觉的表现提升至最佳状态。

### 3.2 Gemini Context Caching 适配器
*   **挑战**：在涉及代码库跨文件重构或阅读整本长篇论文时，动辄百万 Tokens 的上下文会导致其他模型直接崩溃或面临天价账单。
*   **适配逻辑**：当路由层识别到本次任务依赖的对象体积庞大（例如通过 State Store 传递的 Context Pointers 指向了某个仓库的源码索引），且被分配给了 Gemini 模型时，适配器会自动拦截该请求。它不会拼接超长字符串，而是主动调用 Google 的 File API，建立并绑定 Context Cache URI，以极低成本和亚秒级首包延迟处理巨量上下文任务。

### 3.3 Codex / Code Model FIM 适配器
*   **挑战**：专注于写代码的模型（如开源的 DeepSeek Coder 或特定的 Codex 版本）往往不需要甚至不支持闲聊和系统 Prompt。它们期望的是纯粹的填空题。
*   **适配逻辑**：当需要直接修改文件或生成纯代码区块时，适配器会剥离所有的对话上下文记录，将业务意图重组为前缀（Prefix）与后缀（Suffix）结构的 `<fim_prefix>...<fim_suffix>` 专属标识，以此引导模型输出纯粹的中间代码段，极大降低输出的“废话率”。

---

## 4. 能力降级与通用代理兜底策略 (Graceful Degradation & Fallback)

在离线网络、成本压缩策略、主备切换，或系统默认的“三阶通用代理（Codex / Claude / Gemini）”因网络故障、速率限制（Rate Limit）暂时不可用时，系统必须具备强大的平滑降级与角色替补策略。

### 4.1 通用认知角色的替补与降级矩阵 (Cognitive Role Fallback Matrix)
系统依赖三大模型分别承担“施工”、“规划/审查”和“知识整合”角色。当首选模型不可用时，Router 将触发基于认知角色的替补逻辑：

1.  **施工执行者 (Codex) 不可用时**：
    *   **平滑替补**：路由至其他擅长代码补全与工具调用的模型（如 Claude 3.5 Sonnet 或 DeepSeek Coder V2）。
    *   **降级执行**：如果强力代码模型均不可用，将大 Diff 任务降级为逐行/逐块的局部修改指令，交由一般模型分批次完成。
2.  **规划与审查者 (Claude) 不可用时**：
    *   **平滑替补**：路由至 GPT-4o 或具备极强逻辑反思能力的模型。
    *   **机制降级**：如果逻辑强模型不可用，系统将**加强 Review Gate 的确信度阈值**，或强制要求人类介入确认任务拆解清单，绝不让逻辑较弱的模型（如本地 7B 模型）强行生成高风险的架构调整计划。
3.  **知识整合者 (Gemini) 不可用时**：
    *   **平滑替补**：使用其他具备 128k+ 长上下文窗口的模型（如 Claude 3 Opus/Sonnet 或 GPT-4-Turbo）。
    *   **机制降级**：由于失去 Context Caching 的成本优势，系统会自动触发**强制上下文压缩**，要求 Librarian Agent 缩小 RAG 召回窗口，放弃对全量代码库的直接阅读，转而依赖摘要层（Wiki）进行降级整合。

### 4.2 ReAct 风格降级转化 (Tool Capability Fallback)
当能力协商器发现目标（或替补）模型不具备原生工具调用（Native Tool Calling / Structured Outputs）能力时：
1.  **动态转化**：它会将抽象的 Tool Schema 在网关层实时渲染为 ReAct (Reasoning and Acting) 范式的纯文本引导语，并拼接到模型 Prompt 末尾（例如：“你可以使用以下工具，请按照 `Action: [tool_name]` 的格式输出”）。
2.  **强化解析**：在回包阶段，通过更鲁棒的正则表达式与输出流截断机制，在网关层将纯文本还原为标准的内部工具调用意图，确保即使在开源小模型上，系统的核心执行流转也不会断链。提取校验**：在模型返回结果后，适配器不再依赖 SDK 解析 JSON，而是使用强化的正则表达式从输出文本流中提取意图。

### 4.2 降级事件审计与安全阻断
*   **审计记录**：这种降级行为会在系统事件流 (Event Log) 中被打上 `tool_execution_degraded` 标签，为后续的链路排障提供追踪依据。
*   **坚守 State Store 防线**：如果弱模型在降级状态下由于幻觉生成了非法的工具参数，系统也不必惊慌。由于上层的 State Store 具备严格的单一事实防线和 Schema 校验，非法的状态突变会在此处被直接丢弃并打回重试，或者挂起至 `waiting_human` 状态，形成系统级的安全兜底。
