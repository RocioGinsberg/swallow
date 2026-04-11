# Phase 14 Kickoff

## 基本信息

- phase: `Phase 14`
- track: `Retrieval / Memory`
- secondary_tracks:
  - `Evaluation / Policy`
  - `Workbench / UX`
- slice: `Canonical Reuse Policy Baseline`
- status: `kickoff`
- recommended_branch: `feat/phase14-canonical-reuse-policy`

---

## 启动背景

Phase 12 已完成 `Knowledge Promotion And Reuse Review` 的显式 gate。

Phase 13 已完成 `Canonical Knowledge Registry Baseline`，当前系统已经具备：

- task 外部 canonical registry
- canonical promotion write-through
- canonical registry / index inspect 路径
- canonical traceability、dedupe 与 trace-based supersede

因此，当前系统已经解决了：

- staged knowledge 如何通过显式 decision 进入 canonical
- canonical records 如何落到 task 外部持久化结构
- operator 如何检查当前 canonical registry

但仍缺少一个明确回答：

> canonical registry 中的记录，何时、以什么显式规则、通过什么边界，才能进入后续任务的 retrieval / reuse 路径？

目前 canonical registry 仍是“已持久化、可检查”的结构，而不是“已定义 reuse policy”的结构。

---

## 当前问题

当前仓库里已经有：

- staged knowledge review / promote / reject gate
- reusable candidate 与 canonical registry 的显式边界
- canonical registry 的 inspect / index / traceability

但还没有一个稳定的 canonical reuse policy baseline，去回答：

- 哪些 canonical records 默认可用于后续 retrieval
- canonical registry 是否应全部开放，还是仍需显式筛选
- canonical records 进入 retrieval 时如何保持 source traceability
- canonical supersede / inactive 状态是否应影响 reuse visibility
- operator 如何检查当前 canonical reuse policy 的最小结果

换句话说：

Phase 13 建立了 canonical destination，但还没有建立 destination 之后的 reuse policy。

---

## 本轮目标

Phase 14 的目标是建立一个**显式、可检查、可追踪的 canonical reuse policy baseline**。

本轮应实现：

1. canonical registry 到 retrieval reuse 的显式 policy 边界
2. canonical records 的最小 eligibility / visibility 规则
3. policy-aware canonical reuse inspect path
4. canonical retrieval 输出中的 source trace 保持
5. CLI help / README / phase 文档对齐

本轮重点不是自动启用全部 canonical records，而是先把“哪些 canonical 可以被后续 retrieval 看见”做成显式系统规则。

---

## 本轮非目标

本轮不默认推进以下方向：

- automatic global memory
- semantic merge / fuzzy dedupe
- remote registry sync
- background refresh / invalidation workers
- 广义 canonical governance workflow
- 大范围 workbench 扩张
- 让 canonical registry 绕过现有 retrieval / policy gate

---

## 设计边界

### 应保持稳定的部分

本轮不应破坏：

- Phase 12 的 staged knowledge review gate
- Phase 13 的 canonical registry / index / inspect baseline
- task knowledge objects 与 canonical registry 的边界
- inspect / review / queue / control 的现有 operator 路径
- 当前 retrieval baseline 中的显式 traceability 语义

### 本轮新增能力应满足

- canonical reuse 必须由显式 policy 控制
- policy 结果必须可检查，而不是隐式藏在 retrieval 逻辑里
- canonical traceability 在 reuse 输出中必须保持可见
- superseded canonical records 不应被默认当作 active reuse inputs
- 不引入大规模历史知识平台抽象

---

## 本轮建议方向

### 1. canonical reuse policy schema

应至少定义：

- active canonical records 的默认可见性
- superseded canonical records 的默认处理
- source trace 在 retrieval reuse 中的保留要求
- canonical registry 与 retrieval candidate knowledge 的边界

### 2. policy-aware canonical index / summary

需要一个最小伴随结构，说明：

- 当前 registry 中哪些 records reuse-visible
- 哪些 records 被 supersede 或 policy 排除
- 当前 policy 判断的摘要与计数

### 3. retrieval integration baseline

当后续 task 需要 retrieval reuse 时，应至少能：

- 显式读取 reuse-visible canonical records
- 保持 source task / object / artifact traceability
- 不把 canonical registry 误当作自动全局记忆

### 4. inspect / list path

operator 应至少能：

- 查看 canonical reuse policy 摘要
- 看出当前有多少 canonical records 可见 / 不可见
- 看到 active 与 superseded 对 reuse 的影响

### 5. doc alignment

确保 canonical reuse policy 不被文档误写成“自动全局记忆已开启”。

---

## 完成条件

Phase 14 可以 closeout 的最低条件应包括：

1. canonical registry 到 retrieval reuse 之间有显式 policy baseline
2. 至少有一条 operator-facing inspect path 能看到 reuse-visible canonical 摘要
3. superseded canonical records 的默认 reuse 行为已写清楚
4. retrieval reuse 仍保持 source traceability
5. 当前文档已明确 canonical reuse policy 不是自动全局记忆

---

## 下一步

本 kickoff 落地后，下一步应完成：

1. `docs/plans/phase14/breakdown.md`
2. 明确 canonical reuse policy 的最小存储与 inspect 结构
3. 切出 `feat/phase14-canonical-reuse-policy`
4. 从 policy schema / summary baseline 开始实现
