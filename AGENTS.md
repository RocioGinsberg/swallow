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
- Later phases may add a richer workbench UI, more source adapters, more automation, and more advanced multi-agent behavior.

Only Phase 0 is currently active and should be executed concretely.
Later phases are directional and may change based on implementation findings.

## Current phase

Current phase: Phase 0 MVP.

The Phase 0 goal is to prove the smallest useful end-to-end loop:
1. accept a task
2. retrieve relevant context from local sources
3. run a harnessed execution loop through a Codex-first local executor adapter
4. record task state, events, and artifacts
5. generate a structured summary and resume note output

## In scope for Phase 0

Phase 0 should focus on:
- CLI entrypoint only
- a minimal orchestrator with a small state machine
- a minimal harness runtime loop
- Codex as the primary local code executor adapter
- Git repository files as a retrieval source
- Markdown / Obsidian notes as a retrieval source
- a minimal capability registry
- built-in tools only
- local-first development
- simple, inspectable architecture
- artifact outputs such as `summary.md`, `resume_note.md`, and task-scoped output folders

## Out of scope for Phase 0

Do not optimize for these yet unless explicitly requested:
- full desktop UI
- complex multi-agent runtime
- broad provider routing
- broad external plugin compatibility
- multimodal ingestion
- advanced background automation
- premature generalization across many source types
- heavy infrastructure
- full production hardening
- large capability marketplaces

## Working principles

- Build the smallest end-to-end loop first.
- Prefer explicit, readable modules over clever abstractions.
- Keep architecture extensible, but do not over-engineer for future phases.
- Treat the **orchestrator** and **harness runtime** as separate concerns.
- Treat **capabilities** as first-class reusable assets, not scattered prompt fragments.
- Treat Git as the source of truth for code changes.
- Treat retrieval as a first-class subsystem, not a helper utility.
- Treat task state, event logs, and artifact outputs as required MVP capabilities.
- Prefer local and deterministic workflows where possible.
- Keep phase boundaries clear. Do not implement Phase 2 abstractions during Phase 0 unless they are needed to keep Phase 0 code clean.

## Retrieval principles

For Phase 0, retrieval should support only:
- repository files
- markdown / obsidian notes

Do not treat all sources identically.
Source-specific parsing and chunking are preferred.

## Capability principles

For Phase 0:
- prefer a small built-in capability set
- keep tool specs explicit
- keep permission expectations explicit
- do not build a broad plugin marketplace
- allow future extension toward tools, skills, profiles, workflows, and validators

## State and artifact principles

Phase 0 should preserve a clear distinction between:
- **state**: current task status and step progression
- **events**: append-only execution history
- **artifacts**: files and outputs produced by the run

Keep these concepts separate even if the initial storage is simple.

## Provider and executor principles

During Phase 0:
- Codex is the default local executor adapter
- avoid broad provider abstraction unless it directly helps keep interfaces clean
- keep executor boundaries narrow and swappable

The provider-routing layer is a later concern, not a Phase 0 deliverable.

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
* minimal viable remote hooks over complete distributed execution.

### Non-Goals for the Current Phase

Do not optimize early for:

* multi-tenant architecture;
* distributed worker clusters;
* large-scale hosted infrastructure;
* complex permission and billing systems.

The immediate goal is to build a system that is **personally useful, structurally clean, and extensible later**.

Avoid slipping back into older, less precise labels such as a single generic “agent execution layer” when a harness/runtime distinction matters.
