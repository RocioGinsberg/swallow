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
- status: `docs_meta_alignment_in_progress`

---

## 当前状态说明

Phase 60（Route-Aware Retrieval Policy）已经合并到 `main`。当前 `main` 在该能力基线之上继续进行协作文档整理：`docs(agents): upgrade cowork mode part 1` 已提交；本轮正在根据 `change.md` 校准 AGENTS / shared rules / workflows / state docs，使它们和实际仓库结构、当前 release sync 约定以及现有 subagent 集合保持一致。

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

进行中：

- **[Codex]** 正在同步 AGENTS / shared rules / workflow / README / state docs 到当前仓库结构

待执行：

- **[Human]** 审阅本轮 docs/meta diff，并决定是否直接在 `main` 提交或转为 `docs/...` 分支整理

当前阻塞项：

- 无。

---

## 当前下一步

1. **[Codex]** 完成协作文档与状态文档对齐修补。
2. **[Human]** 审阅 `AGENTS.md` / `README.md` / `current_state.md` / workflow 相关改动。
3. **[Human]** 执行本轮 `docs(meta): ...` 提交，并决定是否继续补强剩余可选文档。

---

## 当前产出物

- `change.md`（human, 2026-04-27, 协作文档升级目标）
- `AGENTS.md`（human/codex, 2026-04-27, 路径与 subagent 对齐）
- `.agents/shared/read_order.md`（codex, 2026-04-27, 启动读取顺序补齐）
- `.agents/workflows/feature.md`（human/codex, 2026-04-27, design-auditor / design input 对齐）
- `.agents/workflows/tag_release.md`（human/codex, 2026-04-27, release doc sync 约定修正）
- `README.md`（codex, 2026-04-27, 设计文档链接修正）
- `current_state.md`（codex, 2026-04-27, 恢复入口与 tag 状态修正）
