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
- latest_main_checkpoint_phase: `Surface / CLI / Meta Optimizer Split / LTO-9 Step 1`
- latest_main_checkpoint: `21c1884 Surface / Meta Optimizer Modularity`
- latest_executed_public_tag: `v1.5.0`
- pending_release_tag: `none`
- current_working_phase: `Governance Apply Handler Split / LTO-10`
- checkpoint_type: `lto10_review_complete_recommend_merge`
- active_branch: `feat/governance-apply-handler-split`
- last_checked: `2026-05-02`

说明:

- LTO-9 Step 1 已合并到 `main`，最新 HEAD 为 `21c1884 Surface / Meta Optimizer Modularity`。
- `docs/roadmap.md` 已完成 post-merge factual update，当前 ticket 已切换为 `Governance apply handler split` / LTO-10。
- LTO-10 `plan.md` 已由 Codex 起草并根据 `plan_audit.md` 吸收 5 条 concern: `docs/plans/governance-apply-handler-split/plan.md`。
- `docs/plans/governance-apply-handler-split/plan_audit.md` 已产出，结论为 `has-concerns`, 0 blockers / 5 concerns；5 条 concern 已吸收到 plan。
- Human 已完成 M1 / M2 / M3 / M4 milestone commit；Codex 已完成 M5 facade cleanup / closeout、准备 `docs/plans/governance-apply-handler-split/closeout.md` 与 `pr.md`。
- Claude 已产出 `docs/plans/governance-apply-handler-split/review_comments.md`，结论为 `recommend-merge`，0 blockers / 2 non-blocking concerns / 1 withdrawn blocker。
- Codex 已吸收 review 结论到 closeout、`pr.md`、`docs/active_context.md` 与本恢复入口；当前等待 Human closeout / review state commit、PR 创建/更新与 merge 决策。
- 最新已执行公开 tag 仍为 `v1.5.0`; annotated tag 指向 `bc8abb1 docs(release): sync v1.5.0 release docs`。
- 当前 tag 策略: 不为 LTO-9 Step 1 或 LTO-10 单独打 tag，待 LTO-8 Step 2 / `harness.py` 拆分、LTO-9 Step 2 等后续 Cluster C 收敛后再评估 `v1.6.0`。

---

## 当前默认继续方向

当前推荐从以下状态继续:

- active_branch: `feat/governance-apply-handler-split`
- active_track: `Architecture / Engineering`
- active_phase: `Governance Apply Handler Split / LTO-10`
- active_slice: `PR review complete; recommend-merge; 0 blockers / 2 non-blocking concerns`
- workflow_status: `lto10_review_complete_recommend_merge`

下一步:

1. Human 可选地清理 `9018e25` 的错配 commit message，或在 PR / merge body 中注明它实际对应 M4 outbox extraction。
2. Human 执行 closeout / review state commit。
3. Human 使用 `pr.md` 创建 / 更新 PR，并决定 merge。
4. Merge 后 Codex 同步 post-merge `current_state.md` / `docs/active_context.md`，再触发 roadmap factual update。

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读:

1. `AGENTS.md`
2. `.agents/shared/read_order.md`
3. `.agents/shared/state_sync_rules.md`
4. `docs/active_context.md`
5. `current_state.md`
6. `docs/roadmap.md`
7. `docs/plans/governance-apply-handler-split/plan.md`
8. `docs/plans/governance-apply-handler-split/plan_audit.md`
9. `docs/plans/governance-apply-handler-split/closeout.md`
10. `docs/plans/governance-apply-handler-split/review_comments.md`
11. `pr.md`
12. `docs/design/INVARIANTS.md`
13. `docs/design/DATA_MODEL.md`
14. `docs/design/SELF_EVOLUTION.md`
15. `docs/design/INTERACTION.md`
16. `docs/engineering/CODE_ORGANIZATION.md`
17. `docs/engineering/GOF_PATTERN_ALIGNMENT.md`
18. `docs/engineering/TEST_ARCHITECTURE.md`
19. `docs/plans/surface-cli-meta-optimizer-split/closeout.md`
20. `docs/plans/surface-cli-meta-optimizer-split/review_comments.md`

---

## 最小验证命令

恢复工作前，建议至少执行以下检查:

```bash
git status --short --branch
git branch --show-current
git show --no-patch --decorate --oneline HEAD
sed -n '1,220p' docs/active_context.md
sed -n '1,260p' docs/plans/governance-apply-handler-split/plan.md
sed -n '1,240p' docs/plans/governance-apply-handler-split/closeout.md
sed -n '1,260p' docs/plans/governance-apply-handler-split/review_comments.md
```

LTO-9 Step 1 final validation already passed before merge:

```bash
.venv/bin/python -m pytest -q
# 696 passed, 8 deselected, 10 subtests passed

.venv/bin/python -m compileall -q src/swallow
# passed

git diff --check
# passed
```

LTO-10 M5 final validation 已通过:

```bash
.venv/bin/python -m pytest -q
# 702 passed, 8 deselected, 10 subtests passed

.venv/bin/python -m compileall -q src/swallow
# passed

git diff --check
# passed
```

Claude review independently re-ran:

```bash
.venv/bin/python -m pytest tests/test_invariant_guards.py tests/unit/truth_governance/ tests/test_governance.py tests/test_phase65_sqlite_truth.py -q
# 62 passed

.venv/bin/python -m pytest -q
# 702 passed, 8 deselected, 10 subtests passed

.venv/bin/python -m compileall -q src/swallow
# passed

git diff --check
# clean
```

---

## 当前已知边界

- 不在 `main` 上做 LTO-10 代码实现；当前实现已在 `feat/governance-apply-handler-split` 上推进。
- 不改变 `apply_proposal` 唯一写入入口。
- 不新增 public mutation entry、proposal target kind、schema migration、FastAPI write API、CLI surface 扩张、auth/multi-user、remote worker、Planner/DAG 或 Wiki Compiler 工作。
- 不改变 Provider Router route selection / route default / fallback behavior。
- 不改变 route / policy / canonical 写入语义；本轮目标是 private handler maintainability。
- `docs/design/*.md` 设计语义不在本轮实现中修改。

---

## 当前建议提交范围

当前建议提交 LTO-10 closeout / review state material:

```bash
git add docs/plans/governance-apply-handler-split/closeout.md \
  docs/plans/governance-apply-handler-split/review_comments.md \
  docs/active_context.md \
  current_state.md

git commit -m "docs(state): close governance handler split review"
```

`pr.md` 已准备好供 Human 创建 / 更新 PR；该文件在 `.gitignore` 中，若决定把 PR 草稿纳入提交，需要使用 `git add -f pr.md`。若不重写 `9018e25`，PR / merge body 应注明该 commit 实际对应 M4 outbox extraction。

---

## 本地基础设施

Phase 46 依赖的 Docker 栈位于 `~/ai-stack/`，与仓库分离。

```bash
cd ~/ai-stack
docker compose up -d new-api
docker compose up -d openwebui
docker compose ps
```

当前 LTO-10 closeout 不要求 live HTTP / API-key dependent test。

---

## 恢复命令

重新打开仓库后，可先执行:

```bash
cd /home/rocio/projects/swallow
sed -n '1,220p' docs/active_context.md
sed -n '1,220p' current_state.md
sed -n '1,260p' docs/plans/governance-apply-handler-split/plan.md
sed -n '1,240p' docs/plans/governance-apply-handler-split/closeout.md
sed -n '1,260p' docs/plans/governance-apply-handler-split/review_comments.md
```

然后按“恢复时优先读取”的顺序进入当前工作上下文。
