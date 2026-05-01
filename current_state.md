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
- checkpoint_type: `lto8_plan_draft_pending_audit`
- active_branch: `main`
- last_checked: `2026-05-01`

说明:

- LTO-7 Provider Router Split 已合并到 `main`，merge checkpoint 为 `6033558 Provider Router Maintainability`。
- `docs/roadmap.md` 已更新为 LTO-7 completed / LTO-8 current ticket。
- 当前下一阶段为 `Orchestration Lifecycle Decomposition / LTO-8 Step 1`。
- Codex 已起草 `docs/plans/orchestration-lifecycle-decomposition/plan.md`。
- 当前尚未进入实现；实现前需要 `plan_audit.md`、Human Plan Gate，以及切换到 `feat/orchestration-lifecycle-decomposition`。
- 最新已执行公开 tag 仍为 `v1.5.0`; annotated tag 指向 `bc8abb1 docs(release): sync v1.5.0 release docs`。

---

## 当前默认继续方向

当前推荐从以下状态继续:

- active_branch: `main`
- active_track: `Architecture / Engineering`
- active_phase: `Orchestration Lifecycle Decomposition / LTO-8 Step 1`
- active_slice: `plan drafted; awaiting plan audit and Human Plan Gate`
- workflow_status: `lto8_plan_draft_pending_audit`

下一步:

1. Claude/design-auditor reviews `docs/plans/orchestration-lifecycle-decomposition/plan.md`.
2. Codex absorbs audit findings if needed.
3. Human approves Plan Gate and switches to `feat/orchestration-lifecycle-decomposition`.
4. Codex starts M1 implementation after branch/gate alignment.

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
8. `docs/design/INVARIANTS.md`
9. `docs/design/ORCHESTRATION.md`
10. `docs/design/HARNESS.md`
11. `docs/engineering/CODE_ORGANIZATION.md`
12. `docs/engineering/TEST_ARCHITECTURE.md`
13. `docs/plans/provider-router-split/closeout.md`
14. `docs/plans/provider-router-split/review_comments.md`
15. `docs/concerns_backlog.md`

---

## 最小验证命令

恢复工作前，建议至少执行以下检查:

```bash
git status --short --branch
git branch --show-current
git show --no-patch --decorate --oneline HEAD
git log --oneline --decorate -8
```

LTO-8 planning sync verified with:

```bash
git diff --check
```

Implementation validation will be selected by `docs/plans/orchestration-lifecycle-decomposition/plan.md`.

---

## 当前已知边界

- 不在 `main` 上做 LTO-8 代码实现。
- 不在 plan audit / Human Plan Gate 前修改 orchestration runtime code。
- 不把 LTO-9 Surface / Meta Optimizer 或 LTO-10 Governance 合并进本 phase。
- 不改变 `docs/design/*.md` 设计语义。
- 不改变 Control Plane 权限；helper module 不得成为第二个 Orchestrator。
- 不改变 Path A/B/C 语义。
- 不改变 route selection / Provider Router behavior。
- 不引入 schema migration、真实模型调用要求、远端 worker 或 Planner/DAG。
- `run_task` / `run_task_async` / `create_task` 仍由 `swallow.orchestration.orchestrator` 公开承载。

---

## 当前建议提交范围

如接受 LTO-8 规划与 post-merge 状态同步，建议由 Human 提交:

```bash
git add docs/roadmap.md docs/active_context.md current_state.md docs/plans/orchestration-lifecycle-decomposition/plan.md
git commit -m "docs(plan): start orchestration lifecycle decomposition"
```

---

## 本地基础设施

Phase 46 依赖的 Docker 栈位于 `~/ai-stack/`，与仓库分离。

```bash
cd ~/ai-stack
docker compose up -d new-api
docker compose up -d openwebui
docker compose ps
```

当前 LTO-8 planning phase 不要求 live HTTP / API-key dependent test。

---

## 恢复命令

重新打开仓库后，可先执行:

```bash
cd /home/rocio/projects/swallow
sed -n '1,220p' docs/active_context.md
sed -n '1,220p' current_state.md
sed -n '1,260p' docs/plans/orchestration-lifecycle-decomposition/plan.md
```

然后按“恢复时优先读取”的顺序进入当前工作上下文。
