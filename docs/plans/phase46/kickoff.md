---
author: claude
phase: 46
slice: all
status: draft
depends_on:
  - docs/roadmap.md
  - docs/plans/phase46/design_decision.md
---

> **TL;DR**: Phase 46 目标是打通模型网关物理层——用 HTTP 执行器替代 subprocess CLI 成为主 LLM 路径，同时修复 CLI 执行器的品牌硬编码问题。完成后系统首次具备真实的多模型网络分发能力。

---

# Phase 46 Kickoff: 模型网关物理层实装 (Gateway Core Materialization)

## Phase 信息

- **Phase**: 46
- **Primary Track**: Execution Topology
- **Secondary Track**: Capabilities
- **前置 Phase**: Phase 45 (Eval 基线) ✅ 已完成，tag v0.3.2 已打
- **预期 tag**: v0.4.0（多模型网络引擎纪元）

## 目标

1. 在 Python 层引入 `httpx` HTTP 客户端，实现 `HTTPExecutor`，直连本地 `new-api`（`localhost:3000`，OpenAI-compatible API），让编排层的路由决策真正贯穿到物理网络调用
2. 将 CLI 执行器从品牌硬编码（`run_codex_executor`）重构为配置驱动的 `CLIAgentExecutor`，消除 `AGENT_TAXONOMY_DESIGN.md` §6.2 反模式 #1 违规
3. 注册多模型族 HTTP 路由（claude / qwen / glm / gemini / deepseek），确保方言严格对齐
4. 实现跨执行器族的分层降级链：HTTP → Cline CLI → 离线摘要

## 非目标

- 不废除 Codex CLI 路径（保留向后兼容，但退出降级链）
- 不实现 TensorZero 集成（降级为未来可选插件）
- 不实现 Gemini Context Caching / File API（仅做基础方言适配）
- 不实现流式响应 streaming（留给 Phase 48 异步改造）
- 不修改 Orchestrator 主循环（只替换执行层）
- 不引入 httpx 以外的新外部依赖（Cline CLI 为可选软依赖）

## 设计边界

- HTTP 执行器走 OpenAI-compatible `/v1/chat/completions` 协议，不实现供应商私有 API
- CLI 执行器重构为 `CLIAgentExecutor` + `CLIAgentConfig`，品牌通过配置注入而非硬编码
- 降级链由 `RouteSpec.fallback_route_name` 驱动，不引入新的降级机制
- 所有新增路由必须在 `_build_builtin_route_registry` 中注册，不允许运行时动态注册
- Eval 护航：Phase 45 建立的 EDD 规则（`shared/rules.md` §十）继续适用，新增 HTTP 执行器专属 eval 场景

## Slice 列表

| # | Slice | 风险 | 依赖 |
|---|-------|------|------|
| S1 | 基础设施就绪验证 (Infra Readiness) | 低 (4) | 无 |
| S2 | HTTP 执行器核心 + CLI 去品牌化 (HTTP Executor Core + CLI Debranding) | 高 (8) | S1 |
| S3 | 方言对齐与多模型路由 (Dialect Alignment & Multi-Model Routing) | 中 (5) | S2 |
| S4 | 降级矩阵与 Eval 护航 (Fallback Matrix & Eval Guard) | 高 (7) | S2, S3 |

## 完成条件

1. `HTTPExecutor` 能通过 `new-api` 成功调用至少两个不同模型族的 LLM 并返回有效响应
2. `CLIAgentExecutor` 以配置驱动方式支持 Codex 和 Cline，`run_executor_inline` 不再有品牌隐式兜底
3. 降级链 `http-claude → http-qwen → http-glm → cli/cline → local-summary` 在模拟故障场景下正确触发
4. 全量 pytest 无回归（320+ tests passed）
5. `pytest -m eval` 的 HTTP 执行器质量基线通过

## Stop/Go Gates

- **S2 完成后**：Human gate。必须验证通过 `local-http` 路由发送真实请求到 new-api，收到有效 LLM 响应。如果 new-api 不可用或响应格式不符预期，暂停不进入 S3。
- **S4 完成后**：全量测试 + eval 通过后，准备 PR。

## Eval 验收条件

以下 eval 场景需在 Phase 46 中新增覆盖（补充 Phase 45 已有基线）：

| 场景 | 指标 | 基线 |
|------|------|------|
| HTTP 执行器响应结构完整性 | 响应包含 `choices[0].message.content` | 100% |
| Claude 方言正确性 | 响应中 XML 标签闭合率 | ≥ 95% |
| 跨模型降级触发准确性 | 模拟故障后降级到正确的 fallback 路由 | 100% |

## 分支建议

- 建议分支名：`feat/phase46_gateway-core`
- PR 范围：S1-S4 全部完成后一次性 PR
- 如果 S2 scope 过大，可考虑 S1+S2 先开一个 PR，S3+S4 第二个 PR
