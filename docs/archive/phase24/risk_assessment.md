---
author: claude
phase: 24
slice: staged-knowledge-pipeline-baseline
status: draft
depends_on:
  - docs/plans/phase24/design_decision_claude.md
  - docs/plans/phase24/context_brief.md
---

**TL;DR**: Phase 24 整体风险可控。最高风险项是 Slice 3 的 orchestrator 知识写入路由（总分 6，中等），因其修改了已有流程的分支逻辑。但因只在特定 taxonomy（canonical-write-forbidden / staged-knowledge）下触发，默认行为不变。

# Risk Assessment: Phase 24

## 风险矩阵

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 评级 |
|-------|---------|--------|-----------|------|------|
| 1: Staged Knowledge 数据模型与存储 | 1 | 1 | 1 | 3 | 低 |
| 2: CLI stage-* 命令 | 2 | 1 | 2 | 5 | 中低 |
| 3: Taxonomy-aware 知识写入路由 | 2 | 2 | 2 | 6 | 中等 |

无 slice 总分 ≥7，无需额外人工 gate。

## 逐项风险分析

### Slice 1: 数据模型与存储

**主要风险**：极低。纯新增模块和存储路径，不改变任何已有代码。

**注意点**：JSONL 格式的 update 操作需要 read-modify-write 全文件。当前阶段 staged candidates 数量预期极少（手动提交），性能不是问题。

### Slice 2: CLI 命令

**主要风险**：`stage-promote` 需要调用已有的 `append_canonical_record` 写入 canonical registry。需确保 StagedCandidate 中的字段能正确映射到 canonical record 的必填字段。

**缓解措施**：
- 在 promote 时构造 canonical record，明确映射每个字段
- promote 前校验 candidate status == "pending"，防止重复晋升

**注意点**：`knowledge` 作为新的顶级命令，需要确保不与已有的 `task` 子命令下的 `knowledge-*` 命令混淆。命名策略：全局命令用 `swl knowledge stage-*`，task-local 命令保持 `swl task knowledge-*`。

### Slice 3: Taxonomy-aware 知识写入路由

**主要风险**：修改 orchestrator 中任务完成后的知识处理逻辑。如果路由判断条件写错，可能导致正常任务的知识也被意外导向 staged。

**缓解措施**：
- 路由条件严格限定为 `memory_authority in ("canonical-write-forbidden", "staged-knowledge")`
- 所有内置路由默认 memory_authority = "task-state"，不会触发 staged 路由
- 与 Phase 22 的 dispatch guard 类似的渐进部署策略：默认不激活

**回归风险**：中。需要仔细验证 task-state 实体的知识处理路径完全不受影响。

**边界情况**：
- 任务中没有 promote-intent 的 knowledge objects → 不触发任何 staged 写入
- 任务中有 promote-intent 但 stage != "verified" → 不触发（只处理满足条件的对象）

## 向下兼容分析

| 现有行为 | Phase 24 后 | 影响 |
|----------|-------------|------|
| task-local knowledge promote/reject | 不变 | 无影响 |
| canonical registry 写入 | 不变（task-state 实体） | 无影响 |
| knowledge-review-queue CLI | 不变 | 无影响 |
| 新任务创建和执行 | 不变（默认 taxonomy 不触发 staged 路由） | 无影响 |

## 整体风险总结

- **最高风险项**：Slice 3 的 orchestrator 知识写入路由（总分 6，中等）
- **关键测试重点**：确保 task-state 实体的知识流程完全不受影响；staged 写入的 candidate 字段完整正确
- **回归关注**：所有已有测试必须通过
- **无需额外人工 gate**：所有 slice 总分 < 7
