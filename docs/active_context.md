# Active Context

## 当前轮次

- latest_completed_track: `Evaluation / Policy` (Primary) + `Core Loop` (Secondary)
- latest_completed_phase: `Phase 47`
- latest_completed_slice: `Consensus & Policy Guardrails (v0.5.0)`
- active_track: `none_selected`
- active_phase: `none_selected`
- active_slice: `fresh_kickoff_required`
- active_branch: `main`
- status: `phase47_closed_tagged_waiting_next_kickoff`

---

## 当前状态说明

Phase 47 已完成 merge，`v0.5.0` tag 也已创建并推送。`main` 当前稳定基线已吸收 `Consensus & Policy Guardrails` 的全部实现：N-Reviewer 共识 gate、TaskCard 级 `token_cost_limit` 成本护栏、`swl task consistency-audit` 只读一致性抽检入口，以及对应的回归与 eval 基线。当前稳定验证基线为默认 pytest `359 passed, 7 deselected`，eval pytest `7 passed, 359 deselected`。

`v0.5.0` tag 对齐文件修改已完成：`AGENTS.md`、`README.md` 与 `README.zh-CN.md` 的 tag 级描述现已同步到 Phase 47 merge 后的主线事实。`docs/active_context.md` 与 `current_state.md` 也已切到 merge + tag 完成后的稳定收口状态。下一轮工作不默认继续扩张 Phase 47，而应回到 `docs/roadmap.md` 重新选择 active track / phase / slice。

---

## 当前关键文档

当前进入下一轮 kickoff 前，优先读取：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/roadmap.md`
4. `current_state.md`
5. `docs/plans/phase47/closeout.md`

仅在需要时再读取：

- `docs/plans/phase47/review_comments.md`
- `docs/plans/phase47/design_decision.md`
- `docs/plans/phase47/kickoff.md`
- `docs/plans/phase47/context_brief.md`
- `docs/plans/phase47/risk_assessment.md`
- `README.md`
- `README.zh-CN.md`
- `docs/concerns_backlog.md`

---

## 当前推进

已完成：

- **[Human/Codex]** 完成 Phase 46 并合并至 `main`，打 tag `v0.4.0`。
- **[Gemini]** 完成 Phase 47 `context_brief.md` 与 `roadmap.md` 增量更新。
- **[Claude]** 已产出 Phase 47 `kickoff.md`、`design_decision.md`、`risk_assessment.md`、`review_comments.md`。
- **[Codex]** 已完成 Phase 47 全部实现、review follow-up 吸收、closeout 与回归复验。
- **[Human]** 已完成 Phase 47 merge，`feat/phase47_consensus-guardrails` 已并入 `main`。
- **[Codex]** 已完成 `v0.5.0` tag 对齐：`AGENTS.md`、`README.md`、`README.zh-CN.md` 已同步到 merge 后状态。
- **[Human]** 已创建并推送 tag `v0.5.0`。
- **[Codex]** 已更新 `current_state.md`，将稳定恢复入口切到 Phase 47 / `v0.5.0` checkpoint。

## 当前产出物

- `docs/plans/phase47/context_brief.md` (gemini, 2026-04-20)
- `docs/plans/phase47/kickoff.md` (claude, 2026-04-20)
- `docs/plans/phase47/design_decision.md` (claude, 2026-04-20)
- `docs/plans/phase47/risk_assessment.md` (claude, 2026-04-20)
- `docs/plans/phase47/closeout.md` (codex, 2026-04-20)
- `docs/plans/phase47/review_comments.md` (claude, 2026-04-20)
- `AGENTS.md` (codex, 2026-04-20)
- `README.md` (codex, 2026-04-20)
- `README.zh-CN.md` (codex, 2026-04-20)
- `current_state.md` (codex, 2026-04-20)

## 当前下一步

- **[Human/Gemini/Claude/Codex]** 从 `docs/roadmap.md` 重新选择下一轮 active track / phase / slice。
- **[Gemini/Claude]** 如启动新 phase，先补齐新的 `context_brief.md` / `kickoff.md` / `risk_assessment.md`。
- **[Human]** 完成下一轮方向确认后，再切出新的 feature branch。

当前阻塞项：

- 无阻塞；等待下一轮 phase 选择与 kickoff。
