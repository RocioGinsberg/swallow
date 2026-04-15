---
author: claude
phase: 21
slice: dispatch-policy-gate-and-mock-topology-visibility
status: draft
depends_on:
  - docs/plans/phase21/design_decision.md
  - docs/plans/phase21/context_brief.md
---

**TL;DR**: Phase 21 整体风险可控。唯一中等风险项是 Slice 2 的状态机扩展（acknowledge 流转），需要严格测试状态转换边界。无高风险 slice。

# Risk Assessment: Phase 21

## 风险矩阵

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 评级 |
|-------|---------|--------|-----------|------|------|
| 1: Dispatch Policy 语义校验 | 2 | 1 | 2 | 5 | 中低 |
| 2: CLI acknowledge 命令 | 2 | 2 | 2 | 6 | 中等 |
| 3: [MOCK-REMOTE] 可视化 | 1 | 1 | 1 | 3 | 低 |

无 slice 总分 ≥7，无需额外人工 gate 或拆分。

## 逐项风险分析

### Slice 1: Dispatch Policy

**主要风险**：orchestrator 是核心执行路径，在入口处新增校验调用可能影响性能或引入意外阻塞。

**缓解措施**：
- `validate_handoff_semantics()` 是纯文件系统检查（`os.path.exists`），不涉及网络或重计算
- 作为独立模块 `dispatch_policy.py` 实现，orchestrator 只增加一行调用
- 空 `context_pointers` 不触发校验，不影响无指针任务的执行路径

**回归风险**：低。已有 local/mock-remote/blocked 测试应全部通过，因为新校验只在 context_pointers 含无效引用时才产生 blocked verdict。

### Slice 2: CLI acknowledge

**主要风险**：状态机扩展。`acknowledged` 是新状态值，需要确保：
1. 不与已有状态转换冲突
2. acknowledged 任务在 resume/retry 时走正确路径
3. 不产生 context_brief 警告的"拦截↔放行死循环"

**缓解措施**：
- 设计选择 `dispatch_blocked → running (phase=retrieval)` 的单向流转，不引入循环
- acknowledged 任务的 topology_dispatch_status = `"acknowledged"` 是终态标记，后续不重新评估 dispatch policy
- 测试必须覆盖：acknowledge 后 resume → 完整执行 → completed，验证全链路

**边界情况**：
- 对已 acknowledged 的任务再次 acknowledge → 应报错"已放行"
- 对非 dispatch_blocked 任务 acknowledge → 应报错"状态不匹配"
- acknowledged 任务执行失败后 retry → 应正常 retry，不重新触发 policy gate

### Slice 3: [MOCK-REMOTE] 标识

**主要风险**：极低。纯 CLI 输出层变更，不影响任何状态或逻辑。

**唯一注意点**：确保标签判断条件与 Phase 20 的 mock-remote 路径标识一致（基于 `transport_kind` 或 `topology_dispatch_status`），避免误标或漏标。

## 整体风险总结

- **最高风险项**：Slice 2 的状态机扩展（总分 6，中等）
- **关键测试重点**：acknowledge 后的完整执行链路 + 边界状态拒绝
- **回归关注**：Phase 20 已有的 blocked/mock-remote/local 三路测试必须全部通过
- **无需额外人工 gate**：所有 slice 总分 < 7
