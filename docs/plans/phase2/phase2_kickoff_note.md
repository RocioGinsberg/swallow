# Phase 2 Kickoff Note

Status:

- kickoff baseline completed on 2026-04-08
- closeout reference: `docs/phase2_closeout_note.md`

This note defines the smallest useful Phase 2 starting point after the Phase 1 baseline.

Phase 2 should introduce a broader provider-routing layer without turning the repository into a premature backend platform.

The goal is not "support everything." The goal is to make backend and provider choices explicit, inspectable, and testable while preserving the accepted local task loop.

## Goal

Establish a minimal provider-router baseline that can:

- describe executor and backend capabilities explicitly
- select between small declared routes without scattering routing logic through the orchestrator
- preserve retrieval, state, event, and artifact semantics from the current Phase 1 loop
- prepare the harness boundary for later remote or SDK-backed runtimes without requiring them yet

## Scope

Phase 2 should focus on:

- a narrow provider-router module with declared route records
- explicit separation between:
  - model
  - runtime backend
  - executor
- route selection policies small enough to inspect locally
- capability declarations for the built-in local backends and executors
- persisted route decisions in task state or events

Phase 2 should not focus on:

- large hosted infrastructure
- distributed worker execution
- broad plugin marketplaces
- many third-party backends at once
- complex multi-agent runtime behavior
- full cost optimization or billing logic

## Repository Terms

In this repository, Phase 2 should extend the current architecture rather than replace it:

- the **orchestrator** should decide at a policy level which route family fits the task
- the **harness runtime** should execute a chosen route through a stable boundary
- **capabilities** should declare what a backend or executor can actually do
- **state / memory / artifacts** should preserve routing decisions and execution provenance
- the **provider router** should stay narrow and declarative instead of becoming a second orchestrator

## Minimum Useful Outcome

The minimum useful Phase 2 outcome is:

- one explicit router data shape
- one route-selection function
- declared capability records for existing built-ins such as `codex`, `local`, `mock`, and `note-only`
- persisted evidence showing which route was chosen and why
- tests proving route selection does not break the accepted task loop

If Phase 2 cannot yet select and persist routes cleanly, then it is too early to add more backend breadth.

## Affected Areas

Likely primary modules:

- `src/swallow/orchestrator.py`
- `src/swallow/harness.py`
- `src/swallow/executor.py`
- `src/swallow/models.py`
- `src/swallow/store.py`
- `tests/test_cli.py`

Likely new modules:

- `src/swallow/router.py`
- small capability-declaration helpers for route metadata

Likely documentation updates:

- `README.md`
- `README.zh-CN.md`
- `current_state.md`

## First Slice

Recommended first slice: `P2-01 Route Declaration And Selection Baseline`

Goal:
Introduce a minimal route declaration shape that separates executor, runtime backend, and model assumptions even if the initial built-ins still resolve to local-only behavior.

Scope:

- add route records for current built-ins
- add a route-selection function with simple policy inputs
- persist the selected route in task state and run events
- avoid adding real remote transport or SDK integration in this slice

Completion signal:
The code can explain which route was selected, which capabilities it claims, and why the task used it.

## Implementation Steps

1. Add a route model that names executor, backend kind, optional model hint, and declared capabilities.
2. Introduce a router module that selects a route from a small built-in registry.
3. Thread the selected route through orchestrator and harness without moving retrieval logic into the router.
4. Persist route decisions into task state, run-start events, and summary artifacts.
5. Add tests for route declaration, route selection, and persisted route provenance.

## Validation

Each Phase 2 slice should include:

- unit tests for route declaration and selection behavior
- at least one end-to-end CLI run that shows the selected route in persisted outputs
- explicit checks that Phase 1 semantics remain intact for:
  - `state.json`
  - `events.jsonl`
  - `summary.md`
  - `resume_note.md`
  - `memory.json`

## Deferred Items / Non-Goals

Explicitly defer these until a later Phase 2 slice or beyond:

- real remote execution transport
- cost-aware routing across many providers
- dynamic model pricing ingestion
- large backend capability registries
- general plugin compatibility surfaces
- advanced handoff runtime sessions
- tracing-heavy SDK integration

## Decision Rule

When choosing a Phase 2 task, prefer the smallest step that makes routing more explicit without hiding execution behavior behind broad abstractions.

If a change mostly adds more backends but does not improve declared capabilities, route provenance, or harness clarity, it is probably too early.

## Closeout

The kickoff intent in this note has now been satisfied by the completed `P2-01` through `P2-06` baseline.

This note should remain as the Phase 2 starting rationale.
Use `docs/phase2_closeout_note.md` for the current stop/go decision.
