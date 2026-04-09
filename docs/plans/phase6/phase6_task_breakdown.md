# Phase 6 Task Breakdown

This document turns the next retrieval / memory operationalization direction into small executable slices.

It should preserve:

- the accepted local task loop
- current route and topology semantics
- staged knowledge-object records
- the completed post-Phase-5 executor / external-input closeout judgment
- the completed post-Phase-5 retrieval / memory-next closeout judgment

Status:

- planning baseline created on 2026-04-08
- current runtime reference: `current_state.md`
- kickoff reference: `docs/phase6_kickoff_note.md`
- prior closeout references:
  - `docs/phase5_closeout_note.md`
  - `docs/post_phase5_executor_and_external_input_closeout_note.md`
  - `docs/post_phase5_retrieval_memory_next_closeout_note.md`

## Working Rule

Every slice in this breakdown should preserve:

- truthful lifecycle status
- append-only event history
- inspectable artifacts
- orchestrator-controlled retrieval
- explicit evidence linkage
- explicit distinction between task-local records, reusable verified knowledge, and any future canonical records

This breakdown is about retrieval / memory operationalization.

It is not about hosted search infrastructure or generic knowledge-platform breadth.

## Recommended Order

1. `P6-01` Reusable-knowledge index baseline
2. `P6-02` Refresh and invalidation semantics baseline
3. `P6-03` Canonicalization-boundary baseline
4. `P6-04` Cross-task retrieval reuse baseline
5. `P6-05` Reusable-knowledge evaluation tightening
6. `P6-06` Inspection and closeout tightening

Current completion state:

- `P6-01` completed
- `P6-02` completed
- `P6-03` completed
- `P6-04` completed
- `P6-05` completed
- `P6-06` completed

## Tasks

### P6-01 Reusable-Knowledge Index Baseline

Goal:
Introduce an explicit, inspectable record of reusable knowledge that is eligible for retrieval-layer reuse.

Scope:

- define a narrow reusable-knowledge index or index-like artifact
- keep it separate from raw `knowledge_objects.json`
- preserve source traceability, artifact evidence, and task linkage

Validation:

- operators can inspect which knowledge records are currently reusable
- the index remains derived and inspectable rather than hidden
- default retrieval semantics remain explicit

Non-goals:

- hosted vector stores
- broad automatic indexing services

Completion note:

- implemented with an explicit derived `knowledge_index.json` and readable `knowledge_index_report.md`
- the index records only currently reusable knowledge records that satisfy the active retrieval reuse gate
- task creation now persists knowledge-index artifacts and exposes their counts through state artifact paths and task-created events
- operator-facing inspection now includes `knowledge-index` artifact commands and compact visibility in task inspect/review flows

### P6-02 Refresh And Invalidation Semantics Baseline

Goal:
Make reusable-knowledge records refreshable and invalidatable when their evidence or policy state changes.

Scope:

- introduce narrow refresh metadata
- define invalidation triggers for stale or no-longer-eligible records
- preserve readable operator-facing status

Validation:

- reusable knowledge can become stale or invalid explicitly
- invalid reusable records do not silently remain active

Non-goals:

- large background schedulers
- fully automatic sync engines

Completion note:

- implemented with derived refresh metadata in `knowledge_index.json` and `knowledge_index_report.md`
- reusable candidates are now partitioned into active and inactive index records with explicit invalidation reasons
- current invalidation reasons cover non-retrieval candidates, non-verified stage, and non-artifact-backed evidence
- operator-facing inspection now surfaces refreshed-at timestamps plus active/inactive reusable counts in inspect, review, memory, summary, and resume outputs
- refresh remains derived from current task boundaries rather than a background indexing service

### P6-03 Canonicalization-Boundary Baseline

Goal:
Make the boundary between reusable verified knowledge and canonical knowledge more explicit.

Scope:

- define narrow canonicalization intent or readiness semantics
- avoid treating all verified knowledge as canonical
- keep canonicalization auditable and evidence-aware

Validation:

- verified versus canonical remains operationally meaningful
- canonicalization boundaries are visible in policy or artifact outputs

Non-goals:

- fully automatic promotion of all reusable knowledge
- broad knowledge governance systems

Completion note:

- implemented with an explicit `canonicalization_intent` declaration on imported knowledge objects while keeping `verified` and `canonical` as separate operational stages
- added derived canonicalization boundary semantics such as `review_ready`, `promotion_ready`, `blocked_stage`, and `blocked_evidence`
- canonicalization boundary status is now visible in knowledge-object reports, knowledge-index records, knowledge-policy findings, executor prompt context, task memory, summary/resume artifacts, and compact inspect/review flows
- this slice does not auto-promote verified knowledge into canonical knowledge; it only makes readiness and blocking conditions explicit

### P6-04 Cross-Task Retrieval Reuse Baseline

Goal:
Allow reusable knowledge to participate in later tasks through explicit cross-task retrieval boundaries.

Scope:

- tighten cross-task reuse semantics
- preserve source, task, and artifact references
- avoid silently flattening all history into one undifferentiated retrieval pool

Validation:

- later tasks can reuse eligible knowledge with clear traceability
- task-local and cross-task reused knowledge remain distinguishable

Non-goals:

- large global memory stores
- hidden background recall

Completion note:

- implemented by binding reusable knowledge selection to explicit retrieval context layers instead of implicit global scanning
- current-task reusable knowledge now depends on the `task` context layer, while cross-task reusable knowledge depends on the `history` context layer
- reusable knowledge retrieval metadata now records `knowledge_task_id` and `knowledge_task_relation` so current-task and cross-task reuse remain distinguishable
- retrieval events, reports, task memory, summary/resume artifacts, executor prompt context, and inspect/review flows now surface current-task versus cross-task reused-knowledge counts
- default task retrieval behavior remains unchanged because the accepted baseline still requests only `repo` and `notes`

### P6-05 Reusable-Knowledge Evaluation Tightening

Goal:
Strengthen regression and evaluation coverage around reusable-knowledge behavior.

Scope:

- add focused fixtures for reuse, invalidation, and policy boundaries
- keep evaluation local and lightweight
- preserve inspectable expectations

Validation:

- regressions in reusable-knowledge behavior are caught by tests
- policy and retrieval boundaries are represented in evaluation fixtures

Non-goals:

- heavy external evaluation frameworks
- broad benchmark infrastructure

Completion note:

- implemented with fixture-based reusable-knowledge regression coverage under `tests/fixtures/retrieval_eval/`
- evaluation now covers current-task reusable knowledge, cross-task reusable knowledge, and blocked knowledge that should remain excluded
- fixture-backed tests preserve explicit expectations for `knowledge_task_relation`, citations, and source boundaries instead of relying only on ad hoc inline test data
- the evaluation layer remains local and lightweight; no external benchmark infrastructure was introduced

### P6-06 Inspection And Closeout Tightening

Goal:
Close the phase by aligning operator inspection and producing a clear stop/go judgment.

Scope:

- align CLI and artifact inspection with operational retrieval semantics
- align status documents and references
- write a Phase 6 closeout note

Validation:

- reusable-knowledge operational state is easy to inspect
- current-state and planning-entry docs agree on the resulting checkpoint

Non-goals:

- starting the next phase implicitly

Completion note:

- operator-facing inspection now carries reusable-knowledge operational signals for canonicalization readiness plus current-task versus cross-task reuse boundaries
- Phase 6 closeout is recorded in `docs/phase6_closeout_note.md`
- status and planning-entry documents now agree that Phase 6 baseline is complete and should not continue by default without a fresh planning note
