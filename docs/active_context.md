# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `Architecture / Engineering`
- latest_completed_phase: `Architecture Recomposition First Branch`
- latest_completed_slice: `AD1/V pilot + AB query pilot + roadmap LTO reorganization`
- active_track: `Architecture / Engineering`
- active_phase: `Provider Router Split / LTO-7 Step 1`
- active_slice: `PR review complete; awaiting Human merge decision`
- active_branch: `feat/provider-router-split`
- status: `pr_review_pass_with_3_concerns_recommend_merge`

## 当前状态说明

当前 git 分支为 `feat/provider-router-split`。Architecture Recomposition first branch 已合并，随后 `docs/roadmap.md` 已更新为长期优化目标(`LTO-*`)与近期 phase ticket 队列。

当前 main checkpoint:

- `a1e536b docs(state): update roadmap`
- previous merge: `c3596c2 merge: architecture recomposition first branch`
- latest executed public tag: `v1.5.0` -> `bc8abb1 docs(release): sync v1.5.0 release docs`

Roadmap 当前 ticket 明确为 **Provider Router split (LTO-7 第 1 步)**。Human 已切到 `feat/provider-router-split` 并要求 Codex 开始实现。`model_review.md` 未产出；本轮按 Human 明确实现请求进入实现，并在 active context 中记录该 gate override。

当前 feature branch checkpoint 为 `cbc72ce docs(state): close provider router split implementation`。M1 / M2 / M3 / M4 / M5 均已提交,closeout final。Claude PR review 已完成:`docs/plans/provider-router-split/review_comments.md`。结论:**PASS with 3 CONCERNs (non-blocking),Recommend merge**。Full pytest re-verified locally: `651 passed, 8 deselected, 10 subtests passed`。3 个 CONCERN 已同步到 `docs/concerns_backlog.md` Active Open 表(LTO-7 follow-up group)。

本轮未由 `context-analyst` 产出 `context_brief.md`。依据 `.agents/workflows/feature.md` Step 2，Human 已显式要求 Codex 从 roadmap / design context 生成方案，因此本轮直接产出 `plan.md`；如 plan audit 或 Human 认为需要事实型 brief，可在 Plan Gate 前补 `docs/plans/provider-router-split/context_brief.md`。

## 当前关键文档

1. `docs/active_context.md`(本文)
2. `current_state.md`
3. `docs/roadmap.md`
4. `docs/plans/provider-router-split/plan.md`
5. `docs/plans/provider-router-split/plan_audit.md`
6. `docs/plans/provider-router-split/closeout.md`
7. `docs/plans/provider-router-split/review_comments.md`
8. `docs/concerns_backlog.md`
9. `pr.md`
10. `docs/design/INVARIANTS.md`
11. `docs/design/PROVIDER_ROUTER.md`
12. `docs/design/DATA_MODEL.md`
13. `docs/design/ORCHESTRATION.md`
14. `docs/design/EXECUTOR_REGISTRY.md`
15. `docs/engineering/CODE_ORGANIZATION.md`
16. `docs/engineering/GOF_PATTERN_ALIGNMENT.md`
17. `docs/engineering/TEST_ARCHITECTURE.md`
18. `docs/plans/architecture-recomposition/plan.md`

## 当前推进

已完成:

- **[Human]** Architecture Recomposition first branch merged into `main`:
  - `c3596c2 merge: architecture recomposition first branch`
- **[Human/Codex]** Roadmap LTO reorganization committed on `main`:
  - `a1e536b docs(state): update roadmap`
- **[Codex]** Next phase selected from roadmap:
  - current ticket: `Provider Router split (LTO-7 第 1 步)`
  - recommended implementation branch: `feat/provider-router-split`
- **[Codex]** Provider Router plan drafted:
  - `docs/plans/provider-router-split/plan.md`
- **[Claude/design-auditor]** Provider Router plan audit completed:
  - `docs/plans/provider-router-split/plan_audit.md`
  - result: 1 BLOCKER + 4 CONCERNs, no SCOPE WARNING
- **[Codex]** Provider Router plan revised to absorb audit findings:
  - resolved blocker by requiring extracted selection code to import `DEFAULT_EXECUTOR` / `normalize_executor_name` from `swallow.knowledge_retrieval.dialect_data`, not `swallow.orchestration.executor`
  - folded M0 into M1 to keep the plan at five milestones
  - specified `tests/unit/provider_router/` for new characterization tests
  - made the `agent_llm.py` completion-gateway lazy import update mandatory in M4
  - tightened M2 transaction-wrapper preservation rules
- **[Human]** Implementation start requested on `feat/provider-router-split`.
- **[Codex]** M1 route policy / registry extraction implemented:
  - added `src/swallow/provider_router/route_policy.py` for route policy normalization, SQLite-backed load/save/apply, and current state
  - added `src/swallow/provider_router/route_registry.py` for route registry normalization/default loading, `RouteRegistry`, and candidate route helpers
  - kept `src/swallow/provider_router/router.py` as compatibility facade
  - wired route policy facade calls through `route_policy.py`
  - wired default route registry normalization/loading and `RouteRegistry` through `route_registry.py`
  - removed the Provider Router dependency on `swallow.orchestration.executor` for `DEFAULT_EXECUTOR` / `normalize_executor_name`; provider router now uses `swallow.knowledge_retrieval.dialect_data`
  - added `tests/unit/provider_router/test_registry_policy_modules.py`
- **[Codex]** M1 validation passed:
  - `.venv/bin/python -m pytest tests/unit/provider_router tests/test_router.py tests/test_governance.py tests/test_meta_optimizer.py tests/test_invariant_guards.py tests/test_synthesis.py tests/test_executor_protocol.py tests/test_executor_async.py tests/eval/test_http_executor_eval.py -q` -> `126 passed, 2 deselected`
  - `.venv/bin/python -m compileall -q src/swallow` -> passed
  - `git diff --check` -> passed
  - `.venv/bin/python -m pytest -q` -> `640 passed, 8 deselected, 10 subtests passed`
- **[Human]** M1 implementation committed on `feat/provider-router-split`:
  - `088e80a feat(M1):Baseline, registry, and policy extraction`
- **[Codex]** M2 route metadata store extraction implemented:
  - added `src/swallow/provider_router/route_metadata_store.py` for SQLite-backed route registry, route policy, route weights, capability profiles, legacy JSON bootstrap, and `route_metadata_snapshot`
  - preserved the `_run_sqlite_write` + `sqlite_store.get_connection` transaction wrapper contract verbatim in `route_metadata_store.py`
  - kept `src/swallow/provider_router/router.py` as the public compatibility facade and delegated route metadata load/save/snapshot functions to `route_metadata_store.py`
  - kept route policy normalization / state in `route_policy.py`; policy load/save now route through the metadata store implementation
  - added `tests/unit/provider_router/test_metadata_store_module.py` for module/facade round-trip and snapshot coverage
- **[Codex]** M2 validation passed:
  - `.venv/bin/python -m pytest tests/unit/provider_router -q` -> `5 passed`
  - `.venv/bin/python -m pytest tests/test_router.py tests/test_governance.py tests/test_meta_optimizer.py tests/test_phase65_sqlite_truth.py tests/test_invariant_guards.py -q` -> `106 passed`
  - `.venv/bin/python -m compileall -q src/swallow` -> passed
  - `git diff --check` -> passed
  - `rg -n "from swallow\.orchestration\.executor|orchestration\.executor" src/swallow/provider_router` -> no matches
  - `.venv/bin/python -m pytest -q` -> `642 passed, 8 deselected, 10 subtests passed`
- **[Human]** M2 implementation and M2 state sync committed on `feat/provider-router-split`:
  - `2ff2941 refactor(router): extract route metadata store`
  - `87b2919 docs(state): update provider router split m2 state`
- **[Codex]** M3 route selection extraction implemented:
  - added `src/swallow/provider_router/route_selection.py` for `select_route`, route lookup, detached route construction, fallback chain resolution, route mode/name normalization facade helpers, strategy match reason rendering, and complexity bias
  - kept `src/swallow/provider_router/router.py` as the public compatibility facade; facade functions pass the current `ROUTE_REGISTRY` into `route_selection.py` so existing tests/callers that patch `swallow.provider_router.router.ROUTE_REGISTRY` keep working
  - imported `DEFAULT_EXECUTOR` / `normalize_executor_name` in the extracted selection module from `swallow.knowledge_retrieval.dialect_data`, not `swallow.orchestration.executor`
  - added `tests/unit/provider_router/test_route_selection_module.py` for direct module/facade parity, detached route/fallback chain behavior, and import-boundary coverage
- **[Codex]** M3 validation passed:
  - `.venv/bin/python -m compileall -q src/swallow` -> passed
  - `.venv/bin/python -m pytest tests/unit/provider_router -q` -> `8 passed`
  - `.venv/bin/python -m pytest tests/test_router.py tests/test_synthesis.py tests/test_executor_protocol.py tests/test_executor_async.py tests/eval/test_http_executor_eval.py tests/test_invariant_guards.py -q` -> `94 passed, 2 deselected`
  - `.venv/bin/python -m pytest tests/test_governance.py tests/test_meta_optimizer.py tests/test_phase65_sqlite_truth.py -q` -> `50 passed`
  - `rg -n "from swallow\.orchestration\.executor|orchestration\.executor" src/swallow/provider_router` -> no matches
  - `git diff --check` -> passed
  - `.venv/bin/python -m pytest -q` -> `645 passed, 8 deselected, 10 subtests passed`
- **[Human]** M3 implementation and M3 state sync committed on `feat/provider-router-split`:
  - `eb7c54e refactor(router): extract route selection`
  - `270c239 docs(router): extract route selection`
- **[Codex]** M4 completion gateway and reports extraction implemented:
  - added `src/swallow/provider_router/completion_gateway.py` for the controlled HTTP chat-completions gateway previously exposed as `invoke_completion`
  - added `src/swallow/provider_router/route_reports.py` for route registry / policy / weights / capability profile report rendering
  - kept `src/swallow/provider_router/router.py` as compatibility facade by re-exporting `invoke_completion` and report builders from the extracted modules
  - updated `src/swallow/provider_router/agent_llm.py` lazy import to `from .completion_gateway import invoke_completion`
  - moved route policy report rendering out of `route_policy.py` so route policy owns policy state and normalization only
  - updated the specialist internal LLM invariant guard so direct chat-completion HTTP remains allowed only inside `completion_gateway.invoke_completion`
  - added `tests/unit/provider_router/test_completion_gateway_module.py` and `tests/unit/provider_router/test_reports_module.py`
- **[Codex]** M4 validation passed:
  - `.venv/bin/python -m pytest tests/unit/provider_router -q` -> `11 passed`
  - `.venv/bin/python -m pytest tests/test_router.py tests/test_invariant_guards.py tests/test_cli.py -q` -> `298 passed, 10 subtests passed`
  - `.venv/bin/python -m compileall -q src/swallow` -> passed
  - `git diff --check` -> passed
  - `rg -n "from swallow\.orchestration\.executor|orchestration\.executor" src/swallow/provider_router` -> no matches
  - `.venv/bin/python -m pytest -q` -> `648 passed, 8 deselected, 10 subtests passed`
- **[Human]** M4 implementation and M4 state sync committed on `feat/provider-router-split`:
  - `380d202 refactor(router): extract completion gateway and reports`
  - `18ba7b8 docs(state): update provider router split m4 state`
- **[Codex]** M5 cleanup and closeout implemented:
  - reduced `src/swallow/provider_router/router.py` to a compatibility facade over focused Provider Router modules
  - removed dead private `RouteRegistry`, SQLite route metadata, route selection helper, completion gateway, and report rendering implementations from `router.py`
  - kept public constants, aliases, wrapper functions, and the patched `ROUTE_REGISTRY` compatibility boundary in `router.py`
  - added `tests/unit/provider_router/test_router_facade_module.py` to lock module ownership and facade cleanup expectations
  - wrote `docs/plans/provider-router-split/closeout.md`
  - updated `current_state.md`
  - updated root `pr.md` for Human PR creation
- **[Codex]** M5 validation passed:
  - `.venv/bin/python -m pytest tests/unit/provider_router -q` -> `14 passed`
  - `.venv/bin/python -m pytest tests/test_router.py tests/test_governance.py tests/test_meta_optimizer.py tests/test_phase65_sqlite_truth.py tests/test_invariant_guards.py tests/test_cli.py -q` -> `348 passed, 10 subtests passed`
  - `.venv/bin/python -m pytest tests/test_synthesis.py tests/test_executor_protocol.py tests/test_executor_async.py tests/eval/test_http_executor_eval.py -q` -> `38 passed, 2 deselected`
  - `.venv/bin/python -m compileall -q src/swallow` -> passed
  - `git diff --check` -> passed
  - `rg -n "from swallow\.orchestration\.executor|orchestration\.executor" src/swallow/provider_router` -> no matches
  - `rg -n "sqlite_store|sqlite3|httpx\.post|class RouteRegistry|def invoke_completion|def build_route_registry_report|_replace_route_registry_in_sqlite" src/swallow/provider_router/router.py` -> no matches
  - `.venv/bin/python -m pytest -q` -> `651 passed, 8 deselected, 10 subtests passed`
- **[Human]** M5 cleanup and closeout committed on `feat/provider-router-split`:
  - `64995d6 refactor(router): reduce provider router facade`
  - `cbc72ce docs(state): close provider router split implementation`
- **[Claude]** PR review completed:
  - `docs/plans/provider-router-split/review_comments.md`
  - result: `PASS` with 3 non-blocking CONCERNs
  - recommendation: merge
  - full pytest re-verified during review: `651 passed, 8 deselected, 10 subtests passed`
- **[Codex/Claude]** Review CONCERNs synced to backlog:
  - `docs/concerns_backlog.md`
  - group: `Provider Router Split (LTO-7) follow-up`

进行中:

- **[Human]** Merge gate.

已确认决策:

- **[Human]** Implementation requested on `feat/provider-router-split` before `model_review.md` was produced.
- **[Codex]** Model review status recorded as `not_produced_human_implementation_requested`; implementation proceeded under explicit Human instruction.
- **[Human]** M1 commit is present as `088e80a`.
- **[Human]** M2 implementation and state commits are present as `2ff2941` and `87b2919`.
- **[Human]** M3 implementation and state commits are present as `eb7c54e` and `270c239`.
- **[Human]** M4 implementation and state commits are present as `380d202` and `18ba7b8`.
- **[Human]** M5 implementation and closeout commits are present as `64995d6` and `cbc72ce`.
- **[Claude]** Review produced no BLOCK; Codex assessed no code change is needed before merge.

待执行:

- **[Human]** Merge `feat/provider-router-split` if accepted.
- **[Codex]** After merge, sync `current_state.md` / `docs/active_context.md` on `main`.
- **[roadmap-updater]** After merge, perform roadmap factual update.
- **[Claude]** After merge, perform tag evaluation. Current review recommendation: do not tag LTO-7 alone.

当前阻塞项:

- Waiting for Human merge decision.

## Tag 状态

- 最新已执行 tag: `v1.5.0`
- tag target: `bc8abb1 docs(release): sync v1.5.0 release docs`
- tag message: `v1.5.0: raw material store boundary`
- 结论: tag release gate 已关闭;当前处于 Provider Router Split merge gate。Claude review 建议 LTO-7 alone 不打 tag，等 Cluster-C subtracks 形成更完整能力边界后再评估。

## 当前下一步

1. **[Human]** Review PR and Claude review result.
2. **[Human]** Merge `feat/provider-router-split` if accepted.
3. **[Codex]** Post-merge state sync on `main`.
4. **[roadmap-updater]** Post-merge roadmap factual update.

```markdown
milestone_gate:
- current: provider-router-split-pr-review-pass
- active_branch: feat/provider-router-split
- latest_main_checkpoint: a1e536b docs(state): update roadmap
- previous_merge: c3596c2 merge: architecture recomposition first branch
- active_track: Architecture / Engineering
- active_phase: Provider Router Split / LTO-7 Step 1
- active_slice: PR review complete; awaiting Human merge decision
- plan: docs/plans/provider-router-split/plan.md (revised after audit)
- plan_audit: docs/plans/provider-router-split/plan_audit.md (1 BLOCKER + 4 CONCERN, no SCOPE WARNING)
- audit_absorbed: import source blocker, milestone count, test location, agent_llm update rule, transaction wrapper rule
- context_brief: not produced; Human requested Codex plan generation from roadmap/design context
- model_review.status: not_produced_human_implementation_requested
- implementation_branch: feat/provider-router-split
- m1_commit: 088e80a feat(M1):Baseline, registry, and policy extraction
- m2_commits: 2ff2941 refactor(router): extract route metadata store; 87b2919 docs(state): update provider router split m2 state
- m3_commits: eb7c54e refactor(router): extract route selection; 270c239 docs(router): extract route selection
- m4_commits: 380d202 refactor(router): extract completion gateway and reports; 18ba7b8 docs(state): update provider router split m4 state
- m5_commits: 64995d6 refactor(router): reduce provider router facade; cbc72ce docs(state): close provider router split implementation
- m1_outputs: route_policy.py, route_registry.py, router.py compatibility facade updates, tests/unit/provider_router/test_registry_policy_modules.py
- m1_validation: focused provider/router/governance/meta/invariant/synthesis/executor/eval gate `126 passed, 2 deselected`; compileall passed; full pytest `640 passed, 8 deselected, 10 subtests passed`; git diff --check passed
- m2_outputs: route_metadata_store.py, router.py metadata-store facade delegation, route_policy.py policy persistence delegation, tests/unit/provider_router/test_metadata_store_module.py
- m2_validation: unit provider_router `5 passed`; router/governance/meta/phase65/invariant gate `106 passed`; compileall passed; git diff --check passed; provider_router orchestration.executor grep no matches; full pytest `642 passed, 8 deselected, 10 subtests passed`
- m3_outputs: route_selection.py, router.py selection facade delegation, tests/unit/provider_router/test_route_selection_module.py
- m3_validation: unit provider_router `8 passed`; route/synthesis/executor/eval/invariant gate `94 passed, 2 deselected`; governance/meta/phase65 gate `50 passed`; compileall passed; git diff --check passed; provider_router orchestration.executor grep no matches; full pytest `645 passed, 8 deselected, 10 subtests passed`
- m4_outputs: completion_gateway.py, route_reports.py, router.py gateway/report facade re-exports, agent_llm.py completion gateway lazy import, invariant guard update, tests/unit/provider_router/test_completion_gateway_module.py, tests/unit/provider_router/test_reports_module.py
- m4_validation: unit provider_router `11 passed`; router/invariant/cli gate `298 passed, 10 subtests passed`; compileall passed; git diff --check passed; provider_router orchestration.executor grep no matches; full pytest `648 passed, 8 deselected, 10 subtests passed`
- m5_outputs: router.py thin compatibility facade, tests/unit/provider_router/test_router_facade_module.py, docs/plans/provider-router-split/closeout.md, current_state.md, pr.md, active_context.md state sync
- m5_validation: unit provider_router `14 passed`; router/governance/meta/phase65/invariant/cli gate `348 passed, 10 subtests passed`; synthesis/executor/eval gate `38 passed, 2 deselected`; compileall passed; git diff --check passed; provider_router orchestration.executor grep no matches; router.py extracted-implementation grep no matches; full pytest `651 passed, 8 deselected, 10 subtests passed`
- review: docs/plans/provider-router-split/review_comments.md; PASS with 3 non-blocking CONCERNs; recommend merge
- concerns_backlog: docs/concerns_backlog.md Provider Router Split (LTO-7) follow-up group records all 3 concerns
- next_gate: Human merge decision
```

## 当前产出物

- `docs/active_context.md`(codex, 2026-05-01, updated to Provider Router Split M5 validation / PR-ready state)
- `current_state.md`(codex, 2026-05-01, recovery entry synced to Provider Router Split M5 validation / PR-ready gate)
- `docs/plans/provider-router-split/plan.md`(codex, 2026-05-01, Provider Router Split / LTO-7 Step 1 plan revised after audit)
- `docs/plans/provider-router-split/plan_audit.md`(claude, 2026-05-01, 1 BLOCKER + 4 CONCERN, no SCOPE WARNING; model_review required)
- `docs/plans/provider-router-split/review_comments.md`(claude, 2026-05-01, PR review PASS with 3 non-blocking CONCERNs, recommend merge)
- `docs/concerns_backlog.md`(claude/codex, 2026-05-01, Provider Router Split review concerns recorded under Active Open)
- `src/swallow/provider_router/route_policy.py`(codex, 2026-05-01, route policy module extracted behind router facade; policy persistence now delegates to route metadata store; report rendering moved to route_reports)
- `src/swallow/provider_router/route_registry.py`(codex, 2026-05-01, route registry/default loading module extracted behind router facade)
- `src/swallow/provider_router/route_metadata_store.py`(codex, 2026-05-01, SQLite-backed route metadata store for registry/policy/weights/capability profiles/snapshot)
- `src/swallow/provider_router/route_selection.py`(codex, 2026-05-01, route selection / route lookup / fallback chain module behind router facade)
- `src/swallow/provider_router/completion_gateway.py`(codex, 2026-05-01, controlled HTTP chat-completions gateway extracted behind router facade)
- `src/swallow/provider_router/route_reports.py`(codex, 2026-05-01, route registry/policy/weights/capability profile report rendering extracted behind router facade)
- `src/swallow/provider_router/agent_llm.py`(codex, 2026-05-01, specialist LLM helper lazy-imports completion_gateway directly)
- `src/swallow/provider_router/router.py`(codex, 2026-05-01, thin compatibility facade delegation for route policy/default registry, metadata store, route selection, completion gateway, reports, and executor default import cleanup; dead private implementations removed in M5)
- `tests/unit/provider_router/test_registry_policy_modules.py`(codex, 2026-05-01, focused module/facade compatibility coverage)
- `tests/unit/provider_router/test_metadata_store_module.py`(codex, 2026-05-01, metadata store module/facade round-trip and snapshot coverage)
- `tests/unit/provider_router/test_route_selection_module.py`(codex, 2026-05-01, route selection module/facade parity and import-boundary coverage)
- `tests/unit/provider_router/test_completion_gateway_module.py`(codex, 2026-05-01, completion gateway module/facade and agent_llm lazy-import coverage)
- `tests/unit/provider_router/test_reports_module.py`(codex, 2026-05-01, route report module/facade parity coverage)
- `tests/unit/provider_router/test_router_facade_module.py`(codex, 2026-05-01, router facade ownership and cleanup boundary coverage)
- `tests/test_router.py`(codex, 2026-05-01, mocked completion gateway test retargeted to extracted module)
- `tests/test_invariant_guards.py`(codex, 2026-05-01, specialist internal LLM HTTP guard retargeted to completion_gateway)
- `docs/plans/provider-router-split/closeout.md`(codex, 2026-05-01, Provider Router Split implementation/review closeout and module ownership record)
- `pr.md`(codex, 2026-05-01, Provider Router Split PR body draft updated with Claude review result)
- `docs/roadmap.md`(codex, 2026-05-01, LTO roadmap + Provider Router Split current ticket; existing committed input)
- `docs/plans/architecture-recomposition/plan.md`(codex, 2026-05-01, prior architecture program plan; existing committed input)
