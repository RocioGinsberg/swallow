---
author: claude
phase: 22
slice: taxonomy-aware-routing-baseline
status: draft
depends_on:
  - docs/plans/phase22/design_decision.md
  - docs/plans/phase22/risk_assessment.md
---

**TL;DR**: 三个 slice 全部实现且通过测试（154 passed）。整体 PASS，可合并。无 BLOCK 项，一个 CONCERN 关于 `validate_taxonomy_dispatch` 对所有 contract 生效（含 local-only），但因默认 taxonomy 不触发任何规则，实际无影响。

# Review Comments: Phase 22

## 测试结果

```
154 passed, 5 subtests passed in 4.73s
```

全部通过，无 failure。较 Phase 21 净增 8 个测试。

---

## Slice 1: TaxonomyProfile 定义

### [PASS] 数据结构
- `TaxonomyProfile` 在 `models.py` 中定义，`slots=True`，带 `__post_init__` 自动校验
- `SYSTEM_ROLES` 和 `MEMORY_AUTHORITIES` 枚举元组与 `AGENT_TAXONOMY_DESIGN.md` 一致
- `to_dict()` 返回标准 dict，便于序列化

### [PASS] 测试覆盖
- `test_taxonomy.py` 覆盖：合法值 pass、非法 system_role raise、非法 memory_authority raise
- 错误消息包含合法值列表，便于调试

---

## Slice 2: RouteSpec Taxonomy 挂载

### [PASS] RouteSpec 集成
- `RouteSpec` 新增 `taxonomy` 字段，默认值为 `general-executor / task-state`
- `to_dict()` 正确包含 taxonomy
- `build_detached_route()` 正确传播 taxonomy 到 detached 变体

### [PASS] 内置路由 taxonomy 赋值
- `local-codex`: general-executor / task-state ✓
- `local-mock`: general-executor / task-state ✓
- `local-note`: specialist / task-memory ✓（符合其 note-only 定位）
- `local-summary`: general-executor / task-state ✓
- `mock-remote`: general-executor / task-state ✓

### [PASS] TaskState 传播
- `create_task()`、`run_task()`、`acknowledge_task()` 三处均正确传播 `route_taxonomy_role` 和 `route_taxonomy_memory_authority`
- 新增测试验证 `local-note` 路由分配到 specialist taxonomy

### [PASS] 向下兼容
- TaskState 新字段默认为空字符串，不破坏已有状态文件反序列化
- 已有路由选择测试均补充了 taxonomy 断言

---

## Slice 3: Dispatch Taxonomy Guard

### [PASS] validate_taxonomy_dispatch() 实现
- 三条规则与 design_decision 一致：
  1. validator + write-intent keywords → blocked
  2. canonical-write-forbidden + promotion keywords → blocked
  3. stateless + non-empty context_pointers → blocked
- 关键词常量 `WRITE_INTENT_KEYWORDS` 和 `PROMOTION_KEYWORDS` 提取为模块级常量，可读性好

### [PASS] orchestrator 集成
- 在 `_evaluate_dispatch_for_run()` 中，`validate_taxonomy_dispatch()` 串联在 `validate_handoff_semantics()` 之后
- 校验失败生成 `DispatchVerdict(action="blocked", reason="route taxonomy rejected dispatch contract")`

### [CONCERN] taxonomy guard 对所有 contract 生效（含 local-only）
- Phase 21 的 `validate_handoff_semantics()` 只对 `remote_candidate=True` 的 contract 触发
- Phase 22 的 `validate_taxonomy_dispatch()` 对所有经过 `_evaluate_dispatch_for_run()` 的 contract 都触发
- 这是合理的设计选择——taxonomy guard 应该是全局的，不限于 remote 路径
- 但因所有内置路由默认 taxonomy = general-executor / task-state，三条拦截规则都不会被触发
- **不阻塞本轮**。当未来新增 validator/stateless 路由时，guard 自动生效

### [PASS] 端到端测试
- 通过 `patch("swallow.orchestrator.select_route")` 注入 validator 路由，验证 taxonomy guard 拦截 write-intent contract → dispatch_blocked
- 测试覆盖了 event payload 中 verdict 的 reason 和 blocking_detail

### [PASS] 测试覆盖完整度
- 单元测试：validator write-intent blocked、canonical-write-forbidden promotion blocked、general-executor pass
- 端到端测试：validator route + write-intent goal → orchestrator dispatch_blocked
- 缺少 stateless + context_pointers 的端到端测试，但单元级已覆盖，风险可接受

---

## 与 design_decision 的一致性检查

| 设计要求 | 实现状态 |
|----------|---------|
| TaxonomyProfile dataclass + validate() | PASS |
| SYSTEM_ROLES / MEMORY_AUTHORITIES 枚举 | PASS — 与设计文档一致 |
| RouteSpec 新增 taxonomy 字段 | PASS |
| 5 条内置路由赋默认 taxonomy | PASS — 值与设计一致 |
| TaskState 新增 route_taxonomy_role/memory_authority | PASS |
| create_task/run_task/acknowledge_task 传播 | PASS |
| validate_taxonomy_dispatch 三条规则 | PASS |
| orchestrator 串联调用 | PASS |
| 不引入 RBAC | PASS — 无越界 |
| 不改变 select_route 逻辑 | PASS — 仅新增字段传播 |

## Phase-Guard 检查

- [x] 未越出 Phase 22 scope
- [x] 未触及 non-goals（无 RBAC、无动态注册、无新 executor）
- [x] 默认 taxonomy 保证向下兼容，所有已有路径行为不变

## 结论

**PASS, mergeable.** 三个 slice 全部符合设计，154 测试通过，无 BLOCK 项。taxonomy guard 采用渐进部署策略（默认不激活），风险极低。
