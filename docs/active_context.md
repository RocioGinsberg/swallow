# Active Context

## 当前轮次

- latest_completed_track: `Evaluation / Policy` (Primary) + `Core Loop` (Secondary)
- latest_completed_phase: `Phase 47`
- latest_completed_slice: `Consensus & Policy Guardrails (v0.5.0)`
- active_track: `Core Loop` (Primary) + `State / Truth` (Secondary)
- active_phase: `Phase 48`
- active_slice: `phase48_s4_async_orchestrator_completed`
- active_branch: `feat/phase48_async-storage`
- status: `phase48_s4_validated_ready_for_human_commit`

---

## 当前状态说明

Phase 47 已正式收口并打标 `v0.5.0`。当前 `main` 分支已吸收多模型共识门禁、成本护栏及一致性审计等关键能力。

根据 `docs/roadmap.md`，Phase 48 的重点转向 **“存储引擎升级与全异步改造”**。当前 `feat/phase48_async-storage` 已完成前四个 slice 的最小闭环：S1（`async-executor`）补齐 executor 异步桥接与异步 HTTP fallback；S2（`async-review-gate`）将多 Reviewer 审查切为 `asyncio.gather(..., return_exceptions=True)` 并发执行；S3（`sqlite-schema`）新增 `SqliteTaskStore`、`TaskStoreProtocol` / `FileTaskStore` 双存储分派、`.swl/swallow.db` 路径与 `SWALLOW_STORE_BACKEND=sqlite|file` 切换，并将 CLI / Web API / Meta-Optimizer / execution budget policy 的 state/event 读取改为统一走 store helper；S4（`async-orchestrator`）补齐 `run_task_async()`、async debate loop / async subtask orchestrator 基础能力、CLI 生命周期兼容壳与事件循环内运行路径。当前工作树为 S4 已验证未提交状态，下一步进入 Human 审查与 S5 gate 判断。

---

## 当前关键文档

当前进入 Phase 48 S3 审查前，优先读取：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/roadmap.md`
4. `docs/plans/phase48/kickoff.md`
5. `docs/plans/phase48/design_decision.md`

仅在需要时再读取：

- `docs/plans/phase48/context_brief.md`
- `docs/plans/phase48/risk_assessment.md`
- `current_state.md`
- `docs/plans/phase47/closeout.md`
- `docs/architecture_principles.md`
- `docs/design/STATE_AND_TRUTH_DESIGN.md`

---

## 当前推进

已完成：

- **[Human]** 完成 Phase 47 merge 并打 tag `v0.5.0`。
- **[Gemini]** 更新 `docs/roadmap.md`，将 Phase 47 移入已消化差距，确认 Phase 48 方向。
- **[Gemini]** 产出 `docs/plans/phase48/context_brief.md`。
- **[Claude]** 已产出 `docs/plans/phase48/kickoff.md`、`design_decision.md`、`risk_assessment.md`。
- **[Human]** 已通过当前对话授权开始 Phase 48 实现。
- **[Human]** 已完成前三次提交：
  - `docs(phase48): add kickoff decision and roadmap sync`
  - `feat(async): add executor async bridge and http async path`
  - `feat(async): parallelize review gate execution`
- **[Codex]** 已完成 S3 提交：
  - `feat(store): add sqlite task and event backend` (`b7eb4b4`)
- **[Codex]** 已完成 S1（`async-executor`）：
  - `ExecutorProtocol` 新增 `execute_async()` 过渡接口
  - `LocalCLIExecutor` / `MockExecutor` / `HTTPExecutor` / `CLIAgentExecutor` / `LibrarianExecutor` 均支持异步桥接
  - 新增 `run_executor_async()` / `run_executor_inline_async()` / `run_prompt_executor_async()`
  - 新增 `run_http_executor_async()` 与异步 executor-level fallback 路径
  - `pyproject.toml` 新增 `pytest-asyncio` 的 `dev` 依赖声明
- **[Codex]** 已完成 S2（`async-review-gate`）：
  - `review_gate.py` 新增 `run_review_gate_async()` / `run_consensus_review_async()`
  - N-Reviewer 审查改为 `asyncio.gather(..., return_exceptions=True)` 并发执行
  - 单 reviewer 调用增加 `asyncio.wait_for(...)` 超时保护，超时视为 failed reviewer，不中断其他 reviewer
  - `TaskCard` / planner / `create_task()` 新增 `reviewer_timeout_seconds` 配置透传
  - 同步 `run_review_gate()` 保留为兼容包装层，供现有同步 orchestrator 路径继续调用
- **[Codex]** 已完成 S1 定向验证：
  - `.venv/bin/python -m pytest tests/test_executor_protocol.py tests/test_executor_async.py --tb=short` → `20 passed`
  - `.venv/bin/python -m pytest tests/test_review_gate.py tests/test_consistency_audit.py tests/test_debate_loop.py tests/test_run_task_subtasks.py --tb=short` → `26 passed`
  - `.venv/bin/python -m pytest tests/test_librarian_executor.py --tb=short` → `3 passed`
- **[Codex]** 已完成 S2 定向验证：
  - `.venv/bin/python -m pytest tests/test_review_gate.py tests/test_review_gate_async.py tests/test_planner.py tests/test_debate_loop.py --tb=short -q` → `25 passed`
  - `.venv/bin/python -m pytest tests/test_executor_async.py tests/test_executor_protocol.py --tb=short -vv` → `20 passed`
  - `.venv/bin/python -m pytest tests/eval/test_consensus_eval.py -m eval --tb=short -q` → `3 passed`
  - `.venv/bin/python -m pytest tests/test_run_task_subtasks.py tests/test_librarian_executor.py tests/test_consistency_audit.py --tb=short -vv` → `12 passed`
- **[Codex]** 已完成 S3（`sqlite-schema`）：
  - 新增 `src/swallow/sqlite_store.py`，以 SQLite WAL 模式持久化 `TaskState` / `EventLog`
  - `src/swallow/store.py` 抽出 `TaskStoreProtocol` / `FileTaskStore`，新增 `load_events()` / `iter_recent_task_events()` helper
  - `src/swallow/paths.py` 新增 `.swl/swallow.db` 路径
  - `src/swallow/execution_budget_policy.py` / `src/swallow/cli.py` / `src/swallow/web/api.py` / `src/swallow/meta_optimizer.py` 改为通过 store helper 读取 state/events
  - 新增 `tests/test_sqlite_store.py`，覆盖 sqlite round-trip、event-only 兼容和 sqlite backend 下的 create/run/read 集成链路
- **[Codex]** 已完成 S3 定向验证：
  - `.venv/bin/python -m pytest tests/test_sqlite_store.py tests/test_execution_budget_policy.py tests/test_web_api.py tests/test_meta_optimizer.py --tb=short -q` → `21 passed`
  - `.venv/bin/python -m pytest tests/test_debate_loop.py tests/test_run_task_subtasks.py tests/test_librarian_executor.py tests/test_consistency_audit.py --tb=short -q` → `16 passed`
  - `.venv/bin/python -m pytest tests/test_cli.py -k 'task_list or task_queue or task_inspect' --tb=short -q` → `17 passed, 179 deselected`
- **[Codex]** 已完成 S4（`async-orchestrator`）：
  - `orchestrator.py` 新增 `run_task_async()`、`_run_orchestrator_sync()`、async debate loop / single-task debate / subtask retry 基础链路
  - `run_task()` 保留为兼容包装层，在同步调用面上转发到 async orchestrator
  - `subtask_orchestrator.py` 新增 `AsyncSubtaskOrchestrator`，补齐 level-based `asyncio.gather()` 并发执行能力
  - `harness.py` 新增 async bridge API，供后续切换点继续复用
  - 生命周期入口保持兼容：CLI 仍通过 `run_task()` seam 进入，但实际执行主链路已由 `run_task_async()` 承接
  - 为避免 runtime 在 worker-thread 桥接上的不稳定点，当前收口策略为：retrieval / artifact persistence 直接同步调用，真实多子任务路径仍复用已验证的同步 `SubtaskOrchestrator` 并以 worker-thread 包裹；测试 patch 路径与事件循环内 `run_task_async()` 已打通
- **[Codex]** 已完成 S4 定向验证：
  - `.venv/bin/python -m pytest tests/test_subtask_orchestrator.py tests/test_debate_loop.py tests/test_run_task_subtasks.py tests/test_binary_fallback.py --tb=short -q` → `18 passed`
  - `.venv/bin/python -m pytest tests/test_cli.py -k 'task_run or task_resume or task_rerun' --tb=short -q` → `6 passed, 190 deselected`
  - `.venv/bin/python -m pytest tests/test_sqlite_store.py tests/test_web_api.py --tb=short -q` → `13 passed`

待启动：

- **[Human]** 审查并提交当前 S4（`async-orchestrator`）diff。
- **[Human]** 决定是否对 S5（`store-cutover`）开启新的实现 gate。

## 当前产出物

- `docs/plans/phase48/context_brief.md` (gemini, 2026-04-20)
- `docs/roadmap.md` (gemini, 2026-04-20)
- `docs/plans/phase48/kickoff.md` (claude, 2026-04-20)
- `docs/plans/phase48/design_decision.md` (claude, 2026-04-20)
- `docs/plans/phase48/risk_assessment.md` (claude, 2026-04-20)
- `src/swallow/executor.py` (codex, 2026-04-20)
- `src/swallow/librarian_executor.py` (codex, 2026-04-20)
- `src/swallow/review_gate.py` (codex, 2026-04-20)
- `src/swallow/models.py` (codex, 2026-04-20)
- `src/swallow/planner.py` (codex, 2026-04-20)
- `src/swallow/orchestrator.py` (codex, 2026-04-20)
- `src/swallow/store.py` (codex, 2026-04-20)
- `src/swallow/sqlite_store.py` (codex, 2026-04-20)
- `src/swallow/paths.py` (codex, 2026-04-20)
- `tests/test_executor_async.py` (codex, 2026-04-20)
- `tests/test_review_gate_async.py` (codex, 2026-04-20)
- `tests/test_sqlite_store.py` (codex, 2026-04-20)
- `tests/test_subtask_orchestrator.py` (codex, 2026-04-20)
- `tests/test_debate_loop.py` (codex, 2026-04-20)
- `pyproject.toml` (codex, 2026-04-20)

## 当前下一步

1. Human 审查并提交当前 S4（`async-orchestrator`）实现。
2. Human 基于 S4 收口结果决定是否启动 S5（`store-cutover`）。
3. 如启动 S5，Codex 继续推进 SQLite 默认切换、迁移命令与 doctor 检查补齐。

当前阻塞项：

- 无硬阻塞；当前等待 Human 审查并提交 S4 diff / 决定是否开启 S5。
