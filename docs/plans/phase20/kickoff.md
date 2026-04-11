---
author: codex
phase: 20
slice: mock-dispatch-and-execution-gating
status: draft
depends_on:
  - docs/plans/phase20/design_decision.md
  - docs/plans/phase20/risk_assessment.md
---

**TL;DR**: Phase 20 进入实现态，primary track 选定为 `Execution Topology`。本轮只做 contract-aware dispatch 决策 + orchestrator 拦截点 + MockRemoteExecutor，不扩张到真实 remote execution。

# Phase 20 Kickoff

## 基本信息

- phase: `Phase 20`
- track: `Execution Topology`
- secondary_tracks:
  - `Core Loop`
- slice: `Mock Dispatch & Execution Gating`
- status: `kickoff`
- recommended_branch: `feat/phase20-mock-dispatch-gating`

---

## 启动背景

Phase 19 已完成 `Handoff Contract Schema Unification`，系统已经具备：

- 统一的 `HandoffContractSchema` dataclass（goal / constraints / done / next_steps / context_pointers）
- `remote_handoff_contract.json` 的写盘校验
- 三份设计文档的 Schema Alignment Note

但 contract 目前只是"记录"——orchestrator 不会读取 contract 来决定任务去哪执行。Phase 20 要补齐这个决策点。

---

## 当前问题

当前仓库里已有 handoff contract 的 schema truth 和写盘校验，但还缺少：

- 一个基于 contract record 做出 dispatch 决策的纯函数
- orchestrator 中的 dispatch 拦截点（route selection 之后、executor 调用之前）
- 一个遵循现有接口的 MockRemoteExecutor，用来验证 dispatch → execution → 状态落盘的完整流转

---

## 本轮目标

1. 定义 `DispatchVerdict` dataclass 和 `evaluate_dispatch_verdict()` 纯函数
2. 在 orchestrator 的 `run_task()` 中插入 dispatch verdict 检查
3. 新增 MockRemoteExecutor 和 `mock-remote` route
4. 验证 local / mock_remote / blocked 三条路径的完整状态流转

---

## 本轮非目标

- 不实现真实 remote execution（无网络、无 RPC、无跨机器 transport）
- 不修改 provider routing / capability negotiation
- 不引入自动 dispatch 或 dispatch policy mutation
- 不修改设计文档正文
- 不引入新的 operator-facing CLI 命令
- MockRemoteExecutor 是**测试工具，不是执行器演进路径**

---

## 设计边界

### 应保持稳定的部分

- 现有 local 执行路径（verdict == "local" 时零改动）
- state / events / artifacts 分层
- inspect / review / control / recovery 路径
- 现有 4 条 route（local-codex / local-mock / local-note / local-summary）的行为

### 本轮新增能力应满足

- dispatch verdict 是纯函数，无副作用
- orchestrator 拦截点集中在单一函数调用，不散布多处
- blocked 状态写入 event log（符合四件套原则）
- MockRemoteExecutor 遵循现有 Executor 接口

---

## 影响范围

- `src/swallow/models.py`
- `src/swallow/orchestrator.py`
- `src/swallow/executor.py`
- `src/swallow/router.py`
- `tests/test_cli.py`
- `docs/active_context.md`
- `docs/plans/phase20/*`

---

## 完成条件

1. `evaluate_dispatch_verdict()` 存在且覆盖 local / mock_remote / blocked 三条路径
2. orchestrator 中有明确的 dispatch 拦截点
3. MockRemoteExecutor 存在且遵循 Executor 接口
4. 现有 115+ 测试全部通过（零回归）
5. 新增测试覆盖 dispatch → mock_remote → success/failure 和 dispatch → blocked 场景

---

## 下一步

本 kickoff 落地后，下一步应完成 `breakdown.md`，然后进入实现。
