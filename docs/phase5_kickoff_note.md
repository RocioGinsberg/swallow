# Phase 5 Kickoff Note

Status:

- planning baseline created on 2026-04-08
- track reference: `docs/system_tracks.md`
- prior closeout references:
  - `docs/phase4_closeout_note.md`
  - `docs/phase3_closeout_note.md`
  - `docs/post_phase2_retrieval_closeout_note.md`

This note defines the smallest useful next slice after the completed Phase 4 local workbench baseline.

Phase 5 should advance the `Capabilities` track.

The goal is not to build a marketplace, plugin ecosystem, or broad automation layer. The goal is to turn the repository’s existing tools, skills, profiles, workflows, and validators from “present in the repo” into a small, explicit, composable capability assembly baseline.

## Goal

Establish a minimal capability-system baseline that can:

- preserve the accepted local task loop and current artifact semantics
- make capability selection explicit at the task level
- record what capability pieces were assembled for a run
- prepare the system for later capability composition without requiring a large registry platform now

## Scope

Phase 5 should focus on:

- a small capability manifest or specification shape
- task-level capability selection or reference
- persisted capability-assembly records for inspection
- lightweight validation that referenced capability pieces exist and are compatible with the local baseline
- CLI inspection paths that show what was assembled for a task

Phase 5 should not focus on:

- plugin marketplaces
- remote capability registries
- capability auto-discovery across many sources
- UI-based capability management
- large workflow DSLs

## Track Alignment

Primary track:

- `Capabilities`

Secondary tracks affected:

- `Core Loop`
- `Evaluation / Policy`
- `Workbench / UX`

Phase 5 should preserve the current repository balance:

- the orchestrator still owns task flow
- the harness runtime still owns execution and artifact production
- state and artifacts remain the source of truth for inspection
- the capability layer should describe composition, not absorb task history

## Repository Terms

In this repository, Phase 5 should improve how reusable capability pieces are declared and assembled:

- the **orchestrator** may accept capability references at task creation or run time
- the **harness runtime** should receive an explicit assembled capability view rather than implicit ambient assumptions
- **state / memory / artifacts** should show which capability pieces were active for a task
- the **CLI** should expose lightweight inspection of capability assembly results
- **validators** should remain explicit capability pieces, not hidden side effects

## Minimum Useful Outcome

The minimum useful Phase 5 outcome is:

- one explicit capability manifest shape
- one persisted capability-assembly record per task or run
- one task-level way to select a small capability set
- one CLI path to inspect the assembled capability view
- tests proving invalid capability references fail clearly

If Phase 5 adds new capability terminology but still cannot tell an operator what capability set a task actually used, it is too early.

## Affected Areas

Likely primary modules:

- `src/swallow/models.py`
- `src/swallow/orchestrator.py`
- `src/swallow/cli.py`
- `src/swallow/store.py`
- `tests/test_cli.py`

Likely new modules:

- `src/swallow/capabilities.py`

Likely documentation updates:

- `README.md`
- `README.zh-CN.md`
- `current_state.md`

## First Slice

Recommended first slice: `P5-01 Capability Manifest Baseline`

Goal:
Introduce the smallest explicit manifest shape that can describe a task’s capability selection without changing current executor, retrieval, or artifact truth.

Scope:

- define a compact capability manifest or selection schema
- allow a task to persist that schema
- keep the initial capability pieces intentionally small and local-first

Completion signal:
The code can answer:

- what capability set a task asked for
- which capability pieces were recognized
- whether the requested set is valid for the current local baseline

## Implementation Steps

1. Define a small capability specification layer with explicit local-first pieces.
2. Add task-level capability selection and persistence.
3. Add a persisted capability-assembly record for later inspection.
4. Add CLI inspection and validation coverage.
5. Update README and current-state references once the first slice is accepted.

## Validation

Each Phase 5 slice should include:

- CLI tests for capability selection and inspection
- validation coverage for invalid capability references
- explicit checks that current lifecycle and artifact semantics remain intact
- `py_compile` and `unittest` coverage for the affected modules

## Deferred Items / Non-Goals

Explicitly defer these until a later Phase 5 slice or beyond:

- remote capability registries
- plugin marketplaces
- broad package version resolution
- UI capability browsers
- highly dynamic capability composition rules

## Decision Rule

When choosing a Phase 5 task, prefer the smallest step that makes capability declaration and assembly more explicit without turning the repository into a plugin platform.

If a change mostly adds generality, discovery, or packaging surface without making task-level capability assembly more truthful or inspectable, it is probably too early.
