# Phase 13 Breakdown

## 基本信息

- phase: `Phase 13`
- track: `Retrieval / Memory`
- secondary_tracks:
  - `Workbench / UX`
  - `Evaluation / Policy`
- slice: `Canonical Knowledge Registry Baseline`
- branch: `feat/phase13-canonical-knowledge-registry`

---

## 总体目标

把当前已经具备显式 promote / reject gate 的 canonical knowledge 路径，从 task-local 状态推进到显式 canonical registry baseline。

本轮重点不是自动化 canonical reuse，而是建立 canonical destination、inspect path 和 traceability。

---

## 默认实现顺序

本轮建议按以下顺序推进：

1. canonical record schema baseline
2. canonical registry persistence
3. canonical promotion write-through
4. canonical inspect / list path
5. docs / help alignment
6. phase closeout

这样做的原因是：

- 先明确 canonical record 长什么样
- 再明确 record 落在哪里
- 再把 promote 动作接到 registry
- 最后再补 operator-facing inspect 和文档

---

## Slice 列表

### P13-01 canonical record schema baseline

#### 目标

定义 canonical knowledge record 的最小结构。

#### 建议范围

至少包含：

- canonical_id
- source_task_id
- source_object_id
- promoted_at
- promoted_by / decision ref（如当前模型已有）
- text
- source_ref
- artifact_ref

#### 验收条件

- canonical record 不再只是 task-local object 的隐式延伸
- source traceability 字段清晰
- 不引入过早复杂抽象

#### 推荐提交粒度

- `feat(knowledge): define canonical registry record schema`

---

### P13-02 canonical registry persistence

#### 目标

建立 canonical knowledge 的 task 外部持久化 registry baseline。

#### 建议范围

可优先考虑：

- `.swl` 下单独 canonical registry 文件
- canonical index / list 所需的最小伴随结构

#### 验收条件

- canonical records 有独立持久化位置
- 不再只依赖 task-local knowledge_objects.json
- registry 可被后续 inspect 命令读取

#### 推荐提交粒度

- `feat(store): persist canonical knowledge registry`
- `test(store): cover canonical registry persistence`

---

### P13-03 canonical promotion write-through

#### 目标

把现有 canonical promotion 接到 registry 持久化路径。

#### 建议范围

当 operator 执行 canonical promotion 时：

- task knowledge object 进入 canonical stage
- registry 写入 canonical record
- decision trace 可追溯

#### 验收条件

- canonical promotion 产生 task 外部可检查结果
- promotion 与 registry record 不出现明显双写冲突
- reject / reuse 路径语义不被误改

#### 推荐提交粒度

- `feat(knowledge): write canonical registry on promotion`
- `test(knowledge): cover canonical promotion persistence`

---

### P13-04 canonical inspect / list path

#### 目标

给 operator 提供一个紧凑 canonical registry inspection path。

#### 建议范围

可优先考虑：

- `swl knowledge list`
- 或 task/workbench 范围内的等价 inspect 入口

重点展示：

- canonical_id
- source_task_id / source_object_id
- promoted_at
- source / artifact trace

#### 验收条件

- operator 可以不打开底层 JSON 就看到 canonical registry 概览
- inspect path 不误导为“自动全局记忆已开启”
- source traceability 保持可见

#### 推荐提交粒度

- `feat(cli): add canonical registry inspect command`
- `test(cli): cover canonical registry listing`

---

### P13-05 docs / help alignment

#### 目标

让 canonical registry baseline 的 operator 语义在文档中可见。

#### 建议范围

同步以下内容中至少必要部分：

- CLI help
- `README.md`
- `README.zh-CN.md`
- `docs/active_context.md`

#### 验收条件

- canonical registry 被描述为显式持久化结构，而非自动全局记忆
- 命令名、record 名、artifact 名保持一致
- 文档不顺手扩写成更大平台设计

#### 推荐提交粒度

- `docs(readme): document canonical registry workflow`

---

### P13-06 closeout

#### 目标

完成 Phase 13 的 stop/go judgment。

#### 建议范围

收口时更新：

- `docs/plans/phase13/closeout.md`
- `current_state.md`
- 必要时 `AGENTS.md`

#### 验收条件

- 当前 phase 的 stop / go 边界已写清楚
- 下一轮起点明确
- 当前 registry baseline 已能作为稳定 checkpoint 被恢复

#### 推荐提交粒度

- `docs(phase13): add closeout note`
