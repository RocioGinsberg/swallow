# Phase 9 Kickoff Note

This note defines the next planned phase after the completed Phase 8 Execution Control Policy baseline.

It does not reopen any earlier completed closeout judgment:

- Phase 4 remains complete
- Phase 5 remains complete
- Phase 6 remains complete
- Phase 7 remains complete
- Phase 8 remains complete
- the post-Phase-2 retrieval baseline remains complete
- the post-Phase-5 executor / external-input slice remains complete
- the post-Phase-5 retrieval / memory-next slice remains complete

## Phase Name

Phase 9: Operator Control Workbench

## Why This Phase Exists

The repository now has:

- a stable CLI-first task loop
- explicit route, topology, execution-site, dispatch, handoff, and attempt-ownership records
- explicit retry, stop, escalation, and execution-budget policy records
- usable list, inspect, review, artifacts, and policy inspection commands

What is still missing is a tighter operator-control surface.

The system preserves task truth well, but operators still need to stitch together:

- which tasks need action now
- whether a task is ready for retry or rerun
- how repeated attempts differ
- which control path should be used next

Phase 9 should improve that workbench layer without inventing a new control plane.

## What Problem It Solves

Phase 9 is intended to move the `Workbench / UX` track from:

- task browsing
- grouped artifact inspection
- review-oriented task summaries

toward:

- action-focused operator queue views
- clearer per-task control snapshots
- attempt-history and comparison entrypoints
- tighter rerun and retry ergonomics around existing lifecycle truth

The goal is not to build a desktop app or a hosted dashboard. The goal is to make the current local workbench more operationally useful now that execution-control truth exists.

## Primary Track

- `Workbench / UX`

## Secondary Tracks

- `Core Loop`
- `Evaluation / Policy`

## Scope

Phase 9 should stay focused on:

- CLI entrypoints that help operators decide what to do next
- queue or attention views driven by current state, handoff, and policy artifacts
- concise control snapshots that summarize retry, stop, rerun, and review readiness
- attempt-history visibility for tasks with repeated runs
- small rerun or retry-oriented ergonomics that preserve current state and artifact truth
- operator-readable help and documentation alignment for those entrypoints

## Non-Goals

Phase 9 is not for:

- desktop UI frameworks
- web dashboards
- remote task browsing
- automatic retry execution loops
- remote schedulers or control planes
- hidden state transitions that bypass artifacts

## Key Design Principles

- Workbench commands should expose existing task truth rather than inventing parallel truth.
- Operator-control output should stay concise and decision-oriented.
- Repeated attempts should become easier to inspect without flattening run history.
- Rerun and retry guidance should stay explicit before more automation is added.
- Current artifact-backed lifecycle semantics should remain canonical.

## Current Direction

The current direction is to deepen `Workbench / UX` by making operator control:

- easier to triage across many tasks
- easier to reason about after multiple attempts
- easier to connect to retry, stop, and review policy state
- easier to use without opening raw task directories or raw JSON first

without drifting into UI-platform or hosted-control-plane work.

## Proposed Work Items

Possible Phase 9 slices:

1. operator action queue baseline
2. task control snapshot baseline
3. attempt history and comparison baseline
4. rerun and retry entrypoint tightening
5. workbench command and help alignment
6. closeout and status alignment

## Stop / Go Framing

This note is a planning entrypoint, not an implementation claim.

Go:

- if the next step should make the CLI workbench more actionable without changing where truth lives
- if the next step should reduce operator stitching across list, inspect, review, and policy flows

Stop:

- if the work starts drifting into desktop UI or hosted dashboard breadth
- if the work starts adding automatic control loops instead of operator-facing control entrypoints
- if the work starts hiding lifecycle state behind convenience commands
