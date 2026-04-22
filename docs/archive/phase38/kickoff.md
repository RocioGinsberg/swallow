---
author: claude
phase: 38
slice: cost-telemetry
status: final
depends_on: [docs/roadmap.md, docs/plans/phase37/closeout.md, docs/design/PROVIDER_ROUTER_AND_NEGOTIATION.md]
---

> **TL;DR**: Phase 38 为遥测补齐 `token_cost` 字段，实现本地成本估算（无外部依赖），并升级 Meta-Optimizer 产出成本维度提案。Provider Connector 实际部署（new-api / TensorZero）明确延后到独立 phase。

# Phase 38 Kickoff — Cost Telemetry + Meta-Optimizer 成本维度升级

## 基本信息

- **Phase**: 38
- **Primary Track**: Execution Topology
- **Secondary Track**: Evaluation / Policy
- **Phase 名称**: Cost Telemetry Baseline（对应 roadmap Phase 38a 分期）

---

## 前置依赖与现有基础

- Phase 35 已建立 `TelemetryFields` dataclass（6 字段：task_family / logical_model / physical_route / latency_ms / degraded / error_code）
- `harness.py` 在 executor 事件中注入 telemetry，`orchestrator.py` 在 fallback 事件中补齐 latency
- `meta_optimizer.py` 已实现 route health / failure fingerprint / degradation trend 聚合，但缺少成本维度
- `SELF_EVOLUTION_AND_MEMORY.md` §3.2 定义了 `token_cost: float` 字段
- `PROVIDER_ROUTER_AND_NEGOTIATION.md` §5 定义了 Provider Connector 双层架构，但本轮不部署
- 当前 executor 路径：`run_codex_executor()` 通过 subprocess 调用外部二进制，`run_local_executor()` 本地生成，均不返回 token 用量
- `ExecutorResult` 不携带 token 信息

---

## Phase 38 目标

1. 在 `TelemetryFields` 中补齐 `token_cost` 字段
2. 实现纯 Python 本地成本估算（基于 prompt/output 长度 + 静态模型定价表）
3. 升级 Meta-Optimizer 聚合和提案生成，加入成本维度

**核心约束**：
- **零外部依赖**：不引入 Docker / Go / HTTP client / 定价 API 调用
- **估算而非精确计量**：本轮使用 `len(text) / 4` 近似 token 数 + 静态定价表，为后续 Provider Connector 接入真实用量预留接口
- **不改变执行路径**：executor 仍走 subprocess / local，不接入 new-api

---

## 非目标（明确排除）

| 排除项 | 理由 |
|--------|------|
| new-api 部署 | 引入 Go 二进制 + Docker，延后到独立 Phase 38b |
| TensorZero 集成 | 需 Rust 运行时，延后 |
| 真实 provider usage 数据解析 | 需 Provider Connector 先行 |
| 动态定价表更新 / 在线查询 | 零外部依赖约束 |
| Meta-Optimizer 自动路由干预 | 只读提案，人工审批 |
| token 精确计数（tiktoken 等） | 引入新依赖；近似估算已足够 MVP |
| Control Center 成本面板 | Web UI 扩展延后 |

---

## Slice 拆解

### S1: token_cost 遥测字段 + 本地成本估算

**目标**: 在 executor 事件中注入 `token_cost` 估算值。

**改动范围**:
- `src/swallow/models.py`：`TelemetryFields` 新增 `token_cost: float = 0.0`；`ExecutorResult` 新增 `estimated_input_tokens: int = 0` + `estimated_output_tokens: int = 0`
- `src/swallow/cost_estimation.py`（新文件）：
  - `estimate_tokens(text: str) -> int` — `max(1, len(text) // 4)` 近似
  - `MODEL_PRICING: dict[str, tuple[float, float]]` — 静态定价表（input_price_per_mtok, output_price_per_mtok），覆盖 codex / claude / local / mock 等 model_hint
  - `estimate_cost(model_hint: str, input_tokens: int, output_tokens: int) -> float` — 查表计算
- `src/swallow/executor.py`：各 executor 函数在返回 `ExecutorResult` 时填充 `estimated_input_tokens` / `estimated_output_tokens`（基于 prompt 和 output 长度）
- `src/swallow/harness.py`：`build_telemetry_fields()` 调用点增加 `token_cost` 参数
- `src/swallow/orchestrator.py`：fallback / subtask 事件补齐 `token_cost`
- `tests/`：验证 telemetry 事件包含 `token_cost >= 0`

**静态定价表示例**:
```python
MODEL_PRICING = {
    "codex":   (0.0, 0.0),      # 本地 CLI，无 API 成本
    "claude":  (3.0, 15.0),     # Claude 3.5 Sonnet 近似 ($/MTok)
    "local":   (0.0, 0.0),      # 本地 summary
    "mock":    (0.0, 0.0),      # 测试
}
```

定价表为硬编码常量，后续 Provider Connector 接入后替换为真实用量。

**验收标准**:
- `executor.completed` / `executor.failed` 事件 payload 包含 `token_cost` 字段（float >= 0）
- `task.execution_fallback` 事件 payload 包含 `token_cost`
- 本地 / mock executor 的 `token_cost` 为 0.0
- `TelemetryFields.to_dict()` 输出包含 `token_cost`
- 既有 261+ tests pass + 新增估算逻辑测试

**风险**: 3/9（impact 1, reversibility 1, dependency 1）

---

### S2: Meta-Optimizer 成本维度升级

**目标**: Meta-Optimizer 聚合 token_cost，在提案中加入成本对比和趋势。

**改动范围**:
- `src/swallow/meta_optimizer.py`：
  - `RouteTelemetryStats` 新增 `total_cost: float` + `average_cost() -> float`
  - 事件扫描时提取 `token_cost` 并累加
  - 提案生成新增成本维度规则：
    - 高成本路由识别（average_cost 超过阈值）
    - 跨路由成本对比（同 task_family 不同 route 的 cost 差异）
    - 成本趋势检测（近期 vs 历史平均）
- `tests/test_meta_optimizer.py`：验证成本聚合和成本提案生成

**验收标准**:
- `swl meta-optimize` 输出包含成本统计（per-route average cost）
- 高成本路由触发建议（如 "Route X averaged $0.50/task, consider cheaper alternative"）
- 零成本路由（local/mock）不触发成本告警
- 空 token_cost 事件优雅处理（视为 0.0）

**风险**: 3/9（impact 1, reversibility 1, dependency 1）

---

### S3: Cost Estimation 可配置化预留

**目标**: 为后续 Provider Connector 接入预留清晰接口，但本轮不实现。

**改动范围**:
- `src/swallow/cost_estimation.py`：增加 `CostEstimator` protocol / 接口定义
  ```python
  class CostEstimator(Protocol):
      def estimate(self, model_hint: str, input_tokens: int, output_tokens: int) -> float: ...
  ```
- 默认实现 `StaticCostEstimator` 使用硬编码定价表
- `harness.py` 通过可注入的 estimator 调用（默认 `StaticCostEstimator`）

**验收标准**:
- `CostEstimator` protocol 定义清晰
- `StaticCostEstimator` 通过 protocol 检查
- 后续 Provider Connector 只需实现新的 `CostEstimator` 即可替换

**风险**: 2/9（impact 1, reversibility 1, dependency 0）

---

## 依赖关系

```
S1 (token_cost 字段 + 估算) ──→ S2 (Meta-Optimizer 升级)
S3 (接口预留)                    [独立，可与 S1 并行]
```

推荐顺序：S1 → S2，S3 可在 S1 后或与 S2 并行。

---

## 风险总览

| 维度 | S1 | S2 | S3 | 总体 |
|------|----|----|----|----|
| Impact Scope | 1 | 1 | 1 | — |
| Reversibility | 1 | 1 | 1 | — |
| Dependency Complexity | 1 | 1 | 0 | — |
| **Slice Total** | **3/9** | **3/9** | **2/9** | **8/27** |

**Phase 总体风险**: 低（8/27）

**R1**: 成本估算不准确 — 缓解：本轮明确标注为"估算"，提案中注明 "estimated, not actual provider billing"；后续 Provider Connector 替换为真实数据
**R2**: 定价表过时 — 缓解：硬编码常量，更新只需改一行；后续可扩展为配置文件
**R3**: token 估算偏差 — 缓解：`len/4` 是业界通用近似，偏差 ±20% 对趋势分析足够

---

## 与 roadmap Phase 38b 的关系

本轮（Phase 38 = roadmap 38a）完成后，如需引入真实 Provider Connector：

| 维度 | Phase 38 (本轮) | Phase 38b (后续) |
|------|----------------|-----------------|
| 成本数据源 | 硬编码定价 × 估算 token 数 | Provider 返回的真实 usage |
| 外部依赖 | 零 | new-api (Go binary) |
| 执行路径 | subprocess / local | HTTP → new-api → upstream |
| Meta-Optimizer 输入 | 估算 token_cost | 真实 token_cost |
| CostEstimator | StaticCostEstimator | ProviderCostEstimator（新增） |

Phase 38b 不在当前 kickoff scope 内，需独立 kickoff。
