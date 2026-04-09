# Active Context

## 当前轮次

- active_track: `Evaluation / Policy`
- active_phase: `Phase 15`
- active_slice: `Canonical Reuse Evaluation Baseline`
- active_branch: `feat/phase15-canonical-reuse-evaluation`
- status: `completed`

---

## 当前目标

当前默认目标已完成：仓库已经建立显式 canonical reuse evaluation baseline，并把已有 canonical reuse 路径接到最小 evaluation / judgment 结构。

当前默认不应继续无边界扩张当前 phase，而应把 Phase 15 视为已完成 checkpoint，并在继续前重新选择下一轮 kickoff。

---

## 当前要解决的问题

当前系统已经具备：

- staged knowledge 的显式 review / promote / reject gate
- canonical registry / index / inspect baseline
- canonical promotion write-through、dedupe、trace-based supersede
- canonical reuse policy / retrieval integration / traceability baseline

Phase 15 已经明确并落地：

- canonical reuse evaluation record schema 与 judgment vocabulary
- evaluation summary / judgment distribution 的最小表达
- canonical citation resolution 与 evaluation judgment 的显式对应关系
- retrieval context 已存在时的 provenance attachment
- operator-facing inspect / review / report path

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
- canonical reuse evaluation record / summary / report baseline 已实现
- CLI 已新增 `canonical-reuse-evaluate`、`canonical-reuse-eval`、`canonical-reuse-eval-json`
- `inspect` / `review` 已接入 canonical reuse evaluation 摘要
- evaluation record 已解析 canonical citation，并在存在 `retrieval.json` 时附带 retrieval provenance
- `python3 -m unittest tests.test_cli` 已通过（115 tests）
- `docs/plans/phase15/closeout.md` 已完成

## 下一步

下一步应优先完成：

1. 将当前 Phase 15 分支作为稳定成果整理提交
2. 判断是否将 `feat/phase15-canonical-reuse-evaluation` 合并回 `main`
3. 基于 `docs/system_tracks.md` 为下一轮 phase 做 fresh kickoff
