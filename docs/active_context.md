# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `Governance`
- latest_completed_phase: `Phase 64`
- latest_completed_slice: `Governance Boundary LLM Path Closure + route metadata externalization + review follow-up`
- active_track: `Governance`
- active_phase: `Post-Phase 64 merge`
- active_slice: `merge resolution / post-merge state sync / roadmap factual update / tag decision`
- active_branch: `main`
- status: `phase64_merge_resolved_pending_human_commit`

## 当前状态说明

当前 `main` 正在合入 Phase 64。`docs/active_context.md` 的冲突来自两边高频状态漂移:

- `main` 侧仍携带 Phase 64 design-pending / Phase 63 handoff 前后的旧状态。
- Phase 64 分支侧已推进到 review follow-up + closeout commit gate。

本次 resolution 以 git 当前合入事实为准,保留 Phase 64 已完成状态,丢弃旧的 Phase 62 / Phase 63 启动流水。Human 完成当前 merge / squash commit 后,再由 Codex 同步 `current_state.md`;随后交给 roadmap-updater 做 post-merge factual update,再进入 tag decision。

Phase 64 = roadmap 候选 G.5,目标是收口两条 NO_SKIP 红灯对应的 LLM path governance gap:

- Path B Executor 不再执行 Provider Router selection。Orchestrator 预解析 fallback chain plan 到 `TaskState.fallback_route_chain`;Executor 只消费 chain 并通过只读 `lookup_route_by_name(...)` 读取静态 route metadata。
- Specialist internal chat-completion 不再直连 provider。`agent_llm.call_agent_llm(...)` 变成 thin caller,统一穿透 `router.invoke_completion(...)`;共享 HTTP helper 已移到 `swallow._http_helpers`。

Human-approved follow-up scope 也已完成:

- fallback override config seam: `.swl/route_fallbacks.json`
- route registry metadata externalization: `src/swallow/routes.default.json` + `.swl/routes.json` + `swl route registry show/apply` + route metadata governance 写入
- route selection policy metadata externalization: `src/swallow/route_policy.default.json` + `.swl/route_policy.json` + `swl route policy show/apply` + route metadata governance 写入

Review 状态:

- `docs/plans/phase64/review_comments.md`: APPROVE,0 BLOCK / 1 CONCERN / 8 NOTE。
- 唯一 CONCERN-1 已消化:新增 public `router.resolve_fallback_chain(...)`,Orchestrator / synthesis / tests 不再 import Orchestrator private `_resolve_fallback_chain`。
- `docs/plans/phase64/consistency_report.md`: consistent。
- `docs/plans/phase64/closeout.md`: ready for PR / Merge Gate。
- `docs/design/INVARIANTS.md` 与 `docs/design/DATA_MODEL.md` 保持无改动。

最终验证记录:

- `.venv/bin/python -m pytest tests/test_router.py tests/test_synthesis.py tests/test_executor_protocol.py tests/test_executor_async.py tests/test_invariant_guards.py -q` -> 94 passed
- `.venv/bin/python tests/audit_no_skip_drift.py` -> all 8 tracked guards green
- `.venv/bin/python -m pytest` -> 589 passed / 8 deselected
- `git diff --check` -> passed
- `git diff -- docs/design/INVARIANTS.md docs/design/DATA_MODEL.md` -> no output

## 当前关键文档

1. `docs/active_context.md`(本文)
2. `docs/plans/phase64/closeout.md`
3. `docs/plans/phase64/review_comments.md`
4. `docs/plans/phase64/consistency_report.md`
5. `docs/plans/phase64/commit_summary.md`
6. `docs/plans/phase64/kickoff.md`
7. `docs/plans/phase64/design_decision.md`
8. `docs/plans/phase64/risk_assessment.md`
9. `docs/plans/phase64/design_audit.md`
10. `docs/plans/phase64/model_review.md`
11. `docs/concerns_backlog.md`
12. `current_state.md`(merge commit 后待同步)
13. `docs/roadmap.md`(merge commit 后由 roadmap-updater factual update)
14. `pr.md`(local ignored PR body draft)

---

## 当前推进

已完成:

- **[Human]** Phase 63 已 merge 到 `main`(`a1d2418 merge: Governance Closure`)。
- **[Claude]** Phase 64 context / kickoff / design_decision / risk_assessment / model_review / design_audit 已产出并修订到可实现状态。
- **[Human]** Phase 64 Design Gate 已通过;Codex 按 M1 -> M2 -> follow-up -> review follow-up 完成实现。
- **[Codex]** M1/S1 已完成:Path B fallback chain plan 前移到 Orchestrator,Executor 不再调用 route selection helper,`test_path_b_does_not_call_provider_router` 已启用。
- **[Codex]** M1 follow-up 已完成:fallback chain override 外部化到 `.swl/route_fallbacks.json`,避免把早期内置线性链固化成长期契约。
- **[Codex]** M2/S2 已完成:Specialist internal chat-completion 统一经 `router.invoke_completion(...)`,并启用 `test_specialist_internal_llm_calls_go_through_router`。
- **[Codex]** Human-approved route registry externalization 已完成:`routes.default.json` / `.swl/routes.json` / `swl route registry show/apply` / route metadata governance 写入。
- **[Codex]** Human-approved route policy externalization 已完成:`route_policy.default.json` / `.swl/route_policy.json` / `swl route policy show/apply` / route metadata governance 写入。
- **[Codex]** 已新增 `docs/plans/phase64/commit_summary.md`,说明新增外部化内容是 Human-approved follow-up scope,避免 review 误判为设计外漂移。
- **[Claude/consistency-checker]** Phase 64 consistency report 已产出,verdict = `consistent`。
- **[Claude]** Phase 64 PR review 已产出,verdict = APPROVE。
- **[Codex]** 已消化唯一 review CONCERN:promote fallback chain resolver to `router.resolve_fallback_chain(...)`。
- **[Codex]** Phase 64 closeout 已完成;`docs/concerns_backlog.md` 已标记 G.5 guard skip placeholder resolved,并新增 indirect chat-completion URL guard gap Open concern。
- **[Codex]** 当前 merge conflict 已收敛到本文,并按 post-Phase 64 main 状态解析。

进行中:

- **[Human]** 当前 Phase 64 merge / squash commit 尚未完成。

待执行:

- **[Human]** 完成当前 merge / squash commit。
- **[Codex]** merge commit 完成后同步 `current_state.md` 与必要的 `docs/active_context.md` 后续状态。
- **[Claude/roadmap-updater]** 完成 Phase 64 post-merge factual update。
- **[Claude/Human]** 进入 tag decision:判断 Phase 64 是否构成新的稳定 checkpoint,或是否等候候选 H / Truth Plane 后续 phase。

当前阻塞项:

- 等待 Human 完成当前 merge / squash commit。

---

## 当前下一步

1. **[Human]** 检查 merge resolution 后执行提交。
2. **[Codex]** 在提交完成后同步 `current_state.md` / `docs/active_context.md`。
3. **[Claude/roadmap-updater]** 更新 `docs/roadmap.md` 的 Phase 64 factual state。
4. **[Claude/Human]** 决定是否进入 tag 流程。

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
- next: 已闭环 — Codex 实现和交接已记录 S1/S2 CONCERN 假设,当前无 BLOCKER
```

---

## 当前产出物

- `docs/plans/phase64/context_brief.md`(claude/context-analyst, 2026-04-29)
- `docs/plans/phase64/kickoff.md`(claude, 2026-04-29)
- `docs/plans/phase64/design_decision.md`(claude, 2026-04-29)
- `docs/plans/phase64/risk_assessment.md`(claude, 2026-04-29)
- `docs/plans/phase64/model_review.md`(claude, 2026-04-29)
- `docs/plans/phase64/design_audit.md`(claude/design-auditor, 2026-04-29)
- `docs/plans/phase64/commit_summary.md`(codex, 2026-04-29)
- `docs/plans/phase64/consistency_report.md`(claude/consistency-checker, 2026-04-29)
- `docs/plans/phase64/review_comments.md`(claude, 2026-04-29)
- `docs/plans/phase64/closeout.md`(codex, 2026-04-29)
- `docs/concerns_backlog.md`(codex, 2026-04-29)
- `src/swallow/_http_helpers.py`(codex, Phase 64)
- `src/swallow/routes.default.json`(codex, Phase 64)
- `src/swallow/route_policy.default.json`(codex, Phase 64)
- `src/swallow/router.py` / `src/swallow/orchestrator.py` / `src/swallow/executor.py` / `src/swallow/synthesis.py` / `src/swallow/agent_llm.py` / `src/swallow/cli.py` / `src/swallow/governance.py` / `src/swallow/paths.py` / `src/swallow/truth/route.py`(codex, Phase 64 implementation)
- `tests/test_router.py` / `tests/test_executor_protocol.py` / `tests/test_executor_async.py` / `tests/test_synthesis.py` / `tests/test_invariant_guards.py` / `tests/test_cli.py` / `tests/test_governance.py` / `tests/audit_no_skip_drift.py`(codex, Phase 64 verification)
- `pr.md`(codex, local ignored Phase 64 PR body)
- `docs/active_context.md`(codex, 2026-04-29, Phase 64 merge resolution)
