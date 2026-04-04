# Phase 0 MVP Scope

## Objective

Build a CLI-first MVP that proves a useful and inspectable workflow loop for local project tasks.

## Required capabilities

The MVP must be able to:
- create a task from CLI input
- point at a repository path
- point at a markdown / Obsidian notes path
- retrieve relevant context from those sources
- run a minimal orchestrator
- run a harnessed execution loop
- use a minimal built-in capability set
- call a Codex-centered local executor adapter
- persist task state, events, and artifact references
- emit structured summary and handoff outputs

## Nice-to-have but optional

These are allowed only if they do not slow the MVP significantly:
- simple YAML or TOML task config input
- a minimal replayable run log
- lightweight chunk summaries for better retrieval
- a single sample/demo command
- a very small capability manifest for built-in tools

## Explicit non-goals

Do not treat the following as MVP requirements:
- desktop UI
- broad multi-agent implementation
- multiple provider integrations
- generalized plugin marketplace
- multimodal ingestion
- advanced reranking
- large capability compatibility layers
- production deployment automation

## Success criteria

The MVP is successful if it can:
1. accept a real local task
2. retrieve useful repository and note context
3. execute at least one meaningful harnessed task loop
4. record state and artifacts clearly
5. emit a readable summary and handoff output

## Design constraints

- prefer a few clear modules over many abstract ones
- keep data flow easy to inspect
- keep orchestrator and harness runtime separate
- make it easy to swap or extend executors later, but do not build a large routing layer now
- keep retrieval source-specific where practical
- keep capabilities small and explicit in Phase 0
- keep local development easy to run and debug
