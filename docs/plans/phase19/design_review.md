# Swallow 架构与设计理念把关审查报告 (Architecture & Design Review)

## 审查目标
基于 `@ARCHITECTURE.md` 与 `docs/design/*` 对 Swallow 项目的整体设计理念进行一致性检查与总结提取，为下一阶段 (Phase 19) 的具体执行提供宏观把关。

## 1. 核心设计哲学提炼

Swallow 的核心设计理念可以高度概括为**“反共识的显式化”**：
1. **反聊天记录崇拜 (Explicit State over Chat History)**：彻底摒弃依赖 LLM 长上下文对话记录来维护状态的做法。所有的流转必须通过“四件套”（State Store, Event Log, Artifact Store, Git Truth Layer）进行持久化，Agent 沦为“无状态的纯函数”。
2. **反群聊模式 (Async Structured Handoff over Group Chat)**：多 Agent 协作不通过直接对话，而是通过结构化的 `Handoff Note`（交接单：包含 Goal, Done, Next_Steps, Context_Pointers）进行基于状态的异步通信。
3. **反模型绑定 (Semantic Abstraction over Vendor Lock-in)**：上层业务流、工具声明和约束使用统一语义（Universal Semantic Description），直到第 6 层路由层（Provider Router）才通过能力协商器（Capability Negotiator）下推翻译为模型原生方言（如 Claude XML、Gemini Caching、Codex FIM）。
4. **反黑盒涌现 (Explicit Workflow over Implicit Emergence)**：系统的自我进化与记忆不依赖大模型的黑盒能力，而是建立明确的归档期 (Consolidation Phase)，由专职的 Librarian Agent 进行实体化资产提取与记录。
5. **反裸机执行 (Sandboxed Execution over Direct Shell)**：Harness 拦截一切系统调用，使用 Virtualenv 或 Docker 等进行副作用隔离，配合 Git Truth Layer 提供原子级的快照和安全回滚防线。

## 2. 设计一致性评估

经过对架构层和多个垂直设计域（Interaction, Orchestration, RAG, Provider, Truth, Harness, Memory）的交叉比对，系统的架构设计展现出极强的一致性：
- **强耦合解绑**：各层职责清晰，比如交互层的草稿不会污染状态库；能力提供者（Tool/Skill）与底层模型方言被 Router 层严格隔绝。
- **概念一致性瑕疵（需统一）**：
  关于“任务交接单 (Handoff Note)”和“任务意图”的核心要素定义在几份文档中存在细微表述差异：
  - `KNOWLEDGE_AND_RAG_DESIGN.md` 中外部 AI 会话摄入提取为：`Context`, `Constraints`, `Goals`。
  - `ORCHESTRATION_AND_HANDOFF_DESIGN.md` 中标准的交接单包含：`Goal`, `Done`, `Next_Steps`, `Context_Pointers`。
  - `INTERACTION_AND_WORKBENCH.md` 中的“任务对象”分为：`Goal`, `Context Ref`, `Constraints`。
  **建议**：在具体的代码 Schema 实现中，需将这三处的术语统一（例如整合为 `Goal`, `Constraints`, `Done/History`, `Next_Steps`, `Context_Pointers`），确保跨层流转的契约完全一致。

## 3. 把关意见与演进建议

结合 `docs/active_context.md` 中的状态（当前处于 Phase 18 刚收口、待规划下一轮次的阶段）：

1. **严守基于状态的异步流转**：在进入下一轮具体的 Executor 或 Topology 实现时，极易为了工程便利绕开 State/Artifact 层直接在内存中传递 Context。必须坚守“Agent 之间绝不直接对话，只读写指针”的底线。
2. **完善交接契约 (Handoff Contract) 的 Schema**：既然 Phase 18 刚刚完成了 `Remote Handoff Contract Baseline`，应借机统一上述设计文档中关于交接单各字段的细微表述差异，固化 `remote_handoff_contract.json` 的标准验证逻辑。
3. **能力协商与降级的切片落地**：设计文档中规划的 Provider 降级与兜底非常宏大。在接下来的 Track 规划中（不论是 Capabilities 还是 Orchestration），不要试图一次性实现全部方言适配器，而是通过明确的 Phase 切片，逐个（如先 Gemini Caching，后 Claude XML）落地并辅以 regression 测试保障。

## 结论
Swallow 的整体设计理念高度成熟、自洽，并且极具实战价值。它精准识别了多 Agent 协作中的上下文灾难，采用基于 Git/State 的显式工件流完美替代了对话流。设计理念审查已通过，项目架构稳健，可以安全地向 Phase 19 迈进。