# Phase 2 Task Breakdown

This document turns the Phase 2 kickoff direction into concrete implementation tasks.

It is intentionally small. The goal is to make Phase 2 executable without turning the repository into a broad backend platform too early.

Status:

- baseline complete on 2026-04-08
- closeout reference: `docs/phase2_closeout_note.md`

## Working Rule

Phase 2 should still preserve the accepted loop from the prior phases:

- truthful lifecycle status
- truthful phase progression
- append-only event history
- inspectable artifacts
- traceable route and capability provenance

Each task below should be completed with tests and at least one persisted-output check.

## Task Order

Recommended implementation order:

1. `P2-01` Route declaration and selection baseline
2. `P2-02` Route policy input baseline
3. `P2-03` Capability declaration refinement
4. `P2-04` Route provenance and artifact tightening
5. `P2-05` Backend-compatibility policy baseline
6. `P2-06` Remote-ready hook baseline

Current completion state:

- `P2-01` completed
- `P2-02` completed
- `P2-03` completed
- `P2-04` completed
- `P2-05` completed
- `P2-06` completed

## Tasks

### P2-01 Route Declaration And Selection Baseline

Goal:
Introduce an explicit route model so executor, runtime backend, and model assumptions stop being implicit.

Scope:

- define route records for the built-in local paths
- add a router module with a narrow selection function
- persist route selection into task state and events
- keep retrieval and validation outside the router

Likely affected areas:

- `src/swallow/router.py`
- `src/swallow/models.py`
- `src/swallow/orchestrator.py`
- `src/swallow/harness.py`
- `tests/test_cli.py`

Validation:

- route selection is explicit and testable
- persisted outputs show which route was selected
- the accepted task loop still behaves the same apart from added route provenance

Non-goals:

- real remote transport
- many backend integrations at once
- broad provider registries

### P2-02 Route Policy Input Baseline

Goal:
Allow small, explicit routing policy inputs without introducing a complex policy engine.

Scope:

- add a persisted route-policy input such as `route_mode`
- allow run-time route-policy overrides
- keep policy inputs small enough to inspect locally
- ensure policy inputs remain visible in state, events, prompts, and task memory

Likely affected areas:

- `src/swallow/router.py`
- `src/swallow/models.py`
- `src/swallow/cli.py`
- `src/swallow/orchestrator.py`
- `src/swallow/executor.py`
- `tests/test_cli.py`

Validation:

- route-policy modes are testable end-to-end
- route-policy inputs change route selection in a predictable way
- persisted route provenance still remains clear

Non-goals:

- learning-based route policies
- pricing-aware optimization
- large rule engines

### P2-03 Capability Declaration Refinement

Goal:
Refine route capability declarations from loose string lists into a clearer, inspectable shape.

Scope:

- replace or wrap free-form capability strings with a small structured capability schema
- distinguish capability dimensions such as:
  - code execution
  - tool loop support
  - network expectations
  - resumability
  - determinism
- keep capability declarations lightweight and local-first

Likely affected areas:

- `src/swallow/models.py`
- `src/swallow/router.py`
- `src/swallow/orchestrator.py`
- `src/swallow/harness.py`
- `tests/test_cli.py`

Validation:

- capability declarations are easier to inspect than the current string lists
- route provenance remains readable in state, events, and artifacts
- tests cover the capability declaration shape

Non-goals:

- a huge capability taxonomy
- plugin marketplace compatibility matrices
- vendor-specific feature encyclopedias

### P2-04 Route Provenance And Artifact Tightening

Goal:
Make route decisions easier to reuse across later review, reruns, and debugging.

Scope:

- improve how route decisions appear in summaries, resume notes, and memory
- add a compact route-grounding artifact if needed
- tighten artifact links between route choice, executor outcome, and validation outcome

Likely affected areas:

- `src/swallow/harness.py`
- `src/swallow/store.py`
- `src/swallow/models.py`
- `tests/test_cli.py`

Validation:

- route-linked artifacts are easier to inspect and reuse
- later task review can recover route provenance without replaying the run
- tests confirm route-related artifact behavior remains stable

Non-goals:

- full observability stacks
- distributed tracing
- heavy telemetry infrastructure

### P2-05 Backend-Compatibility Policy Baseline

Goal:
Introduce the first explicit compatibility checks between task needs and route capabilities.

Scope:

- define a small compatibility policy layer
- add first checks around route capability fit versus requested route mode or task shape
- keep compatibility outputs inspectable and easy to persist

Likely affected areas:

- new route-policy or compatibility helper modules
- `src/swallow/router.py`
- `src/swallow/harness.py`
- `src/swallow/models.py`
- `tests/test_cli.py`

Validation:

- compatibility outcomes are visible in persisted outputs or events
- success, warning, and failure cases are testable
- compatibility policy does not break the accepted lifecycle semantics

Non-goals:

- large scheduling systems
- deep cost routing logic
- multi-tenant policy management

### P2-06 Remote-Ready Hook Baseline

Goal:
Prepare the harness boundary for later remote execution without implementing full remote execution now.

Scope:

- add minimal route fields or interfaces that can later distinguish local and remote execution sites
- keep execution location explicit in route or backend records
- avoid real transport, queueing, or worker orchestration in this slice

Likely affected areas:

- `src/swallow/router.py`
- `src/swallow/models.py`
- `src/swallow/harness.py`
- `src/swallow/orchestrator.py`
- `tests/test_cli.py`

Validation:

- the system can declare whether a route is local-only or remote-capable
- persisted route outputs remain understandable
- tests confirm the hook does not change current local behavior

Non-goals:

- real remote workers
- background job orchestration
- hosted infrastructure rollout

## Deferred Beyond This Breakdown

Keep these outside the active Phase 2 task list unless a concrete implementation need appears:

- real remote execution transport
- broad third-party backend integrations
- large capability marketplaces
- pricing or billing systems
- distributed worker fleets
- complex multi-agent runtime sessions

## Closeout Judgment

The planned Phase 2 baseline is complete.

Do not continue Phase 2 by default through open-ended backend expansion.

Use `docs/phase2_closeout_note.md` as the decision reference before starting any follow-up work.
