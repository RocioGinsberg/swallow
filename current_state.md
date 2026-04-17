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

当前 phase 收口材料请看：

- `docs/plans/<phase>/closeout.md`
- `docs/plans/<phase>/review_comments.md`
- `pr.md`

---

## 当前稳定 checkpoint

- repository_state: `runnable`
- latest_completed_phase: `Phase 37`
- latest_completed_slice: `Control Center Baseline`
- checkpoint_type: `phase_closeout`
- last_checked: `2026-04-18`

说明：

- Phase 37 仍是当前已 merge 的最新稳定 checkpoint
- `docs/plans/phase37/closeout.md` 与 `docs/plans/phase37/review_comments.md` 已反映当前 merged / closeout 完成状态
- Phase 38 已在 `feat/phase38-cost-telemetry` 上完成实现与 slice 拆 commit，但尚未进入 review / merge，因此还不是新的 stable checkpoint

---

## 当前默认继续方向

当前推荐从以下状态继续：

- active_track: `Execution Topology` (Primary) + `Evaluation / Policy` (Secondary)
- active_phase: `Phase 38`
- active_slice: `review_pending`

说明：

- Phase 38 已完成实现，当前在 `feat/phase38-cost-telemetry`
- 下一步不是重新 kickoff，而是先完成 review、review follow-up（如有）与 merge 决策

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/roadmap.md`
4. `docs/system_tracks.md`
5. `current_state.md`
6. `docs/plans/phase38/closeout.md`

仅在需要时再读取：

- `docs/plans/phase38/kickoff.md`
- `docs/plans/phase38/review_comments.md`
- `docs/plans/phase37/review_comments.md`
- `docs/plans/phase37/kickoff.md`
- `pr.md`
- `docs/plans/phase36/closeout.md`
- `docs/plans/phase36/review_comments.md`
- `docs/concerns_backlog.md`
- `docs/plans/phase35/closeout.md`
- `docs/plans/phase35/kickoff.md`
- `docs/plans/phase35/context_brief.md`
- `docs/roadmap.md`
- `docs/system_tracks.md`
- `docs/plans/phase34/closeout.md`
- `docs/plans/phase34/review_comments.md`
- `docs/plans/phase34/kickoff.md`
- `docs/plans/phase34/context_brief.md`
- `docs/plans/phase33/closeout.md`
- `docs/plans/phase33/review_comments.md`
- `docs/plans/phase32/closeout.md`
- `docs/plans/phase32/review_comments.md`
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
.venv/bin/python -m swallow.cli --help
```

---

## 当前已知问题

- `_apply_librarian_side_effects()` 当前仍是顺序持久化 + 索引重建，若中途失败可能导致 state 与 index 不一致；该 concern 已记录在 `docs/concerns_backlog.md`。
- 遥测 schema 当前的 `token_cost` 仍是本地估算，不代表真实 provider billing。
- `meta-optimize` 当前为只读分析入口，不会自动采纳提案，也不会直接修改 route policy 或 task state。
- `StaticCostEstimator` 的定价表是硬编码常量，后续需要独立 phase 才能切到 provider usage 驱动。
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
- Phase 33 仅建立有界 1:N Planner、SubtaskOrchestrator、ReviewGate 单次 retry 闭环与父任务级 artifact/event 聚合 baseline，不应误解为系统已经具备 Debate Topology、Literature Specialist、动态 executor negotiation、stateful 多卡写回或并发 knowledge_store 写保护。
- Phase 34 仅建立 capability-aware Strategy Router、Claude XML / Codex FIM concrete dialect 与 route-level binary fallback baseline，不应误解为系统已经具备 provider connector 部署、链式降级矩阵、运行时健康探测、成本感知路由或动态 negotiation。
- Phase 35 仅建立 executor telemetry、只读 Meta-Optimizer 提案与共享 dialect prompt data layer，不应误解为系统已经具备自动提案采纳、runtime optimizer feedback loop 或 provider-side performance control plane。
- Phase 38 仅建立本地估算的 cost telemetry baseline、Meta-Optimizer 成本维度与可替换 `CostEstimator` 接口，不应误解为系统已经具备 provider connector 部署、真实 usage/billing 对账、在线定价同步或自动成本感知路由。

## 当前收口规则

- 在 phase 或 major slice 收口时，本文件才需要更新。
- 平时开发过程中，不应把高频状态写入本文件。

本文件更新时，通常检查以下内容是否变化：

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
sed -n '1,140p' current_state.md
```

然后按“恢复时优先读取”的顺序进入当前工作上下文。

---
