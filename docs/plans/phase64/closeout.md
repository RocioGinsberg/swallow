---
author: codex
phase: phase64
slice: closeout
status: review
created_at: 2026-04-29
depends_on:
  - docs/plans/phase64/kickoff.md
  - docs/plans/phase64/design_decision.md
  - docs/plans/phase64/risk_assessment.md
  - docs/plans/phase64/design_audit.md
  - docs/plans/phase64/model_review.md
  - docs/plans/phase64/commit_summary.md
  - docs/plans/phase64/consistency_report.md
  - docs/plans/phase64/review_comments.md
---

TL;DR: Phase 64 implementation and review follow-up are complete. The two G.5 LLM path guards are active, Path B no longer performs Provider Router selection, Specialist internal chat-completion goes through `router.invoke_completion`, route metadata/policy hardcoding has been externalized under route metadata governance, and Claude review's only CONCERN was handled by promoting fallback chain resolution to `router.resolve_fallback_chain`.

# Phase 64 Closeout

## Conclusion

Phase 64 `Governance Boundary LLM Path Closure` completed the revised-after-model-review S1/S2 scope and the Human-approved route externalization follow-ups:

- Path B fallback selection was moved out of Executor. Orchestrator resolves a full fallback chain plan and writes it to `TaskState.fallback_route_chain`; Executor consumes the chain and may only call `lookup_route_by_name` for static metadata lookup.
- Specialist internal chat-completion now goes through `router.invoke_completion`; `agent_llm.call_agent_llm` is a thin caller, and shared HTTP helpers live in `swallow._http_helpers`.
- `test_path_b_does_not_call_provider_router` and `test_specialist_internal_llm_calls_go_through_router` are both active; `tests/test_invariant_guards.py` contains no `pytest.skip`.
- Route fallback overrides, route registry metadata, and route selection policy metadata are externalized in three distinct layers.
- Route registry and route policy writes go through `register_route_metadata_proposal(...)` and `apply_proposal(..., ProposalTarget.ROUTE_METADATA)`.
- `docs/design/INVARIANTS.md` and `docs/design/DATA_MODEL.md` remain untouched.

The phase is ready for Human PR creation / Merge Gate review after the current review-follow-up and closeout commit.

## Milestone Review

### M1/S1: Path B Fallback Chain Plan

Implemented:

- Added `TaskState.fallback_route_chain`.
- Added read-only `lookup_route_by_name(...)` for Executor metadata consumption.
- Orchestrator populates a full fallback chain plan when applying a route to task state.
- Executor `_load_fallback_route(...)` reads `state.fallback_route_chain` and no longer calls Provider Router selection helpers.
- MPS participant state gets a route-specific fallback chain.
- Enabled `test_path_b_does_not_call_provider_router`.

Validation at gate:

- `tests/test_invariant_guards.py tests/test_router.py` -> 49 passed / 1 skipped.
- `tests/test_executor_protocol.py tests/test_executor_async.py tests/test_binary_fallback.py` -> 34 passed.
- `tests/test_cli.py -k 'fallback or route'` -> 34 passed / 205 deselected.
- `tests/test_synthesis.py` -> 7 passed.
- Full pytest -> 578 passed / 1 skipped / 8 deselected.

### M1 Follow-Up: Fallback Override Config Seam

Implemented after Human feedback that the built-in fallback chain should not become a fixed long-term contract:

- Added `.swl/route_fallbacks.json`.
- Added `load_route_fallbacks(...)` / `apply_route_fallbacks(...)`.
- Applied fallback overrides before route selection use sites build fallback chain state.
- Updated tests so they no longer treat the full built-in chain as a hard-coded permanent contract.

Validation at gate:

- Fallback targeted suite -> 5 passed / 24 deselected.
- Executor sync/async fallback targeted suite -> 3 passed.
- `tests/test_router.py tests/test_invariant_guards.py tests/test_synthesis.py` -> 57 passed / 1 skipped.
- Full pytest -> 579 passed / 1 skipped / 8 deselected.

### M2/S2: Router Completion Gateway

Implemented:

- Added `swallow._http_helpers` for shared HTTP helper code.
- Added `router.invoke_completion(...)`.
- Changed `agent_llm.call_agent_llm(...)` into a thin caller.
- Enabled `test_specialist_internal_llm_calls_go_through_router`.
- Added smoke coverage that mocks `swallow.router.httpx.post` to prove the full `call_agent_llm -> invoke_completion -> httpx.post` path runs.

Validation at gate:

- Gateway guard + smoke test -> 2 passed.
- `tests/test_specialist_agents.py tests/test_retrieval_adapters.py -q` -> 36 passed.
- `tests/test_executor_protocol.py tests/test_executor_async.py -q` -> 31 passed.
- Combined targeted suite -> 119 passed.
- Full pytest rerun -> 581 passed / 8 deselected.

### M2 Follow-Up: Route Registry Metadata Externalization

Implemented after Human asked to eliminate route registry hardcoding:

- Added `src/swallow/routes.default.json`.
- Added workspace override `.swl/routes.json`.
- Added `load_route_registry(...)` / `save_route_registry(...)` / `apply_route_registry(...)`.
- Added `swl route registry show/apply`.
- Extended route metadata governance with `route_registry=...`.
- Added tests for default JSON load, workspace registry application, governance writes, CLI show/apply, and writer guards.

Validation at gate:

- `tests/test_router.py tests/test_governance.py tests/test_invariant_guards.py -q` -> 63 passed.
- Registry CLI + route subset -> 49 passed / 191 deselected / 5 subtests passed.
- `tests/test_meta_optimizer.py -q` -> 19 passed.
- Executor/synthesis targeted suite -> 38 passed.
- `tests/audit_no_skip_drift.py` -> all 8 tracked guards green.
- Full pytest -> 585 passed / 8 deselected.

### M2 Follow-Up: Route Selection Policy Externalization

Implemented after Human asked whether remaining hardcoded mapping/bias items should be externalized:

- Added `src/swallow/route_policy.default.json`.
- Added workspace override `.swl/route_policy.json`.
- Added `load_route_policy(...)` / `save_route_policy(...)` / `apply_route_policy(...)`.
- Added `swl route policy show/apply`.
- Externalized `ROUTE_MODE_TO_ROUTE_NAME`, complexity bias routes, strategy complexity hints, parallel intent hints, and summary fallback route name.
- Extended route metadata governance with `route_policy=...`.
- Added tests for default JSON load, workspace policy application, governance writes, CLI show/apply, and writer guards.

Validation at gate:

- `tests/test_router.py tests/test_governance.py tests/test_invariant_guards.py -q` -> 66 passed.
- Policy CLI + route subset -> 50 passed / 191 deselected / 5 subtests passed.
- `tests/audit_no_skip_drift.py` -> all 8 tracked guards green.
- `tests/test_meta_optimizer.py -q` -> 19 passed.
- Executor/synthesis targeted suite -> 38 passed.
- Full pytest -> 589 passed / 8 deselected.

## Review Follow-Up

Claude review verdict: APPROVE, 0 BLOCK / 1 CONCERN / 8 NOTE.

Handled in this closeout pass:

- CONCERN-1: `synthesis.py` imported Orchestrator's private `_resolve_fallback_chain`. Fixed by promoting the fallback chain resolver to public `router.resolve_fallback_chain(...)`; Orchestrator and synthesis now both call the router API, and tests import the public router API.

Closeout-only notes recorded here:

- `route_fallbacks.json` intentionally remains an operator-local config seam and does not go through governance. Route registry and route policy are the governed metadata layers.
- `retrieval_adapters.py` embeddings HTTP calls remain outside the chat-completion guard scope by design.
- The final `test_specialist_internal_llm_calls_go_through_router` guard is intentionally endpoint-pattern based, not a general "all httpx.post" ban.
- Route policy is intentionally part of `ProposalTarget.ROUTE_METADATA`, not `ProposalTarget.POLICY`, because it governs Provider Router selection metadata rather than global Swallow policy.

Backlog updates made in `docs/concerns_backlog.md`:

- Moved the Phase 61 / Phase 63 G.5 guard skip placeholder concern to Resolved by Phase 64.
- Added Phase 64 review M2-2 as an Open concern: the chat-completion guard does not track indirect URL variable binding such as `endpoint = resolve_new_api_chat_completions_url(); httpx.post(endpoint, ...)`.

## Deferred By Design

- Candidate H / future Truth Plane work: migrate route/policy truth to SQLite and make `apply_proposal` route/policy writes transactional.
- Future durable proposal work: replace in-memory proposal registration with durable proposal artifacts and lifecycle cleanup.
- Future governance work: evaluate the existing canonical `librarian_side_effect` path against INVARIANTS §5.
- Future guard precision work: decide whether the chat-completion guard should implement def-use analysis for indirect URL bindings.

## Final Verification

Review follow-up targeted verification:

```bash
.venv/bin/python -m pytest tests/test_router.py tests/test_synthesis.py tests/test_executor_protocol.py tests/test_executor_async.py tests/test_invariant_guards.py -q
# 94 passed
```

Final full verification:

```bash
.venv/bin/python -m pytest
# 589 passed, 8 deselected

.venv/bin/python tests/audit_no_skip_drift.py
# all 8 tracked guards green

git diff --check
# passed

git diff -- docs/design/INVARIANTS.md docs/design/DATA_MODEL.md
# no output
```

## Stop / Go

### Stop

Phase 64 should stop here. Continuing into SQLite-backed route/policy truth, durable proposals, or deeper AST data-flow guard analysis would expand beyond the approved Phase 64 scope.

### Go

Go to PR creation and Human Merge Gate:

- `review_comments.md` is final and APPROVE.
- The only review CONCERN has been handled in code.
- `consistency_report.md` is consistent.
- `commit_summary.md`, `closeout.md`, `docs/concerns_backlog.md`, `docs/active_context.md`, and `pr.md` reflect the current state.
- Human can use `pr.md` to create or update the PR description.
