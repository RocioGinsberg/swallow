---
author: claude
phase: 35
slice: meta-optimizer
status: draft
depends_on: [docs/roadmap.md, docs/plans/phase34/closeout.md, docs/plans/phase35/context_brief.md]
---

> **TL;DR**: Phase 35 为事件日志引入结构化遥测字段，建立只读 Meta-Optimizer Agent 定期扫描任务历史产出优化提案，并收口 concerns_backlog 中 Phase 29 dialect 重复问题。Gemini Context Caching adapter、hybrid cloud 实际部署与自动提案采纳均延后。

# Phase 35 Kickoff — Event Telemetry + Meta-Optimizer + Dialect Consolidation

## 基本信息

- **Phase**: 35
- **Primary Track**: Evaluation / Policy
- **Secondary Track**: Execution Topology
- **Phase 名称**: Event Telemetry + Meta-Optimizer Advisor + Dialect Data Layer

---

## 前置依赖与现有基础

Phase 31-34 checkpoint：
- `Event` dataclass（`models.py:366`）：`task_id / event_type / message / created_at / payload` 五字段，JSONL append-only
- 事件类型覆盖完整生命周期：task.created → task.planned → executor.* → task.review_gate → validation/policy.* → task.completed/failed
- Phase 34 新增 `task.execution_fallback` 事件，payload 包含 previous/fallback route 上下文
- `harness.py` 发射 retrieval / executor / compatibility / execution_fit / knowledge_policy / validation / retry_policy / stop_policy / checkpoint_snapshot / artifacts.written
- `AGENT_TAXONOMY_DESIGN.md` §7.2 已定义 Meta-Optimizer 角色：specialist / read-only / workflow-optimization
- `SELF_EVOLUTION_AND_MEMORY.md` 已列出期望遥测字段：task_family / logical_model / physical_route / latency_ms / token_cost / degraded / error_code
- `DialectAdapter` 协议已有 4 个实现（plain_text / structured_markdown / claude_xml / codex_fim），concerns_backlog Phase 29 指出信息收集逻辑重复

---

## Phase 35 目标

### Goal 1: Event Telemetry Schema Extension

在现有 `Event.payload` 中标准化遥测字段，使后续分析有统一 schema 可依赖。

**具体产出**：
- 定义 `TelemetryFields` dataclass：`task_family`, `logical_model`, `physical_route`, `latency_ms`, `degraded`, `error_code`
- `executor.completed` / `executor.failed` 事件 payload 自动注入遥测字段
- `task.execution_fallback` 事件 payload 已有大部分字段，补齐 `latency_ms`
- **不引入** `token_cost`：当前无 provider API 计费数据来源，延后到 Provider Connector 阶段

### Goal 2: Meta-Optimizer Agent（只读提案者）

实现定期扫描任务事件日志、产出优化提案的只读 Agent。

**具体产出**：
- `src/swallow/meta_optimizer.py`：扫描指定 base_dir 下所有任务的 `events.jsonl`
- 聚合统计：按 route_name 统计成功率/失败率/fallback 触发率/平均 latency
- 故障指纹聚类：按 `failure_kind` + `error_code` 分组，识别高频失败模式
- 产出 `optimization_proposals.md` artifact：包含路由优化建议、高频故障模式、待关注 degradation 趋势
- CLI 入口：`swl meta-optimize [--base-dir DIR] [--last-n 100]`
- **约束**：纯只读，不修改任何 state/event/config；产出为 markdown artifact，人工审批后决定是否采纳

### Goal 3: Dialect Data Layer 抽取（消化 Phase 29 CONCERN）

消化 concerns_backlog Phase 29 S3 的 "StructuredMarkdownDialect.format_prompt() 与 build_executor_prompt() 信息收集逻辑重复" 问题。

**具体产出**：
- 抽取 `DialectDataCollector` 或等效公共函数，统一从 `TaskState + RetrievalItem[]` 收集通用数据（task metadata / route context / retrieval lines / constraints / acceptance criteria）
- 4 个 dialect adapter 改为从公共 data layer 获取数据，只做格式化
- `build_executor_prompt()` 中的重复收集逻辑改为调用公共 layer

---

## 非目标（明确排除）

| 排除项 | 理由 |
|--------|------|
| Gemini Context Caching adapter | 需真实 Google API 集成，超出当前 scope |
| token_cost 遥测 | 无 provider 计费数据来源，需 Provider Connector 层先行 |
| 自动提案采纳 | Meta-Optimizer 必须为只读+人工审批，per AGENT_TAXONOMY_DESIGN |
| hybrid cloud / remote worker 部署 | 探索性，延后到单独 phase |
| Meta-Optimizer 实时路由干预 | 反模式（Hidden Orchestrator），明确禁止 |
| `CodexFIMDialect` FIM 标记转义 | Phase 34 C1 concern 仍为低优先级，当前无外部用户输入路径 |

---

## Slice 拆解

### S1: Event Telemetry Schema Extension

**目标**: 标准化 executor 事件的遥测字段

**改动范围**:
- `src/swallow/models.py`：新增 `TelemetryFields` dataclass
- `src/swallow/harness.py`：executor.completed / executor.failed 事件注入遥测字段
- `src/swallow/orchestrator.py`：task.execution_fallback 事件补齐 latency_ms
- `tests/test_cli.py`：验证遥测字段出现在事件 payload 中

**验收标准**:
- executor.completed 事件 payload 包含 task_family / logical_model / physical_route / latency_ms / degraded
- executor.failed 事件 payload 包含上述字段 + error_code
- 既有 244+ tests 不 break

**风险**: 2/9（impact 1, reversibility 1, dependency 0）—— 纯 additive payload 扩展

### S2: Meta-Optimizer Agent

**目标**: 实现只读 Event Log 扫描与优化提案产出

**改动范围**:
- `src/swallow/meta_optimizer.py`（新文件）：事件扫描、聚合、提案生成
- `src/swallow/cli.py`：新增 `meta-optimize` 子命令
- `tests/test_meta_optimizer.py`（新文件）：提案产出验证

**验收标准**:
- `swl meta-optimize --base-dir <dir>` 读取所有任务 events.jsonl
- 产出 `optimization_proposals.md` 包含：route 成功率统计、高频故障指纹、degradation 趋势
- 不修改任何 state/event/artifact（只读验证）
- 空任务目录产出 "no data" 提案

**风险**: 4/9（impact 2, reversibility 1, dependency 1）—— 新模块+新 CLI 命令，但不影响既有流程

### S3: Dialect Data Layer

**目标**: 消化 Phase 29 CONCERN，抽取公共数据收集层

**改动范围**:
- `src/swallow/executor.py`：抽取公共数据收集逻辑
- `src/swallow/dialect_adapters/claude_xml.py`：改用公共 data layer
- `src/swallow/dialect_adapters/codex_fim.py`：改用公共 data layer
- `tests/test_dialect_adapters.py`：验证重构后行为不变

**验收标准**:
- `build_executor_prompt()` 和 4 个 dialect 的 `format_prompt()` 不再重复收集 task metadata / retrieval lines
- 既有 dialect 测试全部 pass，输出内容等价
- concerns_backlog Phase 29 S3 可标记 Resolved

**风险**: 5/9（impact 2, reversibility 2, dependency 1）—— 重构 4 个 dialect + prompt builder，回归面较广

---

## 依赖关系

```
S1 (Telemetry) ──→ S2 (Meta-Optimizer)  [S2 需要 S1 的标准字段来聚合]
S3 (Dialect Data Layer)                   [独立于 S1/S2，可并行]
```

推荐执行顺序：S1 → S2，S3 可在 S1 后或与 S2 并行。

---

## 风险总览

| 维度 | S1 | S2 | S3 | 总体 |
|------|----|----|----|----|
| Impact Scope | 1 | 2 | 2 | — |
| Reversibility | 1 | 1 | 2 | — |
| Dependency Complexity | 0 | 1 | 1 | — |
| **Slice Total** | **2/9** | **4/9** | **5/9** | **11/27** |

**Phase 总体风险**: 低（11/27），与 roadmap 评估一致。

**R1**: S3 重构回归 — 缓解：严格保持 format_prompt 输出等价性，增加 snapshot 断言
**R2**: Meta-Optimizer 扫描大量事件文件的性能 — 缓解：`--last-n` 参数限制扫描范围，默认 100
**R3**: 遥测字段 payload 膨胀 — 缓解：仅在 executor 级事件注入，不影响其他事件类型

---

## Concerns Backlog 消化计划

| Backlog 条目 | 本轮处置 |
|-------------|---------|
| Phase 29 S3: dialect 信息收集重复 | S3 直接消化 |
| Phase 34 S2: CodexFIMDialect 转义 | 不消化（低优先级，无外部输入路径） |
| Phase 32 S3: LibrarianExecutor state mutation | 不消化（不在本轮 scope） |
