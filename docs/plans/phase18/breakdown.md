# Phase 18 Breakdown

## 基本信息

- phase: `Phase 18`
- track: `Execution Topology`
- secondary_tracks:
  - `Core Loop`
  - `Workbench / UX`
- slice: `Remote Handoff Contract Baseline`
- branch: `feat/phase18-remote-handoff-contract`

---

## 总体目标

把当前已经具备 local execution-site baseline 的路径，从“能描述 local topology”推进到“能显式描述 remote candidate handoff contract”的 baseline。

本轮重点不是 remote execution implementation，而是建立显式 contract truth。

---

## Affected Areas

- `src/swallow/orchestrator.py`
- `src/swallow/harness.py`
- `src/swallow/cli.py`
- `src/swallow/models.py`
- `tests/test_cli.py`
- `docs/active_context.md`
- `docs/plans/phase18/*`

---

## 默认实现顺序

本轮建议按以下顺序推进：

1. remote handoff contract schema / record
2. execution-site / dispatch / handoff report alignment
3. control / inspect visibility
4. docs / help alignment
5. phase closeout

这样做的原因是：

- 先明确 contract record 长什么样
- 再把它接到已有 report 路径
- 最后再统一 operator-facing surface 与文档

---

## Slice 列表

### P18-01 remote handoff contract schema / record

#### 目标

定义 remote candidate handoff contract 的最小结构。

#### 建议范围

至少包含：

- contract_kind
- contract_status
- handoff_boundary
- ownership_required
- transport_kind
- dispatch_readiness
- operator_ack_required

#### 验收条件

- remote handoff 不再只是抽象概念
- contract 可持久化、可回看
- 不误导为 real remote execution support

#### 推荐提交粒度

- `feat(topology): add remote handoff contract record`

---

### P18-02 execution-site / dispatch / handoff report alignment

#### 目标

让 remote handoff contract 进入现有 execution-site / dispatch / handoff artifacts。

#### 建议范围

可优先考虑：

- execution-site report
- dispatch report
- handoff report

重点展示：

- remote candidate contract fields
- ownership / transport / dispatch truth
- operator-visible readiness

#### 验收条件

- operator 不打开原始 JSON 也能看见 remote handoff baseline
- 报告命名与 contract 字段保持一致
- 不改写当前 local baseline

#### 推荐提交粒度

- `feat(cli): surface remote handoff contract in reports`
- `test(cli): cover remote handoff contract reports`

---

### P18-03 control / inspect visibility

#### 目标

让 operator 在主要入口上看到 remote candidate handoff readiness。

#### 建议范围

可优先考虑：

- `swl task inspect`
- `swl task control`

重点展示：

- contract kind / status
- ownership requirement
- transport boundary
- recommended next operator action

#### 验收条件

- operator 能在主入口快速判断是否到达 remote handoff boundary
- guidance 与 handoff report 语义一致
- 不引入真实 remote dispatch 行为

#### 推荐提交粒度

- `feat(cli): expose remote handoff readiness in inspect and control`

---

### P18-04 docs / help alignment

#### 目标

让 remote handoff contract baseline 的 operator 语义在文档中可见。

#### 建议范围

同步以下内容中至少必要部分：

- CLI help
- `README.md`
- `README.zh-CN.md`
- `docs/active_context.md`

#### 验收条件

- remote handoff contract baseline 被描述为 contract truth，而非 remote executor platform
- 命令与 report 文案保持一致
- 文档不顺手扩写成 remote infrastructure roadmap

#### 推荐提交粒度

- `docs(readme): document remote handoff contract workflow`

---

### P18-05 closeout

#### 目标

完成 Phase 18 的 stop/go judgment。

#### 建议范围

收口时更新：

- `docs/plans/phase18/closeout.md`
- `current_state.md`
- 必要时 `AGENTS.md`

#### 验收条件

- 当前 phase 的 stop / go 边界已写清楚
- 下一轮起点明确
- 当前 remote handoff contract baseline 已能作为稳定 checkpoint 被恢复

#### 推荐提交粒度

- `docs(phase18): add closeout note`
