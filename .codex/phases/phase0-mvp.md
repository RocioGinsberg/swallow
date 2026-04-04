# Phase 0 MVP

## Goal

Build a CLI-first MVP for a stateful AI workflow loop.

## What Phase 0 must deliver

Phase 0 should deliver a working local loop with these components:
- CLI entrypoint
- task manager
- minimal orchestrator
- minimal harness runtime
- retrieval service for repo files and markdown notes
- minimal capability registry
- built-in tools only
- Codex-first local executor adapter
- state tracking
- event logging
- artifact registration
- summary and handoff output generation

## Suggested implementation order

1. Create the project skeleton.
2. Define core task, event, and artifact models.
3. Implement the CLI entrypoint.
4. Implement repository-file retrieval.
5. Implement markdown / Obsidian retrieval.
6. Implement the minimal capability registry.
7. Implement the minimal orchestrator.
8. Implement the harness runtime loop.
9. Implement summary and handoff outputs.
10. Add basic validation and a runnable example.

## Minimal state machine

Recommended first states:
- created
- planning
- retrieving
- executing
- summarizing
- done
- blocked

## Required outputs

Each meaningful task run should be able to produce:
- a task record
- one or more event records
- one or more artifact records
- a `summary.md`
- a `handoff.md` or equivalent run summary

## Validation target

At minimum, a developer should be able to:
- run a CLI command
- point it to a repo path and notes path
- get a traceable task run
- inspect the generated summary output
- inspect what capabilities were used in the run

## Non-goals

Phase 0 should not try to solve:
- desktop UI
- broad provider routing
- full multi-agent orchestration
- many source adapters
- advanced retrieval optimization
- complex background workers
- broad external plugin compatibility

## Exit criteria

Phase 0 is complete when:
- the MVP loop is runnable
- retrieval from both source types works at a basic level
- task/event/artifact tracking is visible and useful
- output summaries are readable and structured
- the orchestrator / harness / capability boundaries are clear enough to extend in Phase 1
