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
- checkpoint_type: `lto9_plan_revised_after_audit_waiting_human_gate`
- active_branch: `main`
- last_checked: `2026-05-02`

说明:

- LTO-8 Step 1 已合并到 `main`，`docs/roadmap.md` 已更新为 LTO-8 Step 1 done / LTO-9 current ticket；当前 main checkpoint 为 `9ee9cc8 docs(state): update roadmap`。
- 当前工作阶段为 `Surface / CLI / Meta Optimizer Split / LTO-9 Step 1`。
- Codex 已产出并按 audit 修订 `docs/plans/surface-cli-meta-optimizer-split/plan.md`。
- Claude/design-auditor 已产出 `docs/plans/surface-cli-meta-optimizer-split/plan_audit.md`，结论为 `has-concerns`，0 blockers / 5 concerns；Codex 已将 5 条 concern 吸收到 plan。
- 本阶段计划范围是 behavior-preserving surface decomposition: CLI command family adapter split、Meta Optimizer read-only path vs Operator proposal apply/review split、application/commands seed，以及 LTO-7 route metadata guard allowlist drift fix。
- 当前等待 Human Plan Gate；实现尚未开始。
- 最新已执行公开 tag 仍为 `v1.5.0`; annotated tag 指向 `bc8abb1 docs(release): sync v1.5.0 release docs`。

---

## 当前默认继续方向

当前推荐从以下状态继续:

- active_branch: `main`
- active_track: `Architecture / Engineering`
- active_phase: `Surface / CLI / Meta Optimizer Split / LTO-9 Step 1`
- active_slice: `plan revised after audit`
- workflow_status: `lto9_plan_revised_after_audit_waiting_human_gate`

下一步:

1. Human reviews revised `plan.md` + `plan_audit.md` and decides Plan Gate.
2. If approved, Human creates `feat/surface-cli-meta-optimizer-split` from `main`.
3. Codex starts M1 implementation only after branch switch and gate approval.

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
9. `docs/design/INVARIANTS.md`
10. `docs/design/INTERACTION.md`
11. `docs/design/SELF_EVOLUTION.md`
12. `docs/engineering/CODE_ORGANIZATION.md`
13. `docs/engineering/TEST_ARCHITECTURE.md`
14. `docs/concerns_backlog.md`
15. `docs/plans/orchestration-lifecycle-decomposition/closeout.md`
16. `docs/plans/orchestration-lifecycle-decomposition/review_comments.md`

---

## 最小验证命令

恢复工作前，建议至少执行以下检查:

```bash
git status --short --branch
git branch --show-current
git show --no-patch --decorate --oneline HEAD
sed -n '1,260p' docs/plans/surface-cli-meta-optimizer-split/plan.md
```

本轮是 docs-only planning update，不要求跑 pytest。

后续实现阶段计划中的基础 gate:

```bash
.venv/bin/python -m pytest tests/test_meta_optimizer.py -q
.venv/bin/python -m pytest tests/unit/application/test_command_boundaries.py -q
.venv/bin/python -m pytest tests/unit/surface_tools/test_meta_optimizer_boundary.py -q
.venv/bin/python -m pytest tests/integration/cli -q
.venv/bin/python -m pytest tests/test_cli.py -k "proposal or meta_optimizer or route_capabilities or route_weights or serve" -q
.venv/bin/python -m pytest tests/test_web_api.py -q
.venv/bin/python -m pytest tests/test_invariant_guards.py -q
.venv/bin/python -m compileall -q src/swallow
git diff --check
```

---

## 当前已知边界

- 不在 `main` 上做 LTO-9 代码实现；`main` 当前只承载 plan / audit gate。
- plan + audit + Human Gate 通过后，Human 先创建 `feat/surface-cli-meta-optimizer-split`。
- 不改变 CLI 命令名、flag、exit code、输出格式。
- 不改变 `docs/design/*.md` 设计语义。
- 不改变 `apply_proposal` 唯一写入入口。
- 不改变 Provider Router route selection / route default behavior。
- 不引入 schema migration、FastAPI write API、UI 扩张、auth/multi-user、远端 worker 或 Planner/DAG。
- MetaOptimizer specialist path 必须保持 read-only / proposal-producing；Operator proposal review/apply 才能进入 governance command path。

---

## 当前建议提交范围

当前只建议提交 LTO-9 revised plan / audit / state docs:

```bash
git add docs/plans/surface-cli-meta-optimizer-split/plan.md \
  docs/plans/surface-cli-meta-optimizer-split/plan_audit.md \
  docs/active_context.md \
  current_state.md

git commit -m "docs(plan): revise surface split plan after audit"
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

当前 LTO-9 planning phase 不要求 live HTTP / API-key dependent test。

---

## 恢复命令

重新打开仓库后，可先执行:

```bash
cd /home/rocio/projects/swallow
sed -n '1,220p' docs/active_context.md
sed -n '1,220p' current_state.md
sed -n '1,260p' docs/plans/surface-cli-meta-optimizer-split/plan.md
```

然后按“恢复时优先读取”的顺序进入当前工作上下文。
