---
author: claude
phase: 42
slice: local-stack-cost
status: final
depends_on:
  - docs/plans/phase42/kickoff.md
  - docs/plans/phase42/risk_assessment.md
---

> **TL;DR** Phase 42 review: 0 BLOCK / 0 CONCERN / 1 NOTE。Merge ready。三个 slice 全部低风险完成：doctor 容器栈 8 项检查 + fallback 成本修正 + debate retry 隔离。310 tests passed。Open concern 清零。

# Phase 42 Review Comments

## Review Scope

- 对照 `docs/plans/phase42/kickoff.md` 的方案拆解
- 对照 `docs/design/*.md` 架构原则一致性
- 测试覆盖充分性
- Phase scope 守界检查

## Checklist

### S1: swl doctor 本地栈健康检查

- [PASS] `diagnose_local_stack()` 实现 8 项检查：docker_daemon / new_api_container / tensorzero_container / postgres_container / pgvector_extension / new_api_http / wireguard_tunnel / egress_proxy
- [PASS] TensorZero 标记为 optional — 容器不存在时 status=skip 不影响整体 exit code
- [PASS] pgvector 检查依赖 postgres 容器状态，容器不 running 时自动 skip
- [PASS] HTTP 检查使用 stdlib `urllib.request.urlopen`，不引入 requests 等第三方依赖
- [PASS] `_run_command` / `_check_command_success` / `_check_container_running` / `_check_http_endpoint` 拆分合理，各自 timeout 可控
- [PASS] CLI 集成：`swl doctor` 默认输出 Codex + 容器栈检查；`swl doctor codex` / `swl doctor stack` 分别单独运行；`--skip-stack` 跳过容器栈
- [PASS] `doctor_command` 设为 `required=False`，裸 `swl doctor` 输出全部检查 — 用户友好
- [PASS] 测试覆盖：全通过 mock 场景 + TensorZero optional skip 场景（2 个测试）
- [PASS] CLI 测试：help 文本包含 doctor 相关命令

### S2: Fallback 成本修正

- [PASS] `meta_optimizer.py:190-192` 在 `EVENT_TASK_EXECUTION_FALLBACK` 处理块中新增 `token_cost` 累加到 `previous_route` 的 `total_cost` / `cost_samples`
- [PASS] 修改位置精准（3 行新增），不影响其他事件类型处理
- [PASS] 测试 `test_run_meta_optimizer_counts_fallback_token_cost_on_previous_route`：验证 fallback 事件的 0.25 token_cost 出现在 previous_route 的 cost_samples 和 total_cost 中
- [PASS] `average_cost()` 正确反映含 fallback 成本的均值

### S3: Debate Retry 事件隔离

- [PASS] executor 事件处理中新增 `review_feedback` 字段检查：非空时计入 `debate_retry_count`，跳过 `success_count` / `failure_count` / `event_count` / `degraded_count` 累加
- [PASS] 仍累加 `total_cost` / `total_latency_ms` / `cost_samples` — 符合 kickoff 设计（retry 的成本和延迟是真实发生的）
- [PASS] `cost_event_count()` 新增为 `event_count + debate_retry_count`，`average_latency_ms()` 和 `average_cost()` 改为基于 `cost_event_count()` 计算 — 正确：成本/延迟均值应包含 retry，但 success/failure rate 不应被 retry 稀释
- [PASS] report 输出包含 `debate_retry={count}` 字段
- [PASS] 测试 `test_run_meta_optimizer_isolates_debate_retry_from_route_health`：验证 1 次正常执行 + 1 次 debate retry 后，event_count=1 / success_count=1 / debate_retry_count=1 / failure_count=0，total_cost 含两次成本

### Concern 消化

- [PASS] Phase 38 C1（fallback 成本遗漏）已从 Open 移入 Resolved
- [PASS] Phase 40 C2（debate retry 混入 route health）已从 Open 移入 Resolved
- [PASS] `docs/concerns_backlog.md` Open 区现在为空

### 架构一致性

- [PASS] doctor 使用 subprocess 调用外部命令，不引入 Docker SDK 或第三方 HTTP 库
- [PASS] Meta-Optimizer 保持只读 — 不修改事件日志，仅改变聚合统计逻辑
- [PASS] 不修改 CostEstimator / StaticCostEstimator — 符合 kickoff 非目标

### Scope 守界

- [PASS] 不接入 TensorZero API 真实账单、不修改 CostEstimator、不扩展 Web 控制中心

## NOTE

### N1: 测试环境已就绪，自动测试已执行

全量 `pytest` 通过：310 passed, 5 subtests passed in 6.65s。无回归。

## 结论

**Merge ready**。三个 slice 全部低风险完成，实现精准、变更范围小。Phase 38 C1 和 Phase 40 C2 已消化，**Open concern 清零**。连续两个 phase（41 + 42）零 CONCERN review，内核稳定性显著提升。
