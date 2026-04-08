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

Current status:

- baseline retrieval for repo files and markdown notes completed in Phase 1
- stronger retrieval baseline completed after Phase 2 through:
  - adapter seam
  - query shaping and rerank
  - task-artifact retrieval
  - retrieval-memory reuse tightening
  - retrieval artifact indexing cleanup
  - fixture-based regression coverage

Still needed for a fuller system:

- clearer historical-context policy
- more deliberate indexing/update policy
- broader source coverage where justified
- stronger retrieval evaluation depth

### 3. Execution Topology

Owns:

- executor boundaries
- route selection
- backend and executor capability fit
- local versus remote execution-site boundaries
- transport and handoff readiness

Current status:

- executor seam baseline completed in Phase 1
- route, policy, compatibility, and remote-ready metadata baselines completed in Phase 2

Still needed for a fuller system:

- real local/remote execution boundary
- transport or job handoff semantics
- longer-running or resumable execution-site behavior

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
- skills and profiles exist, but the capability system is still intentionally light

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

Current status:

- CLI is usable and artifact-driven
- summary, resume, route, compatibility, grounding, retrieval, and memory inspection paths exist

Still needed for a fuller system:

- better task browsing and review workflows
- more operator-friendly artifact navigation
- future workbench interface beyond raw CLI

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

### Post-Phase-2 Retrieval Baseline

Primary tracks:

- Retrieval / Memory

Secondary effect:

- Workbench / UX improvements through retrieval inspection paths
- Evaluation / Policy improvements through retrieval fixtures

## Planning Rule

Future planning should happen in two passes:

1. decide which track is the current priority
2. define the smallest next phase or planning slice for that track

Do not start a new phase before naming:

- the primary track
- the secondary tracks, if any
- what is explicitly deferred

## Current Planning Position

The repository is now at a planning checkpoint with:

- Phase 2 baseline complete
- post-Phase-2 retrieval baseline complete

The next step should be to define a new planning note against one primary track, most likely:

- Execution Topology
- Workbench / UX
- a narrower next Retrieval / Memory direction
