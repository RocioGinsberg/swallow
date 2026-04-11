# Phase 14 Breakdown

## 基本信息

- phase: `Phase 14`
- track: `Retrieval / Memory`
- secondary_tracks:
  - `Evaluation / Policy`
  - `Workbench / UX`
- slice: `Canonical Reuse Policy Baseline`
- branch: `feat/phase14-canonical-reuse-policy`

---

## 总体目标

把当前已经具备 canonical registry baseline 的知识路径，从“显式持久化”推进到“显式 reuse policy baseline”。

本轮重点不是自动开放全部 canonical records，而是建立可检查、可追踪、受 policy 控制的 canonical reuse visibility。

---

## 默认实现顺序

本轮建议按以下顺序推进：

1. canonical reuse policy schema
2. canonical reuse summary / index
3. retrieval integration baseline
4. canonical reuse inspect / list path
5. docs / help alignment
6. phase closeout

这样做的原因是：

- 先明确 policy 长什么样
- 再明确哪些 canonical records 当前可见
- 再把 policy 接到 retrieval reuse
- 最后再补 operator-facing inspect 和文档

---

## Slice 列表

### P14-01 canonical reuse policy schema

#### 目标

定义 canonical records 进入 retrieval reuse 的最小 policy 结构。

#### 建议范围

至少包含：

- reuse-visible active canonical count
- superseded canonical exclusion baseline
- source-trace preservation expectation
- canonical registry 与 task-local reusable knowledge 的边界

#### 验收条件

- canonical reuse 不再只是隐式读取 registry 全量记录
- policy 字段清晰、可检查
- 不引入过早复杂抽象

#### 推荐提交粒度

- `feat(policy): define canonical reuse policy baseline`

---

### P14-02 canonical reuse summary / index

#### 目标

建立 canonical reuse 的最小 summary / index 结构。

#### 建议范围

可优先考虑：

- `.swl/canonical_knowledge/` 下新增 reuse summary 结构
- 复用现有 canonical registry index 的伴随摘要

#### 验收条件

- operator 可以看出当前多少 canonical records reuse-visible
- superseded / inactive canonical records 的排除结果可见
- 不再只依赖 registry 原始 records 推断 policy 结果

#### 推荐提交粒度

- `feat(knowledge): add canonical reuse summary baseline`
- `test(knowledge): cover canonical reuse summary`

---

### P14-03 retrieval integration baseline

#### 目标

把 canonical reuse policy 接到 retrieval reuse 路径。

#### 建议范围

当 retrieval 需要读取 canonical records 时：

- 只读取 policy-visible canonical records
- 保留 source task / object / artifact traceability
- 不影响 task-local staged knowledge 的显式 gate

#### 验收条件

- canonical reuse 不会隐式放开所有 registry records
- retrieval 输出保持 traceability
- superseded canonical records 默认不会误入 active reuse

#### 推荐提交粒度

- `feat(retrieval): apply canonical reuse policy`
- `test(retrieval): cover canonical reuse visibility`

---

### P14-04 canonical reuse inspect / list path

#### 目标

给 operator 提供一个紧凑 canonical reuse inspection path。

#### 建议范围

可优先考虑：

- `swl task canonical-reuse`
- 或 task/workbench 范围内的等价 inspect 入口

重点展示：

- reuse-visible canonical count
- superseded / excluded canonical count
- latest active canonical trace

#### 验收条件

- operator 不打开底层 JSON 也能看到 canonical reuse policy 摘要
- inspect path 不误导为“自动全局记忆已开启”
- source traceability 保持可见

#### 推荐提交粒度

- `feat(cli): add canonical reuse inspect command`
- `test(cli): cover canonical reuse inspection`

---

### P14-05 docs / help alignment

#### 目标

让 canonical reuse policy baseline 的 operator 语义在文档中可见。

#### 建议范围

同步以下内容中至少必要部分：

- CLI help
- `README.md`
- `README.zh-CN.md`
- `docs/active_context.md`

#### 验收条件

- canonical reuse policy 被描述为显式规则，而非自动全局记忆
- 命令名、policy 名、summary 名保持一致
- 文档不顺手扩写成更大平台设计

#### 推荐提交粒度

- `docs(readme): document canonical reuse policy workflow`

---

### P14-06 closeout

#### 目标

完成 Phase 14 的 stop/go judgment。

#### 建议范围

收口时更新：

- `docs/plans/phase14/closeout.md`
- `current_state.md`
- 必要时 `AGENTS.md`

#### 验收条件

- 当前 phase 的 stop / go 边界已写清楚
- 下一轮起点明确
- 当前 canonical reuse policy baseline 已能作为稳定 checkpoint 被恢复

#### 推荐提交粒度

- `docs(phase14): add closeout note`
