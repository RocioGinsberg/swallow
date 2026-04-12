# Active Context

## 当前轮次

- latest_completed_track: `Execution Topology`
- latest_completed_phase: `Phase 20`
- latest_completed_slice: `Mock Dispatch & Execution Gating`
- active_track: `Evaluation / Policy` (Primary) + `Workbench / UX` (Secondary)
- active_phase: `Phase 21`
- active_slice: `Dispatch Policy Gate & Mock Topology Visibility`
- active_branch: `main`（待创建 `feat/phase21-dispatch-policy-gate`）
- status: `design_produced`

---

## 当前目标

启动 Phase 21：基于 Phase 20 的 Mock Dispatch，在调度前引入真正的语义验证策略 (Policy Gate) 拦截非法的交接单；并在 CLI 层面补充拦截任务的人工放行命令 (`acknowledge`) 与可视化的 `[MOCK-REMOTE]` 区分标识，形成逻辑与交互的完整闭环。

---

## 当前要解决的问题

当前系统已经具备：

- staged knowledge 的显式 review / promote / reject gate
- canonical registry / index / inspect baseline
- canonical promotion write-through、dedupe、trace-based supersede
- canonical reuse policy / retrieval integration / traceability baseline
- Handoff Contract Schema 在代码层的统一与写盘校验验证
- 基于 Handoff Contract 的 DispatchVerdict 和 Mock Remote 执行路径

当前待解决的是：
如何在调度器做出 Dispatch 决策前，对交接单（如 `context_pointers` 指向的对象是否存在）进行深层的语义校验；并在任务被 `blocked` 时，提供一个顺畅的 CLI 视图区分与人工疏通 (`acknowledge`) 工作流。

---

## 当前关键文档

当前优先读取：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/system_tracks.md`
4. `current_state.md`
5. `docs/plans/phase21/context_brief.md`

---

## 当前产出物

- docs/plans/phase21/context_brief.md (gemini, 2026-04-12)
- docs/plans/phase21/design_decision.md (claude, 2026-04-12)
- docs/plans/phase21/risk_assessment.md (claude, 2026-04-12)
- .codex/session_bootstrap.md (codex, 2026-04-12)
- .agents/codex/role.md (codex, 2026-04-12)
- .agents/codex/rules.md (codex, 2026-04-12)
- .agents/shared/state_sync_rules.md (codex, 2026-04-12)
- .agents/workflows/feature.md (codex, 2026-04-12)
- AGENTS.md (codex, 2026-04-12)
- pr.md (codex, 2026-04-12)

## 当前推进

已完成：

- Phase 20 `Mock Dispatch & Execution Gating` 测试通过且评审完成（等待合入或基于其上下文推进）。
- `GEMINI.md` 的专属规则已更新，引入了 **"Primary Track + Strong Secondary Track"** 的打包模式以减少碎片化。
- **[Gemini]** 已产出 `docs/plans/phase21/context_brief.md`
- **[Claude]** 已产出 `design_decision.md`（3 slice 拆解）和 `risk_assessment.md`（无高风险项）
- **[Claude]** AGENTS.md 已添加两次提交节奏规则
- **[Codex]** 角色控制文档已更新：git 提交与 PR 创建执行权收回 Human，Codex 改为按 slice 提供 commit 建议并维护 `./pr.md`

## 下一步

等待人工审批 `design_decision.md` 和 `risk_assessment.md`。通过后由 Codex 在 `feat/phase21-dispatch-policy-gate` 分支上开始实现。
