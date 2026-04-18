---
author: claude
phase: 42
slice: local-stack-cost
status: draft
depends_on:
  - docs/roadmap.md
  - docs/plans/phase41/closeout.md
  - docs/concerns_backlog.md
---

> **TL;DR** Phase 42 扩展 `swl doctor` 覆盖本地 Docker 容器栈 + WireGuard 出口隧道健康检查，并修正 Meta-Optimizer 的两个遥测盲区（fallback 成本遗漏 + debate retry 事件混入 route health）。3 个 slice，低风险。

# Phase 42 Kickoff: 本地栈健康检查与成本遥测修正

## Track

- **Primary Track**: Execution Topology
- **Secondary Track**: Evaluation / Policy

## 目标

适配课题组本地全栈拓扑（`docs/deploy.md`），补全运维可观测性和遥测准确性。

具体目标：

1. **S1**: 扩展 `swl doctor` 新增本地 Docker 容器（new-api / TensorZero / Postgres）、pgvector 扩展及 WireGuard 出口隧道的自动化健康检查
2. **S2**: 修正 Meta-Optimizer 的 fallback 成本遗漏（Phase 38 C1）— 将 `EVENT_TASK_EXECUTION_FALLBACK` 的 `token_cost` 累加到 fallback route 的 `total_cost` / `cost_samples`
3. **S3**: 修正 Meta-Optimizer 的 debate retry 事件混入（Phase 40 C2）— 在 route health 聚合中排除带 `review_feedback` 标记的 executor 事件，或以独立 `debate_retry_count` 字段隔离

## 非目标

- **不接入 TensorZero API 抓取真实 Token 账单**：本阶段仅修正现有遥测逻辑的盲区。真实成本数据源接入留待本地 Docker 栈实际部署并积累数据后再评估
- **不修改 CostEstimator protocol 或 StaticCostEstimator**：成本估算模型不变，仅修正遥测消费侧的统计逻辑
- **不扩展 Web 控制中心**：doctor 结果仅通过 CLI 输出

## 设计边界

### S1: swl doctor 容器栈健康检查

**当前现状**：`doctor.py` 仅检查 Codex 二进制是否可用。

**扩展方案**：新增 `diagnose_local_stack()` 函数，检查以下项目：

| 检查项 | 检查方式 | 通过条件 |
|--------|---------|---------|
| Docker daemon | `docker info` 命令 | exit code 0 |
| new-api 容器 | `docker ps --filter name=new-api` | 容器状态 running |
| TensorZero 容器 | `docker ps --filter name=tensorzero` | 容器状态 running（可选，标记为 optional） |
| Postgres 容器 | `docker ps --filter name=postgres` | 容器状态 running |
| new-api 端口可达 | HTTP GET `http://localhost:3000/api/status` | 200 响应 |
| WireGuard 隧道 | `ping -c 1 -W 2 10.8.0.1` | exit code 0 |
| 出口代理 | `curl -x http://10.8.0.1:8888 -s https://ifconfig.me` | 返回 VPS IP（或任何 200 响应） |

**输出格式**：与现有 `format_codex_doctor_result` 对齐，逐项 `check_name=pass/fail/skip`。

**CLI 集成**：现有 `swl doctor` 命令输出 Codex 检查结果后，追加 local stack 检查结果。新增 `--skip-stack` 参数跳过容器栈检查（CI 环境用）。

### S2: Fallback 成本修正

**当前问题**（Phase 38 C1）：

`meta_optimizer.py:177-185` 处理 `EVENT_TASK_EXECUTION_FALLBACK` 时只增加了 `fallback_trigger_count`，没有将 fallback 事件中的 `token_cost` 累加到 route stats。

**修复方案**：

在 fallback 事件处理块中，读取 `payload.get("token_cost", 0.0)` 并累加到 `previous_route` 的 `total_cost` / `cost_samples`。这样 fallback 的成本不会被遗漏，且正确归属到触发 fallback 的原始 route。

### S3: Debate Retry 事件隔离

**当前问题**（Phase 40 C2）：

debate 轮次的 retry 执行事件以 `executor.completed` / `executor.failed` 记录，Meta-Optimizer 无法区分正常执行和 debate retry，导致：
- route 的 `event_count` 被 retry 膨胀
- `success_rate` / `failure_rate` 因 retry 事件被稀释/抬高

**修复方案**：

在 `build_meta_optimizer_snapshot()` 的事件扫描中，检查 executor 事件 payload 的 `review_feedback` 字段：
- 如果 `review_feedback` 非空，说明这是一次 debate retry 执行
- 将此类事件计入独立的 `debate_retry_count` 字段，不计入 `success_count` / `failure_count` / `event_count`
- 但仍累加 `total_cost` 和 `total_latency_ms`（retry 的成本和延迟是真实发生的）

`RouteTelemetryStats` 新增 `debate_retry_count: int = 0` 字段。

## Slice 拆解

### S1: swl doctor 本地栈健康检查

**目标**：扩展 `doctor.py`，新增 `diagnose_local_stack()` + CLI 输出。

**影响范围**：修改 `doctor.py`、`cli.py`

**风险评级**：
- 影响范围: 1 (新增独立检查函数)
- 可逆性: 1 (轻松回滚)
- 依赖复杂度: 1 (仅调用 subprocess + HTTP)
- **总分: 3** — 低风险

**验收条件**：
- `swl doctor` 输出包含 Docker / new-api / Postgres / WireGuard / 出口代理检查结果
- 容器不存在时显示 fail 而非崩溃
- `--skip-stack` 跳过容器栈检查
- 测试覆盖（mock subprocess + HTTP）

### S2: Fallback 成本修正

**目标**：在 `meta_optimizer.py` 的 fallback 事件处理中累加 `token_cost`。

**影响范围**：修改 `meta_optimizer.py`

**风险评级**：
- 影响范围: 1 (单函数修改)
- 可逆性: 1 (轻松回滚)
- 依赖复杂度: 1 (无外部依赖)
- **总分: 3** — 低风险

**验收条件**：
- fallback 事件的 `token_cost` 被累加到 previous_route 的 `total_cost` / `cost_samples`
- 现有 meta_optimizer 测试通过
- 新增测试验证 fallback 成本累加

### S3: Debate Retry 事件隔离

**目标**：在 `meta_optimizer.py` 的事件扫描中隔离 debate retry 事件。

**影响范围**：修改 `meta_optimizer.py`（`RouteTelemetryStats` + `build_meta_optimizer_snapshot`）

**风险评级**：
- 影响范围: 1 (单模块修改)
- 可逆性: 1 (轻松回滚)
- 依赖复杂度: 1 (无外部依赖)
- **总分: 3** — 低风险

**验收条件**：
- 带 `review_feedback` 的 executor 事件不计入 `success_count` / `failure_count` / `event_count`
- 仍累加 `total_cost` 和 `total_latency_ms`
- `RouteTelemetryStats.debate_retry_count` 正确递增
- report 输出包含 `debate_retry` 计数
- 现有 meta_optimizer 测试通过

## Slice 依赖

```
S1 (Doctor) — 独立
S2 (Fallback 成本) — 独立
S3 (Debate retry 隔离) — 独立
```

三个 slice 互不依赖，可并行实现，但建议顺序推进。

## 风险总评

| Slice | 影响 | 可逆 | 依赖 | 总分 | 评级 |
|-------|------|------|------|------|------|
| S1 | 1 | 1 | 1 | 3 | 低 |
| S2 | 1 | 1 | 1 | 3 | 低 |
| S3 | 1 | 1 | 1 | 3 | 低 |
| **合计** | | | | **9/27** | **低** |

本 phase 风险极低。三个 slice 均为单模块修改/新增，互不耦合。

## 完成条件

1. `swl doctor` 输出覆盖 Docker 容器 + WireGuard + 出口代理健康检查
2. Meta-Optimizer fallback 成本累加到 route stats（Phase 38 C1 消化）
3. Meta-Optimizer debate retry 事件隔离（Phase 40 C2 消化）
4. Phase 38 C1 和 Phase 40 C2 在 `docs/concerns_backlog.md` 中标记为 Resolved
5. 全量 pytest 通过，无回归

## Branch Advice

- 当前分支: `main`
- 建议操作: 人工审批 kickoff 后，从 `main` 切出 `feat/phase42-local-stack-cost`
- 理由: 低风险新增 + 修正工作，feature branch 常规操作
- 建议 PR 范围: S1 + S2 + S3 合并为单 PR（三个 slice 互不耦合，总体量可控）
