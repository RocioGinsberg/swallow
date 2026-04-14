---
author: codex
phase: 28
slice: Knowledge Promotion & Refinement Baseline
status: final
depends_on:
  - docs/plans/phase28/context_brief.md
  - docs/plans/phase28/design_decision.md
  - docs/plans/phase28/risk_assessment.md
  - docs/plans/phase28/review_comments.md
---

## TL;DR
Phase 28 已完成实现、测试与 review 收口，当前状态为 **merge ready**。本轮在不改动 staged/canonical 核心数据模型的前提下，补齐了 staged knowledge 的聚合浏览、人工精炼晋升与显式冲突确认闭环。

# Phase 28 Closeout

## 结论

Phase 28 `Knowledge Promotion & Refinement Baseline` 已完成实现、测试验证与 review 收口准备，当前状态为 **merge ready**。

本轮完成了 staged knowledge 向 canonical registry 晋升路径上的最小易用性闭环：

- 新增 `task staged` 聚合浏览入口
- 支持 `knowledge stage-promote --text` 做人工精炼晋升
- 将 supersede 冲突从“仅提示”收紧为“显式确认后再晋升”

## 已完成范围

### Slice 1: `task staged` 聚合浏览命令

- 新增 `swl task staged`
- 支持：
  - `--status pending|promoted|rejected|all`
  - `--task <task_id>`
- 默认只展示 `pending` staged candidates
- 输出包含：
  - `candidate_id`
  - `status`
  - `source_task_id`
  - `submitted_at`
  - `text` 摘要

### Slice 2: 晋升时文本精炼

- 为 `swl knowledge stage-promote` 新增 `--text`
- canonical record 的 `text` 可使用人工精炼后的版本
- 原始 staged candidate 的 `text` 保持不变
- `decision_note` 自动追加 `[refined]` 审计标记

### Slice 3: Preflight 冲突提示增强

- `build_stage_promote_preflight_notices()` 改为结构化 notice
- CLI 输出改为：
  - `[SUPERSEDE]`
  - `[IDEMPOTENT]`
- 当存在 supersede 冲突时：
  - 默认拒绝晋升
  - 必须显式传入 `--force`
- idempotent 场景仅提示，不阻断

### 跨 Slice 回归修复

- 修正若干 `tests/test_cli.py` 中与当前 grounding / attempt 事件顺序对齐的断言
- 为旧测试 mock 补齐 `grounding_evidence_override` 参数签名
- 调整 retrieval 测试 fixture metadata，使 grounding 提取路径与当前基线一致

## 评审结论

- Claude review：**PASS**
- 无 `[BLOCK]`
- 一个 `[CONCERN]`：
  - `build_stage_promote_preflight_notices()` 的返回类型从 `list[str]` 变为 `list[dict[str, str]]`
  - 当前仅为内部函数签名调整，仓库内无外部调用者，影响可接受

## 测试结果

本轮最终验证结果：

```text
176 passed in 4.77s
```

补充说明：

- Phase 28 新增/变更相关定向测试已通过
- 完整 `tests/test_cli.py` 也已恢复全绿

## Stop / Go 边界

### 本轮 stop 在这里

- operator 已可从 `task staged` 聚合查看 staged candidates
- staged → canonical 晋升已支持人工文本精炼
- supersede 冲突已具备显式确认门槛
- 当前目标已在既定 CLI surface 内闭环，再继续扩张会越出本 phase 的易用性补齐边界

### 本轮不继续扩张到

- AI 自动晋升决策
- 语义/向量级去重
- 批量 staged promote
- staged/canonical 数据模型扩张
- 更复杂的 canonical conflict resolution workflow

## 与 design_decision 的对照

### 已完成的目标

- `task staged` 聚合浏览命令
- `knowledge stage-promote --text` 文本精炼
- supersede / idempotent preflight notice 强化
- supersede 场景 `--force` 显式确认
- 三个 slice 的 CLI help 与测试覆盖同步

### 未完成但已明确延后的目标

- 批量晋升
- 语义 dedupe / merge
- 自动晋升 / 自动 canonical promotion
- staged knowledge 与 retrieval 更深集成

这些项目均属于明确延后，不应视为本轮遗失 bug。

## 当前稳定边界

- `task staged` 已成为 staged knowledge 的 operator-facing 聚合浏览入口
- `knowledge stage-promote` 已具备 refine + force-confirm 的最小安全闭环
- staged candidate 原文与 canonical 精炼文本保持分离，审计线索通过 `decision_note` 保留
- canonical registry 的核心结构和 Phase 26 的 dedupe/supersede 逻辑未被重写
- Phase 27 grounding baseline 与本轮 CLI 改动保持兼容，完整 CLI 测试已验证

## 当前已知问题

- `build_stage_promote_preflight_notices()` 的内部返回结构已升级为结构化 dict；若未来出现新的外部调用者，需要继续保持该接口边界清晰
- `src/swallow/cli.py` 仍是仓库内较大的集中式 CLI 文件，本轮未进行拆分；如后续继续增加 operator surface，可单独立项做局部 refactor

## 规则文件同步检查

### 必查
- [x] `docs/plans/phase28/closeout.md`
- [ ] `current_state.md`
- [x] `docs/active_context.md`

### 条件更新
- [ ] `AGENTS.md`
- [ ] `.codex/session_bootstrap.md`
- [ ] `.codex/rules.md`
- [ ] `README.md`
- [ ] `README.zh-CN.md`

说明：

- `current_state.md` 建议在 Human 完成提交 / PR / merge 决策后再按真实 checkpoint 更新
- 本轮未改变长期规则、读取顺序或对外使用说明，因此其余文件无需同步

## Git 收口建议

1. Human 提交本轮实现与测试改动
2. 将 `docs/plans/phase28/closeout.md` 与 `pr.md` 一并纳入收口材料
3. Human push 当前分支，并基于 `pr.md` 创建或更新 PR
4. PR 合并后，再更新 `current_state.md` 与必要的入口状态文档

## 下一轮建议

- 合并完成前，不继续把 Phase 28 扩张为更大的 staged knowledge workflow phase
- 合并完成后，从 `docs/roadmap.md` 重新选择下一轮正式 phase
- 默认优先回到 roadmap 推荐队列，而不是继续在 Phase 28 上追加零散功能
