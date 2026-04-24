---
author: claude
phase: 48
slice: review
status: draft
depends_on:
  - docs/plans/phase48/design_decision.md
  - docs/plans/phase48/risk_assessment.md
  - docs/plans/phase48/commit_summary.md
---

## TL;DR
Phase 48 实现整体与 design_decision 对齐，全量 378 tests passed。无 BLOCK 项。有 4 个 CONCERN，均属可接受的设计权衡，建议登记 backlog 后进入 merge gate。

---

# Phase 48 Review Comments

## 评审范围

- Branch: `feat/phase48_async-storage` vs `main`
- 最新提交: `11cef98 feat(store): cut over default sqlite storage`
- 测试结果: `378 passed, 7 deselected, 5 subtests passed`（全量 pytest，无回归）

---

## 一、与 design_decision 一致性

### [PASS] S1: async-executor
`ExecutorProtocol` 新增 `execute_async()`，所有 executor 实现均通过 `asyncio.to_thread(_run_harness_execution)` 桥接。`pytest-asyncio` 已在 `pyproject.toml` 声明。接口并存策略与设计一致。

### [PASS] S2: async-review-gate
`run_consensus_review_async()` 使用 `asyncio.gather(*reviewer_tasks, return_exceptions=True)`，单 reviewer 超时通过 `asyncio.wait_for` 保护，超时视为 `failed` 而非中断其他 reviewer。`run_review_gate()` 保留为同步兼容包装层。与设计完全一致。

### [PASS] S3: sqlite-schema
Schema 与 design_decision 中的 DDL 完全一致（tasks / events 表，WAL 模式，`PRAGMA busy_timeout=5000`，冗余 status/kind 列）。`TaskStoreProtocol` 抽象、`FileTaskStore` / `DefaultTaskStore` 双存储分派均已实现。

### [PASS] S4: async-orchestrator
`run_task_async()` 已实现，`run_task()` 作为同步兼容壳通过 `_run_orchestrator_sync()` 转发。`_debate_loop_core_async()` 与 `_run_single_task_with_debate_async()` 已落地。`threading.Lock` 未在 orchestrator 中出现（原有 `threading` import 仅用于 `threading.Lock` 在 `_execute_task_card` 的 patch 检测，不在 async 路径上）。

### [PASS] S5: store-cutover
默认 backend 已切换为 SQLite（`DefaultTaskStore`），`SWALLOW_STORE_BACKEND=file` 可强制回退。`swl migrate` 与 `swl doctor sqlite` 均已实现。迁移幂等性（`sqlite_has_state` 跳过）已验证。

---

## 二、架构原则一致性

### [PASS] Markdown Artifact 定位
`executor_output.md` 等 Artifact 继续生成，SQLite 仅承载 TaskState / EventLog，符合"导出视图而非真值"的设计边界。

### [PASS] Phase scope 未越界
未引入 `sqlite-vec`、知识库迁移、Web 层异步扩展等 Phase 49 内容。`[SCOPE WARNING]` 标注的 S4 传染性已通过分步实现控制在合理范围内。

### [PASS] 只读 Web API 零写入保护
`_connect_existing()` 使用 `file:...?mode=ro&immutable=1` URI，`PRAGMA query_only = ON`，严格保持只读语义。

---

## 三、测试覆盖

### [PASS] 新增测试文件覆盖核心路径
- `test_executor_async.py`：executor 异步桥接
- `test_review_gate_async.py`：并发 reviewer、超时、exception 路径
- `test_sqlite_store.py`：round-trip、WAL、fallback、migration
- `test_doctor.py`：SQLite health check
- `test_subtask_orchestrator.py`：AsyncSubtaskOrchestrator level-based 并发

### [PASS] 全量无回归
`378 passed, 7 deselected, 5 subtests passed`，较 Phase 47 基线（359 tests）净增 19 个测试。

---

## 四、CONCERN 项

### [CONCERN] C1: `_run_orchestrator_sync` 在事件循环内抛 RuntimeError，但 `run_task()` 的调用方无感知

**位置**: `orchestrator.py`，`_run_orchestrator_sync()`

**描述**: 当 `run_task()` 在已有事件循环的上下文中被调用（如 FastAPI handler、Jupyter、嵌套 asyncio），会抛出 `RuntimeError("run_task() cannot be used inside a running event loop")`。当前 Web API 路径（`web/api.py`）是否已全部切换为 `run_task_async()` 尚不明确；若有遗漏，operator 会看到不友好的 RuntimeError 而非明确的错误提示。

**建议**: 在 `web/api.py` 中确认所有调用点已使用 `run_task_async()`，或在 `_run_orchestrator_sync` 的 RuntimeError 消息中加入更明确的迁移指引。

**预期消化时机**: Phase 49 或下一次 Web 层改动时顺带确认。

---

### [CONCERN] C2: `DefaultTaskStore.iter_recent_task_events` 中 file store 的 `last_n` 参数放大可能导致性能问题

**位置**: `store.py`，`DefaultTaskStore.iter_recent_task_events()`

**描述**: 当 SQLite 已有部分结果时，file store 的查询参数被放大为 `max(last_n, len(recent_by_task_id) + last_n)`，在任务数量较多时会扫描大量文件系统条目，即使这些结果最终会被截断。这是过渡期双存储的固有代价，但在大型 `.swl/` 目录下可能引发性能退化。

**建议**: 在 `swl migrate` 完成后，operator 应尽快清理旧 JSON 文件以消除此路径的性能影响。可在 `swl doctor` 输出中添加"file-only tasks detected, consider running swl migrate"提示。

**预期消化时机**: Phase 49 或 store 过渡期结束后。

---

### [CONCERN] C3: `SqliteTaskStore._checkpoint()` 在每次 `save_state` 和 `append_event` 后都执行 WAL checkpoint，高频写入场景下可能成为性能瓶颈

**位置**: `sqlite_store.py`，`_checkpoint()`

**描述**: `PRAGMA wal_checkpoint(TRUNCATE)` 是一个相对重的操作，在 N-Reviewer 并发场景下每个 reviewer 完成后都会触发一次 checkpoint，可能抵消部分并发收益。当前测试场景规模较小，未暴露此问题。

**建议**: 考虑将 checkpoint 改为惰性触发（如每 N 次写入或在连接关闭时），或仅在 `swl doctor sqlite` 时手动触发。Phase 49 引入更高并发负载时需重新评估。

**预期消化时机**: Phase 49 性能调优阶段。

---

### [CONCERN] C4: `_run_subtask_orchestration_async` 中的 `_execute_task_card` patch 检测逻辑（`if _execute_task_card is _ORIGINAL_EXECUTE_TASK_CARD`）是测试耦合

**位置**: `orchestrator.py`，`run_task_async()` 中的 subtask 分支

**描述**: 通过比较函数引用来判断是否走 async subtask 路径，是一种测试 patch 感知逻辑，将测试基础设施的实现细节泄漏到生产代码中。这在当前过渡期可以接受，但长期会增加维护负担。

**建议**: Phase 49 完成 subtask 路径的完整异步化后，移除此 patch 检测分支，统一走 `_run_subtask_orchestration_async()`。

**预期消化时机**: Phase 49 subtask 路径完整异步化时。

---

## 五、Branch Advice

```
## Branch Advice

- 当前分支: feat/phase48_async-storage
- 建议操作: 开 PR
- 理由: 全量测试通过，无 BLOCK 项，4 个 CONCERN 均可延后消化
- 建议 PR 范围: S1–S5 全部 slice（7 commits）
```

---

## 六、Tag 评估

Phase 48 完成后建议打 `v0.6.0`（Async Era）。理由：
- 自 `v0.5.0` 以来有明确的用户可感知能力增量：N-Reviewer 并行执行、SQLite 事务存储、`swl migrate` 迁移工具
- 当前 main 处于稳定状态（全量测试通过）
- 4 个 CONCERN 均不影响公共 API 稳定性，不需要等待消化后再打 tag

建议在 merge 到 main 并确认 CI 通过后执行：`git tag -a v0.6.0 -m "Async Era: full async orchestration + SQLite state store"`
