# Phase 12 Breakdown

## 基本信息

- phase: `Phase 12`
- track: `Retrieval / Memory`
- slice: `Knowledge Promotion And Reuse Review`
- branch: `feat/phase12-knowledge-promotion-review`

---

## 总体目标

把当前系统中已存在的 imported knowledge / staged knowledge，从“已记录”推进到“可审查、可决策、可复用准备”的显式 operator 流程。

本轮重点不是新增 intake 能力，而是补齐 intake 之后的 review / promotion / reuse review 闭环。

---

## 默认实现顺序

本轮建议按以下顺序推进：

1. review queue baseline
2. promote / reject entrypoints
3. decision record / artifact
4. reuse-readiness inspection tightening
5. help / README alignment
6. phase closeout

这样做的原因是：

- 先给 operator 一个可见入口
- 再给 operator 可执行动作
- 再把动作结果持久化
- 最后再优化 inspect / 文档路径

---

## Slice 列表

---

### P12-01 review queue baseline

#### 目标

建立一个紧凑的 review queue，让 operator 能快速看出当前 knowledge objects 中哪些：

- 待 review
- 可 promote
- blocked
- 已 reject / 已处理（如当前实现需要）

#### 建议范围

可优先考虑：

- 新增 `swl task knowledge-review-queue`
- 或在现有 inspect / review 路径上补出一个 compact queue 输出

输出至少应能体现：

- object id
- stage
- evidence 状态
- reuse readiness 相关关键信号
- 当前推荐动作（如 `review` / `promote-ready` / `blocked`）

#### 验收条件

- operator 不必先打开原始 JSON 才能看出待处理 knowledge objects
- queue 至少能区分“可进一步处理”和“仍然被阻塞”的对象
- 输出语义与已有 stage / evidence / policy 边界保持一致

#### 推荐提交粒度

- `feat(knowledge): classify review queue states`
- `feat(cli): add knowledge review queue command`
- `test(knowledge): cover review queue output`

---

### P12-02 promote / reject entrypoints

#### 目标

给 operator 提供显式的 staged knowledge 推进与拒绝入口。

#### 建议范围

新增显式操作，例如：

- `swl task knowledge-promote <task-id> ...`
- `swl task knowledge-reject <task-id> ...`

或等价命令边界。

要求：

- promote / reject 必须是显式操作
- 不依赖 create-time flags 作为唯一控制点
- 不隐式修改无关对象
- 不自动推进整批对象，除非明确指定

#### 验收条件

- operator 能明确指定某个 knowledge object 的 promote / reject 动作
- promote / reject 后的对象状态变化可持久化
- 当前命令边界不会和 intake、inspect、review 语义打架

#### 推荐提交粒度

- `feat(knowledge): add promote and reject operations`
- `feat(cli): add knowledge promote and reject commands`
- `test(knowledge): cover promote and reject flows`

---

### P12-03 decision record / artifact

#### 目标

把 promote / reject 决策变成可检查的持久化记录，而不是瞬时命令效果。

#### 建议范围

应至少记录：

- object id
- decision type（promote / reject）
- previous state
- new state
- decided at
- decided by / operator ref（如果当前模型里有）
- optional reason / note

可落在：

- 单独 JSON record
- 独立 report artifact
- 或纳入已有 knowledge-related artifact 体系

要求：
- 记录结构清晰
- inspect / review 路径后续可消费
- 不引入不必要的复杂事件系统重构

#### 验收条件

- promote / reject 的结果不是“只改状态不留痕”
- operator 能通过 artifact 或 inspect 路径看到决策链
- 决策记录与对象状态一致，不出现明显双写冲突

#### 推荐提交粒度

- `feat(knowledge): persist promotion decisions`
- `feat(artifacts): add knowledge decision record artifact`
- `test(knowledge): verify decision persistence`

---

### P12-04 reuse-readiness inspection tightening

#### 目标

让 operator 更直接看出哪些 knowledge objects 已经具备 reuse 条件，哪些仍被 stage / evidence / policy 卡住。

#### 建议范围

优先加强以下路径中的至少一条：

- `swl task inspect`
- `swl task review`
- 新增 compact reuse-readiness 命令
- knowledge report / queue 输出

可重点展示：

- reusable / blocked / task-only
- blocked reason
- evidence readiness
- stage readiness
- policy readiness

#### 验收条件

- operator 可以不读多份底层 JSON，就快速判断复用准备度
- 当前输出不会误导为“已经自动进入 retrieval reuse”
- blocked 对象的阻塞原因尽量可见

#### 推荐提交粒度

- `feat(knowledge): expose reuse readiness states`
- `feat(cli): tighten inspect output for reusable knowledge`
- `test(knowledge): cover reuse readiness inspection`

---

### P12-05 help / README alignment

#### 目标

让 intake 之后的 review / promotion / reuse review 流程在 operator-facing 文档中可见。

#### 建议范围

同步以下内容中至少必要部分：

- CLI help
- `README.md`
- `README.zh-CN.md`
- `AGENTS.md`
- `docs/active_context.md`

要求：
- 文档只更新与当前 phase 直接相关的内容
- 不顺手重写整个 README
- 不把 README 变成 phase 历史总表

#### 验收条件

- operator 能从文档中理解 intake 之后如何进入 review / promotion / reuse review
- 文档与命令名、artifact 名、inspect 路径一致
- 不引入新的文档重复层

#### 推荐提交粒度

- `docs(readme): document knowledge review workflow`
- `docs(agents): align phase12 workflow guidance`
- `docs(help): update CLI help for review and promotion paths`

---

### P12-06 closeout

#### 目标

完成 Phase 12 的正式收口，而不是只停留在实现完成但文档边界模糊的状态。

#### 建议范围

收口时更新：

- `docs/plans/phase12/closeout.md`
- `current_state.md`
- 必要时 `AGENTS.md`
- 必要时 `README.md` / `README.zh-CN.md`
- 可选 `docs/plans/phase12/commit_summary.md`

#### 验收条件

- 当前 phase 的完成条件已判断
- 当前 phase 的 stop/go 边界已写清楚
- 下一轮起点明确
- 高频状态信息没有继续滞留在 `active_context.md` 中冒充长期归档

#### 推荐提交粒度

- `docs(phase12): add closeout note`
- `chore(state): refresh current state after phase12 closeout`
- `docs(phase12): add commit summary`（可选）

---

## 默认不做的工作

以下方向不应在本 breakdown 中默认混入：

- 新 intake 类型扩张
- 自动 knowledge promotion
- remote ingestion / sync
- 大范围 workbench UI 扩张
- 重新整理旧 `post-phase-*`
- 让 imported planning 自动驱动 run preparation
- 把本轮顺手升级成新的大规模 retrieval architecture 重构

如果开发过程中出现这些方向，应先判断：

1. 是否只是当前 slice 的局部实现细节
2. 是否应该延后到下一 phase
3. 是否应该单列为未来新的 track slice

---

## 当前建议里程碑

### Milestone A
完成：

- P12-01 review queue baseline
- P12-02 promote / reject entrypoints

说明：
- 先建立“看得到 + 能操作”的最小闭环

### Milestone B
完成：

- P12-03 decision record / artifact
- P12-04 reuse-readiness inspection tightening

说明：
- 再补齐“动作留痕 + 可检查复用准备度”

### Milestone C
完成：

- P12-05 docs/help alignment
- P12-06 closeout

说明：
- 最后做 operator-facing 收口与 phase 边界确认

---

## 当前建议 Git 节奏

### 分支
- `feat/phase12-knowledge-promotion-review`

### 高频状态更新
只更新：
- `docs/active_context.md`

### 低频同步
仅在 major slice 或 phase 收口时更新：
- `current_state.md`
- `AGENTS.md`
- `README.md`
- `README.zh-CN.md`

### 提交建议
每个 slice 尽量拆成：

1. 功能
2. 测试
3. 必要的当前上下文同步
4. 收口文档

---

## 当前 stop / go 判断

### 可以继续推进的前提
- 当前实现不破坏既有本地任务循环
- knowledge stage / evidence / reuse / policy 语义仍保持一致
- 新命令和新 artifact 不明显重复已有路径

### 应暂停并重新收口的信号
- 当前改动开始扩展到新的 intake 宽度
- 当前改动开始隐式自动 promotion
- 当前改动开始重写大量 workbench / retrieval / policy 边界
- 当前 slice 无法用一个明确 commit 集合解释清楚

---

## 下一步

当前 breakdown 落地后，应立即进入：

1. 切出 `feat/phase12-knowledge-promotion-review`
2. 优先实现 `P12-01 review queue baseline`
3. 在 `docs/active_context.md` 中记录首个 slice 的推进状态