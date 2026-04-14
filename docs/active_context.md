# Active Context

## 当前轮次

- latest_completed_track: `Retrieval / Memory` (Primary) + `Workbench / UX` (Secondary)
- latest_completed_phase: `Phase 29`
- latest_completed_slice: `Provider Dialect Baseline`
- active_track: `Core Loop` (Primary) + `Workbench / UX` (Secondary)
- active_phase: `Phase 30`
- active_slice: `Operator Checkpoint & Selective Retry`
- active_branch: `feat/phase30-checkpoint-selective-retry`
- status: `review_pending`

---

## 当前状态说明

Phase 30 Operator Checkpoint & Selective Retry 首轮实现已完成，当前进入 review / 收口准备。

本轮高风险面集中在 Slice 2：`run_task()` selective retry 跳阶段恢复。当前实现已补齐状态持久化、CLI 入口、checkpoint 可视化与回退测试，待 review 确认后再进入 PR 收口。

Phase 30 的 git 节奏要求额外强调如下：
- 本轮按 Slice 1 / Slice 2 / Slice 3 分 3 次 commit
- 每个 slice 完成后先审查并提交，再进入下一个 slice
- 禁止把 3 个 slices 压成一次大包上传

---

## 当前关键文档

下一轮开始前，优先读取：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/roadmap.md`
4. `docs/system_tracks.md`
5. `current_state.md`
6. `docs/plans/phase29/closeout.md`

---

## 当前产出物
- `docs/roadmap.md` (claude, 2026-04-14) — 跨 phase 蓝图对齐活文档（已更新 P29 消化 + 新队列）
- `docs/plans/phase30/design_decision.md` (claude, 2026-04-14)
- `docs/plans/phase30/risk_assessment.md` (claude, 2026-04-14)
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

## 下一步

- **[Claude]** 开始 Phase 30 review，重点检查 selective retry fallback、checkpoint truth 与 operator surface 一致性
- **[Codex]** 待 review 结论后整理 `pr.md` 与 closeout 材料
