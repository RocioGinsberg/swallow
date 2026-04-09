# Phase 12 Kickoff

## 基本信息

- phase: `Phase 12`
- track: `Retrieval / Memory`
- slice: `Knowledge Promotion And Reuse Review`
- status: `kickoff`
- recommended_branch: `feat/phase12-knowledge-promotion-review`

---

## 启动背景

当前仓库已经完成：

- Phase 0 到 Phase 11 基线
- post-Phase-2 retrieval baseline
- post-Phase-5 executor / external-input slice
- post-Phase-5 retrieval / memory-next slice

这些阶段已经为当前系统建立了：

- 本地任务循环
- task semantics / knowledge objects 的显式输入边界
- inspect / review / control / recovery 相关 operator 路径
- reusable knowledge 的部分字段、分区、索引与检索边界

尤其是 Phase 11 已经解决了“输入如何进入系统”的问题：

- external planning 可以进入 task semantics
- external knowledge 可以进入 knowledge objects
- operator 已经可以 intake 和 inspect imported inputs

因此，下一轮默认不应继续扩大 intake 宽度，而应补齐 intake 之后的 review / promotion / reuse review 闭环。

---

## 当前问题

系统当前已经能“记录” imported knowledge，但还缺少清晰的 operator 决策链，用于回答以下问题：

- 哪些 staged knowledge 正在等待 review
- 哪些 knowledge objects 已具备 promote 条件
- 哪些 knowledge objects 应被 reject 或继续阻塞
- 谁在何时做了 promote / reject 决策
- 哪些 knowledge 已经达到 reuse-ready 状态
- 哪些 knowledge 仍被 stage / evidence / policy 卡住

也就是说，系统在 imported knowledge 上已经具备“录入能力”，但还缺少“显式提级与复用准备能力”。

---

## 本轮目标

Phase 12 的目标是建立一个**显式、可检查、可恢复的 knowledge promotion and reuse review 路径**。

本轮应实现：

1. staged knowledge 的 review queue
2. promote / reject 的 operator entrypoints
3. promotion decision record
4. reuse-readiness 的 inspection tightening
5. intake 之后的 operator 文档与帮助对齐

本轮目标不是自动化一切，而是让 operator 对 imported knowledge 的推进路径更清晰、更显式、更可追踪。

---

## 本轮非目标

本轮不默认推进以下方向：

- 扩大 planning / knowledge intake 的输入宽度
- 自动 knowledge promotion
- 隐式全局记忆
- remote ingestion / sync
- 大范围 Workbench / UX 扩张
- 重新打开旧 `post-phase-*` 过渡方向
- 让 imported planning 自动驱动 run preparation 或执行主循环
- 为了“以后可能需要”而提前引入平台型复杂度

---

## 设计边界

### 应保持稳定的部分

本轮不应破坏以下已有基线：

- 已接受的本地任务循环
- state / events / artifacts 的分层语义
- inspect / review / control / recovery 的现有 operator 路径
- task semantics 与 knowledge objects 的边界
- retrieval、routing、validation、memory 的现有 inspectable 语义

### 本轮新增能力应满足

- 所有 promote / reject 必须为显式操作
- promotion decision 必须可持久化
- reuse readiness 必须可检查
- knowledge objects 的推进路径必须保持 source traceability
- 不能通过隐式魔法绕过 evidence / policy / stage gating

---

## 本轮建议方向

本轮建议围绕以下问题组织实现：

### 1. review queue
给 operator 一个紧凑入口，快速看出：

- 待 review
- 可 promote
- blocked
- 已 reject / 已处理（如适用）

### 2. promote / reject
提供显式命令或等价 operator 入口：

- promote
- reject

要求：
- 不依赖 create-time flags 作为唯一控制点
- 不隐式修改无关对象

### 3. decision record
记录：

- 哪个 knowledge object
- 被谁
- 在何时
- 做了什么决策
- 基于什么条件推进或阻塞

### 4. reuse-readiness inspection
提供比现有 inspect / review 更直接的复用准备度视图，使 operator 能快速判断：

- 哪些对象可进入 retrieval reuse path
- 哪些对象仍被 evidence / stage / policy 卡住

### 5. docs/help alignment
确保 intake 之后的 review / promotion / reuse review 流程在：

- CLI help
- README
- phase 文档

之间保持一致。

---

## 完成条件

Phase 12 可以 closeout 的最低条件应包括：

1. 已有 imported knowledge 存在显式 review queue 路径
2. 已存在 promote 与 reject 的 operator entrypoints
3. promotion / rejection 结果可持久化并可检查
4. reuse-readiness 至少有一条紧凑 inspect 路径
5. 当前文档已说明 intake 之后的 review / promotion / reuse review 流
6. 不破坏当前稳定本地任务循环与现有 artifact 语义

---

## Git 节奏要求

本轮默认采用：

- 一个 phase 对应一个短生命周期 feature branch
- 一个 slice 对应一个或多个小步提交
- 高频状态只更新 `docs/active_context.md`
- phase 收口时再更新：
  - `docs/plans/phase12/closeout.md`
  - `current_state.md`
  - 必要时 `AGENTS.md`
  - 必要时 `README.md` / `README.zh-CN.md`

推荐提交类型：

- `feat(...)`
- `fix(...)`
- `refactor(...)`
- `test(...)`
- `docs(...)`
- `chore(context): update active context ...`

---

## 下一步

本 kickoff 落地后，下一步应完成：

1. `docs/plans/phase12/breakdown.md`
2. 明确最小 slice 顺序
3. 切出 `feat/phase12-knowledge-promotion-review`
4. 从 review queue baseline 开始实现