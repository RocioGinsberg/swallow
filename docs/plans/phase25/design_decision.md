---
author: claude
phase: 25
slice: taxonomy-driven-capability-enforcement
status: draft
depends_on:
  - docs/plans/phase25/context_brief.md
  - docs/design/AGENT_TAXONOMY_DESIGN.md
---

**TL;DR**: Phase 25 分三个 slice：① 建立 taxonomy→capability 的静态约束映射表；② 在 executor prompt 组装前执行硬裁剪，将受限字段降级；③ 裁剪事件记录与 inspect 可视化。不引入动态策略引擎，不改变 general-executor 默认行为。

# Design Decision: Phase 25

## 方案总述

当前系统的 capability 从 RouteSpec 直接流入 TaskState 再到 executor prompt，全程无 taxonomy 过滤。一个被分配为 `validator / stateless` 的实体，如果走了 `local-codex` 路由（理论上不应该，但 acknowledge 等强制路径可能绕过），仍然会在 prompt 中看到 `filesystem_access=workspace_write` 和 `supports_tool_loop=true`。

Phase 25 在 capability assembly 和 executor prompt 之间插入一层 **capability enforcement**：基于 TaskState 中的 taxonomy profile，对 RouteCapabilities 的特定字段执行降级（downgrade），确保执行引擎级别的最小权限。

设计选择：在 `run_task()` 中路由选择之后、executor 调用之前，对 `state.route_capabilities` 做 in-place 降级。这样 executor prompt 自然拿到的就是裁剪后的 capabilities，不需要改 executor 层代码。

## 非目标

- 不引入 OPA 或外部策略引擎
- 不修改 RouteSpec 定义或内置路由的默认 capabilities
- 不新增 executor 类型
- 不改变 `general-executor / task-state` 的默认行为（它是最宽松的，不触发任何降级）
- 不实现动态策略配置（映射表硬编码在代码中）
- 不裁剪 CapabilityManifest（profile_refs/skill_refs 等），只裁剪 RouteCapabilities 运行时字段

## Slice 拆解

### Slice 1: Capability Enforcement 映射表

**目标**：定义 taxonomy 维度到 capability 降级规则的静态映射。

**影响范围**：
- 新建 `src/swallow/capability_enforcement.py`
  - `CapabilityConstraint` dataclass：
    - `field: str` — RouteCapabilities 字段名
    - `max_value: str | bool` — 该 taxonomy 下允许的最大值
    - `reason: str` — 降级理由
  - `TAXONOMY_CAPABILITY_CONSTRAINTS: dict[str, list[CapabilityConstraint]]` — 映射表，key 为 `"{system_role}/{memory_authority}"` 或通配符 `"{system_role}/*"` / `"*/{memory_authority}"`
  - 初始规则（保守基线）：
    - `validator/*`：`filesystem_access → "workspace_read"`，`supports_tool_loop → False`
    - `*/stateless`：`filesystem_access → "none"`，`network_access → "none"`，`supports_tool_loop → False`
    - `*/canonical-write-forbidden`：（不降级 filesystem/network，但记录约束标记供审计）
    - `general-executor/task-state`：无约束（最宽松）
  - `enforce_capability_constraints(taxonomy_role, taxonomy_memory_authority, capabilities) -> tuple[dict, list[CapabilityConstraint]]`
    - 返回降级后的 capabilities dict 和实际触发的约束列表
    - 降级逻辑：对每个匹配的 constraint，如果当前值比 max_value "更宽松"，则降级
  - `_is_stricter(field, current_value, max_value) -> bool` — 比较函数
    - `filesystem_access` 排序：`none < workspace_read < workspace_write`
    - `network_access` 排序：`none < optional < required`
    - `bool` 字段：`False` 严于 `True`
- 新增 `tests/test_capability_enforcement.py`
  - validator + workspace_write → 降级为 workspace_read
  - stateless + workspace_read → 降级为 none
  - general-executor/task-state → 无降级
  - 多条约束同时触发 → 全部应用

**风险评级**：
- 影响范围: 1（新模块）
- 可逆性: 1（纯新增）
- 依赖复杂度: 1（无外部依赖）
- **总分: 3 — 低风险**

**依赖**：无前置依赖。

**验收条件**：
- 映射表与 AGENT_TAXONOMY_DESIGN.md 的权限定义一致
- enforce 函数正确降级并返回触发的约束
- 不影响任何已有测试

---

### Slice 2: Orchestrator Capability 裁剪集成

**目标**：在 `run_task()` 中路由选择之后、executor 调用之前，执行 capability enforcement。

**影响范围**：
- 修改 `src/swallow/orchestrator.py`
  - 在 `run_task()` 中，`state.route_capabilities` 赋值之后，调用 `enforce_capability_constraints()`
  - 将降级后的 capabilities 写回 `state.route_capabilities`
  - 将触发的约束列表暂存，供后续 event 记录使用
- 修改 `src/swallow/orchestrator.py`
  - 在 `acknowledge_task()` 中同样调用 enforce（acknowledge 强制走 local，但如果 taxonomy 仍是受限的，capabilities 应被降级）
- 新增/扩展测试
  - validator route 的 run_task → route_capabilities 中 filesystem_access 被降级
  - general-executor route 的 run_task → route_capabilities 不变
  - acknowledge 后的 route_capabilities 反映 taxonomy 约束

**风险评级**：
- 影响范围: 2（orchestrator run_task + acknowledge_task）
- 可逆性: 1（删除调用即回滚）
- 依赖复杂度: 2（依赖 Slice 1 + 已有 capability 流程）
- **总分: 5 — 中低风险**

**依赖**：Slice 1 必须先完成。

**验收条件**：
- executor prompt 中反映降级后的 capabilities
- 已有 general-executor 测试全部通过（capabilities 不变）
- 已有测试全部通过

---

### Slice 3: 裁剪事件与 Inspect 可视化

**目标**：记录 capability 裁剪事件，并在 CLI inspect 中展示。

**影响范围**：
- 修改 `src/swallow/orchestrator.py`
  - 当 enforce 触发了降级时，记录 event: `task.capability_enforced`
  - payload 包含：触发的约束列表、原始 capabilities、降级后 capabilities、taxonomy_role、taxonomy_memory_authority
- 修改 `src/swallow/cli.py`
  - inspect 命令的 Route And Topology 区域，在 taxonomy 行之后新增：
    - `capability_enforced: yes/no`
    - 如果 yes，显示降级的字段列表（如 `enforced: filesystem_access→workspace_read, supports_tool_loop→false`）
  - 信息来源：从 task event log 中查找最近的 `task.capability_enforced` event，或从 route_capabilities 与默认 capabilities 的 diff 推导
- 新增测试
  - validator route run → event log 包含 task.capability_enforced
  - general-executor run → event log 不包含 task.capability_enforced
  - inspect validator 任务 → 输出包含 `capability_enforced: yes`
  - inspect general-executor 任务 → 输出包含 `capability_enforced: -`

**风险评级**：
- 影响范围: 2（orchestrator event + CLI 渲染）
- 可逆性: 1（纯增量）
- 依赖复杂度: 2（依赖 Slice 2 的 enforce 集成）
- **总分: 5 — 中低风险**

**依赖**：Slice 2 必须先完成。

**验收条件**：
- 降级事件被正确记录
- inspect 输出展示 enforcement 状态
- 已有测试全部通过

---

## 实现顺序

```
Slice 1: capability_enforcement.py 映射表与 enforce 函数
    ↓
Slice 2: orchestrator 集成（run_task + acknowledge_task）
    ↓
Slice 3: 事件记录 + inspect 可视化
```

严格顺序依赖：1→2→3。

## Branch Advice

- 当前分支: `main`
- 建议操作: 新建分支
- 建议分支名: `feat/phase25-capability-enforcement`
- 理由: 3 个 slice 紧密关联，单分支单 PR
- PR 策略: 单 PR 合入

## Phase-Guard 检查

- [x] 方案未越出 context_brief 定义的 goals（仅做静态映射 + 硬裁剪）
- [x] 方案未触及 non-goals（无 OPA、无动态策略、无新 executor）
- [x] general-executor/task-state 不触发任何降级，向下兼容
- [x] Slice 数量 = 3，在建议上限 ≤5 内
- 无 `[SCOPE WARNING]`
