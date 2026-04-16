# 交互与工作台层设计 (Interaction & Workbench Layer)

## 1. 核心定位：从“聊天窗”到“工作台”

目前的 AI 产品普遍采用一维的线性聊天流 (Linear Chat Stream) 作为主要交互界面。这种模式对于日常问答足够，但对于需要审阅长篇代码、对比多份文档、进行任务重构的高复杂度知识工作来说，线性信息流不仅效率低下，而且极易导致上下文丢失。

Swallow 系统的第一层（交互与工作台层）定位于**“立体操作环境”**。它拒绝将聊天作为事实载体，而是将其降级为“操作杠杆”，真正的舞台留给系统运行时的结构化工件 (Artifacts) 与任务状态机。

---

## 2. 多端协同矩阵 (The Multi-Client Matrix)

系统基于“统一后端状态，多元前端表达”的理念，支持三种维度的交互入口，以满足知识工作者在不同场景下的需求：

### 2.1 CLI 终端 (The Hacker's Entry)
作为对开发者最友好的第一前线，CLI 强调的是**隐蔽性、自动化与快速干预**。
*   **状态透视**：通过命令行实时输出正在流转的任务树状图（类似 `htop`），而非滚动打印冗长的 Agent 思考日志。
*   **快捷拦截与纠偏**：允许用户通过热键 (Hotkeys) 随时暂停后台跑偏的 Agent，修改其本地上下文环境或调整权限配置后恢复执行。
*   **本地管道整合**：完美融入现有的 Linux/Unix 生态，可以直接将 `git diff` 或 `grep` 的结果通过管道 (Pipes) 直接喂给系统的任务分发接口。

### 2.2 IDE/Obsidian 插件 (The Deep Context Integration)
知识工作者的时间主要消耗在编辑器中。Swallow 的插件化支持意味着它可以直接感知工作者当前的心智焦点（Mental Context）。
*   **伴随式阅读与重构**：不仅是生成代码，更强调结合 Graph RAG 对代码或笔记仓库的全局分析。例如，在 Obsidian 中选中一段构思，直接右键将其转化为系统的 Task Handoff Note (交接单) 派发给后台执行。
*   **Inline 状态呈现**：代码或文本的修改建议直接以 Inline Diff 的形式浮现，拒绝强行写入。任务的状态标志（`running`, `waiting_human`）融入 IDE 的底栏状态监控。

### 2.3 Web/桌面工作台面板 (The Control Center)
应对多智能体复杂编排的大局观监控中心，更接近于一个高阶的 CI/CD 看板。
*   **任务链图谱可视化**：清晰展现父任务是如何被 Manager Agent 拆解为多个子任务的，以及它们目前的并发执行进度。
*   **工件审阅区 (Artifact Review Area)**：这区别于聊天框，是一个独立的左右分栏区域。左侧是只读的 `Draft` 版本，右侧提供丰富的 Diff 和批注工具，只有人类审查通过（Approve）后，工件才会晋升为 `Canonical` 资产并存入系统记忆层。

---

## 3. 核心交互哲学与关键机制

### 3.1 意图显式剥离 (Explicit Intent Separation)
用户不能简单丢一句“帮我修一下刚才那个 Bug”给系统。交互层在接收输入时，会自动触发“提纯引导”，强制或辅助用户将输入结构化为明确的**任务对象 (Task Object)**，拆分出：`目标 (Goal)`、`上下文引用 (Context Ref)` 与 `约束条件 (Constraints)`，从而杜绝模棱两可的指令污染底层调度。

#### Schema Alignment Note

自 Phase 19 起，交互层提纯后的任务交接 vocabulary 与其他层统一对齐到 [src/swallow/models.py](/home/rocio/projects/swallow/src/swallow/models.py:87) 的 `HandoffContractSchema`。

本节术语与统一 schema 的映射为：
- `Goal` -> `goal`
- `Context Ref` -> `context_pointers`
- `Constraints` -> `constraints`

交互层原始描述未单独展开的 `done` 与 `next_steps`，在统一 schema 中保留为标准字段，供后续 handoff / review / dispatch 路径复用。

### 3.2 中断与接管机制 (Handoff & Interrupt)
系统不盲目追求全自动，而是拥抱**人机交替 (Human-in-the-Loop)**。
*   **权限阻断墙**：当底层 Agent 企图执行高危沙盒命令或尝试合并关键分支时，交互层会强行弹出 `waiting_human` 警告，等待终端用户敲击确认。
*   **平滑交接 (Graceful Takeover)**：用户若发现 Agent 陷入困境，可以随时按下暂停，进入系统环境，手动完成两行关键代码的修改，并在 CLI 中输入 `resume --hint "I fixed the root class, proceed with tests"`，Agent 将无缝读取最新现场继续推进。

### 3.3 拒绝聊天记录崇拜
交互界面上的对话流是”易失性 (Volatile)”的草稿。任何对业务有实际影响的决议、长篇分析结果和代码，都不会留存在聊天记录中，而是会在交互层面被视觉上剥离出来，明确提示已固化为后端的 **Artifact** 或记录至 **Event Log** 中。

---

## 4. AI 聊天面板定位 (AI Chat Panel — Open WebUI)

### 4.1 为什么需要聊天面板

系统中存在两种本质不同的交互模式：

| 交互模式 | 适合的 surface | 典型场景 |
|---|---|---|
| **任务编排与执行**（Planner → Executor → ReviewGate） | CLI（`swl`） | 创建任务、运行任务、查看状态、审查 artifact、知识管理 |
| **探索性对话**（问答、脑暴、初步调研） | AI 聊天面板 | 快速提问、浏览模型回复、导入外部会话、人工审批 |

CLI 擅长结构化操作但不擅长自由探索。聊天面板擅长自由探索但不应承担编排职责。两者互补。

### 4.2 推荐方案：Open WebUI

**Open WebUI**（https://github.com/open-webui/open-webui）是当前最成熟的自托管 AI 聊天面板：

*   多用户 RBAC + SSO（OIDC）
*   OpenAI 兼容接口——可直连 Swallow 的 new-api 或 TensorZero
*   内置 RAG（支持 9 种向量数据库）
*   Web 搜索集成（15+ 搜索引擎）
*   Artifact 渲染（HTML/代码侧边栏预览）
*   语音/视频交互

### 4.3 职责边界（关键）

**聊天面板不是 Swallow 的编排器。** 以下边界必须严格遵守：

| 能力 | CLI（`swl`） | AI 聊天面板 |
|---|---|---|
| 创建/运行/管理 TaskState | **是**（唯一入口） | **否** |
| 触发 `run_task()` | **是** | **否** |
| 写入 Event Log / Artifact Store | **是** | **否** |
| 知识晋升（canonical promotion） | **是** | **否** |
| 探索性对话 / 脑暴 | 不擅长 | **是** |
| 查看任务状态（只读 dashboard） | 是 | 未来可选 |
| 审批知识晋升（只读 + 审批按钮） | 是 | 未来可选 |

### 4.4 与 Swallow 知识体系的集成路径

聊天面板中的对话产出如需进入 Swallow 体系，必须经过 **Ingestion Specialist**：

```
Open WebUI 对话 → 导出为对话记录
    → Ingestion Specialist（解析、提纯、结构化）
        → HandoffContractSchema → 知识库暂存区
            → Librarian Agent 审查后晋升
```

面板不应直接写入 Swallow 的任何持久化层。

### 4.5 部署拓扑

```
用户浏览器
    → Open WebUI（:3000，聊天面板）
    → new-api（:3001，渠道管理）→ LLM Providers

用户终端
    → swl CLI → Swallow Runtime → Provider Connector → LLM Providers
```

两条路径共享 new-api 作为 Provider Connector，但编排逻辑只存在于 CLI → Runtime 这条路径中。
