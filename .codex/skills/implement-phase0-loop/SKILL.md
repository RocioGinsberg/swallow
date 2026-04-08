---
name: implement-phase0-loop
description: "Historical skill for work that explicitly targets the accepted Phase 0 baseline loop: CLI task intake, repo/markdown retrieval, Codex-centered execution, task/event/artifact recording, and summary output."
---

# Implement Phase 0 Loop

## Purpose

Use this skill only when a task explicitly asks to revisit or compare against the accepted Phase 0 loop.

## When to use

Use this skill when:
- validating or revisiting historical Phase 0 behavior
- comparing current implementation against the accepted minimal loop
- making a narrow fix that explicitly targets the original CLI-first baseline

Do not use this skill when:
- the task primarily concerns current Phase 2 routing work
- the task is driven by current active-phase planning
- the task is mostly UI work beyond the CLI
- the task is about broad source-adapter expansion

## Workflow

1. Re-read `/home/rocio/projects/swallow/docs/phase0_exit_checklist.md` and `current_state.md`.
2. Identify the narrowest historical baseline behavior that matters for the task.
3. Keep the code path visible and testable.
4. Preserve clean seams for later phases, but do not pull current routing work back into a Phase 0 framing.
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

- Do not treat this as the default implementation skill for the current repository phase.
- Avoid dragging current Phase 2 routing work into a Phase 0-only framing.
- Avoid broad multi-agent behavior.
- Prefer local-first inspectable behavior.
- Keep artifacts easy to inspect on disk.
