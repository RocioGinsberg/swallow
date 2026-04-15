---
author: claude
phase: 22
slice: taxonomy-aware-routing-baseline
status: draft
depends_on:
  - docs/plans/phase22/design_decision.md
  - docs/plans/phase22/context_brief.md
---

**TL;DR**: Phase 22 整体风险可控，无高风险 slice。最需关注的是 Slice 3 的启发式拦截规则——关键词匹配可能产生误拦截，但因默认路由 taxonomy 不触发任何规则，实际影响面极小。

# Risk Assessment: Phase 22

## 风险矩阵

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 评级 |
|-------|---------|--------|-----------|------|------|
| 1: TaxonomyProfile 定义 | 1 | 1 | 1 | 3 | 低 |
| 2: RouteSpec taxonomy 挂载 | 2 | 1 | 2 | 5 | 中低 |
| 3: Dispatch Taxonomy Guard | 2 | 1 | 2 | 5 | 中低 |

无 slice 总分 ≥7，无需额外人工 gate 或拆分。

## 逐项风险分析

### Slice 1: TaxonomyProfile 定义

**主要风险**：极低。纯数据结构定义，不改变任何运行时行为。

**唯一注意点**：枚举值列表需与 `AGENT_TAXONOMY_DESIGN.md` 保持一致。如果设计文档后续更新了角色/权限类型，代码侧需同步。

### Slice 2: RouteSpec taxonomy 挂载

**主要风险**：为 5 条内置路由赋予默认 taxonomy 时，如果默认值选择不当，可能导致 Slice 3 的 guard 意外拦截正常任务。

**缓解措施**：
- 所有现有路由默认为 `general-executor / task-state`，这是最宽松的组合
- `local-note` 设为 `specialist / task-memory`，因其功能本身就是局部记忆操作
- 默认值不触发 Slice 3 的任何拦截规则

**回归风险**：低。新增字段有默认值，已有代码路径不依赖 taxonomy 字段。

### Slice 3: Dispatch Taxonomy Guard

**主要风险**：基于关键词的启发式拦截可能产生假阳性（误拦截）或假阴性（漏拦截）。

**假阳性场景**：
- contract goal 中包含 "promote discussion"（非知识晋升含义）→ 被 canonical-write-forbidden 规则误拦
- next_steps 包含 "write a summary"（输出动作而非状态修改）→ 被 validator 规则误拦

**缓解措施**：
- 当前系统所有内置路由默认 taxonomy 都是 `general-executor / task-state`，**不会触发任何拦截规则**
- 拦截只在显式设置了 `validator` 或 `canonical-write-forbidden` 的路由上生效
- 这意味着在本轮中，guard 是"已部署但默认不激活"的状态，只有未来新增非 general-executor 路由时才会实际拦截
- 这是符合设计意图的渐进式部署策略

**假阴性**：可接受。初始版本只做最明显的关键词匹配，不追求完美覆盖。

**回归风险**：低。guard 调用链与 Phase 21 的 `validate_handoff_semantics()` 串联，逻辑独立，互不干扰。

## 向下兼容分析

| 现有行为 | Phase 22 后 | 影响 |
|----------|-------------|------|
| local-codex 路由正常执行 | taxonomy=general-executor/task-state，不触发 guard | 无影响 |
| mock-remote 路由正常执行 | taxonomy=general-executor/task-state，不触发 guard | 无影响 |
| dispatch_blocked → acknowledge → resume | taxonomy 字段在 acknowledge 时随 route 重选而更新 | 无影响 |
| inspect/review 输出 | 可选展示 taxonomy 信息（如 Codex 决定在 inspect 中显示） | 纯增量 |

## 整体风险总结

- **最高风险项**：Slice 3 的启发式规则（总分 5，中低）
- **关键测试重点**：确保默认路由（general-executor/task-state）的任务全链路不受 guard 影响
- **回归关注**：Phase 21 已有的 146+ 测试必须全部通过
- **无需额外人工 gate**：所有 slice 总分 < 7
- **渐进部署特性**：guard 默认不激活，降低了上线风险
