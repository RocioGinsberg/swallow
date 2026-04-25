---
author: claude
phase: 57
slice: design-decision
status: draft
depends_on:
  - docs/plans/phase57/kickoff.md
  - docs/plans/phase57/context_brief.md
  - docs/plans/rag_enhancement_roadmap.md
---

## TL;DR

Phase 57 拆为 4 个 slice：S1 神经 embedding 替换（高影响、中风险）、S2 LLM rerank 插入（中影响、低风险）、S3 chunking overlap 优化（低影响、低风险）、S4 specialist CLI 入口补齐（最小、无风险）。S1 → S2 有顺序依赖（rerank 在 embedding 改善后效果更好），S3/S4 与前两者无依赖。

# Phase 57 Design Decision: 检索质量增强

## 方案总述

将检索管线从"本地 hash embedding + 单阶段 term-frequency 评分"升级为"神经 API embedding + LLM 二阶段 rerank"架构。同时优化 chunking 粒度并补齐 specialist CLI 入口。方案复用 Phase 56 已落地的 `runtime_config.py`、`call_agent_llm()` 基础设施，不引入新的外部框架或本地模型依赖。设计核心原则：每一层增强都保留 graceful degradation 到上一层级行为。

## Slice 拆解

### S1: Neural Embedding 接入

**目标**：用 API embedding 模型替换 `build_local_embedding()` 作为 `VectorRetrievalAdapter` 的默认 embedding 函数。

**影响范围**：
- `src/swallow/runtime_config.py` — 新增 `SWL_EMBEDDING_MODEL`、`SWL_EMBEDDING_DIMENSIONS`（可选 `SWL_EMBEDDING_API_BASE_URL`）
- `src/swallow/retrieval_adapters.py` — 新增 `build_api_embedding()` 或独立 `embedding_adapter.py`；修改 `VectorRetrievalAdapter` 和 `search_vector_documents()` 的 embedding 调用点
- sqlite-vec 索引维度从 64 → 模型原生维度（如 1536）
- `src/swallow/doctor.py` — `swl doctor` 新增 embedding API 连通性检查

**实现要点**：

1. **`runtime_config.py` 扩展**：
   - `DEFAULT_SWL_EMBEDDING_MODEL = "text-embedding-3-small"`
   - `get_embedding_model() -> str`：读取 `SWL_EMBEDDING_MODEL` 环境变量
   - `get_embedding_dimensions() -> int`：读取 `SWL_EMBEDDING_DIMENSIONS`，默认 1536
   - `get_embedding_api_base_url() -> str`：读取 `SWL_EMBEDDING_API_BASE_URL`，默认回退到 `SWL_API_BASE_URL`

2. **embedding 调用函数**（建议放在 `retrieval_adapters.py` 或新文件 `embedding_adapter.py`）：
   ```python
   async def build_api_embedding(text: str, *, model: str, base_url: str, api_key: str, dimensions: int) -> list[float]:
       # httpx call to /v1/embeddings
       # 返回 dimensions 维向量
   
   def build_api_embedding_sync(text: str, ...) -> list[float]:
       # sync wrapper
   ```

3. **`VectorRetrievalAdapter` 改造**：
   - 尝试 API embedding → 成功则使用神经向量
   - API 不可用（连接失败 / 无 key / 超时）→ fallback 到 `build_local_embedding()`，发出 WARN
   - 维度由 `get_embedding_dimensions()` 驱动，不再硬编码 64

4. **sqlite-vec 维度迁移**：
   - 新维度的向量不能与旧 64 维向量混存于同一 virtual table
   - 策略：检测现有 table 维度，维度不匹配时自动 drop + recreate（向量索引是辅助结构，不是 truth）
   - 或新建独立 table `knowledge_embeddings_v2`，保留旧 table 作 fallback

5. **`iter_canonical_reuse_items` 路径对齐**：
   - 当前此函数跳过 vector adapter 只用 `score_chunk`
   - S1 中应将其改为与 `iter_verified_knowledge_items` 一致的 vector 路径
   - 这修正了 context_brief 中发现的静默差距

**风险评级**：
- 影响范围: 2（跨 retrieval_adapters + runtime_config + retrieval）
- 可逆性: 1（fallback 到 local embedding 即可回滚）
- 依赖复杂度: 3（依赖外部 embedding API 可用性）
- **总分: 6（中风险）**

**验收条件**：
- `VectorRetrievalAdapter` 默认使用 API embedding
- API 不可用时自动 fallback 到 local embedding + WARN 日志
- `iter_canonical_reuse_items` 走 vector 路径
- `swl doctor` 包含 embedding API 连通性检测
- eval: vector retrieval precision ≥ 0.75, recall ≥ 0.65

---

### S2: LLM Rerank

**目标**：在 `retrieve_context()` 返回最终结果前，对 top-N 候选执行 LLM rerank，提升 top 结果的相关性。

**影响范围**：
- `src/swallow/retrieval.py` — `retrieve_context()` 内新增 rerank 步骤
- `src/swallow/retrieval_config.py` — 新增 rerank 配置（`RERANK_TOP_N`、`RERANK_ENABLED` 等）
- `src/swallow/agent_llm.py` — 复用已有 `call_agent_llm()`，可能新增 rerank-specific prompt 模板

**实现要点**：

1. **rerank 步骤位置**：在所有 source 的 retrieval items 合并、去重、排序后，取 top-N（建议 N=10-15）送入 LLM rerank
2. **rerank prompt**：将 query + top-N items 的 title/text 摘要拼成列表，要求 LLM 输出按相关性排序的 item index 列表
3. **rerank 结果应用**：LLM 输出的排序覆盖原始 score 排序，但不修改原始 score 字段（保留可审计性）
4. **graceful degradation**：
   - LLM 调用失败（超时 / API 错误）→ 保留原始排序，日志 WARN
   - LLM 输出格式不可解析 → 保留原始排序
   - `SWL_CHAT_MODEL` 未配置 → 跳过 rerank
5. **可选关闭**：`RERANK_ENABLED = True` 默认开启，可通过环境变量关闭

**风险评级**：
- 影响范围: 1（仅 retrieval.py 出口处新增一步）
- 可逆性: 1（关闭 rerank 即回到原始行为）
- 依赖复杂度: 2（依赖 `call_agent_llm()` 路径，Phase 56 已验证）
- **总分: 4（低风险）**

**验收条件**：
- `retrieve_context()` 返回前执行 rerank（当 rerank 开启且 LLM 可用时）
- rerank 失败时 graceful fallback 到原始排序
- eval: rerank 后 top-3 中 canonical 对象占比 ≥ 2/3（含噪声场景）

---

### S3: Chunking 优化

**目标**：为 `build_markdown_chunks()` 添加 overlap 和 max_chunk_size 限制，改善 chunk 边界处的上下文完整性。

**影响范围**：
- `src/swallow/retrieval_adapters.py` — `build_markdown_chunks()`、`build_repo_chunks()`
- 已有 staged knowledge 的 retrieve-time score 分布可能变化（但 canonical text 不变）

**实现要点**：

1. **overlap 行数**：`build_markdown_chunks()` 每个 chunk 前后各包含相邻 chunk 的 N 行（建议 N=2-3），通过参数配置
2. **max_chunk_size**：heading section 超过 M 行（建议 M=80）时，按段落边界或固定行数二次分段
3. **build_repo_chunks** 相同逻辑：40 行窗口 + overlap
4. **不改变 ingestion pipeline**：chunking 优化只影响 retrieve-time 的分段行为，不影响 `parse_local_file()` 的 staged knowledge 生成

**风险评级**：
- 影响范围: 1（仅 retrieval_adapters.py 内部）
- 可逆性: 1（overlap=0 + max_chunk_size=inf 即回到原始行为）
- 依赖复杂度: 1（无外部依赖）
- **总分: 3（低风险）**

**验收条件**：
- `build_markdown_chunks()` 支持 `overlap_lines` 和 `max_chunk_size` 参数
- overlap 行为：相邻 chunk 有指定行数重叠
- 超长 section 被二次分段
- pytest 覆盖边界 case（空文件、单 section、超长 section、纯文本）

---

### S4: Specialist CLI 入口补齐

**目标**：`swl task create --executor literature-specialist` 支持 `--document-paths` 参数透传。

**影响范围**：
- `src/swallow/cli.py` — `task create` 子命令新增 `--document-paths` 参数

**实现要点**：

1. `click.option("--document-paths", multiple=True)` 新增参数
2. 当 `executor == "literature-specialist"` 且 `document_paths` 非空时，将路径写入 task card 的 `executor_config`
3. `LiteratureSpecialistAgent` 已可接受 `document_paths`，无需修改 agent 代码

**风险评级**：
- 影响范围: 1（仅 cli.py 单点）
- 可逆性: 1（参数是新增，不影响已有行为）
- 依赖复杂度: 1（无外部依赖）
- **总分: 3（最低风险）**

**验收条件**：
- `swl task create --executor literature-specialist --document-paths docs/design/KNOWLEDGE.md` 可创建 task
- task card 的 `executor_config` 中包含 `document_paths`
- pytest 覆盖参数透传

---

## 依赖说明

```
S1 (Neural Embedding)
  ↓ S2 依赖 S1 完成后效果更好（但 S2 技术上可独立实现）
S2 (LLM Rerank)

S3 (Chunking) — 与 S1/S2 无依赖，可并行
S4 (CLI) — 与所有 slice 无依赖，可并行
```

**推荐实施顺序**：S1 → S2 → S3 → S4

S3 和 S4 可在 S1 完成后并行实施，但为避免 commit 粒度过细，建议按顺序逐个完成。

## 明确的非目标

1. **不引入本地 embedding 模型**（torch / ONNX）— API-only
2. **不引入专用 rerank API**（Jina / Cohere）— 复用 chat completions
3. **不做 query rewrite / expansion** — P3 优先级
4. **不做 hybrid search score 归一化** — P4 优先级
5. **不回填已有 canonical 对象的 embedding** — 只改 pipeline，不迁移数据
6. **不修改 relation expansion 逻辑** — Phase 55 已稳定
7. **不改动 knowledge truth layer** — 只改 retrieval & serving layer
