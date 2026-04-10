# Active Context

## 当前轮次

- latest_completed_track: `Evaluation / Policy`
- latest_completed_phase: `Phase 15`
- latest_completed_slice: `Canonical Reuse Evaluation Baseline`
- active_track: `to_be_selected`
- active_phase: `none_selected`
- active_slice: `fresh_kickoff_required`
- active_branch: `main`
- status: `phase15_closed`

---

## 当前目标

当前默认目标不是继续扩张已完成的 Phase 15，而是把它视为稳定 checkpoint，并在下一轮实现前重新选择新的 active track / phase / slice。

Phase 15 已完成的收口结果以 `docs/plans/phase15/closeout.md` 为准。

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

当前待解决的不是补做 Phase 15 基线，而是为下一轮工作重新确定：

- primary track
- fresh kickoff 边界
- 对应的 feature branch

---

## 当前关键文档

当前优先读取：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `current_state.md`
4. `docs/system_tracks.md`
5. `docs/plans/phase15/closeout.md`

需要恢复历史上下文时再读取：

- `docs/plans/phase15/kickoff.md`
- `docs/plans/phase15/breakdown.md`
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
- Phase 15 `Canonical Reuse Evaluation Baseline` kickoff / breakdown 已建立
- canonical reuse evaluation record / summary / report baseline 已实现
- CLI 已新增 `canonical-reuse-evaluate`、`canonical-reuse-eval`、`canonical-reuse-eval-json`
- `inspect` / `review` 已接入 canonical reuse evaluation 摘要
- evaluation record 已解析 canonical citation，并在存在 `retrieval.json` 时附带 retrieval provenance
- `python3 -m unittest tests.test_cli` 已通过（115 tests）
- `docs/plans/phase15/closeout.md` 已完成
- 当前 `main` 已回到 Phase 15 收口后的稳定状态

## 下一步

下一步应优先完成：

1. 基于 `docs/system_tracks.md` 选择下一轮 primary track
2. 为新一轮 phase 编写 fresh kickoff，明确目标、非目标与验收边界
3. 按新 slice 切出对应的 `feat/<phase-or-slice>` 分支
