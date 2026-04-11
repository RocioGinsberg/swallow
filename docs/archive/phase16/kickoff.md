# Phase 16 Kickoff

## 基本信息

- phase: `Phase 16`
- track: `Evaluation / Policy`
- secondary_tracks:
  - `Retrieval / Memory`
  - `Workbench / UX`
- slice: `Canonical Reuse Regression Baseline`
- status: `kickoff`
- recommended_branch: `feat/phase16-canonical-reuse-regression`

---

## 启动背景

Phase 15 已完成 `Canonical Reuse Evaluation Baseline`。

当前系统已经具备：

- task-local `canonical_reuse_eval.jsonl` judgment record
- `canonical_reuse_eval_report.md` summary/report artifact
- `canonical-reuse-evaluate`、`canonical-reuse-eval`、`canonical-reuse-eval-json` operator 入口
- canonical citation resolution
- optional retrieval provenance attachment

因此，系统已经能回答：

- 某次 task 中有哪些 canonical reuse hits 被显式评为 `useful` / `noisy` / `needs_review`
- operator 如何在 inspect / review 中看到当前 evaluation 摘要

但仍缺少一个明确回答：

> 当 canonical reuse policy、retrieval 规则或 canonical corpus 继续变化时，系统如何稳定判断“当前 reuse baseline 变好了、变差了，还是只是变了”？

Phase 15 建立了 evaluation truth 的记录面，但还没有建立 regression truth 的比较面。

---

## 当前问题

当前仓库里已经有：

- explicit evaluation record
- inspectable judgment summary
- canonical citation to canonical metadata resolution
- retrieval-aware provenance linkage

但还没有一个稳定的 regression baseline 去回答：

- 当前 canonical reuse judgment 分布是否相对既有基线发生退化
- 当前 resolved / unresolved citation 情况是否变差
- retrieval-matched canonical hits 是否出现明显偏移
- operator 如何在一次变更后快速比较“现在”和“基线”

换句话说：

Phase 15 建立了 evaluation record，但还没有建立 evaluation record 的 reusable comparison truth。

---

## 本轮目标

Phase 16 的目标是建立一个**显式、轻量、可比较的 canonical reuse regression baseline**。

本轮应实现：

1. canonical reuse regression baseline artifact
2. baseline 与当前 evaluation summary 的最小 compare path
3. operator-facing regression snapshot / inspect surface
4. 文档与命名对齐，明确这是 regression baseline，不是自动 policy learning

本轮重点不是自动调 policy，而是先把“当前 reuse baseline 是否退化”做成显式系统判断入口。

---

## 本轮非目标

本轮不默认推进以下方向：

- automatic policy rewrite from evaluation judgments
- queue / control 自动升级或阻断流程
- broader retrieval ranking platform
- canonical freshness / invalidation workflow
- remote evaluation sync
- generalized scoring framework for all retrieval sources

---

## 设计边界

### 应保持稳定的部分

本轮不应破坏：

- Phase 15 的 evaluation record / summary / report baseline
- canonical citation resolution 语义
- retrieval provenance 的 optional attachment 语义
- 现有 `inspect` / `review` / CLI 命令边界

### 本轮新增能力应满足

- regression baseline 必须显式落在 artifact 中
- compare 结果必须可检查，而不是靠人工 diff 零散 JSON
- baseline 应复用 Phase 15 judgment vocabulary，而不是新造评分体系
- 不把 regression baseline 误做成自动策略优化器
- 保持 task-local / local-first / 可恢复的路径

---

## 影响范围

本轮大概率会涉及：

- `src/swallow/canonical_reuse_eval.py`
- `src/swallow/orchestrator.py`
- `src/swallow/cli.py`
- `src/swallow/paths.py`
- `src/swallow/store.py`
- `tests/test_cli.py`
- `docs/active_context.md`
- `docs/plans/phase16/*`

---

## 完成条件

Phase 16 可以 closeout 的最低条件应包括：

1. canonical reuse regression baseline 有显式 artifact 表达
2. 至少有一条 operator-facing compare / inspect path 能看到 regression snapshot
3. comparison 复用 Phase 15 summary semantics，而不是另起一套模糊评分
4. 当前文档已明确 regression baseline 不是自动 policy learning
5. 不破坏已有 evaluation baseline 与 retrieval provenance 语义

---

## 下一步

本 kickoff 落地后，下一步应完成：

1. `docs/plans/phase16/breakdown.md`
2. 切出 `feat/phase16-canonical-reuse-regression`
3. 从 regression baseline artifact / compare baseline 开始实现
