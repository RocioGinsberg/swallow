# Interaction & Workbench

> **Design Statement**
> Swallow 的交互层是一个 **truth-aware workbench**——以 CLI 为主入口、以 Control Center 为监控审阅面、以聊天面板为探索性辅助入口。它围绕 task truth、event truth、knowledge truth 与 artifacts 组织真实项目工作的交互与恢复,而不是围绕聊天流组织。

> 项目不变量见 → `INVARIANTS.md`(权威)。术语见 `ARCHITECTURE.md §5`。

---

## 1. 设计动机

线性聊天流对轻量问答足够,但真实项目工作需要:

- 跨多轮、多阶段推进
- 审阅 artifacts 与 diff
- 检查 task state / event truth / route truth
- 在 review / retry / rerun / waiting_human / suspended 之间切换
- 在代码、文档、知识对象和执行结果之间穿梭

因此交互层不是"聊天 UI",而是 **task workbench**。

---

## 2. 四条设计原则

| 原则 | 含义 |
|---|---|
| **CLI 是主入口** | 任务创建、运行、控制、恢复、知识治理的主路径通过 `swl` 进入 |
| **Control Center 是 UI 入口** | 提供与 CLI **能力对等**的 operator 入口:监控、审阅、命令触发、任务创建、文件上传等。所有写操作必须经过与 CLI 相同的 governance 函数(`apply_proposal` / `transition_state` / `ingest` 等),不直接写 truth |
| **聊天面板是探索入口** | 脑暴、问答、外部会话来源,不承担编排职责 |
| **真值在后端** | 有价值的状态与结果沉淀为 task / event / knowledge truth 与 artifacts,不在聊天流里 |

---

## 3. 多入口权限矩阵

| 能力 | CLI(`swl`) | Control Center | 聊天面板 |
|---|---|---|---|
| 创建 / 运行 / 管理 task | ✅ | ✅(经 governance API) | ❌ |
| 触发主任务循环 | ✅ | ✅(经 governance API) | ❌ |
| 查看 task state / subtask tree / route | ✅ | ✅ 强项 | ❌ |
| Artifact 对比与审阅 | ✅ | ✅ 强项 | ❌ |
| 知识摄入(文件上传) | ✅ | ✅(经 ingest API) | ❌ |
| Knowledge review / promote / reject | ✅ | ✅(经 apply_proposal) | ❌ |
| Proposal apply | ✅ | ✅(经 apply_proposal) | ❌ |
| 探索性对话 / 脑暴 | 一般 | ❌ | ✅ |
| 外部会话来源 | 一般 | ❌ | ✅(产出后必须经 ingest) |
| 直接执行 SQL / Repository 写方法 | ❌ | ❌ | ❌ |

这张矩阵的核心作用:**防止任何 surface 在没有明示设计的情况下滑向 hidden orchestrator 或 hidden writer**。

---

## 4. 各入口详述

### 4.1 CLI 终端 — 主任务入口

`swl` 是最核心、最权威的操作入口:

- 任务创建、运行、状态检查、控制
- resume / rerun / suspend(operator 主动) / cancel
- 知识摄入、review queue、promote / reject(均经 `apply_proposal`)
- proposal apply / reject
- artifacts、consistency audit、canonical reuse 等结构化结果查看

定位:**task workbench primary entrypoint**。

### 4.2 Web / 桌面 Control Center

`swl serve` 启动的 operator-facing UI 入口。提供**与 CLI 能力对等**的 operator 操作面。

#### 4.2.1 实现纪律

UI 后端是**对 governance 函数的薄 HTTP 包装**,不是独立的业务层。具体约束:

- UI 后端的每个写操作 API,内部必须调用与 CLI 完全相同的 governance 函数(`apply_proposal` / `transition_state` / `ingest` 等)
- UI 后端**不允许**直接调用 Repository 私有方法
- UI 后端**不允许**直接执行 SQL
- UI 后端**不允许**实现独立的状态机校验、留痕逻辑——这些都在 governance 函数内
- UI 后端可以实现的:身份/会话管理(未来 multi-actor)、请求参数校验、UI 友好的错误信息转换、批量操作的事务包装

类比:UI 后端之于 governance,等同于 GitHub Web UI 后端之于 git——前者是后者的 HTTP 适配层,不是另一套实现。

`test_ui_backend_only_calls_governance_functions` 守卫验证 UI 后端代码路径中没有直接的 Repository 私有方法调用或裸 SQL。

#### 4.2.2 监控与审阅(只读)

- 任务链图 / subtask tree 查看
- Artifact 对比与审阅
- Execution timeline / cost / latency / degraded signals 观测
- 审阅上下文查看
- routing_hint / verdict / event 流可视化

#### 4.2.3 操作面(经 governance API)

| UI 操作语义 | 触发的 governance 函数 | 等价 CLI |
|---|---|---|
| 创建 task | `task_create(...)` | `swl task create` |
| 运行 task | `task_run(task_id)` | `swl task run` |
| 上传文件并摄入 | `ingest(file_path, format=...)` | `swl ingest <path>` |
| Promote staged candidate | `apply_proposal(target=canonical_knowledge)` | `swl knowledge promote` |
| Reject staged candidate | `mark_review_state(rejected)` | `swl knowledge reject` |
| Apply proposal | `apply_proposal(target=route/policy)` | `swl proposal apply` |
| Resume waiting_human / suspended task | `transition_state(running)` | `swl task resume` |
| Suspend running task | `transition_state(suspended)` | `swl task suspend` |
| Cancel non-terminal task | `transition_state(cancelled)` | `swl task cancel` |

**关键边界**:UI 操作走与 CLI 完全相同的代码路径,所有 governance / 校验 / 留痕保持一致。Operator 选择哪个入口纯粹是 UX 偏好,不影响系统行为。

#### 4.2.4 文件上传的特殊处理

文件上传需要把浏览器端文件落到本地受控目录:

- 上传目标:`<workspace_root>/.swl/uploads/<upload_id>/`(临时目录)
- ingest 完成后,根据 ingest 结果决定:进入 staged → 移动到 `<workspace_root>/.swl/staged_sources/<staged_id>/`;失败 → 保留在 uploads 等待 operator 检查
- 上传本身**不**写 truth,只是在文件系统落地;真正的入库由 ingest 函数完成
- 上传文件的清理纪律:成功 ingest 后 30 天自动清理 uploads 临时目录,staged_sources 跟随 staged 对象的生命周期

定位:**operator-facing UI with full governance-equivalent capabilities, narrow direct-write surface**。

---

## 5. 交互层与真值层的关系

交互层不是事实源头,而是 **truth-aware workbench**:

- 结构化真值(task / event / knowledge / route / policy)→ SQLite
- Artifacts / fragments / export views → 文件系统
- 交互层 → 围绕这些真值与产物组织查看、控制、审阅与恢复

聊天记录和前端临时状态**不等于**真实系统状态。

---

## 6. 意图提纯与任务对象化

交互层的职责之一是帮助用户把模糊意图转换成可执行任务语义,而不是把模糊性原样下沉给 runtime。

task intake vocabulary 与统一 schema 的映射(见 DATA_MODEL §3.1):

| 文档术语 | Schema 字段 |
|---|---|
| Goal | `goal` |
| Context Ref | `context_pointers` |
| Constraints | `constraints` |
| Done | `done` |
| Next Steps | `next_steps` |
| Route Override(可选,特权字段) | `route_override_hint`(见 INVARIANTS §7.1) |

---

## 7. 中断、接管与恢复

Swallow 明确拥抱 human-in-the-loop,交互层必须把以下能力做成一等能力:

### 7.1 waiting_human 与 suspended 的暴露

两个状态触发方与语义不同(见 STATE_AND_TRUTH §3.2):

| 状态 | 触发方 | UI 暴露方式 |
|---|---|---|
| `waiting_human` | 系统(review fail / uncertain / budget exhausted) | 醒目通知 + 显示触发原因 |
| `suspended` | Operator 主动 | 安静标记 + 显示挂起时间 |

两者都通过 "Resume" 按钮恢复,但 UI 上必须区分,避免 operator 把"系统说我没法继续"误当成"我自己刚才停的"。

### 7.2 平滑接管

用户可以:

- 暂停任务 → suspend 状态
- 进入现场修正(直接编辑 workspace 文件 / 添加 resume note)
- 让任务从修正后状态继续推进 → resume

### 7.3 结果沉淀确认

聊天流、草稿与自由对话都是易失性的。真正有影响的结果必须被显式提示为已沉淀为:

- artifact(进入 `.swl/artifacts/<task_id>/`)
- event log entry(进入 `event_log` / `event_telemetry`)
- task truth update(进入 `task_records`)
- knowledge candidate(进入 `know_staged`,等待 review)

---

## 8. 与其他文档的接口

| 对接文档 | 接口关系 |
|---|---|
| `INVARIANTS.md` | 写入路径(`apply_proposal`)的权威 |
| `ORCHESTRATION.md` | 交互层形成 task object、展示状态、提供 control surface;编排层负责真正推进 |
| `STATE_AND_TRUTH.md` | 交互层读取 task truth / event truth 做展示;状态迁移通过命令触发 |
| `KNOWLEDGE.md` | CLI 提供 knowledge ingest / review / promote 入口;Control Center 触发同一命令 |
| `SELF_EVOLUTION.md` | CLI / Control Center 都是 proposal review 的入口,均经 `apply_proposal` |
| `HARNESS.md` | Harness 触发任务运行,交互层提供入口 |

---

## 附录 A:Anti-Patterns

| 反模式 | 说明 |
|---|---|
| **聊天 = 主入口** | 把聊天面板重新写成系统主入口 |
| **Control Center 直接写库** | Control Center 绕过 governance 命令直接 SQL 写 truth |
| **前端 = 真值** | 前端临时状态被误当作 authoritative truth |
| **Surface 直通知识层** | 任何 surface 绕过 ingest / review / `apply_proposal` 直接进入知识真值 |
| **UI 先于 runtime 膨胀** | UI 描述先于真实 runtime 边界膨胀 |
| **waiting_human 与 suspended 混用** | 在 UI 上不区分两者,导致 operator 误判任务状态来源 |
| **命令触发面变成隐式 orchestrator** | Control Center 的按钮触发链路绕过 Orchestrator,自己发起 task 推进 |
