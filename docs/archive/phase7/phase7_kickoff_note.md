# Phase 7 Kickoff Note

This note defines the next planned phase after the completed Phase 6 Retrieval / Memory Operationalization baseline.

It does not reopen any earlier completed closeout judgment:

- Phase 3 remains complete enough to stop open-ended execution-topology expansion by default
- Phase 4 remains complete
- Phase 5 remains complete
- the post-Phase-5 executor / external-input slice remains complete
- the post-Phase-5 retrieval / memory-next slice remains complete
- Phase 6 remains complete

## Phase Name

Phase 7: Execution-Site Boundary

## Why This Phase Exists

The repository now has:

- a stable local-first task loop
- explicit route, topology, dispatch, handoff, and execution-fit records
- explicit executor-family declaration in planning and persistence surfaces
- reusable retrieval and memory baselines that should not be reopened by default

What is still missing is a more real execution-site boundary.

The current system can describe execution intent, route fit, topology, dispatch, and handoff in inspectable records. It still executes primarily as a local inline path. That means the repository can explain execution shape better than it can yet enforce execution-site ownership, detached execution boundaries, or family-aware execution contracts.

## What Problem It Solves

Phase 7 is intended to move the `Execution Topology` track from:

- explicit topology truth

toward:

- explicit execution-site contract
- clearer attempt ownership and ownership transfer semantics
- handoff records that act more like execution contracts than narrative notes
- a local-detached execution baseline that proves execution-site separation without requiring remote infrastructure
- family-aware execution-fit rules that distinguish API executor versus CLI executor expectations more operationally

The goal is not to build a remote worker platform. The goal is to make execution-site boundaries real enough that later local-versus-remote expansion has a truthful system seam.

## Primary Track

- `Execution Topology`

## Secondary Tracks

- `Evaluation / Policy`
- `Workbench / UX`
- `Core Loop`

## Scope

Phase 7 should stay focused on:

- execution-site contract records that distinguish inline, detached, and remote-candidate execution intent
- attempt ownership fields and ownership-transfer semantics
- handoff contract tightening around required inputs, expected outputs, and next executor/operator action
- a narrow local-detached execution baseline that remains single-machine and artifact-backed
- family-aware execution-fit checks for API-executor versus CLI-executor expectations
- operator-facing inspection for execution-site, ownership, and handoff-contract state

## Non-Goals

Phase 7 is not for:

- hosted queues or schedulers
- distributed worker fleets
- multi-tenant execution infrastructure
- broad provider-marketplace work
- full API executor runtime implementation
- broad workbench UI redesign

## Key Design Principles

- Execution site should become an enforceable system boundary, not only descriptive metadata.
- Attempt ownership should stay explicit and inspectable.
- Handoff should preserve contract truth, not only summarize operator intent.
- Detached execution should be proven locally before remote transport is introduced.
- Executor family should influence execution-fit policy without collapsing routing and topology into the same concern.
- Current local task-loop, artifact, and event semantics should remain truthful and reusable.

## Current Direction

The current direction is to deepen the execution-topology track by making execution-site and attempt ownership:

- easier to declare
- easier to inspect
- more enforceable at dispatch and handoff boundaries
- more compatible with later local-detached and remote-ready execution shapes

without turning the repository into a hosted execution platform.

## Proposed Work Items

Possible Phase 7 slices:

1. execution-site contract baseline
2. attempt ownership baseline
3. handoff-contract tightening
4. local-detached execution baseline
5. family-aware execution-fit policy tightening
6. inspection and closeout tightening

## Stop / Go Framing

This note is a planning entrypoint, not an implementation claim.

Go:

- if the next step should make execution-site boundaries more real without reopening broad infrastructure work
- if the next step should stress execution ownership, handoff truth, and detached execution semantics while preserving the accepted local task loop

Stop:

- if the work starts drifting into hosted scheduling or worker-fleet work
- if the work starts pretending API executor runtime support is already implemented
- if the work broadens into UI-platform or provider-marketplace work without a narrower execution-topology boundary
