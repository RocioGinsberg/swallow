---
author: claude
phase: 25
slice: taxonomy-driven-capability-enforcement
status: draft
depends_on:
  - docs/plans/phase25/design_decision.md
  - docs/plans/phase25/context_brief.md
---

**TL;DR**: Phase 25 整体风险可控，无高风险 slice。核心风险在于 Slice 2 的 orchestrator 集成——需确保降级逻辑不误伤 general-executor 默认路径。但因默认 taxonomy 不触发任何约束，实际风险极低。

# Risk Assessment: Phase 25

## 风险矩阵

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 评级 |
|-------|---------|--------|-----------|------|------|
| 1: Capability Enforcement 映射表 | 1 | 1 | 1 | 3 | 低 |
| 2: Orchestrator 裁剪集成 | 2 | 1 | 2 | 5 | 中低 |
| 3: 事件记录 + Inspect 可视化 | 2 | 1 | 2 | 5 | 中低 |

无 slice 总分 ≥7，无需额外人工 gate。

## 逐项风险分析

### Slice 1: 映射表

**主要风险**：极低。纯数据定义 + 比较函数。

**注意点**：`_is_stricter()` 的排序逻辑必须与系统中实际使用的 capability 值一致。当前 `filesystem_access` 只有 `none / workspace_read / workspace_write` 三个值，`network_access` 只有 `none / optional / required` 三个值，排序简单明确。

### Slice 2: Orchestrator 集成

**主要风险**：如果 enforce 函数 bug 导致 general-executor 路由的 capabilities 也被意外降级，会影响所有正常任务的执行。

**缓解措施**：
- `general-executor / task-state` 在映射表中无任何约束条目
- enforce 函数对无匹配约束的组合返回原始 capabilities 不变
- 端到端测试必须覆盖 general-executor 路由的 capabilities 完整性

**回归风险**：中低。`route_capabilities` 是 dict，in-place 修改后 executor prompt 自然反映变更，不需要改 executor 层代码。

### Slice 3: 事件与可视化

**主要风险**：极低。纯增量——event 记录和 inspect 输出新增行。

**注意点**：inspect 命令需要决定信息来源。建议直接从 event log 查找 `task.capability_enforced`，而非在 TaskState 中新增字段，保持 state 精简。

## 向下兼容分析

| 现有行为 | Phase 25 后 | 影响 |
|----------|-------------|------|
| local-codex (general-executor/task-state) | 无约束触发，capabilities 不变 | 无影响 |
| mock-remote (general-executor/task-state) | 无约束触发 | 无影响 |
| local-note (specialist/task-memory) | 可能触发部分约束（视映射表配置） | 需测试 |
| acknowledge 后重新执行 | enforce 在 acknowledge 中也执行 | 需测试 |

## 整体风险总结

- **最高风险项**：Slice 2 的 orchestrator 集成（总分 5，中低）
- **关键测试重点**：general-executor 默认路径 capabilities 完整不变
- **回归关注**：所有已有测试必须通过
- **无需额外人工 gate**：所有 slice 总分 < 7
- **渐进部署特性**：与 Phase 22 类似，约束只在非 general-executor taxonomy 下激活
