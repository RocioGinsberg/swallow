---
author: codex
phase: 42
slice: all
status: final
depends_on:
  - docs/plans/phase42/kickoff.md
  - docs/plans/phase42/risk_assessment.md
  - docs/concerns_backlog.md
---

## TL;DR
Phase 42 已完成实现、review 与 PR 收口准备，当前状态为 **merge ready / PR sync ready**。本轮围绕本地栈可观测性和 Meta-Optimizer 遥测准确性做了 3 个低风险 slice：S1 扩展 `swl doctor` 覆盖本地 Docker / pgvector / WireGuard / egress proxy 联检；S2 修复 fallback `token_cost` 漏算；S3 隔离带 `review_feedback` 的 debate retry 事件，避免其污染 route health / failure fingerprint，同时保留真实成本与延迟统计。Claude review 结论为 `0 BLOCK / 0 CONCERN / 1 NOTE / Merge ready`。当前全量回归基线为 `310 passed, 5 subtests passed in 6.65s`。

# Phase 42 Closeout

## 结论

Phase 42 `Local Stack + Cost Telemetry` 已完成实现、review 与验证，当前状态为 **merge ready / PR sync ready**。

本轮交付了三个明确结果：

- S1：`swl doctor` 从单一 Codex 预检扩展到本地栈联检
- S2：Meta-Optimizer 现在会将 fallback 事件里的 `token_cost` 回计到 `previous_route`
- S3：Meta-Optimizer 将 debate retry 事件从 route health 聚合中隔离，并新增 `debate_retry_count`

`pr.md` 已同步为本轮 PR 草稿，可直接作为 PR 描述更新依据。

## 已完成范围

### Slice 1: Local Stack Doctor

- `src/swallow/doctor.py` 新增 `LocalStackCheck` / `LocalStackDoctorResult` 以及 `diagnose_local_stack()`
- 检查范围覆盖：
  - Docker daemon
  - `new-api` 容器
  - `tensorzero` 容器（optional）
  - `postgres` 容器
  - `pgvector` 扩展
  - `http://localhost:3000/api/status`
  - WireGuard `10.8.0.1`
  - `10.8.0.1:8888` 出口代理
- `src/swallow/cli.py` 的 `swl doctor` 新增默认联检、`doctor stack` 与 `--skip-stack`
- `tests/test_doctor.py` 覆盖 local stack 检查与 optional TensorZero 分支
- `tests/test_cli.py` 覆盖 bare `doctor`、`doctor stack` 与 `--skip-stack`

对应 commit：

- `feat(doctor): add local stack health checks`

### Slice 2: Fallback Cost Telemetry

- `src/swallow/meta_optimizer.py` 在 `EVENT_TASK_EXECUTION_FALLBACK` 分支中，新增 `token_cost` 对 `previous_route.total_cost` 与 `cost_samples` 的回计
- `tests/test_meta_optimizer.py` 新增 fallback cost 专项测试，锁定 `previous_route` 的 `total_cost`、`cost_samples` 与 `average_cost`

对应 commit：

- `fix(meta-optimizer): count fallback token cost`

### Slice 3: Debate Retry Telemetry Isolation

- `src/swallow/meta_optimizer.py` 的 `RouteTelemetryStats` 新增 `debate_retry_count`
- 带 `review_feedback` 的 executor 事件现在：
  - 继续累加 `total_cost`
  - 继续累加 `total_latency_ms`
  - 继续保留在 `cost_samples`
  - 不再进入 `event_count`
  - 不再进入 `success_count` / `failure_count`
  - 不再进入 `degraded_count`
  - 不再生成 `failure_fingerprint`
- `build_meta_optimizer_report()` 的 Route Health 输出新增 `debate_retry=<n>`
- `tests/test_meta_optimizer.py` 新增 debate retry 隔离测试，验证 route health、failure fingerprint、cost/latency 统计与 report 输出

对应 commit：

- `fix(meta-optimizer): isolate debate retry telemetry`

## 与 kickoff 完成条件对照

### 已完成的目标

- `swl doctor` 已覆盖 Docker / 容器 / pgvector / WireGuard / proxy 联检
- 容器缺失、命令失败和 optional TensorZero 都会以 `fail` / `skip` 收口，而不是崩溃
- `--skip-stack` 已可用于 CI 或无本地栈环境
- fallback `token_cost` 已计入 route stats，Phase 38 C1 已消化
- debate retry executor 事件已从 route health 聚合隔离，Phase 40 C2 已消化
- report 已显式暴露 `debate_retry` 计数
- 全量 `pytest` 通过

### 未继续扩张的内容

以下方向仍明确不在本 phase 范围内：

- 不接入 TensorZero API 抓取真实账单
- 不修改 `CostEstimator` protocol 或静态价格模型
- 不扩展 Web 控制中心承载 doctor 输出
- 不引入新的 debate event type 或重做 orchestration 事件模型

## Backlog 同步

本轮直接消化了两条 Open concern，现已从 `Open` 移入 `Resolved`：

- Phase 38：fallback `token_cost` 未计入 Meta-Optimizer route stats
- Phase 40：debate retry telemetry 混入正常 route health 聚合

当前 `docs/concerns_backlog.md` 不再有 Open 项。

## Review Follow-up

- Claude review 已完成：`0 BLOCK / 0 CONCERN / 1 NOTE / Merge ready`
- N1：全量 `pytest` 已通过，自动测试环境正常，无额外代码 follow-up
- `pr.md` 已同步最新 review 结论，可直接用于 PR 描述更新

## Stop / Go 判断

### Stop 判断

当前 phase 应停止继续扩张，理由如下：

- kickoff 定义的 3 个 slice 已全部完成，并已按 slice 独立提交
- S1 已提供足够的本地拓扑预检能力
- S2 / S3 已把 Meta-Optimizer 的两处已知遥测盲区收口
- 再继续扩张会自然滑向真实账单接入、更多诊断面板或新的 telemetry 设计，不属于本轮范围

### Go 判断

下一步应按如下顺序推进：

1. Claude 对本轮实现做 review
2. Human 用 `pr.md` 更新 PR 描述
3. Human push 当前分支并决定 merge

## 当前稳定边界

Phase 42 closeout 后，以下边界应视为当前实现候选的稳定 checkpoint：

- `swl doctor` 的 local stack 检查仍是 CLI 级只读诊断，不写入 `.swl/`
- TensorZero 检查仍是 optional，不阻断整体本地栈诊断通过
- fallback 成本回计仍归属到 `previous_route`，而非 fallback route
- debate retry 只从 route health / failure fingerprint 计数中隔离，不从成本与延迟统计中剔除

## 当前已知问题

- `swl doctor` 仍依赖固定的本地拓扑常量（容器名、端口、WireGuard 地址、proxy 地址），尚未参数化
- `pgvector` 检查当前依赖 `docker exec postgres psql ...` 约定，若本地镜像/用户名差异较大需后续再做抽象
- Meta-Optimizer 的成本仍基于静态估算，不是账单真值
- debate retry 当前只在聚合层隔离，没有拆出单独 artifact/report section

以上问题均不阻塞当前进入 review 阶段。

## 测试结果

最终验证结果：

```text
310 passed, 5 subtests passed in 6.65s
```

补充说明：

- `tests/test_doctor.py` 覆盖本地栈检查与 optional 容器分支
- `tests/test_cli.py` 覆盖 `doctor` 默认联检、`doctor stack` 与 `--skip-stack`
- `tests/test_meta_optimizer.py` 覆盖 fallback cost 回计与 debate retry 隔离
- 全量回归已通过

## 规则文件同步检查

### 必查

- [x] `docs/plans/phase42/closeout.md`
- [x] `docs/plans/phase42/kickoff.md`
- [x] `docs/plans/phase42/risk_assessment.md`
- [x] `docs/active_context.md`
- [x] `docs/concerns_backlog.md`
- [x] `./pr.md`

### 条件更新

- [x] `docs/plans/phase42/review_comments.md`
- [ ] `AGENTS.md`
- [ ] `README.md`
- [ ] `README.zh-CN.md`

说明：

- Claude review 已完成，`review_comments.md` 已同步为 `final`
- 本轮未改变长期协作规则与对外 tag 级能力描述，暂不更新 `AGENTS.md` / README

## Git / PR 建议

1. 使用当前根目录 `pr.md` 作为 PR 描述草案
2. 当前 PR 描述应标记为 `0 BLOCK / 0 CONCERN / 1 NOTE / Merge ready`
3. Human 根据当前 review 结论决定 merge

## 下一轮建议

如果 Phase 42 merge 完成，下一轮应优先回到 roadmap，选择新的 phase 方向，而不是继续在本分支追加 doctor 参数化或成本模型扩张。
