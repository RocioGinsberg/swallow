# 多智能体协同与编排设计 (Orchestration & Handoff)

## 0. 阅读约定

本文档描述的是 **Swallow 当前主分支的编排与交接基线**。

这里最重要的不是把系统理解成“很多 Agent 在聊天”，而是明确：

- 编排层是唯一的任务推进协调层
- 执行器只是受控的外部执行单元
- Agent 之间不直接对话，而通过 task truth、artifacts、review feedback 和 handoff objects 协作
- handoff 是 task semantics 的显式延续，而不是聊天记录堆叠

本文档应与当前架构文档中的以下原则一起理解：

- local-first
- SQLite-primary truth
- taxonomy before brand
- truth before retrieval
- explicit separation between controlled HTTP path and black-box agent path

---

## 1. 核心理念：自建编排中枢与基于状态的异步协同

传统多智能体系统常采用：

- 群聊式协作
- 厂商原生 Agent 内部的黑盒分工
- 共享长对话上下文作为协作介质

这在长周期软件工程与知识工作中会带来两个问题：

- 上下文污染严重
- 系统边界被厂商原生工作流绑死

Swallow 当前的核心选择是：

> **系统自建轻量级的编排中枢（Router / Planner / Subtask Orchestrator / Review Gate / Task Runtime），厂商原生 agent 或其他执行器仅作为外部执行单元接入。Agent 之间绝不直接对话。它们通过 task truth、artifacts、review feedback、event truth 与结构化 handoff objects 完成协作。**

因此，Swallow 的协同方式本质上是：

> **state-based asynchronous collaboration**

而不是 group-chat-based collaboration。

---

## 2. 当前编排层的核心职责

Swallow 的编排层是唯一可以决定“任务下一步如何推进”的层。

它至少负责：

- 把模糊意图收束成可执行 task semantics
- 决定是否拆分子任务
- 决定交给哪个 executor / worker surface
- 决定何时触发 review / retry / rerun / waiting_human
- 决定哪些结果只是中间产物，哪些结果可以进入更正式的 truth surfaces

因此，当前必须坚持以下边界：

- **编排层是唯一协调层**
- 执行器不可静默接管全局推进语义
- 审查者不可静默替 executor 施工
- 黑盒 agent 不可演化成 hidden orchestrator

---

## 3. 调度引擎核心组件

### 3.1 Strategy Router

Strategy Router 是编排层的入口判断节点。它在任务进入具体执行路径前完成所有**策略层面**的路由判断。

当前核心职责包括：

- **任务域判断**：工程 / 研究 / 日常 / 批处理等
- **复杂度评估**：决定当前更适合走 Claude Code、Aider、Warp/Oz worker，还是受控 HTTP path
- **能力级别选定**：确定所需能力级别，如强推理、长上下文、实现导向、并行调查导向等
- **能力下限断言 (Capability Floor Assertion)**：高风险任务不允许被错误地下放给能力不足的路径
- **降级策略预判**：在 route 不可用、执行器不可靠或结果不收敛时，决定是缩小任务粒度、切换执行路径、增强 review 还是进入 `waiting_human`

**设计边界**：

Strategy Router 只做策略判断，不负责：

- endpoint 健康探测
- HTTP payload 级方言适配
- provider 侧物理通道切换

这些属于 Provider Routing / Execution Backend 层。

### 3.2 Planner

Planner 负责把较大的用户意图拆成可以操作的 task cards / execution slices。

它当前更适合承担：

- 定义子任务边界
- 明确输入/输出期望
- 明确约束条件
- 定义 review points 与 handoff points
- 帮助决定哪些部分可以交给黑盒 agent，哪些必须保留给更强执行器或更受控路径

Planner 不是“品牌人格”，而是编排层中的一个系统职责。

### 3.3 Subtask Orchestrator

Subtask Orchestrator 负责平台级的子任务并行与汇聚。

当前必须明确区分两类“subagents”：

#### A. 平台级 subtask orchestration
这是 Swallow 自己控制的系统级并行：

- 子任务由编排层创建
- 边界由编排层定义
- 汇总与收口由编排层控制
- review 与 waiting_human 语义由系统统一管理

#### B. Executor-native subagents
这是某些执行器（如 Claude Code、Warp/Oz 或其他原生 agent）内部自带的子代理机制。

系统对它们的正确态度是：

- 可以利用
- 但不能依赖它们承担系统级协同主线
- 应视为某个执行器内部的黑盒增强，而不是系统总编排能力本身

### 3.4 Review Gate

Review Gate 负责在结果进入下一阶段前做结构化审查。

当前职责包括：

- schema / structure 校验
- 基本质量断言
- 一致性检查
- 决定通过、反馈重试或转入 `waiting_human`
- 为后续 consistency audit、operator review 和风险追溯提供结构化痕迹

Review Gate 不负责：

- 直接改写 executor 产出
- 静默接管主链路施工

### 3.5 Debate / feedback-driven retry

当前系统中的 debate 机制，更准确地说应理解为：

> **feedback-driven retry topology**

其关键原则是：

1. Executor 先产出结果
2. Review Gate 做规则式与结构化审查
3. 若不通过，则生成 `ReviewFeedback`
4. Feedback 注入下一轮执行尝试
5. 超过阈值仍不收敛，则熔断进入 `waiting_human`

这里最重要的边界是：

- Reviewer 不负责替 executor 直接修
- Debate 不是多个强 agent 无边界争论
- 它本质上是由编排层控制的一种反馈重试机制

---

## 4. 当前默认执行路径与编排策略

结合当前默认工作组合，Swallow 的编排层现在更适合按下面的模式工作：

### 4.1 Claude Code

默认用于：

- 高价值任务
- 高复杂度任务
- 架构级修改
- 高错误成本任务
- 复杂变更的最终收口

### 4.2 Aider

默认用于：

- 高频实现
- 边界清晰的小到中等复杂度任务
- 已明确目标的 edit loop

### 4.3 Warp / Oz worker surface

默认用于：

- 中等复杂度但可拆分的任务
- 多终端并行调查
- 测试矩阵、环境准备、日志分析、中间结果生产

### 4.4 HTTP controlled path

默认用于：

- 你希望精细控制 prompt / dialect / retrieval assembly / fallback 的场景
- 更偏“受控模型调用”而不是“黑盒 agent 施工”的场景

因此，编排层当前的重要职责之一是：

> **决定某个任务该走 executor governance path，还是 model invocation control path。**

也就是：

- 黑盒 agent path：偏治理、边界、skills、review
- 受控 HTTP path：偏 prompt、dialect、route、fallback

---

## 5. 结构化交接 (Structured Handoff)

Swallow 当前不接受“把整段聊天记录交给下一个执行器”这种粗放交接方式。

当前 handoff 的正确定位是：

> **在任务推进链上，把已经发生的工作压缩成可继续执行的 task semantics continuation object。**

### 5.1 告别堆叠聊天记录

当一个阶段结束，或任务需要流转给：

- 下一个 executor
- 下一个子任务
- review / human operator
- ingestion / knowledge-side process

交接内容都应被提纯，而不是把所有聊天历史原封不动塞给下一段执行。

### 5.2 handoff object 的核心要素

一个合格的 handoff 应尽量包含：

- **Goal**：总目标是什么
- **Done**：已完成了什么，踩过哪些坑
- **Next Steps**：下一步最应该做什么
- **Context Pointers**：最小必要上下文指针，而不是大段原文复制
- **Constraints**：当前仍然生效的边界条件

这里最关键的是 `Context Pointers`：

Swallow 更鼓励传递：

- artifact references
- task refs
- route / topology refs
- file / note / commit / citation pointers

而不是把大段源码或长篇聊天记录整块塞入下一轮 prompt。

### 5.3 handoff 与 artifact / truth 的关系

handoff 不应被误解为“某种孤立的文本备忘录”。

它当前更适合被理解为：

- task truth 的显式延续对象
- artifact surface 的一种结构化产物
- 帮助恢复、接力、审查和继续推进的中间控制对象

也就是说，handoff 可以被持久化为 artifact，但它的价值不止于“存了一段文本”，而在于它被编排层与恢复机制真正消费。

### 5.4 Schema Alignment Note

当前 handoff vocabulary 继续以统一 schema 为 authoritative 定义。

映射：

- `Goal` -> `goal`
- `Done` -> `done`
- `Next_Steps` -> `next_steps`
- `Context_Pointers` -> `context_pointers`
- `Constraints` -> `constraints`

这些字段不应再被某个单独 surface 随意改写成不兼容私有格式。

---

## 6. 多执行器协同拓扑：角色先于品牌

当前协同应以**系统角色**为单位组织，而不是以品牌名称直接组织。

品牌只是当前默认绑定，不是架构本体。

### 6.1 当前更准确的默认绑定

| 系统职责 | 当前默认绑定 | 说明 |
|---|---|---|
| 高复杂度主执行与复杂收口 | Claude Code | 高价值、高复杂度任务主路径 |
| 高频实现施工 | Aider | 默认 implementation executor |
| 并行 worker / terminal operations | Warp / Oz | 中等复杂度并行任务与中间结果生产 |
| 受控模型调用 | HTTP path | prompt/dialect/fallback 可控 |

### 6.2 典型拓扑

#### 工程链路接力
Planner / Strategy Router 判断任务复杂度 → Claude Code 做高层方案或复杂修改 → Aider 承担局部高频施工 → Review Gate / validator 复核 → Human 决定最终合并或继续推进。

#### 并行调查链路
Planner 拆出多个独立子问题 → Subtask Orchestrator 把它们分发给 Warp/Oz worker surface 或其他边界清晰的执行路径 → 汇总中间结果 → 更强执行者或 human 收口。

#### 受控模型调用链路
任务进入 HTTP controlled path → Router 指定 model hint / dialect → HTTPExecutor 发起请求 → 结果进入 review / artifact / handoff 路径。

#### feedback-driven retry 链路
Executor 产出 → Review Gate 失败 → 生成 ReviewFeedback → 重试 → 超阈值后 `waiting_human`。

---

## 7. 编排层与知识层、交互层的关系

当前编排层必须同时与上、下两侧严格解耦：

### 对上：Interaction & Workbench

- 交互层负责形成 task object、展示状态、提供 control surface
- 编排层负责真正推进任务
- 聊天面板不能替代编排层
- Control Center 不能替代编排层

### 对下：Knowledge / State / Provider

- 知识层负责 truth objects 与 retrieval
- 状态层负责 task truth / event truth / artifacts
- Provider Routing 负责物理路由、方言与 fallback
- 编排层不应越权接管 provider 物理层细节

因此，编排层的正确位置是：

> **连接 Interaction、Execution、Knowledge、State 与 Provider 的唯一任务推进中枢。**

---

## 8. 当前对实现者的约束性理解

如果继续扩展 Orchestration & Handoff 层，当前应坚持：

1. 不要把系统重新写成多 agent 群聊协同
2. 不要让黑盒 executor-native subagents 冒充平台级编排能力
3. 不要让 Review Gate 变成偷偷施工的第二执行器
4. 不要让 handoff 退化成长聊天记录堆叠
5. 不要用品牌名直接定义系统职责
6. 不要让聊天面板或 Control Center 绕过编排层直接推进任务
7. 不要混淆 executor governance path 与 HTTP controlled path

---

## 9. 一句话总结

Swallow 当前的编排与交接层，不应理解为：

> 多个 Agent 直接对话、互相转发长上下文的协作网络

而应理解为：

> 一个由 Swallow 自建的唯一编排中枢：它通过 Strategy Router、Planner、Subtask Orchestrator、Review Gate 与结构化 handoff objects，围绕 task truth、artifacts 与 review feedback 协调受控执行路径和黑盒执行器路径的异步协同
