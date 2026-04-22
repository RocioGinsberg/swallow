# Swallow Architecture

**Swallow** 是一个面向真实项目工作的、**local-first 的有状态 AI workflow system**。

它不是单次对话聊天器，也不是某个厂商 Agent 的外壳，而是一个围绕以下目标构建的系统：

- 让任务能跨多轮、多阶段和多会话持续推进
- 让代码工作与知识工作进入同一条任务链路
- 让执行过程留下可恢复、可审计、可复用的状态与工件
- 让外部 AI 工具产生的结论进入系统，但不污染长期知识真值
- 让执行器保持可替换，而不是和某个模型品牌绑定

---

## 0. 阅读约定

本文档**优先描述当前主分支 (`main`) 的架构基线**，仅在单独小节中讨论方向性演进。

- **Current Baseline**：已经在 `main` 上成立，或者已经被 README / active context 视为当前稳定基线的部分
- **Directional / Future**：仍属于后续 phase 的方向，不应被当作已实现能力

如果本文档与 phase 历史设计材料存在表述差异，应以当前基线和最近 tag 对齐理解，而不是回退到旧的概念框架。

---

## 1. 当前系统定位

Swallow 当前应被理解为：

- 一个 **任务工作台 / 工作流系统**
- 一个 **有状态 runtime**
- 一个 **知识对象治理系统**
- 一个 **可替换执行器编排系统**

它当前**不是**：

- 纯聊天产品
- 纯 RAG 项目
- 单一代码 Agent 的包装层
- 默认走 hosted / distributed worker 的平台系统

当前基线坚持三条原则：

1. **Local-first**：单用户、本地工作区与本地状态真值优先
2. **Truth before retrieval**：先定义任务真值与知识真值，再提供检索与召回
3. **Taxonomy before brand**：先定义系统角色，再绑定具体执行器或模型品牌

---

## 2. 当前架构总览

从当前 `main` 的实现出发，Swallow 最适合用下面五个长期层来理解：

```mermaid
graph TD
    UI["1. Interaction / Workbench<br/>CLI / Control Surface / Review Surface"]
    ORCH["2. Orchestrator<br/>Strategy Router / Planner / Review Gate / Subtask Orchestrator"]
    EXEC["3. Execution & Capabilities<br/>General Executor / Specialist Agent / Validator / Tools / Skills / Workflows"]
    KNOW["4. Knowledge Truth & Retrieval<br/>Evidence / Wiki / Canonical / Retrieval Orchestration"]
    STATE["5. State / Event / Artifact / Route Truth<br/>TaskState / EventLog / Artifacts / Policy / Topology"]
    PROVIDER["6. Provider Routing & Execution Backends<br/>Route Registry / Dialect Adapters / HTTP / CLI / Fallback"]

    UI --> ORCH
    ORCH --> EXEC
    ORCH <--> KNOW
    EXEC <--> KNOW
    EXEC <--> STATE
    ORCH --> PROVIDER
    EXEC --> PROVIDER
```

上图比早期的“RAG 层 + Wiki 层”说法更贴近当前基线，因为现在系统中真正居中的并不是向量检索，而是：

- 任务真值
- 知识真值
- 受控检索与受控写入

---

## 3. 各层当前职责

### 3.1 Interaction / Workbench

当前交互层以 CLI 和 operator-facing inspection / review / control surfaces 为主。

它的职责不是“和模型聊天”，而是：

- 创建任务
- 运行任务
- 检查状态、工件、路由、拓扑、策略和 grounding
- 进行 retry / rerun / resume / review / control

这一层应被理解为 **task workbench**，而不是 chatbot shell。

### 3.2 Orchestrator

编排层决定：

- 当前任务要做什么
- 哪些子任务需要拆分
- 何时触发审查
- 何时进入等待人工
- 哪种能力级别适合当前任务

编排层负责策略判断，但**不直接承担供应商路由的物理细节**。

当前与编排层紧密相关的核心构件包括：

- Strategy Router
- Planner / TaskCard planning
- Review Gate / consensus policy
- DAG-based subtask orchestration
- waiting_human / retry / rerun / resume semantics

### 3.3 Execution & Capabilities

执行层的核心不是某个品牌，而是系统角色。

当前应按以下 taxonomy 理解：

- **General Executor**：承担广义任务推进与状态变更
- **Specialist Agent**：承担边界清晰的专项子系统工作
- **Validator / Reviewer**：只做审查与断言，不负责主链路推进

角色先于品牌，品牌只是当前可用实现的例子，而不是架构本体。

同样，执行层不只包含模型调用，还包含：

- tools
- skills
- profiles
- workflows
- validators

也就是说，Swallow 的执行层是 **executor + capability runtime**，而不仅仅是“谁来生成一句回答”。

### 3.4 当前默认工作组合（default operating pattern）

在当前单用户、local-first 的实际工作流中，系统不再预设一组固定品牌阵容作为“永久标准编队”。

更贴近当前使用现实的方式是：

- **Claude Code**：高价值、高复杂度任务的主执行者与复杂收口者
- **Aider**：日常高频实现的默认施工 executor
- **Warp / Oz Agents**：终端原生的并行 worker surface，用于中等复杂度、可拆分的并行任务与环境控制

这三个默认绑定的意义不是取代 taxonomy，而是为当前 operator 提供更高效的默认工作组合。

### 3.5 默认分工原则

#### Claude Code
适合：

- 高错误成本任务
- 高不确定性任务
- 架构改动、复杂重构、疑难排障
- 需要较强判断与方案取舍的工作
- 最终需要高质量收口与 review 的复杂变更

不适合长期被低价值、重复、机械性的实现工作占满。

#### Aider
适合：

- 日常高频实现
- 局部修改
- 明确目标后的 edit loop
- 小到中等复杂度的施工任务
- 已经知道要改什么，只需要高频快速落地的工作

它在当前更适合被理解为 **default implementation executor**。

#### Warp / Oz Agents
适合：

- 多终端管理
- 中等复杂度、可拆分的并行任务
- 批量检查、环境准备、日志分析、测试矩阵、并行调查
- 中间结果生产，而不是高代价主设计裁决

它在当前更适合被理解为 **terminal-native parallel worker layer**，而不是主编排器。

### 3.6 并行不是默认常态，而是条件触发

Swallow 当前并不把“多 agent 并行”视为默认高级形态。

更稳的默认模式是：

- 一个主执行者负责主叙事
- 一个或多个辅助 worker 在边界清晰时并行提供中间结果
- 最终由主执行者或 operator 完成收口

因此，并行更适合在这些场景触发：

- 独立子任务可以清晰拆分
- 需要并行调查多个候选方向
- 需要并行收集日志、测试、环境与中间证据
- 需要一个主执行者 + 一个只读 reviewer / validator

而不适合在高价值复杂任务上让多个强执行者同时争夺主语义。

### 3.7 当前推荐的升级 / 降级路径

更贴近实际使用的默认策略是：

- **简单 / 高频实现** → 默认走 Aider
- **中等复杂、可拆分并行任务** → 默认交给 Warp / Oz worker surface
- **高复杂 / 高价值 / 高错误成本任务** → 升级到 Claude Code

更具体地说：

#### Aider 升级到 Claude Code
当满足任一条件时更适合升级：

- 改动明显扩散
- 需求开始模糊
- 两轮迭代仍不收敛
- 涉及架构边界或高风险设计取舍
- 需要高质量方案说明或复杂 review

#### Warp / Oz 升级到 Claude Code
当满足任一条件时更适合升级：

- 并行结果互相冲突
- 子任务不再独立
- 中间调查上升为设计问题
- 需要统一全局语义和最终裁决

#### Claude Code 降到 Aider
当满足任一条件时更适合降级：

- 方案已经定型
- 后续只剩机械实现
- 改动可明确拆成一组低风险子修改

---

## 4. 当前真值层：State / Event / Artifact / Route Truth

这是 Swallow 与普通 agent demo 的核心区别之一。

系统当前不是依赖单次 prompt 内存推进，而是依赖一组持久化真值：

- **TaskState**：当前任务现场与推进位置
- **EventLog**：过程事件与审计线索
- **Artifacts**：报告、diff、summary、grounding outputs 等显式产物
- **Route / Policy / Topology records**：路由、执行位点、拓扑与策略边界
- **Git truth / workspace truth**：对代码与工作区内容的外部真值约束

这里需要特别区分两件事：

1. **truth records**：系统必须可靠恢复和解释的结构化状态
2. **file outputs / large artifacts**：给人查看、比较、导出的文件产物

在当前基线下，task truth 和 knowledge truth 已经是 **SQLite-primary**；文件镜像、导出文件和 artifact 文件视图仍然保留，但它们不再天然等于 authoritative truth。

---

## 5. 当前知识架构：Knowledge Truth Layer + Retrieval & Serving Layer

这是当前最需要与旧设计语言区分开的部分。

### 5.1 为什么要修正旧叙事

早期可以把知识层粗略理解为：

- Raw Evidence / RAG
- LLM Wiki / Cognitive Layer

但在当前基线下，这种说法已经不够精确，因为系统中真正的中心不再是“向量先召回”，而是 **先知识真值归一，再检索服务**。

### 5.2 Knowledge Truth Layer

当前知识真值层回答的问题是：

- 什么是有效知识对象
- 这些知识从哪里来
- 处于什么阶段
- 是否允许复用
- 是否已被 supersede
- 谁拥有写权限

这一层当前包含的核心对象与边界包括：

- Evidence
- WikiEntry
- canonical records / canonical registry
- staged / task-linked / reusable knowledge
- promote / reject / dedupe / supersede decisions
- source traceability / grounding refs
- Librarian-controlled canonical write authority

当前基线中，知识真值层的 authoritative state 应被理解为 **SQLite-backed knowledge truth**。

### 5.3 Retrieval & Serving Layer

检索层的职责不是取代真值层，而是围绕已治理知识对象提供可用召回。

它负责：

- exact / symbolic retrieval
- metadata / policy-aware filtering
- relation expansion
- vector semantic recall
- text fallback
- evidence pack assembly

因此，向量检索在当前系统中的定位应当是：

> **semantic retrieval augmentation, not authoritative truth**

embedding 和向量索引不是知识源头，也不应成为系统默认入口；它们只是对已治理知识对象进行补充召回的能力。

### 5.4 Wiki 在当前系统中的定位

Wiki 不应再被理解为“RAG 之上的总结页”。

在当前基线中，Wiki 更适合被理解为：

- 项目级知识编译对象
- 稳定语义入口
- 面向人和模型共享的知识组织节点

Wiki 属于知识真值层的一部分，而不是一个飘在向量检索之上的展示壳。

### 5.5 当前推荐的检索顺序

当前设计上更合理的默认顺序应是：

1. task-local / canonical / wiki exact match
2. metadata + policy filtering
3. relation expansion
4. vector semantic recall
5. text fallback

也就是说，Swallow 当前更适合坚持：

> **object-first retrieval, vector-assisted recall**

而不是 vector-first retrieval。

---

## 6. 当前知识写入边界

Swallow 当前知识系统的另一个关键点，是**写入权力被显式收束**。

原则上：

- 并不是所有执行器都能直接写 canonical knowledge
- 高价值、可复用、相对稳定的信息才允许晋升
- 写入需要来源、阶段与复核边界
- Librarian / review 机制负责知识污染控制

这意味着系统追求的不是“记住越多越好”，而是：

- 明确来源
- 明确阶段
- 明确复用边界
- 明确写权限

因此，Swallow 的知识层更接近 **knowledge governance system**，而不是松散的记忆池。

---

## 7. Provider Routing & Execution Backends

### 7.1 当前定位

Provider Routing 层的职责，是把上游已经决定好的任务能力需求，翻译成可执行的物理调用路径。

它当前主要负责：

- route registry / route metadata
- logical model → physical route mapping
- dialect adaptation
- backend selection
- fallback execution path
- route telemetry

### 7.2 当前职责边界

当前需要明确区分两层决策：

| 问题 | 编排层 | Provider Routing |
|---|---|---|
| 任务需要什么级别的能力 | 是 | 否 |
| 任务是否需要 review / waiting_human | 是 | 否 |
| 当前哪条物理路由可用 | 否 | 是 |
| 这次请求如何适配为目标方言 | 否 | 是 |
| 通道异常后切到哪条 fallback | 否 | 是 |

### 7.3 当前执行后端

当前系统已经拥有多种执行后端，而不是单一路径：

- HTTP executor path
- CLI executor path
- route-level fallback
- dialect-aware request formatting

因此，Provider Routing 层已经是现实中的系统边界，而不是抽象概念。

### 7.4 当前两条不同的模型调用路径

为了避免后续混淆，当前需要明确区分两条不同的调用路径：

#### A. Swallow-controlled HTTP path

这条路径的典型形式是：

`TaskState + RetrievalItems -> Router -> route_model_hint / dialect_hint -> HTTPExecutor -> HTTP API`

在这条路径中，Swallow 自己控制：

- prompt 生成与格式化
- retrieval context assembly
- `route_model_hint`
- `dialect_hint`
- request payload 结构
- fallback 逻辑
- telemetry 记录

因此，这条路径上的方言适配器是真正**由 Swallow 控制**的。只要请求仍然经过 router + dialect adapter + HTTPExecutor，模型方言就会按当前 route / model hint 自动生效。

#### B. Agent black-box path

这条路径的典型形式是：

`TaskState -> CLIAgentExecutor / external agent -> agent internal model handling -> model/provider`

例如 Aider、Claude Code、Warp/Oz 这类原生 agent / CLI 工具，一旦在内部自己决定：

- 用哪个模型
- 如何拼接 prompt
- 是否做多轮反思
- 如何调用工具或子代理

那么这些内部策略通常不再由 Swallow 直接控制。

在这条路径里，Swallow 更擅长控制的是：

- 任务边界
- 输入输出契约
- subagents / skills / rules
- 升级 / 降级策略
- 成本、日志与行为观测

而不是精细控制 agent 内部的具体 prompt 或方言实现。

### 7.5 方言适配器的正确作用域

因此，当前应把 dialect adapter 的主要作用域理解为：

- **Swallow-controlled HTTP path** 的模型协议与提示格式翻译层

而不是：

- 所有 agent 内部行为的统一 prompt 控制器

换句话说：

- 对 HTTP 直连模型，方言适配是主控制手段
- 对黑盒 agent，方言适配通常退居次要，系统重点应转向 executor governance

### 7.6 当前对默认绑定的理解

当前 provider / backend 层不应再预设一组固定品牌阵容作为永久标准配置。

更合适的理解是：

- 系统保留可替换执行器框架
- taxonomy 决定角色槽位
- operator 根据真实工作流选择当前默认绑定
- `Claude Code + Aider + Warp/Oz` 是当前更贴近实际使用的默认组合，而不是唯一合法实现

因此，provider 设计的目标是：

- 保持可替换性
- 支持升级 / 降级 / fallback
- 支持并行 worker surface
- 不让某一组品牌默认阵容反过来绑死系统角色

### 7.7 关于旧文档引用

早期某些 provider routing 设计文档已经在后续文档整理中被合并进 phase materials、README 和当前实现语义中。今后若引用 provider routing 设计，应以当前 `main` 上存在的文档与实现为准，而不再依赖已合并移除的旧文件名。

---

## 8. 当前对对象存储 / 远程执行的立场

Swallow 当前仍然应被理解为：

- local-first
- single-user-first
- non-hosted-by-default

因此，当前不应把对象存储或远程 worker 当作知识主真值层。

更合理的分层是：

- **本地文件系统**：原始材料、导出文件、大型 artifact、镜像视图
- **SQLite**：task truth、event truth、knowledge truth、治理状态
- **可选 blob backend（未来）**：S3 / OSS / MinIO 等，仅作为附件 / artifact / archive 的后续扩展

也就是说，未来即使引入对象存储，它也应是 **blob backend**，而不是知识 authoritative store。

---

## 9. 当前与未来：哪些已经成立，哪些仍属方向

### 已经成立（Current Baseline）

- local-first task runtime
- SQLite-primary task truth
- SQLite-primary knowledge truth
- Librarian-governed knowledge boundaries
- optional vector retrieval with fallback semantics
- route / topology / policy visibility
- HTTP + CLI execution backends
- taxonomy-first executor understanding
- default operator workflow anchored on `Claude Code + Aider + Warp/Oz`
- parallelism treated as conditional strategy rather than mandatory default
- explicit separation between controlled HTTP path and black-box agent path

### 仍属方向（Directional / Future）

- real remote execution / multi-machine transport
- object-storage-backed blob layer as a first-class extension
- broader hosted control plane
- larger-scale distributed worker model
- more advanced provider negotiation layers beyond current route registry + fallback model

方向性的东西可以继续设计，但不应倒过来定义当前系统是什么。

---

## 10. 对实现者的约束性理解

如果要继续推进 Swallow，当前最重要的几条理解是：

1. **不要把系统重新拉回纯 RAG 叙事**
2. **不要把向量层误写成知识真值层**
3. **不要让品牌映射重新污染 taxonomy**
4. **不要让未来 hosted / remote 设想反向支配当前 local-first 边界**
5. **不要把“文件仍然存在”误解为“文件永远是唯一真值”**
6. **不要让 Warp / Oz 这类并行 worker surface 悄悄变成隐藏编排器**
7. **不要让 Claude Code 长期被低价值重复实现工作稀释**
8. **不要把黑盒 agent 的内部 prompt 控制能力，误以为等同于 HTTP path 的受控 prompt / dialect 能力**

当前更稳的推进方式是：

- 先巩固 truth layer
- 再扩展 retrieval orchestration
- 再扩展 provider routing / evaluation / audit
- 在默认工作流中让 Claude Code / Aider / Warp-Oz 各守其位
- 对 HTTP path 追求 prompt / dialect / fallback 的强控制
- 对黑盒 agent path 追求任务边界、skills、subagents、review 与 telemetry 的强治理
- 最后才考虑 blob backend、remote worker、hosted control plane 等扩张议题

---

## 11. 一句话总结

Swallow 当前的正确理解不是：

> 一个建立在向量 RAG 之上的多 Agent 平台

而是：

> 一个 local-first、以任务真值和知识真值为中心、通过受控检索与可替换执行器推进真实项目工作的有状态 AI workflow system；其中当前默认工作组合以 Claude Code 处理高复杂高价值任务、Aider 处理高频实现、Warp/Oz 处理并行终端型中间任务，并明确区分受控 HTTP 调用路径与黑盒 agent 调用路径
