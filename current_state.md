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
- latest_main_checkpoint_phase: `post-Hygiene Bundle roadmap sync`
- latest_main_checkpoint: `449653a docs(state): update roadmap`
- latest_executed_public_tag: `v1.8.0`
- pending_release_tag: `none`
- current_working_phase: `lto-1-wiki-compiler-second-stage`
- checkpoint_type: `feature_branch_review_absorbed_ready_for_merge`
- active_branch: `feat/lto-1-wiki-compiler-second-stage`
- last_checked: `2026-05-04`

说明:

- 当前工作分支为 `feat/lto-1-wiki-compiler-second-stage`;branch HEAD 为 `42c6b3d test(wiki): lock compiler second stage guards`。Claude review 已产出 recommend-merge,且 C1 已通过 closeout decision matrix 吸收。
- Human 已选择下一启动方向为 **Wiki Compiler 第二阶段**。Codex 已完成 M1-M5 与 review absorption,当前等待 Human final closeout sync commit / merge gate。
- LTO-13 已合并并完成 `v1.7.0` annotated tag;tag target 为 `2156d4a docs(release): sync v1.7.0 release docs`。
- LTO-1 已合并并完成 `v1.8.0` annotated tag;tag target 为 `d6f2442 docs(release): sync v1.8.0 release docs`;merge commit 为 `349efa9 Knowledge Authoring / LLM Wiki Compiler(authoring specialist)`。
- LTO-6 已合并到 `main` at `883e2a9 Knowledge Plane Facade Solidification`;Knowledge Plane facade 已从 barrel file 收口为 functional facade,旧 direct reach imports 已由 guard 保护。
- Hygiene Bundle 已 merge to `main` at `e656bd3 refactor(hygiene): close service boundaries and router follow-ups`:
  - D4 Phase B/C:`surface_tools` 残余 service-like modules 移至 `application/services/`;`paths.py` / `workspace.py` / `identity.py` 移至 `application/infrastructure/`;repo 内 production/test imports 已无 `swallow.surface_tools`。
  - LTO-6 C1:`knowledge_plane.py` 删除冗余 report `build_*` aliases,报告渲染统一保留 `render_*`。
  - LTO-7 follow-up:`router.py` 不再调用 provider-router 子模块私有名;默认 fallback baseline 由 `route_registry.py` 持有。
  - 最新验证:`compileall -q src/swallow`;focused gates;full pytest `773 passed, 12 deselected`;`git diff --check`。

---

## 当前默认继续方向

当前推荐从以下状态继续:

- active_branch: `feat/lto-1-wiki-compiler-second-stage`
- active_track: `Knowledge Authoring`
- active_phase: `lto-1-wiki-compiler-second-stage`
- active_slice: `PR review absorbed; final closeout ready for merge gate`
- workflow_status: `review_absorbed_waiting_human_final_docs_commit`

下一步:

1. Human 审阅并提交 final review absorption / closeout sync。
2. Human 检查 `./pr.md` 并决定是否合并 feature branch。
3. Codex 在 Human merge 后继续同步 `docs/active_context.md`、`current_state.md` 和 `docs/roadmap.md`。

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

恢复当前 review-absorbed 收口状态时,建议至少执行以下检查:

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
# Wiki Compiler second-stage final rerun: 793 passed, 16 deselected

.venv/bin/python -m compileall -q src/swallow
# passed

git diff --check
# passed
```

---

## 当前已知边界

- 当前不再做 LTO-13 / LTO-6 / LTO-1 第一阶段功能实现;三者均已合并到 `main`,且 `v1.8.0` tag 已执行。
- Hygiene Bundle 已完成;当前不继续扩张该 bundle。
- Wiki Compiler 第二阶段已完成实现、验证和 review absorption,当前只等待 Human final docs commit / merge gate。
- 不改变 Orchestrator / Operator 的 task-state control authority。
- 不改变 `apply_proposal` 唯一 canonical / route / policy 写入入口。
- 不新增 auth/multi-user、remote worker、Planner/DAG 或项目级全图谱可视化。
- `surface_tools` 不保留兼容 shim;仓库内调用点已经全部迁移到 `application/services` / `application/infrastructure` / `adapters`。

---

## 当前建议提交范围

当前建议提交 final review absorption / closeout sync:

```bash
git add docs/active_context.md current_state.md \
  docs/plans/lto-1-wiki-compiler-second-stage/closeout.md \
  docs/plans/lto-1-wiki-compiler-second-stage/review_comments.md
git commit -m "docs(closeout): finalize wiki compiler second stage review"
```

`./pr.md` is ignored by default. If Human wants the PR draft committed, add it explicitly with `git add -f pr.md`.


---

## 本地基础设施

Phase 46 依赖的 Docker 栈位于 `~/ai-stack/`，与仓库分离。

```bash
cd ~/ai-stack
docker compose up -d new-api
docker compose up -d openwebui
docker compose ps
```

当前 Hygiene Bundle 不要求 live HTTP / API-key dependent test。

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
