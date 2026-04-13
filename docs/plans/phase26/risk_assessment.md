---
author: claude
phase: 26
slice: canonical-knowledge-deduplication-and-merge-gate
status: draft
depends_on:
  - docs/plans/phase26/design_decision.md
  - docs/plans/phase26/context_brief.md
---

**TL;DR**: Phase 26 整体风险极低。核心发现：store 层的 supersede 机制已存在，本轮只是修正上层 key 生成使其生效。最高风险项 Slice 1 总分仅 5（中低），且修改范围小。

# Risk Assessment: Phase 26

## 风险矩阵

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 评级 |
|-------|---------|--------|-----------|------|------|
| 1: Canonical Key 修正 | 2 | 1 | 2 | 5 | 中低 |
| 2: Dedupe 前置检查 | 1 | 1 | 2 | 4 | 低 |
| 3: Canonical Audit 命令 | 1 | 1 | 1 | 3 | 低 |

无 slice 总分 ≥7，无需额外人工 gate。

## 逐项风险分析

### Slice 1: Canonical Key 修正

**主要风险**：修改 key 生成逻辑后，同源 candidates 的后续 promote 会触发 supersede，改变了已有的"累积 append"行为。

**缓解措施**：
- supersede 是显式标记（旧记录 status→superseded + superseded_by 指针），不是物理删除
- store 层的 supersede 逻辑已有完整测试（Phase 之前就存在）
- 本轮只改 key 生成，不改 supersede 执行逻辑

**回归风险**：低。现有 stage-promote 测试会验证 canonical record 写入行为。新 key 格式需要新测试覆盖 supersede 场景。

### Slice 2: Dedupe 前置检查

**主要风险**：极低。纯信息提示，不改写入行为。

### Slice 3: Canonical Audit 命令

**主要风险**：极低。只读命令，不改任何状态。

## 整体风险总结

- **最高风险项**：Slice 1 的 key 修正（总分 5，中低）
- **关键测试重点**：同源 candidates 的 supersede 行为 + 不同源的独立性
- **回归关注**：已有 canonical registry 测试必须通过
- **无需额外人工 gate**
- **附带收益**：消化 concerns_backlog 中 Phase 24 的 Open 条目
