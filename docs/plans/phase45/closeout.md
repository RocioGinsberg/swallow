---
author: codex
phase: 45
slice: all
status: draft
depends_on:
  - docs/plans/phase45/kickoff.md
  - docs/plans/phase45/risk_assessment.md
  - docs/concerns_backlog.md
---

## TL;DR
Phase 45 已完成实现与验证，当前状态为 **review pending / PR sync ready**。本轮新增了 eval 基础设施（默认 pytest 排除、`pytest -m eval` 单独触发）、Ingestion 降噪与 Meta-Optimizer 提案质量基线、ChatGPT 对话树主路径/侧枝还原，以及 `swl ingest --summary` 结构化摘要输出。当前专项验证包括 `314 passed, 2 deselected` 的默认 pytest 基线，以及 `2 passed, 314 deselected` 的 eval 基线。

# Phase 45 Closeout

## 结论

Phase 45 `Eval Baseline & Deep Ingestion` 已完成实现与验证，当前状态为 **review pending / PR sync ready**。

本轮围绕 kickoff 定义的 3 个 slice，交付了三个明确增量：

- S1：Eval-Driven Development 基础设施与两组质量基线
- S2：ChatGPT 对话树主路径提取与 abandoned branch 过滤
- S3：`swl ingest --summary` 结构化摘要输出

根目录 `pr.md` 已同步为本轮 PR 草稿，可直接作为 PR 描述更新依据。

## 已完成范围

### Slice 1: Eval Infrastructure + Quality Baselines

- `pyproject.toml` 新增 pytest eval marker 配置，默认 `pytest` 使用 `-m 'not eval'`
- 新增 `tests/eval/`：
  - `test_eval_ingestion_quality.py`
  - `test_eval_meta_optimizer_proposals.py`
- 新增 `tests/fixtures/eval_golden/` fixture 数据：
  - ChatGPT / Claude / Open WebUI golden ingestion cases
  - `meta_optimizer_scenarios/*.jsonl`
- eval 目标已编码为测试断言：
  - ingestion precision ≥ 0.80
  - ingestion recall ≥ 0.70
  - meta-optimizer scenario coverage ≥ 2/3

对应 commit：

- `test(eval): add phase45 quality baseline suite`

### Slice 2: ChatGPT Conversation Tree Restoration

- `src/swallow/ingestion/parsers.py` 的 `parse_chatgpt_export()` 不再仅按 `create_time` 线性平铺
- 新增主路径选择逻辑：优先保留最深、最新 leaf 所在路径
- 非主路径 turn 现在会标记：
  - `metadata["branch"] = "abandoned"`
  - `metadata["parent_turn_id"] = <parent>`
- `src/swallow/ingestion/filters.py` 同步新增 abandoned branch 过滤策略：
  - 中性侧枝直接丢弃
  - 含明确否定/替代语义的侧枝保留，并打上 `abandoned_branch` / `rejected_alternative`
- `merge_conversation_turns()` 不再跨 branch 边界合并消息

对应 commit：

- `feat(ingestion): restore chatgpt conversation branches`

### Slice 3: Structured Summary Output

- `src/swallow/ingestion/pipeline.py` 新增 `build_ingestion_summary()`
- `swl ingest` 新增 `--summary` 参数
- 输出在原有 `# Ingestion Report` 后追加：
  - `## Decisions`
  - `## Constraints`
  - `## Rejected Alternatives`
  - `## Statistics`
- rejected alternatives 除消费 S2 的 `branch=abandoned` / `rejected_alternative` 外，也对文档类文本中的 `reject / abandon / switch to / 改用 / 放弃` 做兜底识别

对应 commit：

- `feat(ingestion): add structured summary output`

## 与 kickoff 完成条件对照

### 已完成的目标

- `tests/eval/` 目录和 pytest eval marker 配置可用
- 默认 `pytest` 不执行 eval 测试
- `pytest -m eval` 可单独执行 eval 测试
- ingestion eval 建立了 precision / recall 基线
- meta-optimizer eval 建立了 scenario-based proposal coverage 基线
- ChatGPT 对话树主路径 / 侧枝区分已实现
- `swl ingest --summary` 结构化摘要可用
- 默认 pytest 与 eval pytest 都通过

### 未继续扩张的内容

以下方向仍明确不在本 phase 范围内：

- 不引入 LLM 辅助降噪
- 不引入 Langsmith / Braintrust 等 eval 平台
- 不做自动化晋升流
- 不做 RAG / embedding 质量 eval
- 不做 Literature Specialist

## Backlog 同步

- 当前 `docs/concerns_backlog.md` 无 Open concern
- 本轮实现没有新增 concern，也没有需要回写 backlog 的 review follow-up

## Review Follow-up

- Claude review 尚未开始，当前阶段为 `review pending`
- `pr.md` 已整理为 Phase 45 草稿，可直接用于创建或更新 PR

## Stop / Go 判断

### Stop 判断

当前 phase 应停止继续扩张，理由如下：

- kickoff 定义的 3 个 slice 已全部完成，并已按 slice 独立提交
- eval 基础设施、对话树还原、摘要输出三条链路都已落地
- 再继续扩张会自然滑向自动晋升、LLM 降噪或 specialist 体系，不属于本轮范围

### Go 判断

下一步应按如下顺序推进：

1. Claude 对 Phase 45 做 review
2. Human 使用 `pr.md` 更新 PR 描述
3. review 完成后再同步最终 closeout 状态

## 当前稳定边界

Phase 45 实现完成后，以下边界应视为当前候选稳定 checkpoint：

- eval 仍是 pytest 内部机制，不引入外部平台
- eval 仍是质量信号，不是 merge blocker
- ChatGPT 分支解析仅对 ChatGPT export 生效，不影响 Claude / Open WebUI / Markdown
- `swl ingest --summary` 只追加文本输出，不改变 staged candidate 持久化逻辑

## 当前已知问题

- ingestion eval 的 golden dataset 目前仍是小规模人工构造样本，不是大规模真实导出语料
- `build_ingestion_summary()` 当前仍是关键词和 signal 驱动，不做语义归纳或跨 fragment 合并
- abandoned branch 的主路径选择仍基于当前导出结构的启发式，不是平台官方“active branch”字段
- eval 基线目前只覆盖 ingestion 与 meta-optimizer 两处，没有扩展到 retrieval 或端到端真实模型 smoke test

以上问题均不阻塞当前进入 review 阶段。

## 测试结果

最终验证结果：

```text
.venv/bin/python -m pytest -> 314 passed, 2 deselected in 7.02s
.venv/bin/python -m pytest -m eval -> 2 passed, 314 deselected in 0.29s
.venv/bin/python -m pytest tests/test_ingestion_parsers.py tests/test_ingestion_filters.py tests/test_ingestion_pipeline.py -> 26 passed
.venv/bin/python -m pytest tests/test_ingestion_pipeline.py tests/test_cli.py -> 200 passed
```

补充说明：

- 默认测试基线和 eval 基线均已单独验证
- S2 与 S3 都在对应范围内做了回归验证

## 规则文件同步检查

### 必查

- [x] `docs/plans/phase45/closeout.md`
- [x] `docs/plans/phase45/kickoff.md`
- [x] `docs/plans/phase45/risk_assessment.md`
- [x] `docs/active_context.md`
- [x] `docs/concerns_backlog.md`
- [x] `./pr.md`

### 条件更新

- [ ] `docs/plans/phase45/review_comments.md`
- [ ] `AGENTS.md`
- [ ] `README.md`
- [ ] `README.zh-CN.md`

说明：

- 当前仍处于 review pending，尚未生成 `review_comments.md`
- 本轮未改变长期协作规则与 tag 级对外能力快照，暂不更新 `AGENTS.md` / README

## Git / PR 建议

1. 使用当前根目录 `pr.md` 作为 PR 描述草案
2. 当前 PR 描述应标记为 `review pending`
3. 等待 Claude review 结论后再同步最终 closeout 与 PR 状态

## 下一轮建议

如果 Phase 45 review 通过并 merge 完成，下一轮应回到 roadmap，优先考虑 Phase 46 的共识 / policy guardrails 或更深一层的 ingestion / specialist 工作，但不应在当前分支直接扩张自动晋升或 LLM 降噪。
