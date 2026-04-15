---
author: claude
phase: 31
slice: runtime-v0
status: draft
depends_on: [docs/plans/phase31/design_decision.md]
---

> **TL;DR**: Phase 31 总体风险中等。最大风险点是 S3 对 `run_task()` 的重构——该函数是系统核心主循环，约 350 行，side effect 密集。通过"行为不变重构"策略和 ReviewGate 刻意不阻断 completion 判断，将引入风险控制在可逆范围内。

# Phase 31 Risk Assessment

## 风险矩阵

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 风险等级 |
|-------|----------|--------|-----------|------|----------|
| S1: TaskCard + Planner | 1 (新增文件) | 1 (可删除) | 1 (无外部依赖) | **3** | 低 |
| S2: ExecutorProtocol | 2 (跨 executor + orchestrator) | 2 (需回退接口变更) | 2 (依赖 S1 + harness) | **6** | 中 |
| S3: ReviewGate + 串联 | 2 (orchestrator 主循环) | 2 (需回退流程变更) | 2 (依赖 S1 + S2) | **6** | 中 |

**Phase 总分：15 / 27 — 中等风险**

无 slice 触发高风险阈值（≥7），无需拆分或增加人工 gate。

---

## 关键风险项

### R1: run_task() 重构回归风险（S3）

**描述**：`orchestrator.run_task()` 是系统核心函数，当前约 350 行，包含路由、retrieval、execution、artifact 写入、event 记录等完整生命周期。重构其内部流程有引入隐式行为变化的风险。

**影响**：如果重构引入 bug，所有 `task run` / `task retry` / `task rerun` 命令都会受影响。

**缓解措施**：
1. **行为不变原则**：v0 的 Planner（1:1 映射）、ExecutorProtocol（委托给现有 run_execution）、ReviewGate（不阻断 completion）都被设计为"透明包装"——外部行为与重构前完全相同。
2. **逐步验证**：Codex 应在每个子步骤后运行 `pytest`，确保回归安全。
3. **ReviewGate 刻意不阻断**：gate_result.status 不参与 `state.status` 计算，避免影响下游 inspect/review/checkpoint 逻辑。

**残余风险**：低。如果测试全部通过，说明外部行为未变。

---

### R2: Scope 膨胀风险

**描述**：Planner 和 ExecutorProtocol 容易被"顺手"扩展为更复杂的版本（如引入 LLM 拆解、动态 executor 注册、capability negotiation）。

**缓解措施**：
1. kickoff 中已显式列出 6 条非目标
2. Planner v0 硬编码为 1:1 映射，`plan()` 函数 < 20 行
3. ExecutorProtocol 只定义 `execute()` 一个方法
4. 不引入 executor 注册表 / 发现机制

---

### R3: TaskCard 与 TaskState 语义重叠

**描述**：`TaskCard` 的部分字段（goal、constraints）与 `TaskState` / `TaskSemantics` 存在概念重叠，可能引起"应该读哪个"的混淆。

**缓解措施**：
1. **明确权威源**：`TaskState` 是系统状态权威，`TaskCard` 是一次性的执行指令。TaskCard 从 TaskState 单向派生，不回写。
2. **命名区分**：TaskCard.parent_task_id 显式指向来源 TaskState
3. **v0 中 TaskCard 不持久化**：只在 run_task() 内部生成和消费，不写入磁盘（event log 中只记录 card_id）

---

### R4: executor.py side effect 封装不完整

**描述**：当前 `run_execution()` 直接修改传入的 `state` 对象（如 `state.executor_status`、`state.executor_name`）。`ExecutorProtocol.execute()` 的返回值是 `ExecutorResult`，但 side effect 仍通过 state 传递。

**缓解措施**：
1. v0 不改变 side effect 行为——`LocalCLIExecutor.execute()` 内部仍然委托给 `run_execution()`，state mutation 照旧发生
2. 在 design_decision 中已标注：未来 Phase 33 应将 state mutation 收敛到 orchestrator 层
3. 不引入"executor 不可修改 state"的强约束（v0 做不到，强推会 break）

**残余风险**：中。这是一个已知的技术债务，但 v0 阶段不解决是正确的——先建接口，再收拾 side effect。

---

## 回滚计划

如果 Phase 31 实现过程中发现严重问题：

1. **S1 回滚**：删除 `planner.py` 和 `TaskCard` dataclass，无其他影响
2. **S2 回滚**：删除 Protocol 和实现类，`run_task()` 恢复直接调用 `run_execution()`
3. **S3 回滚**：删除 `review_gate.py`，`run_task()` 恢复到 S2 之后的状态

每个 slice 都可独立回滚，不影响前序 slice。

---

## 总结

Phase 31 是一个"结构性重构"Phase，风险主要来自对核心函数 `run_task()` 的改动。通过"行为不变包装"策略，将实际风险控制在中等偏低水平。建议 Codex 严格按 S1→S2→S3 顺序实现，每个 slice 完成后独立跑 `pytest` 验证。
