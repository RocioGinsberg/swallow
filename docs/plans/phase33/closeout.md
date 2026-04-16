---
author: codex
phase: 33
slice: subtask-orchestrator
status: final
depends_on:
  - docs/plans/phase33/kickoff.md
  - docs/plans/phase33/review_comments.md
---

## TL;DR
Phase 33 已完成实现、测试、review 与收口，当前状态为 **PR ready / Merge ready**。本轮把 Runtime v0 从单卡静态执行升级为有界 1:N `TaskCard` fan-out + `SubtaskOrchestrator` DAG 编排，并让 `ReviewGate` 正式参与 completion/retry 决策；全量回归结果为 `234 passed in 6.27s`。

# Phase 33 Closeout

## 结论

Phase 33 `Subtask Orchestrator + 并发编排 (1:N Planner + Review Feedback Loop)` 已完成实现、测试与 review 收口准备，当前状态为 **PR ready / Merge ready**。

本轮围绕 kickoff 的 3 个 slice，完成了 Runtime v0 的首个多卡执行闭环：

- `1:N Planner`：让 `plan()` 在受控条件下产出 2-4 张 `TaskCard`
- `SubtaskOrchestrator`：按 `depends_on` 构建 DAG，支持顺序 / 并发子任务执行
- `Review Feedback Loop`：让 review 失败触发一次定向 retry，并把最终结果纳入父任务 completion 判定

Claude review 初始结论为 **0 BLOCK / 1 CONCERN / 0 NOTE / Merge ready**；唯一 concern 已通过 follow-up commit `7434b04` 消化，不再阻塞当前 merge gate。

## 已完成范围

### Slice 1: TaskCard 扩展 + 1:N Planner

- `TaskCard` 新增 `depends_on` 与 `subtask_index`
- `planner.py` 现在可基于 `next_action_proposals` 和 `parallel_subtasks` hint 产出多卡
- fan-out 上限硬限制为 4 张子任务卡，避免执行图膨胀
- Librarian 路径优先级保持不变，promotion-ready knowledge 仍优先走单卡 librarian 执行链
- `tests/test_planner.py` 补齐单卡、Librarian、多卡顺序 / 并行规划回归

对应 commit：

- `611b008` `feat(phase33): add multi-card planner baseline`

### Slice 2: SubtaskOrchestrator 基线

- 新增 `src/swallow/subtask_orchestrator.py`
- `build_subtask_levels()` 使用 Kahn 拓扑排序处理依赖层级
- 无依赖卡可通过 `ThreadPoolExecutor(max_workers<=4)` 并发执行
- 子任务执行使用隔离 `TaskState` 副本，避免共享 state 引用
- 非法 DAG（重复 card、自依赖、未知依赖、循环依赖）会被显式阻断
- `tests/test_subtask_orchestrator.py` 覆盖顺序、并发、依赖收敛、失败聚合与非法 DAG

对应 commit：

- `ffb8cc8` `feat(phase33): add subtask orchestrator baseline`

### Slice 3: Review Feedback Loop + run_task 集成

- `run_task()` 现在在 `len(cards) > 1` 时切入 `SubtaskOrchestrator`
- `task.planned` / `task.review_gate` 事件新增 `card_count`、`card_ids`、`failed_card_ids` 等多卡上下文
- 任一子任务 review 失败时，系统只对失败卡执行一次定向 retry
- retry 后仍失败时会记录 `subtask.{index}.review_gate_retry_exhausted`，并让父任务进入 `failed`
- 子任务 artifacts 与事件统一回写到父任务目录 / 事件流，命名为 `subtask_{index}_attempt{n}_*` 与 `subtask.{index}.*`
- 父任务 `executor_output.md` / `executor.completed|failed` 现在会聚合展示多卡执行结果
- `tests/test_run_task_subtasks.py` 覆盖 retry 成功 / retry exhausted 端到端路径

对应 commit：

- `af3baff` `feat(phase33): add subtask review retry integration`

### Review follow-up: tempdir artifact concern

- Claude review 指出多卡子任务在 tempdir 中执行时，executor 写出的额外 artifact 可能在临时目录清理后丢失
- `_run_subtask_orchestration()` 现在会在 tempdir 清理前收集非标准 artifact，并以 `subtask_{index}_attempt{n}_` 前缀回填到父任务 artifacts 目录
- `tests/test_run_task_subtasks.py` 新增 tempdir 额外 artifact 回填验证
- `docs/concerns_backlog.md` 已将该 concern 从 Open 移到 Resolved

对应 commit：

- `7434b04` `fix(phase33): preserve subtask extra artifacts`

## 与 kickoff 完成条件对照

### 已完成的目标

- `TaskCard` 已新增 `depends_on` 和 `subtask_index`
- `plan()` 已能在规则条件满足时产出 2-4 张带依赖关系的 TaskCard
- `subtask_orchestrator.py` 已实现 DAG 调度、并发执行和结果聚合
- ReviewGate 已参与 completion 判定，失败会触发一次 retry
- `run_task()` 已在多卡场景下调用 `SubtaskOrchestrator`
- 子任务 artifact 和 event 已按约定写入父任务目录 / 事件流
- 所有现有测试通过
- 1:N planner、SubtaskOrchestrator、ReviewGate retry 集成测试已补齐

### 未继续扩张的内容

以下方向仍保持为非目标或延后项，不应视为本 phase 遗失 bug：

- Debate / Review Topology
- Literature Specialist
- LLM 驱动的智能 Planner
- 动态 executor negotiation / capability-based routing
- knowledge_store 并发锁
- retry 后自动 re-plan
- 子任务级独立持久化 state

## stop / go 判断

### stop 判断

当前 phase 可以停止继续扩张，理由如下：

- kickoff 中定义的 1:N Planner、SubtaskOrchestrator、Review Feedback Loop 已全部完成
- 单卡路径和 Librarian 路径保持回归安全，没有被多卡编排破坏
- review concern 已被 follow-up commit 消化，未留下挂起的阻塞项
- 全量测试通过，当前分支已具备 PR / merge gate 条件

### go 判断

下一轮不应继续以“顺手再补一点并发编排能力”为名扩张 Phase 33。merge 后应回到 `docs/roadmap.md` 选择新的正式 phase，并通过新的 kickoff 明确是否进入：

- Debate / Review Topology
- Literature Specialist
- 动态 executor negotiation / capability-aware routing
- stateful executor side effect 收敛（尤其是 Librarian）

## 当前稳定边界

Phase 33 closeout 后，以下边界应视为当前稳定 checkpoint：

- Planner 只做规则驱动的有界 1:N fan-out，不做 LLM 拆解
- 多卡执行上限为 4，防止 DAG 和事件流无边界膨胀
- `run_task()` 只在多卡场景下切换到 `SubtaskOrchestrator`
- Review 失败只触发一次同卡 retry，不做 re-plan
- 子任务不创建独立 task，不写独立 state / events，只回写父任务 surface
- tempdir 中产生的额外子任务 artifact 会在清理前回填到父任务 artifacts 目录
- Librarian 仍保持单卡路径，不进入多卡 stateful writeback

## 当前已知问题

- `LibrarianExecutor.execute()` 仍直接操作 state 和多层持久化；该技术债仍记录在 `docs/concerns_backlog.md`
- 当前多卡编排仍只建立通用执行闭环，不包含 Debate Topology、dynamic negotiation 或 stateful executor writeback 收敛
- knowledge_store 仍未建立并发写保护；本轮通过“子任务不写 knowledge_store”保持边界

以上问题均已在 kickoff / review / backlog 中记录，不阻塞当前 merge。

## 测试结果

最终验证结果：

```text
234 passed in 6.27s
```

补充说明：

- `tests/test_planner.py` 覆盖 1:N Planner 规则边界
- `tests/test_subtask_orchestrator.py` 覆盖 DAG、并发和失败聚合
- `tests/test_run_task_subtasks.py` 覆盖多卡 retry、retry exhausted 与额外 artifact 回填

## 规则文件同步检查

### 必查

- [x] `docs/plans/phase33/closeout.md`
- [x] `current_state.md`
- [x] `docs/active_context.md`
- [x] `./pr.md`

### 条件更新

- [ ] `AGENTS.md`
- [ ] `README.md`
- [ ] `README.zh-CN.md`

说明：

- 本轮未改变长期协作规则或对外使用方式，因此无需同步 `AGENTS.md` / README

## Git 收口建议

1. 保持当前 5 个 commit 历史，不再压缩
2. 使用根目录 `pr.md` 作为 PR 描述
3. Human push `feat/phase33-subtask-orchestrator`
4. Human 创建 PR，并确认 `review_comments.md`、`closeout.md`、`pr.md` 已反映 review follow-up 后的最终状态
5. merge 后再把 `docs/active_context.md` 与 `current_state.md` 切到下一轮 kickoff 入口状态

## 下一轮建议

merge 完成后，不要继续在 Phase 33 分支上扩张并发编排逻辑。应回到 `docs/roadmap.md` 选择下一轮方向，并以新的 kickoff 决定是否推进 Debate Topology、Literature Specialist 或更高阶的 executor negotiation 能力。
