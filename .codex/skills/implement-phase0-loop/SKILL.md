---
name: implement-phase0-loop
description: Use this skill when the task is to implement or refine the core Phase 0 MVP loop CLI task intake, retrieval from repo and markdown notes, Codex-centered execution, task/event/artifact recording, and summary output.
---

# Implement Phase 0 Loop

## Purpose

Use this skill to keep implementation aligned with the current MVP boundary.

## When to use

Use this skill when:
- implementing the CLI-first MVP
- creating the minimal orchestration loop
- wiring retrieval into execution
- adding task, event, or artifact persistence
- adding summary or handoff generation

Do not use this skill when:
- the task primarily concerns later-phase provider routing
- the task is mostly UI work beyond the CLI
- the task is about broad source-adapter expansion

## Workflow

1. Re-read `.codex/phases/phase0-mvp.md`.
2. Identify the narrowest useful implementation slice.
3. Keep the code path visible and testable.
4. Preserve clean seams for future extension, but avoid large abstraction layers.
5. Validate the slice before expanding scope.
6. Produce a structured progress summary.

## Recommended implementation priority

1. CLI entrypoint
2. task/event/artifact models
3. repo retrieval
4. markdown retrieval
5. execution loop
6. summary output

## Constraints

- Avoid Phase 2 routing abstractions.
- Avoid broad multi-agent behavior.
- Prefer local-first inspectable behavior.
- Keep artifacts easy to inspect on disk.
