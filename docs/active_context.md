# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `Governance`
- latest_completed_phase: `Phase 63`
- latest_completed_slice: `Governance Closure + PR review follow-up + merge`
- active_track: `Governance`
- active_phase: `Phase 64`
- active_slice: `Phase 64 review follow-up + closeout / commit gate`
- active_branch: `feat/phase64-llm-router-boundary`
- status: `phase64_review_followup_closeout_commit_gate`

## 当前状态说明

Phase 63 已 merge 至 `main`(`a1d2418 merge: Governance Closure`)。Phase 64 branch 已从合并后的主线切出,当前最新代码提交为 `c404f3e feat(phase64): externalize route selection policy`。

Phase 64 = roadmap 候选 G.5(治理边界 LLM 路径收口)。Human 在 2026-04-29 本会话指示"phase64 方案已产出,着手实现,留 commit gate",视为 Human Design Gate 通过并允许 Codex 在 `feat/phase64-llm-router-boundary` 上启动实现。

Phase 64 design 状态:

- `docs/plans/phase64/kickoff.md` / `design_decision.md` / `risk_assessment.md` 已进入 `revised-after-model-review`
- `docs/plans/phase64/model_review.md` 原始 verdict = BLOCK,4 BLOCK + 7 CONCERN 已由 revised design 消化
- `docs/plans/phase64/design_audit.md` verdict = concerns-only,0 BLOCKER;Codex 需在实现和交接中显式记录 4 条 CONCERN 假设
- 当前 phase 严格不修改 `docs/design/INVARIANTS.md` / `docs/design/DATA_MODEL.md`

Phase 64 milestone 边界:

- **M1/S1**:Path B fallback chain plan + `lookup_route_by_name` + 启用 `test_path_b_does_not_call_provider_router`
- **M2/S2**:`_http_helpers.py` + `router.invoke_completion` + `call_agent_llm` thin caller + 启用 `test_specialist_internal_llm_calls_go_through_router`

Codex 已完成并由 Human 提交 M1/S1 主实现:`afec43c feat(phase64): pre-resolve executor fallback route chain`。随后 Human 反馈不希望把早期 built-in fallback chain 固化为设计/测试契约,要求保留可配置 config seam;Codex 已完成并由 Human 提交 M1 follow-up:`6ad909e feat(phase64): allow route fallback overrides`。

Human 随后指示继续下一个 milestone。Codex 已完成 M2/S2 实现,Human 已提交 `d2f03a8 feat(phase64): route specialist llm calls through router`。

Human 进一步要求消除 route registry 硬编码,将整张 route registry 外部化,并纳入 route metadata governance 变更。Codex 已完成 follow-up 实现,Human 已提交 `900c38b feat(phase64): externalize route registry metadata`:默认 RouteSpec 全量定义迁至 `src/swallow/routes.default.json`,工作区可用 `.swl/routes.json` 覆盖整张 registry;`apply_route_registry(base_dir)` 在 CLI / Orchestrator route metadata overlay 前加载 registry;`register_route_metadata_proposal(..., route_registry=...)` + `apply_proposal(..., ROUTE_METADATA)` 可治理写入 `.swl/routes.json`;CLI 新增 `swl route registry show/apply`。

Human 随后询问 route mode mapping / complexity bias 等剩余硬编码是否适合外部化。Codex 判断这些不属于 route registry 本体,而属于 route selection policy metadata;已完成 follow-up 实现,Human 已提交 `c404f3e feat(phase64): externalize route selection policy`:默认 selection policy 迁至 `src/swallow/route_policy.default.json`,工作区可用 `.swl/route_policy.json` 覆盖;`apply_route_policy(base_dir)` 在 registry 之后、weights/fallback/capability overlays 之前加载;`register_route_metadata_proposal(..., route_policy=...)` + `apply_proposal(..., ROUTE_METADATA)` 可治理写入 `.swl/route_policy.json`;CLI 新增 `swl route policy show/apply`。

为避免后续 review 把 Human follow-up scope 误判为未出现在原 Phase 64 design 的漂移,Codex 已新增 `docs/plans/phase64/commit_summary.md`,集中说明 fallback override config / route registry metadata / route selection policy metadata 三层外部化的边界、治理入口和验证结果。

Claude review 已产出并给出 APPROVE(0 BLOCK / 1 CONCERN / 8 NOTE)。唯一 CONCERN-1 为 `synthesis.py` 反向 import Orchestrator 私有 `_resolve_fallback_chain`;Codex 已在本轮消化:新增 public `router.resolve_fallback_chain(...)`,Orchestrator / synthesis / tests 均改为使用该 router API。Phase closeout 已整理到 `docs/plans/phase64/closeout.md`,PR body 已更新到本地 ignored `pr.md`。

M1/S1 验证结果(2026-04-29):

- `.venv/bin/python -m pytest tests/test_invariant_guards.py tests/test_router.py` → 49 passed / 1 skipped
- `.venv/bin/python -m pytest tests/test_executor_protocol.py tests/test_executor_async.py tests/test_binary_fallback.py` → 34 passed
- `.venv/bin/python -m pytest tests/test_cli.py -k 'fallback or route'` → 34 passed / 205 deselected
- `.venv/bin/python -m pytest tests/test_synthesis.py` → 7 passed
- `.venv/bin/python -m pytest` → 578 passed / 1 skipped / 8 deselected
- `git diff --check` → passed
- `git diff -- docs/design/INVARIANTS.md docs/design/DATA_MODEL.md` → no output

M1/S1 config follow-up 验证结果(2026-04-29):

- `.venv/bin/python -m pytest tests/test_router.py -k 'fallback or lookup_route_by_name' tests/test_executor_protocol.py::ExecutorProtocolTest::test_run_http_executor_falls_back_to_next_http_route_after_timeout tests/test_executor_async.py::ExecutorAsyncProtocolTest::test_run_http_executor_async_falls_back_to_next_http_route_after_timeout tests/test_synthesis.py::test_mps_participant_state_gets_route_specific_fallback_chain` → 5 passed / 24 deselected
- `.venv/bin/python -m pytest tests/test_executor_protocol.py::ExecutorProtocolTest::test_run_http_executor_falls_back_to_next_http_route_after_timeout tests/test_executor_protocol.py::ExecutorProtocolTest::test_run_executor_inline_falls_back_from_http_to_local_summary_when_cli_fallback_is_unavailable tests/test_executor_async.py::ExecutorAsyncProtocolTest::test_run_http_executor_async_falls_back_to_next_http_route_after_timeout` → 3 passed
- `.venv/bin/python -m pytest tests/test_router.py tests/test_invariant_guards.py tests/test_synthesis.py` → 57 passed / 1 skipped
- `.venv/bin/python -m pytest` → 579 passed / 1 skipped / 8 deselected
- `git diff --check` → passed
- `git diff -- docs/design/INVARIANTS.md docs/design/DATA_MODEL.md` → no output

M2/S2 验证结果(2026-04-29):

- `.venv/bin/python -m pytest tests/test_invariant_guards.py::test_specialist_internal_llm_calls_go_through_router tests/test_router.py::RouteRegistryTest::test_call_agent_llm_invokes_router_completion_gateway` → 2 passed
- `.venv/bin/python -m pytest tests/test_specialist_agents.py tests/test_retrieval_adapters.py -q` → 36 passed
- `.venv/bin/python -m pytest tests/test_executor_protocol.py tests/test_executor_async.py -q` → 31 passed
- `.venv/bin/python -m pytest tests/test_router.py tests/test_invariant_guards.py tests/test_specialist_agents.py tests/test_retrieval_adapters.py tests/test_executor_protocol.py tests/test_executor_async.py` → 119 passed
- `.venv/bin/python -m pytest` → first run exposed 2 timing-sensitive failures outside this slice; immediate isolated reruns passed; second full run → 581 passed / 8 deselected
- `git diff --check` → passed
- `git diff -- docs/design/INVARIANTS.md docs/design/DATA_MODEL.md` → no output

M2 follow-up route registry externalization 验证结果(2026-04-29):

- `.venv/bin/python -m pytest tests/test_router.py tests/test_governance.py tests/test_invariant_guards.py -q` → 63 passed
- `.venv/bin/python -m pytest tests/test_cli.py::CliLifecycleTest::test_route_registry_apply_and_show_cli_flow tests/test_cli.py -k 'route or fallback or capability' -q` → 49 passed / 191 deselected / 5 subtests passed
- `.venv/bin/python -m pytest tests/test_meta_optimizer.py -q` → 19 passed
- `.venv/bin/python -m pytest tests/test_executor_protocol.py tests/test_executor_async.py tests/test_synthesis.py -q` → 38 passed
- `.venv/bin/python tests/audit_no_skip_drift.py` → all 8 tracked guards green
- `.venv/bin/python -m pytest` → 585 passed / 8 deselected
- `git diff --check` → passed
- `git diff -- docs/design/INVARIANTS.md docs/design/DATA_MODEL.md` → no output

M2 follow-up route policy externalization 验证结果(2026-04-29):

- `.venv/bin/python -m pytest tests/test_router.py tests/test_governance.py tests/test_invariant_guards.py -q` → 66 passed
- `.venv/bin/python -m pytest tests/test_cli.py::CliLifecycleTest::test_route_policy_apply_and_show_cli_flow tests/test_cli.py -k 'route or fallback or capability' -q` → 50 passed / 191 deselected / 5 subtests passed
- `.venv/bin/python tests/audit_no_skip_drift.py` → all 8 tracked guards green
- `.venv/bin/python -m pytest tests/test_meta_optimizer.py -q` → 19 passed
- `.venv/bin/python -m pytest tests/test_executor_protocol.py tests/test_executor_async.py tests/test_synthesis.py -q` → 38 passed
- `.venv/bin/python -m pytest` → 589 passed / 8 deselected
- `git diff --check` → passed
- `git diff -- docs/design/INVARIANTS.md docs/design/DATA_MODEL.md` → no output

Review follow-up + closeout 验证结果(2026-04-29):

- `.venv/bin/python -m pytest tests/test_router.py tests/test_synthesis.py tests/test_executor_protocol.py tests/test_executor_async.py tests/test_invariant_guards.py -q` → 94 passed
- `.venv/bin/python tests/audit_no_skip_drift.py` → all 8 tracked guards green
- `git diff --check` → passed
- `git diff -- docs/design/INVARIANTS.md docs/design/DATA_MODEL.md` → no output
- `.venv/bin/python -m pytest` → final rerun 589 passed / 8 deselected; two earlier full attempts exposed one-off timing-sensitive failures in `tests/test_synthesis.py::test_synthesis_does_not_mutate_main_task_state` and `tests/test_run_task_subtasks.py::RunTaskSubtaskIntegrationTest::test_run_task_times_out_one_parallel_subtask_without_canceling_other_work`, and both isolated reruns passed.

## 当前关键文档

1. `docs/active_context.md`(本文)
2. `docs/plans/phase64/kickoff.md`
3. `docs/plans/phase64/design_decision.md`
4. `docs/plans/phase64/risk_assessment.md`
5. `docs/plans/phase64/design_audit.md`
6. `docs/plans/phase64/model_review.md`
7. `docs/plans/phase64/context_brief.md`
8. `docs/plans/phase64/commit_summary.md`
9. `docs/design/INVARIANTS.md`
10. `docs/concerns_backlog.md`

---

## 当前推进

已完成:

- **[Human]** Phase 63 已 merge 到 `main`(`a1d2418 merge: Governance Closure`)。
- **[Claude]** Phase 64 context / kickoff / design_decision / risk_assessment / model_review / design_audit 已产出并修订到可实现状态。
- **[Human]** Phase 64 Human Design Gate 已通过(2026-04-29 本会话指示),Codex 可启动 M1/S1。
- **[Codex]** 已完成新会话 reading manifest、状态校验,识别并修正 `docs/active_context.md` 从 Phase 63 到 Phase 64 的 stale state。
- **[Codex]** M1/S1 已完成:新增 `TaskState.fallback_route_chain`,orchestrator 在 `_apply_route_spec_to_state` 中预解析完整 fallback chain,executor 改为只读 chain + `lookup_route_by_name`,MPS participant state 改为 route-specific chain,启用 `test_path_b_does_not_call_provider_router`。验证结果见上方 M1/S1 验证结果。
- **[Human]** 已提交 M1/S1 主实现:`afec43c feat(phase64): pre-resolve executor fallback route chain`。
- **[Codex]** M1 follow-up 已完成:新增 `.swl/route_fallbacks.json` 配置读取 seam(`route_fallbacks_path` / `load_route_fallbacks` / `apply_route_fallbacks`),orchestrator/CLI 在 route selection 前应用 fallback override,测试不再把完整 built-in fallback chain 作为固定契约。验证结果见上方 config follow-up 验证结果。
- **[Human]** 已提交 M1 follow-up:`6ad909e feat(phase64): allow route fallback overrides`。
- **[Codex]** M2/S2 已完成:新增 `swallow._http_helpers`,把 `AgentLLMResponse` / `AgentLLMUnavailable` / HTTP helper 抽到中性模块;新增 `swallow.router.invoke_completion(...)`;`agent_llm.call_agent_llm(...)` 改为 thin caller;启用 `test_specialist_internal_llm_calls_go_through_router`;新增 integration smoke test mock `swallow.router.httpx.post`;同步 `tests/audit_no_skip_drift.py` 的 G.5 守卫语义。验证结果见上方 M2/S2 验证结果。
- **[Human]** 已提交 M2/S2 实现:`d2f03a8 feat(phase64): route specialist llm calls through router`。
- **[Codex]** M2 follow-up 已完成:route registry 默认元数据外部化到 `src/swallow/routes.default.json`;新增 `.swl/routes.json` 工作区覆盖;route registry 写入扩展到 route metadata governance;新增 `swl route registry show/apply`;测试覆盖 JSON 默认加载、工作区 registry 应用、governance 写入和 CLI apply/show。验证结果见上方 M2 follow-up 验证结果。
- **[Human]** 已提交 route registry externalization follow-up:`900c38b feat(phase64): externalize route registry metadata`。
- **[Codex]** M2 follow-up route policy externalization 已完成:route selection policy 默认元数据外部化到 `src/swallow/route_policy.default.json`;新增 `.swl/route_policy.json` 工作区覆盖;route policy 写入扩展到 route metadata governance;新增 `swl route policy show/apply`;测试覆盖 JSON 默认加载、工作区 policy 应用、governance 写入、CLI apply/show 与守卫脚本。验证结果见上方 route policy externalization 验证结果。
- **[Human]** 已提交 route policy externalization follow-up:`c404f3e feat(phase64): externalize route selection policy`。
- **[Codex]** 已新增 `docs/plans/phase64/commit_summary.md`,作为 route externalization follow-up review 前置说明,明确这些外部化改动是 Human-approved follow-up scope,不是原 S1/S2 design 的 accidental drift。
- **[Claude/consistency-checker]** Phase 64 follow-up 一致性核查已产出 → `docs/plans/phase64/consistency_report.md`(verdict = `consistent`,7/7 MATCH:write boundary / Phase 63 守卫保持 active / 无新 ProposalTarget / INVARIANTS+DATA_MODEL 零 diff / S1+S2 主线边界保持 / 加载顺序 5 入口对齐 / 无 schema 改动)。
- **[Claude]** Phase 64 PR review 已完成 → `docs/plans/phase64/review_comments.md`(verdict = APPROVE,0 BLOCK / 1 CONCERN / 8 NOTE)。复跑 `.venv/bin/python -m pytest` → 589 passed / 8 deselected;`grep -c "pytest.skip" tests/test_invariant_guards.py` → 0(§9 17 守卫全 active);`git diff main...HEAD -- docs/design/` 零行。唯一 [CONCERN-1]:`synthesis.py:9 from .orchestrator import _resolve_fallback_chain` 反向 import 私有 helper,Claude 推荐升级到 `router.resolve_fallback_chain` 公开 API(本 PR 内消化),Human 在 Merge Gate 决定。
- **[Codex]** 已消化 CONCERN-1:新增 `router.resolve_fallback_chain(...)`,Orchestrator 与 synthesis 改用 router public API,tests 也改为从 router import;`rg '_resolve_fallback_chain' src tests` 仅剩测试名文本,无私有 helper 调用。
- **[Codex]** Phase 64 closeout 已完成:`docs/plans/phase64/closeout.md`;`docs/concerns_backlog.md` 已将 G.5 guard skip placeholder 标为 Phase 64 resolved,并新增 review M2-2 indirect URL binding guard gap;本地 ignored `pr.md` 已更新为 Phase 64 PR body。

进行中:

- 无。

待执行:

- **[Human]** 审阅并提交 review follow-up + closeout diff。
- **[Human]** push branch + 使用本地 `pr.md` 创建 PR,进入 Merge Gate 最终审批。

当前阻塞项:

- 无。

---

## 当前下一步

1. **[Human]** 审阅并提交当前 review follow-up + closeout diff。
2. **[Human]** push branch + 使用本地 `pr.md` 创建 PR。
3. **[Codex]** PR 创建后如描述或 review 状态变化,继续维护 `pr.md`;merge 后同步 `current_state.md` / `docs/active_context.md`。

```markdown
model_review:
- status: completed
- artifact: docs/plans/phase64/model_review.md
- reviewer: external-model (GPT-5 via mcp__gpt5__chat-with-gpt5_5)
- verdict: BLOCK
- next: 已闭环 — 4 BLOCK + 7 CONCERN 已通过 revised-after-model-review 三件套与 design_audit 复核消化;不再触发二次 model review
```

```markdown
design_audit:
- status: completed
- artifact: docs/plans/phase64/design_audit.md
- verdict: concerns-only
- next: Codex 实现时记录 S1/S2 4 条 CONCERN 假设;当前无 BLOCKER
```

---

## 当前产出物

- `docs/plans/phase64/context_brief.md`(claude/context-analyst, 2026-04-29, Phase 64 G.5 context brief)
- `docs/plans/phase64/kickoff.md`(claude, 2026-04-29, Phase 64 revised-after-model-review kickoff)
- `docs/plans/phase64/design_decision.md`(claude, 2026-04-29, Phase 64 S1/S2 implementation design)
- `docs/plans/phase64/risk_assessment.md`(claude, 2026-04-29, Phase 64 10 risks, 0 high)
- `docs/plans/phase64/model_review.md`(claude, 2026-04-29, external GPT-5 review verdict BLOCK,consumed by revised design)
- `docs/plans/phase64/design_audit.md`(claude/design-auditor, 2026-04-29, concerns-only,0 BLOCKER)
- `docs/active_context.md`(codex, 2026-04-29, Phase 64 M1/S1 state sync before implementation)
- `src/swallow/models.py`(codex, 2026-04-29, M1/S1 `TaskState.fallback_route_chain`)
- `src/swallow/orchestrator.py`(codex, 2026-04-29, M1/S1 fallback chain pre-resolution)
- `src/swallow/router.py`(codex, 2026-04-29, M1/S1 `lookup_route_by_name` read-only helper)
- `src/swallow/executor.py`(codex, 2026-04-29, M1/S1 executor consumes pre-resolved fallback chain)
- `src/swallow/synthesis.py`(codex, 2026-04-29, M1/S1 MPS participant route-specific chain)
- `tests/test_invariant_guards.py`(codex, 2026-04-29, M1/S1 Path B selection guard enabled)
- `tests/test_router.py` / `tests/test_executor_protocol.py` / `tests/test_executor_async.py` / `tests/test_synthesis.py`(codex, 2026-04-29, M1/S1 fallback chain regression coverage)
- `docs/active_context.md`(codex, 2026-04-29, Phase 64 M1/S1 commit gate)
- `src/swallow/paths.py`(codex, 2026-04-29, M1 follow-up `route_fallbacks_path`)
- `src/swallow/router.py`(codex, 2026-04-29, M1 follow-up `load_route_fallbacks` / `apply_route_fallbacks`)
- `src/swallow/orchestrator.py` / `src/swallow/cli.py`(codex, 2026-04-29, M1 follow-up apply route fallback overrides before route selection)
- `tests/test_router.py` / `tests/test_executor_protocol.py` / `tests/test_executor_async.py` / `tests/test_synthesis.py`(codex, 2026-04-29, M1 follow-up avoids hard-coding full built-in fallback chain and covers config override)
- `docs/active_context.md`(codex, 2026-04-29, Phase 64 M1 config follow-up commit gate)
- `src/swallow/_http_helpers.py`(codex, 2026-04-29, M2/S2 neutral HTTP helper module)
- `src/swallow/router.py`(codex, 2026-04-29, M2/S2 `invoke_completion` Provider Router gateway)
- `src/swallow/agent_llm.py`(codex, 2026-04-29, M2/S2 `call_agent_llm` thin caller)
- `src/swallow/executor.py`(codex, 2026-04-29, M2/S2 helper imports / compatibility exports)
- `tests/test_invariant_guards.py`(codex, 2026-04-29, M2/S2 chat-completion gateway guard enabled)
- `tests/test_router.py`(codex, 2026-04-29, M2/S2 `call_agent_llm → invoke_completion → httpx.post` smoke test)
- `tests/audit_no_skip_drift.py`(codex, 2026-04-29, M2/S2 guard audit semantics aligned with chat-completion URL scan)
- `docs/active_context.md`(codex, 2026-04-29, Phase 64 M2/S2 commit gate)
- `src/swallow/routes.default.json`(codex, 2026-04-29, route registry default metadata externalized from Python)
- `src/swallow/router.py`(codex, 2026-04-29, route registry JSON load/save/apply + report helpers)
- `src/swallow/paths.py`(codex, 2026-04-29, `.swl/routes.json` path helper)
- `src/swallow/governance.py` / `src/swallow/truth/route.py`(codex, 2026-04-29, route registry included in route metadata governance writes)
- `src/swallow/cli.py`(codex, 2026-04-29, `swl route registry show/apply`)
- `pyproject.toml`(codex, 2026-04-29, package default route registry JSON)
- `tests/test_router.py` / `tests/test_governance.py` / `tests/test_cli.py` / `tests/test_invariant_guards.py` / `tests/audit_no_skip_drift.py`(codex, 2026-04-29, route registry externalization + governance coverage)
- `docs/active_context.md`(codex, 2026-04-29, Phase 64 route registry externalization commit gate)
- `src/swallow/route_policy.default.json`(codex, 2026-04-29, route selection policy default metadata externalized from Python)
- `src/swallow/router.py`(codex, 2026-04-29, route policy JSON load/save/apply + report helpers)
- `src/swallow/paths.py`(codex, 2026-04-29, `.swl/route_policy.json` path helper)
- `src/swallow/governance.py` / `src/swallow/truth/route.py`(codex, 2026-04-29, route policy included in route metadata governance writes)
- `src/swallow/cli.py`(codex, 2026-04-29, `swl route policy show/apply`)
- `pyproject.toml`(codex, 2026-04-29, package default route policy JSON)
- `tests/test_router.py` / `tests/test_governance.py` / `tests/test_cli.py` / `tests/test_invariant_guards.py` / `tests/audit_no_skip_drift.py`(codex, 2026-04-29, route policy externalization + governance coverage)
- `docs/plans/phase64/commit_summary.md`(codex, 2026-04-29, route externalization follow-up review preface)
- `docs/active_context.md`(codex, 2026-04-29, Phase 64 route policy externalization commit gate)
- `docs/plans/phase64/consistency_report.md`(claude/consistency-checker, 2026-04-29, Phase 64 route externalization consistency report)
- `docs/plans/phase64/review_comments.md`(claude, 2026-04-29, Phase 64 PR review APPROVE with 1 CONCERN)
- `src/swallow/router.py` / `src/swallow/orchestrator.py` / `src/swallow/synthesis.py`(codex, 2026-04-29, review CONCERN-1 public `resolve_fallback_chain` follow-up)
- `tests/test_router.py` / `tests/test_executor_protocol.py` / `tests/test_executor_async.py` / `tests/test_synthesis.py`(codex, 2026-04-29, update fallback chain tests to public router API)
- `docs/concerns_backlog.md`(codex, 2026-04-29, mark G.5 guard skip resolved and add Phase 64 M2-2 indirect URL guard gap)
- `docs/plans/phase64/closeout.md`(codex, 2026-04-29, Phase 64 closeout)
- `pr.md`(codex, 2026-04-29, local ignored Phase 64 PR body)
- `docs/active_context.md`(codex, 2026-04-29, Phase 64 review follow-up closeout commit gate)
