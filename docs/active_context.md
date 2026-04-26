# Active Context

## 当前轮次

- latest_completed_track: `Knowledge / RAG` (Primary) + `Workbench / UX` (Secondary)
- latest_completed_phase: `Phase 57`
- latest_completed_slice: `Phase Closeout`
- active_track: `Direction Selection`
- active_phase: `Phase 58`
- active_slice: `roadmap_direction_gate`
- active_branch: `main`
- status: `phase58_direction_gate_docs_synced`

---

## 当前状态说明

Phase 57（Retrieval Quality Enhancement）已合并到 `main`，神经 API embedding、LLM rerank、默认 overlap 关闭、Literature Specialist document paths 透传均已成为当前主线基线。

当前工作已进入 **Phase 58 路线选择阶段**，不是实现阶段。`docs/roadmap.md` 已根据 Phase 57 后的真实代码状态做收口修正：能力画像字段已被路由消费、planning 已部分抽到 `planner.py`、`local-codex` 仍是 legacy alias、HTTP path 不能统一假设有自主 repo 探索能力、notes 不应立即“退场”而应逐步流向 staged knowledge / artifact refs / explicit refs。

推荐 Phase 58 方向仍是候选 A，但建议采用 **A-lite**：先做 `swl note`、`swl ingest --from-clipboard`、staged review visibility 与统一出口；完整 `BrainstormOrchestrator` / multi-route synthesis 等低摩擦捕获稳定后再推进。

`v1.2.0` tag 仍需单独决策：当前 tag 指向 Phase 56 旧提交；如 Human 决定重打，应先同步 README / AGENTS.md 的 tag-level 能力描述，再在 release docs commit 上重新打 tag。

---

## 当前关键文档

1. `docs/roadmap.md`（Phase 58 方向选择入口）
2. `current_state.md`（恢复 checkpoint）
3. `docs/plans/phase57/closeout.md`（Phase 57 收口事实）
4. `docs/plans/phase57/review_comments.md`（Claude review 结论）
5. `docs/design/ORCHESTRATION.md`（Brainstorm / Planner 蓝图）
6. `docs/design/KNOWLEDGE.md`（staged knowledge / raw materials 边界）
7. `docs/design/PROVIDER_ROUTER.md`（route capability / provider routing 蓝图）

---

## 当前推进

已完成：

- **[Human]** Phase 57 已合并到 `main`。
- **[Claude]** `docs/roadmap.md` 已刷新为 Phase 57 merge 后的路线选择文档。
- **[Codex]** 已对照当前代码与 `docs/design/` 修正 roadmap 中的事实性偏差：
  - route capability profiles 已部分落地并被路由消费，不再描述为“字段存在但未消费”
  - planner 状态改为“已部分抽到 `planner.py`，独立 Planner / DAG / Strategy Router 仍未一等化”
  - 候选 A 从“多模型群聊优先”收紧为“A-lite 捕获入口优先，受控 Brainstorm topology 后置”
  - 候选 B 增补 `local-codex -> local-aider` legacy alias migration 风险
  - 候选 C 增补 HTTP brainstorm / HTTP code-analysis / CLI coding path 的检索差异
  - notes source type 从“退场”改为“长期检索源收缩，内容流向 staged knowledge / artifact refs / explicit refs”
  - tag 建议改为重打在 release docs 同步后的 main head，而不是旧 merge commit
- **[Codex]** `docs/active_context.md` / `current_state.md` 已切到 Phase 58 Direction Gate 恢复基线。

进行中：

- **[Human]** Phase 58 路线选择。

待执行：

- **[Human]** 决定 Phase 58 是否采用候选 A-lite，或改选 B / C / D。
- **[Claude]** 方向确定后产出 Phase 58 kickoff / design_decision / risk_assessment。
- **[Human]** design gate 通过后，从 `main` 切出 `feat/phase58-...` 分支。
- **[Codex]** 仅在 feature branch 上开始 Phase 58 实现。
- **[Human]** 单独决定是否处理 `v1.2.0` retag；如处理，Codex 再同步 README / AGENTS.md release docs。

当前阻塞项：

- 无。

---

## 当前下一步

1. **[Human]** 在 `docs/roadmap.md` 的 Phase 58 候选中选择方向。
2. **[推荐]** 若选择候选 A，Phase 58 范围先限定为 A-lite：`swl note` + clipboard ingest + staged review visibility，不把完整 Brainstorm topology 放进第一轮实现。
3. **[流程]** 方向确定后先走 Claude kickoff / design / risk，再切 feature branch 开始实现。

---

## 当前产出物

- `docs/roadmap.md`（Claude + Codex, 2026-04-26）
- `docs/active_context.md`（Codex, 2026-04-26）
- `current_state.md`（Codex, 2026-04-26）
- `docs/plans/phase57/closeout.md`（Codex, 2026-04-26）
- `docs/plans/phase57/review_comments.md`（Claude, 2026-04-26）
- `pr.md`（Codex, 2026-04-26）

---

## 当前边界

- 当前只做路线选择与状态同步，不进入 Phase 58 代码实现。
- 不在 `main` 上进行日常功能开发；实现必须等待 design gate 与 feature branch。
- 不删除 notes source type；短期只收缩其长期检索定位，并把有价值内容导入 governed staged knowledge。
- 不把 raw brainstorm/chat history 直接提升为 canonical knowledge；所有沉淀都必须经过 staged → review → promote/reject。
