# Active Context

## 当前轮次

- latest_completed_track: `Knowledge / RAG` (Primary) + `Agent Taxonomy` (Secondary)
- latest_completed_phase: `Phase 56`
- latest_completed_slice: `Phase Closeout`
- active_track: `Core Loop` (Primary) + `Knowledge / RAG` (Secondary)
- active_phase: `Phase 57`
- active_slice: `phase57_pre_kickoff_real_data_validation`
- active_branch: `feat/phase56-llm-enhanced-knowledge`
- status: `phase57_pre_kickoff_real_data_validation_completed`

---

## 当前状态说明

Foundation Era（Phase 47-54）已全部完成，tag `v1.0.0`。Phase 55（知识图谱与本地 RAG）已完成并合并。Phase 56（知识质量与 LLM 增强检索）已完成实现、review 与 closeout：S1 成本追踪统一、S2 LiteratureSpecialist LLM 增强、S3 QualityReviewer LLM 增强、S4 relation suggestions 应用 CLI 已全部落地，并通过专项与宽回归。当前处于 merge gate 前状态；后续默认入口切到 Phase 57 方向。

---

## 当前关键文档

1. `docs/roadmap.md`（全量刷新，2026-04-24）
2. `docs/plans/phase56/kickoff.md`
3. `docs/plans/phase56/design_decision.md`
4. `docs/plans/phase56/risk_assessment.md`
5. `docs/plans/phase56/review_comments.md`
6. `docs/plans/phase56/closeout.md`
7. `docs/plans/phase57/pre_kickoff_real_data_validation.md`

---

## 当前推进

已完成：

- **[Human]** Phase 54 已合并到 `main`，tag `v1.0.0`。
- **[Claude]** Roadmap 全量刷新，Knowledge Loop Era 已确立。
- **[Human]** Phase 55 已稳定落盘，Phase 56 方案已生成。
- **[Claude]** Phase 56 `kickoff` / `design_decision` / `risk_assessment` 已产出（2026-04-25）。
- **[Codex]** Phase 56 S1 已完成：
  - HTTP executor 优先使用 API `usage`
  - `_attach_estimated_usage()` 改为 fallback-only
- **[Codex]** Phase 56 S2/S3 基础实现已完成：
  - 新增 `agent_llm.py` 共享 helper
  - LiteratureSpecialist 支持 LLM 分析 + relation suggestions + heuristic fallback
  - QualityReviewer 支持 LLM 语义评估 + heuristic fallback
- **[Codex]** Phase 56 S4 已完成：
  - `executor_side_effects.json` 标准 artifact 落盘
  - `swl knowledge apply-suggestions --task-id <id> [--dry-run]` 已落地
  - relation suggestions 支持应用、去重、dry-run 预览
- **[Claude]** Phase 56 review 完成，结论 `approved`，无 CONCERN（见 `docs/plans/phase56/review_comments.md`）。
- **[Codex]** Phase 56 closeout 完成（见 `docs/plans/phase56/closeout.md`）。
- **[Codex]** 当前专项回归已通过：
  - `tests/test_executor_protocol.py tests/test_executor_async.py` 目标集 `6 passed`
  - `tests/test_specialist_agents.py tests/test_executor_protocol.py tests/test_executor_async.py` 全集 `40 passed`
  - `tests/test_cli.py tests/test_specialist_agents.py tests/test_executor_protocol.py tests/test_executor_async.py` 全集 `259 passed, 5 subtests passed`
- **[Codex]** Phase 57 kickoff 前真实数据验证已完成：
  - `SWL_API_BASE_URL` / `SWL_API_KEY` / `SWL_CHAT_MODEL` 已打通运行时与 doctor
  - provider 实测：`gpt-4o-mini` 可用，`google/gemma-4-26b-a4b-it` 当前返回 `model_price_error`
  - embedding 实测：`text-embedding-3-small` 可用，`text-embedding-v1` 当前返回 `Model does not exist`
  - design 文档 ingest + promote + literature-specialist LLM 分析 + `apply-suggestions` 已完成
  - LiteratureSpecialist relation suggestion grounding 已修复，真实 dry-run / apply 均通过
  - 当前结论已沉淀到 `docs/plans/phase57/pre_kickoff_real_data_validation.md`

进行中：

- 无。

待执行：

- **[Human]** 基于 `docs/plans/phase57/pre_kickoff_real_data_validation.md` 决定 Phase 57 scope（embedding / rerank / chunking / specialist CLI 入口）。
- **[Human]** 如坚持使用 `google/gemma-4-26b-a4b-it`，先完成 provider 侧价格配置。

当前阻塞项：

- 无。

---

## 当前下一步

1. **[Human]** 阅读 `docs/plans/phase57/pre_kickoff_real_data_validation.md`，确认 Phase 57 是否以 retrieval quality enhancement 为主。
2. **[Human]** 决定 chat / embedding 的真实 provider 基线模型配置。
3. **[Human]** 启动 Phase 57 kickoff。

---

## 当前产出物

- `docs/active_context.md`（codex, 2026-04-25）
- `docs/plans/phase56/kickoff.md`（claude, 2026-04-25）
- `docs/plans/phase56/design_decision.md`（claude, 2026-04-25）
- `docs/plans/phase56/risk_assessment.md`（claude, 2026-04-25）
- `docs/plans/phase56/review_comments.md`（claude, 2026-04-25）
- `docs/plans/phase56/closeout.md`（codex, 2026-04-25）
- `docs/plans/phase57/pre_kickoff_real_data_validation.md`（codex, 2026-04-25）
- `src/swallow/agent_llm.py`（codex, 2026-04-25）
- `src/swallow/canonical_registry.py`（codex, 2026-04-25）
- `src/swallow/executor.py`（codex, 2026-04-25）
- `src/swallow/harness.py`（codex, 2026-04-25）
- `src/swallow/knowledge_suggestions.py`（codex, 2026-04-25）
- `src/swallow/literature_specialist.py`（codex, 2026-04-25）
- `src/swallow/quality_reviewer.py`（codex, 2026-04-25）
- `src/swallow/cli.py`（codex, 2026-04-25）
- `src/swallow/orchestrator.py`（codex, 2026-04-25）
- `tests/test_cli.py`（codex, 2026-04-25）
- `tests/test_knowledge_relations.py`（codex, 2026-04-25）
- `tests/test_executor_protocol.py`（codex, 2026-04-25）
- `tests/test_executor_async.py`（codex, 2026-04-25）
- `tests/test_specialist_agents.py`（codex, 2026-04-25）
