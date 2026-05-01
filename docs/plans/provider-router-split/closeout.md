---
author: codex
phase: provider-router-split
slice: m5-cleanup-closeout
status: final
depends_on:
  - docs/plans/provider-router-split/plan.md
  - docs/plans/provider-router-split/plan_audit.md
  - docs/active_context.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/design/INVARIANTS.md
  - docs/design/PROVIDER_ROUTER.md
---

TL;DR:
Provider Router Split completed the LTO-7 first step without changing routing semantics, route metadata schema, default route data, or Path A/B/C boundaries.
`router.py` is now a compatibility facade over focused modules for registry, policy, metadata storage, selection, completion gateway, and reports.
Final validation passed with full pytest: `651 passed, 8 deselected, 10 subtests passed`; Claude PR review recommends merge with three non-blocking concerns recorded in `docs/concerns_backlog.md`.

# Provider Router Split Closeout

## Scope

- phase: `Provider Router Split / LTO-7 Step 1`
- branch: `feat/provider-router-split`
- implementation mode: facade-first refactor
- public compatibility target: `swallow.provider_router.router`
- design docs changed: none
- route metadata schema changed: no
- default route metadata changed: no
- live HTTP/API-key test required: no

## What Was Completed

1. M1 extracted route registry and route policy ownership.
2. M2 extracted SQLite-backed route metadata storage.
3. M3 extracted route selection, route lookup, detached route construction, fallback-chain resolution, and complexity bias.
4. M4 extracted the controlled HTTP completion gateway and route report rendering.
5. M5 reduced `router.py` to a compatibility facade and removed dead private implementations that had already moved to focused modules.
6. Focused module/facade tests were added under `tests/unit/provider_router/`.
7. Invariant guards were kept aligned with the new gateway location.
8. `agent_llm.py` now lazy-imports `completion_gateway.invoke_completion` directly.

## Final Module Ownership

| Module | Ownership |
|---|---|
| `route_registry.py` | `RouteRegistry`, route spec normalization, default registry loading, route candidate matching helpers |
| `route_policy.py` | route mode/name aliases, route policy normalization, application state, complexity/parallel intent hints |
| `route_metadata_store.py` | SQLite-backed route registry, route policy, route weights, route capability profiles, legacy JSON bootstrap, metadata snapshot |
| `route_selection.py` | `select_route`, route lookup, detached route construction, fallback chain resolution, strategy match reason rendering, complexity bias |
| `completion_gateway.py` | controlled HTTP chat-completions gateway exposed as `invoke_completion` |
| `route_reports.py` | route registry, route policy, route weights, and route capability profile report rendering |
| `router.py` | compatibility facade, public constants/aliases, public wrapper functions, patched `ROUTE_REGISTRY` boundary |

## Compatibility Notes

- Existing imports from `swallow.provider_router.router` remain valid for the repo's current callers.
- `router.ROUTE_REGISTRY` remains the compatibility patch point for tests and current callers that override route selection state.
- Public functions used by orchestration, governance, CLI, meta optimizer, and tests still route through `router.py`.
- Broad caller migration from `router.py` to focused modules was intentionally deferred. The first split keeps import churn low and leaves migration optional for later touched surfaces.

## Boundary Notes

- Provider Router internals still do not import executor defaults through `swallow.orchestration.executor`.
- `route_selection.py` imports executor defaults from `swallow.knowledge_retrieval.dialect_data`.
- `apply_proposal` remains the route metadata / policy mutation boundary through governance.
- Path B remains outside Provider Router.
- No `docs/design/*.md` semantics were changed.

## Review Outcome

Claude PR review was recorded in `docs/plans/provider-router-split/review_comments.md`.

- verdict: `PASS`
- recommendation: merge
- blocking findings: none
- concerns: 3 non-blocking follow-ups

The three concerns were triaged into `docs/concerns_backlog.md` under `Provider Router Split (LTO-7) follow-up`:

1. Align `test_route_metadata_writes_only_via_apply_proposal` allowlist with the new `route_metadata_store.py` implementation owner before LTO-10.
2. Clean up `router.py` access to underscore-prefixed helpers in `route_policy.py` / `route_registry.py` on a touched-surface basis.
3. Consider moving `_BUILTIN_ROUTE_FALLBACKS` ownership from `router.py` into registry-owned code on a touched-surface basis.

## Validation Commands Run

Focused validation:

```bash
.venv/bin/python -m pytest tests/unit/provider_router -q
# 14 passed

.venv/bin/python -m pytest tests/test_router.py tests/test_governance.py tests/test_meta_optimizer.py tests/test_phase65_sqlite_truth.py tests/test_invariant_guards.py tests/test_cli.py -q
# 348 passed, 10 subtests passed

.venv/bin/python -m pytest tests/test_synthesis.py tests/test_executor_protocol.py tests/test_executor_async.py tests/eval/test_http_executor_eval.py -q
# 38 passed, 2 deselected
```

Final validation:

```bash
.venv/bin/python -m compileall -q src/swallow
# passed

git diff --check
# passed

rg -n "from swallow\.orchestration\.executor|orchestration\.executor" src/swallow/provider_router
# no matches

rg -n "sqlite_store|sqlite3|httpx\.post|class RouteRegistry|def invoke_completion|def build_route_registry_report|_replace_route_registry_in_sqlite" src/swallow/provider_router/router.py
# no matches

.venv/bin/python -m pytest -q
# 651 passed, 8 deselected, 10 subtests passed
```

## Deferred Follow-up

- Optional touched-surface caller migration can import focused modules directly later, but this branch deliberately keeps `router.py` as the stable public surface.
- The three Claude review concerns are non-blocking and are tracked in `docs/concerns_backlog.md`.
- Post-merge state sync and roadmap factual update should happen after Human merge decision.
- Tag evaluation remains a post-merge Claude/Human decision.

## Completion Status

Provider Router Split implementation and review are complete. The branch is ready for Human merge decision.
