# System Tracks

This document defines the long-running delivery tracks for the repository.

The goal is to keep future planning grounded in a stable system map instead of treating each phase as an isolated bundle of mixed work.

## Why Tracks Exist

The repository is already beyond a single MVP phase.

Without explicit tracks, later phases are likely to mix together:

- execution topology work
- retrieval work
- capability-system work
- workbench-facing usability
- validation and policy work

That makes phase boundaries less clear and makes it harder to tell what the system has actually completed.

Tracks solve that by separating:

- the long-running system concerns
- the current implementation checkpoint
- the next phase-specific slice

## Track Map

### 1. Core Loop

Owns:

- orchestrator lifecycle
- harness runtime loop
- task intake
- phase progression
- state and event truthfulness
- artifact write timing
- resume semantics

Current status:

- strong local-first baseline implemented
- accepted lifecycle semantics established in Phase 0
- hardened through Phase 1 and Phase 2 without breaking the core loop
- preserved through Phase 3, Phase 4, and Phase 5 while topology, workbench, and capability truth expanded
- tightened further in Phase 7 and Phase 8 through explicit execution-site and execution-control artifacts without breaking the accepted task loop
- preserved through Phase 9 while operator-control entrypoints expanded around the accepted run path
- tightened further in Phase 10 through checkpoint snapshots, resume semantics, interruption-oriented recovery classification, and explicit recovery-boundary guidance

Still needed for a fuller system:

- richer long-running workflow progression
- stronger interruption and recovery policies
- better operator checkpoints and stop/resume control

### 2. Retrieval / Memory

Owns:

- source adapters
- parsing and chunking
- ranking and rerank logic
- grounding outputs
- retrieval artifact indexing
- memory reuse around retrieved context
- retrieval evaluation fixtures
- external planning ingestion and handoff normalization
- external knowledge capture
- staged knowledge promotion
- task-linked and artifact-linked knowledge reuse
- noise control, verification, and canonicalization

Current status:

- baseline retrieval for repo files and markdown notes completed in Phase 1
- stronger retrieval baseline completed after Phase 2 through:
  - adapter seam
  - query shaping and rerank
  - task-artifact retrieval
  - retrieval-memory reuse tightening
  - retrieval artifact indexing cleanup
  - fixture-based regression coverage
- external planning ingestion and staged knowledge-object handling completed in the post-Phase-5 executor / external-input slice
- reusable-knowledge retrieval, verification, refresh, invalidation, canonicalization boundaries, cross-task reuse, and fixture-backed evaluation tightening completed in Phase 6

Still needed for a fuller system:

- clearer historical-context policy
- more deliberate indexing/update policy
- broader source coverage where justified
- stronger retrieval evaluation depth
- clearer external-input ingestion policy
- explicit distinction between task objects and knowledge objects
- staged `raw` / `candidate` / `verified` / `canonical` promotion semantics

### 3. Execution Topology

Owns:

- executor boundaries
- route selection
- backend and executor capability fit
- local versus remote execution-site boundaries
- transport and handoff readiness
- executor family distinction
- API-executor versus CLI-executor routing boundaries
- family-specific capability and integration contracts

Current status:

- executor seam baseline completed in Phase 1
- route, policy, compatibility, and remote-ready metadata baselines completed in Phase 2
- execution-site, dispatch, handoff, execution-fit, and attempt-identity baselines completed in Phase 3
- execution-site contract, attempt ownership, handoff contract, local-detached execution, and family-aware execution-fit tightening completed in Phase 7

Still needed for a fuller system:

- real remote execution boundary beyond the current local-inline and local-detached baselines
- transport or job handoff semantics across machines
- longer-running or resumable execution-site behavior
- broader family-aware routing between API executors and CLI executors
- explicit integration rules for hosted API execution versus local or semi-local CLI shells

### 4. Capabilities

Owns:

- tools
- skills
- profiles
- workflows
- validators
- future capability packs

Current status:

- small local-first capability surface exists
- validators and route capability declarations are explicit
- Phase 5 completed the baseline with explicit requested manifests, effective assembly records, task-level selection, inspection paths, and clear failure for unknown capability references
- the capability system remains intentionally light rather than marketplace-oriented

Still needed for a fuller system:

- cleaner capability pack structure
- stronger composition and versioning rules
- clearer assembly between workflows, validators, and profiles

### 5. Workbench / UX

Owns:

- CLI ergonomics
- artifact inspection paths
- review and hand-off usability
- future TUI/UI surfaces
- input entrypoints for planning handoff and knowledge capture

Current status:

- CLI is usable and artifact-driven
- Phase 4 completed the baseline with task listing, inspect, grouped artifacts, review, and operator-attention views
- later slices added inspection paths for capabilities, task semantics, knowledge objects, reusable knowledge, execution-site, dispatch, handoff, execution-fit, and execution-control policy
- Phase 9 completed the current operator-control baseline with queue, control, attempt history/comparison, retry, and rerun entrypoints

Still needed for a fuller system:

- better action-oriented task browsing and review workflows
- more operator-friendly control entrypoints around retry, rerun, and repeated attempts
- future workbench interface beyond raw CLI
- clearer operator-facing entrypoints for external planning and external knowledge capture without collapsing those concerns into chat history

### 6. Evaluation / Policy

Owns:

- validation
- compatibility checks
- retrieval evaluation
- future permission, retry, budget, and operator policy controls

Current status:

- validator baseline completed in Phase 1
- route compatibility baseline completed in Phase 2
- retrieval regression fixtures completed in the post-Phase-2 retrieval baseline
- knowledge-policy checks completed in the post-Phase-5 executor / external-input and retrieval / memory-next slices
- execution-control policy baseline completed in Phase 8 through retry, stop, escalation, detached-checkpoint, and execution-budget records plus operator-facing inspection paths

Still needed for a fuller system:

- broader execution policies
- richer operator safety checkpoints
- more systematic regression coverage across tracks

## Phase-To-Track Mapping

### Phase 0

Primary tracks:

- Core Loop

Secondary effect:

- initial Retrieval / Memory baseline
- initial Workbench / UX baseline through CLI and artifacts

### Phase 1

Primary tracks:

- Retrieval / Memory
- Core Loop hardening
- Evaluation / Policy baseline

Secondary effect:

- early Execution Topology progress through executor seam cleanup

### Phase 2

Primary tracks:

- Execution Topology
- Evaluation / Policy around route fit

Secondary effect:

- Core Loop preserved while routing became explicit

### Phase 3

Primary tracks:

- Execution Topology

Secondary effect:

- Evaluation / Policy around dispatch and execution-fit truth
- Workbench / UX improvements through inspection of topology-specific artifacts

### Phase 4

Primary tracks:

- Workbench / UX

Secondary effect:

- Core Loop preserved while operator inspection paths expanded
- Retrieval / Memory and Execution Topology became easier to inspect through CLI workbench commands

### Phase 5

Primary tracks:

- Capabilities

Secondary effect:

- Workbench / UX improvements through capability inspection paths
- Core Loop preserved while capability declaration and assembly became explicit task truth

### Post-Phase-2 Retrieval Baseline

Primary tracks:

- Retrieval / Memory

Secondary effect:

- Workbench / UX improvements through retrieval inspection paths
- Evaluation / Policy improvements through retrieval fixtures

### Post-Phase-5 Executor / External-Input Slice

Primary tracks:

- Retrieval / Memory
- Execution Topology

Secondary effect:

- Workbench / UX improvements through task-semantics and knowledge-object inspection
- Evaluation / Policy improvements through knowledge-policy checks

### Post-Phase-5 Retrieval / Memory Next Slice

Primary tracks:

- Retrieval / Memory
- Evaluation / Policy

Secondary effect:

- Workbench / UX improvements through reusable-knowledge inspection paths

### Phase 6

Primary track:

- Retrieval / Memory

Secondary effect:

- Evaluation / Policy
- Workbench / UX
- Capabilities

### Phase 7

Primary tracks:

- Execution Topology

Secondary effect:

- Evaluation / Policy through execution-fit and ownership tightening
- Workbench / UX through execution-site and handoff-contract inspection paths
- Core Loop preserved while a real local-detached boundary was added

### Phase 8

Primary tracks:

- Evaluation / Policy

Secondary effect:

- Workbench / UX through policy-focused inspect, review, and grouped artifact views
- Execution Topology preserved while detached execution gained explicit checkpoint policy
- Core Loop preserved while retry, stop, and budget truth became explicit

### Phase 9

Primary tracks:

- Workbench / UX

Secondary effect:

- Core Loop through rerun/retry control ergonomics
- Evaluation / Policy through operator-facing control use of existing policy truth

### Phase 10

Primary tracks:

- Core Loop

Secondary effect:

- Workbench / UX through resume and checkpoint entrypoints
- Evaluation / Policy through clearer recovery-boundary decisions

## Planning Rule

Future planning should happen in two passes:

1. decide which track is the current priority
2. define the smallest next phase or planning slice for that track

Do not start a new phase before naming:

- the primary track
- the secondary tracks, if any
- what is explicitly deferred

## Current Planning Position

The repository is now at a closeout checkpoint with:

- Phase 2 baseline complete
- post-Phase-2 retrieval baseline complete
- Phase 3 baseline complete
- Phase 4 baseline complete
- Phase 5 baseline complete
- post-Phase-5 executor / external-input slice complete
- post-Phase-5 retrieval / memory-next slice complete
- Phase 6 baseline complete
- Phase 7 baseline complete
- Phase 8 baseline complete
- Phase 9 baseline complete
- Phase 10 baseline complete

Current stop/go reference:

- `docs/phase10_closeout_note.md`

Current reusable commit-summary reference:

- `docs/phase10_commit_summary.md`

Next planning requirement:

- choose the next primary track intentionally
- write a fresh kickoff note before starting the next slice
