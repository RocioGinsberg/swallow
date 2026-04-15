---
author: claude
phase: 27
slice: knowledge-driven-task-grounding-baseline
status: draft
depends_on:
  - docs/plans/phase27/design_decision.md
  - docs/plans/phase27/context_brief.md
---

**TL;DR**: Phase 27 整体风险可控，无高风险 slice。核心风险在于 Slice 2 的 resume 锁定逻辑——需确保首次执行和 resume 路径的一致性。但新增字段有默认值，不破坏已有 state 反序列化。

# Risk Assessment: Phase 27

## 风险矩阵

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 评级 |
|-------|---------|--------|-----------|------|------|
| 1: Grounding Evidence Artifact | 2 | 1 | 2 | 5 | 中低 |
| 2: Context Refs + Resume 锁定 | 2 | 1 | 2 | 5 | 中低 |
| 3: Inspect 可视化 | 1 | 1 | 2 | 4 | 低 |

无 slice 总分 ≥7，无需额外人工 gate。

## 逐项风险分析

### Slice 1: Grounding Evidence Artifact

**主要风险**：harness 的 `write_task_artifacts()` 是核心 artifact 写入路径，新增 grounding 写入需确保不干扰已有 artifact 生成。

**缓解措施**：
- grounding 写入是独立的 append 操作，不修改已有 artifact 的生成逻辑
- 如果 retrieval 无 canonical items，生成空 grounding（entries=[]），不 skip 写入

### Slice 2: Context Refs + Resume 锁定

**主要风险**：`grounding_locked` 逻辑需要在 run_task 中正确区分首次执行 vs. resume。

**缓解措施**：
- 首次执行：`grounding_locked == False`（默认值）→ 提取 + 锁定
- resume：`grounding_locked == True` → 跳过提取，使用已有 artifact
- 边界情况：retry（从头开始）应重置 `grounding_locked = False`，重新提取

**回归风险**：低。`grounding_refs` 和 `grounding_locked` 有默认值（空 list 和 False），已有 state 文件反序列化不受影响。

### Slice 3: Inspect 可视化

**主要风险**：极低。纯展示变更。

## 整体风险总结

- **最高风险项**：Slice 1 和 Slice 2 并列（总分 5，中低）
- **关键测试重点**：resume 后 grounding 不漂移 + 首次执行正确锁定
- **回归关注**：所有已有测试必须通过
- **无需额外人工 gate**
