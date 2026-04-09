# Phase 13 Kickoff

## 基本信息

- phase: `Phase 13`
- track: `Retrieval / Memory`
- secondary_tracks:
  - `Workbench / UX`
  - `Evaluation / Policy`
- slice: `Canonical Knowledge Registry Baseline`
- status: `kickoff`
- recommended_branch: `feat/phase13-canonical-knowledge-registry`

---

## 启动背景

Phase 12 已完成 `Knowledge Promotion And Reuse Review` 的最小闭环。

当前系统已经具备：

- staged knowledge 的 review queue
- promote / reject entrypoints
- promotion / rejection decision record
- reuse-readiness inspect / review tightening
- task-level knowledge review queue / control visibility

因此，当前系统已经解决了：

- imported knowledge 如何进入 staged pipeline
- operator 如何显式 review / promote / reject

但仍缺少一个明确回答：

> 当 knowledge object 被显式 promote 为 canonical 之后，它在系统中到底进入哪里？

目前 canonical promotion 仍主要停留在 task-local knowledge object 状态层。

这意味着系统还没有建立：

- 独立于 task-local knowledge objects 的 canonical knowledge registry
- canonical records 的显式 inspect / list / trace path
- canonical promotion 与 registry persistence 的清晰对应关系

---

## 当前问题

当前仓库里已经有：

- task-linked staged knowledge
- retrieval-candidate reusable knowledge
- canonical stage 字段

但还没有一个稳定的 canonical registry baseline，去回答：

- 哪些 canonical knowledge 已经被正式写入系统级可检查结构
- canonical record 如何关联 source task、source object、source evidence
- canonical promotion 是否真的产生了 task 外部的持久化结果
- operator 如何查看当前 canonical knowledge 的最小索引视图

换句话说：

Phase 12 建立了显式 gate，但还没有建立 gate 之后的 canonical destination。

---

## 本轮目标

Phase 13 的目标是建立一个**显式、可检查、可追踪的 canonical knowledge registry baseline**。

本轮应实现：

1. canonical knowledge record schema
2. canonical registry persistence baseline
3. canonical promotion 到 registry 的显式写入路径
4. canonical registry inspect / list 入口
5. source task / source object / evidence traceability
6. CLI help / README / phase 文档对齐

本轮的重点不是“自动复用所有 canonical knowledge”，而是先把 canonical destination 做成显式系统结构。

---

## 本轮非目标

本轮不默认推进以下方向：

- automatic global memory
- implicit retrieval reuse of all canonical knowledge
- background sync / remote registry
- semantic dedupe / merge automation
- 大范围 workbench 扩张
- 多租户 canonical knowledge 平台
- 复杂 ranking / freshness / invalidation 体系

---

## 设计边界

### 应保持稳定的部分

本轮不应破坏：

- 已接受的本地任务循环
- Phase 12 的 promote / reject / decision record 基线
- task knowledge objects 与 canonical registry 的边界
- inspect / review / queue / control 的现有 operator 路径
- current retrieval baseline 中的显式 gate 语义

### 本轮新增能力应满足

- canonical registry 必须显式持久化
- registry record 必须保留 source task / source object traceability
- canonical promotion 不能变成隐式全局记忆开关
- canonical registry inspect path 必须紧凑、可读、可检查
- 不引入大规模知识平台抽象

---

## 本轮建议方向

### 1. canonical record schema

应至少记录：

- canonical_id
- source_task_id
- source_object_id
- promoted_at
- artifact_ref / source_ref
- canonical text
- optional note / decision reference

### 2. registry persistence

需要一个 task 外部的 canonical registry baseline。

目标不是最终平台设计，而是最小可检查结构，例如：

- `.swl/canonical_knowledge/*.jsonl`
- 或等价的 compact registry/index 结构

### 3. canonical promotion write path

当 operator 执行 canonical promotion 时，应产生：

- task-local stage update
- canonical registry record
- 可检查的 promotion trace

### 4. inspect / list path

operator 应至少能：

- 查看 canonical registry 概览
- 查看 canonical record 的 source trace
- 看出 canonical registry 中当前有哪些记录

### 5. doc alignment

确保 canonical knowledge 不被文档误写成“自动全局记忆”。

---

## 完成条件

Phase 13 可以 closeout 的最低条件应包括：

1. canonical promotion 能显式产出 task 外部 registry record
2. canonical registry 至少有一条紧凑 inspect / list 路径
3. canonical record 可追到 source task / object / evidence
4. 当前文档已明确 canonical registry 不是自动全局记忆
5. 不破坏已完成的 Phase 12 operator gate 和 artifact 语义

---

## 下一步

本 kickoff 落地后，下一步应完成：

1. `docs/plans/phase13/breakdown.md`
2. 明确 canonical registry 的最小存储位置
3. 切出 `feat/phase13-canonical-knowledge-registry`
4. 从 canonical registry schema / persistence baseline 开始实现
