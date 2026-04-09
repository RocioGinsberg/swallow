# Active Context

## 当前轮次

- active_track: `Evaluation / Policy`
- active_phase: `Phase 15`
- active_slice: `Canonical Reuse Evaluation Baseline`
- active_branch: `feat/phase15-canonical-reuse-evaluation`
- status: `planning`

---

## 当前目标

当前默认目标是建立显式 canonical reuse evaluation baseline，并把已有 canonical reuse 路径接到最小 evaluation / judgment 结构。

当前重点不是继续扩 ranking 平台、自动策略学习或 freshness workflow，而是先建立 canonical reuse 的 evaluation truth。

---

## 当前要解决的问题

当前系统已经具备：

- staged knowledge 的显式 review / promote / reject gate
- canonical registry / index / inspect baseline
- canonical promotion write-through、dedupe、trace-based supersede
- canonical reuse policy / retrieval integration / traceability baseline

当前最需要明确的是：

- canonical reuse evaluation record schema
- evaluation summary / judgment distribution 的最小表达
- retrieval hit provenance 与 evaluation judgment 的显式对应关系
- operator 如何检查当前 canonical reuse evaluation baseline

---

## 当前关键文档

本轮优先读取：

1. `AGENTS.md`
2. `docs/system_tracks.md`
3. `docs/plans/phase15/kickoff.md`
4. `docs/plans/phase15/breakdown.md`

需要恢复历史上下文时再读取：

- `current_state.md`
- `docs/plans/phase14/closeout.md`
- `docs/plans/phase14/kickoff.md`
- `docs/plans/phase14/breakdown.md`
- `docs/plans/phase13/closeout.md`
- `docs/plans/phase13/kickoff.md`
- `docs/plans/phase13/breakdown.md`
- `docs/archive/*`
- 旧 `post-phase-*` 归档文档

---

## 当前推进

已完成：

- Phase 14 `Canonical Reuse Policy Baseline` 已完成
- 下一轮 primary track 已选择为 `Evaluation / Policy`
- Phase 15 `Canonical Reuse Evaluation Baseline` kickoff / breakdown 已建立
- 当前已进入新一轮 planning 状态

## 下一步

下一步应优先完成：

1. 明确 canonical reuse evaluation 的最小 schema / summary 结构
2. 切出 `feat/phase15-canonical-reuse-evaluation`
3. 从 evaluation baseline 开始实现
