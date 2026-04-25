---
author: claude
phase: 57
slice: kickoff
status: draft
depends_on:
  - docs/plans/phase56/closeout.md
  - docs/plans/phase57/pre_kickoff_real_data_validation.md
  - docs/plans/phase57/context_brief.md
  - docs/plans/rag_enhancement_roadmap.md
---

## TL;DR

Phase 57 将检索管线从"本地 hash embedding + 单阶段评分"升级为"神经 embedding + LLM rerank + chunking 优化"三层增强，同时补齐 specialist CLI 入口缺口。roadmap 原定的"编排增强"因真实数据验证暴露检索质量瓶颈而后移至 Phase 58。

# Phase 57 Kickoff: 检索质量增强 (Retrieval Quality Enhancement)

## Phase 身份

- **Phase**: 57
- **Primary Track**: Knowledge / RAG
- **Secondary Track**: Workbench / UX
- **分支建议**: `feat/phase57-retrieval-quality`

## 背景与动机

Phase 55 打通了"本地文件 → 知识图谱 → relation-aware retrieval → 任务执行"闭环。Phase 56 将 specialist agent 从启发式升级为 LLM 增强，并完成了 gated relation suggestion 工作流。然而，Phase 57 前置真实数据验证（`pre_kickoff_real_data_validation.md`）暴露了检索质量的核心瓶颈：

1. **embedding 是 blake2b hash，不是神经网络**：64 维 hash 投影无法捕获语义相似性，"知识架构"与"knowledge architecture"在当前向量空间中距离很远
2. **无 reranking 层**：所有候选在单次 scoring pass 内排序后截断，top-1 噪声（如 `results/knowledge.md`）稳定压过 canonical 知识对象
3. **chunking 粒度偏粗且无 overlap**：heading-based 分段切断上下文，repo 文件 40 行固定窗口无 overlap
4. **canonical reuse 路径绕过 vector 层**：`iter_canonical_reuse_items` 完全走 term-frequency，与 `iter_verified_knowledge_items` 行为不一致

同时，`swl task create --executor literature-specialist` 缺少 `document_paths` 透传，operator 无法完全靠 CLI 复现 specialist 闭环。

## 目标

1. **G1 — 神经 Embedding 接入**：用 API embedding 模型替换 `build_local_embedding()` 的 blake2b hash，保留本地 hash 为 fallback
2. **G2 — LLM Rerank**：在 `retrieve_context()` 返回前插入 LLM rerank 步骤，复用 `call_agent_llm()` 基础设施
3. **G3 — Chunking 优化**：为 markdown chunking 添加 overlap 和 max_chunk_size 限制
4. **G4 — Specialist CLI 入口补齐**：`swl task create --executor literature-specialist` 透传 `document_paths` 参数

## 非目标

- **编排增强（Planner / DAG / Strategy Router）**：后移至 Phase 58
- **Graph RAG / 社区发现 / 图结构摘要**：远期方向，不在本轮
- **Agentic retrieval / 多跳推理**：远期方向
- **Query rewrite / expansion**：P3 优先级，不在本轮
- **Hybrid search score 归一化**：P4 优先级，需 neural embedding 稳定后再做
- **已有 staged knowledge 的 re-embedding 或 re-chunking**：本轮只改 pipeline 逻辑，不回填历史数据
- **新增 provider / model 接入**：使用已验证可用的 `text-embedding-3-small`，不探索新模型

## 设计边界

1. **embedding 为 API 调用**：通过 `SWL_EMBEDDING_MODEL` + `SWL_EMBEDDING_API_BASE_URL` 配置驱动，不引入本地模型文件
2. **graceful degradation**：embedding API 不可用时 fallback 到 `build_local_embedding()`，rerank 失败时 fallback 到原始排序
3. **sqlite-vec 维度变化**：从 64 维扩展到模型原生维度（如 1536），需处理已有 index 兼容性（重建或新建表）
4. **rerank 复用 `call_agent_llm()`**：不引入专用 rerank API 依赖，使用已有 chat completions 路径
5. **chunking 改动只影响新入库数据**：已有 canonical 对象的 text 字段不变，但 retrieve-time score 分布可能变化

## 完成条件

1. **神经 embedding 可用**：`VectorRetrievalAdapter` 使用 API embedding，`build_local_embedding` 仅作 fallback
2. **LLM rerank 生效**：`retrieve_context()` 在返回前对 top-N 结果执行 LLM rerank，rerank 失败时 graceful fallback
3. **chunking overlap 生效**：`build_markdown_chunks()` 支持 overlap 行数配置和 max_chunk_size 限制
4. **specialist CLI 可用**：`swl task create --executor literature-specialist --document-paths <path>` 可端到端运行
5. **测试覆盖**：neural embedding / local fallback 路径、rerank 成功 / 失败路径、chunking overlap 行为、specialist CLI 参数透传均有 pytest 覆盖
6. **eval 基线**（如适用）：neural embedding 下 vector retrieval 的 precision / recall 不低于现有 eval 基线

## Eval 验收条件

本轮涉及"质量有梯度"的检索增强逻辑，需要 eval 覆盖：

| Slice | Eval 需要 | Eval 指标 |
|-------|----------|----------|
| S1 (Neural Embedding) | 是 | vector retrieval precision ≥ 0.75, recall ≥ 0.65（对照 Phase 49 基线 precision ≥ 0.70, recall ≥ 0.60） |
| S2 (LLM Rerank) | 是 | rerank 后 top-3 中 canonical 对象占比 ≥ 2/3（在含噪声 candidate 的场景下） |
| S3 (Chunking) | 否 | pytest 覆盖边界行为即可 |
| S4 (CLI) | 否 | pytest 覆盖参数透传即可 |

## roadmap 调整说明

roadmap 原定 Phase 57 为"编排增强"，Phase 56 pre-kickoff 真实数据验证后，决定将检索质量增强前移至 Phase 57，编排增强后移至 Phase 58。理由：

1. 检索质量是当前可感知的最大瓶颈（real data validation 已证实）
2. 编排增强依赖检索质量稳定后才能显现价值
3. neural embedding + rerank 的基础设施（`runtime_config.py`、`call_agent_llm()`）在 Phase 56 已就绪

## Branch Advice

- 当前分支: `main`
- 建议操作: 新建分支
- 理由: Phase 56 已合并到 main，Phase 57 应在新 feature branch 上开发
- 建议分支名: `feat/phase57-retrieval-quality`
- 建议 PR 范围: S1-S4 全部 slice 合入单个 PR
