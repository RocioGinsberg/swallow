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
- checkpoint_type: `lto10_m3_complete_waiting_human_commit`
- active_branch: `feat/governance-apply-handler-split`
- last_checked: `2026-05-02`

说明:

- LTO-9 Step 1 已合并到 `main`，最新 HEAD 为 `21c1884 Surface / Meta Optimizer Modularity`。
- `docs/roadmap.md` 已完成 post-merge factual update，当前 ticket 已切换为 `Governance apply handler split` / LTO-10。
- LTO-10 `plan.md` 已由 Codex 起草并根据 `plan_audit.md` 吸收 5 条 concern: `docs/plans/governance-apply-handler-split/plan.md`。
- `docs/plans/governance-apply-handler-split/plan_audit.md` 已产出，结论为 `has-concerns`, 0 blockers / 5 concerns；5 条 concern 已吸收到 plan。
- Human 已完成 M1 / M2 milestone commit，Codex 已完成并验证 M3 route metadata handler extraction，当前等待 Human 审查并执行 M3 milestone commit。
- 最新已执行公开 tag 仍为 `v1.5.0`; annotated tag 指向 `bc8abb1 docs(release): sync v1.5.0 release docs`。
- 当前 tag 策略: 不为 LTO-9 Step 1 单独打 tag，待 LTO-10 与后续 Cluster C 收敛后再评估 `v1.6.0`。

---

## 当前默认继续方向

当前推荐从以下状态继续:

- active_branch: `feat/governance-apply-handler-split`
- active_track: `Architecture / Engineering`
- active_phase: `Governance Apply Handler Split / LTO-10`
- active_slice: `M3 route metadata handler extraction complete`
- workflow_status: `lto10_m3_complete_waiting_human_commit`

下一步:

1. Human 审查 M3 后执行 milestone commit。
2. Codex 在 Human commit 后进入 M4 apply envelope / outbox helper tightening。

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
9. `docs/design/INVARIANTS.md`
10. `docs/design/DATA_MODEL.md`
11. `docs/design/SELF_EVOLUTION.md`
12. `docs/design/INTERACTION.md`
13. `docs/engineering/CODE_ORGANIZATION.md`
14. `docs/engineering/GOF_PATTERN_ALIGNMENT.md`
15. `docs/engineering/TEST_ARCHITECTURE.md`
16. `docs/plans/surface-cli-meta-optimizer-split/closeout.md`
17. `docs/plans/surface-cli-meta-optimizer-split/review_comments.md`

---

## 最小验证命令

恢复工作前，建议至少执行以下检查:

```bash
git status --short --branch
git branch --show-current
git show --no-patch --decorate --oneline HEAD
sed -n '1,220p' docs/active_context.md
sed -n '1,260p' docs/plans/governance-apply-handler-split/plan.md
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

M3 focused validation 已通过；进入 M4 前先等待 Human milestone commit。

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

当前建议提交 LTO-10 planning / state material（由 Human 决定是否包含已更新的 roadmap）:

```bash
git add docs/roadmap.md \
  docs/active_context.md \
  current_state.md \
  docs/plans/governance-apply-handler-split/plan.md \
  docs/plans/governance-apply-handler-split/plan_audit.md

git commit -m "docs(plan): add governance apply handler split plan"
```

如希望严格拆分来源，也可将 `docs/roadmap.md` 单独提交为 `docs(state): update roadmap after surface split`，再提交 plan/state 文档。

---

## 本地基础设施

Phase 46 依赖的 Docker 栈位于 `~/ai-stack/`，与仓库分离。

```bash
cd ~/ai-stack
docker compose up -d new-api
docker compose up -d openwebui
docker compose ps
```

当前 LTO-10 planning 不要求 live HTTP / API-key dependent test。

---

## 恢复命令

重新打开仓库后，可先执行:

```bash
cd /home/rocio/projects/swallow
sed -n '1,220p' docs/active_context.md
sed -n '1,220p' current_state.md
sed -n '1,260p' docs/plans/governance-apply-handler-split/plan.md
```

然后按“恢复时优先读取”的顺序进入当前工作上下文。
