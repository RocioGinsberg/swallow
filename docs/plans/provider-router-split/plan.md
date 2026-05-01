---
author: codex
phase: provider-router-split
slice: phase-plan
status: review
depends_on:
  - docs/roadmap.md
  - docs/active_context.md
  - docs/plans/provider-router-split/plan_audit.md
  - docs/design/INVARIANTS.md
  - docs/design/PROVIDER_ROUTER.md
  - docs/design/DATA_MODEL.md
  - docs/design/ORCHESTRATION.md
  - docs/design/EXECUTOR_REGISTRY.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/GOF_PATTERN_ALIGNMENT.md
  - docs/engineering/TEST_ARCHITECTURE.md
---

TL;DR:
This phase starts `LTO-7` by splitting `src/swallow/provider_router/router.py` behind its existing compatibility facade.
The goal is behavior-preserving maintainability: registry, policy, metadata store, selection, completion gateway, and reports become focused modules without changing public routing semantics.
The audit blocker is absorbed: extracted selection code must avoid the current `router.py` -> `orchestration.executor` dependency and import executor defaults from their true source.

# Provider Router Split Plan

## Frame

- phase: `provider-router-split`
- track: `Architecture / Engineering`
- long_term_goal: `LTO-7 Provider Router Maintainability`
- recommended_branch: `feat/provider-router-split`
- goal: split Provider Router internals into focused modules while preserving the current `swallow.provider_router.router` public compatibility surface.
- current_state: plan revised after audit on `main`; implementation is blocked until required model review, Human Plan Gate, and branch switch.

## Goals

1. Keep `src/swallow/provider_router/router.py` as the compatibility facade for existing imports.
2. Extract route registry / normalization responsibilities into focused modules with unit coverage.
3. Extract route policy and route metadata SQLite persistence without changing route metadata semantics.
4. Extract route selection into a testable strategy module while preserving current `select_route` decisions.
5. Extract completion gateway and report rendering only after lower-risk extraction is stable.
6. Preserve Path A / Path C governance and ensure Path B still never calls Provider Router.

## Non-Goals

- Do not change Provider Router design semantics or update `docs/design/*.md`.
- Do not introduce new providers, new network protocols, new model defaults, or live model test requirements.
- Do not change `routes.default.json` / `route_policy.default.json` contents except if a test fixture must be corrected.
- Do not change Truth schema or add migrations.
- Do not add a new public route metadata mutation entry.
- Do not move Orchestrator control decisions into Provider Router.
- Do not implement LTO-8 Orchestration, LTO-9 Surface / Meta Optimizer, or LTO-10 Governance work in this phase.

## Anchors

- `docs/design/INVARIANTS.md`
  - Path A / B / C boundaries remain fixed.
  - Route metadata / policy writes remain governed by `apply_proposal`.
  - Provider Router must not gain Control Plane authority.
- `docs/design/PROVIDER_ROUTER.md`
  - Router maps logical requests to physical routes for Path A / Path C only.
  - `unsupported_task_types` is hard filtering; `quality_weight` is soft ordering; `quality_weight = 0.0` is disabling.
  - Fallback stays within the same path and does not decide semantic retry or `waiting_human`.
- `docs/design/DATA_MODEL.md`
  - `route_registry`, `route_health`, `event_telemetry`, `policy_records`, and change logs retain their existing write boundaries.
- `docs/design/ORCHESTRATION.md`
  - Orchestrator / Strategy Router remain responsible for task strategy and state advancement.
- `docs/design/EXECUTOR_REGISTRY.md`
  - Entity-to-brand bindings stay outside design docs and remain registry-bound.
- `docs/engineering/CODE_ORGANIZATION.md`
  - Target modules: `route_registry.py`, `route_policy.py`, `route_metadata_store.py`, `route_selection.py`, `completion_gateway.py`, `route_reports.py`.
  - Migration is facade-first with stable public imports.
- `docs/engineering/GOF_PATTERN_ALIGNMENT.md`
  - Use Facade / Strategy / Registry / Adapter as responsibility language, not decorative abstraction.
- `docs/engineering/TEST_ARCHITECTURE.md`
  - Focused tests precede or accompany movement; invariant guards remain prominent.

## Existing Surface

Current direct imports of `swallow.provider_router.router` exist in:

- orchestration: `orchestrator.py`, `synthesis.py`, `review_gate.py`, `executor.py`
- governance: `governance.py`, `truth/route.py`
- surfaces: `cli.py`, `meta_optimizer.py`, `consistency_audit.py`
- tests: `test_router.py`, `test_governance.py`, `test_meta_optimizer.py`, invariant guards, synthesis/executor/eval tests

`router.py` is therefore a compatibility facade for this phase. New modules may be imported by `router.py`, but broad caller migration is not required for the first split unless a small touched-surface migration reduces coupling without changing behavior.

## Dependency Direction Constraints

`router.py` currently imports `DEFAULT_EXECUTOR` and `normalize_executor_name` from `swallow.orchestration.executor`, but those names are defined in `swallow.knowledge_retrieval.dialect_data` and only re-exported through `orchestration.executor`.

Implementation rule:

- extracted Provider Router modules must not import `DEFAULT_EXECUTOR` or `normalize_executor_name` from `swallow.orchestration.executor`.
- `route_selection.py` must import them from `swallow.knowledge_retrieval.dialect_data`, unless implementation first introduces a narrower constants module in a direction that does not create a cross-layer cycle.
- this phase must not add new imports from orchestration implementation modules into provider router internals.

## Target Module Shape

| Module | Ownership | Public Through Facade |
|---|---|---|
| `route_registry.py` | `RouteRegistry`, route spec normalization, default registry loading, fallback chain primitives | yes |
| `route_policy.py` | route mode aliases, route policy normalization/application state, complexity hints | yes |
| `route_metadata_store.py` | SQLite-backed route registry / weights / capability profiles / route policy load-save-bootstrap snapshot | yes |
| `route_selection.py` | `select_route`, candidate ordering, capability/model/task-family filtering, complexity bias, detached route construction; imports executor defaults from `dialect_data`, not `orchestration.executor` | yes |
| `completion_gateway.py` | controlled HTTP chat-completions gateway currently exposed as `invoke_completion`; `agent_llm.py` lazy import must point here after extraction | yes |
| `route_reports.py` | route registry / policy / weights / capability profile report rendering | yes |
| `router.py` | compatibility facade, constants intentionally kept public, re-exports | existing imports stay valid |

The exact split may be adjusted during implementation if tests show a cleaner dependency direction, but the phase must not collapse multiple unrelated architecture subtracks into this work.

## Plan

| Milestone | Slice | Scope | Risk | Validation | Gate |
|---|---|---|---|---|---|
| M1 | Baseline, registry, and policy extraction | Add characterization/import-contract coverage under `tests/unit/provider_router/`, then move normalization, `RouteRegistry`, default registry/policy loading, aliases, and policy state into `route_registry.py` / `route_policy.py`; `router.py` re-exports. | medium | `tests/unit/provider_router/`, `tests/test_router.py`, `tests/test_governance.py` focused cases, invariant guards | Human review + commit |
| M2 | Metadata store extraction | Move SQLite route metadata bootstrap/load/save/snapshot and weights/capability profile persistence into `route_metadata_store.py`; keep `apply_*` facade functions stable and preserve the `_run_sqlite_write` + `sqlite_store.get_connection` transaction wrapper contract verbatim. | high | route metadata tests, governance route proposal tests, `tests/test_phase65_sqlite_truth.py`, invariant guards | Separate Human review + commit |
| M3 | Selection extraction | Move `select_route`, candidate ordering, capability/model/task-family filtering, complexity bias, detached route selection, and fallback chain helpers as appropriate into `route_selection.py`; import `DEFAULT_EXECUTOR` / `normalize_executor_name` from `swallow.knowledge_retrieval.dialect_data`, not `swallow.orchestration.executor`. | high | route selection tests, orchestrator/synthesis focused tests, eval import smoke if cheap | Separate Human review + commit |
| M4 | Completion gateway and reports | Move `invoke_completion` to `completion_gateway.py` and report rendering to `route_reports.py`; update `agent_llm.py`'s lazy import to `from .completion_gateway import invoke_completion`; keep `router.py` re-exporting `invoke_completion` for existing callers. | medium | mocked HTTP gateway test, CLI route report tests, compileall | Human review + commit |
| M5 | Cleanup and closeout | Remove dead private wrappers, document final module ownership and any deferred caller migration in closeout, run full validation. | medium | full pytest, compileall, `git diff --check` | PR-ready gate |

## Material Risks

- Path boundary drift: extraction could make Path B import or call routing behavior accidentally. Mitigation: keep `test_path_b_does_not_call_provider_router` and specialist router guards in every high-risk gate.
- Route metadata write drift: persistence extraction could create a second public metadata mutation path. Mitigation: preserve `apply_proposal` route metadata guards and keep save/apply functions under existing facade semantics.
- Global policy state drift: `ROUTE_MODE_TO_ROUTE_NAME`, complexity hints, and fallback state are module globals today. Mitigation: move state in one milestone, preserve facade-visible getters, and test `apply_route_policy` / `current_route_policy`.
- Transaction nesting regression: current metadata functions use `sqlite_store.get_connection` and `_run_sqlite_write` transaction behavior. Mitigation: M2 must move or preserve that wrapper contract verbatim, keep the same nested-transaction behavior, and pass focused SQLite truth tests before any cleanup.
- Cross-layer import cycle: current `router.py` reaches executor defaults through `orchestration.executor`, which imports Provider Router helpers. Mitigation: extracted Provider Router modules import executor defaults from `swallow.knowledge_retrieval.dialect_data` or a new narrower non-orchestration constants module.
- Import churn: many callers import from `router.py`. Mitigation: first phase keeps existing imports valid; caller migration is optional and touched-surface only.
- Over-extraction: new modules could become powerless wrappers. Mitigation: each module must own one concrete responsibility listed in the target shape; otherwise keep the code in the facade for this phase.

## Validation

Minimum command set for implementation milestones:

```bash
.venv/bin/python -m pytest tests/unit/provider_router -q
.venv/bin/python -m pytest tests/test_router.py -q
.venv/bin/python -m pytest tests/test_governance.py tests/test_meta_optimizer.py -q
.venv/bin/python -m pytest tests/test_invariant_guards.py -q
.venv/bin/python -m compileall -q src/swallow
git diff --check
```

Additional focused checks by milestone:

```bash
.venv/bin/python -m pytest tests/test_phase65_sqlite_truth.py -q
.venv/bin/python -m pytest tests/test_synthesis.py tests/test_executor_protocol.py tests/test_executor_async.py -q
.venv/bin/python -m pytest tests/eval/test_http_executor_eval.py -q
```

Final PR gate:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src/swallow
git diff --check
```

No live HTTP or API-key dependent test is required for this phase; `invoke_completion` coverage should remain mocked.

## Branch And PR Recommendation

- Plan / audit may remain on `main` until Human Plan Gate.
- Implementation branch after Plan Gate: `feat/provider-router-split`.
- Recommended commit shape:
  - `docs(plan): add provider router split plan`
  - `refactor(router): characterize facade and extract registry policy modules`
  - `refactor(router): extract route metadata store`
  - `refactor(router): extract route selection`
  - `refactor(router): extract completion gateway and reports`
  - `docs(state): update provider router split state`

High-risk milestones M2 and M3 should not be combined with unrelated cleanup commits.

## Completion Conditions

1. Existing imports from `swallow.provider_router.router` remain compatible.
2. `router.py` is reduced to a compatibility facade plus intentional public re-exports.
3. Route registry, policy, metadata store, selection, completion gateway, and reports each have an explicit module owner or a documented reason to defer.
4. No design semantics, schema, default route metadata, or public CLI/API behavior changes are introduced.
5. Extracted Provider Router modules do not import executor defaults through `swallow.orchestration.executor`.
6. Invariant guards, focused router/governance tests, compileall, full pytest, and diff hygiene pass.
7. `docs/active_context.md`, closeout material, and PR material record the final module split and any deferred follow-up.

## Plan Audit Notes

- `context_brief.md` is not present because Human asked Codex to begin plan generation directly from roadmap / design context. A `context-analyst` brief can still be requested before audit if Human or Claude wants a separate fact-only coupling summary.
- `docs/plans/provider-router-split/plan_audit.md` found one blocker and four concerns. This revision absorbs them by mapping the executor-default import source, merging M0 into M1 to keep the phase at five milestones, naming `tests/unit/provider_router/`, making the `agent_llm.py` update mandatory in M4, and tightening the M2 transaction-wrapper rule.
- Model review is required before Human Plan Gate because this phase touches Provider Router route metadata boundaries and the audit contained a blocker.
