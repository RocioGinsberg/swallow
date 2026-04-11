---
author: claude
phase: 20
slice: mock-dispatch-and-execution-gating
status: draft
depends_on:
  - docs/plans/phase20/context_brief.md
---

**TL;DR**: Phase 20 在 Orchestrator 中引入 contract-aware dispatch 决策函数和拦截点，配合 MockRemoteExecutor 验证完整的 dispatch → mock execution → 状态落盘流程。3 个 slice，改动集中在 orchestrator.py、executor.py、models.py。

---

# Design Decision — Phase 20

## Track 确认

- **Primary Track**: Execution Topology
- **Secondary Track**: Core Loop
- **Slice**: Mock Dispatch & Execution Gating

## 设计总述

Phase 19 让 handoff contract 成为了可定义、可验证的 schema truth。Phase 20 的目标是让这个 truth **驱动行为**——orchestrator 在执行任务时，读取 contract record，做出"本地执行 / mock 远端派发 / 拦截拒绝"的三向决策。

这不是真实 remote execution。MockRemoteExecutor 是一个**测试工具**，用来验证 dispatch 路径的状态流转是否正确，不是 remote executor 的演进基础。

---

## 方案拆解

### Slice 1: Contract-aware dispatch decision function

**目标**：一个纯函数，输入 contract record dict，输出 dispatch verdict。

**具体内容**：

```python
@dataclass
class DispatchVerdict:
    action: str          # "local" | "mock_remote" | "blocked"
    reason: str
    blocking_detail: str  # 非空仅当 action == "blocked"

def evaluate_dispatch_verdict(contract: dict) -> DispatchVerdict:
    ...
```

决策逻辑：
- `remote_candidate == False` → `local`（绝大多数现有任务）
- `remote_candidate == True` 且 `operator_ack_required == True` 且未获 ack → `blocked`
- `remote_candidate == True` 且 contract 校验通过 → `mock_remote`

**影响范围**：`src/swallow/models.py`（新增 DispatchVerdict dataclass + evaluate 函数）
**验收条件**：纯函数，无副作用，有完整的单元测试覆盖三条路径
**风险评级**：影响 1 / 可逆 1 / 依赖 1 = **总分 3（低风险）**

---

### Slice 2: Orchestrator dispatch interception point

**目标**：在 orchestrator 的执行路径中嵌入 dispatch verdict 检查。

**具体内容**：
- 在 `run_task()` 的执行阶段（route selection 之后、executor 调用之前）插入 verdict 评估
- `local` → 走现有执行路径，完全不变
- `blocked` → 跳过执行，写入 blocked 事件到 event log，设置 task state 为 `dispatch_blocked`
- `mock_remote` → 路由到 MockRemoteExecutor（Slice 3）

**关键约束**：
- **现有 local 路径必须零改动**：verdict == "local" 时的代码路径应与 Phase 19 完全一致，不能因为插入 verdict 检查而影响现有行为
- 拦截点应作为一个明确的函数调用，不要散布在 orchestrator 的多个位置
- blocked 状态必须写入 event log（符合四件套原则）

**影响范围**：`src/swallow/orchestrator.py`（插入拦截点）、`src/swallow/models.py`（可能新增 task state 值）
**验收条件**：现有 115+ 测试全部通过（local 路径无回归），blocked 路径有事件记录
**风险评级**：影响 2 / 可逆 1 / 依赖 2 = **总分 5（中风险）**

---

### Slice 3: MockRemoteExecutor + 端到端测试

**目标**：一个遵循现有 Executor 接口的 mock 实现，用于验证 dispatch → execution → 状态落盘的完整流转。

**具体内容**：
- MockRemoteExecutor 接收任务，模拟成功或失败（通过配置参数控制）
- 执行结果写入 state / event log / artifacts，与 local executor 的落盘格式一致
- 不引入任何网络、序列化、进程间通信逻辑

**关键约束**：
- **必须遵循现有 Executor 接口**（executor.py 中的抽象），不为 mock 修改接口
- MockRemoteExecutor 应放在 `src/swallow/executor.py` 中，与现有 executor 并列
- 在 router.py 中新增 `mock-remote` route，但**不修改任何现有 route 的行为**

**影响范围**：`src/swallow/executor.py`、`src/swallow/router.py`（新增 route）、`tests/test_cli.py`
**验收条件**：
- dispatch → mock_remote → success 的完整状态流转测试
- dispatch → mock_remote → failure 的完整状态流转测试
- dispatch → blocked 的事件记录测试
- 现有 local 路径所有测试不变
**风险评级**：影响 2 / 可逆 1 / 依赖 2 = **总分 5（中风险）**

---

## 实现顺序

Slice 1 → Slice 2 → Slice 3（严格顺序）

## 非目标

- 不实现真实 remote execution（无网络、无 RPC、无跨机器 transport）
- 不修改 provider routing / capability negotiation
- 不引入自动 dispatch（dispatch 决策基于 contract record 中已有字段，不引入新的动态判断）
- 不修改设计文档正文
- MockRemoteExecutor 是**测试工具，不是执行器演进路径**——后续真实 remote executor 应从头设计，不应在 mock 上堆积行为
- 不引入新的 operator-facing CLI 命令（dispatch verdict 通过现有 inspect/review 路径可见即可）

---

## Branch Advice

- **建议分支名**：`feat/phase20-mock-dispatch-gating`
- **建议操作**：从 `main` 切出新分支
- **PR 策略（方案 C）**：
  - **PR 1（Planning）**：context_brief + design_decision + risk_assessment + kickoff + breakdown → 人工审批设计
  - **PR 2（Implementation）**：代码实现 + review_comments → 人工审批合并
