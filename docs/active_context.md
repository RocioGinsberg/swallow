# Active Context

## 当前轮次

- active_track: `Retrieval / Memory`
- active_phase: `Phase 13`
- active_slice: `Canonical Knowledge Registry Baseline`
- active_branch: `feat/phase13-canonical-knowledge-registry`
- status: `planning`

---

## 当前目标

当前默认目标是把 Phase 12 已建立的 canonical promotion gate，推进到显式 canonical registry baseline。

当前重点不是继续扩 queue / control / review 宽度，而是补齐 canonical destination、inspect path 和 source traceability。

---

## 当前要解决的问题

当前系统已经具备：

- staged knowledge 的显式 review / promote / reject gate
- canonical promotion 的 task-local 状态变化
- decision record / inspect / queue / control 的 operator 路径

当前最缺少的是：

- task 外部 canonical registry
- canonical record schema
- canonical promotion 与 registry persistence 的明确对应关系
- canonical inspect / list 入口
- canonical record 的 source task / object / evidence traceability

---

## 当前关键文档

本轮优先读取：

1. `AGENTS.md`
2. `docs/system_tracks.md`
3. `docs/plans/phase13/kickoff.md`
4. `docs/plans/phase13/breakdown.md`

需要恢复历史上下文时再读取：

- `current_state.md`
- `docs/plans/phase12/closeout.md`
- `docs/archive/*`
- 旧 `post-phase-*` 归档文档

---

## 当前建议拆解

1. canonical record schema baseline
2. canonical registry persistence
3. canonical promotion write-through
4. canonical inspect / list path
5. docs / help alignment
6. phase closeout

## 下一步

下一步应优先完成：

1. `docs/plans/phase13/breakdown.md`
2. 确认 canonical registry 的最小存储位置
3. 从 canonical registry schema / persistence baseline 开始实现
