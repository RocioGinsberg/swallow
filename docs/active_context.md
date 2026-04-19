# Active Context

## 当前轮次

- latest_completed_track: `Retrieval / Memory` (Primary) + `Evaluation / Policy` (Secondary)
- latest_completed_phase: `Phase 45`
- latest_completed_slice: `Eval Baseline + Deep Ingestion`
- active_track: `Execution Topology` (Primary) + `Capabilities` (Secondary)
- active_phase: `Phase 46`
- active_slice: `phase46_post_review_followup_ready_for_closeout_commit`
- active_branch: `feat/phase46_gateway-core`
- status: `phase46_review_complete_waiting_human_closeout_commit`

---

## 当前状态说明

Phase 45 已完成，稳定基线仍为 `v0.3.2`。Phase 46 当前已完成实现、Claude review 与 review follow-up，方向为模型网关物理层实装：用 HTTP 执行器替代 subprocess CLI 成为主 LLM 路径，同时将 CLI 执行器去品牌化并补齐多模型路由 / fallback。Claude review 结论为 `0 BLOCK / 1 CONCERN / 2 NOTE / Merge ready`；唯一 concern C1 已在本轮吸收：HTTP 429 现在映射为 `http_rate_limited`，走重试 / backoff 语义，不再立即触发 route fallback。

Phase 46 方案拆解已产出（`docs/plans/phase46/design_decision.md`）。4 个 slice：S1 基础设施就绪验证、S2 HTTP 执行器核心 + CLI 去品牌化（高风险）、S3 方言对齐与多模型路由（claude/qwen/glm/gemini/deepseek）、S4 降级矩阵（HTTP → Cline CLI → 离线）+ Eval 护航。整体风险 24/36（中-高）。当前 post-review 基线已验证：默认 pytest 为 `342 passed, 4 deselected`，`pytest -m eval -v` 为 `4 passed, 342 deselected`。`docs/plans/phase46/closeout.md` 与 `./pr.md` 已同步完成，等待 Human 执行审查收口 commit / push / PR 更新。

---

## 当前关键文档

当前收口阶段，优先读取：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/roadmap.md`
4. `docs/plans/phase46/review_comments.md`
5. `docs/plans/phase46/closeout.md`

仅在需要时再读取：

- `docs/plans/phase46/kickoff.md`
- `docs/plans/phase46/breakdown.md`
- `docs/plans/phase46/design_decision.md`
- `docs/plans/phase46/risk_assessment.md`
- `docs/concerns_backlog.md`
- 历史 phase closeout / review_comments

---

## 当前推进

已完成：

- **[Human]** 已审批 Phase 46 规划文档并授权进入实现。
- **[Human]** 已切换实现分支到 `feat/phase46_gateway-core`。
- **[Codex]** 已完成 Phase 46 文档与执行层边界核对，并按 S1 → S4 推进完整实现。
- **[Human/Codex]** 已完成 S1：`httpx` 依赖、`doctor` 的 `new-api` 检查项与 HTTP executor eval 骨架已落地；`new-api` 本地栈已确认就绪。
- **[Human/Codex]** 已完成 S2 Human gate：修正 `new-api` 的 DeepSeek 模型映射后，`POST /v1/chat/completions` 对 `deepseek-chat` 返回有效 completion（`PHASE46_HTTP_OK`，真实上游 `deepseek/deepseek-chat-v3` via DeepInfra）。
- **[Human]** 已完成实现提交：
  - `8e030a7 feat(gateway): add http executor and debrand cli agents`
  - `b5ccf5e feat(gateway): align http dialect routing matrix`
  - `14a4629 feat(gateway): add fallback matrix for http routes`
- **[Claude]** 已完成 `docs/plans/phase46/review_comments.md`，结论为 `0 BLOCK / 1 CONCERN / 2 NOTE / Merge ready`。
- **[Codex]** 已吸收 C1 follow-up：
  - HTTP 429 现在映射为 `failure_kind="http_rate_limited"`
  - HTTP executor 在 rate-limit 场景保持当前 route，不立即触发 executor route fallback
  - orchestrator binary fallback 对 `http_rate_limited` 显式跳过二次降级
  - retry policy 改为重试 `http_rate_limited`，不再将通用 `http_error` 视为 retryable
  - checkpoint snapshot 将 `http_rate_limited` 归入 `interruption_recovery`
- **[Codex]** 已补齐 C1 回归测试：`tests/test_executor_protocol.py`、`tests/test_binary_fallback.py`、`tests/test_retry_policy.py`、`tests/test_checkpoint_snapshot.py`。
- **[Codex]** 已完成 post-review 验证：`.venv/bin/pytest --tb=short` 为 `342 passed, 4 deselected`；`.venv/bin/pytest -m eval -v` 为 `4 passed, 342 deselected`。
- **[Codex]** 已同步 `docs/plans/phase46/closeout.md`、`docs/active_context.md` 与 `./pr.md`，准备交给 Human 做审查收口 commit。

当前产出物：

- `src/swallow/executor.py` (codex, 2026-04-20)
- `src/swallow/models.py` (codex, 2026-04-20)
- `src/swallow/router.py` (codex, 2026-04-20)
- `src/swallow/dialect_adapters/codex_fim.py` (codex, 2026-04-20)
- `src/swallow/dialect_data.py` (codex, 2026-04-20)
- `src/swallow/cost_estimation.py` (codex, 2026-04-20)
- `src/swallow/harness.py` (codex, 2026-04-20)
- `src/swallow/orchestrator.py` (codex, 2026-04-20)
- `src/swallow/retry_policy.py` (codex, 2026-04-20)
- `src/swallow/checkpoint_snapshot.py` (codex, 2026-04-20)
- `docs/plans/phase46/review_comments.md` (claude, 2026-04-20)
- `docs/plans/phase46/closeout.md` (codex, 2026-04-20)
- `.gitignore` (codex, 2026-04-20)
- `tests/test_executor_protocol.py` (codex, 2026-04-20)
- `tests/test_router.py` (codex, 2026-04-20)
- `tests/test_dialect_adapters.py` (codex, 2026-04-20)
- `tests/test_cost_estimation.py` (codex, 2026-04-20)
- `tests/test_cli.py` (codex, 2026-04-20)
- `tests/eval/test_http_executor_eval.py` (codex, 2026-04-20)
- `tests/test_retry_policy.py` (codex, 2026-04-20)
- `tests/test_checkpoint_snapshot.py` (codex, 2026-04-20)
- `pr.md` (codex, 2026-04-20)
- `tests/fixtures/retrieval_eval/.swl/tasks/demo/artifacts/summary.md` (codex, 2026-04-20)
- `tests/fixtures/retrieval_eval/.swl/tasks/demo/knowledge_objects.json` (codex, 2026-04-20)
- `tests/fixtures/retrieval_eval/.swl/tasks/prior/knowledge_objects.json` (codex, 2026-04-20)

下一步：

- **[Human]** 审查当前 diff，并执行审查收口 commit（含 C1 follow-up、`review_comments.md`、`closeout.md`、`docs/active_context.md`）。
- **[Human]** push `feat/phase46_gateway-core`，并使用 `./pr.md` 创建 / 更新 PR 描述。
- **[Human]** 根据当前 review 结论决定 merge；如合并完成，可按 review 建议评估 `v0.4.0` tag。

当前阻塞项：

- 无代码阻塞；等待 Human 完成审查收口 commit / push / PR 同步 / merge 决策。
