# Active Context

## 当前轮次

- latest_completed_track: `Retrieval / Memory` (Primary) + `Workbench / UX` (Secondary)
- latest_completed_phase: `Phase 24`
- latest_completed_slice: `Staged Knowledge Pipeline Baseline`
- active_track: `Capabilities` (Primary) + `Evaluation / Policy` (Secondary)
- active_phase: `Phase 25`
- active_slice: `Taxonomy-Driven Capability Enforcement`
- active_branch: `main`（待创建 `feat/phase25-capability-enforcement`）
- status: `design_produced`

---

## 当前目标

启动 Phase 25 规划，执行方向 B：在底层的 Harness 沙盒与能力装配（Capability Assembly）阶段，根据任务的 `TaxonomyProfile` 动态裁剪并剥离执行实体无权使用的底层工具（Tools）。彻底封死智能体越界调用敏感工具的安全隐患。

---

## 当前要解决的问题

当前系统：
- 已经具备派发层面的安全拦截（Phase 22）。
- 已经具备暂存知识管道（Phase 24）。
- 但如果将只读任务委派给 Validator Agent，底层 Harness 可能依旧粗放地将所有注册的 Capabilities 注入给了大模型。

需要解决的是：在代码底层实现执行时的“最小权限原则（Least Privilege）”过滤。

---

## 当前关键文档

当前优先读取：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `current_state.md`
4. `docs/plans/phase25/context_brief.md` (新产出的阶段目标简报)

---

## 当前产出物

- `docs/plans/phase25/design_preview.md` (gemini, 2026-04-12)
- `docs/plans/phase25/context_brief.md` (gemini, 2026-04-12)
- `docs/plans/phase25/design_decision.md` (claude, 2026-04-13)
- `docs/plans/phase25/risk_assessment.md` (claude, 2026-04-13)

## 当前推进

已完成：
- **[Gemini]** 收到人类操作员指令，确认推进方案 B（基于分类学的运行时能力沙盒）。
- **[Gemini]** 完成了 `docs/plans/phase25/context_brief.md` 的起草。
- **[Gemini]** 切换了 `docs/active_context.md` 的 active track、slice 与 status。
- **[Claude]** 已产出 `design_decision.md`（3 slice：映射表 → orchestrator 裁剪 → 事件与可视化）和 `risk_assessment.md`（无高风险项，general-executor 默认不触发任何降级）

## 下一步

等待人工审批 `design_decision.md` 和 `risk_assessment.md`。通过后由 Codex 在 `feat/phase25-capability-enforcement` 分支上开始实现。