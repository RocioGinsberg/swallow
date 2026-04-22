# 模型路由与能力协商设计 (Provider Router & Capability Negotiation)

## 0. 阅读约定

本文档描述的是 **Swallow 当前主分支的 Provider Routing / Execution Backend 基线**。

这里最重要的不是“接了多少模型”，而是明确：

- 上层只表达任务需要的能力与执行路径偏好
- Provider Router 负责把逻辑需求翻译成物理路由
- 方言适配主要服务于 **Swallow-controlled HTTP path**
- 黑盒 agent 工具内部的模型选择与 prompt 组织，通常不属于 Provider Router 的精细控制范围

本文档应与当前架构文档中的以下原则一起理解：

- taxonomy before brand
- truth before retrieval
- explicit separation between controlled HTTP path and black-box agent path
- provider/backend/executor family 不等于 system role

---

## 1. Gateway 设计哲学 (Gateway Design Philosophy)

Swallow 的第 6 层不是普通“API 转发器”，而是：

> **负责在逻辑能力需求与物理模型通道之间建立稳定映射关系的 provider routing layer。**

在进入具体设计前，以下原则构成当前基线：

### 1.1 逻辑能力身份 vs 物理路由身份

系统请求的是一种**逻辑能力**，例如：

- 强推理
- 长上下文
- 高频实现
- 代码补全
- 中等复杂度并行调查

而不是某个具体 endpoint。网关层的核心职责，就是维护“逻辑能力 → 物理路由”的映射，而不是把二者直接绑死。

### 1.2 能力语义 vs 供应商语义

Swallow 内部使用自己的语义词汇，例如：

- task family
- capability tier
- route model hint
- dialect hint
- degraded / fallback

供应商使用自己的产品命名和 API 结构。这两套词汇不应混淆。供应商改名、换包装、换格式时，Swallow 的内部语义不应被迫重写。

### 1.3 聚合器是上游，不是网关本身

OpenRouter、AiHubMix、new-api 等都可以是上游或连接层，但它们不是 Swallow 的架构中心。

Swallow 自己必须保留：

- route identity
- routing semantics
- fallback semantics
- telemetry semantics

否则项目会坍缩为某个聚合器的薄封装。

### 1.4 本地模型与本地连接是一等公民

本地运行的模型、本地 HTTP 兼容接口、以及 CLI/agent 路径，都应被视为系统的一等接入方式，而不是“临时旁路”。

差异应体现在：

- route metadata
- capability notes
- cost / latency / reliability profile

而不是通过绕过网关的特殊逻辑处理。

### 1.5 可观测性服务于任务语义

网关层遥测不能只停留在：

- HTTP 状态码
- QPS
- token usage
- latency

更关键的是它要与任务语义绑定，例如：

- 这条 route 在哪类 task family 上最不稳定
- 哪类 fallback 最常发生
- 哪类 degraded 结果最容易触发 review failure

这样 Meta-Optimizer 才能做真正有战略价值的判断。

---

## 2. 当前核心定位：Provider Router，不是全能 Negotiator

早期文档里将这一层写成“Capability Negotiator + Dialect Translator”的中心，这在概念上有启发性，但在当前基线下应收束为更清晰的说法：

> **Swallow 当前更强调 Provider Router / Execution Backend 层，而不是一个包办所有上层语义的全能 Negotiator。**

它的职责是：

- 接收上层已经做过策略判断的逻辑需求
- 选择物理 route
- 决定 dialect / request formatting
- 执行 fallback
- 回收 telemetry

它不应承担：

- 任务域判断
- 风险等级判断
- 是否进入 waiting_human 的最终裁决
- 高层任务分解与执行器角色分派

这些仍应留在编排层。

---

## 3. 统一语义描述与推迟绑定

Swallow 在编排层、状态层、知识层和执行框架中流转的对象，必须保持平台中立。

### 3.1 抵制硬编码

应用层不应出现：

- `if provider == "xxx"`
- 某家模型专用 API 结构泄漏到 task logic 中
- 将品牌名直接视为系统职责名

### 3.2 标准化契约

上层传入网关层的应是：

- 逻辑 route hint
- dialect hint
- executor / backend selection result
- 结构化 prompt ingredients
- context assembly output

而不是厂商专有 payload。

### 3.3 推迟绑定

直到实际发起网络调用或执行物理 route 的最后一刻，Swallow 才将统一语义绑定到具体 provider / endpoint / payload 结构上。

这能最大限度保持：

- 路由灵活性
- 供应商可替换性
- 上层架构稳定性

---

## 4. Controlled HTTP Path vs Agent Black-Box Path

这是当前 Provider Router 文档里最需要写清的边界。

### 4.1 Swallow-controlled HTTP path

典型形态：

`TaskState + RetrievalItems -> Router -> route_model_hint / dialect_hint -> HTTPExecutor -> HTTP API`

在这条路径中，Provider Router 真正可以精细控制：

- route selection
- `model` 字段映射
- dialect / request formatting
- payload shape
- fallback route chain
- degraded telemetry

因此，这条路径是 Provider Router 的主战场。

### 4.2 Agent black-box path

典型形态：

`TaskState -> CLIAgentExecutor / external agent -> agent internal model handling -> model/provider`

例如：

- Aider
- Claude Code
- Warp / Oz
- 其他原生 agent / CLI

一旦这些工具在内部自己决定：

- 用哪个模型
- 怎么写 prompt
- 怎么调工具
- 是否启用内部 subagents

那么 Provider Router 通常无法像 HTTP path 那样精细控制其底层请求。

这时 Swallow 更适合控制：

- 任务边界
- rules / skills / subagents
- input/output contract
- 升级 / 降级策略
- 成本、日志与行为观测

因此，这类路径不应被误写成“也能自动套用同样的 dialect adapter 体系”。

### 4.3 这意味着什么

所以当前应牢记：

- **方言适配器主要服务于受控 HTTP path**
- **黑盒 agent path 主要依赖 executor governance，而不是 provider-side prompt 微控制**

---

## 5. 当前方言适配的正确定位

方言适配的价值仍然存在，但需要被摆到正确的位置上。

### 5.1 方言适配器是什么

方言适配器是：

> **把统一语义请求翻译成特定模型/后端更擅长接收的格式的翻译层。**

例如：

- Claude XML 风格
- Plain Text 风格
- FIM 风格

### 5.2 它主要解决什么问题

- 同样的任务意图，不同模型的最优输入格式不同
- 同样的上下文，不同后端的 payload 结构不同
- 同样的 route intent，需要根据物理后端生成不同请求形态

### 5.3 它不该被误解为什么

- 不是所有 agent 内部 prompt 的统一控制器
- 不是编排层的替代品
- 不是“给所有品牌套一层魔法适配器后就能完全等价”

因此，当前应把 dialect adapter 的作用域限定在：

- **HTTPExecutor 能直接控制的调用路径**

---

## 6. 当前多模型路由策略

当前更合理的 provider routing 思路是：

- 上层先决定任务大致需要哪类能力
- Provider Router 再决定哪条 route 最适合承担该能力
- Route metadata 记录每条 route 的：
  - model family / model hint
  - dialect hint
  - backend kind
  - transport kind
  - fallback route
  - cost / latency / reliability traits

### 6.1 当前 route 选择的关注点

- 逻辑能力是否匹配
- 物理 route 是否健康
- 当前后端是否可用
- 降级链是否存在
- 该 route 是否属于 HTTP controlled path 还是 black-box agent path

### 6.2 编排层与网关层的边界

编排层负责：

- 这个任务值不值得走高阶执行器
- 应不应该降级任务粒度
- 该不该进入 waiting_human
- 哪条路径更适合该任务（HTTP controlled path vs black-box agent path）

网关层负责：

- 如果已经选定某条物理调用路径，该怎么真正发出去
- 失败时沿哪条 fallback 链切换
- 切换后如何记录 degraded telemetry

---

## 7. Graceful Degradation & Fallback

Swallow 当前仍然需要平滑降级机制，但它的语义必须与编排层解耦。

### 7.1 当前 fallback 的正确边界

Provider Router 只处理：

- 物理通道不可用
- HTTP 429 / timeout / 5xx
- route health 异常
- 预定义 fallback route chain 切换

它不负责独立决定：

- 是否允许弱能力模型承担高风险任务
- 是否应该挂起到 waiting_human
- 是否应该缩小任务粒度

这些应由编排层决定。

### 7.2 当前 fallback 语义

更稳的理解是：

- **HTTP 内部降级优先**：尽量先在同类 HTTP 路径内切换
- **CLI/agent 兜底是后续层**：当受控 HTTP path 全链路不可用时，再考虑黑盒执行器兜底
- **最终还需 review 校准信任**：执行级降级后，产出信任度不自动等同于主路径产出

### 7.3 degraded telemetry

所有降级事件都应显式记录：

- `degraded`
- `original_route`
- `fallback_route`
- 相关 task family / logical model / physical route

这样编排层和 Meta-Optimizer 才能消费这些信息。

---

## 8. Provider Connector 与 Swallow Gateway Core 的关系

Swallow 需要明确区分两层：

### 8.1 Swallow Gateway Core（自建）

这部分应继续由系统自己持有：

- route resolution
- dialect adapters
- fallback semantics
- telemetry semantics
- 受控 HTTP path 的 prompt/control integration

### 8.2 Provider Connector Layer

这部分是上游连接层，可以使用：

- new-api
- OpenRouter
- AiHubMix
- 其他 OpenAI-compatible / provider-specific backends

这些连接层的价值在于：

- 渠道管理
- key 管理
- 协议兼容
- 格式互转
- 额度与基础运维面板

但它们不是 Swallow 自己的路由语义中心。

---

## 9. 当前对 new-api 与聚合器的定位

结合你当前的项目语义，更贴切的表述是：

- **new-api**：当前较适合被视为 provider connector / channel manager
- **OpenRouter / AiHubMix 等**：上游渠道或聚合器
- **Swallow**：保留 route identity、fallback semantics、telemetry semantics 和 controlled HTTP path 的核心控制权

因此，Swallow 不应把自己重写成：

- new-api 的薄封装
- OpenRouter 的前端壳
- 某一聚合器的 provider-specific workflow

---

## 10. 当前对实现者的约束性理解

如果继续扩展 Provider Router 层，当前应坚持：

1. 不要把 provider/backend/executor family 混同为 system role
2. 不要把方言适配器误写成黑盒 agent 的通用 prompt 控制器
3. 不要让网关层接管编排层的高层判断
4. 不要让聚合器成为架构中心
5. 不要把 route metadata、长期模型评估与战略知识全部坍缩到一个配置表里
6. 不要让 fallback 逻辑变成“任何情况都自动硬降级”的借口
7. 不要忽略 controlled HTTP path 与 black-box agent path 的根本差异

---

## 11. 一句话总结

Swallow 当前的 Provider Router，不应理解为：

> 一个能统一接管所有 agent 与所有 provider 内部行为的全能协商器

而应理解为：

> 一个把上层逻辑能力需求映射到物理模型路由上的 provider routing layer；它主要服务于受控 HTTP 调用路径，在 route 选择、方言适配、fallback 与 telemetry 上提供强控制，而对黑盒 agent 路径则只保留边界化的外部治理与观测能力
