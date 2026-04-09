# Active Context

## 当前轮次

- active_track: `Retrieval / Memory`
- active_phase: `Phase 14`
- active_slice: `Canonical Reuse Policy Baseline`
- active_branch: `feat/phase14-canonical-reuse-policy`
- status: `planning`

---

## 当前目标

当前默认目标是建立显式 canonical reuse policy baseline，并把现有 canonical registry 接到受 policy 控制的 retrieval / reuse 可见性路径。

当前重点不是继续扩 canonical governance workflow 或自动全局记忆，而是补齐 canonical destination 之后的 reuse policy 边界。

---

## 当前要解决的问题

当前系统已经具备：

- staged knowledge 的显式 review / promote / reject gate
- canonical registry / index / inspect baseline
- canonical promotion write-through、dedupe、trace-based supersede

当前最缺少的是：

- canonical registry 到 retrieval reuse 的显式 policy 边界
- canonical records 的最小 eligibility / visibility 规则
- superseded canonical records 的默认 reuse 行为
- policy-aware canonical reuse inspect path

---

## 当前关键文档

本轮优先读取：

1. `AGENTS.md`
2. `docs/system_tracks.md`
3. `docs/plans/phase14/kickoff.md`
4. `docs/plans/phase14/breakdown.md`

需要恢复历史上下文时再读取：

- `current_state.md`
- `docs/plans/phase13/closeout.md`
- `docs/plans/phase13/kickoff.md`
- `docs/plans/phase13/breakdown.md`
- `docs/archive/*`
- 旧 `post-phase-*` 归档文档

---

## 当前推进

已完成：

- Phase 13 `Canonical Knowledge Registry Baseline` 已完成
- 下一轮 primary track 已选择为 `Retrieval / Memory`
- Phase 14 `Canonical Reuse Policy Baseline` kickoff / breakdown 已建立
- 当前已进入新一轮 planning 状态

## 下一步

下一步应优先完成：

1. 明确 canonical reuse policy 的最小 schema / summary 结构
2. 切出 `feat/phase14-canonical-reuse-policy`
3. 从 policy baseline 开始实现
