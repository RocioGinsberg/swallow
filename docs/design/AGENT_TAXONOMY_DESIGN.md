# 智能体分类学设计 (Agent Taxonomy)

## 0. 阅读约定

本文档描述的是 **Swallow 当前主分支的角色分类基线**。

在当前系统中，分类学的首要目标不是给模型起名字，而是回答：

- 这个实体在系统里承担什么职责
- 它在哪里运行
- 它能读写哪些真值面
- 它是否有权推动主任务前进

因此，当前文档优先坚持：

> **taxonomy before brand**

品牌、模型族和具体执行器实现，只能作为例子或当前可用实例，不能取代系统角色本身。

---

## 1. 文档目的与核心原则

Swallow 不是一个单次对话壳层，而是一个围绕：

- 任务编排
- 上下文检索
- 执行器集成
- 状态持久化
- 知识治理

构建的长期工作流系统。

因此，仅仅把某个角色叫做“Claude Agent”或“Gemini Agent”是不够的，因为这种命名会掩盖：

- 它在系统中的权责边界
- 它是否拥有任务推进权
- 它是否能写入知识对象
- 它的运行站点与后端形态

当前分类学要回答的核心问题是：

1. 系统中应该存在哪些角色
2. 通用执行者与专项智能体的边界是什么
3. Provider / backend / executor family 与 system role 如何解耦
4. 如何防止任何新增实体变成隐藏编排器或隐式全局记忆写入者

### 核心设计原则

- 编排器与运行时边界必须清晰
- capabilities 始终是一等公民
- state / event / artifact / knowledge truth 必须显式可观测
- retrieval 是系统能力，不是某一个 agent 的私有副作用
- provider、backend、executor family 与 role 绝不能混为一谈
- knowledge promotion 必须显式且 policy-gated
- Canonical write 默认禁止，而不是默认开放

---

## 2. 三个正交维度

Swallow 当前继续使用三个正交维度对实体进行分类：

1. **System Role**：该实体承担什么职责
2. **Execution Site**：它在什么环境中运行
3. **Memory Authority**：它能读写哪些范围的真值与记忆

这三个维度应始终先于品牌、模型名、CLI 名称或 API 提供商。

---

## 3. 系统角色 (System Role)

### 3.1 Orchestrator

**定义**：决定系统“下一步该做什么”的唯一协调层。

**核心职责**：

- 垄断任务进展语义
- 决定何时拆分子任务
- 决定何时触发 review gate
- 决定何时停止自动推进并进入 `waiting_human`
- 组合 retrieval、execution、policy 与 state truth

**设计底线**：

- 编排器是唯一协调层
- 任何 executor / specialist / validator 都不应静默接管全局推进语义

### 3.2 General Executor

**定义**：能够承担相对完整或大体量工作切片的执行实体。

**典型职责**：

- 代码仓库级工作
- 文件编辑
- 命令行操作
- 计划草案生成
- 大跨度任务总结

**能力边界**：

- 可以产出核心 task artifacts
- 可以在受控边界下影响 task-state
- 无权重定义全局路由策略
- 无权越过当前 phase / review / policy 边界

### 3.3 Specialist Agent

**定义**：拥有单一且高价值边界职责的实体。

**典型特征**：

- 输入输出边界强
- 成功标准清晰
- 写权限窄
- 风险比通用执行者更容易治理

**适合的职责类型**：

- ingestion
- memory curation
- literature parsing
- retrieval evaluation
- failure analysis
- operator interaction adaptation

### 3.4 Validator / Reviewer

**定义**：用于评估、审计和检查其他组件产出质量的实体。

**关键特点**：

- 不主导任务主链路推进
- 不代替执行者施工
- 最好保持无状态或强约束状态
- 发现问题后返回断言或意见，而不是偷偷修复主链路

### 3.5 Human Operator

**定义**：不是 Agent，但在系统中是一等公民角色。

**核心职责**：

- 批准设计方向
- 决定高风险变更是否进入主线
- 对知识晋升做最终把关
- 在系统不应自动裁决的歧义处作决定

---

## 4. 通用执行者 vs 专项智能体

如果把所有好用模型或辅助能力都统称为“Agent”，并赋予相同权限，系统很快会失去边界感。

### 通用执行者
适合承担：

- 一整块实际工作
- 明确主输出
- 对 task-state / artifacts 有较强影响

### 专项智能体
适合承担：

- 一个受限区域内的分析
- 提纯、审计、验证、结构化抽取
- 局部建议而非整体接管

### 判断法则

- 如果你可以合理要求它“接管这步任务并产出主要输出”，它更像 **general executor**
- 如果它更像“在一个窄边界内分析、验证、提纯或提出建议”，它更像 **specialist**

---

## 5. 运行站点 (Execution Site)

角色不应与部署形态混淆。同一个角色可以运行在不同站点。

### 5.1 Local

- 与主任务环境同机或同工作区
- 延迟低
- 更容易接近 workspace / local state truth
- 风险与本地执行权限强绑定

### 5.2 Cloud-backed

- 调用发生在本地，但能力由远程 API / 服务提供
- 能力通常更强
- 内部过程更不透明
- 更依赖策略拦截与审查边界

### 5.3 Remote Worker

- 在独立机器或远端站点执行
- 当前更多属于扩展方向，而不是默认基线
- 需要额外处理网络、交接、安全和执行位点真值

### 5.4 Hybrid

- 跨多个站点协作
- 例如本地接收输入、云端理解意图、本地执行动作
- 只有在边界明确时才适合引入

---

## 6. 记忆权限 (Memory Authority)

Swallow 当前严格区分：

- task state truth
- task memory / task-local outputs
- staged knowledge
- canonical knowledge truth

因此，不同实体不能共享同一记忆权限。

### 6.1 Stateless

- 除明确入参外，不跨调用保留记忆
- 最安全的默认选项
- 适合 validator 和单次审查器

### 6.2 Task-State Access

- 可读取或修改任务执行所依赖的 task truth、event truth 或运行时产出
- 适合 general executors

### 6.3 Task-Memory

- 可在当前任务或当前会话周期内读写局部记忆伪像
- 常见产物包括 resume note、局部压缩摘要、失败分析结果

### 6.4 Staged-Knowledge

- 有权生成或修改待审查的知识候选对象
- 适合 ingestion、memory curation、知识整理类 specialist

### 6.5 Canonical-Write-Forbidden

- 当前系统中的关键默认安全标签
- 大多数实体默认**禁止**直接突变 canonical knowledge truth
- 它们只能产生草稿、候选对象、建议或 staged changes

### 6.6 Canonical Promotion Authority

- 最窄、最敏感的权限域
- 只属于少数强约束流程，通常需要 review / operator gate

---

## 7. 推荐命名格式

当前架构讨论中，每个实体都应尽量使用显式四段命名：

`[system role] / [execution site] / [memory authority] / [domain]`

例如：

- `general-executor / local / task-state / implementation`
- `general-executor / cloud-backed / task-state / planning-and-review`
- `specialist / cloud-backed / staged-knowledge / conversation-ingestion`
- `validator / cloud-backed / stateless / consistency-check`

这里的最后一段应优先表示**功能领域**，而不是品牌或产品名。

### 关于品牌与工具名

品牌名、API 名或 CLI 名可以作为：

- 当前实现实例
- operator-facing alias
- backend binding information

但它们不应取代 taxonomy 本体。

也就是说：

- `implementation` 是 role-domain
- `codex-cli` / `cline-cli` / `http-claude` 是 implementation binding

前者属于分类学，后者属于执行后端映射。

---

## 8. 常见反模式

### 8.1 Brand-Only Agent

只把实体叫做“Gemini Agent”或“Claude Agent”，会掩盖：

- 它到底是 executor、specialist 还是 validator
- 它是不是拥有任务推进权
- 它的 memory authority 到底是什么

### 8.2 Hidden Orchestrator

某个 planner / reflection / routing helper 在未获授权的情况下，悄悄接管系统下一步执行走向。

这会直接破坏可观测性和任务真值边界。

### 8.3 Implicit Global Memory Writer

某个局部 agent 未经过 review / promotion guard，就把自己的结论直接写入长期 canonical truth。

这会污染知识层，是当前系统必须避免的模式。

### 8.4 Everything Agent

一个实体同时承担计划、执行、审查、路由、记忆提纯和知识晋升。

这通常意味着系统边界没有定义清楚，而不是说明这个实体真的“全能”。

### 8.5 Brand-Leaking Taxonomy

把具体 CLI / API / provider 名称直接写进 taxonomy 主体，久而久之会让角色设计反过来受品牌能力牵引。

当前系统要尽量避免这种反向绑定。

---

## 9. 默认安全预设

当为系统引入新的实体时，当前推荐默认值是：

- **system role**：默认为 `specialist`
- **execution site**：选运维最简单的方式，但不以站点代替角色
- **memory authority**：默认为 `stateless` 或 `task-memory`
- **canonical truth authority**：默认 `Canonical-Write-Forbidden`

只有在工程需求充分明确时，才显式放宽权限。

---

## 10. 当前典型角色模式

### 10.1 General cognitive domains

当前系统中可以保留三类高层认知模式，但应理解为**认知领域**，不是品牌绑定：

1. **Implementation**
   - 偏稳健施工、代码修改、终端执行、落地实现
2. **Planning & Review**
   - 偏方案判断、任务拆解、风险识别、复杂纠偏
3. **Knowledge Integration**
   - 偏长上下文消化、跨文档整合、一致性维护、知识草稿整理

这些领域可以由不同 executor implementations 承担，品牌只是当前可选映射。

### 10.2 当前默认角色绑定（default role bindings）

在当前单用户、local-first 的真实工作流中，更贴近实际的默认绑定是：

#### Claude Code
更适合绑定为：

- `general-executor / cloud-backed-or-hybrid / task-state / planning-and-review`
- 在复杂实现任务中，也可承担高价值的 `implementation` 收口职责

当前建议把它理解为：

- 高价值任务主执行者
- 高复杂度任务主执行者
- 复杂变更的最终收口者

它不适合长期承担大量重复、简单、机械性的实现工作；这类工作应下放给子执行器或更高频的实现工具。

#### Aider
更适合绑定为：

- `general-executor / local / task-state / implementation`

当前建议把它理解为：

- 日常高频实现入口
- 默认施工 executor
- 小到中等复杂度 edit loop 的主力

当需求已经明确、边界已经清晰时，优先使用 Aider 比把所有工作都升级到高阶执行器更稳。

#### Warp / Oz Agents
更适合绑定为：

- `specialist-or-general-executor / local / task-memory-or-task-state / terminal-parallel-operations`

当前建议把它理解为：

- terminal-native worker surface
- 多终端管理层
- 中等复杂度、可拆分任务的并行处理层
- 环境准备、日志调查、测试矩阵、批量分析与中间结果生产层

Warp / Oz 的价值不在于成为第二个主编排器，而在于成为：

> **parallel worker and terminal control plane**

### 10.3 同角色多执行器并存

同一认知角色可以有多个执行器实现并存。系统角色与具体工具是正交的。

例如：

- `general-executor / local / task-state / implementation`
  - 可由 Aider 或其他 CLI executor 实现
- `general-executor / cloud-backed / task-state / planning-and-review`
  - 可由 Claude Code 或某个 HTTP/API executor 实现
- `general-executor / cloud-backed / task-state / knowledge-integration`
  - 可由另一个 HTTP/API executor 实现

在代码层面，关键是所有执行器共享统一协议与统一 route / executor taxonomy，而不是靠品牌名撑起架构。

### 10.4 当前推荐的升级 / 降级矩阵

#### 默认分配

- **简单 / 高频实现** → Aider
- **中等复杂、可拆分并行任务** → Warp / Oz
- **高复杂 / 高价值 / 高错误成本任务** → Claude Code

#### Aider 升级到 Claude Code

当满足任一条件时更适合升级：

- 改动范围明显扩散
- 需求开始模糊
- 两轮以上 edit loop 仍不收敛
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

- 方案已定型
- 后续主要是机械实现
- 改动可拆为一组明确低风险子修改

### 10.5 并行的默认边界

当前不应把多 agent 并行视为默认高级形态。

更稳的做法是：

- 一个主执行者拥有主叙事
- 其他并行 worker 只在边界清晰时承担子任务
- 最终由主执行者或 human operator 完成收口

因此，Warp / Oz 等并行 surface 适合：

- 平行调查多个候选方向
- 批量收集日志、测试与环境证据
- 生成中间结果或候选 patch

但不应在没有明确边界时接管复杂任务主线，否则会滑向 hidden orchestrator 反模式。

### 10.6 核心专项角色

#### Librarian
- `specialist / cloud-backed / staged-knowledge / memory-curation`
- 负责知识冲突检测、去重、变更整理与受控写入收口
- 允许写入 staged knowledge，并受 canonical boundary 约束

#### Ingestion Specialist
- `specialist / cloud-backed / staged-knowledge / conversation-ingestion`
- 负责外部会话与外部材料的提纯、抽取和结构化候选对象生成

#### Literature Specialist
- `specialist / cloud-backed / task-memory / domain-rag-parsing`
- 负责领域资料的深度解析与结构化比较

#### Meta-Optimizer
- `specialist / cloud-backed / read-only / workflow-optimization`
- 负责扫描 event truth、识别模式并提出优化建议
- 输出应保持提案性质，而不是直接修改主系统策略

### 10.7 核心验证者

#### Quality Reviewer
- `validator / cloud-backed / stateless / artifact-validation`
- 用于关键节点的独立校验
- 不负责偷偷修复主链路

#### Consistency Reviewer
- `validator / cloud-backed / stateless / consistency-check`
- 用于识别架构偏离、知识冗余、文档实现不一致

---

## 11. 当前对实现者的约束性理解

如果继续扩展分类学，当前应坚持：

1. 角色先于品牌
2. provider / backend / executor family 不等于 system role
3. 绝不允许 specialist 静默变成 hidden orchestrator
4. 绝不允许大多数实体直接拥有 canonical write authority
5. taxonomy 应服务于治理和可替换性，而不是服务于“给某家模型安排身份设定”
6. 不要让 Claude Code 长期被低价值重复实现工作稀释
7. 不要让 Warp / Oz 在没有清晰边界时演化成第二编排器

---

## 12. 一句话总结

Swallow 当前的 Agent Taxonomy，不应理解为：

> 给不同模型品牌分配不同人格和头衔

而应理解为：

> 先用 role、site、memory authority 和 domain 定义系统边界，再把具体 provider、API 或 CLI 实现映射进去；当前默认工作组合以 Claude Code 处理高复杂高价值任务、Aider 处理高频实现、Warp/Oz 处理并行终端型中间任务
