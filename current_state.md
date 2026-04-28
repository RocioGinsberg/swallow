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
- latest_main_checkpoint_phase: `Phase 61`
- latest_public_tag: `v1.3.0`
- current_working_phase: `Phase 62`
- checkpoint_type: `phase62_ready_for_human_merge_gate`
- active_branch: `feat/phase62-multi-perspective-synthesis`
- last_checked: `2026-04-29`

说明：

- `main` 已包含 Phase 61 merge(`c66fa87 merge: Refine codes after PRD change`):canonical knowledge / route metadata / policy 三类主写入收敛到 `apply_proposal()` governance boundary。
- `v1.3.0` 仍是当前公开 tag。Human 已确认后续 tag 决策为 `v1.3.1`,但 release docs / tag 命令尚未完成。
- 当前工作分支 `feat/phase62-multi-perspective-synthesis` 已完成 MPS 实装、Claude review 消化、closeout 与 `pr.md` 准备,等待 Human Merge Gate。

---

## 当前默认继续方向

当前推荐从以下状态继续：

- active_branch: `feat/phase62-multi-perspective-synthesis`
- active_track: `Orchestration`
- active_phase: `Phase 62`
- active_slice: `M1+M2+M3 + Review 消化 + Closeout 完成`
- workflow_status: `human_merge_gate_pending`

说明：

- 当前默认动作不是继续扩张 Phase 62,而是 Human 审阅 `pr.md` / `docs/plans/phase62/review_comments.md` / `docs/plans/phase62/closeout.md` 后决定是否合并。
- 若 Human 接受,应提交 review follow-up + closeout / PR body / state sync,创建或更新 PR,再进入 merge 决策。
- merge 后由 Codex 同步 `current_state.md` / `docs/active_context.md`,再由 Claude / roadmap-updater 更新 roadmap factual state。

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `current_state.md`
4. `.agents/shared/read_order.md`
5. `.agents/workflows/feature.md`
6. `.agents/workflows/tag_release.md`
7. `docs/design/INVARIANTS.md`
8. `docs/plans/phase62/review_comments.md`
9. `docs/plans/phase62/closeout.md`
10. `pr.md`

仅在需要时再读取：

- `CLAUDE.md`
- `.codex/session_bootstrap.md`
- `docs/concerns_backlog.md`
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

当前 Phase 62 merge 前最小验证命令：

```bash
.venv/bin/python -m pytest
git diff --check
```

---

## 当前已知边界

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
