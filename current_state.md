# Current State

## 文档目的

本文件用于在终端会话中断、重新打开仓库或切换设备后，**快速恢复到当前稳定工作位置**。

它回答的问题是：

- 当前最近的稳定 checkpoint 是什么
- 当前默认应从哪里继续
- 恢复前需要先看哪些文件
- 最小验证命令是什么
- 当前已知问题是什么

本文件不是：

- 完整开发编年史
- 当前高频状态板
- 当前 phase 的详细 breakdown
- 历史 phase 索引页

当前高频状态请看：

- `docs/active_context.md`

当前 phase 计划请看：

- `docs/plans/<active-phase>/kickoff.md`
- `docs/plans/<active-phase>/breakdown.md`
- `docs/plans/<active-phase>/closeout.md`

---

## 当前稳定 checkpoint

- repository_state: `runnable`
- latest_completed_phase: `Phase 22`
- latest_completed_slice: `Taxonomy-Aware Routing Baseline`
- checkpoint_type: `phase_closeout`
- last_checked: `2026-04-12`

说明：

- Phase 0 到 Phase 22 已完成并形成稳定 checkpoint
- 当前默认不再继续扩张已完成的 Phase 22，而应从新的 kickoff 选择下一轮工作。

---

## 当前默认继续方向

当前推荐从以下方向继续：

- active_track: `Workbench / UX` (Primary) + `Execution Topology` (Secondary)
- active_phase: `Phase 23`
- active_slice: `Taxonomy Visibility in CLI Surfaces`

说明：

- 当前已基于 Phase 22 完成的 Taxonomy 元数据基础，开展操作员视图层面的可见性提升。
- 新的 planning 已在 `docs/plans/phase23/context_brief.md` 起草。

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `current_state.md`
4. `docs/system_tracks.md`
5. `docs/plans/phase23/context_brief.md`

仅在需要时再读取：

- `docs/plans/phase22/closeout.md`
- `docs/plans/phase22/review_comments.md`
- `docs/archive/*`
- 历史 phase closeout

---

## 最小验证命令

恢复工作前，建议至少执行以下检查：

```bash
.venv/bin/python -m pytest
.venv/bin/python -m swallow.cli --help
```

---

## 当前已知问题
- 真实 codex exec 在当前环境中仍可能因 outbound network / WebSocket 受限而失败。
- Phase 22 的 taxonomy-aware routing baseline 目前仍是 taxonomy metadata + defensive dispatch guard baseline，不应误解为当前系统已经建立完整 RBAC、动态 taxonomy 注册、capability negotiation 或全量权限治理。

## 当前收口规则
- 在 phase 或 major slice 收口时，本文件才需要更新。
- 平时开发过程中，不应把高频状态写入本文件。

- 本文件更新时，通常检查以下内容是否变化：
  - 最新稳定 checkpoint
  - 最近完成的 phase
  - 当前默认继续方向
  - 恢复时优先读取文件
  - 最小验证命令
  - 已知问题

如果这些内容没有变化，不需要更新本文件。

## 恢复命令

重新打开仓库后，可先执行：
```bash
cd /home/rocio/projects/swallow
sed -n '1,120p' current_state.md
```
然后按“恢复时优先读取”的顺序进入当前工作上下文。

---