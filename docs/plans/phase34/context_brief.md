---
author: gemini
phase: 34
slice: none_selected
status: draft
depends_on: [docs/roadmap.md, docs/active_context.md, docs/plans/phase33/closeout.md]
---

# Context Brief: Phase 34 — 认知模型路由与全局降级兜底网格

## TL;DR
本阶段旨在升级编排层的 **Strategy Router**（能力匹配选路）和网关层的 **Dialect Adapters**（方言翻译），并建立最简二元降级机制。注意：本轮的核心改动在编排层（第 2 层）和网关层的语义转换部分（第 6 层本地侧），不涉及 Provider Connector 层（new-api / TensorZero）的实际部署。

## 变更范围

### 核心模块
- `src/swallow/router.py`: 升级 `select_route` 逻辑，使其能够根据模型能力矩阵、任务类型和可用性进行更智能的路由决策，引入 `Strategy Router` 的核心概念。
- `src/swallow/executor.py`: 扩展 `DialectAdapter` 协议，实现具体的方言翻译器（例如 Claude XML、Gemini Context Caching、Codex FIM），确保模型调用能以最佳性能表现。
- `src/swallow/models.py`: 新增或扩展 `DialectSpec`、`FallbackPolicy` 等模型，定义方言规范和降级策略的数据结构。
- `src/swallow/orchestrator.py`: 更新 `decide_task_knowledge` 及相关调度逻辑，使其能利用新的路由与降级能力，并在模型故障时触发相应的降级或重试流程。
- `src/swallow/provider_router.py` (预期新增): 集中处理外部模型供应商的接口适配和请求分发，集成 `new-api` 和 `TensorZero` 的功能。

### 新增模块 (预期)
- `src/swallow/dialect_adapters/`: 包含不同模型方言适配器的子目录，例如 `claude_xml_adapter.py`, `gemini_context_caching_adapter.py`, `codex_fim_adapter.py`。

## 近期变更摘要 (Git History)
- `6c8ecea`: 优化 Agent 执行器协作文档，添加 UI 提案。
- `103adfe`: 同步 Phase 33 合并后的状态入口。
- `d3ac7af`: 合并 Phase 33：Subtask & Concurrency Orchestrator，引入多子任务并发编排。
- `7434b04`: 修复 Phase 33 中子任务额外工件的保存问题。
- `af3baff`: 引入子任务审查重试集成。
- `ffb8cc8`: 添加 `Subtask Orchestrator` 基线。
- `611b008`: 添加多卡片 `Planner` 基线。

## 关键上下文
- **Phase 33 的并发基础**: Phase 33 引入的 `Subtask Orchestrator` 提供了多子任务并行执行的能力，Phase 34 的智能路由和降级策略将在此基础上进一步优化模型资源分配和任务弹性。
- **Gateway 融合蓝图**: `docs/design/GATEWAY_PHILOSOPHY.md` 和 `PROVIDER_ROUTER_AND_NEGOTIATION.md` 已经为网关层提供了清晰的设计哲学和技术选型（`TensorZero` + `new-api` 双层架构），本阶段应严格遵循。
- **旧版路由的局限**: 当前 `router.py` 主要基于简单的 `route_name` 和 `executor_family` 进行选择，缺乏动态能力协商和细粒度降级策略。
- **Phase 32 的知识层**: 知识双层架构和 Librarian Agent (Phase 32) 确保了知识的质量，但 Phase 34 的路由需要考虑如何高效地将检索到的知识通过方言适配器传递给不同模型，以最大化其长上下文能力。

## 风险信号
- **方言翻译复杂度**: 实现不同模型的“原生方言”适配器可能引入较高的复杂度，尤其是在语义转换和保持通用性之间。
- **降级策略的验证**: 降级矩阵需要全面的测试覆盖，以确保在各种故障场景下都能平滑切换，避免意外的循环降级或任务挂起。
- **性能开销**: 路由决策和方言转换逻辑可能会引入额外的延迟。需确保 `Provider Connector` 层的性能优化（如 `TensorZero`）能够抵消这部分开销。
- **配置管理**: 随着模型数量和降级策略的增加，配置管理将变得复杂，需要设计清晰、可维护的配置模式。
