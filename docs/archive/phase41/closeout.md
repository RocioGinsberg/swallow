---
author: codex
phase: 41
slice: all
status: final
depends_on:
  - docs/plans/phase41/kickoff.md
  - docs/plans/phase41/risk_assessment.md
  - docs/concerns_backlog.md
---

## TL;DR
Phase 41 已完成实现、review 与 PR 收口准备，当前状态为 **merge ready / PR sync ready**。本轮聚焦内核收口：S1 将 Librarian 持久化链路改为批量原子提交，解决 `save_state -> index` 中间失败可能导致的不一致；S2 提取共享 `_debate_loop_core()`，统一单任务与子任务 debate loop 的 round 管理、feedback 生成与 breaker 判定。Claude review 结论为 `0 BLOCK / 0 CONCERN / 1 NOTE / Merge ready`。当前全量回归基线为 `303 passed in 6.72s`。

# Phase 41 Closeout

## 结论

Phase 41 `Librarian Consolidation` 已完成实现、review 与验证，当前分支状态为 **merge ready / PR sync ready**。

本轮围绕 kickoff 定义的 2 个 slice，交付了两个明确的内核修正：

- S1：Librarian 持久化从顺序 best-effort 写入升级为批量原子提交，失败时回滚到旧文件状态
- S2：单任务与子任务 debate loop 提取共享核心，降低后续 review 策略调整的双点维护成本

Claude review 已完成，结论为 `0 BLOCK / 0 CONCERN / 1 NOTE / Merge ready`。`pr.md` 已同步为本轮的 PR 草稿，可直接作为 PR 描述更新依据。

## 已完成范围

### Slice 1: Librarian Atomic Persistence

- `src/swallow/store.py` 新增 `apply_atomic_text_updates()`，支持多文件 `write-tmp + os.replace + rollback`
- `src/swallow/orchestrator.py` 的 `_apply_librarian_side_effects()` 改为先构造完整写入计划，再一次性提交
- 原子提交范围覆盖：
  - `state.json`
  - `knowledge_objects.json`
  - knowledge evidence / wiki store entries
  - `knowledge_partition.json`
  - `knowledge_index.json`
  - `canonical_knowledge/index.json`
  - `canonical_knowledge/reuse_policy.json`
- `tests/test_librarian_executor.py` 新增故障路径测试，验证 `os.replace()` 中途失败时旧文件恢复且临时文件被清理

对应 commit：

- `2465336` `fix(librarian): make persistence updates atomic`

### Slice 2: Debate Loop Core Extraction

- `src/swallow/orchestrator.py` 新增 `_build_debate_last_feedback()` 与 `_debate_loop_core()`
- `_run_single_task_with_debate()` 与 `_run_subtask_debate_retries()` 改为调用共享核心
- 保持不变的边界：
  - `max_rounds = 3`
  - `task.debate_round` / `task.debate_circuit_breaker`
  - `subtask.{index}.debate_round` / `subtask.{index}.debate_circuit_breaker`
  - feedback artifact 命名
  - `waiting_human` 收口语义
  - executor failure 不进入 debate
- `tests/test_debate_loop.py` 与 `tests/test_run_task_subtasks.py` 零修改通过

对应 commit：

- `923c81e` `refactor(debate): extract shared loop core`

## 与 kickoff 完成条件对照

### 已完成的目标

- `_apply_librarian_side_effects()` 已改为原子提交 `state / knowledge / index` 路径
- 中间步骤失败时，旧文件保持不变且无残留 `.tmp` / `.restore`
- `_debate_loop_core()` 已提取完成，单任务与子任务路径均通过它执行 debate loop
- 现有 debate loop 测试零修改通过
- 全量 `pytest` 通过

### 未继续扩张的内容

以下方向仍明确不在本 phase 范围内：

- WAL / checkpoint-level 事务日志
- LibrarianExecutor 语义增强或冲突仲裁
- debate loop 的动态轮次策略
- debate retry telemetry 与 Meta-Optimizer 聚合修正
- Reviewer Agent、共识拓扑或多模型审查

## Backlog 同步

本轮直接消化了两条 Open concern，现已从 `Open` 移入 `Resolved`：

- Phase 36 C1：`_apply_librarian_side_effects()` 中 `save_state -> index` 顺序写入的一致性风险
- Phase 40 C1：单任务与子任务 debate loop 代码重复

仍保留未解决 concern：

- Phase 38 C1：fallback 成本未计入 Meta-Optimizer route stats
- Phase 40 C2：debate retry telemetry 仍混入正常 route health 聚合

## Review Follow-up

- Claude review 已完成：`0 BLOCK / 0 CONCERN / 1 NOTE / Merge ready`
- N1：全量 `pytest` 已通过，自动测试环境正常，无额外代码 follow-up
- 当前无新增 concern，也无需要回写 backlog 的 review 阻塞项

## Stop / Go 判断

### Stop 判断

当前 phase 应停止继续扩张，理由如下：

- kickoff 定义的 2 个 slice 已全部完成，并已按 slice 独立提交
- S1 已把最关键的数据一致性风险压缩到 append-only 路径之外
- S2 已消除 debate loop 的双点维护结构重复
- 再继续扩张会自然滑向 Phase 42 的成本遥测，或 Phase 43 的 ReAct 降级，不属于本轮范围

### Go 判断

下一步应按如下顺序推进：

1. Human 用 `pr.md` 更新 PR 描述
2. Human push 当前分支
3. Human 决定 merge

## 当前稳定边界

Phase 41 closeout 后，以下边界应视为当前实现候选的稳定 checkpoint：

- Librarian append-only 路径仍保持非事务化；原子提交只覆盖 state / knowledge / index / policy 文件
- knowledge evidence / wiki store 的增删改已纳入同一批次提交，不再先于主 state 落盘
- debate loop 行为未变化，只抽了共享控制流
- 单任务与子任务 debate 的事件 payload、artifact 命名和 breaker 条件保持兼容

## 当前已知问题

- Librarian append 操作（decision / canonical registry）仍是顺序追加，尚未提升到 WAL 或全链路事务级保护
- `apply_atomic_text_updates()` 会在失败时做文件内容级恢复，但不提供 crash-after-replace 的进程外恢复机制
- debate retry telemetry 混入 Meta-Optimizer route health 聚合的问题仍存在，待后续 phase 处理
- fallback `token_cost` 统计仍未并入 Meta-Optimizer route stats

以上问题均不阻塞当前进入 merge 阶段。

## 测试结果

最终验证结果：

```text
303 passed, 5 subtests passed in 6.72s
```

补充说明：

- `tests/test_librarian_executor.py` 覆盖 Librarian 原子提交故障路径
- `tests/test_debate_loop.py` 覆盖单任务 debate retry / 熔断
- `tests/test_run_task_subtasks.py` 覆盖子任务 targeted retry / 熔断 / 非 debate executor failure
- 全量回归已通过

## 规则文件同步检查

### 必查

- [x] `docs/plans/phase41/closeout.md`
- [x] `docs/plans/phase41/kickoff.md`
- [x] `docs/plans/phase41/risk_assessment.md`
- [x] `docs/active_context.md`
- [x] `docs/concerns_backlog.md`
- [x] `./pr.md`

### 条件更新

- [x] `docs/plans/phase41/review_comments.md`
- [ ] `AGENTS.md`
- [ ] `README.md`
- [ ] `README.zh-CN.md`

说明：

- Claude review 已完成，`review_comments.md` 已同步为 `final`
- 本轮未改变长期协作规则与 README 级对外叙述，暂不更新 `AGENTS.md` / README

## Git / PR 建议

1. 使用当前根目录 `pr.md` 作为 PR 描述草案
2. 当前 PR 描述应标记为 `0 BLOCK / 0 CONCERN / 1 NOTE / Merge ready`
3. Human 根据当前 review 结论决定 merge

## 下一轮建议

如果 Phase 41 merge 完成，下一轮应优先回到 roadmap，推进本地栈健康检查 / 真实成本遥测，或按优先级处理 debate retry telemetry concern，但不应在当前分支继续追加 Librarian 或 debate 扩张。
