# Post-Phase-5 Executor And External Input Task Breakdown

This document turns the post-Phase-5 executor-family and external-input direction into small executable slices.

It should preserve the accepted local task loop, current artifact semantics, and the completed Phase 5 closeout judgment while defining the next planning-ready implementation path.

Status:

- planning baseline created on 2026-04-08
- current runtime reference: `current_state.md`
- kickoff reference: `docs/post_phase5_executor_and_external_input_kickoff_note.md`
- prior closeout references:
  - `docs/phase5_closeout_note.md`
  - `docs/phase4_closeout_note.md`
  - `docs/post_phase2_retrieval_closeout_note.md`

## Working Rule

Every slice in this breakdown should preserve:

- truthful lifecycle status
- truthful phase progression
- append-only event history
- inspectable artifacts
- explicit route and topology records
- retrieval under orchestrator control
- local-first baseline behavior unless a slice explicitly changes the boundary

This breakdown is about ingestion, normalization, executor-family boundaries, and persistence semantics.

It is not about pretending that API executors are already implemented, and it is not about turning the repository into a generic chat product.

## Recommended Order

1. `X1-01` Executor family declaration baseline
2. `X1-02` Task-semantics ingestion baseline
3. `X1-03` Staged knowledge-object record baseline
4. `X1-04` Artifact-backed external knowledge capture baseline
5. `X1-05` Promotion and verification policy baseline
6. `X1-06` Inspection and closeout tightening

Current completion state:

- `X1-01` completed
- `X1-02` completed
- `X1-03` completed
- `X1-04` completed
- `X1-05` completed
- `X1-06` completed

## Tasks

### X1-01 Executor Family Declaration Baseline

Goal:
Make executor family a first-class declared planning concept without changing the current accepted executor behavior.

Scope:

- add an explicit executor-family concept to planning and task-facing records
- distinguish at least:
  - `api`
  - `cli`
- keep the current model / runtime-backend / executor distinction intact
- avoid implying that hosted API execution already exists

Likely affected areas:

- route and executor planning documents
- task or route metadata models
- operator-facing summaries and inspection artifacts

Validation:

- executor family is declared explicitly and readably
- route and executor records remain truthful
- current local executor paths remain valid

Non-goals:

- full API executor implementation
- vendor-specific adapters
- remote hosted execution

Completion note:

- implemented with an explicit `executor_family` baseline carried through route selection, task state, topology, dispatch, handoff, memory, prompt context, and operator-facing reports
- current built-in routes declare `cli` as the accepted executor family baseline
- this slice preserves current executor behavior and does not imply that API executor support already exists

### X1-02 Task-Semantics Ingestion Baseline

Goal:
Turn external planning handoff into a small explicit task-semantics record instead of leaving it as loose notes or chat residue.

Scope:

- define a task-semantics shape for imported planning intent
- support fields such as:
  - task goal
  - constraints
  - acceptance criteria
  - priority hints
  - next-action proposals
- keep imported planning separate from canonical task truth until explicitly accepted

Likely affected areas:

- task-state and artifact planning
- task creation or task-import boundaries
- summary and review semantics

Validation:

- external planning input is represented as task-linked semantics instead of raw conversation
- task semantics remain distinguishable from execution results
- source linkage is preserved

Non-goals:

- full planner UI
- free-form chat archival
- automatic execution from raw imported plans

Completion note:

- implemented with an explicit `task_semantics` record persisted as `task_semantics.json`
- task creation now accepts small imported-planning fields such as constraints, acceptance criteria, priority hints, next action proposals, and an optional planning source reference
- the imported planning handoff is rendered into `task_semantics_report.md` and carried through task state, `task.created`, prompt context, summary, resume note, memory, and compact task inspection
- this slice preserves current task truth and does not yet introduce staged knowledge objects or automatic plan execution

### X1-03 Staged Knowledge-Object Record Baseline

Goal:
Introduce a minimal explicit record for external knowledge objects with staged promotion semantics.

Scope:

- define a staged knowledge-object shape
- support at least:
  - `raw`
  - `candidate`
  - `verified`
  - `canonical`
- distinguish knowledge objects from task objects
- preserve task linkage and artifact linkage where relevant

Likely affected areas:

- retrieval and memory planning
- artifact schemas
- knowledge-capture documentation and state references

Validation:

- external knowledge no longer needs to be represented as undifferentiated notes
- staged status is explicit and inspectable
- task-linked versus reusable knowledge usage remains distinguishable

Non-goals:

- large knowledge-base platforms
- automatic canonicalization
- hidden background ingestion

Completion note:

- implemented with explicit staged knowledge-object records persisted as `knowledge_objects.json`
- task creation now accepts repeatable imported knowledge fragments plus an initial stage and optional source reference
- the current baseline supports `raw`, `candidate`, `verified`, and `canonical` stages as explicit record fields
- knowledge objects are rendered into `knowledge_objects_report.md` and carried through task state, prompt context, summary, resume note, memory, and compact inspection
- this slice does not yet make knowledge objects retrievable by default and does not yet automate promotion policy

### X1-04 Artifact-Backed External Knowledge Capture Baseline

Goal:
Require stronger evidence and source traceability for captured external knowledge.

Scope:

- define artifact-backed evidence expectations for imported knowledge
- preserve:
  - source identity
  - capture time
  - task linkage where relevant
  - artifact linkage where relevant
- prefer source-backed records over unsupported summaries

Likely affected areas:

- retrieval artifacts
- memory artifacts
- imported-note or imported-summary records

Validation:

- knowledge records can point back to a source or supporting artifact
- evidence preservation remains compatible with staged promotion
- unsupported knowledge can be kept as `raw` or `candidate` instead of being over-promoted

Non-goals:

- full citation-management systems
- external document-sync platforms

Completion note:

- implemented with explicit per-object evidence fields such as `artifact_ref`, `captured_at`, and `evidence_status`
- task creation now accepts optional artifact-backed evidence refs aligned to imported knowledge objects
- the current baseline distinguishes `artifact_backed`, `source_only`, and `unbacked` knowledge records
- evidence counts are now visible in creation events, prompt context, summary, resume note, memory, compact inspection, and `knowledge_objects_report.md`
- this slice preserves traceability and evidence shape without yet enforcing promotion or verification policy

### X1-05 Promotion And Verification Policy Baseline

Goal:
Define a small explicit policy for how imported knowledge moves between stages.

Scope:

- define promotion rules between:
  - `raw`
  - `candidate`
  - `verified`
  - `canonical`
- define minimal verification expectations
- keep policy readable and operator-auditable

Likely affected areas:

- retrieval and memory policy documents
- validation or review records
- operator inspection paths

Validation:

- promotion status changes are explainable
- noise control and canonicalization remain explicit
- the system does not treat every imported statement as durable truth

Non-goals:

- full trust scoring engines
- heavyweight moderation systems

Completion note:

- implemented with an explicit `knowledge_policy` evaluation layer that checks stage and evidence consistency for imported knowledge objects
- the current baseline persists `knowledge_policy.json` and `knowledge_policy_report.md` alongside the existing task, retrieval, and validation artifacts
- policy status is now surfaced through summary, resume note, handoff, memory, compact inspection, review flows, and terminal task payloads
- blocking policy failures now prevent imported knowledge from being treated as a successful run baseline while preserving the underlying source and artifact trail

### X1-06 Inspection And Closeout Tightening

Goal:
Close the slice by making executor-family and external-input records inspectable and resumable.

Scope:

- align operator-facing inspection paths with the new planning objects
- ensure task objects and knowledge objects remain distinguishable
- update status references and resume references once the slice is implemented

Likely affected areas:

- inspection commands and summaries
- README and current-state references
- future closeout notes

Validation:

- operators can tell what was imported, how it was normalized, and what evidence exists
- executor-family records do not blur into backend or vendor records
- closeout judgment can be made without ambiguity

Non-goals:

- new chat-centric UI
- broad product-surface redesign

Completion note:

- implemented with explicit CLI inspection paths for task semantics, knowledge objects, and knowledge policy in both report and JSON form
- review-oriented output now exposes task semantics and staged knowledge artifacts alongside handoff and validation surfaces
- README, current-state references, and closeout references are aligned so this slice can stop cleanly without pretending a new phase has started

## Deferred Beyond This Breakdown

Keep these outside the active slice unless a narrower implementation need appears:

- full API executor runtime support
- broad vendor integration matrices
- marketplace or hosted knowledge services
- direct canonical storage of external chat logs
- generic social or messaging features

## Planning Judgment

This breakdown is the current planning-ready follow-up to the completed Phase 5 baseline.

It is a valid next implementation direction if the repository wants to:

- refine execution boundaries beyond a single executor category
- make external planning and external knowledge legible inside the workflow system
- strengthen retrieval and memory semantics without changing the accepted local-first baseline

Do not start this slice by default without naming the smallest first cut.
