# Swallow Invariants

> **本文档是 Swallow 的项目宪法。**
> 所有设计文档、所有实现 PR,在与本文档冲突时一律以本文档为准。
> 本文档**只增不改**——任何修改必须经过 phase-level review,并在 CHANGELOG 中显式记录。
> 长度上限 200 行;一旦超过,说明放进了不该放的东西。

---

## 0. 四句不可违反的规则

> 1. **Control 只在 Orchestrator 和 Operator 手里。** 任何执行实体不得静默推进 task state。
> 2. **Execution 永远不直接写 Truth。** 执行实体只能通过受控 repository 接口写入,不允许裸 SQL。
> 3. **LLM 调用只有三条路径。** Controlled HTTP、Agent Black-box、Specialist Internal,Provider Router 治理穿透其中两条。
> 4. **Proposal 与 Mutation 的边界由唯一的 `apply_proposal` 入口在代码里强制。** Canonical knowledge / route metadata / policy 三类对象的写入只有这一个函数入口。

任何后续设计或实现违背其中一条都属于架构漂移。

---

## 1. 全局原则

| 编号 | 原则 | 含义 |
|---|---|---|
| P1 | **Local-first** | Truth 在本地。跨设备同步、远程访问通过外部工具(git / Syncthing / Tailscale),不引入云端 truth 镜像。 |
| P2 | **SQLite-primary truth** | 任务状态与知识治理状态以 SQLite 为权威存储。文件镜像与索引视图是辅助产物。 |
| P3 | **Truth before retrieval** | 先定义知识真值对象,再提供检索与召回。向量索引是召回手段,不是知识真值本身。 |
| P4 | **Taxonomy before brand** | 先定义系统角色,再绑定具体执行器或模型品牌。品牌只在 EXECUTOR_REGISTRY.md 中出现。 |
| P5 | **Explicit state over implicit memory** | 任务推进依赖外部可验证状态,不依赖模型对话记忆或上下文缓存。 |
| P6 | **Controlled vs black-box path** | 受控 HTTP 调用路径与黑盒 agent 调用路径必须显式区分,不混用治理手段。 |
| P7 | **Proposal over mutation** | 系统自我改进以提案为主,不自动突变运行时策略或长期知识。 |
| P8 | **Canonical-write-forbidden by default** | 大多数实体默认禁止直接写入长期知识真值。 |

---

## 2. 三个约束面

```
┌─────────────────────────────────────────────────────┐
│  CONTROL PLANE     谁有权决定下一步                       │
│    Orchestrator (唯一)                               │
│    Operator (人,通过 CLI 受控写入)                       │
├─────────────────────────────────────────────────────┤
│  EXECUTION PLANE   谁动手做事 / 在什么环境里做             │
│    General Executor / Specialist / Validator         │
├─────────────────────────────────────────────────────┤
│  TRUTH PLANE       事实存在哪里、谁能改                   │
│    SQLite (task / event / knowledge / route / policy)│
│    Filesystem (artifacts / workspace / git)         │
└─────────────────────────────────────────────────────┘
```

**铁律**:任何实体最多在 Execution Plane 上活动;Control Plane 只有 Orchestrator 和 Operator;Truth Plane 只能通过受控接口写入。

---

## 3. 实体描述格式(五元组)

每个执行实体使用统一的五元组描述,不允许复合或"或"型角色:

```
Entity = (
    role,              # {general_executor, specialist, validator}
    advancement_right, # {none, propose_only, advance_via_orchestrator}
    truth_writes,      # 显式枚举的 Truth 面白名单
    llm_call_path,     # {none, controlled_http, agent_internal, specialist_internal}
    runtime_site,      # {local_process, hybrid, remote_worker}
)
```

`runtime_site` 判定规则:**LLM 调用走 controlled_http 才算 hybrid;走 agent_internal 一律算 local_process**(对 Swallow 而言它就是个本地黑盒进程)。

具体实体绑定见 → `EXECUTOR_REGISTRY.md`。

---

## 4. 三条 LLM 调用路径

| 路径 | 谁组装 prompt | 是否经过 Provider Router | 适用 |
|---|---|---|---|
| **A. Controlled HTTP** | Orchestrator | ✅ | brainstorm / review / synthesis / classification / 抽取 |
| **B. Agent Black-box** | Agent 自己 | ❌(agent 内部决定模型) | 代码库阅读 / 实施 / 需要 tool-loop 的任务 |
| **C. Specialist Internal** | Specialist 内部 pipeline | ✅(穿透到底层 Path A) | Librarian / Ingestion / Literature / Meta-Optimizer |

**Path C = N × Path A**,Specialist 内部 LLM 调用必须穿透到 Provider Router,不允许绕路直连 provider。

---

## 5. Truth 写权限矩阵(权威拷贝)

```
                     │ task │ event │ stagedK │ canonK │ route │ policy │ artifact │ proposal │
─────────────────────┼──────┼───────┼─────────┼────────┼───────┼────────┼──────────┤──────────┤
Orchestrator         │  W   │   W   │    -    │   -    │   W   │   W    │    -     │    -     │
General Executor     │  -   │   W*  │    -    │   -    │   -   │   -    │    W     │    -     │
Specialist           │  -   │   W*  │    W    │   -    │   -   │   -    │    W     │    -     │
Validator            │  -   │   W*  │    -    │   -    │   -   │   -    │    -     │    -     │
Provider Router      │  -   │   W*  │    -    │   -    │   W*  │   -    │    -     │    -     │
Meta-Optimizer       │  -   │   W*  │    -    │   -    │   -   │   -    │    -     │    W     │
Operator (via CLI)   │  W   │   W   │    W    │   W    │   W   │   W    │    W     │    -     │
```

`W*` = 仅 append,不允许 update / delete。
`artifact` 列指任务执行产出的 artifact 文件(`.swl/artifacts/<task_id>/`)。
`proposal` 列指 Meta-Optimizer / Librarian 等产出的提案 artifact 文件(`.swl/artifacts/proposals/`),与任务执行产出物理与语义都分离。

任何执行器**不得直接写 task truth**;状态推进只走 Orchestrator。
canonical knowledge / route metadata / policy 的写入**只有 `apply_proposal` 一个代码入口**,Specialist 与 Meta-Optimizer 的代码路径里不存在该函数调用。
Operator 的 `proposal` 列为 `-`,因为 Operator 不是产出提案的角色,而是**审阅与应用**提案的角色——应用通过 `apply_proposal` 函数,作用于 canonK / route / policy 列。

---

## 6. 接入边界规则

具备以下任一特征的外部系统,**不得作为 Swallow Executor 接入**:

1. 自身是 orchestration platform(有自己的 task lifecycle / scheduler / fan-out)
2. 维护与 Swallow Truth Plane 平行的事实存储(云端 task store / session DB)
3. 默认运行模式假设 multi-tenant 或 team-shared 语义

这类系统可以作为**用户工作环境的一部分**(例如终端应用),但不进入 EXECUTOR_REGISTRY。

---

## 7. Single-user 是当前实现选择,不是架构假设

所有 truth 对象的 schema 必须能扩展为 multi-actor:

- 所有 ID 使用 ULID 或 UUID,不允许包含 hostname / username / 设备路径等本机标识
- `event_log` 等过程表预留 `actor` 字段,默认值 `"local"`
- Handoff object 不引用本机绝对路径,只用 ID / git ref / 相对路径
- `workspace_root` 存相对 git 仓库的路径,运行时解析为绝对路径

当前 phase **不实现** authn / authz / 并发写冲突解决——这些是远期 phase。

为防止实现阶段无意识写出 single-user 假设的代码,以下工程约束必须遵守:

- **身份硬编码集中化**:`"local"` 这个 actor 字符串只允许出现在 `swallow.identity.local_actor()` 一个函数内。其他模块要拿当前 actor,必须调用该函数。grep `"local"` 字面量在代码库的命中数应保持为 1(测试代码除外)。
- **路径绝对化集中化**:从相对路径解析到绝对路径只允许在 `swallow.workspace.resolve_path()` 一个函数内完成。Truth 写入函数禁止接收 `Path.absolute()` 之后的路径作为持久化字段。
- **当前用户假设禁止扩散**:任何函数签名不允许出现 `assume_single_user: bool` 之类的开关。要么整个系统是 single-user(此时 `local_actor()` 永远返回 `"local"`),要么不是——不允许在调用点二选一。
- **守卫测试**:`test_no_hardcoded_local_actor_outside_identity_module` 与 `test_no_absolute_path_in_truth_writes` 是 §9 守卫测试集的一部分。

这三条约束的目标:未来切换到 multi-actor 时,只需替换 `local_actor()` 的实现,不需要在代码库各处搜索修改。

### 7.1 任务级 route override 的边界

Task semantics 允许携带 `route_override_hint` 字段,用于调试或强制走特定 route 的场景。该字段是**特权字段**,使用时必须遵守:

- 仅 Operator 通过 CLI 显式设置,Strategy Router / Planner / executor **均不得**自行写入此字段
- 设置时必须在 `event_log` 中以 `kind = "route_override_set"` 留痕,记录 reason
- Strategy Router 看到此字段时,跳过常规路由策略判断,直接传给 Provider Router
- Provider Router 仍然执行 capability boundary guard(`unsupported_task_types`)——override 不能突破能力边界,只能在能力允许范围内强制选择

`test_route_override_only_set_by_operator` 守卫测试验证 override 字段的写入路径仅来自 CLI 入口。

---

## 8. 当前 phase 非目标

以下方向架构上保留扩展空间,实现上不投入:

- 多用户并发写、authn / authz、团队权限模型
- 分布式 worker 集群、跨机器 transport
- 云端 truth 镜像、跨设备实时同步(用户层面通过 git / 同步盘解决)
- 无边界 UI 扩张

以下方向是**永久非目标**(与本宪法核心原则矛盾):

- 隐式全局记忆、自动 knowledge promotion(违反 P7 / P8)
- 把 truth 上云作为 source of truth(违反 P1 / P2)
- 让外部 orchestration platform 接管推进语义(违反 §0 第 1 条)

---

## 9. 不变量守卫测试

每个 phase 必须保留下面这些守卫测试,任何 PR 不允许删除或弱化:

| 守卫 | 验证 | 引入位置 |
|---|---|---|
| `test_no_executor_can_write_task_table_directly` | §5 矩阵 | INVARIANTS §5 |
| `test_state_transitions_only_via_orchestrator` | §0 第 1 条 | INVARIANTS §0 |
| `test_path_b_does_not_call_provider_router` | §4 | INVARIANTS §4 |
| `test_validator_returns_verdict_only` | §0 第 1 条 | INVARIANTS §0 |
| `test_specialist_internal_llm_calls_go_through_router` | §4 Path C | INVARIANTS §4 |
| `test_canonical_write_only_via_apply_proposal` | §0 第 4 条 | INVARIANTS §0 |
| `test_all_ids_are_global_unique_no_local_identity` | §7 | INVARIANTS §7 |
| `test_event_log_has_actor_field` | §7 | INVARIANTS §7 |
| `test_no_hardcoded_local_actor_outside_identity_module` | §7 | INVARIANTS §7 |
| `test_no_absolute_path_in_truth_writes` | §7 | INVARIANTS §7 |
| `test_no_foreign_key_across_namespaces` | DATA_MODEL §2 / §5 | DATA_MODEL §2 |
| `test_append_only_tables_reject_update_and_delete` | DATA_MODEL §4.2 | DATA_MODEL §4.2 |
| `test_only_apply_proposal_calls_private_writers` | DATA_MODEL §4.1 | DATA_MODEL §4.1 |
| `test_artifact_path_resolved_from_id_only` | DATA_MODEL §6 | DATA_MODEL §6 |
| `test_route_metadata_writes_only_via_apply_proposal` | PROVIDER_ROUTER §6.4.1 | PROVIDER_ROUTER §6.4 |
| `test_route_override_only_set_by_operator` | §7.1 | INVARIANTS §7.1 |
| `test_ui_backend_only_calls_governance_functions` | INTERACTION §4.2.1 | INTERACTION §4.2.1 |

这些测试是"边界没有漂移"的可执行证明。


