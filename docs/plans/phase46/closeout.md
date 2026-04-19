---
author: codex
phase: 46
slice: all
status: final
depends_on:
  - docs/plans/phase46/kickoff.md
  - docs/plans/phase46/risk_assessment.md
  - docs/plans/phase46/review_comments.md
---

## TL;DR
Phase 46 已完成实现、review 与 review follow-up，当前状态为 **merge ready / PR sync ready**。本轮完成了模型网关物理层实装：`HTTPExecutor` 已接入本地 `new-api` OpenAI-compatible 端点，CLI 执行器已去品牌化并改为配置驱动，HTTP 多模型路由与方言矩阵已落地，降级链 `http-claude -> http-qwen -> http-glm -> local-cline -> local-summary` 可用。Claude review 结论为 `0 BLOCK / 1 CONCERN / 2 NOTE / Merge ready`，唯一 concern C1 已在本轮吸收。最终验证基线为默认 pytest `342 passed, 4 deselected`，eval pytest `4 passed, 342 deselected`。

# Phase 46 Closeout

## 结论

Phase 46 `Gateway Core Materialization` 已完成实现、review 与验证，当前状态为 **merge ready / PR sync ready**。

本轮围绕 kickoff 定义的 4 个 slice，完成了四条关键增量：

- S1：`new-api` / `httpx` / HTTP executor eval 基础设施就绪验证
- S2：`HTTPExecutor` 核心落地 + CLI executor 去品牌化
- S3：Claude / Qwen / GLM / Gemini / DeepSeek HTTP 路由与方言对齐
- S4：`http -> http -> local-cline -> local-summary` 降级矩阵与 eval 护航

Claude review 已完成，唯一 concern C1 已通过 post-review patch 吸收；`pr.md` 与本 closeout 已同步，可直接用于 Human 审查收口与 PR 更新。

## 已完成范围

### Slice 1: Infra Readiness

- 引入 `httpx` 依赖，补齐 `doctor` 中的 `new-api` 检查项与 HTTP executor eval 骨架
- 确认宿主机 `localhost:3000` 可达，HTTP executor 已支持 `AIWF_NEW_API_KEY` / `OPENAI_API_KEY` / `NEW_API_KEY`
- 完成 S2 前置 Human gate：修正 `new-api` 模型映射后，真实 `POST /v1/chat/completions` 对 `deepseek-chat` 返回 `PHASE46_HTTP_OK`
- 真实上游解析为 `deepseek/deepseek-chat-v3` via DeepInfra，证明本地鉴权链路与 OpenAI-compatible payload 均已打通

### Slice 2: HTTP Executor Core + CLI Debranding

- 新增 `HTTPExecutor`，使 `run_executor_inline()` 可通过本地网关执行 OpenAI-compatible chat completion
- 将品牌硬编码 CLI 路径重构为配置驱动的 `CLIAgentExecutor` / `CLIAgentConfig`
- 注册 `local-http` 路由、`http` route_mode 映射以及 `http/qwen/glm/gemini/deepseek` 计费与路由入口
- 对应实现提交：
  - `8e030a7 feat(gateway): add http executor and debrand cli agents`

### Slice 3: Dialect Alignment + Multi-Model Routing

- 注册 `http-claude` / `http-qwen` / `http-glm` / `http-gemini` / `http-deepseek`
- `route_model_hint` 优先命中匹配的 HTTP 物理路由；`local-http` 兼容别名会解析到配置的默认模型
- Claude 路由走 `claude_xml`，DeepSeek code 路由走 `codex_fim`，Qwen / GLM / Gemini 走 `plain_text`
- 对应实现提交：
  - `b5ccf5e feat(gateway): align http dialect routing matrix`

### Slice 4: Fallback Matrix + Eval Guard

- 新增 `local-cline` 路由，并将降级链接入 `http-claude -> http-qwen -> http-glm -> local-cline -> local-summary`
- executor 内部沿 `RouteSpec.fallback_route_name` 进行链式降级，包含循环检测
- `ExecutorResult` 与 executor telemetry 新增显式降级元数据：
  - `degraded`
  - `original_route_name`
  - `fallback_route_name`
- 保留 orchestrator 既有 binary fallback，并补齐回归覆盖
- 对应实现提交：
  - `14a4629 feat(gateway): add fallback matrix for http routes`

## 与 kickoff 完成条件对照

### 已完成的目标

- `HTTPExecutor` 已能通过本地 `new-api` 返回有效 completion；真实 Human gate 已通过
- `CLIAgentExecutor` 以配置驱动支持 Codex 和 Cline，`run_executor_inline` 不再保留品牌隐式兜底
- 降级链 `http-claude -> http-qwen -> http-glm -> local-cline -> local-summary` 在模拟故障场景下正确触发
- 默认 pytest 与 `pytest -m eval` 均已通过
- Phase 45 建立的 eval 机制继续维持隔离，不影响默认测试路径

### 未继续扩张的内容

以下方向仍明确不在本 phase 范围内：

- 不接入 TensorZero 或其他额外 provider 平台
- 不引入流式响应 streaming
- 不改写 Orchestrator 主循环
- 不把 Codex CLI 路径重新放回降级链
- 不新增 `httpx` 之外的重型外部依赖

## Review Follow-up

- Claude review 已完成：`0 BLOCK / 1 CONCERN / 2 NOTE / Merge ready`
- C1 已在本轮吸收：
  - `run_http_executor()` 对 HTTP `429` 映射为 `failure_kind="http_rate_limited"`
  - rate-limit 场景保持当前 route，不立即触发 executor-route fallback
  - `_run_binary_fallback()` 对 `http_rate_limited` 显式跳过二次降级
  - `RETRYABLE_FAILURE_KINDS` 现在重试 `http_rate_limited`，不再把通用 `http_error` 当作 retryable
  - `checkpoint_snapshot.py` 将 `http_rate_limited` 归入 `interruption_recovery`
  - 新增回归测试覆盖上述语义
- N1 / N2 保留为非阻塞后续事项：
  - `doctor.py` 仍有 postgres / pgvector 噪音检查
  - `normalize_executor_name` passthrough 仍缺少独立单测
- 本轮没有新增 open backlog concern：唯一 concern C1 已关闭

## Stop / Go 判断

### Stop 判断

当前 phase 应停止继续扩张，理由如下：

- kickoff 定义的 4 个 slice 已全部完成
- review 唯一 concern 已吸收，核心网关链路与降级链都已有对应测试
- 再继续扩张会自然滑向 infra 清理、streaming、异步改造或 provider 平台扩展，不属于本轮范围

### Go 判断

下一步应按如下顺序推进：

1. Human 审查当前 diff，并执行审查收口 commit
2. Human push 当前分支，并使用 `pr.md` 创建 / 更新 PR 描述
3. Human 根据当前 review 结论决定 merge
4. 如合并完成，可按 review 建议评估 `v0.4.0`

## 当前稳定边界

Phase 46 收口后，以下边界应视为当前候选稳定 checkpoint：

- 主 LLM live path 已从 subprocess CLI 扩展为本地 OpenAI-compatible HTTP gateway
- CLI executor 以配置驱动支持 `codex` / `cline`，未知 executor 会显式报错而非静默品牌兜底
- HTTP 路由矩阵与方言矩阵已对齐：Claude XML、DeepSeek FIM、Qwen / GLM / Gemini plain text
- 降级链由 `RouteSpec.fallback_route_name` 驱动，并具备循环检测与显式降级元数据
- HTTP 429 现在被视为“应重试的中断型失败”，而不是“立即切换路线的不可用失败”

## 当前已知问题

- `doctor.py` 仍会报 postgres / pgvector 检查失败噪音
- `normalize_executor_name` 的 passthrough 行为仍缺少独立单测
- 真实 provider 可用性仍受本地 `new-api` 栈、上游配额和网络环境约束

以上问题均不阻塞当前进入 merge 阶段。

## 测试结果

最终验证结果：

```text
.venv/bin/pytest --tb=short -> 342 passed, 4 deselected
.venv/bin/pytest -m eval -v -> 4 passed, 342 deselected
.venv/bin/pytest tests/test_executor_protocol.py tests/test_binary_fallback.py tests/test_retry_policy.py tests/test_checkpoint_snapshot.py -> passed
.venv/bin/pytest tests/test_cli.py -k "retry_policy or checkpoint_snapshot or provider_dialect_is_visible_in_prompt_artifact_events_inspect_and_review" -> passed
```

补充说明：

- 默认测试基线与 eval 基线均已单独验证
- review follow-up 的 429 / retry / checkpoint 语义已有专项回归测试

## 规则文件同步检查

### 必查

- [x] `docs/plans/phase46/closeout.md`
- [x] `docs/plans/phase46/kickoff.md`
- [x] `docs/plans/phase46/risk_assessment.md`
- [x] `docs/plans/phase46/review_comments.md`
- [x] `docs/active_context.md`
- [x] `./pr.md`

### 条件更新

- [ ] `current_state.md`
- [ ] `AGENTS.md`
- [ ] `README.md`
- [ ] `README.zh-CN.md`

说明：

- `current_state.md` 仍表示已合并稳定 checkpoint；Phase 46 尚未 merge，当前不提前更新
- 本轮未改变长期协作规则与 tag 级对外能力快照，暂不更新 `AGENTS.md` / README

## Git / PR 建议

1. Human 审查当前 diff，并执行审查收口 commit
2. Human 使用当前根目录 `pr.md` 作为 PR 描述草案
3. Human push `feat/phase46_gateway-core`，并更新 / 创建 PR
4. merge 后可评估 `v0.4.0`

## 下一轮建议

如果 Phase 46 merge 完成，下一轮应回到 roadmap，优先进入 Phase 47 的多 Reviewer / policy guardrails，而不是继续在当前分支扩张 infra 清理或流式执行能力。
