# State & Truth Layer

> **Design Statement**
> 状态与真值层是 Swallow 全系统的持久化底座。它定义五个真值域的**语义边界、状态迁移规则、安全兜底语义**——让任务推进、恢复、审计与安全停止建立在外部可验证的结构化事实之上,而不是依赖模型对话记忆。

> 物理 schema 见 → `DATA_MODEL.md`(权威)。本文档不重复表结构定义,只描述每个真值面的**语义**与**演化规则**。

> 项目不变量见 → `INVARIANTS.md`(权威)。

---

## 1. 设计动机

传统 AI Agent 依赖对话历史维持上下文。当任务复杂度上升时,这种模式会暴露三个问题:

1. **淹没**——对话线性增长,关键事实被冗余信息掩盖。
2. **混杂**——意图、过程、结果混在同一条文本流中,无法独立恢复或审计。
3. **漂移**——模型上下文偏移后,会基于错误记忆继续推进。

Swallow 的选择是:**把事实托管到外部可验证存储中**,让模型退回到"读取事实 → 做判断 → 产出动作"的角色,而不是"靠记忆推进流程"。

---

## 2. 五个真值域

| 真值域 | 物理位置 | 核心语义 |
|---|---|---|
| **Task Truth** | `task_*` 表 | 任务推进位置、阶段、review/retry/resume/waiting_human 语义 |
| **Event Truth** | `event_*` 表(append-only) | 过程事件、executor 遥测、降级痕迹、审计线索 |
| **Knowledge Truth** | `know_*` 表 | 知识对象的治理状态(详见 KNOWLEDGE.md) |
| **Route / Policy Truth** | `route_*` / `policy_*` 表 | 路由元数据、策略阈值、能力边界 |
| **Workspace Truth** | 文件系统 + git | 代码与文本内容(外部约束,不在 SQLite) |

物理 schema、命名空间隔离规则、Repository 接口见 → `DATA_MODEL.md`。

> **关键区分**:**结构化真值**(task / event / knowledge / route / policy)以 SQLite 为权威;**面向人类查看的产物**(reports / diffs / summaries)以 artifact 文件为权威。两者互补,不互替。

---

## 3. Task Truth 的语义边界

Task Truth 是一个持久化的**任务现场对象**,受显式状态迁移规则约束。

### 3.1 它回答的问题

- 任务推进到了哪里?
- 系统应如何恢复?
- 是否已进入 `waiting_human`?
- budget 是否已耗尽?
- 当前 review / retry / rerun 语义是什么?

### 3.2 状态机

```
   pending ──────► running ──────► completed
                    │  │  │
                    │  │  └─────► waiting_human ─────► running
                    │  │              │
                    │  │              └─────► cancelled
                    │  │
                    │  └─────► suspended ─────► running
                    │              │
                    │              └─────► cancelled
                    │
                    └─────► failed ─────► running(rerun)
                              │
                              └─────► cancelled
```

| 状态 | 语义 | 触发方 | 允许的迁移 |
|---|---|---|---|
| `pending` | 已创建,未开始 | — | → `running` / `cancelled` |
| `running` | 执行中 | — | → `completed` / `waiting_human` / `suspended` / `failed` |
| `waiting_human` | **系统主动**停止,等待 operator 裁决 | Orchestrator(review fail / uncertain / budget exhausted) | → `running` / `cancelled` |
| `suspended` | **Operator 主动**挂起,任务未失败也未完成 | Operator | → `running` / `cancelled` |
| `completed` | 终态 | — | → 仅允许 archive |
| `failed` | 终态(可 rerun) | — | → `running`(rerun)/ `cancelled` |
| `cancelled` | 终态 | — | 不可迁移 |

`waiting_human` 与 `suspended` 是两个分离的状态,**触发方不同、语义不同**:

- `waiting_human` 是系统说"我没法继续了,你来决定"
- `suspended` 是 operator 说"我让它先停一下"

两者都通过 `running` 恢复,但 event_log 中保留独立的 `kind`(`entered_waiting_human` / `suspended_by_operator`),方便审计与 Meta-Optimizer 区分系统主动停顿与人为干预的频率。


### 3.3 状态迁移的执行边界

**所有状态迁移只能通过 Orchestrator 执行**(INVARIANTS §0 第 1 条)。Repository 层暴露 `transition_state(task_id, from_state, to_state, reason)` 方法,内部:

- 校验迁移是否在状态机定义内
- 校验调用方是否为 Orchestrator(通过传入的 caller token)
- 写入 `event_log` 留痕(actor 字段记录 operator 或 system)
- 更新 `task_records.state` 与 `updated_at`

`test_state_transitions_only_via_orchestrator` 守卫测试验证除 Operator-via-CLI 路径外,所有迁移都来自 Orchestrator 调用栈。

### 3.4 Resume、Rerun、Retry 的区别

| 操作 | 适用状态 | 含义 | task_id | attempt |
|---|---|---|---|---|
| **Resume** | `waiting_human` / `suspended` → `running` | 任务暂停后继续推进,保留所有 done 工作和 context | 不变 | 不变 |
| **Rerun** | `failed` / `completed` → `running` | 重新执行任务,产生新的 event_log 序列 | 不变 | +1 |
| **Retry**(Review Gate 触发) | `running` 内部循环 | 不改变 state,在执行步骤内部循环,直到 retry_limit | 不变 | 不变 |

**新 task_id 只在新任务创建时产生**。Resume / Rerun 不开新 task,通过 `(task_id, attempt)` 二元组定位某次具体执行。

### 3.5 归档(Archive)

`archived_at` 字段(见 DATA_MODEL §3.1)实现软删除:

- 归档不改变任务的 truth 内容,只影响默认查询过滤
- 归档不是状态迁移,与 `state` 字段正交
- 归档可对 `completed` / `failed` / `cancelled` 任意终态执行
- `pending` / `running` / `waiting_human` **不允许归档**——必须先进入终态

---

## 4. Event Truth 的语义边界

Event Log 以 append-oriented 方式记录系统中发生过的事件,**永不修改、永不删除**(数据库层 trigger 强制,见 DATA_MODEL §4.2)。

### 4.1 四类消费者

| 消费者 | 消费方式 |
|---|---|
| 审计 | 完整还原任务推进过程 |
| 遥测 | executor latency / token cost / degraded / error_code |
| 诊断 | retry / review / fallback 过程追踪 |
| Meta-Optimizer | 行为模式识别与优化提案输入(只读消费) |

### 4.2 写入纪律

- 任何执行实体都可以 append event,**但不能 update / delete**
- 每条 event 必须带 `actor` 字段(默认 `"local"`,见 INVARIANTS §7)
- event 的 `payload` 是 JSON,**不允许嵌入跨命名空间的引用对象 snapshot**——只用 ID 引用(见 DATA_MODEL §5)

### 4.3 event_log 与 event_telemetry 的分工

| 表 | 内容 | 消费者 |
|---|---|---|
| `event_log` | 语义事件(任务创建、状态迁移、review 结果、handoff 创建等) | 审计、诊断、UI 展示 |
| `event_telemetry` | 性能数据(latency、token、cost、degraded、error_code) | Meta-Optimizer、Provider Router 优化 |

读取 pattern 不同,分表减少索引开销。

---

## 5. Route / Policy Truth 的语义边界

### 5.1 写入路径唯一

`route_registry` 与 `policy_records` 的 metadata 字段写入**只有 `apply_proposal` 一个代码入口**(INVARIANTS §0 第 4 条)。

- Provider Router 可以 append `route_health` 记录(系统观测)
- Provider Router **不允许**改 `route_registry.quality_weight` / `unsupported_task_types` 等 metadata 字段
- Meta-Optimizer 产出 proposal artifact,等待 Operator 审阅

### 5.2 与 Task Truth 的解耦

Route / Policy Truth **默认不绑定**到具体任务——它们是系统级配置。Task 在执行时引用当前生效的 route / policy,但不持久化引用关系(只在 `event_telemetry.physical_route` 记录"实际使用了哪条 route")。

理由:route / policy 演化频率与 task 不同,绑定会让历史 task 在 route 变更后变得不可读。

**例外:任务级 route override**。Operator 可通过 `task_records.route_override_hint` 字段为单个任务指定 route。这是显式特权字段,使用边界见 INVARIANTS §7.1。该字段不影响 route / policy 的全局配置,只影响该任务的路由解析。

---

## 6. Workspace / Git Truth

文件系统和 Git 仍然是内容层的权威约束。SQLite 管理的是**任务与知识的治理状态**,workspace / git 管理的是**内容本身**。

### 6.1 路径的真值约束

- `workspace_root` 字段存**相对 git 仓库根的路径**(INVARIANTS §7)
- 绝对路径解析只在 `swallow.workspace.resolve_path()` 一处完成
- Truth 写入字段**不允许**包含绝对路径(由 `test_no_absolute_path_in_truth_writes` 守卫)

理由:同事 clone 仓库后,任务能自然 resume;跨设备同步时不依赖路径一致性。

### 6.2 Git ref 作为 ContextPointer

`ContextPointer` 支持 `kind = "git_ref"`(见 DATA_MODEL §5)。这允许 handoff / artifact 引用具体 commit 与文件位置,跨设备 / 跨用户都可解析。

---

## 7. "单一事实源"的正确含义

Swallow 的 Single Source of Truth 不是"只有一个物理存储",而是:

> **每个真值域有明确的权威存储,由 Orchestrator / runtime 统一解释。**

具体映射:

| 真值域 | 权威存储 |
|---|---|
| 任务推进与知识治理状态 | SQLite |
| 代码与工作区内容 | Workspace / Git |
| 面向查看的文件产物 | Artifact files |
| 角色绑定 | EXECUTOR_REGISTRY.md(文档作为配置源) |

---

## 8. 安全兜底语义

当出现以下情况时,真值层承担最终安全兜底:

| 触发条件 | 真值层响应 |
|---|---|
| 模型输出不可靠 | 拦截非法状态突变(状态机校验失败 → 拒绝写入) |
| Route degraded | 记录 degraded 事件,标记信任度降低,由 Review Gate 决定下一步 |
| Review 不通过 | Review Gate 阻止推进,进入 feedback-driven retry |
| Fallback 触发 | 记录 fallback 路径,保留原始 route 信息 |
| 参数不符 schema | Repository 层拒绝写入 |
| 自动推进不再可信 | 停止推进,转入 `waiting_human` |
| 数据库 schema 落后 | 启动时检测,进入 `waiting_human` 提示运行 migrate(见 DATA_MODEL §8) |

**核心原则**:**宁可显式停止并移交人类,也不让模型在事实不完整时继续假装推进**。

---

## 9. 与方言 / 执行后端的解耦

真值层与底层模型品牌和协议**保持解耦**:

- 状态层不硬编码任何厂商的 prompt 协议
- route、dialect、executor family 作为显式元数据存在于 Route Truth 中
- 具体方言适配下沉到 Provider Router(见 PROVIDER_ROUTER.md)

状态层记录的是**任务意图、执行边界与策略约束**,而不是某一家厂商的原生协议格式。

---

## 10. Single-user 假设的处理

当前 phase 是 single-user(INVARIANTS §7),但 truth 层不允许写出阻塞未来扩展的代码。具体约束:

- 所有 truth 表预留 `actor` / `created_by` 字段,默认 `"local"`
- 所有主键使用 ULID,不含本机标识
- 所有路径以相对 git root 形式存储
- `"local"` 字面量集中在 `swallow.identity.local_actor()` 一处

切换到 multi-actor 时,只需替换 `local_actor()` 实现 + 实现 authn / authz / 并发冲突解决,不需要在代码各处搜索修改。

---

## 11. 与其他文档的接口

| 对接文档 | 接口关系 |
|---|---|
| `INVARIANTS.md` | 权限矩阵、推进权限边界、actor 埋点的权威 |
| `DATA_MODEL.md` | 物理 schema、Repository 接口、命名空间隔离的实现细节 |
| `ORCHESTRATION.md` | Orchestrator 是 task state 迁移的唯一执行方;Review Gate 写状态 |
| `KNOWLEDGE.md` | Knowledge Truth 的语义边界(详见该文档) |
| `PROVIDER_ROUTER.md` | Route Truth 的 health 写入路径,metadata 写入仅经 apply_proposal |
| `INTERACTION.md` | 各 surface 读取真值做展示,但不直接改写真值 |

---

## 附录 A:Anti-Patterns

| 反模式 | 说明 |
|---|---|
| **Prompt Memory 依赖** | 把对话历史当作状态层的替代品,导致恢复和审计不可行 |
| **Artifact File = 唯一真值** | 忽略 SQLite 中的结构化治理状态,只看文件产物 |
| **忽略执行边界真值** | 不持久化 route / policy,导致降级和 fallback 不可追溯 |
| **方言渗透** | 把特定厂商的 prompt 协议结构硬编码进状态层 schema |
| **退回纯 JSON 文件** | 放弃 SQLite-primary 基线,回到散落的 JSON 文件式状态管理 |
| **Executor 写 task state** | 任何执行实体直接 update task_records.state(必须经 Orchestrator) |
| **状态机外迁移** | 绕过状态机定义,直接写入非法状态值 |
| **路径绝对化渗透** | 在多个模块各自实现路径解析,不集中到 `resolve_path()` |
