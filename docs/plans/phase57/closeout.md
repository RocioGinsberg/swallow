---
author: codex
phase: 57
slice: closeout
status: final
depends_on:
  - docs/plans/phase57/kickoff.md
  - docs/plans/phase57/design_decision.md
  - docs/plans/phase57/risk_assessment.md
  - docs/plans/phase57/pre_kickoff_real_data_validation.md
---

## TL;DR

Phase 57 已完成实现与 slice 拆 commit，当前状态为 **review pending / PR sync ready**。本轮将检索管线从“hash embedding + 单阶段排序”升级为“神经 embedding + LLM rerank + overlap chunking”，并补齐了 `literature-specialist` 的 CLI 输入透传缺口。结论：**phase implementation complete, ready for review / PR sync gate**。

# Phase 57 Closeout

## 结论

Phase 57 `Retrieval Quality Enhancement` 已完成实现与验证，当前分支状态为 **review pending / PR sync ready**。

本轮围绕 kickoff 定义的 4 个 slices，完成了以下能力增强：

- S1：向量检索切换到 API neural embedding，并将 canonical reuse 路径与 verified knowledge 路径对齐
- S2：`retrieve_context()` 出口新增可关闭、可退化的 LLM rerank
- S3：markdown / repo 检索分段加入 overlap 与超长 section 二次切分
- S4：`swl task create --executor literature-specialist` 支持 `--document-paths` 并贯通到 planner / specialist executor

当前尚未进入 Claude review，因此本轮 closeout 的语义是“实现完成，等待 review / PR 同步”，而不是 merge ready。

## 已完成范围

### Slice 1: Neural Embedding

- `runtime_config.py` 新增统一 embedding 配置：
  - `SWL_EMBEDDING_MODEL`
  - `SWL_EMBEDDING_DIMENSIONS`
  - `SWL_EMBEDDING_API_BASE_URL`
- `retrieval_adapters.py` 新增 `build_api_embedding()`
- `VectorRetrievalAdapter` 改为强依赖 neural embedding；embedding API 不可用时显式报错
- 仅 `sqlite-vec` 不可用时回退到文本检索
- `iter_canonical_reuse_items()` 改为走与 verified knowledge 一致的 vector/text fallback 路径
- `doctor.py` 新增 embedding API 探针

对应 commit：

- `631e3d2` `feat(retrieval): require neural embedding for vector search`

### Slice 2: LLM Rerank

- `retrieval_config.py` 新增 `RetrievalRerankConfig`
- 支持环境变量：
  - `SWL_RETRIEVAL_RERANK_ENABLED`
  - `SWL_RETRIEVAL_RERANK_TOP_N`
- `retrieve_context()` 在合并、去重、排序之后，对 top-N 执行 LLM rerank
- rerank 失败或 JSON 不可解析时，保留原排序
- rerank 元数据写入 `metadata` / `score_breakdown`

对应 commit：

- `11d3d92` `feat(retrieval): add llm rerank stage`

### Slice 3: Chunking 优化

- `build_markdown_chunks()` 新增：
  - `overlap_lines`
  - `max_chunk_size`
- markdown 长 section 优先按段落空行切分，不足时再按固定行数截断
- overlap 改为回带前序非空行，避免只重叠空白行
- `build_repo_chunks()` 增加固定窗口 overlap
- repo `chunk_id` 继续按原始 base range 编码，避免引用语义漂移

对应 commit：

- `30c4c5f` `feat(retrieval): improve chunk overlap behavior`

### Slice 4: Specialist CLI

- `task create` 新增 repeatable `--document-paths`
- 仅当 `--executor literature-specialist` 时，将绝对路径列表写入 `TaskState.input_context`
- `TaskState` 新增 `input_context` 持久化字段
- `planner._base_input_context()` 透传 `state.input_context`
- create → state → card → specialist executor 的 `document_paths` 全链路打通

对应 commit：

- `76c6d9c` `feat(cli): pass document paths to literature specialist`

## 与 kickoff 完成条件对照

### 已完成的目标

- `VectorRetrievalAdapter` 已使用 API embedding
- embedding API 失败时显式报错；`sqlite-vec` 缺失时退回文本检索
- `retrieve_context()` 返回前已具备可关闭的 rerank 阶段
- rerank 失败时不会阻断检索主流程
- `build_markdown_chunks()` 已支持 overlap 与 max chunk size
- `swl task create --executor literature-specialist --document-paths ...` 已可创建并透传 specialist 输入
- neural embedding / rerank / chunking / CLI 透传均有 pytest 覆盖

### 与原设计存在的已记录偏差

- kickoff / design 中曾写明 S1 在 embedding API 不可用时 fallback 到 local hash embedding；本轮实现已根据真实使用决策收紧为：
  - embedding API 失败显式报错
  - 仅 `sqlite-vec` 缺失时退回文本检索
- S4 设计文档中写的是“写入 task card 的 `executor_config`”；实际仓库现有稳定承载位为 `TaskState.input_context`，并经 planner 透传到 `TaskCard.input_context`。本轮按现有系统结构落地，没有引入新配置层。

以上偏差均为有意收敛，不构成未完成项。

## Stop / Go 判断

### Stop 判断

当前 phase 应停止继续扩张，理由如下：

- kickoff 定义的 S1 / S2 / S3 / S4 已全部完成，并已按 slice 独立提交
- 当前实现已覆盖前置真实数据验证暴露的 4 个核心缺口
- 再继续扩张会自然滑向下一轮问题域，例如 query rewrite、hybrid score normalization、编排增强或更大范围 eval 工作，不属于本轮 scope

### Go 判断

下一步应按如下顺序推进：

1. Human push 当前分支
2. Claude 执行 Phase 57 review
3. Codex 根据 review follow-up 修正实现或文档
4. Human 决定 PR / merge 节奏

## 当前稳定边界

Phase 57 closeout 后，以下边界应视为当前实现候选的稳定 checkpoint：

- 检索语义增强已落到 retrieval layer，不改 knowledge truth layer
- rerank 是 additive 的排序增强，不替代 direct hits
- chunking 优化仅影响 retrieve-time 分段，不回填历史 canonical text
- `literature-specialist` 的 CLI 入口已贯通，但只补齐输入透传，不扩张 specialist 生命周期语义
- 不引入 query rewrite / expansion、hybrid normalization 或 Graph RAG 新阶段

## 当前已知问题 / 后续候选

- rerank 是否在真实数据场景中稳定进入 top-K，仍取决于 direct hits 分布与 score 截断，不是代码 bug，但值得在真实数据验证中持续观察
- Phase 57 目前主要依靠 targeted pytest；针对真实数据的 operator-facing eval 还需要在下一轮测试阶段继续沉淀
- retrieval 配置仍分散在 `runtime_config.py` 与 `retrieval_config.py` 两层；若后续继续扩张检索策略，可考虑进一步整理 operator-facing 配置入口

以上问题均不阻塞进入 review 阶段。

## 测试结果

关键验证包括：

```bash
.venv/bin/python -m pytest tests/test_retrieval_adapters.py tests/test_doctor.py
.venv/bin/python -m pytest tests/test_retrieval_adapters.py
.venv/bin/python -m pytest tests/test_cli.py -k "literature_specialist_input_context or persists_route_dialect_for_default_aider_route"
.venv/bin/python -m pytest tests/test_specialist_agents.py -k "literature_specialist"
```

结果：

- `21 passed`
- `18 passed`
- `2 passed, 218 deselected`
- `5 passed, 11 deselected`

## 规则文件同步检查

### 必查

- [x] `docs/plans/phase57/closeout.md`
- [x] `docs/plans/phase57/kickoff.md`
- [x] `docs/active_context.md`
- [x] `current_state.md`

### 条件更新

- [ ] `docs/plans/phase57/review_comments.md`
- [ ] `./pr.md`
- [ ] `AGENTS.md`
- [ ] `README.md`
- [ ] `README.zh-CN.md`

说明：

- 当前尚未进入 review，因此不存在 `review_comments.md`
- 本轮尚未进入 PR 文案同步，因此 `pr.md` 暂不更新
- 本轮不涉及 tag-level 对外能力描述变更，暂不更新 `AGENTS.md` / README

## Git / Review 建议

1. 使用当前分支 `feat/phase57-retrieval-quality`
2. 以本 closeout 作为 review 前的 stop/go 参考
3. Claude review 后如有 follow-up，继续在同一分支吸收
4. review 通过后再同步 `pr.md` 并准备 merge

## 下一轮建议

如果 Phase 57 review / merge 完成，下一轮建议回到 roadmap 调整后的默认顺序，优先进入真实数据测试与编排增强邻接方向，而不是继续无边界扩张 retrieval 细节。
