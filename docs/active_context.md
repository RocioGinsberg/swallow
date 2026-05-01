# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `Architecture / Engineering`
- latest_completed_phase: `Provider Router Split / LTO-7 Step 1`
- latest_completed_slice: `Provider Router Maintainability`
- active_track: `Architecture / Engineering`
- active_phase: `Orchestration Lifecycle Decomposition / LTO-8 Step 1`
- active_slice: `M4 execution attempt helper extraction`
- active_branch: `feat/orchestration-lifecycle-decomposition`
- status: `m4_validation_passed_waiting_human_commit`

## 当前状态说明

当前 git 分支为 `feat/orchestration-lifecycle-decomposition`。LTO-7 Provider Router Split 已合并到 `main`:

- `6033558 Provider Router Maintainability`

`docs/roadmap.md` 已由 post-merge factual update 切到下一阶段 ticket:

- 当前 ticket: `Orchestration lifecycle decomposition`
- 对应长期目标: `LTO-8`
- 默认边界: task lifecycle / execution attempts / subtask flow / retrieval flow / knowledge flow helpers
- 硬边界: Control 权限不可转出 Orchestrator

Codex 已按最新 roadmap 起草并根据 plan audit 修订下一阶段计划:

- `docs/plans/orchestration-lifecycle-decomposition/plan.md`
- `docs/plans/orchestration-lifecycle-decomposition/plan_audit.md`

Plan audit 结论为 `has-blockers`，包含 1 个 BLOCKER 与 7 个 CONCERN。Codex 已吸收:

- 将 milestone 数量从 6 降到 5，把原 M6 closeout / PR gate 折进 M5 与 Completion Conditions。
- 明确禁止 helper module 以 import / call / closure / field 等任何形式接收或调用 `save_state`。
- 明确 `harness.py` 不在本 phase 迁移范围内。
- 将 target module 命名对齐 `CODE_ORGANIZATION.md §5`:`subtask_flow.py` / `artifact_writer.py`。
- 明确 helper 默认不得调用 `append_event`，如确需 helper-owned event append 必须先修订计划。
- 明确 M5 不移动 `_apply_librarian_side_effects(...)` 或任何直接 `apply_proposal` caller。

Human 已批准开始实现。M1 已完成并已由 Human 提交:

- `0c6545d refactor(orchestration): extract lifecycle payload helpers`

M1 范围保持为纯 lifecycle helper extraction:

- 新增 `src/swallow/orchestration/task_lifecycle.py`
- 新增 `tests/unit/orchestration/test_task_lifecycle_module.py`
- `orchestrator.py` 仍保留 `_set_phase(...)` / `_record_phase_checkpoint(...)` / `_append_phase_recovery_fallback(...)` 的 `save_state(...)` 与 `append_event(...)` 调用，只把 payload 构造委托给纯 helper。
- `task_lifecycle.py` 无 `save_state` / `append_event` / `orchestration.harness` / `orchestration.executor` 依赖命中。

Codex 已完成 M2 retrieval flow extraction:

- 目标模块: `src/swallow/orchestration/retrieval_flow.py`
- `orchestrator.py` 继续决定 retrieval skip / rerun 和 task advancement。
- 未移动 `harness.py` 中的 `run_retrieval(...)` / `run_retrieval_async(...)` execution。
- `retrieval_flow.py` 无 `save_state` / `append_event` / `orchestration.harness` / `orchestration.executor` 依赖命中。
- 新增 focused tests 覆盖 retrieval source policy、explicit override、previous retrieval artifact loading、selective retry invalid artifact fallback。
- M2 已由 Human 提交:
  - `e4d0539 refactor(orchestration): extract retrieval flow`

Codex 已完成 M3 artifact writer / subtask glue extraction:

- 目标模块: `src/swallow/orchestration/artifact_writer.py` 与 `src/swallow/orchestration/subtask_flow.py`
- 已抽取 artifact path map construction、小型 Orchestrator-side artifact copy helpers、窄范围 subtask attempt artifact serialization helpers。
- 不吸收 `harness.py` summary/resume/report builders。
- 不改变 `.swl/tasks/<task_id>/artifacts/*` 文件名。
- 新 helper 无 `save_state` / `append_event` / `orchestration.harness` / `orchestration.executor` 依赖命中。
- `orchestrator.py` 继续保留 task advancement、event append、subtask scheduling、fallback routing 决策。
- M3 已由 Human 提交:
  - `246aac3 refactor(orchestration): extract artifact writer and subtask glue`

Codex 已完成 M4 execution attempt helper extraction:

- 目标模块: `src/swallow/orchestration/execution_attempts.py`
- 已抽取 safe execution-attempt metadata helpers、budget exhausted executor / review-gate field builders、budget event type / payload builders、debate exhausted executor result builder。
- 已抽取 sync / async debate-loop core，但 executor invocation、review feedback construction、review gate decision consumption、event append、status transition sequencing 仍由 `orchestrator.py` 提供回调并持有。
- `orchestrator.py` 继续保留 executor invocation、review gate decision consumption、status transition sequencing、`save_state(...)` 与 `append_event(...)`。
- M4 helper 允许 append 的 event kind: none。`task.budget_exhausted` / `subtask.<n>.budget_exhausted` / `task.debate_round` / `task.debate_circuit_breaker` / `subtask.<n>.debate_round` / `subtask.<n>.debate_circuit_breaker` 均继续在 `orchestrator.py` 中 append。
- `execution_attempts.py` 无 `save_state` / `append_event` / `orchestration.harness` / `orchestration.executor` / `orchestration.review_gate` 依赖命中，避免通过 review gate runtime import 形成隐性 executor dependency。

## 当前关键文档

1. `docs/active_context.md`(本文)
2. `current_state.md`
3. `docs/roadmap.md`
4. `docs/plans/orchestration-lifecycle-decomposition/plan.md`
5. `docs/plans/orchestration-lifecycle-decomposition/plan_audit.md`
6. `docs/design/INVARIANTS.md`
7. `docs/design/ORCHESTRATION.md`
8. `docs/design/HARNESS.md`
9. `docs/design/DATA_MODEL.md`
10. `docs/engineering/CODE_ORGANIZATION.md`
11. `docs/engineering/TEST_ARCHITECTURE.md`
12. `docs/plans/provider-router-split/closeout.md`
13. `docs/plans/provider-router-split/review_comments.md`
14. `docs/concerns_backlog.md`

## 当前推进

已完成:

- **[Human]** Merged Provider Router Split into `main`:
  - `6033558 Provider Router Maintainability`
- **[roadmap-updater]** Updated `docs/roadmap.md` to mark LTO-7 done and advance the near-term queue to LTO-8.
- **[Codex]** Drafted LTO-8 plan:
  - `docs/plans/orchestration-lifecycle-decomposition/plan.md`
- **[Codex]** Synced post-merge recovery state:
  - `current_state.md`
  - `docs/active_context.md`
- **[Claude/design-auditor]** Produced LTO-8 plan audit:
  - `docs/plans/orchestration-lifecycle-decomposition/plan_audit.md`
  - result: 1 BLOCKER + 7 CONCERNs
- **[Codex]** Revised LTO-8 plan to absorb audit findings:
  - folded M6 into M5 / Completion Conditions
  - added no-`save_state` closure-injection rule
  - excluded `harness.py` migration from this phase
  - aligned target module names with `CODE_ORGANIZATION.md §5`
  - clarified `append_event` and `apply_proposal` boundaries
- **[Human]** Approved implementation start on `feat/orchestration-lifecycle-decomposition`.
- **[Codex]** M1 lifecycle helper extraction implemented:
  - added `src/swallow/orchestration/task_lifecycle.py` with pure phase event / checkpoint / recovery fallback payload builders
  - updated `src/swallow/orchestration/orchestrator.py` to use those payload builders while keeping state writes and event appends in Orchestrator
  - added `tests/unit/orchestration/test_task_lifecycle_module.py` for payload parity and no-control-plane-write-surface assertions
- **[Codex]** M1 validation passed:
  - `.venv/bin/python -m pytest tests/unit/orchestration -q` -> `4 passed`
  - `.venv/bin/python -m pytest tests/test_invariant_guards.py -q` -> `25 passed`
  - `.venv/bin/python -m compileall -q src/swallow/orchestration` -> passed
  - `git diff --check` -> passed
  - `rg -n "save_state|append_event|orchestration\.harness|orchestration\.executor" src/swallow/orchestration/task_lifecycle.py` -> no matches
- **[Human]** Committed M1:
  - `0c6545d refactor(orchestration): extract lifecycle payload helpers`
- **[Codex]** M2 retrieval flow extraction implemented:
  - added `src/swallow/orchestration/retrieval_flow.py` for retrieval request construction and previous retrieval artifact loading
  - updated `src/swallow/orchestration/orchestrator.py` to import the retrieval flow helpers while keeping retrieval skip / rerun decisions in Orchestrator
  - added `tests/unit/orchestration/test_retrieval_flow_module.py` for source policy, artifact loading, selective retry fallback, and boundary assertions
- **[Codex]** M2 validation passed:
  - `.venv/bin/python -m pytest tests/unit/orchestration -q` -> `13 passed`
  - `.venv/bin/python -m pytest tests/test_cli.py -k build_task_retrieval_request -q` -> `8 passed, 234 deselected, 5 subtests passed`
  - `.venv/bin/python -m pytest tests/test_cli.py -q` -> `242 passed, 10 subtests passed`
  - `.venv/bin/python -m pytest tests/test_invariant_guards.py -q` -> `25 passed`
  - `.venv/bin/python -m compileall -q src/swallow/orchestration` -> passed
  - `git diff --check` -> passed
  - `git diff --check --no-index /dev/null src/swallow/orchestration/retrieval_flow.py` -> no whitespace warnings
  - `git diff --check --no-index /dev/null tests/unit/orchestration/test_retrieval_flow_module.py` -> no whitespace warnings
  - `rg -n "save_state|append_event|orchestration\.harness|orchestration\.executor" src/swallow/orchestration/retrieval_flow.py` -> no matches
- **[Human]** Committed M2:
  - `e4d0539 refactor(orchestration): extract retrieval flow`
- **[Codex]** M3 artifact writer / subtask glue extraction implemented:
  - added `src/swallow/orchestration/artifact_writer.py` for initial/run artifact path maps, parent executor artifact writing, and prefixed executor artifact copies
  - added `src/swallow/orchestration/subtask_flow.py` for subtask attempt artifact writes, extra artifact collection, and subtask artifact refs
  - updated `src/swallow/orchestration/orchestrator.py` to delegate those helper surfaces while keeping state writes, events, routing, and scheduling in Orchestrator
  - added focused tests for artifact path stability, artifact filename preservation, subtask attempt artifacts, and helper boundary assertions
- **[Codex]** M3 validation passed:
  - `.venv/bin/python -m pytest tests/unit/orchestration -q` -> `22 passed`
  - `.venv/bin/python -m pytest tests/test_run_task_subtasks.py tests/test_subtask_orchestrator.py tests/test_review_gate.py -q` -> `27 passed`
  - `.venv/bin/python -m pytest tests/test_web_api.py -q` -> `10 passed`
  - `.venv/bin/python -m pytest tests/test_cli.py -q` -> `242 passed, 10 subtests passed`
  - `.venv/bin/python -m pytest tests/test_consistency_audit.py -q` -> `11 passed`
  - `.venv/bin/python -m pytest tests/test_invariant_guards.py -q` -> `25 passed`
  - `.venv/bin/python -m compileall -q src/swallow` -> passed
  - `git diff --check` -> passed
  - `git diff --check --no-index /dev/null <new M3 files>` -> no whitespace warnings
  - `rg -n "save_state|append_event|orchestration\.harness|orchestration\.executor" src/swallow/orchestration/artifact_writer.py src/swallow/orchestration/subtask_flow.py` -> no matches
- **[Human]** Committed M3:
  - `246aac3 refactor(orchestration): extract artifact writer and subtask glue`
- **[Codex]** M4 execution attempt helper extraction implemented:
  - added `src/swallow/orchestration/execution_attempts.py` for attempt metadata, budget exhausted result/event payload builders, and generic sync / async debate-loop core
  - updated `src/swallow/orchestration/orchestrator.py` to delegate those helper surfaces while keeping executor invocation, review gate integration, `save_state(...)`, and `append_event(...)` in Orchestrator
  - added `tests/unit/orchestration/test_execution_attempts_module.py` for metadata/budget/debate behavior and helper boundary assertions
  - M4 helper event append allowlist: none
- **[Codex]** M4 validation passed:
  - `.venv/bin/python -m pytest tests/unit/orchestration -q` -> `31 passed`
  - `.venv/bin/python -m pytest tests/test_run_task_subtasks.py tests/test_subtask_orchestrator.py tests/test_review_gate.py -q` -> `27 passed`
  - `.venv/bin/python -m pytest tests/test_review_gate_async.py -q` -> `2 passed`
  - `.venv/bin/python -m pytest tests/test_web_api.py -q` -> `10 passed`
  - `.venv/bin/python -m pytest tests/test_consistency_audit.py -q` -> `11 passed`
  - `.venv/bin/python -m pytest tests/test_invariant_guards.py -q` -> `25 passed`
  - `.venv/bin/python -m pytest tests/test_cli.py -q` -> `242 passed, 10 subtests passed`
  - `.venv/bin/python -m compileall -q src/swallow` -> passed
  - `git diff --check` -> passed
  - `git diff --check --no-index /dev/null <new M4 files>` -> no whitespace warnings
  - `rg -n "save_state|append_event|orchestration\.harness|orchestration\.executor|orchestration\.review_gate" src/swallow/orchestration/execution_attempts.py` -> no matches
  - runtime import audit for `execution_attempts.py` -> `orchestration.executor`, `orchestration.harness`, and `orchestration.review_gate` not loaded

进行中:

- None. M4 is waiting for Human review / commit.

待执行:

- **[Human]** Review and commit M4 if accepted.
- **[Codex]** After M4 commit is confirmed, begin M5 knowledge-flow / facade cleanup per plan.

当前阻塞项:

- 等待人工审批: review and commit M4.

## Tag 状态

- 最新已执行 tag: `v1.5.0`
- tag target: `bc8abb1 docs(release): sync v1.5.0 release docs`
- tag message: `v1.5.0: raw material store boundary`
- 当前结论: 不为 LTO-7 单独打 tag;等 Cluster-C subtracks 形成更完整能力边界后再评估。

## 当前下一步

1. **[Human]** Review M4 changes and commit if accepted.
2. **[Codex]** After Human confirms the M4 commit, continue to M5 knowledge-flow / facade cleanup per plan.

```markdown
milestone_gate:
- current: lto8-m4-validation-passed-waiting-human-commit
- active_branch: feat/orchestration-lifecycle-decomposition
- latest_main_checkpoint: 6033558 Provider Router Maintainability
- active_track: Architecture / Engineering
- active_phase: Orchestration Lifecycle Decomposition / LTO-8 Step 1
- active_slice: M4 execution attempt helper extraction
- plan: docs/plans/orchestration-lifecycle-decomposition/plan.md (revised after audit)
- plan_audit: docs/plans/orchestration-lifecycle-decomposition/plan_audit.md (1 BLOCKER + 7 CONCERNs)
- audit_absorbed: milestone count, save_state closure ban, harness scope, module naming, append_event boundary, apply_proposal movement boundary
- roadmap: docs/roadmap.md current ticket Orchestration lifecycle decomposition
- recommended_implementation_branch: feat/orchestration-lifecycle-decomposition
- m1_outputs: task_lifecycle.py pure payload helpers, orchestrator.py payload delegation, tests/unit/orchestration/test_task_lifecycle_module.py
- m1_validation: unit orchestration `4 passed`; invariant guards `25 passed`; compileall orchestration passed; git diff --check passed; task_lifecycle forbidden dependency grep no matches
- m1_commit: 0c6545d refactor(orchestration): extract lifecycle payload helpers
- m2_outputs: retrieval_flow.py request/loading helpers, orchestrator.py facade import and loader call, tests/unit/orchestration/test_retrieval_flow_module.py
- m2_validation: unit orchestration `13 passed`; CLI retrieval request focused `8 passed`; full CLI `242 passed`; invariant guards `25 passed`; compileall orchestration passed; git diff --check passed; retrieval_flow forbidden dependency grep no matches
- m2_commit: e4d0539 refactor(orchestration): extract retrieval flow
- m3_outputs: artifact_writer.py artifact path/copy helpers, subtask_flow.py subtask attempt artifact helpers, orchestrator.py helper delegation, focused unit tests
- m3_validation: unit orchestration `22 passed`; subtask/review regression `27 passed`; Web API `10 passed`; full CLI `242 passed`; consistency audit `11 passed`; invariant guards `25 passed`; compileall src/swallow passed; git diff --check passed; M3 helper forbidden dependency grep no matches
- m3_commit: 246aac3 refactor(orchestration): extract artifact writer and subtask glue
- m4_outputs: execution_attempts.py metadata/budget/debate helpers, orchestrator.py helper delegation while retaining executor/review/status/event ownership, tests/unit/orchestration/test_execution_attempts_module.py
- m4_event_append_allowlist: none; M4 helper appends no events
- m4_validation: unit orchestration `31 passed`; subtask/review regression `27 passed`; review gate async `2 passed`; Web API `10 passed`; consistency audit `11 passed`; invariant guards `25 passed`; full CLI `242 passed, 10 subtests passed`; compileall src/swallow passed; git diff --check passed; execution_attempts forbidden dependency grep/runtime import audit no matches
- next_gate: Human M4 review / commit
```

## 当前产出物

- `docs/roadmap.md`(roadmap-updater, 2026-05-01, LTO-7 complete and LTO-8 current ticket)
- `docs/plans/orchestration-lifecycle-decomposition/plan.md`(codex, 2026-05-01, LTO-8 Step 1 plan revised after audit)
- `docs/plans/orchestration-lifecycle-decomposition/plan_audit.md`(claude, 2026-05-01, 1 BLOCKER + 7 CONCERNs)
- `src/swallow/orchestration/task_lifecycle.py`(codex, 2026-05-01, pure lifecycle payload builders)
- `src/swallow/orchestration/orchestrator.py`(codex, 2026-05-01, M1 payload builder delegation while retaining state/event writes)
- `tests/unit/orchestration/test_task_lifecycle_module.py`(codex, 2026-05-01, lifecycle payload parity and boundary tests)
- `src/swallow/orchestration/retrieval_flow.py`(codex, 2026-05-01, retrieval request construction and previous retrieval artifact loading)
- `tests/unit/orchestration/test_retrieval_flow_module.py`(codex, 2026-05-01, retrieval flow policy, selective retry fallback, and boundary tests)
- `src/swallow/orchestration/artifact_writer.py`(codex, 2026-05-02, artifact path maps and executor artifact copy/write helpers)
- `src/swallow/orchestration/subtask_flow.py`(codex, 2026-05-02, subtask attempt artifact write/collect/ref helpers)
- `tests/unit/orchestration/test_artifact_writer_module.py`(codex, 2026-05-02, artifact writer path/file/boundary tests)
- `tests/unit/orchestration/test_subtask_flow_module.py`(codex, 2026-05-02, subtask artifact serialization and boundary tests)
- `src/swallow/orchestration/execution_attempts.py`(codex, 2026-05-02, execution attempt metadata, budget, and debate-loop helper extraction)
- `tests/unit/orchestration/test_execution_attempts_module.py`(codex, 2026-05-02, execution attempt helper behavior and boundary tests)
- `current_state.md`(codex, 2026-05-01, post-merge recovery state for LTO-7 / LTO-8 planning gate)
- `docs/active_context.md`(codex, 2026-05-02, active phase switched to LTO-8 M4 review / commit gate)
