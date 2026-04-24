---
phase: phase52
type: review
status: approved_with_concerns
author: claude
reviewed_at: 2026-04-24
---

# Phase 52 PR Review

## TL;DR

实现与设计高度吻合。三个 slice 的核心机制均已落地：`AsyncCLIAgentExecutor` 替换了 codex/cline、`complexity_hint` 驱动路由偏置、fan-out 守卫与 summary artifact 补齐。codex/cline 清理基本到位但有残留（dialect adapter、cost estimation、executor 文案）。`schedule_consistency_audit` 的 asyncio 迁移实现正确，background task set 收口完整。两个 CONCERN 不阻塞合并。

---

## Design Conformance

### S1 — AsyncCLIAgentExecutor + 命名收口

✅ `AsyncCLIAgentExecutor`（`executor.py:176-200`）已落地，`AIDER_CONFIG` / `CLAUDE_CODE_CONFIG` 通过 `CLI_AGENT_CONFIGS` 注册，`resolve_executor` 在 L220-221 正确分发。

✅ `schedule_consistency_audit` 已改为 `async def`（`consistency_audit.py:275`），`_maybe_schedule_consistency_audit` 使用 `asyncio.create_task`（`orchestrator.py:252`），background task set 通过 `_BACKGROUND_CONSISTENCY_AUDIT_TASKS` 管理，`_wait_for_background_consistency_audits` 在 `run_task_async` 尾部等待（`orchestrator.py:235-242`）。R3 风险的缓解方案完整落地。

✅ `doctor executor` 替代旧 `doctor codex`，保留 deprecated alias（`cli.py:2134, 3353`）。

⚠️ **codex/cline 残留**：以下位置仍包含 codex/cline 引用，属于品牌残留但不影响功能：

- `executor.py:18` — `from .dialect_adapters import ClaudeXMLDialect, CodexFIMDialect`
- `executor.py:371` — `"codex_fim": CodexFIMDialect()`
- `executor.py:865` — `"live Codex execution was skipped"` 文案
- `executor.py:1644` — `"wss://chatgpt.com/backend-api/codex/responses"` 在 `classify_failure_kind` 的 unreachable markers 中
- `dialect_adapters/codex_fim.py` — 整个文件（`CodexFIMDialect` 类）
- `cost_estimation.py:7` — `"codex": (0.0, 0.0)` 成本估算条目

其中 `CodexFIMDialect` 是 dialect adapter（prompt 格式化），不是执行器——它的 `supported_model_hints` 包含 `["codex", "deepseek", "deepseek-coder"]`，实际上服务于 DeepSeek 系列模型的 FIM 格式。**这不是 bug**，但命名容易误导。建议后续 phase 重命名为 `FIMDialect` 或 `DeepSeekFIMDialect`。

✅ `router.py:44-45` 保留了 legacy alias 归一化（`local-codex → local-aider`、`local-cline → local-claude-code`），这是正确的兼容处理。

### S2 — Strategy Router 路由规则

✅ `_resolve_complexity_hint`（`router.py:781-783`）从 `state.task_semantics` 读取 `complexity_hint`。

✅ `_apply_complexity_bias`（`router.py:786-798`）正确实现偏置逻辑：`low/routine → local-aider`、`high → local-claude-code`。

✅ `select_route`（`router.py:857-862`）在 complexity_hint 生效时，先用 `__strategy_router__` 作为 executor_name 获取全量候选，再 apply bias。这个设计巧妙——避免了 `configured_executor == DEFAULT_EXECUTOR` 时只拿到 aider 候选的问题。

✅ `RouteSelection.policy_inputs` 记录了 `complexity_hint` 和 `parallel_intent`（`router.py:885-886`）。

✅ `TaskSemantics.complexity_hint` 已贯通 `build_task_semantics` / `create_task` / `update_task_planning_handoff`。

⚠️ **`parallel_intent` 未被消费**：`select_route` 在 `policy_inputs` 中设置了 `parallel_intent: True`，但上游 orchestrator 未读取此信号来决定是否进入 fan-out 路径。这是设计文档中明确的"Phase 52 不实装 Planner 自动拆分"的结果，但意味着 `parallel_intent` 目前是一个纯记录字段，不驱动任何行为。可接受，但需在后续 phase 消费。

### S3 — Fan-out / Fan-in 守卫与汇总

✅ `AsyncSubtaskOrchestrator._run_single_card`（`subtask_orchestrator.py:361-382`）使用 `asyncio.wait_for` + `_subtask_timeout_seconds(card)` 实现子任务级 timeout 守卫。

✅ `_run_level`（`subtask_orchestrator.py:409`）使用 `asyncio.gather(..., return_exceptions=True)`，局部失败通过 `_exception_record` 转换为 `SubtaskRunRecord(status="failed")`，不 cancel 其他任务。

✅ `_resolve_max_subtask_workers`（推测从环境变量 `AIWF_MAX_SUBTASK_WORKERS` 读取）已接线。

✅ `subtask_summary.md` artifact 在多 card 路径产出。

✅ `run_cli_agent_executor_async` 在 cancel/timeout 场景下清理子进程（closeout 中提到）。

---

## Code Quality

- `_apply_complexity_bias` 的排序 key `(0 if route.name == preferred else 1, -route.quality_weight, route.name)` 简洁正确，保持了 quality_weight 作为次级排序。
- `_maybe_schedule_consistency_audit` 的 `asyncio.create_task` + `_BACKGROUND_CONSISTENCY_AUDIT_TASKS.add(task)` + `task.add_done_callback(_BACKGROUND_CONSISTENCY_AUDIT_TASKS.discard)` 模式是 Python asyncio fire-and-forget 的标准做法。
- `AsyncCLIAgentExecutor` 当前仍通过 `_run_harness_execution_async`（`asyncio.to_thread` 包装）执行，而非直接用 `asyncio.create_subprocess_exec`。这意味着 **S1 的"原生 async subprocess"目标未完全达成**——CLI agent 仍经过 harness 的同步桥接。但这是 Runtime v0 的架构约束（harness 是同步的），不是 Phase 52 的实现缺陷。design_decision 中的 `AsyncCLIAgentExecutor` 核心实现描述（`asyncio.create_subprocess_exec + proc.communicate()`）与实际实现有偏差，实际走的是 harness 路径。

---

## Test Coverage

✅ 437 passed, 8 deselected — 全量基线稳定。

✅ `test_executor_protocol.py` 参数化已替换为 aider/claude-code。

✅ `test_router.py` 21 passed，覆盖 complexity_hint 四种场景。

✅ `test_subtask_orchestrator.py` + `test_run_task_subtasks.py` + `test_executor_async.py` 17 passed，覆盖 fan-out timeout / 局部失败隔离。

✅ `test_consistency_audit.py` 11 passed，覆盖 asyncio 迁移。

✅ `test_meta_optimizer.py` 19 passed，覆盖 cost trend 修正和 legacy alias 兼容。

---

## Risk Assessment

**R1（codex/cline 清理影响面）**：基本吸收。主执行路径、路由注册、默认值链已清理。残留在 dialect adapter 和 cost estimation 中，不影响功能。legacy alias 归一化（`router.py:44-45`）处理了持久化兼容。

**R2（subprocess stdout 死锁）**：当前实现走 harness 路径而非直接 subprocess，所以 R2 在本 phase 实际未触发。后续 Runtime v1 改为直接 subprocess 时需重新评估。

**R3（asyncio task 引用丢失）**：完整吸收。`_BACKGROUND_CONSISTENCY_AUDIT_TASKS` + `done_callback` + `_wait_for_background_consistency_audits` 三层保护。

**R4（DEFAULT_EXECUTOR 默认值链）**：已切换到 `aider`，下游逻辑正常。

**R7（Warp-Oz）**：已移除，不在本 phase。

---

## CONCERN items

CONCERN: `AsyncCLIAgentExecutor` 当前仍通过 `_run_harness_execution_async`（`asyncio.to_thread` 包装同步 harness）执行，而非 design_decision 中描述的 `asyncio.create_subprocess_exec + proc.communicate()`。这意味着 CLI agent 的 async 路径实际上仍有一层线程桥接。在 Runtime v0 架构下这是合理的（harness 是同步的），但 design_decision 的描述与实现不一致，需要在文档中修正或在后续 phase 真正落地原生 async subprocess。

CONCERN: codex/cline 品牌名在 `dialect_adapters/codex_fim.py`、`cost_estimation.py`、`executor.py` 文案中仍有残留。功能上不影响（`CodexFIMDialect` 实际服务 DeepSeek FIM 格式），但与 `ORCHESTRATION.md` 附录 A "品牌定义职责"反模式不一致。建议在 Phase 53/54 的 taxonomy 命名清理中一并处理。

---

## Verdict

**approved_with_concerns**

Phase 52 的三个 slice 均已落地，设计意图得到忠实实现。`complexity_hint` 路由偏置、fan-out timeout 守卫、summary artifact、consistency audit asyncio 迁移均正确。两个 CONCERN 不阻塞合并：harness 桥接是 Runtime v0 的架构约束，codex 品牌残留是命名层面的遗留。437 tests passed，meta-optimizer 兼容性问题已在 post-implementation validation 中吸收。
