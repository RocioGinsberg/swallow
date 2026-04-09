# Post-Phase-5 Retrieval And Memory Next Kickoff Note

This note defines the next planning slice after the completed post-Phase-5 executor-family and external-input baseline.

It does not change any accepted closeout judgment. Phase 5 remains complete, and the post-Phase-5 executor/external-input slice remains complete enough to stop by default.

## Why This Slice Exists

The repository now has:

- a stable local-first task loop
- explicit route, topology, dispatch, handoff, and execution-fit records
- a retrieval baseline with grounding, rerank, memory reuse, and inspection artifacts
- explicit task semantics for imported planning
- staged knowledge objects for imported external knowledge
- a small promotion and verification policy for imported knowledge

What is still missing is a clearer system path from:

- imported knowledge records
- verified knowledge objects
- artifact-backed evidence

toward retrieval-facing reuse that remains explicit, traceable, and resistant to knowledge-base pollution.

Without this slice, the system risks stopping at "knowledge objects are recorded" without answering:

- which knowledge objects should be reusable by retrieval
- how staged knowledge enters later task context
- how verified knowledge differs from canonical knowledge in practice
- how task-linked knowledge and reusable knowledge should remain separate

## What Problem It Solves

This slice is intended to improve:

- retrieval-facing reuse of staged knowledge objects
- memory semantics around imported and verified knowledge
- distinction between task-local records and reusable knowledge-layer records
- evidence-preserving reuse without silently promoting every imported statement

The goal is not to build a general knowledge platform. The goal is to make the current staged external-input baseline materially useful to later retrieval and task execution.

## Primary Track

- `Retrieval / Memory`

## Secondary Tracks

- `Evaluation / Policy`
- `Workbench / UX`
- `Execution Topology`

## Scope

This slice should stay focused on:

- retrieval-facing reuse rules for staged knowledge objects
- explicit distinction between task-linked knowledge and reusable retrieval knowledge
- artifact-backed and source-backed reuse boundaries
- promotion-aware retrieval policy
- compact operator inspection for reused knowledge records
- persistence semantics for reusable knowledge snapshots or indexes

## Non-Goals

This slice is not for:

- remote execution
- API executor runtime implementation
- broad new source adapters
- generic chat-memory products
- full hosted knowledge infrastructure
- automatic canonicalization of all imported knowledge

## Key Design Principles

- Reuse should be explicit, not implied by the mere existence of a knowledge object.
- Verified knowledge should not automatically mean canonical knowledge.
- Task-linked knowledge and reusable retrieval knowledge should stay distinguishable.
- Reuse should preserve evidence linkage and promotion status.
- Retrieval should remain orchestrator-controlled rather than turning into an opaque background memory layer.
- Operator inspection should show why a knowledge record was reusable, not only that it existed.

## Current Direction

The current direction is to treat staged knowledge objects as a bridge between:

- imported external input
- task-scoped artifacts
- later retrieval and memory reuse

That bridge is not fully implemented yet.

The current baseline can already:

- store staged knowledge records
- preserve source and artifact evidence
- evaluate basic promotion and verification policy
- expose those records through CLI inspection

The next slice should make some of those records meaningfully reusable by later runs without collapsing everything into a single long-lived store.

## Proposed Work Items

Possible follow-on slices:

1. retrieval-eligible knowledge declaration baseline
2. task-linked versus reusable knowledge partition baseline
3. verified-knowledge retrieval source baseline
4. reuse-aware retrieval artifact and memory tightening
5. knowledge-reuse policy and verification tightening
6. inspection and closeout tightening

## Stop / Go Framing

This note is a planning entrypoint, not an implementation claim.

Go:

- if the next step should make staged knowledge usable by retrieval in a narrow, inspectable way
- if the next step should strengthen retrieval and memory semantics without changing the accepted local task loop

Stop:

- if the work starts turning into a broad hosted knowledge platform
- if the work starts assuming every imported knowledge object belongs in long-term canonical memory
- if the work drifts into remote execution, API executor runtime work, or broad UI redesign
