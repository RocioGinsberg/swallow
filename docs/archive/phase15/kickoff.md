# Phase 15 Kickoff

## 基本信息

- phase: `Phase 15`
- track: `Evaluation / Policy`
- secondary_tracks:
  - `Retrieval / Memory`
  - `Workbench / UX`
- slice: `Canonical Reuse Evaluation Baseline`
- status: `kickoff`
- recommended_branch: `feat/phase15-canonical-reuse-evaluation`

---

## 启动背景

Phase 12 已完成 `Knowledge Promotion And Reuse Review` 的显式 gate。

Phase 13 已完成 `Canonical Knowledge Registry Baseline`。

Phase 14 已完成 `Canonical Reuse Policy Baseline`，当前系统已经具备：

- canonical registry / index / inspect 路径
- canonical reuse policy summary
- retrieval 对 policy-visible canonical records 的读取
- retrieval report / grounding / summary / resume note 中的 canonical reuse traceability

因此，当前系统已经解决了：

- canonical knowledge 如何进入 task 外 registry
- canonical records 如何通过显式 policy 进入 retrieval reuse
- operator 如何检查 canonical reuse 的当前可见面

但仍缺少一个明确回答：

> 当前 canonical reuse policy 实际上是否有效，operator 应该依据什么最小评价结构来判断它值得继续扩展？

目前系统已经有 canonical reuse 路径，但还没有一个显式 evaluation baseline 去回答：

- retrieval 命中的 canonical reuse 是否有用
- 哪些 canonical hits 只是噪音
- supersede / visibility 规则是否带来误召回或漏召回
- operator 如何记录和复查这些判断

---

## 当前问题

当前仓库里已经有：

- canonical destination
- canonical reuse policy
- retrieval integration
- inspectable traceability

但还没有一个稳定的 canonical reuse evaluation baseline，去回答：

- 当前 retrieval 里有多少 hits 来自 canonical reuse
- 这些 canonical hits 是否被认为有效 / 无效 / 待复查
- operator 如何记录 evaluation judgment
- policy baseline 是否需要后续收紧或放宽
- 如何形成最小 regression truth，而不是只凭直觉继续加规则

换句话说：

Phase 14 建立了 reuse path，但还没有建立 reuse path 的 evaluation truth。

---

## 本轮目标

Phase 15 的目标是建立一个**显式、可检查、可回顾的 canonical reuse evaluation baseline**。

本轮应实现：

1. canonical reuse evaluation record schema
2. evaluation summary / artifact baseline
3. operator-facing inspect path for canonical reuse evaluation
4. retrieval hit provenance 与 evaluation judgment 的最小对应关系
5. CLI help / README / phase 文档对齐

本轮重点不是自动优化 policy，而是先把“当前 canonical reuse 是否有用”做成显式系统记录。

---

## 本轮非目标

本轮不默认推进以下方向：

- automatic policy learning
- semantic relevance scoring platform
- large-scale ranking / rerank redesign
- canonical freshness / invalidation workflow
- remote evaluation sync
- 大范围 workbench 扩张
- 让 evaluation judgment 自动驱动 policy 改写

---

## 设计边界

### 应保持稳定的部分

本轮不应破坏：

- Phase 12 的 explicit review / promote / reject gate
- Phase 13 的 canonical registry baseline
- Phase 14 的 canonical reuse policy / retrieval integration baseline
- 当前 retrieval traceability 语义
- inspect / review / queue / control 的既有 operator 路径

### 本轮新增能力应满足

- evaluation judgment 必须显式记录
- evaluation 结果必须可检查，而不是散落在聊天历史里
- canonical reuse hit 与 evaluation judgment 之间要保留 provenance 对应关系
- 不把 evaluation baseline 误做成自动 policy optimizer
- 不引入过大抽象或平台化复杂度

---

## 本轮建议方向

### 1. canonical reuse evaluation schema

应至少定义：

- evaluated_at
- evaluated_by
- task_id / retrieval_context_ref
- canonical references under review
- judgment status（如 useful / noisy / needs_review）
- optional note

### 2. evaluation summary / artifact

需要一个最小伴随结构，说明：

- 当前记录了多少 canonical reuse evaluations
- useful / noisy / needs_review 各有多少
- 最近一次 evaluation 指向哪些 canonical references

### 3. inspect / list path

operator 应至少能：

- 查看 canonical reuse evaluation 摘要
- 看出当前 canonical reuse baseline 的最小 judgment 分布
- 追到 evaluation 对应的 retrieval / canonical references

### 4. retrieval provenance linkage

evaluation 至少应能显式引用：

- canonical_id
- citation / source trace
- task / run context

### 5. doc alignment

确保 canonical reuse evaluation 不被误写成自动策略学习或自动 policy tuning。

---

## 完成条件

Phase 15 可以 closeout 的最低条件应包括：

1. canonical reuse evaluation 有显式 record baseline
2. 至少有一条 operator-facing inspect path 能看到 evaluation 摘要
3. retrieval hit provenance 与 evaluation judgment 可追溯
4. 当前文档已明确 evaluation baseline 不是自动优化器
5. 不破坏已有 canonical reuse policy baseline

---

## 下一步

本 kickoff 落地后，下一步应完成：

1. `docs/plans/phase15/breakdown.md`
2. 明确 canonical reuse evaluation 的最小存储与 inspect 结构
3. 切出 `feat/phase15-canonical-reuse-evaluation`
4. 从 evaluation schema / summary baseline 开始实现
