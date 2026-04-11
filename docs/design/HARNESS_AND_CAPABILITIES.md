# Harness 与能力分层设计 (Harness & Capabilities)

## 1. 核心概念：什么是 Harness？
Harness 并非简单的方法或函数列表，它是专门为 Agent 打造的**沙盒与执行上下文 (Sandbox & Execution Context)**。
如果说大模型是 Agent 的大脑，那么 Harness 就是其躯干与物理环境。它为 Agent 提供了对现实世界的感知途径与操作杠杆，同时设定了严格的物理法则（权限与边界）。Harness 确保 Agent 的每一次推理都能转化为受控的、上下文感知的有效行动。

## 2. 安全执行沙盒 (防污染隔离)
受 Claude Code 等先进开发环境的启发，系统的首要准则是：**绝对不能让自主运行的 Agent 破坏宿主环境。** Harness 实现了一套严密的防污染隔离机制：

*   **终端指令拦截与审查 (Command Interception):** Agent 生成的任何 Shell 命令都不会被直接抛给宿主系统。Harness 充当指令代理，拦截并进行静态扫描，基于黑白名单屏蔽如 `rm -rf /` 或系统级提权等高危破坏性指令。
*   **虚拟化与容器映射 (Isolation via Virtualenv & Containers):** 所有具备副作用的执行动作都被限制在隔离沙盒中。例如，Python 代码执行会被隐式重定向至项目专用的 Virtualenv，而需要系统级依赖的构建或测试命令，则被映射并分配至临时 Docker 容器内执行，从而确保主机底层环境零污染。
*   **状态快照与回滚:** 沙盒层提供了文件系统和执行状态的快照机制。若 Agent 的复杂操作链条进入死循环或产出灾难性修改，Harness 能够快速将上下文恢复至执行前的安全基线。

## 3. 能力分层架构 (The Capabilities Hierarchy)
Harness 内部的能力供应遵循严格的分层设计，从底层基础操作到高层行为准则，分为 Tools、Skills 和 Profiles 三层：

### 3.1 工具层 (Tools)：原子化操作
工具是系统能够执行的最小化、不可分割的原子操作。它们没有业务状态，只有明确的输入和输出。
*   **文件系统交互:** `read_file`, `write_file`, `glob_search`
*   **代码语法理解:** `ast_parse`, `find_references`
*   **系统底层操作:** `run_isolated_shell`, `fetch_url`

### 3.2 技能层 (Skills)：方法论工作流
技能是将多个“工具”和“专家提示词 (Prompts)”有针对性地打包在一起的复杂工作流。它为 Agent 注入了特定的专业执行范式。
*   **`test_driven_development` (测试驱动开发):** 赋予 Agent “编写失败测试 -> 编写代码实现 -> 运行测试验证 -> 重构” 的闭环工作流体系。
*   **`literature_review` (文献检索分析):** 深度整合了 `fetch_url`、`read_file` 以及内容结构化提取 Prompt 的能力集，专用于快速消化长文本、开源仓库文档和前沿学术资料。
*   **核心机制:** 技能封装了特定领域的业务逻辑，使得 Agent 在处理常见工程任务时不必每次从零推理工具链，极大提升了成功率与执行效率。

### 3.3 角色层 (Profiles)：行为边界与验证准则
Profiles 定义了 Agent 当前所处的“人设 (Persona)”，它是决定 Agent 行为约束、验证严格程度及拒绝执行阈值的顶层控制器。
*   **`Senior Reviewer` (资深审查专家):** 在此 Profile 下，Agent 具备极高的校验标准。它会强制启用性能分析工具、安全漏洞扫描和代码风格规范。如果检测到非惯用语法或潜在的内存泄漏，它将直接拒绝合并请求或强制打回修改。
*   **`Rapid Prototyper` (敏捷原型专家):** 优先追求系统运行速度和业务验证可用性，会主动放宽对测试覆盖率及极致性能的限制。
*   Profiles 决定了在特定任务上下文中，Harness 应该为 Agent 激活哪些 Skills 组合，以及设定何种程度的验收标准。

## 4. 与 Provider Router 的集成与分层调度
Harness 明确了应用层的标准能力协议，然而底层的大型模型厂商（如 OpenAI, Anthropic, Google）有着截然不同的 Tool Use / Function Calling 数据接口标准。同时，出于成本控制与专有任务的考量，系统实现了多维度的调度策略：

*   **能力协商器 (Capability Negotiator) 与动态翻译:** 作为一个中间适配层，Capability Negotiator 部署在 Harness 与模型网关 (Provider Router) 之间。当 Agent 根据 Profile 激活相应的 Tools 时，它负责将标准化的工具定义精准无损地“翻译”为对应底层 Provider 的结构（如 Claude 的 `tools` 或 Gemini 的 `functionDeclarations`）。这一机制完美桥接了上层沙盒工具链与底层多模型基座。
*   **模型分级路由 (Model Tiering):** 并非所有任务都需要顶配算力。Harness/Orchestrator 能够智能感知任务复杂度并进行路由：
    *   **高认知任务:** 复杂架构规划、深层逻辑推理等核心环节交由**旗舰级模型**（如 GPT-4o, Claude 3.5 Sonnet）处理。
    *   **低认知任务:** 大量低密度的重复执行、文本格式化、基础内容提取等交由**经济型/高速模型**（如 Llama 3, Claude 3 Haiku, Gemini Flash）完成，从而大幅降低 Token 成本并提升系统响应速度。
*   **专用 RAG 管道集成 (Specialized RAG Pipelines):** RAG 链路不能仅依靠大语言模型。Capability Negotiator 同样支持针对非生成式 AI 的专用模型路由。对于构建知识图谱与检索系统，Harness 专门调度特定的**向量嵌入模型 (Embedding Models)**（如 BGE-M3）和**重排模型 (Reranking Models)**（如 Cohere Rerank）来完成高精度的召回，最后再交由 LLM 完成最终的总结与生成。