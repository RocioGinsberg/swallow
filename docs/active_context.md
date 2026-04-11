# Active Context

## 当前轮次

- latest_completed_track: `Core Loop`
- latest_completed_phase: `Phase 19`
- latest_completed_slice: `Handoff Contract Schema Unification`
- active_track: `Execution Topology`
- active_phase: `Phase 20`
- active_slice: `Mock Dispatch & Execution Gating`
- active_branch: `feat/phase20-mock-dispatch-gating`
- status: `implementation_complete_awaiting_review`

---

## 当前目标

启动 Phase 20：基于 Phase 19 统一的 Handoff Contract Schema，在 Orchestrator 中引入 Dispatch 拦截器与 Mock Remote Executor，实现基于 Contract 的模拟远端派发与 Execution Gating（不涉及真实 RPC 和网络传输）。

---

## 当前要解决的问题

当前系统已经具备：

- staged knowledge 的显式 review / promote / reject gate
- canonical registry / index / inspect baseline
- canonical promotion write-through、dedupe、trace-based supersede
- canonical reuse policy / retrieval integration / traceability baseline
- Handoff Contract Schema 在代码层的统一与写盘校验验证

当前待解决的是：
如何让上述“静态记录”的交接单真正驱动 Orchestrator 的分发路由（Dispatch），哪怕最初只是分发给一个 Mock 的远端沙盒节点。我们需要补齐这个拓扑决策点。

---

## 当前关键文档

当前优先读取：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/system_tracks.md`
4. `current_state.md`
5. `docs/plans/phase20/context_brief.md`

---

## 当前推进

已完成：

- Phase 18 `Remote Handoff Contract Baseline` 已完成
- Phase 19 `Handoff Contract Schema Unification` 已完成，确立了 `HandoffContractSchema` 校验。
- 架构审查已通过，推荐进入 Track 3 (Execution Topology)。
- **[Gemini]** 已产出 `docs/plans/phase20/context_brief.md`
- **[Claude]** 已产出 `docs/plans/phase20/design_decision.md` (draft)
- **[Claude]** 已产出 `docs/plans/phase20/risk_assessment.md` (draft)
- **[Claude]** 已产出 `docs/plans/phase20/kickoff.md` (draft)
- **[Claude]** 已产出 `docs/plans/phase20/breakdown.md` (draft)
- **[Codex]** 已实现 `DispatchVerdict` + `evaluate_dispatch_verdict()` 纯函数
- **[Codex]** 已实现 orchestrator dispatch interception point，blocked 路径会写入 `task.dispatch_blocked` 事件
- **[Codex]** 已实现 `mock-remote` route + mock remote executor
- **[Codex]** 已补齐 blocked / mock_remote success / mock_remote failure 测试
- `python3 -m unittest tests.test_cli` 已通过（135 tests）

## 下一步

建议下一步：
1. 由 Claude 产出 `docs/plans/phase20/review_comments.md`
2. 整理 Phase 20 implementation commit 边界
3. 组装 PR 2 并进入人工审阅
