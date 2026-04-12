---
author: claude
phase: 22
slice: taxonomy-aware-routing-baseline
status: draft
depends_on:
  - docs/plans/phase22/context_brief.md
  - docs/design/AGENT_TAXONOMY_DESIGN.md
---

**TL;DR**: Phase 22 分三个 slice 实现：① 在 models/capabilities 中定义 Taxonomy 元数据（system_role + memory_authority）；② 在 router 的 RouteSpec 中挂载 taxonomy 标签并为 5 条内置路由赋予默认值；③ 在 dispatch_policy 中新增 taxonomy guard，拦截角色/权限不匹配的派发。全程不引入 RBAC、不改变已有路由选择逻辑、不影响 local-path 默认行为。

# Design Decision: Phase 22

## 方案总述

Phase 22 将 `AGENT_TAXONOMY_DESIGN.md` 中定义的三维分类学（System Role / Execution Site / Memory Authority）在代码层落地。当前系统的路由决策完全基于 executor_family + execution_site + transport_kind 三元组，缺乏对接收端"身份"和"权限"的感知。本轮在不改变已有路由选择逻辑的前提下，为路由和调度增加 taxonomy 元数据声明与防御性校验，使系统能在派发时拦截角色或权限不匹配的情况。

Execution Site 维度已在现有 `RouteSpec.execution_site` 中有良好支撑，本轮不重复建设，聚焦 System Role 和 Memory Authority 两个新维度。

## 非目标

- 不引入分布式 RBAC / 鉴权系统
- 不改变 `select_route()` 的已有决策逻辑（executor_override → route_mode → configured → legacy）
- 不新增 Agent 实体或 executor 类型
- 不扩展 Canonical Promotion Authority 的运行时强制（保持在设计文档层面）
- 不引入动态 taxonomy 注册 / 发现机制
- 不修改已有测试的通过行为

## Slice 拆解

### Slice 1: Taxonomy 元数据定义

**目标**：在代码层定义 system_role 和 memory_authority 的可选值与数据结构。

**影响范围**：
- 修改 `src/swallow/models.py`
  - 新增 `SYSTEM_ROLES: tuple[str, ...]` 常量：`("orchestrator", "general-executor", "specialist", "validator", "human-operator")`
  - 新增 `MEMORY_AUTHORITIES: tuple[str, ...]` 常量：`("stateless", "task-state", "task-memory", "staged-knowledge", "canonical-write-forbidden", "canonical-promotion")`
  - 新增 `TaxonomyProfile` dataclass：`system_role: str, memory_authority: str`，带 `validate()` 方法检查值合法性
- 修改 `src/swallow/capabilities.py`
  - `CapabilityAssembly` 或 `RouteCapabilities` 级别可选挂载 `TaxonomyProfile`（具体见 Slice 2 确定挂载点后回填）
- 新增测试 `tests/test_taxonomy.py`
  - TaxonomyProfile 合法值 → pass
  - TaxonomyProfile 非法 system_role → raise
  - TaxonomyProfile 非法 memory_authority → raise

**风险评级**：
- 影响范围: 1（新增定义，不改已有逻辑）
- 可逆性: 1（纯新增，删除即回滚）
- 依赖复杂度: 1（无外部依赖）
- **总分: 3 — 低风险**

**依赖**：无前置依赖。

**验收条件**：
- `TaxonomyProfile` 可实例化并校验
- 合法值和非法值测试通过
- 不影响任何已有测试

---

### Slice 2: RouteSpec Taxonomy 挂载

**目标**：为每条路由声明其 taxonomy profile，使路由选择结果携带身份信息。

**影响范围**：
- 修改 `src/swallow/router.py`
  - `RouteSpec` 新增字段 `taxonomy: TaxonomyProfile`
  - 5 条 `BUILTIN_ROUTES` 赋予默认 taxonomy：
    - `local-codex`: `general-executor / task-state`
    - `local-mock`: `general-executor / task-state`
    - `local-note`: `specialist / task-memory`
    - `local-summary`: `general-executor / task-state`
    - `mock-remote`: `general-executor / task-state`
  - `RouteCapabilities.to_dict()` 包含 taxonomy 信息
- 修改 `src/swallow/models.py`
  - `TaskState` 新增字段 `route_taxonomy_role: str = ""` 和 `route_taxonomy_memory_authority: str = ""`
- 修改 `src/swallow/orchestrator.py`
  - `select_route()` 返回后，在路由字段赋值处增加 taxonomy 字段的传播：`state.route_taxonomy_role = route.taxonomy.system_role` 等
- 新增/扩展测试
  - select_route 返回的 RouteSelection 包含正确的 taxonomy
  - TaskState 路由字段包含 taxonomy 信息
  - 已有路由测试不破

**风险评级**：
- 影响范围: 2（router + models + orchestrator 赋值）
- 可逆性: 1（新增字段，删除即回滚）
- 依赖复杂度: 2（依赖 Slice 1 的 TaxonomyProfile）
- **总分: 5 — 中低风险**

**依赖**：Slice 1 必须先完成（TaxonomyProfile 定义）。

**验收条件**：
- 每条内置路由有正确的默认 taxonomy
- TaskState 在路由选择后携带 taxonomy 字段
- 已有 146+ 测试全部通过

---

### Slice 3: Dispatch Taxonomy Guard

**目标**：在 dispatch 阶段增加 taxonomy 防御性校验，拦截角色或权限不匹配的派发。

**影响范围**：
- 修改 `src/swallow/dispatch_policy.py`
  - 新增 `validate_taxonomy_dispatch(task_state, contract) -> PolicyResult`
  - 校验规则（初始版本，保守策略）：
    1. **Validator 不接收写入性任务**：如果 route_taxonomy_role == "validator" 且 contract 的 `next_steps` 包含写入性关键词（"write", "modify", "create", "edit", "delete"），返回 blocked
    2. **Canonical-Write-Forbidden 不接收 promotion 任务**：如果 route_taxonomy_memory_authority == "canonical-write-forbidden" 且 contract 的 goal 包含 "promot" 关键词，返回 blocked
    3. **Stateless 不接收需要 task-state 的任务**：如果 route_taxonomy_memory_authority == "stateless" 且 contract 需要读取 task state artifacts（context_pointers 非空），返回 blocked
  - 这些规则是初始的保守启发式，未来可参数化为策略配置
- 修改 `src/swallow/orchestrator.py`
  - 在 `_evaluate_dispatch_for_run()` 中，继 Phase 21 的 `validate_handoff_semantics()` 之后，调用 `validate_taxonomy_dispatch()`
  - 校验失败同样生成 `DispatchVerdict(action="blocked")`
- 新增测试
  - validator 角色接收写入性 contract → blocked
  - canonical-write-forbidden 接收 promotion contract → blocked
  - general-executor 接收正常 contract → pass（不拦截）
  - 已有 local-path 默认行为不受影响（因为默认 taxonomy 是 general-executor / task-state）

**风险评级**：
- 影响范围: 2（dispatch_policy + orchestrator 调用点）
- 可逆性: 1（删除调用即回滚）
- 依赖复杂度: 2（依赖 Slice 2 的 taxonomy 字段传播）
- **总分: 5 — 中低风险**

**依赖**：Slice 2 必须先完成（TaskState 需要有 taxonomy 字段）。

**验收条件**：
- taxonomy 不匹配的派发被正确拦截
- 默认路由（general-executor / task-state）的正常任务不受影响
- 所有已有测试通过

---

## 实现顺序

```
Slice 1: TaxonomyProfile 定义 (models.py)
    ↓
Slice 2: RouteSpec taxonomy 挂载 (router.py + orchestrator.py)
    ↓
Slice 3: Dispatch Taxonomy Guard (dispatch_policy.py + orchestrator.py)
```

严格顺序依赖：1→2→3。

## Branch Advice

- 当前分支: `main`
- 建议操作: 新建分支
- 建议分支名: `feat/phase22-taxonomy-aware-routing`
- 理由: 3 个 slice 紧密关联，单分支单 PR
- PR 策略: 单 PR 合入，总风险可控

## Phase-Guard 检查

- [x] 方案未越出 context_brief 定义的 goals（仅做 runtime validation & routing gate）
- [x] 方案未触及 non-goals（无 RBAC、无动态注册、无新 executor）
- [x] 已有路由的默认 taxonomy 保证向下兼容（general-executor / task-state 不触发任何拦截）
- [x] Slice 数量 = 3，在建议上限 ≤5 内
- 无 `[SCOPE WARNING]`
