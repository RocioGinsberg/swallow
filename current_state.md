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
- latest_main_checkpoint_phase: `LTO-8 Step 2 — harness decomposition / Cluster C closure`
- latest_main_checkpoint: `ea4a886 Orchestration Lifecycle Decomposition`
- latest_executed_public_tag: `v1.5.0`
- pending_release_tag: `v1.6.0`
- current_working_phase: `release docs for v1.6.0`
- checkpoint_type: `v1_6_0_release_docs_ready_for_tag`
- active_branch: `main`
- last_checked: `2026-05-03`

说明:

- 当前分支为 `main`,HEAD 为 `ea4a886 Orchestration Lifecycle Decomposition`。
- LTO-8 Step 2 已合并到 `main`;merge 后簇 C 完整闭合:
  - LTO-7 Provider Router Maintainability 完成。
  - LTO-8 Orchestration Lifecycle Decomposition Step 1 + Step 2 完成。
  - LTO-9 Surface / Meta Optimizer Modularity Step 1 + Step 2 完成。
  - LTO-10 Governance Apply Handler Maintainability 完成。
- LTO-8 Step 2 closeout / review 结论:
  - `docs/plans/orchestration-lifecycle-decomposition-step2/closeout.md`
  - `docs/plans/orchestration-lifecycle-decomposition-step2/review_comments.md`
  - Claude verdict: `recommend-merge`,0 blockers / 2 non-blocking concerns;concerns 已吸收。
  - Codex + Claude full validation 均为 `.venv/bin/python -m pytest -q` -> `734 passed, 8 deselected, 10 subtests passed`。
- Human 已决定打 `v1.6.0` tag。Codex 已将 `README.md` release snapshot 与本文恢复入口同步到 `v1.6.0` release-docs-ready 状态。
- 最新已执行公开 tag 仍为 `v1.5.0`; annotated tag 指向 `bc8abb1 docs(release): sync v1.5.0 release docs`。
- 当前等待 Human 提交 release docs,然后在 `main` 上执行 `v1.6.0` annotated tag。

---

## 当前默认继续方向

当前推荐从以下状态继续:

- active_branch: `main`
- active_track: `Architecture / Engineering`
- active_phase: `v1.6.0 release docs / tag preparation`
- active_slice: `release docs synced; awaiting Human commit and tag`
- workflow_status: `v1_6_0_release_docs_ready_for_tag`

下一步:

1. Human 审阅并提交 release docs。
2. Human 在 `main` 上执行 annotated tag `v1.6.0`。
3. Human 确认 tag 完成后,Codex 更新 `docs/active_context.md` 的 tag 状态。
4. tag 完成后,再由 roadmap factual update 将 LTO-8 标为 Step 1 + Step 2 已完成、簇 C 完全终结、当前 ticket 推进到 LTO-13。

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读:

1. `AGENTS.md`
2. `.agents/shared/read_order.md`
3. `.agents/shared/state_sync_rules.md`
4. `docs/active_context.md`
5. `current_state.md`
6. `README.md`
7. `docs/roadmap.md`
8. `docs/plans/orchestration-lifecycle-decomposition-step2/closeout.md`
9. `docs/plans/orchestration-lifecycle-decomposition-step2/review_comments.md`
10. `docs/design/INVARIANTS.md`
11. `docs/design/ORCHESTRATION.md`
12. `docs/design/HARNESS.md`
13. `docs/engineering/CODE_ORGANIZATION.md`
14. `docs/engineering/TEST_ARCHITECTURE.md`

---

## 最小验证命令

release tag 前建议至少执行以下检查:

```bash
git status --short --branch
git branch --show-current
git show --no-patch --decorate --oneline HEAD
git tag --list "v1.6.0"
sed -n '1,120p' README.md
sed -n '1,220p' docs/active_context.md
sed -n '1,220p' current_state.md
```

LTO-8 Step 2 final validation 已通过:

```bash
.venv/bin/python -m pytest -q
# 734 passed, 8 deselected, 10 subtests passed

.venv/bin/python -m compileall -q src/swallow
# passed

git diff --check
# passed
```

---

## 当前已知边界

- 当前不再做 LTO-8 Step 2 代码实现;实现已合并到 `main`。
- 当前只做 release docs / tag 状态同步。
- 不改变 Orchestrator / Operator 的 task-state control authority。
- 不改变 `apply_proposal` 唯一 canonical / route / policy 写入入口。
- 不新增 schema migration、FastAPI write API、Control Center write path、CLI public surface、proposal target kind、auth/multi-user、remote worker、Planner/DAG 或 Wiki Compiler 工作。
- `docs/roadmap.md` 的 post-merge factual update 应在 release docs / tag 动作完成后单独处理,避免混入 release docs commit。

---

## 当前建议提交范围

当前建议提交 release docs:

```bash
git add README.md current_state.md docs/active_context.md

git commit -m "docs(release): sync v1.6.0 release docs"
```

提交后建议执行 annotated tag:

```bash
git tag -a v1.6.0 -m "v1.6.0 cluster C closure"
```

如果需要推送:

```bash
git push origin main
git push origin v1.6.0
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

当前 release docs / tag 准备不要求 live HTTP / API-key dependent test。

---

## 恢复命令

重新打开仓库后，可先执行:

```bash
cd /home/rocio/projects/swallow
git status --short --branch
sed -n '1,220p' docs/active_context.md
sed -n '1,220p' current_state.md
sed -n '1,120p' README.md
```

然后按“恢复时优先读取”的顺序进入当前工作上下文。
