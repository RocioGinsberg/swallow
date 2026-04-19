# Active Context

## 当前轮次

- latest_completed_track: `Retrieval / Memory` (Primary) + `Evaluation / Policy` (Secondary)
- latest_completed_phase: `Phase 45`
- latest_completed_slice: `Eval Baseline + Deep Ingestion`
- active_track: `Execution Topology` (Primary) + `Capabilities` (Secondary)
- active_phase: `Phase 46`
- active_slice: `S2_http_executor_core_completed_waiting_commit_gate`
- active_branch: `feat/phase46_gateway-core`
- status: `phase46_s2_completed_waiting_commit_gate`

---

## 当前状态说明

Phase 45 已完成，稳定基线仍为 `v0.3.2`。Phase 46 当前已获 Human 实现授权，方向为模型网关物理层实装：用 HTTP 执行器替代 subprocess CLI 成为主 LLM 路径，同时将 CLI 执行器去品牌化并补齐多模型路由 / fallback。S1 基础设施就绪验证已完成并单独提交；S2 已完成核心实现、真实 `new-api` gate 与全量 pytest 验证，当前等待 Human 执行该 slice 的独立 commit。

Phase 46 方案拆解已产出（`docs/plans/phase46/design_decision.md`）。4 个 slice：S1 基础设施就绪验证、S2 HTTP 执行器核心 + CLI 去品牌化（高风险）、S3 方言对齐与多模型路由（claude/qwen/glm/gemini/deepseek）、S4 降级矩阵（HTTP → Cline CLI → 离线）+ Eval 护航。整体风险 24/36（中-高）。当前工作要求按 slice 推进，并在每个 slice 完成后设置独立 commit gate；S2 完成后另有 Human gate 验证真实 `new-api` 调用。

---

## 当前关键文档

当前新一轮工作开始前，优先读取：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/roadmap.md`
4. `docs/plans/phase46/kickoff.md`
5. `docs/plans/phase46/breakdown.md`

仅在需要时再读取：

- `docs/plans/phase46/design_decision.md`
- `docs/plans/phase46/risk_assessment.md`
- `docs/concerns_backlog.md`
- 历史 phase closeout / review_comments

---

## 当前推进

已完成：

- **[Human]** 已审批 Phase 46 规划文档并授权进入实现。
- **[Human]** 已切换实现分支到 `feat/phase46_gateway-core`。
- **[Codex]** 已完成 Phase 46 文档与执行层边界核对，开始按 S1 → S4 顺序推进。
- **[Human/Codex]** 已完成 S1：`httpx` 依赖、`doctor` 的 `new-api` 检查项与 HTTP executor eval 骨架已落地；`new-api` 本地栈已确认就绪。
- **[Codex]** 已完成 S2 核心实现：`HTTPExecutor`、配置驱动的 `CLIAgentExecutor`、`local-http` 路由、`http` route_mode 映射、`http/qwen/glm/gemini/deepseek` 计费基线入口已落地。
- **[Codex]** 已补齐 S2 定向测试：`tests/test_executor_protocol.py`、`tests/test_router.py`、`tests/test_cost_estimation.py`、`tests/test_binary_fallback.py`、相关 `tests/test_cli.py` 定向用例通过。
- **[Codex]** 已确认宿主机 `localhost:3000` 可达；鉴权链路已打通，HTTP executor 已支持 `AIWF_NEW_API_KEY` / `OPENAI_API_KEY` / `NEW_API_KEY` 鉴权头。
- **[Human/Codex]** 已完成 S2 Human gate：修正 `new-api` 的 DeepSeek 模型映射后，`POST /v1/chat/completions` 对 `deepseek-chat` 返回有效 completion（`PHASE46_HTTP_OK`，真实上游 `deepseek/deepseek-chat-v3` via DeepInfra）。
- **[Codex]** 已补齐缺失的 retrieval eval fixture（`tests/fixtures/retrieval_eval/.swl/...`）并为其开放 `.gitignore` 例外；全量 pytest 现为 `330 passed, 3 deselected`。

当前产出物：

- `src/swallow/executor.py` (codex, 2026-04-20)
- `src/swallow/router.py` (codex, 2026-04-20)
- `src/swallow/dialect_data.py` (codex, 2026-04-20)
- `src/swallow/cost_estimation.py` (codex, 2026-04-20)
- `src/swallow/retry_policy.py` (codex, 2026-04-20)
- `src/swallow/checkpoint_snapshot.py` (codex, 2026-04-20)
- `.gitignore` (codex, 2026-04-20)
- `tests/test_executor_protocol.py` (codex, 2026-04-20)
- `tests/test_router.py` (codex, 2026-04-20)
- `tests/test_cost_estimation.py` (codex, 2026-04-20)
- `tests/test_cli.py` (codex, 2026-04-20)
- `tests/fixtures/retrieval_eval/.swl/tasks/demo/artifacts/summary.md` (codex, 2026-04-20)
- `tests/fixtures/retrieval_eval/.swl/tasks/demo/knowledge_objects.json` (codex, 2026-04-20)
- `tests/fixtures/retrieval_eval/.swl/tasks/prior/knowledge_objects.json` (codex, 2026-04-20)

下一步：

- **[Human]** 审查当前 diff，并为 S2 执行独立 commit
- **[Codex]** Human commit 完成后，更新状态并进入 S3 方言对齐与多模型路由
- **[Human/Codex]** S3 开始时以真实可用模型集合为准注册多模型 HTTP 路由，不再假设 `claude` 在当前 `new-api` 默认 group 下可用

当前阻塞项：

- 无。S2 当前进入 Human commit gate。
