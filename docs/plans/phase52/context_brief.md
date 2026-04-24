---
author: claude
phase: 52
slice: context_brief
status: final
depends_on:
  - docs/roadmap.md
  - docs/plans/phase51/closeout.md
  - docs/concerns_backlog.md
  - src/swallow/executor.py
  - src/swallow/orchestrator.py
  - docs/design/ORCHESTRATION.md
---

## TL;DR
Phase 51 (v0.8.0) 已稳定落地 MetaOptimizerAgent 独立生命周期与 route capability profile，Policy Era 基线已确立。Phase 52 的目标是将执行层的最后一批同步桥接层改为原生 async，并在此基础上实装 ORCHESTRATION.md §5.6 定义的 fan-out/fan-in 并行拓扑。核心风险在于 `run_cli_agent_executor`（codex/cline）当前通过 `asyncio.to_thread` 包装同步 `subprocess.run`，以及 `schedule_consistency_audit` 使用 `threading.Thread` 而非 asyncio 原语，两者在全异步链路下存在并发模型分叉。

---

# Phase 52 Context Brief

## 上游状态 (What Phase 51 delivered)

Phase 51 (commit `4b0de67`, tag `v0.8.0`) 已稳定交付以下能力，Phase 52 可直接依赖：

- `MetaOptimizerAgent` 独立生命周期：`execute` / `execute_async` 接口，`MetaOptimizerExecutor` 兼容包装器，`resolve_executor` 已接线
- `AuditTriggerPolicy` fire-and-forget 触发：`_maybe_schedule_consistency_audit` 在 `run_task_async` 主路径末尾调用，当前实现为 `threading.Thread`（daemon=True）
- `RouteCapabilityProfile`：`task_family_scores` / `unsupported_task_types` 持久化，route selection 已集成 task-family guard
- `MetaOptimizerSnapshot` 含 `route_task_family_stats`，proposal apply 已拆分 `load_route_weights` / `apply_route_weights` 语义
- 全量测试基线：237 passed（`test_cli.py`），18 passed（`test_meta_optimizer.py`），15 passed（`test_router.py`），18 passed（`test_executor_protocol.py`）

## 当前系统状态

### 同步桥接层现状（executor.py）

`run_prompt_executor_async`（第 575 行）中：

- `codex` 路径：`await asyncio.to_thread(run_codex_executor, ...)` — 同步 `subprocess.run` 包装
- `cline` 路径：`await asyncio.to_thread(run_cline_executor, ...)` — 同步 `subprocess.run` 包装
- `mock` / `mock-remote` / `note-only` / `local` 路径：同步函数直接调用（无 await），在 async 上下文中阻塞事件循环

`run_cli_agent_executor`（第 1338 行）：核心实现使用 `subprocess.run`（阻塞），无原生 async 版本。

`run_detached_executor`（第 703 行）：使用 `subprocess.run`，async 路径通过 `asyncio.to_thread` 包装（第 398 行）。

### 审计触发并发模型

`schedule_consistency_audit`（`consistency_audit.py` 第 270 行）：使用 `threading.Thread(daemon=True)`，在 asyncio 事件循环外独立运行。`_maybe_schedule_consistency_audit` 在 `run_task_async` 末尾（第 3517 行）同步调用，不 await。

### orchestrator.py 同步桥接

`_run_subtask_orchestration`（第 1902 行）：同步版本，内部使用 `threading.Lock`（`subtask_extra_artifacts_lock`，第 1910 行）管理 artifact 收集。异步版本 `_run_subtask_orchestration_async`（第 2030 行）已存在，主路径 `run_task_async` 使用异步版本。

`_run_orchestrator_sync`（第 3095 行）：同步入口，通过 `asyncio.run()` 包装 `run_task_async`，供 CLI 调用。

### 已完成的 async 覆盖

- `run_task_async` 为主执行路径，完整 async
- `HTTPExecutor.execute_async` / `run_http_executor_async`：原生 `httpx.AsyncClient`，已完全异步
- `LibrarianExecutor.execute_async`、`MetaOptimizerExecutor.execute_async`：已实装
- `_run_subtask_orchestration_async`：已实装，主路径使用

## 设计蓝图对齐

`ORCHESTRATION.md §5.6` 定义了 fan-out/fan-in 并行链路：

```
Planner 拆出独立任务 → asyncio.gather 并发执行 → 汇总 summary artifact → Human 或 Review Gate 收口
```

适用场景：无依赖关系的独立子任务批量执行（批量文件处理、多环境测试、并行调查）。

`ORCHESTRATION.md §2.3` 明确区分平台级 subtask orchestration（Swallow 编排层控制）与 executor-native subagents（黑盒增强），Phase 52 的并行拓扑属于前者。

`ORCHESTRATION.md §5.2` 并行调查链路要求 Subtask Orchestrator 分发给多个执行器并汇总中间结果，当前 `_run_subtask_orchestration_async` 已有基础，但尚未实装跨模型并行分发与资源争抢保护。

## Open Concerns 继承

来自 `docs/concerns_backlog.md`（Phase 51 登记）：

**C2（Phase 51 S3）**：`schedule_consistency_audit` 使用 `threading.Thread`，设计文档以 `asyncio.create_task` 描述 fire-and-forget。在全异步执行链路下，若继续保留双并发模型（asyncio 主路径 + threading 审计），可能造成语义分叉。计划在 Phase 52 全异步执行器收紧时统一并发原语。

**C1（Phase 51 S2）**：`MetaOptimizerAgent.memory_authority = "canonical-write-forbidden"` 语义与 artifact 写入 side effect 的区分，计划在 Phase 53 taxonomy 文档收紧时处理，不影响 Phase 52。

**Phase 49 C1**（`retrieval.py` `_sqlite_vec_warning_emitted` 竞态）：Phase 51 引入多进程 worker 前应改为 `threading.Event`，Phase 52 若引入多进程并行需先处理。

## Phase 52 的核心问题

1. **S1 边界**：`run_cli_agent_executor` 改为原生 async subprocess（`asyncio.create_subprocess_exec`）后，`CLIAgentExecutor.execute_async` 是否可以去掉 `asyncio.to_thread` 包装？`run_detached_executor` 是否也需要同步改造，还是保留 `asyncio.to_thread` 包装？

2. **S2 并发控制**：多路 subtask 并行时，`_run_subtask_orchestration_async` 中的 `subtask_extra_artifacts_lock`（`threading.Lock`）在 asyncio 上下文中是否需要替换为 `asyncio.Lock`？资源争抢保护（信号量、超时、死锁检测）的粒度应在 orchestrator 层还是 executor 层？

3. **C2 消化时机**：`schedule_consistency_audit` 的 `threading.Thread` 是否在 S1 完成后立即统一为 `asyncio.create_task`，还是作为独立 slice 处理？两者在 daemon 行为和异常传播上有差异，需要明确。

## 建议 kickoff 焦点

- 明确 S1 的改造边界：哪些执行器路径改为原生 async subprocess，哪些保留 `asyncio.to_thread`（如 `run_detached_executor` 的跨进程场景）
- 明确 S2 的并行拓扑实装范围：是否在本 phase 实装完整的 fan-out/fan-in，还是先完成执行器异步化后再压测
- 明确 C2 的消化方式：`threading.Thread` → `asyncio.create_task` 的迁移是否纳入 S1 或作为独立 slice
- 明确 `threading.Lock` → `asyncio.Lock` 的替换范围（`_run_subtask_orchestration_async` 中的 artifact 收集锁）
