---
author: claude
phase: 57
slice: review
status: draft
depends_on:
  - docs/plans/phase57/design_decision.md
  - docs/plans/phase57/closeout.md
---

## TL;DR

Phase 57 实现结构清晰，S2/S3/S4 质量良好。一个 BLOCK 项：`_vector_or_text_matches()` 仅捕获 `VectorRetrievalUnavailable` 而遗漏 `EmbeddingAPIUnavailable`，导致 9 个预存在的 `test_cli.py` 检索测试回归（main 上全部通过，feature branch 上全部失败）。修复后可进入 merge 流程。

# Phase 57 Review Comments

**Review 基线**：`git diff main...HEAD`（6 commits, 21 files, +1977/-260）
**Review 结论**：`approved_with_concerns`（1 BLOCK 必须修复，1 CONCERN 登记）

---

## Checklist

### S1: Neural Embedding

- [PASS] `runtime_config.py` 新增 `resolve_swl_embedding_model()` / `resolve_swl_embedding_dimensions()` / `resolve_swl_embedding_api_base_url()` / `resolve_swl_api_base_url()` / `resolve_swl_api_key()`，与已有 `resolve_swl_chat_model()` 模式一致。
- [PASS] `build_api_embedding()` 通过 httpx 调用 OpenAI-compatible `/v1/embeddings`，错误处理完整（HTTPError / JSON decode / 维度校验 / 空向量），全部包装为 `EmbeddingAPIUnavailable`。
- [PASS] `doctor.py` 中 `resolve_new_api_base_url()` 已被 `resolve_swl_api_base_url()` 替换，消除了重复定义。`_check_embedding_api_endpoint()` 新增 embedding API 探针。
- [PASS] `VectorRetrievalAdapter.search()` 改为调用 `build_api_embedding()` 替代 `build_local_embedding()`，query 和 document embedding 都走 API 路径。
- [PASS] `knowledge_index.py` 从 `runtime_config.resolve_swl_embedding_dimensions()` 读取维度，不再硬编码 64。
- [PASS] `iter_canonical_reuse_items()` 从 term-frequency-only 改为走 `_vector_or_text_matches()` 共享路径，修正了 context_brief 中识别的静默行为差距。
- [PASS] `httpx` 已在 `pyproject.toml` 中声明为依赖。
- [BLOCK] **`_vector_or_text_matches()` 遗漏 `EmbeddingAPIUnavailable` 的 fallback 捕获**。详见下方 BLOCK 项。
- [CONCERN] `VECTOR_EMBEDDING_DIMENSIONS = resolve_swl_embedding_dimensions()` 在模块导入时求值。如果后续有场景需要在运行时动态改变维度（如 test fixture），模块级常量不会更新。当前无实际影响（测试通过 mock 绕过），但与 `VectorRetrievalAdapter.embedding_dimensions = field(default_factory=resolve_swl_embedding_dimensions)` 的延迟求值模式不一致。

### S2: LLM Rerank

- [PASS] `rerank_retrieval_items()` 复用 `call_agent_llm()` + `extract_json_object()`，不引入新 API 依赖。
- [PASS] `_parse_rerank_indexes()` 做了完整的防御：bool 过滤、范围校验、去重、不可解析跳过、缺失 index 补尾。
- [PASS] rerank 失败路径（`AgentLLMUnavailable` / `ValueError`）直接返回原始列表，不阻断检索。
- [PASS] rerank 元数据（`rerank_applied`、`rerank_model`、`rerank_position`）写入 `metadata` / `score_breakdown`，支持后续审计。
- [PASS] `RetrievalRerankConfig` 支持 `SWL_RETRIEVAL_RERANK_ENABLED` / `SWL_RETRIEVAL_RERANK_TOP_N` 环境变量，`resolve_retrieval_rerank_config()` 解析完整。
- [PASS] `retrieve_context()` 在 sort 后、limit 截断前调用 rerank，位置正确。
- [PASS] 测试覆盖 rerank 成功路径（index 重排序 + 元数据）、失败路径（LLM 不可用 → 保持原序）、环境变量关闭路径。

### S3: Chunking 优化

- [PASS] `_expand_range_with_overlap()` 回带前序非空行实现合理，避免了 overlap 只重叠空白行的问题。
- [PASS] `_split_range_by_max_lines()` 优先按段落边界切分，不足时按固定行数截断，空行过滤完整。
- [PASS] `build_markdown_chunks()` 新增 `overlap_lines` 和 `max_chunk_size` 参数，preface / section / full-file 三种路径都经过处理。
- [PASS] `build_repo_chunks()` overlap 实现正确，`chunk_id` 保持按 base range 编码（`lines-1-40` 而非 `lines-1-42`），避免引用语义漂移。
- [PASS] chunk metadata 中记录了 `base_line_start` / `base_line_end` / `overlap_lines` / `segment_index` / `segment_count`，可审计性好。
- [PASS] 测试覆盖：section overlap、长 section 段落切分、纯文本 max_chunk_size、repo overlap + chunk_id 保持。

### S4: Specialist CLI 入口补齐

- [PASS] `--document-paths` 使用 `action="append"` + `default=[]`，支持 repeatable 输入。
- [PASS] 路径 normalize 使用 `Path(raw_path).resolve()`，去重使用 `seen_paths: set[str]`。
- [PASS] 仅当 `executor == "literature-specialist"` 时写入 `input_context`，不影响其他 executor。
- [PASS] `TaskState.input_context` 新增为 `dict[str, Any]` + `field(default_factory=dict)`，兼容已有序列化。
- [PASS] `planner._base_input_context()` 透传 `state.input_context`，确保 create → state → card → specialist 全链路连通。
- [PASS] `orchestrator.create_task()` 新增 `input_context` 参数和 event log 记录。
- [PASS] 测试验证了 CLI → state → plan card 的 `document_paths` 透传完整性。

### 文档与状态同步

- [PASS] `closeout.md` YAML frontmatter + TL;DR 格式正确，与 kickoff 完成条件逐项对照。
- [PASS] closeout 中显式记录了与 design_decision 的两处有意偏差（fallback 收紧、input_context 替代 executor_config）。
- [PASS] commit 按 slice 独立拆分，符合工作节奏规则。

### 与 design_decision 的一致性

- [PASS] S1 核心结构（`build_api_embedding` + `VectorRetrievalAdapter` 改造 + `runtime_config` 扩展 + `iter_canonical_reuse_items` 对齐）与设计一致。
- [PASS] S2 rerank 位置、prompt 结构、fallback 行为与设计一致。
- [PASS] S3 overlap + max_chunk_size 与设计一致。
- [PASS] S4 CLI 参数透传与设计意图一致（载体从 `executor_config` 改为 `input_context` 是合理简化）。

### 与 architecture_principles 的一致性

- [PASS] 改动限于 Retrieval & Serving Layer，未触及 Knowledge Truth Layer。
- [PASS] 未引入本地模型文件、专用 rerank API 或新的外部框架。

### 测试覆盖

- [PASS] S1: API embedding 成功路径、API 不可用 → 显式报错、sqlite-vec 缺失 → VectorRetrievalUnavailable。
- [PASS] S2: rerank 成功重排 + 元数据、LLM 不可用 → 保持原序、环境变量禁用 → 不调用 LLM。
- [PASS] S3: markdown section overlap、长 section 段落拆分、纯文本 max_chunk_size、repo overlap + chunk_id 保持。
- [PASS] S4: CLI → state → plan card document_paths 透传。
- [BLOCK] 9 个预存在的 `test_cli.py` 检索测试因 `EmbeddingAPIUnavailable` 未被捕获而回归。

### 是否越出 phase scope

- [PASS] 未触及编排增强、Graph RAG、query rewrite 等非目标。`doctor.py` 的 `resolve_new_api_base_url()` 内联到 `runtime_config` 是自然收口，不是范围扩张。

---

## BLOCK 项

### B1: `_vector_or_text_matches()` 未捕获 `EmbeddingAPIUnavailable`，导致 9 个预存在测试回归

**位置**：`src/swallow/retrieval.py:417-443`（`_vector_or_text_matches()`）

**问题**：
- `VectorRetrievalAdapter.search()` 现在调用 `build_api_embedding()`，当 `SWL_API_KEY` 未设置时抛出 `EmbeddingAPIUnavailable`
- `_vector_or_text_matches()` 仅捕获 `VectorRetrievalUnavailable`，不捕获 `EmbeddingAPIUnavailable`
- 预存在的 9 个 `test_cli.py` 检索测试在无 API key 环境下全部回归（main 上 pass，feature branch 上 fail）

**回归测试列表**：
1. `test_cli_end_to_end_local_file_promotion_link_and_relation_retrieval`
2. `test_end_to_end_local_file_relation_expansion_reaches_task_run`
3. `test_retrieve_context_can_include_cross_task_knowledge_when_history_is_requested`
4. `test_retrieve_context_can_include_verified_knowledge_when_explicitly_requested`
5. `test_retrieve_context_includes_canonical_reuse_visible_records`
6. `test_retrieve_context_includes_relation_expansion_metadata_for_linked_knowledge`
7. `test_retrieve_context_limits_knowledge_reuse_to_current_task_when_history_is_not_requested`
8. `test_retrieve_context_uses_markdown_sections_for_notes`
9. `test_retrieve_context_uses_repo_line_chunks_and_symbol_titles`

**修复方向**：
在 `_vector_or_text_matches()` 中将 `except VectorRetrievalUnavailable:` 扩展为 `except (VectorRetrievalUnavailable, EmbeddingAPIUnavailable):`。这与 design_decision 中的 graceful degradation 意图一致：embedding API 不可用时回退到文本检索。

closeout 中记录的"有意收敛"（embedding API 失败显式报错）在 `VectorRetrievalAdapter.search()` 层面是合理的（向上传播错误），但在 `_vector_or_text_matches()` 这个 fallback 入口层面应该被捕获并走文本回退，而不是让整个检索链路崩溃。

**验收标准**：修复后 `test_cli.py` 全量回归 0 failures。

---

## CONCERN 项

### C1: 模块级 `VECTOR_EMBEDDING_DIMENSIONS` 在 import 时求值

**位置**：`src/swallow/retrieval_adapters.py:37`

**描述**：`VECTOR_EMBEDDING_DIMENSIONS = resolve_swl_embedding_dimensions()` 在模块首次 import 时即固化。同文件中 `VectorRetrievalAdapter.embedding_dimensions` 使用 `field(default_factory=resolve_swl_embedding_dimensions)` 实现延迟求值，两者模式不一致。

**当前影响**：无实际影响。`VECTOR_EMBEDDING_DIMENSIONS` 主要被 `build_local_embedding()` 的默认参数和测试引用。测试通过 mock 绕过。

**消化时机**：后续 phase 如果需要在同一进程中切换 embedding 维度（如 eval 场景同时对比不同维度），再统一为延迟求值或注入式配置。当前不阻塞。

---

## Review 结论

**Verdict**: `approved_with_concerns`

- 1 个 BLOCK 必须修复：`_vector_or_text_matches()` 补充 `EmbeddingAPIUnavailable` 捕获
- 1 个 CONCERN 登记到 backlog：模块级 embedding dimensions 求值时机

BLOCK 修复预估为单行代码变更。修复后应运行 `test_cli.py` 全量回归确认 0 failures，然后即可进入 PR 同步。
