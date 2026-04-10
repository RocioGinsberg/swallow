# Phase 17 Kickoff

## 基本信息

- phase: `Phase 17`
- track: `Workbench / UX`
- secondary_tracks:
  - `Evaluation / Policy`
  - `Retrieval / Memory`
- slice: `Canonical Reuse Regression Control Baseline`
- status: `kickoff`
- recommended_branch: `feat/phase17-canonical-reuse-regression-control`

---

## 启动背景

Phase 16 已完成 `Canonical Reuse Regression Baseline`。

当前系统已经具备：

- task-local `canonical_reuse_regression.json` baseline artifact
- `canonical-reuse-regression` compare report
- regression snapshot 在 `inspect` / `review` 中的可见面
- delta / mismatch indicators

因此，系统已经能回答：

- 当前 canonical reuse regression baseline 和 current evaluation summary 是否一致
- 哪些字段发生了 drift 或 baseline stale

但仍缺少一个明确回答：

> 当 regression mismatch 真的出现时，operator 应该在系统的哪个主入口上第一时间看到它，并据此决定下一步？

Phase 16 建立了 comparison truth，但还没有把这层 truth 充分接到 operator-facing control surface。

---

## 当前问题

当前仓库里已经有：

- explicit regression baseline artifact
- compact regression compare command
- inspectable regression snapshot

但还没有一个稳定的 operator control baseline 去回答：

- queue 是否应该显式提示 regression mismatch
- control / inspect 是否应该给出 regression-aware next action
- mismatch 是否应该形成更直接的 operator attention signal

换句话说：

Phase 16 建立了 regression truth，但还没有建立 regression truth 的 action-oriented operator surface。

---

## 本轮目标

Phase 17 的目标是建立一个**显式、紧凑、面向 operator 的 canonical reuse regression control baseline**。

本轮应实现：

1. regression mismatch summary 的 control / queue surface
2. regression-aware operator guidance baseline
3. inspect / review / control 命名与输出对齐
4. 文档与 phase 边界对齐，明确这不是自动 policy gate

本轮重点不是自动阻断任务，而是先把“哪里需要 operator 注意 regression mismatch”做成系统内清晰入口。

---

## 本轮非目标

本轮不默认推进以下方向：

- automatic policy mutation from regression mismatch
- mandatory stop / retry gate on every mismatch
- generalized queue overhaul unrelated to regression control
- broader retrieval regression for all source types
- canonical freshness / invalidation workflow
- remote sync or cross-task aggregation platform

---

## 设计边界

### 应保持稳定的部分

本轮不应破坏：

- Phase 15 的 evaluation record / summary baseline
- Phase 16 的 regression baseline artifact / compare semantics
- 现有 task-local artifact 与恢复路径
- queue / control / inspect / review 的既有最小语义

### 本轮新增能力应满足

- regression mismatch attention 必须显式、可检查
- operator guidance 应基于已有 compare truth，而不是重造评分体系
- 不把 mismatch signal 误做成自动 policy gate
- 继续保持 local-first、task-local、可恢复路径

---

## 影响范围

本轮大概率会涉及：

- `src/swallow/cli.py`
- `src/swallow/canonical_reuse_eval.py`
- `tests/test_cli.py`
- `docs/active_context.md`
- `docs/plans/phase17/*`

---

## 完成条件

Phase 17 可以 closeout 的最低条件应包括：

1. 至少一个 operator-facing control surface 能直接显示 regression mismatch attention
2. queue / control / inspect / review 中至少一条路径给出 regression-aware guidance
3. mismatch attention 复用 Phase 16 compare semantics，而不是另起新的评分规则
4. 当前文档已明确 regression control baseline 不是自动 policy gate
5. 不破坏已有 evaluation / regression artifact 语义

---

## 下一步

本 kickoff 落地后，下一步应完成：

1. `docs/plans/phase17/breakdown.md`
2. 切出 `feat/phase17-canonical-reuse-regression-control`
3. 从 queue / control 的 regression mismatch surface 开始实现
