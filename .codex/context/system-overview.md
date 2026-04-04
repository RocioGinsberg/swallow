# System Overview

## One-sentence positioning

This project is a stateful AI workflow system for knowledge work and code work, combining orchestration, harnessed execution, reusable capabilities, retrieval, and persistent task tracking.

## Why this project exists

Many real tasks are fragmented across code repositories, notes, documents, logs, and partial outputs. Generic chat interfaces do not reliably track task state, retrieve the right project context, standardize reusable capabilities, or organize incremental work products.

This project exists to create a practical AI workflow loop that can:
- retrieve relevant local context
- execute work in a local code environment
- record progress and artifacts
- reuse structured capabilities across tasks
- produce structured summaries and handoff outputs

## Long-term target shape

The long-term system includes:
- an orchestration layer
- a harness runtime
- reusable capabilities
- retrieval and memory over multiple local sources
- task state, event logs, and artifacts
- optional provider routing and cost-aware execution policies
- replaceable local and cloud executors

## Current MVP boundary

The current boundary is intentionally narrow.

Phase 0 aims to prove a CLI-first MVP with:
- a CLI task entrypoint
- a minimal orchestrator
- a minimal harness runtime
- a minimal capability registry with built-in tools only
- Codex as the primary local code executor adapter
- retrieval from repository files
- retrieval from markdown / Obsidian notes
- minimal task, event, and artifact persistence
- structured summary and handoff outputs

## Core subsystems in the final architecture

- interaction / workbench layer
- orchestrator
- harness runtime
- capabilities layer
- state / memory / artifacts layer
- provider router
- external models, executors, and utilities

## Current implementation strategy

During Phase 0:
- prioritize a narrow and reliable end-to-end loop
- keep modules explicit and inspectable
- avoid premature provider abstraction
- avoid broad source ingestion
- avoid broad plugin/platform expansion
- validate the system against real local tasks

## Non-goals for now

Not goals for Phase 0:
- desktop UI
- heavy multi-agent scheduling
- wide provider compatibility
- full automation framework
- multimodal retrieval
- elaborate production infrastructure
- broad capability marketplace support

## Expected evolution after Phase 0

If Phase 0 succeeds, the likely next steps are:
- improve retrieval quality
- refine the harness runtime
- add a second code executor
- refine workflow and validation policies
- enrich artifact indexing and memory
- prepare for a provider-routing layer later
