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

- repository_state: `phase32_pr_ready`
- latest_completed_phase: `Phase 31`
- latest_completed_slice: `Runtime v0 — Planner + Executor Interface + Review Gate`
- checkpoint_type: `phase31_stable + phase32_pr_ready`
- last_checked: `2026-04-16`

说明：

- Phase 0 到 Phase 31 已完成并形成稳定 checkpoint
- Phase 32 已完成实现、测试、review 与 closeout，当前处于 `feat/phase32-knowledge-dual-layer` 的 PR ready 状态，尚未 merge 回 `main`
- 当前主线稳定 checkpoint 仍是 Phase 31；Phase 32 的 merge gate 由人工执行

---

## 当前默认继续方向

当前推荐从以下状态继续：

- active_track: `Retrieval / Memory`
- active_phase: `Phase 32`
- active_slice: `Closeout + Merge Gate`

说明：

- Phase 32 已完成双层知识存储、canonical promotion authority 校验与 LibrarianExecutor 集成。
- 当前默认不是继续改代码，而是：
  1. 阅读 `docs/plans/phase32/closeout.md`
  2. 阅读 `docs/plans/phase32/review_comments.md`
  3. 使用根目录 `pr.md` 创建或更新 PR 描述
  4. 由 Human 执行 merge gate
- merge 完成后，再切回下一轮 kickoff 入口状态。

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/plans/phase32/closeout.md`
4. `docs/plans/phase32/review_comments.md`
5. `docs/roadmap.md`
6. `current_state.md`

仅在需要时再读取：

- `pr.md`
- `docs/plans/phase32/kickoff.md`
- `docs/plans/phase32/context_brief.md`
- `docs/plans/phase31/design_decision.md`
- `docs/plans/phase31/risk_assessment.md`
- `docs/plans/phase31/review_comments.md`
- `docs/plans/phase30/design_decision.md`
- `docs/plans/phase30/risk_assessment.md`
- `docs/plans/phase30/review_comments.md`
- `docs/plans/phase28/context_brief.md`
- `docs/plans/phase28/design_decision.md`
- `docs/plans/phase28/risk_assessment.md`
- `docs/plans/phase28/review_comments.md`
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
git log --oneline main..HEAD
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
- Phase 28 仅建立 staged knowledge promotion 的 CLI 聚合浏览、人工精炼晋升与 supersede 显式确认 baseline，不应误解为系统已经具备自动晋升、批量晋升、语义 dedupe 或复杂 canonical merge workflow。
- Phase 29 仅建立 provider dialect adapter、structured markdown prompt 变体与 dialect 可观测性 baseline，不应误解为系统已经具备 provider API 直连、runtime dialect negotiation、Claude XML dialect 或更复杂的 provider negotiation pipeline。
- Phase 30 仅建立 phase-level checkpoint、selective retry 与 operator-facing checkpoint visibility baseline，不应误解为系统已经具备 step-level pause/resume、独立 phase 子命令、跨任务 checkpoint 或更复杂的 recovery policy engine。
- Phase 31 仅建立 Runtime v0 的 TaskCard + Planner、ExecutorProtocol 与非阻断 ReviewGate baseline，不应误解为系统已经具备 1:N planner 拆解、动态 executor negotiation、ReviewGate 阻断 completion、multi-card 并发编排或 fallback matrix。
- Phase 32 仅建立 Evidence/Wiki 双层存储、canonical promotion authority 防线与规则驱动 LibrarianExecutor baseline，不应误解为系统已经具备外部会话摄入、向量检索、Librarian 语义提纯、staged 自动晋升或 canonical 冲突仲裁。

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
然后按“恢复时优先读取”的顺序进入当前工作上下文；如果 Phase 32 仍未 merge，优先完成 PR / merge gate，而不是继续扩张实现范围。

---
