# Active Context

## 当前轮次

- latest_completed_track: `Retrieval / Memory` (Primary) + `Workbench / UX` (Secondary)
- latest_completed_phase: `Phase 29`
- latest_completed_slice: `Provider Dialect Baseline`
- active_track: `Core Loop` (Primary) + `Workbench / UX` (Secondary)
- active_phase: `Phase 30`
- active_slice: `Operator Checkpoint & Selective Retry`
- active_branch: `main`（等待 design gate 通过后切分支）
- status: `design_review`

---

## 当前状态说明

Phase 30 Operator Checkpoint & Selective Retry 已完成方案拆解与风险评估，等待人工审批。

本轮首次包含高风险 slice（Slice 2，总分 7），改动 `run_task()` 核心流程。建议 Slice 2 完成后增加人工 gate。

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

## 当前推进

已完成：

- **[Claude]** 更新 roadmap（消化 E3-1、新增 Phase 30-32 队列）并完成 Phase 30 design_decision + risk_assessment。

## 下一步

等待人工审批 `design_decision.md` 和 `risk_assessment.md`：
- 通过：Human 从 main 切出 `feat/phase30-checkpoint-selective-retry`，通知 Codex 开始实现
- 打回：Claude 根据反馈修改方案
- 注意：Slice 2 为高风险，建议完成后增加人工 gate
