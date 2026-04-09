# Active Context

## 当前轮次

- active_track: `Retrieval / Memory`
- active_phase: `Phase 13`
- active_slice: `Canonical Knowledge Registry Baseline`
- active_branch: `feat/phase13-canonical-knowledge-registry`
- status: `in_progress`

---

## 当前目标

当前默认目标是建立显式 canonical knowledge registry baseline，并把现有 canonical promotion 接到 task 外持久化路径。

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

## 当前推进

已完成：

- canonical record schema baseline 已落地
- canonical registry persistence 已落地：
  - `.swl/canonical_knowledge/registry.jsonl`
  - `.swl/canonical_knowledge/index.json`
- canonical promotion 已接入 registry write-through
- 新增 operator inspect 入口：
  - `swl task canonical-registry`
  - `swl task canonical-registry-json`
- 新增 canonical registry index 入口：
  - `swl task canonical-registry-index`
  - `swl task canonical-registry-index-json`
- task artifact 视图已包含 canonical registry 路径
- inspect / review 已纳入 canonical registry 摘要
- 相关 CLI 测试已补齐并通过

## 下一步

下一步应优先完成：

1. 视需要把 canonical registry 摘要进一步纳入 queue / control
2. 继续评估 canonical registry 是否需要更明确的去重 / replace 规则
3. 为 Phase 13 后续 closeout 预留 stop/go 边界
