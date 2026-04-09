# Phase 10 Kickoff Note

This note defines the next planned phase after the completed Phase 9 Operator Control Workbench baseline.

It does not reopen any earlier completed closeout judgment:

- Phase 4 remains complete
- Phase 5 remains complete
- Phase 6 remains complete
- Phase 7 remains complete
- Phase 8 remains complete
- Phase 9 remains complete
- the post-Phase-2 retrieval baseline remains complete
- the post-Phase-5 executor / external-input slice remains complete
- the post-Phase-5 retrieval / memory-next slice remains complete

## Phase Name

Phase 10: Resume And Recovery Loop

## Why This Phase Exists

The repository now has:

- a stable CLI-first task loop
- explicit execution-site, handoff, ownership, and execution-control policy records
- explicit queue, control, attempt-history, retry, and rerun operator entrypoints

What is still missing is a tighter recovery loop.

The system now makes task state and operator control much easier to inspect, but the actual recovery path is still too manual when an operator needs to decide among:

- resume
- retry
- rerun
- review before resuming

Phase 10 should improve the `Core Loop` around interruption, checkpoint, and resume semantics without turning the system into a workflow engine or a remote scheduler.

## What Problem It Solves

Phase 10 is intended to move the system from:

- strong task truth
- strong operator inspection
- explicit retry and rerun controls

toward:

- clearer checkpoint and resume artifacts
- a narrower resume entrypoint that follows persisted truth
- better separation between resume, retry, and rerun semantics
- less operator stitching after interrupted or partially reviewed runs

## Primary Track

- `Core Loop`

## Secondary Tracks

- `Workbench / UX`
- `Evaluation / Policy`

## Scope

Phase 10 should stay focused on:

- explicit checkpoint or recovery snapshots derived from current persisted task truth
- a local-first resume path that does not bypass the accepted run lifecycle
- tighter operator guidance around resume versus retry versus rerun
- interruption and checkpoint semantics that remain inspectable in state, events, and artifacts
- closeout-time synchronization of status-entry documentation
- a short phase-local commit summary note that is easy to reuse when creating Git commits manually

## Non-Goals

Phase 10 is not for:

- distributed workflow orchestration
- remote recovery coordinators
- automatic background resume loops
- broad multi-step planning engines
- hidden recovery state outside persisted artifacts

## Key Design Principles

- Resume should follow persisted task truth rather than inventing parallel control state.
- Resume, retry, and rerun should remain meaningfully different operator choices.
- Recovery artifacts should stay compact, explicit, and reviewable.
- Phase closeout should always synchronize user-facing and agent-facing status documents.
- Phase closeout should leave a short commit-summary artifact that can be reused when committing the phase manually.

## Current Direction

The current direction is to deepen the `Core Loop` by making interruption and recovery:

- easier to understand from the latest task state
- easier to act on from the local workbench
- more consistent with handoff and execution-control policy truth
- easier to summarize at the end of a phase without re-reading the whole repository history

without drifting into hosted orchestration or broad workflow-platform work.

## Proposed Work Items

Possible Phase 10 slices:

1. checkpoint snapshot baseline
2. resume entrypoint baseline
3. resume versus retry versus rerun boundary tightening
4. interruption recovery semantics baseline
5. operator-facing resume/help alignment
6. closeout, status sync, and commit-summary note

## Stop / Go Framing

This note is a planning entrypoint, not an implementation claim.

Go:

- if the next step should improve interruption and recovery handling inside the accepted local task loop
- if the next step should reduce operator stitching between inspect, review, control, retry, and rerun flows
- if the phase closeout is expected to leave both synchronized status documents and a short commit-summary artifact

Stop:

- if the work starts drifting into background orchestration or distributed scheduling
- if the work starts adding implicit automation that bypasses persisted run truth
- if the work starts broadening into generic workbench polish without a recovery-loop reason
