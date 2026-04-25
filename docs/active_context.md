# Active Context

## 当前轮次

- latest_completed_track: `Knowledge / RAG` (Primary) + `Agent Taxonomy` (Secondary)
- latest_completed_phase: `Phase 56`
- latest_completed_slice: `Phase Closeout`
- active_track: `Knowledge / RAG` (Primary) + `Workbench / UX` (Secondary)
- active_phase: `Phase 57`
- active_slice: `merge_gate_pending`
- active_branch: `feat/phase57-retrieval-quality`
- status: `phase57_pr_synced_merge_gate_pending`

---

## 当前状态说明

Phase 56（知识质量与 LLM 增强检索）已完成并合并到 main。Phase 57 前置真实数据验证暴露检索质量为核心瓶颈：blake2b hash embedding 非语义、无 rerank、chunking 无 overlap。Phase 57 方向已切到"检索质量增强"（原 roadmap 编排增强后移至 Phase 58），当前 4 个 implementation slices 均已完成并提交，`docs/plans/phase57/closeout.md` 与 `pr.md` 均已同步到 review 后真实状态。Claude review 的唯一 BLOCK 已修复并通过 `tests/test_cli.py` 全量回归，当前等待 Human merge gate 决策。

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
- **[Claude]** Phase 57 review 完成（2026-04-26），结论 `approved_with_concerns`：
  - 1 BLOCK：`_vector_or_text_matches()` 未捕获 `EmbeddingAPIUnavailable`，导致 9 个预存在 `test_cli.py` 检索测试回归
  - 1 CONCERN：模块级 `VECTOR_EMBEDDING_DIMENSIONS` import 时求值（已登记 backlog）
  - 修复方向：`except VectorRetrievalUnavailable:` → `except (VectorRetrievalUnavailable, EmbeddingAPIUnavailable):`
  - 见 `docs/plans/phase57/review_comments.md`
- **[Codex]** Phase 57 review BLOCK 已修复（2026-04-26）：
  - `src/swallow/retrieval.py` 现已在 verified knowledge 与 canonical reuse 两条 fallback 入口捕获 `EmbeddingAPIUnavailable` 并回退到文本检索
  - embedding fallback 改为输出准确 WARN；`chunk_id` 保持 base range 时，file retrieval citation 也同步恢复为 base range，避免 overlap 扩大引用范围
  - 回归验证：`tests/test_retrieval_adapters.py -k 'embedding_api_is_unavailable or sqlite_vec_is_unavailable'` 通过（`4 passed`）
  - 全量 CLI 回归：`tests/test_cli.py` 通过（`220 passed`）
- **[Codex]** Phase 57 后续收紧（2026-04-26）：
  - `src/swallow/retrieval_adapters.py` 已将 repo / notes 的默认 overlap 关闭（`REPO_CHUNK_OVERLAP_LINES=0`、`MARKDOWN_CHUNK_OVERLAP_LINES=0`）
  - 保留 heading / symbol 分段与 `max_chunk_size`，仅停止默认 overlap 扩张，后续如需实验仍可通过显式参数开启
- **[Codex]** Phase 57 PR / closeout 已同步（2026-04-26）：
  - `docs/plans/phase57/closeout.md` 已切到 review 后真实状态，纳入 BLOCK 修复、默认 overlap 关闭与最新验证结果
  - `pr.md` 已重写为 Phase 57 PR 文案，反映当前实现、review 结论与 merge gate 状态

进行中：

- 无。

待执行：

- **[Human]** 审阅当前 diff / PR 材料，决定 merge gate。

当前阻塞项：

- 无。

---

## 当前下一步

1. **[Human]** 审阅 phase57 当前 diff / `pr.md` / `docs/plans/phase57/closeout.md`，决定 merge gate。

---

## 当前产出物

- `docs/plans/phase57/review_comments.md`（claude, 2026-04-26）
- `docs/plans/phase57/context_brief.md`（claude, 2026-04-26）
- `docs/plans/phase57/kickoff.md`（claude, 2026-04-26）
- `docs/plans/phase57/design_decision.md`（claude, 2026-04-26）
- `docs/plans/phase57/risk_assessment.md`（claude, 2026-04-26）
- `docs/plans/phase57/closeout.md`（codex, 2026-04-26）
- `pr.md`（codex, 2026-04-26）
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
