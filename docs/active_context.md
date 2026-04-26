# Active Context

## 当前轮次

- latest_completed_track: `Knowledge / RAG` (Primary) + `Workbench / UX` (Secondary)
- latest_completed_phase: `Phase 57`
- latest_completed_slice: `Phase Closeout`
- active_track: `Knowledge / RAG` (Primary) + `Workbench / UX` (Secondary)
- active_phase: `Phase 58`
- active_slice: `phase closeout`
- active_branch: `feat/phase58-knowledge-capture`
- status: `phase58_closeout_in_progress`

---

## 当前状态说明

Phase 57 已合并到 main。Phase 58 方向已确认为候选 A（A-lite）：思考-讨论-沉淀闭环。kickoff / design_decision / risk_assessment 已产出，并已根据 Codex gate review 修正实现级约束：`candidate_id` 保持 `staged-*`、`topic` 在 update/report 路径保留、clipboard `source_ref=clipboard://...`、omitted `--format` 走 parser auto-detect、S2 增加受限 `generic_chat_json` 且不做 URL/shared-link 摄入。当前分支已切到 `feat/phase58-knowledge-capture`，S1 `swl note`、S3 staged review visibility、S2 clipboard transport + `generic_chat_json` 均已实现并提交。Claude review 已完成；1 条实现 concern 已修复，剩余 1 条低影响 concern 已登记 backlog，当前进入阶段收口。

外部对话输入格式边界已同步到 `docs/design/KNOWLEDGE.md`：明确区分内容语义、输入载体、内容格式；规定 provider JSON / generic chat JSON / Markdown transcript / note / local file 的使用边界，并把 URL/shared-link 摄入排除出默认知识能力。

---

## 当前关键文档

1. `docs/roadmap.md`（Phase 58 方向选择入口）
2. `docs/plans/phase58/kickoff.md`（claude, 2026-04-26）
3. `docs/plans/phase58/design_decision.md`（claude, 2026-04-26）
4. `docs/plans/phase58/risk_assessment.md`（claude, 2026-04-26）
5. `docs/plans/phase58/context_brief.md`（claude, 2026-04-26）
6. `docs/design/KNOWLEDGE.md`（外部输入格式长期边界）

---

## 当前推进

已完成：

- **[Human]** Phase 57 已合并到 `main`。
- **[Claude]** roadmap 全量刷新（候选 A/B/C/D 评估，推荐 A → B → C → D）。
- **[Codex]** roadmap 事实性偏差修正（legacy alias / planner 状态 / capability profiles 等）。
- **[Claude]** Phase 58 context_brief 已产出（2026-04-26）：关键发现包括 StagedCandidate 无 topic 字段、swl ingest CLI 签名冲突、review visibility 多个 report 入口信息密度不一致。
- **[Claude]** Phase 58 kickoff / design_decision / risk_assessment 已产出（2026-04-26）：
  - Phase 58 方向：A-lite（`swl note` + clipboard transport / `generic_chat_json` + staged review visibility）
  - 3 个 slice：S1 swl note（低风险 3 分）、S2 clipboard transport + generic_chat_json（低风险 5 分）、S3 review visibility（低风险 3 分）
  - 建议分支：`feat/phase58-knowledge-capture`
  - 推荐实施顺序：S1 → S3 → S2
- **[Codex]** Phase 58 方案 gate review 已完成并同步修订文档（2026-04-26）：
  - 修正 `swl note` 的 candidate_id 约束，禁止实现为 `note-*`
  - 明确 `topic` 必须同步 `from_dict()` / `to_dict()` / `update_staged_candidate()` / report views
  - 明确 clipboard transport 不伪装为 Path，必须写 `source_ref=clipboard://<format-or-auto>`
  - 明确 omitted `--format` 传 `None`，不把 `"auto"` 直接传给 parser
  - 明确 S2 支持受限 `generic_chat_json` flat message-list JSON，但不做 URL / shared link / provider plugin 抽象
- **[Codex]** `docs/design/KNOWLEDGE.md` 已补充外部输入格式长期规范（2026-04-26）：
  - 区分内容语义 / 输入载体 / 内容格式
  - 固化 provider JSON、`generic_chat_json`、Markdown transcript、`swl note`、`swl knowledge ingest-file` 的使用边界
  - 将 URL / shared link 摄入标为非默认能力，需未来独立 slice 设计

进行中：

- **[Codex]** Phase 58 closeout：
  - 吸收 review 中的低成本实现 concern（剪切板 detected format decode 冗余）
  - 产出 `closeout.md`
  - 同步 `pr.md` 与 `docs/active_context.md`

待执行：

- **[Claude]** review_comments.md 已完成（2026-04-26）。2 CONCERN / 0 BLOCK。建议直接进入收口。
- **[Codex]** 已吸收 review 中的 `_resolve_detected_format()` decode 冗余 concern；对应 backlog 项已移除。
- **[Human]** 审查 closeout 材料，决定是否执行收口提交 / 推送 / 建 PR。

当前阻塞项：

- 无。

---

## 当前下一步

1. **[Human]** 审查 `docs/plans/phase58/closeout.md` 与 `pr.md`。
2. **[Human]** 执行审查收口提交，推送分支，创建 PR。
3. **[Claude]** 如 PR review 新增 follow-up，再继续同分支吸收。

---

## 当前产出物

- `docs/plans/phase58/context_brief.md`（claude, Codex adjustments, 2026-04-26）
- `docs/plans/phase58/kickoff.md`（claude, Codex adjustments, 2026-04-26）
- `docs/plans/phase58/design_decision.md`（claude, Codex adjustments, 2026-04-26）
- `docs/plans/phase58/risk_assessment.md`（claude, Codex adjustments, 2026-04-26）
- `docs/design/KNOWLEDGE.md`（Codex, 2026-04-26）
- `src/swallow/staged_knowledge.py`（Codex, S1 implementation, 2026-04-26）
- `src/swallow/ingestion/pipeline.py`（Codex, S1/S2 implementation + review follow-up, 2026-04-26）
- `src/swallow/ingestion/__init__.py`（Codex, S1 implementation, 2026-04-26）
- `src/swallow/cli.py`（Codex, S1 implementation, 2026-04-26）
- `tests/test_staged_knowledge.py`（Codex, S1 tests, 2026-04-26）
- `tests/test_ingestion_pipeline.py`（Codex, S1 tests, 2026-04-26）
- `tests/test_cli.py`（Codex, S1 tests, 2026-04-26）
- `docs/plans/phase58/review_comments.md`（claude, 2026-04-26）
- `docs/plans/phase58/closeout.md`（Codex, 2026-04-26）
- `pr.md`（Codex, 2026-04-26）
- `docs/concerns_backlog.md`（claude + Codex, 2026-04-26, 1 open CONCERN retained）
