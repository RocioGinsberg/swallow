---
author: claude
phase: 21
slice: dispatch-policy-gate-and-mock-topology-visibility
status: draft
depends_on:
  - docs/plans/phase21/context_brief.md
  - docs/plans/phase20/closeout.md
---

**TL;DR**: Phase 21 分三个 slice 实现：① 新建 `dispatch_policy.py` 做 context_pointers 语义校验；② CLI 新增 `acknowledge` 子命令疏通 dispatch_blocked 任务；③ inspect/review 输出添加 `[MOCK-REMOTE]` 标签。逻辑层先行，交互层跟进，形成"拦截→提示→人工接管"闭环。

# Design Decision: Phase 21

## 方案总述

Phase 21 在 Phase 20 已有的 `DispatchVerdict` 拦截点上，增加真正的语义验证能力——检查交接单 `context_pointers` 引用的 artifact/知识点是否实际存在，而非盲信指针。同时在 CLI 层补齐两个缺口：被拦截任务的人工放行路径 (`acknowledge`) 和 mock-remote 执行路径的显式视觉标识。将验证逻辑与操作员交互打包实现，闭环"发现问题→拦截→提示人→人工接管"的标准工作流。

## 非目标

- 不引入网络传输、跨进程通信或真实 RPC
- 不做 Provider 能力降级 / Capability Negotiator
- 不扩展 dispatch verdict 为自动审批 / policy mutation
- 不对 mock-remote executor 赋予生产语义
- 不修改已有 local-path 执行行为

## Slice 拆解

### Slice 1: Dispatch Policy — 语义校验层

**目标**：在 dispatch verdict 评估前，对 handoff contract 的 `context_pointers` 进行语义验证，确保引用的 artifact 实际存在。

**影响范围**：
- 新建 `src/swallow/dispatch_policy.py`
  - `validate_handoff_semantics(contract, task_dir) -> PolicyResult`
  - 遍历 `context_pointers`，逐条检查指向的文件/artifact 是否存在于 task artifacts 目录
  - 返回 `PolicyResult(valid: bool, errors: list[str])`
- 修改 `src/swallow/orchestrator.py`
  - 在 `_evaluate_dispatch_for_run()` 中，调用 `validate_handoff_semantics()` 作为前置检查
  - 如果校验失败，直接生成 `DispatchVerdict(action="blocked", reason=..., blocking_detail=errors)`
  - 不改变现有 blocked/local/mock_remote 三路逻辑，只在入口前增加一道过滤
- 新增 `tests/test_dispatch_policy.py`
  - 测试 context_pointers 全部有效 → pass
  - 测试 context_pointers 含无效引用 → blocked
  - 测试 context_pointers 为空列表 → pass（空指针不阻塞）

**风险评级**：
- 影响范围: 2（单模块，但 orchestrator 是核心路径）
- 可逆性: 1（新文件 + 调用入口，回滚只需删除调用）
- 依赖复杂度: 2（依赖 task artifacts 目录结构）
- **总分: 5 — 中低风险**

**依赖**：无前置 slice 依赖。

**验收条件**：
- `validate_handoff_semantics()` 能正确识别死链指针并返回错误
- orchestrator 在语义校验失败时生成 blocked verdict
- 已有 local-path 和 mock-remote-path 测试不受影响（回归不破）

---

### Slice 2: CLI `acknowledge` 命令 — 人工放行路径

**目标**：为 `dispatch_blocked` 状态的任务提供 CLI 疏通命令，操作员可在确认后强制放行。

**影响范围**：
- 修改 `src/swallow/cli.py`
  - 新增 `swl task acknowledge <task_id>` 子命令
  - 读取任务状态，校验当前 status == `dispatch_blocked`
  - 将状态转换为 `running`，phase 转换为 `retrieval`（回到正常执行入口）
  - topology_dispatch_status 设为 `acknowledged`（新增枚举值）
  - 记录 event: `task.dispatch_acknowledged`
- 修改 `src/swallow/models.py`
  - `topology_dispatch_status` 允许值新增 `"acknowledged"`
- 修改 `src/swallow/orchestrator.py`
  - `resume` / `retry` 逻辑中，对 `acknowledged` 状态的任务走正常 local dispatch（跳过已失败的语义校验）
- 新增测试
  - acknowledge 一个 dispatch_blocked 任务 → 状态正确转换
  - acknowledge 一个非 dispatch_blocked 任务 → 报错拒绝
  - acknowledged 任务可正常 resume → 完整执行路径

**状态流转设计**：
```
dispatch_blocked --[acknowledge]--> running (phase=retrieval, dispatch_status=acknowledged)
                                    --> 正常 local 执行流程
```

选择回到 `retrieval` 而非 `pending` 的理由：acknowledged 意味着操作员确认了风险，应直接进入执行流程而非重新排队。不引入"强制 mock_remote"路径，避免 context_brief 中警告的状态循环死锁。

**风险评级**：
- 影响范围: 2（CLI + orchestrator + models）
- 可逆性: 2（状态机新增值需要额外清理）
- 依赖复杂度: 2（依赖 Slice 1 的 blocked 行为）
- **总分: 6 — 中等风险**

**依赖**：逻辑上依赖 Slice 1（需要有 policy-blocked 任务来测试），但代码上可利用 Phase 20 已有的 blocked 路径独立实现。建议 Slice 1 先行。

**验收条件**：
- `swl task acknowledge <id>` 能将 dispatch_blocked 任务转为可执行状态
- 状态转换产生正确的 event 记录
- acknowledged 任务的后续 resume/run 能正常完成

---

### Slice 3: Mock-Remote 可视化标识

**目标**：在 CLI inspect/review 输出中，对 mock-remote 路径的任务添加显式 `[MOCK-REMOTE]` 标签，消除与真实 remote execution 的视觉混淆。

**影响范围**：
- 修改 `src/swallow/cli.py`
  - `inspect` 命令的 topology 渲染部分：当 `transport_kind == "mock_remote_transport"` 或 `topology_dispatch_status == "mock_remote_dispatched"` 时，在 route/transport 行前添加 `[MOCK-REMOTE]` 标签
  - `review` 命令同理（如有 topology 展示区域）
  - `dispatch` 报告命令：在输出中标注 mock 属性
- 新增测试
  - inspect 一个 mock-remote 任务 → 输出包含 `[MOCK-REMOTE]`
  - inspect 一个 local 任务 → 输出不包含该标签
  - inspect 一个 dispatch_blocked 任务 → 输出体现 blocked 状态

**风险评级**：
- 影响范围: 1（仅 CLI 渲染层）
- 可逆性: 1（纯展示变更）
- 依赖复杂度: 1（无外部依赖）
- **总分: 3 — 低风险**

**依赖**：无硬依赖，可独立实现。但建议在 Slice 1/2 之后，以便一次性验证完整的视觉体验。

**验收条件**：
- mock-remote 任务在 inspect 输出中有明确 `[MOCK-REMOTE]` 标识
- local 任务和 blocked 任务不受影响
- 已有 CLI 测试不破

---

## 实现顺序

```
Slice 1: dispatch_policy.py (语义校验)
    ↓
Slice 2: acknowledge CLI 命令 (人工放行)
    ↓
Slice 3: [MOCK-REMOTE] 可视化标识
```

Slice 1→2 有逻辑依赖（先有拦截才有疏通）。Slice 3 独立但建议最后做。

## Branch Advice

- 当前分支: `main`
- 建议操作: 新建分支
- 建议分支名: `feat/phase21-dispatch-policy-gate`
- 理由: Phase 21 涵盖 3 个 slice，建议单分支承载全部改动，PR 范围 = Slice 1 + 2 + 3
- PR 策略: 单 PR 合入，因三个 slice 紧密关联且总体风险可控

## Phase-Guard 检查

- [x] 方案未越出 context_brief 定义的 goals
- [x] 方案未触及 non-goals（无真实 remote/RPC/provider negotiation）
- [x] Slice 数量 = 3，在建议上限 ≤5 内
- 无 `[SCOPE WARNING]`
