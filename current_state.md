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
- latest_main_checkpoint_phase: `LTO-9 Step 2 — broad CLI command-family migration`
- latest_main_checkpoint: `1251c3c LTO-9 Step 2 — broad CLI command-family migration`
- latest_executed_public_tag: `v1.5.0`
- pending_release_tag: `none`
- current_working_phase: `LTO-8 Step 2 — harness decomposition`
- checkpoint_type: `lto8_step2_review_complete_recommend_merge`
- active_branch: `feat/orchestration-lifecycle-decomposition-step2`
- last_checked: `2026-05-03`

说明:

- LTO-9 Step 2 已合并到 `main`，merge commit 为 `1251c3c LTO-9 Step 2 — broad CLI command-family migration`；其 post-merge roadmap update commit 为 `4229680 docs(state): update roadmap`。
- 当前 feature branch 为 `feat/orchestration-lifecycle-decomposition-step2`，用于 LTO-8 Step 2 / cluster C closure phase。
- LTO-8 Step 2 `plan.md` 已由 Codex 起草并吸收 `plan_audit.md` 的 5 条 concern；Human 已通过 plan gate。
- Human 已完成 M1-M5 milestone commits：
  - `c8a94f3 test(orchestration): characterize harness facade`
  - `3f0973c refactor(orchestration): split retrieval and report helpers`
  - `eb4366f refactor(orchestration): split artifact record helpers`
  - `5bf1c84 refactor(orchestration): split execution attempts and telemetry`
  - `e65e606 refactor(orchestration): thin harness write pipeline`
- Codex 已准备并更新 LTO-8 Step 2 closeout / PR materials：
  - `docs/plans/orchestration-lifecycle-decomposition-step2/closeout.md`
  - `pr.md`
  - `docs/active_context.md`
  - `current_state.md`
- Claude 已产出 implementation / PR review：`docs/plans/orchestration-lifecycle-decomposition-step2/review_comments.md`，结论为 `recommend-merge`，0 blockers / 2 non-blocking concerns。
- Codex 已吸收 2 条非阻塞 concern：
  - closeout / `pr.md` 不再把 1028 行 `harness.py` 描述为完整 thin facade，而是描述为 "import-compatible orchestration facade with policy/artifact pipeline extracted"，并记录 report-rendering deferred work。
  - `docs/design/INVARIANTS.md §9` 已登记 `test_harness_helper_modules_only_emit_allowlisted_event_kinds`，作为 helper-side `append_event` allowlist 的守卫测试。
- 最新已执行公开 tag 仍为 `v1.5.0`; annotated tag 指向 `bc8abb1 docs(release): sync v1.5.0 release docs`。
- 当前 tag 策略: defer `v1.6.0` 到 LTO-8 Step 2 merge 后，届时 cluster C closure 才完整。

---

## 当前默认继续方向

当前推荐从以下状态继续:

- active_branch: `feat/orchestration-lifecycle-decomposition-step2`
- active_track: `Architecture / Engineering`
- active_phase: `LTO-8 Step 2 — harness decomposition`
- active_slice: `PR review complete; recommend-merge; concerns absorbed; ready for Human PR decision`
- workflow_status: `lto8_step2_review_complete_recommend_merge`

下一步:

1. Human 审查并提交 closeout / review state materials。
2. Human 使用 `pr.md` 创建或更新 PR，并决定 merge。
3. Merge 后 Codex 同步 post-merge `current_state.md` / `docs/active_context.md`，再触发 roadmap factual update 和 tag evaluation。

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读:

1. `AGENTS.md`
2. `.agents/shared/read_order.md`
3. `.agents/shared/state_sync_rules.md`
4. `docs/active_context.md`
5. `current_state.md`
6. `docs/roadmap.md`
7. `docs/plans/orchestration-lifecycle-decomposition-step2/plan.md`
8. `docs/plans/orchestration-lifecycle-decomposition-step2/plan_audit.md`
9. `docs/plans/orchestration-lifecycle-decomposition-step2/closeout.md`
10. `docs/plans/orchestration-lifecycle-decomposition-step2/review_comments.md`
11. `pr.md`
12. `docs/design/INVARIANTS.md`
13. `docs/design/ORCHESTRATION.md`
14. `docs/design/HARNESS.md`
15. `docs/engineering/CODE_ORGANIZATION.md`
16. `docs/engineering/TEST_ARCHITECTURE.md`

---

## 最小验证命令

恢复工作前，建议至少执行以下检查:

```bash
git status --short --branch
git branch --show-current
git show --no-patch --decorate --oneline HEAD
sed -n '1,220p' docs/active_context.md
sed -n '1,260p' docs/plans/orchestration-lifecycle-decomposition-step2/plan.md
sed -n '1,260p' docs/plans/orchestration-lifecycle-decomposition-step2/closeout.md
sed -n '1,260p' pr.md
```

LTO-8 Step 2 final Codex validation 已通过:

```bash
.venv/bin/python -m pytest tests/test_grounding.py tests/unit/orchestration/test_artifact_writer_module.py tests/test_invariant_guards.py -q
# 40 passed

.venv/bin/python -m pytest tests/unit/orchestration -q
# 46 passed

.venv/bin/python -m pytest tests/test_grounding.py tests/test_cost_estimation.py tests/test_executor_protocol.py tests/test_executor_async.py tests/test_debate_loop.py tests/test_librarian_executor.py tests/test_invariant_guards.py -q
# 79 passed

.venv/bin/python -m pytest tests/test_cli.py -q
# 242 passed, 10 subtests passed

.venv/bin/python -m compileall -q src/swallow
# passed

.venv/bin/python -m pytest -q
# 734 passed, 8 deselected, 10 subtests passed

git diff --check
# passed
```

Claude review independently re-ran:

```bash
.venv/bin/python -m pytest -q
# 734 passed, 8 deselected, 10 subtests passed
```

---

## 当前已知边界

- 不在 `main` 上做 LTO-8 Step 2 代码实现；当前实现已在 `feat/orchestration-lifecycle-decomposition-step2` 上推进。
- 不改变 Orchestrator / Operator 的 task-state control authority。
- 不改变 `apply_proposal` 唯一 canonical / route / policy 写入入口。
- 不新增 schema migration、FastAPI write API、Control Center write path、CLI public surface、proposal target kind、auth/multi-user、remote worker、Planner/DAG 或 Wiki Compiler 工作。
- 不改变 Provider Router route selection / route default / fallback behavior。
- 不改变 executor registry brand binding。
- `docs/design/*.md` 设计语义不在本轮实现中修改。

---

## 当前建议提交范围

当前建议分两步提交,避免把设计文档更新与状态收口混在同一个 commit。

先提交 review concern 中的设计守卫登记:

```bash
git add docs/design/INVARIANTS.md

git commit -m "docs(design): register helper event guard"
```

再提交 LTO-8 Step 2 closeout / review state material:

```bash
git add docs/plans/orchestration-lifecycle-decomposition-step2/closeout.md \
  docs/plans/orchestration-lifecycle-decomposition-step2/review_comments.md \
  docs/active_context.md \
  current_state.md

git commit -m "docs(state): close harness decomposition review"
```

`pr.md` 已准备好供 Human 创建 / 更新 PR；该文件在 `.gitignore` 中。若决定把 PR 草稿纳入提交，需要使用:

```bash
git add -f pr.md
git commit -m "docs(pr): draft harness decomposition pr"
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

当前 LTO-8 Step 2 closeout 不要求 live HTTP / API-key dependent test。

---

## 恢复命令

重新打开仓库后，可先执行:

```bash
cd /home/rocio/projects/swallow
sed -n '1,220p' docs/active_context.md
sed -n '1,220p' current_state.md
sed -n '1,260p' docs/plans/orchestration-lifecycle-decomposition-step2/plan.md
sed -n '1,260p' docs/plans/orchestration-lifecycle-decomposition-step2/closeout.md
sed -n '1,260p' pr.md
```

然后按“恢复时优先读取”的顺序进入当前工作上下文。
