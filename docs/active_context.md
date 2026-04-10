# Active Context

## 当前轮次

- latest_completed_track: `Evaluation / Policy`
- latest_completed_phase: `Phase 15`
- latest_completed_slice: `Canonical Reuse Evaluation Baseline`
- active_track: `Evaluation / Policy`
- active_phase: `Phase 16`
- active_slice: `Canonical Reuse Regression Baseline`
- active_branch: `feat/phase16-canonical-reuse-regression`
- status: `kickoff`

---

## 当前目标

当前默认目标是在不扩张 Phase 15 边界的前提下，为 canonical reuse evaluation 建立最小 regression baseline。

Phase 15 已完成的收口结果仍以 `docs/plans/phase15/closeout.md` 为准；Phase 16 以 fresh kickoff 重新定义边界。

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

当前待解决的问题是：

- 如何把 task-local canonical reuse judgments 组织成可复查、可比较的 regression truth
- 如何让 operator 在不依赖手工比对 JSON 的情况下看出当前 baseline 是否退化
- 如何保持 evaluation baseline 显式、轻量，而不把它扩张成自动 policy optimizer

---

## 当前关键文档

当前优先读取：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/system_tracks.md`
4. `current_state.md`
5. `docs/plans/phase15/closeout.md`
6. `docs/plans/phase16/kickoff.md`
7. `docs/plans/phase16/breakdown.md`

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
- Phase 16 `Canonical Reuse Regression Baseline` 已完成 kickoff / breakdown 规划

## 下一步

下一步应优先完成：

1. 切出 `feat/phase16-canonical-reuse-regression`
2. 先实现 regression baseline artifact / compare path 的最小骨架
3. 再补 CLI inspect / report 对齐与测试覆盖
