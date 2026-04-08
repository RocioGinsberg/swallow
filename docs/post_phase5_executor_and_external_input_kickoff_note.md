# Post-Phase-5 Executor And External Input Kickoff Note

This note defines a possible next planning slice after the completed Phase 5 baseline.

It does not change the current implementation-status judgment. Phase 5 remains complete enough to stop open-ended `Capabilities` expansion by default.

## Why This Slice Exists

The repository now has:

- a stable local-first task loop
- explicit route and topology records
- a retrieval and memory baseline
- workbench inspection paths
- explicit capability declaration and assembly

What is still missing is a clearer planning-level treatment of two adjacent system concerns:

1. executor families are not yet treated as first-class planning concepts beyond the current executor seam
2. external AI planning and external knowledge inputs are not yet normalized into durable system objects

Without this slice, the system risks:

- treating every executor as if it served the same type of work
- treating external planning as loose chat residue instead of task semantics
- treating external knowledge capture as ad hoc notes instead of staged retrieval-layer input
- polluting long-term memory with unverified conversation fragments

## What Problem It Solves

This slice is intended to improve:

- routing clarity between cognitive execution and environment execution
- normalization of external planning into task-linked objects
- normalization of external knowledge into staged knowledge records
- evidence-preserving ingestion without turning chat history into the system of record

The goal is not to add more generic conversation features. The goal is to make outside inputs legible inside the existing workflow system.

## Primary Tracks

- `Retrieval / Memory`
- `Execution Topology`

## Secondary Tracks

- `Workbench / UX`
- `Capabilities`

## Scope

This slice should stay focused on:

- planning-level executor family distinction between API executors and CLI executors
- ingestion boundaries for external planning handoff
- ingestion boundaries for external knowledge capture
- task objects versus knowledge objects
- staged knowledge promotion and persistence semantics
- source traceability and artifact-backed evidence
- routing and normalization rules that can later guide implementation

## Non-Goals

This slice is not for:

- building a new generic chat UI
- pretending API executor support is already implemented
- broad hosted platform engineering
- marketplace expansion
- replacing the current retrieval or task loop baseline
- storing full external chat logs as canonical knowledge

## Key Design Principles

- Treat executor family as a planning concern before turning it into implementation detail.
- Route by family and capability, not only by vendor or tool name.
- Preserve the existing distinction between model, runtime backend, and executor.
- Do not make chat history the system of record.
- Preserve source traceability for external input.
- Prefer artifact-backed evidence over unsupported summaries.
- Separate planning objects from reusable knowledge objects.
- Prefer staged promotion over immediate canonicalization.

## Executor Family Distinction

The current repository already distinguishes:

- model
- runtime backend
- executor

The next planning direction should further distinguish executor families:

- **API executor**
  - intended for discussion, planning, summarization, route judgment, retrieval-backed synthesis, and structured output
  - expected to fit official model APIs or deeper hosted reasoning interfaces more naturally
  - should not be assumed to perform environment execution by default
- **CLI executor**
  - intended for repository reading, file editing, command execution, local tool use, and environment-bound actions
  - expected to fit local or semi-local code-agent shells more naturally
  - should not be assumed to be the best default surface for every planning-heavy or synthesis-heavy task

This is still a planning-level distinction, not a fully implemented runtime distinction.

## External Planning Handoff

External planning handoff should be treated as a valid input path.

The intended direction is:

- capture outside planning outputs
- normalize them into explicit task semantics
- persist them as task-linked records or artifacts
- keep the task object separate from raw conversational residue

Examples of what should become task semantics rather than loose notes:

- task goals
- constraints
- acceptance criteria
- priority ordering
- operator intent
- proposed next actions

## External Knowledge Capture

External knowledge capture should also be treated as a valid input path, but it should not bypass retrieval and memory discipline.

The intended direction is:

- capture outside summaries, findings, references, or distilled notes
- preserve source linkage where possible
- store them as staged knowledge objects
- make them available to retrieval only according to promotion policy

This belongs primarily to the `Retrieval / Memory` track, not to a generic chat-interface layer.

## Task Objects Versus Knowledge Objects

The system should keep these object classes separate:

- **task objects**
  - execution intent
  - planning structure
  - constraints
  - acceptance criteria
  - run linkage
- **knowledge objects**
  - reusable evidence
  - extracted findings
  - summarized references
  - task-linked or artifact-linked context
  - retrieval-facing distilled records

That separation is important because not every plan becomes reusable knowledge, and not every knowledge fragment should change task semantics.

## Staged Ingestion And Promotion

External input should not jump directly into canonical memory.

The intended promotion path should be explicit:

- `raw`
  - direct capture from an outside discussion, note, or imported artifact
- `candidate`
  - normalized enough to be reviewable and linked to a task or source
- `verified`
  - checked against evidence, task outcomes, or trusted sources
- `canonical`
  - stable enough to serve as durable retrieval-layer knowledge

This model is intended to preserve evidence while avoiding knowledge-base pollution.

## Evidence And Traceability

The system should preserve:

- source identity
- task linkage where relevant
- artifact linkage where relevant
- capture time
- promotion status
- verification status

Distillation is allowed, but unsupported transformation should be avoided. The long-term system should prefer artifact-backed evidence over free-floating remembered conclusions.

## Proposed Work Items

Possible follow-on slices:

1. executor family declaration baseline
2. task-semantics ingestion baseline for external planning handoff
3. staged knowledge-object record baseline
4. artifact-backed external knowledge capture baseline
5. promotion and verification policy baseline
6. inspection-path updates for task objects and staged knowledge objects

## Stop / Go Framing

This note is a planning entrypoint, not an implementation claim.

Go:

- if the next slice should clarify executor-family routing and external-input normalization
- if the next slice should strengthen retrieval and execution boundaries without changing current Phase 5 conclusions

Stop:

- if the work starts drifting into generic chat UI design
- if the work starts pretending API executor support already exists
- if the work starts broadening into marketplace or platform work without a narrower slice definition
