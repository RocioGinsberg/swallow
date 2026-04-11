# Phase 17 Breakdown

## 基本信息

- phase: `Phase 17`
- track: `Workbench / UX`
- secondary_tracks:
  - `Evaluation / Policy`
  - `Retrieval / Memory`
- slice: `Canonical Reuse Regression Control Baseline`
- branch: `feat/phase17-canonical-reuse-regression-control`

---

## 总体目标

把当前已经具备 canonical reuse regression baseline 的路径，从“可比较”推进到“operator 能在主入口快速看到并处理 mismatch”的 baseline。

本轮重点不是自动 policy gating，而是建立显式 control truth。

---

## Affected Areas

- `src/swallow/cli.py`
- `src/swallow/canonical_reuse_eval.py`
- `tests/test_cli.py`
- `docs/active_context.md`
- `docs/plans/phase17/*`

---

## 默认实现顺序

本轮建议按以下顺序推进：

1. regression mismatch attention summary
2. queue / control surface
3. inspect / review guidance alignment
4. docs / help alignment
5. phase closeout

这样做的原因是：

- 先明确 mismatch attention 长什么样
- 再把它接到真正的 operator 入口
- 最后统一文档和收口

---

## Slice 列表

### P17-01 regression mismatch attention summary

#### 目标

定义 canonical reuse regression mismatch 的最小 operator summary。

#### 建议范围

至少包含：

- comparison status
- mismatch count
- key mismatch labels
- recommended next operator action

#### 验收条件

- mismatch attention 不再只埋在独立 compare report 里
- summary 可被 queue / control / inspect 复用
- 不引入自动 gate 逻辑

#### 推荐提交粒度

- `feat(cli): add canonical reuse regression attention summary`

---

### P17-02 queue / control surface

#### 目标

让 operator 在 queue / control 上直接看到 regression mismatch attention。

#### 建议范围

可优先考虑：

- `swl task queue`
- `swl task control <task-id>`

重点展示：

- whether regression mismatch is present
- mismatch summary
- recommended command

#### 验收条件

- operator 不进入专门 compare 命令也能发现 mismatch
- 输出保持 compact
- 不改写既有 control 语义

#### 推荐提交粒度

- `feat(cli): surface regression mismatch in queue and control`
- `test(cli): cover regression mismatch control surfaces`

---

### P17-03 inspect / review guidance alignment

#### 目标

让 inspect / review 的 operator guidance 与 regression mismatch surface 对齐。

#### 建议范围

可优先考虑：

- 统一 recommended action
- review 路径上的 mismatch 提示
- inspect 路径上的 regression-aware guidance

#### 验收条件

- inspect / review / control 对 regression mismatch 的语义不冲突
- operator guidance 更直接
- 不引入新的抽象层

#### 推荐提交粒度

- `feat(cli): align regression guidance across inspect and review`

---

### P17-04 docs / help alignment

#### 目标

让 regression control baseline 的 operator 语义在文档中可见。

#### 建议范围

同步以下内容中至少必要部分：

- CLI help
- `README.md`
- `README.zh-CN.md`
- `docs/active_context.md`

#### 验收条件

- regression control baseline 被描述为 operator attention surface，而非自动 gate
- 命令与 guidance 文案保持一致
- 文档不顺手扩写成更大 queue platform 设计

#### 推荐提交粒度

- `docs(readme): document regression control workflow`

---

### P17-05 closeout

#### 目标

完成 Phase 17 的 stop/go judgment。

#### 建议范围

收口时更新：

- `docs/plans/phase17/closeout.md`
- `current_state.md`
- 必要时 `AGENTS.md`

#### 验收条件

- 当前 phase 的 stop / go 边界已写清楚
- 下一轮起点明确
- 当前 regression control baseline 已能作为稳定 checkpoint 被恢复

#### 推荐提交粒度

- `docs(phase17): add closeout note`
