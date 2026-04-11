# Phase 15 Breakdown

## 基本信息

- phase: `Phase 15`
- track: `Evaluation / Policy`
- secondary_tracks:
  - `Retrieval / Memory`
  - `Workbench / UX`
- slice: `Canonical Reuse Evaluation Baseline`
- branch: `feat/phase15-canonical-reuse-evaluation`

---

## 总体目标

把当前已经具备 canonical reuse policy 的路径，从“可用”推进到“可评价、可复查、可形成最小 regression truth”的 baseline。

本轮重点不是自动优化 policy，而是建立显式 evaluation truth。

---

## 默认实现顺序

本轮建议按以下顺序推进：

1. canonical reuse evaluation schema
2. evaluation summary / artifact
3. inspect / list path
4. retrieval provenance linkage tightening
5. docs / help alignment
6. phase closeout

这样做的原因是：

- 先明确 evaluation record 长什么样
- 再明确 summary 怎么表达
- 再补 operator-facing inspect
- 最后再收紧 provenance 和文档

---

## Slice 列表

### P15-01 canonical reuse evaluation schema

#### 目标

定义 canonical reuse evaluation record 的最小结构。

#### 建议范围

至少包含：

- task_id
- evaluated_at / evaluated_by
- canonical references under evaluation
- judgment
- note

#### 验收条件

- evaluation 不再只是临时观察
- judgment 可持久化、可回看
- 不引入过早复杂抽象

#### 推荐提交粒度

- `feat(policy): define canonical reuse evaluation schema`

---

### P15-02 evaluation summary / artifact

#### 目标

建立 canonical reuse evaluation 的最小 summary / artifact 结构。

#### 建议范围

可优先考虑：

- task-local evaluation record
- compact evaluation summary artifact
- optional global summary only if needed for inspect

#### 验收条件

- operator 可以看出当前 evaluation judgments 的最小分布
- useful / noisy / needs_review 等状态可见
- 不再只依赖 retrieval report 手工判断

#### 推荐提交粒度

- `feat(knowledge): add canonical reuse evaluation summary`
- `test(knowledge): cover canonical reuse evaluation summary`

---

### P15-03 inspect / list path

#### 目标

给 operator 提供一个紧凑 canonical reuse evaluation inspection path。

#### 建议范围

可优先考虑：

- `swl task canonical-reuse-eval`
- 或 task/workbench 范围内的等价 inspect 入口

重点展示：

- evaluation count
- judgment distribution
- latest evaluated canonical refs

#### 验收条件

- operator 不打开底层 JSON 也能看到 evaluation 摘要
- inspect path 不误导为自动策略学习
- provenance 对应关系可见

#### 推荐提交粒度

- `feat(cli): add canonical reuse evaluation inspect command`
- `test(cli): cover canonical reuse evaluation inspection`

---

### P15-04 retrieval provenance linkage tightening

#### 目标

让 evaluation judgment 与 retrieval provenance 的关系更稳定。

#### 建议范围

至少保证 evaluation 能引用：

- canonical_id
- citation
- source_ref / artifact_ref
- task / run context

#### 验收条件

- judgment 可追到具体 canonical hit
- provenance 表达不依赖模糊推断
- 不改写现有 retrieval 主循环语义

#### 推荐提交粒度

- `feat(retrieval): tighten canonical evaluation provenance`
- `test(retrieval): cover canonical evaluation provenance`

---

### P15-05 docs / help alignment

#### 目标

让 canonical reuse evaluation baseline 的 operator 语义在文档中可见。

#### 建议范围

同步以下内容中至少必要部分：

- CLI help
- `README.md`
- `README.zh-CN.md`
- `docs/active_context.md`

#### 验收条件

- canonical reuse evaluation 被描述为显式判断记录，而非自动 policy learning
- 命令名、artifact 名、summary 名保持一致
- 文档不顺手扩写成更大平台设计

#### 推荐提交粒度

- `docs(readme): document canonical reuse evaluation workflow`

---

### P15-06 closeout

#### 目标

完成 Phase 15 的 stop/go judgment。

#### 建议范围

收口时更新：

- `docs/plans/phase15/closeout.md`
- `current_state.md`
- 必要时 `AGENTS.md`

#### 验收条件

- 当前 phase 的 stop / go 边界已写清楚
- 下一轮起点明确
- 当前 evaluation baseline 已能作为稳定 checkpoint 被恢复

#### 推荐提交粒度

- `docs(phase15): add closeout note`
