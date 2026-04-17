---
author: codex
phase: 38
slice: all
status: final
depends_on:
  - docs/plans/phase38/kickoff.md
  - docs/plans/phase37/closeout.md
---

## TL;DR
Phase 38 已完成实现与 slice 拆 commit，当前状态为 **review pending / PR sync ready**。本轮为执行遥测补齐了 `token_cost` 基线：S1 在 executor / fallback 事件中写入本地估算成本，S2 为 Meta-Optimizer 增加成本聚合与提案，S3 预留 `CostEstimator` protocol 与默认 `StaticCostEstimator`。当前全量回归基线为 `267 passed in 6.23s`。

# Phase 38 Closeout

## 结论

Phase 38 `Cost Telemetry Baseline` 已完成实现与验证，当前分支状态为 **review pending / PR sync ready**。

本轮围绕 kickoff 定义的 3 个 slice，交付了一个零外部依赖、基于本地估算的成本遥测基线：

- S1：`token_cost` 字段、本地 token/cost 估算与 executor/fallback telemetry 注入
- S2：Meta-Optimizer 成本维度聚合、摘要与提案生成
- S3：`CostEstimator` protocol 与默认 `StaticCostEstimator`，为后续 provider-side usage 接入预留替换点

当前尚未进入 Claude review，因此本轮 closeout 的语义是“实现完成，等待 review / PR 同步”，而不是 merge ready。

## 已完成范围

### Slice 1: `token_cost` 遥测字段 + 本地成本估算

- `src/swallow/models.py` 为 `TelemetryFields` 增加 `token_cost`，为 `ExecutorResult` 增加 `estimated_input_tokens` / `estimated_output_tokens`
- 新增 `src/swallow/cost_estimation.py`，提供 `estimate_tokens()`、静态 `MODEL_PRICING` 和 `estimate_cost()`
- `src/swallow/executor.py` 在 executor 顶层统一按 prompt / output 回填估算 token
- `src/swallow/harness.py` 和 `src/swallow/orchestrator.py` 现在会在 `executor.completed` / `executor.failed` / `task.execution_fallback` 中写入 `token_cost`
- `tests/test_cost_estimation.py`、`tests/test_binary_fallback.py`、`tests/test_cli.py` 已覆盖成本 telemetry 基线

对应 commit：

- `a10b1cd` `feat(telemetry): add estimated token cost telemetry baseline`

### Slice 2: Meta-Optimizer 成本维度升级

- `src/swallow/meta_optimizer.py` 为 route 聚合增加 `total_cost`、`average_cost()`、`task_families` 与成本样本
- `build_meta_optimizer_report()` 新增 `Cost Summary`
- 提案规则新增：
  - 高成本路由识别
  - 同一 `task_family` 下的跨路由成本对比
  - 基于扫描窗口的成本上升趋势提示
- `tests/test_meta_optimizer.py` 已覆盖成本聚合与三类成本提案

对应 commit：

- `0b5a2c7` `feat(meta-optimizer): add cost aggregation and proposals`

### Slice 3: Cost Estimation 可配置化预留

- `src/swallow/cost_estimation.py` 新增 `CostEstimator` protocol 和默认 `StaticCostEstimator`
- 保留 `estimate_cost()` 作为兼容包装，默认走 `StaticCostEstimator`
- `src/swallow/harness.py` 的 `run_execution()` 现在接受可注入 `cost_estimator=`
- `tests/test_cost_estimation.py` 已覆盖 protocol 检查、默认实现和 `run_execution(..., cost_estimator=...)` 注入路径

对应 commit：

- `c9d5003` `refactor(cost): add configurable cost estimator protocol`

## 与 kickoff 完成条件对照

### 已完成的目标

- `TelemetryFields.to_dict()` 已输出 `token_cost`
- `executor.completed` / `executor.failed` 事件 payload 已包含 `token_cost`
- `task.execution_fallback` 事件 payload 已包含 `token_cost`
- local / mock 路由的 `token_cost` 为 `0.0`
- `swl meta-optimize` 报告已包含 per-route `avg_cost` / `total_cost`
- 高成本路由、跨路由成本对比、成本趋势上升均可触发建议
- `CostEstimator` protocol 与 `StaticCostEstimator` 已存在
- harness 已支持 estimator 注入
- 全量测试通过

### 未继续扩张的内容

以下方向仍明确不在本 phase 范围内：

- new-api / TensorZero / Provider Connector 实际部署
- 真实 provider usage 数据解析
- 在线定价表更新或外部 billing 查询
- `tiktoken` 等精确 token 计数依赖
- Meta-Optimizer 自动采纳提案或改写 route policy
- Control Center 成本看板

## Stop / Go 判断

### Stop 判断

当前 phase 应停止继续扩张，理由如下：

- kickoff 定义的 S1 / S2 / S3 已全部完成，并已按 slice 独立提交
- 零外部依赖、本地估算、执行路径不变的三条边界均已满足
- 当前实现已经形成一个清晰的成本遥测 baseline
- 再继续扩张会自然滑向 provider connector 部署、真实 usage 接入或自动路由干预，超出本轮 scope

### Go 判断

下一步应按如下顺序推进：

1. Human push 当前分支
2. 用根目录 `pr.md` 同步 PR 描述
3. Claude 执行 review
4. 如有 review follow-up，在同一分支继续修正
5. Human 决定 merge

## 当前稳定边界

Phase 38 closeout 后，以下边界应视为当前实现候选的稳定 checkpoint：

- 成本数据仍是本地估算，不代表真实 provider billing
- token 计数仍是 `len(text) // 4` 近似，不做精确计量
- provider connector、真实 usage 与外部依赖仍明确延后
- Meta-Optimizer 仍是只读提案生成，不自动修改 route policy 或 task state
- `CostEstimator` 目前只提供替换点，不引入新 provider runtime

## 当前已知问题

- 静态定价表会随上游 provider 定价变化而陈旧，需要后续 phase 手工更新或配置化
- 当前成本趋势分析基于最近任务扫描顺序和启发式阈值，不代表严格统计基线
- `token_cost` 目前尚未进入 Web Control Center surface
- 真实 codex exec 在当前环境中仍可能因 outbound network / WebSocket 受限而失败，进而导致 cost telemetry 主要反映 fallback/local 路径

以上问题均不阻塞进入 review 阶段。

## 测试结果

最终验证结果：

```text
267 passed in 6.23s
```

补充说明：

- `tests/test_cost_estimation.py` 覆盖本地估算、protocol 与 harness 注入路径
- `tests/test_meta_optimizer.py` 覆盖成本聚合、成本摘要与提案规则
- `tests/test_binary_fallback.py` / `tests/test_cli.py` 覆盖事件 payload 中的 `token_cost`

## 规则文件同步检查

### 必查

- [x] `docs/plans/phase38/closeout.md`
- [x] `docs/plans/phase38/kickoff.md`
- [x] `docs/active_context.md`
- [x] `current_state.md`
- [x] `./pr.md`

### 条件更新

- [ ] `AGENTS.md`
- [ ] `README.md`
- [ ] `README.zh-CN.md`
- [ ] `docs/plans/phase38/review_comments.md`

说明：

- 当前还未进入 review，因此不存在 `review_comments.md`
- 本轮未改变长期协作规则与 README 级对外叙述，暂不更新 `AGENTS.md` / README

## Git / PR 建议

1. 使用当前根目录 `pr.md` 作为 PR 描述草案
2. Human push `feat/phase38-cost-telemetry`
3. PR 描述明确当前为 `review pending`
4. Claude review 后再进入 merge 决策

## 下一轮建议

如果 Phase 38 merge 完成，下一轮应优先考虑 provider connector / 真实 usage 接入或把成本 surface 暴露到 Control Center，但不应默认同时推进两者。
