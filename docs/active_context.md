# Active Context

## 当前轮次

- latest_completed_track: `Evaluation / Policy` (Primary) + `Core Loop` (Secondary)
- latest_completed_phase: `Phase 47`
- latest_completed_slice: `Consensus & Policy Guardrails (v0.5.0)`
- active_track: `Core Loop` (Primary) + `State / Truth` (Secondary)
- active_phase: `Phase 48`
- active_slice: `phase48_review_followups_absorbed`
- active_branch: `feat/phase48_async-storage`
- status: `phase48_review_followups_validated_ready_for_human_commit`

---

## 当前状态说明

Phase 47 已正式收口并打标 `v0.5.0`。当前 `main` 分支已吸收多模型共识门禁、成本护栏及一致性审计等关键能力。

根据 `docs/roadmap.md`，Phase 48 的重点转向 **“存储引擎升级与全异步改造”**。当前 `feat/phase48_async-storage` 已完成五个 slice 的实现与提交：S1（`async-executor`）补齐 executor 异步桥接与异步 HTTP fallback；S2（`async-review-gate`）将多 Reviewer 审查切为 `asyncio.gather(..., return_exceptions=True)` 并发执行；S3（`sqlite-schema`）新增 `SqliteTaskStore`、`TaskStoreProtocol` / `FileTaskStore` 双存储分派、`.swl/swallow.db` 路径与 `SWALLOW_STORE_BACKEND=sqlite|file` 切换，并将 CLI / Web API / Meta-Optimizer / execution budget policy 的 state/event 读取改为统一走 store helper；S4（`async-orchestrator`）补齐 `run_task_async()`、async debate loop / async subtask orchestrator 基础能力、CLI 生命周期兼容壳与事件循环内运行路径；S5（`store-cutover`）将默认 store backend 切换为 SQLite，引入 sqlite primary + file mirror/fallback 的过渡实现，补齐 `swl migrate` 与 `swl doctor sqlite`，并让默认 `swl doctor` 输出包含 SQLite 健康检查。Claude review 已完成；当前分支继续吸收了 4 个 non-blocking concern，并完成定向回归验证，现处于 review follow-up 已验证、等待 Human 审查并提交收口补丁的阶段。

---

## 当前关键文档

当前进入 Phase 48 review follow-up 收口前，优先读取：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/plans/phase48/review_comments.md`
4. `docs/plans/phase48/commit_summary.md`
5. `docs/concerns_backlog.md`
6. `pr.md`

仅在需要时再读取：

- `docs/plans/phase48/design_decision.md`
- `docs/plans/phase48/risk_assessment.md`
- `docs/roadmap.md`
- `docs/plans/phase48/kickoff.md`
- `docs/plans/phase48/context_brief.md`
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
- **[Human]** 当前分支已有提交：
  - `docs(phase48): add kickoff decision and roadmap sync`
  - `feat(async): add executor async bridge and http async path`
  - `feat(async): parallelize review gate execution`
  - `feat(store): add sqlite task and event backend` (`b7eb4b4`)
  - `feat(async): add orchestrator async runtime path` (`6c36925`)
  - `test(phase47):add orchestrator async runtime path` (`2a91bec`)
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
- **[Codex]** 已完成 S5（`store-cutover`）：
  - `src/swallow/store.py` 将默认 backend 切换为 SQLite，并新增 `DefaultTaskStore` 作为 sqlite primary + file mirror/fallback 过渡层
  - `src/swallow/store.py` 新增 `migrate_file_tasks_to_sqlite()`，支持 legacy file task → SQLite 回填与 `--dry-run`
  - `src/swallow/sqlite_store.py` 补齐 task/event existence、count 与 database health helper，避免 `swl migrate --dry-run` 意外建库
  - `src/swallow/doctor.py` 新增 SQLite doctor result / formatter / diagnose 流程
  - `src/swallow/cli.py` 新增 `swl migrate`、`swl doctor sqlite`，并将默认 `swl doctor` 扩展为 codex + sqlite + stack 三段输出
  - `tests/test_sqlite_store.py` / `tests/test_doctor.py` / `tests/test_cli.py` 补齐默认 backend、legacy fallback、migration dry-run / idempotent、doctor sqlite 与 CLI 迁移路径覆盖
- **[Codex]** 已完成 S5 定向验证：
  - `pytest -q tests/test_sqlite_store.py tests/test_doctor.py tests/test_cli.py` → `211 passed, 5 subtests passed`
  - `pytest -q tests/test_web_api.py tests/test_execution_budget_policy.py tests/test_meta_optimizer.py tests/test_run_task_subtasks.py tests/test_debate_loop.py` → `27 passed`
- **[Human]** 已完成 S5 提交：
  - `feat(store): cut over default sqlite storage` (`11cef98`)
- **[Codex]** 已完成 review handoff 准备：
  - 新增 `docs/plans/phase48/commit_summary.md`，汇总实现边界、验证结果与建议 review 焦点
  - 根目录 `pr.md` 已切换为 Phase 48 预审稿，待 Claude review 结果回填 Review 节
- **[Claude]** 已完成 Phase 48 review：
  - `docs/plans/phase48/review_comments.md` 结论为 `0 BLOCK / 4 CONCERN / PR ready`
  - `docs/concerns_backlog.md` 已登记 Phase 48 concern
- **[Codex]** 已吸收 Phase 48 review concern：
  - C1：`run_task()` 在事件循环内的报错改为明确指向 `await run_task_async(...)`
  - C2：`DefaultTaskStore.iter_recent_task_events()` 改为只读取 file-only task 的事件文件；`swl doctor sqlite` 新增迁移建议
  - C3：`SqliteTaskStore._checkpoint()` 从 `wal_checkpoint(TRUNCATE)` 调整为 `wal_checkpoint(PASSIVE)`
  - C4：删除 `_execute_task_card is _ORIGINAL_EXECUTE_TASK_CARD` patch 检测分支，统一走 async subtask orchestration
- **[Codex]** 已完成 review follow-up 定向验证：
  - `pytest -q tests/test_sqlite_store.py tests/test_doctor.py tests/test_run_task_subtasks.py` → `18 passed`
  - `pytest -q tests/test_cli.py tests/test_web_api.py tests/test_meta_optimizer.py tests/test_debate_loop.py tests/test_execution_budget_policy.py` → `222 passed, 5 subtests passed`
  - `pytest -q tests/test_subtask_orchestrator.py tests/test_review_gate_async.py` → `8 passed`

待执行：

- **[Human]** 审查并提交当前 review follow-up diff（active_context / concerns_backlog / commit_summary + concern absorption patch）。
- **[Human]** 基于已吸收 concern 的 branch、`review_comments.md` 与 `pr.md` 决定是否进入 merge gate。
- **[Human]** merge 后打 tag `v0.6.0`（Claude 建议：可打）；届时 **[Codex]** 再同步 README / AGENTS.md。

## 当前产出物

- `docs/plans/phase48/context_brief.md` (gemini, 2026-04-20)
- `docs/roadmap.md` (gemini, 2026-04-20)
- `docs/plans/phase48/kickoff.md` (claude, 2026-04-20)
- `docs/plans/phase48/design_decision.md` (claude, 2026-04-20)
- `docs/plans/phase48/risk_assessment.md` (claude, 2026-04-20)
- `docs/plans/phase48/commit_summary.md` (codex, 2026-04-21)
- `docs/plans/phase48/review_comments.md` (claude, 2026-04-21)
- `docs/concerns_backlog.md` (claude/codex, 2026-04-21, Phase 48 concern 已登记并吸收)
- `src/swallow/executor.py` (codex, 2026-04-20)
- `src/swallow/librarian_executor.py` (codex, 2026-04-20)
- `src/swallow/review_gate.py` (codex, 2026-04-20)
- `src/swallow/models.py` (codex, 2026-04-20)
- `src/swallow/planner.py` (codex, 2026-04-20)
- `src/swallow/orchestrator.py` (codex, 2026-04-20)
- `src/swallow/cli.py` (codex, 2026-04-21)
- `src/swallow/doctor.py` (codex, 2026-04-21)
- `src/swallow/store.py` (codex, 2026-04-21)
- `src/swallow/sqlite_store.py` (codex, 2026-04-21)
- `src/swallow/paths.py` (codex, 2026-04-20)
- `tests/test_cli.py` (codex, 2026-04-21)
- `tests/test_doctor.py` (codex, 2026-04-21)
- `tests/test_executor_async.py` (codex, 2026-04-20)
- `tests/test_review_gate_async.py` (codex, 2026-04-20)
- `tests/test_sqlite_store.py` (codex, 2026-04-21)
- `tests/test_subtask_orchestrator.py` (codex, 2026-04-20)
- `tests/test_debate_loop.py` (codex, 2026-04-20)
- `pyproject.toml` (codex, 2026-04-20)
- `pr.md` (codex, 2026-04-21)

## 当前下一步

1. Human 审查并提交当前 review follow-up diff。
2. Human 基于已吸收 concern 的 branch、`review_comments.md` 与 `pr.md` 决定是否直接进入 merge gate。
3. merge 到 main 后打 `v0.6.0`，再由 Codex 同步 README / AGENTS.md。

当前阻塞项：

- 无硬阻塞；当前等待 Human 审查并提交 review follow-up diff。
