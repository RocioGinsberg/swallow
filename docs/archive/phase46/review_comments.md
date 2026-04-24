---
author: claude
phase: 46
status: final
verdict: 0 BLOCK / 1 CONCERN / 2 NOTE / Merge ready
---

# Phase 46 Review Comments

## 总体评价

Phase 46 目标完整达成。`HTTPExecutor` 已落地并通过真实 new-api 调用验证，`CLIAgentExecutor` + `CLIAgentConfig` 消除了品牌硬编码，5 条 HTTP 路由 + `local-cline` 注册完整，降级链 `http-claude → http-qwen → http-glm → local-cline → local-summary` 有循环检测保护。全量 337 passed，4 eval passed，无回归。

---

## BLOCK（阻塞合并）

无。

---

## CONCERN（建议合并前处理）

**C1：429 rate-limit 未做退避，直接触发降级**

`run_http_executor` 对 `httpx.HTTPStatusError` 统一映射为 `http_error` 并立即触发 fallback，没有区分 429 与 5xx。429 的语义是"稍后重试"，直接降级会浪费已配置的主力路由（如 `http-claude`），且 `retry_policy.py` 已将 `http_error` 列为可重试类型，两者存在语义不一致。

建议：在 `HTTPStatusError` 分支中对 `status_code == 429` 单独映射为 `failure_kind="http_rate_limited"`，并从 `RETRYABLE_FAILURE_KINDS` 中移除 `http_error`（保留 `http_timeout`）。`http_rate_limited` 可在 `checkpoint_snapshot.py` 中归入 `interruption_recovery` 语义。这样降级链只在真正不可用时触发，429 走重试路径。

---

## NOTE（可接受，建议后续跟进）

**N1：`doctor.py` 仍保留 postgres / pgvector 检查项**

`diagnose_local_stack` 中仍有 `_check_container_running("postgres_container", "postgres")` 和 `_check_pgvector_extension()`。当前部署已移除 PostgreSQL，这两项每次都会报 fail，产生噪音。建议在 Phase 47 或下一个 docs/infra 清理 slice 中将其标注为 `optional` 或移除。不阻塞本次合并。

**N2：`normalize_executor_name` 的 fallback 行为变更未加测试**

`dialect_data.py` 将 `normalize_executor_name` 的 fallback 从 `DEFAULT_EXECUTOR`（`"codex"`）改为 `normalized or DEFAULT_EXECUTOR`，使未知 executor name 透传而非静默降级到 codex。这是正确方向（配合 `UnknownExecutorError`），但当前测试套件没有覆盖"未知 executor name 透传后被 `run_executor_inline` 的 `UnknownExecutorError` 捕获"这条完整路径。`test_run_executor_inline_raises_for_unknown_executor` 覆盖了 inline 层，但没有覆盖 `normalize_executor_name` 的透传行为本身。建议后续补一个单元测试。不阻塞本次合并。

---

## 验收确认

| 条件 | 状态 |
|------|------|
| `HTTPExecutor` 通过真实 new-api 调用返回有效 LLM 响应 | ✅ Human gate 已通过 |
| `CLIAgentExecutor` 以配置驱动支持 Codex 和 Cline | ✅ |
| 降级链在模拟故障场景下正确触发 | ✅ eval + unit 覆盖 |
| 全量 pytest 无回归（337 passed） | ✅ |
| `pytest -m eval` 4 passed | ✅ |
| `run_executor_inline` 对未知 executor 抛 `UnknownExecutorError` | ✅ |

---

## Tag 建议

Phase 46 完成后系统首次具备真实多模型网络分发能力，大脑（Orchestrator）与手脚（HTTPExecutor）正式连通。建议合并后打 `v0.4.0`（多模型网络引擎纪元），与 roadmap 预期一致。前提：C1 的 429 处理在合并前或 v0.4.0 打标前修复。
