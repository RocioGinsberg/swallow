# Phase 18 Kickoff

## 基本信息

- phase: `Phase 18`
- track: `Execution Topology`
- secondary_tracks:
  - `Core Loop`
  - `Workbench / UX`
- slice: `Remote Handoff Contract Baseline`
- status: `kickoff`
- recommended_branch: `feat/phase18-remote-handoff-contract`

---

## 启动背景

Phase 17 已完成 `Canonical Reuse Regression Control Baseline`。

当前系统已经具备：

- explicit route / topology / execution-site / dispatch / handoff records
- local-inline 与 local-detached 的最小 execution-site contract baseline
- operator-facing queue / control / inspect / review 入口
- recovery / retry / rerun 的 checkpoint truth

因此，系统已经能回答：

- 当前任务走的是哪条 route
- 当前执行站点与 transport baseline 是什么
- 当前 handoff 和 operator control 的最小语义是什么

但仍缺少一个明确回答：

> 当 route 声明自己是 remote-capable，或者 execution-site 不再停留在 local baseline 时，系统究竟应该如何显式记录 handoff contract、ownership truth 与 transport contract？

当前实现已经有 remote candidate 的概念，但还没有一个可恢复、可检查的 remote handoff contract baseline 去承接它。

---

## 当前问题

当前仓库里已经有：

- route / topology / execution-site / dispatch / handoff 的 record baseline
- local-inline 与 local-detached 的 contract baseline
- operator-facing control / inspect path

但还没有一个稳定的 remote handoff contract baseline 去回答：

- remote-capable route 和 actual remote handoff 之间的边界如何表达
- handoff contract 中哪些字段属于 transport truth、ownership truth、dispatch truth
- remote candidate state 如何进入 artifacts / reports，而不误导成“已经支持 remote execution”
- operator 如何检查当前任务是否到达了 remote handoff readiness

换句话说：

现有系统已经能记录本地执行拓扑，但还没有建立 remote candidate handoff 的显式 contract truth。

---

## 本轮目标

Phase 18 的目标是建立一个**显式、可检查、可恢复的 remote handoff contract baseline**。

本轮应实现：

1. remote handoff contract record baseline
2. transport / ownership / dispatch truth 的最小字段约定
3. operator-facing execution-site / handoff report 对齐
4. 文档与命名对齐，明确这是 remote candidate baseline，不是 remote executor 平台

本轮重点不是直接跑 remote executor，而是先把“系统何时到达 remote handoff boundary”做成显式结构。

---

## 本轮非目标

本轮不默认推进以下方向：

- real remote worker execution
- cross-machine transport implementation
- distributed job queue
- hosted remote orchestration platform
- remote sync / multi-tenant infrastructure
- automatic remote dispatch without operator-visible contract

---

## 设计边界

### 应保持稳定的部分

本轮不应破坏：

- 当前 local-inline / local-detached baseline
- 现有 route / topology / execution-site / dispatch / handoff record 语义
- 当前 checkpoint / retry / stop / review 路径
- local-first execution baseline

### 本轮新增能力应满足

- remote handoff boundary 必须显式落在 records / artifacts 中
- transport / ownership / dispatch 字段必须可检查，而不是靠模糊推断
- remote candidate baseline 不得伪装成真实 remote execution support
- 继续保持可恢复、可追踪、operator-visible 的路径

---

## 影响范围

本轮大概率会涉及：

- `src/swallow/orchestrator.py`
- `src/swallow/harness.py`
- `src/swallow/cli.py`
- `src/swallow/models.py`
- `tests/test_cli.py`
- `docs/active_context.md`
- `docs/plans/phase18/*`

---

## 完成条件

Phase 18 可以 closeout 的最低条件应包括：

1. remote handoff contract 有显式 record baseline
2. execution-site / handoff 至少有一条 operator-facing surface 能看见 remote candidate contract truth
3. transport / ownership / dispatch 字段约定已经清晰
4. 当前文档已明确 remote handoff contract baseline 不是 remote executor implementation
5. 不破坏已有 local execution baseline

---

## 下一步

本 kickoff 落地后，下一步应完成：

1. `docs/plans/phase18/breakdown.md`
2. 从 remote handoff contract schema / artifact baseline 开始实现
3. 再补 execution-site / handoff report 与 CLI 对齐
