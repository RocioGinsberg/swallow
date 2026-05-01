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
- latest_main_checkpoint_phase: `Architecture Recomposition First Branch`
- latest_executed_public_tag: `v1.5.0`
- pending_release_tag: `none`
- current_working_phase: `Provider Router Split / LTO-7 Step 1`
- checkpoint_type: `post_architecture_recomposition_merge_next_phase_planning`
- active_branch: `main`
- last_checked: `2026-05-01`

说明:

- `main` 当前最新 checkpoint 为 `a1e536b docs(state): update roadmap`。
- Architecture Recomposition first branch 已 merge 到 `main`:
  - `c3596c2 merge: architecture recomposition first branch`
- 该 branch 完成了第一轮 architecture recomposition pilot:
  - minimal test helper foundation
  - Knowledge Plane facade pilot
  - narrow upper-layer import migration
  - focused test relocation
  - Control Center application query pilot
- Roadmap 已重组为长期优化目标(`LTO-*`)与近期 phase ticket 队列。
- 最新已执行公开 tag 仍为 `v1.5.0`;annotated tag 指向 `bc8abb1 docs(release): sync v1.5.0 release docs`。
- 当前下一阶段按 roadmap 从 `LTO-7 Provider Router Maintainability` 开始，`docs/plans/provider-router-split/plan.md` 已按 audit 修订，下一步等待 required model review / Human Plan Gate。

---

## 当前默认继续方向

当前推荐从以下状态继续:

- active_branch: `main`
- active_track: `Architecture / Engineering`
- active_phase: `Provider Router Split / LTO-7 Step 1`
- active_slice: `Plan revised after audit; awaiting model review`
- workflow_status: `plan_revision_complete_model_review_pending`

说明:

- 当前只允许推进计划审查与 gate，不进入实现。
- `plan_audit.md` 已产出，Codex 已吸收 blocker / concerns 到 `plan.md`。
- 实现前必须完成 required `model_review.md`，由 Human 通过 Plan Gate，并从 `main` 切换到 `feat/provider-router-split`。
- Codex 不执行 `git commit`、`git tag`、`git push`、PR 创建或 merge。

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读:

1. `AGENTS.md`
2. `.agents/shared/read_order.md`
3. `.agents/shared/state_sync_rules.md`
4. `docs/active_context.md`
5. `current_state.md`
6. `docs/roadmap.md`
7. `docs/plans/provider-router-split/plan.md`
8. `docs/plans/provider-router-split/plan_audit.md`
9. `docs/design/INVARIANTS.md`
10. `docs/design/PROVIDER_ROUTER.md`
11. `docs/design/DATA_MODEL.md`
12. `docs/design/ORCHESTRATION.md`
13. `docs/design/EXECUTOR_REGISTRY.md`
14. `docs/engineering/CODE_ORGANIZATION.md`
15. `docs/engineering/GOF_PATTERN_ALIGNMENT.md`
16. `docs/engineering/TEST_ARCHITECTURE.md`

仅在需要追溯上一阶段边界时再读取:

- `docs/plans/architecture-recomposition/plan.md`
- git log around `c3596c2 merge: architecture recomposition first branch`

---

## 最小验证命令

恢复工作前，建议至少执行以下检查:

```bash
git status --short --branch
git branch --show-current
git show --no-patch --decorate --oneline HEAD
git log --oneline --decorate -8
git tag --list 'v*' --sort=-creatordate | head -n 5
```

Provider Router Split planning gate 的最小文档检查:

```bash
git diff --check
sed -n '1,220p' docs/plans/provider-router-split/plan.md
```

实现阶段 baseline checks 由 `docs/plans/provider-router-split/plan.md` 定义。进入实现前至少保留:

```bash
.venv/bin/python -m pytest tests/test_router.py -q
.venv/bin/python -m pytest tests/test_invariant_guards.py -q
.venv/bin/python -m compileall -q src/swallow
.venv/bin/python -m pytest -q
git diff --check
```

---

## 当前已知边界

- 当前阶段是 `Provider Router Split / LTO-7 Step 1` 的 model review / plan gate 前状态。
- 不在 `main` 上做实现。
- 不把 LTO-8 Orchestration、LTO-9 Surface / Meta Optimizer 或 LTO-10 Governance 合并进本 phase。
- 不改变 `docs/design/*.md` 设计语义。
- 不改变 Path A/B/C 语义，不让 Path B 调用 Provider Router。
- 不改变 Control Plane 权限，Provider Router 不做任务域判断、复杂度评估、waiting_human 决策或语义级 retry 决策。
- 不绕过 `apply_proposal` 直接写 route metadata / policy。
- 不引入新的 provider、网络协议、schema migration 或真实模型调用要求。
- Provider Router selection extraction must not import executor defaults through `swallow.orchestration.executor`; use `swallow.knowledge_retrieval.dialect_data` unless a narrower non-orchestration constants module is explicitly introduced.
- README 当前为单文件双语结构;不要再要求同步不存在的 `README.zh-CN.md`。

---

## 当前建议提交范围

如接受本轮状态同步、plan audit 与修订后的计划，建议由 Human 单独提交文档:

```bash
git add docs/active_context.md current_state.md docs/plans/provider-router-split/plan.md docs/plans/provider-router-split/plan_audit.md
git commit -m "docs(plan): add provider router split plan"
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

验证 new-api 可达:

```bash
curl http://localhost:3000/api/status
```

---

## 恢复命令

重新打开仓库后，可先执行:

```bash
cd /home/rocio/projects/swallow
sed -n '1,220p' docs/active_context.md
sed -n '1,220p' current_state.md
sed -n '1,220p' docs/plans/provider-router-split/plan.md
sed -n '1,220p' docs/plans/provider-router-split/plan_audit.md
```

然后按“恢复时优先读取”的顺序进入当前工作上下文。
