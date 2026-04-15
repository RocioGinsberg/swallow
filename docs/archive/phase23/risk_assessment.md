---
author: claude
phase: 23
slice: taxonomy-visibility-in-cli
status: draft
depends_on:
  - docs/plans/phase23/design_decision.md
  - docs/plans/phase23/context_brief.md
---

**TL;DR**: Phase 23 是本项目迄今最低风险的 phase。两个 slice 总分均为 3（低风险），纯 CLI 输出变更，不涉及状态机、路由逻辑或数据模型。

# Risk Assessment: Phase 23

## 风险矩阵

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 评级 |
|-------|---------|--------|-----------|------|------|
| 1: inspect taxonomy 展示 | 1 | 1 | 1 | 3 | 低 |
| 2: review taxonomy 展示 | 1 | 1 | 1 | 3 | 低 |

无 slice 总分 ≥7，无需额外人工 gate。

## 风险分析

### 唯一注意点：旧状态文件兼容

Phase 22 之前创建的任务，其 `route_taxonomy_role` 和 `route_taxonomy_memory_authority` 字段为空字符串（TaskState 默认值）。CLI 展示时需要处理这种情况，显示 `taxonomy: -` 而非空白行。

### 回归风险

极低。变更仅在 CLI 输出中插入新行，不改变任何已有行的内容或顺序（新行插入在 `route_label` 之后）。已有的 inspect/review 测试断言的是特定字段存在性，不会因新增行而破坏。

## 整体风险总结

- **最高风险项**：无。两个 slice 均为低风险
- **关键测试重点**：新增的 taxonomy 行内容正确
- **回归关注**：已有 inspect/review 测试必须通过
- **无需额外人工 gate**
