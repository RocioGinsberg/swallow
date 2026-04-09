# Phase 9 Task Breakdown

This document turns the next operator-control-workbench direction into small executable slices.

It should preserve:

- the accepted local task loop
- the completed Phase 4 workbench baseline
- the completed Phase 7 execution-site baseline
- the completed Phase 8 execution-control-policy baseline
- explicit state, event, and artifact truthfulness

Status:

- planning baseline created on 2026-04-09
- current runtime reference: `current_state.md`
- kickoff reference: `docs/phase9_kickoff_note.md`
- prior closeout references:
  - `docs/phase4_closeout_note.md`
  - `docs/phase7_closeout_note.md`
  - `docs/phase8_closeout_note.md`

## Working Rule

Every slice in this breakdown should preserve:

- truthful lifecycle status
- append-only event history
- inspectable artifacts
- explicit execution-control decisions
- local-first default execution

This breakdown is about operator control in the local workbench.

It is not about desktop UI, hosted dashboards, or automatic control-plane behavior.

## Recommended Order

1. `P9-01` Operator action queue baseline
2. `P9-02` Task control snapshot baseline
3. `P9-03` Attempt history and comparison baseline
4. `P9-04` Rerun and retry entrypoint tightening
5. `P9-05` Workbench command and help alignment
6. `P9-06` Closeout and status alignment

Current completion state:

- `P9-01` complete
- `P9-02` complete
- `P9-03` complete
- `P9-04` complete
- `P9-05` complete
- `P9-06` complete

## Tasks

### P9-01 Operator Action Queue Baseline

Goal:
Add a compact operator queue view that surfaces which tasks currently need action.

Scope:

- define a narrow queue-oriented CLI entrypoint or focused list mode
- summarize action-needed state from current task status, handoff, and stop-policy truth
- keep queue logic explicit and deterministic

Likely affected areas:

- `src/swallow/cli.py`
- `src/swallow/store.py`
- `tests/test_cli.py`

Validation:

- queue output remains stable across mixed task states
- action-needed tasks are easier to identify than with raw list output alone
- queue logic does not invent lifecycle state beyond persisted truth

Non-goals:

- inbox systems
- notifications
- background watchers

### P9-02 Task Control Snapshot Baseline

Goal:
Add a concise per-task control snapshot that summarizes what an operator can do next.

Scope:

- surface retry, stop, rerun, and review readiness in one place
- keep the snapshot tied to current handoff and policy artifacts
- avoid duplicating full inspect or review output

Likely affected areas:

- `src/swallow/cli.py`
- `src/swallow/store.py`
- `tests/test_cli.py`

Validation:

- operators can understand next control options without opening multiple artifacts first
- snapshot output remains truthful after successful, failed, and detached runs

Non-goals:

- replacing inspect, review, or policy commands
- automatic command execution

### P9-03 Attempt History And Comparison Baseline

Goal:
Make repeated attempts easier to inspect by adding compact attempt-history and comparison paths.

Scope:

- expose recent attempt summaries for a task
- add a narrow comparison view for adjacent or selected attempts
- preserve append-only event and artifact history

Likely affected areas:

- `src/swallow/cli.py`
- `src/swallow/store.py`
- `src/swallow/models.py`
- `tests/test_cli.py`

Validation:

- repeated runs remain easier to compare without manual file inspection
- comparison output stays compact and does not flatten historical truth

Non-goals:

- graphical diff views
- cross-task analytics

### P9-04 Rerun And Retry Entrypoint Tightening

Goal:
Tighten the operator-facing entrypoints for rerun and retry decisions around existing control-policy truth.

Scope:

- add small CLI ergonomics for rerun or retry guidance
- keep retry eligibility and stop-policy boundaries explicit
- preserve the existing run loop rather than automating recovery

Likely affected areas:

- `src/swallow/cli.py`
- `src/swallow/orchestrator.py`
- `tests/test_cli.py`

Validation:

- rerun and retry entrypoints remain consistent with policy artifacts
- no hidden lifecycle mutation bypasses the accepted run path

Non-goals:

- automatic retries
- remote retry orchestration

### P9-05 Workbench Command And Help Alignment

Goal:
Align command naming, help text, and operator-facing documentation with the new control-focused workbench surface.

Scope:

- tighten CLI help around queue, control, and attempt-history paths
- align README or status-entry references where needed
- keep command boundaries understandable in a fresh session

Likely affected areas:

- `src/swallow/cli.py`
- `README.md`
- `README.zh-CN.md`
- `current_state.md`
- `tests/test_cli.py`

Validation:

- workbench help output remains coherent
- operator-control entrypoints are discoverable without reading implementation code

Non-goals:

- broad documentation redesign
- non-CLI interfaces

### P9-06 Closeout And Status Alignment

Goal:
Close the phase by aligning status documents and producing a clear stop/go judgment.

Scope:

- align status-entry documents with the resulting workbench baseline
- write a Phase 9 closeout note
- ensure planning-entry references point to the right checkpoint

Likely affected areas:

- `current_state.md`
- `.codex/phases/active.md`
- `.codex/context/current-system.md`
- `.codex/context/current-scope.md`

Validation:

- status documents agree on the resulting checkpoint
- closeout note gives a clear stop/go boundary

Non-goals:

- starting the next phase implicitly

## Deferred Beyond This Breakdown

Keep these outside the active Phase 9 task list unless a concrete implementation need appears:

- desktop or web workbench platforms
- remote queue or scheduler views
- automatic retry controllers
- large history analytics surfaces
- hosted operator coordination

## Planning Judgment

Phase 9 should start from operator control in the local workbench rather than from broader UI-platform or remote-control work.

If later planning changes the primary track, this breakdown should be updated rather than half-followed.
