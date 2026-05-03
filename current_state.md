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
- latest_main_checkpoint_phase: `LTO-1 — Wiki Compiler 第一阶段 merged`
- latest_main_checkpoint: `349efa9 Knowledge Authoring / LLM Wiki Compiler(authoring specialist)`
- latest_executed_public_tag: `v1.7.0`
- pending_release_tag: `v1.8.0`
- current_working_phase: `v1.8.0 release docs / tag preparation`
- checkpoint_type: `v1_8_0_release_docs_ready_for_tag_commit`
- active_branch: `main`
- last_checked: `2026-05-04`

说明:

- 当前工作分支为 `main`;HEAD 为 `349efa9 Knowledge Authoring / LLM Wiki Compiler(authoring specialist)`。
- LTO-13 已合并并完成 `v1.7.0` annotated tag;tag target 为 `2156d4a docs(release): sync v1.7.0 release docs`。
- LTO-6 已合并到 `main` at `883e2a9 Knowledge Plane Facade Solidification`;Knowledge Plane facade 已从 barrel file 收口为 functional facade,旧 direct reach imports 已由 guard 保护。
- LTO-1 Wiki Compiler 第一阶段已合并到 `main`:
  - `swl wiki draft/refine/refresh-evidence` CLI 与 `application.commands.wiki` 已落地。
  - Wiki Compiler 作为 propose-only specialist 注册到 executor registry,Path C 经 Provider Router,不直接写 canonical truth。
  - Knowledge Browse HTTP routes 与 Web Control Center 只读 Knowledge panel 已落地。
  - M5 guard / eval / review cleanup 已完成;Claude review verdict 为 `recommend-merge`,0 blockers。
- `v1.8.0` release docs 已准备好;Human 提交 release docs 后执行 annotated tag。

---

## 当前默认继续方向

当前推荐从以下状态继续:

- active_branch: `main`
- active_track: `Release / Tag Preparation`
- active_phase: `v1.8.0 release docs`
- active_slice: `release docs synced; ready for tag commit`
- workflow_status: `v1_8_0_release_docs_ready_for_tag_commit`

下一步:

1. Human 审阅本轮 release docs diff。
2. Human 提交 release docs commit。
3. Human 执行 annotated tag `v1.8.0`。
4. Human 确认 tag 完成后,Codex 同步 `docs/active_context.md` 的 tag 已执行状态。

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

`v1.8.0` tag commit 前建议至少执行以下检查:

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
# LTO-1 final rerun before merge: 773 passed, 12 deselected

.venv/bin/python -m compileall -q src/swallow
# passed

git diff --check
# passed
```

---

## 当前已知边界

- 当前不再做 LTO-13 或 LTO-6 代码实现;两者均已合并到 `main`。
- 当前 LTO-1 implementation / review / C1 cleanup 已完成并合并到 `main`;本轮只做 release/tag 文档同步。
- 不改变 Orchestrator / Operator 的 task-state control authority。
- 不改变 `apply_proposal` 唯一 canonical / route / policy 写入入口。
- 不新增 auth/multi-user、remote worker、Planner/DAG 或项目级全图谱可视化。
- Wiki Compiler 第一阶段只做设计文档已批准的 authoring specialist + Knowledge Browse 视图 1/2 + guard 范围;Web 侧 Wiki Compiler trigger、自动 promotion/supersede/conflict resolution 仍 deferred。

---

## 当前建议提交范围

当前建议提交 `v1.8.0` release docs:

```bash
git add README.md current_state.md docs/active_context.md docs/roadmap.md
git commit -m "docs(release): sync v1.8.0 release docs"
```

提交后建议执行:

```bash
git tag -a v1.8.0 -m "v1.8.0 Wiki Compiler first stage"
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

当前 `v1.8.0` release docs 不要求 live HTTP / API-key dependent test。

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
