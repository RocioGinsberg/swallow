# Phase 4 Kickoff Note

Status:

- planning baseline created on 2026-04-08
- track reference: `docs/system_tracks.md`
- prior closeout references:
  - `docs/phase3_closeout_note.md`
  - `docs/post_phase2_retrieval_closeout_note.md`

This note defines the smallest useful next slice after the completed Phase 3 execution-topology baseline.

Phase 4 should advance the `Workbench / UX` track.

The goal is not to build a full desktop UI or hosted operator console. The goal is to turn the current CLI-plus-artifacts surface into a more coherent local workbench for browsing tasks, reviewing run state, and resuming work without manually reconstructing context from many files.

## Goal

Establish a minimal workbench baseline that can:

- preserve the accepted local task loop and all current artifact semantics
- make task review and inspection faster through CLI-level aggregation
- make recent attempts, key artifacts, and current next actions easier to understand
- prepare the system for later TUI or UI work without requiring one now

## Scope

Phase 4 should focus on:

- task-list and task-summary views across `.swl/tasks`
- a compact per-task overview that aggregates:
  - lifecycle state
  - latest attempt identity
  - route and topology summary
  - validation / compatibility / execution-fit status
  - retrieval / grounding / memory availability
  - next-operator guidance
- tighter artifact index presentation so operators can find the right record quickly
- CLI review flows that reduce the need to inspect raw JSON or browse task folders manually

Phase 4 should not focus on:

- desktop UI frameworks
- web dashboards
- remote workbench infrastructure
- execution-topology expansion
- broad new retrieval source breadth
- capability marketplaces

## Track Alignment

Primary track:

- `Workbench / UX`

Secondary tracks affected:

- `Core Loop`
- `Execution Topology`
- `Retrieval / Memory`

Phase 4 should preserve the current repository balance:

- the local CLI remains the operator surface
- artifacts remain the source of truth for task inspection
- retrieval, routing, validation, and execution-topology outputs stay separate and inspectable
- no layer should be collapsed into a generic dashboard abstraction too early

## Repository Terms

In this repository, Phase 4 should improve how existing system truth is surfaced rather than changing where truth lives:

- the **orchestrator** should still own task flow and persisted task state
- the **harness runtime** should still produce task-scoped artifacts
- **state / memory / artifacts** should remain the primary review substrate
- the **CLI** should become a stronger workbench entrypoint by aggregating those outputs
- **capabilities** and **provider routing** should remain visible in review surfaces, not hidden behind generic summaries

## Minimum Useful Outcome

The minimum useful Phase 4 outcome is:

- one task-list view that helps an operator find and sort current tasks
- one task-overview view that summarizes the latest meaningful state of a task
- one tighter artifact index path that points an operator to the right artifacts without guesswork
- tests proving these views remain truthful across multi-attempt runs

If Phase 4 adds more commands but still requires manual reconstruction of task state from raw files, it is too early.

## Affected Areas

Likely primary modules:

- `src/swallow/cli.py`
- `src/swallow/store.py`
- `src/swallow/orchestrator.py`
- `src/swallow/models.py`
- `tests/test_cli.py`

Likely new modules:

- task-view helpers
- artifact-index or summary-format helpers

Likely documentation updates:

- `README.md`
- `README.zh-CN.md`
- `current_state.md`

## First Slice

Recommended first slice: `P4-01 Task List And Summary Baseline`

Goal:
Introduce the smallest operator-facing task browsing path that makes the local CLI feel like a workbench rather than only a command launcher.

Scope:

- add a task list command that shows stable summaries for tasks under `.swl/tasks`
- display enough state to decide which task to inspect next
- keep output compact and deterministic

Completion signal:
An operator can answer:

- what tasks exist
- which tasks are active, completed, or failed
- which task was updated most recently
- which task likely needs attention next

## Implementation Steps

1. Add a small task-view layer that reads persisted task state and artifact paths without changing artifact truth.
2. Introduce one list-style CLI entrypoint and one per-task overview entrypoint.
3. Tighten artifact index presentation so summaries and overview outputs point to the most useful records first.
4. Add tests for multiple tasks, repeated attempts, and mixed terminal states.
5. Update README and current-state references once the first slice is accepted.

## Validation

Each Phase 4 slice should include:

- CLI tests for operator-facing output shape
- at least one multi-task fixture or temporary-task scenario
- explicit checks that artifact and state truth remain unchanged
- `py_compile` and `unittest` coverage for the affected modules

## Deferred Items / Non-Goals

Explicitly defer these until a later Phase 4 slice or beyond:

- desktop GUI or web UI work
- remote operator consoles
- advanced search or full-text artifact dashboards
- new backend/provider expansion
- deeper execution-topology breadth
- broad capability-system redesign

## Decision Rule

When choosing a Phase 4 task, prefer the smallest step that makes operator review, task browsing, and handoff inspection easier without relocating system truth out of artifacts and task state.

If a change mostly adds UI surface area, dashboard language, or broad infrastructure without making local task review more truthful or easier, it is probably too early.
