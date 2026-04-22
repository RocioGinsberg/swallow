---
author: claude
phase: 41
slice: librarian-consolidation
status: draft
depends_on:
  - docs/roadmap.md
  - docs/plans/phase40/closeout.md
  - docs/concerns_backlog.md
---

> **TL;DR** Phase 41 消化 2 条 Open concern：S1 将 `_apply_librarian_side_effects()` 中的顺序持久化改为原子替换（解决 save_state → index 中间步骤失败的一致性风险）；S2 提取 debate loop 共享核心函数（消除 ~170 行重复）。2 个 slice，低-中风险。

# Phase 41 Kickoff: Librarian 收口与结构化清理

## Track

- **Primary Track**: Core Loop
- **Secondary Track**: Retrieval / Memory

## 目标

消化 `docs/concerns_backlog.md` 中 2 条最紧迫的 Open concern，稳固内核路径的原子性和可维护性。

具体目标：

1. **S1**: 将 `_apply_librarian_side_effects()` 的持久化操作改为原子替换模式——先写临时文件再 rename，中间步骤失败时不会留下 state 与 index 不一致的状态
2. **S2**: 提取 `_run_single_task_with_debate()` 和 `_run_subtask_debate_retries()` 的共享核心为 `_debate_loop_core()`，消除约 170 行逻辑重复

## 非目标

- **不引入 WAL / 事务日志**：本阶段仅做原子替换（write-tmp + rename），不引入 WAL 机制。WAL 属于更重的持久化基础设施，留待未来有真实并发写入需求时评估
- **不修改 LibrarianExecutor 的执行逻辑**：`execute()` 方法的 side_effects 返回结构已在 Phase 36 收口完成，本阶段只优化 orchestrator 侧的持久化消费路径
- **不修改 debate loop 的行为语义**：S2 为纯重构，debate loop 的 max_rounds、熔断行为、事件类型不变
- **不修改 ReviewGate 或 ReviewFeedback**：本阶段不触碰审查逻辑

## 设计边界

### S1: Librarian 持久化原子化

**当前问题**（Phase 36 C1）：

`_apply_librarian_side_effects()` 在 `orchestrator.py:274-291` 执行以下顺序操作：

```python
# 1. 写知识决策记录
for decision_record in decision_records:
    append_knowledge_decision(...)

# 2. 写 canonical 记录 + wiki 条目
for canonical_record in canonical_records:
    append_canonical_record(...)
    persist_wiki_entry_from_record(...)

# 3. 更新 state + 写 knowledge objects
state.knowledge_objects = updated_knowledge_objects
save_state(base_dir, state)
save_knowledge_objects(base_dir, state.task_id, state.knowledge_objects)

# 4. 重建索引
save_knowledge_partition(...)
save_knowledge_index(...)
```

如果步骤 3 成功但步骤 4 失败（磁盘满、进程被 kill），state 已经指向新的 knowledge objects，但 index 还是旧的。下次读取时 index 与 state 不一致。

**修复方案**：

对步骤 3-4 引入原子替换：
- `save_state` / `save_knowledge_objects` / `save_knowledge_partition` / `save_knowledge_index` 先写到 `.tmp` 文件
- 全部写完后再逐个 `os.replace()` 到目标路径
- 如果中间任何步骤失败，`.tmp` 文件不影响现有数据

不修改步骤 1-2（append 操作本身是追加写，天然幂等——重复 append 不会破坏数据一致性，只会多一条重复记录，可被 dedupe 消化）。

### S2: Debate loop 核心提取

**当前问题**（Phase 40 C1）：

`_run_single_task_with_debate()` (orchestrator.py:603, ~80 行) 和 `_run_subtask_debate_retries()` (orchestrator.py:836, ~90 行) 核心循环结构近似：

```
while True:
    执行 → review → 通过则返回
    → round 超限则熔断
    → 生成 feedback → persist → append event → round++
```

差异仅在于：
- 执行方式不同（单任务调用 `_execute_task_card`，子任务调用 `_run_subtask_attempt`）
- artifact 命名前缀不同（`review_feedback_round_{n}` vs `subtask_{idx}_review_feedback_round_{n}`）
- 事件 event_type 前缀不同（`task.debate_*` vs `subtask.{idx}.debate_*`）

**提取方案**：

定义 `_debate_loop_core()` 接收以下回调参数：
- `execute_fn`: 执行一轮的回调，返回 `(ExecutorResult, ReviewGateResult)`
- `persist_feedback_fn`: 持久化 feedback artifact 的回调
- `persist_exhausted_fn`: 持久化 debate_exhausted artifact 的回调
- `append_round_event_fn`: 写 debate_round 事件的回调
- `append_breaker_event_fn`: 写 circuit_breaker 事件的回调

核心循环逻辑（round 管理、feedback 生成、熔断判断）在 `_debate_loop_core()` 内实现，具体的执行/持久化/事件写入通过回调参数化。

`_run_single_task_with_debate()` 和 `_run_subtask_debate_retries()` 各自准备回调后调用 `_debate_loop_core()`。

## Slice 拆解

### S1: Librarian 持久化原子化

**目标**：将 `_apply_librarian_side_effects()` 中步骤 3-4 的文件写入改为原子替换（write-tmp + os.replace）。

**影响范围**：修改 `orchestrator.py`（`_apply_librarian_side_effects`）、修改 `store.py`（新增 atomic write helper 或直接在调用处实现）

**风险评级**：
- 影响范围: 2 (Librarian 执行路径 + store 层)
- 可逆性: 1 (轻松回滚)
- 依赖复杂度: 2 (依赖 state + knowledge objects + index 的写入顺序)
- **总分: 5** — 中风险

**验收条件**：
- `_apply_librarian_side_effects()` 的文件写入使用 write-tmp + os.replace 模式
- 模拟中间步骤失败时，原有文件不被破坏（可通过 mock os.replace 抛异常验证）
- 全量 pytest 通过，Librarian 相关测试无回归
- 现有 knowledge promotion 端到端路径正常

### S2: Debate loop 核心提取

**目标**：提取 `_debate_loop_core()` 共享函数，`_run_single_task_with_debate()` 和 `_run_subtask_debate_retries()` 改为调用它。

**影响范围**：修改 `orchestrator.py`

**风险评级**：
- 影响范围: 2 (单任务 + 子任务执行路径)
- 可逆性: 1 (轻松回滚)
- 依赖复杂度: 2 (依赖 debate loop 内多个交互点)
- **总分: 5** — 中风险

**验收条件**：
- `_debate_loop_core()` 抽取完成，单任务和子任务路径均通过它执行 debate loop
- 现有 debate loop 测试（`test_debate_loop.py` + `test_run_task_subtasks.py`）全部通过，无行为变更
- 全量 pytest 通过

## Slice 依赖

```
S1 (Librarian 原子化) — 独立
S2 (Debate loop 提取) — 独立
```

S1 和 S2 互不依赖，可并行实现，但建议顺序推进以控制 review 复杂度。

## 风险总评

| Slice | 影响 | 可逆 | 依赖 | 总分 | 评级 |
|-------|------|------|------|------|------|
| S1 | 2 | 1 | 2 | 5 | 中 |
| S2 | 2 | 1 | 2 | 5 | 中 |
| **合计** | | | | **10/18** | **低-中** |

两个 slice 均为中风险但互不耦合。S1 的关键是确保原子替换的故障路径测试覆盖；S2 的关键是确保行为零变更。

## 完成条件

1. `_apply_librarian_side_effects()` 使用原子替换写入 state/knowledge/index 文件
2. `_debate_loop_core()` 提取完成，消除单任务/子任务 debate loop 重复代码
3. Phase 36 C1 和 Phase 40 C1 在 `docs/concerns_backlog.md` 中标记为 Resolved
4. 全量 pytest 通过，无回归

## Branch Advice

- 当前分支: `main`
- 建议操作: 人工审批 kickoff 后，从 `main` 切出 `feat/phase41-librarian-consolidation`
- 理由: Phase 41 修改核心执行路径，应在 feature branch 上进行
- 建议 PR 范围: S1 + S2 合并为单 PR（两个 slice 互不耦合但同属内核优化）
