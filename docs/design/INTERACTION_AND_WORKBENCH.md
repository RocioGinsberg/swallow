# 交互与工作台层设计 (Interaction & Workbench Layer)

## 0. 阅读约定

本文档描述的是 **Swallow 当前主分支的交互与工作台基线**。

这里最重要的不是“给系统准备多少前端”，而是明确：

- 哪些 surface 是任务工作的主入口
- 哪些 surface 只负责探索性对话
- 哪些 surface 只负责只读监控与审阅
- 哪些东西是真值，哪些只是交互外壳

本文档应与当前架构文档中的以下原则一起理解：

- local-first
- SQLite-primary truth
- truth before retrieval
- taxonomy before brand
- explicit separation between controlled HTTP path and black-box agent path

---

## 1. 核心定位：从聊天窗到工作台

大多数 AI 产品仍以线性的聊天流作为默认交互范式。这对于轻量问答足够，但对真实项目工作并不理想，因为真实任务往往需要：

- 跨多轮、多阶段推进
- 审阅 artifacts 与 diff
- 检查 task state / event truth / route truth
- 在 review、retry、rerun、waiting_human 之间切换
- 在代码、文档、知识对象和执行结果之间来回穿梭

因此，Swallow 的交互层不应被理解为“聊天 UI”，而应被理解为：

> **围绕任务真值、知识真值与审阅/恢复流程组织起来的工作台层。**

聊天只是其中一个辅助 surface，而不是事实承载层。

---

## 2. 当前交互层的总原则

Swallow 当前更适合坚持以下四条原则：

1. **CLI 是主入口**：任务创建、运行、控制、恢复、知识治理的主路径仍应通过 `swl` 进入
2. **Control Center 是只读工作台**：用于监控、检查、对比和审阅，而不是直接改写真值
3. **聊天面板是探索入口**：适合脑暴、问答和外部会话来源，不承担编排职责
4. **真值在后端，不在聊天流里**：真正有价值的状态与结果必须沉淀为 task truth、event truth、knowledge truth 或 artifacts

---

## 3. 当前多入口矩阵 (Multi-Surface Matrix)

系统当前采用“统一后端状态，多元前端表达”的思路，但不同入口职责必须严格分离。

### 3.1 CLI 终端：主任务入口

CLI 仍然是当前最核心、最权威的操作入口。

它擅长的是：

- 创建任务
- 运行任务
- 检查 task state / route / topology / grounding
- 执行 retry / rerun / resume / control
- 触发知识摄入、knowledge review、promotion / rejection
- 查看 artifacts、consistency audit、canonical reuse 等结构化结果

因此，CLI 在当前更适合被理解为：

> **task workbench primary entrypoint**

而不是“开发者版聊天框”。

### 3.2 IDE / 笔记环境集成：方向性入口

编辑器与笔记环境集成仍然有价值，但当前更适合作为方向性增强，而不是系统主入口。

它的长期价值包括：

- 在用户当前心智焦点附近触发 task handoff
- 提供 inline diff / inline review surface
- 将文档、代码与任务状态更自然地连接起来

但当前基线下，不应把它写成已经成熟落地的主控制面。更稳的理解是：

- 它属于未来增强方向
- 它应复用既有 task truth / artifact / review 语义
- 它不应绕过 CLI 或 backend truth layer 直接形成独立状态系统

### 3.3 Web / 桌面 Control Center：只读监控与审阅中心

当前 Web Control Center 更接近：

- 任务监控面板
- artifact 审阅区
- 子任务树 / 执行时间线 / route 观测面板
- 只读 control surface

它不应被写成“第二个编排入口”，也不应被写成“聊天工作台”。

当前更准确的理解是：

> **operator-facing read-only control center**

它适合：

- 查看任务链图
- 查看 Subtask Tree
- 对比 artifact
- 检查 execution timeline / cost / latency / degraded signals
- 查看审阅上下文

不适合：

- 直接运行任务主循环
- 直接改写 task truth / knowledge truth
- 取代 CLI 成为 canonical promotion 主入口

### 3.4 聊天面板：探索性对话入口

系统中仍然需要自由探索、脑暴和快速问答的 surface，但它的地位必须被严格限定。

聊天面板更适合：

- 快速提问
- 自由探索
- 形成初步方案草稿
- 产生待摄入的外部会话材料

它不适合：

- 承担 task orchestration
- 成为 task truth 的直接写入口
- 跳过 ingest / review / promotion 直接进入长期知识层

因此，聊天面板应被视为：

> **exploration surface, not orchestration surface**

---

## 4. 当前各入口的职责边界

为了避免后续混淆，当前可用以下表格理解：

| 能力 | CLI (`swl`) | Control Center | 聊天面板 |
|---|---|---|---|
| 创建/运行/管理 TaskState | **是（主入口）** | 否 | 否 |
| 触发主任务循环 | **是** | 否 | 否 |
| 查看任务状态 / 子任务树 / 路由 | 是 | **是（只读强项）** | 否 |
| artifact 对比与审阅 | 是 | **是（强项）** | 否 |
| 知识摄入与 review 队列 | **是** | 未来可选只读 | 否 |
| canonical promotion / reject | **是** | 否 | 否 |
| 探索性对话 / 脑暴 | 一般 | 否 | **是** |
| 外部会话来源 | 一般 | 否 | **是** |
| 写入 task truth / event truth / knowledge truth | **是（受控）** | 否 | 否 |

这张表最重要的作用，是防止任何 surface 在没有明示设计的情况下滑向 hidden orchestrator 或 hidden writer。

---

## 5. 交互层与真值层的关系

当前最容易过时的一个旧误解是：

> “工作台就是读写 `.swl/tasks/*/state.json` 的前端。”

这已经不再准确。

当前基线下，更稳的说法是：

- **Task truth / event truth / knowledge truth**：以 SQLite 为主
- **Artifacts / mirrors / export views**：仍保留文件视图
- **交互层**：围绕这些真值与产物组织查看、控制、审阅与恢复

也就是说，交互层不是事实源头，而是：

> **truth-aware workbench**

它必须始终建立在 task truth / event truth / knowledge truth 之上，而不是把聊天记录或临时前端状态误当作真实状态。

---

## 6. 意图提纯与任务对象化

Swallow 当前不应鼓励用户仅用一句模糊指令驱动复杂任务。

更稳的交互原则是：

- 用户输入需要被提纯为 task object
- goal / context pointers / constraints 应尽可能显式化
- 交互层要帮助用户把模糊意图转换成可执行任务语义，而不是把模糊性原样下沉给 runtime

因此，交互层的职责之一是：

> **assist explicit task formation**

### Schema Alignment Note

当前 task handoff / intake vocabulary 应继续与统一 schema 对齐。

本节术语与统一 schema 的映射为：

- `Goal` -> `goal`
- `Context Ref` -> `context_pointers`
- `Constraints` -> `constraints`

而 `done`、`next_steps` 等字段也应继续被视为统一 schema 的组成部分，而不是某个 surface 自己的临时附属字段。

---

## 7. 中断、接管与恢复

Swallow 不追求无条件全自动，而是明确拥抱 human-in-the-loop。

因此，交互层必须把以下能力做成一等能力：

### 7.1 waiting_human 暴露

当系统遇到：

- 高风险操作
- review 不通过
- budget exhausted
- fallback 后仍不可信
- 语义歧义无法自动裁决

交互层必须显式暴露 `waiting_human`，而不是让系统继续假装推进。

### 7.2 平滑接管

用户应能够：

- 暂停任务
- 进入现场修正局部问题
- 添加 resume note / hint
- 让任务从修正后的状态继续推进

这意味着交互层不是只负责“启动”，还必须负责：

- interruption
- controlled takeover
- recovery entry

### 7.3 拒绝聊天记录崇拜

交互层上的聊天流、草稿与自由对话都是易失性的。

真正对业务有影响的结果，必须被显式提示为已经沉淀为：

- Artifact
- Event Log
- Task truth update
- Knowledge candidate / promoted object

这样用户才不会把“UI 上看到的一段对话”误以为系统已经真正记住并接纳。

---

## 8. Open WebUI / Chat Panel 的正确位置

如果你采用 Open WebUI 或其他聊天面板，它在当前体系中的正确位置仍然是：

- 探索性对话面板
- 外部会话来源
- 人类脑暴辅助 surface

而不是：

- Swallow 编排器
- TaskState 管理入口
- Knowledge truth 写入口

### 推荐集成路径

更合理的路径仍然是：

`Chat Panel conversation -> export / capture -> Ingestion Specialist -> staged knowledge / handoff object -> review / promotion`

也就是说，聊天面板中的内容若要进入系统，必须经过：

- 提取
- 过滤
- 结构化
- staged
- review / promotion

而不是直接写入知识真值层。

---

## 9. Control Center 的当前表述修订

当前 Control Center 的公开表述应从早期的“远期大而全控制面”收束为：

- 已存在只读 Web 基线
- 当前重点是 inspect / review / compare / timeline / subtree visibility
- 不承担写入职责
- 不承担主编排职责

因此，当前更准确的状态描述应是：

> `swl serve` 提供的是一个只读、operator-facing 的控制中心，而不是一个可直接替代 CLI 的全功能工作台。

它的价值在于：

- 让 operator 看清 runtime 正在发生什么
- 让 artifacts 更容易被审阅
- 让 route / latency / degraded / topology 更容易被观察

而不是在前端重新发明一套独立状态机。

---

## 10. 当前对实现者的约束性理解

如果继续扩展 Interaction & Workbench 层，当前应坚持：

1. 不要把聊天面板重新写成系统主入口
2. 不要把 Control Center 误写成带写权限的第二编排器
3. 不要把前端临时状态误当作 authoritative truth
4. 不要再使用“本地文件直读即唯一真值”的旧叙事
5. 不要让任何 surface 绕过 ingest / review / promotion 直接进入知识真值层
6. 不要让 UI 描述先于真实 runtime 边界膨胀

---

## 11. 一句话总结

Swallow 当前的 Interaction & Workbench 层，不应理解为：

> 一套围绕聊天窗口展开的多端壳层

而应理解为：

> 一个以 CLI 为主入口、以只读 Control Center 为监控审阅面、以聊天面板为探索性辅助入口的 truth-aware workbench layer；它围绕 task truth、event truth、knowledge truth 与 artifacts 组织真实项目工作的交互与恢复
