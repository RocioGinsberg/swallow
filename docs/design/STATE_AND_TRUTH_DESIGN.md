# 状态与事实层设计 (State & Truth Layer)

## 1. 核心理念 (Core Philosophy)

在传统的 AI Agent 设计中，系统通常高度依赖大语言模型（LLM）的“对话历史（Chat History）”来维持上下文。然而，随着任务复杂度的提升，这种方式暴露出致命缺陷：对话历史是线性的、冗长的、易丢失关键细节的，且极易导致 LLM 产生幻觉。它将“意图”、“执行过程”和“最终结果”混为一谈。

**抛弃单纯的对话历史，引入状态机（State Machine）与单一事实源（Single Source of Truth）**是本架构的核心基石。

*   **单一事实源 (Single Source of Truth)**：LLM 不应该依赖其有限的上下文窗口去“记忆”当前代码库的状态或任务进行到了哪一步。所有的客观事实必须托管在外部的、可验证的存储引擎中（Git、数据库、文件系统）。LLM 被降维成一个“无状态的纯函数”，它只负责读取当前的绝对事实，进行推理，并发出改变状态的指令。
*   **状态机驱动 (State Machine Driven)**：将复杂的工程任务转化为具有明确生命周期的状态机。状态的流转（如“进行中”、“等待人类介入”）不仅为系统提供了极强的可预测性，还使得任务的随时中断、可观测性和灾难恢复成为可能。

---

## 2. 四件套 (The Four Pillars)

为了实现上述理念，系统在底层构建了四个核心组件，统称为“四件套”：

### 2.1 状态库 (State Store)

**职责**：维护和管理任务的全局状态机。它是 Agent 当前到底在“做什么”和“处于什么阶段”的权威数据字典。

**数据结构与流转**：
状态库通常以结构化的 JSON 格式持久化。任务状态流转包含明确的边界，例如：
`pending` (排队中) -> `running` (执行中) -> `waiting_human` (等待人类提供输入/授权) -> `running` (恢复执行) -> `completed` (完成) 或 `failed` (失败)。

**JSON 示例**：
```json
{
  "task_id": "tsk_9f8a7b",
  "status": "waiting_human",
  "current_phase": "design_review",
  "context_refs": ["art_112", "git_commit_8f7e2a"],
  "metadata": {
    "started_at": "2023-10-25T10:00:00Z",
    "last_updated": "2023-10-25T10:15:00Z"
  }
}
```

### 2.2 事件流 (Event Log)

**职责**：一个只追加（Append-only）的事件日志库。它记录了系统中发生的所有状态变更、工具调用和决策过程。
事件流是系统的“黑匣子”，为审计追踪（Auditing）、性能遥测（Telemetry）以及任务重放（Replay/Time-travel）提供基础。借鉴 CQRS 和事件溯源（Event Sourcing）模式。

**事件载荷 (Event Payload) 结构**：
```json
{
  "event_id": "evt_001",
  "timestamp": "2023-10-25T10:05:22Z",
  "event_type": "tool_execution",
  "agent_id": "architect_agent",
  "payload": {
    "tool_name": "run_shell_command",
    "parameters": {"command": "npm run test"}
  },
  "diff_or_result": "Test failed: 2 errors found"
}
```

### 2.3 工件库 (Artifact Store)

**职责**：专门用于存储、追踪和版本化控制 Agent 产出的“非代码类实体资产”或“中间结构化数据”（如架构设计草案、API 契约文档、搜集到的知识图谱片段等）。

**生命周期与版本控制**：
工件不应该只是随时被覆写的临时文本，而是有着严格的生命周期：
*   **Draft (草稿)**：Agent 正在迭代和思考的初步产出。
*   **Reviewed (已评审)**：经过人类或其他 Reviewer Agent 审查和批准的版本。
*   **Canonical (规范/最终版)**：被确认为单一事实源并作为后续任务参考基准的最终工件。

### 2.4 Git 事实层 (Git Truth Layer)

**职责**：实现与底层版本控制系统（Git）的深度整合。对于代码和文本类的编辑，文件系统本身不足以作为事实源，带有版本历史的 Git 才是。

**核心机制**：
*   **自动分支 (Auto Branching)**：Agent 接收到任务后，自动基于主干创建隔离的工作分支（如 `agent/tsk_9f8a7b-fix-login`）。
*   **检查点提交 (Checkpoint Commits)**：Agent 在执行具有破坏性修改或完成一个子步骤后，自动执行原子性的 WIP (Work In Progress) Commit。
*   **安全回滚 (Instant Rollback)**：一旦代码测试失败，或检测到 LLM 的幻觉（破坏了语法树），系统可以通过 Git Checkpoint 瞬间将代码恢复到上一个健康状态，无需依赖 LLM 尝试“把代码改回去”。

---

## 3. 数据流示例 (Data Flow Example)

**场景：修复一个特定的 UI 渲染 Bug**

以下是数据如何在“四件套”中流转的典型场景：

1.  **触发阶段**：用户提交 Bug 描述。
    *   **State Store**：创建一个新任务，状态置为 `pending`。
    *   **Event Log**：追加一条 `task_created` 事件。
2.  **准备阶段**：Agent 接手任务。
    *   **State Store**：状态更新为 `running`。
    *   **Git Truth Layer**：自动从 `main` 切出一个新分支 `fix/ui-render-bug`。
3.  **分析与规划阶段**：Agent 通过检索代码库定位问题，并撰写修复方案。
    *   **Artifact Store**：生成一个修复方案的 `Draft` 工件（包含问题根因和修改计划）。
    *   **State Store**：状态更新为 `waiting_human`，请求用户确认修复方案。
4.  **评审阶段**：用户阅读方案并点击“同意”。
    *   **Artifact Store**：该工件状态流转为 `Reviewed`。
    *   **State Store**：状态切回 `running`。
5.  **执行修改**：Agent 依据已评审的方案修改代码。
    *   **Git Truth Layer**：Agent 修改完成后，触发 `git commit -m "checkpoint: apply UI fix"`。
    *   **Event Log**：记录 `file_modified` 和 `git_commit_created` 事件。
6.  **验证与回滚**：Agent 运行本地单元测试。
    *   *假设测试失败*：**Git Truth Layer** 立即执行 `git reset --hard HEAD~1` 丢弃错误代码，**Event Log** 记录 `rollback_executed`，Agent 重新尝试。
    *   *假设测试成功*：**Git Truth Layer** 追加 `commit -m "fix: resolve UI render bug"`。
7.  **完成阶段**：
    *   **State Store**：状态置为 `completed`。
    *   **Event Log**：记录 `task_finished`。
    *   **Artifact Store**：相关文档标记为 `Canonical`。

---

## 4. 状态语义的抽象与差异化下推 (State Abstraction & Push-Down Execution)

为保证系统的持久化层不被特定的模型供应商（Vendor Lock-in）所绑定，状态与事实层在设计上必须与底层的模型能力高度解耦。

### 4.1 统一语义描述 (Universal Semantic Description)
状态库（State Store）与事件流（Event Log）中记录的所有任务意图、提示语模板（Prompt Templates）以及工具调用的负载参数（Payload），均强制采用与底层模型无关的**统一语义描述**。系统坚决抵制在状态机或工件库中硬编码诸如 OpenAI 的特定 Function Calling 格式，或 Anthropic 特有的结构标志（如 `<tool_name>` 等 XML 标签）。

### 4.2 下推差异化执行 (Push-Down Differentiated Execution)
当系统状态机流转到需要大模型进行推理的环节时，这种“通用语义”才会流转至网络底层的 **能力协商器 (Capability Negotiator)**。协商器负责读取当前的统一状态，并执行**下推差异化执行**。例如：
*   它将统一的会话状态转化为 Claude 最适合的 XML 结构树。
*   它利用状态记录中的长文档哈希索引，自动对接 Gemini 的 Context Caching 功能。
*   它对代码层面的结构修改需求，组装为 Codex 的 FIM (Fill-In-the-Middle) 格式。

### 4.3 状态驱动的优雅降级 (State-Driven Graceful Degradation)
当系统由于策略、成本或离线环境退级到较弱的本地/开源模型时，这些模型可能不具备复杂的原生 Tool Calling 能力。此时，路由层与能力协商器会触发工具的**优雅降级 (Graceful Degradation)**，将通用结构的调用意图转化为 ReAct Prompt：
1.  **事件审计**：这种降级操作会被事件流（Event Log）精准捕获，例如标记该次动作为 `tool_execution_degraded`，用于系统后续的模型行为审计。
2.  **安全兜底**：即便发生降级且模型利用正则解析给出了存在幻觉的工具参数，由于 **State Store** 具有严格的单一事实防线和 Schema 校验，非法的状态突变会被直接拦截。系统会将任务退回安全状态或直接挂起至 `waiting_human` 状态，确保容错与绝对安全。