# Phase 8 Task Breakdown

This document turns the next execution-control-policy direction into small executable slices.

It should preserve:

- the accepted local task loop
- current route, topology, execution-site, and handoff semantics
- the completed Phase 7 execution-site-boundary baseline
- explicit state, event, and artifact truthfulness

Status:

- planning baseline created on 2026-04-09
- current runtime reference: `current_state.md`
- kickoff reference: `docs/phase8_kickoff_note.md`
- prior closeout references:
  - `docs/phase3_closeout_note.md`
  - `docs/phase4_closeout_note.md`
  - `docs/phase5_closeout_note.md`
  - `docs/post_phase5_executor_and_external_input_closeout_note.md`
  - `docs/post_phase5_retrieval_memory_next_closeout_note.md`
  - `docs/phase6_closeout_note.md`
  - `docs/phase7_closeout_note.md`

## Working Rule

Every slice in this breakdown should preserve:

- truthful lifecycle status
- append-only event history
- inspectable artifacts
- explicit execution-control decisions
- local-first default execution

This breakdown is about execution control policy.

It is not about hosted governance, remote scheduling, or broad platform administration.

## Recommended Order

1. `P8-01` Retry-policy baseline
2. `P8-02` Stop and escalation policy baseline
3. `P8-03` Detached-execution checkpoint baseline
4. `P8-04` Execution budget and timeout policy baseline
5. `P8-05` Policy inspection and review tightening
6. `P8-06` Closeout and status alignment

Current completion state:

- `P8-01` complete
- `P8-02` complete
- `P8-03` complete
- `P8-04` complete
- `P8-05` complete
- `P8-06` complete

## Tasks

### P8-01 Retry-Policy Baseline

Goal:
Introduce an explicit retry-policy record for execution attempts.

Scope:

- define narrow retry eligibility and retry state fields
- record whether a failure is retryable by current baseline policy
- keep retry decisions explicit rather than implied by executor output alone

Likely affected areas:

- `src/swallow/models.py`
- `src/swallow/harness.py`
- `src/swallow/store.py`
- `src/swallow/cli.py`
- `tests/test_cli.py`

Validation:

- retry policy is explicit and testable
- retryable versus non-retryable failures are visible in artifacts and review flows
- current accepted run loop remains truthful

Non-goals:

- automatic retry loops
- distributed retry workers

### P8-02 Stop And Escalation Policy Baseline

Goal:
Make stop versus continue policy explicit when execution fails or reaches a checkpoint boundary.

Scope:

- define narrow stop, continue, and escalate policy states
- persist policy decisions in execution-control artifacts
- preserve operator-facing readability

Likely affected areas:

- `src/swallow/harness.py`
- `src/swallow/execution_fit.py`
- `src/swallow/compatibility.py`
- `tests/test_cli.py`

Validation:

- stop and escalation policy outcomes are explicit and inspectable
- policy does not silently alter lifecycle truth

Non-goals:

- approval workflows
- multi-operator routing

### P8-03 Detached-Execution Checkpoint Baseline

Goal:
Add a narrow safety checkpoint policy around detached local execution.

Scope:

- define when detached execution should require explicit review or checkpoint handling
- keep detached policy small and local-first
- preserve detached runtime truth added in Phase 7

Likely affected areas:

- `src/swallow/harness.py`
- `src/swallow/execution_fit.py`
- `src/swallow/cli.py`
- `tests/test_cli.py`

Validation:

- detached execution policy decisions are visible in state and artifacts
- inline and detached paths remain distinguishable

Non-goals:

- remote-worker checkpoint systems
- supervisor daemons

### P8-04 Execution Budget And Timeout Policy Baseline

Goal:
Make narrow budget and timeout policy visible without building a full resource-governance layer.

Scope:

- define inspectable timeout and budget-policy records
- connect them to existing executor timeout behavior where appropriate
- keep policy artifact-backed and local

Likely affected areas:

- `src/swallow/executor.py`
- `src/swallow/harness.py`
- `src/swallow/cli.py`
- `tests/test_cli.py`

Validation:

- timeout and budget policy records are explicit
- policy remains reviewable through summary, review, and dedicated artifacts

Non-goals:

- billing systems
- hosted quota management

### P8-05 Policy Inspection And Review Tightening

Goal:
Align operator inspection paths with the new execution-control policy semantics.

Scope:

- expose retry, stop, escalation, checkpoint, and timeout policy state in inspect/review flows
- add or tighten dedicated artifacts as needed
- preserve current artifact grouping clarity

Likely affected areas:

- `src/swallow/cli.py`
- `src/swallow/harness.py`
- `tests/test_cli.py`

Validation:

- operators can inspect execution-control policy state without reading raw JSON first
- policy artifacts remain separate from route, topology, and retrieval artifacts

Non-goals:

- full dashboard UI
- external observability systems

### P8-06 Closeout And Status Alignment

Goal:
Close the phase by aligning status documents and producing a clear stop/go judgment.

Scope:

- align status-entry documents with resulting policy baseline
- write a Phase 8 closeout note
- ensure planning-entry references point to the right checkpoint

Likely affected areas:

- `current_state.md`
- `.codex/phases/active.md`
- `.codex/context/current-system.md`
- `.codex/context/current-scope.md`
- `tests/test_cli.py`

Validation:

- status documents agree on the resulting checkpoint
- closeout note gives a clear stop/go boundary

Non-goals:

- starting the next phase implicitly

## Deferred Beyond This Breakdown

Keep these outside the active Phase 8 task list unless a concrete implementation need appears:

- automatic remote retry orchestration
- hosted policy control planes
- multi-tenant governance
- broad budget optimization systems
- remote transport policy breadth
- large workbench UI expansion

## Planning Judgment

Phase 8 should start from execution-control policy rather than from broader execution-topology or hosted-governance work.

If later planning changes the primary track, this breakdown should be updated rather than half-followed.
