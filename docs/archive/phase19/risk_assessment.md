---
author: claude
phase: 19
slice: handoff-contract-schema-unification
status: draft
depends_on:
  - docs/plans/phase19/design_decision.md
---

**TL;DR**: Phase 19 整体风险低。唯一中风险项是 Slice 2（验证逻辑嵌入 harness），因为 harness.py 是 90KB 大文件，需要精确定位 artifact 写入路径。无高风险项。

---

# Risk Assessment — Phase 19

## 风险矩阵

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 等级 |
|-------|---------|--------|-----------|------|------|
| 1: Schema 术语统一 | 1 (单文件) | 1 (轻松回滚) | 1 (无外部依赖) | 3 | 低 |
| 2: 验证逻辑 | 2 (单模块) | 1 (轻松回滚) | 2 (依赖内部模块) | 5 | 中 |
| 3: 文档标注 | 1 (单文件×3) | 1 (轻松回滚) | 1 (无外部依赖) | 3 | 低 |

**无高风险项（≥7 分）。**

---

## Slice 2 中风险详细分析

### 风险点
- `harness.py` 是 90KB 大文件，修改需要精确定位 handoff contract artifact 的写入位置
- 验证逻辑嵌入位置选择不当可能影响其他 artifact 的写入路径

### 缓解措施
- Codex 实现前应先定位 harness.py 中 `remote_handoff_contract.json` 的写入点（Phase 18 引入），只在该点添加验证调用
- 验证逻辑本身应作为独立函数/方法，不内联到写入路径中
- 必须有专门针对验证失败场景的测试

### 最坏情况
- 验证逻辑误拦截合法 contract → 测试会覆盖此场景
- 完全可通过 revert 单个 commit 回滚

---

## 整体评估

Phase 19 是一个低风险、高收益的统一性工作。改动量小，但解决了 Gemini 审查报告中标注的核心一致性问题，为后续 Capabilities track（能力协商/降级）打好 Schema 基础。

不需要额外的人工 gate（标准 workflow 中的两个 gate 已足够）。
