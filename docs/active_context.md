# Active Context

## 当前轮次

- latest_completed_track: `Core Loop` (Primary) + `Execution Topology` (Secondary)
- latest_completed_phase: `Phase 31`
- latest_completed_slice: `Runtime v0 — Planner + Executor Interface + Review Gate`
- active_track: `none_selected`
- active_phase: `none_selected`
- active_slice: `fresh_kickoff_required`
- active_branch: `main`
- status: `direction_gate_pending`

---

## 当前状态说明

Phase 31 已完成 merge，并已回到 `main`。当前默认入口不再是 Phase 31 的实现或收口，而是**下一轮方向选择 / kickoff 前状态**。

Phase 31 已形成的稳定 checkpoint：

- 引入 `TaskCard` 与规则驱动 `Planner v0`
- 建立 `ExecutorProtocol` 统一执行器接口
- 在 `run_task()` 中接入非阻断 `ReviewGate`
- 补齐 `task.planned` / `task.review_gate` 运行期可观测性

当前默认不应继续在 `main` 上顺手扩张：

- 1:N TaskCard 拆解
- ReviewGate 阻断 completion / retry
- 动态 executor negotiation / fallback matrix
- 多卡并发编排 / Subtask Orchestrator

下一轮应回到 `docs/roadmap.md` 和 `docs/system_tracks.md` 重新选择方向，再启动新的正式 kickoff。

---

## 当前关键文档

下一轮开始前，优先读取：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/roadmap.md`
4. `docs/system_tracks.md`
5. `current_state.md`
6. `docs/plans/phase31/closeout.md`

---

## Gateway 融合（2026-04-16，Claude 独立执行）

将 `docs/design_gateway.md` 的架构哲学内化至长期设计蓝图，核心变更：

- `ARCHITECTURE.md`：第6层重命名为"模型网关层"，Mermaid图引入 Strategy Router 分离，§3.5 完整重写
- `PROVIDER_ROUTER_AND_NEGOTIATION.md`：新增 §0 Gateway 设计哲学，§4.1 降级矩阵拆分为纯执行级
- `ORCHESTRATION_AND_HANDOFF_DESIGN.md`：§2.1 Router 扩充为 Strategy Router（承接能力下限断言），§2.4.1 新增降级联动规则
- `SELF_EVOLUTION_AND_MEMORY.md`：Meta-Optimizer 新增第4项扫描职责 + 路由遥测数据接口契约
- 新建 `docs/design/GATEWAY_PHILOSOPHY.md`（演化阶段论、治理壳、边界清单、反模式速查）
- 融合方案总览：`docs/plans/gateway_fusion/00_overview.md`
- 技术选型写入：`PROVIDER_ROUTER_AND_NEGOTIATION.md` §5（TensorZero 首选 / Portkey 备选 / LiteLLM 排除 / Cloudflare 远期治理壳）

---

## 当前产出物
- `docs/roadmap.md` (gemini+claude, 2026-04-15) — 差距分析 + 5-Phase 路线图 + 推荐队列优先级排序与风险批注
- `docs/plans/phase31/kickoff.md` (claude, 2026-04-15) — Phase 31 kickoff (approved)
- `docs/plans/phase31/design_decision.md` (claude, 2026-04-15) — 方案拆解：3 slice，三段式重构
- `docs/plans/phase31/risk_assessment.md` (claude, 2026-04-15) — 风险评估：总分 15/27，中等风险
- `docs/plans/phase31/review_comments.md` (claude, 2026-04-16) — PR review: Merge ready, 0 BLOCK, 0 CONCERN
- `docs/plans/phase31/closeout.md` (codex, 2026-04-16) — Phase 31 closeout: PR ready, stop/go 边界与稳定 checkpoint

## 当前推进

已完成：

- **[Human]** 已完成 Phase 31 merge，并切换回 `main`。
- **[Codex]** 已将入口文档切换到“下一阶段启动前”状态。

## 下一步

- **[Human]** 从 `docs/roadmap.md` 选择下一轮方向
- **[Gemini / Claude]** 如有需要，刷新 roadmap 优先级与方向判断
- **[Human]** 确认下一 phase 方向后启动新的 kickoff
