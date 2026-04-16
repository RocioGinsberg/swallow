# Active Context

## 当前轮次

- latest_completed_track: `Core Loop` (Primary) + `Execution Topology` (Secondary)
- latest_completed_phase: `Phase 31`
- latest_completed_slice: `Runtime v0 — Planner + Executor Interface + Review Gate`
- active_track: `Retrieval / Memory`
- active_phase: `Phase 32`
- active_slice: `S1: Evidence/Wiki 双层存储`
- active_branch: `main`
- status: `s1_completed_waiting_human_commit`

---

## 当前状态说明

Phase 32 kickoff 已完成并经 Human 口头确认进入实现。Codex 已完成 **S1: Evidence/Wiki 双层存储** 的代码落地与回归验证，当前工作树仍在 `main`，尚未切到本轮 feature branch，也尚未进行 slice 提交。

本次 S1 已完成的核心内容：

- 新增 `knowledge_store.py`，将 task knowledge view 拆分为 Evidence Store + Wiki Store，并保留 merged view 兼容层
- 为 `KnowledgeObject` 增加 `store_type`，新增 `WikiEntry` 扩展模型
- 在 `store.save_knowledge_objects()` 中同步持久化双层存储与旧 `knowledge_objects.json` 兼容镜像
- CLI 的 intake / inspect / review / knowledge-review-queue / knowledge-objects-json 已切到 merged view
- `knowledge stage-promote` 现在会同步写入 Wiki Store
- 全量测试已通过：`218 passed`

当前下一步不应跳过：

- Human 审阅 S1 diff
- Human 先切出 `feat/phase32-knowledge-dual-layer`（或等价命名）并提交 S1
- Codex 在 S1 commit 后继续 S2：权限校验 + Librarian 角色边界

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
- `docs/plans/phase32/kickoff.md` (claude, 2026-04-16) — Phase 32 kickoff: 3 slice，双层存储 + 权限校验 + Librarian 集成，风险 7/15 低
- `docs/plans/phase32/context_brief.md` (gemini, 2026-04-16) — Phase 32 目标总结与边界控制
- `src/swallow/knowledge_store.py` (codex, 2026-04-16) — S1 双层知识存储读写 API + merged view 兼容层
- `src/swallow/store.py` (codex, 2026-04-16) — `save_knowledge_objects()` 接入双层持久化，新增 `load_knowledge_objects()`
- `src/swallow/cli.py` (codex, 2026-04-16) — intake / inspect / review / queue 改读 merged view；stage-promote 同步写 Wiki Store
- `src/swallow/models.py` (codex, 2026-04-16) — `KnowledgeObject.store_type` + `WikiEntry`
- `tests/test_knowledge_store.py` (codex, 2026-04-16) — S1 存储分层与 overlay 回归测试
- `tests/test_cli.py` (codex, 2026-04-16) — stage-promote 写入 Wiki Store 覆盖
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
- **[Gemini]** 已根据 roadmap 输出 Phase 32 的 context_brief。
- **[Claude]** 已完成 Gateway 设计融合（design_gateway.md 内化至蓝图）+ 技术选型写入。
- **[Claude]** 已完成 Phase 32 kickoff 撰写（3 slice 方案拆解 + 风险评估）。
- **[Codex]** 已完成 S1：Evidence/Wiki 双层存储，实现 merged view 兼容层并接通 CLI/operator 视图。
- **[Codex]** 已完成 S1 回归验证：`.venv/bin/python -m pytest` → `218 passed in 5.75s`。

## 下一步

- **[Human]** 审阅当前 S1 diff，并先切换到 `feat/phase32-knowledge-dual-layer`（或等价 feature branch）
- **[Human]** 执行 S1 独立提交，不与后续 S2/S3 混包
- **[Codex]** 在 Human 完成 S1 commit 后进入 S2：promotion 权限校验 + Librarian 角色边界
- **[Claude]** 如 Codex 完成后需要 PR review，待指派

## 当前阻塞项

- 等待人工审批: S1 实现 diff
- 等待人工操作: 从 `main` 切出 Phase 32 feature branch，并完成 S1 独立 commit
