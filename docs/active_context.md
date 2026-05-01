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
- active_slice: `M3 route selection extraction`
- active_branch: `feat/provider-router-split`
- status: `m3_validation_passed_waiting_human_review_commit`

## 当前状态说明

当前 git 分支为 `feat/provider-router-split`。Architecture Recomposition first branch 已合并，随后 `docs/roadmap.md` 已更新为长期优化目标(`LTO-*`)与近期 phase ticket 队列。

当前 main checkpoint:

- `a1e536b docs(state): update roadmap`
- previous merge: `c3596c2 merge: architecture recomposition first branch`
- latest executed public tag: `v1.5.0` -> `bc8abb1 docs(release): sync v1.5.0 release docs`

Roadmap 当前 ticket 明确为 **Provider Router split (LTO-7 第 1 步)**。Human 已切到 `feat/provider-router-split` 并要求 Codex 开始实现。`model_review.md` 未产出；本轮按 Human 明确实现请求进入实现，并在 active context 中记录该 gate override。

当前 feature branch checkpoint 为 `87b2919 docs(state): update provider router split m2 state`。M1 与 M2 均已提交，M3 route selection extraction 已完成并通过验证，等待 Human review / commit。

本轮未由 `context-analyst` 产出 `context_brief.md`。依据 `.agents/workflows/feature.md` Step 2，Human 已显式要求 Codex 从 roadmap / design context 生成方案，因此本轮直接产出 `plan.md`；如 plan audit 或 Human 认为需要事实型 brief，可在 Plan Gate 前补 `docs/plans/provider-router-split/context_brief.md`。

## 当前关键文档

1. `docs/active_context.md`(本文)
2. `current_state.md`
3. `docs/roadmap.md`
4. `docs/plans/provider-router-split/plan.md`
5. `docs/plans/provider-router-split/plan_audit.md`
6. `docs/design/INVARIANTS.md`
7. `docs/design/PROVIDER_ROUTER.md`
8. `docs/design/DATA_MODEL.md`
9. `docs/design/ORCHESTRATION.md`
10. `docs/design/EXECUTOR_REGISTRY.md`
11. `docs/engineering/CODE_ORGANIZATION.md`
12. `docs/engineering/GOF_PATTERN_ALIGNMENT.md`
13. `docs/engineering/TEST_ARCHITECTURE.md`
14. `docs/plans/architecture-recomposition/plan.md`

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
  - added `src/swallow/provider_router/route_policy.py` for route policy normalization, SQLite-backed load/save/apply, current state, and report rendering
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
  - kept route policy normalization / state / report rendering in `route_policy.py`; policy load/save now route through the metadata store implementation
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

进行中:

- **[Human/Codex]** M3 review / commit gate.

已确认决策:

- **[Human]** Implementation requested on `feat/provider-router-split` before `model_review.md` was produced.
- **[Codex]** Model review status recorded as `not_produced_human_implementation_requested`; implementation proceeded under explicit Human instruction.
- **[Human]** M1 commit is present as `088e80a`; M2 now proceeds on top of that branch checkpoint.
- **[Human]** M2 commit and state commit are present as `2ff2941` and `87b2919`; Codex may proceed to M3.

待执行:

- **[Human]** Review / commit M3 after validation passes.
- **[Codex]** After M3 commit gate, continue M4 completion gateway and reports extraction.

当前阻塞项:

- Waiting for Human review / commit of M3.

## Tag 状态

- 最新已执行 tag: `v1.5.0`
- tag target: `bc8abb1 docs(release): sync v1.5.0 release docs`
- tag message: `v1.5.0: raw material store boundary`
- 结论: tag release gate 已关闭;当前处于 Provider Router Split M3 implementation review gate。

## 当前下一步

1. **[Human]** Review M3 route selection extraction diff.
2. **[Human]** Commit M3 if accepted.
3. **[Codex]** Continue with M4 completion gateway and reports extraction after commit gate.

```markdown
milestone_gate:
- current: provider-router-split-m3-validation-passed
- active_branch: feat/provider-router-split
- latest_main_checkpoint: a1e536b docs(state): update roadmap
- previous_merge: c3596c2 merge: architecture recomposition first branch
- active_track: Architecture / Engineering
- active_phase: Provider Router Split / LTO-7 Step 1
- active_slice: M3 route selection extraction
- plan: docs/plans/provider-router-split/plan.md (revised after audit)
- plan_audit: docs/plans/provider-router-split/plan_audit.md (1 BLOCKER + 4 CONCERN, no SCOPE WARNING)
- audit_absorbed: import source blocker, milestone count, test location, agent_llm update rule, transaction wrapper rule
- context_brief: not produced; Human requested Codex plan generation from roadmap/design context
- model_review.status: not_produced_human_implementation_requested
- implementation_branch: feat/provider-router-split
- m1_commit: 088e80a feat(M1):Baseline, registry, and policy extraction
- m2_commits: 2ff2941 refactor(router): extract route metadata store; 87b2919 docs(state): update provider router split m2 state
- m1_outputs: route_policy.py, route_registry.py, router.py compatibility facade updates, tests/unit/provider_router/test_registry_policy_modules.py
- m1_validation: focused provider/router/governance/meta/invariant/synthesis/executor/eval gate `126 passed, 2 deselected`; compileall passed; full pytest `640 passed, 8 deselected, 10 subtests passed`; git diff --check passed
- m2_outputs: route_metadata_store.py, router.py metadata-store facade delegation, route_policy.py policy persistence delegation, tests/unit/provider_router/test_metadata_store_module.py
- m2_validation: unit provider_router `5 passed`; router/governance/meta/phase65/invariant gate `106 passed`; compileall passed; git diff --check passed; provider_router orchestration.executor grep no matches; full pytest `642 passed, 8 deselected, 10 subtests passed`
- m3_outputs: route_selection.py, router.py selection facade delegation, tests/unit/provider_router/test_route_selection_module.py
- m3_validation: unit provider_router `8 passed`; route/synthesis/executor/eval/invariant gate `94 passed, 2 deselected`; governance/meta/phase65 gate `50 passed`; compileall passed; git diff --check passed; provider_router orchestration.executor grep no matches; full pytest `645 passed, 8 deselected, 10 subtests passed`
- next_gate: Human M3 review / commit
```

## 当前产出物

- `docs/active_context.md`(codex, 2026-05-01, updated to Provider Router Split M3 validation state)
- `current_state.md`(codex, 2026-05-01, recovery entry synced to Provider Router Split planning)
- `docs/plans/provider-router-split/plan.md`(codex, 2026-05-01, Provider Router Split / LTO-7 Step 1 plan revised after audit)
- `docs/plans/provider-router-split/plan_audit.md`(claude, 2026-05-01, 1 BLOCKER + 4 CONCERN, no SCOPE WARNING; model_review required)
- `src/swallow/provider_router/route_policy.py`(codex, 2026-05-01, route policy module extracted behind router facade; policy persistence now delegates to route metadata store)
- `src/swallow/provider_router/route_registry.py`(codex, 2026-05-01, route registry/default loading module extracted behind router facade)
- `src/swallow/provider_router/route_metadata_store.py`(codex, 2026-05-01, SQLite-backed route metadata store for registry/policy/weights/capability profiles/snapshot)
- `src/swallow/provider_router/route_selection.py`(codex, 2026-05-01, route selection / route lookup / fallback chain module behind router facade)
- `src/swallow/provider_router/router.py`(codex, 2026-05-01, compatibility facade delegation for route policy/default registry, metadata store, and executor default import cleanup)
- `tests/unit/provider_router/test_registry_policy_modules.py`(codex, 2026-05-01, focused module/facade compatibility coverage)
- `tests/unit/provider_router/test_metadata_store_module.py`(codex, 2026-05-01, metadata store module/facade round-trip and snapshot coverage)
- `tests/unit/provider_router/test_route_selection_module.py`(codex, 2026-05-01, route selection module/facade parity and import-boundary coverage)
- `docs/roadmap.md`(codex, 2026-05-01, LTO roadmap + Provider Router Split current ticket; existing committed input)
- `docs/plans/architecture-recomposition/plan.md`(codex, 2026-05-01, prior architecture program plan; existing committed input)
