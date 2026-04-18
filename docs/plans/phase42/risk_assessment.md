---
author: claude
phase: 42
slice: local-stack-cost
status: draft
depends_on:
  - docs/plans/phase42/kickoff.md
---

> **TL;DR** Phase 42 整体风险 9/27（低）。三个 slice 互不耦合，均为单模块修改/新增。无核心路径变更。

# Phase 42 Risk Assessment

## 风险矩阵

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 风险等级 |
|-------|---------|--------|-----------|------|---------|
| S1: Doctor 本地栈检查 | 1 — 新增函数 | 1 — 轻松回滚 | 1 — subprocess + HTTP | **3** | 低 |
| S2: Fallback 成本修正 | 1 — 单函数 | 1 — 轻松回滚 | 1 — 无外部依赖 | **3** | 低 |
| S3: Debate retry 隔离 | 1 — 单模块 | 1 — 轻松回滚 | 1 — 无外部依赖 | **3** | 低 |

**总分: 9/27** — 全部低风险。

## 各 Slice 风险详述

### S1: Doctor 本地栈检查

**风险极低**。纯新增代码，不修改现有执行路径。

- Docker / WireGuard 命令可能在 CI 环境中不可用 → `--skip-stack` 参数解决，测试使用 mock
- `http://localhost:3000/api/status` 端点可能因 new-api 版本不同而路径不同 → 使用宽松检查（任意 2xx 响应即可），或 catch ConnectionError 标记为 fail

### S2: Fallback 成本修正

**风险极低**。在 `meta_optimizer.py:177-185` 的 fallback 事件处理块中增加 3 行 token_cost 累加。

- 需确认 fallback 事件 payload 中确实有 `token_cost` 字段 → 检查 `orchestrator.py` 的 fallback 事件写入代码

### S3: Debate Retry 隔离

**风险极低**。在 `meta_optimizer.py:149-175` 的 executor 事件处理块中增加 `review_feedback` 字段检查。

- `RouteTelemetryStats` 新增 `debate_retry_count` 字段，不影响现有字段的序列化/消费
- `build_meta_optimizer_report()` 的 Route Health 输出需新增 `debate_retry` 显示

## Concern 消化对齐

| Concern | 来源 | 消化 Slice | 验证 |
|---------|------|-----------|------|
| fallback token_cost 未计入 route stats | Phase 38 C1 | S2 | 新增测试：fallback 事件 token_cost 出现在 previous_route 的 cost_samples |
| debate retry 混入 route health | Phase 40 C2 | S3 | 新增测试：带 review_feedback 的 executor 事件不计入 event_count |

## 整体判断

Phase 42 为本轮 roadmap 中风险最低的 phase。三个 slice 互不耦合，无核心路径变更，无需额外设计 gate。
