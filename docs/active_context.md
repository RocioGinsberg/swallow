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
- active_slice: `Cowork Mode Upgrade`
- active_branch: `main`
- status: `docs_meta_alignment_ready_for_human_review`

---

## 当前状态说明

Phase 60（Route-Aware Retrieval Policy）已经合并到 `main`。当前 `main` 在该能力基线之上继续进行协作文档整理：`docs(agents): upgrade cowork mode part 1` 已提交；本轮已根据 `change.md` 完成 AGENTS / shared rules / workflows / state docs 的对齐修补，并额外把 feature workflow 的隐藏 handoff 收口为显式步骤：kickoff producer、milestone review cadence、PR review concern sync、post-merge state sync、post-merge roadmap update。

---

## 当前关键文档

1. `change.md`（本轮协作文档升级目标与差距说明）
2. `AGENTS.md`（仓库入口控制面；本轮需要补齐实际路径与 subagent 列表）
3. `.agents/shared/read_order.md`（启动读取顺序）
4. `.agents/workflows/feature.md`（主流程；需与 design-auditor / tag workflow 对齐）
5. `.agents/workflows/tag_release.md`（tag sync 详细规则）

---

## 当前推进

已完成：

- **[Human]** Phase 60 已 merge 到 `main`
- **[Human]** `docs(agents): upgrade cowork mode part 1` 已提交到 `main`
- **[Codex]** 已完成 `change.md` 差距检查：确认存在路径漂移、状态文档滞后、tag workflow 仍引用不存在文件等问题
- **[Codex]** 已完成 workflow 效率审计与修补：补齐 kickoff producer、将 review gate 默认切到 milestone、显式化 concern backlog sync、将 post-merge state sync / roadmap update 从 tag flow 中解耦

进行中：

- 无。

待执行：

- **[Human]** 审阅本轮 docs/meta diff，并决定是否直接在 `main` 提交或转为 `docs/...` 分支整理

当前阻塞项：

- 无。

---

## 当前下一步

1. **[Human]** 审阅 `AGENTS.md` / `.agents/workflows/feature.md` / `.agents/workflows/tag_release.md` / `current_state.md` 的本轮协作规则调整。
2. **[Human]** 执行本轮 `docs(meta): ...` 提交。
3. **[Human]** 如认可新的 milestone review cadence，再决定是否继续把同类规则同步到其他模板或历史文档。

---

## 当前产出物

- `change.md`（human, 2026-04-27, 协作文档升级目标）
- `AGENTS.md`（human/codex, 2026-04-27, 路径与 subagent 对齐）
- `.agents/shared/read_order.md`（codex, 2026-04-27, 启动读取顺序补齐）
- `.agents/shared/document_discipline.md`（codex, 2026-04-27, subagent output 边界补齐）
- `.agents/workflows/feature.md`（human/codex, 2026-04-27, design-auditor / design input 对齐）
- `.agents/workflows/tag_release.md`（human/codex, 2026-04-27, release doc sync 与 roadmap 解耦）
- `.agents/claude/role.md`（codex, 2026-04-27, kickoff / concern sync / subagent state sync 职责对齐）
- `.agents/claude/rules.md`（codex, 2026-04-27, design_decision 增加 milestone 分组要求）
- `.agents/codex/role.md`（codex, 2026-04-27, milestone commit cadence 与 current_state 可写范围对齐）
- `.agents/codex/rules.md`（codex, 2026-04-27, milestone review gate 规则对齐）
- `.codex/session_bootstrap.md`（codex, 2026-04-27, milestone commit / tag sync 入口对齐）
- `README.md`（codex, 2026-04-27, 设计文档链接修正）
- `current_state.md`（codex, 2026-04-27, 恢复入口与 tag 状态修正）
- `.agents/shared/rules.md`（codex, 2026-04-27, kickoff / breakdown 产出边界调整）
- `.agents/shared/state_sync_rules.md`（codex, 2026-04-27, post-merge state sync 规则补齐）
