---
author: claude
phase: 30
slice: Operator Checkpoint & Selective Retry
status: draft
depends_on: [docs/plans/phase30/design_decision.md]
---

## TL;DR
Phase 30 含一个高风险 Slice（Slice 2，总分 7）。核心风险在于 `run_task()` 主循环的条件分支——跳过 retrieval/execution 时需要正确加载历史 artifact 并处理边界情况。建议 Slice 2 实现后增加人工 gate。

---

# Risk Assessment

## 风险矩阵

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 评级 |
|:------|:---------|:-------|:-----------|:-----|:-----|
| 1: Execution Phase 显式化 | 2 | 1 | 1 | 4 | 低 |
| 2: Selective Retry 支持 | 3 | 2 | 2 | 7 | **高** |
| 3: Checkpoint 可观测性 | 2 | 1 | 2 | 5 | 中低 |

Slice 2 总分 ≥7，标注为高风险。

---

## 逐项风险分析

### Slice 1: Execution Phase 显式化

**风险点**：无显著风险。纯新增字段 + save_state 调用点。

**唯一关注**：`save_state()` 调用次数增加（每个 phase checkpoint 一次）。当前 run_task 已经多次调用 save_state，增加 2-3 次不会有性能问题。

---

### Slice 2: Selective Retry 支持

**风险点**：

1. **`run_task()` 核心流程变更**：引入 `skip_to_phase` 条件分支，改动了系统最核心的执行路径。任何逻辑错误都可能导致任务执行不完整或状态不一致。

2. **历史 artifact 加载的边界情况**：
   - retrieval items artifact 文件不存在（任务从未成功完成 retrieval）
   - executor result artifact 文件不存在（任务从未成功完成 execution）
   - artifact 文件格式不兼容（旧版本任务 state 无 execution_phase 字段）
   - artifact 文件被手动删除或损坏

3. **状态一致性**：跳过 retrieval 时，TaskState 中的 retrieval 相关字段（retrieval_count、retrieval_record 等）应保持上次值还是重新计算？

4. **事件链完整性**：跳过阶段后，events.jsonl 中的事件序列是否仍然对后续 analysis 逻辑（stop_policy、retry_policy）有效？

**缓解措施**：

1. `skip_to_phase` 默认空字符串，不传时完全走原始路径（零行为变化）
2. 加载历史 artifact 时做严格校验 + fallback：文件不存在或格式错误 → 打印 warning → 自动 fallback 到完整流程
3. 跳过的阶段保留上次 TaskState 中的所有相关字段值（不清零）
4. 跳过的阶段记录 `task.phase_checkpoint` 事件（`skipped: true`），确保事件链对下游可见

**建议**：Slice 2 实现后，在进入 Slice 3 之前做一次人工 gate：
- 全量测试确认
- 手动测试 `--from-phase execution` 和 `--from-phase analysis` 各一次
- 确认 fallback 路径正常工作

---

### Slice 3: Checkpoint 可观测性

**风险点**：无显著风险。纯展示层增加字段。

---

## 跨 Slice 风险

### TaskState 序列化兼容

Phase 29 刚新增了 `route_dialect` 字段，Phase 30 再新增 `execution_phase`。需确认旧版 state.json（无这些字段）的 `TaskState.from_dict()` 能正确处理缺失字段（使用默认值）。

**验证方式**：在测试中构造不含 `execution_phase` 的旧格式 state.json，确认 `load_state()` 不报错。

### run_task 复杂度膨胀

`run_task()` 已经是 ~300 行的大函数。Slice 2 增加条件分支会进一步增加复杂度。

**建议**：将 "加载历史 retrieval items" 和 "加载历史 executor result" 提取为独立函数放在 harness.py 中，不在 run_task 内部写内联逻辑。

---

## 总体评估

Phase 30 是本项目首次含高风险 slice 的 phase。Slice 2 改动了 `run_task()` 核心流程，需要格外谨慎。建议严格按 Slice 1 → 全量测试 → Slice 2 → 人工 gate → Slice 3 的节奏推进。
