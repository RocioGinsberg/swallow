# Phase 8 Kickoff Note

This note defines the next planned phase after the completed Phase 7 Execution-Site Boundary baseline.

It does not reopen any earlier completed closeout judgment:

- Phase 3 remains complete
- Phase 4 remains complete
- Phase 5 remains complete
- the post-Phase-5 executor / external-input slice remains complete
- the post-Phase-5 retrieval / memory-next slice remains complete
- Phase 6 remains complete
- Phase 7 remains complete

## Phase Name

Phase 8: Execution Control Policy

## Why This Phase Exists

The repository now has:

- a stable local-first task loop
- explicit route, topology, execution-site, dispatch, handoff, and execution-fit records
- explicit attempt ownership and handoff-contract state
- a narrow local-detached execution baseline
- family-aware execution-fit checks that keep current executor-family support honest

What is still missing is a clearer execution-control policy layer.

The current system can declare execution shape and preserve truthful execution artifacts. It still lacks a more deliberate policy baseline for retry, stop, escalation, operator checkpoint, and detached-execution safety decisions.

## What Problem It Solves

Phase 8 is intended to move the `Evaluation / Policy` track from:

- validator, compatibility, and retrieval-evaluation baselines

toward:

- explicit execution retry policy
- clearer stop and escalation policy
- operator checkpoint policy around failure and detached execution
- narrow execution budget and timeout policy records
- policy inspection that makes execution-control decisions reviewable

The goal is not to build a hosted governance platform. The goal is to make execution control more explicit before the repository broadens execution topology further.

## Primary Track

- `Evaluation / Policy`

## Secondary Tracks

- `Execution Topology`
- `Workbench / UX`
- `Core Loop`

## Scope

Phase 8 should stay focused on:

- retry-policy records and retry-eligibility decisions
- stop versus continue policy at execution boundaries
- operator-checkpoint policy for detached execution and failure recovery
- narrow execution budget or timeout policy visibility
- policy inspection in summaries, review flows, and dedicated artifacts
- lightweight regression coverage for execution-control decisions

## Non-Goals

Phase 8 is not for:

- remote worker transport
- full job scheduling systems
- multi-tenant governance
- billing systems
- broad provider-marketplace policy layers
- full desktop workbench redesign

## Key Design Principles

- Policy should remain explicit, inspectable, and artifact-backed.
- Execution control should not be hidden inside executor-specific behavior.
- Operator checkpoints should be deliberate rather than implied by prose alone.
- Retry policy should be narrow and truthful before it becomes more automatic.
- Detached execution should gain safety policy before it gains infrastructure breadth.
- Existing local task-loop semantics should remain understandable and reusable.

## Current Direction

The current direction is to deepen `Evaluation / Policy` by making execution control:

- easier to inspect
- easier to reason about at failure and retry boundaries
- easier to compare across inline and detached execution
- safer for later topology expansion

without drifting into hosted governance or large control-plane work.

## Proposed Work Items

Possible Phase 8 slices:

1. retry-policy baseline
2. stop and escalation policy baseline
3. detached-execution checkpoint baseline
4. execution budget and timeout policy baseline
5. policy inspection and review tightening
6. closeout and status alignment

## Stop / Go Framing

This note is a planning entrypoint, not an implementation claim.

Go:

- if the next step should make execution-control policy more explicit without broadening infrastructure
- if the next step should improve retry, stop, and checkpoint truthfulness while preserving the accepted local task loop

Stop:

- if the work starts drifting into hosted control planes or distributed scheduling
- if the work starts pretending remote execution policy already exists
- if the work broadens into platform governance without a narrower execution-control boundary
