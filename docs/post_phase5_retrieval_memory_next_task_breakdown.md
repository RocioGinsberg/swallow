# Post-Phase-5 Retrieval And Memory Next Task Breakdown

This document turns the next retrieval/memory direction into small executable slices.

It should preserve the accepted local task loop, current route/topology semantics, staged knowledge-object records, and the completed post-Phase-5 executor/external-input closeout judgment.

Status:

- planning baseline created on 2026-04-08
- current runtime reference: `current_state.md`
- kickoff reference: `docs/post_phase5_retrieval_memory_next_kickoff_note.md`
- prior closeout references:
  - `docs/post_phase5_executor_and_external_input_closeout_note.md`
  - `docs/post_phase2_retrieval_closeout_note.md`
  - `docs/phase5_closeout_note.md`

## Working Rule

Every slice in this breakdown should preserve:

- truthful lifecycle status
- truthful phase progression
- append-only event history
- inspectable artifacts
- orchestrator-controlled retrieval
- explicit distinction between task objects and knowledge objects
- explicit distinction between task-linked knowledge and reusable retrieval-layer knowledge

This breakdown is about retrieval-facing reuse, staged promotion boundaries, and memory semantics.

It is not about building a generic knowledge service or pretending canonical long-term storage already exists.

## Recommended Order

1. `R2-01` Retrieval-eligible knowledge declaration baseline
2. `R2-02` Task-linked versus reusable knowledge partition baseline
3. `R2-03` Verified-knowledge retrieval source baseline
4. `R2-04` Reuse-aware retrieval memory tightening
5. `R2-05` Knowledge-reuse policy and verification tightening
6. `R2-06` Inspection and closeout tightening

Current completion state:

- `R2-01` completed
- `R2-02` completed
- `R2-03` completed
- `R2-04` completed
- `R2-05` completed
- `R2-06` completed

## Tasks

### R2-01 Retrieval-Eligible Knowledge Declaration Baseline

Goal:
Make it explicit which staged knowledge objects are eligible for retrieval reuse.

Scope:

- add a narrow declaration for retrieval eligibility
- keep eligibility separate from promotion stage itself
- keep task-local imported knowledge usable without making it automatically reusable

Likely affected areas:

- knowledge-object record shape
- retrieval and memory artifacts
- operator-facing inspection

Validation:

- retrieval eligibility is explicit and inspectable
- knowledge stage and retrieval eligibility remain separate concepts
- current task-local knowledge records still work without reuse enabled

Non-goals:

- full indexing system
- automatic eligibility inference for every record

Completion note:

- implemented with explicit per-object `retrieval_eligible` and `knowledge_reuse_scope` fields
- task creation can now declare imported knowledge as retrieval-eligible candidates without automatically enabling reuse in retrieval
- retrieval-eligibility state is visible in `knowledge_objects.json`, `knowledge_objects_report.md`, task events, summary, resume note, task memory, prompt context, and compact inspection
- this slice preserves the current retrieval baseline by keeping eligibility declarative rather than automatically adding a new retrieval source

### R2-02 Task-Linked Versus Reusable Knowledge Partition Baseline

Goal:
Separate knowledge that stays task-bound from knowledge that can be reused by later tasks.

Scope:

- define a minimal partition between:
  - task-linked knowledge
  - reusable knowledge
- preserve links back to task, source, and artifact evidence
- avoid silently flattening everything into one shared memory surface

Likely affected areas:

- knowledge-object storage semantics
- memory artifacts
- retrieval planning documents

Validation:

- operators can tell whether a record is task-bound or reusable
- reuse boundaries stay explicit
- task-specific context does not leak into generic retrieval by default

Non-goals:

- multi-tenant knowledge stores
- global deduplication engines

Completion note:

- implemented with an explicit `knowledge_partition` record that separates task-linked knowledge from reusable retrieval candidates
- the current baseline persists `knowledge_partition.json` and `knowledge_partition_report.md` without changing default retrieval behavior
- partition state is now visible in creation events, compact inspection, review flows, grouped artifact indexes, task memory, and dedicated CLI inspection commands
- this slice keeps task-bound context and reusable knowledge distinct without introducing a global shared knowledge store

### R2-03 Verified-Knowledge Retrieval Source Baseline

Goal:
Introduce a narrow retrieval source path for explicitly reusable verified knowledge.

Scope:

- allow retrieval to include a verified-knowledge source when explicitly requested or policy-eligible
- preserve citation, source traceability, and artifact evidence
- keep this source narrow and inspectable

Likely affected areas:

- retrieval source selection
- retrieval metadata
- grounding and retrieval artifacts

Validation:

- retrieval can surface verified reusable knowledge through an explicit source type
- grounding still points back to artifact-backed or source-backed records
- default retrieval behavior stays stable unless the new source is explicitly enabled

Non-goals:

- canonical knowledge base platform
- broad semantic search infrastructure

Completion note:

- implemented with an explicit `knowledge` retrieval source that remains opt-in rather than joining the default `repo + notes` source set
- retrieval now surfaces only `verified` knowledge objects whose reuse scope is `retrieval_candidate`
- retrieved knowledge records preserve source traceability through `knowledge_objects.json#<object_id>` citations and metadata such as `knowledge_stage`, `knowledge_reuse_scope`, `artifact_ref`, and `source_ref`
- this slice preserves the current retrieval baseline by keeping verified-knowledge reuse explicit and narrow instead of silently broadening default retrieval

### R2-04 Reuse-Aware Retrieval Memory Tightening

Goal:
Make retrieval memory and rerun context aware of reusable verified knowledge.

Scope:

- expose reused knowledge records in retrieval memory
- tighten summary, resume note, and task memory so reused knowledge is visible
- preserve distinction between fresh retrieval and prior reusable knowledge

Likely affected areas:

- memory artifacts
- summary and resume note generation
- retrieval reports

Validation:

- later runs can tell when reusable knowledge was part of context
- task memory remains explicit about evidence and reuse origin
- reused knowledge does not hide fresh retrieval

Non-goals:

- opaque caching layers
- hidden background memory retrieval

Completion note:

- implemented with explicit reused-knowledge summaries in retrieval memory, retrieval reports, summary output, resume notes, and retrieval completion events
- task memory now records reused verified-knowledge counts, references, object ids, and evidence-status counts alongside the broader retrieval snapshot
- rerun prompt context now surfaces prior reused-knowledge counts and references so later executions can distinguish fresh retrieval from previously reused verified knowledge
- this slice preserves current retrieval selection behavior while making reuse visible and auditable across reruns

### R2-05 Knowledge-Reuse Policy And Verification Tightening

Goal:
Refine policy around when verified knowledge can be reused and when it should stay blocked or task-local.

Scope:

- tighten policy for reuse eligibility versus promotion status
- preserve explicit blocking or warning states
- keep policy readable and operator-auditable

Likely affected areas:

- knowledge policy
- retrieval policy
- operator review artifacts

Validation:

- reuse policy is explainable
- verified versus canonical remains meaningful
- unsupported records do not silently enter reusable retrieval

Non-goals:

- heavy trust scoring
- fully automated canonical knowledge management

Completion note:

- implemented with explicit reuse-gate policy tightening for retrieval-candidate knowledge records
- the current baseline now treats only `verified + artifact_backed + retrieval_candidate` records as reusable by the retrieval layer
- `source_only` verified retrieval candidates remain recorded and inspectable but are warned on and kept out of reusable retrieval
- non-verified retrieval candidates now fail policy explicitly instead of silently remaining ambiguous

### R2-06 Inspection And Closeout Tightening

Goal:
Close the slice by making reusable knowledge decisions easy to inspect and resume from.

Scope:

- align CLI inspection paths with reusable-knowledge semantics
- align summary/resume/current-state references
- produce a clear stop/go judgment

Completion note:

- implemented with reusable-knowledge visibility in `swl task inspect` and `swl task review`, including reused-knowledge counts and references from the latest retrieval record
- review flows now surface `retrieval_report` and `source_grounding` alongside knowledge-policy and knowledge-object artifacts when reusable knowledge is part of operator review
- the slice is closed out in `docs/post_phase5_retrieval_memory_next_closeout_note.md`, which becomes the new stop/go reference for this retrieval / memory segment

Likely affected areas:

- inspection commands and reports
- README and current-state references
- future closeout notes

Validation:

- operators can tell which knowledge was reusable, why, and with what evidence
- task-linked and reusable records remain distinguishable
- closeout judgment can be made without ambiguity

Non-goals:

- new UI surfaces
- unrelated executor or topology expansion

## Deferred Beyond This Breakdown

Keep these outside the active slice unless a narrower implementation need appears:

- full long-lived canonical knowledge store
- remote retrieval infrastructure
- hosted synchronization and indexing services
- API executor runtime integration
- broad new source-family expansion

## Planning Judgment

This breakdown is the current planning-ready follow-up if the repository wants to continue on the `Retrieval / Memory` track after the completed post-Phase-5 executor/external-input slice.

It is a valid next implementation direction if the repository wants to:

- make staged knowledge objects useful to later retrieval
- preserve evidence and promotion boundaries while increasing reuse value
- avoid turning imported external input into an uncontrolled long-term memory layer

Do not start this slice by default without naming the smallest first cut.
