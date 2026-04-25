---
author: codex
phase: 57
slice: pre_kickoff_real_data_validation
status: completed
last_updated: 2026-04-25
---

## TL;DR

Phase 57 kickoff 前的真实数据验证已跑通最小闭环：`SWL_*` 环境变量已可驱动 HTTP / agent LLM 路径，design 文档已完成 ingest + promote + literature-specialist LLM 分析 + `apply-suggestions` 实落库。结论是：**Phase 56 的主链条成立，但暴露出两个真实场景缺口**：

1. provider 侧 `google/gemma-4-26b-a4b-it` 当前不可用（`model_price_error`），不能作为当下默认 chat 测试模型；
2. LiteratureSpecialist 原始 relation suggestion 未 grounding 到真实 knowledge object id，已在本轮修复。

## 1. 环境配置结论

当前本地 `.env` 已使用：

```bash
export SWL_API_KEY=...
export SWL_API_BASE_URL='http://localhost:3000'
```

本轮测试使用的可运行 chat model：

```bash
export SWL_CHAT_MODEL='gpt-4o-mini'
```

说明：

- `SWL_API_KEY` / `SWL_API_BASE_URL` / `SWL_CHAT_MODEL` 已在运行时代码中生效，并有测试覆盖；
- `google/gemma-4-26b-a4b-it` 在当前 provider 返回 `model_price_error`，属于 provider 配置问题，不是 swallow 代码问题；
- `/v1/models` 可访问，`text-embedding-3-small` embeddings 可成功调用；
- 用户候选的 `text-embedding-v1` 在当前 provider 上返回 `400 Model does not exist`，Phase 57 如要做 neural embedding，应先确认真实可用模型名。

## 2. 已执行的真实数据步骤

### 2.1 Design 文档 ingest

已执行：

- `swl knowledge ingest-file docs/design/KNOWLEDGE.md`
- `swl knowledge ingest-file docs/design/AGENT_TAXONOMY.md`
- `swl knowledge ingest-file docs/design/ARCHITECTURE.md`

观察：

- `KNOWLEDGE.md` 分成 13 个 staged candidates
- `AGENT_TAXONOMY.md` 分成 15 个 staged candidates
- `ARCHITECTURE.md` 分成 11 个 staged candidates

分段质量判断：

- heading-based chunking 对 design 文档总体可用；
- `##` 级 section 大多语义完整，适合作为 canonical 候选；
- 但 chunk 粒度仍偏粗，没有 overlap，后续如要做更强 dense retrieval / rerank，仍建议进入 chunking tuning。

### 2.2 Promote 的 verified / canonical 选择

本轮实际 promote 并用于 relation 测试的核心对象：

- `canonical-staged-4435a53b`
  - `ingest-knowledge-fragment-0004`
  - `2.1 Knowledge Truth Layer`
- `canonical-staged-94beec56`
  - `ingest-knowledge-fragment-0005`
  - `2.2 Retrieval & Serving Layer`
- `canonical-staged-0e9ef63f`
  - `ingest-agent_taxonomy-fragment-0007`
  - `5. Memory Authority`

这些对象适合作为 verified / canonical 基线，因为它们正好构成了本轮想观察的三角关系：knowledge truth / retrieval serving / memory authority。

### 2.3 LiteratureSpecialist LLM 增强实测

真实调用结果：

- `analysis_method: llm`
- `input_tokens: 1027`
- `output_tokens: 598`
- `model: openai/gpt-4o-mini`

说明：

- agent LLM 路径已真实消费 API usage，不是 `len // 4` 估算；
- Phase 56 的 `analysis_method` / `llm_usage` / `relation_suggestions` 主链条成立。

## 3. 本轮发现并已修复的问题

### 3.1 `SWL_*` 环境变量别名覆盖不完整

已修复：

- `SWL_API_BASE_URL`
- `SWL_API_KEY`
- `SWL_CHAT_MODEL`

涉及模块：

- `src/swallow/executor.py`
- `src/swallow/agent_llm.py`
- `src/swallow/doctor.py`

### 3.2 Relation suggestion 产出 filename alias，无法 `apply-suggestions`

真实问题：

- LLM 初始输出使用 `KNOWLEDGE.md` / `AGENT_TAXONOMY.md` / `ARCHITECTURE.md`
- `swl knowledge apply-suggestions --dry-run` 全部报 `Unknown knowledge object`
- 仅靠 canonical alias helper 还不够，因为同一文档会切成多个 fragment，文件名天然是歧义 alias

本轮修复：

- `resolve_knowledge_object_id()` 扩展为支持 canonical record alias 解析；
- 更关键的是，`LiteratureSpecialistAgent` 现在会从 retrieval items 提取可用 knowledge object id，并要求 LLM 仅输出这些真实 object id；
- relation suggestion 归一化阶段也会将常见 alias 回写为真实 `knowledge_object_id`。

结果：

- `swl knowledge apply-suggestions --task-id 50735ff2a63b --dry-run`
  - 从 `invalid_count=5` 变为 `applied_count=5`

### 3.3 Specialist 的真实 CLI 入口仍不完整

真实现象：

- `swl task create --executor literature-specialist`
- `swl task run <task_id> --executor literature-specialist`

当前仍会退回普通任务路径，因为 CLI 没有把 `document_paths` 输入到 literature-specialist card。

结论：

- 这不是 LLM / retrieval / provider 问题，而是 specialist 的 operator-facing CLI 入口能力仍不完整；
- 本轮真实验证通过 runtime API 补跑，说明 specialist 本体可用，但 CLI 入口仍是待补工作项。

## 4. 本轮实际落库的关系

对 LLM 原始 5 条建议做人工筛选后，保留 3 条较稳妥关系并实际应用：

- `ingest-architecture-fragment-0003 -> ingest-knowledge-fragment-0004 [refines]`
- `ingest-knowledge-fragment-0005 -> ingest-agent_taxonomy-fragment-0004 [related_to]`
- `ingest-agent_taxonomy-fragment-0007 -> ingest-architecture-fragment-0003 [extends]`

剔除：

- `cites`：证据不足，语义偏弱
- `contradicts`：明显高风险 hallucination

## 5. 普通任务检索观察

普通任务：

- task id: `9178b9eb276f`
- goal: `Explain the relationship between knowledge truth, retrieval serving, and agent roles in the Swallow design docs`

观察：

- `retrieval_reused_knowledge_count: 6`
- `retrieval_reused_canonical_registry_count: 6`
- canonical knowledge 明显进入 top references
- `knowledge_priority_bonus=50` 生效，canonical 片段稳定排在前列

但也有两个现实问题：

1. `results/knowledge.md` 仍以高分压在第一位，说明 repo / notes 层噪声仍可能盖过 canonical；
2. 本轮新增 relation 已落库，但在这个 query 下没有明显出现 `relation expansion` 可见项，说明 direct hits 已足够强，expansion 没有带来额外曝光。

这与 Phase 56 review 中的判断一致：**relation expansion 逻辑成立，但在真实 query 下不一定显性可见。**

## 6. 对 Phase 57 的建议

基于本轮真实验证，Phase 57 启动前建议按以下优先级决策：

### P0

确认真实 provider 配置：

- chat 默认模型先用当前真正可跑通的模型；
- embedding 模型不要直接写死 `text-embedding-v1`，先以真实探针结果为准；
- 若坚持使用 `google/gemma-4-26b-a4b-it`，需要先在 provider 侧完成价格 / 分组配置。

### P1

优先考虑 **retrieval quality enhancement**，而不是继续追加更多 relation logic：

- neural embedding
- rerank
- chunking tuning

原因：

- canonical 优先级已成立；
- specialist LLM 分析已成立；
- 真正仍影响真实查询质量的是 top-1 噪声与 dense retrieval 基础设施不足。

### P2

将 literature-specialist 的真实 CLI 入口补齐，至少支持：

- `document_paths`
- 或显式 `knowledge_object_id` / `canonical_id` 输入

否则 operator 虽然能在内部 runtime 跑通 specialist，但无法完全靠公开 CLI 复现同样闭环。
