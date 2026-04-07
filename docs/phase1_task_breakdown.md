# Phase 1 Task Breakdown

This document turns the Phase 1 kickoff direction into concrete implementation tasks.

It is intentionally small. The goal is to make Phase 1 executable without expanding it into a broad platform program.

## Working Rule

Phase 1 should still preserve the accepted Phase 0 loop:

- truthful lifecycle status
- truthful phase progression
- append-only event history
- inspectable artifacts

Each task below should be completed with tests and at least one persisted-output check.

## Task Order

Recommended implementation order:

1. `P1-01` Retrieval result shape and metadata baseline
2. `P1-02` Source-aware chunking and ranking baseline
3. `P1-03` Harness retrieval boundary cleanup
4. `P1-04` Executor selection seam and second-executor groundwork
5. `P1-05` Validator and execution-policy baseline
6. `P1-06` Artifact and memory tightening

## Tasks

### P1-01 Retrieval Result Shape And Metadata Baseline

Goal:
Define a retrieval result shape that can act as a system-level knowledge record rather than a one-shot prompt helper.

Scope:

- add clearer retrieval metadata for source type, path, chunk identity, and score context
- ensure retrieval outputs are traceable and suitable for citation or artifact storage
- keep the retrieval layer external to any single executor surface

Likely affected areas:

- `src/swallow/models.py`
- `src/swallow/retrieval.py`
- `src/swallow/store.py`
- `tests/test_cli.py`

Validation:

- retrieval outputs remain persisted under task state
- retrieval metadata is explicit enough to explain why an item was returned
- tests cover the new retrieval result shape

Non-goals:

- vector databases
- reranker models
- large ingestion infrastructure

### P1-02 Source-Aware Chunking And Ranking Baseline

Goal:
Replace naive file-level retrieval with a more useful source-aware baseline for repository files and markdown notes.

Scope:

- separate chunking behavior for repo files and markdown notes
- add stronger ranking signals such as path, headings, filenames, or section structure
- improve retrieval stability for practical task prompts

Likely affected areas:

- `src/swallow/retrieval.py`
- new retrieval helper modules if needed
- `tests/test_cli.py`

Validation:

- tests cover both repo-file and markdown-note retrieval behavior
- realistic prompts return more believable top hits than the current file-level baseline
- persisted retrieval records remain readable and traceable

Non-goals:

- full hybrid lexical + vector search
- query decomposition
- GraphRAG

### P1-03 Harness Retrieval Boundary Cleanup

Goal:
Clarify the runtime boundary between retrieval-layer mechanics and orchestrator retrieval decisions.

Scope:

- make it clearer which layer decides whether to retrieve, from where, and whether to retrieve again
- keep chunking, metadata, rerank hooks, and citation shaping inside the retrieval layer
- keep retrieval invocation and stopping conditions inside orchestrator or harness control flow

Likely affected areas:

- `src/swallow/orchestrator.py`
- `src/swallow/harness.py`
- `src/swallow/retrieval.py`
- `tests/test_cli.py`

Validation:

- orchestration flow remains inspectable
- retrieval behavior does not leak executor-specific assumptions into the core loop
- state and event semantics from Phase 0 stay intact

Non-goals:

- multi-agent retrieval delegation
- provider-router abstractions

### P1-04 Executor Selection Seam And Second-Executor Groundwork

Goal:
Prove that retrieval and execution are not hard-bound to the Codex path.

Scope:

- introduce a narrow executor selection seam
- prepare or add a second executor path without destabilizing the accepted loop
- keep vendor built-in retrieval optional and shortcut-only

Likely affected areas:

- `src/swallow/executor.py`
- `src/swallow/harness.py`
- `src/swallow/models.py`
- `tests/test_cli.py`

Validation:

- executor selection is explicit and testable
- retrieval behavior remains system-controlled regardless of executor choice
- tests cover at least two executor paths

Non-goals:

- broad provider routing
- large backend capability registry

### P1-05 Validator And Execution-Policy Baseline

Goal:
Introduce the first explicit quality checks around run outputs.

Scope:

- define a minimal validator or policy shape
- add first checks around artifact completeness, retrieval result sanity, or run-result consistency
- keep validator outputs inspectable and easy to persist

Likely affected areas:

- new validator or policy modules
- `src/swallow/harness.py`
- `src/swallow/models.py`
- `src/swallow/store.py`
- `tests/test_cli.py`

Validation:

- validator outcomes are visible in persisted outputs or events
- success, warning, and failure cases are testable
- the validator layer does not break the accepted Phase 0 lifecycle semantics

Non-goals:

- large policy engines
- complex evaluation orchestration

### P1-06 Artifact And Memory Tightening

Goal:
Make retrieval outputs easier to reuse across later runs and later task stages.

Scope:

- improve how retrieval outputs connect to summary, resume note, and later task reuse
- tighten how retrieval records cooperate with state / memory / artifacts
- prepare for richer historical-context usage later without implementing a full long-term memory system

Likely affected areas:

- `src/swallow/store.py`
- `src/swallow/harness.py`
- `src/swallow/models.py`
- `tests/test_cli.py`

Validation:

- retrieval-linked artifacts are easier to inspect and reuse
- later task review can recover source grounding more easily
- tests confirm retrieval-related artifact behavior remains stable

Non-goals:

- full long-term memory architecture
- background indexing or memory services

## Deferred Beyond This Breakdown

Keep these outside the active Phase 1 task list unless a concrete implementation need appears:

- provider routing work
- GraphRAG by default
- large source matrix expansion
- complex multi-agent retrieval
- hosted indexing infrastructure
