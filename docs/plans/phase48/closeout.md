---
author: codex
phase: 48
slice: closeout
status: final
depends_on:
  - docs/plans/phase48/kickoff.md
  - docs/plans/phase48/design_decision.md
  - docs/plans/phase48/risk_assessment.md
  - docs/plans/phase48/review_comments.md
  - docs/active_context.md
---

## TL;DR
Phase 48 已完成 5 个实现 slice、4 个 review concern 吸收、test harness 收口与全量 pytest/eval 复验，当前状态为 **closeout final / ready for human merge gate**。本轮把系统推进到 `v0.6.0` 候选基线：`run_task_async()`、并发 `ReviewGate`、`AsyncSubtaskOrchestrator`、SQLite 默认 store、`swl migrate` 与 `swl doctor sqlite` 均已落地。当前分支最新提交为 `6f4106d fix(test): runtime guard async to normal test case`，工作树干净。

# Phase 48 Closeout

## 结论

Phase 48 `Storage & Async Engine` 已在 `feat/phase48_async-storage` 上完成实现、review concern 吸收、验证复验与 closeout 文档整理，当前可以进入 Human merge gate。

本轮围绕 kickoff 定义的五个目标，完成了两条主线的合流：

- async 主线：`execute_async()`、`run_review_gate_async()`、`run_task_async()` 与 `AsyncSubtaskOrchestrator`
- state/store 主线：`SqliteTaskStore`、SQLite 默认后端、legacy file mirror/fallback、`swl migrate`、`swl doctor sqlite`

当前 branch 的 phase 提交序列如下：

- `ccf919c docs(phase48): add kickoff decision and roadmap sync`
- `00bd9d2 feat(async): add executor async bridge and http async path`
- `6b8aadb feat(async): parallelize review gate execution`
- `b7eb4b4 feat(store): add sqlite task and event backend`
- `6c36925 feat(async): add orchestrator async runtime path`
- `2a91bec test(phase47):add orchestrator async runtime path`
- `11cef98 feat(store): cut over default sqlite storage`
- `ba37f7a fix(review): absorb phase48 review followups`
- `350dcbe docs(phase48): sync review followup status`
- `6f4106d fix(test): runtime guard async to normal test case`

## 与 kickoff 完成条件对照

### 已完成

- 5 个 slice 已全部完成，并已分别落账到 branch commit history。
- 非 eval 全量 pytest 已通过；当前基线为 `380 selected / 7 deselected`，无失败。
- eval suite 已通过；当前基线为 `7 passed, 380 deselected`。
- SQLite backend 下的 create/run/read 集成链路已由 `tests/test_sqlite_store.py`、`tests/test_cli.py`、`tests/test_run_task_subtasks.py` 覆盖。
- N-Reviewer 并发执行语义已由 `tests/test_review_gate_async.py` 覆盖，closeout 以测试验收为准。
- `docs/plans/phase48/closeout.md`、`docs/active_context.md`、`current_state.md` 已同步到本轮 closeout 状态。

### 明确保留的说明

- kickoff 中关于独立并发 benchmark artifact 的要求，本轮没有额外沉淀独立性能报告；当前以 async test 与回归验证作为验收依据。
- `current_state.md` 已切到“Phase 48 closeout 候选分支”的恢复入口，但 `latest_completed_phase` 仍保持 Phase 47，因为 `main` 尚未吸收本轮成果。

## 已完成范围

### S1: async-executor

- `ExecutorProtocol` 新增 `execute_async()` 过渡接口。
- `HTTPExecutor` 打通异步主路径，CLI / mock / librarian 执行器均保留兼容桥接。
- 新增 async executor helper 与对应测试，`pytest-asyncio` 开发依赖已落地。

### S2: async-review-gate

- `run_review_gate_async()` 与 `run_consensus_review_async()` 已落地。
- 多 reviewer 路径切为 `asyncio.gather(..., return_exceptions=True)` 并发执行。
- reviewer timeout 通过 `reviewer_timeout_seconds` 配置透传，超时不会中断其他 reviewer。

### S3: sqlite-schema

- 新增 `SqliteTaskStore` 与 `.swl/swallow.db` 路径。
- `store.py` 抽出 `TaskStoreProtocol` / `FileTaskStore`，CLI / Web API / Meta-Optimizer / execution budget policy 统一走 store helper。
- SQLite WAL、busy_timeout、task/event round-trip 与只读读取链路均已测试覆盖。

### S4: async-orchestrator

- `run_task_async()`、async debate loop、`AsyncSubtaskOrchestrator` 与 harness async bridge 已落地。
- `run_task()` 保留同步兼容壳，事件循环内会给出明确的迁移指引。
- 多 card 路径已统一走 async subtask orchestration，不再保留测试 patch 感知分支。

### S5: store-cutover

- 默认 backend 已切为 SQLite，并保留 file mirror/fallback 作为过渡层。
- 新增 `swl migrate` 与 `swl doctor sqlite`；默认 `swl doctor` 已包含 sqlite 段落。
- `migrate --dry-run`、幂等迁移、legacy file-only fallback 与 operator-facing doctor 输出均已覆盖。

## Review 吸收与后续补丁

- Claude review 结论：`0 BLOCK / 4 CONCERN / PR ready`
- C1 已吸收：`run_task()` 在已有事件循环内的报错改为明确指向 `await run_task_async(...)`
- C2 已吸收：recent-event 合并逻辑只读取 file-only task 的事件文件；`swl doctor sqlite` 增加迁移建议
- C3 已吸收：SQLite checkpoint 从 `wal_checkpoint(TRUNCATE)` 改为 `wal_checkpoint(PASSIVE)`
- C4 已吸收：删除 `_execute_task_card is _ORIGINAL_EXECUTE_TASK_CARD` 测试耦合分支
- review follow-up 之后，又补了一次 test harness 收口：将 runtime guard 测试从 `IsolatedAsyncioTestCase` 切为普通 `TestCase + asyncio.run(...)`，规避 anyio pytest 插件与隔离事件循环测试基类的交互问题；该补丁仅影响测试 harness，不改变生产行为

## 风险吸收情况

### 已吸收

- R1 async 覆盖断层：新增 async 测试文件，并完成非 eval / eval 全量复验；test harness 干扰点也已在本轮收口。
- R2 迁移完整性：`swl migrate --dry-run`、幂等迁移与 file-only fallback 已覆盖，且保留原 JSON 文件不自动删除。
- R3 async 上下文阻塞风险：orchestrator 多 card 路径已统一到 async 编排；事件循环内同步入口会显式拒绝并给出迁移提示。
- R4 SQLite 并发写入：WAL + `busy_timeout` 保持启用，checkpoint 策略已降为 `PASSIVE`，减少高频写入整理成本。
- R5 pytest-asyncio 兼容性：async 测试基础设施已落地并通过当前仓库测试矩阵。
- R6 reviewer timeout 语义：timeout 仍为显式可配置策略，并保持 event-driven 可审查。

### 当前边界

- SQLite 当前只承载 `TaskState` / `EventLog`；知识层、`sqlite-vec` 与向量化检索留到 Phase 49。
- `DefaultTaskStore` 仍保留 file mirror/fallback 过渡语义；大体量旧 `.swl/` 目录仍建议运行 `swl migrate`。
- `CLIAgentExecutor` 尚未改为原生 async subprocess，当前仍通过线程桥接。
- Web Control Center 仍保持严格只读，不引入前端构建链。

## 测试结果

最终 closeout 参考基线：

```text
.venv/bin/python -m pytest --tb=short -> 380 selected / 7 deselected, failures=0, errors=0
.venv/bin/python -m pytest -m eval --tb=short -> 7 passed, 380 deselected
```

补充说明：

- 非 eval 全量结果同时写入 `/tmp/phase48_full.xml`，其中 `failures=0`、`errors=0`
- review follow-up 之后已完成定向回归：store / doctor / subtask / web api / meta-optimizer / debate / execution budget / async review gate 均已复验

## 规则文件同步检查

### 必查

- [x] `docs/plans/phase48/closeout.md`
- [x] `docs/plans/phase48/kickoff.md`
- [x] `docs/plans/phase48/design_decision.md`
- [x] `docs/plans/phase48/risk_assessment.md`
- [x] `docs/plans/phase48/review_comments.md`
- [x] `docs/active_context.md`
- [x] `current_state.md`

### 条件更新

- [x] `docs/plans/phase48/commit_summary.md`
- [x] `docs/concerns_backlog.md`
- [x] `pr.md`
- [ ] `AGENTS.md`
- [ ] `README.md`
- [ ] `README.zh-CN.md`

说明：

- `AGENTS.md` / `README*.md` 属于 tag 级对齐文件，应等待 merge 到 `main` 并打 `v0.6.0` 后再更新
- 当前 branch 已达到 merge gate 前置状态，但尚未形成新的 `main` 分支稳定 checkpoint

## Git / PR 建议

1. Human 复核 `docs/plans/phase48/closeout.md`、`docs/plans/phase48/review_comments.md` 与当前 branch diff。
2. Human 将 `feat/phase48_async-storage` 合并回 `main`。
3. Human 依据 Claude 建议决定是否立即打 `v0.6.0`。
4. merge / tag 完成后，由 Codex 同步 `AGENTS.md`、`README.md` 与 `README.zh-CN.md` 的 tag 对齐内容。

## 下一轮建议

Phase 48 merge 完成后，应按 `docs/roadmap.md` 转入 Phase 49，重点推进 `sqlite-vec`、知识层迁移与 retrieval / grounding 闭环，而不是继续在当前分支扩张过渡期 store 逻辑。
