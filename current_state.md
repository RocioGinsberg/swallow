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
- latest_main_checkpoint_phase: `LTO-6 — Knowledge Plane Facade Solidification + Wiki Compiler design prep`
- latest_main_checkpoint: `b73ebf8 docs(state): update roadmap`
- latest_executed_public_tag: `v1.7.0`
- pending_release_tag: `none`
- current_working_phase: `LTO-1 — Wiki Compiler 第一阶段 Plan Gate preparation`
- checkpoint_type: `lto1_plan_audit_absorbed_ready_for_gate`
- active_branch: `main`
- last_checked: `2026-05-04`

说明:

- 当前分支为 `main`,HEAD 为 `b73ebf8 docs(state): update roadmap`。
- LTO-13 已合并并完成 `v1.7.0` annotated tag;tag target 为 `2156d4a docs(release): sync v1.7.0 release docs`。
- LTO-6 已合并到 `main` at `883e2a9 Knowledge Plane Facade Solidification`;Knowledge Plane facade 已从 barrel file 收口为 functional facade,旧 direct reach imports 已由 guard 保护。
- Wiki Compiler 设计准备已落到 `main`:
  - `docs/design/EXECUTOR_REGISTRY.md` 增加 Wiki Compiler specialist 五元组、4 模式表与 conflict 决策段。
  - `docs/design/SELF_EVOLUTION.md` 增加 Wiki Compiler 起草侧 / Librarian 守门侧 / Operator 共同收口工作流。
  - `docs/roadmap.md` 当前 ticket 已切到 **LTO-1 Wiki Compiler 第一阶段**。
- `docs/plans/lto-1-wiki-compiler-first-stage/plan_audit.md` 已产出(0 blockers / 5 concerns / 2 nits),Codex 已吸收到 `plan.md`;实现尚未开始,Plan Gate 尚未通过。

---

## 当前默认继续方向

当前推荐从以下状态继续:

- active_branch: `main`
- active_track: `Knowledge Authoring`
- active_phase: `LTO-1 — Wiki Compiler 第一阶段(prep)`
- active_slice: `LTO-1 plan audit absorbed; ready for Human Plan Gate`
- workflow_status: `lto1_plan_audit_absorbed_ready_for_gate`

下一步:

1. Human 审阅已吸收 audit 的 plan + plan_audit,确认 Plan Gate。
2. Human 提交 planning docs,然后从 `main` 切出 `feat/lto-1-wiki-compiler-first-stage`。
3. Codex 再进入实现阶段。

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
8. `docs/design/EXECUTOR_REGISTRY.md`
9. `docs/design/SELF_EVOLUTION.md`
10. `docs/design/INVARIANTS.md`
11. `docs/design/INTERACTION.md`
12. `docs/engineering/CODE_ORGANIZATION.md`
13. `docs/engineering/TEST_ARCHITECTURE.md`
14. `docs/engineering/ARCHITECTURE_DECISIONS.md`
15. `docs/engineering/ADAPTER_DISCIPLINE.md`
16. `docs/design/KNOWLEDGE.md`

---

## 最小验证命令

LTO-1 plan gate 前建议至少执行以下检查:

```bash
git status --short --branch
git branch --show-current
git show --no-patch --decorate --oneline HEAD
sed -n '1,220p' docs/active_context.md
sed -n '1,220p' current_state.md
sed -n '1,220p' docs/roadmap.md
```

最新 full-suite validation 记录:

```bash
.venv/bin/python -m pytest -q
# LTO-6 final: 755 passed, 8 deselected

.venv/bin/python -m compileall -q src/swallow
# passed

git diff --check
# passed
```

---

## 当前已知边界

- 当前不再做 LTO-13 或 LTO-6 代码实现;两者均已合并到 `main`。
- 当前只做 LTO-1 phase plan / plan_audit absorption;Plan Gate 前不开始实现、不切 feature branch。
- 不改变 Orchestrator / Operator 的 task-state control authority。
- 不改变 `apply_proposal` 唯一 canonical / route / policy 写入入口。
- 不新增 auth/multi-user、remote worker、Planner/DAG 或项目级全图谱可视化。
- Wiki Compiler 第一阶段只做设计文档已批准的 authoring specialist + Knowledge Browse 视图 1/2 + guard 范围。

---

## 当前建议提交范围

当前建议提交 LTO-1 planning state sync / plan 文档:

```bash
git add current_state.md docs/active_context.md docs/plans/lto-1-wiki-compiler-first-stage/plan.md docs/plans/lto-1-wiki-compiler-first-stage/plan_audit.md

git commit -m "docs(plan): add lto-1 wiki compiler plan"
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

当前 LTO-1 planning 不要求 live HTTP / API-key dependent test。

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
