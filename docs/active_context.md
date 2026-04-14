# Active Context

## 当前轮次

- latest_completed_track: `Core Loop` (Primary) + `Workbench / UX` (Secondary)
- latest_completed_phase: `Phase 30`
- latest_completed_slice: `Operator Checkpoint & Selective Retry`
- active_track: `none_selected`
- active_phase: `none_selected`
- active_slice: `fresh_kickoff_required`
- active_branch: `main`
- status: `merged`

---

## 当前状态说明

Phase 30 Operator Checkpoint & Selective Retry 已完成实现、review、PR 与 merge 收口，当前已回到主线并等待下一轮 kickoff。

本轮高风险面集中在 Slice 2：`run_task()` selective retry 跳阶段恢复。当前实现已补齐状态持久化、CLI 入口、checkpoint 可视化与回退测试，并已完成合并。

当前默认不应继续无边界扩张 phase30，而应重新从 `docs/roadmap.md` / `docs/system_tracks.md` 选择下一轮正式 phase。

---

## 当前关键文档

下一轮开始前，优先读取：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/roadmap.md`
4. `docs/system_tracks.md`
5. `current_state.md`
6. `docs/plans/phase30/closeout.md`

---

## 当前产出物
- `docs/roadmap.md` (claude, 2026-04-14) — 跨 phase 蓝图对齐活文档（已更新 P29 消化 + 新队列）
- `docs/plans/phase30/design_decision.md` (claude, 2026-04-14)
- `docs/plans/phase30/risk_assessment.md` (claude, 2026-04-14)
- `docs/plans/phase30/review_comments.md` (claude, 2026-04-14)
- `docs/plans/phase30/closeout.md` (codex, 2026-04-14)
- `src/swallow/orchestrator.py` (codex, 2026-04-14)
- `src/swallow/cli.py` (codex, 2026-04-14)
- `src/swallow/models.py` (codex, 2026-04-14)
- `src/swallow/checkpoint_snapshot.py` (codex, 2026-04-14)
- `src/swallow/harness.py` (codex, 2026-04-14)
- `tests/test_cli.py` (codex, 2026-04-14)

## 当前推进

已完成：

- **[Claude]** 更新 roadmap（消化 E3-1、新增 Phase 30-32 队列）并完成 Phase 30 design_decision + risk_assessment。
- **[Codex]** 完成 Slice 1-3 首轮实现：新增 `execution_phase` / `last_phase_checkpoint_at`、`task.phase_checkpoint` 事件、`task retry|rerun --from-phase` selective retry、缺失 artifact fallback、`inspect` / `review` / `checkpoint_snapshot` 可视化。
- **[Codex]** 补齐 CLI 回归测试并通过 `tests/test_cli.py` 全量验证。
- **[Claude]** 完成 Phase 30 PR review，结论：**Merge ready**，无 BLOCK，无 CONCERN。
- **[Codex]** 已整理 `docs/plans/phase30/closeout.md` 与 `pr.md`，完成 PR 收口材料。
- **[Human]** 已完成 Phase 30 merge，当前分支已回到 `main`。

## 下一步

- **[Gemini/Claude/Human]** 从 `docs/roadmap.md` 选择下一轮方向并启动新的 kickoff
- **[Codex]** 待下一轮 phase 明确后进入实现
