# Phase 3 Kickoff Note

Status:

- planning baseline created on 2026-04-08
- track reference: `docs/system_tracks.md`
- closeout reference: `docs/phase3_closeout_note.md`

This note defines the smallest useful Phase 3 starting point after the completed Phase 2 baseline and the completed post-Phase-2 retrieval baseline.

Phase 3 should advance the `Execution Topology` track.

The goal is not to build hosted infrastructure or a worker fleet. The goal is to move from "remote-ready metadata exists" to "execution location, handoff shape, and run ownership have a real system boundary."

## Goal

Establish a minimal execution-topology baseline that can:

- keep the current local task loop as the default working path
- make execution location a real runtime boundary instead of only route metadata
- preserve the current state, event, and artifact semantics while adding explicit execution-attempt and handoff records
- prepare the system for later local-versus-remote execution without requiring a full remote platform now

## Scope

Phase 3 should focus on:

- a narrow execution-topology model that distinguishes:
  - task intent
  - route selection
  - execution site
  - dispatch or handoff status
  - execution attempt identity
- explicit persisted records for execution dispatch and handoff decisions
- lifecycle semantics that can represent:
  - local execution
  - prepared-but-not-yet-executed handoff
  - resumable execution attempts
- CLI and artifact paths that let an operator inspect where a run was supposed to execute and what happened at the dispatch boundary

Phase 3 should not focus on:

- distributed worker clusters
- hosted job queues
- multi-tenant infrastructure
- billing or cost-management systems
- broad provider expansion
- a full desktop workbench

## Track Alignment

Primary track:

- `Execution Topology`

Secondary tracks affected:

- `Core Loop`
- `Workbench / UX`
- `Evaluation / Policy`

Phase 3 should not displace the current repository balance:

- retrieval remains a separate system layer
- provider routing remains narrower than orchestration
- artifacts remain inspectable and task-scoped
- the local workbench remains the main operator surface

## Repository Terms

In this repository, Phase 3 should extend the current architecture rather than collapse layers together:

- the **orchestrator** should still decide task flow and when execution should happen
- the **provider router** should still decide route fit and capability fit
- the **harness runtime** should now own a clearer dispatch and execution-attempt boundary
- **state / memory / artifacts** should preserve execution-site and handoff truth in a reusable form
- **capabilities** may describe execution constraints, but should not absorb execution history or attempt tracking

## Minimum Useful Outcome

The minimum useful Phase 3 outcome is:

- one explicit execution-topology model beyond route metadata alone
- one persisted execution-dispatch or handoff record per run attempt
- one readable artifact explaining execution-site intent and dispatch outcome
- one lifecycle path that can represent "prepared for another execution site" without pretending the run already executed there
- tests proving the accepted local path still works and the new topology records stay truthful

If Phase 3 adds remote language but still cannot truthfully represent handoff, attempt ownership, or dispatch outcome, then it is too early.

## Affected Areas

Likely primary modules:

- `src/swallow/orchestrator.py`
- `src/swallow/harness.py`
- `src/swallow/router.py`
- `src/swallow/models.py`
- `src/swallow/store.py`
- `src/swallow/paths.py`
- `src/swallow/cli.py`
- `tests/test_cli.py`

Likely new modules:

- execution-topology helpers
- dispatch or handoff record helpers

Likely documentation updates:

- `README.md`
- `README.zh-CN.md`
- `current_state.md`

## First Slice

Recommended first slice: `P3-01 Execution Topology Contract Baseline`

Goal:
Introduce the smallest explicit model that separates:

- selected route
- selected execution site
- dispatch state
- execution attempt record

Scope:

- add an execution-topology record shape
- persist it into state, events, and dedicated artifacts
- keep all current built-ins local by default
- allow the system to represent a future handoff state without pretending remote execution exists already

Completion signal:
The code can explain:

- where the run was intended to execute
- whether it was dispatched locally or held for handoff
- which attempt record owns the execution
- how the operator should resume or inspect the run

## Implementation Steps

1. Add a topology model that distinguishes route provenance from execution-attempt provenance.
2. Introduce a dispatch or handoff record that can be written before execution begins.
3. Thread topology records through orchestrator and harness without moving retrieval or routing logic into the topology layer.
4. Persist execution-topology outputs into task state, run-start events, and dedicated artifacts.
5. Add tests for local dispatch, deferred handoff representation, and truthful lifecycle behavior.

## Validation

Each Phase 3 slice should include:

- unit tests for execution-topology and dispatch-record behavior
- at least one end-to-end CLI run that persists execution-topology outputs
- explicit checks that current semantics remain intact for:
  - `state.json`
  - `events.jsonl`
  - `summary.md`
  - `resume_note.md`
  - `memory.json`
  - route and compatibility artifacts

## Deferred Items / Non-Goals

Explicitly defer these until a later Phase 3 slice or beyond:

- real remote worker execution
- distributed scheduling
- background daemon infrastructure
- hosted service management
- multi-user coordination
- broad backend or model expansion
- UI-heavy workbench implementation

## Decision Rule

When choosing a Phase 3 task, prefer the smallest step that makes execution location, dispatch, and ownership more truthful without hiding behavior behind infrastructure abstractions.

If a change mostly adds remote terminology or backend breadth but does not improve execution-topology truthfulness, handoff clarity, or attempt traceability, it is probably too early.

## Closeout

The kickoff intent in this note has now been satisfied by the completed `P3-01` through `P3-06` baseline.

This note should remain as the Phase 3 starting rationale.
Use `docs/phase3_closeout_note.md` for the current stop/go decision.
