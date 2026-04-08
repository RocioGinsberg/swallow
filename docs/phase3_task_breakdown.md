# Phase 3 Task Breakdown

This document turns the Phase 3 kickoff direction into concrete implementation tasks.

It is intentionally small. The goal is to make the next execution-topology baseline executable without turning the repository into a distributed platform too early.

Status:

- planning baseline created on 2026-04-08
- current runtime reference: `current_state.md`
- kickoff reference: `docs/phase3_kickoff_note.md`

## Working Rule

Phase 3 should preserve the accepted loop from the prior phases:

- truthful lifecycle status
- truthful phase progression
- append-only event history
- inspectable artifacts
- traceable route, compatibility, and retrieval provenance
- local-first default execution

Each task below should be completed with tests and at least one persisted-output check.

## Task Order

Recommended implementation order:

1. `P3-01` Execution topology contract baseline
2. `P3-02` Dispatch record and attempt identity baseline
3. `P3-03` Handoff artifact baseline
4. `P3-04` Topology-aware lifecycle semantics
5. `P3-05` Execution-fit policy baseline
6. `P3-06` Operator inspection path tightening

Current completion state:

- `P3-01` pending
- `P3-02` pending
- `P3-03` pending
- `P3-04` pending
- `P3-05` pending
- `P3-06` pending

## Tasks

### P3-01 Execution Topology Contract Baseline

Goal:
Introduce an explicit execution-topology model so route selection and execution-attempt records stop being implicitly conflated.

Scope:

- define a topology record that captures:
  - route reference
  - execution site
  - transport kind
  - dispatch status
  - remote capability intent
- keep current built-ins local-first
- persist the topology record into task state and run-start events

Likely affected areas:

- `src/swallow/models.py`
- `src/swallow/orchestrator.py`
- `src/swallow/harness.py`
- `src/swallow/router.py`
- `tests/test_cli.py`

Validation:

- topology records are explicit and testable
- persisted outputs show route choice and execution-site choice as related but separate facts
- the accepted local task loop still behaves the same apart from added topology provenance

Non-goals:

- real remote dispatch
- queue systems
- worker orchestration

### P3-02 Dispatch Record And Attempt Identity Baseline

Goal:
Make each run attempt own a clear dispatch record instead of jumping directly from route selection to execution output.

Scope:

- add a small execution-attempt identifier or record
- persist when dispatch was requested and whether it began locally or stayed pending
- keep attempt history append-only and tied to the current run segment

Likely affected areas:

- `src/swallow/harness.py`
- `src/swallow/store.py`
- `src/swallow/models.py`
- `src/swallow/paths.py`
- `tests/test_cli.py`

Validation:

- each run attempt has a stable dispatch record
- events and artifacts show which attempt produced which outputs
- repeated runs remain understandable without replaying the whole event log

Non-goals:

- background supervisors
- external run coordinators
- cross-machine locking

### P3-03 Handoff Artifact Baseline

Goal:
Add a dedicated artifact that explains when a run is prepared for another execution site or operator handoff.

Scope:

- add a readable handoff artifact, likely adjacent to current route and compatibility artifacts
- record execution-site intent, dispatch status, blocking reason, and next operator action
- keep summary and resume note roles intact while improving topology-specific inspection

Likely affected areas:

- `src/swallow/harness.py`
- `src/swallow/store.py`
- `src/swallow/paths.py`
- `src/swallow/cli.py`
- `tests/test_cli.py`

Validation:

- handoff information is easier to inspect than inferring it from raw state
- artifact roles remain separated rather than overloading `summary.md` or `resume_note.md`
- CLI inspection remains coherent

Non-goals:

- full workbench UI
- complex operator inboxes
- external notification systems

### P3-04 Topology-Aware Lifecycle Semantics

Goal:
Allow lifecycle status and phase semantics to represent prepared, dispatched, and resumable execution states truthfully.

Scope:

- define the smallest lifecycle additions needed for topology-aware runs
- make sure a handoff-prepared task is not incorrectly marked as locally executed
- preserve truthful terminal semantics for completed and failed runs

Likely affected areas:

- `src/swallow/orchestrator.py`
- `src/swallow/harness.py`
- `src/swallow/models.py`
- `tests/test_cli.py`

Validation:

- state and events distinguish between execution preparation and execution completion
- resume behavior remains understandable for local runs and deferred-handoff runs
- no regression in accepted lifecycle truthfulness

Non-goals:

- long-lived workflow engines
- arbitrary state-machine expansion

### P3-05 Execution-Fit Policy Baseline

Goal:
Introduce a small policy layer that checks whether the requested execution shape fits the chosen topology.

Scope:

- add first checks around local-only versus handoff-eligible execution shapes
- keep outputs inspectable and artifact-backed
- avoid turning this into a full scheduler or cost policy

Likely affected areas:

- new execution-fit helper modules
- `src/swallow/harness.py`
- `src/swallow/models.py`
- `src/swallow/store.py`
- `tests/test_cli.py`

Validation:

- success, warning, and failure cases are testable
- execution-fit results are visible in persisted outputs or events
- policy checks do not break the accepted local path

Non-goals:

- resource autoscaling
- cost optimization
- multi-tenant quotas

### P3-06 Operator Inspection Path Tightening

Goal:
Make execution-topology outputs easier to review, resume, and compare during later task work.

Scope:

- add or tighten dedicated CLI inspection paths for topology and handoff artifacts
- improve how summaries, resume notes, and memory reference topology outputs
- keep artifact indexing stable and easy to inspect

Likely affected areas:

- `src/swallow/cli.py`
- `src/swallow/harness.py`
- `src/swallow/store.py`
- `tests/test_cli.py`

Validation:

- operators can inspect topology outputs without reading raw JSON first
- topology artifacts remain clearly separated from route, compatibility, retrieval, and validation artifacts
- reruns preserve topology context in a reusable form

Non-goals:

- full task dashboard UI
- external observability platforms

## Deferred Beyond This Breakdown

Keep these outside the active Phase 3 task list unless a concrete implementation need appears:

- real remote workers
- hosted job queues
- distributed scheduling systems
- fleet management
- broad provider-marketplace expansion
- heavy multi-agent runtime orchestration
- large desktop workbench implementation

## Planning Judgment

Phase 3 should start from this execution-topology baseline rather than from backend breadth or UI breadth.

If later planning changes the primary track, this breakdown should be updated rather than half-followed.
