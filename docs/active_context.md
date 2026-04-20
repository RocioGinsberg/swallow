# Active Context

## 当前轮次

- latest_completed_track: `Evaluation / Policy` (Primary) + `Core Loop` (Secondary)
- latest_completed_phase: `Phase 47`
- latest_completed_slice: `Consensus & Policy Guardrails (v0.5.0)`
- active_track: `Core Loop` (Primary) + `State / Truth` (Secondary)
- active_phase: `Phase 48`
- active_slice: `phase48_s2_async_review_gate_completed`
- active_branch: `feat/phase48_async-storage`
- status: `phase48_s1_s2_validated_ready_for_split_commits`

---

## 当前状态说明

Phase 47 已正式收口并打标 `v0.5.0`。当前 `main` 分支已吸收多模型共识门禁、成本护栏及一致性审计等关键能力。

根据 `docs/roadmap.md`，Phase 48 的重点转向 **“存储引擎升级与全异步改造”**。Human 已通过本轮对话授权开始实现，当前已在 `feat/phase48_async-storage` 上完成前两个 slice 的最小闭环：S1（`async-executor`）为 executor 协议补齐 `execute_async()`、`run_executor_async()`、`run_prompt_executor_async()` 与异步 HTTP fallback 路径；S2（`async-review-gate`）为 ReviewGate 新增 `run_review_gate_async()` / `run_consensus_review_async()`，将多 Reviewer 审查改为 `asyncio.gather(..., return_exceptions=True)` 并发执行，并引入 `reviewer_timeout_seconds` TaskCard 配置以约束单路 reviewer 超时。当前工作树尚未按 slice 提交，Human 应先按 S1 / S2 路径拆分提交。

---

## 当前关键文档

当前进入 Phase 48 S2 审查前，优先读取：

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

待启动：

- **[Human]** 审查并按 slice 拆分提交当前 S1 / S2 diff。
- **[Codex]** S1 / S2 提交完成后继续进入 S3（`sqlite-schema`）。

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
- `tests/test_executor_async.py` (codex, 2026-04-20)
- `tests/test_review_gate_async.py` (codex, 2026-04-20)
- `pyproject.toml` (codex, 2026-04-20)

## 当前下一步

1. Human 先按路径拆分当前 diff，提交 S1（`async-executor`）实现。
2. Human 再提交 S2（`async-review-gate`）实现。
3. Codex 基于已提交的 S1 / S2 继续推进 S3（`sqlite-schema`）。

当前阻塞项：

- 无硬阻塞；当前等待 Human 将工作树按 slice 拆分提交。
