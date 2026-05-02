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
- latest_main_checkpoint_phase: `Orchestration Lifecycle Decomposition / LTO-8 Step 1`
- latest_main_checkpoint: `9ee9cc8 docs(state): update roadmap`
- latest_executed_public_tag: `v1.5.0`
- pending_release_tag: `none`
- current_working_phase: `Surface / CLI / Meta Optimizer Split / LTO-9 Step 1`
- checkpoint_type: `lto9_step1_review_complete_merge_ready`
- active_branch: `feat/surface-cli-meta-optimizer-split`
- last_checked: `2026-05-02`

说明:

- LTO-8 Step 1 已合并到 `main`，`docs/roadmap.md` 已更新为 LTO-8 Step 1 done / LTO-9 current ticket；当前 main checkpoint 仍为 `9ee9cc8 docs(state): update roadmap`。
- 当前工作分支为 `feat/surface-cli-meta-optimizer-split`，LTO-9 Step 1 implementation 与 PR review 已完成，当前处于可 merge 状态。
- Codex 已完成 M1-M5:
  - M1 application command seed for proposal / meta-optimizer operator paths。
  - M2 Meta-Optimizer read-only module split。
  - M3 focused CLI command adapter split for `meta-optimize`、`proposal review/apply`、`route weights show/apply`、`route capabilities show/update`。
  - M4 Control Center read-only query tightening and LTO-7 route metadata guard allowlist drift fix。
  - M5 compatibility audit、same-process route metadata CLI proposal id collision fix、closeout / PR draft。
- `docs/plans/surface-cli-meta-optimizer-split/closeout.md` and `pr.md` are prepared.
- Claude PR review has been produced at `docs/plans/surface-cli-meta-optimizer-split/review_comments.md` with recommendation: `merge`.
- Review recorded 0 blockers and 2 non-blocking follow-up concerns; both are deferred/tracked, not merge blockers.
- 最新已执行公开 tag 仍为 `v1.5.0`; annotated tag 指向 `bc8abb1 docs(release): sync v1.5.0 release docs`。

---

## 当前默认继续方向

当前推荐从以下状态继续:

- active_branch: `feat/surface-cli-meta-optimizer-split`
- active_track: `Architecture / Engineering`
- active_phase: `Surface / CLI / Meta Optimizer Split / LTO-9 Step 1`
- active_slice: `M5 closeout complete`
- workflow_status: `lto9_step1_review_complete_merge_ready`

下一步:

1. Human commits review/closeout state material if accepted.
2. Human creates / updates PR using `pr.md`.
3. Human merges when satisfied.
4. After merge, Codex syncs `current_state.md` / `docs/active_context.md`; roadmap-updater should then update `docs/roadmap.md`.

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读:

1. `AGENTS.md`
2. `.agents/shared/read_order.md`
3. `.agents/shared/state_sync_rules.md`
4. `docs/active_context.md`
5. `current_state.md`
6. `docs/roadmap.md`
7. `docs/plans/surface-cli-meta-optimizer-split/plan.md`
8. `docs/plans/surface-cli-meta-optimizer-split/plan_audit.md`
9. `docs/plans/surface-cli-meta-optimizer-split/closeout.md`
10. `docs/plans/surface-cli-meta-optimizer-split/review_comments.md`
11. `pr.md`
12. `docs/design/INVARIANTS.md`
13. `docs/design/INTERACTION.md`
14. `docs/design/SELF_EVOLUTION.md`
15. `docs/engineering/CODE_ORGANIZATION.md`
16. `docs/engineering/TEST_ARCHITECTURE.md`
17. `docs/concerns_backlog.md`

---

## 最小验证命令

恢复工作前，建议至少执行以下检查:

```bash
git status --short --branch
git branch --show-current
git show --no-patch --decorate --oneline HEAD
sed -n '1,260p' docs/active_context.md
sed -n '1,260p' docs/plans/surface-cli-meta-optimizer-split/closeout.md
```

LTO-9 Step 1 final validation already passed:

```bash
.venv/bin/python -m pytest -q
# 696 passed, 8 deselected, 10 subtests passed

.venv/bin/python -m compileall -q src/swallow
# passed

git diff --check
# passed
```

---

## 当前已知边界

- 不在 `main` 上做 LTO-9 代码实现；当前实现位于 `feat/surface-cli-meta-optimizer-split`。
- Claude review 已完成并建议 merge；合并前只需 Human PR decision。
- 不改变 CLI 命令名、flag、exit code、输出格式。
- 不改变 `docs/design/*.md` 设计语义。
- 不改变 `apply_proposal` 唯一写入入口。
- 不改变 Provider Router route selection / route default behavior。
- 不引入 schema migration、FastAPI write API、UI 扩张、auth/multi-user、远端 worker 或 Planner/DAG。
- MetaOptimizer specialist path 必须保持 read-only / proposal-producing；Operator proposal review/apply 才能进入 governance command path。

---

## 当前建议提交范围

当前建议提交 review / closeout 状态材料:

```bash
git add docs/plans/surface-cli-meta-optimizer-split/closeout.md \
  docs/plans/surface-cli-meta-optimizer-split/review_comments.md \
  docs/concerns_backlog.md \
  docs/active_context.md \
  current_state.md

git commit -m "docs(state): mark surface split ready to merge"
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

当前 LTO-9 Step 1 closeout 不要求 live HTTP / API-key dependent test。

---

## 恢复命令

重新打开仓库后，可先执行:

```bash
cd /home/rocio/projects/swallow
sed -n '1,220p' docs/active_context.md
sed -n '1,220p' current_state.md
sed -n '1,260p' docs/plans/surface-cli-meta-optimizer-split/closeout.md
```

然后按“恢复时优先读取”的顺序进入当前工作上下文。
