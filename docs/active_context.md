# Active Context

## 当前轮次

- latest_completed_track: `Execution Topology` (Primary) + `Core Loop` (Secondary)
- latest_completed_phase: `Phase 33`
- latest_completed_slice: `Subtask Orchestrator + 并发编排 (1:N Planner + Review Feedback Loop)`
- active_track: `Execution Topology` (Primary) + `Evaluation / Policy` (Secondary)
- active_phase: `Phase 34`
- active_slice: `S3_binary_fallback_complete`
- active_branch: `feat/phase34-strategy-router`
- status: `implementation_completed_waiting_human_review`

---

## 当前状态说明

Phase 33 已完成实现、review、review follow-up、closeout 与 merge。Phase 34 方案已获 Human 批准，当前仓库已切到 `feat/phase34-strategy-router`，实现与验证已完成，等待人工审查与 commit gate。

Phase 34 的核心目标是升级编排层的 Strategy Router（能力匹配选路）和网关层本地侧的 Dialect Adapters（方言翻译），并建立最简二元降级机制。当前已完成 kickoff 中的 S1 `RouteRegistry + Strategy Router`、S2 `Dialect Adapters`、S3 `Binary Fallback`，并通过全量 `pytest` 与 CLI 入口回归。注意：本轮不涉及 Provider Connector 层（new-api / TensorZero）的实际部署。

---

## 当前关键文档

下一轮开始前，优先读取：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/roadmap.md`
4. `docs/system_tracks.md`
5. `current_state.md`
6. `docs/plans/phase34/kickoff.md`

---

## Phase 34 前设计文档更新（2026-04-17，Claude 独立执行）

基于 Human 的四个方向性问题，更新了以下设计文档：

- `AGENT_TAXONOMY_DESIGN.md` §7.1：新增"同角色多执行器并存"说明（Codex + Cursor 等可共存，Strategy Router 决定路由）
- `PROVIDER_ROUTER_AND_NEGOTIATION.md` §5.1-5.2：Provider Connector 从 TensorZero 单选改为双层架构（new-api 渠道管理 + TensorZero 推理优化，可共存或只用 new-api 起步）
- `INTERACTION_AND_WORKBENCH.md` §4：新增"AI 聊天面板定位"（Open WebUI 推荐，严格限制为探索性对话 surface，不参与编排）
- `docs/roadmap.md` Phase 34：降级矩阵措辞更新为 Strategy Router + Gateway 协作，补充多执行器并存 PoC 建议

---

## 当前产出物

- `docs/plans/phase34/kickoff.md` (claude, 2026-04-17) — Phase 34 kickoff: 3 slice，RouteRegistry + Dialect Adapters + Binary Fallback，风险 6/15 低
- `docs/plans/phase34/context_brief.md` (gemini, 2026-04-17) — Phase 34 目标总结与变更范围界定
- `src/swallow/router.py` (codex, 2026-04-17) — S1: RouteRegistry + Strategy Router 能力匹配选路与 fallback route 解析
- `src/swallow/executor.py` (codex, 2026-04-17) — S2: dialect registry 接入 Claude XML / Codex FIM
- `src/swallow/orchestrator.py` (codex, 2026-04-17) — S3: binary fallback 执行路径、事件与 fallback 工件保留
- `src/swallow/dialect_adapters/__init__.py` (codex, 2026-04-17) — Phase 34 dialect adapters 包入口
- `src/swallow/dialect_adapters/claude_xml.py` (codex, 2026-04-17) — Claude XML adapter
- `src/swallow/dialect_adapters/codex_fim.py` (codex, 2026-04-17) — Codex FIM adapter
- `tests/test_router.py` (codex, 2026-04-17) — S1 路由注册表与优先级测试
- `tests/test_dialect_adapters.py` (codex, 2026-04-17) — S2 dialect adapter 测试
- `tests/test_binary_fallback.py` (codex, 2026-04-17) — S3 binary fallback 集成测试
- `tests/test_cli.py` (codex, 2026-04-17) — Phase 34 回归断言更新（dialect / fallback / lifecycle）
- `docs/plans/phase33/review_comments.md` (claude, 2026-04-17) — PR review: Merge ready, 0 BLOCK, 1 CONCERN, 0 NOTE
- `docs/plans/phase33/closeout.md` (codex, 2026-04-17) — Phase 33 closeout: merge ready, 范围收口与稳定边界确认
- `docs/plans/phase33/kickoff.md` (claude, 2026-04-16) — Phase 33 kickoff: 3 slice，1:N Planner + SubtaskOrchestrator + Review Feedback Loop
- `docs/plans/phase33/context_brief.md` (gemini, 2026-04-16) — Phase 33 目标总结与变更范围界定
- `pr.md` (codex, 2026-04-17, ignored) — Phase 33 PR 文案，本地草稿

---

## 当前推进

已完成：

- **[Human]** 已完成 Phase 33 merge，并审批 Phase 34 kickoff。
- **[Human]** 已切出实现分支 `feat/phase34-strategy-router`。
- **[Claude]** 已完成 Phase 34 前设计文档更新（多执行器并存 / Gateway 选型 / 聊天面板定位 / roadmap 措辞）。
- **[Gemini]** 已根据 roadmap 选定 Phase 34 方向并产出 context_brief。
- **[Claude]** 已完成 Phase 34 kickoff 撰写（3 slice 方案拆解 + 风险 6/15）。
- **[Codex]** 已完成 S1：`RouteRegistry + Strategy Router`，建立 RouteRegistry、能力匹配选路与 fallback route 解析。
- **[Codex]** 已完成 S2：`Dialect Adapters`，落地 Claude XML / Codex FIM 并接入默认 codex 路由。
- **[Codex]** 已完成 S3：`Binary Fallback`，主路由失败后切换到 route-level fallback，并保留 `fallback_*` 工件与 `task.execution_fallback` 事件。
- **[Codex]** 已完成验证：`.venv/bin/python -m pytest` 通过（244 passed），`.venv/bin/python -m swallow.cli --help` 正常。

## 下一步

- **[Human]** 审查 Phase 34 当前 diff，确认 S1/S2/S3 是否按 slice 拆 commit 或作为单次实现提交落地
- **[Human]** 执行实现提交，并在需要时通知 Codex 继续整理 `pr.md` / closeout

## 当前阻塞项

- 等待人工审查: Phase 34 实现 diff 与 commit 切分决策
