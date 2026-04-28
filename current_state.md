# Current State

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: phase 收口、main 稳定 checkpoint 变化、恢复入口变化、公开 tag 变化
> Anti-scope: 不维护高频推进状态、不复制 roadmap 队列、不替代 closeout 作为 phase 历史

## 文档目的

本文件用于在终端会话中断、重新打开仓库或切换设备后，快速恢复到当前稳定工作位置。

它回答的问题是：

- 当前最近的稳定 checkpoint 是什么
- 当前默认应从哪里继续
- 恢复前需要先看哪些文件
- 最小验证命令是什么
- 当前已知边界是什么

当前高频状态请看：

- `docs/active_context.md`

---

## 当前稳定 checkpoint

- repository_state: `runnable`
- latest_main_checkpoint_phase: `Phase 62`
- latest_public_tag: `v1.3.1`
- current_working_phase: `Release v1.3.1`
- checkpoint_type: `v1.3.1_tag_completed`
- active_branch: `main`
- last_checked: `2026-04-29`

说明：

- `main` 已包含 Phase 62 merge(`ce98f92 merge: Complete Refine codes after PRD change`):Multi-Perspective Synthesis(MPS) 的 Path A participant / arbiter 编排、MPS policy、仲裁 artifact 与 explicit staged handoff 已落地。
- `v1.3.1` tag 已完成,覆盖 `v1.3.0` 之后的 Phase 60 / 61 / 62 稳定成果。tag message:`v1.3.1: Governance boundary and multi-perspective synthesis`;tag 指向 release docs commit `d6e4b90`。
- 当前默认动作是进入下一轮 direction / phase 决策,不要继续扩张 Phase 62。

---

## 当前默认继续方向

当前推荐从以下状态继续：

- active_branch: `main`
- active_track: `Release`
- active_phase: `v1.3.1`
- active_slice: `Tag Completed`
- workflow_status: `v1.3.1_tag_completed`

说明：

- 当前默认动作不是继续扩张 Phase 62,而是进入下一轮 direction / phase 决策。
- release docs 已同步并提交;tag preflight `.venv/bin/python -m pytest` 已通过(559 passed / 8 deselected)。
- tag result 已同步到 `docs/active_context.md`;后续若进入新 phase,先更新 active_context 的 active track / phase / slice。

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `current_state.md`
4. `.agents/shared/read_order.md`
5. `.agents/workflows/tag_release.md`
6. `.agents/workflows/feature.md`
7. `docs/design/INVARIANTS.md`
8. `docs/plans/phase62/closeout.md`
9. `README.md`
10. `docs/roadmap.md`

仅在需要时再读取：

- `CLAUDE.md`
- `.codex/session_bootstrap.md`
- `docs/concerns_backlog.md`
- `docs/plans/phase62/review_comments.md`
- `docs/plans/phase61/closeout.md`
- 历史 phase closeout / review_comments / archive 文档

---

## 最小验证命令

恢复工作前，建议至少执行以下检查：

```bash
git status --short
git branch --show-current
git show --no-patch --decorate --oneline HEAD
git log --oneline --decorate -8
git tag --list 'v*' --sort=-creatordate | head -n 5
```

当前 tag 后恢复验证命令：

```bash
.venv/bin/python -m pytest
git diff --check
```

---

## 当前已知边界

- `v1.3.1` tag 已完成;不要删除或重打该 tag。
- Phase 62 不引入 Planner 自动路由到 MPS;MPS 当前仅通过 `swl synthesis` CLI 显式触发。
- Phase 62 不给 Orchestrator 新增 stagedK 写权限;`swl synthesis stage` 是 Operator CLI 路径。
- Phase 62 不实现自动 knowledge promotion;仲裁结果只进入 staged review。
- MPS Path A 默认 route 使用 `local-http`;不要把 Path B 的 `local-claude-code` 当作 HTTP Path A route。
- Phase 62 audit 已登记的 `orchestrator.py` librarian-side-effect 等价 stagedK 直写路径仍为 Open concern。
- INVARIANTS §7 提及的 `swallow.identity.local_actor()` / `swallow.workspace.resolve_path()` 实际缺失仍为 Open concern。
- `docs/design/` 是产品设计真相源;协作规则、release sync 和状态信息不应在 `AGENTS.md` 里重复维护副本。
- README 当前为单文件双语结构;不要再要求同步不存在的 `README.zh-CN.md`。

---

## 本地基础设施

Phase 46 依赖的 Docker 栈位于 `~/ai-stack/`，与仓库分离。

```bash
cd ~/ai-stack
docker compose up -d new-api
docker compose up -d openwebui
docker compose ps
```

验证 new-api 可达：

```bash
curl http://localhost:3000/api/status
```

---

## 恢复命令

重新打开仓库后，可先执行：

```bash
cd /home/rocio/projects/swallow
sed -n '1,220p' docs/active_context.md
sed -n '1,240p' AGENTS.md
sed -n '1,220p' current_state.md
```

然后按“恢复时优先读取”的顺序进入当前工作上下文。
