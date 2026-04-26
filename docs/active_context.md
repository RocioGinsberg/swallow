# Active Context

## 当前轮次

- latest_completed_track: `CLI / Routing` (Primary)
- latest_completed_phase: `Phase 59`
- latest_completed_slice: `Phase Closeout`
- active_track: `Knowledge / RAG`
- active_phase: `Phase 60`
- active_slice: `Phase Closeout`
- active_branch: `feat/phase60-retrieval-policy`
- status: `phase60_ready_for_human_merge_gate`

---

## 当前状态说明

Phase 58 (Knowledge Capture) 和 Phase 59 (Codex CLI Route) 均已合并到 main，v1.3.0 已打。Phase 60 方向 C（路径感知的 Retrieval Policy）已完成 kickoff / design_decision / risk_assessment，并已对齐最新长期设计：代码库上下文默认由 autonomous CLI tool-loop 负责，HTTP path 默认聚焦 knowledge + notes，Specialist 依赖 explicit input_context / artifacts，repo 仅作为 explicit override 或 legacy fallback 辅助源。

---

## 当前关键文档

1. `docs/plans/phase60/kickoff.md`（Phase 60 目标、slice 拆分、完成条件）
2. `docs/plans/phase60/design_decision.md`（policy 表设计、改动文件、测试要求）
3. `docs/plans/phase60/risk_assessment.md`（R1-R5 风险评级与缓解路径）
4. `docs/plans/phase60/context_brief.md`（代码现状分析）

---

## 当前推进

已完成：

- **[Claude]** roadmap 全量刷新（2026-04-26）：Phase 58/59 完成记录、差距表更新、候选 C/D/E 评估、推荐 C → E → D、tag 评估。
- **[Claude]** Phase 60 context_brief（2026-04-26）
- **[Claude]** Phase 60 kickoff / design_decision / risk_assessment（2026-04-26）
- **[Codex]** Phase 60 文档口径修正（2026-04-26）：移除 HTTP 默认 repo 表述，明确 repo source 显式化
- **[Codex]** 长期设计文档补充（2026-04-26）：`KNOWLEDGE.md` 明确 repo/notes/knowledge source 语义，`AGENT_TAXONOMY.md` 明确 HTTP/CLI/Specialist 生态位，`ARCHITECTURE.md` 增加全局执行生态位表
- **[Codex]** roadmap / kickoff 复核修正（2026-04-26）：补充长期设计锚点、Specialist 不误分类约束、当前分支与文档 gate 状态
- **[Human]** Phase 60 S1 已提交：`feat(retrieval): add phase60 s1 route-aware source policy`
- **[Human]** Phase 60 S2 已提交：`test(retrieval): cover explicit http source policy`
- **[Human]** Phase 60 S3 已提交：`feat(retrieval): add explicit retrieval source overrides`
- **[Human]** Phase 60 review fix 已提交：`test(phase60): fix review regression assertions`
- **[Codex]** Phase 60 S3 已完成实现并通过 `.venv` 定向 pytest：`TaskSemantics.retrieval_source_types` 已支持显式 override、合法 source 校验、保序去重；planning handoff / semantics report 不再丢失 override
- **[Claude]** Phase 60 review 已完成（2026-04-26）：1 BLOCK + 1 CONCERN，详见 `docs/plans/phase60/review_comments.md`
- **[Codex]** Phase 60 closeout 已完成：`docs/plans/phase60/closeout.md` 与 `pr.md` 已同步，`.venv` 全量非 eval pytest `535 passed`

进行中：

- 无。

待执行：

- **[Human]** 审阅 closeout / PR 文案并执行 push / PR / merge 决策

当前阻塞项：

- 无。

---

## 当前下一步

1. **[Human]** 审阅 `docs/plans/phase60/closeout.md` 与 `pr.md`。
2. **[Human]** push 当前分支并创建 / 更新 PR。
3. **[Human]** 基于 review、closeout 与全量测试结果执行 merge 决策。

---

## 当前产出物

- `docs/roadmap.md`（claude, 2026-04-26, Phase 58/59 完成 + 候选 C/D/E 评估）
- `docs/plans/phase60/context_brief.md`（claude, 2026-04-26）
- `docs/plans/phase60/kickoff.md`（claude, 2026-04-26）
- `docs/plans/phase60/design_decision.md`（claude, 2026-04-26）
- `docs/plans/phase60/risk_assessment.md`（claude, 2026-04-26）
- `docs/plans/phase60/review_comments.md`（claude, 2026-04-26）
- `docs/plans/phase60/closeout.md`（codex, 2026-04-26）
- `pr.md`（codex, 2026-04-26, Phase 60 merge prep）
