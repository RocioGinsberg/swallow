---
author: claude
phase: 30
slice: Operator Checkpoint & Selective Retry
status: draft
depends_on: [docs/plans/phase30/design_decision.md]
---

## TL;DR
全部 PASS，无 BLOCK，无 CONCERN。高风险 Slice 2 实现质量高——fallback 路径完整，状态一致性正确，测试通过 patch 精确验证了跳过行为。

---

# Review Comments

## 检查范围
- 对比: `git diff main...feat/phase30-checkpoint-selective-retry`
- 对比 design_decision.md 一致性
- 重点审查 Slice 2 高风险项：selective retry 的状态一致性与 fallback 路径
- 涉及文件: models.py, orchestrator.py, cli.py, harness.py, checkpoint_snapshot.py, test_cli.py

---

## Slice 1: Execution Phase 显式化

- [PASS] `TaskState` 新增 `execution_phase: str = "pending"` 和 `last_phase_checkpoint_at: str = ""`
- [PASS] `_record_phase_checkpoint()` 辅助函数干净——更新 state、save、记录事件，三步一气呵成
- [PASS] `run_task()` 在 retrieval/execution/analysis 完成后分别调用 checkpoint，记录 `retrieval_done`/`execution_done`/`analysis_done`
- [PASS] `_begin_execution_attempt()` 时重置 `execution_phase = "pending"`（通过 run_task 开头的显式赋值）
- [PASS] `task.phase_checkpoint` 事件 payload 含 `execution_phase`、`skipped`、`source`
- [PASS] 测试: `test_run_persists_execution_phase_checkpoints` 验证三阶段 checkpoint 事件序列

---

## Slice 2: Selective Retry 支持（高风险 Slice）

### 核心逻辑

- [PASS] `run_task()` 新增 `skip_to_phase: str = "retrieval"` 参数，默认值确保不传时行为不变
- [PASS] `--from-phase` 添加到 `retry` 和 `rerun` 命令，choices 为 `retrieval`/`execution`/`analysis`
- [PASS] `resume` 不支持 `--from-phase`，符合设计

### Retrieval 跳过路径

- [PASS] `_load_previous_retrieval_items()` 从 retrieval.json 加载历史 items，严格校验：文件不存在 → None，JSON 格式错误 → None，非 list → None，entry 非 dict → None
- [PASS] 加载失败时触发 `_append_phase_recovery_fallback()` 事件并 fallback 到完整 retrieval
- [PASS] 跳过时 `retrieval_skipped = True` 传入 checkpoint 事件

### Execution 跳过路径

- [PASS] `_load_previous_executor_result()` 从 artifact 文件重建 `ExecutorResult`，处理了 dialect header 剥离（`prompt.startswith("dialect: ")`）
- [PASS] 加载失败时 fallback 到完整 execution
- [PASS] 跳过时 `execution_lifecycle = "reused"`，状态正确区分

### 状态一致性

- [PASS] 跳过阶段后，TaskState 保留上次相关字段值（retrieval_count 等不清零）
- [PASS] 事件链完整：跳过的阶段有 `task.phase_checkpoint` 事件（`skipped: true`）+ fallback 事件（如触发）
- [PASS] `assert retrieval_items is not None` 在 fallback 逻辑后确保不会带 None 继续

### 测试覆盖

- [PASS] `test_rerun_from_execution_reuses_previous_retrieval`：用 `patch("swallow.harness.retrieve_context", side_effect=AssertionError)` 精确验证 retrieval 被跳过
- [PASS] `test_rerun_from_analysis_reuses_previous_execution_artifacts`：同时 patch retrieval + executor，验证两者都被跳过
- [PASS] 测试验证了 checkpoint 事件的 skipped/source 字段正确

### 安全评估

高风险 Slice 2 的所有缓解措施均已落地：
1. 默认空/retrieval 时完全走原始路径 ✓
2. 加载失败 graceful fallback + 事件记录 ✓
3. 跳过阶段保留 TaskState 字段 ✓
4. 跳过阶段记录 checkpoint 事件 ✓

---

## Slice 3: Checkpoint 可观测性

- [PASS] `task inspect` 新增 `execution_phase` 和 `last_phase_checkpoint_at`
- [PASS] `task review` 新增同上字段（两处：lifecycle 区和 handoff 区）
- [PASS] `task control` snapshot 新增同上字段
- [PASS] `CheckpointSnapshotResult` 新增 `execution_phase` 和 `last_phase_checkpoint_at` 字段
- [PASS] `checkpoint_snapshot.py` 正确传递这两个字段到 report
- [PASS] `harness.py` 的 checkpoint event payload 和 task_memory 均新增字段
- [PASS] terminal event payload 新增 `execution_phase` 和 `last_phase_checkpoint_at`
- [PASS] `execute_task_run()` 输出新增 `execution_phase=` 信息

---

## 跨 Slice 检查

- [PASS] 与 design_decision 的一致性: 三个 slice 均按设计实现，无越界
- [PASS] 非目标未被触及: 无 step-level 中断、无 run_task 拆分、无 stop_policy 变更、无 retry_policy 变更
- [PASS] 测试全量通过: 183 passed, 5 subtests passed
- [PASS] 现有测试适配了新增的 checkpoint 事件（state/event 序列断言已更新）
- [PASS] `_load_previous_retrieval_items` 和 `_load_previous_executor_result` 作为独立函数放在 orchestrator.py（符合 risk_assessment 建议）

---

## 额外观察

diff 中包含若干现有测试的 state/event 序列断言更新，这是因为新增的 `task.phase_checkpoint` 事件和 `save_state()` 调用改变了 state 快照序列。这些调整是合理的回归适配。

---

## 结论

**Merge ready.** 无 BLOCK，无 CONCERN。高风险 Slice 2 实现质量超出预期——fallback 路径、状态一致性、测试覆盖均已充分验证。
