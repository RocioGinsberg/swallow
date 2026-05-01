# Current State

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: phase 收口、main 稳定 checkpoint 变化、恢复入口变化、公开 tag 变化
> Anti-scope: 不维护高频推进状态、不复制 roadmap 队列、不替代 closeout 作为 phase 历史

## 文档目的

本文件用于在终端会话中断、重新打开仓库或切换设备后，快速恢复到当前稳定工作位置。

当前高频状态请看:

- `docs/active_context.md`

---

## 当前稳定 checkpoint

- repository_state: `runnable`
- latest_main_checkpoint_phase: `Provider Router Split / LTO-7 Step 1`
- latest_main_checkpoint: `6033558 Provider Router Maintainability`
- latest_executed_public_tag: `v1.5.0`
- pending_release_tag: `none`
- current_working_phase: `Orchestration Lifecycle Decomposition / LTO-8 Step 1`
- checkpoint_type: `lto8_pr_review_pass_waiting_human_merge`
- active_branch: `feat/orchestration-lifecycle-decomposition`
- last_checked: `2026-05-02`

说明:

- LTO-7 Provider Router Split 已合并到 `main`，merge checkpoint 为 `6033558 Provider Router Maintainability`。
- `docs/roadmap.md` 已更新为 LTO-7 completed / LTO-8 current ticket。
- 当前工作阶段为 `Orchestration Lifecycle Decomposition / LTO-8 Step 1`。
- Codex 已起草并根据 audit 修订 `docs/plans/orchestration-lifecycle-decomposition/plan.md`。
- Claude plan audit 已产出在 `docs/plans/orchestration-lifecycle-decomposition/plan_audit.md`，结论为 1 BLOCKER + 7 CONCERNs。
- Audit BLOCKER 已通过计划修订吸收：milestone 数量从 6 降到 5，原 M6 closeout / PR gate 折进 M5 与 Completion Conditions。
- Human Plan Gate 已通过，M1-M5 均已由 Human 提交。
- Claude PR review 已完成，结论为 merge，3 个 non-blocking concerns 已记录到 `docs/concerns_backlog.md`。
- Codex 已同步 closeout / `current_state.md` / `docs/active_context.md` / `pr.md` 收口状态。
- 当前等待 Human 提交或更新 PR 并执行 merge。
- 最新已执行公开 tag 仍为 `v1.5.0`; annotated tag 指向 `bc8abb1 docs(release): sync v1.5.0 release docs`。

---

## 当前默认继续方向

当前推荐从以下状态继续:

- active_branch: `feat/orchestration-lifecycle-decomposition`
- active_track: `Architecture / Engineering`
- active_phase: `Orchestration Lifecycle Decomposition / LTO-8 Step 1`
- active_slice: `PR review complete; awaiting Human merge decision`
- workflow_status: `pr_review_pass_with_3_concerns_recommend_merge`

下一步:

1. Human commits or updates the review / closeout docs if needed, then uses `pr.md` to update the PR.
2. Human decides whether to merge the PR.
3. After merge, Codex syncs post-merge state and roadmap factual update.
4. If merge happens, roadmap-updater should mark LTO-8 as Step 1 done, not fully complete.

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读:

1. `AGENTS.md`
2. `.agents/shared/read_order.md`
3. `.agents/shared/state_sync_rules.md`
4. `docs/active_context.md`
5. `current_state.md`
6. `docs/roadmap.md`
7. `docs/plans/orchestration-lifecycle-decomposition/plan.md`
8. `docs/plans/orchestration-lifecycle-decomposition/plan_audit.md`
9. `docs/design/INVARIANTS.md`
10. `docs/design/ORCHESTRATION.md`
11. `docs/design/HARNESS.md`
12. `docs/engineering/CODE_ORGANIZATION.md`
13. `docs/engineering/TEST_ARCHITECTURE.md`
14. `docs/plans/provider-router-split/closeout.md`
15. `docs/plans/provider-router-split/review_comments.md`
16. `docs/concerns_backlog.md`
17. `docs/plans/orchestration-lifecycle-decomposition/review_comments.md`
18. `docs/plans/orchestration-lifecycle-decomposition/closeout.md`
19. `pr.md`

---

## 最小验证命令

恢复工作前，建议至少执行以下检查:

```bash
git status --short --branch
git branch --show-current
git show --no-patch --decorate --oneline HEAD
git log --oneline --decorate -8
```

LTO-8 implementation validation and PR review completed with:

```bash
git status --short --branch
git diff --check
.venv/bin/python -m pytest tests/unit/orchestration -q
.venv/bin/python -m pytest tests/test_librarian_executor.py -q
.venv/bin/python -m pytest tests/test_invariant_guards.py -q
.venv/bin/python -m pytest tests/test_cli.py -k "knowledge or canonical_reuse or librarian" -q
.venv/bin/python -m pytest tests/test_review_gate.py -q
.venv/bin/python -m compileall -q src/swallow
.venv/bin/python -m pytest -q
```

Final default pytest result: `686 passed, 8 deselected, 10 subtests passed`.

---

## 当前已知边界

- 不在 `main` 上做 LTO-8 代码实现。
- 不把 LTO-9 Surface / Meta Optimizer 或 LTO-10 Governance 合并进本 phase。
- 不改变 `docs/design/*.md` 设计语义。
- 不改变 Control Plane 权限；helper module 不得成为第二个 Orchestrator。
- 不改变 Path A/B/C 语义。
- 不改变 route selection / Provider Router behavior。
- 不引入 schema migration、真实模型调用要求、远端 worker 或 Planner/DAG。
- `run_task` / `run_task_async` / `create_task` 仍由 `swallow.orchestration.orchestrator` 公开承载。
- `_apply_librarian_side_effects(...)` 与任何 direct `apply_proposal` caller 仍留在 `orchestrator.py`。
- `knowledge_flow.py` 不依赖 `save_state` / `append_event` / `apply_proposal` / `orchestration.harness` / `orchestration.executor`。
- LTO-8 Step 1 仍是分解里的第一步，`orchestrator.py` 后续还会继续收缩，但不会把控制权移出 Orchestrator。

---

## 当前建议提交范围

M5 implementation 已提交到 `fe31d72`。当前只建议提交 review / closeout 状态材料:

```bash
git add docs/plans/orchestration-lifecycle-decomposition/closeout.md \
  docs/plans/orchestration-lifecycle-decomposition/review_comments.md \
  docs/concerns_backlog.md \
  docs/active_context.md \
  current_state.md

git commit -m "docs(state): close orchestration lifecycle review"
```

`pr.md` has been updated as the local PR body draft, but it is ignored by git in this repository; do not include it in the commit unless Human explicitly wants to force-add it.

---

## 本地基础设施

Phase 46 依赖的 Docker 栈位于 `~/ai-stack/`，与仓库分离。

```bash
cd ~/ai-stack
docker compose up -d new-api
docker compose up -d openwebui
docker compose ps
```

当前 LTO-8 implementation phase 不要求 live HTTP / API-key dependent test。

---

## 恢复命令

重新打开仓库后，可先执行:

```bash
cd /home/rocio/projects/swallow
sed -n '1,220p' docs/active_context.md
sed -n '1,220p' current_state.md
sed -n '1,260p' docs/plans/orchestration-lifecycle-decomposition/plan.md
sed -n '1,260p' docs/plans/orchestration-lifecycle-decomposition/closeout.md
```

然后按“恢复时优先读取”的顺序进入当前工作上下文。
