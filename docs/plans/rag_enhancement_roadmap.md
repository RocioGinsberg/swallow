---
author: claude
status: living-document
last_updated: 2026-04-25
---

## TL;DR

当前 RAG 管线已具备知识治理层优势（staged promotion、canonical registry、relation graph），但检索质量基础设施有明确短板：embedding 为 blake2b hash 投影（非神经网络）、无 rerank、无 query rewrite。本文档记录标准 RAG 对照、增强路径与优先级，供后续 phase 决策参考。

# RAG 增强路径规划

## 1. 当前管线与标准 RAG 对照

| 阶段 | 标准 RAG | Swallow 当前 | 差距 |
|------|---------|-------------|------|
| ① Document Loading | ✅ | ✅ `ingest_local_file` | 无 |
| ② Chunking | 语义分段 + overlap | heading 分段，无 overlap | **中** |
| ③ Embedding | 神经网络（768-1536 维） | blake2b hash 64 维 | **大** |
| ④ Vector Store | ✅ | ✅ sqlite-vec | 无 |
| ⑤ Query Processing | query rewrite + expansion | tokenize + stopwords | **中** |
| ⑥ Retrieval | hybrid（dense + sparse） | 多阶段但非 hybrid | **中** |
| ⑦ Reranking | cross-encoder / LLM rerank | 无 | **大** |
| ⑧ Context Assembly | ✅ | ✅ retrieval items → executor prompt | 无 |
| ⑨ Generation | ✅ | ✅ executor | 无 |
| ⑩ Evaluation | 检索质量反馈闭环 | QualityReviewer 存在但未接入检索反馈 | **低** |

### Swallow 的独有优势（标准 RAG 不具备）

- **知识治理层**：staged promotion、canonical registry、memory authority
- **关系图谱**：`knowledge_relations` 表 + Relation Expansion（BFS 遍历）
- **LLM 关系推断**：LiteratureSpecialist 自动建议关系 + operator gate（P7）
- **成本追踪统一**：API usage 优先 + fallback

## 2. 增强优先级

按投入产出比排序：

### P0: Neural Embedding 替换（最高优先级）

**现状**：`retrieval_adapters.py:build_local_embedding()` 使用 blake2b hash 投影到 64 维。这不是语义 embedding——"知识架构"和"knowledge architecture"在此空间中距离很远。这是当前检索质量的最大瓶颈。

**目标**：替换为神经网络 embedding 模型，通过 API 调用生成。

**推荐模型**：

| 模型 | 维度 | 优点 | 接入方式 |
|------|------|------|---------|
| **Qwen text-embedding-v3** | 1024 | 中英双语强、与现有 Qwen 路由生态一致 | OpenAI 兼容 `/v1/embeddings` |
| `bge-m3` | 1024 | 多语言、稀疏+稠密混合 | 同上 |
| `text-embedding-3-small` (OpenAI) | 1536 | 广泛使用、基线参考 | 同上 |

**实现路径**：
- `.env` 新增 `SWL_EMBEDDING_API_BASE_URL` + `SWL_EMBEDDING_MODEL`（默认可复用现有中转 URL）
- 新增 `embedding_adapter.py`，替换 `build_local_embedding()` 的调用点
- sqlite-vec 的 embedding 列从 64 维扩展（需要重建 index 或新建表）
- `build_local_embedding()` 保留为 fallback（API 不可用时降级）

**预估工作量**：8-12h

### P1: LLM Rerank（高优先级）

**现状**：检索结果直接按 score 排序返回，第一阶段召回的噪声直接传递到 executor。

**目标**：在最终返回前，用 LLM 对 top-N 结果做一次重排序。

**实现路径**：

| 方案 | 优点 | 缺点 |
|------|------|------|
| **A. 复用 `call_agent_llm()`** | 零新增依赖，Phase 56 基础设施已到位 | 每次检索多一次 LLM 调用 |
| B. 专用 rerank API（Jina / Cohere） | 精度更高、延迟更低 | 新增 API 依赖 + key 管理 |
| C. 本地 cross-encoder | 离线可用 | 需装 torch + 模型，体积大 |

**推荐**：先用方案 A（`call_agent_llm`），效果不够再切方案 B。

**实现要点**：
- `.env` 可选新增 `SWL_RERANK_API_BASE_URL` + `SWL_RERANK_MODEL`
- `retrieve_context()` 返回前插入 rerank 步骤
- rerank prompt 将 top-N items 拼成列表，要求 LLM 按相关性重排
- rerank 失败时 fallback 到原始排序

**预估工作量**：6-8h

### P2: Chunking 优化（中优先级）

**现状**：
- 摄入侧：`parse_local_file()` 按 `##` heading 分段
- 检索侧：`build_markdown_chunks()` 按任意级别 heading 分段

**已知问题**（待实测确认）：
- 无 chunk overlap，边界处信息丢失
- 纯文本文件不分段，大文件成为单个巨大 chunk
- 无 `max_chunk_size` 限制

**改进方向**：
- 添加 chunk overlap（前后 2-3 行）
- `max_chunk_size` 拆分过长 section
- 纯文本按段落或固定行数分段

**预估工作量**：4-6h

### P3: Query Processing（低优先级）

**现状**：`prepare_query_plan()` 做 tokenize + stopwords + bigrams，无语义处理。

**改进方向**：
- Query rewrite：用 LLM 改写 query 为更精确的检索表述
- Query expansion：生成同义词 / 相关概念
- 复用 `call_agent_llm()` 实现

**预估工作量**：4-6h

### P4: Hybrid Search（低优先级）

**现状**：vector search 和 text scoring 各自独立评分，未做归一化融合。

**改进方向**：
- 归一化 vector score 和 text score 到同一尺度
- 加权融合（`alpha * vector_score + (1 - alpha) * text_score`）
- alpha 可配置

**前置条件**：P0（neural embedding）完成后再做，否则 vector score 本身不可靠。

**预估工作量**：4h

## 3. 建议实施顺序

```
Phase 57 候选（基于 Phase 56 实测反馈选择）:
  P0: Neural Embedding → 替换 blake2b hash
  P1: LLM Rerank → 复用 call_agent_llm

Phase 58+ 候选:
  P2: Chunking 优化 → overlap + max_chunk_size
  P3: Query Processing → LLM rewrite
  P4: Hybrid Search → score 归一化融合
```

P0 和 P1 可以合并为一个 phase（约 16-20h），这是检索质量提升最显著的一步。P2-P4 可以根据实测反馈按需做。

## 4. 环境配置规划

```bash
# 现有（LLM chat completions）
SWL_API_BASE_URL=...          # 中转 URL
SWL_API_KEY=...               # API key
SWL_CHAT_MODEL=...            # 默认 chat model

# 新增（embedding）— 可复用中转 URL 或配置独立端点
SWL_EMBEDDING_API_BASE_URL=... # 默认复用 SWL_API_BASE_URL
SWL_EMBEDDING_MODEL=...        # 推荐 qwen text-embedding-v3 或 bge-m3
SWL_EMBEDDING_DIMENSIONS=1024  # 模型输出维度

# 新增（rerank，可选）
SWL_RERANK_API_BASE_URL=...    # 专用 rerank 端点（或复用中转）
SWL_RERANK_MODEL=...           # 推荐 bge-reranker-v2-m3
```

## 5. 决策时机

本文档为参考性规划，**不替代 phase kickoff**。具体决策在 Phase 56 真实数据验证完成后做出——根据"检索排序 / 召回覆盖度 / LLM 分析质量"三个维度的实测结论决定 Phase 57 的具体 scope。

参见 `docs/plans/phase56/post_merge_action_items.md` §4-§5 的观察记录和方向决策框架。
