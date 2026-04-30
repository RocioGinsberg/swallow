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
- latest_main_checkpoint_phase: `Phase 66`
- latest_executed_public_tag: `v1.4.0`
- pending_release_tag: `none`
- current_working_phase: `Post-Phase 66 roadmap update`
- checkpoint_type: `phase66_merged`
- active_branch: `main`
- last_checked: `2026-04-30`

说明：

- `main` 已包含 Phase 66 merge:`596b54b merge: read-only code hygiene audit of project`。
- Phase 66 完成 roadmap 候选 K:对 `src/swallow/` 的严格 read-only code hygiene audit。
- Phase 66 audit 统计:75 Python files / 30954 LOC / 46 findings / 2 high / 36 med / 8 low。
- Phase 66 产出 5 份 block report、`audit_index.md`、3 份 milestone review、`closeout.md` 与 backlog theme updates。
- Phase 66 未修改 `src/`、`tests/`、`docs/design/`。
- 最新公开 tag 仍为 `v1.4.0`;Phase 66 kickoff 明确 audit-only 默认不打 release tag。
- 当前默认动作是 post-merge factual update:先由 Claude/roadmap-updater 更新 `docs/roadmap.md`,再进入下一轮 Direction Gate / phase 决策。

---

## 当前默认继续方向

当前推荐从以下状态继续：

- active_branch: `main`
- active_track: `Post-merge`
- active_phase: `Phase 66`
- active_slice: `Roadmap factual update pending`
- workflow_status: `phase66_merged_pending_roadmap_update`

说明：

- Phase 66 已 merge,不应继续扩张该 phase 的 audit scope。
- 后续清理不能把 46 个 finding 合并成一个大 refactor；应按 `audit_index.md` 的 quick-win 与 design-needed 分组进入后续 Direction Gate。
- Phase 66 自身不构成 capability-bearing release 节点；若 Human 想打 tag,应先由 Claude 做 tag assessment。
- `docs/roadmap.md` 仍需 post-merge factual update,将候选 K 标记为已完成/已消化并引用 Phase 66 closeout 与 audit index。

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `current_state.md`
4. `.agents/shared/read_order.md`
5. `.agents/shared/state_sync_rules.md`
6. `docs/design/INVARIANTS.md`
7. `docs/plans/phase66/closeout.md`
8. `docs/plans/phase66/audit_index.md`
9. `docs/plans/phase66/review_comments_block2_index.md`
10. `docs/concerns_backlog.md`
11. `docs/roadmap.md`

仅在需要时再读取：

- `CLAUDE.md`
- `.codex/session_bootstrap.md`
- `.agents/workflows/feature.md`
- `.agents/workflows/tag_release.md`
- `docs/plans/phase66/kickoff.md`
- `docs/plans/phase66/design_decision.md`
- `docs/plans/phase66/risk_assessment.md`
- Phase 66 block audit reports
- 历史 phase closeout / review_comments / archive 文档

---

## 最小验证命令

恢复工作前，建议至少执行以下检查：

```bash
git status --short --branch
git branch --show-current
git show --no-patch --decorate --oneline HEAD
git log --oneline --decorate -8
git tag --list 'v*' --sort=-creatordate | head -n 5
```

当前 post-merge 状态同步验证命令：

```bash
git diff --check
git diff -- src tests docs/design
git status --short --branch
```

Phase 66 最近一次 closeout 验证：

```bash
git diff --check
# passed

git diff -- src tests docs/design
# no output
```

最近一次完整 pytest baseline 仍来自 Phase 65 / v1.4.0 checkpoint：

```bash
.venv/bin/python -m pytest -q
# 610 passed, 8 deselected, 10 subtests passed

.venv/bin/python tests/audit_no_skip_drift.py
# all 8 tracked guards green
```

Phase 66 是 read-only audit phase,未新增或修改 runtime behavior,因此 closeout 未要求重新跑 pytest。

---

## 当前已知边界

- `v1.4.0` tag 已完成；不要删除或重打该 tag。
- Phase 66 已 merge 到 `main`;不要回头扩张 Phase 66 audit scope。
- Phase 66 kickoff guidance:默认不打新 release tag,除非 Human 另行要求并经过 Claude tag assessment。
- Phase 66 findings 是后续 phase 输入材料,不是当前 phase 内可顺手修复的待办。
- `docs/roadmap.md` 尚需 post-merge factual update,由 Claude/roadmap-updater 负责。
- `docs/design/INVARIANTS.md` / `docs/design/DATA_MODEL.md` 在 Phase 66 中未修改。
- Phase 65 carry-forward known gaps 仍以 `docs/concerns_backlog.md` 与 `docs/plans/phase65/closeout.md` 为权威来源；Phase 66 audit 未消化这些实现债。
- 不主动推进多租户、分布式 worker、云端 truth 镜像或无边界 UI 扩张。
- 不绕过 `apply_proposal` 直接写 canonical / route / policy。
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
