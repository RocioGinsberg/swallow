# Current Scope

## What the repository can do now

The current repository can:

- create and run tasks from the CLI
- retrieve context from repo files and markdown notes
- execute through multiple local routes
- persist route decisions and route-policy inputs
- validate run outputs
- write reusable grounding and task-memory artifacts

## What the current phase has established

The completed Phase 3 and Phase 4 baselines established:

- execution-topology clarity
- execution-site and dispatch truthfulness
- handoff and attempt-ownership semantics
- operator inspection of topology-specific artifacts
- task-list and task-overview workbench entrypoints
- grouped artifact review and operator attention views

The completed Phase 5 baseline established:

- explicit requested capability manifests
- explicit effective capability assembly records
- task-level capability selection during create and run
- operator-facing capability inspection
- clear failure for unknown capability references

The completed post-Phase-5 executor / external-input slice established:

- explicit executor-family declaration in planning and persistence surfaces
- task-semantics ingestion for imported planning
- staged knowledge-object records for imported external knowledge
- artifact-backed evidence tracking and knowledge-policy checks
- CLI inspection paths for task semantics, knowledge objects, and knowledge policy

The completed post-Phase-5 retrieval / memory-next slice established:

- explicit retrieval-eligibility and reuse-scope declarations on knowledge objects
- a task-linked versus reusable knowledge partition record
- an opt-in verified-knowledge retrieval source
- reuse-aware retrieval memory and rerun prompt visibility
- a tighter reuse gate for artifact-backed verified knowledge
- CLI inspection visibility for reused knowledge inside retrieval and review flows

The completed Phase 8 baseline established:

- explicit retry, stop, escalation, and execution-budget policy artifacts
- detached-specific checkpoint policy for `local_detached` execution
- policy-state visibility across handoff, memory, summary, resume, inspect, review, and grouped artifact lists
- a compact operator-facing `swl task policy` inspection path

## Explicit non-goals right now

Do not treat these as current-slice requirements:

- full remote execution
- broad third-party backend integrations
- pricing-aware optimization
- large plugin ecosystems
- distributed worker infrastructure
- heavy tracing or telemetry platforms

## Practical planning rule

When planning the next task:

- prefer `docs/system_tracks.md` before phase-local planning
- use `docs/phase3_closeout_note.md` before deciding whether to continue execution-topology work
- use `docs/phase4_closeout_note.md` before deciding whether to continue Workbench / UX work
- use `docs/phase5_closeout_note.md` before deciding whether to continue `Capabilities` work
- use `docs/post_phase5_executor_and_external_input_closeout_note.md` before deciding whether to continue that completed slice
- use `docs/post_phase5_retrieval_memory_next_closeout_note.md` before deciding whether to continue that completed `Retrieval / Memory` slice
- use `docs/phase6_closeout_note.md` before deciding whether to continue the completed `Retrieval / Memory Operationalization` baseline
- use `docs/phase7_closeout_note.md` before deciding whether to continue the completed `Execution Topology` slice
- use `docs/phase8_closeout_note.md` as the stop/go reference for the completed `Evaluation / Policy` slice
- prefer a fresh planning note over open-ended continuation
