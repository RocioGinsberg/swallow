---
author: claude
phase: 57
slice: context-brief
status: draft
depends_on:
  - docs/plans/phase56/closeout.md
  - docs/plans/phase57/pre_kickoff_real_data_validation.md
---

TL;DR: Phase 56 landed LLM-enhanced specialist agents and a gated relation-suggestion workflow; real-data validation
then revealed that retrieval quality (not orchestration) is the binding constraint. Phase 57 pivots to dense
embedding, reranking, and chunking — the vector layer exists but currently uses a 64-dim local hash embedding,
not a neural model, and the canonical-reuse scoring path never calls the vector adapter at all.

## 变更范围

- **直接影响模块**:
  - `src/swallow/retrieval_adapters.py` — `VectorRetrievalAdapter` (currently wraps local `build_local_embedding`,
    64-dim blake2b hash), `build_local_embedding`, `build_markdown_chunks` (heading-only split, no overlap),
    `build_repo_chunks` (40-line fixed window, no overlap), `score_search_document` (term-frequency rerank
    baseline used as the sole non-vector scoring path)
  - `src/swallow/retrieval.py` — `iter_verified_knowledge_items` (vector path for knowledge objects),
    `iter_canonical_reuse_items` (uses `score_chunk` only — no vector call), `retrieve_context` (top-level
    pipeline; file chunks also use `score_chunk` only)
  - `src/swallow/retrieval_config.py` — `KNOWLEDGE_PRIORITY_BONUS` (50), `RelationExpansionConfig`
  - `src/swallow/literature_specialist.py` — CLI entry gap: `document_paths` not wired from `swl task create`
  - `src/swallow/cli.py` — `swl task create --executor literature-specialist` does not pass `document_paths`
    to the specialist card

- **间接影响模块**:
  - `src/swallow/agent_llm.py` — could host or route embedding API calls if neural embedding goes through
    the same HTTP helper
  - `src/swallow/runtime_config.py` — will need an `SWL_EMBEDDING_MODEL` entry if the embedding model
    becomes configurable at runtime
  - `src/swallow/knowledge_store.py` — no changes expected but read by `iter_verified_knowledge_items`
  - `src/swallow/knowledge_suggestions.py` — not in scope; relation-suggestion apply already landed in Phase 56

## 近期相关变更 (git history)

| Commit | 描述 | 相关模块 |
|--------|------|---------|
| 5f4ccd1 | docs(phase57): refresh pre-kickoff validation model baseline | docs/plans/phase57/ |
| 30a29ea | refactor(config): centralize swl chat model runtime config | runtime_config.py |
| 5bb3f8f | docs(config): align phase56 and deploy docs with swl api envs | docs |
| 238d0cc | test(config): add actual test example of retrieval | tests |
| d94a54a | refactor(config): remove legacy api env fallbacks, default gpt-4o-mini | executor.py, agent_llm.py |
| ef7d0b1 | merge: LLM Enhanced Retrieval & RAG Optimize | — |
| e3bb4a7 | docs(state): close out phase56 and advance next-phase entry | active_context.md |
| cc43ff8 | feat(knowledge): apply relation suggestions from task artifacts | knowledge_suggestions.py, cli.py |
| 989aa8e | feat(agent): add llm enhancement for specialist reviews | literature_specialist.py, quality_reviewer.py |
| deaaae8 | refactor(executor): prefer api usage for http token tracking | executor.py |

## 关键上下文

- **当前 vector 层不是神经 embedding**: `VectorRetrievalAdapter` 使用 `build_local_embedding`（64 维
  blake2b hash + bigram，纯本地计算），与 API 无关。`text-embedding-3-small` 可用但当前未被任何生产路径调用；
  `text-embedding-v1` 在当前 provider 返回 400。引入神经 embedding 意味着为 `VectorRetrievalAdapter`
  或新 adapter 增加 API 调用路径，需与 `runtime_config.py` 对齐管理模型名。

- **canonical reuse 路径绕过了 vector 层**: `iter_canonical_reuse_items` 完全走 `score_chunk`
  （term-frequency），不调用 `VectorRetrievalAdapter`。这与 `iter_verified_knowledge_items` 的行为不一致，
  是一个已存在的静默差距。

- **chunk 粒度偏粗且无 overlap**: markdown 按 heading 切分，没有 overlap；repo 文件按 40 行固定窗口切分，
  也没有 overlap。pre-kickoff 验证观察到 `KNOWLEDGE.md` 被切为 13 个 staged candidates，chunk
  边界会切断上下文。改动 chunking 会影响所有已有 staged knowledge 对象的 retrieval score，应视为 breaking
  change 对已有索引。

- **reranking 尚不存在**: `score_search_document` 中有一个局部 rerank 权重（coverage, bigram, phrase
  hit），但这不是 cross-encoder 或 LLM rerank。当前没有两阶段（recall + rerank）结构；所有候选在单次
  scoring pass 内排序后截断到 `limit`。

- **`document_paths` CLI 缺口是单点缺口**: `LiteratureSpecialistAgent` 本体已可接受 `document_paths`，
  问题仅在 `cli.py` 的 `swl task create` 未透传该参数。pre-kickoff 验证通过 runtime API 补跑绕过了此缺口。

- **`SWL_EMBEDDING_MODEL` 尚不存在**: `runtime_config.py` 目前只管理 `SWL_CHAT_MODEL`。Phase 57 引入神经
  embedding 前需先确认真实可用的 embedding model 名，并在 `runtime_config.py` 中统一管理，而不是在
  retrieval adapter 内写死。

- **`KNOWLEDGE_PRIORITY_BONUS = 50` 是固定偏移**: 在真实 query 测试中，`results/knowledge.md`
  仍以高 term-frequency 分压过 canonical 对象进入 top-1，说明 bonus 尚不足以稳定压制 repo 层噪声。

## 风险信号

- **神经 embedding 引入网络依赖**: 当前 `VectorRetrievalAdapter` 是纯本地路径，fallback 到
  `TextFallbackAdapter` 完全不涉及网络。若 embedding 改为 API 调用，retrieval 路径将引入网络延迟与
  provider 可用性依赖，需保留本地 embedding fallback 或增加超时策略。

- **chunking 改动影响已有索引**: 改变 `build_markdown_chunks` 的边界逻辑（如加 overlap）会使已有
  staged knowledge 文本的 chunk boundary 发生位移，已落库的 canonical 对象 text 字段来源不变，
  但 retrieve-time 的 score 分布会变化。

- **embedding model 名称未经实测**: 只有 `text-embedding-3-small` 在当前 provider 上经过确认，
  `text-embedding-v1` 已知不可用，其他候选模型名未经验证。Phase 57 不应写死 model 名。

- **`active_branch` 状态**: `active_context.md` 显示 `active_branch: feat/phase56-llm-enhanced-knowledge`，
  但 Phase 56 已 closeout 且标记 `ready for merge`。Phase 57 应在新 branch 上开发；
  若 phase56 branch 尚未合并到 main，Phase 57 需确认基线分支。
