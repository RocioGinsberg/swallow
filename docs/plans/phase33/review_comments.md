---
author: claude
phase: 33
slice: subtask-orchestrator
status: final
depends_on: [docs/plans/phase33/kickoff.md]
---

# Phase 33 Review Comments

> 审查范围：`main..feat/phase33-subtask-orchestrator` (4 commits, +1417/-83 lines, 10 files)
> 测试结果：234 passed, 5 subtests passed in 6.91s
> 审查结论：**Merge ready — 0 BLOCK, 1 CONCERN, 0 NOTE**

---

## Slice 总览与 kickoff 对照

| Slice | kickoff 完成条件 | 实际交付 | 判定 |
|-------|----------------|---------|------|
| S1: TaskCard + 1:N Planner | `depends_on`/`subtask_index` 字段 + 规则驱动多卡产出 | `models.py` 新增两字段，`planner.py` 支持 `next_action_proposals` 驱动 + `parallel_subtasks` constraint | PASS |
| S2: SubtaskOrchestrator | DAG 调度 + 并发执行 + 结果聚合 | `subtask_orchestrator.py` 223 行，Kahn 拓扑排序 + ThreadPoolExecutor + 完整错误处理 | PASS |
| S3: Review Feedback Loop + 集成 | ReviewGate retry + run_task 多卡分支 + artifact/event | `orchestrator.py` +329 行新增，单次 retry + 子任务 artifact/event 写入 + 父任务聚合 | PASS |

---

## 架构审查

### 1:N Planner（S1）

**优点**：

- Librarian 路径优先级保持不变（`_should_plan_librarian_card` 仍在 `plan()` 顶部），知识写回防线未被并发编排破坏。
- 多卡触发条件清晰：`len(next_actions) > 1`，且上限 `MAX_SUBTASK_CARDS = 4`。
- 并行/顺序由 `parallel_subtasks` constraint 控制，`depends_on` 链式构建逻辑正确（并行时 `depends_on=[]`，顺序时依赖前一张卡）。
- 单卡路径（`plan()` 末尾）完全不变，保持 Phase 31 回归安全。

### SubtaskOrchestrator（S2）

**优点**：

- `build_subtask_levels()` 使用标准 Kahn 算法做拓扑排序，环检测到位（`processed_count != len(cards)` 抛异常）。
- `_validate_cards()` 覆盖了重复 card_id、自依赖、未知依赖三种非法情况。
- `_clone_state()` 通过 `TaskState.from_dict(state.to_dict())` 深拷贝，子任务不共享 state 引用——并发安全。
- `_run_single_card()` 包裹了 `try/except` 防御性路径，executor 异常不会崩溃整个编排。
- 并发控制：`min(self._max_workers, len(level))` 避免为单卡 level 创建多余线程。

### Review Feedback Loop + run_task 集成（S3）

**优点**：

- 单卡路径与多卡路径通过 `multi_card_plan = len(cards) > 1` 显式分叉，单卡路径零改动。
- retry 逻辑精确：只对 `failed_records` 重试，`retry_card = replace(cards_by_id[...], depends_on=[])` 去除依赖——正确，retry 时无需等待前置。
- `attempt_counts` 字典追踪每张卡的尝试次数，retry exhausted 事件中包含 `attempt_count: 2`。
- 子任务 artifact 使用 `subtask_{index}_attempt{n}_` 前缀，物理隔离清晰。
- 父任务最终 `executor_output.md` 聚合了所有子任务的状态摘要（`_build_subtask_executor_result`）。
- `skip_to_phase == "analysis"` 在多卡场景下强制回退到 `execution`——正确，多卡不支持 selective reuse。

---

## 测试覆盖审查

| 测试文件 | 覆盖范围 | 判定 |
|---------|---------|------|
| `test_planner.py` (+69 行) | 单卡回归、Librarian 优先、多卡顺序/并行、上限截断 | 充分 |
| `test_subtask_orchestrator.py` (208 行) | 顺序执行、并发执行（含 max_active 验证）、依赖收敛、失败聚合、非法 DAG | 充分 |
| `test_run_task_subtasks.py` (203 行) | retry 成功端到端、retry exhausted 端到端、artifact/event 完整性 | **关键测试，充分** |

---

## CONCERN（非阻塞，建议追踪）

### C1: 子任务执行在 tempdir 中，artifact 丢失

`_run_subtask_orchestration` 中的 `execute_subtask` 闭包将每个子任务执行在 `tempfile.TemporaryDirectory` 中（`orchestrator.py:1459-1462`）：

```python
def execute_subtask(...):
    with tempfile.TemporaryDirectory(prefix="swallow-subtask-") as tmp:
        return _execute_task_card(Path(tmp), isolated_state, card, subtask_retrieval_items)
```

这意味着子任务 executor 内部（如 `run_execution` / `write_artifact`）写入的 artifact 在 tempdir 清理后丢失。当前这不是 bug——子任务 artifact 已经通过 `_write_subtask_attempt_artifacts` 从 `ExecutorResult` 的 prompt/output/stdout/stderr 重新写入父任务目录。但如果未来有 executor 在 `base_dir` 下写入额外 artifact（如 LibrarianExecutor 的 change_log），这些会被 tempdir 销毁。

**当前状态**：Librarian 走单卡路径，不进入此分支，所以不受影响。

**建议**：在 concerns_backlog 中记录，消化时机为 Librarian 或其他 stateful executor 进入多卡编排时。

---

## 回归验证

```
234 passed, 5 subtests passed in 6.91s
```

全量通过，无 skip、无 xfail。

---

## 结论

**Merge ready — 0 BLOCK, 1 CONCERN, 0 NOTE**

Phase 33 的 3 个 Slice 全部满足 kickoff 完成条件。1:N Planner 保持 Librarian 优先级不变，SubtaskOrchestrator 的 DAG 调度和并发执行实现扎实，Review Feedback Loop 的单次 retry 逻辑精确。单卡路径零改动，回归安全。C1 作为已知限制记录，当前不影响任何执行路径。
