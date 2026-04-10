# Active Context

## 当前轮次

- latest_completed_track: `Evaluation / Policy`
- latest_completed_phase: `Phase 16`
- latest_completed_slice: `Canonical Reuse Regression Baseline`
- active_track: `Workbench / UX`
- active_phase: `Phase 17`
- active_slice: `Canonical Reuse Regression Control Baseline`
- active_branch: `feat/phase17-canonical-reuse-regression-control`
- status: `in_progress`

---

## 当前目标

当前默认目标是在不扩张 Phase 16 评分语义的前提下，把 canonical reuse regression mismatch 带到更清晰的 operator-facing control surface。

Phase 16 已完成的收口结果仍以 `docs/plans/phase16/closeout.md` 为准；Phase 17 以 fresh kickoff 重新定义边界。

---

## 当前要解决的问题

当前系统已经具备：

- staged knowledge 的显式 review / promote / reject gate
- canonical registry / index / inspect baseline
- canonical promotion write-through、dedupe、trace-based supersede
- canonical reuse policy / retrieval integration / traceability baseline

Phase 16 已经明确并落地：

- canonical reuse evaluation record schema 与 judgment vocabulary
- evaluation summary / judgment distribution 的最小表达
- canonical citation resolution 与 evaluation judgment 的显式对应关系
- retrieval context 已存在时的 provenance attachment
- operator-facing inspect / review / report path
- task-local `canonical_reuse_regression.json` baseline artifact
- baseline 与当前 evaluation summary 的 compare path
- regression snapshot 在 `inspect` / `review` 中的可见面

当前待解决的问题是：

- regression mismatch 出现时，operator 如何在 queue / control / review 中快速看到它
- 当前 compare 结果如何进入更直接的 action-oriented surface，而不是停留在单独命令
- 如何保持 mismatch handling 显式、轻量，而不把它扩张成自动 policy mutation

---

## 当前关键文档

当前优先读取：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/system_tracks.md`
4. `current_state.md`
5. `docs/plans/phase16/closeout.md`
6. `docs/plans/phase17/kickoff.md`
7. `docs/plans/phase17/breakdown.md`

需要恢复历史上下文时再读取：

- `docs/plans/phase17/kickoff.md`
- `docs/plans/phase17/breakdown.md`
- `docs/plans/phase16/kickoff.md`
- `docs/plans/phase16/breakdown.md`
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
- Phase 16 已落地 task-local `canonical_reuse_regression.json` baseline artifact
- `inspect` / `review` 已接入 canonical reuse regression snapshot
- CLI 已新增 `canonical-reuse-regression` compare report
- CLI 已新增 `canonical-reuse-regression-json`
- regression baseline / compare path 已有针对性 CLI 测试覆盖
- `README.md` / `README.zh-CN.md` 已同步 regression workflow operator 入口
- `docs/plans/phase16/closeout.md` 已完成
- Phase 17 `Canonical Reuse Regression Control Baseline` 已完成 kickoff / breakdown 规划
- Phase 17 已新增 regression mismatch attention summary
- `queue` / `control` 已接入 regression mismatch surface
- `inspect` / `review` 已接入 regression-aware guidance
- regression control baseline 已有针对性 CLI 测试覆盖

## 下一步

下一步应优先完成：

1. 视完成度决定是否同步 README 中的 regression control workflow
2. 判断是否需要为 regression attention 增加更明确的 next-action 文案
3. 若当前边界已足够，开始准备 Phase 17 closeout
