# Active Context

## 当前轮次

- latest_completed_track: `Evaluation / Policy` (Primary) + `Workbench / UX` (Secondary)
- latest_completed_phase: `Phase 21`
- latest_completed_slice: `Dispatch Policy Gate & Mock Topology Visibility`
- active_track: `to_be_selected`
- active_phase: `none_selected`
- active_slice: `fresh_kickoff_required`
- active_branch: `main`
- status: `phase_closed`

---

## 当前目标

Phase 21 已完成并合并到 `main`。当前默认目标不是继续扩张 Phase 21，而是从系统 track 重新选择下一轮 kickoff。

---

## 当前要解决的问题

当前系统已经具备：

- staged knowledge 的显式 review / promote / reject gate
- canonical registry / index / inspect baseline
- canonical promotion write-through、dedupe、trace-based supersede
- canonical reuse policy / retrieval integration / traceability baseline
- Handoff Contract Schema 在代码层的统一与写盘校验验证
- 基于 Handoff Contract 的 DispatchVerdict 和 Mock Remote 执行路径
- dispatch 前 `context_pointers` 语义校验
- `dispatch_blocked` -> `acknowledge` -> 本地恢复执行路径
- `[MOCK-REMOTE]` CLI 视图区分

当前待解决的是：
下一轮应选择哪个 active track / phase / slice，而不是继续无边界扩张已完成的 Phase 21。

---

## 当前关键文档

当前优先读取：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/system_tracks.md`
4. `current_state.md`
5. `docs/plans/phase21/closeout.md`

---

## 当前产出物

- docs/plans/phase21/context_brief.md (gemini, 2026-04-12)
- docs/plans/phase21/design_decision.md (claude, 2026-04-12)
- docs/plans/phase21/risk_assessment.md (claude, 2026-04-12)
- docs/plans/phase21/review_comments.md (claude, 2026-04-12)
- docs/plans/phase21/closeout.md (codex, 2026-04-12)
- .codex/session_bootstrap.md (codex, 2026-04-12)
- .agents/codex/role.md (codex, 2026-04-12)
- .agents/codex/rules.md (codex, 2026-04-12)
- .agents/shared/state_sync_rules.md (codex, 2026-04-12)
- .agents/workflows/feature.md (codex, 2026-04-12)
- AGENTS.md (codex, 2026-04-12)
- pr.md (codex, 2026-04-12)

## 当前推进

已完成：

- Phase 21 已完成、review 通过并合并到 `main`。
- `GEMINI.md` 的专属规则已更新，引入了 **"Primary Track + Strong Secondary Track"** 的打包模式以减少碎片化。
- **[Gemini]** 已产出 `docs/plans/phase21/context_brief.md`
- **[Claude]** 已产出 `design_decision.md`（3 slice 拆解）和 `risk_assessment.md`（无高风险项）
- **[Claude]** 已产出 `review_comments.md`，结论 **PASS, mergeable**
- **[Codex]** 角色控制文档已更新：git 提交与 PR 创建执行权收回 Human，Codex 改为按 slice 提供 commit 建议并维护 `./pr.md`
- **[Codex]** 已补充分支切换时机：design gate 通过后，Human 先从 `main` 切到 feature branch，再开始实现；并在 workflow 中写明每个 slice 的人工提交节奏点
- **[Codex]** 已补充 PR / merge 节奏：`push -> create PR -> Claude review -> 如有修改继续更新 ./pr.md 和分支提交 -> Human merge`，并要求 merge 前校验 `./pr.md` 与 `review_comments.md` 一致
- **[Codex]** 已补充 Phase 21 closeout，并将恢复入口切回新一轮 kickoff 待选状态

## 下一步

- 从 `docs/system_tracks.md` 重新选择下一轮 active track / phase / slice
- 为下一轮工作编写 fresh kickoff，而不是继续扩张已完成的 Phase 21
