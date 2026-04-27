# Provider Router & Negotiation

> **Design Statement**
> Provider Router 把上层(Orchestrator)已经做过策略判断的逻辑能力需求,映射到物理模型路由上。它服务于 Path A 和 Path C(Path C 内部多次调用 Path A,治理穿透),不参与 Path B。它在 route 选择、方言适配、fallback 与 telemetry 上提供强控制——**仅此而已**。

> 项目不变量见 → `INVARIANTS.md`(权威)。三条调用路径定义见 `INVARIANTS.md §4`。

---

## 1. Provider Router 做什么 / 不做什么

### 1.1 做什么

```python
def resolve(logical_request: LogicalCallRequest) -> PhysicalCallPlan:
    # 1. 接收逻辑能力需求(由 Orchestrator 组装好的)
    # 2. 查 route_registry,过 capability boundary guard(unsupported_task_types)
    # 3. 按 quality_weight 排序候选 routes
    # 4. 选第一个 healthy 的 route,返回 PhysicalCallPlan(provider, endpoint, payload_template, fallback_chain)
```

| 职责 | 说明 |
|---|---|
| 接收逻辑需求 | 上层传入 route hint / dialect hint / capability 需求 |
| 选择物理 route | 从 `route_registry` 中匹配最合适的物理通道 |
| 方言适配 | 把统一语义请求翻译成目标模型的最优输入格式 |
| Fallback 执行 | 物理通道不可用时沿降级链切换 |
| Telemetry 回收 | 写入 `event_telemetry` 与 `route_health` 供 Meta-Optimizer 消费 |

### 1.2 不做什么

以下决策属于 Orchestrator,Provider Router **不得越权**:

- 任务域判断(工程 / 研究 / 日常)
- 风险等级判断
- 任务复杂度评估
- 是否进入 `waiting_human` 的决策
- 高层任务分解与执行器角色分派
- 失败重试是否进行 / 重试次数(只做单次 fallback chain 切换,不做语义级 retry)
- 是否切换 Path A / B / C(那是 Strategy Router 的职责)

`test_path_b_does_not_call_provider_router`(INVARIANTS §9 守卫)从代码层确保 Path B 不调用 Provider Router。Path C 通过 Path A 间接调用,不绕过。

---

## 2. 三条调用路径下的 Router 角色

| 路径 | Router 是否参与 | 控制粒度 |
|---|---|---|
| **Path A**(controlled HTTP) | ✅ 主战场 | route selection + dialect + fallback + telemetry |
| **Path B**(agent black-box) | ❌ 不参与 | agent 内部决定模型,Swallow 不直接控制 |
| **Path C**(specialist internal) | ✅ 穿透 | Specialist 内部多次调用 Path A,每次都经过 Router |

Path C 穿透规则:Specialist 不允许在内部维护自己的 provider 连接、自己的方言适配或自己的 fallback 链。它发出的每次 LLM 调用都是一次 Path A 调用,完整经过 `resolve()`。

`test_specialist_internal_llm_calls_go_through_router` 守卫验证 Specialist 代码路径中没有绕过 Router 的直连。

---

## 3. 四条设计准则

| 准则 | 含义 |
|---|---|
| **逻辑身份 ≠ 物理身份** | 系统请求"强推理"或"长上下文"等逻辑能力,Router 翻译为物理 endpoint |
| **能力语义 ≠ 供应商语义** | Swallow 内部词汇(task family / capability tier / dialect hint)与供应商产品命名互不混淆 |
| **聚合器是上游,不是网关** | OpenRouter / AiHubMix / new-api 等是连接层,不是 Swallow 的架构中心 |
| **本地模型是一等公民** | 本地 HTTP 兼容接口与云端 API 共享同一套 route metadata 体系 |

---

## 4. 推迟绑定原则

### 4.1 上层传入的标准契约

```python
class LogicalCallRequest:
    capability_tier: str           # "strong_reasoning" / "long_context" / ...
    task_family: str               # 用于 telemetry 关联
    dialect_hint: str | None       # "claude_xml" / "plain_text" / "fim" / None
    executor_id: str               # 用于 capability boundary check
    prompt_ingredients: PromptBundle    # 结构化 prompt 片段
    context_assembly: AssembledContext  # 已组装好的上下文
    # 不传入厂商专有 payload
```

### 4.2 推迟绑定

直到实际发起网络调用的最后一刻,才将统一语义绑定到具体 provider / endpoint / payload。

应用层禁止出现 `if provider == "openai":` 之类的硬编码。`grep` 守卫检测此类分支。

---

## 5. 方言适配

### 5.1 什么是方言适配器

把统一语义请求翻译成特定模型 / 后端更擅长接收的格式的翻译层。当前已知的方言:

- Claude XML 风格
- Plain Text 风格
- FIM(Fill-in-the-Middle)风格

### 5.2 它解决什么

同一任务意图在不同模型上的最优输入格式不同;同一上下文在不同后端的 payload 结构不同。

### 5.3 作用域边界

**方言适配器只服务于 Path A / Path C**(它们的本质都是 controlled HTTP)。它不是:

- Path B 的 prompt 控制器(Path B 由 agent 内部决定)
- Orchestrator 的替代品(它不做策略决策)
- 跨任务的全局 prompt 模板(那是 Harness 的 skills 层)

---

## 6. Route 选择策略

### 6.1 Route Metadata

每条 route 的元数据由 `route_registry` 表持久化(见 DATA_MODEL.md §3.4)。核心字段:

| 字段 | 说明 |
|---|---|
| `model_family` / `model_hint` | 模型族与具体模型提示 |
| `dialect_hint` | 方言适配器标识 |
| `backend_kind` | http / cli / local |
| `transport_kind` | 传输方式 |
| `fallback_route_id` | 降级目标 |
| `quality_weight` | operator 可调整的质量权重(1.0=正常,<1.0=降权,0.0=禁用) |
| `unsupported_task_types` | 该 route 明确不支持的任务类型列表 |
| `cost_profile` | 成本、延迟与可靠性画像 |

### 6.2 选择算法

```python
def resolve(req: LogicalCallRequest) -> PhysicalCallPlan:
    # 第一层:capability boundary guard(硬过滤,零 LLM 成本)
    candidates = [r for r in route_registry
                  if req.task_family not in r.unsupported_task_types]

    # 第二层:健康过滤
    candidates = [r for r in candidates if route_health[r].status != "down"]

    # 第三层:能力 tier 匹配
    candidates = [r for r in candidates
                  if matches_capability(r, req.capability_tier)]

    # 第四层:按 quality_weight 排序(quality_weight=0 等价于完全淘汰)
    candidates.sort(key=lambda r: -r.quality_weight)
    candidates = [r for r in candidates if r.quality_weight > 0]

    if not candidates:
        raise NoRouteAvailable(req)

    return build_plan(candidates[0], req, fallback_chain=candidates[1:])
```

### 6.3 `unsupported_task_types` 与 `quality_weight` 的合并规则

权威定义:

> **`unsupported_task_types` 是硬过滤(出局),`quality_weight` 是软排序(降权)。先硬过滤再软排序。`quality_weight = 0.0` 等价于把所有 task_type 都加进 `unsupported_task_types` 的语法糖。**

不允许实现层把这两个字段当成"二选一"或"AND/OR 任意组合"——顺序固定:**第一层硬过滤 → 第二层健康 → 第三层能力 tier → 第四层 quality_weight 排序**。

### 6.4 能力画像(远期方向)

为每条 route 维护任务维度的能力评分(reasoning / code_edit / long_context),用于多候选时的评分匹配,替代纯 quality_weight 排序。

维护原则:

- **隐式信号优先**:从 `event_telemetry` 自动聚合(成功率、review pass rate、retry 次数、成本)
- **外部知识摄入**:官网/文档对模型能力边界的描述通过 `swl ingest --source model-intel` 进入 staged knowledge,operator 确认后 promote 为 route metadata 更新提案
- **Proposal over mutation**(P7):画像更新以提案形式产出,operator 确认后通过 `apply_proposal` 应用,不自动突变
- **Meta-Optimizer 消费**:Meta-Optimizer 扫描遥测后可产出能力画像更新提案

当前 phase 不实现,但 schema 不阻塞此扩展。

### 6.4.1 聚合 → proposal → 应用,不允许直接修改

从遥测聚合产生的画像更新**只能产生 proposal artifact**,不能直接修改 `route_registry.quality_weight` 或其他 metadata 字段。完整路径:
```
event_telemetry 聚合
    → Meta-Optimizer / 画像聚合器 产出 proposal artifact
    → operator 审阅
    → operator 通过 apply_proposal 应用
    → route_registry 更新
```

理由:聚合本身是一种推断,可能产生误判(短期波动、特定任务族的偶发失败)。把"聚合"和"应用"分离,确保短期遥测异常不会自动突变长期路由策略。这是 P7(Proposal over mutation)在 Provider Router 域的具体体现。

`test_route_metadata_writes_only_via_apply_proposal` 守卫测试验证 `route_registry` 的 metadata 字段写入路径只来自 `apply_proposal`(`route_health` 表的 append-only 写入不在此约束内,见 §1.1)。
---

## 7. Fallback 与降级

### 7.1 Provider Router 处理的 fallback 范围

- 物理通道不可用(HTTP 429 / timeout / 5xx)
- route health 异常
- 预定义 `fallback_route_id` 链切换

它**不**独立决定:

- 是否允许弱模型承担高风险任务(那是 Strategy Router 的能力下限断言)
- 是否挂起到 `waiting_human`(那是 Review Gate)
- 是否缩小任务粒度(那是 Planner)

### 7.2 降级优先级

1. **同 path 内降级优先**——先在 Path A 内切换到 fallback route
2. **不跨 path 自动切换**——Path A 全链路不可用时,Router 返回失败,由 Orchestrator 决定是否降级到 Path B 或挂起
3. **Review 校准信任**——降级后产出信任度由 Review Gate 处理,不由 Router 决定

### 7.3 Degraded Telemetry

所有降级事件显式记录到 `event_telemetry`:

```
{
  "degraded": true,
  "original_route": "<route_id>",
  "fallback_route": "<route_id>",
  "task_family": "<family>",
  "logical_capability": "<tier>",
  "physical_route": "<route_id>",  # 实际使用的 route
  "error_code": "<code>",
}
```

---

## 8. Swallow Gateway Core vs Provider Connector Layer

| 层 | 持有者 | 职责 |
|---|---|---|
| **Swallow Gateway Core**(自建) | Swallow | route resolution、dialect adapters、fallback semantics、telemetry semantics |
| **Provider Connector Layer**(可选上游) | new-api / OpenRouter / AiHubMix 等 | 渠道管理、key 管理、协议兼容、格式互转 |

Swallow 保留 route identity、routing semantics、fallback semantics 与 telemetry semantics 的核心控制权,**不坍缩为某个聚合器的薄封装**。

---

## 9. 可观测性要求

`event_telemetry` 不能只停留在 HTTP 状态码 / QPS / token usage / latency。必须与任务语义绑定:

| 观测维度 | 价值 |
|---|---|
| 哪类 task family 上某 route 最不稳定 | 帮助 Meta-Optimizer 做战略判断 |
| 哪类 fallback 最常发生 | 识别系统性通道问题 |
| 哪类 degraded 结果最容易触发 review failure | 帮助 Strategy Router 调整能力下限断言 |

---

## 10. 与其他文档的接口

| 对接文档 | 接口关系 |
|---|---|
| `INVARIANTS.md` | 三条路径定义、写权限矩阵的权威 |
| `DATA_MODEL.md` | `route_registry` / `route_health` / `event_telemetry` 物理 schema |
| `ORCHESTRATION.md` | Strategy Router(在 Orchestrator 内)做策略判断后,传入逻辑需求;Router 返回执行结果与 telemetry |
| `HARNESS.md` | Harness 提供执行环境,Router 提供物理路径选择 |
| `EXECUTOR_REGISTRY.md` | executor 与 Path 的映射;HTTP Executor 是 Router 的主要客户 |
| `SELF_EVOLUTION.md` | Meta-Optimizer 只读消费 route telemetry,产出优化提案 |

---

## 附录 A:Anti-Patterns

| 反模式 | 说明 |
|---|---|
| **方言 = 通用 prompt 控制** | 把方言适配器误写成 Path B 的内部 prompt 控制器 |
| **Router 越权** | Router 接管任务域判断、复杂度评估或 waiting_human 决策 |
| **聚合器中心化** | 让 new-api / OpenRouter 成为架构中心,Swallow 退化为薄封装 |
| **无差别硬降级** | fallback 逻辑变成"任何情况都自动降级",不经 Orchestrator 确认 |
| **Specialist 直连 Provider** | Specialist 内部维护自己的 provider 连接,绕过 Router(违反 INVARIANTS §4 Path C) |
| **Path B 调用 Router** | Path B executor 试图通过 Router 选择模型(违反 INVARIANTS §4 Path B) |
| **`unsupported_task_types` 与 `quality_weight` 混用** | 把两个字段当成可任意组合的过滤器,不遵循 §6.3 的顺序 |
| **Provider 硬编码** | `if provider == "xxx"` 类型的分支出现在应用层 |
