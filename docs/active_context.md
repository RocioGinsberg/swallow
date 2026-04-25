# Active Context

## 当前轮次

- latest_completed_track: `Knowledge / RAG` (Primary) + `Agent Taxonomy` (Secondary)
- latest_completed_phase: `Phase 56`
- latest_completed_slice: `Phase Closeout`
- active_track: `Knowledge / RAG` (Primary) + `Workbench / UX` (Secondary)
- active_phase: `Phase 57`
- active_slice: `phase_closeout_ready_for_review`
- active_branch: `feat/phase57-retrieval-quality`
- status: `phase57_implementation_complete_review_pending`

---

## 当前状态说明

Phase 56（知识质量与 LLM 增强检索）已完成并合并到 main。Phase 57 前置真实数据验证暴露检索质量为核心瓶颈：blake2b hash embedding 非语义、无 rerank、chunking 无 overlap。Phase 57 方向已切到"检索质量增强"（原 roadmap 编排增强后移至 Phase 58），当前 4 个 implementation slices 均已完成并提交，`docs/plans/phase57/closeout.md` 已产出，整体状态切换为“实现完成，等待 review / PR 同步”。

---

## 当前关键文档

1. `docs/roadmap.md`（全量刷新，2026-04-24）
2. `docs/plans/phase57/kickoff.md`（claude, 2026-04-26）
3. `docs/plans/phase57/design_decision.md`（claude, 2026-04-26）
4. `docs/plans/phase57/risk_assessment.md`（claude, 2026-04-26）
5. `docs/plans/phase57/context_brief.md`（claude, 2026-04-26）
6. `docs/plans/phase57/pre_kickoff_real_data_validation.md`（codex, 2026-04-25）
7. `docs/plans/rag_enhancement_roadmap.md`（claude, 2026-04-25）

---

## 当前推进

已完成：

- **[Human]** Phase 56 已合并到 `main`。
- **[Codex]** Phase 57 前置真实数据验证已完成（`pre_kickoff_real_data_validation.md`）。
- **[Claude]** Phase 57 context_brief 已产出（2026-04-26）。
- **[Claude]** Phase 57 kickoff / design_decision / risk_assessment 已产出（2026-04-26）：
  - Phase 57 方向：检索质量增强（Neural Embedding + LLM Rerank + Chunking 优化 + Specialist CLI 补齐）
  - 4 个 slice：S1 Neural Embedding（中风险 6 分）、S2 LLM Rerank（低风险 4 分）、S3 Chunking（低风险 3 分）、S4 CLI（低风险 3 分）
  - 无高风险 slice，无需额外人工 gate
  - 建议分支：`feat/phase57-retrieval-quality`
- **[Human]** 已切换实现分支：`feat/phase57-retrieval-quality`
- **[Codex]** Phase 57 S1 已完成并提交：
  - `runtime_config.py` 新增 embedding model / dimensions / base_url 解析
  - `retrieval_adapters.py` 新增 API embedding 调用；embedding API 失败显式报错，仅 `sqlite-vec` 缺失时退回文本检索
  - `iter_canonical_reuse_items()` 已切到与 verified knowledge 一致的 vector/text fallback 路径
  - `knowledge_index.py` 已改为读取统一 embedding dimensions
  - `swl doctor` 已新增 embedding API 探针
  - 专项回归：`tests/test_retrieval_adapters.py tests/test_doctor.py` 通过（`18 passed`）
- **[Codex]** Phase 57 S2 已完成并提交：
  - `retrieval_config.py` 新增 `RetrievalRerankConfig` 与 `SWL_RETRIEVAL_RERANK_ENABLED` / `SWL_RETRIEVAL_RERANK_TOP_N`
  - `retrieve_context()` 出口新增 LLM rerank，只作用于 top-N 候选，最终仍按 `limit` 截断
  - rerank 失败时保持原排序，不阻断检索主流程
  - rerank 元数据写入 `metadata` / `score_breakdown`，便于 inspect 与后续审计
  - 专项回归：`tests/test_retrieval_adapters.py tests/test_doctor.py` 通过（`21 passed`）
- **[Codex]** Phase 57 S3 已完成并提交：
  - `build_markdown_chunks()` 新增 `overlap_lines` / `max_chunk_size` 参数，默认启用检索时 overlap 与超长 section 二次分段
  - markdown 长 section 优先按段落边界切分，纯文本 markdown 也会受 `max_chunk_size` 限制
  - overlap 改为回带前序非空行，避免只重叠空白行导致上下文无效
  - `build_repo_chunks()` 增加固定窗口 overlap，同时保持 `chunk_id` 仍按原始 base range 编码，避免引用语义漂移
  - 专项回归：`tests/test_retrieval_adapters.py` 通过（`18 passed`）
- **[Codex]** Phase 57 S4 已完成并提交：
  - `task create` 新增 repeatable `--document-paths` 参数
  - 仅当 `--executor literature-specialist` 时，CLI 将 `document_paths` 写入 `TaskState.input_context`
  - `planner._base_input_context()` 已透传 `state.input_context`，确保 create → state → card → specialist executor 全链路可见
  - `TaskState` 新增 `input_context` 持久化字段，兼容既有 dataclass 序列化/反序列化路径
  - 专项回归：`tests/test_cli.py -k literature_specialist_input_context`、`tests/test_specialist_agents.py -k literature_specialist` 通过（`7 passed`）
- **[Codex]** Phase 57 closeout 已完成：
  - 新增 `docs/plans/phase57/closeout.md`
  - `docs/active_context.md` / `current_state.md` 已切到 review pending 恢复基线
  - 当前分支已具备 Claude review / PR 同步前置材料

进行中：

- **[Human]** 准备发起 Claude review / Phase 57 收口审查。

待执行：

- **[Human]** 触发 Claude review。
- **[Codex]** 根据 review follow-up 吸收实现或文档修正。
- **[Codex]** review 通过后整理 `pr.md` 并准备 merge 材料。

当前阻塞项：

- 等待 Claude review 结论与后续 follow-up

---

## 当前下一步

1. **[Human]** 发起 Phase 57 Claude review。
2. **[Human]** 将 review 结论同步给 Codex。
3. **[Codex]** 吸收 follow-up，并在通过后整理 PR 材料。

---

## 当前产出物

- `docs/plans/phase57/context_brief.md`（claude, 2026-04-26）
- `docs/plans/phase57/kickoff.md`（claude, 2026-04-26）
- `docs/plans/phase57/design_decision.md`（claude, 2026-04-26）
- `docs/plans/phase57/risk_assessment.md`（claude, 2026-04-26）
- `docs/plans/phase57/closeout.md`（codex, 2026-04-26）
- `docs/plans/phase57/pre_kickoff_real_data_validation.md`（codex, 2026-04-25）
- `src/swallow/runtime_config.py`（codex, 2026-04-26）
- `src/swallow/models.py`（codex, 2026-04-26）
- `src/swallow/retrieval_adapters.py`（codex, 2026-04-26）
- `src/swallow/retrieval.py`（codex, 2026-04-26）
- `src/swallow/retrieval_config.py`（codex, 2026-04-26）
- `src/swallow/knowledge_index.py`（codex, 2026-04-26）
- `src/swallow/doctor.py`（codex, 2026-04-26）
- `src/swallow/planner.py`（codex, 2026-04-26）
- `src/swallow/orchestrator.py`（codex, 2026-04-26）
- `src/swallow/cli.py`（codex, 2026-04-26）
- `tests/test_retrieval_adapters.py`（codex, 2026-04-26）
- `tests/test_doctor.py`（codex, 2026-04-26）
- `tests/test_cli.py`（codex, 2026-04-26）
