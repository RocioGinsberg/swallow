# Phase 1 Kickoff Plan

This document turns the current Phase 1 direction into a small executable plan.

Phase 1 should improve the quality and extensibility of the accepted Phase 0 loop without expanding the system into a broad platform prematurely.

For the concrete task sequence, use `docs/phase1_task_breakdown.md` as the execution-facing companion document.

## Goal

Establish a stronger working baseline beyond the Phase 0 MVP by elevating retrieval into an orchestrator-controlled system-level knowledge layer, refining the harness runtime boundary, proving executor replaceability, and introducing the first explicit validation and capability-shaping mechanisms.

## Scope

Phase 1 should focus on:

- system-level retrieval baseline improvements for repository files and markdown notes
- clearer harness runtime boundaries between retrieval, execution, validation, and artifact writing
- a second executor path to prove executor replaceability
- first-class validators and basic execution policies
- tighter artifact and memory reuse semantics

Phase 1 should not focus on:

- broad provider routing
- full desktop UI
- large source-ingestion expansion
- large plugin or marketplace surfaces
- complex multi-agent runtime behavior

## Affected Areas

Likely primary modules:

- `src/swallow/retrieval.py`
- `src/swallow/harness.py`
- `src/swallow/orchestrator.py`
- `src/swallow/executor.py`
- `src/swallow/models.py`
- `src/swallow/store.py`
- `tests/test_cli.py`

Likely new modules:

- retrieval chunking, ranking, and metadata helpers
- executor selection/registration helpers
- validator or policy modules
- artifact indexing or memory helpers

## Milestones

### Milestone 1: System-Level Retrieval Baseline

Goal:
Establish retrieval as a system-level knowledge layer that remains external, traceable, and orchestrator-controlled without expanding beyond repository files and markdown notes.

Target outcomes:

- source-specific chunking instead of relying only on naive file-level previews
- stronger metadata in retrieval results
- retrieval outputs that are citation-ready and artifact-friendly
- more stable ranking for practical task prompts
- cleaner separation between retrieval-layer mechanics and orchestrator retrieval decisions
- a retrieval shape that can later serve session, workspace, task, and historical context without being tied to one executor surface
- tests that cover retrieval behavior by source type

Completion signal:
Retrieval results are easier to inspect, more believable on realistic local tasks, and structured clearly enough to act as a reusable system knowledge layer rather than a one-shot prompt helper.

### Milestone 2: Harness And Executor Boundary Cleanup

Goal:
Make the runtime loop clearer so later additions do not blur orchestrator, harness, executor, and artifact responsibilities.

Target outcomes:

- clearer harness step boundaries for retrieval, execution, validation, and artifact writing
- executor selection shaped as a narrow swappable interface
- no accidental drift into provider-router abstractions
- tests that cover the updated step boundaries

Completion signal:
Adding or changing an executor no longer requires threading special cases through the whole run loop.

### Milestone 3: Validation And Second-Executor Proof

Goal:
Prove that the accepted Phase 0 loop can support quality checks and more than one executor without losing simplicity.

Target outcomes:

- a minimal validator interface or policy layer
- first validator checks around artifact completeness or run-result consistency
- a second executor path with explicit selection semantics
- tests covering executor switching and validator outcomes

Completion signal:
The system can run with at least two executor options and emit a first explicit validation result.

## Task Sequence

Recommended order:

1. Improve retrieval structure and ranking first.
2. Refine harness boundaries around the current run loop.
3. Introduce a narrow executor selection shape and add the second executor.
4. Add validators and minimal execution policies.
5. Tighten artifact indexing and memory reuse only after the above boundaries are stable.

## Validation

Each Phase 1 slice should include:

- unit tests for the new or changed module behavior
- one end-to-end CLI path showing the new behavior in persisted outputs
- explicit checks that retrieval outputs remain traceable, reusable, and suitable for citation or artifact storage
- explicit checks that Phase 0 semantics remain intact for:
  - `state.json`
  - `events.jsonl`
  - `summary.md`
  - `resume_note.md`

Phase 1 should continue to preserve:

- truthful lifecycle status
- truthful phase progression
- append-only event history
- inspectable artifacts

## Deferred Items / Non-Goals

Explicitly defer these until later unless a concrete implementation need appears:

- provider routing layer
- broad backend capability declarations
- full remote execution support
- large plugin and capability marketplace surfaces
- multimodal source ingestion
- complex UI work

## First Suggested Slice

Start with `System-Level Retrieval Baseline`.

Reason:

- it is directly named in the repository’s Phase 1 direction
- it improves practical task quality immediately
- it upgrades retrieval from executor-adjacent behavior into an independent system layer
- it creates better inputs for later executor and validator work
- it does not require premature Phase 2 abstractions
