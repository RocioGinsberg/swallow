# Phase 7 Task Breakdown

This document turns the next execution-site-boundary direction into small executable slices.

It should preserve:

- the accepted local task loop
- current route and topology semantics
- the completed Phase 3 execution-topology baseline
- the completed Phase 6 retrieval / memory operationalization baseline
- explicit state, event, and artifact truthfulness

Status:

- planning baseline created on 2026-04-09
- current runtime reference: `current_state.md`
- kickoff reference: `docs/phase7_kickoff_note.md`
- prior closeout references:
  - `docs/phase3_closeout_note.md`
  - `docs/phase4_closeout_note.md`
  - `docs/phase5_closeout_note.md`
  - `docs/post_phase5_executor_and_external_input_closeout_note.md`
  - `docs/post_phase5_retrieval_memory_next_closeout_note.md`
  - `docs/phase6_closeout_note.md`

## Working Rule

Every slice in this breakdown should preserve:

- truthful lifecycle status
- append-only event history
- inspectable artifacts
- explicit route-versus-topology separation
- explicit attempt ownership
- local-first default execution

This breakdown is about execution-site boundary tightening.

It is not about hosted scheduling, remote worker fleets, or broad platform infrastructure.

## Recommended Order

1. `P7-01` Execution-site contract baseline
2. `P7-02` Attempt ownership baseline
3. `P7-03` Handoff-contract tightening
4. `P7-04` Local-detached execution baseline
5. `P7-05` Family-aware execution-fit policy tightening
6. `P7-06` Inspection and closeout tightening

Current completion state:

- `P7-01` completed
- `P7-02` completed
- `P7-03` completed
- `P7-04` completed
- `P7-05` completed
- `P7-06` completed

## Tasks

### P7-01 Execution-Site Contract Baseline

Goal:
Introduce an explicit execution-site contract that distinguishes inline execution from detached or remote-candidate execution intent.

Scope:

- define a narrow execution-site record or contract
- keep route selection and execution-site selection related but separate
- persist execution-site intent into state, events, and dedicated artifacts

Likely affected areas:

- `src/swallow/models.py`
- `src/swallow/orchestrator.py`
- `src/swallow/harness.py`
- `src/swallow/store.py`
- `src/swallow/paths.py`
- `tests/test_cli.py`

Validation:

- execution-site records are explicit and testable
- persisted outputs show inline, detached, and remote-candidate intent clearly
- current local inline behavior remains the default baseline

Non-goals:

- real remote transport
- worker scheduling
- queue backends

### P7-02 Attempt Ownership Baseline

Goal:
Make each execution attempt carry an explicit owner and ownership status instead of relying only on dispatch timestamps and attempt identity.

Scope:

- add owner and owner-kind fields for attempts
- define narrow ownership-transfer or handoff-transfer semantics
- preserve append-only attempt history

Likely affected areas:

- `src/swallow/models.py`
- `src/swallow/harness.py`
- `src/swallow/store.py`
- `src/swallow/orchestrator.py`
- `tests/test_cli.py`

Validation:

- each attempt has a stable owner record
- ownership transfer is explicit in events and artifacts
- repeated runs remain understandable without replaying raw history

Non-goals:

- cross-machine locking
- multi-operator arbitration
- distributed coordination

### P7-03 Handoff-Contract Tightening

Goal:
Make handoff artifacts act more like execution contracts than operator-facing summaries.

Scope:

- define required inputs, expected outputs, and next-owner expectations for handoff records
- preserve blocking reason and next action semantics
- keep `summary.md` and `resume_note.md` separate from execution handoff truth

Likely affected areas:

- `src/swallow/harness.py`
- `src/swallow/store.py`
- `src/swallow/paths.py`
- `src/swallow/cli.py`
- `tests/test_cli.py`

Validation:

- handoff artifacts explain what another execution site or owner would need to continue
- handoff truth is easier to inspect than inferring from summary prose alone
- artifact roles remain clearly separated

Non-goals:

- external notification systems
- workbench inboxes
- generic collaboration tooling

### P7-04 Local-Detached Execution Baseline

Goal:
Prove a real execution-site boundary locally by introducing a narrow detached execution path that remains single-machine and artifact-backed.

Scope:

- add a detached local execution mode or equivalent runtime boundary
- preserve current local-inline execution as the default path
- persist detached dispatch and completion semantics truthfully

Likely affected areas:

- `src/swallow/harness.py`
- `src/swallow/executor.py`
- `src/swallow/orchestrator.py`
- `src/swallow/models.py`
- `src/swallow/store.py`
- `tests/test_cli.py`

Validation:

- detached local execution is distinguishable from inline execution in state, events, and artifacts
- summary, resume note, and memory stay truthful for both paths
- no regression in the accepted local inline baseline

Non-goals:

- remote workers
- long-lived daemons
- hosted supervisors

### P7-05 Family-Aware Execution-Fit Policy Tightening

Goal:
Tighten execution-fit policy so executor-family expectations affect whether a requested execution shape is valid.

Scope:

- add first family-aware checks around API executor versus CLI executor expectations
- keep outputs inspectable and artifact-backed
- avoid turning this into cost or budget policy work

Likely affected areas:

- `src/swallow/execution_fit.py`
- `src/swallow/compatibility.py`
- `src/swallow/models.py`
- `src/swallow/harness.py`
- `tests/test_cli.py`

Validation:

- success, warning, and failure cases are testable
- family-aware fit status is visible in persisted outputs
- policy checks do not break the current accepted local path

Non-goals:

- full API runtime support
- provider pricing logic
- quota systems

### P7-06 Inspection And Closeout Tightening

Goal:
Close the phase by aligning operator inspection and producing a clear stop/go judgment.

Scope:

- align CLI and artifact inspection with execution-site and ownership semantics
- align status documents and references
- write a Phase 7 closeout note

Likely affected areas:

- `src/swallow/cli.py`
- `src/swallow/store.py`
- `src/swallow/harness.py`
- `tests/test_cli.py`
- `current_state.md`

Validation:

- execution-site and ownership state is easy to inspect
- current-state and planning-entry documents agree on the resulting checkpoint
- the closeout note gives a clear stop/go boundary

Non-goals:

- starting the next phase implicitly

## Deferred Beyond This Breakdown

Keep these outside the active Phase 7 task list unless a concrete implementation need appears:

- real remote transport
- hosted job queues
- worker fleet management
- multi-tenant execution control
- broad provider-marketplace expansion
- full API executor runtime implementation
- large workbench UI expansion

## Planning Judgment

Phase 7 should start from execution-site boundary tightening rather than from remote-platform breadth.

If later planning changes the primary track, this breakdown should be updated rather than half-followed.

## Closeout Judgment

The planned Phase 7 baseline is complete.

Do not continue Phase 7 by default through open-ended execution-topology expansion.

Use `docs/phase7_closeout_note.md` as the decision reference before starting follow-up work.
