# Current State

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
- latest_completed_phase: `Phase 44`
- latest_completed_slice: `Web Control Center Enhancement`
- checkpoint_type: `phase_closeout`
- last_checked: `2026-04-19`

说明：

- Phase 44 已完成实现、review、PR 与 merge，并已形成新的稳定 checkpoint。
- `docs/plans/phase44/closeout.md` 与 `docs/plans/phase44/review_comments.md` 已反映当前收口结论。
- 当前默认不再继续扩张已完成的 Phase 44，而应从 roadmap 重新选择下一轮方向。

---

## 当前默认继续方向

当前推荐从以下状态继续：

- active_track: `none_selected`
- active_phase: `none_selected`
- active_slice: `fresh_kickoff_required`

说明：

- 当前主线已经回到 `main` 的稳定基线。
- 下一轮工作应先依据 `docs/roadmap.md` 与新设计文档确认 active phase，再生成 kickoff / risk / slice 边界。

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/roadmap.md`
4. `docs/system_tracks.md`
5. `current_state.md`
6. `docs/plans/phase44/closeout.md`

仅在需要时再读取：

- `docs/plans/phase44/review_comments.md`
- `docs/concerns_backlog.md`
- `pr.md`
- 历史 phase closeout / review_comments

---

## 最小验证命令

恢复工作前，建议至少执行以下检查：

```bash
.venv/bin/python -m pytest
.venv/bin/python -m swallow.cli --help
```

---

## 当前已知边界

- Web Control Center 仍保持严格只读；不会写入 `.swl/`，也未引入前端构建工具链。
- Artifact compare 当前是纯文本双栏 compare，不包含结构化 diff 高亮或批注工作流。
- `meta-optimize` 仍是只读分析入口，不会自动采纳策略提案，也不会直接修改 route policy 或 task state。
- 真实执行环境下的外部网络、代理与 provider 连通性仍受本地环境约束，`swl doctor` 只负责诊断，不负责修复。
- 系统当前已具备多轮 debate retry 与 `waiting_human` 熔断，但尚未进入多 Reviewer 共识拓扑。

---

## 恢复命令

重新打开仓库后，可先执行：

```bash
cd /home/rocio/projects/swallow
sed -n '1,160p' current_state.md
```

然后按“恢复时优先读取”的顺序进入当前工作上下文。
