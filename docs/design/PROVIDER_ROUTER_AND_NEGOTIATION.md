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

> 完整的架构哲学论述见下方 §0.6–§0.7。

### 0.6 需保护的架构边界（审查清单）

以下边界应在架构审查中显式检查：

| # | 边界 | 保护的是什么 | 违反的信号 |
|---|---|---|---|
| 1 | 任务语义 vs 供应商机制 | 项目不沦为供应商 API 的薄封装 | 上层代码出现 `if provider == "xxx"` |
| 2 | 路由执行 vs 战略评估 | 网关不变成运营与判断的混合体 | 网关层代码包含任务风险评估逻辑 |
| 3 | 项目知识 vs 网关配置 | 长期模型理解不随执行层变化而丢失 | 模型适用性评估写在路由配置文件里 |
| 4 | 内部路由身份 vs 外部网关产品 | 架构独立性 | 系统只能通过特定聚合器工作 |
| 5 | 逻辑能力 vs 物理通道 | 在真实世界最不稳定的地方保持灵活性 | 代码中 logical model 和 endpoint URL 1:1 绑定 |

### 0.7 常见失败模式（反模式速查）

- **供应商泄漏**：上游供应商的假设扩散到每个工作流中，使得变更代价高昂、战略控制薄弱。
- **聚合器当基础**：聚合器可以是有用的路由，但如果项目把它们误认为架构中心，就会依赖于一个自己无法控制的层。
- **路由与战略混淆**：一条快速、便宜或健康的路由不等于正确的战略选择。执行便利不应默默改写策略。
- **万物塞进一个注册表**：当路由元数据、战略评估、能力笔记和策略推理全部坍缩到一个配置表面时，项目会丧失区分"操作事实"和"积累判断"的能力。
- **网关隐藏太多**：抽象有用，直到它摧毁透明性。如果运维人员无法理解系统为什么那样做，架构就以另一种方式变得脆弱了。

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

### 4.2 降级事件审计与安全阻断
*   **审计记录**：这种降级行为会在系统事件流 (Event Log) 中被打上 `tool_execution_degraded` 标签，为后续的链路排障提供追踪依据。
*   **坚守 State Store 防线**：如果弱模型在降级状态下由于幻觉生成了非法的工具参数，系统也不必惊慌。由于上层的 State Store 具备严格的单一事实防线和 Schema 校验，非法的状态突变会在此处被直接丢弃并打回重试，或者挂起至 `waiting_human` 状态，形成系统级的安全兜底。

---

## 5. 技术选型参考 (Technology Selection Reference)

> 选型评估日期：2026-04-16。技术生态变化快，实施前应重新验证。

### 5.1 Provider Connector 层：渠道管理 + 自建遥测

#### 推理遥测层：Swallow 自建（替代 TensorZero）

推理遥测（token usage、route health、latency、task family 标签）由 Swallow 自建层承担，不引入外部服务依赖：

- **真实 token 成本**：HTTPExecutor 从每次 API 响应的 `usage` 字段（`prompt_tokens` / `completion_tokens`）捕获真实 token 数据，写入 event log，替代原有的静态成本估算
- **route health 遥测**：现有 Meta-Optimizer 消费 event log，分析路由健康度、失败指纹、降级趋势
- **task family 标签**：现有 executor event telemetry 已携带 `task_family` / `logical_model` / `physical_route` / `latency_ms` / `degraded` / `error_code`
- **存储**：写入 swallow 自身的 event log（SQLite，Phase 48 迁移目标），零外部依赖

> **TensorZero 评估结论（2026-04-19）**：TensorZero 强依赖 PostgreSQL，与项目"本地优先、零外部依赖"原则冲突。其核心价值（结构化遥测 + 真实成本数据）可由 Swallow 自建层覆盖。A/B 实验框架（variant 路由）留待未来 phase 评估是否自建或引入轻量替代。TensorZero 从"可选插件"降级为"暂不考虑"。

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

#### 协作关系

两者定位不同，可以共存也可以只用其一：

- **当前方案**：new-api 作为渠道管理网关（管理多 key、供应商接入、额度监控），遥测由 Swallow 自建层承担
- **未来扩展**：如需 A/B 实验框架，届时评估自建或引入轻量替代（不引入 PostgreSQL 依赖）

**备选方案**：如果 new-api 不适用，**Portkey Gateway**（2026.3 完全开源，200+ LLM，50+ Guardrails，Node.js）是第三选择。

**明确排除**：
*   **TensorZero**：强依赖 PostgreSQL，与项目零外部依赖原则冲突。核心遥测功能由 Swallow 自建层覆盖。
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
  ├── 自建遥测层             — HTTPExecutor 捕获 usage 字段，写入 event log
  └── Provider Connector 层
        └── new-api          — 渠道管理 + 格式互转 + 额度控制（自部署，SQLite）

第 7 层  LLM Providers / Local Models (ollama, vLLM, etc.)
```

### 5.3 已知聚合器通道

以下聚合平台均提供 OpenAI 兼容接口，可在 Route Resolver 中作为物理通道注册。它们的定位是**上游供应商**，不是网关本身（§0.3）。自部署 new-api 后，这些平台可作为 new-api 的上游渠道接入，无需在 Swallow 侧逐一配置。还可考虑：Together、Fireworks、DeepInfra 等

| 聚合器 | base_url | 接入方式 | 备注 |
|---|---|---|---|
| **AiHubMix** | `https://aihubmix.com/v1` | OpenAI SDK，改 base_url + api_key | 460+ 模型，按量付费，支持 Claude 原生 v1/messages 接口 |
| **OpenRouter** | `https://openrouter.ai/api/v1` | OpenAI SDK 兼容 | 广泛的开源/闭源模型覆盖 |

在 new-api 中，将上述聚合器声明为 OpenAI-compatible provider 即可接入，无需特殊适配。

### 5.4 部署拓扑与网络出口

> 完整运维配置（Docker Compose、WireGuard、Tinyproxy 等）见 `docs/deploy.md`。本节只描述架构拓扑与设计原则。

**核心原则：Docker Stack 在本地，VPS 只做出口代理。**

所有服务（new-api、Open WebUI）运行在课题组工作站上，Swallow Runtime 通过 `localhost:3000` 零延迟直连 new-api。VPS 瘦身为纯出口代理（WireGuard + Tinyproxy），仅承担让 API 请求从干净 IP 出去的职责。跨设备访问走 Tailscale 内网，不需要公网暴露任何 HTTP 服务。

**部署拓扑概览**：

```
课题组工作站（编排侧 + 服务侧）
  swl CLI → Swallow Runtime
    ├── Strategy Router (RouteRegistry)  — 纯本地，零延迟
    ├── Dialect Adapters                 — 纯本地
    ├── 自建遥测层                       — event log，SQLite
    └── HTTP → localhost:3000 (new-api)

  Docker Compose Stack:
    new-api    :3000  渠道管理 + 格式互转（SQLite）
      └── HTTPS_PROXY → VPS WireGuard 隧道
    Open WebUI :3002  探索性对话面板（SQLite）

VPS（纯出口代理，1C 512M）
  WireGuard Server :51820 (UDP)
  Tinyproxy        10.8.0.1:8888（仅绑 WG 内网）

Tailscale（跨设备访问）
  手机/iPad/笔记本 → 100.x.x.10:3002 (Open WebUI)
```

**三条数据通路**：
- **编排路径**（零延迟）：swl CLI → localhost:3000 (new-api) → HTTPS_PROXY → VPS Tinyproxy → LLM Providers
- **对话路径**（零延迟）：本地浏览器 → localhost:3002 (Open WebUI) → localhost:3000 (new-api) → 同上
- **跨设备路径**（Tailscale）：远程设备 → 100.x.x.10:3002 (Open WebUI) → 同上

**安全设计**：
- new-api 端口绑定 `127.0.0.1`，仅本机可达
- Open WebUI 绑定 `0.0.0.0:3002`，Tailscale 内网可达
- Tinyproxy 绑定 WG 内网接口（`Listen 10.8.0.1`），公网不可达
- VPS 防火墙仅开 SSH + WireGuard UDP

> 完整部署拓扑详见 `docs/deploy.md`。
> 治理壳哲学详见本文件 §0.6–§0.7。

### 5.5 技术栈演化预期

当前阶段以 Python 快速验证为主。初步成型后将向更轻量、高性能的方向改写（如 Go/Rust）。选型时已优先考虑与语言无关的集成方式（new-api 通过 HTTP API 接入，不绑定特定语言 SDK），确保技术栈迁移时 Provider Connector 层无需更换。

遥测层当前由 Swallow 自建（event log + Meta-Optimizer），Phase 48 迁移至 SQLite 后具备完整的本地查询能力。如未来需要 A/B 实验框架，届时评估是否自建 variant 路由或引入轻量替代，不引入 PostgreSQL 依赖。
