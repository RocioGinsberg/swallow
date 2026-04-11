---
author: codex
phase: 20
slice: mock-dispatch-and-execution-gating
status: draft
depends_on:
  - docs/plans/phase20/kickoff.md
  - docs/plans/phase20/design_decision.md
---

**TL;DR**: Phase 20 按 3 个 slice 推进。Slice 1 是纯函数新增（低风险），Slice 2 在 orchestrator 中插入拦截点（中风险，需守住 local 零改动底线），Slice 3 新增 MockRemoteExecutor 和端到端测试。

# Phase 20 Breakdown

## 基本信息

- phase: `Phase 20`
- track: `Execution Topology`
- secondary_tracks:
  - `Core Loop`
- slice: `Mock Dispatch & Execution Gating`
- branch: `feat/phase20-mock-dispatch-gating`

---

## 总体目标

让 Phase 19 统一的 handoff contract schema 驱动实际的 dispatch 决策。orchestrator 在执行任务时读取 contract record，做出 local / mock_remote / blocked 三向决策。

---

## Affected Areas

- `src/swallow/models.py`
- `src/swallow/orchestrator.py`
- `src/swallow/executor.py`
- `src/swallow/router.py`
- `tests/test_cli.py`

---

## 默认实现顺序

1. dispatch verdict 纯函数 + 单元测试
2. orchestrator 拦截点 + 回归测试确认
3. MockRemoteExecutor + mock-remote route + 端到端测试
4. 状态同步

---

## Slice 列表

### P20-01 contract-aware dispatch decision function

#### 目标

定义 `DispatchVerdict` dataclass 和 `evaluate_dispatch_verdict()` 纯函数。

#### 建议范围

- `DispatchVerdict` 包含 `action` (local / mock_remote / blocked)、`reason`、`blocking_detail`
- 决策逻辑：
  - `remote_candidate == False` → `local`
  - `remote_candidate == True` 且 `operator_ack_required == True` 且未获 ack → `blocked`
  - `remote_candidate == True` 且 contract 校验通过 → `mock_remote`
- 纯函数，无副作用

#### 验收条件

- dataclass 和函数存在于 `models.py`
- 单元测试覆盖三条决策路径
- 不引入任何 orchestrator / executor 改动

#### 推荐提交粒度

- `feat(topology): add contract-aware dispatch verdict function`
- `test(topology): cover dispatch verdict decision paths`

---

### P20-02 orchestrator dispatch interception point

#### 目标

在 orchestrator 的 `run_task()` 中，route selection 之后、executor 调用之前，插入 dispatch verdict 检查。

#### 建议范围

- `local` → 走现有执行路径，**零改动**
- `blocked` → 跳过执行，写入 blocked 事件到 event log，设置 task state
- `mock_remote` → 路由到 MockRemoteExecutor（Slice 3 实现后才完整可用）

#### 关键约束

- 拦截逻辑集中在单一函数调用中
- 现有 115+ 测试全部通过
- blocked 事件必须写入 event log

#### 验收条件

- orchestrator 中有明确的 dispatch 拦截点
- local 路径行为与 Phase 19 完全一致
- blocked 路径有事件记录
- 全量回归测试通过

#### 推荐提交粒度

- `feat(topology): add dispatch interception to orchestrator`
- `test(topology): cover dispatch blocked path`

#### Stop/Go Signal

- **stop**: 任何现有测试失败
- **go**: 115+ 测试全部通过 + blocked 路径有事件记录

---

### P20-03 MockRemoteExecutor + 端到端测试

#### 目标

新增 MockRemoteExecutor，验证 dispatch → mock execution → 状态落盘的完整流转。

#### 建议范围

- MockRemoteExecutor 遵循现有 Executor 接口
- 支持配置模拟成功或失败
- 新增 `mock-remote` route（不修改现有 route）
- 执行结果写入 state / event log / artifacts

#### 关键约束

- 不修改现有 Executor 接口定义
- MockRemoteExecutor 是**测试工具**，docstring 明确标注
- `mock-remote` route 只在显式指定时使用，不影响默认 route selection

#### 验收条件

- dispatch → mock_remote → success 端到端测试通过
- dispatch → mock_remote → failure 端到端测试通过
- 状态落盘格式与 local executor 一致
- 现有所有测试不变

#### 推荐提交粒度

- `feat(topology): add MockRemoteExecutor and mock-remote route`
- `test(topology): cover mock remote dispatch end-to-end`

---

## 非目标

- 真实 remote execution
- 新 CLI 命令
- provider capability negotiation
- 设计文档修改
- 在 MockRemoteExecutor 上堆积行为

## Stop/Go Signal（Phase 级别）

- **stop**: 现有测试回归、MockRemoteExecutor 开始承载非测试职责
- **go**: 三条 dispatch 路径均有测试覆盖、local 路径零回归
