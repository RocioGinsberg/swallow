# Post-Phase-2 Retrieval Task Breakdown

This document turns the post-Phase-2 retrieval direction into small executable slices.

It should preserve the accepted local task loop and current artifact semantics while expanding retrieval into a more sustainable system layer.

Status:

- baseline complete on 2026-04-08
- current runtime reference: `current_state.md`
- closeout reference: `docs/post_phase2_retrieval_closeout_note.md`

## Working Rule

Every retrieval slice should keep these repository truths intact:

- truthful lifecycle status
- truthful phase progression
- append-only event history
- inspectable grounding artifacts
- reusable task memory
- retrieval under orchestrator control rather than executor control

## Recommended Order

1. `R1-01` Retrieval adapter seam baseline
2. `R1-02` Query shaping and rerank baseline
3. `R1-03` Local source coverage expansion
4. `R1-04` Retrieval-memory reuse tightening
5. `R1-05` Retrieval artifact indexing cleanup
6. `R1-06` Retrieval evaluation fixture baseline

Current completion state:

- `R1-01` completed
- `R1-02` completed
- `R1-03` completed
- `R1-04` completed
- `R1-05` completed
- `R1-06` completed

## Tasks

### R1-01 Retrieval Adapter Seam Baseline

Goal:
Introduce a clearer retrieval source-adapter boundary so source coverage can expand without turning `retrieval.py` into one large mixed parser.

Scope:

- define a small adapter shape for source-specific parsing and chunking
- keep repo-file and markdown-note behavior working through the new seam
- preserve current retrieval result shape and citation semantics

Likely affected areas:

- `src/swallow/retrieval.py`
- new retrieval adapter helper modules
- `tests/test_cli.py`

Validation:

- repo and markdown retrieval behavior still passes
- retrieval outputs remain traceable and citation-ready
- no task lifecycle semantics change

Non-goals:

- remote source ingestion
- vector databases
- background index daemons

### R1-02 Query Shaping And Rerank Baseline

Goal:
Improve retrieval quality beyond the current token-count scoring baseline.

Scope:

- add a small query-preparation layer
- add lightweight rerank or score-normalization hooks
- keep scoring inspectable through persisted score metadata

Likely affected areas:

- `src/swallow/retrieval.py`
- new ranking helpers if needed
- `src/swallow/models.py`
- `tests/test_cli.py`

Validation:

- tests show predictable ranking improvements for representative queries
- `retrieval.json` and `source_grounding.md` still explain why items were returned

Non-goals:

- opaque ML rerank services
- vendor-only retrieval shortcuts

### R1-03 Local Source Coverage Expansion

Goal:
Broaden local source coverage without changing the local-first operating model.

Scope:

- add at least one new local source family beyond current repo files and markdown notes
- likely candidates:
  - local docs and design notes under dedicated folders
  - task-produced artifacts such as summaries or grounding files
  - structured local text formats that remain easy to parse
- keep source-specific metadata explicit

Likely affected areas:

- `src/swallow/retrieval.py`
- new source-adapter helpers
- `src/swallow/harness.py`
- `tests/test_cli.py`

Validation:

- new source type is visible in `retrieval.json`
- source grounding remains readable
- orchestrator retrieval flow stays unchanged

Non-goals:

- arbitrary binary ingestion
- remote SaaS connectors

### R1-04 Retrieval-Memory Reuse Tightening

Goal:
Make prior retrieval outputs easier to reuse in later runs instead of recomputing context every time.

Scope:

- tighten the link between current retrieval outputs and `memory.json`
- surface reusable prior grounding more explicitly during reruns
- keep reuse explicit rather than silently mixing historical context into fresh retrieval

Likely affected areas:

- `src/swallow/harness.py`
- `src/swallow/executor.py`
- `src/swallow/store.py`
- `tests/test_cli.py`

Validation:

- rerun prompts or memory packets expose prior retrieval grounding more clearly
- persisted outputs distinguish fresh retrieval from historical reuse

Non-goals:

- fully autonomous long-term memory systems
- hidden retrieval caches that cannot be inspected

### R1-05 Retrieval Artifact Indexing Cleanup

Goal:
Make retrieval artifacts easier to review, reuse, and connect to later task stages.

Scope:

- tighten artifact indexing for `retrieval.json`, `source_grounding.md`, and memory references
- improve how summaries and resume notes point to grounding outputs
- keep artifact semantics stable while improving discoverability

Likely affected areas:

- `src/swallow/harness.py`
- `src/swallow/orchestrator.py`
- `tests/test_cli.py`

Validation:

- artifact links are easier to inspect
- route, compatibility, validation, and retrieval artifacts remain clearly separated

Non-goals:

- observability stacks
- external dashboards

### R1-06 Retrieval Evaluation Fixture Baseline

Goal:
Add a small regression-oriented evaluation layer for retrieval quality.

Scope:

- define a tiny set of representative retrieval fixtures
- encode expected ranking or inclusion outcomes in tests
- make retrieval improvements easier to verify before adding more source breadth

Likely affected areas:

- `tests/test_cli.py`
- optional small fixture files under `tests/`

Validation:

- tests fail when retrieval quality regresses on the covered fixtures
- evaluation remains lightweight and local

Non-goals:

- large benchmark suites
- hosted retrieval evaluation infrastructure

## Deferred Beyond This Breakdown

Keep these outside the active retrieval expansion plan unless a concrete implementation need appears:

- GraphRAG as the default path
- broad remote connectors
- cloud vector services
- hidden retrieval inside a single vendor executor
- heavyweight background indexing systems

## Closeout Judgment

The planned post-Phase-2 retrieval baseline is complete.

Do not keep expanding retrieval by default without a fresh planning note that names the next concrete problem to solve.

Use `docs/post_phase2_retrieval_closeout_note.md` as the decision reference before starting any follow-up retrieval work.
