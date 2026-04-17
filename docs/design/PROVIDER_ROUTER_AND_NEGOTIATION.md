# 模型路由与能力协商设计 (Provider Router & Capability Negotiation)

## 0. Gateway 设计哲学 (Gateway Design Philosophy)

本文档描述的模型路由与能力协商机制，是 Swallow 模型网关层（第 6 层）的实现方案。在进入具体设计前，以下五条原则锚定了网关层的长期设计边界：

### 0.1 逻辑模型身份 vs 物理路由身份

系统请求的是一种**逻辑能力**（如"强推理"、"长上下文"、"代码补全"），而非特定的 endpoint。同一逻辑能力可能经由多条物理通道到达（官方 API、聚合器、本地部署）。网关层的核心工作是维护这个映射关系，而不是把二者等同。

### 0.2 能力语义 vs 供应商语义

项目内部使用自己的能力词汇表（task family、capability tier）。供应商使用自己的产品命名和 API 结构。这两套词汇不应混淆。当供应商改名、重新打包产品、或调整 API 时，项目的内部语言不应被迫重写。网关层正是这两套词汇之间的翻译层。

### 0.3 聚合器是上游，不是网关本身

OpenRouter 等聚合器可以作为物理路由之一，但网关层不应在概念上坍缩为聚合器的薄封装。路由身份、策略语义、观测逻辑应由项目自主持有。

### 0.4 本地模型是一等公民

本地部署的模型（如 ollama 上的开源模型）应当和云端模型一样，经由同一个网关表面接入。它们的成本结构、延迟特性、能力天花板与云端不同，但这些差异应在路由元数据中体现，而非通过绕开网关的特殊通道处理。

### 0.5 可观测性服务于任务语义

纯粹的供应商流量监控（每分钟请求数、HTTP 错误率）是必要但不充分的。网关层的遥测应当关联**任务族标签**（planning / review / extraction / retrieval），这样 Meta-Optimizer 才能回答"哪类任务在哪条路由上表现最差"这样的战略性问题。

> 完整的架构哲学论述见 `GATEWAY_PHILOSOPHY.md`。

---

## 1. 核心定位：智能网关与方言翻译器

在多模型生态并存的时代，Swallow 系统的架构不能被单一的大模型供应商（Vendor Lock-in）所绑架。在第 6 层（模型接入与路由层），我们引入了区别于普通 API 转发网关的核心组件——**能力协商 器 (Capability Negotiator)** 与 **方言适配器 (Dialect Translators)**。

它的根本职责是：**承接上层统一的语义意图，将其智能分配至最具性价比的模型基座，并翻译为该模型能达到最高性能表现的“专属原生方言”。**

---

## 2. 统一语义描述 (Universal Semantic Description)

系统在编排层 (Orchestrator)、状态存储 (State Store) 和执行框架 (Harness) 中流转的所有数据结构，必须保持纯净和抽象。

*   **抵制硬编码**：坚决禁止在应用层代码中出现 `if openai:` 或写死特定模型的 API 结构。
*   **标准化契约**：工具 (Tools) 必须使用与平台无关的规范（例如标准的 JSON Schema 或 OpenAPI 规范）进行声明；系统 Prompt 与逻辑约束也必须采用纯粹的语义表达，而不是针对某个模型特调的模版。
*   **推迟绑定**：直到实际发包请求网络的最后一刻，统一语义才会流转到 Provider Router 进行具象化转换。

---

## 3. 下推差异化执行 (Push-Down Differentiated Execution)

当通用请求抵达路由层时，能力协商器会根据模型能力矩阵触发下推逻辑，通过专属适配器将请求“降维打击”为特定模型的原生形态：

### 3.1 Claude XML 适配器
*   **挑战**：Anthropic 的 Claude 模型对 JSON 和松散的文本指令敏感度较低，但在结构化 XML 标签体系下展现出极强的逻辑控制力。
*   **适配逻辑**：适配器会自动扫描上层传递的 System Prompt 和规则约束，将其转换包裹进对应的 `<thinking>`, `<scratchpad>`, `<instructions>` 等特定 XML 标签中。这能将 Claude 的长文 本遵循能力和减少幻觉的表现提升至最佳状态。

### 3.2 Gemini Context Caching 适配器
*   **挑战**：在涉及代码库跨文件重构或阅读整本长篇论文时，动辄百万 Tokens 的上下文会导致其他模型直接崩溃或面临天价账单。
*   **适配逻辑**：当路由层识别到本次任务依赖的对象体积庞大（例如通过 State Store 传递的 Context Pointers 指向了某个仓库的源码索引），且被分配给了 Gemini 模型时，适配器会自动拦截该请求。它不会拼接超长字符串，而是主动调用 Google 的 File API，建立并绑定 Context Cache URI，以极低成本和亚秒级首包延迟处理巨量上下文任务。

### 3.3 Codex / Code Model FIM 适配器
*   **挑战**：专注于写代码的模型（如开源的 DeepSeek Coder 或特定的 Codex 版本）往往不需要甚至不支持闲聊和系统 Prompt。它们期望的是纯粹的填空题。
*   **适配逻辑**：当需要直接修改文件或生成纯代码区块时，适配器会剥离所有的对话上下文记录，将业务意图重组为前缀（Prefix）与后缀（Suffix）结构的 `<fim_prefix>...<fim_suffix>` 专属标识，以此引导模型输出纯粹的中间代码段，极大降低输出的“废话率”。

---

## 4. 能力降级与通用代理兜底策略 (Graceful Degradation & Fallback)

在离线网络、成本压缩策略、主备切换，或系统默认的“三阶通用代理（Codex / Claude / Gemini）”因网络故障、速率限制（Rate Limit）暂时不可用时，系统必须具备强大的平滑降级与角色替补策略。

### 4.1 执行级通道降级矩阵 (Execution-Level Fallback Matrix)

当编排层 Strategy Router 已选定能力级别后，若首选物理通道不可用，网关层按以下规则切换备选通道。**网关层只处理”通道不通”，不判断”能力是否足够”**——后者由编排层的 Strategy Router 负责（见 `ORCHESTRATION_AND_HANDOFF_DESIGN.md` §2.1）。

1.  **施工执行通道不可用时**：
    *   **通道切换**：路由至备选代码补全通道（如 Claude Sonnet、DeepSeek Coder V2）。
    *   **上报编排层**：如果所有满足能力要求的通道均不可用，上报 Strategy Router 决定是否降级任务粒度或挂起至 `waiting_human`。
2.  **规划与审查通道不可用时**：
    *   **通道切换**：路由至备选强推理通道（如 GPT-4o）。
    *   **上报编排层**：如果所有强推理通道均不可用，上报 Strategy Router 触发 Review Gate 的人工介入流程。
3.  **知识整合通道不可用时**：
    *   **通道切换**：路由至备选长上下文通道（如 Claude Opus/Sonnet 128k+）。
    *   **上报编排层**：如果 Context Caching 不可用，上报 Strategy Router 决定是否启用上下文压缩策略。

> **设计边界**：策略性降级约束（如”禁止弱模型做架构规划”、”降级后加强 Review Gate 置信度阈值”、”要求 Librarian Agent 缩小 RAG 召回窗口”）已迁移至编排层。详见 `ORCHESTRATION_AND_HANDOFF_DESIGN.md` §2.1（Strategy Router）和 §2.4.1（降级场景下的 Review Gate 联动）。

### 4.2 ReAct 风格降级转化 (Tool Capability Fallback)
当能力协商器发现目标（或替补）模型不具备原生工具调用（Native Tool Calling / Structured Outputs）能力时：
1.  **动态转化**：它会将抽象的 Tool Schema 在网关层实时渲染为 ReAct (Reasoning and Acting) 范式的纯文本引导语，并拼接到模型 Prompt 末尾（例如：“你可以使用以下工具，请按照 `Action: [tool_name]` 的格式输出”）。
2.  **强化解析**：在回包阶段，通过更鲁棒的正则表达式与输出流截断机制，在网关层将纯文本还原为标准的内部工具调用意图，确保即使在开源小模型上，系统的核心执行流转也不会断链。提取校验**：在模型返回结果后，适配器不再依赖 SDK 解析 JSON，而是使用强化的正则表达式从输出文本流中提取意图。

### 4.2 降级事件审计与安全阻断
*   **审计记录**：这种降级行为会在系统事件流 (Event Log) 中被打上 `tool_execution_degraded` 标签，为后续的链路排障提供追踪依据。
*   **坚守 State Store 防线**：如果弱模型在降级状态下由于幻觉生成了非法的工具参数，系统也不必惊慌。由于上层的 State Store 具备严格的单一事实防线和 Schema 校验，非法的状态突变会在此处被直接丢弃并打回重试，或者挂起至 `waiting_human` 状态，形成系统级的安全兜底。

---

## 5. 技术选型参考 (Technology Selection Reference)

> 选型评估日期：2026-04-16。技术生态变化快，实施前应重新验证。

### 5.1 Provider Connector 层：双层架构（推理优化 + 渠道管理）

网关层的 Provider Connector 采用双层架构，分别解决两个正交问题：

#### 推理优化层：TensorZero

负责结构化推理追踪、A/B 实验和任务语义遥测。

| 维度 | TensorZero | 与 Swallow 哲学的契合 |
|---|---|---|
| 语言 | Rust（编译型二进制分发） | 无 pip/npm 供应链投毒风险 |
| 性能 | <1ms P99 @ 10k QPS | 网关层"应该透明"得到物理保障 |
| 结构化推理 | 内置 "function" 概念 | 天然对应 Swallow task family，遥测自带任务语义标签 |
| 配置方式 | 声明式 TOML，GitOps 驱动 | 与 Git Truth Layer 哲学一致 |
| A/B 实验 | 内置 variant 路由 | Strategy Router 可直接利用做模型对比 |
| 可观测性 | 结构化推理追踪 + 反馈收集 | 直接喂 Meta-Optimizer，无需额外 ETL |

#### 渠道管理层：new-api（自部署）

负责多渠道/多 key 统一管理、格式互转和额度控制。

| 维度 | new-api (QuantumNous) | 与 Swallow 哲学的契合 |
|---|---|---|
| 语言 | Go | 性能好，部署简单（单 Docker 容器） |
| 核心能力 | 多租户 API 管理 + OpenAI/Claude/Gemini 三格式互转 | 替代外部聚合器（AiHubMix 等），自持渠道管理权 |
| Key 管理 | 多渠道、多 key、额度分配、消费统计面板 | 运维可视化，成本治理 |
| 许可证 | AGPLv3 | 自用无传染性风险，对外提供服务需注意 |
| 格式转换 | 原生支持 Claude/Gemini 格式输出 | 比 TensorZero 更强的多格式覆盖 |

> 项目地址：https://github.com/QuantumNous/new-api

#### 两层协作关系

两者定位不同，可以共存也可以只用其一：

- **完整方案**：new-api 作为渠道管理网关（管理多 key、供应商接入、额度监控），TensorZero 叠加在其上做推理优化和遥测
- **轻量起步**：先只部署 new-api + Swallow 自建 thin wrapper，推理优化和遥测后续引入

**备选方案**：如果两者均不适用，**Portkey Gateway**（2026.3 完全开源，200+ LLM，50+ Guardrails，Node.js）是第三选择。

**明确排除**：
*   **LiteLLM**：2026.3 供应链投毒事件（PyPI 版本 1.82.7/1.82.8 泄露用户凭证）+ Python GIL 高并发瓶颈 + 运维重（需 Redis + PostgreSQL）。
*   **Kong AI Gateway**：企业级 API 管理工具，对 Swallow 当前规模而言过于重量级，定价模型不适合。

### 5.2 架构定位：Connector 而非 Gateway 本身

**核心原则：Provider Connector 层的所有组件都不是 Swallow 的第 6 层本身。**

Swallow 自持的网关逻辑（Route Resolver、Dialect Adapters、Execution Fallback 的上报机制）不应坍缩到任何外部产品中。Provider Connector 层的角色是**替代手写 SDK 集成的苦力活**，提供统一 API 调用 + 渠道管理 + 遥测，但路由决策权、语义转换、降级策略仍归 Swallow 自建层持有。

```
第 6 层  Swallow Gateway Core（自建）
  ├── Route Resolver         — 自建，消费 Strategy Router 的逻辑标识
  ├── Dialect Adapters       — 自建，Swallow 特有的语义转换（§3）
  ├── Execution Fallback     — 自建上报机制
  └── Provider Connector 层
        ├── new-api          — 渠道管理 + 格式互转 + 额度控制（自部署）
        └── TensorZero       — 推理优化 + 遥测收集器（可选叠加）

第 7 层  LLM Providers / Local Models (ollama, vLLM, etc.)
```

### 5.3 已知聚合器通道

以下聚合平台均提供 OpenAI 兼容接口，可在 Route Resolver 中作为物理通道注册。它们的定位是**上游供应商**，不是网关本身（§0.3）。自部署 new-api 后，这些平台可作为 new-api 的上游渠道接入，无需在 Swallow 侧逐一配置。

| 聚合器 | base_url | 接入方式 | 备注 |
|---|---|---|---|
| **AiHubMix** | `https://aihubmix.com/v1` | OpenAI SDK，改 base_url + api_key | 460+ 模型，按量付费，支持 Claude 原生 v1/messages 接口 |
| **OpenRouter** | `https://openrouter.ai/api/v1` | OpenAI SDK 兼容 | 广泛的开源/闭源模型覆盖 |

在 TensorZero 中，将上述聚合器声明为 OpenAI-compatible provider 即可接入，无需特殊适配。

### 5.4 外部治理壳：Cloudflare

Cloudflare 不参与网关内部逻辑，定位为**VPS 侧服务的外部流量入口治理壳**：

*   **域名反代**：通过 Cloudflare 为 VPS 上的 new-api / Open WebUI 统一入口域名，隐藏后端 IP
*   **边缘缓存**：对幂等的 RAG 检索类请求做 CDN 级缓存
*   **DDoS / Rate Limit**：保护 VPS 服务免受外部滥用
*   **可选 Tunnel**：通过 Cloudflare Tunnel 暴露本地 Control Center 供远程访问

**关键区分**：Cloudflare 只套在 VPS 前面，不套在本地 Swallow Runtime 前面。本地 Runtime 是 Cloudflare 的客户端（通过 HTTPS 访问 `api.yourdomain.com`），不是被它保护的服务端。

**部署拓扑概览**：

```
本地机器（编排侧）
  swl CLI → Swallow Runtime
    ├── Strategy Router (RouteRegistry)  — 纯本地，零延迟
    ├── Dialect Adapters                 — 纯本地
    └── HTTP 请求 → api.yourdomain.com

Cloudflare（治理壳）
  api.yourdomain.com → VPS
  chat.yourdomain.com → VPS

VPS 主机（服务侧）
  new-api (:3000)      → 渠道管理 + 格式互转
  TensorZero (:3001)   → 推理遥测（可选）
  Open WebUI (:3002)   → 探索性对话面板
```

> 完整部署拓扑详见 `INTERACTION_AND_WORKBENCH.md` §4.5。
> 治理壳哲学详见 `GATEWAY_PHILOSOPHY.md` §3。

### 5.5 技术栈演化预期

当前阶段以 Python 快速验证为主。初步成型后将向更轻量、高性能的方向改写（如 Go/Rust）。选型时已优先考虑与语言无关的集成方式（TensorZero 通过 HTTP API 接入，不绑定特定语言 SDK），确保技术栈迁移时 Provider Connector 层无需更换。
