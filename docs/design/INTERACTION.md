# 交互与工作台层 (Interaction & Workbench)

> **Design Statement**
> Swallow 的交互层是一个 truth-aware workbench——以 CLI 为主入口、以只读 Control Center 为监控审阅面、以聊天面板为探索性辅助入口。它围绕 task truth、event truth、knowledge truth 与 artifacts 组织真实项目工作的交互与恢复，而不是围绕聊天流组织。

> 全局原则见 → `ARCHITECTURE.md §1`。术语定义见 → `ARCHITECTURE.md §6`。

---

## 1. 设计动机

线性聊天流对轻量问答足够，但真实项目工作需要：

- 跨多轮、多阶段推进
- 审阅 artifacts 与 diff
- 检查 task state / event truth / route truth
- 在 review / retry / rerun / waiting_human 之间切换
- 在代码、文档、知识对象和执行结果之间穿梭

因此交互层不是"聊天 UI"，而是 **task workbench**。

---

## 2. 四条设计原则

| 原则 | 含义 |
|---|---|
| **CLI 是主入口** | 任务创建、运行、控制、恢复、知识治理的主路径通过 `swl` 进入 |
| **Control Center 是只读工作台** | 监控、检查、对比、审阅，不直接改写真值 |
| **聊天面板是探索入口** | 脑暴、问答、外部会话来源，不承担编排职责 |
| **真值在后端** | 有价值的状态与结果沉淀为 task truth / event truth / knowledge truth / artifacts，不在聊天流里 |

---

## 3. 多入口权限矩阵

| 能力 | CLI (`swl`) | Control Center | 聊天面板 |
|---|---|---|---|
| 创建 / 运行 / 管理 TaskState | ✅ 主入口 | ❌ | ❌ |
| 触发主任务循环 | ✅ | ❌ | ❌ |
| 查看 task state / subtask tree / route | ✅ | ✅ 只读强项 | ❌ |
| Artifact 对比与审阅 | ✅ | ✅ 强项 | ❌ |
| 知识摄入与 review 队列 | ✅ | 未来可选只读 | ❌ |
| Canonical promotion / reject | ✅ | ❌ | ❌ |
| 探索性对话 / 脑暴 | 一般 | ❌ | ✅ |
| 外部会话来源 | 一般 | ❌ | ✅ |
| 写入 task / event / knowledge truth | ✅ 受控 | ❌ | ❌ |

这张矩阵的核心作用：**防止任何 surface 在没有明示设计的情况下滑向 hidden orchestrator 或 hidden writer。**

---

## 4. 各入口详述

### 4.1 CLI 终端 — 主任务入口

`swl` 是最核心、最权威的操作入口：

- 任务创建、运行、状态检查、控制
- retry / rerun / resume / checkpoint
- 知识摄入、review queue、promote / reject
- artifacts、consistency audit、canonical reuse 等结构化结果查看

定位：**task workbench primary entrypoint**。

### 4.2 Web / 桌面 Control Center — 只读监控与审阅

`swl serve` 提供的只读 operator-facing 控制中心：

- 任务链图 / subtask tree 查看
- Artifact 对比与审阅
- Execution timeline / cost / latency / degraded signals 观测
- 审阅上下文查看

定位：**operator-facing read-only control center**。不运行任务主循环，不改写 truth。

### 4.3 聊天面板 — 探索性对话

适合快速提问、自由探索、形成初步方案草稿、产生待摄入的外部会话材料。

如果聊天面板内容要进入系统，必须经过完整路径：

```
Chat Panel → export / capture → Ingestion Specialist → staged knowledge → review / promotion
```

定位：**exploration surface, not orchestration surface**。

### 4.4 IDE / 笔记环境集成 — 方向性增强

长期价值包括 inline diff / inline review surface、在用户心智焦点附近触发 task handoff。属于未来增强方向，应复用既有 task truth / artifact / review 语义，不绕过 CLI 或 backend truth layer。

---

## 5. 交互层与真值层的关系

交互层不是事实源头，而是 **truth-aware workbench**：

- 结构化真值（task / event / knowledge）→ SQLite
- Artifacts / mirrors / export views → 文件系统
- 交互层 → 围绕这些真值与产物组织查看、控制、审阅与恢复

聊天记录和前端临时状态不等于真实系统状态。

---

## 6. 意图提纯与任务对象化

交互层的职责之一是帮助用户把模糊意图转换成可执行任务语义，而不是把模糊性原样下沉给 runtime。

task intake vocabulary 与统一 schema 的映射：

| 文档术语 | Schema 字段 |
|---|---|
| Goal | `goal` |
| Context Ref | `context_pointers` |
| Constraints | `constraints` |
| Done | `done` |
| Next Steps | `next_steps` |

---

## 7. 中断、接管与恢复

Swallow 明确拥抱 human-in-the-loop，交互层必须把以下能力做成一等能力：

### 7.1 waiting_human 暴露

高风险操作、review 不通过、budget exhausted、fallback 后仍不可信、语义歧义无法自动裁决——这些情况交互层必须显式暴露 `waiting_human`，不让系统继续假装推进。

### 7.2 平滑接管

用户可以：暂停任务 → 进入现场修正 → 添加 resume note / hint → 让任务从修正后状态继续推进。

### 7.3 结果沉淀确认

聊天流、草稿与自由对话都是易失性的。真正有影响的结果必须被显式提示为已沉淀为 artifact / event log / task truth update / knowledge candidate。

---

## 8. 与其他层的接口

| 对接层 | 接口关系 |
|---|---|
| **Orchestrator** | 交互层形成 task object、展示状态、提供 control surface；编排层负责真正推进任务 |
| **State & Truth** | 交互层读取 task truth / event truth 做展示，写入通过 CLI 受控完成 |
| **Knowledge** | CLI 提供 knowledge review / promote / reject 入口 |
| **Harness** | 交互层触发任务运行，Harness 提供受控执行环境 |

---

## 附录 A：Anti-Patterns

| 反模式 | 说明 |
|---|---|
| **聊天 = 主入口** | 把聊天面板重新写成系统主入口 |
| **Control Center 写权限** | Control Center 变成带写权限的第二编排器 |
| **前端 = 真值** | 前端临时状态被误当作 authoritative truth |
| **Surface 直通知识层** | 任何 surface 绕过 ingest / review / promotion 直接进入知识真值 |
| **UI 先于 runtime 膨胀** | UI 描述先于真实 runtime 边界膨胀 |
