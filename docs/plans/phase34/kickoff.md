---
author: claude
phase: 34
slice: cognitive-router
status: draft
depends_on: [docs/roadmap.md, docs/plans/phase33/closeout.md, docs/plans/phase34/context_brief.md]
---

> **TL;DR**: Phase 34 将静态 executor-name 路由升级为基于能力矩阵的 Strategy Router，实现 Claude XML + Codex FIM 两个 concrete dialect adapter，并建立"主力不可用→fallback 到备选通道"的最简二元降级。全量降级策略和 Gemini Context Caching 延后。

# Phase 34 Kickoff — 认知模型路由与降级兜底网格

## 基本信息

- **Phase**: 34
- **Primary Track**: Execution Topology
- **Secondary Track**: Evaluation / Policy
- **Phase 名称**: Cognitive Router + Dialect Framework + Binary Fallback

---

## 前置依赖与现有基础

Phase 31-33 checkpoint：
- `ExecutorProtocol` 统一接口 + `resolve_executor()` 注册机制
- `Planner v0` 规则驱动 1:N 拆解 + `SubtaskOrchestrator` DAG 并发
- `ReviewGate` + 单次 retry feedback loop
- `DialectAdapter` 协议已定义（`executor.py:39-42`），`PlainTextDialect` + `StructuredMarkdownDialect` 已实现
- `RouteSpec` 包含 `dialect_hint`、`model_hint`、`capabilities`、`taxonomy`

**当前路由局限**（`router.py`）：
- `select_route()` 是纯静态映射：executor name → hardcoded RouteSpec
- `BUILTIN_ROUTES` 只有 5 条固定路由，没有能力匹配逻辑
- 没有 fallback 机制——选中的路由不可用就直接 fail
- `DialectAdapter` 虽已有协议但只用于 prompt formatting，不参与路由决策

---

## 目标

1. **Strategy Router 升级**：`select_route()` 从"executor name → route"静态映射升级为基于能力矩阵的匹配——根据 TaskCard 的需求（capability tier、model hint、执行器族）从候选路由池中选择最优路由。
2. **Concrete Dialect Adapters**：实现 Claude XML adapter 和 Codex FIM adapter，验证 dialect 框架的端到端流转。
3. **Binary Fallback**：当首选路由的 executor 执行失败时，自动 fallback 到预定义的备选路由重新执行。v0 只做一次 fallback，不做链式降级。

---

## 非目标

- ❌ Gemini Context Caching adapter——需要真实 Google API 集成，延后
- ❌ 全量降级矩阵（多级链式降级、认知角色替补策略）——延后至 Phase 35
- ❌ 动态能力协商（运行时探测 provider 健康状态/延迟/成本）——延后
- ❌ Provider Connector 层集成（new-api / TensorZero 实际部署）——延后，本轮只建立接口契约
- ❌ ReAct 风格降级转化（无 tool calling 时降级为纯文本引导）——延后
- ❌ 多执行器竞速 / Debate Topology

---

## 设计边界

### Strategy Router 边界

**核心改造**：`select_route()` 升级为两阶段选择。

**阶段 1：候选路由生成**
- 维护一个可扩展的路由注册表 `RouteRegistry`（替代当前 `BUILTIN_ROUTES` 硬编码 dict）
- 路由注册表支持从配置文件或代码注册新路由
- 每条路由声明自己的 `capabilities`、`taxonomy`、`dialect_hint`、`model_hint`

**阶段 2：能力匹配**
- TaskCard 或 TaskState 携带的需求（executor_type、route_hint、constraints）作为查询条件
- `select_route()` 从注册表中筛选满足条件的候选路由，按优先级排序
- 优先级规则（v0，规则驱动）：
  1. 精确匹配 executor_name / route_hint → 最高优先
  2. 匹配 executor_family + execution_site → 次优先
  3. 匹配 capability tier（execution_kind、supports_tool_loop）→ 通用匹配
- 未匹配到任何路由 → 返回 `local-summary` 作为最终兜底

**与编排层的协作**：Strategy Router 在编排层做策略决策，`select_route()` 是其代码入口。能力下限断言（如"禁止弱模型做架构规划"）作为过滤规则在候选筛选阶段执行。

### Dialect Adapter 边界

**框架扩展**：在现有 `DialectAdapter` 协议基础上，新增 `dialect_adapters/` 子模块。

**Claude XML Adapter**：
- 触发条件：`dialect_hint == "claude_xml"` 或 `model_hint` 含 "claude"
- 行为：将 System Prompt 和 constraints 包裹进 `<instructions>`、`<context>`、`<task>` 等 XML 标签
- 保留原始语义，不修改 prompt 内容，只做结构重组

**Codex FIM Adapter**：
- 触发条件：`dialect_hint == "codex_fim"` 或 `model_hint` 含 "codex"/"deepseek-coder"
- 行为：剥离对话上下文，将 task goal + code context 重组为 `<fim_prefix>...<fim_suffix>` 结构
- 仅在 `execution_kind == "code_execution"` 时激活

**不做**：Gemini Context Caching（需要真实 API 集成）、ReAct 纯文本降级（延后）。

### Binary Fallback 边界

**核心机制**：在 `run_task()` 的执行阶段，当 executor 返回 `status == "failed"` 时，触发一次 fallback。

**Fallback 规则**（v0，静态配置）：
- 每条 RouteSpec 新增可选字段：`fallback_route_name: str`
- 当执行失败时，如果 `fallback_route_name` 非空，自动使用该路由重新执行
- fallback 只执行一次，不做链式降级
- fallback 执行的 artifact 以 `fallback_` 前缀写入
- fallback 事件记录为 `task.execution_fallback`

**与 Review Feedback Loop 的关系**：
- Review retry（Phase 33）在 ReviewGate 失败时重试**同一 executor**
- Binary fallback（本轮）在 executor 本身失败时切换到**不同 executor**
- 两者互补，不冲突：先尝试 executor 执行 → 如果 executor 失败则 fallback → 如果 review 失败则 retry

**不做**：链式降级（A→B→C）、运行时健康探测、Provider 级别的通道切换（那是 Gateway 层的职责，本轮只建框架）。

---

## 完成条件

1. `RouteRegistry` 替代 `BUILTIN_ROUTES`，支持注册/查询/优先级排序
2. `select_route()` 从静态映射升级为基于注册表的能力匹配
3. Claude XML adapter 实现并通过 prompt 格式化验证
4. Codex FIM adapter 实现并通过 prompt 格式化验证
5. RouteSpec 新增 `fallback_route_name`，executor 失败时触发一次 fallback
6. fallback 执行的 artifact 和 event 按约定写入
7. 所有现有测试通过（回归安全）
8. 新增测试覆盖：RouteRegistry 查询/优先级、dialect adapter 格式化、fallback 触发/artifact/event

---

## Slice 拆解

| Slice | 目标 | 关键文件 | 风险评级 |
|-------|------|----------|----------|
| S1: RouteRegistry + Strategy Router | 路由注册表 + 能力匹配选路 | 改 `router.py`，改 `models.py`（RouteSpec 扩展） | 中 (影响 2 / 可逆 2 / 依赖 2 = 6) |
| S2: Dialect Adapters | Claude XML + Codex FIM 两个 concrete adapter | 新建 `dialect_adapters/`，改 `executor.py` | 低 (影响 1 / 可逆 1 / 依赖 2 = 4) |
| S3: Binary Fallback + 集成 | executor 失败 → fallback 路由 + artifact/event | 改 `orchestrator.py`，改 `models.py` | 中 (影响 2 / 可逆 2 / 依赖 2 = 6) |

### 依赖关系

```
S1 (RouteRegistry + Strategy Router)
  ├──→ S2 (Dialect Adapters)  [需要注册表支持 dialect_hint 查询]
  └──→ S3 (Binary Fallback)    [需要注册表支持 fallback_route_name]
```

S2 和 S3 对 S1 有依赖但彼此独立，理论可并行，建议串行以控制带宽。推荐顺序 S1 → S2 → S3。

---

## 风险评估

### R1: router.py 改动影响面（中）
- **风险**：`select_route()` 被 `orchestrator.py` 的 `create_task()` 和 `run_task()` + `acknowledge_task()` 三处调用，改动签名或行为可能破坏全链路
- **缓解**：`RouteRegistry` 内部仍保留所有 `BUILTIN_ROUTES` 的等价路由，`select_route()` 保持相同的入参签名，只在内部从 dict 查找改为注册表查找。现有测试通过即证明回归安全
- **检验**：全量测试 + 现有 route 相关测试不变

### R2: Dialect adapter 与现有 prompt 格式的兼容性（低）
- **风险**：Claude XML adapter 重组 prompt 结构后，现有测试中对 prompt 内容的断言可能失败
- **缓解**：新 adapter 只在 `dialect_hint` 显式指定时激活，默认仍走 `plain_text` 或 `structured_markdown`，不影响现有路径
- **检验**：现有 prompt 格式测试全部通过

### R3: Fallback 与 SubtaskOrchestrator 的交互（中）
- **风险**：多卡场景下子任务执行失败触发 fallback，可能与 Review retry 产生交叉
- **缓解**：Fallback 在 executor 级别触发（`_execute_task_card` 返回 failed），Review retry 在 ReviewGate 级别触发。执行顺序为：executor → fallback（如果 executor failed）→ ReviewGate → retry（如果 review failed）。两层不交叉
- **检验**：新增集成测试覆盖单卡 fallback + 多卡场景下的 fallback 行为

---

## 风险评分

| 维度 | 评分 (1-3) | 说明 |
|------|-----------|------|
| 影响范围 | 2 | 改动 router 核心 + 新增 dialect 子模块 + orchestrator fallback 分支 |
| 可逆性 | 1 | RouteRegistry 可回退为 dict，fallback 可通过空 fallback_route_name 关闭 |
| 外部依赖 | 1 | 纯内部重构，不依赖外部服务或真实 API |
| 状态突变 | 1 | 不改变 TaskState 持久化结构 |
| 并发风险 | 1 | 路由选择是只读操作，fallback 在单卡串行路径中触发 |
| **总分** | **6/15** | **低风险**（低于 roadmap 预估的"高"，因为严格控制了 scope） |

---

## 与 roadmap 批注的对照

roadmap 标注 Phase 34 是"风险最高的 Phase"，建议分期。本 kickoff 严格遵循该建议：

- **本轮做**：Dialect 框架 + 2 个 concrete dialect（Claude XML + Codex FIM）+ 最简二元降级
- **延后到 Phase 35**：全量降级策略、Gemini Context Caching、ReAct 降级转化、动态健康探测
- **额外收获**：RouteRegistry 替代硬编码路由表，为 Phase 35 的多执行器注册和动态路由打下基础

## 与 concerns_backlog 的关系

- Phase 32 的 LibrarianExecutor state mutation 技术债：本轮不消化。Librarian 仍走单卡路径，不进入 fallback 分支。
- Phase 29 的 dialect 信息收集逻辑重复：本轮 **部分消化**——新的 dialect_adapters 子模块可以作为公共数据收集层的初步雏形，但完整提取延后到 Phase 35。
