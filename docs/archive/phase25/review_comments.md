---
author: claude
phase: 25
slice: taxonomy-driven-capability-enforcement
status: draft
depends_on:
  - docs/plans/phase25/design_decision.md
  - docs/plans/phase25/risk_assessment.md
---

**TL;DR**: 三个 slice 全部实现且通过测试（178 passed）。整体 PASS，可合并。一个 CONCERN 关于 `canonical_write_guard` 约束字段在 RouteCapabilities 中不是原生字段，但不阻塞。

# Review Comments: Phase 25

## 测试结果

```
178 passed, 5 subtests passed in 4.74s
```

全部通过，无 failure。较上一轮净增 11 个测试。

---

## Slice 1: Capability Enforcement 映射表

### [PASS] 数据结构与映射表
- `CapabilityConstraint` dataclass 简洁：field、max_value、reason
- `TAXONOMY_CAPABILITY_CONSTRAINTS` 使用通配符 key（`validator/*`、`*/stateless`、`*/canonical-write-forbidden`），匹配逻辑在 `_matching_constraints()` 中按精确匹配→role 通配→authority 通配顺序查找
- 初始规则与 design_decision 一致

### [PASS] enforce 函数
- `enforce_capability_constraints()` 正确返回降级后的 capabilities + 触发的约束列表
- `_is_stricter()` 使用排序 dict 比较 filesystem_access 和 network_access，逻辑清晰
- 对未在 capabilities 中的字段（如 `canonical_write_guard`），自动注入 max_value 并记录约束

### [CONCERN] canonical_write_guard 非原生字段
- `*/canonical-write-forbidden` 约束注入了 `canonical_write_guard: True` 到 capabilities dict，但 `RouteCapabilities` dataclass 中没有这个字段
- 这意味着它是一个"审计标记"而非真正的能力降级——当前没有代码检查 `canonical_write_guard` 来阻止实际写入
- 设计上可接受（Phase 24 的 staged knowledge 路由已经在 orchestrator 层做了真正的写入拦截），但命名暗示了它是一个 guard 而实际只是标记
- **不阻塞本轮**：作为审计信号足够，真正的写入拦截由 Phase 24 保障

### [PASS] 测试覆盖
- validator + workspace_write → 降级为 workspace_read + tool_loop=false
- stateless + workspace_read → 全降级为 none
- general-executor/task-state → 无降级
- validator/stateless 组合 → 多条约束同时应用

---

## Slice 2: Orchestrator 裁剪集成

### [PASS] run_task 集成
- `_apply_capability_enforcement()` 在路由赋值之后、execution 之前调用
- 保存 `original_route_capabilities` 用于 event payload 对比
- 降级后的 capabilities 写入 `state.route_capabilities`，executor prompt 自然拿到裁剪后的值

### [PASS] acknowledge_task 集成
- acknowledge 重选路由后同样调用 enforce
- event payload 包含 `capability_constraints_applied`

### [PASS] executor 接收降级后的 capabilities
- 测试通过 `run_execution_spy` 捕获传入 executor 的 state，验证 capabilities 已降级
- general-executor 路由的 capabilities 完整保留，spy 验证值不变

### [PASS] 向下兼容
- general-executor/task-state 不触发任何约束，无 enforcement event
- 所有已有 167 个测试 + 11 个新测试全部通过

---

## Slice 3: 事件记录与 Inspect 可视化

### [PASS] event: task.capability_enforced
- 只在有约束触发时记录（`if applied_constraints:` 条件）
- payload 包含完整的审计信息：taxonomy、original capabilities、enforced capabilities、constraints 列表
- general-executor 不产生 enforcement event

### [PASS] inspect 可视化
- `load_latest_capability_enforcement()` 从 event log 逆序查找最近的 enforcement event
- `format_capability_enforcement_summary()` 输出紧凑格式：`capability_enforced: yes` + `capability_enforced_fields: filesystem_access->workspace_read, supports_tool_loop->false`
- 无 enforcement 时显示 `capability_enforced: -`

### [PASS] 测试覆盖
- validator route → inspect 包含 `capability_enforced: yes` + 具体字段
- general-executor → inspect 包含 `capability_enforced: -`
- enforcement event payload 内容验证

---

## 与 design_decision 的一致性检查

| 设计要求 | 实现状态 |
|----------|---------|
| CapabilityConstraint dataclass | PASS |
| TAXONOMY_CAPABILITY_CONSTRAINTS 映射表 | PASS — 三组规则与设计一致 |
| enforce_capability_constraints 函数 | PASS |
| _is_stricter 比较逻辑 | PASS |
| run_task 中裁剪集成 | PASS |
| acknowledge_task 中裁剪集成 | PASS |
| event: task.capability_enforced | PASS |
| inspect capability_enforced 展示 | PASS |
| general-executor 不受影响 | PASS |
| 不引入 OPA / 动态策略 | PASS |

## Phase-Guard 检查

- [x] 未越出 Phase 25 scope
- [x] 未触及 non-goals（无 OPA、无新 executor、无动态配置）
- [x] general-executor/task-state 默认行为完全不变

## 结论

**PASS, mergeable.** 三个 slice 全部符合设计，178 测试通过，无 BLOCK 项。capability enforcement 成功建立了 taxonomy→capability 降级的最小权限防线。
