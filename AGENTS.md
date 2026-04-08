# AGENTS.md

## Repository identity

This repository is building a stateful AI workflow system for knowledge work and code work.

The long-term system is organized around:
- an **orchestrator**
- a **harness runtime**
- reusable **capabilities**
- **state / memory / artifacts**
- **provider routing**

Capabilities are not only tools. They may include:
- tools
- skills
- profiles
- workflows
- validators

This is not a generic chatbot repository. It is also not a pure RAG repository. It is an AI workflow system with orchestration, harnessed execution, retrieval, reusable capabilities, and persistent task state.

## Delivery phases

This project is developed in phases.

- Phase 0: CLI-first MVP with a minimal orchestrator, a minimal harness runtime, a minimal capability registry, Codex as the primary local executor adapter, repository-file retrieval, markdown-note retrieval, and a minimal task/event/artifact loop.
- Phase 1: improve retrieval quality, refine the harness runtime, add a second executor, and introduce richer capability packs and validation policies.
- Phase 2: introduce a broader provider-routing layer, including proxy/provider abstractions, routing policies, and broader capability/plugin extension surfaces.
- Post-Phase-2 retrieval baseline: strengthen retrieval as a durable system layer through adapter seams, rerank/query shaping, broader local source coverage, retrieval-memory reuse, artifact indexing, and regression fixtures.
- Phase 3: continue the system through an `Execution Topology` slice that turns remote-ready metadata into a clearer execution-site, dispatch, handoff, and attempt-ownership boundary.

Phase 0, Phase 1, and the planned Phase 2 baseline are already complete.
The post-Phase-2 retrieval baseline is also complete.
New implementation work should begin from the current planning checkpoint rather than treating Phase 0 as the active default.

## System tracks

Long-running planning should follow system tracks first, then phase slices.

Primary tracks:
- `Core Loop`
- `Retrieval / Memory`
- `Execution Topology`
- `Capabilities`
- `Workbench / UX`
- `Evaluation / Policy`

Use `docs/system_tracks.md` as the top-level planning map before defining or executing a new phase slice.

## Current planning state

Current planning checkpoint: Phase 4 closeout.

Current implementation status:
1. Phase 0 accepted
2. Phase 1 complete
3. Phase 2 baseline complete
4. post-Phase-2 retrieval baseline complete
5. Phase 3 baseline complete
6. Phase 4 baseline complete

Current planning direction:
1. anchor new work in `docs/system_tracks.md`
2. use `docs/phase4_closeout_note.md` as the current Workbench / UX stop/go reference
3. use `docs/phase3_closeout_note.md` as the execution-topology stop/go reference
4. write a fresh planning note before expanding beyond the completed Phase 4 baseline

Do not default new work back to a generic MVP feature bundle. Start from the current system map and current closeout checkpoint.

## Current scope

Current planning should focus on:
- preserving the accepted local task loop and artifact semantics
- treating the completed Phase 3 and Phase 4 baselines as stable checkpoints
- planning the next slice against the repository’s current system tracks
- avoiding accidental open-ended continuation of execution-topology or Workbench / UX work
- keeping retrieval, routing, validation, memory, and artifact semantics inspectable

## Current non-goals

Do not optimize by default for:
- distributed worker clusters
- hosted queue infrastructure
- broad third-party backend marketplaces
- large plugin ecosystems
- multi-tenant architecture
- premature workbench UI breadth
- hidden retrieval infrastructure
- heavy production platform engineering

## Working principles

- Build the smallest end-to-end loop first.
- Prefer explicit, readable modules over clever abstractions.
- Keep architecture extensible, but do not over-engineer for future phases.
- Treat the **orchestrator** and **harness runtime** as separate concerns.
- Treat **capabilities** as first-class reusable assets, not scattered prompt fragments.
- Treat Git as the source of truth for code changes.
- Treat retrieval as a first-class subsystem, not a helper utility.
- Treat task state, event logs, and artifact outputs as required system capabilities.
- Prefer local and deterministic workflows where possible.
- Keep track and phase boundaries clear. Do not slip back into Phase 0 framing when the active planning slice is later-track work.

## Retrieval principles

The current retrieval baseline supports:
- repository files
- markdown / obsidian notes
- task-scoped artifacts when explicitly requested

Do not treat all sources identically.
Source-specific parsing and chunking are preferred.

## Retrieval and Context Policy

- Treat retrieval as a system-level knowledge layer, not a single-agent-only feature.
- Do not bind retrieval to one executor, one model vendor, or one product-surface agent.
- Default direction:
  - enhanced RAG first
  - light agentic retrieval later
  - GraphRAG only when multi-hop structure or cross-document relationship modeling is clearly needed
- GraphRAG is optional, not the default path.
- Keep the RAG layer and the orchestrator separate:
  - the RAG layer is responsible for ingestion, parsing, chunking, metadata, hybrid retrieval, rerank, and citation
  - the orchestrator is responsible for whether to retrieve, which source to retrieve, whether to retrieve again, and when to stop
- Treat enhanced RAG as a retrieval-layer upgrade, and agentic retrieval as an orchestration-layer upgrade.
- Vendor built-in retrieval from Codex, Claude, Gemini, or similar tools may be reused as a shortcut, but it must not be the only knowledge substrate.
- Preserve an independent, traceable, orchestrator-controlled retrieval layer as the primary system baseline.
- When tasks move to API key plus cheap-model operation, do not assume vendor built-in retrieval still exists or remains reliable.
- If a task depends on external knowledge, workspace files, notes, docs, or multi-source material, route through the system retrieval layer or an equivalent explicit interface.
- Do not collapse context into only the current prompt or current conversation.
- Distinguish at least four context layers:
  - session context
  - workspace context
  - task context
  - historical context
- Retrieval outputs must remain traceable, citable, and reusable.
- Do not return only conclusions when source grounding is required; preserve sources, key excerpts, and task linkage in a form that can be written into state, memory, or artifacts.
- Treat retrieval as cooperating with state / memory / artifacts, not as a one-shot prompt helper.
- Domain adaptation should live in domain packs or capability packs, not in scattered hard-coded prompt fragments.
- Domain-specific behavior may include parser choices, chunk policy, metadata schema, query rewrite policy, retrieval policy, and evaluation sets.
- Current priority order:
  - stable baseline
  - enhanced retrieval
  - light agentic retrieval
  - graph only when clearly needed

## Capability principles

For the current baseline:
- prefer a small built-in capability set
- keep tool specs explicit
- keep permission expectations explicit
- do not build a broad plugin marketplace by default
- allow future extension toward tools, skills, profiles, workflows, and validators

## State and artifact principles

The repository should preserve a clear distinction between:
- **state**: current task status and step progression
- **events**: append-only execution history
- **artifacts**: files and outputs produced by the run

Keep these concepts separate even if the initial storage is simple.

## Provider and executor principles

For the current baseline:
- Codex is the default local executor adapter
- explicit routing and capability declarations already exist
- avoid broad provider abstraction unless it directly helps keep interfaces clean
- keep executor boundaries narrow and swappable

The next planning concern is no longer "whether routing exists" or "whether execution-topology truth exists." Those baselines are now implemented; the next concern is choosing the next track and boundary intentionally.

## Backend compatibility principles

For future phases:
- distinguish clearly between **model**, **runtime backend**, and **executor**
- do not assume all backends support the same tool loops, handoff semantics, resumability, or code execution
- a unified harness boundary may exist, but backend capabilities must be declared explicitly
- prefer capability-based routing over assuming universal backend compatibility

## Documentation expectations

When producing or modifying implementation plans, keep them aligned with this structure:
- orchestrator
- harness runtime
- capabilities
- state / memory / artifacts
- provider router


## Runtime Shape

This project is designed around a **local workbench + optional remote heavy execution** model.

### Design Intent

* The **local side** is the primary workbench for daily interaction:

  * desktop UI
  * lightweight CLI
  * task creation
  * artifact review
  * local file access
  * small-scale processing

* The **remote side** is reserved for heavier or longer-running workloads:

  * long-running workflows
  * heavy RAG pipelines
  * large repository analysis
  * multi-step agent execution
  * persistent background services

### Architectural Constraints

When implementing features, keep the following boundaries clear:

1. **UI is not the executor**
   The workbench should not be tightly coupled to execution internals.

2. **Execution location is abstractable**
   A task may run locally or remotely. Avoid hard-coding logic that assumes a single machine.

3. **State and artifacts must survive execution context changes**
   Task state, logs, outputs, and artifacts should remain understandable and portable regardless of where execution happens.

4. **Local-first is an MVP strategy, not a permanent limitation**
   The current phase may prioritize local execution for simplicity, but the architecture should remain remote-capable.

### Current Implementation Priority

At this stage, prefer:

* single-user usability over multi-user infrastructure;
* clear module boundaries over full deployment complexity;
* workflow validation over platform engineering;
* operator-facing task review and inspection improvements over broader platform expansion.

### Non-Goals for the Current Phase

Do not optimize early for:

* multi-tenant architecture;
* distributed worker clusters;
* large-scale hosted infrastructure;
* complex permission and billing systems.

The immediate goal is to build a system that is **personally useful, structurally clean, and extensible later**.

Avoid slipping back into older, less precise labels such as a single generic “agent execution layer” when a harness/runtime distinction matters.
