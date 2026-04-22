# 模型路由与能力协商 (Provider Router)

> **Design Statement**
> Provider Router 负责把上层已经做过策略判断的逻辑能力需求，映射到物理模型路由上。它主要服务于受控 HTTP 调用路径，在 route 选择、方言适配、fallback 与 telemetry 上提供强控制；对黑盒 agent 路径只保留边界化的外部治理与观测能力。它不是全能 negotiator，也不是编排层的替代品。

> 全局原则见 → `ARCHITECTURE.md §1`。两条调用路径的定义见 → `ARCHITECTURE.md §4`。

---

## 1. Gateway 设计哲学

### 1.1 核心职责

| 职责 | 说明 |
|---|---|
| 接收逻辑需求 | 上层（编排层）已完成策略判断后，传入 route hint / dialect hint / capability 需求 |
| 选择物理 route | 从 Route Registry 中匹配最合适的物理通道 |
| 方言适配 | 把统一语义请求翻译成目标模型的最优输入格式 |
| Fallback 执行 | 物理通道不可用时沿降级链切换 |
| Telemetry 回收 | 记录 route 维度的遥测数据供 Meta-Optimizer 消费 |

### 1.2 不承担的职责

以下决策属于编排层，Provider Router 不应越权：

- 任务域判断（工程 / 研究 / 日常）
- 风险等级判断
- 是否进入 `waiting_human` 的最终裁决
- 高层任务分解与执行器角色分派

### 1.3 四条设计准则

| 准则 | 含义 |
|---|---|
| **逻辑身份 ≠ 物理身份** | 系统请求"强推理"或"长上下文"等逻辑能力，网关负责翻译为物理 endpoint |
| **能力语义 ≠ 供应商语义** | Swallow 内部词汇（task family / capability tier / dialect hint）与供应商产品命名互不混淆 |
| **聚合器是上游，不是网关** | OpenRouter / AiHubMix / new-api 等是连接层，不是 Swallow 的架构中心 |
| **本地模型是一等公民** | 本地 HTTP 兼容接口、CLI 路径与云端 API 共享同一套 route metadata 体系 |

---

## 2. Controlled HTTP Path vs Black-box Agent Path

这是 Provider Router 最关键的作用域边界。

### 2.1 受控 HTTP 路径——Provider Router 的主战场

```
TaskState + RetrievalItems → Router → route_model_hint / dialect_hint → HTTPExecutor → HTTP API
```

Provider Router 在此路径上精细控制：route selection、model 字段映射、dialect / request formatting、payload shape、fallback chain、degraded telemetry。

### 2.2 黑盒 agent 路径——边界化治理

```
TaskState → CLIAgentExecutor / external agent → agent 内部模型处理 → model/provider
```

Agent 内部的模型选择、prompt 组织、工具调用和 subagent 行为不受 Provider Router 直接控制。Swallow 转向控制任务边界、rules / skills / subagents、input/output contract、升级/降级策略、成本与行为观测。

**结论**：方言适配器主要服务于受控 HTTP path；黑盒 agent path 主要依赖 executor governance。

---

## 3. 统一语义与推迟绑定

### 3.1 上层传入网关的标准契约

- 逻辑 route hint
- dialect hint
- executor / backend selection result
- 结构化 prompt ingredients
- context assembly output

不传入厂商专有 payload。

### 3.2 推迟绑定原则

直到实际发起网络调用的最后一刻，才将统一语义绑定到具体 provider / endpoint / payload 结构。应用层不应出现 `if provider == "xxx"` 之类的硬编码。

---

## 4. 方言适配的正确定位

### 什么是方言适配器

把统一语义请求翻译成特定模型/后端更擅长接收的格式的翻译层。已有适配器包括 Claude XML 风格、Plain Text 风格、FIM 风格。

### 它解决什么

同一任务意图在不同模型上的最优输入格式不同；同一上下文在不同后端的 payload 结构不同。

### 它的作用域

限定在 **HTTPExecutor 能直接控制的调用路径**。它不是所有 agent 内部 prompt 的统一控制器，也不是编排层的替代品。

---

## 5. Route 选择策略

### 5.1 Route Metadata

每条 route 携带以下元数据：

| 字段 | 说明 |
|---|---|
| model family / model hint | 模型族与具体模型提示 |
| dialect hint | 方言适配器标识 |
| backend kind | HTTP / CLI / local |
| transport kind | 传输方式 |
| fallback route | 降级目标 |
| cost / latency / reliability traits | 成本、延迟与可靠性画像 |

### 5.2 选择关注点

1. 逻辑能力是否匹配
2. 物理 route 是否健康
3. 后端是否可用
4. 降级链是否存在
5. 该 route 属于 HTTP controlled path 还是 black-box agent path

### 5.3 编排层 vs 网关层的决策边界

| 决策 | 编排层 | 网关层 |
|---|---|---|
| 任务值不值得走高阶执行器 | ✅ | — |
| 应否降级任务粒度 | ✅ | — |
| 该不该进入 waiting_human | ✅ | — |
| 选定路径后如何发出请求 | — | ✅ |
| 失败后沿哪条 fallback 切换 | — | ✅ |
| 切换后如何记录 degraded telemetry | — | ✅ |

---

## 6. Graceful Degradation & Fallback

### 6.1 Provider Router 处理的 fallback 范围

- 物理通道不可用（HTTP 429 / timeout / 5xx）
- route health 异常
- 预定义 fallback route chain 切换

它**不**独立决定：是否允许弱模型承担高风险任务、是否挂起到 waiting_human、是否缩小任务粒度。这些由编排层裁决。

### 6.2 降级优先级

1. HTTP 内部降级优先——先在同类 HTTP 路径内切换
2. CLI / agent 兜底——受控 HTTP path 全链路不可用时再考虑
3. Review 校准信任——降级后产出信任度不自动等同于主路径产出

### 6.3 Degraded Telemetry

所有降级事件显式记录：`degraded` 标记、`original_route`、`fallback_route`、关联的 task family / logical model / physical route。

---

## 7. Swallow Gateway Core vs Provider Connector Layer

| 层 | 持有者 | 职责 |
|---|---|---|
| **Swallow Gateway Core**（自建） | Swallow | route resolution、dialect adapters、fallback semantics、telemetry semantics |
| **Provider Connector Layer** | new-api / OpenRouter / AiHubMix 等 | 渠道管理、key 管理、协议兼容、格式互转 |

Swallow 保留 route identity、routing semantics、fallback semantics 和 telemetry semantics 的核心控制权，不坍缩为某个聚合器的薄封装。

---

## 8. 可观测性要求

网关遥测不能只停留在 HTTP 状态码 / QPS / token usage / latency。更关键的是与任务语义绑定：

| 观测维度 | 价值 |
|---|---|
| 哪类 task family 上某 route 最不稳定 | 帮助 Meta-Optimizer 做战略判断 |
| 哪类 fallback 最常发生 | 识别系统性通道问题 |
| 哪类 degraded 结果最容易触发 review failure | 帮助编排层调整能力下限断言 |

---

## 9. 与其他层的接口

| 对接层 | 接口关系 |
|---|---|
| **Orchestrator** | 编排层做策略判断后，传入逻辑需求；网关层返回执行结果与 telemetry |
| **Harness** | Harness 提供执行环境，Provider Router 提供物理路径选择 |
| **State & Truth** | route / degraded / fallback 元数据记录到 Route Truth |
| **Self-Evolution** | Meta-Optimizer 只读消费 route telemetry，产出优化提案 |

---

## 附录 A：Anti-Patterns

| 反模式 | 说明 |
|---|---|
| **方言 = 通用 prompt 控制** | 把方言适配器误写成黑盒 agent 的内部 prompt 控制器 |
| **网关越权** | 网关层接管编排层的任务域判断或 waiting_human 裁决 |
| **聚合器中心化** | 让 new-api / OpenRouter 成为架构中心，Swallow 退化为薄封装 |
| **无差别硬降级** | fallback 逻辑变成"任何情况都自动降级"，不经编排层确认 |
| **路径不分** | 忽略 controlled HTTP path 与 black-box agent path 的根本差异 |
