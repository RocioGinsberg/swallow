# Phase 6 Kickoff Note

This note defines the next planned phase after the completed post-Phase-5 retrieval / memory-next slice.

It does not change any accepted closeout judgment:

- Phase 5 remains complete
- the post-Phase-5 executor / external-input slice remains complete
- the post-Phase-5 retrieval / memory-next slice remains complete

## Phase Name

Phase 6: Retrieval / Memory Operationalization

## Why This Phase Exists

The repository now has:

- a stable local task loop
- explicit route, topology, dispatch, handoff, and execution-fit records
- a staged external-input baseline with task semantics and knowledge objects
- a reusable-knowledge bridge into retrieval with explicit evidence and policy boundaries

What is still missing is a more operational retrieval / memory layer.

The current system can declare reusable knowledge, gate it, retrieve it explicitly, and preserve evidence. It cannot yet treat that knowledge as a more sustained retrieval substrate with clear indexing, refresh, verification, and reuse-management semantics.

## What Problem It Solves

Phase 6 is intended to move the retrieval / memory track from:

- explicit reusable-knowledge baseline

toward:

- more durable retrieval-layer organization
- clearer indexing and refresh semantics
- better cross-task reuse boundaries
- stronger verification and canonicalization boundaries
- more operational inspection and evaluation

The goal is not to build a generic hosted knowledge platform. The goal is to make the repository’s retrieval and memory layer more sustainable as the system grows.

## Primary Track

- `Retrieval / Memory`

## Secondary Tracks

- `Evaluation / Policy`
- `Workbench / UX`
- `Capabilities`

## Scope

Phase 6 should stay focused on:

- reusable-knowledge indexing or index-like records
- refresh and invalidation semantics for reusable knowledge
- stronger separation between verified reusable knowledge and canonical knowledge
- retrieval operational artifacts and operator inspection
- evaluation fixtures for reusable knowledge behavior
- cross-task retrieval reuse that remains traceable and policy-bounded

## Non-Goals

Phase 6 is not for:

- broad remote execution work
- API executor runtime implementation
- generic chat-memory products
- fully automatic canonical knowledge management
- large hosted search infrastructure
- broad new UI surfaces

## Key Design Principles

- Reuse should stay explicit and artifact-backed.
- Indexing should remain inspectable rather than hidden behind opaque background services.
- Verified knowledge should remain distinct from canonical knowledge.
- Retrieval reuse should preserve task linkage, evidence linkage, and promotion state.
- Operationalization should improve sustainability without weakening orchestrator control over retrieval.
- New retrieval surfaces should be introduced through narrow, reviewable slices rather than broad platform claims.

## Current Direction

The current direction is to deepen the retrieval / memory track by making reusable knowledge:

- easier to organize
- easier to refresh or invalidate
- easier to inspect across tasks
- easier to evaluate for correctness and drift

without collapsing the system into a generic knowledge base product.

## Proposed Work Items

Possible Phase 6 slices:

1. reusable-knowledge index baseline
2. refresh and invalidation semantics baseline
3. canonicalization-boundary baseline
4. cross-task retrieval reuse baseline
5. reusable-knowledge evaluation tightening
6. inspection and closeout tightening

## Stop / Go Framing

This note is a planning entrypoint, not an implementation claim.

Go:

- if the next step should deepen retrieval / memory sustainability
- if the next step should make reusable knowledge operational without changing the accepted local task loop

Stop:

- if the work starts turning into a general hosted knowledge platform
- if the work starts assuming all verified knowledge should become canonical
- if the work drifts into remote execution, API executor runtime work, or broad UI redesign
