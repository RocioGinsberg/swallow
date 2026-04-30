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
- latest_main_checkpoint_phase: `Phase 65`
- latest_executed_public_tag: `v1.4.0`
- pending_release_tag: `none`
- current_working_phase: `Release v1.4.0`
- checkpoint_type: `v1.4.0_tag_completed`
- active_branch: `main`
- last_checked: `2026-04-30`

说明：

- `main` 已包含 Phase 65 merge(`64cbba7 merge: Truth Plane SQLite Transfer`)。
- Phase 65 完成 Governance 三段闭合中的候选 H：route metadata / policy truth 迁入 SQLite,`apply_proposal` route/policy 写入由显式 `BEGIN IMMEDIATE` transaction 保护,并新增 `route_change_log` / `policy_change_log` append-only audit log。
- `docs/roadmap.md` 已完成 Phase 65 post-merge factual update。
- `v1.4.0` annotated tag 已完成,tag message:`v1.4.0: Governance boundary and SQLite truth closure`;tag 指向 release docs commit `5ec637f`。
- 当前 `main` HEAD 为 `c95eb86 docs(state): uodate roadmap to framework closure era`,位于 `v1.4.0` tag 之后。
- 当前默认动作是进入下一轮 Direction Gate / phase 决策,不要继续扩张 Phase 65。

---

## 当前默认继续方向

当前推荐从以下状态继续：

- active_branch: `main`
- active_track: `Release`
- active_phase: `v1.4.0`
- active_slice: `Tag Completed`
- workflow_status: `v1.4.0_tag_completed`

说明：

- Phase 63 + Phase 64 + Phase 65 合并后形成治理三段完整闭合：
  - Phase 63:治理守卫收口、Repository 抽象层、§7 集中化函数、apply_proposal 写边界。
  - Phase 64:NO_SKIP 红灯修复、Path B fallback selection 归位、Specialist Internal 调用穿透 Provider Router、route metadata/policy 外部化。
  - Phase 65:route/policy truth SQLite 化、事务回滚与 append-only audit log。
- `v1.4.0` 是 minor bump,主题为 Governance boundary + SQLite truth closure。
- 当前应进入下一轮 Direction Gate。当前 roadmap 推荐候选包括代码卫生 audit(K)、真实使用反馈观察(R)、以及后置编排增强(D)。

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
8. `docs/plans/phase65/closeout.md`
9. `README.md`
10. `docs/roadmap.md`

仅在需要时再读取：

- `CLAUDE.md`
- `.codex/session_bootstrap.md`
- `docs/concerns_backlog.md`
- `docs/plans/phase65/review_comments.md`
- `docs/plans/phase64/closeout.md`
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
.venv/bin/python -m pytest -q
git diff --check
git diff -- docs/design/INVARIANTS.md
```

Phase 65 最近一次完整验证：

```bash
.venv/bin/python -m pytest -q
# 610 passed, 8 deselected, 10 subtests passed

.venv/bin/python tests/audit_no_skip_drift.py
# all 8 tracked guards green
```

---

## 当前已知边界

- `v1.4.0` tag 已完成；不要删除或重打该 tag。
- 不删除、不重打历史 tag。
- `docs/design/INVARIANTS.md` 在 Phase 65 中未修改。
- `route_fallbacks.json` 仍是 operator-local config seam,不属于 SQLite truth 迁移范围。
- Review record application artifact 写在 SQLite transaction 外；Phase 65 已将失败语义收敛为 warning-only,后续如需更强语义可设计 outbox / stale marker。
- `route_change_log` / `policy_change_log` 目前存完整 JSON snapshot,无 size cap / truncation policy；超大 payload 写入失败时整体 rollback 是 intentional。
- Phase 65 只建立 initial `schema_version=1` 与 `swl migrate --status`;真正 v1 -> v2 migration runner 留到首次 schema upgrade phase。
- `events` / `event_log` 历史 backfill 仍为 Open concern,不属于 Phase 65。
- durable proposal artifact lifecycle 仍未实现；`PendingProposalRepo` 仍为进程内 proposal registry。
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
