---
author: claude
phase: 46
slice: all
status: draft
depends_on:
  - docs/roadmap.md
  - docs/design/PROVIDER_ROUTER_AND_NEGOTIATION.md
  - docs/design/AGENT_TAXONOMY_DESIGN.md
  - src/swallow/executor.py
  - src/swallow/router.py
  - src/swallow/dialect_data.py
---

> **TL;DR**: Phase 46 用 `httpx` 实现 `HTTPExecutor`，直连 `localhost:3000` (new-api) 的 OpenAI-compatible 端点，替代 `subprocess.run(["codex"])` 成为系统主 LLM 路径。同时将 CLI 执行器从品牌硬编码重构为配置驱动的 `CLIAgentExecutor`（修复 Agent Taxonomy 反模式）。分 4 个 slice：基础设施验证 → HTTP 执行器核心 + CLI 去品牌化 → 方言对齐与多模型路由（claude/qwen/glm/gemini/deepseek）→ 降级矩阵（HTTP → Cline CLI → 离线）与 Eval 护航。

---

# Phase 46: 模型网关物理层实装 — 方案拆解

## 方案总述

当前系统的编排层（Orchestrator + Router + Dialect Adapters）已经具备完整的多模型路由语义，但执行层唯一能真正调用 LLM 的活路径是 `run_codex_executor`，通过 `subprocess.run` 调用 Codex CLI 二进制。这意味着 `route_model_hint`、`route_dialect`、降级策略等所有路由决策在最后一公里全部失效。

此外，当前 CLI 执行器存在品牌硬编码问题（违反 `AGENT_TAXONOMY_DESIGN.md` §6.2 反模式 #1）：函数名 `run_codex_executor`、变量 `codex_bin`、`executor_name="codex"` 全部绑定了特定品牌，而 `run_executor_inline` 的 `else` 兜底也隐式默认走 Codex。按分类学设计，CLI 执行器应以系统角色（`general-executor / local / task-state / cli-agent`）而非品牌来标识。

Phase 46 的目标是：
1. 在 Python 层引入 `httpx` HTTP 客户端，直连本地 `new-api`（`localhost:3000`，OpenAI-compatible API），让编排层的路由决策真正贯穿到物理网络调用
2. 将 CLI 执行器从品牌硬编码重构为配置驱动的 `CLIAgentExecutor`，消除分类学违规

完成后，系统将首次具备真实的多模型网络分发能力，且执行器命名符合 Agent Taxonomy 规范。

## 一条关键边界说明：HTTP 受控路径 vs Agent 黑盒路径

为了避免后续混淆，Phase 46 需要明确区分两类不同执行路径。

### A. HTTP 受控路径（Swallow-controlled HTTP path）

典型形态：

`TaskState + RetrievalItems -> Router -> route_model_hint / dialect_hint -> HTTPExecutor -> HTTP API`

在这条路径中，Swallow 自己控制：

- prompt 生成与格式化
- retrieval context assembly
- `route_model_hint`
- `dialect_hint`
- request payload 结构
- fallback 逻辑
- telemetry 与 eval 基线

因此，这条路径上的方言适配器是真正由 Swallow 主导的。只要模型调用仍经过 router + dialect adapters + HTTPExecutor，方言就应按照当前 route/model hint 自动生效。

### B. Agent 黑盒路径（agent black-box path）

典型形态：

`TaskState -> CLIAgentExecutor / external agent -> agent internal model handling -> model/provider`

例如 Aider、Claude Code、Warp/Oz、Cline 等 agent / CLI 工具，一旦在内部自己决定：

- 使用哪个模型
- 如何拼接 prompt
- 是否做多轮反思
- 如何调用工具或子代理

这些内部行为通常不再由 Swallow 精细控制。

在这条路径中，Swallow 更擅长控制的是：

- 任务边界
- skills / subagents / rules
- 输入输出契约
- 升级 / 降级策略
- 成本、日志与行为观测

而不是像 HTTP 受控路径那样精细控制底层 prompt / dialect。

这意味着：

- **方言适配器主要服务于 HTTP 受控路径**
- **黑盒 agent 路径主要依赖 executor governance，而不是统一的 prompt/dialect 微控制**

后续若系统接入更多原生 agent 工具，也应优先把它们视为“黑盒执行器”处理，除非某个工具暴露足够稳定、可控的中间协议接口。

## Slice 拆解

### S1: 基础设施就绪验证 (Infra Readiness)

**目标**：确认 `new-api` Docker 栈可用，验证 OpenAI-compatible 端点的请求/响应格式，建立 Phase 46 的 eval 测试基础设施。

**具体任务**：
- 验证 `localhost:3000` (new-api) 的 `/v1/chat/completions` 端点可达，确认请求格式（model、messages、temperature 等）
- 在 `tests/eval/` 下新增 `test_http_executor_eval.py`，定义 HTTP 执行器的质量基线场景（方言正确性、JSON Schema 遵循率、响应结构完整性）
- 在 `pyproject.toml` 中添加 `httpx` 依赖
- 新增 `swl doctor` 检查项：`new-api` 端点连通性

**影响范围**：`pyproject.toml`、`tests/eval/`、`src/swallow/doctor.py`
**风险评级**：影响范围 1 + 可逆性 1 + 依赖复杂度 2 = **4（低）**
**验收条件**：
- `httpx` 已加入项目依赖
- `swl doctor` 能报告 `new-api` 端点状态
- eval 测试骨架存在且可通过 `pytest -m eval` 收集

---

### S2: HTTP 执行器核心 + CLI 执行器去品牌化 (HTTP Executor Core + CLI Debranding)

**目标**：实现 `HTTPExecutor`，通过 `httpx` 直连 `new-api` 的 OpenAI-compatible 端点，成为系统的主 LLM 路径。同时将 CLI 执行器从品牌硬编码重构为配置驱动。

**具体任务**：

**HTTP 执行器**：
- 在 `executor.py` 中新增 `HTTPExecutor` 类，实现 `ExecutorProtocol`
- 核心逻辑：接收 `TaskState` + `RetrievalItem[]` → `build_formatted_executor_prompt` → 构造 OpenAI-compatible `ChatCompletion` 请求 → `httpx.post` 到 `state.route_endpoint`（默认 `http://localhost:3000/v1/chat/completions`）→ 解析响应 → 返回 `ExecutorResult`
- 在 `run_executor_inline` 中新增 `elif executor_name == "http":` 分支，调用 `run_http_executor`
- 在 `resolve_executor` 中新增 `elif normalized_type == "http":` 分支，返回 `HTTPExecutor()`
- 在 `router.py` 的 `_build_builtin_route_registry` 中注册 `local-http` 路由：`executor_name="http"`、`backend_kind="http_api"`、`transport_kind="http"`、`model_hint="claude"`（初始默认）
- 在 `ROUTE_MODE_TO_ROUTE_NAME` 中添加 `"http": "local-http"` 映射
- 处理基本错误：连接超时、HTTP 4xx/5xx、响应解析失败，统一映射到 `ExecutorResult` 的 `failure_kind`
- 补充 `build_failure_recommendations` 的 `"http_error"` / `"http_timeout"` 分支

**CLI 执行器去品牌化**（修复 AGENT_TAXONOMY_DESIGN.md §6.2 反模式 #1）：
- 将 `run_codex_executor` 重构为通用的 `CLIAgentExecutor` 类，实现 `ExecutorProtocol`
- 引入 `CLIAgentConfig` 数据类，包含 `bin_name`、`args_template`、`output_parse_mode`、`env_var_prefix` 等配置字段
- Codex 和 Cline 作为 `CLIAgentExecutor` 的不同配置实例：
  - `CLIAgentConfig(bin_name="codex", args=["exec", "--full-auto", ...], env_prefix="AIWF_CODEX")`
  - `CLIAgentConfig(bin_name="cline", args=["-y", "--output-format", "json", ...], env_prefix="AIWF_CLINE")`
- 修复 `run_executor_inline` 的 `else` 兜底：改为显式报错（`UnknownExecutorError`），不再隐式默认走任何品牌
- 更新 `resolve_executor` 中的 `"codex"` 和 `"cline"` 分支，均返回对应配置的 `CLIAgentExecutor` 实例
- 在 `cost_estimation.py` 的 `MODEL_PRICING` 中补充 `"qwen"`、`"glm"` 等模型定价

**影响范围**：`executor.py`（重构核心）、`router.py`、`cost_estimation.py`、`models.py`（如需新增 route 字段）
**风险评级**：影响范围 3 + 可逆性 2 + 依赖复杂度 3 = **8（高）**
**验收条件**：
- `HTTPExecutor` 通过 `ExecutorProtocol` 一致性测试
- `CLIAgentExecutor` 通过 `ExecutorProtocol` 一致性测试，Codex/Cline 均为配置实例
- `resolve_executor("http", "http")` 返回 `HTTPExecutor` 实例
- `resolve_executor("cli", "codex")` 和 `resolve_executor("cli", "cline")` 返回对应配置的 `CLIAgentExecutor`
- `run_executor_inline` 对未知 executor name 抛出 `UnknownExecutorError` 而非默认走 Codex
- `route_mode="http"` 能正确路由到 `local-http` 路由
- 使用 mock HTTP server 的单元测试通过（不依赖真实 new-api）
- 使用真实 new-api 的 eval 测试通过（`pytest -m eval`）
- 现有 320+ pytest 无回归（CLI 重构不破坏已有路径）

**stop/go gate**：S2 完成后必须验证——通过 `local-http` 路由发送一个真实请求到 new-api，收到有效的 LLM 响应。如果 new-api 不可用或响应格式不符预期，在此暂停，不进入 S3。

---

### S3: 方言对齐与多模型路由 (Dialect Alignment & Multi-Model Routing)

**目标**：确保 `route_model_hint` 严格决定物理路由和方言选择，补齐缺失的方言适配器，让不同模型收到各自的原生格式。

**具体任务**：
- 在 `_build_builtin_route_registry` 中注册多条 HTTP 路由，每条对应一个模型族：
  - `http-claude`：`model_hint="claude"`、`dialect_hint="claude_xml"`
  - `http-qwen`：`model_hint="qwen"`、`dialect_hint="plain_text"`
  - `http-glm`：`model_hint="glm"`、`dialect_hint="plain_text"`
  - `http-gemini`：`model_hint="gemini"`、`dialect_hint="plain_text"`（或新增 `gemini_context` 方言）
  - `http-deepseek`：`model_hint="deepseek"`、`dialect_hint="codex_fim"`（降低优先级，仅作为代码补全场景备选）
- 确保 `HTTPExecutor` 在构造请求时，根据 `state.route_model_hint` 设置正确的 `model` 字段（new-api 的渠道名 → 上游模型）
- 验证 Claude 路由收到 `<thinking>` XML 标签、DeepSeek 路由收到 FIM 标记
- 如果 Gemini 需要特殊处理（如 context caching），在本 slice 中仅做方言层的 stub，不实现完整的 File API 集成（那是未来 phase 的事）
- 更新 `resolve_dialect_name` 的 `supported_model_hints`，确保 `"gemini"` 能匹配到正确方言

**影响范围**：`router.py`、`executor.py`、`dialect_adapters.py`（可能）、`dialect_data.py`
**风险评级**：影响范围 2 + 可逆性 1 + 依赖复杂度 2 = **5（中）**
**验收条件**：
- 三条以上 HTTP 路由均已注册且可通过 `candidate_routes` 查询
- `route_model_hint="claude"` 的请求经过 `ClaudeXMLDialect` 格式化
- `route_model_hint="deepseek"` 的请求经过 `CodexFIMDialect` 格式化
- `route_model_hint="qwen"` / `"glm"` 的请求经过 `PlainTextDialect` 格式化
- 方言正确性 eval 测试通过

---

### S4: 降级矩阵与 Eval 护航 (Fallback Matrix & Eval Guard)

**目标**：实现跨执行器族的分层降级，确保网络异常时系统不崩溃，并通过 Eval 验证整体替换不降级。

**降级链设计**：

```
http-claude (超时/429)
  → http-qwen (跨模型族降级，仍走 HTTP 主路径)
    → http-glm (二级 HTTP 降级)
      → cli/cline -y (HTTP 全链路不可用时的 agent 兜底)
        → local-summary (离线最终兜底，无 LLM)
```

设计理由：
- HTTP 层内降级（claude → qwen → glm）优先，因为 Swallow 对 HTTP 路径有完整的路由/方言/遥测控制。Qwen 和 GLM 当前综合能力优于 DeepSeek（DeepSeek 保留为代码补全专用路由，不进入通用降级链）
- 当 HTTP 全链路不可用（如 new-api 容器挂了）时，降级到 Cline CLI（headless `-y` 模式），保留活 LLM 能力。Cline 支持多模型、JSON 输出，比 Codex 更灵活，适合作为 agent 级兜底
- CLI 执行器族（Cline/Codex）的遥测控制力有限（模型选择、工具调用在 agent 内部发生），这是所有 CLI 执行器的共性约束，不影响其作为兜底的价值
- `local-summary` 作为最终离线兜底，确保系统在完全无网络时仍能产出结构化摘要

**具体任务**：
- 在 `HTTPExecutor` 中实现降级逻辑：当目标模型不可用时，按 `RouteSpec.fallback_route_name` 链式降级
- 新增 Cline 的 `CLIAgentConfig` 配置实例（复用 S2 重构的 `CLIAgentExecutor`），通过 `subprocess.run(["cline", "-y", "--output-format", "json", ...])` 调用 Cline CLI headless 模式
- 在 `resolve_executor` 中确认 `"cline"` 分支返回对应配置的 `CLIAgentExecutor`
- 在 `_build_builtin_route_registry` 中注册 `local-cline` 路由：`executor_name="cline"`、`executor_family="cli"`、`transport_kind="local_process"`
- 配置 fallback 链：`http-claude.fallback → http-qwen.fallback → http-glm.fallback → local-cline.fallback → local-summary`
- 实现降级遥测：在 `ExecutorResult` 中记录 `degraded=True`、`original_route`、`fallback_route`（复用现有 telemetry 字段）
- 实现限流感知：识别 HTTP 429 响应，触发退避 + 降级
- 补齐 S1 中定义的 eval 基线测试的完整实现
- 运行全量 `pytest`（非 eval）确保现有 320+ 测试无回归
- 运行 `pytest -m eval` 确保 HTTP 执行器的质量基线达标

**影响范围**：`executor.py`、`router.py`、`tests/eval/`、`tests/test_executor_protocol.py`
**风险评级**：影响范围 2 + 可逆性 2 + 依赖复杂度 3 = **7（高）**
**验收条件**：
- 模拟 HTTP 超时/429/5xx 时，系统按 fallback 链降级而非崩溃
- Cline CLI 兜底路径可通过 mock 测试验证（不依赖真实 Cline 安装）
- 降级事件在 telemetry 中可追踪
- 全量 pytest 无回归（320+ tests passed）
- eval 基线测试通过

---

## 依赖说明

```
S1 (基础设施就绪)
  └──→ S2 (HTTP 执行器核心) ← 强依赖：S2 需要 httpx 依赖和 eval 骨架
         └──→ S3 (方言对齐) ← 强依赖：S3 需要 HTTPExecutor 已能发送请求
         └──→ S4 (降级矩阵) ← 强依赖：S4 需要 HTTPExecutor + 多路由已注册
```

S3 和 S4 之间无强依赖，但建议先 S3 后 S4，因为降级矩阵需要多条路由已注册才能测试跨模型降级。

## 明确的非目标

- **不废除 Codex CLI 路径**：`run_codex_executor` 和 `local-codex` 路由保留，作为向后兼容。但 Codex 不再是降级链的一环——Cline CLI 取代其兜底定位。
- **不实现 TensorZero 集成**：TensorZero 降级为未来可选插件（roadmap 已确认）。
- **不实现 Gemini Context Caching**：Gemini 方言在 S3 中仅做基础适配，File API / Context Cache 是未来 phase 的事。
- **不实现流式响应 (streaming)**：初版 HTTP 执行器使用同步请求/响应，streaming 留给 Phase 48 的异步改造。
- **不修改 Orchestrator 主循环**：Phase 46 只替换执行层，不改变编排逻辑。
- **不引入新的外部依赖**（除 `httpx`）。Cline CLI 作为可选兜底，不作为硬依赖——未安装时跳过该降级层。
- **不假设黑盒 agent 的内部 prompt / dialect 可被 Swallow 完整接管**：对于 Aider、Claude Code、Warp/Oz 等原生 agent 路径，系统默认只做 executor governance，而不承诺做底层 prompt 微控制。

## 整体风险评估

| Slice | 风险分 | 等级 |
|-------|--------|------|
| S1 基础设施就绪 | 4 | 低 |
| S2 HTTP 执行器核心 + CLI 去品牌化 | 8 | 高 |
| S3 方言对齐 | 5 | 中 |
| S4 降级矩阵 + Cline 兜底 | 7 | 高 |
| **总计** | **24/36** | **中-高** |

S2 和 S4 是两个高风险 slice。S2 完成后设置 Human gate，确认 HTTP 执行器能真实调用 LLM。S4 的 Cline CLI 集成采用 graceful degradation——Cline 未安装时自动跳过该降级层，不阻塞系统运行。
