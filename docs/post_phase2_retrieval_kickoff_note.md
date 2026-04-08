# Post-Phase-2 Retrieval Kickoff Note

Status:

- retrieval baseline completed on 2026-04-08
- closeout reference: `docs/post_phase2_retrieval_closeout_note.md`

This note defines the next planning direction after the completed Phase 2 baseline.

The repository should now strengthen retrieval as a durable system layer without breaking the accepted local task loop or the current artifact semantics.

## Goal

Move retrieval from the current baseline into a more extensible system-level RAG layer that improves:

- retrieval quality
- source coverage
- memory reuse
- grounding reuse across reruns and later task stages

The immediate goal is not to build a giant retrieval platform. The immediate goal is to make context acquisition more reliable, more reusable, and easier to extend while preserving the current task lifecycle and artifact model.

## Scope

This planning direction should focus on:

- better retrieval ranking and query shaping
- clearer source-adapter boundaries
- broader local source coverage beyond the current repo-file and markdown-note baseline
- tighter reuse between retrieval outputs, task memory, source grounding, and later reruns
- retrieval outputs that remain traceable, citable, and inspectable

This planning direction should preserve:

- the current local-first task loop
- truthful `state.json` and `events.jsonl`
- the current `summary.md`, `resume_note.md`, `source_grounding.md`, `memory.json`, `validation_report.md`, `route_report.md`, and `compatibility_report.md` semantics
- orchestrator control over whether and when retrieval runs

## Repository Terms

In this repository, the retrieval layer should remain separate from:

- the **orchestrator**, which decides when retrieval is needed
- the **harness runtime**, which runs the workflow loop and persists outcomes
- the **provider router**, which should not absorb retrieval logic

The retrieval layer should own:

- source adapters
- parsing
- chunking
- metadata shaping
- query preparation
- scoring or reranking hooks
- citation-ready grounding outputs

## Minimum Useful Outcome

The minimum useful post-Phase-2 retrieval outcome is:

- one explicit retrieval planning note and task breakdown
- one cleaner source-adapter seam
- one measurable retrieval-quality improvement over the current scoring baseline
- one source-coverage expansion that remains local-first and inspectable
- one tighter reuse path between retrieval outputs and `memory.json` / `source_grounding.md`
- tests that prove artifact semantics remain stable

If retrieval becomes broader but less traceable, the change is not successful.

## Likely First Slices

Recommended first implementation slices:

1. retrieval adapter seam cleanup
2. query shaping and rerank baseline
3. source coverage expansion for local docs and task-produced artifacts
4. retrieval-memory reuse tightening
5. retrieval evaluation fixture baseline

## Affected Areas

Likely primary modules:

- `src/swallow/retrieval.py`
- `src/swallow/orchestrator.py`
- `src/swallow/harness.py`
- `src/swallow/models.py`
- `src/swallow/store.py`
- `tests/test_cli.py`

Likely new modules:

- retrieval adapter helpers
- ranking or query-shaping helpers
- retrieval-memory helpers

Likely documentation updates:

- `README.md`
- `README.zh-CN.md`
- `current_state.md`

## Validation

Each retrieval slice should include:

- tests for source-specific chunking or ranking behavior
- at least one persisted-output check over `retrieval.json`, `source_grounding.md`, or `memory.json`
- explicit checks that current task lifecycle semantics remain unchanged
- explicit checks that current summary and resume note roles remain unchanged

## Deferred Items / Non-Goals

Explicitly defer these unless a concrete implementation need appears:

- GraphRAG by default
- broad web-scale connectors
- hosted vector infrastructure
- heavy background indexing services
- retrieval logic hidden inside one executor vendor
- full multi-agent retrieval orchestration
- opaque retrieval that cannot be explained through citations and artifacts

## Decision Rule

Prefer the smallest retrieval change that improves grounding quality or reuse while keeping the system:

- local-first
- artifact-driven
- orchestrator-controlled
- easy to inspect during reruns and debugging

## Closeout

The kickoff intent in this note has now been satisfied by the completed `R1-01` through `R1-06` baseline.

This note should remain as the retrieval starting rationale.
Use `docs/post_phase2_retrieval_closeout_note.md` for the current stop/go decision.
