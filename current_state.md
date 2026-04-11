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
- latest_completed_phase: `Phase 20`
- latest_completed_slice: `Mock Dispatch & Execution Gating`
- checkpoint_type: `phase_closeout`
- last_checked: `2026-04-12`

说明：

- Phase 0 到 Phase 20 已完成并形成稳定 checkpoint
- post-Phase-2 retrieval baseline 已完成
- post-Phase-5 executor / external-input slice 已完成
- post-Phase-5 retrieval / memory-next slice 已完成
- 当前默认不再继续这些已收口阶段，而应从新的 kickoff 选择下一轮工作

---

## 当前默认继续方向

当前推荐从以下方向继续：

- active_track: `to_be_selected`
- active_phase: `none_selected`
- active_slice: `fresh_kickoff_required`

说明：

- 当前默认不再继续扩张已完成的 Phase 20，而应先重新选择下一轮 primary track
- 当前最近完成的 stop/go 边界以 `docs/plans/phase20/closeout.md` 为准

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `current_state.md`
4. `docs/system_tracks.md`
5. `docs/plans/phase20/closeout.md`

仅在需要时再读取：

- `docs/plans/phase20/kickoff.md`
- `docs/plans/phase20/breakdown.md`
- `docs/plans/phase20/review_comments.md`
- `docs/plans/phase19/closeout.md`
- `docs/plans/phase19/kickoff.md`
- `docs/plans/phase19/breakdown.md`
- `docs/plans/phase18/closeout.md`
- `docs/plans/phase18/kickoff.md`
- `docs/plans/phase18/breakdown.md`
- `docs/plans/phase17/kickoff.md`
- `docs/plans/phase17/breakdown.md`
- `docs/plans/phase16/kickoff.md`
- `docs/plans/phase16/breakdown.md`
- `docs/plans/phase15/kickoff.md`
- `docs/plans/phase15/breakdown.md`
- `docs/plans/phase14/kickoff.md`
- `docs/plans/phase14/breakdown.md`
- `docs/plans/phase13/kickoff.md`
- `docs/plans/phase13/breakdown.md`
- `docs/plans/phase12/kickoff.md`
- `docs/plans/phase12/breakdown.md`
- `docs/archive/*`
- 历史 phase closeout
- 旧 `post-phase-*` 归档材料

---

## 最小验证命令

恢复工作前，建议至少执行以下检查：

```bash
python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m swallow.cli --help
# 如需确认当前运行环境下的真实 executor 行为，可按需补充：
AIWF_EXECUTOR_TIMEOUT_SECONDS=10 PYTHONPATH=src python3 -m swallow.cli --base-dir /tmp/aiwf-exec-real task run <task-id>
```

---

## 当前已知问题
- 真实 codex exec 在当前环境中仍可能因 outbound network / WebSocket 受限而失败。
- 一些旧设计与历史文档仍保留了较重的 phase 历史叙述，后续应逐步收拢到 archive，不再作为默认读取入口。
- 当前 current_state.md 已重新定义为恢复入口，后续不应再把高频状态或完整历史继续堆回本文件。
- Phase 15 的 canonical reuse evaluation provenance 只在任务已有 `retrieval.json` 时附带，不应误解为当前 run loop 的强制前置条件。
- Phase 16 的 regression compare 目前仍是 task-local CLI/report surface，不应误解为当前系统已经建立全局 regression gate。
- Phase 17 的 regression attention 目前仍是 operator-facing CLI surface，不应误解为当前系统已经建立自动 mismatch gate。
- Phase 18 的 remote handoff contract 目前仍是 contract-truth / operator-facing baseline，不应误解为当前系统已经建立真实 remote execution 或 transport implementation。
- Phase 19 的 handoff schema unification 目前仍是 schema-truth / write-time validation baseline，不应误解为当前系统已经建立 handoff-driven execution gating、自动 dispatch 或 provider negotiation。
- Phase 20 的 mock dispatch & execution gating 目前仍是 topology-validation / mock execution baseline，不应误解为当前系统已经建立真实 remote worker execution、operator approval workflow 或 production remote dispatch。

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
sed -n '1,220p' current_state.md
```
然后按“恢复时优先读取”的顺序进入当前工作上下文。

---
