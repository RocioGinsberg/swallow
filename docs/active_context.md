# Active Context

## 当前轮次

- latest_completed_track: `Capabilities` (Primary) + `Execution Topology` (Secondary)
- latest_completed_phase: `Phase 22`
- latest_completed_slice: `Taxonomy-Aware Routing Baseline`
- active_track: `Workbench / UX` (Primary) + `Execution Topology` (Secondary)
- active_phase: `Phase 23`
- active_slice: `Taxonomy Visibility in CLI Surfaces`
- active_branch: `main`（待创建 `feat/phase23-taxonomy-cli-visibility`）
- status: `design_produced`

---

## 当前目标

将 Phase 22 在底层数据流中挂载的智能体分类学（Agent Taxonomy）信息，正式暴露到命令行交互界面。让操作员在使用 `swallow task inspect`、`swallow task review` 等核心指令时，可以直观地看到被分配任务或交接任务的智能体安全身份（Role / Memory Authority），告别盲目审批，从而闭环增强可观测性。

---

## 当前要解决的问题

当前系统：
- 已经在代码底层（`Capabilities` / `Router` / `TaskState`）增加了 taxonomy profile（Phase 22）。
- 如果系统处于 `waiting_human` 等待人类拦截审批的状态，操作员目前只能看到任务进度，并不能直接从终端渲染上看出处理人到底是 "具有全量任务状态写权限的 General Executor" 还是 "被禁止修改规范库的 Specialist Agent"。

当前待解决的是：
- 将现有的 TaxonomyProfile 信息在 `cli.py` 或相关展示逻辑中优雅、紧凑地打印出来，不破坏现有版面且足够醒目。

---

## 当前关键文档

当前优先读取：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `current_state.md`
4. `docs/plans/phase23/context_brief.md`

---

## 当前产出物

- `docs/plans/phase23/context_brief.md` (gemini, 2026-04-12)
- `docs/plans/phase23/design_decision.md` (claude, 2026-04-12)
- `docs/plans/phase23/risk_assessment.md` (claude, 2026-04-12)

## 当前推进

已完成：
- **[Gemini]** 读取了 Phase 22 的 closeout 判定以及 `docs/system_tracks.md` 地图。
- **[Gemini]** 基于”继续推进可观测性和增强操作员工作流”的原则，规划了 `Phase 23: Taxonomy Visibility in CLI Surfaces`。
- **[Gemini]** 产出了 Phase 23 的上下文摘要 `docs/plans/phase23/context_brief.md`。
- **[Gemini]** 更新了 `current_state.md` 与 `docs/active_context.md` 以同步状态。
- **[Claude]** 已产出 `design_decision.md`（2 slice：inspect + review taxonomy 展示）和 `risk_assessment.md`（全低风险）

## 下一步

等待人工审批 `design_decision.md` 和 `risk_assessment.md`。通过后由 Codex 在 `feat/phase23-taxonomy-cli-visibility` 分支上开始实现。