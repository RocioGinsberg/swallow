# Phase 10 Task Breakdown

This document turns the next resume-and-recovery direction into small executable slices.

It should preserve:

- the accepted local task loop
- the completed Phase 7 execution-site baseline
- the completed Phase 8 execution-control-policy baseline
- the completed Phase 9 operator-control-workbench baseline
- explicit state, event, and artifact truthfulness

Status:

- planning baseline created on 2026-04-09
- current runtime reference: `current_state.md`
- kickoff reference: `docs/phase10_kickoff_note.md`
- prior closeout references:
  - `docs/phase7_closeout_note.md`
  - `docs/phase8_closeout_note.md`
  - `docs/phase9_closeout_note.md`

## Working Rule

Every slice in this breakdown should preserve:

- truthful lifecycle status
- append-only event history
- inspectable artifacts
- explicit execution-control decisions
- local-first default execution

Every phase closeout in this planning direction should also leave:

- synchronized status-entry documentation
- a short phase-local commit summary note under `docs/`

This breakdown is about tightening the local resume and recovery loop.

It is not about remote orchestration, background schedulers, or broad workflow automation.

## Recommended Order

1. `P10-01` Checkpoint snapshot baseline
2. `P10-02` Resume entrypoint baseline
3. `P10-03` Resume versus retry versus rerun boundary tightening
4. `P10-04` Interruption recovery semantics baseline
5. `P10-05` Resume command and help alignment
6. `P10-06` Closeout, documentation synchronization, and commit-summary note

Current completion state:

- `P10-01` complete
- `P10-02` complete
- `P10-03` complete
- `P10-04` complete
- `P10-05` complete
- `P10-06` complete

## Tasks

### P10-01 Checkpoint Snapshot Baseline

Goal:
Add a compact checkpoint or recovery snapshot that summarizes what is needed to continue a task safely.

Scope:

- derive a narrow checkpoint view from current task state, handoff, and policy truth
- keep the snapshot explicit and artifact-backed
- avoid inventing a second state machine

Likely affected areas:

- `src/swallow/cli.py`
- `src/swallow/store.py`
- `src/swallow/models.py`
- `tests/test_cli.py`

Validation:

- operators can see recovery-relevant truth without opening multiple raw artifacts
- checkpoint output remains stable across completed, failed, and interrupted-style task states

Non-goals:

- workflow graphs
- background checkpoints

### P10-02 Resume Entrypoint Baseline

Goal:
Add a narrow operator-facing resume entrypoint that follows persisted truth.

Scope:

- add a small CLI resume path
- keep resume behavior consistent with accepted run-loop semantics
- require explicit operator intent rather than hidden automation

Likely affected areas:

- `src/swallow/cli.py`
- `src/swallow/orchestrator.py`
- `tests/test_cli.py`

Validation:

- resume uses persisted task truth rather than implicit heuristics alone
- resume does not bypass accepted task-run lifecycle boundaries

Non-goals:

- automatic resume daemons
- remote execution recovery

### P10-03 Resume Versus Retry Versus Rerun Boundary Tightening

Goal:
Make resume, retry, and rerun distinct and operator-readable choices.

Scope:

- tighten control guidance and failure messaging around the three paths
- ensure each path is aligned with persisted policy and handoff truth
- keep semantics compact and inspectable

Likely affected areas:

- `src/swallow/cli.py`
- `src/swallow/harness.py`
- `src/swallow/orchestrator.py`
- `tests/test_cli.py`

Validation:

- operators can tell which path is allowed and why
- command behavior stays aligned with existing retry and stop-policy truth

Non-goals:

- generic workflow branching
- policy redesign unrelated to recovery

### P10-04 Interruption Recovery Semantics Baseline

Goal:
Tighten how interrupted or partially completed runs are classified for later recovery.

Scope:

- make interruption-oriented recovery semantics explicit in artifacts or task summaries
- preserve append-only event history and current lifecycle truth
- avoid pretending that unimplemented remote recovery exists

Likely affected areas:

- `src/swallow/models.py`
- `src/swallow/harness.py`
- `src/swallow/store.py`
- `tests/test_cli.py`

Validation:

- recovery-relevant interruption states are visible without rewriting prior run history
- summary, review, and control flows stay coherent after interrupted-style tasks

Non-goals:

- durable supervisors
- distributed worker recovery

### P10-05 Resume Command And Help Alignment

Goal:
Align command naming, help text, and operator-facing documentation with the tighter recovery loop.

Scope:

- align CLI help around resume, retry, rerun, and checkpoint paths
- update status-entry or README references where needed
- keep recovery entrypoints understandable in a fresh session

Likely affected areas:

- `src/swallow/cli.py`
- `README.md`
- `README.zh-CN.md`
- `current_state.md`
- `tests/test_cli.py`

Validation:

- recovery entrypoints are discoverable without reading implementation code
- help output makes the resume-versus-retry-versus-rerun boundary clearer

Non-goals:

- broad documentation redesign
- non-CLI interfaces

### P10-06 Closeout, Documentation Synchronization, And Commit-Summary Note

Goal:
Close the phase by aligning status documents and leaving a short commit-summary artifact for manual Git submission.

Scope:

- align status-entry documents with the resulting Phase 10 baseline
- write a Phase 10 closeout note
- write `docs/phase10_commit_summary.md` as a short reusable commit-summary note
- ensure planning-entry references point to the right checkpoint

Likely affected areas:

- `docs/phase10_closeout_note.md`
- `docs/phase10_commit_summary.md`
- `current_state.md`
- `AGENTS.md`
- `README.md`
- `README.zh-CN.md`
- `.codex/phases/active.md`
- `.codex/context/current-system.md`
- `.codex/context/current-scope.md`

Validation:

- status documents agree on the resulting checkpoint
- closeout note gives a clear stop/go boundary
- the commit-summary note is short, current, and usable without re-reading all diffs

Non-goals:

- starting Phase 11 implicitly
- generating Git commits automatically

## Deferred Beyond This Breakdown

Keep these outside the active Phase 10 task list unless a concrete implementation need appears:

- remote resume orchestration
- background recovery loops
- broad workflow-state machines
- multi-operator recovery coordination
- hosted checkpoint dashboards

## Planning Judgment

Phase 10 should start from local interruption and recovery semantics in the accepted task loop rather than from broader orchestration or platform automation.

If later planning changes the primary track, this breakdown should be updated rather than half-followed.
