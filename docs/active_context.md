# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `Knowledge / RAG`
- latest_completed_phase: `Phase 60`
- latest_completed_slice: `Phase Closeout`
- active_track: `Collaboration / Workflow`
- active_phase: `Meta Docs Sync`
- active_slice: `Roadmap Audit & Closeout`
- active_branch: `main`
- status: `meta_docs_sync_closeout_ready_for_human_review`

---

## 当前状态说明

Phase 60(Route-Aware Retrieval Policy)已合并到 `main`。本轮 Meta Docs Sync 经过两个 slice:

1. **Cowork Mode Upgrade**(已完成):AGENTS / shared rules / workflows / role / rules / state docs 对齐修补;feature workflow 隐藏 handoff 显式化(kickoff producer / milestone review cadence / concern backlog sync / post-merge state sync / post-merge roadmap update)
2. **Roadmap Audit & Closeout**(本轮新增):Claude 主线重读设计文档(12 份)与代码现状(64 个 `.py`)、6 个 phase closeout,产出两件事——

   **a. Roadmap 增量更新**(`roadmap-updater` subagent + Claude 主线协作)
   - Phase 60 在差距表 / 推荐队列 / 战略锚点表三处下线,标 `[已消化]`
   - Specialist 计数从"7"修正为权威口径(4 Specialist + 2 Validator)
   - 新增差距条目"`apply_proposal()` 入口函数化"为 candidate F
   - Claude 主线评审推荐次序:**F → E → D**

   **b. `apply_proposal()` 漂移登记 concern**:INVARIANTS §0 第 4 条 / §9 守卫测试要求 `apply_proposal()` 是 canonical / route / policy 写入唯一入口,代码 `grep -rn "apply_proposal" src/ tests/` 零匹配——已记入 `docs/concerns_backlog.md` Open 表(Meta Docs Sync / Roadmap audit (closeout) 行)

`docs(meta)` 提交尚未发生;待 Human 审阅本轮 Claude 主线产出后批准提交,再由 Codex 执行 post-merge state sync。

---

## 当前关键文档

1. `change.md`(本轮协作文档升级目标与差距说明)
2. `AGENTS.md`(仓库入口控制面;本轮已补齐实际路径与 subagent 列表)
3. `.agents/shared/read_order.md`(启动读取顺序)
4. `.agents/workflows/feature.md`(主流程;已与 design-auditor / tag workflow 对齐)
5. `.agents/workflows/tag_release.md`(tag sync 详细规则)
6. `docs/roadmap.md`(增量更新已完成,待 Human 审阅)
7. `docs/concerns_backlog.md`(新增 `apply_proposal()` 漂移条目)

---

## 当前推进

已完成:

- **[Human]** Phase 60 已 merge 到 `main`
- **[Human]** `docs(agents): upgrade cowork mode part 1` 已提交到 `main`
- **[Codex]** 已完成 `change.md` 差距检查与 workflow 效率审计修补
- **[Claude]** 重读设计文档(12 份)+ 代码现状 + 6 个 phase closeout,完成 roadmap audit
- **[Claude + roadmap-updater]** `docs/roadmap.md` 增量更新:Phase 60 下线、specialist 计数修正、新增 candidate F、Claude 推荐次序刷新
- **[Claude]** `docs/concerns_backlog.md` 新增 `apply_proposal()` 漂移条目

进行中:

- 无。

待执行:

- **[Human]** 审阅本轮 docs/meta diff(`.agents/` / `AGENTS.md` / `current_state.md` / `docs/roadmap.md` / `docs/concerns_backlog.md` / `docs/active_context.md`),决定提交策略(直接 main 或开 docs branch)
- **[Human]** Direction Gate:在候选 F / E / D 中决策下一 phase 方向
- **[Codex]** 提交后执行 post-merge state sync(切换 latest_completed_* 与 active_*)

当前阻塞项:

- 无。

---

## 当前下一步

1. **[Human]** 审阅本轮调整(`.agents/` 协作文档 + `docs/roadmap.md` + `docs/concerns_backlog.md` + 本文件)
2. **[Human]** 执行本轮 `docs(meta): ...` 提交
3. **[Human]** 选择下一 phase 方向(Claude 推荐次序 F → E → D,见 `docs/roadmap.md §五`)
4. **[Codex]** post-merge state sync,切换 active_phase 到下一方向

---

## 当前产出物

- `change.md`(human, 2026-04-27, 协作文档升级目标)
- `AGENTS.md`(human/codex, 2026-04-27, 路径与 subagent 对齐)
- `.agents/shared/read_order.md`(codex, 2026-04-27, 启动读取顺序补齐)
- `.agents/shared/document_discipline.md`(codex, 2026-04-27, subagent output 边界补齐)
- `.agents/workflows/feature.md`(human/codex, 2026-04-27, design-auditor / design input 对齐)
- `.agents/workflows/tag_release.md`(human/codex, 2026-04-27, release doc sync 与 roadmap 解耦)
- `.agents/claude/role.md`(codex, 2026-04-27, kickoff / concern sync / subagent state sync 职责对齐)
- `.agents/claude/rules.md`(codex, 2026-04-27, design_decision 增加 milestone 分组要求)
- `.agents/codex/role.md`(codex, 2026-04-27, milestone commit cadence 与 current_state 可写范围对齐)
- `.agents/codex/rules.md`(codex, 2026-04-27, milestone review gate 规则对齐)
- `.codex/session_bootstrap.md`(codex, 2026-04-27, milestone commit / tag sync 入口对齐)
- `README.md`(codex, 2026-04-27, 设计文档链接修正)
- `current_state.md`(codex, 2026-04-27, 恢复入口与 tag 状态修正)
- `.agents/shared/rules.md`(codex, 2026-04-27, kickoff / breakdown 产出边界调整)
- `.agents/shared/state_sync_rules.md`(codex, 2026-04-27, post-merge state sync 规则补齐)
- `docs/roadmap.md`(claude + roadmap-updater, 2026-04-28, Phase 60 收口 + candidate F 入差距表 + Claude 推荐次序 F→E→D)
- `docs/concerns_backlog.md`(claude, 2026-04-28, `apply_proposal()` 漂移条目)
- `docs/active_context.md`(claude, 2026-04-28, Meta Docs Sync 收尾 + Direction Gate 待决)
