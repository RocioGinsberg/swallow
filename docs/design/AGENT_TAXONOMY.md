# Agent Taxonomy

> **Design Statement**
> Swallow 的分类学只回答一个问题:**给定一个候选实体,它能在 Execution Plane 的哪个位置上活动,能写哪些 Truth 面**。它不绑定品牌,不预测未来执行器形态,不替代 INVARIANTS。
>
> 实体到具体品牌 / CLI / API 的绑定见 → `EXECUTOR_REGISTRY.md`。

> 项目不变量见 → `INVARIANTS.md`(权威)。本文档只对其中的实体描述格式做展开和示例。

---

## 1. 设计动机

仅用品牌名标识实体会掩盖三个关键信息:

1. 它在系统中承担什么**职责**,是否有权推进主任务前进
2. 它的**记忆权限**——能写哪些 Truth 面
3. 它的**运行站点**——延迟与风险特征

分类学的目的是回答这些问题,而不是给模型起名字。

---

## 2. 实体描述格式:五元组

每个执行实体使用统一的五元组描述。**不允许复合型角色**。

```
Entity = (
    role,              # {general_executor, specialist, validator}
    advancement_right, # {none, propose_only, advance_via_orchestrator}
    truth_writes,      # 显式枚举的 Truth 面白名单
    llm_call_path,     # {none, controlled_http, agent_internal, specialist_internal}
    runtime_site,      # {local_process, hybrid, remote_worker}
)
```

### 2.1 各字段含义

#### `role` —— 系统角色

| 取值 | 含义 | 关键约束 |
|---|---|---|
| `general_executor` | 承担完整工作切片的执行实体 | 可产出核心 artifacts,可经 Orchestrator 影响 task-state,但无权重定义路由策略或越过 review 边界 |
| `specialist` | 拥有单一高价值边界职责的实体 | 输入输出边界强、写权限窄、风险更容易治理 |
| `validator` | 评估其他组件产出质量的实体 | 只产出 verdict,不主导主链路推进 |

> **判断法则**:
> - 可以合理要求它"接管这步任务并产出主要输出" → `general_executor`
> - 在窄边界内执行固定 pipeline,产出结构化候选物 → `specialist`
> - 只评估、只断言、只产出 verdict,不做修改 → `validator`

`Orchestrator` 与 `Operator` 不是 role 的取值——它们在 Control Plane,不进入 Execution Plane 枚举。

#### `advancement_right` —— 推进权限

| 取值 | 含义 |
|---|---|
| `none` | 不能推进 task state(典型:Validator) |
| `propose_only` | 只能产出 proposal artifact,等待 Operator 通过 `apply_proposal` 应用 |
| `advance_via_orchestrator` | 产出结果交给 Orchestrator,由 Orchestrator 决定是否推进 |

**没有任何实体可以"直接 advance task state"**。这条边界由 INVARIANTS §0 第 1 条强制。

#### `truth_writes` —— Truth 写权限

显式枚举的 Truth 面白名单,取值范围:

```
{task_artifacts, event_log, staged_knowledge, canonical_knowledge,
 route_telemetry, route_metadata, policy, resume_notes}
```

**默认安全预设**:新实体引入时,默认值为 `{event_log}`(只能 append-only 留痕)。任何额外写权限都需要在 EXECUTOR_REGISTRY 中显式声明。

具体的写权限矩阵见 → `INVARIANTS.md §5`(权威)。

#### `llm_call_path` —— LLM 调用路径

| 取值 | 含义 | 经过 Provider Router |
|---|---|---|
| `none` | 不调用 LLM(纯规则 / 纯计算实体) | — |
| `controlled_http` | Orchestrator 组装 prompt 后调用(Path A) | ✅ |
| `agent_internal` | Agent 内部自主调用,Swallow 不可见(Path B) | ❌ |
| `specialist_internal` | Specialist 内部 pipeline 多次调用 Path A(Path C) | ✅(穿透) |

#### `runtime_site` —— 运行站点

| 取值 | 含义 |
|---|---|
| `local_process` | 在本机进程内运行。即使内部调远程 API,只要 Swallow 看到的接口是本地黑盒进程,就归此类 |
| `hybrid` | 本地控制流 + 受控远程 LLM 调用(必然伴随 `llm_call_path = controlled_http` 或 `specialist_internal`) |
| `remote_worker` | 完整执行体在远程机器(当前 phase 不实现,见 INVARIANTS §8) |

> **判定规则**:`llm_call_path = agent_internal` 时,`runtime_site` 一律是 `local_process`,不论 agent 内部是否调远程 API——因为对 Swallow 而言它就是个本地黑盒进程。

---

## 3. 三类系统角色详述

### 3.1 General Executor

承担完整工作切片的执行实体。

| 属性 | 默认值 |
|---|---|
| `advancement_right` | `advance_via_orchestrator` |
| `truth_writes` | `{task_artifacts, event_log}` |

允许的工作:代码修改、文件编辑、计划草案、大跨度总结、artifact 产出。

不允许的工作:重定义路由策略、越过 review 边界自行 promote 知识、写入 task state。

### 3.2 Specialist Agent

拥有单一高价值边界职责的实体。

| 属性 | 默认值 |
|---|---|
| `advancement_right` | `propose_only` 或 `advance_via_orchestrator`(取决于 specialist 类型) |
| `truth_writes` | 至多 `{task_artifacts, event_log, staged_knowledge}` |

| 特征 | 说明 |
|---|---|
| 边界明确 | 输入输出 schema 固定,不允许自由扩张 |
| 写权限窄 | 默认不允许写 canonical / route / policy |
| Pipeline 固定 | 内部流程封装,Orchestrator 不介入其内部步骤 |

**Specialist 不是第三种通用执行器**;它可以复用 Path A 调用底层 LLM(Path C),但系统角色、输入输出和写权限必须保持窄边界。

### 3.3 Validator

只产出 verdict 的实体。

| 属性 | 默认值 |
|---|---|
| `advancement_right` | `none` |
| `truth_writes` | `{event_log}`(append verdict 与 reasons) |
| `llm_call_path` | 通常是 `controlled_http`(走 Path A) |

输出:`VerdictReport {pass | fail | uncertain, reasons[], severity, evidence_refs[]}`。

**关键边界**:Validator 写完 verdict 就结束。"是否推进任务"的决策由 Orchestrator 内部的 Review Gate 读取 verdict 后做出(见 ORCHESTRATION.md)。

Validator 不是 Reviewer——Reviewer 这个词在文档中保留作为人类审阅者(Operator)的别名,不是执行实体的 role 取值。

---

## 4. 推进权限的语义边界

```
                     │ 改 task state │ 改 staged knowledge │ 改 canonical / route / policy │
─────────────────────┼───────────────┼─────────────────────┼───────────────────────────────┤
Orchestrator         │      ✅       │         -           │              -                │
General Executor     │   间接(经 O)│         -           │              -                │
Specialist           │      -        │         ✅          │              -                │
Validator            │      -        │         -           │              -                │
Operator (via CLI)   │      ✅       │         ✅          │      ✅(经 apply_proposal) │
```

完整 Truth 写权限矩阵见 → `INVARIANTS.md §5`。本表只展示与"推进"相关的核心边界。

---

## 5. 默认安全预设

为系统引入新实体时,默认值如下。任何放宽必须在 EXECUTOR_REGISTRY 中显式声明,并附带理由。

| 维度 | 默认值 |
|---|---|
| `role` | `specialist` |
| `advancement_right` | `propose_only` |
| `truth_writes` | `{event_log}` |
| `llm_call_path` | `none`(除非确有需要) |
| `runtime_site` | `local_process` |

---

## 6. 五元组示例

下面三个示例只用于说明五元组的填写方式。**当前真实绑定的所有执行器五元组见 EXECUTOR_REGISTRY.md**,本文档不重复列出。

### 6.1 一个本地施工型 General Executor

```
role               = general_executor
advancement_right  = advance_via_orchestrator
truth_writes       = {task_artifacts, event_log}
llm_call_path      = agent_internal
runtime_site       = local_process
```

### 6.2 一个云端规划型 General Executor(走 Path A)

```
role               = general_executor
advancement_right  = advance_via_orchestrator
truth_writes       = {task_artifacts, event_log}
llm_call_path      = controlled_http
runtime_site       = hybrid
```

### 6.3 一个 ingestion Specialist

```
role               = specialist
advancement_right  = propose_only
truth_writes       = {task_artifacts, event_log, staged_knowledge}
llm_call_path      = specialist_internal
runtime_site       = hybrid
```

---

## 7. HTTP / CLI / Specialist 的生态位

三者**不在同一维度上竞争**:

| 类别 | 本质 | 适合 | 不适合 |
|---|---|---|---|
| **Path A (HTTP Executor)** | 无工具循环的模型认知层 | brainstorm / review / synthesis / classification / 结构化抽取 | 默认代码库问答、代码修改、命令验证 |
| **Path B (Autonomous CLI)** | workspace 行动层 / 黑盒 tool-loop | 读 repo / 改代码 / 跑测试 / 追踪调用链 / 验证结果 | 固定 schema ingestion、canonical promotion、只读审计 |
| **Path C (Specialist)** | 固定专精流程封装 | ingestion / librarian / literature parsing / meta-optimization / quality validation | 开放式施工、自由探索、隐藏编排、替代通用 executor |
| **Validator** | 结果质量防线 | schema 校验 / artifact 评估 / 一致性审计 / verdict 产出 | 替 executor 施工、自动修正主产物 |

判断规则:

- 任务成功依赖"读 workspace / 跑命令 / 改文件 / 验证结果" → 默认 Path B
- 任务成功依赖"理解材料 / 形成判断 / 生成结构化报告" → 默认 Path A
- 任务是高频、边界稳定、输入输出 schema 明确的专精流程 → 封装为 Specialist(Path C)
- Specialist Agent 不是第三种通用 executor family;它复用 Path A,但保持窄边界
- Orchestrator 通过 task truth、artifacts、handoff objects 与 explicit input_context 协调,不通过原始聊天记录或 repo chunk 传递

---

## 8. 与其他文档的接口

| 对接文档 | 接口关系 |
|---|---|
| `INVARIANTS.md` | 五元组定义 / 写权限矩阵 / Path A/B/C 定义的权威 |
| `EXECUTOR_REGISTRY.md` | 实体到具体品牌 / CLI / API 的绑定 |
| `ORCHESTRATION.md` | 编排层依据 taxonomy 选择 executor 并控制权责边界 |
| `PROVIDER_ROUTER.md` | provider / backend / executor family 映射到角色槽位,不等于角色本身 |
| `HARNESS.md` | Harness 根据角色定位提供不同层级的约束与能力支撑 |

---

## 附录 A:Anti-Patterns

| 反模式 | 说明 |
|---|---|
| **Brand-Only Agent** | 只用品牌名标识实体,掩盖其权责边界 |
| **Hidden Orchestrator** | 任何 Execution Plane 实体悄悄接管系统推进走向 |
| **Implicit Global Memory Writer** | 局部实体绕过 review/promotion 直接写入 canonical truth |
| **Everything Agent** | 一个实体同时承担 general_executor、specialist、validator 多个 role |
| **Brand-Leaking Taxonomy** | 把品牌名直接写进 taxonomy 主体,导致角色设计被品牌能力牵引 |
| **Specialist-as-General-Executor** | 把 Specialist 暴露成可自由接管任意任务的通用执行器 |
| **Composite Role** | 用 `specialist-or-general-executor` 之类的"或"型角色,违反五元组单一性 |
| **HTTP-as-Coding-Default** | 让无 tool-loop 的 Path A 默认承担代码库阅读与实施职责 |
| **Sub-Orchestrator Adoption** | 把自身具备 orchestration 能力的外部平台接入为 executor(违反 INVARIANTS §6) |
