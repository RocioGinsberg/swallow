---
author: claude
phase: 50
slice: design
status: draft
depends_on: ["docs/plans/phase50/kickoff.md", "docs/plans/phase50/context_brief.md"]
---

TL;DR: 三个 slice 的核心设计决策：S1 引入 OptimizationProposal dataclass 替换文本输出；S2 在 orchestrator 层插入 fire-and-forget 审计触发，verdict 从 LLM 输出正则解析；S3 在 RouteSpec 加 quality_weight 字段，持久化到独立 JSON 文件，CLI apply 是唯一写入路径。

# Phase 50 Design Decision

## 方案总述

Phase 50 的核心设计是**在三个已有模块之间建立单向数据流**，而不是重写任何模块：

```
EventLog → MetaOptimizer → OptimizationProposal (结构化)
                                    ↓
                         operator CLI apply
                                    ↓
                         RouteRegistry (quality_weight)
                                    ↓
                         candidate_routes() 排序

TaskExecution → AuditTriggerPolicy → ConsistencyAudit (fire-and-forget)
                                              ↓
                                     verdict → (可选) 权重建议
```

所有写入路径都经过 operator 确认，没有自动变更生产路由的路径。

---

## S1: Meta-Optimizer 结构化提案

### 设计决策

**新增 `OptimizationProposal` dataclass**（在 `models.py`）：

```python
@dataclass
class OptimizationProposal:
    proposal_type: str          # "route" | "workflow" | "route_weight"
    severity: str               # "info" | "warn" | "critical"
    route_name: str | None      # 针对特定 route 的提案
    description: str            # 人类可读描述
    suggested_action: str       # 建议操作
    suggested_weight: float | None  # 仅 route_weight 类型使用
```

**`build_optimization_proposals()` 返回 `list[OptimizationProposal]`**，原有启发式规则保留，输出格式改为结构化。

**新增 workflow 类提案触发条件**：
- debate retry 率 ≥ 30%（同一 task_family）→ `proposal_type=workflow`, severity=warn
- 单 task_family 成本离群（≥ 2x 中位数）→ `proposal_type=workflow`, severity=warn

**`build_meta_optimizer_report()` 从 `list[OptimizationProposal]` 渲染**，markdown 格式不变，向后兼容。

### 影响范围

- `models.py`：新增 `OptimizationProposal`
- `meta_optimizer.py`：`build_optimization_proposals()` 返回类型变更，新增 workflow 提案逻辑
- `tests/test_meta_optimizer.py`：更新断言，新增 workflow 提案测试

### 非目标

- 不改变 artifact 文件格式（仍写 markdown）
- 不改变 CLI `swl meta-optimizer` 的输出格式

---

## S2: 一致性审计自动触发

### 设计决策

**`AuditTriggerPolicy` dataclass**（在 `models.py`）：

```python
@dataclass
class AuditTriggerPolicy:
    enabled: bool = False
    trigger_on_degraded: bool = True      # executor 标记 degraded=True 时触发
    trigger_on_cost_above: float | None = None  # token_cost 超过阈值时触发
    auditor_route: str = "http-claude"    # 审计使用的 route
```

**触发点**：在 `AsyncSubtaskOrchestrator` 或 `run_task_async()` 完成后，检查最后一个 executor 事件的 payload，满足 policy 条件则 `asyncio.create_task()` 触发审计（fire-and-forget，不 await）。

**verdict 解析**：`run_consistency_audit()` 在 LLM 输出中查找关键词：
- 包含 "PASS" / "consistent" / "no issues" → `verdict = "pass"`
- 包含 "FAIL" / "inconsistent" / "critical" → `verdict = "fail"`
- 其他 → `verdict = "inconclusive"`

`ConsistencyAuditResult` 新增 `verdict: str` 字段。

**持久化**：policy 存储在 `.swl/audit_policy.json`，`swl audit policy show/set` 读写此文件。

### 触发点选择理由

选择在 orchestrator 层（而非 harness 层）插入触发点，原因：
- orchestrator 已有完整的任务完成事件，可直接读取 executor payload
- harness 层更底层，插入触发会增加 harness 的职责边界
- fire-and-forget 在 async 上下文中天然安全

### 影响范围

- `models.py`：新增 `AuditTriggerPolicy`，`ConsistencyAuditResult` 加 `verdict` 字段
- `consistency_audit.py`：新增 verdict 解析逻辑
- `orchestrator.py` 或 `harness.py`：插入触发检查（≤10 行）
- `cli.py`：新增 `swl audit policy show/set` 子命令
- `tests/test_consistency_audit.py`：新增 verdict 解析、policy 触发测试

### 非目标

- 不阻塞主任务路径（fire-and-forget）
- 不将 verdict 写入任务 state（只写 artifact）
- 不做批量审计

---

## S3: 路由质量权重

### 设计决策

**`RouteSpec` 新增字段**（在 `models.py`）：

```python
quality_weight: float = 1.0  # 1.0=正常, <1.0=降权, 0.0=禁用
```

**`candidate_routes()` 排序**：当返回多个候选时，按 `quality_weight` 降序排序（高权重优先）。单候选时不变。

**持久化**：权重存储在 `.swl/route_weights.json`：
```json
{"http-claude": 0.8, "http-qwen": 1.0}
```
`RouteRegistry` 在初始化时加载此文件，覆盖 `RouteSpec` 的默认值。

**CLI**：
- `swl route weights show` — 显示所有 route 的当前权重
- `swl route weights apply <proposal-file>` — 从 Meta-Optimizer 提案文件中提取 `route_weight` 类提案并应用

**Meta-Optimizer 权重提案**：当 route 失败率 ≥ 25% 时，除原有文本建议外，额外产出 `proposal_type=route_weight` 提案，`suggested_weight = max(0.1, 1.0 - failure_rate)`。

### 持久化位置选择理由

选择独立 `.swl/route_weights.json` 而非写入 `swallow.db`：
- 避免修改 SQLite 主 schema（kickoff 非目标）
- 权重是 operator 配置，语义上更接近配置文件而非事件日志
- 便于 git 追踪（可选择 commit 权重变更）

### 影响范围

- `models.py`：`RouteSpec` 加 `quality_weight` 字段
- `router.py`：`RouteRegistry` 加载权重文件，`candidate_routes()` 加排序
- `meta_optimizer.py`：新增 `route_weight` 类提案生成
- `cli.py`：新增 `swl route weights show/apply` 子命令
- `tests/test_router.py`：新增权重排序、持久化测试

### 非目标

- 不做概率采样（权重只影响排序，不做随机选择）
- 不做自动权重衰减
- 不修改 fallback chain 逻辑

---

## 依赖说明

- S3 依赖 S1：`route_weight` 提案需要 `OptimizationProposal` 结构
- S2 独立：可与 S3 并行，但 S2 的 verdict 字段为 S3 未来扩展预留接口
- S1 无依赖，先做

## 明确的非目标

- 不做自动路由切换
- 不做 Web UI 扩展
- 不改 SQLite 主 schema
- 不做跨任务并发审计
- 不引入新的 LLM 调用（verdict 解析用正则，不用 LLM）

## 验收条件

| Slice | 验收条件 |
|-------|---------|
| S1 | `OptimizationProposal` dataclass 存在；workflow 提案覆盖；原有 eval 通过 |
| S2 | `AuditTriggerPolicy` 可配置；harness/orchestrator 集成；verdict 字段解析正确；CLI 入口可用 |
| S3 | `quality_weight` 字段存在；候选排序正确；CLI apply/show 可用；权重持久化与加载正确 |
| 全量 | `pytest` 全量通过（395+ tests）；新增测试覆盖三个 slice 的核心路径 |
