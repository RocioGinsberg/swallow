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
- latest_main_checkpoint_phase: `post-v1.8.0 roadmap sync`
- latest_main_checkpoint: `f81503b docs(state): update roadmap`
- latest_executed_public_tag: `v1.8.0`
- pending_release_tag: `none`
- current_working_phase: `Hygiene Bundle`
- checkpoint_type: `hygiene_bundle_validation_passed_pending_commit`
- active_branch: `main`
- last_checked: `2026-05-04`

说明:

- 当前工作分支为 `main`;HEAD 为 `f81503b docs(state): update roadmap`。Hygiene Bundle 当前处于 validated dirty working tree,等待 Human 审阅并提交。
- LTO-13 已合并并完成 `v1.7.0` annotated tag;tag target 为 `2156d4a docs(release): sync v1.7.0 release docs`。
- LTO-1 已合并并完成 `v1.8.0` annotated tag;tag target 为 `d6f2442 docs(release): sync v1.8.0 release docs`;merge commit 为 `349efa9 Knowledge Authoring / LLM Wiki Compiler(authoring specialist)`。
- LTO-6 已合并到 `main` at `883e2a9 Knowledge Plane Facade Solidification`;Knowledge Plane facade 已从 barrel file 收口为 functional facade,旧 direct reach imports 已由 guard 保护。
- Hygiene Bundle 已在当前 working tree 完成并验证:
  - D4 Phase B/C:`surface_tools` 残余 service-like modules 移至 `application/services/`;`paths.py` / `workspace.py` / `identity.py` 移至 `application/infrastructure/`;repo 内 production/test imports 已无 `swallow.surface_tools`。
  - LTO-6 C1:`knowledge_plane.py` 删除冗余 report `build_*` aliases,报告渲染统一保留 `render_*`。
  - LTO-7 follow-up:`router.py` 不再调用 provider-router 子模块私有名;默认 fallback baseline 由 `route_registry.py` 持有。
  - 最新验证:`compileall -q src/swallow`;focused gates;full pytest `773 passed, 12 deselected`;`git diff --check`。

---

## 当前默认继续方向

当前推荐从以下状态继续:

- active_branch: `main`
- active_track: `Architecture / Hygiene`
- active_phase: `Hygiene Bundle`
- active_slice: `validated; pending human commit`
- workflow_status: `hygiene_bundle_validation_passed_pending_commit`

下一步:

1. Human 审阅 Hygiene Bundle diff。
2. Human 按 bundle 内语义执行一个或多个 commit。
3. Human 从 `docs/roadmap.md` Direction Gate 候选中选择下一启动方向。

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

Hygiene Bundle commit 前建议至少执行以下检查:

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
# Hygiene Bundle final rerun: 773 passed, 12 deselected

.venv/bin/python -m compileall -q src/swallow
# passed

git diff --check
# passed
```

---

## 当前已知边界

- 当前不再做 LTO-13 / LTO-6 / LTO-1 功能实现;三者均已合并到 `main`,且 `v1.8.0` tag 已执行。
- Hygiene Bundle 是压缩流程工程收口,不新增功能、不新增 LLM 调用、不变更 schema、不 cut tag。
- 不改变 Orchestrator / Operator 的 task-state control authority。
- 不改变 `apply_proposal` 唯一 canonical / route / policy 写入入口。
- 不新增 auth/multi-user、remote worker、Planner/DAG 或项目级全图谱可视化。
- `surface_tools` 不保留兼容 shim;仓库内调用点已经全部迁移到 `application/services` / `application/infrastructure` / `adapters`。

---

## 当前建议提交范围

当前建议提交 Hygiene Bundle:

```bash
git add -A
git commit -m "refactor(hygiene): close service boundaries and router follow-ups"
```

本 bundle 不建议 cut 新 tag。

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
