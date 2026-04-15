---
author: claude
phase: 20
slice: mock-dispatch-and-execution-gating
status: draft
depends_on:
  - docs/plans/phase20/design_decision.md
  - docs/plans/phase20/risk_assessment.md
---

**TL;DR**: PR 整体 PASS。三个 slice 均与 design_decision 一致，local 路径零改动原则得到遵守（135 tests 通过含原有 115+），dispatch verdict 三条路径全部有端到端测试覆盖。1 个 CONCERN 不阻塞合并。

---

# Review Comments — Phase 20 PR #2

## 审查范围

对比对象：`feat/phase20-mock-dispatch-gating` vs `main`
参照文档：`design_decision.md`、`risk_assessment.md`、`context_brief.md`

---

## Slice 1: Contract-aware dispatch decision function (models.py)

- [PASS] `DispatchVerdict` dataclass 存在，包含 `action`、`reason`、`blocking_detail`，与 design_decision 一致
- [PASS] `evaluate_dispatch_verdict()` 是纯函数，无副作用
- [PASS] 三条决策路径实现正确：
  - `remote_candidate == False` → `local`
  - `remote_candidate == True` 且 contract 校验失败 → `blocked`（design_decision 未显式提到校验失败分支，但这是合理的防御性增强）
  - `remote_candidate == True` 且 `operator_ack_required == True` → `blocked`
  - `remote_candidate == True` 且校验通过且无需 ack → `mock_remote`
- [PASS] 单元测试覆盖了 local / blocked (ack) / mock_remote 三条路径

## Slice 2: Orchestrator dispatch interception point (orchestrator.py)

- [PASS] `_evaluate_dispatch_for_run()` 和 `_apply_blocked_dispatch_verdict()` 作为两个独立函数，拦截逻辑集中，未散布到 orchestrator 多处
- [PASS] 拦截点位于 route selection 之后、retrieval 之前——与 design_decision 中"route selection 之后、executor 调用之前"一致
- [PASS] `blocked` 路径写入 `task.dispatch_blocked` 事件到 event log，payload 包含 verdict 详情，符合四件套原则
- [PASS] `blocked` 路径设置了 `status`、`phase`、`execution_lifecycle`、`executor_status`、`topology_dispatch_status` 五个状态字段，状态语义完整
- [PASS] `local` 路径：verdict 为 local 时，代码直接跳过 blocked 分支继续走现有流程——**零改动原则得到遵守**
- [PASS] 测试 `test_run_task_blocks_remote_dispatch_when_operator_ack_is_required` 验证了 blocked 路径中 retrieval 和 execution 均未被调用

## Slice 3: MockRemoteExecutor + mock-remote route (executor.py, router.py, harness.py)

- [PASS] `run_mock_remote_executor()` 遵循现有函数签名模式（state, retrieval_items, prompt → ExecutorResult）
- [PASS] 通过 `AIWF_MOCK_REMOTE_OUTCOME` 环境变量控制成功/失败，与现有 mock executor 的环境变量模式一致
- [PASS] `mock-remote` route 在 `BUILTIN_ROUTES` 中新增，未修改任何现有 route
- [PASS] `route_for_executor` 映射中新增 `mock-remote`，不影响现有映射
- [PASS] harness.py 中新增了 `mock_remote_transport` 分支，为 mock-remote 生成专属 contract record（`operator_ack_required: False`，`contract_status: ready`），使其能通过 dispatch verdict 到达 mock_remote 路径
- [PASS] execution_fit.py 新增了 mock_remote 的 execution_site 和 transport 识别，dispatch 状态判断也扩展了 `mock_remote_dispatched`
- [PASS] 端到端测试覆盖了 success（`test_run_task_dispatches_to_mock_remote_executor_and_completes`）和 failure（`test_run_task_dispatches_to_mock_remote_executor_and_fails`）
- [CONCERN] `run_mock_remote_executor()` 的 docstring 写了 "Deterministic remote-dispatch stub used only for topology validation tests"——很好，符合"测试工具不是演进路径"的约束。但 router.py 中 `mock-remote` route 的 `execution_site` 设为 `"remote"`，这意味着在 inspect/review 路径中它会被当作真实 remote route 展示。**建议**：后续在 operator-facing 报告中标注 mock-remote 的测试性质，避免混淆

## 状态文档更新

- [PASS] `docs/active_context.md` 已更新分支、状态、产出物列表
- [PASS] 测试从 115+ 增长到 135，增量 20 个测试，覆盖充分

## Phase Guard

- [PASS] 未引入真实 remote execution（无网络、无 RPC）
- [PASS] 未引入新 CLI 命令
- [PASS] 未修改 provider routing / capability negotiation
- [PASS] 未修改设计文档正文
- [PASS] 现有 route 行为未改变
- [PASS] MockRemoteExecutor 未承载非测试职责

---

## 总结

| 类别 | PASS | CONCERN | BLOCK |
|------|------|---------|-------|
| Dispatch decision | 4 | 0 | 0 |
| Orchestrator interception | 6 | 0 | 0 |
| MockRemoteExecutor + route | 7 | 1 | 0 |
| 状态同步 | 2 | 0 | 0 |
| Phase Guard | 5 | 0 | 0 |

**评审结论：PASS，可合并。**

1 个 CONCERN 不阻塞：mock-remote route 的 `execution_site: "remote"` 在 operator 报告中可能造成混淆，建议后续 phase 在 inspect/review 中对 mock route 加标注。
