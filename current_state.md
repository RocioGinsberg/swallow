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
- latest_completed_phase: `Phase 27`
- latest_completed_slice: `Knowledge-Driven Task Grounding Baseline`
- checkpoint_type: `phase_closeout`
- last_checked: `2026-04-13`

说明：

- Phase 0 到 Phase 27 已完成并形成稳定 checkpoint
- 当前默认不再继续扩张已完成的 Phase 27，而应从新的 kickoff 选择下一轮工作。

---

## 当前默认继续方向

当前推荐从以下状态继续：

- active_track: `none_selected`
- active_phase: `none_selected`
- active_slice: `fresh_kickoff_required`

说明：

- Phase 27 已完成 grounding artifact、grounding refs 锁定与 operator-facing grounding 可视化。
- 下一轮应重新从 `docs/system_tracks.md` 选择方向，再写新的 kickoff 与 breakdown。

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `current_state.md`
4. `docs/system_tracks.md`
5. `docs/plans/phase27/closeout.md`

仅在需要时再读取：

- `docs/plans/phase27/context_brief.md`
- `docs/plans/phase27/design_decision.md`
- `docs/plans/phase27/risk_assessment.md`
- `docs/plans/phase27/review_comments.md`
- `docs/plans/phase26/closeout.md`
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
- Phase 23 仅补齐 operator-facing taxonomy visibility，不应误解为系统已经建立 taxonomy-aware route selection、权限审批流增强或更复杂的 UI 层。
- Phase 24 仅建立 staged knowledge pipeline baseline，不应误解为系统已经具备 staged 自动晋升、staged retrieval integration、跨任务候选合并或复杂 review workflow。
- Phase 25 仅建立 runtime capability enforcement baseline，不应误解为系统已经具备动态策略引擎、manifest 级 capability pruning 或完整策略治理平台。
- Phase 26 仅建立 canonical registry 的 metadata-key dedupe、supersede 提示与 audit baseline，不应误解为系统已经具备语义合并、自动冲突解决或全自动 canonical promotion。
- Phase 27 仅建立 grounding artifact、grounding 锁定与 operator-facing grounding surface，不应误解为系统已经具备向量 grounding、prompt 直注入 canonical knowledge 或复杂 Agentic RAG。

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
